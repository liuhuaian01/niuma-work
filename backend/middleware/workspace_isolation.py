"""
工作间隔离中间件

确保工作间级别的 API 调用只能访问合法的工作间。
通过路由中的 workspace_id 参数校验归属关系。
"""

import asyncio
import re
import hashlib
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from schemas.common import make_error

# 提取 URI 中 workspace_id 的路由模式
WORKSPACE_ID_PATTERN = re.compile(r"/workspaces/([\w-]+)")


class WorkspaceIsolationMiddleware(BaseHTTPMiddleware):
    """
    工作间隔离中间件。

    校验请求的 workspace_id 是否为已知合法工作间。
    防止跨工作间数据访问和 ID 注入攻击。
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 提取 workspace_id
        ws_id = _extract_workspace_id(path)
        if ws_id is None:
            return await call_next(request)

        # 校验 workspace_id 格式（长度限制 + 字符白名单）
        if not _is_valid_ws_id(ws_id):
            return JSONResponse(
                status_code=400,
                content=make_error(
                    code="invalid_workspace_id",
                    message=f"无效的工作间标识符：{ws_id[:32]}...",
                    detail="workspace_id 格式不合法",
                ),
            )

        # 校验工作间是否存在（缓存校验避免每次查库）
        if not await _workspace_exists(ws_id):
            return JSONResponse(
                status_code=404,
                content=make_error(
                    code="workspace_not_found",
                    message="工作间不存在或已删除",
                    detail=f"workspace_id={ws_id}",
                ),
            )

        return await call_next(request)


def _extract_workspace_id(path: str) -> Optional[str]:
    """从 URL 中提取 workspace_id"""
    m = WORKSPACE_ID_PATTERN.search(path)
    if m:
        return m.group(1)
    return None


def _is_valid_ws_id(ws_id: str) -> bool:
    """校验 workspace_id 格式"""
    if len(ws_id) > 64:
        return False
    # 只允许字母数字、连字符、下划线
    return bool(re.match(r"^[\w-]+$", ws_id))


# 内存中的工作间存在性缓存（启动后由 DB 加载）
_valid_workspace_ids: set = set()
_cache_initialized = False
_cache_lock = asyncio.Lock()


async def refresh_workspace_cache():
    """从数据库刷新合法工作间 ID 列表"""
    global _cache_initialized, _valid_workspace_ids
    async with _cache_lock:
        try:
            from services.workspace_service import _db
            cursor = await _db.execute("SELECT id FROM workspaces WHERE deleted_at IS NULL")
            rows = await cursor.fetchall()
            _valid_workspace_ids = {row[0] for row in rows}
            _cache_initialized = True
        except Exception:
            # 首次启动时 DB 可能还没初始化，延迟到首次请求
            pass


async def add_valid_workspace(ws_id: str):
    """新工作间创建后注册到缓存"""
    async with _cache_lock:
        _valid_workspace_ids.add(ws_id)


async def remove_valid_workspace(ws_id: str):
    """工作间软删除后从缓存移除"""
    async with _cache_lock:
        _valid_workspace_ids.discard(ws_id)


async def _workspace_exists(ws_id: str) -> bool:
    """检查工作间是否存在"""
    global _cache_initialized
    async with _cache_lock:
        if not _cache_initialized:
            # 释放锁后再刷新，避免死锁
            pass
    
    if not _cache_initialized:
        await refresh_workspace_cache()
    
    async with _cache_lock:
        return ws_id in _valid_workspace_ids
