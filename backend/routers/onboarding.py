"""
对话式引导路由 (Onboarding Wizard)

5 步引导体验 (< 60s, 可跳过), 新用户首次启动时触发。
遵循太极引擎 Pi 原则：不弹窗打断，不强制填写。

步进:
  1. welcome — 打招呼 + 一句话介绍
  2. scene  — 选场景（创作/编程/分析/通用）
  3. model  — 模型偏好（国产优先 / 本地优先 / 全自动）
  4. create — 创建工作间+默认 Agent
  5. done   — 完成 + 标记引导已过
"""

import json
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from typing import Optional

from schemas.common import make_response
from config.settings import settings
from services.workspace_service import create_workspace

router = APIRouter()

# Onboarding 步骤请求模型
class OnboardingStepRequest(BaseModel):
    step: str = Field(
        ...,
        pattern=r'^(welcome|scene|model|create|done|skip)$',
        description="步骤ID"
    )
    data: dict = Field(default_factory=dict, description="步骤数据")


class SceneData(BaseModel):
    scene: str = Field(
        ...,
        pattern=r'^(novel-writing|code-dev|self-media|blank)$',
        description="场景类型"
    )


class ModelPreferenceData(BaseModel):
    preference: str = Field(
        ...,
        pattern=r'^(cloud-first|local-first|auto)$',
        description="模型偏好"
    )

SETTINGS_FILE = Path(settings.DATA_DIR) / "settings.json"

# 默认引导配置
DEFAULT_ONBOARDING = {
    "completed": False,
    "current_step": None,   # None | "welcome" | "scene" | "model" | "create" | "done"
    "scene": None,           # None | "novel-writing" | "code-dev" | "self-media" | "blank"
    "model_preference": None,  # None | "cloud-first" | "local-first" | "auto"
    "skipped": False,
}


def _load_settings() -> dict:
    """从文件加载设置"""
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_settings(data: dict):
    """保存设置到文件"""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_onboarding() -> dict:
    """获取引导状态"""
    data = _load_settings()
    ob = data.get("onboarding", DEFAULT_ONBOARDING.copy())
    # 确保字段齐全
    for k, v in DEFAULT_ONBOARDING.items():
        ob.setdefault(k, v)
    return ob


def _set_onboarding(onboarding: dict):
    """更新引导状态"""
    data = _load_settings()
    data["onboarding"] = onboarding
    _save_settings(data)


# ---------- API ----------


@router.get("/onboarding/status")
async def api_onboarding_status(request: Request):
    """获取引导状态"""
    rid = getattr(request.state, "request_id", "")
    ob = _get_onboarding()
    return make_response(ob, request_id=rid)


@router.get("/onboarding/steps")
async def api_onboarding_steps(request: Request):
    """获取所有引导步骤的配置"""
    rid = getattr(request.state, "request_id", "")
    steps = [
        {
            "id": "welcome",
            "title": "欢迎来到超级牛马",
            "description": "我是 Hermes，你的 AI 工作台管家。让我带你快速上手。",
            "actions": [
                {"label": "开始引导", "next": "scene"},
                {"label": "跳过引导", "action": "skip"},
            ],
        },
        {
            "id": "scene",
            "title": "你想做什么？",
            "description": "选一个场景，我帮你配好工作间和 AI 助手。以后随时可以改。",
            "options": [
                {"id": "novel-writing", "icon": "📝", "name": "小说创作",
                 "desc": "Director + Writer + Editor，三 Agent 协创"},
                {"id": "code-dev", "icon": "💻", "name": "代码开发",
                 "desc": "Director + Coder + Reviewer，编程协作"},
                {"id": "self-media", "icon": "📱", "name": "自媒体运营",
                 "desc": "Director + Writer + Researcher，内容创作"},
                {"id": "blank", "icon": "📄", "name": "自由模式",
                 "desc": "空白工作间，自由探索"},
            ],
            "actions": [
                {"label": "下一步", "next": "model"},
                {"label": "跳过引导", "action": "skip"},
            ],
        },
        {
            "id": "model",
            "title": "模型偏好",
            "description": "AI 模型是工作台的大脑。我推荐国产优先——省钱又稳定。",
            "options": [
                {"id": "cloud-first", "icon": "☁️", "name": "国产云端优先（推荐）",
                 "desc": "DeepSeek/Kimi/混元/GLM，省钱又好用"},
                {"id": "local-first", "icon": "💻", "name": "本地优先",
                 "desc": "Gemma-4 本地运行，数据完全不出设备"},
                {"id": "auto", "icon": "⚡", "name": "全自动",
                 "desc": "让太极引擎替你选，智能调度"},
            ],
            "actions": [
                {"label": "下一步", "next": "create"},
                {"label": "跳过引导", "action": "skip"},
            ],
        },
        {
            "id": "create",
            "title": "创建工作间",
            "description": "让我为你创建一个专属工作间和 AI 助手团队。",
            "actions": [
                {"label": "创建并开始", "next": "done", "action": "create_workspace"},
                {"label": "跳过引导", "action": "skip"},
            ],
        },
    ]
    return make_response(steps, request_id=rid)


@router.post("/onboarding/step")
async def api_onboarding_step(request: Request, body: OnboardingStepRequest):
    """提交引导步骤数据"""
    rid = getattr(request.state, "request_id", "")
    step_id = body.step
    data = body.data

    ob = _get_onboarding()

    if step_id == "scene":
        scene = data.get("scene")
        if scene and scene in ("novel-writing", "code-dev", "self-media", "blank"):
            ob["scene"] = scene
            ob["current_step"] = "scene"
    elif step_id == "model":
        pref = data.get("preference")
        if pref and pref in ("cloud-first", "local-first", "auto"):
            ob["model_preference"] = pref
            ob["current_step"] = "model"
    elif step_id == "create":
        # 执行创建工作间 + Agent
        scene = ob.get("scene") or "blank"
        model_pref = ob.get("model_preference") or "cloud-first"
        ws = await create_workspace(
            name=_scene_name(scene),
            template=scene,
        )
        ob["workspace_id"] = ws["id"]
        ob["current_step"] = "create"

        # 保存模型偏好到设置
        settings_data = _load_settings()
        settings_data.setdefault("features", {})["model_preference"] = model_pref
        _save_settings(settings_data)

    elif step_id == "done":
        ob["completed"] = True
        ob["current_step"] = "done"
    elif step_id == "skip":
        ob["completed"] = True
        ob["skipped"] = True
        ob["current_step"] = None

    _set_onboarding(ob)
    return make_response(ob, request_id=rid)


@router.post("/onboarding/skip")
async def api_onboarding_skip(request: Request):
    """跳过全部引导"""
    rid = getattr(request.state, "request_id", "")
    ob = _get_onboarding()
    ob["completed"] = True
    ob["skipped"] = True
    ob["current_step"] = None
    _set_onboarding(ob)
    return make_response(ob, request_id=rid)


@router.post("/onboarding/reset")
async def api_onboarding_reset(request: Request):
    """重置引导（调试/重新引导用）"""
    rid = getattr(request.state, "request_id", "")
    _set_onboarding(DEFAULT_ONBOARDING.copy())
    return make_response({"completed": False}, request_id=rid)


def _scene_name(scene_id: str) -> str:
    """模板 ID → 中文名"""
    names = {
        "novel-writing": "小说创作",
        "code-dev": "代码开发",
        "self-media": "自媒体运营",
        "blank": "我的工作间",
    }
    return names.get(scene_id, "我的工作间")
