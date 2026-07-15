"""对话管理路由

Phase 2: SSE 流式输出（接模型适配层）
"""

import asyncio
import json
import logging
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Query
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from schemas.common import make_response, make_paginated_response, make_error
from schemas.chat import MessageCreate
from services.chat_service import (
    create_message, list_messages, search_messages, clear_messages,
    update_message_status, get_message_by_id,
)
from model_adapter.registry import model_registry
from engine.chat_hooks import chat_integration

logger = logging.getLogger("niuma.chat.sse")
router = APIRouter()

# 活跃的流式生成任务（用于停止生成）
_active_streams: dict[str, asyncio.Event] = {}

# SSE连接配置
SSE_CONNECTION_TIMEOUT = timedelta(minutes=30)  # 30分钟超时
SSE_HEARTBEAT_INTERVAL = 15  # 15秒心跳间隔


# ============================================================
# SSE 事件构造
# ============================================================

def _build_sse_event(event_type: str, data: dict, ensure_ascii: bool = False) -> str:
    """构造标准 SSE 事件字符串。"""
    payload = json.dumps(data, ensure_ascii=ensure_ascii)
    return f"event: {event_type}\ndata: {payload}\n\n"


def _build_sse_comment(comment: str) -> str:
    """构造SSE注释（用于心跳）。"""
    return f": {comment}\n\n"


def _get_level_label(level: int) -> str:
    """获取压缩级别标签"""
    return {0: "正常", 1: "预警", 2: "裁剪中", 3: "已压缩"}.get(level, "未知")


# ============================================================
# 对话上下文构建
# ============================================================

async def _build_from_l1(workspace_id: str) -> list[dict]:
    """从 L1 记忆引擎获取智能上下文。返回消息列表，失败时返回空列表。"""
    from services.memory.memory_service import get_memory_engine
    import logging
    logger = logging.getLogger("niuma.chat.context")

    try:
        mem_engine = get_memory_engine()
        mem_session_id = await mem_engine.get_or_create_session(workspace_id)
        token_status = mem_engine.l1.get_token_status(mem_session_id)

        if not token_status or token_status.total_tokens == 0:
            return []

        l1_messages = await mem_engine.get_context(workspace_id)
        if not l1_messages:
            return []

        # Token 预算检查：如果超阈值，在回复前注入压缩提示
        if token_status.usage_ratio >= 0.60:
            level_label = _get_level_label(token_status.compression_level)
            ratio_pct = round(token_status.usage_ratio * 100, 1)
            l1_messages.insert(0, {
                "role": "system",
                "content": (
                    f"[记忆引擎] 上下文 {level_label}: 已用 {ratio_pct}% "
                    f"({token_status.total_tokens}/{token_status.max_tokens} tokens)，"
                    f"预计还可回复约 {token_status.estimated_remaining_turns} 轮"
                ),
            })
        return l1_messages
    except Exception as e:
        logger.warning(f"L1 memory unavailable for {workspace_id}: {e}", exc_info=True)
        return []


async def _build_from_db(workspace_id: Optional[str]) -> list[dict]:
    """从 DB 回退获取历史消息。"""
    from db.database import get_engine
    from sqlalchemy import text

    engine = get_engine()
    messages = []
    async with engine.connect() as conn:
        if workspace_id:
            result = await conn.execute(
                text(
                    "SELECT role, content FROM chat_messages "
                    "WHERE workspace_id = :ws_id AND status IN ('completed', 'stopped') "
                    "ORDER BY created_at DESC LIMIT 20"
                ),
                {"ws_id": workspace_id},
            )
        else:
            result = await conn.execute(
                text(
                    "SELECT role, content FROM chat_messages "
                    "WHERE workspace_id IS NULL AND status IN ('completed', 'stopped') "
                    "ORDER BY created_at DESC LIMIT 20"
                ),
            )
        rows = list(result.fetchall())
        rows.reverse()
        for row in rows:
            messages.append({"role": row.role, "content": row.content})
    return messages


