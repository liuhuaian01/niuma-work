"""
日志配置模块

统一日志格式和级别,支持开发/生产环境不同配置。

环境自适应策略:
- development: DEBUG级别详细日志,便于调试
- production: WARNING级别日志,减少性能影响
- 关键业务模块(engine/services)始终保持INFO级别
"""

import logging
import os
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from config.settings import settings


def setup_logging():
    """配置全局日志系统 - 环境自适应
    
    根据ENVIRONMENT环境变量自动调整日志级别:
    - development: 控制台DEBUG + 文件INFO,详细日志便于调试
    - production: 控制台WARNING + 文件WARNING,减少性能影响
    - 关键业务模块(engine/services)始终保持INFO级别
    
    日志文件策略:
    - app.log: 应用主日志,按天轮转,保留30天
    - error.log: 错误日志,按天轮转,保留90天
    - taiji_engine.log: 太极引擎专用日志,按大小轮转(10MB*5=50MB上限)
    """
    # 获取环境配置
    env = os.getenv('ENVIRONMENT', 'development').lower()
    is_production = env == 'production'
    
    # 根据环境设置根日志级别
    if is_production:
        root_level = logging.WARNING
        console_level = logging.WARNING
        file_level = logging.WARNING
    else:
        root_level = logging.DEBUG
        console_level = logging.DEBUG
        file_level = logging.INFO
    
    # 根日志器配置
    root_logger = logging.getLogger()
    root_logger.setLevel(root_level)
    
    # 清除已有handler(避免重复)
    root_logger.handlers.clear()
    
    # 日志格式
    detailed_format = logging.Formatter(
        fmt="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    simple_format = logging.Formatter(
        fmt="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S"
    )
    
    # 1. 控制台处理器(始终启用)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(simple_format if not is_production else detailed_format)
    root_logger.addHandler(console_handler)
    
    # 2. 文件处理器(始终启用,带轮转)
    log_dir = Path(settings.DATA_DIR) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 应用日志 - 按天轮转,保留30天
    app_log_file = log_dir / "app.log"
    app_handler = TimedRotatingFileHandler(
        filename=app_log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    app_handler.setLevel(file_level)
    app_handler.setFormatter(detailed_format)
    root_logger.addHandler(app_handler)
    
    # 错误日志 - 单独记录ERROR及以上,保留90天
    error_log_file = log_dir / "error.log"
    error_handler = TimedRotatingFileHandler(
        filename=error_log_file,
        when="midnight",
        interval=1,
        backupCount=90,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_format)
    root_logger.addHandler(error_handler)
    
    # 太极引擎专用日志 - 按大小轮转(10MB*5=50MB上限)
    taiji_log_file = log_dir / "taiji_engine.log"
    taiji_handler = RotatingFileHandler(
        filename=taiji_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,               # 最多5个备份文件,总计50MB
        encoding="utf-8"
    )
    taiji_handler.setLevel(logging.DEBUG if not is_production else logging.INFO)
    taiji_handler.setFormatter(detailed_format)
    
    # 太极引擎日志器
    taiji_logger = logging.getLogger("niuma.engine")
    taiji_logger.setLevel(logging.DEBUG if not is_production else logging.INFO)
    taiji_logger.addHandler(taiji_handler)
    
    # 3. 关键业务模块单独配置INFO级别(不受环境影响)
    logging.getLogger('engine').setLevel(logging.INFO)
    logging.getLogger('services').setLevel(logging.INFO)
    logging.getLogger('niuma.engine').setLevel(logging.INFO)
    logging.getLogger('niuma.services').setLevel(logging.INFO)
    
    # 抑制第三方库的过多日志
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # 记录启动信息
    logger = logging.getLogger("niuma.logging")
    logger.info(f"日志系统初始化完成 (ENV={env}, ROOT_LEVEL={logging.getLevelName(root_level)}, "
                f"CONSOLE_LEVEL={logging.getLevelName(console_level)}, FILE_LEVEL={logging.getLevelName(file_level)})")
    logger.info(f"日志文件目录: {log_dir}")
    logger.info(f"太极引擎日志轮转策略: 10MB/文件, 最多5个备份(总计50MB)")


def get_logger(name: str) -> logging.Logger:
    """获取命名日志器
    
    Args:
        name: 日志器名称，通常使用 __name__
        
    Returns:
        配置好的Logger实例
    """
    # 确保以 niuma 为前缀，便于日志过滤
    if not name.startswith("niuma"):
        name = f"niuma.{name}"
    return logging.getLogger(name)
