"""
太极引擎 · 意识路由

前端可读取每日意识摘要——太极引擎在反思后自动生成。
"""

from __future__ import annotations
from fastapi import APIRouter

from engine.chat_hooks import chat_integration

router = APIRouter(prefix="/api/v1/consciousness", tags=["意识"])


@router.get("/today")
async def get_today_consciousness():
    """获取今日意识摘要。"""
    return chat_integration.daily_reflection()


@router.get("/recent")
async def get_recent_consciousness(days: int = 7):
    """获取近 N 天意识。"""
    records = chat_integration.logger.get_recent(days)
    reflection = chat_integration.reflection.reflect(records)
    return {
        "date_range": f"近{days}天",
        "total_executions": reflection.total_executions,
        "success_rate": reflection.success_rate,
        "recommended_actions": reflection.recommended_actions,
        "summary": chat_integration.reflection.consciousness_summary(reflection),
    }


@router.get("/health")
async def get_engine_health():
    """获取太极引擎所有模块的健康状态。"""
    from engine.engine_watchdog import watchdog
    return watchdog.get_stats()
