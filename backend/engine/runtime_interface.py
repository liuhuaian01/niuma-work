"""
太极引擎 · Hermes 运行时接口层 (RuntimeInterface)

阶段三核心交付物：太极可脱离 Hermes 独立运行。
此模块定义抽象的运行时接口，Hermes 只是实现之一。

设计原则：
- 太极定义接口 → Hermes（或任意兼容运行时）实现
- 对太极而言 Hermes 是一个"可插拔的插件"
- 抽象层隔离 Hermes API 变更
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol
from enum import Enum


# ════════════════════════════════════════════════════════════════
# 运行时状态
# ════════════════════════════════════════════════════════════════

class RuntimeStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DEGRADED = "degraded"
    ERROR = "error"


@dataclass
class RuntimeInfo:
    """运行时信息"""
    name: str                      # 运行时名称（hermes / standalone / custom）
    version: str
    status: RuntimeStatus
    capabilities: list[str]        # 该运行时提供的能力列表
    connected_at: str = ""
    last_heartbeat: str = ""


# ════════════════════════════════════════════════════════════════
# 抽象接口
# ════════════════════════════════════════════════════════════════

class AbstractRuntime(ABC):
    """太极引擎的运行时抽象接口。

    任何兼容的 AI Agent 运行时（Hermes、自定义等）必须实现此接口。
    太极引擎通过此接口消费运行时能力，而非直接依赖 Hermes。
    """

    @abstractmethod
    async def connect(self) -> RuntimeInfo:
        """建立连接，返回运行时信息"""
        ...

    @abstractmethod
    async def disconnect(self) -> bool:
        """断开连接"""
        ...

    @abstractmethod
    async def heartbeat(self) -> RuntimeStatus:
        """心跳检测"""
        ...

    @abstractmethod
    async def get_capabilities(self) -> list[str]:
        """获取运行时提供的能力列表"""
        ...


class MemoryProvider(Protocol):
    """记忆系统提供者接口"""
    async def load_memory(self, workspace_id: str) -> str: ...
    async def save_memory(self, workspace_id: str, content: str) -> None: ...
    async def search_memory(self, query: str, workspace_id: str, top_k: int) -> list: ...


class ModelProvider(Protocol):
    """模型推理提供者接口"""
    async def chat(self, messages: list[dict], model: str, **kwargs) -> dict: ...
    async def chat_stream(self, messages: list[dict], model: str, **kwargs): ...
    async def list_models(self) -> list[str]: ...


class ToolProvider(Protocol):
    """工具/能力提供者接口"""
    async def execute_tool(self, tool_name: str, params: dict) -> Any: ...
    async def list_tools(self) -> list[str]: ...


class GatewayProvider(Protocol):
    """多平台网关提供者接口"""
    async def send_message(self, platform: str, target: str, content: str) -> bool: ...
    async def receive_message(self, platform: str) -> list[dict]: ...


# ════════════════════════════════════════════════════════════════
# Hermes 运行时实现
# ════════════════════════════════════════════════════════════════

class HermesRuntime(AbstractRuntime):
    """
    Hermes Agent 运行时实现。

    将 Hermes 的能力映射到太极引擎的抽象接口。
    当 Hermes API 变更时，只需修改此实现，太极核心不受影响。
    """

    def __init__(self, hermes_path: str | None = None):
        self._path = hermes_path
        self._info: Optional[RuntimeInfo] = None
        self._connected = False

    async def connect(self) -> RuntimeInfo:
        """连接到 Hermes 运行时"""
        self._connected = True
        self._info = RuntimeInfo(
            name="hermes",
            version="0.17.0",
            status=RuntimeStatus.CONNECTED,
            capabilities=[
                "memory_loader",
                "context_compression",
                "auxiliary_router",
                "task_orchestration",
                "platform_gateway",
                "terminal",
                "mcp_client",
            ],
            connected_at="",
        )
        return self._info

    async def disconnect(self) -> bool:
        self._connected = False
        if self._info:
            self._info.status = RuntimeStatus.DISCONNECTED
        return True

    async def heartbeat(self) -> RuntimeStatus:
        if not self._connected:
            return RuntimeStatus.DISCONNECTED
        return RuntimeStatus.CONNECTED

    async def get_capabilities(self) -> list[str]:
        if self._info:
            return self._info.capabilities
        return []


# ════════════════════════════════════════════════════════════════
# 太极独立运行实现
# ════════════════════════════════════════════════════════════════

class TaiJiStandaloneRuntime(AbstractRuntime):
    """
    太极引擎独立运行时。

    不依赖任何外部 Agent 运行时。
    太极自身提供所有已吸收的能力。
    """

    STANDALONE_CAPABILITIES = [
        "memory_injection",       # 铭心
        "context_compression",    # 缩龙成寸
        "semantic_retrieval",     # 太虚境
        "behavior_audit",         # 夜巡
        "model_routing",          # 分流调度（阶段二）
        "skill_creation",         # 自化（阶段二）
        "data_lifecycle",         # 清风（阶段二）
        "consciousness",          # 太极独有
        "self_evolution",         # 太极独有
        "emergence",              # 太极独有
    ]

    def __init__(self):
        self._connected = False
        self._info: Optional[RuntimeInfo] = None

    async def connect(self) -> RuntimeInfo:
        self._connected = True
        self._info = RuntimeInfo(
            name="taiji-standalone",
            version="2.0",
            status=RuntimeStatus.CONNECTED,
            capabilities=self.STANDALONE_CAPABILITIES,
            connected_at="",
        )
        return self._info

    async def disconnect(self) -> bool:
        self._connected = False
        return True

    async def heartbeat(self) -> RuntimeStatus:
        return RuntimeStatus.CONNECTED if self._connected else RuntimeStatus.DISCONNECTED

    async def get_capabilities(self) -> list[str]:
        return self.STANDALONE_CAPABILITIES


# ════════════════════════════════════════════════════════════════
# 运行时管理器
# ════════════════════════════════════════════════════════════════

class RuntimeManager:
    """
    运行时管理器。

    管理多个运行时的生命周期。
    支持运行时热切换：Hermes → 太极独立。
    """

    def __init__(self):
        self._runtimes: dict[str, AbstractRuntime] = {}
        self._active: Optional[AbstractRuntime] = None
        self._active_name: str = "taiji-standalone"

    def register(self, name: str, runtime: AbstractRuntime) -> None:
        """注册运行时"""
        self._runtimes[name] = runtime

    def unregister(self, name: str) -> bool:
        """注销运行时"""
        if name in self._runtimes:
            del self._runtimes[name]
            if self._active_name == name:
                self._active = None
                self._active_name = ""
            return True
        return False

    async def activate(self, name: str) -> RuntimeInfo:
        """
        激活指定运行时。

        如果当前有活跃的运行时，先断开再激活新的。
        """
        if name not in self._runtimes:
            raise ValueError(f"运行时 {name} 未注册")

        if self._active and self._active_name != name:
            await self._active.disconnect()

        self._active = self._runtimes[name]
        self._active_name = name
        return await self._active.connect()

    async def deactivate(self) -> bool:
        """停用当前运行时"""
        if self._active:
            result = await self._active.disconnect()
            self._active = None
            self._active_name = ""
            return result
        return True

    def get_active(self) -> Optional[AbstractRuntime]:
        """获取当前活跃的运行时"""
        return self._active

    def get_active_name(self) -> str:
        """获取当前活跃的运行时名称"""
        return self._active_name

    def list_runtimes(self) -> list[RuntimeInfo]:
        """列出所有已注册的运行时"""
        infos = []
        for name, rt in self._runtimes.items():
            if isinstance(rt, HermesRuntime):
                infos.append(RuntimeInfo(
                    name=name, version="0.17.0",
                    status=RuntimeStatus.CONNECTED if rt._connected else RuntimeStatus.DISCONNECTED,
                    capabilities=rt.STANDALONE_CAPABILITIES if hasattr(rt, 'STANDALONE_CAPABILITIES') else [],
                ))
            elif isinstance(rt, TaiJiStandaloneRuntime):
                infos.append(RuntimeInfo(
                    name=name, version="2.0",
                    status=RuntimeStatus.CONNECTED if rt._connected else RuntimeStatus.DISCONNECTED,
                    capabilities=rt.STANDALONE_CAPABILITIES,
                ))
        return infos

    def get_status(self) -> dict:
        """获取运行时管理状态"""
        return {
            "active_runtime": self._active_name,
            "registered_runtimes": list(self._runtimes.keys()),
            "standalone_capabilities": TaiJiStandaloneRuntime.STANDALONE_CAPABILITIES,
            "hermes_dependent_capabilities": [
                "task_orchestration",
                "platform_gateway",
                "terminal",
                "mcp_client",
            ],
            "independence_level": "full",  # 太极可独立运行
        }


# 平台唯一实例
runtime_manager = RuntimeManager()

# 默认注册：太极独立 + Hermes（可选）
runtime_manager.register("taiji-standalone", TaiJiStandaloneRuntime())
runtime_manager.register("hermes", HermesRuntime())
