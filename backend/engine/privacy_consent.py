"""
太极引擎 · 用户隐私同意管理（Privacy Consent Manager）

道法自然，人遁其一。

收集用户信息来改进产品的前提——
用户必须知晓，且能随时关闭。

核心原则：
  1. 默认关闭（opt-in）——尊重隐私优先
  2. 首次启动必须通知（toast/splash）
  3. 用户可以随时开关（设置页面）
  4. 只传元数据，不传任何用户内容
  5. 用户关闭后所有收集立即停止
  6. 开关状态持久化到本地存储

与 telemetry_hub.py 的关系：
  PrivacyConsentManager = 前端感知层（通知+设置+持久化）
  TelemetryHub = 后端执行层（收据+打包+匿名化）
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
import json
import os
import logging

from engine.telemetry_hub import telemetry_hub

logger = logging.getLogger(__name__)


class ConsentStatus(Enum):
    """隐私同意状态。"""
    UNKNOWN = "unknown"           # 尚未告知用户（首次启动）
    NOTIFIED = "notified"         # 已通知但未响应用户
    ACCEPTED = "accepted"         # 用户已同意
    DECLINED = "declined"         # 用户已拒绝
    REVOKED = "revoked"           # 曾同意后撤回


@dataclass
class PrivacyPolicy:
    """隐私政策版本记录。"""
    version: str = "v1.0"
    effective_date: str = "2026-06-23"
    summary: str = (
        "超级牛马工作台会收集以下匿名元数据来改进产品：\n"
        "  - 哪些模型组合成功率更高（如 DeepSeek V4 + Coding 任务）\n"
        "  - Smart Allocator 自动调整了哪些参数（如预算阈值）\n"
        "  - 哪些自愈规则效果好\n"
        "  - 硬件配置与模型性能的关联（仅 RAM/VRAM，无精确硬件信息）\n\n"
        "我们不会收集：\n"
        "  - ❌ 您的对话内容、文件内容、代码\n"
        "  - ❌ 您的个人身份信息\n"
        "  - ❌ 您的 API Key 或密钥\n\n"
        "每次数据包 < 1KB，完全匿名化，您可随时关闭。"
    )


class PrivacyConsentManager:
    """用户隐私同意管理器。

    工作流：
      1. 用户首次启动 → 显示 toast/splash 通知
      2. 用户选择"同意"或"拒绝"
      3. 状态持久化到本地 JSON 文件
      4. 用户可随时在设置页面更改
      5. 关闭后 TelemetryHub 停止收集且数据立即清空
    """

    CONSENT_FILE = "data/privacy_consent.json"

    def __init__(self, consent_dir: str | None = None) -> None:
        self._policy = PrivacyPolicy()
        self._consent_dir = consent_dir or "data"
        self._consent_path = os.path.join(self._consent_dir, "privacy_consent.json")
        self._status: ConsentStatus = ConsentStatus.UNKNOWN
        self._consent_time: str = ""
        self._loaded = False

    # ────────────────────────────────────────────────────────────
    # 状态加载 & 持久化
    # ────────────────────────────────────────────────────────────

    def _ensure_dir(self) -> None:
        """确保持久化目录存在。"""
        os.makedirs(self._consent_dir, exist_ok=True)

    def load(self) -> None:
        """从本地持久化文件加载隐私同意状态。"""
        if self._loaded:
            return
        self._ensure_dir()
        if os.path.exists(self._consent_path):
            try:
                with open(self._consent_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._status = ConsentStatus(data.get("status", "unknown"))
                self._consent_time = data.get("consent_time", "")
                self._policy.version = data.get("policy_version", "v1.0")
                logger.info("隐私同意已加载: %s (since %s)", self._status.value, self._consent_time)
            except Exception as e:
                logger.warning("加载隐私同意文件失败，使用默认值: %s", e)
                self._status = ConsentStatus.UNKNOWN
        else:
            logger.info("未找到隐私同意文件，首次启动")
            self._status = ConsentStatus.UNKNOWN
        self._loaded = True

        # 同步到 TelemetryHub
        self._sync_telemetry()

    def save(self) -> None:
        """持久化当前隐私同意状态。"""
        self._ensure_dir()
        data = {
            "status": self._status.value,
            "consent_time": self._consent_time,
            "policy_version": self._policy.version,
            "updated_at": datetime.now().isoformat(),
        }
        try:
            with open(self._consent_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("隐私同意已保存: %s", self._status.value)
        except Exception as e:
            logger.error("保存隐私同意文件失败: %s", e)

        # 同步到 TelemetryHub
        self._sync_telemetry()

    def _sync_telemetry(self) -> None:
        """同步同意状态到 TelemetryHub。"""
        if self._status == ConsentStatus.ACCEPTED:
            telemetry_hub.enable()
        else:
            telemetry_hub.disable()

    # ────────────────────────────────────────────────────────────
    # 前端 API
    # ────────────────────────────────────────────────────────────

    def get_consent_info(self) -> dict:
        """获取当前隐私同意状态（供前端展示）。"""
        self.load()
        return {
            "status": self._status.value,
            "consent_time": self._consent_time,
            "policy_summary": self._policy.summary,
            "policy_version": self._policy.version,
            "effective_date": self._policy.effective_date,
            "requires_notification": self._status in (ConsentStatus.UNKNOWN, ConsentStatus.NOTIFIED),
            "telemetry_active": telemetry_hub.is_enabled,
        }

    def accept(self) -> dict:
        """用户同意收集匿名元数据。"""
        self.load()
        self._status = ConsentStatus.ACCEPTED
        self._consent_time = datetime.now().isoformat()
        self.save()
        logger.info("用户已同意匿名数据收集")
        return self.get_consent_info()

    def decline(self) -> dict:
        """用户拒绝收集匿名元数据。"""
        self.load()
        self._status = ConsentStatus.DECLINED
        self._consent_time = datetime.now().isoformat()
        self.save()
        logger.info("用户已拒绝匿名数据收集")
        return self.get_consent_info()

    def revoke(self) -> dict:
        """撤回之前的同意（等同 decline）。"""
        if self._status == ConsentStatus.ACCEPTED:
            self._status = ConsentStatus.REVOKED
            self._consent_time = datetime.now().isoformat()
            self.save()
            logger.info("用户已撤回数据收集同意")
        return self.get_consent_info()

    def update_consent(self, agreed: bool) -> dict:
        """统一接口——前端设置页面回调。"""
        if agreed:
            return self.accept()
        else:
            if self._status == ConsentStatus.ACCEPTED:
                return self.revoke()
            return self.decline()

    def is_consented(self) -> bool:
        """快捷检查——用户是否已同意。"""
        self.load()
        return self._status == ConsentStatus.ACCEPTED

    # ────────────────────────────────────────────────────────────
    # 首次启动通知
    # ────────────────────────────────────────────────────────────

    def get_onboarding_data(self) -> dict | None:
        """获取首次启动通知数据。

        Returns:
            如果用户尚未被告知，返回通知内容
            如果已处理，返回 None
        """
        self.load()
        if self._status in (ConsentStatus.UNKNOWN, ConsentStatus.NOTIFIED):
            return {
                "type": "privacy_notice",
                "title": "帮助改进超级牛马",
                "message": self._policy.summary,
                "policy_version": self._policy.version,
                "actions": ["accept", "decline"],
                # 建议 toast 显示时长 8 秒
                "suggested_duration_ms": 8000,
            }
        return None

    def mark_notified(self) -> None:
        """标记用户已被告知（但不一定做出选择）。"""
        self.load()
        if self._status == ConsentStatus.UNKNOWN:
            self._status = ConsentStatus.NOTIFIED
            self.save()

    # ────────────────────────────────────────────────────────────
    # 统计
    # ────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """获取隐私同意统计。"""
        self.load()
        return {
            "status": self._status.value,
            "consent_time": self._consent_time,
            "policy_version": self._policy.version,
            "telemetry_enabled": telemetry_hub.is_enabled,
            "consent_file": self._consent_path,
            "consent_file_exists": os.path.exists(self._consent_path),
        }


# 平台唯一实例
privacy_consent = PrivacyConsentManager()
