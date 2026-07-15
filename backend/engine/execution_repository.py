"""
执行日志Repository - 迁移到SQLAlchemy异步模式

解决双重数据库系统问题，统一使用SQLAlchemy异步引擎。
"""

from typing import Optional, List
from sqlalchemy import text
from db.repository import BaseRepository


class ExecutionRepository(BaseRepository):
    """执行日志的数据访问层
    
    优势:
    1. 统一使用SQLAlchemy异步引擎
    2. 自动事务管理
    3. SQL注入防护（参数化查询）
    """
    
    async def init_tables(self) -> None:
        """初始化表结构"""
        await self.execute("""
            CREATE TABLE IF NOT EXISTS execution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT, workspace_id TEXT, task_type TEXT,
                model_used TEXT, tokens_used INTEGER, gate_score REAL,
                success INTEGER, tools_used INTEGER, duration_ms INTEGER,
                error_type TEXT, user_feedback TEXT,
                timestamp TEXT DEFAULT (datetime('now'))
            )
        """)
        await self.execute("""
            CREATE INDEX IF NOT EXISTS idx_exec_log_date
            ON execution_log (timestamp)
        """)
    
    async def insert_record(self, record_data: dict) -> None:
        """插入执行记录（异步）"""
        await self.execute(
            """INSERT INTO execution_log
               (agent_id, workspace_id, task_type, model_used, tokens_used,
                gate_score, success, tools_used, duration_ms, error_type, user_feedback, timestamp)
               VALUES (:agent_id, :workspace_id, :task_type, :model_used, :tokens_used,
                       :gate_score, :success, :tools_used, :duration_ms, :error_type, :user_feedback, :timestamp)""",
            record_data
        )
    
    async def get_today_records(self, today: str) -> list[dict]:
        """获取今日记录"""
        rows = await self.fetch_all(
            "SELECT * FROM execution_log WHERE date(timestamp) = :today ORDER BY timestamp DESC",
            {"today": today}
        )
        return [self._row_to_dict(r) for r in rows] if rows else []
    
    async def get_recent_records(self, days: int) -> list[dict]:
        """获取近N天的记录"""
        rows = await self.fetch_all(
            "SELECT * FROM execution_log WHERE timestamp >= datetime('now', :days) ORDER BY timestamp DESC",
            {"days": f'-{days} days'}
        )
        return [self._row_to_dict(r) for r in rows] if rows else []
    
    async def get_stats(self, today: str) -> dict:
        """获取今日统计"""
        # 总数
        total_row = await self.fetch_one(
            "SELECT COUNT(*) as cnt FROM execution_log WHERE date(timestamp) = :today",
            {"today": today}
        )
        total_count = total_row[0] if total_row else 0
        
        if total_count == 0:
            return {"today": today, "total_executions": 0}
        
        # 成功数
        success_row = await self.fetch_one(
            "SELECT COUNT(*) as cnt FROM execution_log WHERE date(timestamp) = :today AND success = 1",
            {"today": today}
        )
        success_count = success_row[0] if success_row else 0
        
        # Token统计
        token_row = await self.fetch_one(
            "SELECT SUM(tokens_used) as total, AVG(tokens_used) as avg FROM execution_log WHERE date(timestamp) = :today",
            {"today": today}
        )
        total_tokens = token_row[0] if token_row and token_row[0] else 0
        avg_tokens = int(token_row[1]) if token_row and token_row[1] else 0
        
        return {
            "today": today,
            "total_executions": total_count,
            "success_count": success_count,
            "success_rate": round(success_count / total_count, 2) if total_count > 0 else 0,
            "total_tokens": total_tokens,
            "avg_tokens": avg_tokens
        }
    
    def _row_to_dict(self, row) -> dict:
        """将Row对象转换为字典"""
        return {
            "id": row[0],
            "agent_id": row[1],
            "workspace_id": row[2],
            "task_type": row[3],
            "model_used": row[4],
            "tokens_used": row[5],
            "gate_score": row[6] or 0,
            "success": bool(row[7]),
            "tools_used": row[8] or 0,
            "duration_ms": row[9] or 0,
            "error_type": row[10] or "",
            "user_feedback": row[11] or "",
            "timestamp": row[12]
        }
