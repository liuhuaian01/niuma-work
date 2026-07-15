"""
数据库索引优化脚本 (幂等可重复执行)

功能:
1. 为高频查询字段添加复合索引
2. 使用 IF NOT EXISTS 确保幂等性
3. 提供 EXPLAIN ANALYZE 验证工具

使用方法:
    python db/create_indexes.py
    
或在代码中调用:
    from db.create_indexes import create_optimized_indexes, analyze_query_performance
    await create_optimized_indexes(engine)
"""

import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


# ============================================================
# 索引定义 (按表分组)
# ============================================================

INDEX_DEFINITIONS = {
    "workspaces": [
        # 软删除查询优化
        "CREATE INDEX IF NOT EXISTS idx_workspaces_deleted ON workspaces(deleted_at)",
        # 按创建时间排序
        "CREATE INDEX IF NOT EXISTS idx_workspaces_created_at ON workspaces(created_at)",
    ],
    
    "agents": [
        # 工作间内Agent查询
        "CREATE INDEX IF NOT EXISTS idx_agents_workspace ON agents(workspace_id)",
        # 工作间+角色组合查询
        "CREATE INDEX IF NOT EXISTS idx_agents_role ON agents(workspace_id, role)",
        # 在线状态过滤
        "CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(workspace_id, status)",
        # 软删除过滤
        "CREATE INDEX IF NOT EXISTS idx_agents_deleted ON agents(deleted_at)",
    ],
    
    "workspace_configs": [
        # 配置查询优化
        "CREATE INDEX IF NOT EXISTS idx_workspace_configs_workspace ON workspace_configs(workspace_id)",
    ],
    
    "chat_messages": [
        # 工作间消息查询 (最频繁)
        "CREATE INDEX IF NOT EXISTS idx_messages_workspace ON chat_messages(workspace_id)",
        # 工作间+时间范围查询
        "CREATE INDEX IF NOT EXISTS idx_messages_time ON chat_messages(workspace_id, created_at)",
        # 工作间+时间倒序 (聊天历史)
        "CREATE INDEX IF NOT EXISTS idx_messages_workspace_desc ON chat_messages(workspace_id, created_at DESC)",
        # 角色过滤 (user/assistant)
        "CREATE INDEX IF NOT EXISTS idx_messages_role ON chat_messages(workspace_id, role)",
        # 父子消息关联
        "CREATE INDEX IF NOT EXISTS idx_messages_parent ON chat_messages(parent_message_id)",
        # 消息状态过滤
        "CREATE INDEX IF NOT EXISTS idx_messages_status ON chat_messages(workspace_id, status)",
    ],
    
    "orchestration_tasks": [
        # 工作间任务查询
        "CREATE INDEX IF NOT EXISTS idx_tasks_workspace ON orchestration_tasks(workspace_id)",
        # 工作间+状态组合
        "CREATE INDEX IF NOT EXISTS idx_tasks_status ON orchestration_tasks(workspace_id, status)",
        # Director Agent关联
        "CREATE INDEX IF NOT EXISTS idx_tasks_director ON orchestration_tasks(director_agent_id)",
        # 触发消息关联
        "CREATE INDEX IF NOT EXISTS idx_tasks_trigger ON orchestration_tasks(trigger_message_id)",
    ],
    
    "scheduled_reports": [
        # 工作间报告查询
        "CREATE INDEX IF NOT EXISTS idx_reports_workspace ON scheduled_reports(workspace_id)",
        # 启用状态过滤
        "CREATE INDEX IF NOT EXISTS idx_reports_enabled ON scheduled_reports(enabled)",
        # 下次执行时间 (定时任务调度)
        "CREATE INDEX IF NOT EXISTS idx_reports_next_run ON scheduled_reports(next_run_at)",
    ],
    
    "skill_market": [
        # 分类查询
        "CREATE INDEX IF NOT EXISTS idx_skill_category ON skill_market(category)",
        # 激活状态过滤
        "CREATE INDEX IF NOT EXISTS idx_skill_active ON skill_market(is_active)",
        # 技能名称搜索
        "CREATE INDEX IF NOT EXISTS idx_skill_name ON skill_market(name)",
    ],
    
    "user_skills": [
        # 技能ID关联
        "CREATE INDEX IF NOT EXISTS idx_user_skills_skill_id ON user_skills(skill_id)",
        # 启用状态过滤
        "CREATE INDEX IF NOT EXISTS idx_user_skills_enabled ON user_skills(enabled)",
        # 来源过滤 (market/custom)
        "CREATE INDEX IF NOT EXISTS idx_user_skills_source ON user_skills(source)",
    ],
    
    "l2_memory_entries": [
        # 工作间记忆查询
        "CREATE INDEX IF NOT EXISTS idx_l2_workspace ON l2_memory_entries(workspace_id)",
        # 过期时间过滤
        "CREATE INDEX IF NOT EXISTS idx_l2_expires ON l2_memory_entries(expires_at)",
        # 工作间+过期时间组合 (清理过期数据)
        "CREATE INDEX IF NOT EXISTS idx_l2_workspace_expires ON l2_memory_entries(workspace_id, expires_at)",
        # 条目类型过滤
        "CREATE INDEX IF NOT EXISTS idx_l2_type ON l2_memory_entries(workspace_id, entry_type)",
        # 源会话关联
        "CREATE INDEX IF NOT EXISTS idx_l2_source_session ON l2_memory_entries(source_session_id)",
        # 检索次数 (L3升级候选)
        "CREATE INDEX IF NOT EXISTS idx_l2_retrieval ON l2_memory_entries(retrieval_count)",
    ],
    
    "audit_logs": [
        # 审计日志时间排序
        "CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_logs(created_at)",
        # 操作类型过滤
        "CREATE INDEX IF NOT EXISTS idx_audit_operation ON audit_logs(operation)",
        # 工作间审计查询
        "CREATE INDEX IF NOT EXISTS idx_audit_workspace ON audit_logs(workspace_id)",
        # Agent操作审计
        "CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_logs(agent_id)",
        # 工作间+时间倒序 (审计面板)
        "CREATE INDEX IF NOT EXISTS idx_audit_workspace_time ON audit_logs(workspace_id, created_at DESC)",
    ],
    
    "backup_records": [
        # 备份记录时间排序
        "CREATE INDEX IF NOT EXISTS idx_backup_created ON backup_records(created_at)",
        # 备份类型过滤
        "CREATE INDEX IF NOT EXISTS idx_backup_type ON backup_records(type)",
    ],
    
    "background_tasks": [
        # 工作间后台任务
        "CREATE INDEX IF NOT EXISTS idx_bg_tasks_workspace ON background_tasks(workspace_id)",
        # 工作间+状态组合
        "CREATE INDEX IF NOT EXISTS idx_bg_tasks_status ON background_tasks(workspace_id, status)",
        # Agent任务查询
        "CREATE INDEX IF NOT EXISTS idx_bg_tasks_agent ON background_tasks(agent_id)",
        # 触发消息关联
        "CREATE INDEX IF NOT EXISTS idx_bg_tasks_trigger ON background_tasks(trigger_message_id)",
        # 结果消息关联
        "CREATE INDEX IF NOT EXISTS idx_bg_tasks_result ON background_tasks(result_message_id)",
    ],
}


