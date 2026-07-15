"""
太极引擎 · 递归自进化引擎（Recursive Evolution Engine）

太极第七律·生生不息——引擎自己进化。
"不烧Token、不打扰用户、不越界——但越用越强。"

核心机制：
  1. 对话计数器：每完成一次对话，+1
  2. 微型周期（Micro Cycle）：每 N 次对话触发一次轻量闭环评估
  3. 每日周期（Daily Cycle）：每天触发一次深度进化分析
  4. 意识流（Consciousness）：追踪引擎的"自我感知"——性能变化趋势
  5. 进化历史（History）：可回溯的进化轨迹

数据流：
  chat.py post_task → increment_chat() → counter++
    → 达到阈值 → _trigger_micro_cycle() → 轻量模式识别+参数微调
  main.py daily task → trigger_daily_cycle() → 反思→闭合→回传
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional
import asyncio
import json
import logging
import os

logger = logging.getLogger("niuma.evolution")


# ============================================================
# 数据模型
# ============================================================

@dataclass
class ConsciousnessEvent:
    """意识流事件——引擎的"自我感知"记录"""
    id: str
    timestamp: str
    event_type: str          # micro_cycle / daily_cycle / pattern_found / anomaly / growth
    summary: str
    metrics: dict = field(default_factory=dict)
    importance: float = 0.5  # 0.0-1.0


@dataclass
class EvolutionCycle:
    """一次进化周期记录"""
    id: str
    cycle_type: str          # micro / daily / manual
    started_at: str
    completed_at: str = ""
    findings: list[str] = field(default_factory=list)
    changes_applied: list[str] = field(default_factory=list)
    metrics_before: dict = field(default_factory=dict)
    metrics_after: dict = field(default_factory=dict)
    success: bool = False


# ============================================================
# 递归自进化引擎
# ============================================================

class RecursiveEvolutionEngine:
    """递归自进化引擎。

    不替代 SelfEvolutionWriter（安全配置写入）或 ClosureEngine（闭合链路），
    而是它们的上层调度器——决定何时触发、采用什么策略、记录进化轨迹。

    太极哲学：顺势而为——只在有足够样本时进化，不瞎折腾。
    """

    MICRO_CYCLE_THRESHOLD = 5   # 每5次对话触发微型周期
    MAX_CONSCIOUSNESS = 100     # 意识流上限
    DATA_DIR = "data/evolution"

    def __init__(self, db_path: str = "data/taiji.db", data_dir: str | None = None) -> None:
        self._db_path = db_path
        self._data_dir = data_dir or self.DATA_DIR
        self._chat_counter: int = 0
        self._micro_cycles_completed: int = 0
        self._daily_cycles_completed: int = 0
        self._last_daily_date: str = ""        # ISO date string
        self._last_micro_at: int = 0            # chat_counter 触发时的值
        self._consciousness: list[ConsciousnessEvent] = []
        self._evolution_history: list[EvolutionCycle] = []
        self._pending_changes: list[str] = []
        self._trend_data: dict = {
            "success_rate": [],
            "avg_tokens": [],
            "model_diversity": [],
            "patterns_found": 0,
        }
        self._is_initialized = False

    # ============================================================
    # 初始化
    # ============================================================

    async def initialize(self) -> None:
        """从持久化恢复状态。"""
        os.makedirs(self._data_dir, exist_ok=True)
        state_file = os.path.join(self._data_dir, "evolution_state.json")
        try:
            if os.path.exists(state_file):
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                self._chat_counter = state.get("chat_counter", 0)
                self._micro_cycles_completed = state.get("micro_cycles_completed", 0)
                self._daily_cycles_completed = state.get("daily_cycles_completed", 0)
                self._last_daily_date = state.get("last_daily_date", "")
                self._last_micro_at = state.get("last_micro_at", 0)
                # 恢复意识流（只保留最近MAX条）
                raw_consciousness = state.get("consciousness", [])
                self._consciousness = [
                    ConsciousnessEvent(**c) for c in raw_consciousness[-self.MAX_CONSCIOUSNESS:]
                ]
                # 恢复进化历史
                raw_history = state.get("evolution_history", [])
                self._evolution_history = [EvolutionCycle(**h) for h in raw_history]
                self._trend_data = state.get("trend_data", self._trend_data)
                logger.info(
                    f"递归自进化引擎恢复: {self._chat_counter}次对话, "
                    f"{self._micro_cycles_completed}微周期, {self._daily_cycles_completed}日周期"
                )
        except Exception:
            logger.warning("进化状态文件损坏，从零开始", exc_info=True)
        self._is_initialized = True

    async def _save_state(self) -> None:
        """持久化当前状态（fire-and-forget，静默失败）。"""
        state_file = os.path.join(self._data_dir, "evolution_state.json")
        try:
            # 只保存最近100条意识流
            conscious_raw = [
                {
                    "id": c.id, "timestamp": c.timestamp, "event_type": c.event_type,
                    "summary": c.summary, "metrics": c.metrics, "importance": c.importance,
                }
                for c in self._consciousness[-self.MAX_CONSCIOUSNESS:]
            ]
            history_raw = [
                {
                    "id": h.id, "cycle_type": h.cycle_type,
                    "started_at": h.started_at, "completed_at": h.completed_at,
                    "findings": h.findings, "changes_applied": h.changes_applied,
                    "metrics_before": h.metrics_before, "metrics_after": h.metrics_after,
                    "success": h.success,
                }
                for h in self._evolution_history[-50:]
            ]
            state = {
                "chat_counter": self._chat_counter,
                "micro_cycles_completed": self._micro_cycles_completed,
                "daily_cycles_completed": self._daily_cycles_completed,
                "last_daily_date": self._last_daily_date,
                "last_micro_at": self._last_micro_at,
                "consciousness": conscious_raw,
                "evolution_history": history_raw,
                "trend_data": self._trend_data,
                "saved_at": datetime.now().isoformat(),
            }
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.debug("进化状态持久化失败", exc_info=True)

    # ============================================================
    # 对话计数 — 主入口
    # ============================================================

    async def increment_chat(self, workspace_id: str = "", agent_id: str = "",
                             model_used: str = "", tokens_used: int = 0,
                             success: bool = True, gate_score: float = 0.0,
                             task_type: str = "", task_desc: str = "",
                             tools_used: list[str] | None = None) -> bool:
        """每次对话完成后调用。达到阈值自动触发微型周期。

        v1.8: 新增 task_type/task_desc/tools_used 参数，记录轨迹到经验蒸馏层。

        Returns:
            True 如果触发了微型周期（调用方可异步处理但不阻塞）
        """
        if not self._is_initialized:
            return False

        self._chat_counter += 1

        # v1.8: 记录轨迹到经验蒸馏层
        try:
            from engine.distillation import distillation
            if distillation._is_initialized:
                await distillation.record_trajectory(
                    task_type=task_type or "conversation",
                    task_desc=task_desc or f"workspace={workspace_id}",
                    model_used=model_used,
                    tools_used=tools_used,
                    success=success,
                    gate_score=gate_score,
                    tokens_used=tokens_used,
                )
        except Exception:
            logger.debug("轨迹记录失败（非致命）", exc_info=True)

        # 更新趋势数据
        self._trend_data["success_rate"].append(1.0 if success else 0.0)
        if len(self._trend_data["success_rate"]) > 100:
            self._trend_data["success_rate"] = self._trend_data["success_rate"][-100:]
        if tokens_used > 0:
            self._trend_data["avg_tokens"].append(tokens_used)
            if len(self._trend_data["avg_tokens"]) > 100:
                self._trend_data["avg_tokens"] = self._trend_data["avg_tokens"][-100:]

        # 检查微型周期触发条件
        chats_since_last = self._chat_counter - self._last_micro_at
        if chats_since_last >= self.MICRO_CYCLE_THRESHOLD:
            # 异步触发，不阻塞
            asyncio.ensure_future(self._trigger_micro_cycle())
            return True

        # 持久化（每5次存一次，减少IO）
        if self._chat_counter % 5 == 0:
            asyncio.ensure_future(self._save_state())

        return False

    # ============================================================
    # 微型周期
    # ============================================================

    async def _trigger_micro_cycle(self) -> EvolutionCycle:
        """微型进化周期——轻量快速，不阻塞用户。

        流程：
          1. 收集近期趋势数据
          2. 检测模式变化
          3. 如果需要 → 微调参数（预算/权重/降级偏好）
          4. 记录意识事件
        """
        cycle = EvolutionCycle(
            id=f"micro-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self._chat_counter}",
            cycle_type="micro",
            started_at=datetime.now().isoformat(),
        )

        try:
            # 1. 分析近期成功率趋势
            recent_success = self._trend_data["success_rate"][-20:]
            avg_success = sum(recent_success) / len(recent_success) if recent_success else 0.0

            # 2. 检测模型多样性
            model_diversity = len(set(
                self._trend_data.get("model_diversity", ["deepseek-v4-pro"])
            ))

            # 3. 生成发现
            findings = []
            if avg_success < 0.7:
                findings.append(f"近期成功率偏低({avg_success:.0%})，建议检查降级链")
            elif avg_success > 0.95:
                findings.append(f"成功率优秀({avg_success:.0%})，当前模型组合稳定")
            if model_diversity <= 1:
                findings.append("模型使用单一，建议启用多模型并行探索")

            # 4. 记录趋势数据
            recent_avg_tokens = (
                sum(self._trend_data["avg_tokens"][-20:]) / 20
                if len(self._trend_data["avg_tokens"]) >= 20
                else 0
            )
            cycle.metrics_before = {
                "chat_counter": self._chat_counter,
                "avg_success_rate": round(avg_success, 3),
                "model_diversity": model_diversity,
                "recent_avg_tokens": recent_avg_tokens,
            }

            # 5. 如果有模式发现，尝试闭合链路
            changes = []
            if findings:
                try:
                    from engine.closure_engine import closure_engine
                    for finding in findings:
                        if "成功率" in finding:
                            closure_engine.evaluate_from_reflection(
                                f"micro_cycle:{finding}", avg_success
                            )
                    auto_result = closure_engine.auto_apply_safe_changes()
                    if auto_result.get("applied", 0) > 0:
                        changes.append(f"自动应用了{auto_result['applied']}个安全变更")
                except Exception:
                    logger.debug("闭合链路不可用，跳过", exc_info=True)

            # v1.8: 经验蒸馏 — 从轨迹中提取决策规则
            try:
                from engine.distillation import distillation
                if distillation._is_initialized:
                    new_rules = await distillation.distill_rules()
                    if new_rules:
                        changes.append(f"经验蒸馏提取{len(new_rules)}条决策规则")
                        for rule in new_rules[:3]:  # 只记录前3条
                            findings.append(f"蒸馏规则: {rule.action}")
            except Exception:
                logger.debug("经验蒸馏不可用，跳过", exc_info=True)

            # v1.8: SkillForge 迭代淘汰 — 淘汰低效技能
            try:
                from engine.skill_forge import skill_forge
                prune_result = skill_forge.prune_skills()
                if prune_result.get("deprecated"):
                    changes.append(f"淘汰{len(prune_result['deprecated'])}个低效技能")
                    findings.append(f"SkillForge淘汰: {', '.join(d['name'] for d in prune_result['deprecated'])}")
                if prune_result.get("warned"):
                    changes.append(f"预警{len(prune_result['warned'])}个技能即将淘汰")
            except Exception:
                logger.debug("SkillForge不可用，跳过", exc_info=True)

            cycle.findings = findings
            cycle.changes_applied = changes
            cycle.completed_at = datetime.now().isoformat()
            cycle.success = True

            # 6. 涌现引擎——检测模块间自然形成的模式
            try:
                from engine.emergence import emergence_engine as _ee
                emerge_result = await _ee.run_emergence_cycle()
                if emerge_result.get("new_patterns", 0) > 0:
                    findings.append(f"涌现引擎发现{emerge_result['new_patterns']}个新行为模式")
                if emerge_result.get("new_insights", 0) > 0:
                    findings.append(f"涌现引擎生成{emerge_result['new_insights']}个洞察")
            except Exception:
                logger.debug("涌现引擎不可用", exc_info=True)

            # 7. 记录意识事件
            event = ConsciousnessEvent(
                id=f"conscious-{cycle.id}",
                timestamp=datetime.now().isoformat(),
                event_type="micro_cycle",
                summary=f"微周期#{self._micro_cycles_completed + 1}: {', '.join(findings) if findings else '无异常'}",
                metrics=cycle.metrics_before,
                importance=0.3 if not findings else 0.7,
            )
            self._consciousness.append(event)

            self._micro_cycles_completed += 1
            self._last_micro_at = self._chat_counter
            self._evolution_history.append(cycle)

            logger.info(
                f"微周期完成: chat#{self._chat_counter}, "
                f"成功率={avg_success:.0%}, 发现={len(findings)}, 变更={len(changes)}"
            )

        except Exception:
            logger.exception("微周期执行异常")
            cycle.completed_at = datetime.now().isoformat()
            cycle.findings = ["微周期执行异常"]

        # 仅在触发时持久化
        asyncio.ensure_future(self._save_state())
        return cycle

    # ============================================================
    # 每日周期
    # ============================================================

    async def trigger_daily_cycle(self) -> EvolutionCycle | None:
        """每日深度进化周期。

        由自动化任务或手动触发。如果今天已经执行过，跳过。
        """
        today = date.today().isoformat()
        if self._last_daily_date == today:
            logger.debug(f"今日({today})已执行每日周期，跳过")
            return None

        cycle = EvolutionCycle(
            id=f"daily-{today}",
            cycle_type="daily",
            started_at=datetime.now().isoformat(),
        )

        try:
            # 1. 汇总指标
            total_chats_today = self._chat_counter  # 累计值
            recent_success = self._trend_data["success_rate"][-50:]
            avg_success = sum(recent_success) / len(recent_success) if recent_success else 0.0

            cycle.metrics_before = {
                "total_chats": total_chats_today,
                "micro_cycles_today": self._micro_cycles_completed,
                "daily_cycles_total": self._daily_cycles_completed,
                "avg_success_rate": round(avg_success, 3),
                "consciousness_events": len(self._consciousness),
            }

            # 2. 分析趋势数据（本引擎自身趋势，不依赖外部队列）
            findings = []
            if avg_success < 0.7:
                findings.append(f"近期成功率偏低({avg_success:.0%})，建议检查降级链和模型配置")
            elif avg_success > 0.92:
                findings.append(f"成功率优秀({avg_success:.0%})，当前配置稳定")
            if self._chat_counter > 0:
                avg_token = (
                    sum(self._trend_data["avg_tokens"][-50:]) / min(50, len(self._trend_data["avg_tokens"]))
                    if self._trend_data["avg_tokens"] else 0
                )
                if avg_token > 0:
                    findings.append(f"近期平均Token消耗: {avg_token:.0f}/次 (累计{self._chat_counter}次对话)")

            # 3. 调用闭合链路
            changes = []
            try:
                from engine.closure_engine import closure_engine
                auto_result = closure_engine.auto_apply_safe_changes()
                if auto_result.get("applied", 0) > 0:
                    changes.append(f"自动应用了{auto_result['applied']}个变更")
                if auto_result.get("rolled_back", 0) > 0:
                    changes.append(f"回滚了{auto_result['rolled_back']}个失败变更")
            except Exception:
                logger.debug("闭合链路不可用", exc_info=True)

            # 4. 涌现引擎——每日深度模式检测
            try:
                from engine.emergence import emergence_engine as _ee
                emerge_result = await _ee.run_emergence_cycle()
                if emerge_result.get("new_insights", 0) > 0:
                    findings.append(f"涌现引擎发现{emerge_result['new_insights']}个新洞察")
            except Exception:
                logger.debug("涌现引擎不可用", exc_info=True)

            # 5. 进化回传
            try:
                from engine.telemetry_hub import telemetry_hub
                if telemetry_hub.is_enabled():
                    telemetry_hub.collect(
                        patterns=[{"name": f"daily-{today}", "success_rate": avg_success}],
                        auto_changes=[{"applied": len(changes), "date": today}],
                        savings={},
                        hardware={},
                    )
            except Exception:
                pass

            cycle.findings = findings
            cycle.changes_applied = changes
            cycle.metrics_after = {
                "patterns_found": len(findings),
                "changes_applied": len(changes),
            }
            cycle.completed_at = datetime.now().isoformat()
            cycle.success = True

            # 5. 记录意识事件
            event = ConsciousnessEvent(
                id=f"conscious-daily-{today}",
                timestamp=datetime.now().isoformat(),
                event_type="daily_cycle",
                summary=f"日周期#{self._daily_cycles_completed + 1}: {len(findings)}发现, {len(changes)}变更",
                metrics=cycle.metrics_before,
                importance=0.8,
            )
            self._consciousness.append(event)

            self._daily_cycles_completed += 1
            self._last_daily_date = today
            self._evolution_history.append(cycle)

            logger.info(f"日周期完成: {today}, 发现={len(findings)}, 变更={len(changes)}")

        except Exception:
            logger.exception("每日周期执行异常")
            cycle.completed_at = datetime.now().isoformat()
            cycle.findings = ["日周期执行异常"]

        await self._save_state()
        return cycle

    # ============================================================
    # 手动触发
    # ============================================================

    async def trigger_manual_cycle(self, reason: str = "manual") -> EvolutionCycle:
        """手动触发进化周期——用于调试或紧急场景。"""
        cycle = EvolutionCycle(
            id=f"manual-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            cycle_type="manual",
            started_at=datetime.now().isoformat(),
        )

        try:
            # 取得近期数据
            recent_success = self._trend_data["success_rate"][-30:]
            avg_success = sum(recent_success) / len(recent_success) if recent_success else 0.0

            cycle.metrics_before = {
                "chat_counter": self._chat_counter,
                "avg_success_rate": round(avg_success, 3),
                "reason": reason,
            }

            # 运行闭合链路
            changes = []
            try:
                from engine.closure_engine import closure_engine
                closure_engine.evaluate_from_reflection(f"manual_trigger:{reason}", avg_success)
                auto_result = closure_engine.auto_apply_safe_changes()
                if auto_result.get("applied", 0) > 0:
                    changes.append(f"应用{auto_result['applied']}变更")
            except Exception:
                pass

            cycle.findings = [f"手动触发: {reason}"]
            cycle.changes_applied = changes
            cycle.completed_at = datetime.now().isoformat()
            cycle.success = True

            self._evolution_history.append(cycle)

        except Exception:
            logger.exception("手动周期异常")
            cycle.completed_at = datetime.now().isoformat()

        return cycle

    # ============================================================
    # 查询接口
    # ============================================================

    def get_status(self) -> dict:
        """获取当前进化状态。"""
        recent_success = self._trend_data["success_rate"][-20:]
        avg_success = sum(recent_success) / len(recent_success) if recent_success else 0.0
        chats_until_next = self.MICRO_CYCLE_THRESHOLD - (self._chat_counter - self._last_micro_at)

        return {
            "version": "v1.7",
            "chat_counter": self._chat_counter,
            "micro_cycles_completed": self._micro_cycles_completed,
            "daily_cycles_completed": self._daily_cycles_completed,
            "last_daily_date": self._last_daily_date,
            "chats_until_next_micro": max(0, chats_until_next),
            "micro_threshold": self.MICRO_CYCLE_THRESHOLD,
            "avg_success_rate": round(avg_success, 3),
            "consciousness_events": len(self._consciousness),
            "evolution_cycles": len(self._evolution_history),
            "pending_changes": len(self._pending_changes),
            "initialized": self._is_initialized,
        }

    def get_consciousness(self, limit: int = 20) -> list[dict]:
        """获取意识流——最近的事件。"""
        events = self._consciousness[-limit:]
        return [
            {
                "id": e.id,
                "timestamp": e.timestamp,
                "event_type": e.event_type,
                "summary": e.summary,
                "metrics": e.metrics,
                "importance": e.importance,
            }
            for e in reversed(events)
        ]

    def get_trend(self) -> dict:
        """获取进化趋势数据。"""
        recent_success = self._trend_data["success_rate"][-50:]
        recent_tokens = self._trend_data["avg_tokens"][-50:]

        return {
            "chat_counter": self._chat_counter,
            "success_rate": {
                "recent_50": round(
                    sum(recent_success) / len(recent_success), 3
                ) if recent_success else 0.0,
                "trend": "up" if (
                    len(recent_success) >= 20 and
                    sum(recent_success[-10:]) / 10 > sum(recent_success[:10]) / 10
                ) else "stable" if len(recent_success) < 20 else "down",
            },
            "avg_tokens": {
                "recent_50": round(
                    sum(recent_tokens) / len(recent_tokens), 0
                ) if recent_tokens else 0,
                "trend": "stable",
            },
            "patterns_found": self._trend_data.get("patterns_found", 0),
            "micro_cycles": self._micro_cycles_completed,
            "daily_cycles": self._daily_cycles_completed,
        }

    def get_history(self, limit: int = 10) -> list[dict]:
        """获取进化历史。"""
        cycles = self._evolution_history[-limit:]
        return [
            {
                "id": c.id,
                "cycle_type": c.cycle_type,
                "started_at": c.started_at,
                "completed_at": c.completed_at,
                "findings": c.findings,
                "changes_applied": c.changes_applied,
                "success": c.success,
            }
            for c in reversed(cycles)
        ]

    def get_daily(self) -> dict | None:
        """获取今日的每日周期结果。"""
        today = date.today().isoformat()
        for c in reversed(self._evolution_history):
            if c.cycle_type == "daily" and c.id.endswith(today):
                return {
                    "id": c.id,
                    "started_at": c.started_at,
                    "completed_at": c.completed_at,
                    "findings": c.findings,
                    "changes_applied": c.changes_applied,
                    "success": c.success,
                }
        return None


# ============================================================
# 全局实例
# ============================================================

recursive_evolution = RecursiveEvolutionEngine()
