"""
涌现引擎 API — "三生万物"的前端接口

端点:
  GET  /api/v1/emergence/status          — 引擎状态概览
  GET  /api/v1/emergence/modules          — 模块注册表
  GET  /api/v1/emergence/patterns         — 行为模式列表
  GET  /api/v1/emergence/insights         — 涌现洞察
  GET  /api/v1/emergence/cross-module     — 跨模块协同图
  POST /api/v1/emergence/insights/{id}/approve  — 批准洞察
  POST /api/v1/emergence/insights/{id}/reject   — 拒绝洞察
  POST /api/v1/emergence/cycle            — 手动触发涌现周期
  GET  /api/v1/emergence/orphans          — 孤岛模块
"""

from fastapi import APIRouter, Request, HTTPException
from engine.lazy_loader import lazy_get

router = APIRouter(prefix="/api/v1/emergence", tags=["emergence"])


def _get_engine(request: Request):
    """从 app.state 获取涌现引擎实例。"""
    engine = getattr(request.app.state, "emergence", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="涌现引擎未初始化")
    return engine


@router.get("/status")
async def get_status():
    """引擎状态概览。"""
    return emergence_engine.get_status()


@router.get("/modules")
async def get_modules():
    """所有已注册模块的详情。"""
    return {"modules": emergence_engine.get_modules()}


@router.get("/patterns")
async def get_patterns(status: str = "all"):
    """检测到的行为模式。status: all|observing|confirmed|rejected|rule_created"""
    return {"patterns": emergence_engine.get_patterns(status)}


@router.get("/insights")
async def get_insights(status: str = "all"):
    """涌现洞察。status: all|new|reviewed|accepted|rejected|implemented"""
    return {"insights": emergence_engine.get_insights(status)}


@router.post("/insights/{insight_id}/approve")
async def approve_insight(insight_id: str):
    """批准一个洞察。"""
    if emergence_engine.approve_insight(insight_id):
        return {"status": "ok", "insight_id": insight_id}
    raise HTTPException(status_code=404, detail="洞察不存在")


@router.post("/insights/{insight_id}/reject")
async def reject_insight(insight_id: str):
    """拒绝一个洞察。"""
    if emergence_engine.reject_insight(insight_id):
        return {"status": "ok", "insight_id": insight_id}
    raise HTTPException(status_code=404, detail="洞察不存在")


@router.post("/cycle")
async def trigger_cycle():
    """手动触发一次涌现周期。"""
    result = await lazy_get("engine.emergence", "emergence_engine").run_emergence_cycle()
    return result


@router.get("/cross-module")
async def get_cross_module():
    """跨模块协同关系图。"""
    return lazy_get("engine.emergence", "emergence_engine").get_cross_module_graph()


@router.get("/orphans")
async def get_orphans():
    """孤岛模块列表。"""
    return {"orphans": lazy_get("engine.emergence", "emergence_engine").get_orphan_modules()}
