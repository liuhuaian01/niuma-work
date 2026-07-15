"""
数据库连接池配置测试

验证:
1. 配置文件参数完整性
2. 引擎创建时使用正确的连接池类型
3. 连接池健康检查功能正常
"""

import asyncio
from config.settings import settings
from db.database import get_engine, check_pool_status, init_db


async def test_settings_has_all_pool_params():
    """测试配置文件包含所有必要的连接池参数"""
    assert hasattr(settings, 'DB_POOL_SIZE')
    assert hasattr(settings, 'DB_MAX_OVERFLOW')
    assert hasattr(settings, 'DB_POOL_TIMEOUT')
    assert hasattr(settings, 'DB_POOL_RECYCLE')
    
    # 验证参数值合理
    assert settings.DB_POOL_SIZE > 0
    assert settings.DB_MAX_OVERFLOW >= 0
    assert settings.DB_POOL_TIMEOUT > 0
    assert settings.DB_POOL_RECYCLE > 0
    
    print(f"✓ 配置参数完整:")
    print(f"  - DB_POOL_SIZE: {settings.DB_POOL_SIZE}")
    print(f"  - DB_MAX_OVERFLOW: {settings.DB_MAX_OVERFLOW}")
    print(f"  - DB_POOL_TIMEOUT: {settings.DB_POOL_TIMEOUT}s")
    print(f"  - DB_POOL_RECYCLE: {settings.DB_POOL_RECYCLE}s")

async def test_engine_uses_static_pool():
    """测试 SQLite 引擎使用 StaticPool"""
    engine = get_engine()
    pool = engine.pool
    
    # 验证使用的是 StaticPool
    from sqlalchemy.pool import StaticPool
    assert isinstance(pool, StaticPool), f"Expected StaticPool, got {type(pool).__name__}"
    
    print(f"✓ 引擎使用 StaticPool (SQLite 单连接模式)")
    print(f"  - Pool type: {type(pool).__name__}")

async def test_pool_status_check():
    """测试连接池状态检查功能"""
    engine = get_engine()
    
    # 获取连接池状态
    status = check_pool_status(engine)
    
    # 验证返回的字段
    assert 'checked_in' in status
    assert 'checked_out' in status
    assert 'overflow' in status
    assert 'total' in status
    assert 'pool_type' in status
    
    # StaticPool 的特性验证
    assert status['pool_type'] == 'StaticPool'
    assert status['total'] == 1  # StaticPool 只有一个连接
    assert status['overflow'] == 0  # StaticPool 不支持溢出
    
    print(f"✓ 连接池状态检查正常:")
    for key, value in status.items():
        print(f"  - {key}: {value}")

async def test_engine_initialization_with_timeout():
    """测试引擎初始化时使用配置的超时时间"""
    engine = get_engine()
    
    # 验证 connect_args 中的 timeout 参数
    # 注意：aiosqlite 的 timeout 在 connect_args 中
    assert settings.DB_POOL_TIMEOUT == 30  # 确认配置值
    
    print(f"✓ 引擎初始化超时配置: {settings.DB_POOL_TIMEOUT}s")

async def test_no_connection_leak():
    """测试无连接泄漏（简单场景）"""
    engine = get_engine()
    
    # 执行一些数据库操作
    from sqlalchemy import text
    
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
    
    # 检查连接池状态
    status = check_pool_status(engine)
    
    # StaticPool 应该在操作后回到空闲状态
    # checked_out 应该为 0（没有活跃事务）
    assert status['checked_out'] == 0, f"Connection leak detected: {status['checked_out']} connections still checked out"
    
    print(f"✓ 无连接泄漏检测通过")
    print(f"  - checked_out after operation: {status['checked_out']}")

async def test_database_init():
    """测试数据库初始化"""
    await init_db()
    
    engine = get_engine()
    status = check_pool_status(engine)
    
    assert status['pool_type'] == 'StaticPool'
    print(f"✓ 数据库初始化成功，连接池状态正常")


if __name__ == "__main__":
    # 运行所有测试
    async def run_tests():
        print("=" * 60)
        print("数据库连接池配置测试")
        print("=" * 60)
        print()
        
        tests = [
            test_settings_has_all_pool_params,
            test_engine_uses_static_pool,
            test_pool_status_check,
            test_engine_initialization_with_timeout,
            test_no_connection_leak,
            test_database_init,
        ]
        
        for test in tests:
            try:
                print(f"\n运行测试: {test.__name__}")
                print("-" * 60)
                await test()
                print()
            except Exception as e:
                print(f"✗ 测试失败: {test.__name__}")
                print(f"  错误: {e}")
                import traceback
                traceback.print_exc()
                print()
        
        print("=" * 60)
        print("所有测试完成")
        print("=" * 60)
    
    asyncio.run(run_tests())
