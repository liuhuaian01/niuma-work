"""
连接管理路由 — 前端对接

提供 MCP 连接列表和健康检查的基础端点。
从 MCP Registry 和 agent_card 注册表中获取数据。
"""

from fastapi import APIRouter, Request

from schemas.common import make_response, make_error
from engine.lazy_loader import lazy_get

router = APIRouter()


@router.get("/connections")
async def api_list_connections(request: Request):
    """列出所有已注册的 MCP 连接/服务器"""
    rid = getattr(request.state, "request_id", "")

    connections = []

    # 从 MCP Registry 获取已注册的服务器列表
    try:
        mcp_registry = lazy_get("engine.mcp_client", "mcp_registry")
        servers = mcp_registry.list_servers() if mcp_registry else []
        for s in servers:
            connections.append({
                "id": s.get("id", s.get("name", "")),
                "name": s.get("name", s.get("display_name", "")),
                "type": "mcp",
                "status": s.get("status", "unknown"),
                "provider": s.get("provider", ""),
                "description": s.get("description", ""),
                "created_at": s.get("created_at", ""),
            })
    except Exception:
        pass  # MCP Registry 可能未初始化

    # 从 Agent Card 注册表获取活跃的 Agent
    try:
        from engine.agent_card import agent_card_registry
        if agent_card_registry and agent_card_registry._initialized:
            cards = agent_card_registry.list_all() if hasattr(agent_card_registry, 'list_all') else []
            for c in cards:
                if hasattr(c, 'id'):
                    connections.append({
                        "id": str(c.id),
                        "name": getattr(c, 'name', str(c.id)),
                        "type": "agent",
                        "status": "active",
                        "provider": getattr(c, 'provider', ''),
                        "description": getattr(c, 'description', ''),
                    })
    except Exception:
        pass

    return make_response({"connections": connections, "count": len(connections)}, request_id=rid)


@router.get("/connections/{connection_id}/health")
async def api_connection_health(request: Request, connection_id: str):
    """检查指定连接的健康状态"""
    rid = getattr(request.state, "request_id", "")

    # 尝试从 MCP Registry 找到连接
    try:
        mcp_registry = lazy_get("engine.mcp_client", "mcp_registry")
        if mcp_registry:
            servers = mcp_registry.list_servers()
            for s in servers:
                sid = s.get("id", s.get("name", ""))
                if sid == connection_id:
                    return make_response({
                        "id": connection_id,
                        "status": s.get("status", "connected"),
                        "healthy": s.get("status") in ("connected", "active", "ready"),
                        "checked_at": "",
                    }, request_id=rid)
    except Exception:
        pass

    return make_response({
        "id": connection_id,
        "status": "unknown",
        "healthy": False,
        "message": "连接未注册或不可达",
    }, request_id=rid)
