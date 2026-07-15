"""
外网访问审批 + Token 预算——管理路由

天道法则：web_fetch/web_search 默认关闭。用户可手动开启（人遁其一）。
平台帮用户评估本地是否有答案、预估外网消耗。
"""

from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from engine.taiji import taiji
from engine.token_budget import token_budget, BudgetStatus

# 拆分为两个精确前缀的路由器（P2-15: 避免 /api/v1 过度宽泛捕获）
web_access_router = APIRouter(prefix="/api/v1/web-access", tags=["天道法则·外网访问"])
budget_router = APIRouter(prefix="/api/v1/budget", tags=["天道法则·Token预算"])


class WebAccessRequest(BaseModel):
    capability: str  # "fetch" or "search"
    reason: str = ""  # 用户说明为什么需要外网
    agent_id: str | None = None


class WebAccessResponse(BaseModel):
    allowed: bool
    suggestion: str
    local_has_answer: bool = False
    estimated_tokens: int = 0


class BudgetStatusResponse(BaseModel):
    agent_id: str
    daily_budget: int
    used_today: int
    remaining: int
    percentage: float
    can_continue: bool
    message: str
    alert_level: str


@web_access_router.post("/request", response_model=WebAccessResponse)
async def request_web_access(req: WebAccessRequest):
    """请求外网访问。返回（是否允许、建议、本地是否有答案、预估消耗）。"""
    if req.capability not in ("fetch", "search"):
        raise HTTPException(400, "无效的能力类型，仅支持 fetch/search")

    # 用户主动请求 → 记录用户意图
    if req.agent_id:
        taiji.flags.set_agent_override(req.agent_id, req.capability, True)

    # 模拟检测本地知识库/记忆系统是否有答案
    # Phase 4 接入真实 L2/L3 检索
    local_has_answer = False

    suggestion = (
        f"外网{req.capability}已开启。本次任务结束后将自动关闭。"
        if not local_has_answer
        else "本地知识库已有相关信息，建议先查看。如仍需外网补充，已为你开启。"
    )

    return WebAccessResponse(
        allowed=True,
        suggestion=suggestion,
        local_has_answer=local_has_answer,
        estimated_tokens=2000 if req.capability == "search" else 5000,
    )


@web_access_router.post("/close")
async def close_web_access(agent_id: str | None = None):
    """任务结束后关闭外网访问。"""
    if agent_id:
        taiji.flags.clear_agent_overrides(agent_id)
    else:
        taiji.flags.fetch = False
        taiji.flags.search = False
    return {"status": "closed", "message": "外网访问已关闭。天道法则恢复默认。"}


@budget_router.get("/{agent_id}", response_model=BudgetStatusResponse)
async def get_budget_status(agent_id: str):
    """查询 Agent 的 Token 预算状态。"""
    status = token_budget.check(agent_id)
    return BudgetStatusResponse(
        agent_id=status.agent_id,
        daily_budget=status.daily_budget,
        used_today=status.used_today,
        remaining=status.remaining,
        percentage=round(status.percentage, 2),
        can_continue=status.can_continue,
        message=status.message,
        alert_level=status.alert_level.value,
    )


@budget_router.post("/{agent_id}/override")
async def override_budget(agent_id: str, daily_budget: int | None = None):
    """用户手动设置预算（人遁其一）。None = 恢复默认。"""
    token_budget.set_user_budget(agent_id, daily_budget)
    return {
        "agent_id": agent_id,
        "daily_budget": token_budget.get_effective_budget(agent_id),
        "user_override": daily_budget is not None,
    }


@budget_router.get("/stats")
async def get_budget_stats():
    """获取全局预算统计。"""
    return token_budget.get_stats()