async def _inject_agent_prompt(messages: list[dict], at_agent_id: str) -> None:
    """如果有 @Agent，注入 system prompt 到上下文头部。"""
    from db.database import get_engine
    from sqlalchemy import text

    engine = get_engine()
    async with engine.connect() as conn:
        agent_result = await conn.execute(
            text("SELECT system_prompt FROM agents WHERE id = :aid AND deleted_at IS NULL"),
            {"aid": at_agent_id},
        )
        agent_row = agent_result.fetchone()
        if agent_row and agent_row.system_prompt:
            messages.insert(0, {"role": "system", "content": agent_row.system_prompt})


async def _build_context(workspace_id: Optional[str], at_agent_id: Optional[str] = None) -> list[dict]:
    """构建对话上下文：铭心记忆注入 → L1 → DB 回退 → Agent 注入 → 内容路由 + 语义评分剪枝 → GoalLoop规则注入。"""
    messages = []

    # ── 铭心：MEMORY.md / USER.md 自动注入（Hermes 兼容，最高优先级）──
    try:
        from engine.memory_loader import memory_loader
        from config.settings import settings as app_settings
        workspace_root = str(app_settings.BASE_DIR.parent) if app_settings.BASE_DIR else None
        mem_ctx = memory_loader.build_context(workspace_root=workspace_root)
        if mem_ctx.system_prompt_fragment:
            messages.insert(0, {"role": "system", "content": mem_ctx.system_prompt_fragment})
            import logging
            logging.getLogger("niuma.chat.context").debug(
                f"铭心: 注入 {mem_ctx.total_tokens}t, 来源: {mem_ctx.sources}"
                + (" [已截断]" if mem_ctx.truncated else "")
            )
    except Exception as e:
        import logging
        logging.getLogger("niuma.chat.context").debug(f"铭心不可用: {e}")

    if workspace_id:
        messages = await _build_from_l1(workspace_id)

    if not messages:
        messages = await _build_from_db(workspace_id)

    if at_agent_id:
        await _inject_agent_prompt(messages, at_agent_id)

    # RuleRouter + SemanticGrader 流水线：路由内容类型 → 语义评分 → 智能剪枝
    if messages:
        try:
            from engine.rule_router import rule_router
            from engine.semantic_grader import semantic_grader

            # 提取对话内容用于上下文提示
            context_hint = _extract_context_hint(messages)

            # 消息数超过阈值时启用语义剪枝
            if len(messages) > 15:
                messages = semantic_grader.filter_messages(
                    messages,
                    max_keep=20,
                    context_hint=context_hint,
                )
        except Exception as e:
            import logging
            logging.getLogger("niuma.chat.context").debug(
                f"RuleRouter/SemanticGrader unavailable: {e}, using full context"
            )

    # GoalLoop: 注入相关规则到 system prompt
    if messages:
        try:
            from engine.goal_loop_engine import goal_loop
            context_hint = _extract_context_hint(messages)
            active_rules = goal_loop.get_context_rules(
                task_type="", content_hint=context_hint,
            )
            if active_rules:
                rule_lines = [
                    f"[目标循环] 当前激活规则 ({len(active_rules)}条):",
                ]
                for r in active_rules:
                    rule_lines.append(f"  · {r['name']}: {r['description']}")
                rule_prompt = "\n".join(rule_lines)
                messages.insert(0, {"role": "system", "content": rule_prompt})
        except Exception as e:
            import logging
            logging.getLogger("niuma.chat.context").debug(
                f"GoalLoop unavailable: {e}, skipping rule injection"
            )

    # 太极网格: 注入网格可用性到 system prompt（v2.0）
    if messages:
        try:
            from engine.taiji_mesh import taiji_mesh
            if taiji_mesh.is_initialized and taiji_mesh.contributing:
                stats = taiji_mesh.get_mesh_stats()
                healthy = stats.get("network", {}).get("healthy_peers", 0)
                models = stats.get("network", {}).get("unique_models", 0)
                if healthy > 0:
                    mesh_prompt = (
                        f"[太极网格] 当前可用算力邻居: {healthy}个节点, "
                        f"覆盖{models}个模型。若本地无匹配模型，可请求网格邻居协助推理。"
                    )
                    messages.insert(0, {"role": "system", "content": mesh_prompt})
        except Exception as e:
            import logging
            logging.getLogger("niuma.chat.context").debug(
                f"TaijiMesh unavailable: {e}, skipping mesh context injection"
            )

    return messages


