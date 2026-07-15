"""后台任务服务

v1.5 简化版后台任务：
- Director 接收“后台执行”指令 → 子 Agent 异步执行
- Toast 通知 + 对话插入结果
- 不支持定时/Cron/Webhook
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from db.database import get_engine
from utils import utc_now, calculate_offset


async def create_background_task(
    workspace_id: str,
    agent_id: str,
    title: str,
    description: str = "",
    trigger_message_id: str | None = None,
) -> dict:
    """创建后台任务"""
    engine = get_engine()
    task_id = f"bgtask-{uuid.uuid4().hex[:12]}"
    now = _utc_now()

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO background_tasks "
                "(id, workspace_id, agent_id, trigger_message_id, title, description, "
                "status, progress, created_at) "
                "VALUES (:id, :ws_id, :agent_id, :trigger_msg, :title, :desc, "
                "'pending', 0, :now)"
            ),
            {
                "id": task_id, "ws_id": workspace_id,
                "agent_id": agent_id, "trigger_msg": trigger_message_id,
                "title": title, "desc": description, "now": now,
            },
        )

    return {
        "id": task_id,
        "workspace_id": workspace_id,
        "agent_id": agent_id,
        "title": title,
        "description": description,
        "status": "pending",
        "progress": 0,
        "created_at": now,
    }


async def list_background_tasks(
    workspace_id: str, status: str | None = None, page: int = 1, page_size: int = 20
) -> tuple[list, int]:
    """列出后台任务"""
    engine = get_engine()
    offset = calculate_offset(page, page_size)

    async with engine.connect() as conn:
        where = "WHERE workspace_id = :ws_id"
        params: dict = {"ws_id": workspace_id, "limit": page_size, "offset": offset}

        if status:
            where += " AND status = :status"
            params["status"] = status

        count_result = await conn.execute(
            text(f"SELECT COUNT(*) FROM background_tasks {where}"),
            {k: v for k, v in params.items() if k not in ("limit", "offset")},
        )
        total = count_result.scalar()

        result = await conn.execute(
            text(
                f"SELECT id, workspace_id, agent_id, title, description, status, "
                f"progress, result_summary, total_tokens, duration_ms, "
                f"started_at, completed_at, created_at "
                f"FROM background_tasks {where} "
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )

        tasks = []
        for row in result:
            tasks.append({
                "id": row.id,
                "workspace_id": row.workspace_id,
                "agent_id": row.agent_id,
                "title": row.title,
                "description": row.description,
                "status": row.status,
                "progress": row.progress,
                "result_summary": row.result_summary,
                "total_tokens": row.total_tokens,
                "duration_ms": row.duration_ms,
                "started_at": row.started_at,
                "completed_at": row.completed_at,
                "created_at": row.created_at,
            })

        return tasks, total


async def get_background_task(task_id: str) -> dict | None:
    """获取后台任务详情"""
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT * FROM background_tasks WHERE id = :id"),
            {"id": task_id},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None


async def update_task_status(
    task_id: str, status: str, **kwargs
) -> dict | None:
    """更新任务状态"""
    engine = get_engine()
    now = _utc_now()

    async with engine.begin() as conn:
        set_clauses = ["status = :status"]
        params: dict = {"task_id": task_id, "status": status}

        if status == "running" and "started_at" not in kwargs:
            set_clauses.append("started_at = :now")
            params["now"] = now

        if status in ("completed", "failed", "cancelled"):
            set_clauses.append("completed_at = :completed_at")
            params["completed_at"] = now

        for field in ["progress", "result_summary", "result_message_id",
                       "error_info", "total_tokens", "duration_ms"]:
            if field in kwargs:
                set_clauses.append(f"{field} = :{field}")
                params[field] = kwargs[field]

        sql = f"UPDATE background_tasks SET {', '.join(set_clauses)} WHERE id = :task_id"
        await conn.execute(text(sql), params)

    return await get_background_task(task_id)


async def cancel_background_task(task_id: str) -> dict | None:
    """取消后台任务"""
    task = await get_background_task(task_id)
    if not task:
        return None
    if task["status"] not in ("pending", "running"):
        return None

    return await update_task_status(task_id, "cancelled")
