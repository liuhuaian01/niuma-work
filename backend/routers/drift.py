"""
上下文漂移路由 — Context Drift Detector API — v1.8: 6维扩展

太极引擎认知三元守护者 — 检测个体对话是否偏离意图锚点。

API:
  - POST /record-intent  → 记录意图锚点（v1.8: 新增agent_role参数）
  - POST /check          → 显式触发漂移检测（v1.8: 返回6维数据）
  - POST /reaffirm       → 用户确认意图（重置漂移）
  - GET  /status         → 检测器全局状态
  - GET  /session/{id}   → 某会话的漂移详情
  - GET  /summary        → 所有活跃会话的漂移摘要
  - POST /remove-session → 删除会话记录
"""
from fastapi import APIRouter, Request
from schemas.common import make_response
from engine.context_drift import context_drift

router = APIRouter(prefix="/api/v1/drift", tags=["上下文漂移"])


@router.post("/record-intent")
async def record_intent(request: Request):
    """记录对话意图锚点。 v1.8: 新增agent_role参数。"""
    body = await request.json()
    session_id = body.get("session_id", "default")
    task_type = body.get("task_type", "")
    user_query = body.get("user_query", "")
    explicit_goals = body.get("explicit_goals")
    agent_role = body.get("agent_role", "")  # v1.8新增

    await context_drift.record_intent(
        session_id=session_id,
        task_type=task_type,
        user_query=user_query,
        explicit_goals=explicit_goals,
        agent_role=agent_role,
    )
    return make_response({"session_id": session_id, "status": "anchored"})


@router.post("/check")
async def check_drift(request: Request):
    """显式触发漂移检测。 v1.8: 返回6维数据。"""
    body = await request.json()
    session_id = body.get("session_id", "default")
    recent_messages = body.get("recent_messages")

    report = await context_drift.check_drift(
        session_id=session_id,
        recent_messages=recent_messages,
    )
    if not report:
        return make_response({"session_id": session_id, "checked": False})

    return make_response({
        "session_id": session_id,
        "drift_score": report.drift_score,
        "severity": report.severity,
        "findings": report.findings,
        "suggested_action": report.suggested_action,
        "dimensions": {
            "term_drift": report.term_drift,
            "task_drift": report.task_drift,
            "scope_drift": report.scope_drift,
            "tool_pattern_drift": report.tool_pattern_drift,
            "role_adherence_drift": report.role_adherence_drift,
            "output_length_drift": report.output_length_drift,
        },
    })


@router.post("/reaffirm")
async def reaffirm_intent(request: Request):
    """用户确认意图——重置漂移状态。"""
    body = await request.json()
    session_id = body.get("session_id", "default")
    success = await context_drift.reaffirm_intent(session_id)
    return make_response({"session_id": session_id, "reaffirmed": success})


@router.get("/status")
async def get_status():
    """获取检测器全局状态。"""
    return make_response(context_drift.get_status())


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """获取某会话的漂移详情。 v1.8: 返回6维数据。"""
    latest = context_drift.get_latest_report(session_id)
    history = context_drift.get_session_drift_history(session_id)
    return make_response({
        "session_id": session_id,
        "latest_report": {
            "drift_score": latest.drift_score,
            "severity": latest.severity,
            "findings": latest.findings,
            "suggested_action": latest.suggested_action,
            "dimensions": {
                "term_drift": latest.term_drift,
                "task_drift": latest.task_drift,
                "scope_drift": latest.scope_drift,
                "tool_pattern_drift": latest.tool_pattern_drift,
                "role_adherence_drift": latest.role_adherence_drift,
                "output_length_drift": latest.output_length_drift,
            },
        } if latest else None,
        "history": history,
    })


@router.get("/summary")
async def get_summary():
    """获取所有活跃会话的漂移摘要。"""
    return make_response(context_drift.get_drift_summary())


@router.post("/remove-session")
async def remove_session(request: Request):
    """删除会话记录（对话结束时调用）。"""
    body = await request.json()
    session_id = body.get("session_id", "")
    if not session_id:
        return make_response({"error": "session_id required"}, status_code=400)
    success = context_drift.remove_session(session_id)
    return make_response({"session_id": session_id, "removed": success})
