"""
太极引擎 · 能力开关管理路由

提供前端可调用的能力开关 API。
"大道五十，天衍四十九，人遁其一"——用户掌控的那"一"。
"""

from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from engine.taiji import taiji

router = APIRouter(prefix="/api/v1/capabilities", tags=["capabilities"])


class CapabilityStatus(BaseModel):
    capability: str
    allowed: bool
    is_default: bool


class CapabilityToggleRequest(BaseModel):
    capability: str
    enabled: bool
    agent_id: str | None = None


@router.get("/status", response_model=list[CapabilityStatus])
async def get_capability_status(agent_id: str | None = None):
    """获取所有能力开关的当前状态。"""
    caps = ["fetch", "search", "mcp", "skills", "attachments", "memory", "subagents"]
    defaults = {
        "fetch": False, "search": False, "mcp": False,
        "skills": True, "attachments": True, "memory": True, "subagents": False
    }
    return [
        CapabilityStatus(
            capability=c,
            allowed=taiji.flags.is_allowed(c, agent_id),
            is_default=taiji.flags.is_allowed(c) == defaults[c]
        )
        for c in caps
    ]


@router.post("/toggle")
async def toggle_capability(req: CapabilityToggleRequest):
    """切换能力开关。这是用户掌握的'一'。"""
    valid = {"fetch", "search", "mcp", "skills", "attachments", "memory", "subagents"}
    if req.capability not in valid:
        raise HTTPException(status_code=400, detail=f"无效的能力名称: {req.capability}")

    if req.agent_id:
        taiji.flags.set_agent_override(req.agent_id, req.capability, req.enabled)
    else:
        setattr(taiji.flags, req.capability, req.enabled)

    return {
        "capability": req.capability,
        "enabled": req.enabled,
        "agent_id": req.agent_id,
    }


@router.post("/reset")
async def reset_capabilities(agent_id: str | None = None):
    """重置所有能力到平台默认值。任务结束后前端调用。"""
    if agent_id:
        taiji.flags.clear_agent_overrides(agent_id)
    else:
        taiji.flags.fetch = False
        taiji.flags.search = False
        taiji.flags.mcp = False
        taiji.flags.skills = True
        taiji.flags.attachments = True
        taiji.flags.memory = True
        taiji.flags.subagents = False
    return {"status": "reset", "agent_id": agent_id}
