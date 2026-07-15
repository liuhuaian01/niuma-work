"""技能服务层"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from db.database import get_engine
from utils import utc_now


async def list_market_skills(category: str | None = None) -> list:
    """获取技能市场列表"""
    engine = get_engine()
    async with engine.connect() as conn:
        if category:
            result = await conn.execute(
                text(
                    "SELECT id, name, description, category, author, version, icon, "
                    "token_level, install_count, recommend_reason "
                    "FROM skill_market WHERE is_active = 1 AND category = :cat "
                    "ORDER BY install_count DESC"
                ),
                {"cat": category},
            )
        else:
            result = await conn.execute(
                text(
                    "SELECT id, name, description, category, author, version, icon, "
                    "token_level, install_count, recommend_reason "
                    "FROM skill_market WHERE is_active = 1 "
                    "ORDER BY install_count DESC"
                ),
            )

        skills = []
        for row in result:
            # 检查是否已安装
            installed = await conn.execute(
                text("SELECT COUNT(*) FROM user_skills WHERE skill_id = :sid"),
                {"sid": row.id},
            )
            skills.append({
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "category": row.category,
                "author": row.author,
                "version": row.version,
                "icon": row.icon,
                "token_level": row.token_level,
                "install_count": row.install_count,
                "recommend_reason": row.recommend_reason,
                "installed": installed.scalar() > 0,
            })

        return skills


async def install_skill(skill_id: str) -> dict:
    """安装技能"""
    engine = get_engine()
    now = _utc_now()

    async with engine.begin() as conn:
        # 获取市场技能
        result = await conn.execute(
            text("SELECT * FROM skill_market WHERE id = :sid AND is_active = 1"),
            {"sid": skill_id},
        )
        skill = result.fetchone()
        if not skill:
            from fastapi import HTTPException
            raise HTTPException(status_code=404,
                                detail={"code": "SKILL_NOT_FOUND", "message": "技能不存在"})

        # 检查是否已安装
        dup = await conn.execute(
            text("SELECT id FROM user_skills WHERE skill_id = :sid"),
            {"sid": skill_id},
        )
        if dup.fetchone():
            from fastapi import HTTPException
            raise HTTPException(status_code=409,
                                detail={"code": "SKILL_ALREADY_INSTALLED", "message": "技能已安装"})

        # 安装
        user_skill_id = f"uskill-{uuid.uuid4().hex[:12]}"
        await conn.execute(
            text(
                "INSERT INTO user_skills (id, skill_id, name, description, category, "
                "author, version, icon, source, definition, enabled, is_custom, "
                "installed_at, updated_at) "
                "VALUES (:id, :sid, :name, :desc, :cat, :author, :ver, :icon, "
                "'market', :def, 1, 0, :now, :now)"
            ),
            {
                "id": user_skill_id, "sid": skill_id,
                "name": skill.name, "desc": skill.description,
                "cat": skill.category, "author": skill.author,
                "ver": skill.version, "icon": skill.icon,
                "def": skill.definition, "now": now,
            },
        )

        # 增加安装计数
        await conn.execute(
            text("UPDATE skill_market SET install_count = install_count + 1, updated_at = :now "
                 "WHERE id = :sid"),
            {"sid": skill_id, "now": now},
        )

        return {
            "skill_id": skill_id, "name": skill.name,
            "id": user_skill_id, "installed": True,
        }


async def list_user_skills() -> list:
    """获取已安装技能"""
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT id, skill_id, name, description, category, author, version, "
                "icon, source, enabled, is_custom, installed_at "
                "FROM user_skills ORDER BY installed_at DESC"
            ),
        )
        return [dict(r._mapping) for r in result]


async def toggle_skill(user_skill_id: str, enabled: bool) -> dict | None:
    """启用/禁用技能"""
    engine = get_engine()
    now = _utc_now()
    async with engine.begin() as conn:
        result = await conn.execute(
            text("UPDATE user_skills SET enabled = :enabled, updated_at = :now WHERE id = :id"),
            {"id": user_skill_id, "enabled": 1 if enabled else 0, "now": now},
        )
        if result.rowcount == 0:
            return None

    engine2 = get_engine()
    async with engine2.connect() as conn:
        result = await conn.execute(
            text("SELECT * FROM user_skills WHERE id = :id"),
            {"id": user_skill_id},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None


async def uninstall_skill(user_skill_id: str) -> bool:
    """卸载技能"""
    engine = get_engine()
    async with engine.begin() as conn:
        result = await conn.execute(
            text("DELETE FROM user_skills WHERE id = :id"),
            {"id": user_skill_id},
        )
        return result.rowcount > 0
