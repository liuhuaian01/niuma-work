"""
数据库版本迁移系统

检测当前数据库版本，执行增量迁移脚本。
Pi 原则：迁移必须是幂等的，多次执行结果一致。
"""

from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent
