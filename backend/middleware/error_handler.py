"""全局异常处理"""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from schemas.common import make_error

logger = logging.getLogger("niuma.error_handler")


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        rid = getattr(request.state, "request_id", "")
        return JSONResponse(
            status_code=exc.status_code,
            content=make_error(
                code="HTTP_ERROR",
                message=exc.detail,
                request_id=rid,
            ),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        from config.settings import settings
        logger.exception(f"Unhandled exception: {exc}")

        rid = getattr(request.state, "request_id", "")
        debug = getattr(settings, "DEBUG", False)
        
        # 安全策略：永远不向客户端暴露完整堆栈或内部实现细节
        detail = None
        if debug and isinstance(exc, ValueError):
            # 只暴露业务逻辑错误，限制长度防止信息泄露
            detail = str(exc)[:200]
        
        return JSONResponse(
            status_code=500,
            content=make_error(
                code="INTERNAL_ERROR",
                message="服务器内部错误",
                detail=detail,
                request_id=rid,
            ),
        )
