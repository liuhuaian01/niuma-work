"""
太极引擎 · 对话流接入层（Chat Integration Hooks）

将太极引擎注入实际对话流程：
  发送前 → Smart Allocator + TokenBudget + CapabilityFlags + LocalAnswerCheck + AttentionEngine
  完成后 → ExecutionLogger + SelfHealing + TokenSavings + HonchoModeler + HealingTracker

v2.1 (2026-06-24): 通过 hook_registry 解耦，从 21 个直接导入减至 1 个统一接入层。
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import asyncio
import json
import logging

# 统一依赖接入层——替代 21 个直接导入
from engine.hook_registry import hook_registry as _reg

# 数据类型（零耦合，纯 dataclass/枚举导入）
from engine.smart_allocator import TaskType, ForceProbeInput, get_registry_name
from engine.token_budget import AlertLevel, PER_REQUEST_MAX_TOKENS, check_per_request
from engine.execution_log import ExecutionRecord
from engine.self_healing import InterceptEvent, HealingAction
from engine.dynamic_balancer import RuntimeMode
from typing import Callable, Awaitable

LlmCallback = Callable[[str, str], Awaitable[str]]

logger = logging.getLogger(__name__)


# ============================================================
# EngineDegradationProvider — 引擎降级提供者
# ============================================================

@dataclass
class FallbackProbeResult:
    """SmartAllocator 失败时的降级探测结果。"""
    recommended_model: str = 'deepseek-chat'
    estimated_tokens: int = 10000
    reason: str = 'watchdog fallback'


@dataclass
class FallbackBudgetResult:
    """TokenBudget 检查失败时的降级预算结果。"""
    can_continue: bool = True
    message: str = ''
    alert_level: AlertLevel = AlertLevel.NONE


class EngineDegradationProvider:
    """引擎降级提供者——通过 DynamicDegradationEngine 动态决策降级路径。v2.0: 不硬编码任何模型名称。"""

    def __init__(self, fallback_cost, allocator) -> None:
        self._fallback_cost = fallback_cost
        self._allocator = allocator

    def get_probe_fallback(
        self, task_type: TaskType, original_model: str = "deepseek-v4"
    ) -> FallbackProbeResult:
        """SmartAllocator 失败时的动态降级探测。"""
        dd = _reg.dynamic_degradation
        next_model, reason, path = dd.degrade(
            task_type=task_type.value,
            budget_remaining=self._allocator.get_budget_remaining(task_type)
                if hasattr(self._allocator, 'get_budget_remaining') else 10000,
            priority=0.5,
            preferred_model=original_model,
        )

        if next_model:
            return FallbackProbeResult(
                recommended_model=dd.get_registry_name(next_model),
                estimated_tokens=10000,
                reason=f'动态降级: {reason}',
            )

        best_fallback = ""
        best_loss = 1.0
        for model in dd.list_available_models():
            if model.model_id == original_model:
                continue
            cost = self._fallback_cost.analyze(original_model, model.model_id, task_type.value)
            if cost.acceptable and cost.quality_loss < best_loss:
                best_loss = cost.quality_loss
                best_fallback = model.model_id
            elif not best_fallback and cost.quality_loss < best_loss:
                best_loss = cost.quality_loss
                best_fallback = model.model_id

        if best_fallback:
            return FallbackProbeResult(
                recommended_model=dd.get_registry_name(best_fallback),
                estimated_tokens=10000,
                reason=f'动态降级兜底: {best_fallback} (质量损失 {best_loss:.1%})',
            )

        return FallbackProbeResult(
            recommended_model=get_registry_name("deepseek-v4"),
            estimated_tokens=10000,
            reason='watchdog fallback: 所有模型不可用，使用默认 deepseek-v4',
        )

    def get_budget_fallback(self) -> FallbackBudgetResult:
        """TokenBudget 检查失败时的降级预算结果。"""
        return FallbackBudgetResult(
            can_continue=True,
            message='预算检查跳过（降级模式）',
            alert_level=AlertLevel.NONE,
        )


# ============================================================
# PreChatCheck
# ============================================================

@dataclass
class PreChatCheck:
    """发送消息前的检查结果。"""
    can_proceed: bool
    recommended_model: str
    estimated_tokens: int
    budget_alert: str = ""
    capability_blocked: str = ""
    force_probe_reason: str = ""
    local_answer_suggestion: str = ""
    gate_upgrade_suggested: bool = False
    task_complexity_level: str = ""
    mesh_routed: bool = False
    mesh_peer: str = ""
    routing_layer: str = ""


# ============================================================
# ChatIntegration
# ============================================================

class ChatIntegration:
    """对话流的太极引擎接入层。

    v2.1: 通过 hook_registry 统一接入，不再直接依赖 21 个引擎模块。
    """

    def __init__(self, db_path: str | None = None) -> None:
        # 从 Registry 批量创建引擎实例
        engines = _reg.create_engines()
        self.allocator = engines.get("smart_allocator")
        self.logger_obj = engines.get("execution_logger")
        self.reflection = engines.get("reflection_engine")
        self.local_checker = engines.get("local_answer_checker")
        self.honcho = engines.get("honcho_modeler")
        self.balancer = engines.get("dynamic_balancer")
        self.orchestrator = engines.get("swarm_orchestrator")
        self.fallback_cost = engines.get("fallback_cost")
        self.fallback = EngineDegradationProvider(self.fallback_cost, self.allocator)
        self.closure_engine = engines.get("closure_engine")
        self.auto_gate_upgrade: bool = True
        self._llm_callback: LlmCallback | None = None
        self._otel_enabled: bool = _reg.tracer and _reg.tracer.is_available

    async def pre_chat_check(
        self, content: str, workspace_id: str, agent_id: str, user_priority: float = 0.5
    ) -> PreChatCheck:
        """消息发送前——每个引擎模块都经过 watchdog 熔断保护。"""
        otel_tracer = _reg.tracer
        span_attrs = {
            "agent.id": agent_id,
            "workspace.id": workspace_id,
            "content.length": len(content),
            "trace.id": otel_tracer.generate_trace_id() if otel_tracer else "n/a",
        }
        with (otel_tracer.span("chat.pre_check", span_attrs) if otel_tracer else _null_context()) as otel_span:

            task_type = self._infer_task_type(content)
            if otel_span:
                otel_span.set_attribute("task.type", task_type.value)

            # Dynamic Balancer（非关键——熔断后跳过）
            balance_decision = None
            routing_layer = "cloud"
            mesh_peer = ""

            watchdog = _reg.watchdog
            should, _ = watchdog.should_call("dynamic_balancer")
            if should:
                try:
                    balance_decision = await self.balancer.decide(
                        privacy_sensitive=self._is_sensitive(content),
                        task_complexity=self._estimate_complexity(content),
                        user_prefers_local=False,
                        model_name="",
                    )
                    watchdog.record_success("dynamic_balancer")
                except Exception as e:
                    watchdog.record_failure("dynamic_balancer", str(e))
                    logger.warning("DynamicBalancer 调用失败: %s", e, exc_info=True)

            # 太极网格三层路由
            mesh_routed = False
            if balance_decision and balance_decision.mode.value == "mesh":
                try:
                    mesh = _reg.taiji_mesh
                    if mesh and mesh.is_initialized and mesh.contributing:
                        healthy = mesh.get_healthy_peers()
                        if healthy:
                            routing_layer = "mesh"
                            mesh_routed = True
                            mesh_peer = healthy[0].hostname
                            logger.info(
                                "太极网格路由: 节点=%s, 可用邻居=%d",
                                mesh_peer, len(healthy),
                            )
                        else:
                            routing_layer = "cloud"
                            logger.info("太极网格无健康邻居节点，回退云端")
                    else:
                        routing_layer = "cloud"
                        logger.debug("太极网格未初始化或未开启贡献，跳过")
                except Exception as e:
                    logger.warning("太极网格路由失败，回退云端: %s", e)
                    routing_layer = "cloud"
            elif balance_decision:
                routing_layer = balance_decision.mode.value

            # Smart Allocator（关键——熔断后用 EngineDegradationProvider 降级）
            should, reason = watchdog.should_call("smart_allocator")
            if should:
                try:
                    remaining = self.allocator.get_budget_remaining(task_type, agent_id)
                    runtime_mode = balance_decision.mode.value if balance_decision else None
                    probe = self.allocator.probe(
                        ForceProbeInput(task_type, remaining, user_priority, runtime_mode=runtime_mode)
                    )
                    watchdog.record_success("smart_allocator")
                except Exception as e:
                    watchdog.record_failure("smart_allocator", str(e))
                    logger.warning("SmartAllocator 调用失败，使用 EngineDegradationProvider 降级: %s", e, exc_info=True)
                    probe = self.fallback.get_probe_fallback(task_type, "deepseek-v4")
            else:
                probe = self.fallback.get_probe_fallback(task_type, "deepseek-v4")
                probe.reason = f'熔断: {reason}'

            if otel_span:
                otel_span.set_attribute("model.recommended", probe.recommended_model)
                otel_span.set_attribute("tokens.estimated", probe.estimated_tokens)

            # Token Budget
            token_budget = _reg.token_budget
            should, _ = watchdog.should_call("token_budget")
            if should:
                try:
                    budget = token_budget.check(agent_id)
                    watchdog.record_success("token_budget")
                except Exception as e:
                    watchdog.record_failure("token_budget", str(e))
                    logger.warning("TokenBudget 检查失败，使用 EngineDegradationProvider 降级: %s", e, exc_info=True)
                    budget = self.fallback.get_budget_fallback()
            else:
                budget = self.fallback.get_budget_fallback()

            if not budget.can_continue:
                if otel_span:
                    otel_span.set_attribute("outcome", "budget_blocked")
                return PreChatCheck(
                    can_proceed=False,
                    recommended_model=probe.recommended_model,
                    estimated_tokens=probe.estimated_tokens,
                    budget_alert=budget.message,
                    force_probe_reason="",
                    routing_layer=routing_layer,
                )

            # 请求级硬上限检查 —— vLLM Micro-Agent 蒸馏
            # 日预算可能还有余量，但单次请求已超过安全阈值
            estimated_tokens = probe.estimated_tokens  # 默认使用探针估值
            can_request, req_msg = check_per_request(
                estimated_tokens=estimated_tokens,
                max_tokens=PER_REQUEST_MAX_TOKENS,
            )
            if not can_request:
                if otel_span:
                    otel_span.set_attribute("outcome", "request_budget_blocked")
                logger.warning("请求级预算拦截: %s", req_msg)
                return PreChatCheck(
                    can_proceed=False,
                    recommended_model=probe.recommended_model,
                    estimated_tokens=estimated_tokens,
                    budget_alert=req_msg,
                    force_probe_reason="",
                    routing_layer=routing_layer,
                )

            # LocalAnswerChecker
            local_answer_suggestion = ""
            try:
                local_result = self.local_checker.check(content)
                if local_result.found:
                    local_answer_suggestion = local_result.suggestion
            except Exception:
                logger.warning("LocalAnswerChecker 检查失败", exc_info=True)

            # CapabilityFlags
            capability_blocked = ""
            try:
                taiji = _reg.taiji
                if self._needs_web_search(content) and not taiji.flags.is_allowed("search", agent_id):
                    capability_blocked = "外网搜索默认关闭。如需使用请手动开启。"
                if self._needs_web_search(content) and local_answer_suggestion:
                    capability_blocked = (
                        capability_blocked + " " if capability_blocked else ""
                    ) + f"本地已有相关答案: {local_answer_suggestion}"
            except Exception:
                logger.warning("CapabilityFlags 检查失败", exc_info=True)

            # AttentionEngine
            attention_events = []
            try:
                attention_events = _reg.attention_engine.evaluate({
                    "user_id": agent_id,
                    "task_type": task_type.value,
                })
            except Exception:
                logger.warning("AttentionEngine 评估失败", exc_info=True)

            has_important_attention = any(
                e.priority >= 7 for e in attention_events
            )

            if not has_important_attention and estimated_tokens > 5000:
                estimated_tokens = max(5000, int(estimated_tokens * 0.6))

            # Gate 智能升级
            gate_suggested = (
                self.auto_gate_upgrade
                and self._llm_callback is not None
                and self._estimate_complexity(content) > 0.65
            )
            complexity_level = self._classify_complexity(content)
            if otel_span:
                otel_span.set_attribute("gate.upgrade_suggested", str(gate_suggested))
                otel_span.set_attribute("task.complexity", complexity_level)
                otel_span.set_attribute("outcome", "ok")

            registry_model = get_registry_name(probe.recommended_model)
            return PreChatCheck(
                can_proceed=True,
                recommended_model=registry_model,
                estimated_tokens=estimated_tokens,
                budget_alert=budget.message if budget.alert_level.value != "none" else "",
                capability_blocked=capability_blocked,
                force_probe_reason=probe.reason,
                local_answer_suggestion=local_answer_suggestion,
                gate_upgrade_suggested=gate_suggested,
                task_complexity_level=complexity_level,
                mesh_routed=mesh_routed,
                mesh_peer=mesh_peer,
                routing_layer=routing_layer,
            )

    def set_llm_callback(self, callback: LlmCallback) -> None:
        """注入 LLM 回调——用于 Gate 智能升级和 Swarm 编排。"""
        self._llm_callback = callback
        self.orchestrator.set_llm_callback(callback)
        logger.info("ChatIntegration LLM callback 已注入，Gate 智能升级已就绪")

    def _classify_complexity(self, content: str) -> str:
        length = len(content)
        c = content.lower()
        keyword_score = 0
        if any(w in c for w in ["架构", "系统设计", "重构", "大规模", "多步骤"]):
            keyword_score += 2
        if any(w in c for w in ["分析", "对比", "报告", "方案"]):
            keyword_score += 1
        if any(w in c for w in ["代码", "优化", "修复", "部署"]):
            keyword_score += 1
        length_score = 0.5 if length > 100 else 0.2 if length > 50 else 0
        total = keyword_score + length_score
        if total >= 2:   return "complex"
        if total >= 1:   return "moderate"
        if length > 20:  return "simple"
        return "trivial"

    def post_chat_record(
        self, content: str, workspace_id: str, agent_id: str,
        model_used: str, tokens_used: int, gate_score: float,
        success: bool, tools_used: int = 0, duration_ms: int = 0,
        error_type: str = "", user_feedback: str = "",
    ) -> None:
        """消息完成后——记录 + 学习。所有非关键模块 fire-and-forget，不阻塞响应。"""
        otel_tracer = _reg.tracer
        span_attrs = {
            "agent.id": agent_id,
            "workspace.id": workspace_id,
            "model.used": model_used,
            "tokens.used": tokens_used,
            "gate.score": gate_score,
        }
        with (otel_tracer.span("chat.post_record", span_attrs) if otel_tracer else _null_context()) as otel_span:
            task_type = self._infer_task_type(content)
            if otel_span:
                otel_span.set_attribute("task.type", task_type.value)
                otel_span.set_attribute("outcome", "success" if success else "error")

            # 关键：执行日志 + Smart Allocator + Token
            try:
                self.logger_obj.log(ExecutionRecord(
                    agent_id=agent_id, workspace_id=workspace_id,
                    task_type=task_type.value, model_used=model_used,
                    tokens_used=tokens_used, gate_score=gate_score,
                    success=success, tools_used=tools_used,
                    duration_ms=duration_ms, error_type=error_type,
                    user_feedback=user_feedback,
                ))
                quality = gate_score if success else 0.3
                self.allocator.record_execution(task_type, tokens_used, quality, agent_id)
                _reg.token_budget.record_usage(agent_id, tokens_used)
            except Exception:
                logger.warning("执行日志记录失败", exc_info=True)

            # 非关键：fire-and-forget
            try:
                _reg.savings_engine.record_execution(task_type.value, tokens_used, model_used)
            except Exception:
                logger.warning("TokenSavings 记录失败", exc_info=True)
            try:
                self.honcho.learn_from_execution(agent_id, task_type.value, model_used, success)
            except Exception:
                logger.warning("HonchoModeler 学习失败", exc_info=True)
            try:
                if error_type:
                    _reg.healing_tracker.record(error_type, error_type, "auto_healed")
                    _reg.healing_tracker.record_result("auto_healed", success)
            except Exception:
                logger.warning("HealingTracker 记录失败", exc_info=True)
            # 递归自进化: 每次对话完成递增计数器
            try:
                _reg.recursive_evolution.increment_chat(
                    workspace_id=workspace_id, agent_id=agent_id,
                    model_used=model_used, tokens_used=tokens_used,
                    success=success, gate_score=gate_score,
                    task_type=task_type.value,
                    task_desc=content[:200] if content else "",
                )
            except Exception:
                logger.debug("递归自进化计数器更新失败", exc_info=True)
            # 涌现引擎: 记录行为模式 + 跨模块事件
            try:
                from engine.emergence import emergence_engine as _emerge
                _emerge.record_action({
                    "action": "chat",
                    "task_type": task_type.value,
                    "model": model_used,
                    "tokens": tokens_used,
                    "success": success,
                    "agent_id": agent_id,
                    "workspace_id": workspace_id,
                })
                _emerge.log_cross_module(
                    from_module="chat_hooks",
                    to_module="smart_allocator",
                    event_type="invocation",
                    detail=f"{task_type.value} → {model_used}",
                    performance_delta=gate_score - 0.5,
                )
            except Exception:
                pass

            # v1.8: L2场景分块 — 按项目/任务记录场景以便精准召回
            try:
                from engine.scene_chunker import scene_chunker
                if scene_chunker._is_initialized:
                    asyncio.ensure_future(
                        scene_chunker.record_chunk(
                            session_id=f"{workspace_id}:{agent_id}",
                            project=workspace_id or "default",
                            task_type=task_type.value,
                            task_label=content[:100] if content else "",
                            content=content[:2000] if content else "",
                            model_used=model_used,
                            outcome="成功" if success else "失败",
                        )
                    )
            except Exception:
                logger.debug("场景分块记录失败（非致命）", exc_info=True)

        # Gate 反馈
        if not success and gate_score < 0.5 and self._llm_callback is not None:
            logger.info(
                "Gate feedback: 任务失败 (score=%.2f), LLM Gate 可用但未启用。"
                "建议下次同类任务启用 LLM Gate。",
                gate_score,
            )

        # 上下文漂移检测: 记录消息 + 触发周期性检查
        try:
            drift = _reg.context_drift
            if drift:
                session_id = f"{workspace_id}:{agent_id}" if workspace_id and agent_id else "default"
                drift_report = drift.record_message(
                    session_id=session_id,
                    user_message=content,
                )
                if drift_report and drift_report.severity in ("red", "critical"):
                    logger.warning(
                        "上下文漂移告警: session=%s score=%.2f %s",
                        session_id[:12], drift_report.drift_score,
                        "; ".join(drift_report.findings),
                    )
                    # 红级漂移时通知涌现引擎
                    try:
                        from engine.emergence import emergence_engine as _emerge
                        _emerge.log_cross_module(
                            from_module="context_drift",
                            to_module="goal_loop_engine",
                            event_type="alert",
                            detail=f"drift_score={drift_report.drift_score}: {drift_report.suggested_action}",
                            performance_delta=-drift_report.drift_score,
                        )
                    except Exception:
                        pass
        except Exception:
            logger.debug("上下文漂移检测失败", exc_info=True)

    def handle_error(self, error_type: str, agent_id: str, workspace_id: str,
                     detail: str = "", context: dict | None = None) -> str:
        """错误处理——触发自愈回路。"""
        event = InterceptEvent(
            event_type=error_type,
            agent_id=agent_id,
            workspace_id=workspace_id,
            detail=detail,
            context=context or {},
        )
        result = _reg.self_healing.heal(event)
        if result.action == HealingAction.BLOCK_AND_NOTIFY:
            return f"操作被拦截: {result.suggestion}"
        return result.suggestion or ""

    def daily_reflection(self) -> dict:
        """每日反思——纯数据检索，不执行闭合链路/回传/Token报告。

        进化链统一入口在 recursive_evolution.trigger_daily_cycle()。
        本方法仅提供原始反思数据，不触发任何副作用。
        """
        records = self.logger_obj.get_today_records()
        if not records:
            records = self.logger_obj.get_recent(1)
        reflection = self.reflection.reflect(records)
        summary = self.reflection.consciousness_summary(reflection)

        return {
            "date": reflection.date,
            "total_executions": reflection.total_executions,
            "success_rate": reflection.success_rate,
            "recommended_actions": reflection.recommended_actions,
            "summary": summary,
            "top_success": reflection.top_success_pattern.recommendation if reflection.top_success_pattern else None,
            "top_failure": reflection.top_failure_pattern.name if reflection.top_failure_pattern else None,
        }

    def _infer_task_type(self, content: str) -> TaskType:
        """从消息内容推断任务类型。"""
        c = content.lower()
        if any(w in c for w in ["代码", "code", "编程", "函数", "bug", "修复", "debug", "调试", "重构", "类", "接口"]):
            return TaskType.CODING
        if any(w in c for w in ["写", "文章", "报告", "方案", "文案", "润色", "大纲"]):
            return TaskType.WRITING
        if any(w in c for w in ["分析", "数据", "对比", "竞品", "研究", "调研"]):
            return TaskType.ANALYSIS
        if any(w in c for w in ["搜", "查", "找", "搜索", "最新"]):
            return TaskType.SEARCH
        return TaskType.CONVERSATION

    def _needs_web_search(self, content: str) -> bool:
        return any(w in content.lower() for w in ["搜", "查最新", "网上", "互联网", "实时"])

    def _is_sensitive(self, content: str) -> bool:
        return any(w in content.lower() for w in ["密码", "密钥", "私密", "隐私", "机密", "内部"])

    def _estimate_complexity(self, content: str) -> float:
        if len(content) > 200: return 0.8
        if any(w in content.lower() for w in ["分析", "对比", "报告", "方案", "架构"]): return 0.7
        return 0.3


# ============================================================
# Null Context Manager (OTel 不可用时)
# ============================================================

class _NullContext:
    """空上下文管理器——当 OTel tracer 不可用时占位。"""
    def __enter__(self): return None
    def __exit__(self, *args): pass
    def set_attribute(self, *args, **kwargs): pass


_null_context = _NullContext


# ============================================================
# 全局实例
# ============================================================

_chat_integration: ChatIntegration | None = None


def get_chat_integration(db_path: str | None = None) -> ChatIntegration:
    global _chat_integration
    if _chat_integration is None:
        _chat_integration = ChatIntegration(db_path)
    elif db_path and _chat_integration.allocator._db_path is None:
        _chat_integration = ChatIntegration(db_path)
    return _chat_integration


class _ChatIntegrationProxy:
    """代理对象，将属性访问延迟到实际初始化之后。"""
    def __getattr__(self, name: str):
        return getattr(get_chat_integration(), name)


chat_integration: ChatIntegration = _ChatIntegrationProxy()  # type: ignore[assignment]
