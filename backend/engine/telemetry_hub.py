"""
太极引擎 · 进化回传通道（Evolution Feedback Channel）

用户端的太极引擎在自己进化，但进化的成果不应该只困在一台电脑里。

规则（不可侵犯）：
  1. 只传元数据——不传任何用户内容（对话、文件、代码）
  2. 用户必须主动开启（opt-in）——"人遁其一"
  3. 数据匿名化——不关联用户身份
  4. 每次回传的数据体积 < 1KB

回传内容：
  - 发现了什么成功模式（如 "writing+deepseek 连续 15 天成功率 95%"）
  - Smart Allocator 自调了什么参数（如 "Writer 预算 30K→35K"）
  - 哪些 Skill 被自动降权了
  - 哪些自愈规则效果好
  - 硬件配置与模型性能的关联
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import json
import hashlib


@dataclass
class EvolutionTelemetry:
    """一次进化回传——只含元数据，不含用户内容。"""
    timestamp: str
    platform_version: str = "v1.6"

    # 引擎发现
    discovered_patterns: list[dict] = field(default_factory=list)
    # [{"name": "writing+deepseek", "success_rate": 0.95, "sample_count": 15}]

    # 自动变更
    auto_changes: list[dict] = field(default_factory=list)
    # [{"type": "budget", "agent": "writer", "old": 30000, "new": 35000}]

    # Skill 生态
    skill_changes: list[dict] = field(default_factory=list)
    # [{"name": "auto-seo", "action": "demoted", "reason": "low_success_rate"}]

    # 自愈效果
    healing_stats: dict = field(default_factory=dict)
    # {"total_events": 12, "success_rate": 0.75}

    # Token 节约
    savings: dict = field(default_factory=dict)
    # {"today_saved": 45000, "savings_rate": 0.28}

    # 硬件信息（用于模型推荐关联分析）
    hardware: dict = field(default_factory=dict)
    # {"ram_gb": 16, "vram_gb": 8, "local_models": ["gemma-4", "qwen-vl"]}

    # 设备指纹（SHA256(hostname+install_id) → 纯匿名字符串）
    device_hash: str = ""


class TelemetryHub:
    """进化回传中枢。

    收集本地的进化成果，打包成 < 1KB 的元数据包。
    用户决定是否回传（默认关闭）。
    """

    MAX_PACKET_SIZE = 1024  # 1KB

    def __init__(self, install_id: str = "local") -> None:
        import socket
        self._install_id = install_id
        self._device_hash = hashlib.sha256(
            f"{socket.gethostname()}:{install_id}".encode()
        ).hexdigest()[:16]
        self._enabled: bool = False  # 用户必须主动开启（opt-in）——"人遁其一"
        self._last_sync: str = ""
        self._queue: list[EvolutionTelemetry] = []

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def collect(
        self, patterns: list[dict] | None = None,
        auto_changes: list[dict] | None = None,
        skill_changes: list[dict] | None = None,
        healing: dict | None = None,
        savings: dict | None = None,
        hardware: dict | None = None,
    ) -> Optional[EvolutionTelemetry]:
        """收集本地的进化数据，打包成一个回传包。
        
        用户未开启（opt-in）时不收集，返回 None。
        """
        if not self._enabled:
            return None
        packet = EvolutionTelemetry(
            timestamp=datetime.now().isoformat(),
            discovered_patterns=patterns or [],
            auto_changes=auto_changes or [],
            skill_changes=skill_changes or [],
            healing_stats=healing or {},
            savings=savings or {},
            hardware=hardware or {},
            device_hash=self._device_hash,
        )
        self._queue.append(packet)
        return packet

    def export_payload(self) -> str:
        """导出为 JSON 字符串——可直接发送到远程端点。"""
        if not self._enabled:
            return "{}"

        if not self._queue:
            return "{}"

        # 取最近一条
        payload = asdict(self._queue[-1])
        # 确保 < 1KB
        json_str = json.dumps(payload, ensure_ascii=False)
        if len(json_str) > self.MAX_PACKET_SIZE:
            # 截断模式发现和变更记录
            payload["discovered_patterns"] = payload["discovered_patterns"][:3]
            payload["auto_changes"] = payload["auto_changes"][:3]
            json_str = json.dumps(payload, ensure_ascii=False)

        self._last_sync = datetime.now().isoformat()
        return json_str

    def get_stats(self) -> dict:
        return {
            "enabled": self._enabled,
            "device_hash": self._device_hash,
            "queued_packets": len(self._queue),
            "last_sync": self._last_sync,
            "packet_size_limit": f"{self.MAX_PACKET_SIZE} bytes",
        }


# 平台唯一实例
telemetry_hub = TelemetryHub()
