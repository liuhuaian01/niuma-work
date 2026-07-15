"""
Agent 身份验证中间件 (P1-7 + P1-12 + P1-19)

在 API 请求处理前验证 Agent 身份令牌。
通过 Authorization: Bearer <token> 头认证。

v1.1 (P1-12): 扩展覆盖至太极引擎路由（consciousness/models/evolution/
    goal-loop/mesh/emergence/drift/patrol/api-keys/agent-identity/swarm/
    capabilities/web-access/budget），彻底关闭认证旁路。

v1.2 (P1-19, R25): 补齐 background-tasks 和 ws 路由认证覆盖。
"""

import logging
from typing import Dict, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from schemas.common import make_error

logger = logging.getLogger(__name__)


class AgentAuthMiddleware(BaseHTTPMiddleware):
    """Agent 身份认证中间件 (v1.2)。

    三层路由：
    - PUBLIC_PATHS: 跳过认证（health/docs/onboarding/settings/dashboard）
    - AGENT_PROTECTED_PATHS: 需要 Agent 令牌（业务路由 + 引擎路由）
    - MCP_PATHS: 需要 MCP 单次令牌

    P1-12: 引擎路由（consciousness/models/evolution/goal-loop/mesh/
    emergence/drift/patrol/api-keys/agent-identity/swarm/capabilities/
    web-access/budget）现已全部纳入保护范围。

    P1-19 (R25): 新增 background-tasks 和 ws 路径覆盖。
    """

    # 跳过认证的路径前缀
    _PUBLIC_PATHS = (
        "/api/v1/health",
        "/docs",
        "/openapi.json",
        "/api/v1/onboarding",
        "/api/v1/settings",
        "/api/v1/license",
        "/api/v1/dashboard",
        # v2.1: 前端公开对接端点
        "/api/v1/files",
        "/api/v1/connections",
        "/api/v1/experts",
        "/api/v1/skills/market",    # 技能市场（只读）
        "/api/v1/models/marketplace",  # 模型市场（只读）
        "/api/v1/api-keys/status",  # API Key 状态（只读）
        "/api/v1/api-keys/configure",  # API Key 配置
        "/api/v1/memory/search",    # 记忆搜索
        "/api/v1/memory",           # 记忆概览
        "/api/v1/agent-identity/token",  # P0-1: 认证令牌签发（不能自己锁自己）
        "/api/v1/models/downloadable",   # P0-4: 可下载模型列表
        "/api/v1/models/download",       # P0-4: 触发模型下载
        "/api/v1/models/local",          # P0-4: 本地模型管理
    )

    # 需要 Agent 身份认证的路径前缀
    _AGENT_PROTECTED_PATHS = (
        "/api/v1/agents/",
        "/api/v1/chat/",
        "/api/v1/memory/",
        "/api/v1/skills/",
        "/api/v1/workspaces/",
        "/api/v1/workspaces",         # 裸路径（无尾斜杠）
        # ---- P1-12: 引擎路由纳入认证保护 ----
        "/api/v1/consciousness/",
        "/api/v1/models/",
        "/api/v1/evolution/",
        "/api/v1/goal-loop/",
        "/api/v1/mesh/",
        "/api/v1/emergence/",
        "/api/v1/drift/",
        "/api/v1/patrol/",
        "/api/v1/api-keys/",
        "/api/v1/agent-identity/",
        "/api/v1/swarm/",
        "/api/v1/capabilities/",
        "/api/v1/web-access/",
        "/api/v1/budget/",
        # ---- P1-16: 补充旁路路由器认证保护 (R20) ----
        "/api/v1/audit/",
        "/api/v1/backup/",
        "/api/v1/backup",             # 裸路径（无尾斜杠）
        "/api/v1/export/",            # 数据导出（含 chat-history）
        "/api/v1/agent-cards/",
        "/api/v1/lifecycle/",
        # ---- P1-19: R25认证缺口修复 ----
        "/api/v1/background-tasks/",    # 后台任务单任务端点
        "/api/v1/ws",                   # WebSocket 连接（无尾斜杠）
    )

    # MCP 专用路径
    _MCP_PATHS = (
        "/api/v1/mcp/",
    )

    def __init__(self, app, agent_registry=None):
        super().__init__(app)
        self._agent_registry = agent_registry
        self._enabled = True

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 公开路径跳过认证
        if any(path.startswith(p) for p in self._PUBLIC_PATHS):
            return await call_next(request)

        # 检查是否需要 Agent 认证
        needs_agent_auth = any(path.startswith(p) for p in self._AGENT_PROTECTED_PATHS)
        needs_mcp_auth = any(path.startswith(p) for p in self._MCP_PATHS)

        if not needs_agent_auth and not needs_mcp_auth:
            return await call_next(request)

        # 提取认证头
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return JSONResponse(
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
                content=make_error(
                    code="unauthorized",
                    message="缺少 Authorization 头",
                    detail="Agent 身份令牌需要通过 Bearer token 提供",
                ),
            )

        # 解析 Bearer token
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
                content=make_error(
                    code="unauthorized",
                    message="认证头格式错误",
                    detail="需要 Bearer token 格式: Authorization: Bearer <token>",
                ),
            )

        token_str = auth_header[7:].strip()
        if not token_str:
            return JSONResponse(
                status_code=401,
                content=make_error(
                    code="unauthorized",
                    message="令牌为空",
                ),
            )

        # 验证 Agent 令牌
        if needs_agent_auth and self._agent_registry:
            from engine.agent_registry import agent_registry
            registry = self._agent_registry or agent_registry
            valid, reason, agent_info = await registry.verify_token(token_str)

            if not valid:
                logger.warning("Agent 认证失败: %s (path=%s)", reason, path)
                return JSONResponse(
                    status_code=401,
                    content=make_error(
                        code="unauthorized",
                        message=f"Agent 身份验证失败: {reason}",
                    ),
                )

            # 将 Agent 信息注入 request.state
            request.state.agent_info = agent_info

        # 验证 MCP 令牌（从 app.state 获取已初始化的实例）
        if needs_mcp_auth:
            mcp_auth = getattr(request.app.state, "mcp_auth", None)
            if mcp_auth is not None:
                is_valid = await mcp_auth.validate_token(token_str)
                if not is_valid:
                    logger.warning("MCP 认证失败 (path=%s)", path)
                    return JSONResponse(
                        status_code=401,
                        content=make_error(
                            code="unauthorized",
                            message="MCP 令牌验证失败——令牌无效或已被使用",
                        ),
                    )

        return await call_next(request)
