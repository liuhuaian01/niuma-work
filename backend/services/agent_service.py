"""Agent 服务层"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from db.database import get_engine
from config.settings import settings
from utils import utc_now


async def list_agents(workspace_id: str) -> list:
    """列出工作间所有 Agent"""
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT id, workspace_id, name, role, icon, model, system_prompt, "
                "temperature, max_tokens, status, sort_order, created_at, updated_at "
                "FROM agents WHERE workspace_id = :ws_id AND deleted_at IS NULL "
                "ORDER BY sort_order"
            ),
            {"ws_id": workspace_id},
        )
        return [dict(r._mapping) for r in result]


async def add_agent(workspace_id: str, data: dict) -> dict:
    """添加 Agent"""
    engine = get_engine()
    agent_id = f"agent-{uuid.uuid4().hex[:12]}"
    now = _utc_now()

    async with engine.begin() as conn:
        # 检查工作间存在
        ws = await conn.execute(
            text("SELECT id FROM workspaces WHERE id = :id AND deleted_at IS NULL"),
            {"id": workspace_id},
        )
        if not ws.fetchone():
            from fastapi import HTTPException
            raise HTTPException(status_code=404,
                                detail={"code": "WORKSPACE_NOT_FOUND", "message": "工作间不存在"})

        # 检查 Agent 限额
        count_result = await conn.execute(
            text("SELECT COUNT(*) FROM agents WHERE workspace_id = :ws_id AND deleted_at IS NULL"),
            {"ws_id": workspace_id},
        )
        if count_result.scalar() >= settings.AGENT_LIMIT_PER_WORKSPACE:
            from fastapi import HTTPException
            raise HTTPException(status_code=409,
                                detail={"code": "AGENT_LIMIT_EXCEEDED",
                                        "message": f"每个工作间最多 {settings.AGENT_LIMIT_PER_WORKSPACE} 个 Agent"})

        # 检查角色重复（custom 除外）
        if data.get("role") != "custom":
            dup = await conn.execute(
                text("SELECT id FROM agents WHERE workspace_id = :ws_id "
                     "AND role = :role AND deleted_at IS NULL"),
                {"ws_id": workspace_id, "role": data["role"]},
            )
            if dup.fetchone():
                from fastapi import HTTPException
                raise HTTPException(status_code=409,
                                    detail={"code": "AGENT_DUPLICATE_ROLE",
                                            "message": f"角色 '{data['role']}' 已存在"})

        # 确定排序
        max_sort = await conn.execute(
            text("SELECT COALESCE(MAX(sort_order), -1) FROM agents "
                 "WHERE workspace_id = :ws_id AND deleted_at IS NULL"),
            {"ws_id": workspace_id},
        )
        sort_order = max_sort.scalar() + 1

        params = {
            "id": agent_id, "ws_id": workspace_id,
            "name": data["name"], "role": data["role"],
            "icon": data.get("icon", "🤖"),
            "model": data.get("model", "deepseek-v4-pro"),
            "prompt": data.get("system_prompt", ""),
            "temp": data.get("temperature", 0.7),
            "max_tok": data.get("max_tokens", 4096),
            "status": "offline", "sort": sort_order, "now": now,
        }

        await conn.execute(
            text(
                "INSERT INTO agents (id, workspace_id, name, role, icon, model, "
                "system_prompt, temperature, max_tokens, status, sort_order, "
                "created_at, updated_at) "
                "VALUES (:id, :ws_id, :name, :role, :icon, :model, :prompt, "
                ":temp, :max_tok, :status, :sort, :now, :now)"
            ),
            params,
        )

    return {
        "id": agent_id, "workspace_id": workspace_id,
        "name": data["name"], "role": data["role"],
        "icon": data.get("icon", "🤖"),
        "model": data.get("model", "deepseek-v4-pro"),
        "system_prompt": data.get("system_prompt"),
        "temperature": data.get("temperature", 0.7),
        "max_tokens": data.get("max_tokens", 4096),
        "status": "offline", "sort_order": sort_order,
        "created_at": now, "updated_at": now,
    }


async def update_agent(workspace_id: str, agent_id: str, updates: dict) -> dict | None:
    """更新 Agent"""
    engine = get_engine()
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT id FROM agents WHERE id = :aid AND workspace_id = :ws_id AND deleted_at IS NULL"),
            {"aid": agent_id, "ws_id": workspace_id},
        )
        if not result.fetchone():
            return None

        set_clauses = []
        params = {"aid": agent_id, "ws_id": workspace_id, "now": _utc_now()}

        for field in ["name", "icon", "model", "system_prompt", "temperature", "max_tokens"]:
            if field in updates and updates[field] is not None:
                set_clauses.append(f"{field} = :{field}")
                params[field] = updates[field]

        if set_clauses:
            set_clauses.append("updated_at = :now")
            sql = f"UPDATE agents SET {', '.join(set_clauses)} WHERE id = :aid AND workspace_id = :ws_id"
            await conn.execute(text(sql), params)

    engine2 = get_engine()
    async with engine2.connect() as conn:
        result = await conn.execute(
            text("SELECT * FROM agents WHERE id = :aid"), {"aid": agent_id}
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None


async def remove_agent(workspace_id: str, agent_id: str) -> bool:
    """软删除 Agent"""
    engine = get_engine()
    now = _utc_now()
    async with engine.begin() as conn:
        result = await conn.execute(
            text("UPDATE agents SET deleted_at = :now, updated_at = :now "
                 "WHERE id = :aid AND workspace_id = :ws_id AND deleted_at IS NULL"),
            {"aid": agent_id, "ws_id": workspace_id, "now": now},
        )
        return result.rowcount > 0
