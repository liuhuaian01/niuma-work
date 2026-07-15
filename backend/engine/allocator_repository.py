"""
智能分配器Repository - 迁移到SQLAlchemy异步模式

解决双重数据库系统问题，统一使用SQLAlchemy异步引擎。
"""

from typing import Optional, Tuple
from sqlalchemy import text
from db.repository import BaseRepository


class AllocatorRepository(BaseRepository):
    """智能分配器的数据访问层
    
    优势:
    1. 统一使用SQLAlchemy异步引擎
    2. 自动事务管理
    3. SQL注入防护（参数化查询）
    4. 支持跨操作事务
    """
    
    async def init_tables(self) -> None:
        """初始化表结构"""
        await self.execute("""
            CREATE TABLE IF NOT EXISTS allocator_history (
                task_type TEXT PRIMARY KEY,
                total_tasks INTEGER DEFAULT 0,
                avg_tokens REAL DEFAULT 0,
                avg_quality REAL DEFAULT 0.5,
                total_tokens INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await self.execute("""
            CREATE TABLE IF NOT EXISTS allocator_daily_usage (
                date TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                PRIMARY KEY (date, agent_id)
            )
        """)
    
    async def load_history(self) -> dict:
        """加载历史记录
        
        Returns:
            {task_type_value: (avg_tokens, total_tasks, avg_quality)}
        """
        rows = await self.fetch_all(
            "SELECT task_type, total_tasks, avg_tokens, avg_quality FROM allocator_history"
        )
        history = {}
        for row in rows:
            try:
                tt = row[0]
                history[tt] = (int(row[2]), int(row[1]), float(row[3]))
            except (ValueError, IndexError, TypeError):
                continue
        return history
    
    async def save_history(self, task_type: str, avg_tokens: int, 
                          total_tasks: int, avg_quality: float) -> None:
        """保存历史记录（异步）"""
        await self.execute(
            """INSERT OR REPLACE INTO allocator_history
               (task_type, total_tasks, avg_tokens, avg_quality, total_tokens, updated_at)
               VALUES (:task_type, :total_tasks, :avg_tokens, :avg_quality, :total_tokens, datetime('now'))""",
            {
                "task_type": task_type,
                "total_tasks": total_tasks,
                "avg_tokens": avg_tokens,
                "avg_quality": avg_quality,
                "total_tokens": avg_tokens * total_tasks
            }
        )
    
    async def record_daily_usage(self, date_str: str, agent_id: str, tokens_used: int) -> None:
        """记录每日用量（异步，UPSERT）"""
        await self.execute(
            """INSERT INTO allocator_daily_usage (date, agent_id, tokens_used)
               VALUES (:date, :agent_id, :tokens_used)
               ON CONFLICT(date, agent_id) DO UPDATE SET tokens_used = tokens_used + :tokens_used""",
            {"date": date_str, "agent_id": agent_id, "tokens_used": tokens_used}
        )
    
    async def get_daily_usage(self, date_str: str, agent_id: str) -> int:
        """获取某日的用量"""
        row = await self.fetch_one(
            "SELECT tokens_used FROM allocator_daily_usage WHERE date = :date AND agent_id = :agent_id",
            {"date": date_str, "agent_id": agent_id}
        )
        return row[0] if row else 0
