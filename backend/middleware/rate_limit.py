"""
请求速率限制中间件

基于 IP 的滑动窗口限流，防止暴力请求和 DoS。
生产环境建议替换为 Redis 方案（当前内存实现满足桌面端单用户需求）。
"""

import time
from collections import defaultdict
from typing import Dict, List

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from schemas.common import make_error


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    滑动窗口限流器。

    配置:
    - window_seconds: 时间窗口（秒）
    - max_requests: 窗口内最大请求数
    不同端点可设不同限流策略。
    """

    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.window_seconds = kwargs.get("window_seconds", 60)
        self.max_requests = kwargs.get("max_requests", 120)
        self._store: Dict[str, List[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # 健康检查/文档不受限流
        path = request.url.path
        if path.startswith(("/health", "/docs", "/openapi.json")):
            return await call_next(request)

        client_ip = _get_client_ip(request)
        now = time.time()

        # 根据端点调整限流策略
        limits = self._get_limits(path)
        key = f"{client_ip}:{limits['route_group']}"
        bucket = self._store[key]

        # 清理过期记录
        window_start = now - self.window_seconds
        while bucket and bucket[0] < window_start:
            bucket.pop(0)

        if len(bucket) >= limits["max_requests"]:
            retry_after = int(self.window_seconds - (now - bucket[0]))
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(max(1, retry_after))},
                content=make_error(
                    code="rate_limit_exceeded",
                    message=f"请求过于频繁，请在 {max(1, retry_after)} 秒后重试",
                    detail=f"max={limits['max_requests']} per {self.window_seconds}s",
                ),
            )

        bucket.append(now)
        return await call_next(request)

    def _get_limits(self, path: str) -> dict:
        """根据端点返回限流策略"""
        if "/chat/stream" in path:
            return {"route_group": "chat_stream", "max_requests": self.max_requests // 2}
        if path.startswith("/api/v1/chat"):
            return {"route_group": "chat", "max_requests": self.max_requests // 4}
        if path.startswith("/api/v1/memory"):
            return {"route_group": "memory", "max_requests": self.max_requests // 2}
        return {"route_group": "default", "max_requests": self.max_requests}


def _get_client_ip(request: Request) -> str:
    """获取客户端真实 IP（处理反向代理场景）"""
    x_forwarded = request.headers.get("X-Forwarded-For")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    x_real = request.headers.get("X-Real-IP")
    if x_real:
        return x_real.strip()
    client = request.client
    return client.host if client else "127.0.0.1"
