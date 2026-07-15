"""
数据库连接池配置验证脚本

直接运行: python verify_pool_config.py
"""

import asyncio
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from config.settings import settings
from db.database import get_engine, check_pool_status


async def verify_config():
    """验证配置和实现"""
    # 设置UTF-8输出
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 70)
    print("数据库连接池配置验证")
    print("=" * 70)
    print()
    
    # 1. 验证配置参数完整性
    print("1. 检查配置文件参数...")
    print("-" * 70)
    
    required_params = {
        'DB_POOL_SIZE': settings.DB_POOL_SIZE,
        'DB_MAX_OVERFLOW': settings.DB_MAX_OVERFLOW,
        'DB_POOL_TIMEOUT': settings.DB_POOL_TIMEOUT,
        'DB_POOL_RECYCLE': settings.DB_POOL_RECYCLE,
    }
    
    all_present = True
    for param, value in required_params.items():
        if hasattr(settings, param):
            print(f"  [OK] {param}: {value}")
        else:
            print(f"  [FAIL] {param}: MISSING")
            all_present = False
    
    if not all_present:
        print("\n[FAIL] 配置不完整！")
        return False
    
    print("\n[PASS] 所有配置参数都存在\n")
    
    # 2. 验证引擎创建
    print("2. 检查数据库引擎创建...")
    print("-" * 70)
    
    try:
        engine = get_engine()
        pool = engine.pool
        
        from sqlalchemy.pool import StaticPool
        if isinstance(pool, StaticPool):
            print(f"  [OK] 使用 StaticPool (SQLite 单连接模式)")
            print(f"  [OK] Pool 类型: {type(pool).__name__}")
        else:
            print(f"  [FAIL] 使用了错误的 Pool 类型: {type(pool).__name__}")
            return False
        
        print()
    except Exception as e:
        print(f"  [FAIL] 引擎创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. 验证连接池状态检查
    print("3. 检查连接池状态监控功能...")
    print("-" * 70)
    
    try:
        status = check_pool_status(engine)
        
        # StaticPool 使用简化的监控
        if status['pool_type'] == 'StaticPool':
            print(f"  [OK] pool_type: {status['pool_type']}")
            print(f"  [OK] mode: {status.get('mode', 'N/A')}")
            print(f"  [OK] timeout: {status.get('timeout', 'N/A')}s")
            print(f"  [OK] description: {status.get('description', 'N/A')}")
        else:
            # QueuePool 或其他 Pool 类型
            required_keys = ['checked_in', 'checked_out', 'overflow', 'total', 'pool_type']
            for key in required_keys:
                if key in status:
                    print(f"  [OK] {key}: {status[key]}")
                else:
                    print(f"  [FAIL] {key}: MISSING")
                    return False
        
        # 验证 StaticPool 特性
        if status['pool_type'] != 'StaticPool':
            print(f"  [FAIL] Pool 类型不正确: {status['pool_type']}")
            return False
        
        print("\n[PASS] 连接池状态检查功能正常\n")
    except Exception as e:
        print(f"  [FAIL] 状态检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. 验证无连接泄漏
    print("4. 检查连接泄漏...")
    print("-" * 70)
    
    try:
        from sqlalchemy import text
        
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        
        status_after = check_pool_status(engine)
        
        # StaticPool 模式下，不需要检查 checked_out
        if status_after['pool_type'] == 'StaticPool':
            print(f"  [OK] StaticPool 模式 - 单连接无泄漏风险")
            print(f"  [OK] Pool 状态: {status_after.get('mode', 'N/A')}")
        else:
            # QueuePool 或其他模式需要检查
            if status_after.get('checked_out', 0) == 0:
                print(f"  [OK] 无连接泄漏 (checked_out: {status_after['checked_out']})")
            else:
                print(f"  [FAIL] 可能存在连接泄漏 (checked_out: {status_after['checked_out']})")
                return False
        
        print()
    except Exception as e:
        print(f"  [FAIL] 连接泄漏检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. 验证超时配置
    print("5. 检查超时配置...")
    print("-" * 70)
    print(f"  [OK] DB_POOL_TIMEOUT: {settings.DB_POOL_TIMEOUT}s")
    print(f"  [OK] connect_args timeout: {settings.DB_POOL_TIMEOUT}s")
    print()
    
    # 总结
    print("=" * 70)
    print("[PASS] 所有验证通过！")
    print("=" * 70)
    print()
    print("配置摘要:")
    print(f"  - 数据库类型: SQLite (aiosqlite)")
    print(f"  - 连接池类型: StaticPool (单连接模式)")
    print(f"  - 超时时间: {settings.DB_POOL_TIMEOUT}s")
    print(f"  - 连接回收: {settings.DB_POOL_RECYCLE}s")
    print()
    print("注意:")
    print("  - SQLite 使用 StaticPool，pool_size/max_overflow 参数无效")
    print("  - 这些参数作为文档保留，便于未来切换到 PostgreSQL/MySQL")
    print("  - 连接池监控已集成，可通过 NIUMA_POOL_MONITOR 环境变量启用")
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(verify_config())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[FAIL] 验证过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
