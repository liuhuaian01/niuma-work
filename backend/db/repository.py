"""
统一数据库访问层 - Repository模式

解决双重数据库系统问题，所有模块通过此层访问数据库。
提供线程安全的异步CRUD操作。
"""

from typing import Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from db.database import get_engine


class BaseRepository:
    """基础Repository - 所有数据访问的基类
    
    优势：
    1. 统一使用SQLAlchemy异步引擎
    2. 自动事务管理
    3. SQL注入防护（参数化查询）
    4. 减少代码重复
    
    使用示例：
    ```python
    class SmartAllocatorRepository(BaseRepository):
        async def record_decision(self, ...):
            await self.execute(
                "INSERT INTO allocator_history ...",
                {...}
            )
    ```
    """
    
    def __init__(self):
        # 不立即获取引擎，延迟到首次使用
        self._engine: Optional[AsyncEngine] = None
    
    async def _get_engine(self) -> AsyncEngine:
        """获取引擎（延迟初始化，支持依赖注入）"""
        if self._engine is None:
            self._engine = await get_engine()
        return self._engine
    
    async def execute(self, sql: str, params: Optional[dict] = None) -> int:
        """执行写操作（INSERT/UPDATE/DELETE）
        
        Args:
            sql: SQL语句（使用:name占位符）
            params: 参数字典
            
        Returns:
            受影响的行数
        """
        engine = await self._get_engine()
        async with engine.begin() as conn:
            result = await conn.execute(text(sql), params or {})
            return result.rowcount
    
    async def fetch_one(self, sql: str, params: Optional[dict] = None) -> Optional[tuple]:
        """查询单条记录
        
        Args:
            sql: SQL语句
            params: 参数字典
            
        Returns:
            单行数据或None
        """
        engine = await self._get_engine()
        async with engine.begin() as conn:
            result = await conn.execute(text(sql), params or {})
            return result.fetchone()
    
    async def fetch_all(self, sql: str, params: Optional[dict] = None) -> list[tuple]:
        """查询多条记录
        
        Args:
            sql: SQL语句
            params: 参数字典
            
        Returns:
            行列表
        """
        engine = await self._get_engine()
        async with engine.begin() as conn:
            result = await conn.execute(text(sql), params or {})
            return result.fetchall()
    
    async def fetch_dict_one(self, sql: str, params: Optional[dict] = None) -> Optional[dict]:
        """查询单条记录并返回字典
        
        Args:
            sql: SQL语句
            params: 参数字典
            
        Returns:
            字典或None
        """
        row = await self.fetch_one(sql, params)
        if row:
            # 从SQLAlchemy Row对象提取列名
            return dict(row._mapping)
        return None
    
    async def fetch_dict_all(self, sql: str, params: Optional[dict] = None) -> list[dict]:
        """查询多条记录并返回字典列表
        
        Args:
            sql: SQL语句
            params: 参数字典
            
        Returns:
            字典列表
        """
        rows = await self.fetch_all(sql, params)
        return [dict(row._mapping) for row in rows]
    
    async def execute_many(self, sql: str, params_list: list[dict]) -> int:
        """批量执行（高效插入多条记录）
        
        Args:
            sql: SQL语句
            params_list: 参数列表
            
        Returns:
            受影响的总行数
        """
        engine = await self._get_engine()
        async with engine.begin() as conn:
            result = await conn.execute(text(sql), params_list)
            return result.rowcount


class TransactionContext:
    """事务上下文管理器 - 支持跨多个操作的事务
    
    使用示例：
    ```python
    async with TransactionContext() as ctx:
        await ctx.execute("INSERT INTO ...", {...})
        await ctx.execute("UPDATE ...", {...})
        # 自动commit，异常时自动rollback
    ```
    """
    
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._conn = None
    
    async def _get_engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = await get_engine()
        return self._engine
    
    async def __aenter__(self):
        engine = await self._get_engine()
        self._conn = await engine.begin()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self._conn.rollback()
        else:
            await self._conn.commit()
        await self._conn.__aexit__(exc_type, exc_val, exc_tb)
    
    async def execute(self, sql: str, params: Optional[dict] = None):
        """在事务中执行"""
        return await self._conn.execute(text(sql), params or {})
    
    async def fetch_one(self, sql: str, params: Optional[dict] = None):
        """在事务中查询"""
        return await self._conn.execute(text(sql), params or {}).fetchone()
    
    async def fetch_all(self, sql: str, params: Optional[dict] = None):
        """在事务中查询多条"""
        return await self._conn.execute(text(sql), params or {}).fetchall()
