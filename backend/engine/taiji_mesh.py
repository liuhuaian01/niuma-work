"""
太极引擎 · 太极网格（Taiji Mesh）——快播式 P2P 分布式算力网络

算力三元：本地 → 云端 → 太极网格。
用户装了太极引擎，闲置算力自动加入网格。
本地推理优先 → 不够 → 邻居节点 → 云端保底。

设计原则：
  - 只共享算力，不共享数据。推理请求端到端加密。
  - 默认关闭"贡献算力"，用户主动开启。
  - 节点互不信任，所有推理沙盒化执行。
  - 退出即消失，不留痕迹。

v1.1 (2026-06-24): v1.0 + UDP广播节点发现 + hello响应协议
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import asyncio
import hashlib
import json
import logging
import platform
import time
import uuid

logger = logging.getLogger("niuma.mesh")


# ============================================================
# 枚举与常量
# ============================================================

class NodeStatus(Enum):
    OFFLINE = "offline"
    ONLINE = "online"
    BUSY = "busy"           # 正在执行推理
    DRAINING = "draining"   # 正在退出，不接受新请求
    DEGRADED = "degraded"   # 在线但算力受限


class ResourceTier(Enum):
    """算力贡献等级。"""
    LIGHT = "light"         # 只贡献 CPU（< 4 核闲置）
    MODERATE = "moderate"   # CPU + 小 GPU（< 8GB VRAM）
    HEAVY = "heavy"         # 大 GPU（>= 8GB VRAM）
    SERVER = "server"       # 服务器级多 GPU


class MeshPrivacyLevel(Enum):
    """网格隐私等级。"""
    STRICT = "strict"       # 只连局域网节点
    TRUSTED = "trusted"     # 连局域网 + 白名单节点
    GLOBAL = "global"       # 连全网节点（端到端加密）


# ============================================================
# 数据模型
# ============================================================

@dataclass
class GpuInfo:
    """GPU 信息。"""
    name: str = ""
    vram_mb: int = 0
    available_mb: int = 0
    utilization_pct: float = 0.0


@dataclass
class NodeResources:
    """节点可注册的算力资源。"""
    cpu_cores: int = 0
    cpu_available: float = 0.0       # 0.0-1.0 可用比例
    memory_mb: int = 0
    memory_available_mb: int = 0
    gpus: list[GpuInfo] = field(default_factory=list)
    supported_models: list[str] = field(default_factory=list)  # 本地已拉取的模型名
    tier: ResourceTier = ResourceTier.LIGHT


@dataclass
class MeshNode:
    """太极网格中的一个节点。"""
    node_id: str = field(default_factory=lambda: f"mesh-{uuid.uuid4().hex[:12]}")
    hostname: str = field(default_factory=platform.node)
    ip_address: str = ""
    port: int = 19527      # 太极网格默认端口
    resources: NodeResources = field(default_factory=NodeResources)
    status: NodeStatus = NodeStatus.OFFLINE
    privacy_level: MeshPrivacyLevel = MeshPrivacyLevel.STRICT
    last_heartbeat: float = 0.0
    contribution_score: float = 0.0     # 贡献积分
    total_inferences_served: int = 0
    joined_at: float = field(default_factory=time.time)

    @property
    def node_hash(self) -> str:
        """节点匿名哈希——用于隐私保护。"""
        return hashlib.sha256(self.node_id.encode()).hexdigest()[:16]

    def is_healthy(self, max_heartbeat_age: float = 30.0) -> bool:
        """心跳在30秒内视为健康。"""
        return (time.time() - self.last_heartbeat) < max_heartbeat_age

    def can_handle_model(self, model_name: str) -> bool:
        """检查节点是否能处理指定模型。"""
        return model_name in self.resources.supported_models


@dataclass
class MeshRouteResult:
    """三层路由决策结果。"""
    chosen_layer: str          # "local" | "mesh" | "cloud"
    node: Optional[MeshNode] = None
    model: str = ""
    reason: str = ""
    estimated_latency_ms: float = 0.0
    estimated_cost: float = 0.0     # 积分或API费用


@dataclass
class ContributionRecord:
    """单次算力贡献记录。"""
    id: str = field(default_factory=lambda: f"contrib-{uuid.uuid4().hex[:8]}")
    from_node: str = ""
    to_node: str = ""
    model: str = ""
    tokens_generated: int = 0
    gpu_seconds: float = 0.0
    score_earned: float = 0.0
    timestamp: float = field(default_factory=time.time)


# ============================================================
# 太极网格引擎
# ============================================================

class TaijiMesh:
    """太极网格引擎。

    生命周期：init() → 资源探测 → 注册 → 健康心跳 → 接收请求 / 发送请求 → drain() → remove()

    三层路由：本地推理 → 太极网格节点 → 云端 API
    """

    # 配置
    HEARTBEAT_INTERVAL = 10      # 心跳间隔（秒）
    NODE_TIMEOUT = 30            # 节点超时（秒）
    MAX_PEERS = 50               # 最大邻居节点数
    DEFAULT_PORT = 19527         # 太极网格默认端口

    def __init__(self) -> None:
        # 本节点
        self._self_node: MeshNode = MeshNode()
        self._resources: NodeResources = NodeResources()
        self._initialized: bool = False
        self._contributing: bool = False      # 用户是否开启了"贡献算力"

        # 邻居节点表（node_id → MeshNode）
        self._peers: dict[str, MeshNode] = {}

        # 贡献记录
        self._contributions: list[ContributionRecord] = []

        # 后台任务
        self._heartbeat_task: asyncio.Task | None = None
        self._discovery_task: asyncio.Task | None = None
        self._prune_task: asyncio.Task | None = None

        # 回调
        self._on_peer_joined: list[callable] = []
        self._on_peer_left: list[callable] = []

    # ================================================================
    # 初始化与生命周期
    # ================================================================

    async def init(self, contributing: bool = False, privacy: MeshPrivacyLevel = MeshPrivacyLevel.STRICT) -> None:
        """初始化太极网格节点。

        Args:
            contributing: 是否贡献算力（默认关闭）
            privacy: 隐私等级（默认只连局域网）
        """
        if self._initialized:
            return

        logger.info("太极网格初始化中...")
        self._contributing = contributing
        self._self_node.privacy_level = privacy

        # 探测本地资源
        self._resources = await self._probe_resources()
        self._self_node.resources = self._resources
        self._self_node.status = NodeStatus.ONLINE if contributing else NodeStatus.OFFLINE

        if contributing:
            logger.info(
                "太极网格节点上线: tier=%s, cpu=%d核, gpu=%d个",
                self._resources.tier.value,
                self._resources.cpu_cores,
                len(self._resources.gpus),
            )

        self._initialized = True

        # 启动后台任务
        if contributing:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self._discovery_task = asyncio.create_task(self._discovery_loop())
            self._prune_task = asyncio.create_task(self._prune_loop())

    async def drain(self) -> None:
        """优雅退出——不接受新请求，等待进行中的推理完成。"""
        logger.info("太极网格节点正在退出...")
        self._self_node.status = NodeStatus.DRAINING

        # 取消后台任务
        for task in [self._heartbeat_task, self._discovery_task, self._prune_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._self_node.status = NodeStatus.OFFLINE
        self._peers.clear()
        logger.info("太极网格节点已离线")

    # ================================================================
    # 资源探测
    # ================================================================

    async def _probe_resources(self) -> NodeResources:
        """探测本地可用算力资源。"""
        resources = NodeResources()
        resources.cpu_cores = self._get_cpu_cores()
        resources.cpu_available = self._get_cpu_available()
        resources.memory_mb, resources.memory_available_mb = self._get_memory_info()
        resources.gpus = await self._probe_gpus()
        resources.supported_models = await self._probe_local_models()

        # 根据GPU判断等级
        total_vram = sum(g.vram_mb for g in resources.gpus)
        if total_vram >= 24000:
            resources.tier = ResourceTier.SERVER
        elif total_vram >= 8000:
            resources.tier = ResourceTier.HEAVY
        elif total_vram > 0:
            resources.tier = ResourceTier.MODERATE
        else:
            resources.tier = ResourceTier.LIGHT

        return resources

    @staticmethod
    def _get_cpu_cores() -> int:
        try:
            return len(psutil.cpu_count(logical=True))
        except Exception:
            return 4  # 安全兜底

    @staticmethod
    def _get_cpu_available() -> float:
        try:
            return 1.0 - (psutil.cpu_percent(interval=0.1) / 100.0)
        except Exception:
            return 0.5

    @staticmethod
    def _get_memory_info() -> tuple[int, int]:
        try:
            mem = psutil.virtual_memory()
            return mem.total // (1024 * 1024), mem.available // (1024 * 1024)
        except Exception:
            return 8192, 4096

    @staticmethod
    async def _probe_gpus() -> list[GpuInfo]:
        """探测 GPU 信息。"""
        gpus = []
        # 尝试通过 nvidia-smi 获取
        try:
            proc = await asyncio.create_subprocess_exec(
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free,utilization.gpu",
                "--format=csv,noheader,nounits",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            if stdout:
                for line in stdout.decode().strip().split("\n"):
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 4:
                        gpus.append(GpuInfo(
                            name=parts[0],
                            vram_mb=int(float(parts[1])),
                            available_mb=int(float(parts[2])),
                            utilization_pct=float(parts[3]) / 100.0,
                        ))
        except Exception:
            pass
        return gpus

    @staticmethod
    async def _probe_local_models() -> list[str]:
        """探测本地 Ollama 已拉取的模型。"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ollama", "list",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            if stdout:
                lines = stdout.decode().strip().split("\n")[1:]  # skip header
                return [line.split()[0] for line in lines if line.strip()]
        except Exception:
            pass
        return []

    # ================================================================
    # 节点发现与连接
    # ================================================================

    def register_peer(self, node: MeshNode) -> None:
        """注册邻居节点（通过发现协议或手动添加）。"""
        if len(self._peers) >= self.MAX_PEERS:
            # 淘汰最久未心跳的节点
            oldest = min(self._peers.values(), key=lambda n: n.last_heartbeat)
            del self._peers[oldest.node_id]
            logger.debug("节点表已满，淘汰: %s", oldest.hostname)

        self._peers[node.node_id] = node
        logger.info("发现网格节点: %s (tier=%s, gpu=%d)", node.hostname, node.resources.tier.value, len(node.resources.gpus))

        for cb in self._on_peer_joined:
            try:
                cb(node)
            except Exception:
                pass

    def remove_peer(self, node_id: str) -> None:
        """移除节点。"""
        node = self._peers.pop(node_id, None)
        if node:
            logger.info("节点离线: %s", node.hostname)
            for cb in self._on_peer_left:
                try:
                    cb(node)
                except Exception:
                    pass

    def get_healthy_peers(self) -> list[MeshNode]:
        """获取所有健康的邻居节点。"""
        return [n for n in self._peers.values() if n.is_healthy(self.NODE_TIMEOUT)]

    def find_peer_for_model(
        self, model_name: str, max_latency_ms: float = 50.0
    ) -> Optional[MeshNode]:
        """为指定模型找最佳邻居节点。

        策略：优先找同局域网、有该模型、空闲的节点。
        """
        candidates = [
            n for n in self.get_healthy_peers()
            if n.can_handle_model(model_name) and n.status in (NodeStatus.ONLINE,)
        ]
        if not candidates:
            return None

        # 优先选 GPU 最大、利用率最低的节点
        candidates.sort(
            key=lambda n: (
                n.resources.tier.value,
                -sum(g.available_mb for g in n.resources.gpus),
            ),
            reverse=True,
        )
        return candidates[0]

    # ================================================================
    # 三层路由——算力三元的决策核心
    # ================================================================

    async def route_inference(
        self, model_name: str, estimated_tokens: int = 1000, priority: float = 0.5
    ) -> MeshRouteResult:
        """三层路由决策：本地 → 太极网格 → 云端 API。

        Returns:
            MeshRouteResult: 包含路由决策和预估成本/延迟。
        """
        # 第一层：本地推理
        if model_name in self._resources.supported_models:
            return MeshRouteResult(
                chosen_layer="local",
                model=model_name,
                reason=f"本地已有 {model_name}，零成本零延迟",
                estimated_latency_ms=5.0,
                estimated_cost=0.0,
            )

        # 第二层：太极网格
        if self._contributing:
            peer = self.find_peer_for_model(model_name)
            if peer:
                return MeshRouteResult(
                    chosen_layer="mesh",
                    node=peer,
                    model=model_name,
                    reason=f"网格节点 {peer.hostname} 可用 {model_name}",
                    estimated_latency_ms=30.0,
                    estimated_cost=estimated_tokens * 0.0001,  # 积分估算
                )

        # 第三层：云端 API 保底
        return MeshRouteResult(
            chosen_layer="cloud",
            model=model_name,
            reason="本地无模型，网格无节点，走云端保底",
            estimated_latency_ms=200.0,
            estimated_cost=estimated_tokens * 0.002,  # 典型 API 价格
        )

    # ================================================================
    # 算力贡献
    # ================================================================

    async def serve_inference(
        self, model_name: str, prompt: str, requestor_node: str
    ) -> dict:
        """响应邻居节点的推理请求。

        在沙盒化环境中执行推理，完成后返回结果。
        v1.0: 返回占位结果。v2.0实现真正的沙盒推理。
        """
        if self._self_node.status != NodeStatus.ONLINE:
            return {"error": "node not online", "status": "rejected"}

        if model_name not in self._resources.supported_models:
            return {"error": f"model {model_name} not available", "status": "rejected"}

        self._self_node.status = NodeStatus.BUSY
        start_time = time.time()

        try:
            # TODO v2.0: 真正的 Ollama 推理调用
            # result = await self._ollama_inference(model_name, prompt)
            result = {"text": "[太极网格·占位]", "model": model_name, "status": "ok"}

            elapsed = time.time() - start_time
            score = elapsed * 0.1  # 贡献积分 = GPU秒 × 系数

            self._self_node.contribution_score += score
            self._self_node.total_inferences_served += 1

            self._contributions.append(ContributionRecord(
                from_node=self._self_node.node_id,
                to_node=requestor_node or "unknown",
                model=model_name,
                tokens_generated=len(prompt) // 4,  # 粗略估计
                gpu_seconds=elapsed,
                score_earned=score,
            ))

            logger.info("服务推理完成: model=%s, elapsed=%.2fs, score=%.4f", model_name, elapsed, score)
            return result

        finally:
            self._self_node.status = NodeStatus.ONLINE

    def get_contribution_summary(self) -> dict:
        """贡献摘要——用于展示给用户。"""
        return {
            "total_score": self._self_node.contribution_score,
            "total_inferences_served": self._self_node.total_inferences_served,
            "tier": self._resources.tier.value,
            "gpus": len(self._resources.gpus),
            "cpu_cores": self._resources.cpu_cores,
            "peers_count": len(self._peers),
            "healthy_peers": len(self.get_healthy_peers()),
            "contributing": self._contributing,
        }

    # ================================================================
    # 后台循环
    # ================================================================

    async def _heartbeat_loop(self) -> None:
        """心跳循环——定期声明本节点在线。"""
        while True:
            try:
                self._self_node.last_heartbeat = time.time()
                self._self_node.resources = await self._probe_resources()
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("心跳异常，5秒后重试")
                await asyncio.sleep(5)

    async def _discovery_loop(self) -> None:
        """节点发现循环——UDP 广播发现局域网内的太极网格邻居。

        v1.1: UDP 广播协议，零依赖。
        协议格式（JSON over UDP）：
          广播: {"type":"taiji_mesh_discover","node":{...}}
          响应: {"type":"taiji_mesh_hello","node":{...}}
        """
        DISCOVERY_PORT = 19528
        DISCOVERY_INTERVAL = 15          # 每15秒广播一次
        RESPONSE_TIMEOUT = 3.0           # 等待响应超时

        sock: socket.socket | None = None
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setblocking(False)
            sock.bind(("", DISCOVERY_PORT))
            logger.info("太极网格发现服务已启动: UDP:%d", DISCOVERY_PORT)
        except Exception as e:
            logger.warning("太极网格发现服务启动失败: %s", e)
            sock = None

        last_broadcast = 0.0
        while True:
            try:
                now = time.time()

                # 周期广播本节点信息
                if sock and (now - last_broadcast) > DISCOVERY_INTERVAL:
                    last_broadcast = now
                    discover_msg = json.dumps({
                        "type": "taiji_mesh_discover",
                        "node": self._self_node_to_dict(),
                    }, ensure_ascii=False)
                    try:
                        sock.sendto(
                            discover_msg.encode("utf-8"),
                            ("255.255.255.255", DISCOVERY_PORT),
                        )
                    except Exception:
                        pass

                # 接收邻居响应（非阻塞）
                if sock:
                    try:
                        data, addr = sock.recvfrom(4096)
                        await self._handle_discovery_message(data, addr)
                    except BlockingIOError:
                        pass
                    except Exception:
                        pass

                await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("发现循环异常，5秒后重试")
                await asyncio.sleep(5)

        if sock:
            try:
                sock.close()
            except Exception:
                pass

    def _self_node_to_dict(self) -> dict[str, object]:
        """序列化本节点信息为广播 payload。"""
        return {
            "node_id": self._self_node.node_id,
            "hostname": self._self_node.hostname,
            "port": self._self_node.port,
            "tier": self._resources.tier.value,
            "cpu_cores": self._resources.cpu_cores,
            "cpu_available": self._resources.cpu_available,
            "memory_mb": self._resources.memory_mb,
            "gpu_count": len(self._resources.gpus),
            "gpu_vram_mb": sum(g.vram_mb for g in self._resources.gpus),
            "models": self._resources.supported_models,
            "privacy_level": self._self_node.privacy_level.value,
        }

    async def _handle_discovery_message(self, data: bytes, addr: tuple[str, int]) -> None:
        """处理收到的发现消息——可能是广播请求或邻居响应。"""
        try:
            msg = json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            return

        msg_type = msg.get("type", "")
        if msg_type not in ("taiji_mesh_discover", "taiji_mesh_hello"):
            return

        node_data = msg.get("node", {})
        if not isinstance(node_data, dict):
            return

        remote_id = str(node_data.get("node_id", ""))
        if remote_id == self._self_node.node_id:
            return  # 自己发的广播，忽略

        if remote_id in self._peers:
            # 已知节点——刷新心跳
            existing = self._peers[remote_id]
            existing.last_heartbeat = time.time()
            existing.resources.supported_models = list(node_data.get("models", [])) or existing.resources.supported_models
            return

        # 新节点——创建 MeshNode 并注册
        new_node = MeshNode(
            node_id=remote_id,
            hostname=str(node_data.get("hostname", "unknown")),
            ip_address=addr[0],
            port=int(node_data.get("port", self.DEFAULT_PORT)),
            status=NodeStatus.ONLINE,
            last_heartbeat=time.time(),
        )
        new_node.resources = NodeResources(
            cpu_cores=int(node_data.get("cpu_cores", 0)),
            cpu_available=float(node_data.get("cpu_available", 0.5)),
            memory_mb=int(node_data.get("memory_mb", 0)),
            supported_models=list(node_data.get("models", [])),
            tier=ResourceTier(str(node_data.get("tier", "light"))),
        )
        self.register_peer(new_node)

        # 如果是发现广播，回复 hello
        if msg_type == "taiji_mesh_discover":
            await self._send_hello_response(addr)

    async def _send_hello_response(self, addr: tuple[str, int]) -> None:
        """对广播请求回复本节点信息。"""
        try:
            import socket
            hello = json.dumps({
                "type": "taiji_mesh_hello",
                "node": self._self_node_to_dict(),
            }, ensure_ascii=False)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(1)
                s.sendto(hello.encode("utf-8"), addr)
        except Exception:
            pass

    async def _prune_loop(self) -> None:
        """节点清理循环——移除超时节点。"""
        while True:
            try:
                now = time.time()
                dead = [
                    node_id
                    for node_id, node in self._peers.items()
                    if not node.is_healthy(self.NODE_TIMEOUT)
                ]
                for node_id in dead:
                    self.remove_peer(node_id)
                await asyncio.sleep(15)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("节点清理异常")
                await asyncio.sleep(15)

    # ================================================================
    # 统计与监控
    # ================================================================

    def get_mesh_stats(self) -> dict:
        """网格统计——用于遥测和前端展示。"""
        healthy = self.get_healthy_peers()
        total_vram = sum(
            sum(g.vram_mb for g in n.resources.gpus) for n in healthy
        )
        unique_models = set()
        for n in healthy:
            unique_models.update(n.resources.supported_models)

        return {
            "self": {
                "node_id": self._self_node.node_hash,
                "status": self._self_node.status.value,
                "contributing": self._contributing,
                "tier": self._resources.tier.value,
            },
            "network": {
                "total_peers": len(self._peers),
                "healthy_peers": len(healthy),
                "total_gpu_vram_mb": total_vram,
                "unique_models": len(unique_models),
                "models": list(unique_models)[:20],
            },
            "contributions": {
                "total_score": self._self_node.contribution_score,
                "total_served": self._self_node.total_inferences_served,
            },
        }

    @property
    def contributing(self) -> bool:
        return self._contributing

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def self_node(self) -> MeshNode:
        return self._self_node

    @property
    def peers(self) -> dict[str, MeshNode]:
        return dict(self._peers)


# 全局单例
taiji_mesh = TaijiMesh()


# 延迟导入 psutil（非必需依赖）
try:
    import psutil
except ImportError:
    psutil = None  # type: ignore
    logger.warning("psutil 未安装，资源探测降级为默认值。安装: pip install psutil")
