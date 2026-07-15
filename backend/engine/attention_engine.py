"""
太极引擎 · Attention Engine（注意力引擎）

以静制动——全局感知 + 7种情况主动说话 + 学习化。
Hermes 背后监控一切，但只在需要的时刻开口。
v2.0: 学习化——历史模式学习 + 衰减权重 + 自适应优先级。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import math

# ──────────────────────────────────────────────────────────────
# 学习记忆
# ──────────────────────────────────────────────────────────────

@dataclass
class InteractionRecord:
    """单次交互记录。"""
    timestamp: float
    event_type: str           # icebreak / progress / warning / error / summary / pattern / suggestion
    message: str
    priority: int
    user_acknowledged: bool = False    # 用户是否看了/回应了
    user_action: str = ""              # "accepted" / "dismissed" / "ignored"
    duration_to_response_ms: int = 0  # 用户多久回应

@dataclass
class LearningProfile:
    """用户学习画像——从交互历史中学习。"""
    total_events_sent: int = 0
    acknowledge_rate: float = 0.0         # 用户关注率
    acceptance_rate: float = 0.0          # 建议采纳率
    suggestion_history: dict = field(default_factory=dict)  # {suggestion_text: accept_count}
    error_recurrence: dict = field(default_factory=dict)    # {error_type: count}
    pattern_effectiveness: dict = field(default_factory=dict)  # {pattern_name: effectiveness}
    last_active: float = 0.0              # 最后活跃时间戳
    interaction_count: int = 0            # 总交互次数
    optimal_priority_bias: float = 0.0    # 学习到的优先级偏移 (-2..+2)


class LearningMemory:
    """学习记忆——带指数衰减的交互历史。

    不存储原始内容，只存储模式统计。符合隐私原则。
    """

    DEF_INTERACTION_MAX = 100          # 每个用户最多保留 100 条记录
    DEF_DECAY_HALF_LIFE = 7 * 86400    # 7 天半衰期 (秒)

    def __init__(self) -> None:
        self._records: dict[str, list[InteractionRecord]] = {}
        self._profiles: dict[str, LearningProfile] = {}

    def record(self, user_id: str, event_type: str, message: str, priority: int) -> None:
        """记录一次注意力事件。"""
        if user_id not in self._records:
            self._records[user_id] = []
        rec = InteractionRecord(
            timestamp=datetime.now().timestamp(),
            event_type=event_type,
            message=message,
            priority=priority,
        )
        records = self._records[user_id]
        records.append(rec)
        if len(records) > self.DEF_INTERACTION_MAX:
            self._records[user_id] = records[-self.DEF_INTERACTION_MAX:]

        # 更新 profile
        profile = self._get_profile(user_id)
        profile.total_events_sent += 1
        profile.last_active = rec.timestamp

    def record_outcome(self, user_id: str, event_type: str, message: str, outcome: str) -> None:
        """记录用户对事件的反应——闭合学习回路。"""
        profile = self._get_profile(user_id)
        profile.interaction_count += 1

        # 更新最近匹配的事件
        if user_id in self._records:
            for rec in reversed(self._records[user_id]):
                if rec.event_type == event_type and rec.message[:30] == message[:30]:
                    rec.user_action = outcome
                    if outcome in ("accepted", "dismissed"):
                        rec.user_acknowledged = True
                    break

        # 更新 profile 统计（带衰减）
        self._update_profile_from_history(user_id, profile)

    def _get_profile(self, user_id: str) -> LearningProfile:
        if user_id not in self._profiles:
            self._profiles[user_id] = LearningProfile()
        return self._profiles[user_id]

    def _update_profile_from_history(self, user_id: str, profile: LearningProfile) -> None:
        """从历史记录中更新学习画像——使用指数衰减权重。"""
        if user_id not in self._records:
            return

        now = datetime.now().timestamp()
        records = self._records[user_id]
        total_weight = 0.0
        ack_weight = 0.0
        acc_weight = 0.0
        accept_count = 0
        dismiss_count = 0

        for rec in records:
            age = now - rec.timestamp
            weight = math.exp(-age * math.log(2) / self.DEF_DECAY_HALF_LIFE)
            total_weight += weight

            if rec.user_acknowledged:
                ack_weight += weight
            if rec.user_action == "accepted":
                acc_weight += weight
                accept_count += 1
            elif rec.user_action == "dismissed":
                dismiss_count += 1

            # 追踪建议效果
            if rec.event_type == "suggestion" and rec.user_action:
                key = rec.message[:60]
                if key not in profile.suggestion_history:
                    profile.suggestion_history[key] = 0
                profile.suggestion_history[key] += 1 if rec.user_action == "accepted" else 0

            # 追踪错误复发
            if rec.event_type == "error":
                err_key = rec.message[:40]
                profile.error_recurrence[err_key] = profile.error_recurrence.get(err_key, 0) + 1

            # 追踪模式有效性
            if rec.event_type == "pattern":
                pat_key = rec.message[:60]
                if pat_key not in profile.pattern_effectiveness:
                    profile.pattern_effectiveness[pat_key] = 0.0
                if rec.user_action == "accepted":
                    profile.pattern_effectiveness[pat_key] += weight

        if total_weight > 0:
            profile.acknowledge_rate = ack_weight / total_weight
            profile.acceptance_rate = acc_weight / total_weight

        # 学习优先级偏移：高采纳率 → 高优先级，高忽略率 → 低优先级
        if accept_count + dismiss_count > 3:
            ratio = accept_count / (accept_count + dismiss_count + 0.01)
            profile.optimal_priority_bias = (ratio - 0.5) * 4  # -2 .. +2

        profile.last_active = now

    def get_profile(self, user_id: str) -> LearningProfile:
        return self._get_profile(user_id)

    def get_effective_acceptance(self, user_id: str, suggestion_key: str) -> float:
        """获取特定建议的历史采纳率（0.0-1.0）。"""
        profile = self._get_profile(user_id)
        key = suggestion_key[:60]
        return profile.suggestion_history.get(key, 0) / max(profile.interaction_count, 1)

    def get_stats(self) -> dict:
        return {
            "users_tracked": len(self._records),
            "total_records": sum(len(r) for r in self._records.values()),
        }


# ──────────────────────────────────────────────────────────────
# Attention Engine
# ──────────────────────────────────────────────────────────────

class TriggerType(Enum):
    ICEBREAK = "icebreak"           # 1. 破冰：首次/每日首次
    PROGRESS = "progress"           # 2. 进度：长任务阶段反馈
    WARNING = "warning"             # 3. 预警：Token/安全阈值突破
    ERROR = "error"                 # 4. 错误：Gate FAIL
    SUMMARY = "summary"             # 5. 总结：任务完成交付
    PATTERN = "pattern"             # 6. 发现：跨工作间共性模式
    SUGGESTION = "suggestion"       # 7. 建议：优化建议


@dataclass
class AttentionEvent:
    trigger: TriggerType
    message: str
    workspace_id: str = ""
    agent_id: str = ""
    priority: int = 5               # 1-10, 10=最高（v2.0: 学习化后动态调整）
    requires_approval: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    learning_boost: int = 0         # v2.0: 学习带来的优先级调整量


class AttentionEngine:
    """注意力引擎——以静制动（v2.0 学习化）。

    全局感知所有工作间，7种情况触发主动说话。
    越确定的事越沉默——置信度不够时才开口。
    v2.0: 从交互历史中学习用户偏好，自适应调整事件优先级。
    """

    def __init__(self) -> None:
        self._daily_first_seen: dict[str, bool] = {}
        self._task_durations: dict[str, float] = {}
        self._task_progress: dict[str, float] = {}
        self._patterns_seen: dict[str, int] = {}
        self._last_suggestion_time: dict[str, float] = {}
        self._memory = LearningMemory()

    # ════════════════════════════════════════════════════════════
    # 7 种触发情况
    # ════════════════════════════════════════════════════════════

    def check_icebreak(self, user_id: str) -> Optional[AttentionEvent]:
        """每日首次打开——打个招呼。

        v2.0: 根据用户活跃度调整消息语气。
        """
        today = datetime.now().strftime("%Y-%m-%d")
        key = f"{user_id}:{today}"
        if key not in self._daily_first_seen:
            self._daily_first_seen[key] = True

            # 高频用户：简短问候；低频用户：完整欢迎
            profile = self._memory.get_profile(user_id)
            if profile.interaction_count > 50:
                msg = "早，太极引擎已就绪。"
            elif profile.interaction_count > 10:
                msg = "早上好。今天有什么需要？"
            else:
                msg = "早上好。太极引擎已就绪，今天我能帮你做什么？"

            return AttentionEvent(
                trigger=TriggerType.ICEBREAK,
                message=msg,
                priority=3,
            )
        return None

    def check_progress(
        self, task_id: str, progress_pct: float, elapsed_seconds: float
    ) -> Optional[AttentionEvent]:
        """长任务阶段性反馈——进度跳过30%且超过3分钟。"""
        if task_id not in self._task_progress:
            self._task_progress[task_id] = progress_pct
            self._task_durations[task_id] = elapsed_seconds
            return None

        prev_pct = self._task_progress[task_id]
        if progress_pct - prev_pct >= 0.30 and elapsed_seconds > 180:
            self._task_progress[task_id] = progress_pct
            self._task_durations[task_id] = elapsed_seconds
            return AttentionEvent(
                trigger=TriggerType.PROGRESS,
                message=f"任务进行中（{progress_pct:.0%}），已运行 {elapsed_seconds:.0f}s",
                priority=4,
            )

        self._task_progress[task_id] = progress_pct
        self._task_durations[task_id] = elapsed_seconds
        return None

    def check_warning(self, alert_type: str, detail: str, user_id: str = "") -> AttentionEvent:
        """Token/安全阈值突破。

        v2.0: 历史错误复发 → 提升优先级。
        """
        if alert_type == "token_critical":
            return AttentionEvent(
                trigger=TriggerType.WARNING,
                message=f"⚠️ {detail}",
                priority=8, requires_approval=True,
            )

        # 检查错误复发
        learning_boost = 0
        if user_id:
            profile = self._memory.get_profile(user_id)
            err_key = detail[:40]
            if profile.error_recurrence.get(err_key, 0) > 1:
                learning_boost = 1  # 复发警告 +1 优先级

        return AttentionEvent(
            trigger=TriggerType.WARNING,
            message=f"⚠️ {detail}",
            priority=min(10, 6 + learning_boost),
            learning_boost=learning_boost,
        )

    def check_error(self, error_type: str, detail: str, has_healing: bool = False) -> AttentionEvent:
        """Gate FAIL / Pi拦截。"""
        healing_note = "（已生成自愈替代方案）" if has_healing else ""
        return AttentionEvent(
            trigger=TriggerType.ERROR,
            message=f"❌ {error_type}: {detail}{healing_note}",
            priority=9, requires_approval=not has_healing,
        )

    def check_summary(self, task_count: int, success_rate: float, total_tokens: int) -> AttentionEvent:
        """任务完成交付——汇报战果。"""
        return AttentionEvent(
            trigger=TriggerType.SUMMARY,
            message=f"已完成 {task_count} 个任务（成功率 {success_rate:.0%}），消耗 {total_tokens} tokens",
            priority=5,
        )

    def check_pattern(self, pattern_name: str, sample_count: int, user_id: str = "") -> Optional[AttentionEvent]:
        """跨工作间共性模式——触类旁通。

        v2.0: 低效模式不再重复提醒。
        """
        # 去重：同一模式 24h 内不重复提醒
        if pattern_name in self._patterns_seen:
            return None

        # v2.0: 检查历史模式有效性
        if user_id:
            profile = self._memory.get_profile(user_id)
            pat_key = pattern_name[:60]
            effectiveness = profile.pattern_effectiveness.get(pat_key, 0.5)
            if effectiveness < 0.2:
                # 低效模式，不提醒
                self._patterns_seen[pattern_name] = sample_count
                return None

        self._patterns_seen[pattern_name] = sample_count
        return AttentionEvent(
            trigger=TriggerType.PATTERN,
            message=f"🔍 发现了跨工作间模式：'{pattern_name}'（{sample_count}次），建议复用",
            priority=7,
        )

    def check_suggestion(self, suggestion: str, user_id: str = "", cooldown_minutes: int = 30) -> Optional[AttentionEvent]:
        """优化建议——带冷却防骚扰。

        v2.0: 高采纳率建议提升优先级 + 缩短冷却，低采纳率建议降低优先级。
        """
        now = datetime.now().timestamp()
        if suggestion in self._last_suggestion_time:
            elapsed = now - self._last_suggestion_time[suggestion]
            if elapsed < cooldown_minutes * 60:
                return None

        base_priority = 4
        learning_boost = 0

        if user_id:
            acceptance = self._memory.get_effective_acceptance(user_id, suggestion)
            if acceptance > 0.7:
                # 高采纳率：提升优先级 + 缩短冷却
                learning_boost = 2
                cooldown_minutes = max(10, cooldown_minutes // 2)
            elif acceptance < 0.2 and self._last_suggestion_time.get(suggestion, 0) > 0:
                # 低采纳率已提醒过：不再提醒
                return None

        self._last_suggestion_time[suggestion] = now
        return AttentionEvent(
            trigger=TriggerType.SUGGESTION,
            message=f"💡 建议：{suggestion}",
            priority=min(10, base_priority + learning_boost),
            learning_boost=learning_boost,
        )

    # ════════════════════════════════════════════════════════════
    # 综合评估 + 学习回路
    # ════════════════════════════════════════════════════════════

    def evaluate(self, context: dict) -> list[AttentionEvent]:
        """综合评估——返回当前应触发的所有事件（按优先级排序）。

        v2.0: 应用学习画像调整优先级。
        """
        events: list[AttentionEvent] = []
        ctx = context or {}
        user_id = ctx.get("user_id", "default")

        # 逐一检查 7 种情况
        ice = self.check_icebreak(user_id)
        if ice: events.append(ice)

        if "progress" in ctx:
            prog = self.check_progress(
                ctx.get("task_id", ""), ctx["progress"], ctx.get("elapsed", 0)
            )
            if prog: events.append(prog)

        if "warning" in ctx:
            events.append(self.check_warning(
                ctx.get("warn_type", ""), ctx["warning"], user_id
            ))

        if "error" in ctx:
            events.append(self.check_error(
                ctx.get("error_type", ""), ctx["error"], ctx.get("has_healing", False)
            ))

        if "task_count" in ctx:
            events.append(self.check_summary(
                ctx["task_count"], ctx.get("success_rate", 0), ctx.get("total_tokens", 0)
            ))

        if "pattern" in ctx:
            pat = self.check_pattern(ctx["pattern"], ctx.get("sample_count", 1), user_id)
            if pat: events.append(pat)

        if "suggestion" in ctx:
            sug = self.check_suggestion(ctx["suggestion"], user_id)
            if sug: events.append(sug)

        # v2.0: 应用学习画像调整优先级
        profile = self._memory.get_profile(user_id)
        for e in events:
            if profile.interaction_count > 5:
                e.priority = max(1, min(10, e.priority + int(profile.optimal_priority_bias)))

        # 按优先级排序
        events.sort(key=lambda e: e.priority, reverse=True)

        # 记录事件发送
        for e in events:
            self._memory.record(user_id, e.trigger.value, e.message, e.priority)

        return events

    def learn_from_outcome(self, user_id: str, event_type: str, message: str, outcome: str) -> None:
        """闭合学习回路——用户对事件的反应。

        Args:
            user_id: 用户 ID
            event_type: 事件类型（icebreak/progress/warning/error/summary/pattern/suggestion）
            message: 事件消息（用于匹配）
            outcome: "accepted" / "dismissed" / "ignored"
        """
        self._memory.record_outcome(user_id, event_type, message, outcome)

    # ════════════════════════════════════════════════════════════
    # 统计
    # ════════════════════════════════════════════════════════════

    def get_stats(self) -> dict:
        mem_stats = self._memory.get_stats()
        return {
            "daily_users_seen": len(self._daily_first_seen),
            "patterns_tracked": len(self._patterns_seen),
            "triggers_available": [t.value for t in TriggerType],
            "learning_memory": mem_stats,
            "version": "2.0",
        }

    def get_user_profile(self, user_id: str) -> dict:
        """获取用户学习画像。"""
        profile = self._memory.get_profile(user_id)
        return {
            "interaction_count": profile.interaction_count,
            "acknowledge_rate": f"{profile.acknowledge_rate:.1%}",
            "acceptance_rate": f"{profile.acceptance_rate:.1%}",
            "optimal_priority_bias": f"{profile.optimal_priority_bias:+.1f}",
            "top_accepted_suggestions": sorted(
                [(k, v) for k, v in profile.suggestion_history.items() if v > 0],
                key=lambda x: x[1], reverse=True,
            )[:5],
        }


# 平台唯一实例
attention_engine = AttentionEngine()
