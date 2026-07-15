"""备份管理路由"""

import os
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from schemas.common import make_response, make_error
from services.backup_service import (
    list_backups, create_backup, get_backup_download_path, restore_backup, _get_backup_dir,
)

router = APIRouter()


@router.get("/backup")
async def api_list_backups(request: Request):
    rid = getattr(request.state, "request_id", "")
    data = await list_backups()
    return make_response(data, request_id=rid)


@router.post("/backup")
async def api_create_backup(request: Request):
    rid = getattr(request.state, "request_id", "")
    data = await create_backup()
    return make_response(data, request_id=rid)


@router.get("/backup/{backup_id}/download")
async def api_download_backup(request: Request, backup_id: str):
    """下载备份文件（含路径遍历防护）"""
    path = await get_backup_download_path(backup_id)
    if not path or not os.path.exists(path):
        return make_error("BACKUP_FAILED", "备份文件不存在")
    # 路径遍历防护
    if not str(os.path.abspath(path)).startswith(str(os.path.abspath(_get_backup_dir()))):
        return make_error("BACKUP_FAILED", "备份文件不存在")
    return FileResponse(path, media_type="application/zip", filename=os.path.basename(path))


@router.post("/backup/restore")
async def api_restore_backup(request: Request):
    rid = getattr(request.state, "request_id", "")
    return make_response(
        {"status": "not_implemented", "message": "还原功能将在 Phase 2 实现"},
        request_id=rid,
    )


@router.get("/export/chat-history")
async def export_chat_history(request: Request, workspace_id: str = "global"):
    """导出聊天历史为 JSON — 用户有权随时带走自己的数据。"""
    rid = getattr(request.state, "request_id", "")
    from db.database import get_engine
    from sqlalchemy import text
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT role, content, model, created_at FROM chat_messages WHERE workspace_id = :ws ORDER BY created_at"),
            {"ws": workspace_id},
        )
        rows = [{"role": r[0], "content": r[1][:500], "model": r[2], "time": str(r[3])} for r in result.fetchall()]

    return make_response({
        "workspace_id": workspace_id,
        "total_messages": len(rows),
        "messages": rows,
        "exported_at": __import__('datetime').datetime.now().isoformat(),
    }, request_id=rid)