def _extract_context_hint(messages: list[dict]) -> str:
    """从消息列表提取上下文提示（最近一条用户消息）。"""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            hint = msg.get("content", "")
            return hint[:500] if hint else ""
    return ""


# ============================================================
# SSE 流式响应
# ============================================================

async def _stream_response(
    adapter, actual_model: str, messages: list[dict],
    stop_event: asyncio.Event, message_id: str, msg: dict,
):
    """主流式生成器：消费模型适配器事件并逐条 SSE 发送。

    包含完整的异常处理、资源清理和取消支持。
    """
    collected_content = ""
    total_tokens = 0
    adapter_resource = None

    try:
        logger.info(f"SSE stream started for message_id={message_id}, model={actual_model}")
        adapter_resource = adapter

        async for event in adapter.chat_stream(messages):
            # 停止检查
            if stop_event.is_set():
                logger.info(f"SSE stream stopped by client for message_id={message_id}")
                await update_message_status(message_id, "stopped",
                                            content=collected_content, token_count=total_tokens)
                done_data = {
                    "message_id": message_id, "role": "assistant", "total_tokens": total_tokens,
                    "model": actual_model, "finish_reason": "stopped", "partial_content": collected_content,
                }
                yield _build_sse_event("done", done_data)
                return

            event_type = event.get("event", "")
            event_data = event.get("data", {})

            if event_type == "token":
                collected_content += event_data.get("content", "")
                total_tokens = event_data.get("index", 0) + 1
                yield _build_sse_event("token", event_data)

            elif event_type == "done":
                final_content = event_data.get("content", collected_content)
                final_tokens = event_data.get("total_tokens", total_tokens)

                # 产出物自动识别
                extra_kwargs = {}
                try:
                    from services.artifact_service import detect_artifacts
                    artifacts = detect_artifacts(final_content)
                    if artifacts:
                        extra_kwargs["artifacts"] = json.dumps(artifacts)
                except Exception as e:
                    logger.debug(f"Artifact detection failed: {e}")

                await update_message_status(message_id, "completed",
                                            content=final_content, token_count=final_tokens,
                                            **extra_kwargs)
                finish_reason = event_data.get("finish_reason", "stop")
                chat_integration.post_chat_record(
                    content=final_content, workspace_id=msg.get("workspace_id", ""),
                    agent_id=msg.get("at_agent_id", "default"), model_used=actual_model,
                    tokens_used=final_tokens, gate_score=1.0 if finish_reason == "stop" else 0.5,
                    success=finish_reason == "stop", tools_used=0, duration_ms=0,
                )

                # 夜巡：后台非阻塞审查（不影响主流程）
                try:
                    from engine.night_patrol import get_patrol, PatrolContext
                    patrol = get_patrol()
                    patrol_ctx = PatrolContext(
                        message_id=message_id,
                        workspace_id=msg.get("workspace_id", ""),
                        agent_id=msg.get("at_agent_id", "default"),
                        role="assistant",
                        content=final_content,
                        model=actual_model,
                        token_count=final_tokens,
                    )
                    asyncio.ensure_future(patrol.patrol(patrol_ctx))
                except Exception as e:
                    logger.debug(f"夜巡启动失败: {e}")
                
                logger.info(f"SSE stream completed for message_id={message_id}, tokens={final_tokens}")
                done_data = {
                    "message_id": message_id, "role": "assistant",
                    "total_tokens": final_tokens,
                    "model": event_data.get("model", actual_model),
                    "finish_reason": event_data.get("finish_reason", "stop"),
                }
                yield _build_sse_event("done", done_data)

            elif event_type == "error":
                await _handle_stream_error(
                    event_data, message_id, collected_content,
                    total_tokens, actual_model,
                )
                # 错误处理后 yield 对应事件
                error_code = event_data.get("code", "MODEL_UNAVAILABLE")
                if error_code == "MODEL_UNAVAILABLE" and collected_content:
                    yield _build_sse_event("done", {
                        "message_id": message_id, "role": "assistant",
                        "total_tokens": total_tokens, "model": actual_model,
                        "finish_reason": "stopped", "partial_content": collected_content,
                    })
                else:
                    yield _build_sse_event("error", event_data)

    except asyncio.CancelledError:
        logger.warning(f"SSE stream cancelled for message_id={message_id}")
        # 保存已收集的内容
        if collected_content:
            await update_message_status(message_id, "stopped",
                                        content=collected_content, token_count=total_tokens)
        raise  # 重新抛出以正确传播取消信号

    except Exception as e:
        logger.error(f"SSE stream error for message_id={message_id}: {e}", exc_info=True)
        healing = chat_integration.handle_error(
            "internal_error", msg.get("at_agent_id", "default"),
            msg.get("workspace_id", ""), str(e),
        )
        await update_message_status(
            message_id, "error",
            error_info=json.dumps({"code": "INTERNAL_ERROR", "message": str(e), "healing_suggestion": healing}),
        )
        yield _build_sse_event("error", {
            "code": "INTERNAL_ERROR", "message": str(e), "healing": healing,
        })

    finally:
        # 清理资源
        adapter_resource = None
        logger.debug(f"SSE stream resources cleaned for message_id={message_id}")


