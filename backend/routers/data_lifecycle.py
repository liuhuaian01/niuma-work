"""
清风（数据生命周期）API 路由

端点：
- GET  /api/v1/lifecycle/stats     — 存储统计
- GET  /api/v1/lifecycle/policies   — 策略配置
- PUT  /api/v1/lifecycle/policies   — 更新策略
- POST /api/v1/lifecycle/patrol     — 手动触发巡检
- POST /api/v1/lifecycle/cleanup    — 手动清理
- POST /api/v1/lifecycle/purge      — 硬删除过期数据
- GET  /api/v1/lifecycle/events     — 生命周期事件历史
- GET  /api/v1/lifecycle/health     — 存储健康报告
"""

from typing import Optional

from fastapi import APIRouter, Body, Request, Query

from schemas.common import make_response, make_error

router = APIRouter(prefix="/api/v1/lifecycle", tags=["清风·数据管理"])


@router.get("/stats")
async def get_storage_stats(request: Request):
    """获取所有数据类别的存储统计"""
    rid = getattr(request.state, "request_id", "")
    try:
        from engine.data_lifecycle import data_lifecycle
        stats = await data_lifecycle.get_storage_stats()
        result = {
            cat: {
                "record_count": s.record_count,
                "size_bytes": s.size_bytes,
                "size_mb": round(s.size_bytes / 1024 / 1024, 2),
                "oldest_record": s.oldest_record,
                "newest_record": s.newest_record,
            }
            for cat, s in stats.items()
        }
        return make_response(result, request_id=rid)
    except Exception as e:
        return make_error("LIFECYCLE_ERROR", str(e), request_id=rid)


@router.get("/policies")
async def get_policies(request: Request):
    """获取生命周期策略配置"""
    rid = getattr(request.state, "request_id", "")
    try:
        from engine.data_lifecycle import data_lifecycle
        policies = data_lifecycle.get_policies()
        return make_response(policies, request_id=rid)
    except Exception as e:
        return make_error("LIFECYCLE_ERROR", str(e), request_id=rid)


@router.put("/policies/{category}")
async def update_policy(request: Request, category: str, updates: dict = Body(...)):
    """更新特定类别的生命周期策略"""
    rid = getattr(request.state, "request_id", "")
    try:
        from engine.data_lifecycle import data_lifecycle
        policy = data_lifecycle.update_policy(category, updates)
        if not policy:
            return make_error(
                "INVALID_CATEGORY",
                f"无效的数据类别: {category}",
                request_id=rid,
            )
        return make_response({
            "category": category,
            "warn_after_days": policy.warn_after_days,
            "archive_after_days": policy.archive_after_days,
            "soft_delete_after_days": policy.soft_delete_after_days,
            "max_size_mb": policy.max_size_mb,
        }, request_id=rid)
    except Exception as e:
        return make_error("LIFECYCLE_ERROR", str(e), request_id=rid)


@router.post("/patrol")
async def trigger_patrol(request: Request):
    """手动触发数据巡检"""
    rid = getattr(request.state, "request_id", "")
    try:
        from engine.data_lifecycle import data_lifecycle
        events = await data_lifecycle.patrol()
        return make_response({
            "events_triggered": len(events),
            "events": [
                {
                    "category": e.category,
                    "action": e.action,
                    "affected_count": e.affected_count,
                    "details": e.details,
                }
                for e in events
            ],
        }, request_id=rid)
    except Exception as e:
        return make_error("LIFECYCLE_ERROR", str(e), request_id=rid)


@router.post("/cleanup/{category}")
async def manual_cleanup(request: Request, category: str):
    """手动触发指定类别的数据清理"""
    rid = getattr(request.state, "request_id", "")
    try:
        from engine.data_lifecycle import data_lifecycle
        event = await data_lifecycle.manual_cleanup(category)
        return make_response({
            "category": event.category,
            "action": event.action,
            "timestamp": event.timestamp,
            "message": f"已触发 {category} 清理",
        }, request_id=rid)
    except Exception as e:
        return make_error("LIFECYCLE_ERROR", str(e), request_id=rid)


@router.post("/purge")
async def purge_deleted(
    request: Request,
    older_than_days: int = Body(30, embed=True),
):
    """硬删除超过N天的软删除记录（不可逆！）"""
    rid = getattr(request.state, "request_id", "")
    try:
        from engine.data_lifecycle import data_lifecycle
        event = await data_lifecycle.purge_deleted(older_than_days)
        return make_response({
            "action": event.action,
            "affected_count": event.affected_count,
            "timestamp": event.timestamp,
            "warning": "此操作不可逆，已软删除的数据将被永久删除",
        }, request_id=rid)
    except Exception as e:
        return make_error("LIFECYCLE_ERROR", str(e), request_id=rid)


@router.get("/events")
async def list_events(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
):
    """获取生命周期事件历史"""
    rid = getattr(request.state, "request_id", "")
    try:
        from engine.data_lifecycle import data_lifecycle
        events = data_lifecycle.get_events(limit)
        return make_response({
            "total": len(events),
            "events": events,
        }, request_id=rid)
    except Exception as e:
        return make_error("LIFECYCLE_ERROR", str(e), request_id=rid)


@router.get("/health")
async def get_health_report(request: Request):
    """获取存储健康报告"""
    rid = getattr(request.state, "request_id", "")
    try:
        from engine.data_lifecycle import data_lifecycle
        report = data_lifecycle.get_health_report()
        return make_response(report, request_id=rid)
    except Exception as e:
        return make_error("LIFECYCLE_ERROR", str(e), request_id=rid)
