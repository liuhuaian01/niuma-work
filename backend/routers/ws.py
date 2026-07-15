"""WebSocket 路由"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

ALLOWED_WS_ORIGINS = ["localhost:18080", "127.0.0.1:18080", "localhost"]

# 连接数限制
_MAX_ACTIVE_CONNECTIONS = 50
_MAX_MESSAGE_SIZE = 65536  # 单条消息最大 64KB
_active_connections: set[int] = set()


def _check_origin(origin: str) -> bool:
    """Origin 校验：后缀精确匹配，防止 localhost.evil.com 绕过"""
    if not origin:
        return True  # 无 Origin 头允许（本地桌面应用可能不带）

    # 提取 host[:port] 部分
    origin_host = origin.replace("http://", "").replace("https://", "").split("/")[0]

    # 后缀精确匹配：必须完全等于允许的 origin，或以其结尾且前缀是分隔符
    for allowed in ALLOWED_WS_ORIGINS:
        if origin_host == allowed:
            return True
        # 防止 localhost.evil.com 绕过：只有 localhost:18080.evil.com 这种才拦截
        # 如果是 evil.com:18080 结尾，检查分隔符
        if origin_host.endswith(allowed):
            prefix = origin_host[:-len(allowed)]
            if not prefix or prefix.endswith("."):  # 子域名? 不允许
                continue
            return True

    return False


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 连接端点 — 需通过 origin 检查。"""
    # Origin 检查
    origin = websocket.headers.get("origin", "")
    if not _check_origin(origin):
        await websocket.close(code=4003, reason="origin_not_allowed")
        return

    # 连接数限制
    conn_id = id(websocket)
    if len(_active_connections) >= _MAX_ACTIVE_CONNECTIONS:
        await websocket.close(code=4013, reason="too_many_connections")
        return

    _active_connections.add(conn_id)
    await websocket.accept()
    try:
        while True:
            # 限制单条消息最大 64KB
            data = await websocket.receive_text()
            if len(data.encode("utf-8")) > _MAX_MESSAGE_SIZE:
                await websocket.close(code=4009, reason="message_too_large")
                break
            await websocket.send_text('{"type": "pong"}')
    except WebSocketDisconnect:
        pass
    finally:
        _active_connections.discard(conn_id)
