"""
自化（技能创建）API 路由

端点：
- GET  /api/v1/skills/suggestions — 待审核建议列表
- POST /api/v1/skills/suggestions/{id}/approve — 采纳建议
- POST /api/v1/skills/suggestions/{id}/reject — 拒绝建议
- POST /api/v1/skills/suggestions/{id}/modify — 修改后采纳
- POST /api/v1/skills/forge/trigger — 触发技能发现
- GET  /api/v1/skills/forge/stats — 自化引擎统计
"""

from typing import Optional

from fastapi import APIRouter, Body, Request, Query

from schemas.common import make_response, make_error

router = APIRouter(prefix="/api/v1/skills", tags=["自化·技能创建"])


@router.get("/suggestions")
async def list_suggestions(
    request: Request,
    status: Optional[str] = Query(None, description="过滤状态: pending/approved/rejected"),
):
    """获取技能建议列表"""
    rid = getattr(request.state, "request_id", "")
    try:
        from engine.skill_forge import skill_forge

        if status == "approved":
            suggestions = skill_forge.list_approved_skills()
        elif status == "rejected":
            suggestions = [
                s for s in skill_forge._suggestions.values()
                if s.status == "rejected"
            ]
        else:
            suggestions = skill_forge.list_pending_suggestions()

        return make_response({
            "total": len(suggestions),
            "suggestions": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "trigger_pattern": s.trigger_pattern,
                    "recommended_model": s.recommended_model,
                    "suggested_token_budget": s.suggested_token_budget,
                    "success_rate": s.success_rate,
                    "sample_count": s.sample_count,
                    "quality_score": s.quality_score,
                    "status": s.status,
                    "version": s.version,
                    "generated_at": s.generated_at,
                    "approved_at": s.approved_at,
                }
                for s in suggestions
            ],
        }, request_id=rid)
    except Exception as e:
        return make_error("FORGE_ERROR", str(e), request_id=rid)


@router.post("/suggestions/{suggestion_id}/approve")
async def approve_suggestion(request: Request, suggestion_id: str):
    """采纳技能建议，自动生成 SKILL.md"""
    rid = getattr(request.state, "request_id", "")
    try:
        from engine.skill_forge import skill_forge

        suggestion = skill_forge.approve(suggestion_id)
        if not suggestion:
            return make_error(
                "SUGGESTION_NOT_FOUND",
                f"建议 {suggestion_id} 不存在",
                request_id=rid,
            )

        return make_response({
            "id": suggestion.id,
            "name": suggestion.name,
            "status": suggestion.status,
            "approved_at": suggestion.approved_at,
            "message": f"技能 '{suggestion.name}' 已生成 SKILL.md",
        }, request_id=rid)
    except Exception as e:
        return make_error("FORGE_ERROR", str(e), request_id=rid)


@router.post("/suggestions/{suggestion_id}/reject")
async def reject_suggestion(
    request: Request,
    suggestion_id: str,
    feedback: Optional[str] = Body(None, embed=True),
):
    """拒绝技能建议"""
    rid = getattr(request.state, "request_id", "")
    try:
        from engine.skill_forge import skill_forge

        suggestion = skill_forge.reject(suggestion_id, feedback or "")
        if not suggestion:
            return make_error(
                "SUGGESTION_NOT_FOUND",
                f"建议 {suggestion_id} 不存在",
                request_id=rid,
            )

        return make_response({
            "id": suggestion.id,
            "status": suggestion.status,
            "message": "建议已拒绝",
        }, request_id=rid)
    except Exception as e:
        return make_error("FORGE_ERROR", str(e), request_id=rid)


@router.post("/suggestions/{suggestion_id}/modify")
async def modify_and_approve_suggestion(
    request: Request,
    suggestion_id: str,
    modifications: dict = Body(...),
):
    """修改后采纳技能建议"""
    rid = getattr(request.state, "request_id", "")
    try:
        from engine.skill_forge import skill_forge

        suggestion = skill_forge.modify_and_approve(suggestion_id, modifications)
        if not suggestion:
            return make_error(
                "SUGGESTION_NOT_FOUND",
                f"建议 {suggestion_id} 不存在",
                request_id=rid,
            )

        return make_response({
            "id": suggestion.id,
            "name": suggestion.name,
            "status": suggestion.status,
            "quality_score": suggestion.quality_score,
            "message": f"技能 '{suggestion.name}' 已修改并生成 SKILL.md",
        }, request_id=rid)
    except Exception as e:
        return make_error("FORGE_ERROR", str(e), request_id=rid)


@router.post("/forge/trigger")
async def trigger_skill_discovery(request: Request):
    """手动触发技能发现"""
    rid = getattr(request.state, "request_id", "")
    try:
        from engine.skill_forge import skill_forge

        suggestions = skill_forge.propose_all_ready()
        return make_response({
            "discovered": len(suggestions),
            "suggestions": [
                {"id": s.id, "name": s.name, "quality_score": s.quality_score}
                for s in suggestions
            ],
        }, request_id=rid)
    except Exception as e:
        return make_error("FORGE_ERROR", str(e), request_id=rid)


@router.get("/forge/stats")
async def get_forge_stats(request: Request):
    """获取自化引擎统计"""
    rid = getattr(request.state, "request_id", "")
    try:
        from engine.skill_forge import skill_forge
        stats = skill_forge.get_stats()
        return make_response(stats, request_id=rid)
    except Exception as e:
        return make_error("FORGE_ERROR", str(e), request_id=rid)


@router.post("/forge/observe")
async def observe_task(
    request: Request,
    task_type: str = Body(...),
    model: str = Body(...),
    success: bool = Body(...),
    tokens_used: int = Body(0),
    duration_ms: int = Body(0),
    workspace_id: str = Body("default"),
):
    """记录任务执行观察"""
    rid = getattr(request.state, "request_id", "")
    try:
        from engine.skill_forge import skill_forge
        skill_forge.observe(task_type, model, success, tokens_used, duration_ms, workspace_id)
        return make_response({"message": "观察已记录"}, request_id=rid)
    except Exception as e:
        return make_error("FORGE_ERROR", str(e), request_id=rid)
