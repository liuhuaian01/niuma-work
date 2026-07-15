"""
L3知识库Repository - 迁移到SQLAlchemy异步模式

解决双重数据库系统问题，统一使用SQLAlchemy异步引擎。
支持FTS5全文搜索。
"""

from typing import Optional, List
from sqlalchemy import text
from db.repository import BaseRepository


class KnowledgeRepository(BaseRepository):
    """L3知识库的数据访问层
    
    优势:
    1. 统一使用SQLAlchemy异步引擎
    2. 自动事务管理
    3. SQL注入防护（参数化查询）
    4. FTS5全文搜索集成
    """
    
    async def init_tables(self) -> None:
        """初始化表结构和FTS5索引"""
        # 创建主表
        await self.execute("""
            CREATE TABLE IF NOT EXISTS l3_knowledge (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source TEXT DEFAULT 'agent_generated',
                tags TEXT DEFAULT '[]',
                workspace_id TEXT DEFAULT 'global',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # 删除旧的FTS表并重建
        await self.execute("DROP TABLE IF EXISTS l3_fts")
        await self.execute("""
            CREATE VIRTUAL TABLE l3_fts USING fts5(
                id, content, source, tags, workspace_id
            )
        """)
        
        # 同步现有数据到FTS索引
        await self.execute("""
            INSERT INTO l3_fts (id, content, source, tags, workspace_id)
            SELECT id, content, source, tags, workspace_id FROM l3_knowledge
        """)
    
    async def insert_or_replace(self, entry_id: str, content: str, source: str, 
                                tags_json: str, workspace_id: str) -> None:
        """插入或替换知识条目（异步，事务安全）"""
        # 先删除旧记录
        await self.execute("DELETE FROM l3_knowledge WHERE id = :id", {"id": entry_id})
        await self.execute("DELETE FROM l3_fts WHERE id = :id", {"id": entry_id})
        
        # 插入新记录
        await self.execute(
            "INSERT INTO l3_knowledge (id, content, source, tags, workspace_id) VALUES (:id, :content, :source, :tags, :workspace_id)",
            {"id": entry_id, "content": content, "source": source, "tags": tags_json, "workspace_id": workspace_id}
        )
        await self.execute(
            "INSERT INTO l3_fts (id, content, source, tags, workspace_id) VALUES (:id, :content, :source, :tags, :workspace_id)",
            {"id": entry_id, "content": content, "source": source, "tags": tags_json, "workspace_id": workspace_id}
        )
    
    async def search(self, query: str, workspace_id: Optional[str] = None, limit: int = 5) -> list[dict]:
        """全文搜索（使用FTS5）"""
        if workspace_id:
            rows = await self.fetch_all(
                """SELECT id, content, source, tags, workspace_id, created_at FROM l3_knowledge 
                   WHERE id IN (SELECT id FROM l3_fts WHERE l3_fts MATCH :query) 
                   AND workspace_id = :workspace_id
                   ORDER BY created_at DESC LIMIT :limit""",
                {"query": query, "workspace_id": workspace_id, "limit": limit}
            )
        else:
            rows = await self.fetch_all(
                """SELECT id, content, source, tags, workspace_id, created_at FROM l3_knowledge 
                   WHERE id IN (SELECT id FROM l3_fts WHERE l3_fts MATCH :query)
                   ORDER BY created_at DESC LIMIT :limit""",
                {"query": query, "limit": limit}
            )
        
        return [self._row_to_dict(r) for r in rows] if rows else []
    
    async def get_recent(self, workspace_id: Optional[str] = None, limit: int = 10) -> list[dict]:
        """获取最近条目"""
        if workspace_id:
            rows = await self.fetch_all(
                """SELECT id, content, source, tags, workspace_id, created_at FROM l3_knowledge 
                   WHERE workspace_id = :workspace_id
                   ORDER BY created_at DESC LIMIT :limit""",
                {"workspace_id": workspace_id, "limit": limit}
            )
        else:
            rows = await self.fetch_all(
                """SELECT id, content, source, tags, workspace_id, created_at FROM l3_knowledge 
                   ORDER BY created_at DESC LIMIT :limit""",
                {"limit": limit}
            )
        
        return [self._row_to_dict(r) for r in rows] if rows else []
    
    async def get_stats(self) -> dict:
        """获取统计信息"""
        row = await self.fetch_one("SELECT COUNT(*) FROM l3_knowledge")
        count = row[0] if row else 0
        return {"total_entries": count, "source": "FTS5 (SQLAlchemy async)"}
    
    def _row_to_dict(self, row) -> dict:
        """将Row对象转换为字典"""
        import json
        return {
            "id": row[0],
            "content": row[1][:200],  # 截断内容
            "source": row[2],
            "tags": json.loads(row[3]) if row[3] else [],
            "workspace_id": row[4],
            "created_at": row[5]
        }
