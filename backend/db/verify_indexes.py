"""
数据库索引验证工具 (独立运行,无需pytest)

功能:
1. 验证所有索引已正确创建
2. 使用 EXPLAIN QUERY PLAN 确认查询使用索引
3. 性能基准测试

运行方式:
    python db/verify_indexes.py
"""

import asyncio
import sys
import os
import time
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import get_engine, init_db
from db.create_indexes import create_optimized_indexes, analyze_query_performance, print_analysis_report
from sqlalchemy import text


async def verify_indexes():
    """验证索引优化效果"""
    print("\n" + "="*80)
    print("数据库索引优化验证报告")
    print("="*80)
    
    # 初始化数据库
    print("\n[1/5] 初始化数据库")
    print("-" * 80)
    await init_db()
    engine = get_engine()
    print("OK 数据库初始化完成")
    
    # 创建/验证索引
    print("\n[2/5] 创建优化索引")
    print("-" * 80)
    stats = await create_optimized_indexes(engine)
    print(f"\n统计结果:")
    print(f"  总索引数: {stats['total_indexes']}")
    print(f"  新建索引: {stats['created']}")
    print(f"  跳过索引: {stats['skipped']}")
    print(f"  错误数量: {stats['errors']}")
    
    if stats['errors'] > 0:
        print("\nWARNING: 索引创建过程中出现错误!")
    else:
        print("\nOK 所有索引创建成功")
    
    # 列出所有索引
    print("\n[3/5] 数据库索引清单")
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
            print(f"  OK {index_name}")
    
    print(f"\n总计: {len(indexes)} 个业务索引")
    
    # 分析查询性能
    print("\n[4/5] 查询性能分析 (EXPLAIN QUERY PLAN)")
    print("-" * 80)
    
    # 定义高频查询场景
    test_queries = [
        ("聊天历史查询", "SELECT * FROM chat_messages WHERE workspace_id = 'ws_001' ORDER BY created_at DESC LIMIT 20"),
        ("Agent状态查询", "SELECT * FROM agents WHERE workspace_id = 'ws_001' AND status = 'online' AND deleted_at IS NULL"),
        ("任务状态查询", "SELECT * FROM orchestration_tasks WHERE workspace_id = 'ws_001' AND status = 'pending'"),
        ("L2记忆清理", "SELECT * FROM l2_memory_entries WHERE workspace_id = 'ws_001' AND expires_at < datetime('now')"),
        ("审计日志查询", "SELECT * FROM audit_logs WHERE workspace_id = 'ws_001' ORDER BY created_at DESC LIMIT 50"),
        ("后台任务查询", "SELECT * FROM background_tasks WHERE workspace_id = 'ws_001' AND status = 'running'"),
        ("技能市场查询", "SELECT * FROM skill_market WHERE category = '文档内容' AND is_active = 1"),
        ("用户技能查询", "SELECT * FROM user_skills WHERE enabled = 1 AND source = 'market'"),
    ]
    
    query_names = [name for name, _ in test_queries]
    queries = [sql for _, sql in test_queries]
    
    results = await analyze_query_performance(engine, queries)
    
    print("\n详细分析:")
    print("-" * 80)
    
    indexed_count = 0
    scan_count = 0
    
    for i, (result, name) in enumerate(zip(results, query_names), 1):
        print(f"\n{i}. {name}")
        print(f"   查询: {result['query'][:70]}...")
        
        if "error" in result:
            print(f"   ❌ 错误: {result['error']}")
            continue
        
        uses_index = result.get("uses_index", False)
        if uses_index:
            print(f"   OK 使用索引")
            indexed_count += 1
        else:
            print(f"   WARNING 全表扫描")
            scan_count += 1
        
        # 显示执行计划摘要
        plan_summary = []
        for line in result["plan"]:
            line_str = str(line)
            if "USING INDEX" in line_str:
                plan_summary.append(f"      [INDEX] {line_str.strip()}")
            elif "SCAN TABLE" in line_str:
                plan_summary.append(f"      [SCAN] {line_str.strip()}")
        
        if plan_summary:
            print("   执行计划:")
            for summary in plan_summary:
                print(summary)
    
    # 性能总结
    print("\n" + "="*80)
    print("性能优化总结")
    print("="*80)
    print(f"\n总查询数: {len(results)}")
    print(f"OK 使用索引: {indexed_count} ({indexed_count/len(results)*100:.1f}%)")
    print(f"WARNING 全表扫描: {scan_count} ({scan_count/len(results)*100:.1f}%)")
    
    if scan_count == 0:
        print("\nEXCELLENT! 所有高频查询均已使用索引优化!")
    elif scan_count <= 2:
        print(f"\nGOOD! 大部分查询已优化,仅 {scan_count} 个查询需要进一步调整。")
    else:
        print(f"\nATTENTION: {scan_count} 个查询仍在使用全表扫描,建议添加相应索引。")
    
    # 性能基准测试
    print("\n[5/5] 性能基准测试")
    print("-" * 80)
    
    # 准备测试数据
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM workspaces"))
        ws_count = result.scalar()
        
        if ws_count == 0:
            now = datetime.utcnow().isoformat()
            await conn.execute(text("""
                INSERT INTO workspaces (id, name, created_at, updated_at)
                VALUES ('ws_bench', 'Benchmark Workspace', :now, :now)
            """), {"now": now})
            
            # 插入测试消息
            print("  插入测试数据...")
            for i in range(100):
                msg_time = (datetime.utcnow() - timedelta(minutes=i)).isoformat()
                await conn.execute(text("""
                    INSERT INTO chat_messages (id, workspace_id, role, content, created_at)
                    VALUES (:id, 'ws_bench', 'user', 'Test message', :time)
                """), {"id": f"msg_{i}", "time": msg_time})
            print("  OK 测试数据准备完成")
    
    # 执行基准测试
    iterations = 10
    times = []
    
    print(f"\n执行 {iterations} 次查询测试...")
    for i in range(iterations):
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
    
    print(f"\n性能测试结果:")
    print(f"  平均响应时间: {avg_time*1000:.2f} ms")
    print(f"  最快响应时间: {min_time*1000:.2f} ms")
    print(f"  最慢响应时间: {max_time*1000:.2f} ms")
    
    if avg_time < 0.01:
        print(f"\nOK 优秀! 平均响应时间 < 10ms")
    elif avg_time < 0.05:
        print(f"\nOK 良好! 平均响应时间 < 50ms")
    else:
        print(f"\nWARNING 一般: 平均响应时间 {avg_time*1000:.2f}ms,可能需要进一步优化")
    
    # 最终验收标准检查
    print("\n" + "="*80)
    print("验收标准检查")
    print("="*80)
    
    checks = [
        ("核心查询使用索引", indexed_count >= len(results) * 0.8, 
         f"{indexed_count}/{len(results)} 个查询使用索引"),
        ("无全表扫描或极少", scan_count <= 2, 
         f"{scan_count} 个全表扫描查询"),
        ("响应时间 < 50ms", avg_time < 0.05, 
         f"平均 {avg_time*1000:.2f}ms"),
        ("索引创建幂等", stats['errors'] == 0, 
         f"错误数: {stats['errors']}"),
    ]
    
    all_passed = True
    for check_name, passed, detail in checks:
        status = "OK" if passed else "FAIL"
        print(f"[{status}] {check_name}: {detail}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*80)
    if all_passed:
        print("SUCCESS! 所有验收标准通过! 索引优化成功!")
    else:
        print("WARNING: 部分验收标准未通过,请查看上述详情。")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(verify_indexes())
