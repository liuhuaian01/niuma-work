"""
文件管理路由 — 前端对接

提供文件列表和上传的基础端点。
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Request, UploadFile, File as FastAPIFile

from schemas.common import make_response, make_error
from config.settings import settings

router = APIRouter()

# 文件存储目录
UPLOAD_DIR = Path(settings.DATA_DIR) / "uploads"


def _ensure_upload_dir():
    """确保上传目录存在"""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/files")
async def api_list_files(request: Request):
    """列出上传目录中的所有文件"""
    rid = getattr(request.state, "request_id", "")
    _ensure_upload_dir()

    files = []
    try:
        for entry in sorted(UPLOAD_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if entry.is_file():
                stat = entry.stat()
                files.append({
                    "id": entry.name,
                    "name": entry.name,
                    "size": stat.st_size,
                    "type": entry.suffix.lower(),
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
    except Exception as e:
        return make_error("FILE_LIST_ERROR", f"文件列表读取失败: {str(e)}", request_id=rid)

    return make_response({"files": files, "count": len(files)}, request_id=rid)


@router.post("/files/upload")
async def api_upload_file(request: Request, file: UploadFile = FastAPIFile(...)):
    """上传文件"""
    rid = getattr(request.state, "request_id", "")
    _ensure_upload_dir()

    if not file.filename:
        return make_error("INVALID_FILE", "文件名不能为空", request_id=rid)

    # 安全检查：防止路径遍历
    safe_name = Path(file.filename).name
    dest = UPLOAD_DIR / safe_name

    try:
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        return make_error("UPLOAD_FAILED", f"文件写入失败: {str(e)}", request_id=rid)

    return make_response({
        "id": safe_name,
        "name": safe_name,
        "size": dest.stat().st_size,
        "type": dest.suffix.lower(),
    }, request_id=rid)


@router.delete("/files/{filename}")
async def api_delete_file(request: Request, filename: str):
    """删除文件"""
    rid = getattr(request.state, "request_id", "")
    _ensure_upload_dir()

    safe_name = Path(filename).name
    filepath = UPLOAD_DIR / safe_name

    if not filepath.exists():
        return make_error("FILE_NOT_FOUND", "文件不存在", request_id=rid)

    try:
        filepath.unlink()
    except Exception as e:
        return make_error("DELETE_FAILED", f"文件删除失败: {str(e)}", request_id=rid)

    return make_response({"deleted": safe_name}, request_id=rid)
