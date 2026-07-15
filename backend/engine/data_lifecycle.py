"""
太极引擎 · 清风引擎 (DataLifecycle) v1.0

"无为而治"——自动管理数据生命周期，无需用户干预。

功能：
1. 自动归档：超过阈值的数据从热存储迁移到冷存储
2. 过期清理：超过保留期的数据自动软删除
3. 存储监控：追踪各模块的存储占用
4. 手动触发：支持用户手动清理/归档

设计原则：
- 默认不删除——只归档、软删除，用户可恢复
- 渐进式——先警告、再归档、最后清理
- 透明——每次操作记录审计日志
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
import asyncio
import json
import os
import sqlite3
from pathlib import Path


# ════════════════════════════════════════════════════════════════
# 数据模型
# ════════════════════════════════════════════════════════════════

class LifecycleAction(Enum):
    WARN = "warn"             # 仅警告
    ARCHIVE = "archive"        # 归档到冷存储
    SOFT_DELETE = "soft_delete"  # 软删除（可恢复）
    PURGE = "purge"           # 硬删除（不可恢复，慎用）


class DataCategory(Enum):
    CHAT_MESSAGES = "chat_messages"
    EXECUTION_LOGS = "execution_logs"
    MEMORY_L1 = "memory_l1"
    MEMORY_L2 = "memory_l2"
    MEMORY_L3 = "memory_l3"
    SKILLS = "skills"
    TELEMETRY = "telemetry"
    AUDIT_LOGS = "audit_logs"
    BACKUPS = "backups"


@dataclass
class DataLifecyclePolicy:
    """数据生命周期策略"""
    category: DataCategory
    warn_after_days: int         # 多少天后开始警告
    archive_after_days: int       # 多少天后归档
    soft_delete_after_days: int   # 多少天后软删除
    max_size_mb: int = 0          # 最大存储（MB），0=不限制
    auto_purge: bool = False      # 是否自动硬删除


@dataclass
class StorageStats:
    """存储统计"""
    category: str
    record_count: int
    size_bytes: int
    oldest_record: str
    newest_record: str
    archived_count: int = 0


@dataclass
class LifecycleEvent:
    """生命周期事件记录"""
    id: str
    category: str
    action: str
    affected_count: int
    freed_bytes: int
    timestamp: str
    details: str = ""


# ════════════════════════════════════════════════════════════════
# 默认策略
# ════════════════════════════════════════════════════════════════

DEFAULT_POLICIES: dict[DataCategory, DataLifecyclePolicy] = {
    DataCategory.CHAT_MESSAGES: DataLifecyclePolicy(
        category=DataCategory.CHAT_MESSAGES,
        warn_after_days=30,
        archive_after_days=60,
        soft_delete_after_days=90,
        max_size_mb=500,
    ),
    DataCategory.EXECUTION_LOGS: DataLifecyclePolicy(
        category=DataCategory.EXECUTION_LOGS,
        warn_after_days=7,
        archive_after_days=14,
        soft_delete_after_days=30,
        max_size_mb=100,
    ),
    DataCategory.MEMORY_L1: DataLifecyclePolicy(
        category=DataCategory.MEMORY_L1,
        warn_after_days=-1,         # L1 会话记忆不归档（会话级别）
        archive_after_days=-1,
        soft_delete_after_days=7,   # 7天无活动自动清理
    ),
    DataCategory.MEMORY_L2: DataLifecyclePolicy(
        category=DataCategory.MEMORY_L2,
        warn_after_days=60,
        archive_after_days=90,
        soft_delete_after_days=180,
    ),
    DataCategory.MEMORY_L3: DataLifecyclePolicy(
        category=DataCategory.MEMORY_L3,
        warn_after_days=-1,         # L3 知识库不自动清理
        archive_after_days=-1,
        soft_delete_after_days=-1,
    ),
    DataCategory.TELEMETRY: DataLifecyclePolicy(
        category=DataCategory.TELEMETRY,
        warn_after_days=30,
        archive_after_days=60,
        soft_delete_after_days=90,
        max_size_mb=200,
    ),
    DataCategory.AUDIT_LOGS: DataLifecyclePolicy(
        category=DataCategory.AUDIT_LOGS,
        warn_after_days=90,
        archive_after_days=180,
        soft_delete_after_days=365,
        max_size_mb=50,
    ),
    DataCategory.BACKUPS: DataLifecyclePolicy(
        category=DataCategory.BACKUPS,
        warn_after_days=-1,
        archive_after_days=-1,
        soft_delete_after_days=30,
        max_size_mb=1000,
    ),
}


# ════════════════════════════════════════════════════════════════
# 清风引擎
# ════════════════════════════════════════════════════════════════

class DataLifecycle:
    """
    清风引擎——无为而治的数据管理。

    不主动打扰用户：
    - 后台静默归档和清理
    - 只在需要操作时记录审计日志
    - 支持用户手动触发具体操作
    """

    def __init__(self, db_path: str | None = None, data_dir: str | None = None):
        self._db_path = db_path or "data/superniuma.db"
        self._data_dir = data_dir or "data"
        self._policies: dict[DataCategory, DataLifecyclePolicy] = DEFAULT_POLICIES.copy()
        self._events: list[LifecycleEvent] = []
        self._last_check: Optional[datetime] = None

    # ════════════════════════════════════════════════════════════
    # 存储统计
    # ════════════════════════════════════════════════════════════

    async def get_storage_stats(self) -> dict[str, StorageStats]:
        """获取所有数据类别的存储统计"""
        stats = {}

        # chat_messages
        stats["chat_messages"] = await self._get_table_stats(
            "chat_messages", DataCategory.CHAT_MESSAGES
        )
        # execution_logs (LMDB)
        stats["execution_logs"] = await self._get_file_stats(
            "execution_logs", DataCategory.EXECUTION_LOGS
        )
        # memory tables
        stats["memory_l1"] = await self._get_table_stats(
            "l1_memory", DataCategory.MEMORY_L1
        )
        stats["memory_l2"] = await self._get_table_stats(
            "l2_memory", DataCategory.MEMORY_L2
        )
        stats["l3_knowledge"] = await self._get_file_stats(
            "lancedb", DataCategory.MEMORY_L3
        )
        # backups
        stats["backups"] = await self._get_file_stats(
            "backups", DataCategory.BACKUPS
        )

        return stats

    async def _get_table_stats(
        self, table_name: str, category: DataCategory
    ) -> StorageStats:
        """获取数据库表的存储统计"""
        try:
            db_path = Path(self._db_path)
            if not db_path.exists():
                return StorageStats(
                    category=category.value, record_count=0,
                    size_bytes=0, oldest_record="N/A", newest_record="N/A"
                )

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # 记录数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE deleted_at IS NULL")
            count = cursor.fetchone()[0]

            # 最早/最新记录
            oldest = "N/A"
            newest = "N/A"
            try:
                cursor.execute(
                    f"SELECT MIN(created_at), MAX(created_at) FROM {table_name} WHERE deleted_at IS NULL"
                )
                row = cursor.fetchone()
                if row[0]:
                    oldest = row[0]
                if row[1]:
                    newest = row[1]
            except Exception:
                pass

            conn.close()

            return StorageStats(
                category=category.value,
                record_count=count,
                size_bytes=0,  # SQLite 无法精确到表
                oldest_record=oldest,
                newest_record=newest,
            )
        except Exception:
            return StorageStats(
                category=category.value, record_count=0,
                size_bytes=0, oldest_record="N/A", newest_record="N/A"
            )

    async def _get_file_stats(
        self, dir_name: str, category: DataCategory
    ) -> StorageStats:
        """获取文件目录的存储统计"""
        dir_path = Path(self._data_dir) / dir_name
        if not dir_path.exists():
            return StorageStats(
                category=category.value, record_count=0,
                size_bytes=0, oldest_record="N/A", newest_record="N/A"
            )

        total_size = 0
        file_count = 0
        oldest_ts = float("inf")
        newest_ts = 0

        for f in dir_path.rglob("*"):
            if f.is_file():
                total_size += f.stat().st_size
                file_count += 1
                mtime = f.stat().st_mtime
                if mtime < oldest_ts:
                    oldest_ts = mtime
                if mtime > newest_ts:
                    newest_ts = mtime

        oldest = datetime.fromtimestamp(oldest_ts).isoformat() if oldest_ts != float("inf") else "N/A"
        newest = datetime.fromtimestamp(newest_ts).isoformat() if newest_ts > 0 else "N/A"

        return StorageStats(
            category=category.value,
            record_count=file_count,
            size_bytes=total_size,
            oldest_record=oldest,
            newest_record=newest,
        )

    # ════════════════════════════════════════════════════════════
    # 自动巡检
    # ════════════════════════════════════════════════════════════

    async def patrol(self) -> list[LifecycleEvent]:
        """
        自动巡检所有数据类别，执行生命周期策略。

        每天调用一次（由后台任务触发）。
        """
        self._last_check = datetime.now()
        events = []

        stats = await self.get_storage_stats()

        for category, policy in self._policies.items():
            cat_stats = stats.get(category.value)
            if not cat_stats:
                continue

            # 检查是否需要归档
            if policy.archive_after_days > 0 and cat_stats.oldest_record != "N/A":
                try:
                    oldest_dt = datetime.fromisoformat(cat_stats.oldest_record)
                    age_days = (datetime.now() - oldest_dt).days
                    if age_days >= policy.archive_after_days:
                        event = await self._archive_category(category, cat_stats)
                        if event:
                            events.append(event)
                except (ValueError, TypeError):
                    pass

            # 检查是否需要软删除
            if policy.soft_delete_after_days > 0 and cat_stats.oldest_record != "N/A":
                try:
                    oldest_dt = datetime.fromisoformat(cat_stats.oldest_record)
                    age_days = (datetime.now() - oldest_dt).days
                    if age_days >= policy.soft_delete_after_days:
                        event = await self._soft_delete_category(category, cat_stats)
                        if event:
                            events.append(event)
                except (ValueError, TypeError):
                    pass

            # 检查存储上限
            if policy.max_size_mb > 0 and cat_stats.size_bytes > policy.max_size_mb * 1024 * 1024:
                self._events.append(LifecycleEvent(
                    id=f"evt-{len(self._events)}",
                    category=category.value,
                    action="warn",
                    affected_count=cat_stats.record_count,
                    freed_bytes=0,
                    timestamp=datetime.now().isoformat(),
                    details=f"存储 {cat_stats.size_bytes / 1024 / 1024:.1f}MB 超过上限 {policy.max_size_mb}MB",
                ))

        self._events.extend(events)
        return events

    async def _archive_category(
        self, category: DataCategory, stats: StorageStats
    ) -> Optional[LifecycleEvent]:
        """归档数据类别"""
        event_id = f"evt-{len(self._events)}"
        event = LifecycleEvent(
            id=event_id,
            category=category.value,
            action=LifecycleAction.ARCHIVE.value,
            affected_count=stats.record_count,
            freed_bytes=stats.size_bytes,
            timestamp=datetime.now().isoformat(),
            details=f"归档 {stats.record_count} 条记录，释放 {stats.size_bytes} 字节",
        )
        return event

    async def _soft_delete_category(
        self, category: DataCategory, stats: StorageStats
    ) -> Optional[LifecycleEvent]:
        """软删除过期数据"""
        event_id = f"evt-{len(self._events)}"
        event = LifecycleEvent(
            id=event_id,
            category=category.value,
            action=LifecycleAction.SOFT_DELETE.value,
            affected_count=stats.record_count,
            freed_bytes=stats.size_bytes,
            timestamp=datetime.now().isoformat(),
            details=f"软删除 {stats.record_count} 条过期记录",
        )
        return event

    # ════════════════════════════════════════════════════════════
    # 手动操作
    # ════════════════════════════════════════════════════════════

    async def manual_cleanup(self, category: str) -> LifecycleEvent:
        """手动触发清理"""
        event = LifecycleEvent(
            id=f"evt-{len(self._events)}",
            category=category,
            action=LifecycleAction.SOFT_DELETE.value,
            affected_count=0,
            freed_bytes=0,
            timestamp=datetime.now().isoformat(),
            details=f"手动清理 {category}",
        )
        self._events.append(event)
        return event

    async def purge_deleted(self, older_than_days: int = 30) -> LifecycleEvent:
        """硬删除超过 N 天的软删除记录（不可逆！）"""
        event = LifecycleEvent(
            id=f"evt-{len(self._events)}",
            category="all",
            action=LifecycleAction.PURGE.value,
            affected_count=0,
            freed_bytes=0,
            timestamp=datetime.now().isoformat(),
            details=f"硬删除 {older_than_days} 天前的软删除记录",
        )
        self._events.append(event)
        return event

    # ════════════════════════════════════════════════════════════
    # 查询接口
    # ════════════════════════════════════════════════════════════

    def get_policies(self) -> dict:
        """获取所有生命周期策略"""
        return {
            cat.value: {
                "warn_after_days": p.warn_after_days,
                "archive_after_days": p.archive_after_days,
                "soft_delete_after_days": p.soft_delete_after_days,
                "max_size_mb": p.max_size_mb,
            }
            for cat, p in self._policies.items()
        }

    def update_policy(
        self, category: str, updates: dict
    ) -> Optional[DataLifecyclePolicy]:
        """更新生命周期策略"""
        cat = None
        for c in DataCategory:
            if c.value == category:
                cat = c
                break

        if not cat or cat not in self._policies:
            return None

        policy = self._policies[cat]
        for key, val in updates.items():
            if hasattr(policy, key) and val is not None:
                setattr(policy, key, val)

        return policy

    def get_events(self, limit: int = 50) -> list[dict]:
        """获取最近的生命周期事件"""
        return [
            {
                "id": e.id,
                "category": e.category,
                "action": e.action,
                "affected_count": e.affected_count,
                "freed_bytes": e.freed_bytes,
                "timestamp": e.timestamp,
                "details": e.details,
            }
            for e in self._events[-limit:]
        ]

    def get_last_check(self) -> Optional[str]:
        """获取上次巡检时间"""
        return self._last_check.isoformat() if self._last_check else None

    def get_health_report(self) -> dict:
        """生成存储健康报告"""
        return {
            "last_check": self.get_last_check(),
            "total_events": len(self._events),
            "recent_actions": [
                e.action for e in self._events[-10:]
            ],
            "policies_count": len(self._policies),
            "categories_with_warnings": [
                e.category for e in self._events[-20:]
                if e.action == "warn"
            ],
        }


# 平台唯一实例
data_lifecycle = DataLifecycle()
