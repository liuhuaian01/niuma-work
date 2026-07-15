"""
MCP Server 管理路由 — v1.8 新增

太极引擎工具接入层 API。
行业趋势：MCP已成为事实标准，企业平均20-50个MCP Server，需统一管理。

API:
  - GET  /servers          → 列出所有已注册的 MCP Server
  - GET  /servers/{id}     → 获取单个 Server 详情
  - POST /register         → 注册新的 MCP Server
  - POST /connect/{id}     → 连接指定 Server
  - POST /disconnect/{id}  → 断开指定 Server
  - DELETE /unregister/{id}→ 注销 Server
  - GET  /tools            → 聚合所有 Server 的工具列表
  - POST /call             → 调用工具（自动路由到正确的 Server）
  - POST /call/{server_id} → 调用指定 Server 上的工具
  - GET  /health           → 所有 Server 健康检查
  - GET  /stats            → Registry 全局统计
"""
from fastapi import APIRouter, Request
from schemas.common import make_response
from engine.lazy_loader import lazy_get

router = APIRouter(prefix="/api/v1/mcp", tags=["MCP工具接入"])


# P2-16: 启动初始化已移至 main.py lifespan，此路由器不再持有生命周期钩子


@router.get("/servers")
async def list_servers():
    """列出所有已注册的 MCP Server。"""
    return make_response(lazy_get("engine.mcp_client", "mcp_registry").list_servers())


@router.get("/servers/{server_id}")
async def get_server(server_id: str):
    """获取单个 Server 详情。"""
    data = lazy_get("engine.mcp_client", "mcp_registry").get_server(server_id)
    if not data:
        return make_response({"error": "Server not found"}, status_code=404)
    return make_response(data)


@router.post("/register")
async def register_server(request: Request):
    """注册新的 MCP Server。

    Body:
        server_id: 唯一标识
        name: 显示名称
        command: 启动命令列表（如 ["uvx", "mcp-server-filesystem", "/path"]）
        api_key: 可选——认证密钥
    """
    body = await request.json()
    server_id = body.get("server_id", "")
    name = body.get("name", "")
    command = body.get("command", [])
    api_key = body.get("api_key", "")

    if not server_id or not name:
        return make_response({"error": "server_id and name required"}, status_code=400)

    entry = await lazy_get("engine.mcp_client", "mcp_registry").register(server_id, name, command, api_key)
    return make_response(entry.to_dict())


@router.post("/connect/{server_id}")
async def connect_server(server_id: str):
    """连接指定的 MCP Server。"""
    success = await lazy_get("engine.mcp_client", "mcp_registry").connect(server_id)
    return make_response({"server_id": server_id, "connected": success})


@router.post("/disconnect/{server_id}")
async def disconnect_server(server_id: str):
    """断开指定的 MCP Server。"""
    success = await lazy_get("engine.mcp_client", "mcp_registry").disconnect(server_id)
    return make_response({"server_id": server_id, "disconnected": success})


@router.delete("/unregister/{server_id}")
async def unregister_server(server_id: str):
    """注销 MCP Server。"""
    success = await lazy_get("engine.mcp_client", "mcp_registry").unregister(server_id)
    return make_response({"server_id": server_id, "unregistered": success})


@router.get("/tools")
async def list_all_tools():
    """聚合所有已连接 Server 的工具列表。"""
    tools = await lazy_get("engine.mcp_client", "mcp_registry").list_all_tools()
    return make_response({"tools": tools, "count": len(tools)})


@router.post("/call")
async def call_tool_auto(request: Request):
    """按工具名自动路由到正确的 Server 并调用。

    Body:
        tool_name: 工具名称
        arguments: 工具参数
    """
    body = await request.json()
    tool_name = body.get("tool_name", "")
    arguments = body.get("arguments", {})

    if not tool_name:
        return make_response({"error": "tool_name required"}, status_code=400)

    result = await lazy_get("engine.mcp_client", "mcp_registry").call_tool_by_name(tool_name, arguments)
    return make_response({
        "tool_name": result.tool_name,
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "duration_ms": result.duration_ms,
    })


@router.post("/call/{server_id}")
async def call_tool_on_server(server_id: str, request: Request):
    """调用指定 Server 上的工具。

    Body:
        tool_name: 工具名称
        arguments: 工具参数
    """
    body = await request.json()
    tool_name = body.get("tool_name", "")
    arguments = body.get("arguments", {})

    if not tool_name:
        return make_response({"error": "tool_name required"}, status_code=400)

    result = await lazy_get("engine.mcp_client", "mcp_registry").call_tool(server_id, tool_name, arguments)
    return make_response({
        "server_id": server_id,
        "tool_name": result.tool_name,
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "duration_ms": result.duration_ms,
    })


@router.get("/health")
async def health_check():
    """所有 Server 健康检查。"""
    results = await lazy_get("engine.mcp_client", "mcp_registry").health_check()
    return make_response(results)


@router.get("/stats")
async def get_stats():
    """Registry 全局统计。"""
    return make_response(lazy_get("engine.mcp_client", "mcp_registry").get_stats())
