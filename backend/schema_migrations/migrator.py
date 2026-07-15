"""
数据库迁移执行器

检测当前 schema 版本，按顺序执行所有未应用的迁移。
迁移文件命名: V{数字}__{描述}.sql
"""

import logging
import re
from pathlib import Path

from sqlalchemy import text

from db.database import get_engine
from schema_migrations import MIGRATIONS_DIR

logger = logging.getLogger("niuma.migration")

# 当前代码期望的 schema 版本
SCHEMA_VERSION = 1


async def check_and_migrate():
    """
    检查数据库版本并执行迁移。

    在 app 启动时调用，幂等。
    """
    engine = get_engine()

    # 创建版本表（如果不存在）
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS _schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """))

        # 获取当前版本
        result = await conn.execute(text("SELECT COALESCE(MAX(version), 0) FROM _schema_version"))
        current_version = result.scalar() or 0

        if current_version >= SCHEMA_VERSION:
            logger.info(f"[Migration] Schema up-to-date (v{current_version}), no migration needed")
            return

        # 执行缺失的迁移
        for version in range(current_version + 1, SCHEMA_VERSION + 1):
            await _apply_migration(conn, version)

        logger.info(f"[Migration] Schema migrated from v{current_version} → v{SCHEMA_VERSION}")


async def _apply_migration(conn, version: int):
    """执行单个迁移"""
    migration_file = MIGRATIONS_DIR / f"V{version:03d}__migration.sql"

    if not migration_file.exists():
        logger.warning(f"[Migration] V{version:03d}__migration.sql not found, skipping")
        return

    sql = migration_file.read_text(encoding="utf-8")
    logger.info(f"[Migration] Applying V{version:03d}...")

    # 按分号分割执行（支持多语句）
    statements = [s.strip() for s in re.split(r";\s*", sql) if s.strip()]
    for stmt in statements:
        await conn.execute(text(stmt))

    # 记录版本
    await conn.execute(
        text("INSERT INTO _schema_version (version) VALUES (:ver)"),
        {"ver": version},
    )
    logger.info(f"[Migration] V{version:03d} applied successfully")


async def get_schema_version() -> int:
    """获取当前 schema 版本（外部查询用）"""
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT COALESCE(MAX(version), 0) FROM _schema_version"))
        return result.scalar() or 0
