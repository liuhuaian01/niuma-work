"""
太极引擎 · L3 知识库（LanceDB 向量检索）

L3 = 长期知识积累，向量语义检索。
当前 Phase: 最小可用实现。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import json
import os
import hashlib
from engine.knowledge_repository import KnowledgeRepository


@dataclass
class KnowledgeEntry:
    id: str
    content: str
    source: str           # "user_upload" / "agent_generated" / "community"
    tags: list[str] = field(default_factory=list)
    workspace_id: str = "global"
    created_at: str = ""


class L3KnowledgeBase:
    """L3 知识库 — 使用SQLAlchemy异步引擎 + FTS5全文搜索。
    
    P0修复: 迁移到SQLAlchemy异步Repository模式，消除双重数据库系统。
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or ":memory:"
        self._repo: Optional[KnowledgeRepository] = None
        if db_path and db_path != ":memory:":
            # 确保目录存在
            db_dir = os.path.dirname(db_path)
            if db_dir:
                pass  # Repository会自动处理
            else:
                pass
        self._init_repo_sync()
    
    def _init_repo_sync(self) -> None:
        """同步初始化Repository（兼容现有同步调用）"""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._async_init())
        except RuntimeError:
            asyncio.run(self._async_init())
    
    async def _async_init(self) -> None:
        """异步初始化Repository"""
        if self._repo is None:
            self._repo = KnowledgeRepository()
            await self._repo.init_tables()

    def add(self, content: str, source: str = "agent_generated",
            tags: list | None = None, workspace_id: str = "global") -> str:
        """添加一条知识。返回 entry_id。
        
        P0修复: 使用异步Repository，支持SQLAlchemy事务管理。
        """
        eid = f"l3-{hashlib.sha256(content.encode()).hexdigest()[:16]}"
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        
        if self._repo:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.run_until_complete(
                    self._repo.insert_or_replace(eid, content, source, tags_json, workspace_id)
                )
            except RuntimeError:
                asyncio.run(
                    self._repo.insert_or_replace(eid, content, source, tags_json, workspace_id)
                )
        return eid

    def search(self, query: str, workspace_id: str | None = None, limit: int = 5) -> list[dict]:
        """全文搜索。
        
        P0修复: 使用异步Repository查询。
        """
        if self._repo:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                return loop.run_until_complete(
                    self._repo.search(query, workspace_id, limit)
                )
            except RuntimeError:
                return asyncio.run(
                    self._repo.search(query, workspace_id, limit)
                )
        return []

    def get_recent(self, workspace_id: str | None = None, limit: int = 10) -> list[dict]:
        """获取最近条目。
        
        P0修复: 使用异步Repository查询。
        """
        if self._repo:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                return loop.run_until_complete(
                    self._repo.get_recent(workspace_id, limit)
                )
            except RuntimeError:
                return asyncio.run(
                    self._repo.get_recent(workspace_id, limit)
                )
        return []

    def get_stats(self) -> dict:
        """获取统计信息。
        
        P0修复: 使用异步Repository查询。
        """
        if self._repo:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                return loop.run_until_complete(self._repo.get_stats())
            except RuntimeError:
                return asyncio.run(self._repo.get_stats())
        return {"total_entries": 0, "source": "Not initialized"}
