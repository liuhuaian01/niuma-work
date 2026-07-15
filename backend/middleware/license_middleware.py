"""
许可证中间件

在所有 API 请求之前检查用户是否有权使用产品。
试用期内 or 许可证有效 → 放行。否则 → 返回 402。
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from schemas.common import make_error

# 不需要许可证检查的路径
PUBLIC_PATHS = [
    "/health",
    "/api/v1/license",
    "/api/v1/license/activate",
    "/docs",
    "/openapi.json",
]


class LicenseMiddleware(BaseHTTPMiddleware):
    """许可证中间件——保护所有非公开路径。"""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 公开路径跳过检查
        if any(path.startswith(p) for p in PUBLIC_PATHS):
            return await call_next(request)

        # 许可证检查
        from services.user_manager import user_manager

        if not user_manager.can_use:
            trial_left = user_manager.trial_days_left
            msg = f"免费试用已到期（{trial_left}天前）。请购买会员继续使用。" if trial_left == 0 else "请先激活产品"
            return JSONResponse(
                status_code=402,
                content=make_error(
                    code="license_required",
                    message=msg,
                    detail=f"trial_days_left={trial_left}",
                ),
            )

        return await call_next(request)
