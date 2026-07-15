"""健康检查路由"""

import logging
import time

from fastapi import APIRouter, Request
from sqlalchemy import text

from schemas.common import make_response
from model_adapter.registry import model_registry
from version import VERSION

router = APIRouter()
logger = logging.getLogger("niuma.health")

# 应用启动时间
_start_time = time.time()


@router.get("/health")
async def health_check(request: Request):
    """服务健康检查"""
    rid = getattr(request.state, "request_id", "")

    # 初始化模型注册
    model_registry.initialize()

    # 获取模型状态
    models_status = model_registry.list_models_status()
    models_available = [m["id"] for m in models_status if m["configured"]]

    uptime = int(time.time() - _start_time)

    # 真实验证 DB 连接
    db_ok = False
    try:
        from db.database import get_engine
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        logger.warning("DB health check failed", exc_info=True)

    return make_response(
        {
            "status": "healthy" if db_ok else "degraded",
            "version": VERSION,
            "db_connected": db_ok,
            "uptime_seconds": uptime,
            "models_available": models_available,
            "models_status": models_status,
        },
        request_id=rid,
    )
