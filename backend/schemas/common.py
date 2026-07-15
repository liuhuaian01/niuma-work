"""
通用响应模型
"""

from typing import Any, Optional, Generic, TypeVar
from pydantic import BaseModel
from datetime import datetime, timezone


T = TypeVar("T")


class ResponseMeta(BaseModel):
    request_id: str
    timestamp: str


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    meta: Optional[ResponseMeta] = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    detail: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    meta: Optional[ResponseMeta] = None


def make_response(data: Any, request_id: str = "") -> dict:
    """构建成功响应"""
    return {
        "success": True,
        "data": data,
        "meta": {
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    }


def make_paginated_response(
    data: list, page: int, page_size: int, total: int, request_id: str = ""
) -> dict:
    """构建分页响应"""
    return {
        "success": True,
        "data": data,
        "meta": {
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": max(1, (total + page_size - 1) // page_size),
            },
        },
    }


def make_error(code: str, message: str, detail: str = "", request_id: str = "") -> dict:
    """构建错误响应"""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "detail": detail,
        },
        "meta": {
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    }
