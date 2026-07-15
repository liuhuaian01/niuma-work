"""
进化路由 — 递归自进化 + 进化回传

v1.7: 新增 RecursiveEvolutionEngine API
  - GET  /status         → 引擎状态
  - GET  /consciousness  → 意识流
  - GET  /trend          → 进化趋势
  - POST /trigger        → 手动触发进化周期
  - GET  /daily          → 今日日周期
  - GET  /history        → 进化历史

原有回传端点保留：
  - GET  /telemetry/status
  - POST /telemetry/enable
  - POST /telemetry/disable
  - GET  /telemetry/payload
"""
from fastapi import APIRouter, Request, Query

from schemas.common import make_response
from engine.lazy_loader import lazy_get

router = APIRouter(prefix="/api/v1/evolution", tags=["进化"])


# ============================================================
# 递归自进化 API
# ============================================================

@router.get("/status")
async def get_evolution_status(request: Request):
    """获取递归自进化引擎当前状态。"""
    return make_response(lazy_get("engine.recursive_evolution", "recursive_evolution").get_status())


@router.get("/consciousness")
async def get_consciousness(request: Request, limit: int = Query(20, ge=1, le=100)):
    """获取意识流——引擎的"自我感知"事件时间线。"""
    return make_response({
        "events": lazy_get("engine.recursive_evolution", "recursive_evolution").get_consciousness(limit),
        "total": len(lazy_get("engine.recursive_evolution", "recursive_evolution")._consciousness),
    })


@router.get("/trend")
async def get_evolution_trend(request: Request):
    """获取进化趋势数据——成功率/Token消耗/模式发现。"""
    return make_response(lazy_get("engine.recursive_evolution", "recursive_evolution").get_trend())


@router.post("/trigger")
async def trigger_evolution(request: Request):
    """手动触发一次进化周期（调试/紧急场景）。"""
    reason = "api_manual"
    try:
        body = await request.json()
        reason = body.get("reason", reason)
    except Exception:
        pass

    cycle = await lazy_get("engine.recursive_evolution", "recursive_evolution").trigger_manual_cycle(reason)
    return make_response({
        "cycle_id": cycle.id,
        "findings": cycle.findings,
        "changes_applied": cycle.changes_applied,
        "success": cycle.success,
    })


@router.get("/daily")
async def get_daily_cycle(request: Request):
    """获取今日的每日进化周期结果（如有）。"""
    daily = lazy_get("engine.recursive_evolution", "recursive_evolution").get_daily()
    if daily:
        return make_response(daily)
    return make_response({"message": "今日尚未执行日周期", "available": False})


@router.get("/history")
async def get_evolution_history(request: Request, limit: int = Query(10, ge=1, le=50)):
    """获取进化周期历史。"""
    return make_response({
        "cycles": lazy_get("engine.recursive_evolution", "recursive_evolution").get_history(limit),
        "total": len(lazy_get("engine.recursive_evolution", "recursive_evolution")._evolution_history),
    })


# ============================================================
# 回传 API（保留）
# ============================================================

@router.get("/telemetry/status")
async def get_telemetry_status(request: Request):
    """查看回传状态——是否开启、有哪些待回传数据。"""
    return make_response(lazy_get("engine.telemetry_hub", "telemetry_hub").get_stats())


@router.post("/telemetry/enable")
async def enable_telemetry(request: Request):
    """开启进化回传——将本地发现分享给平台。
    只传元数据（模式发现、参数调整），不传任何用户内容。
    默认关闭——人遁其一。
    """
    lazy_get("engine.telemetry_hub", "telemetry_hub").enable()
    return make_response({"status": "enabled", "message": "进化回传已开启。仅回传引擎元数据，不含任何对话/文件内容。"})


@router.post("/telemetry/disable")
async def disable_telemetry(request: Request):
    lazy_get("engine.telemetry_hub", "telemetry_hub").disable()
    return make_response({"status": "disabled"})


@router.get("/telemetry/payload")
async def view_payload(request: Request):
    """查看即将回传的数据包内容——用户可以审查。"""
    payload = lazy_get("engine.telemetry_hub", "telemetry_hub").export_payload()
    return make_response({"payload": payload, "empty": payload == "{}"})