async def _handle_stream_error(
    event_data: dict, message_id: str, collected_content: str,
    total_tokens: int, actual_model: str,
) -> None:
    """处理流式错误事件。"""
    error_code = event_data.get("code", "MODEL_UNAVAILABLE")

    if error_code == "MODEL_UNAVAILABLE" and collected_content:
        await update_message_status(message_id, "stopped",
                                    content=collected_content, token_count=total_tokens)
    else:
        await update_message_status(message_id, "error",
                                    error_info=json.dumps(event_data))


# ============================================================
# API 路由
# ============================================================

@router.post("/chat/messages", status_code=201)
async def api_send_message(request: Request, body: MessageCreate):
    """发送消息并触发 AI 回复"""
    rid = getattr(request.state, "request_id", "")

    # 创建用户消息
    user_msg = await create_message(
        workspace_id=body.workspace_id,
        content=body.content,
        role="user",
        model=body.model,
        at_agent_id=body.at_agent_id,
    )

    # InstructionCache: 检查高频固定指令缓存，命中则跳过 LLM 调用
    cached_response = None
    try:
        from engine.instruction_cache import instruction_cache
        cached_response = instruction_cache.lookup(
            body.content,
            workspace_id=body.workspace_id or "",
        )
    except Exception as e:
        import logging
        logging.getLogger("niuma.chat.cache").debug(f"InstructionCache lookup failed: {e}")

    # 模型选择：Auto → Smart Allocator, 手动 → 用户指定
    is_auto = not body.model or body.model == "auto"
    requested_model = body.model if (body.model and body.model != "auto") else "deepseek-v4-pro"

    # 太极引擎：Auto模式下力点探测推荐模型
    if is_auto:
        engine_check = await chat_integration.pre_chat_check(
            content=body.content,
            workspace_id=body.workspace_id or "global",
            agent_id=body.at_agent_id or "default",
        )
        if engine_check.recommended_model:
            requested_model = engine_check.recommended_model
            from engine.smart_allocator import get_registry_name
            requested_model = get_registry_name(requested_model)
    else:
        engine_check = None

    # 能力开关检查 + TokenBudget 拦截
    if engine_check:
        if engine_check.capability_blocked:
            return make_error("CAPABILITY_BLOCKED", engine_check.capability_blocked, request_id=rid)
        if not engine_check.can_proceed:
            return make_error("BUDGET_EXCEEDED", engine_check.budget_alert or "Token预算超限", request_id=rid)

    # InstructionCache 命中快路径：跳过 LLM 调用直接返回缓存
    if cached_response:
        ai_msg = await create_message(
            workspace_id=body.workspace_id,
            content=cached_response,
            role="assistant",
            model="cache",
            at_agent_id=body.at_agent_id,
        )
        user_msg["stream_url"] = None
        user_msg["ai_message_id"] = ai_msg["id"]
        user_msg["cached"] = True
        return make_response(user_msg, request_id=rid)

    # 创建 AI 消息占位
    ai_msg = await create_message(
        workspace_id=body.workspace_id,
        content="",
        role="assistant",
        model=requested_model,
        at_agent_id=body.at_agent_id,
    )

    user_msg["stream_url"] = f"/api/v1/chat/stream/{ai_msg['id']}"
    user_msg["ai_message_id"] = ai_msg["id"]

    return make_response(user_msg, request_id=rid)


