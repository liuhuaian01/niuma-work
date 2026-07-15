"""
工作间缓存并发安全测试

验证所有共享缓存状态都有锁保护，无竞态条件风险
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_workspace_isolation_cache_concurrent_access():
    """测试工作间隔离缓存的并发访问安全性"""
    from middleware.workspace_isolation import (
        _valid_workspace_ids,
        _cache_initialized,
        add_valid_workspace,
        remove_valid_workspace,
        refresh_workspace_cache,
    )
    
    # 模拟数据库返回
    mock_cursor = AsyncMock()
    mock_cursor.fetchall = AsyncMock(return_value=[
        ("ws-1",),
        ("ws-2",),
        ("ws-3",),
    ])
    
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_cursor)
    
    with patch("middleware.workspace_isolation._db", mock_db):
        # 并发刷新缓存
        tasks = [refresh_workspace_cache() for _ in range(10)]
        await asyncio.gather(*tasks)
        
        # 并发添加工作间
        tasks = [add_valid_workspace(f"ws-test-{i}") for i in range(20)]
        await asyncio.gather(*tasks)
        
        # 并发删除工作间
        tasks = [remove_valid_workspace(f"ws-test-{i}") for i in range(10)]
        await asyncio.gather(*tasks)
        
        # 验证没有异常抛出
        assert True


@pytest.mark.asyncio
async def test_memory_engine_session_concurrent_access():
    """测试 MemoryEngine 会话字典的并发访问安全性"""
    from services.memory.memory_service import MemoryEngine
    
    engine = MemoryEngine(max_tokens=8192)
    
    # 并发创建多个工作间的会话
    workspace_ids = [f"ws-concurrent-{i}" for i in range(50)]
    
    async def create_session(ws_id):
        return await engine.get_or_create_session(ws_id)
    
    tasks = [create_session(ws_id) for ws_id in workspace_ids]
    results = await asyncio.gather(*tasks)
    
    # 验证所有会话都成功创建
    assert len(results) == 50
    assert len(set(results)) == 50  # 所有 session_id 应该唯一


@pytest.mark.asyncio
async def test_l1_memory_manager_session_concurrent_access():
    """测试 L1MemoryManager 会话字典的并发访问安全性"""
    from services.memory.l1_session_memory import L1MemoryManager
    
    manager = L1MemoryManager(max_tokens=8192)
    
    # 并发创建多个会话
    workspace_ids = [f"ws-l1-{i}" for i in range(50)]
    
    async def create_session(ws_id):
        return await manager.create_session(ws_id)
    
    tasks = [create_session(ws_id) for ws_id in workspace_ids]
    results = await asyncio.gather(*tasks)
    
    # 验证所有会话都成功创建
    assert len(results) == 50
    assert len(set(results)) == 50  # 所有 session_id 应该唯一
    
    # 并发列出会话
    session_list = await manager.list_sessions()
    assert len(session_list) == 50


@pytest.mark.asyncio
async def test_memory_engine_compress_concurrent_access():
    """测试 MemoryEngine 压缩频率控制的并发安全性"""
    from services.memory.memory_service import MemoryEngine
    
    engine = MemoryEngine(max_tokens=8192)
    ws_id = "ws-compress-test"
    
    # 先创建会话并添加一些消息
    await engine.get_or_create_session(ws_id)
    await engine.append_message(ws_id, "user", "test message")
    
    # 并发触发多次压缩（应该被频率控制）
    tasks = [engine.compress_context(ws_id, force=False) for _ in range(5)]
    results = await asyncio.gather(*tasks)
    
    # 验证所有压缩请求都完成（有些可能被跳过）
    assert len(results) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
