"""
太极引擎 · 智能资源调度器（Smart Allocator）

四两拨千斤——力点探测 → 精准分配 → 执行监控 → 降级/提升。

v2.0: 模型信息不再硬编码，委托 DynamicDegradationEngine 动态决策。
      probe() 返回完整的降级路径，而非单一推荐模型。
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from utils import is_new_day
from engine.allocator_repository import AllocatorRepository
from engine.dynamic_degradation import dynamic_degradation, DegradationPath


class TaskType(Enum):
    WRITING = "writing"
    CODING = "coding"
    ANALYSIS = "analysis"
    SEARCH = "search"
    CONVERSATION = "conversation"

    @classmethod
    def from_string(cls, s: str) -> "TaskType":
        try:
            return cls(s.lower())
        except ValueError:
            return cls.CONVERSATION


class BudgetLevel(Enum):
    HIGH = "high"
    STANDARD = "standard"
    LOW = "low"


class TaskUrgency(Enum):
    """v1.9: 任务紧急程度——用于峰谷定价错峰调度。"""
    IMMEDIATE = "immediate"    # 立即执行（用户正在等待）
    BATCH = "batch"            # 批量任务（可延迟几分钟）
    BACKGROUND = "background"  # 后台任务（可延迟到非高峰）


@dataclass
class ForceProbeInput:
    task_type: TaskType
    budget_remaining: int
    user_priority: float = 0.5
    runtime_mode: Optional[str] = None  # "local" / "cloud" / "hybrid" — 来自 DynamicBalancer
    urgency: TaskUrgency = TaskUrgency.IMMEDIATE  # v1.9: 任务紧急程度
    peak_pricing: bool = False                     # v1.9: 是否处于 API 高峰定价时段


@dataclass
class ForceProbeResult:
    task_type: TaskType
    budget_level: BudgetLevel
    recommended_model: str
    reason: str
    estimated_tokens: int
    confidence: float = 0.5
    degradation_path: Optional[dict] = None  # 完整的降级路径信息
    defer_to_offpeak: bool = False            # v1.9: 是否建议错峰执行
    estimated_saving: float = 0.0             # v1.9: 错峰预计节省成本（美元）


def get_registry_name(model_id: str) -> str:
    """获取模型在 ModelRegistry 中的实际名称——委托 DynamicDegradationEngine。"""
    return dynamic_degradation.get_registry_name(model_id) or model_id


# 默认每日预算上限
DEFAULT_DAILY_BUDGETS: dict[TaskType, int] = {
    TaskType.CODING:        50000,
    TaskType.ANALYSIS:      40000,
    TaskType.WRITING:       30000,
    TaskType.SEARCH:        15000,
    TaskType.CONVERSATION:  10000,
}

# 综合得分权重
SCORE_WEIGHTS = {"priority": 0.4, "roi": 0.35, "budget": 0.25}


class SmartAllocator:
    """智能资源调度器。

    v2.0: 模型推荐委托 DynamicDegradationEngine 动态决策。
          probe() 返回的 ForceProbeResult 包含完整降级路径。

    使用方式:
        allocator = SmartAllocator(db_path)
        result = allocator.probe(ForceProbeInput(TaskType.WRITING, 25000, 0.8))
        # → HIGH budget, deepseek-v4, 30000 tokens, degradation_path=[...]
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path
        self._repo: Optional[AllocatorRepository] = None
        self._history: dict[TaskType, tuple[int, int, float]] = {}
        self._today_token_usage: dict[str, int] = {}
        _, self._today_date = is_new_day("")
        # 确保动态降级引擎已初始化
        if not dynamic_degradation._initialized:
            dynamic_degradation.register_known_models()
        if db_path:
            self._init_repo_sync()

    def _init_repo_sync(self) -> None:
        """同步初始化Repository（兼容现有同步调用）"""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._async_init())
        except RuntimeError:
            asyncio.run(self._async_init())

    async def _async_init(self) -> None:
        """异步初始化Repository"""
        if self._repo is None:
            self._repo = AllocatorRepository()
            await self._repo.init_tables()
            self._history = await self._load_history_async()

    async def _load_history_async(self) -> dict[TaskType, tuple[int, int, float]]:
        """异步加载历史记录"""
        if not self._repo:
            return {}
        raw_history = await self._repo.load_history()
        history = {}
        for tt_value, data in raw_history.items():
            try:
                tt = TaskType(tt_value)
                history[tt] = data
            except ValueError:
                continue
        return history

    async def _save_history_async(self, task_type: TaskType) -> None:
        """异步保存历史记录"""
        if not self._repo:
            return
        hist = self._history.get(task_type)
        if not hist:
            return
        avg_tokens, total_tasks, avg_quality = hist
        await self._repo.save_history(
            task_type.value, avg_tokens, total_tasks, avg_quality
        )

    def record_execution(
        self, task_type: TaskType, tokens_used: int, quality_score: float,
        agent_id: str = "default", model_used: str = "",
    ) -> None:
        """记录一次任务执行结果。用于持续学习。

        v2.0: 同时记录到 DynamicDegradationEngine 的质量学习。
        """
        if task_type in self._history:
            old_tokens, old_count, old_quality = self._history[task_type]
            new_count = old_count + 1
            new_tokens = int((old_tokens * old_count + tokens_used) / new_count)
            new_quality = (old_quality * old_count + quality_score) / new_count
        else:
            new_count, new_tokens, new_quality = 1, tokens_used, quality_score
        self._history[task_type] = (new_tokens, new_count, new_quality)

        # 异步保存（后台任务）
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._save_history_async(task_type))
        except RuntimeError:
            asyncio.run(self._save_history_async(task_type))

        # 更新今日用量
        is_new, self._today_date = is_new_day(self._today_date)
        if is_new:
            self._today_token_usage = {}
        key = f"{agent_id}:{task_type.value}"
        self._today_token_usage[key] = self._today_token_usage.get(key, 0) + tokens_used

        # 异步记录每日用量
        if self._repo:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    self._repo.record_daily_usage(self._today_date, key, tokens_used)
                )
            except RuntimeError:
                asyncio.run(
                    self._repo.record_daily_usage(self._today_date, key, tokens_used)
                )

        # v2.0: 同步质量到 DynamicDegradationEngine
        if model_used:
            dynamic_degradation.record_quality(
                model_id=model_used,
                task_type=task_type.value,
                quality_score=quality_score,
                success=True,
            )

    def get_budget_remaining(self, task_type: TaskType, agent_id: str = "default") -> int:
        """获取某个 Agent 在某个任务类型上的今日剩余预算。"""
        daily = DEFAULT_DAILY_BUDGETS.get(task_type, 20000)
        is_new, self._today_date = is_new_day(self._today_date)
        if is_new:
            return daily
        key = f"{agent_id}:{task_type.value}"
        used = self._today_token_usage.get(key, 0)
        return max(0, daily - used)

    def probe(self, input_data: ForceProbeInput) -> ForceProbeResult:
        """力点探测——四两拨千斤的核心算法。

        v2.0: 委托 DynamicDegradationEngine 动态决策模型选择，
              不再依赖硬编码 MODEL_INFO。

        决策流程：
          1. 先用历史 ROI + 优先级 + 预算 决定预算级别
          2. 委托 DynamicDegradationEngine 构建降级路径
          3. 将完整路径信息嵌入 ForceProbeResult
        """
        task_type = input_data.task_type
        daily_budget = DEFAULT_DAILY_BUDGETS.get(task_type, 20000)
        budget_ratio = input_data.budget_remaining / daily_budget if daily_budget > 0 else 0
        priority = input_data.user_priority

        hist = self._history.get(task_type)

        # ============================================================
        # 第一步：确定预算级别（BudgetLevel）
        # ============================================================

        if hist is None or hist[1] == 0:
            budget_level = BudgetLevel.STANDARD
            estimated = daily_budget // 2
            confidence = 0.3
        else:
            hist_tokens, task_count, avg_quality = hist

            # ROI + 优先级 + 预算综合评分
            raw_roi = avg_quality / max(hist_tokens / 10000, 1)
            normalized_roi = min(1.0, max(0.0, raw_roi))
            score = (
                priority * SCORE_WEIGHTS["priority"]
                + normalized_roi * SCORE_WEIGHTS["roi"]
                + budget_ratio * SCORE_WEIGHTS["budget"]
            )

            # runtime_mode 影响得分
            runtime_mode = input_data.runtime_mode
            if runtime_mode == "local":
                score += 0.1
            elif runtime_mode == "cloud":
                score -= 0.1

            # 边界规则：低优先级 + 预算紧张
            if priority < 0.3 and budget_ratio < 0.4:
                budget_level = BudgetLevel.LOW
                estimated = min(daily_budget // 5, 5000)
                confidence = 0.95
            elif task_type == TaskType.CONVERSATION and priority < 0.6:
                budget_level = BudgetLevel.LOW
                estimated = min(daily_budget // 5, 5000)
                confidence = 0.90
            elif score > 0.45 or (priority > 0.7 and avg_quality > (0.7 if task_type in (TaskType.CODING, TaskType.ANALYSIS) else 0.8)):
                budget_level = BudgetLevel.HIGH
                estimated = min(daily_budget, int(hist_tokens * 1.3))
                confidence = 0.85
            elif score > 0.25:
                budget_level = BudgetLevel.STANDARD
                estimated = min(daily_budget // 2, hist_tokens)
                confidence = 0.7
            else:
                budget_level = BudgetLevel.LOW
                estimated = min(daily_budget // 5, 5000)
                confidence = 0.9

        # ============================================================
        # 第二步：委托 DynamicDegradationEngine 选模型
        # ============================================================

        # 根据预算级别调整优先级因子（预算紧张时倾向廉价模型）
        adjusted_priority = priority
        if budget_level == BudgetLevel.LOW:
            adjusted_priority = priority * 0.6
        elif budget_level == BudgetLevel.HIGH:
            adjusted_priority = min(1.0, priority * 1.2)

        # 构建降级路径
        path = dynamic_degradation.build_degradation_path(
            task_type=task_type.value,
            budget_remaining=input_data.budget_remaining,
            priority=adjusted_priority,
        )

        if not path.primary_model:
            # 无可用模型——兜底
            return ForceProbeResult(
                task_type=task_type,
                budget_level=budget_level,
                recommended_model="",
                reason="无可用的模型",
                estimated_tokens=estimated,
                confidence=0.0,
                degradation_path=None,
            )

        # ============================================================
        # 第二步半: v1.9 峰谷错峰调度检测
        # ============================================================
        recommended = path.primary_model
        defer_to_offpeak = False
        estimated_saving = 0.0
        reason_parts = []

        if input_data.peak_pricing and input_data.urgency != TaskUrgency.IMMEDIATE:
            # 非紧急任务 + 高峰时段 → 建议错峰
            # 仅当推荐模型是 DeepSeek V4 系列（受峰谷定价影响）
            cloud_models = ("deepseek-v4-pro", "deepseek-v4-flash")
            if path.primary_model in cloud_models:
                # 错峰省 50%（高峰 2x → 非高峰 1x）
                estimated_saving = (path.estimated_tokens / 1000) * 0.002  # 粗略估算
                if input_data.urgency == TaskUrgency.BACKGROUND:
                    # 后台任务强烈建议错峰
                    defer_to_offpeak = True
                    reason_parts = [
                        f"高峰时段(2x定价) → 建议错峰至非高峰执行",
                        f"预计节省约 ${estimated_saving:.4f}",
                        f"或继续使用 {path.primary_model}（高峰价格）",
                    ]
                elif input_data.urgency == TaskUrgency.BATCH:
                    # 批量任务：提示但不强制
                    reason_parts = [
                        f"高峰时段(2x定价) → 可考虑错峰，预计节省 ${estimated_saving:.4f}",
                    ]

        if not defer_to_offpeak and not reason_parts:
            reason_parts = [
                f"Auto 模式推荐 {recommended}",
                f"预算级别: {budget_level.value}",
                f"信心: {path.confidence:.1%}",
            ]
            if path.steps:
                reason_parts.append(f"降级路径: {' → '.join(path.all_model_ids)}")

        return ForceProbeResult(
            task_type=task_type,
            budget_level=budget_level,
            recommended_model=recommended if not defer_to_offpeak else "",
            reason=" · ".join(reason_parts),
            estimated_tokens=path.estimated_tokens if budget_level != BudgetLevel.LOW else estimated,
            confidence=min(confidence, path.confidence),
            degradation_path={
                "primary": path.primary_model,
                "steps": [{"model": s.model_id, "loss": s.quality_loss, "reason": s.reason} for s in path.steps],
                "total_quality_loss": path.total_quality_loss,
                "confidence": path.confidence,
            },
            defer_to_offpeak=defer_to_offpeak,
            estimated_saving=round(estimated_saving, 6),
        )

    # ---- 与 FallbackManager 的集成接口 ----

    def recommend_model(self, task_type: TaskType, budget_remaining: int, priority: float) -> tuple[str, int]:
        """返回（推荐模型, 建议Token数）。供 FallbackManager 调用。"""
        result = self.probe(ForceProbeInput(task_type, budget_remaining, priority))
        return result.recommended_model, result.estimated_tokens

    def get_stats(self) -> dict:
        """获取分配器统计信息。"""
        return {
            "history": {k.value: {"avg_tokens": v[0], "tasks": v[1], "avg_quality": round(v[2], 2)}
                        for k, v in self._history.items()},
            "today_usage": dict(self._today_token_usage),
            "today_date": self._today_date,
        }
