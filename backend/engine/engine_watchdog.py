"""
太极引擎 · 引擎自愈守卫（Engine Watchdog）

不是只修复用户任务的 self_healing——
是修复太极引擎自身模块的故障。

机制：
  熔断器 — 连续失败 N 次自动跳过该模块，每隔 T 秒探测恢复
  降级链 — 模块不可用时用保守默认值接管
  回滚器 — 数据损坏时恢复到上一次已知良好状态
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional


class CircuitState(Enum):
    CLOSED = "closed"            # 正常——调用模块
    OPEN = "open"                # 熔断——跳过模块，用降级值
    HALF_OPEN = "half_open"      # 半开——尝试一次探测调用


@dataclass
class ModuleHealth:
    module_name: str
    circuit_state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    total_failures: int = 0
    last_failure_time: str = ""
    last_failure_error: str = ""
    last_success_time: str = ""
    last_recovery_action: str = ""


class EngineWatchdog:
    """太极引擎自身守卫——监控每个引擎模块的健康状态。

    规则：
      - 连续失败 3 次 → 熔断（OPEN），跳过该模块
      - 熔断 30 秒后 → 半开（HALF_OPEN），尝试一次探测
      - 探测成功 → 闭合（CLOSED），恢复正常
      - 探测失败 → 重新熔断（OPEN），再等 30 秒
    """

    MAX_CONSECUTIVE_FAILURES = 3
    CIRCUIT_BREAK_TIMEOUT = 30        # 熔断 30 秒后尝试恢复

    def __init__(self) -> None:
        self._health: dict[str, ModuleHealth] = {}

    def _get(self, module_name: str) -> ModuleHealth:
        if module_name not in self._health:
            self._health[module_name] = ModuleHealth(module_name=module_name)
        return self._health[module_name]

    def record_success(self, module_name: str) -> None:
        """记录模块调用成功。"""
        h = self._get(module_name)
        h.consecutive_failures = 0
        h.circuit_state = CircuitState.CLOSED
        h.last_success_time = datetime.now().isoformat()

    def record_failure(self, module_name: str, error: str) -> tuple[bool, str]:
        """记录模块调用失败。返回 (是否应熔断, 建议降级策略)。"""
        h = self._get(module_name)
        h.consecutive_failures += 1
        h.total_failures += 1
        h.last_failure_time = datetime.now().isoformat()
        h.last_failure_error = error

        # P1: HALF_OPEN 状态下一次失败应立即回 OPEN（标准断路器模式）
        if h.circuit_state == CircuitState.HALF_OPEN:
            h.circuit_state = CircuitState.OPEN
            h.last_recovery_action = (
                f"半开探测失败——一次失败即回熔断（{h.last_failure_error[:100]}），30秒后尝试恢复"
            )
            return True, h.last_recovery_action

        if h.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            h.circuit_state = CircuitState.OPEN
            h.last_recovery_action = f"熔断——连续 {h.consecutive_failures} 次失败，30秒后尝试恢复"
            return True, h.last_recovery_action

        return False, ""

    def should_call(self, module_name: str) -> tuple[bool, str]:
        """判断是否应该调用该模块。返回 (是否应调用, 原因)。"""
        h = self._get(module_name)

        if h.circuit_state == CircuitState.CLOSED:
            return True, ""

        if h.circuit_state == CircuitState.OPEN:
            # 检查熔断是否过期
            try:
                fail_time = datetime.fromisoformat(h.last_failure_time)
                if (datetime.now() - fail_time).total_seconds() >= self.CIRCUIT_BREAK_TIMEOUT:
                    h.circuit_state = CircuitState.HALF_OPEN
                    return True, "半开探测——尝试恢复"
            except (ValueError, TypeError):
                pass
            return False, f"熔断中——{h.last_recovery_action}"

        # HALF_OPEN — 允许一次探测
        return True, ""

    def attempt_recovery(self, module_name: str, recovery_fn: Callable) -> Optional[Any]:
        """尝试恢复一个模块。传入恢复函数，成功则闭合，失败则重新熔断。"""
        try:
            result = recovery_fn()
            self.record_success(module_name)
            return result
        except Exception as e:
            self.record_failure(module_name, str(e))
            return None

    def get_health_report(self) -> dict:
        """获取所有模块的健康报告。"""
        return {
            name: {
                "state": h.circuit_state.value,
                "consecutive_failures": h.consecutive_failures,
                "total_failures": h.total_failures,
                "last_failure": h.last_failure_error[:100] if h.last_failure_error else "",
                "last_recovery": h.last_recovery_action,
            }
            for name, h in self._health.items()
        }

    def get_stats(self) -> dict:
        total = len(self._health)
        healthy = sum(1 for h in self._health.values() if h.circuit_state == CircuitState.CLOSED)
        return {
            "modules_tracked": total,
            "healthy": healthy,
            "circuit_broken": total - healthy,
            "details": self.get_health_report(),
        }


# 平台唯一实例
watchdog = EngineWatchdog()
