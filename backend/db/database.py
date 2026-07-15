"""
数据库连接与初始化

Phase 2: metadata.create_all() 统一建表，废弃 _SCHEMA_SQL 原始 SQL。
SQLite 使用 StaticPool（单连接），因为 SQLite 是文件级锁，多连接会导致性能下降。
"""

import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import text
from sqlalchemy.pool import StaticPool

from config.settings import settings
from models.tables import metadata

logger = logging.getLogger(__name__)

# 全局引擎单例
_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """获取数据库引擎（延迟初始化）
    
    SQLite 使用 StaticPool（单连接模式），避免多连接导致的文件锁竞争。
    
    注意：
    - pool_size/max_overflow 等参数在 StaticPool 模式下无效
    - connect_args 中的 timeout 参数控制 SQLite 文件锁等待时间
    - 如需切换到 PostgreSQL/MySQL，可移除 poolclass=StaticPool 并启用连接池参数
    """
    global _engine
    if _engine is None:
        db_dir = os.path.dirname(settings.DB_PATH)
        os.makedirs(db_dir, exist_ok=True)
        
        # SQLite 专用配置：使用 StaticPool 单连接模式
        engine_kwargs = {
            "echo": settings.DEBUG,
            "poolclass": StaticPool,
            "connect_args": {"timeout": settings.DB_POOL_TIMEOUT},
        }
        
        # 记录连接池配置（用于调试）
        logger.info(
            f"Database engine initialized with StaticPool (SQLite mode). "
            f"Timeout: {settings.DB_POOL_TIMEOUT}s"
        )
        
        _engine = create_async_engine(
            settings.DB_URL,
            **engine_kwargs
        )
    return _engine


async def init_db():
    """初始化数据库：启用 WAL + 建表（metadata.create_all）+ 创建优化索引"""
    engine = get_engine()

    async with engine.begin() as conn:
        # SQLite 优化
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.execute(text("PRAGMA busy_timeout=5000"))

        # 使用 SQLAlchemy metadata 建表（含索引）
        await conn.run_sync(metadata.create_all)

    # 创建性能优化索引 (幂等操作)
    from db.create_indexes import create_optimized_indexes
    await create_optimized_indexes(engine)

    # 初始化技能市场种子数据
    await _seed_skill_market()


async def _seed_skill_market():
    """初始化技能市场种子数据（幂等）"""
    engine = get_engine()
    async with engine.begin() as conn:
        count_result = await conn.execute(text("SELECT COUNT(*) FROM skill_market"))
        count = count_result.scalar()
        if count > 0:
            return  # 已初始化，跳过

        now = "2026-05-29T00:00:00Z"
        skills = [
            ("skill-deaihua", "去AI味", "检测并移除AI写作痕迹", "文档内容", "✍️", "low",
             "提升Writer文风自然度，减少AI痕迹", '["写作","文风","检测"]'),
            ("skill-value-check", "价值检验", "检验内容是否有实质信息量", "文档内容", "🔍", "low",
             "减少无效输出，提升内容密度", '["写作","质量"]'),
            ("skill-style-compare", "风格对比", "对比不同版本文风差异", "文档内容", "📊", "medium",
             "确保文风一致性", '["写作","对比"]'),
            ("skill-style-detect", "文风检测", "分析文本的写作风格特征", "文档内容", "🔬", "low",
             "减少Writer文风偏差", '["写作","检测"]'),
            ("skill-outline-gen", "大纲生成", "自动生成结构化大纲", "文档内容", "📋", "medium",
             "提升Director编排效率", '["写作","大纲"]'),
            ("skill-chara-mgmt", "角色管理", "管理小说角色档案和关系", "文档内容", "👥", "low",
             "保持角色一致性", '["写作","角色"]'),
            ("skill-conflict-detect", "剧情冲突检测", "检测情节逻辑矛盾", "文档内容", "⚡", "medium",
             "减少剧情Bug", '["写作","检测"]'),
            ("skill-market-analysis", "市场分析", "分析网文市场趋势和榜单", "搜索研究", "📈", "high",
             "为创作方向提供数据支撑", '["研究","市场"]'),
            ("skill-code-review", "代码审查", "审查代码质量和安全性", "代码开发", "🔍", "medium",
             "提升Coder输出质量", '["代码","审查"]'),
            ("skill-seo-optimize", "SEO优化", "优化内容搜索引擎可见性", "文档内容", "🎯", "low",
             "提升自媒体内容曝光", '["内容","SEO"]'),
            ("skill-translate-polish", "翻译润色", "翻译并润色多语言内容", "文档内容", "🌐", "medium",
             "提升翻译质量", '["翻译","润色"]'),
            ("skill-data-viz", "数据可视化", "将数据转化为可视化图表", "代码开发", "📊", "medium",
             "提升数据呈现效果", '["数据","可视化"]'),
        ]

        for skill in skills:
            await conn.execute(
                text(
                    "INSERT INTO skill_market (id, name, description, category, icon, token_level, "
                    "recommend_reason, tags, created_at, updated_at) "
                    "VALUES (:id, :name, :desc, :cat, :icon, :level, :reason, :tags, :now, :now)"
                ),
                {
                    "id": skill[0], "name": skill[1], "desc": skill[2],
                    "cat": skill[3], "icon": skill[4], "level": skill[5],
                    "reason": skill[6], "tags": skill[7], "now": now,
                },
            )


