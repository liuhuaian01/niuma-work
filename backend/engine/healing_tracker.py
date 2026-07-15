"""
太极引擎 · 自愈效果追踪

自愈回路生成的替代方案有没有真的帮到 Agent？
追踪每次自愈后的重试成功率。
长期无效的替代方案自动废弃。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class HealingRecord:
    event_type: str
    original_error: str
    suggestion: str
    retry_result: str = "unknown"   # "succeeded" / "failed" / "not_retried"
    retry_after_ms: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class HealingTracker:
    """自愈效果追踪。

    每次 SelfHealing 生成替代方案后：
    1. 记录原始错误 + 建议
    2. Agent 重试
    3. 记录重试结果
    4. 长期成功率 < 30% 的替代方案 → 废弃
    """

    HEALING_MIN_SUCCESS_RATE = 0.30    # 低于30% → 废弃该规则

    def __init__(self) -> None:
        self._records: list[HealingRecord] = []
        self._rule_success: dict[str, list[bool]] = {}   # rule → [True, False, ...]

    def record(self, event_type: str, error: str, suggestion: str) -> str:
        """记录一次自愈事件。返回记录 ID。"""
        record = HealingRecord(
            event_type=event_type, original_error=error, suggestion=suggestion,
        )
        self._records.append(record)
        return suggestion  # 返回给 Agent 的建议

    def record_result(self, suggestion: str, success: bool) -> None:
        """记录重试结果。"""
        for r in reversed(self._records):
            if r.suggestion == suggestion and r.retry_result == "unknown":
                r.retry_result = "succeeded" if success else "failed"
                break
        # 更新规则成功率
        rule_key = suggestion[:60]
        if rule_key not in self._rule_success:
            self._rule_success[rule_key] = []
        self._rule_success[rule_key].append(success)

    def is_rule_effective(self, rule: str) -> bool:
        """判断一条自愈规则是否仍然有效。"""
        key = rule[:60]
        results = self._rule_success.get(key, [])
        if len(results) < 3:
            return True  # 样本不足，先保留
        rate = sum(results) / len(results)
        return rate >= self.HEALING_MIN_SUCCESS_RATE

    def get_deprecated_rules(self) -> list[str]:
        """获取应废弃的规则列表。"""
        return [k for k in self._rule_success if not self.is_rule_effective(k)]

    def get_healing_effectiveness(self) -> dict:
        """自愈整体效果。"""
        all_results = [r for rs in self._rule_success.values() for r in rs]
        if not all_results:
            return {"retry_count": 0, "success_rate": 0, "active_rules": 0}
        return {
            "retry_count": len(all_results),
            "success_rate": round(sum(all_results) / len(all_results), 3),
            "active_rules": len(self._rule_success) - len(self.get_deprecated_rules()),
            "deprecated_rules": len(self.get_deprecated_rules()),
        }

    def get_stats(self) -> dict:
        return {
            "total_events": len(self._records),
            "retried": sum(1 for r in self._records if r.retry_result != "unknown"),
            "succeeded": sum(1 for r in self._records if r.retry_result == "succeeded"),
            "failed": sum(1 for r in self._records if r.retry_result == "failed"),
        }


healing_tracker = HealingTracker()
