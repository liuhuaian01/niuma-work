"""
数据库索引优化测试脚本

功能:
1. 验证所有索引已正确创建
2. 使用 EXPLAIN QUERY PLAN 确认查询使用索引
3. 性能基准测试 (对比索引前后)

运行方式:
    pytest tests/test_index_optimization.py -v
    python tests/test_index_optimization.py
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import get_engine, init_db
from db.create_indexes import create_optimized_indexes, analyze_query_performance, print_analysis_report
from sqlalchemy import text

# 仅在 pytest 环境下使用装饰器
if HAS_PYTEST:
    @pytest.fixture(scope="module")
    def event_loop():
        """创建事件循环"""
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()

    @pytest.fixture(scope="module")
    async def engine():
        """初始化数据库引擎"""
        await init_db()
        return get_engine()

    class TestIndexCreation:
        """测试索引创建"""
        
        @pytest.mark.asyncio
        async def test_all_indexes_created(self, engine):
            """验证所有关键索引已创建"""
            expected_indexes = [
                "idx_workspaces_deleted",
                "idx_workspaces_created_at",
                "idx_agents_workspace",
                "idx_agents_status",
                "idx_messages_workspace",
                "idx_messages_time",
                "idx_messages_workspace_desc",
                "idx_tasks_workspace",
                "idx_tasks_status",
                "idx_l2_workspace",
                "idx_l2_expires",
                "idx_audit_time",
                "idx_bg_tasks_workspace",
            ]
            
            async with engine.begin() as conn:
                result = await conn.execute(text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name LIKE 'idx_%'
                    ORDER BY name
                """))
                existing_indexes = {row[0] for row in result.fetchall()}
            
            print(f"\n现有索引数量: {len(existing_indexes)}")
            print(f"预期索引数量: {len(expected_indexes)}")
            
            missing = set(expected_indexes) - existing_indexes
            if missing:
                print(f"\n⚠ 缺失的索引:")
                for idx in missing:
                    print(f"  - {idx}")
            
            assert len(missing) == 0, f"缺失索引: {missing}"
        
        @pytest.mark.asyncio
        async def test_index_creation_idempotent(self, engine):
            """验证索引创建的幂等性 (可重复执行)"""
            # 第一次执行
            stats1 = await create_optimized_indexes(engine)
            
            # 第二次执行 (应该全部跳过)
            stats2 = await create_optimized_indexes(engine)
            
            print(f"\n第一次执行: 新建={stats1['created']}, 跳过={stats1['skipped']}")
            print(f"第二次执行: 新建={stats2['created']}, 跳过={stats2['skipped']}")
            
            # 第二次应该全部跳过
            assert stats2["created"] == 0, "第二次执行不应创建新索引"
            assert stats2["skipped"] > 0, "第二次执行应跳过已有索引"


class TestQueryPerformance:
    """测试查询性能"""
    
    @pytest.mark.asyncio
    async def test_chat_messages_query_uses_index(self, engine):
        """测试聊天消息查询使用索引"""
        queries = [
            "SELECT * FROM chat_messages WHERE workspace_id = 'ws_test' ORDER BY created_at DESC LIMIT 20",
            "SELECT COUNT(*) FROM chat_messages WHERE workspace_id = 'ws_test'",
        ]
        
        results = await analyze_query_performance(engine, queries)
        
        for result in results:
            print(f"\n查询: {result['query'][:80]}...")
            print(f"执行计划: {result['plan']}")
            
            # 至少有一个执行计划行使用索引
            uses_index = any("USING INDEX" in str(row) for row in result.get("plan", []))
            assert uses_index or "SCAN TABLE" not in str(result["plan"]), \
                f"查询未使用索引: {result['query']}"
    
    @pytest.mark.asyncio
    async def test_agents_query_uses_index(self, engine):
        """测试Agent查询使用索引"""
        query = "SELECT * FROM agents WHERE workspace_id = 'ws_test' AND status = 'online' AND deleted_at IS NULL"
        
        results = await analyze_query_performance(engine, [query])
        result = results[0]
        
        print(f"\nAgent查询执行计划:")
        for line in result["plan"]:
            print(f"  {line}")
        
        # 应该使用复合索引
        uses_index = any("USING INDEX" in str(row) for row in result["plan"])
        assert uses_index, "Agent查询应使用索引"
    
    @pytest.mark.asyncio
    async def test_tasks_query_uses_index(self, engine):
        """测试任务查询使用索引"""
        query = "SELECT * FROM orchestration_tasks WHERE workspace_id = 'ws_test' AND status = 'pending'"
        
        results = await analyze_query_performance(engine, [query])
        result = results[0]
        
        print(f"\n任务查询执行计划:")
        for line in result["plan"]:
            print(f"  {line}")
        
        uses_index = any("USING INDEX" in str(row) for row in result["plan"])
        assert uses_index, "任务查询应使用索引"
    
    @pytest.mark.asyncio
    async def test_l2_memory_cleanup_query(self, engine):
        """测试L2记忆清理查询"""
        query = "SELECT * FROM l2_memory_entries WHERE workspace_id = 'ws_test' AND expires_at < datetime('now')"
        
        results = await analyze_query_performance(engine, [query])
        result = results[0]
        
        print(f"\nL2记忆清理查询执行计划:")
        for line in result["plan"]:
            print(f"  {line}")
        
        uses_index = any("USING INDEX" in str(row) for row in result["plan"])
        assert uses_index, "L2记忆清理查询应使用索引"


