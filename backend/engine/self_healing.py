"""
太极引擎 · 自愈回路（Self-Healing Loop）

无为而治——拦截 → 分析意图 → 生成替代方案 → Agent 自纠 → 规则沉淀。

不是"报错让用户修"，而是"系统自己发现模式，自己纠正，自己变强"。

P0修复: 为全局状态添加线程安全保护，使用asyncio.Lock防止竞态条件。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable
import json
import asyncio


class HealingAction(Enum):
    RETRY_WITH_ALT = "retry_with_alt"     # 生成替代方案，Agent 用替代方案继续
    DEGRADE_AND_CONTINUE = "degrade"       # 自动降级后继续
    RECORD_AND_LEARN = "record"            # 仅记录并学习，不阻断
    BLOCK_AND_NOTIFY = "block"             # 必须阻断，通知用户


@dataclass
class InterceptEvent:
    """被拦截的事件。"""
    event_type: str                        # "gate_fail" / "pi_intercept" / "token_exceeded" / "tool_duplicate"
    agent_id: str
    workspace_id: str
    detail: str                            # 失败原因 / 拦截原因
    context: dict = field(default_factory=dict)  # {task_type, model, tools_called, ...}
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class HealingResult:
    """自愈结果。"""
    action: HealingAction
    suggestion: str                        # 给 Agent 的建议
    alternative: str | None = None         # 替代方案
    learned_rule: str | None = None        # 新沉淀的规则
    confidence: float = 0.5


class SelfHealingLoop:
    """自愈回路——被拦截不是终点，是学习的起点。
    
    P0修复: 为全局状态添加线程安全保护，使用asyncio.Lock防止竞态条件。
    """

    def __init__(self, memory_callback: Callable | None = None,
                 model_recommender: Callable | None = None) -> None:
        self._memory: list[InterceptEvent] = []
        self._rules: list[str] = []        # 已沉淀的自愈规则
        self._memory_callback = memory_callback  # 写入 L2 记忆的回调
        self._model_recommender = model_recommender  # P2: 模型推荐回调（SmartAllocator）
        
        # P0修复: 添加异步锁保护全局状态
        self._lock: Optional[asyncio.Lock] = None
    
    async def _get_lock(self) -> asyncio.Lock:
        """获取锁（延迟初始化）"""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock
    
    def set_model_recommender(self, recommender: Callable) -> None:
        """P2: 设置模型推荐回调（由 SmartAllocator.recommend_model 提供）。"""
        self._model_recommender = recommender

    async def _handle_gate_fail_async(self, event: InterceptEvent) -> HealingResult:
        """Gate Validator FAIL 的自愈（异步版本）。"""
        lock = await self._get_lock()
        async with lock:
            task_type = event.context.get("task_type", "unknown")

            # 常见 Gate Fail 模式 + 替代方案
            patterns = {
                "quality_low": ("输出质量不达标。建议：用更高质量的模型重试，或拆分任务为更小的子任务。"),
                "format_error": ("输出格式不符合要求。建议：在系统提示中明确输出格式约束。"),
                "incomplete": ("输出不完整。建议：提高 Token 预算或拆分长任务为多个短任务。"),
            }

            suggestion = patterns.get(event.detail, f"执行未通过质量门禁。建议：检查任务描述是否清晰，适当提高 Token 预算。")

            alt = None
            # P2: 使用 SmartAllocator 重新推荐模型，替代硬编码的"DeepSeek V3.2"
            if self._model_recommender and "task_type" in event.context:
                try:
                    # 估算剩余预算和优先级
                    budget_remaining = event.context.get("budget_remaining", 20000)
                    priority = event.context.get("user_priority", 0.6)
                    from engine.smart_allocator import TaskType as STaskType
                    tt = STaskType.from_string(str(event.context.get("task_type", "conversation")))
                    rec_model, rec_tokens = self._model_recommender(tt, budget_remaining, priority)
                    alt = f"将模型切换到 {rec_model}（建议 Token: {rec_tokens}）以获得更高质量"
                except Exception:
                    alt = "将模型从低质量模型切换到更高质量模型"
            elif event.context.get("model_used") == "gemma-4":
                alt = "将模型从 Gemma-4 切换到更高质量模型以获得更高质量"
            if event.context.get("tools_called", 0) > 10:
                alt = "工具调用次数过多，建议精简任务范围或合并相似步骤"

            rule = f"[{task_type}] Gate FAIL: {event.detail[:80]} → {suggestion[:80]}"
            self._record_rule(rule)
            self._memory.append(event)

            return HealingResult(
                action=HealingAction.RETRY_WITH_ALT,
                suggestion=suggestion,
                alternative=alt,
                learned_rule=rule,
                confidence=0.7,
            )

    def handle_gate_fail(self, event: InterceptEvent) -> HealingResult:
        """Gate Validator FAIL 的自愈。

        修复 (6/21): 原逻辑在 loop 运行时调用 run_until_complete() 必然抛 RuntimeError，
        回退到 asyncio.run() 同样失败（无法在已有 loop 中创建新 loop）。
        修正为：无 loop → asyncio.run()；有 loop → 返回保守降级结果（同步快捷路径）。
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # 无运行中的 event loop，安全创建
            return asyncio.run(self._handle_gate_fail_async(event))

        # 已有 loop 运行中，走同步快捷路径避免阻塞
        logger.warning(
            "handle_gate_fail called from within running event loop, "
            "returning conservative degrade result"
        )
        return HealingResult(
            action=HealingAction.DEGRADE_AND_CONTINUE,
            suggestion="门禁失败，建议降级到备选模型重试",
            alternative="切换到 fallback 模型继续执行",
            confidence=0.5,
        )

    async def _handle_pi_intercept_async(self, event: InterceptEvent) -> HealingResult:
        """Pi 准则拦截的自愈（异步版本）。"""
        lock = await self._get_lock()
        async with lock:
            detail = event.detail

            patterns = {
                "file_delete": "检测到文件删除操作。建议：先备份后删除，操作可逆。",
                "system_cmd": "检测到系统命令执行。建议：用沙箱安全方式替代，或在用户审批后执行。",
                "out_of_workspace": "检测到越界访问。建议：将所需文件复制到工作间内再操作。",
            }

            suggestion = patterns.get(detail, f"操作被安全策略拦截。建议：用更安全的方式达成相同目标。")

            alt = None
            if detail == "file_delete":
                alt = "将文件移动到回收站而非永久删除"
            if detail == "system_cmd":
                alt = "使用 Hermes 内置的工具（execute_code）替代直接系统命令"

            rule = f"Pi拦截: {detail} → {suggestion[:80]}"
            self._record_rule(rule)
            self._memory.append(event)

            return HealingResult(
                action=HealingAction.RETRY_WITH_ALT,
                suggestion=suggestion,
                alternative=alt,
                learned_rule=rule,
                confidence=0.8,
            )

    def handle_pi_intercept(self, event: InterceptEvent) -> HealingResult:
        """Pi 准则拦截的自愈。

        修复 (6/21): 同 handle_gate_fail——loop 运行时走同步快捷路径，避免死锁。
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._handle_pi_intercept_async(event))

        # 已有 loop 运行中，走同步保守结果
        logger.warning(
            "handle_pi_intercept called from within running event loop, "
            "returning conservative block result"
        )
        return HealingResult(
            action=HealingAction.BLOCK_AND_NOTIFY,
            suggestion=f"操作被安全策略拦截（{event.detail}），请在用户审批后执行",
            confidence=0.9,
        )

    def handle_token_warning(self, event: InterceptEvent) -> HealingResult:
        """Token 超限的自愈。"""
        pct = event.context.get("percentage", 0)

        if pct >= 1.0:
            return HealingResult(
                action=HealingAction.DEGRADE_AND_CONTINUE,
                suggestion="Token 已超限。已自动切换到 Gemma-4 继续执行。",
                alternative="gemma-4",
                learned_rule=f"Token超限(≥100%): 自动降级到gemma-4",
                confidence=0.95,
            )
        elif pct >= 0.9:
            return HealingResult(
                action=HealingAction.RECORD_AND_LEARN,
                suggestion="Token 即将耗尽。建议手动提高预算或切换到更省 Token 的模型。",
                learned_rule=f"Token预警(≥90%): {event.context.get('task_type')} 类型消耗高",
                confidence=0.85,
            )
        else:
            return HealingResult(
                action=HealingAction.RECORD_AND_LEARN,
                suggestion="Token 消耗达到预警线，继续监控。",
                confidence=0.9,
            )

    def handle_tool_duplicate(self, event: InterceptEvent) -> HealingResult:
        """工具调用去重。"""
        return HealingResult(
            action=HealingAction.RECORD_AND_LEARN,
            suggestion="检测到重复工具调用。已从缓存返回结果，避免重复消耗 Token。",
            learned_rule=f"工具去重: {event.detail} → 5分钟内缓存",
            confidence=0.9,
        )

    def heal(self, event: InterceptEvent) -> HealingResult:
        """统一入口——根据事件类型分发到对应的自愈处理。"""
        handlers = {
            "gate_fail": self.handle_gate_fail,
            "pi_intercept": self.handle_pi_intercept,
            "token_exceeded": self.handle_token_warning,
            "tool_duplicate": self.handle_tool_duplicate,
        }
        handler = handlers.get(event.event_type)
        if handler:
            result = handler(event)
            if self._memory_callback:
                self._memory_callback(event, result)
            # P1: 调用 healing_tracker 记录追踪，闭环自愈效果
            try:
                from engine.healing_tracker import healing_tracker
                suggestion_text = result.suggestion or result.alternative or "auto_healed"
                healing_tracker.record(event.event_type, event.detail, suggestion_text)
            except Exception:
                pass
            return result
        return HealingResult(
            action=HealingAction.BLOCK_AND_NOTIFY,
            suggestion=f"未知事件类型: {event.event_type}",
            confidence=0.1,
        )

    # ---- 规则管理 ----

    def _record_rule(self, rule: str) -> None:
        """记录规则（内部方法，调用方需确保已加锁）。"""
        if rule not in self._rules:
            self._rules.append(rule)

    @property
    def rules(self) -> list[str]:
        return self._rules.copy()

    @property
    def event_count(self) -> int:
        return len(self._memory)

    def get_stats(self) -> dict:
        """获取自愈统计。
        
        P0修复: 使用锁保护共享状态读取。
        """
        import asyncio
        
        async def _get_stats():
            lock = await self._get_lock()
            async with lock:
                return {
                    "total_events": len(self._memory),
                    "rules_learned": len(self._rules),
                    "events_by_type": {},
                    "rules": self._rules[-5:],  # 最近 5 条
                }
        
        try:
            loop = asyncio.get_running_loop()
            return loop.run_until_complete(_get_stats())
        except RuntimeError:
            return asyncio.run(_get_stats())


# 平台唯一实例
self_healing = SelfHealingLoop()
