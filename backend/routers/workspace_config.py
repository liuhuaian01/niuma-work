"""工作间配置路由"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from sqlalchemy import text

from db.database import get_engine
from schemas.common import make_response, make_error
from schemas.workspace import WorkspaceConfigUpdate
from utils import utc_now

router = APIRouter()


@router.get("/workspaces/{workspace_id}/config")
async def api_get_config(request: Request, workspace_id: str):
    rid = getattr(request.state, "request_id", "")
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT * FROM workspace_configs WHERE workspace_id = :ws_id"),
            {"ws_id": workspace_id},
        )
        row = result.fetchone()
        if not row:
            return make_error("WORKSPACE_NOT_FOUND", "工作间不存在", request_id=rid)

        config = dict(row._mapping)
        config.pop("id", None)
        # 将 auto_summary 从 int 转为 bool
        if "auto_summary" in config:
            config["auto_summary"] = bool(config["auto_summary"])
        return make_response(config, request_id=rid)


@router.put("/workspaces/{workspace_id}/config")
async def api_update_config(request: Request, workspace_id: str, body: WorkspaceConfigUpdate):
    rid = getattr(request.state, "request_id", "")
    engine = get_engine()
    now = _utc_now()
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT id FROM workspace_configs WHERE workspace_id = :ws_id"),
            {"ws_id": workspace_id},
        )
        row = result.fetchone()
        if not row:
            return make_error("WORKSPACE_NOT_FOUND", "工作间不存在", request_id=rid)

        set_clauses = []
        params = {"ws_id": workspace_id, "now": now}
        updates = body.model_dump(exclude_none=True)

        for field, value in updates.items():
            if field == "auto_summary":
                set_clauses.append(f"{field} = :{field}")
                params[field] = 1 if value else 0
            else:
                set_clauses.append(f"{field} = :{field}")
                params[field] = value

        if set_clauses:
            set_clauses.append("updated_at = :now")
            sql = f"UPDATE workspace_configs SET {', '.join(set_clauses)} WHERE workspace_id = :ws_id"
            await conn.execute(text(sql), params)

    # 返回更新后的配置
    engine2 = get_engine()
    async with engine2.connect() as conn:
        result = await conn.execute(
            text("SELECT * FROM workspace_configs WHERE workspace_id = :ws_id"),
            {"ws_id": workspace_id},
        )
        row = result.fetchone()
        config = dict(row._mapping)
        config.pop("id", None)
        if "auto_summary" in config:
            config["auto_summary"] = bool(config["auto_summary"])
        return make_response(config, request_id=rid)