@router.get("/chat/stream/{message_id}")
async def api_stream_message(request: Request, message_id: str):
    """SSE 流式获取 AI 回复
    
    包含:
    - 连接超时机制（30分钟）
    - 心跳检测保持连接活跃
    - 完善的资源清理
    - 详细的日志记录
    """
    rid = getattr(request.state, "request_id", "")
    start_time = datetime.now()

    msg = await get_message_by_id(message_id)
    if not msg:
        logger.warning(f"SSE stream failed: message {message_id} not found")
        return make_error("MESSAGE_NOT_FOUND", "消息不存在", request_id=rid)

    if msg["role"] != "assistant":
        logger.warning(f"SSE stream failed: message {message_id} is not assistant role")
        return make_error("STREAM_NOT_FOUND", "只能流式获取 AI 回复", request_id=rid)

    logger.info(f"SSE connection established for message_id={message_id}, client={request.client.host if request.client else 'unknown'}")

    stop_event = asyncio.Event()
    _active_streams[message_id] = stop_event

    async def event_generator():
        """事件生成器，包含超时和心跳机制。"""
        try:
            requested_model = msg.get("model", "deepseek-v4-pro")

            from model_adapter.fallback import fallback_manager
            adapter, actual_model = await fallback_manager.get_allocator_preferred_model(requested_model)

            if not adapter:
                logger.error(f"SSE stream failed: no available model for {requested_model}")
                yield _build_sse_event("error", {
                    "code": "MODEL_ALL_DOWN",
                    "message": "所有模型不可用，请检查 API Key 配置",
                })
                await update_message_status(message_id, "error",
                                            error_info=json.dumps({"code": "MODEL_ALL_DOWN"}))
                return

            await update_message_status(message_id, "streaming", model=actual_model)

            messages = await _build_context(msg.get("workspace_id"), msg.get("at_agent_id"))

            # 记录开始时间用于超时检查
            connection_start = datetime.now()
            last_activity = datetime.now()
            
            # 流式生成AI响应，同时监控超时和发送心跳
            stream_gen = _stream_response(
                adapter, actual_model, messages, stop_event, message_id, msg,
            )
            
            try:
                async for event in stream_gen:
                    # 更新最后活动时间
                    last_activity = datetime.now()
                    
                    # 检查超时
                    elapsed = last_activity - connection_start
                    if elapsed > SSE_CONNECTION_TIMEOUT:
                        logger.warning(f"SSE connection timeout for message_id={message_id}, elapsed={elapsed.total_seconds():.1f}s")
                        yield _build_sse_event("error", {
                            "code": "CONNECTION_TIMEOUT",
                            "message": f"连接超时（{SSE_CONNECTION_TIMEOUT.total_seconds()/60}分钟）",
                        })
                        await update_message_status(message_id, "error",
                                                    error_info=json.dumps({"code": "CONNECTION_TIMEOUT"}))
                        break
                    
                    yield event
                    
                    # 如果距离上次活动超过心跳间隔，发送心跳
                    time_since_last = datetime.now() - last_activity
                    if time_since_last.total_seconds() >= SSE_HEARTBEAT_INTERVAL:
                        yield _build_sse_comment("heartbeat")
                        last_activity = datetime.now()
                        
            finally:
                # 确保生成器关闭
                await stream_gen.aclose()
                logger.info(f"SSE stream generator closed for message_id={message_id}")
                
        except asyncio.CancelledError:
            logger.info(f"SSE connection cancelled by client for message_id={message_id}")
            raise
        except Exception as e:
            logger.error(f"SSE stream generator error for message_id={message_id}: {e}", exc_info=True)
            yield _build_sse_event("error", {
                "code": "STREAM_ERROR",
                "message": f"流式响应错误: {str(e)}",
            })
        finally:
            # 最终清理
            elapsed = datetime.now() - start_time
            logger.info(f"SSE connection closed for message_id={message_id}, duration={elapsed.total_seconds():.1f}s")
            _active_streams.pop(message_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Connection-Timeout": str(int(SSE_CONNECTION_TIMEOUT.total_seconds())),
        },
        background=BackgroundTask(lambda: _active_streams.pop(message_id, None)),  # 双重保障
    )


