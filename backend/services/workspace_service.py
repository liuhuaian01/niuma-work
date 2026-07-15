"""
工作间服务层

Phase 1: SQLite 直接操作，Phase 2 可加缓存层
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from db.database import get_engine
from config.settings import settings
from middleware.workspace_isolation import add_valid_workspace, remove_valid_workspace
from utils import utc_now, calculate_offset



async def list_workspaces(page: int = 1, page_size: int = 20) -> tuple[list, int]:
    """列出所有未删除的工作间"""
    engine = get_engine()
    offset = calculate_offset(page, page_size)

    async with engine.connect() as conn:
        total_result = await conn.execute(
            text("SELECT COUNT(*) FROM workspaces WHERE deleted_at IS NULL")
        )
        total = total_result.scalar()

        result = await conn.execute(
            text(
                "SELECT id, name, icon, theme_color, is_default, created_at, updated_at "
                "FROM workspaces WHERE deleted_at IS NULL "
                "ORDER BY updated_at DESC LIMIT :limit OFFSET :offset"
            ),
            {"limit": page_size, "offset": offset},
        )

        workspaces = []
        for row in result:
            # 统计 agent 数
            agent_count_result = await conn.execute(
                text("SELECT COUNT(*) FROM agents WHERE workspace_id = :ws_id AND deleted_at IS NULL"),
                {"ws_id": row.id},
            )
            agent_count = agent_count_result.scalar()

            workspaces.append({
                "id": row.id,
                "name": row.name,
                "icon": row.icon,
                "theme_color": row.theme_color,
                "is_default": bool(row.is_default),
                "agent_count": agent_count,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            })

        return workspaces, total


async def create_workspace(name: str, icon: str = "📄", theme_color: str = "#FF6B35",
                           template: str | None = None) -> dict:
    """创建工作间"""
    engine = get_engine()
    ws_id = f"ws-{uuid.uuid4().hex[:12]}"
    now = utc_now()

    async with engine.begin() as conn:
        # 检查限额
        limit_result = await conn.execute(
            text("SELECT COUNT(*) FROM workspaces WHERE deleted_at IS NULL")
        )
        count = limit_result.scalar()
        if count >= settings.FREE_WORKSPACE_LIMIT:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=409,
                detail={"code": "WORKSPACE_LIMIT_EXCEEDED",
                        "message": f"免费版最多创建 {settings.FREE_WORKSPACE_LIMIT} 个工作间"}
            )

        # 创建第一个工作间 → 设为默认
        is_default = 1 if count == 0 else 0

        await conn.execute(
            text(
                "INSERT INTO workspaces (id, name, icon, theme_color, is_default, created_at, updated_at) "
                "VALUES (:id, :name, :icon, :theme_color, :is_default, :now, :now)"
            ),
            {"id": ws_id, "name": name, "icon": icon, "theme_color": theme_color,
             "is_default": is_default, "now": now},
        )

        # 注册到工作间隔离缓存
        await add_valid_workspace(ws_id)

        # 创建默认配置
        config_id = f"cfg-{uuid.uuid4().hex[:12]}"
        await conn.execute(
            text(
                "INSERT INTO workspace_configs "
                "(id, workspace_id, default_model, token_budget, security_level, "
                "context_threshold, auto_summary, created_at, updated_at) "
                "VALUES (:id, :ws_id, :model, :budget, :sec, :ctx, :summary, :now, :now)"
            ),
            {
                "id": config_id, "ws_id": ws_id,
                "model": settings.MODEL_NAMES.get("deepseek-v4-pro", "deepseek-v4-pro"),
                "budget": settings.DEFAULT_TOKEN_BUDGET,
                "sec": settings.DEFAULT_SECURITY_LEVEL,
                "ctx": settings.DEFAULT_CONTEXT_THRESHOLD,
                "summary": 1, "now": now,
            },
        )

        # 如果是模板创建 → 加入默认 Agent
        agents_list = []
        if template and template != "blank":
            template_agents = _get_template_agents(template)
            for i, ta in enumerate(template_agents):
                agent_id = f"agent-{uuid.uuid4().hex[:12]}"
                await conn.execute(
                    text(
                        "INSERT INTO agents (id, workspace_id, name, role, icon, model, "
                        "system_prompt, status, sort_order, created_at, updated_at) "
                        "VALUES (:id, :ws_id, :name, :role, :icon, :model, "
                        ":prompt, 'online', :sort, :now, :now)"
                    ),
                    {
                        "id": agent_id, "ws_id": ws_id,
                        "name": ta["name"], "role": ta["role"],
                        "icon": ta.get("icon", "🤖"),
                        "model": ta.get("model", "deepseek-v4-pro"),
                        "prompt": ta.get("system_prompt", ""),
                        "sort": i, "now": now,
                    },
                )
                agents_list.append({
                    "id": agent_id, "name": ta["name"], "role": ta["role"],
                    "icon": ta.get("icon", "🤖"),
                    "model": ta.get("model", "deepseek-v4-pro"),
                    "status": "online",
                })

        return {
            "id": ws_id, "name": name, "icon": icon, "theme_color": theme_color,
            "agents": agents_list,
            "config": {
                "default_model": "deepseek-v4-pro",
                "token_budget": settings.DEFAULT_TOKEN_BUDGET,
                "security_level": settings.DEFAULT_SECURITY_LEVEL,
                "context_threshold": settings.DEFAULT_CONTEXT_THRESHOLD,
                "auto_summary": True,
            },
            "created_at": now,
        }


async def get_workspace(workspace_id: str) -> dict | None:
    """获取工作间详情"""
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT id, name, icon, theme_color, is_default, created_at, updated_at "
                "FROM workspaces WHERE id = :id AND deleted_at IS NULL"
            ),
            {"id": workspace_id},
        )
        row = result.fetchone()
        if not row:
            return None

        ws = {
            "id": row.id, "name": row.name, "icon": row.icon,
            "theme_color": row.theme_color, "is_default": bool(row.is_default),
            "created_at": row.created_at, "updated_at": row.updated_at,
        }

        # 获取 agents
        agents_result = await conn.execute(
            text(
                "SELECT id, workspace_id, name, role, icon, model, system_prompt, "
                "temperature, max_tokens, status, sort_order, created_at, updated_at "
                "FROM agents WHERE workspace_id = :ws_id AND deleted_at IS NULL "
                "ORDER BY sort_order"
            ),
            {"ws_id": workspace_id},
        )
        ws["agents"] = [dict(r._mapping) for r in agents_result]

        # 获取配置
        cfg_result = await conn.execute(
            text(
                "SELECT default_model, token_budget, security_level, "
                "context_threshold, auto_summary "
                "FROM workspace_configs WHERE workspace_id = :ws_id"
            ),
            {"ws_id": workspace_id},
        )
        cfg_row = cfg_result.fetchone()
        if cfg_row:
            ws["config"] = {
                "default_model": cfg_row.default_model,
                "token_budget": cfg_row.token_budget,
                "security_level": cfg_row.security_level,
                "context_threshold": cfg_row.context_threshold,
                "auto_summary": bool(cfg_row.auto_summary),
            }

        return ws


async def update_workspace(workspace_id: str, updates: dict) -> dict | None:
    """更新工作间"""
    engine = get_engine()
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT id FROM workspaces WHERE id = :id AND deleted_at IS NULL"),
            {"id": workspace_id},
        )
        if not result.fetchone():
            return None

        set_clauses = []
        params = {"id": workspace_id, "now": utc_now()}

        for field in ["name", "icon", "theme_color"]:
            if field in updates and updates[field] is not None:
                set_clauses.append(f"{field} = :{field}")
                params[field] = updates[field]

        if set_clauses:
            set_clauses.append("updated_at = :now")
            sql = f"UPDATE workspaces SET {', '.join(set_clauses)} WHERE id = :id"
            await conn.execute(text(sql), params)

    return await get_workspace(workspace_id)


async def soft_delete_workspace(workspace_id: str) -> bool:
    """软删除工作间"""
    engine = get_engine()
    now = utc_now()
    async with engine.begin() as conn:
        result = await conn.execute(
            text("UPDATE workspaces SET deleted_at = :now, updated_at = :now "
                 "WHERE id = :id AND deleted_at IS NULL"),
            {"id": workspace_id, "now": now},
        )
        if result.rowcount > 0:
            # 从工作间隔离缓存移除
            await remove_valid_workspace(workspace_id)
            return True
        return False


async def get_templates() -> list:
    """获取工作间模板列表"""
    return [
        {
            "id": "novel-writing", "name": "小说创作",
            "description": "Director + Writer + Editor，适合长篇网文创作",
            "icon": "📝", "default_model": "deepseek-v4-pro",
            "agents": _get_template_agents("novel-writing"),
        },
        {
            "id": "self-media", "name": "自媒体",
            "description": "Director + Writer + Researcher，适合内容创作",
            "icon": "📱", "default_model": "kimi",
            "agents": _get_template_agents("self-media"),
        },
        {
            "id": "code-dev", "name": "代码开发",
            "description": "Director + Coder + Reviewer，适合软件开发",
            "icon": "💻", "default_model": "deepseek-v4-pro",
            "agents": _get_template_agents("code-dev"),
        },
        {
            "id": "blank", "name": "空白工作间",
            "description": "不预设 Agent，自由添加",
            "icon": "📄", "default_model": "deepseek-v4-pro",
            "agents": [],
        },
    ]


def _get_template_agents(template: str) -> list:
    """模板 Agent 定义"""
    templates = {
        "novel-writing": [
            {"name": "Director", "role": "director", "icon": "🎬", "model": "deepseek-v4-pro",
             "system_prompt": "你是小说创作工作室的总监(Director)，负责协调团队、审核产出、把控质量。"},
            {"name": "Writer", "role": "writer", "icon": "✍️", "model": "deepseek-v4-pro",
             "system_prompt": "你是专业的小说写手，擅长长篇网文创作，文风流畅自然。"},
            {"name": "Editor", "role": "editor", "icon": "📝", "model": "deepseek-v4-flash",
             "system_prompt": "你是资深的文字编辑，负责文风一致性检查、去AI味、语法修正。"},
        ],
        "self-media": [
            {"name": "Director", "role": "director", "icon": "🎬", "model": "kimi",
             "system_prompt": "你是自媒体工作室的总监，负责内容策略和团队协调。"},
            {"name": "Writer", "role": "writer", "icon": "✍️", "model": "kimi",
             "system_prompt": "你是自媒体内容创作者，擅长公众号文章、短视频脚本等。"},
            {"name": "Researcher", "role": "researcher", "icon": "🔍", "model": "kimi",
             "system_prompt": "你是信息研究员，负责收集素材、分析热点、提供数据支撑。"},
        ],
        "code-dev": [
            {"name": "Director", "role": "director", "icon": "🎬", "model": "deepseek-v4-pro",
             "system_prompt": "你是开发团队的总监，负责任务分配和技术决策。"},
            {"name": "Coder", "role": "coder", "icon": "💻", "model": "deepseek-v4-pro",
             "system_prompt": "你是资深软件工程师，擅长 Python/TypeScript，代码规范严谨。"},
            {"name": "Reviewer", "role": "reviewer", "icon": "🔍", "model": "deepseek-v4-flash",
             "system_prompt": "你是代码审查专家，检查代码质量、安全性和性能优化。"},
        ],
    }
    return templates.get(template, [])
