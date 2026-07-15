"""技能管理路由"""

from fastapi import APIRouter, Request, Query

from schemas.common import make_response, make_error
from schemas.skill import SkillInstallRequest, SkillToggleRequest
from services.skill_service import (
    list_market_skills, install_skill,
    list_user_skills, toggle_skill, uninstall_skill,
)

router = APIRouter()


@router.get("/skills/market")
async def api_market_skills(request: Request, category: str = Query(None)):
    rid = getattr(request.state, "request_id", "")
    skills = await list_market_skills(category)
    return make_response(skills, request_id=rid)


@router.post("/skills/market/install")
async def api_install_skill(request: Request, body: SkillInstallRequest):
    rid = getattr(request.state, "request_id", "")
    try:
        result = await install_skill(body.skill_id)
        return make_response(result, request_id=rid)
    except Exception as e:
        if hasattr(e, "detail") and isinstance(e.detail, dict):
            return make_error(**e.detail, request_id=rid)
        raise


@router.get("/skills/my")
async def api_my_skills(request: Request):
    rid = getattr(request.state, "request_id", "")
    skills = await list_user_skills()
    return make_response(skills, request_id=rid)


@router.put("/skills/my/{skill_id}")
async def api_toggle_skill(request: Request, skill_id: str, body: SkillToggleRequest):
    rid = getattr(request.state, "request_id", "")
    skill = await toggle_skill(skill_id, body.enabled)
    if not skill:
        return make_error("SKILL_NOT_FOUND", "技能不存在", request_id=rid)
    return make_response(skill, request_id=rid)


@router.delete("/skills/my/{skill_id}", status_code=204)
async def api_uninstall_skill(request: Request, skill_id: str):
    rid = getattr(request.state, "request_id", "")
    removed = await uninstall_skill(skill_id)
    if not removed:
        return make_error("SKILL_NOT_FOUND", "技能不存在", request_id=rid)
    return None


# Phase 2 预留: POST /skills/upload → 上传自定义技能（含去重检测）
