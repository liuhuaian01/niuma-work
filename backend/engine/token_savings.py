"""
太极引擎 · Token 节约引擎（Token Savings）

量化为证——不用 Smart Allocator 会花多少？用了省了多少？
核心卖点的自证能力。

算法:
  基线预算 = 该任务类型在所有可用模型上的平均历史消耗（未优化时）
  实际消耗 = Smart Allocator 推荐模型下的实际消耗
  节约量   = 基线 - 实际
  节约率   = 节约量 / 基线

  日/周报告:
    总节约 = ∑ 每天每个任务的节约量
    节超比 = 实际 / 基线（<1 省钱, >1 超支）
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from typing import Optional
from utils import is_new_day


@dataclass
class SavingsRecord:
    task_type: str
    baseline_tokens: int       # 如果没用 Smart Allocator，预计消耗
    actual_tokens: int         # 实际消耗
    saved: int                 # 节约量 = baseline - actual
    savings_rate: float        # 节约率 = saved / baseline
    model_used: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DailySavingsReport:
    date: str
    total_tasks: int
    total_baseline: int
    total_actual: int
    total_saved: int           # 省下的 Token
    savings_rate: float        # 整体节约率
    by_task_type: dict = field(default_factory=dict)
    trend: str = ""            # "⬆️ 越来越省" / "➡️ 持平" / "⬇️ 效率下降"


class SavingsEngine:
    """Token 节约度量引擎。

    冷启动: 前 5 次不计算 (no baseline)，从第 6 次开始计算对比。
    """

    COLD_START_THRESHOLD = 10  # 最少10次有效执行才计算基线（原来5次→1个数据点算基线没意义）

    def __init__(self) -> None:
        _, self._today = is_new_day("")  # 初始化为今天
        self._records: list[SavingsRecord] = []
        self._history: dict[str, list[int]] = defaultdict(list)

    def _reset_if_new_day(self) -> None:
        is_new, self._today = is_new_day(self._today)
        if is_new:
            self._records = []

    def learn_baseline(self, task_type: str, tokens_used: int) -> None:
        """积累历史数据，形成基线。冷启动期之后才有效。"""
        self._history[task_type].append(tokens_used)
        if len(self._history[task_type]) > 30:
            self._history[task_type] = self._history[task_type][-30:]

    def record_execution(
        self, task_type: str, actual_tokens: int, model_used: str = "unknown"
    ) -> Optional[SavingsRecord]:
        """记录一次执行并计算节约。冷启动期内返回 None。"""
        self._reset_if_new_day()
        self.learn_baseline(task_type, actual_tokens)

        history = self._history.get(task_type, [])
        if len(history) < self.COLD_START_THRESHOLD:
            return None  # 冷启动——样本太少，基线不具统计意义

        # 基线 = 排除最近30%样本的历史中位数（中位数比平均数更抗异常值）
        exclude = max(1, len(history) // 3)
        sorted_history = sorted(history[:-exclude])
        if not sorted_history:
            return None
        midpoint = len(sorted_history) // 2
        baseline = sorted_history[midpoint] if len(sorted_history) % 2 == 1 else (sorted_history[midpoint-1] + sorted_history[midpoint]) // 2
        saved = baseline - actual_tokens
        rate = saved / baseline if baseline > 0 else 0

        record = SavingsRecord(
            task_type=task_type, baseline_tokens=baseline,
            actual_tokens=actual_tokens, saved=saved,
            savings_rate=rate, model_used=model_used,
        )
        self._records.append(record)
        return record

    def daily_report(self) -> DailySavingsReport:
        """今日节约报告——核心卖点自证。"""
        self._reset_if_new_day()
        if not self._records:
            return DailySavingsReport(
                date=self._today, total_tasks=0, total_baseline=0,
                total_actual=0, total_saved=0, savings_rate=0,
                trend="冷启动阶段, 数据积累中",
            )

        total_baseline = sum(r.baseline_tokens for r in self._records)
        total_actual = sum(r.actual_tokens for r in self._records)
        total_saved = sum(r.saved for r in self._records)
        rate = total_saved / total_baseline if total_baseline > 0 else 0

        by_type = defaultdict(lambda: {"tasks": 0, "saved": 0, "rate": 0.0})
        for r in self._records:
            bt = by_type[r.task_type]
            bt["tasks"] += 1
            bt["saved"] += r.saved
            bt["rate"] = bt["saved"] / (r.baseline_tokens * bt["tasks"]) if r.baseline_tokens > 0 else 0

        if rate > 0.3:
            trend = "⬆️ Smart Allocator 显著降低 Token 消耗"
        elif rate > 0:
            trend = "⬆️ 持续优化中"
        elif rate == 0:
            trend = "➡️ 持平"
        else:
            trend = "⬇️ 今日消耗略高于预期，可能是新任务类型"

        return DailySavingsReport(
            date=self._today, total_tasks=len(self._records),
            total_baseline=total_baseline, total_actual=total_actual,
            total_saved=total_saved, savings_rate=round(rate, 3),
            by_task_type=dict(by_type), trend=trend,
        )

    def get_stats(self) -> dict:
        report = self.daily_report()
        return {
            "today": report.date,
            "tasks": report.total_tasks,
            "saved_tokens": report.total_saved,
            "savings_rate": f"{report.savings_rate:.1%}",
            "trend": report.trend,
            "cold_start_active": sum(len(v) for v in self._history.values()) < self.COLD_START_THRESHOLD,
            "by_task_type": report.by_task_type,
        }


# 平台唯一实例
savings_engine = SavingsEngine()