async def create_optimized_indexes(engine: AsyncEngine):
    """
    创建所有优化索引 (幂等操作)
    
    Args:
        engine: SQLAlchemy 异步引擎实例
        
    Returns:
        dict: 包含每个表的索引创建统计
            {
                "total_indexes": 总索引数,
                "created": 新创建的索引数,
                "skipped": 已存在跳过的索引数,
                "errors": 错误数
            }
    """
    stats = {
        "total_indexes": 0,
        "created": 0,
        "skipped": 0,
        "errors": 0,
    }
    
    logger.info("开始创建数据库优化索引...")
    
    async with engine.begin() as conn:
        for table_name, indexes in INDEX_DEFINITIONS.items():
            logger.info(f"处理表 '{table_name}' 的索引 ({len(indexes)} 个)...")
            
            for index_sql in indexes:
                stats["total_indexes"] += 1
                
                try:
                    # 检查索引是否已存在
                    index_name = index_sql.split("idx_")[1].split(" ")[0]
                    index_name = f"idx_{index_name}"
                    
                    check_sql = text("""
                        SELECT name FROM sqlite_master 
                        WHERE type='index' AND name=:idx_name
                    """)
                    result = await conn.execute(check_sql, {"idx_name": index_name})
                    exists = result.fetchone() is not None
                    
                    if exists:
                        stats["skipped"] += 1
                        logger.debug(f"  ✓ 索引 '{index_name}' 已存在,跳过")
                    else:
                        # 创建索引
                        await conn.execute(text(index_sql))
                        stats["created"] += 1
                        logger.info(f"  + 创建索引 '{index_name}'")
                        
                except Exception as e:
                    stats["errors"] += 1
                    logger.error(f"  ✗ 创建索引失败: {e}")
                    logger.error(f"    SQL: {index_sql}")
    
    logger.info(
        f"索引创建完成: "
        f"总计={stats['total_indexes']}, "
        f"新建={stats['created']}, "
        f"跳过={stats['skipped']}, "
        f"错误={stats['errors']}"
    )
    
    return stats


