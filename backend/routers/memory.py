"""记忆引擎 REST API 路由

按照 security_memory_api.md §二 设计：
- GET  /memory/context   — 上下文统计
- GET  /memory/l1/{ws_id} — L1 会话快照
- GET  /memory/l2/{ws_id} — L2 列表查询
- POST /memory/l2/{ws_id} — 添加 L2 条目
- DELETE /memory/l2/{ws_id}/{entry_id} — 删除 L2 条目
- POST /memory/compress/{ws_id} — 手动触发压缩
- GET  /memory/l3/{ws_id} — L3 知识库概览
- POST /memory/l3/{ws_id} — 添加 L3 条目
"""

from typing import Optional

from fastapi import APIRouter, Body, Request, Query
from pydantic import BaseModel, Field


class L2MemoryEntry(BaseModel):
    entry_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r'^(request|learned|completed|decision|error|custom|compress_event)$',
        description="条目类型"
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="内容"
    )
    tags: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="标签列表"
    )
    expires_at: str | None = Field(None, description="过期时间 ISO 8601")


class L3KnowledgeAdd(BaseModel):
    """L3 知识添加请求体"""
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="标题"
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="内容"
    )
    schema_type: str = Field(
        default="S10_通用",
        pattern=r'^S\d{2}_.+$',
        description="Schema 类型"
    )
    source: str = Field(default="", max_length=200, description="来源")
    tags: list[str] = Field(default_factory=list, max_length=20, description="标签")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")


class L3SearchRequest(BaseModel):
    """L3 搜索请求体"""
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="搜索查询"
    )
    top_k: int = Field(default=10, ge=1, le=100, description="返回数量")
    schema_type: Optional[str] = Field(None, pattern=r'^S\d{2}_.+$', description="Schema 过滤")
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="最小置信度")


class CompressRequest(BaseModel):
    """压缩请求体"""
    strategy: str = Field(
        default="auto",
        pattern=r'^(auto|budget|snip|summarize)$',
        description="压缩策略"
    )
    force: bool = Field(default=False, description="强制执行")

from schemas.common import make_response, make_paginated_response, make_error
from services.memory.memory_service import get_memory_engine

router = APIRouter()


# ============================================================
# 前端简化对接端点（无需 workspace_id）
# ============================================================

@router.get("/memory")
async def api_memory_overview(request: Request):
    """获取记忆系统概览（前端 MemoryView 对接）

    GET /api/v1/memory
    返回 L1/L2/L3 的汇总统计
    """
    rid = getattr(request.state, "request_id", "")
    engine = get_memory_engine() if get_memory_engine else None

    try:
        # 返回基本结构，即使引擎未初始化也不报错
        if engine is None:
            return make_response({
                "l1": {"sessions": 0, "total_tokens": 0},
                "l2": {"entries": 0},
                "l3": {"entries": 0},
                "compress": {"events": 0},
            }, request_id=rid)

        # 尝试获取统计
        l1_sessions = 0
        l1_tokens = 0
        l2_entries = 0
        try:
            l1_sessions = len(getattr(engine.l1, '_sessions', {}))
            for sid in getattr(engine.l1, '_sessions', {}):
                ts = engine.l1.get_token_status(sid)
                if ts:
                    l1_tokens += ts.total_tokens
        except Exception:
            pass

        try:
            l2_entries = len(getattr(engine.l2, '_entries', []))
        except Exception:
            pass

        return make_response({
            "l1": {"sessions": l1_sessions, "total_tokens": l1_tokens},
            "l2": {"entries": l2_entries},
            "l3": {"entries": "see /memory/l3/{ws_id}"},
            "compress": {"events": "see /memory/compress-history/{ws_id}"},
        }, request_id=rid)
    except Exception as e:
        return make_response({
            "l1": {"sessions": 0, "total_tokens": 0},
            "l2": {"entries": 0},
            "l3": {"entries": 0},
            "message": f"引擎未就绪: {e}",
        }, request_id=rid)


