"""
请求体大小限制中间件

防止大载荷 DDoS 攻击和内存耗尽。
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from schemas.common import make_error

# 默认限制（字节）
DEFAULT_MAX_SIZE = 10 * 1024 * 1024  # 10MB（通用）
CHAT_MAX_SIZE = 1 * 1024 * 1024      # 1MB（对话消息）
UPLOAD_MAX_SIZE = 50 * 1024 * 1024   # 50MB（文件上传、备份恢复）


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """请求体大小限制中间件。"""

    async def dispatch(self, request: Request, call_next):
        # GET/HEAD/DELETE/OPTIONS 没有请求体
        if request.method in ("GET", "HEAD", "DELETE", "OPTIONS"):
            return await call_next(request)

        path = request.url.path
        max_size = _get_max_size(path)
        content_length = request.headers.get("Content-Length")

        if content_length:
            try:
                cl = int(content_length)
                if cl > max_size:
                    return JSONResponse(
                        status_code=413,
                        content=make_error(
                            code="payload_too_large",
                            message=f"请求体过大：{_format_size(cl)}，最大允许 {_format_size(max_size)}",
                            detail=f"max={max_size}",
                        ),
                    )
            except (ValueError, TypeError):
                pass  # Content-Length 无效，由下游处理

        return await call_next(request)


def _get_max_size(path: str) -> int:
    """根据端点返回最大请求体大小"""
    if path.startswith("/api/v1/chat"):
        return CHAT_MAX_SIZE
    if path.startswith("/api/v1/backup") or "/upload" in path:
        return UPLOAD_MAX_SIZE
    return DEFAULT_MAX_SIZE


def _format_size(size: int) -> str:
    """格式化字节为可读字符串"""
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size}{unit}"
        size //= 1024
    return f"{size}TB"