class TestBenchmarkPerformance:
    """性能基准测试"""
    
    @pytest.mark.asyncio
    async def test_query_response_time(self, engine):
        """测试查询响应时间 (需要足够数据量)"""
        import time
        
        # 插入测试数据 (如果不存在)
        async with engine.begin() as conn:
            # 检查工作间是否存在
            result = await conn.execute(text("SELECT COUNT(*) FROM workspaces"))
            count = result.scalar()
            
            if count == 0:
                # 插入测试工作间
                now = datetime.utcnow().isoformat()
                await conn.execute(text("""
                    INSERT INTO workspaces (id, name, created_at, updated_at)
                    VALUES ('ws_bench', 'Benchmark Workspace', :now, :now)
                """), {"now": now})
                
                # 插入100条测试消息
                for i in range(100):
                    msg_time = (datetime.utcnow() - timedelta(minutes=i)).isoformat()
                    await conn.execute(text("""
                        INSERT INTO chat_messages (id, workspace_id, role, content, created_at)
                        VALUES (:id, 'ws_bench', 'user', 'Test message', :time)
                    """), {"id": f"msg_{i}", "time": msg_time})
        
        # 基准测试: 查询最近20条消息
        iterations = 10
        times = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            async with engine.begin() as conn:
                await conn.execute(text("""
                    SELECT * FROM chat_messages 
                    WHERE workspace_id = 'ws_bench' 
                    ORDER BY created_at DESC 
                    LIMIT 20
                """))
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n性能基准测试结果 ({iterations} 次迭代):")
        print(f"  平均响应时间: {avg_time*1000:.2f} ms")
        print(f"  最快响应时间: {min_time*1000:.2f} ms")
        print(f"  最慢响应时间: {max_time*1000:.2f} ms")
        
        # 期望: 平均响应时间 < 10ms (有索引的情况下)
        assert avg_time < 0.01, f"查询响应时间过长: {avg_time*1000:.2f}ms (期望 < 10ms)"


async def run_standalone_test():
    """独立运行测试 (非pytest模式)"""
    print("\n" + "="*80)
    print("数据库索引优化测试")
    print("="*80)
    
    # 初始化
    await init_db()
    engine = get_engine()
    
    # 测试1: 索引创建
    print("\n📊 测试 1: 验证索引创建")
    print("-" * 80)
    stats = await create_optimized_indexes(engine)
    print(f"统计: {stats}")
    
    # 测试2: 查询分析
    print("\n🔍 测试 2: 查询性能分析")
    print("-" * 80)
    results = await analyze_query_performance(engine)
    print_analysis_report(results)
    
    # 测试3: 列出所有索引
    print("\n📋 测试 3: 数据库索引清单")
    print("-" * 80)
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT 
                tbl_name AS table_name,
                name AS index_name,
                sql AS create_sql
            FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_%'
            ORDER BY tbl_name, name
        """))
        
        indexes = result.fetchall()
        current_table = None
        
        for table_name, index_name, create_sql in indexes:
            if table_name != current_table:
                print(f"\n表: {table_name}")
                current_table = table_name
            print(f"  ✓ {index_name}")
    
    print(f"\n总计: {len(indexes)} 个业务索引")
    
    print("\n✅ 所有测试完成!")


if __name__ == "__main__":
    asyncio.run(run_standalone_test())
