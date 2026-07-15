"""
模型注册中心 + 降级链管理

降级链: DeepSeek → Kimi → 混元 → GLM
连续失败3次自动禁用5分钟
"""

from typing import Optional

from model_adapter.base import AbstractModelAdapter
from model_adapter.openai_compat import create_adapters, OpenAICompatAdapter
from config.settings import settings


class ModelRegistry:
    """模型注册中心"""

    def __init__(self):
        self._adapters: dict[str, OpenAICompatAdapter] = {}
        self._fallback_chain: list[str] = settings.FALLBACK_CHAIN.copy()
        self._initialized = False

    def initialize(self):
        """初始化所有模型适配器"""
        if self._initialized:
            return
        self._adapters = create_adapters()
        self._initialized = True

    def register(self, adapter: AbstractModelAdapter):
        """注册模型适配器"""
        self._adapters[adapter.model_name] = adapter

    def get(self, model_name: str) -> Optional[OpenAICompatAdapter]:
        """获取模型适配器"""
        if not self._initialized:
            self.initialize()
        return self._adapters.get(model_name)

    async def get_available(self, preferred: str | None = None) -> Optional[OpenAICompatAdapter]:
        """按降级链获取首个可用模型

        Args:
            preferred: 首选模型名称

        Returns:
            第一个可用的模型适配器，None 表示全部不可用
        """
        if not self._initialized:
            self.initialize()

        # 构建尝试顺序
        chain = list(self._fallback_chain)
        if preferred and preferred in self._adapters:
            # 首选模型放到最前面
            if preferred in chain:
                chain.remove(preferred)
            chain.insert(0, preferred)

        # 按顺序找第一个可用的
        for model_name in chain:
            adapter = self._adapters.get(model_name)
            if adapter and await adapter.is_available():
                return adapter

        return None

    def get_fallback_info(self, requested: str, actual: str) -> dict | None:
        """获取降级信息"""
        if requested == actual:
            return None
        adapter = self._adapters.get(actual)
        return {
            "requested_model": requested,
            "fallback_model": actual,
            "fallback_display_name": adapter.display_name if adapter else actual,
        }

    def list_models_status(self) -> list[dict]:
        """列出所有模型状态"""
        if not self._initialized:
            self.initialize()
        result = []
        for name, adapter in self._adapters.items():
            result.append({
                "id": name,
                "display_name": adapter.display_name,
                "configured": adapter.is_configured,
                "fail_count": adapter.fail_count,
                "max_context": adapter.max_context,
            })
        return result

    def disable_model(self, model_name: str):
        """临时禁用模型（连续失败3次后调用）"""
        adapter = self._adapters.get(model_name)
        if adapter:
            adapter._fail_count = 3
            adapter._last_fail_time = __import__("time").time()

    def enable_model(self, model_name: str):
        """重新启用模型"""
        adapter = self._adapters.get(model_name)
        if adapter:
            adapter._fail_count = 0


# 全局单例
model_registry = ModelRegistry()