@router.get("/memory/search")
async def api_memory_search(
    request: Request,
    q: str = Query(..., min_length=1, description="搜索关键词"),
):
    """记忆搜索（前端对接，无需 workspace_id）

    GET /api/v1/memory/search?q=关键词
    """
    rid = getattr(request.state, "request_id", "")

    results = []

    # 搜索 L2 记忆
    try:
        engine = get_memory_engine()
        if engine:
            # 遍历所有可能的 workspace 来搜索 L2
            for ws_id in list(getattr(engine.l2, '_workspaces', {}).keys()):
                entries, _ = await engine.l2_list(
                    workspace_id=ws_id,
                    keyword=q,
                    page=1,
                    page_size=20,
                )
                for entry in entries:
                    results.append({
                        "id": entry.get("id", ""),
                        "type": "l2",
                        "entry_type": entry.get("entry_type", ""),
                        "content": entry.get("content", ""),
                        "tags": entry.get("tags", []),
                        "workspace_id": ws_id,
                        "created_at": entry.get("created_at", ""),
                    })
    except Exception:
        pass

    # 搜索 L3 知识库
    try:
        from engine.taixu_core import get_taixu
        taixu = get_taixu()
        if taixu:
            await taixu.init()
            l3_results = await taixu.search(query=q, top_k=10)
            for r in l3_results:
                results.append({
                    "id": r.entry.id,
                    "type": "l3",
                    "title": r.entry.title,
                    "content": r.entry.summary or "",
                    "schema_type": r.entry.schema_type.value if hasattr(r.entry.schema_type, 'value') else str(r.entry.schema_type),
                    "score": r.score,
                    "created_at": "",
                })
    except Exception:
        pass

    return make_response({
        "query": q,
        "total": len(results),
        "results": results,
    }, request_id=rid)


# ============================================================
# 上下文统计
# ============================================================

@router.get("/memory/context")
async def api_context_stats(
    request: Request,
    workspace_id: str = Query(..., description="工作间 ID"),
):
    """获取当前工作间的上下文状态

    GET /api/v1/memory/context?workspace_id=xxx

    返回 L1/L2/L3 + 压缩状态的综合统计
    """
    rid = getattr(request.state, "request_id", "")
    engine = get_memory_engine()

    try:
        stats = await engine.get_context_stats(workspace_id)
        return make_response(stats, request_id=rid)
    except Exception as e:
        return make_error("MEMORY_ERROR", f"获取上下文统计失败: {e}", request_id=rid)


# ============================================================
# L1 会话工作记忆
# ============================================================

@router.get("/memory/l1/{workspace_id}")
async def api_l1_snapshot(
    request: Request,
    workspace_id: str,
):
    """获取 L1 会话记忆快照

    GET /api/v1/memory/l1/{workspace_id}
    """
    rid = getattr(request.state, "request_id", "")
    engine = get_memory_engine()

    try:
        session_id = engine.get_or_create_session(workspace_id)
        token_status = engine.l1.get_token_status(session_id)
        session_info = engine.l1.get_session_info(session_id)

        if not session_info:
            return make_error("MEMORY_NOT_FOUND", "会话不存在", request_id=rid)

        return make_response(session_info, request_id=rid)
    except Exception as e:
        return make_error("MEMORY_ERROR", str(e), request_id=rid)


@router.delete("/memory/l1/{workspace_id}")
async def api_l1_clear(
    request: Request,
    workspace_id: str,
):
    """清除 L1 会话记忆

    DELETE /api/v1/memory/l1/{workspace_id}
    """
    rid = getattr(request.state, "request_id", "")
    engine = get_memory_engine()

    try:
        archived = await engine.archive_session(workspace_id)
        # 重新创建新会话
        engine.get_or_create_session(workspace_id)
        return make_response({
            "workspace_id": workspace_id,
            "archived_entries": archived,
            "action": "会话已重置",
        }, request_id=rid)
    except Exception as e:
        return make_error("MEMORY_ERROR", str(e), request_id=rid)


# ============================================================
# L2 短期档案 CRUD
# ============================================================

