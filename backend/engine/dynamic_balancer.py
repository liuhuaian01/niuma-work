"""
太极引擎 · Dynamic Balancer（阴阳均衡器）

阴阳平衡——本地←→网格←→云端 动态均衡。
不是 if-else 选边，是根据任务度、隐私度、预算加权动态调整。

v1.1: CLOUD_HEALTH_HOST 可配置 + asyncio TCP Ping + 60s TTL 缓存
v2.0 (2026-06-24): 新增 MESH 模式——三层路由（本地→太极网格→云端）
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging
import time
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


class RuntimeMode(Enum):
    LOCAL = "local"          # 本地 Ollama/llama.cpp
    MESH = "mesh"            # 太极网格 P2P（新增 v2.0）
    CLOUD = "cloud"          # 云端 API
    HYBRID = "hybrid"        # 混合——本地优先，云端 backup


@dataclass
class BalanceDecision:
    mode: RuntimeMode
    reason: str
    local_weight: float = 0.0     # 本地权重 0.0-1.0
    mesh_weight: float = 0.0      # 网格权重 0.0-1.0（新增 v2.0）
    cloud_weight: float = 0.0      # 云端权重 0.0-1.0
    mesh_peer_id: str = ""          # 如果走网格，记录邻居节点 ID
    peak_pricing: bool = False      # v1.9: 是否处于 API 高峰定价时段
    peak_multiplier: float = 1.0    # v1.9: 高峰价格倍率（1.0=平时, 2.0=高峰）


class DynamicBalancer:
    """阴阳均衡器——v2.0 三层路由。

    v1.1 健康检查升级:
    - CLOUD_HEALTH_HOST: None=信任模式
    - 60s TTL 缓存

    v2.0 新增三层路由:
    - 第一层：本地推理（零成本、零延迟、隐私最好）
    - 第二层：太极网格 P2P（低成本、低延迟、算力共享）
    - 第三层：云端 API（能力最强、成本最高、保底路径）
    """

    # 健康检查配置
    OLLAMA_HEALTH_URL = "http://localhost:11434/api/tags"
    CLOUD_HEALTH_HOST: str | None = None
    HEALTH_CHECK_TIMEOUT = 3
    HEALTH_CHECK_TTL = 60

    # 网格三层路由分界点
    MESH_PREFERRED_LOCAL_THRESHOLD = 0.65   # 高于此值走本地
    MESH_FALLBACK_CLOUD_THRESHOLD = 0.35    # 低于此值走云端
                                             # 中间走网格

    # v1.9: DeepSeek V4 峰谷定价配置
    PEAK_HOURS_MORNING = (9, 12)            # 早高峰 9:00-12:00 (北京时间)
    PEAK_HOURS_AFTERNOON = (14, 18)         # 晚高峰 14:00-18:00 (北京时间)
    PEAK_PRICE_MULTIPLIER = 2.0             # 高峰时段价格倍率
    PEAK_TIMEZONE_OFFSET = 8                # 北京时间 UTC+8

    def __init__(self, cloud_health_host: str | None = None) -> None:
        # 健康检查状态
        self._local_available: bool = False
        self._cloud_available: bool = True    # 信任模式默认 True
        self._mesh_available: bool = False    # 默认无网格
        self._health_checked: bool = False
        self._last_health_check: float = 0.0

        # 网格引用（惰性加载）
        self._mesh = None

        if cloud_health_host is not None:
            self.CLOUD_HEALTH_HOST = cloud_health_host

    @property
    def _mesh_engine(self):
        """惰性加载太极网格引擎。"""
        if self._mesh is None:
            try:
                from engine.taiji_mesh import taiji_mesh
                self._mesh = taiji_mesh
            except ImportError:
                self._mesh = None
        return self._mesh

    # ================================================================
    # 异步健康检查（P1-2: 同步 HTTP → asyncio.to_thread，避免阻塞事件循环）
    # ================================================================

    async def _ensure_health_checked(self) -> None:
        """异步健康检查——保持 TTL 缓存，但使用非阻塞 HTTP。"""
        now = time.time()
        if self._health_checked and (now - self._last_health_check) < self.HEALTH_CHECK_TTL:
            return

        logger.debug("执行异步健康检查 (TTL=%ds)", self.HEALTH_CHECK_TTL)
        # 使用 asyncio.to_thread 将同步 HTTP 转为非阻塞
        local_ok, cloud_ok = await asyncio.to_thread(
            lambda: (self._check_ollama_health(), self._check_cloud_health())
        )
        self._local_available = local_ok
        self._cloud_available = cloud_ok

        # 检查网格是否可用
        mesh = self._mesh_engine
        self._mesh_available = bool(
            mesh and mesh.is_initialized and mesh.contributing
        )

        self._health_checked = True
        self._last_health_check = now

    def _check_ollama_health(self) -> bool:
        try:
            req = urllib.request.Request(self.OLLAMA_HEALTH_URL, method="GET")
            urllib.request.urlopen(req, timeout=self.HEALTH_CHECK_TIMEOUT)
            return True
        except Exception as e:
            logger.info("Ollama 健康检查失败: %s", e)
            return False

    def _check_cloud_health(self) -> bool:
        if self.CLOUD_HEALTH_HOST is None:
            return True

        host = self.CLOUD_HEALTH_HOST
        if ":" in host and not host.startswith("http"):
            parts = host.rsplit(":", 1)
            try:
                port = int(parts[1])
                return self._tcp_ping(parts[0], port)
            except ValueError:
                pass

        try:
            url = f"https://{host}" if not host.startswith("http") else host
            req = urllib.request.Request(url, method="GET")
            urllib.request.urlopen(req, timeout=self.HEALTH_CHECK_TIMEOUT)
            return True
        except Exception as e:
            logger.info("云端健康检查失败: %s", e)
            return False

    def _tcp_ping(self, host: str, port: int) -> bool:
        import socket
        try:
            sock = socket.create_connection((host, port), timeout=self.HEALTH_CHECK_TIMEOUT)
            sock.close()
            return True
        except Exception as e:
            logger.info("TCP Ping 失败 (%s:%d): %s", host, port, e)
            return False

    # ================================================================
    # 异步健康检查
    # ================================================================

    async def _check_cloud_health_async(self) -> bool:
        if self.CLOUD_HEALTH_HOST is None:
            return True

        host = self.CLOUD_HEALTH_HOST
        if ":" in host and not host.startswith("http"):
            parts = host.rsplit(":", 1)
            try:
                port = int(parts[1])
                return await self._tcp_ping_async(parts[0], port)
            except ValueError:
                pass

        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._check_cloud_health)
        except RuntimeError:
            return self._check_cloud_health()

    async def _tcp_ping_async(self, host: str, port: int) -> bool:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=self.HEALTH_CHECK_TIMEOUT,
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception as e:
            logger.info("异步 TCP Ping 失败 (%s:%d): %s", host, port, e)
            return False

    async def _check_ollama_health_async(self) -> bool:
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._check_ollama_health)
        except RuntimeError:
            return self._check_ollama_health()

    async def refresh_health_async(self) -> dict:
        local_task = self._check_ollama_health_async()
        cloud_task = self._check_cloud_health_async()
        results = await asyncio.gather(local_task, cloud_task, return_exceptions=True)

        self._local_available = results[0] if not isinstance(results[0], BaseException) else False
        self._cloud_available = results[1] if not isinstance(results[1], BaseException) else True

        mesh = self._mesh_engine
        self._mesh_available = bool(
            mesh and mesh.is_initialized and mesh.contributing
        )

        self._health_checked = True
        self._last_health_check = time.time()

        logger.info("异步健康检查完成: local=%s, mesh=%s, cloud=%s",
                     self._local_available, self._mesh_available, self._cloud_available)
        return {
            "local": self._local_available,
            "mesh": self._mesh_available,
            "cloud": self._cloud_available,
        }

    @staticmethod
    def _is_peak_hour() -> tuple[bool, float]:
        """判断当前是否处于 DeepSeek V4 API 高峰定价时段。

        高峰时段（北京时间工作日）: 9:00-12:00, 14:00-18:00
        非高峰时段及周末/节假日: 按平时价格计费。

        Returns:
            (is_peak, multiplier): 是否高峰 + 价格倍率
        """
        from datetime import datetime, timezone, timedelta
        now_utc = datetime.now(timezone.utc)
        beijing_tz = timezone(timedelta(hours=DynamicBalancer.PEAK_TIMEZONE_OFFSET))
        now_bj = now_utc.astimezone(beijing_tz)

        # 周末不适用峰谷定价
        if now_bj.weekday() >= 5:  # 5=周六, 6=周日
            return False, 1.0

        hour = now_bj.hour
        morning_start, morning_end = DynamicBalancer.PEAK_HOURS_MORNING
        afternoon_start, afternoon_end = DynamicBalancer.PEAK_HOURS_AFTERNOON

        if morning_start <= hour < morning_end:
            return True, DynamicBalancer.PEAK_PRICE_MULTIPLIER
        if afternoon_start <= hour < afternoon_end:
            return True, DynamicBalancer.PEAK_PRICE_MULTIPLIER

        return False, 1.0

    async def decide(
        self, privacy_sensitive: bool = False, task_complexity: float = 0.5,
        budget_remaining_pct: float = 0.8, user_prefers_local: bool = True,
        model_name: str = "",
    ) -> BalanceDecision:
        """根据因子动态决定运行模式——三层路由 + v1.9 峰谷感知。

        决策逻辑（v2.0 + v1.9）：
        1. 隐私敏感 → 强制本地
        2. 本地有模型 → 本地（零成本零延迟）
        3. 本地无模型、网格可用 → 走网格 P2P
        4. 网格不可用或预算充足 → 走云端保底
        5. v1.9: 云端模式下附加峰谷定价标记
        """
        await self._ensure_health_checked()
        is_peak, peak_mult = self._is_peak_hour()

        def _make(mode, reason, lw=0.0, mw=0.0, cw=0.0, peer="", peak_aware=False):
            return BalanceDecision(
                mode=mode, reason=reason,
                local_weight=lw, mesh_weight=mw, cloud_weight=cw,
                mesh_peer_id=peer,
                peak_pricing=peak_aware and is_peak,
                peak_multiplier=peak_mult if peak_aware else 1.0,
            )

        # 隐私敏感 → 强制本地
        if privacy_sensitive and self._local_available:
            return _make(RuntimeMode.LOCAL, "隐私敏感任务，强制本地运行", lw=1.0)

        # 本地不可用 → 必须走远程
        if not self._local_available:
            if not self._cloud_available:
                return _make(RuntimeMode.LOCAL, "本地和云端均不可用，强制本地尝试", lw=1.0)
            if self._mesh_available:
                return _make(RuntimeMode.MESH, "本地不可用，优先太极网格", mw=0.7, cw=0.3)
            return _make(RuntimeMode.CLOUD, "本地和网格均不可用，走云端保底", cw=1.0, peak_aware=True)

        # 云端不可用 → 本地或网格
        if not self._cloud_available:
            if self._local_available:
                return _make(RuntimeMode.LOCAL, "云端不可用，使用本地模型", lw=1.0)
            if self._mesh_available:
                return _make(RuntimeMode.MESH, "云端不可用，走太极网格", mw=1.0)

        # 三层路由：计算本地得分
        local_score = (
            (1.0 if user_prefers_local else 0.0) * 0.3 +
            (1 - task_complexity) * 0.3 +
            budget_remaining_pct * 0.4
        )
        local_score = max(0.0, min(1.0, local_score))
        remaining = 1.0 - local_score

        # 三层分界
        if local_score > self.MESH_PREFERRED_LOCAL_THRESHOLD:
            return _make(RuntimeMode.LOCAL,
                f"综合评分倾向本地(local={local_score:.2f})",
                lw=local_score, cw=remaining * 0.5, mw=remaining * 0.5)

        elif local_score > self.MESH_FALLBACK_CLOUD_THRESHOLD:
            # 中间地带——网格优先
            if self._mesh_available:
                # 检查网格是否有该模型
                mesh_peer_id = ""
                mesh = self._mesh_engine
                if mesh and model_name:
                    peer = mesh.find_peer_for_model(model_name)
                    if peer:
                        mesh_peer_id = peer.node_hash

                return _make(RuntimeMode.MESH,
                    f"中间地带，太极网格优先(local={local_score:.2f}, mesh可用)",
                    lw=local_score * 0.3, mw=remaining * 0.7, cw=remaining * 0.3,
                    peer=mesh_peer_id)
            else:
                peak_note = f"{'+峰谷定价' if is_peak else ''}"
                return _make(RuntimeMode.CLOUD,
                    f"中间地带但网格不可用，走云端(local={local_score:.2f}){peak_note}",
                    lw=local_score * 0.3, cw=remaining, peak_aware=True)

        else:
            # 低分 → 云端
            peak_note = f"{'+峰谷定价' if is_peak else ''}"
            return _make(RuntimeMode.CLOUD,
                f"综合评分倾向云端(local={local_score:.2f}){peak_note}",
                lw=local_score * 0.2, cw=remaining, peak_aware=True)

    # ================================================================
    # 手动控制
    # ================================================================

    def set_local_available(self, available: bool) -> None:
        self._local_available = available

    def set_cloud_available(self, available: bool) -> None:
        self._cloud_available = available

    def set_mesh_available(self, available: bool) -> None:
        self._mesh_available = available

    def refresh_health(self) -> None:
        self._local_available = self._check_ollama_health()
        self._cloud_available = self._check_cloud_health()
        mesh = self._mesh_engine
        self._mesh_available = bool(
            mesh and mesh.is_initialized and mesh.contributing
        )
        self._health_checked = True
        self._last_health_check = time.time()

    def get_stats(self) -> dict:
        mesh = self._mesh_engine
        mesh_stats = {}
        if mesh and mesh.is_initialized:
            mesh_stats = mesh.get_mesh_stats()

        return {
            "local_available": self._local_available,
            "mesh_available": self._mesh_available,
            "cloud_available": self._cloud_available,
            "health_check_ttl": self.HEALTH_CHECK_TTL,
            "last_check_age": time.time() - self._last_health_check if self._last_health_check else None,
            "cloud_health_host": self.CLOUD_HEALTH_HOST,
            "mesh": mesh_stats,
        }