def check_pool_status(engine: AsyncEngine) -> dict:
    """检查连接池状态
    
    Args:
        engine: SQLAlchemy 异步引擎实例
        
    Returns:
        包含连接池状态的字典：
        - checked_in: 空闲连接数
        - checked_out: 正在使用的连接数
        - overflow: 溢出连接数（超过 pool_size 的连接）
        - total: 总连接数
        - pool_size: 配置的池大小
        - max_overflow: 配置的最大溢出数
        
    Note:
        SQLite 使用 StaticPool 时，这些值通常为:
        - checked_in: 1（唯一连接空闲时）
        - checked_out: 0 或 1（取决于是否有活跃事务）
        - overflow: 0（StaticPool 不支持溢出）
        - total: 1（始终只有一个连接）
    """
    pool = engine.pool
    pool_type = type(pool).__name__
    
    try:
        # StaticPool 没有 checkedin/checkedout 等方法，需要特殊处理
        if pool_type == 'StaticPool':
            # StaticPool 是单连接模式，简化监控
            status = {
                "pool_type": "StaticPool",
                "mode": "single_connection",
                "description": "SQLite uses single connection to avoid file lock contention",
                "timeout": settings.DB_POOL_TIMEOUT,
            }
        else:
            # QueuePool 或其他支持完整监控的 Pool
            status = {
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "total": pool.size(),
                "pool_size": getattr(pool, '_pool', None) or "N/A",
                "max_overflow": getattr(pool, '_max_overflow', None) or "N/A",
                "pool_type": pool_type,
            }
        
        logger.debug(f"Connection pool status: {status}")
        return status
        
    except Exception as e:
        logger.warning(f"Failed to get pool status: {e}")
        return {
            "error": str(e),
            "pool_type": pool_type,
        }


async def log_pool_status_periodically(interval_seconds: int = 300):
    """定期记录连接池状态（用于监控）
    
    Args:
        interval_seconds: 记录间隔（秒），默认 5 分钟
        
    Usage:
        在应用启动时作为后台任务运行：
        ```python
        import asyncio
        from db.database import log_pool_status_periodically, get_engine
        
        async def startup():
            await init_db()
            asyncio.create_task(log_pool_status_periodically(300))
        ```
    """
    import asyncio
    
    engine = get_engine()
    
    while True:
        try:
            status = check_pool_status(engine)
            logger.info(f"[Pool Monitor] {status}")
            
            # 检查是否有潜在的连接泄漏
            if status.get("checked_out", 0) > 3:
                logger.warning(
                    f"[Pool Monitor] High checked_out count: {status['checked_out']}. "
                    f"Possible connection leak?"
                )
            
        except Exception as e:
            logger.error(f"[Pool Monitor] Error checking pool status: {e}")
        
        await asyncio.sleep(interval_seconds)
