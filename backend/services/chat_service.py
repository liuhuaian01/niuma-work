"""对话服务层"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from db.database import get_engine
from utils import utc_now, calculate_offset


async def _workspace_exists(workspace_id: str) -> bool:
    """检查 workspace 是否存在（工作间隔离校验）"""
    if not workspace_id:
        return False
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM workspaces WHERE id = :ws_id AND deleted_at IS NULL"),
            {"ws_id": workspace_id},
        )
        return result.fetchone() is not None


async def create_message(workspace_id: str | None, content: str,
                         role: str = "user", model: str | None = None,
                         at_agent_id: str | None = None) -> dict:
    """创建消息"""
    # 工作间隔离：非全局消息需验证 workspace 存在
    if workspace_id is not None and not await _workspace_exists(workspace_id):
        raise ValueError(f"Workspace 不存在: {workspace_id}")
    engine = get_engine()
    msg_id = f"msg-{uuid.uuid4().hex[:12]}"
    now = utc_now()

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO chat_messages (id, workspace_id, role, content, model, "
                "at_agent_id, status, created_at) "
                "VALUES (:id, :ws_id, :role, :content, :model, :at_agent, 'queued', :now)"
            ),
            {
                "id": msg_id, "ws_id": workspace_id,
                "role": role, "content": content,
                "model": model, "at_agent": at_agent_id, "now": now,
            },
        )

    return {
        "id": msg_id, "workspace_id": workspace_id,
        "role": role, "content": content,
        "model": model, "status": "queued",
        "token_count": None, "created_at": now,
        "stream_url": f"/api/v1/chat/stream/{msg_id}",
    }


async def list_messages(workspace_id: str | None, page: int = 1,
                        page_size: int = 50, before_id: str | None = None) -> tuple[list, int]:
    """获取对话历史"""
    # 工作间隔离：非全局查询需验证 workspace 存在
    if workspace_id and workspace_id != "global":
        if not await _workspace_exists(workspace_id):
            return [], 0

    engine = get_engine()
    offset = calculate_offset(page, page_size)

    async with engine.connect() as conn:
        # 构建查询条件
        where_clause = "WHERE 1=1"
        params: dict = {"limit": page_size, "offset": offset}

        if workspace_id and workspace_id != "global":
            where_clause += " AND workspace_id = :ws_id"
            params["ws_id"] = workspace_id
        elif workspace_id == "global" or workspace_id is None:
            where_clause += " AND workspace_id IS NULL"

        if before_id:
            where_clause += " AND id < :before_id"
            params["before_id"] = before_id

        # 总数
        count_result = await conn.execute(
            text(f"SELECT COUNT(*) FROM chat_messages {where_clause}"),
            {k: v for k, v in params.items() if k not in ("limit", "offset")},
        )
        total = count_result.scalar()

        # 消息列表
        result = await conn.execute(
            text(
                f"SELECT id, workspace_id, role, content, model, at_agent_id, "
                f"status, token_count, artifacts, parent_message_id, created_at "
                f"FROM chat_messages {where_clause} "
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )

        messages = []
        for row in result:
            msg = dict(row._mapping)
            msg["error_info"] = None  # 暂不返回错误详情
            messages.append(msg)

        return messages, total


def _escape_like(s: str) -> str:
    """转义 SQL LIKE 通配符（AUDIT-002 修复）"""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def search_messages(query: str, workspace_id: str | None) -> list:
    """搜索对话内容"""
    # 工作间隔离：指定 workspace 时验证其存在
    if workspace_id:
        if not await _workspace_exists(workspace_id):
            return []

    engine = get_engine()
    safe_pattern = f"%{_escape_like(query)}%"
    async with engine.connect() as conn:
        if workspace_id:
            result = await conn.execute(
                text(
                    "SELECT id, workspace_id, content, created_at "
                    "FROM chat_messages WHERE workspace_id = :ws_id "
                    "AND content LIKE :pattern ESCAPE '\\' ORDER BY created_at DESC LIMIT 20"
                ),
                {"ws_id": workspace_id, "pattern": safe_pattern},
            )
        else:
            result = await conn.execute(
                text(
                    "SELECT id, workspace_id, content, created_at "
                    "FROM chat_messages WHERE content LIKE :pattern "
                    "ESCAPE '\\' ORDER BY created_at DESC LIMIT 20"
                ),
                {"pattern": safe_pattern},
            )

        return [
            {
                "message_id": r.id,
                "workspace_id": r.workspace_id,
                "content_preview": r.content[:200],
                "created_at": r.created_at,
            }
            for r in result
        ]


async def clear_messages(workspace_id: str) -> int:
    """清除对话历史"""
    # 工作间隔离：global 是合法标识，其他需验证 workspace 存在
    if workspace_id != "global":
        if not await _workspace_exists(workspace_id):
            return 0

    engine = get_engine()
    async with engine.begin() as conn:
        if workspace_id == "global":
            result = await conn.execute(
                text("DELETE FROM chat_messages WHERE workspace_id IS NULL")
            )
        else:
            result = await conn.execute(
                text("DELETE FROM chat_messages WHERE workspace_id = :ws_id"),
                {"ws_id": workspace_id},
            )
        return result.rowcount


async def get_message_by_id(msg_id: str) -> dict | None:
    """根据 ID 获取消息"""
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT * FROM chat_messages WHERE id = :msg_id"),
            {"msg_id": msg_id},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None


# 允许的字段白名单（防止SQL注入）
ALLOWED_UPDATE_FIELDS = {"content", "token_count", "model", "error_info", "artifacts"}

async def update_message_status(msg_id: str, status: str, **kwargs) -> dict | None:
    """更新消息状态（使用字段白名单防止SQL注入）"""
    engine = get_engine()
    async with engine.begin() as conn:
        set_clauses = ["status = :status"]
        params: dict = {"msg_id": msg_id, "status": status}

        # 只允许白名单中的字段，防止SQL注入
        for key, value in kwargs.items():
            if key not in ALLOWED_UPDATE_FIELDS or value is None:
                continue
            set_clauses.append(f"{key} = :{key}")
            params[key] = value

        sql = f"UPDATE chat_messages SET {', '.join(set_clauses)} WHERE id = :msg_id"
        await conn.execute(text(sql), params)

        # 同一事务中查询更新后的数据（避免二次连接）
        result = await conn.execute(
            text("SELECT * FROM chat_messages WHERE id = :msg_id"),
            {"msg_id": msg_id},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None
