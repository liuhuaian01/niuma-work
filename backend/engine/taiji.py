"""
太极引擎（Taiji Engine）——超级牛马工作台底层核心引擎。

道 → 一（太极）→ 二（阴阳）→ 三（七元）→ 万物

七元：
  平台三元 (Hermes→Swarm→Work间)
  记忆三元 (L1→L2→L3→Honcho)
  管控三元 (开关→预算→降级)
  编排三元 (Root→Worker→Gate+Synthesizer)
  算力三元 (本地→云端→太极网格)    ← 2026-06-24 新增
  认知三元 (个体→群体→涌现)
  连接三元 (模型→应用→设备)

使用方式:
    from engine.taiji import taiji
    await taiji.init(contributing=True)  # 开启太极网格算力共享
    taiji.flags.is_allowed("web_fetch")  # → False (默认关闭)
    taiji.mesh.get_mesh_stats()          # → 网格统计
"""

from __future__ import annotations
from engine.capability_flags import CapabilityFlags


class TaijiEngine:
    """太极引擎——平台唯一实例。道生一，一即太极。

    七元不是七个模块的集合，是"一"的七个面。
    2026-06-24: 新增太极网格集成——算力三元落地。
    """

    def __init__(self) -> None:
        self._flags: CapabilityFlags | None = None
        self._mesh = None        # TaijiMesh（惰性加载）
        self._initialized: bool = False

    @property
    def flags(self) -> CapabilityFlags:
        if self._flags is None:
            self._flags = CapabilityFlags()
        return self._flags

    @property
    def mesh(self):
        """太极网格——算力三元。惰性加载。"""
        if self._mesh is None:
            from engine.taiji_mesh import taiji_mesh
            self._mesh = taiji_mesh
        return self._mesh

    async def init(self, contributing: bool = False) -> None:
        """初始化太极引擎。应用启动时调用一次。

        Args:
            contributing: 是否贡献算力到太极网格（默认关闭，用户主动开启）
        """
        if self._initialized:
            return
        self._flags = CapabilityFlags()

        # 初始化太极网格（算力三元）
        if self._mesh is None:
            from engine.taiji_mesh import taiji_mesh
            self._mesh = taiji_mesh
        await self._mesh.init(contributing=contributing)

        self._initialized = True

    async def shutdown(self) -> None:
        """优雅关闭太极引擎。"""
        if self._mesh and self._mesh.is_initialized:
            await self._mesh.drain()
        self._initialized = False

    @property
    def initialized(self) -> bool:
        return self._initialized

    # ================================================================
    # 七元入口（语义化API）
    # ================================================================

    def one(self) -> "TaijiEngine":
        """道生一：太极引擎自身。"""
        return self

    def two(self) -> dict:
        """一生二：七象阴阳。"""
        return {
            "deploy": "本地↔云端",
            "action": "沉默↔介入",
            "govern": "刚↔柔",
            "space": "沙盒↔穿透",
            "compute": "独享↔共享",      # 新增
            "cognition": "个体↔群体",    # 新增
            "connect": "锁死↔开放",      # 新增
        }

    def three(self) -> dict:
        """二生三：七大三元稳定结构。"""
        return {
            "platform": "Hermes→Swarm→Work间→群聊",
            "memory": "L1→L2→L3→Honcho建模",
            "control": "开关→预算→降级→执行过剩为零",
            "orchestration": "Root→Worker→Gate→Synthesizer",
            "compute": "本地→云端→太极网格→永不卡顿",       # 新增
            "cognition": "个体→群体→涌现→超越设计",          # 新增
            "connect": "模型→应用→设备→无缝体验",            # 新增
        }

    async def myriad(self) -> dict:
        """三生万物：所有从七元中衍生的功能。"""
        stats = {}
        if self._mesh and self._mesh.is_initialized:
            stats = self._mesh.get_mesh_stats()
        return {
            "mesh": stats,
            "flags": self._flags.summary() if self._flags else {},
            "triads": self.three(),
        }


# 平台唯一实例 —— 一即太极
taiji = TaijiEngine()