@router.get("/memory/l2/{workspace_id}")
async def api_l2_list(
    request: Request,
    workspace_id: str,
    entry_type: Optional[str] = Query(None, description="条目类型: request|learned|completed|decision|error"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    observation_type: Optional[str] = Query(None, description="Observation 类型 (18种)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取 L2 短期档案列表

    GET /api/v1/memory/l2/{workspace_id}?entry_type=learned&keyword=xxx

    支持按类型过滤、关键词搜索、时间范围、分页
    """
    rid = getattr(request.state, "request_id", "")
    engine = get_memory_engine()

    try:
        entries, total = await engine.l2_list(
            workspace_id=workspace_id,
            entry_type=entry_type,
            keyword=keyword,
            observation_type=observation_type,
            page=page,
            page_size=page_size,
        )
        return make_paginated_response(entries, page, page_size, total, request_id=rid)
    except Exception as e:
        return make_error("MEMORY_ERROR", str(e), request_id=rid)


@router.post("/memory/l2/{workspace_id}", status_code=201)
async def api_l2_add(
    request: Request,
    workspace_id: str,
    body: L2MemoryEntry,
):
    """手动添加 L2 记忆条目

    POST /api/v1/memory/l2/{workspace_id}

    请求体:
    {
        "entry_type": "decision",         // 必填
        "content": "角色设定：主角使用第一人称叙事",
        "tags": ["角色", "叙事"],          // 可选
        "summary": "叙事视角决策",          // 可选
        "observation_type": "decision"     // 可选
    }
    """
    rid = getattr(request.state, "request_id", "")
    engine = get_memory_engine()

    valid_types = ("request", "learned", "completed", "decision", "error", "custom",
                   "compress_event")
    if body.entry_type not in valid_types:
        return make_error(
            "INVALID_PARAMS",
            f"entry_type 必须为: {', '.join(valid_types)}",
            request_id=rid,
        )

    try:
        entry = await engine.l2_add(
            workspace_id=workspace_id,
            entry_type=body.entry_type,
            content=body.content,
            summary=None,
            tags=body.tags,
            observation_type=None,
        )
        return make_response(entry, request_id=rid)
    except Exception as e:
        return make_error("MEMORY_ERROR", str(e), request_id=rid)


@router.delete("/memory/l2/{workspace_id}/{entry_id}")
async def api_l2_delete(
    request: Request,
    workspace_id: str,
    entry_id: str,
):
    """删除指定 L2 记忆条目

    DELETE /api/v1/memory/l2/{workspace_id}/{entry_id}
    """
    rid = getattr(request.state, "request_id", "")
    engine = get_memory_engine()

    try:
        deleted = await engine.l2_delete(workspace_id, entry_id)
        if deleted:
            return make_response({"entry_id": entry_id, "deleted": True}, request_id=rid)
        else:
            return make_error("MEMORY_NOT_FOUND", "记忆条目不存在", request_id=rid)
    except Exception as e:
        return make_error("MEMORY_ERROR", str(e), request_id=rid)


# ============================================================
# 上下文压缩
# ============================================================

@router.post("/memory/compress/{workspace_id}")
async def api_compress_context(
    request: Request,
    workspace_id: str,
    body: CompressRequest = Body(default=None),
):
    """手动触发上下文压缩

    POST /api/v1/memory/compress/{workspace_id}

    请求体 (可选):
    {
        "strategy": "auto",    // auto|budget|snip|summarize
        "force": false         // 是否强制执行 (跳过频率限制)
    }
    """
    rid = getattr(request.state, "request_id", "")
    engine = get_memory_engine()

    strategy = body.strategy if body else "auto"
    force = body.force if body else False

    try:
        report = await engine.compress_context(
            workspace_id=workspace_id,
            strategy=strategy,
            force=force,
        )

        # 构建详情
        details: dict = {}
        for action in report.actions:
            if action.type == "budget":
                details["budget"] = {
                    "truncated_count": action.details.compressed_count if action.details else 0,
                    "freed": action.saved_tokens,
                }
            elif action.type == "snip":
                details["snip"] = {
                    "removed_count": action.details.snipped_messages if action.details else 0,
                    "freed": action.saved_tokens,
                }
            elif action.type == "summarize":
                details["summarize"] = {
                    "summarized_count": action.details.batches if action.details else 0,
                    "freed": action.saved_tokens,
                    "tokens_used": 0,
                }

        return make_response({
            "workspace_id": workspace_id,
            "before_tokens": report.pre_tokens,
            "after_tokens": report.post_tokens,
            "freed_tokens": report.total_saved,
            "saving_ratio": round(report.saving_ratio * 100, 1),
            "strategies_applied": [a.type for a in report.actions],
            "details": details,
            "warnings": report.warnings,
        }, request_id=rid)
    except Exception as e:
        return make_error("COMPRESS_ERROR", str(e), request_id=rid)


# ============================================================
# L3 长期知识库（太虚境）
# ============================================================

@router.get("/memory/l3/{workspace_id}")
async def api_l3_list(
    request: Request,
    workspace_id: str,
):
    """获取 L3 知识库概览

    GET /api/v1/memory/l3/{workspace_id}
    """
    rid = getattr(request.state, "request_id", "")

    try:
        from engine.taixu_core import get_taixu
        taixu = get_taixu()
        stats = await taixu.get_stats(workspace_id=workspace_id)
        return make_response({
            "workspace_id": workspace_id,
            "total_entries": stats["total_entries"],
            "by_schema": stats["by_schema"],
            "total_relations": stats["total_relations"],
            "pending_upgrades": stats["pending_upgrades"],
            "vector_engine": stats["vector_engine"],
        }, request_id=rid)
    except Exception as e:
        return make_error("L3_ERROR", str(e), request_id=rid)


@router.post("/memory/l3/{workspace_id}/search")
async def api_l3_search(
    request: Request,
    workspace_id: str,
    body: L3SearchRequest,
):
    """太虚境语义搜索

    POST /api/v1/memory/l3/{workspace_id}/search

    请求体:
    {
        "query": "全棉支数分析",        // 必填
        "top_k": 10,                    // 可选，默认10
        "schema_type": "S01_材质",       // 可选，领域过滤
        "min_confidence": 0.5           // 可选，最小置信度
    }
    """
    rid = getattr(request.state, "request_id", "")

    try:
        from engine.taixu_core import get_taixu
        taixu = get_taixu()
        await taixu.init()

        results = await taixu.search(
            query=body.query,
            top_k=body.top_k,
            schema_type=body.schema_type,
            workspace_id=workspace_id,
            min_confidence=body.min_confidence,
        )

        return make_response({
            "query": body.query,
            "total": len(results),
            "results": [
                {
                    "id": r.entry.id,
                    "title": r.entry.title,
                    "summary": r.entry.summary,
                    "schema_type": r.entry.schema_type.value,
                    "score": r.score,
                    "match_type": r.match_type,
                    "highlights": r.highlights,
                    "retrieval_count": r.entry.retrieval_count,
                    "source": r.entry.source,
                }
                for r in results
            ],
        }, request_id=rid)
    except Exception as e:
        return make_error("L3_SEARCH_ERROR", str(e), request_id=rid)


@router.post("/memory/l3/{workspace_id}/add")
async def api_l3_add(
    request: Request,
    workspace_id: str,
    body: L3KnowledgeAdd,
):
    """添加知识到太虚境

    POST /api/v1/memory/l3/{workspace_id}/add

    请求体:
    {
        "title": "全棉60S面料分析",
        "content": "...",
        "schema_type": "S01_材质",
        "source": "official_pr",
        "tags": ["全棉", "60S"],
        "confidence": 0.9
    }
    """
    rid = getattr(request.state, "request_id", "")

    try:
        from engine.taixu_core import get_taixu
        taixu = get_taixu()
        await taixu.init()

        entry = await taixu.add_knowledge(
            title=body.title,
            content=body.content,
            schema_type=body.schema_type,
            source=body.source,
            tags=body.tags,
            confidence=body.confidence,
            workspace_id=workspace_id,
        )

        return make_response(entry.to_dict(), request_id=rid)
    except Exception as e:
        return make_error("L3_ADD_ERROR", str(e), request_id=rid)


@router.post("/memory/l3/{workspace_id}/upgrade")
async def api_l3_upgrade(
    request: Request,
    workspace_id: str,
):
    """触发 L2→L3 自动升级

    POST /api/v1/memory/l3/{workspace_id}/upgrade
    """
    rid = getattr(request.state, "request_id", "")

    try:
        from engine.taixu_core import get_taixu
        taixu = get_taixu()
        await taixu.init()

        candidates = await taixu.check_upgrade_candidates(workspace_id=workspace_id)
        if not candidates:
            return make_response({
                "message": "无符合条件的升级候选",
                "candidates": 0,
                "upgraded": [],
            }, request_id=rid)

        upgraded = await taixu.execute_upgrade(candidates)
        return make_response({
            "candidates_found": len(candidates),
            "upgraded_count": len(upgraded),
            "upgraded": upgraded,
        }, request_id=rid)
    except Exception as e:
        return make_error("L3_UPGRADE_ERROR", str(e), request_id=rid)


# ============================================================
# 压缩历史
# ============================================================

@router.get("/memory/compress-history/{workspace_id}")
async def api_compress_history(
    request: Request,
    workspace_id: str,
    limit: int = Query(20, ge=1, le=100),
):
    """获取压缩历史记录

    GET /api/v1/memory/compress-history/{workspace_id}
    """
    rid = getattr(request.state, "request_id", "")
    engine = get_memory_engine()

    try:
        entries, total = await engine.l2_list(
            workspace_id=workspace_id,
            entry_type="compress_event",
            page=1,
            page_size=limit,
        )

        events = []
        total_saved = 0
        for entry in entries:
            try:
                detail = json.loads(entry["content"]) if isinstance(entry["content"], str) else entry["content"]
                events.append({
                    "level": detail.get("level", 0),
                    "pre_tokens": detail.get("pre_tokens", 0),
                    "post_tokens": detail.get("post_tokens", 0),
                    "saved_tokens": detail.get("saved_tokens", 0),
                    "saving_ratio": detail.get("saving_ratio", 0),
                    "actions": detail.get("actions", []),
                    "timestamp": entry.get("created_at"),
                })
                total_saved += detail.get("saved_tokens", 0)
            except (json.JSONDecodeError, TypeError):
                pass

        return make_response({
            "events": events,
            "summary": {
                "total_compressions": len(events),
                "total_tokens_saved": total_saved,
                "cost_saved": round(total_saved * 1.0 / 1_000_000, 6),
            },
        }, request_id=rid)
    except Exception as e:
        return make_error("MEMORY_ERROR", str(e), request_id=rid)