async def analyze_query_performance(engine: AsyncEngine, queries: list[str] | None = None):
    """
    分析查询性能 (使用 EXPLAIN QUERY PLAN)
    
    Args:
        engine: SQLAlchemy 异步引擎实例
        queries: 要分析的查询列表,如果为None则使用默认高频查询
        
    Returns:
        list[dict]: 每个查询的执行计划
    """
    if queries is None:
        # 默认高频查询场景
        queries = [
            # 1. 聊天历史查询 (最常见)
            "SELECT * FROM chat_messages WHERE workspace_id = 'ws_001' ORDER BY created_at DESC LIMIT 20",
            
            # 2. Agent状态查询
            "SELECT * FROM agents WHERE workspace_id = 'ws_001' AND status = 'online' AND deleted_at IS NULL",
            
            # 3. 任务状态查询
            "SELECT * FROM orchestration_tasks WHERE workspace_id = 'ws_001' AND status = 'pending'",
            
            # 4. L2记忆清理查询
            "SELECT * FROM l2_memory_entries WHERE workspace_id = 'ws_001' AND expires_at < datetime('now')",
            
            # 5. 审计日志查询
            "SELECT * FROM audit_logs WHERE workspace_id = 'ws_001' ORDER BY created_at DESC LIMIT 50",
            
            # 6. 后台任务查询
            "SELECT * FROM background_tasks WHERE workspace_id = 'ws_001' AND status = 'running'",
            
            # 7. 技能市场查询
            "SELECT * FROM skill_market WHERE category = '文档内容' AND is_active = 1",
            
            # 8. 用户技能查询
            "SELECT * FROM user_skills WHERE enabled = 1 AND source = 'market'",
        ]
    
    results = []
    
    async with engine.begin() as conn:
        for i, query in enumerate(queries, 1):
            logger.info(f"\n分析查询 #{i}: {query[:80]}...")
            
            try:
                explain_sql = text(f"EXPLAIN QUERY PLAN {query}")
                result = await conn.execute(explain_sql)
                plan_rows = result.fetchall()
                
                plan_details = []
                uses_index = False
                
                for row in plan_rows:
                    detail = str(row)
                    plan_details.append(detail)
                    
                    # 检测是否使用索引
                    if "USING INDEX" in detail or "USING COVERING INDEX" in detail:
                        uses_index = True
                        logger.info(f"  ✓ 使用索引: {detail}")
                    elif "SCAN TABLE" in detail:
                        logger.warning(f"  ⚠ 全表扫描: {detail}")
                
                results.append({
                    "query": query,
                    "uses_index": uses_index,
                    "plan": plan_details,
                })
                
            except Exception as e:
                logger.error(f"  ✗ 分析失败: {e}")
                results.append({
                    "query": query,
                    "error": str(e),
                })
    
    return results


def print_analysis_report(results: list[dict]):
    """打印分析报告"""
    print("\n" + "="*80)
    print("数据库索引优化分析报告")
    print("="*80)
    
    total_queries = len(results)
    indexed_queries = sum(1 for r in results if r.get("uses_index", False))
    scan_queries = total_queries - indexed_queries
    
    print(f"\n总查询数: {total_queries}")
    print(f"使用索引: {indexed_queries} ({indexed_queries/total_queries*100:.1f}%)")
    print(f"全表扫描: {scan_queries} ({scan_queries/total_queries*100:.1f}%)")
    
    print("\n" + "-"*80)
    print("详细执行计划:")
    print("-"*80)
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. 查询: {result['query'][:100]}...")
        
        if "error" in result:
            print(f"   错误: {result['error']}")
            continue
        
        status = "✓ 使用索引" if result["uses_index"] else "⚠ 全表扫描"
        print(f"   状态: {status}")
        
        print("   执行计划:")
        for line in result["plan"]:
            print(f"     {line}")
    
    print("\n" + "="*80)
    
    if scan_queries > 0:
        print("\n⚠ 警告: 发现全表扫描查询,建议添加相应索引!")
    else:
        print("\n✓ 所有查询均已使用索引优化!")
    
    print("="*80 + "\n")


# ============================================================
# 主函数 (命令行入口)
# ============================================================

async def main():
    """命令行执行入口"""
    import sys
    import os
    
    # 添加项目根目录到路径
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from db.database import get_engine, init_db
    
    # 初始化数据库
    await init_db()
    engine = get_engine()
    
    print("\n📊 步骤 1: 创建优化索引")
    print("-" * 80)
    stats = await create_optimized_indexes(engine)
    print(f"\n统计: {stats}")
    
    print("\n🔍 步骤 2: 分析查询性能")
    print("-" * 80)
    results = await analyze_query_performance(engine)
    print_analysis_report(results)
    
    print("\n✅ 索引优化完成!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
