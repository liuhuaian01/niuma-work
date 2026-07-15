"""降级链管理器

太极引擎 Phase 2 / v2.0: Smart Allocator + DynamicDegradationEngine 驱动降级。
降级链不再硬编码——委托 DynamicDegradationEngine 动态构建最优降级路径。

保留 settings.FALLBACK_CHAIN 作为最后的静态兜底（理论上不会走到这里）。
"""

import asyncio
import time
from typing import Optional

from model_adapter.base import AbstractModelAdapter
from model_adapter.registry import model_registry
from config.settings import settings
from engine.dynamic_degradation import dynamic_degradation
from engine.fallback_cost import FallbackCostAnalyzer


class FallbackManager:
    """降级链管理器

    v2.0: get_available_model 改用 DynamicDegradationEngine 动态降级路径，
          不再线性遍历 settings.FALLBACK_CHAIN。
    """

    def __init__(self):
        self._static_chain: list[str] = settings.FALLBACK_CHAIN.copy()
        self._failure_tracker: dict[str, list] = {}
        self._max_consecutive_failures = 3
        self._disable_duration = 1800  # 30 分钟
        self._quota_exhausted: set[str] = set()   # Token 用完（不是故障，是余额不足）
        self._fallback_cost = FallbackCostAnalyzer()
        # 确保动态降级引擎已初始化
        if not dynamic_degradation._initialized:
            dynamic_degradation.register_known_models()

    def record_success(self, model_name: str):
        """记录模型调用成功，重置失败计数"""
        if model_name in self._failure_tracker:
            self._failure_tracker[model_name] = [0, 0]
        self._quota_exhausted.discard(model_name)
        # 同步到 DynamicDegradationEngine
        dynamic_degradation.record_quality(model_name, "", 0.8, success=True)

    def record_failure(self, model_name: str):
        """记录模型调用失败"""
        if model_name not in self._failure_tracker:
            self._failure_tracker[model_name] = [0, 0]

        self._failure_tracker[model_name][0] += 1
        self._failure_tracker[model_name][1] = time.time()

        if self._failure_tracker[model_name][0] >= self._max_consecutive_failures:
            model_registry.disable_model(model_name)

    def record_quota_exhausted(self, model_name: str):
        """标记模型 Token 已用完。"""
        self._quota_exhausted.add(model_name)

    def is_quota_exhausted(self, model_name: str) -> bool:
        return model_name in self._quota_exhausted

    def is_model_disabled(self, model_name: str) -> bool:
        """检查模型是否被禁用（考虑过期恢复）"""
        if model_name not in self._failure_tracker:
            return False

        failures, last_failure = self._failure_tracker[model_name]
        if failures < self._max_consecutive_failures:
            return False

        # 检查禁用是否过期
        if time.time() - last_failure > self._disable_duration:
            model_registry.enable_model(model_name)
            self._failure_tracker[model_name] = [0, 0]
            return False

        return True

    async def get_available_model(
        self, preferred: str | None = None, task_type: str = "general"
    ) -> tuple[Optional[AbstractModelAdapter], Optional[str]]:
        """按动态降级路径获取可用模型。

        v2.0: 不再线性遍历 settings.FALLBACK_CHAIN。
              改用 DynamicDegradationEngine 构建任务感知的动态降级路径。

        Args:
            preferred: 首选模型名称
            task_type: 任务类型（影响降级路径选择）

        Returns:
            (adapter, actual_model_name)
            (None, None) — 所有模型不可用
        """
        # 1) 用 DynamicDegradationEngine 生成降级路径
        #    将 model_registry 里的 registry_name 映射回内部 ID
        internal_preferred = None
        if preferred:
            for mid, m in {m.model_id: m for m in dynamic_degradation.list_all_models()}.items():
                if m.registry_name == preferred or m.model_id == preferred:
                    internal_preferred = mid
                    break

        path = dynamic_degradation.build_degradation_path(
            task_type=task_type,
            budget_remaining=50000,  # 预算充足——fallback 场景先保可用
            priority=0.6,
            preferred_model=internal_preferred,
        )

        # 2) 按降级路径遍历（首选 + 降级步骤）
        tried = set()
        for model_id in path.all_model_ids:
            # 获取 registry_name
            cap = dynamic_degradation.get_model(model_id)
            registry_name = cap.registry_name if cap else model_id

            if registry_name in tried:
                continue
            tried.add(registry_name)

            # 跳过已禁用的
            if self.is_model_disabled(registry_name):
                continue

            adapter = model_registry.get(registry_name)
            if adapter:
                try:
                    available = await adapter.is_available()
                    if available:
                        return adapter, registry_name
                except Exception:
                    continue

        # 3) 兜底——尝试 settings.FALLBACK_CHAIN
        for model_name in self._static_chain:
            if model_name in tried:
                continue
            if model_registry.is_disabled(model_name):
                self.is_model_disabled(model_name)
                adapter = model_registry.get(model_name)
                if adapter:
                    return adapter, model_name
                continue
            try:
                adapter = model_registry.get(model_name)
                if adapter and await adapter.is_available():
                    return adapter, model_name
            except Exception:
                continue

        return None, None

    async def get_allocator_preferred_model(
        self, recommended: str, task_type: str = "general"
    ) -> tuple[Optional[AbstractModelAdapter], Optional[str]]:
        """太极引擎 v2.0: 优先使用 Smart Allocator 推荐的模型。
        若推荐模型不可用，委托 DynamicDegradationEngine 动态降级。
        """
        return await self.get_available_model(preferred=recommended, task_type=task_type)

    def get_fallback_info(self) -> dict:
        """获取降级链状态信息"""
        info = {}
        for model_name in self._static_chain:
            disabled = self.is_model_disabled(model_name)
            failures = self._failure_tracker.get(model_name, [0, 0])
            info[model_name] = {
                "disabled": disabled,
                "consecutive_failures": failures[0],
                "last_failure": failures[1],
                "quota_exhausted": self.is_quota_exhausted(model_name),
            }
        return info


# 全局单例
fallback_manager = FallbackManager()
