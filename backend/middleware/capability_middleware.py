"""
太极引擎 · 能力开关中间件

天道法则——在所有路由处理之前，检查能力开关。
"""

from __future__ import annotations
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from engine.capability_flags import CAPABILITY_ADVICES
from engine.self_healing import self_healing, InterceptEvent

# 需要检查外网访问能力的路径模式
WEB_FETCH_PATHS = ["/api/v1/chat/fetch", "/api/v1/web/fetch"]
WEB_SEARCH_PATHS = ["/api/v1/chat/search-web", "/api/v1/web/search"]
MCP_PATHS = ["/api/v1/mcp/"]


class CapabilityMiddleware(BaseHTTPMiddleware):
    """能力开关中间件——挡在所有路由之前。"""

    async def dispatch(self, request: Request, call_next):
        from engine.taiji import taiji

        path = request.url.path

        # 外网抓取检查
        if any(path.startswith(p) for p in WEB_FETCH_PATHS):
            if not taiji.flags.is_allowed("fetch"):
                self_healing.heal(InterceptEvent(
                    event_type="pi_intercept", agent_id="system", workspace_id="",
                    detail="web_fetch_blocked",
                    context={"path": path},
                ))
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "capability_blocked",
                        "capability": "web_fetch",
                        "message": CAPABILITY_ADVICES["fetch"],
                        "action": "approval_required",
                    },
                )

        # 外网搜索检查
        if any(path.startswith(p) for p in WEB_SEARCH_PATHS):
            if not taiji.flags.is_allowed("search"):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "capability_blocked",
                        "capability": "web_search",
                        "message": CAPABILITY_ADVICES["search"],
                        "action": "approval_required",
                    },
                )

        # MCP 检查
        if any(path.startswith(p) for p in MCP_PATHS):
            if not taiji.flags.is_allowed("mcp"):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "capability_blocked",
                        "capability": "mcp",
                        "message": CAPABILITY_ADVICES["mcp"],
                        "action": "approval_required",
                    },
                )

        return await call_next(request)
