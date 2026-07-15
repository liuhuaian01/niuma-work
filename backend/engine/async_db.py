"""
统一异步数据库助手

替换所有引擎模块中的同步 sqlite3 → aiosqlite。
使用 aiosqlite 在异步事件循环中安全操作。
"""

import aiosqlite
import os
from typing import Optional

# 全局引擎数据库路径
_engine_db_path: Optional[str] = None


def set_engine_db_path(path: str) -> None:
    global _engine_db_path
    _engine_db_path = path
    os.makedirs(os.path.dirname(path), exist_ok=True)


async def get_db() -> aiosqlite.Connection:
    """获取引擎数据库连接。"""
    if not _engine_db_path:
        raise RuntimeError("Engine DB path not set. Call set_engine_db_path() first.")
    db = await aiosqlite.connect(_engine_db_path)
    db.row_factory = aiosqlite.Row
    return db


async def execute(sql: str, params: tuple = ()) -> None:
    """执行写操作。"""
    db = await get_db()
    try:
        await db.execute(sql, params)
        await db.commit()
    finally:
        await db.close()


async def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    """执行读操作。"""
    db = await get_db()
    try:
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def fetch_one(sql: str, params: tuple = ()) -> Optional[dict]:
    """执行单行查询。"""
    db = await get_db()
    try:
        cursor = await db.execute(sql, params)
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def table_exists(name: str) -> bool:
    """检查表是否存在。"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
        )
        return await cursor.fetchone() is not None
    finally:
        await db.close()
