"""用户设置路由"""

import json
from pathlib import Path

from fastapi import APIRouter, Request

from schemas.common import make_response
from schemas.settings_schema import SettingsUpdate
from config.settings import settings
from engine.privacy_consent import privacy_consent
from engine.lazy_loader import lazy_get


router = APIRouter()

# 设置文件路径
SETTINGS_FILE = Path(settings.DATA_DIR) / "settings.json"

# 默认设置
DEFAULT_SETTINGS = {
    "profile": {"name": "牛马君", "avatar": "🐮", "bio": ""},
    "appearance": {"theme": "dark", "font_size": "medium", "language": "zh-CN"},
    "features": {"pi_rules": True, "agent_always_on": False, "memory_sync": False},
    "limits": {
        "workspace_limit": settings.FREE_WORKSPACE_LIMIT,
        "agent_limit_per_workspace": settings.AGENT_LIMIT_PER_WORKSPACE,
    },
    "privacy": {
        "telemetry_enabled": False,       # 默认关闭
        "consent_status": "unknown",
        "consent_time": "",
        "policy_version": "v1.0",
    },
}


def _load_settings() -> dict:
    """从文件加载设置"""
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_SETTINGS.copy()


def _save_settings(data: dict):
    """保存设置到文件"""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("/settings")
async def api_get_settings(request: Request):
    rid = getattr(request.state, "request_id", "")
    data = _load_settings()
    return make_response(data, request_id=rid)


@router.put("/settings")
async def api_update_settings(request: Request, body: SettingsUpdate):
    rid = getattr(request.state, "request_id", "")
    current = _load_settings()

    # 深度合并
    if body.profile:
        current.setdefault("profile", {}).update(
            {k: v for k, v in body.profile.model_dump().items() if v is not None}
        )
    if body.appearance:
        current.setdefault("appearance", {}).update(
            {k: v for k, v in body.appearance.model_dump().items() if v is not None}
        )
    if body.features:
        current.setdefault("features", {}).update(
            {k: v for k, v in body.features.model_dump().items() if v is not None}
        )

    _save_settings(current)
    return make_response(current, request_id=rid)


# ============================================================
# 隐私设置 API
# ============================================================

@router.get("/settings/privacy")
async def api_get_privacy(request: Request):
    """获取隐私设置状态（含首次启动通知数据）。"""
    rid = getattr(request.state, "request_id", "")
    info = privacy_consent.get_consent_info()
    return make_response(info, request_id=rid)


@router.put("/settings/privacy")
async def api_update_privacy(request: Request):
    """更新隐私设置。

    Request body: {"telemetry_enabled": true|false}
    """
    rid = getattr(request.state, "request_id", "")
    body = await request.json()
    agreed = body.get("telemetry_enabled", False)
    result = privacy_consent.update_consent(agreed)

    # 同步到 settings.json
    current = _load_settings()
    current.setdefault("privacy", {}).update({
        "telemetry_enabled": agreed,
        "consent_status": result["status"],
        "consent_time": result.get("consent_time", ""),
        "policy_version": result.get("policy_version", "v1.0"),
    })
    _save_settings(current)

    return make_response(result, request_id=rid)


@router.post("/settings/privacy/onboarding")
async def api_mark_privacy_notified(request: Request):
    """标记隐私通知已展示（首次启动时调用）。"""
    rid = getattr(request.state, "request_id", "")
    privacy_consent.mark_notified()
    return make_response({"notified": True}, request_id=rid)