@router.post("/chat/stream/{message_id}/stop")
async def api_stop_stream(request: Request, message_id: str):
    """停止当前正在生成的回复"""
    rid = getattr(request.state, "request_id", "")
    stop_event = _active_streams.get(message_id)
    if stop_event:
        stop_event.set()
        return make_response({"message_id": message_id, "status": "stopping"}, request_id=rid)
    return make_error("STREAM_NOT_FOUND", "流式连接不存在或已结束", request_id=rid)


@router.get("/chat/messages")
async def api_list_messages(
    request: Request,
    workspace_id: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    before_id: str = Query(None),
):
    rid = getattr(request.state, "request_id", "")
    messages, total = await list_messages(workspace_id, page, page_size, before_id)
    return make_paginated_response(messages, page, page_size, total, request_id=rid)


@router.delete("/chat/messages")
async def api_clear_messages(request: Request, workspace_id: str = Query(...)):
    rid = getattr(request.state, "request_id", "")
    count = await clear_messages(workspace_id)
    return make_response({"deleted_count": count}, request_id=rid)


@router.get("/chat/search")
async def api_search_messages(
    request: Request,
    q: str = Query(..., min_length=2),
    workspace_id: str = Query(None),
):
    rid = getattr(request.state, "request_id", "")
    results = await search_messages(q, workspace_id)
    return make_response(results, request_id=rid)


@router.get("/chat/context")
async def api_get_context(request: Request, workspace_id: str = Query(None)):
    """获取上下文统计 — 接入 L1/L2 记忆引擎实时数据"""
    rid = getattr(request.state, "request_id", "")
    from services.memory.memory_service import get_memory_engine
    import logging
    logger = logging.getLogger("niuma.chat.context")

    if workspace_id:
        try:
            mem_engine = get_memory_engine()
            stats = await mem_engine.get_context_stats(workspace_id)
            return make_response({
                "total_tokens": stats["l1"]["total_tokens"],
                "token_limit": stats["l1"]["token_limit"],
                "usage_percent": stats["l1"]["usage_percent"],
                "message_count": stats["l1"]["message_count"],
                "l1_memory_size": stats["l1"]["message_count"],
                "l2_injections": stats["l2"]["entries_count"],
                "status": stats["l1"].get("status", "green"),
                "compression": {
                    "budget_applied": stats["compression"]["budget_applied"],
                    "snip_applied": stats["compression"]["snip_applied"],
                    "summarize_applied": stats["compression"]["summarize_applied"],
                    "freed_tokens": stats["compression"]["freed_tokens"],
                },
            }, request_id=rid)
        except Exception as e:
            logger.warning(f"L1 memory unavailable for {workspace_id}: {e}", exc_info=True)

    from config.settings import settings
    return make_response(
        {
            "total_tokens": 0,
            "token_limit": settings.DEFAULT_CONTEXT_THRESHOLD,
            "usage_percent": 0.0,
            "message_count": 0,
            "l1_memory_size": 0,
            "l2_injections": 0,
            "status": "green",
            "compression": {
                "budget_applied": False,
                "snip_applied": False,
                "summarize_applied": False,
                "freed_tokens": 0,
            },
        },
        request_id=rid,
    )


# ============================================================
# Swarm LLM 回调注入（P1-1 修复）
# ============================================================

async def _call_llm(prompt: str, model_hint: str = "deepseek-v4-flash") -> str:
    """LLM 回调：调用模型适配器获取回复

    用于 Swarm Gate 智能升级和 LLM 增强分解路径。
    类型签名匹配 LlmCallback = Callable[[str, str], Awaitable[str]]。
    """
    try:
        adapter = await model_registry.get_available(model_hint)
        if not adapter:
            return ""
        messages = [{"role": "user", "content": prompt}]
        result = await adapter.chat(messages)
        return result.get("content", "")
    except Exception as e:
        import logging
        logging.getLogger("niuma.chat.swarm").warning(
            f"LLM callback failed (model={model_hint}): {e}", exc_info=True,
        )
        return ""


# 模块级别注入 —— 应用启动时自动接线
# `set_llm_callback` 是同步方法，只存储函数引用，不执行回调
chat_integration.set_llm_callback(_call_llm)
