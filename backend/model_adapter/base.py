"""
模型适配器抽象基类

Phase 1: 接口定义（暂不实现）
Phase 2: 接入 DeepSeek / Kimi / 混元 / GLM
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator


class AbstractModelAdapter(ABC):
    """模型适配器抽象基类"""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """模型标识名称"""
        ...

    @property
    @abstractmethod
    def api_base_url(self) -> str:
        """API 基础地址"""
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> dict:
        """同步对话（一次性返回完整响应）"""
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """流式对话（逐个 token 返回）"""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """检查模型是否可用"""
        ...
