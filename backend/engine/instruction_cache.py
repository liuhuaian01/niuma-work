"""
太极引擎 · 指令缓存层

SQLite 存储用户高频固定指令，SHA256 哈希去重，TTL 30 天自动过期。

集成点：api_send_message 阶段，用户输入 → 哈希 → 查缓存 → 命中则直接返回。
减少重复 LLM 调用，对标 WorkBuddy 的指令全局缓存机制。

流水线位置：
  api_send_message (InstructionCache) → _build_context → LLM 调用
"""
from __future__ import annotations

import hashlib
import sqlite3
import time
import logging
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)


class InstructionCache:
    """用户指令去重缓存。

    特点：
    - SQLite 单文件存储，零配置
    - SHA256 哈希去重，安全高效
    - TTL 30 天自动过期
    - 线程安全读写
    - 采用 LRU 淘汰 + 定期清理双策略
    """

    DB_NAME = "instruction_cache.db"
    TTL_SECONDS = 30 * 24 * 3600  # 30 天
    MAX_ENTRIES = 1000
    CLEANUP_INTERVAL = 100  # 每 100 次写入触发一次清理

    def __init__(self, db_dir: Optional[Path] = None) -> None:
        self._db_path = (db_dir or Path(__file__).parent.parent / "data") / self.DB_NAME
        self._lock = Lock()
        self._write_count = 0
        self._init_db()

    # ---- SQLite 初始化 ----

    def _init_db(self) -> None:
        """建表 + 索引。"""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS instruction_cache (
                    content_hash TEXT PRIMARY KEY,
                    instruction TEXT NOT NULL,
                    cached_response TEXT NOT NULL,
                    workspace_id TEXT DEFAULT '',
                    created_at REAL NOT NULL,
                    last_hit_at REAL NOT NULL,
                    hit_count INTEGER DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ic_workspace
                ON instruction_cache(workspace_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ic_last_hit
                ON instruction_cache(last_hit_at DESC)
            """)
            conn.commit()

    @contextmanager
    def _get_conn(self):
        """获取数据库连接（线程安全）。"""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # ---- 核心操作 ----

    def lookup(self, instruction: str, workspace_id: str = "") -> Optional[str]:
        """查找缓存的响应。

        Args:
            instruction: 用户输入的完整指令
            workspace_id: 工作间 ID（用于隔离不同工作间的缓存）

        Returns:
            缓存的响应文本，未命中返回 None
        """
        content_hash = self._hash(instruction)

        with self._lock, self._get_conn() as conn:
            row = conn.execute(
                """SELECT cached_response, last_hit_at, hit_count
                   FROM instruction_cache
                   WHERE content_hash = ? AND workspace_id = ?
                   AND (strftime('%s', 'now') - last_hit_at) < ?""",
                (content_hash, workspace_id, self.TTL_SECONDS),
            ).fetchone()

            if row is None:
                return None

            # 更新命中统计
            now = time.time()
            conn.execute(
                """UPDATE instruction_cache
                   SET last_hit_at = ?, hit_count = hit_count + 1
                   WHERE content_hash = ?""",
                (now, content_hash),
            )
            conn.commit()

            logger.debug(f"Cache hit: {content_hash[:8]}... (×{row['hit_count'] + 1})")
            return row["cached_response"]

    def store(self, instruction: str, response: str, workspace_id: str = "") -> None:
        """缓存指令-响应对。

        Args:
            instruction: 用户输入
            response: LLM 返回的响应
            workspace_id: 工作间 ID
        """
        content_hash = self._hash(instruction)
        now = time.time()

        with self._lock, self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO instruction_cache
                   (content_hash, instruction, cached_response, workspace_id,
                    created_at, last_hit_at, hit_count)
                   VALUES (?, ?, ?, ?, ?, ?, 1)""",
                (content_hash, instruction, response, workspace_id, now, now),
            )
            conn.commit()

        self._write_count += 1

        # 定期清理
        if self._write_count % self.CLEANUP_INTERVAL == 0:
            self._cleanup()

    def lookup_or_none(self, instruction: str, workspace_id: str = "") -> Optional[str]:
        """同 lookup，但返回 Optional 类型提示更清晰。"""
        return self.lookup(instruction, workspace_id)

    # ---- 管理 ----

    def _cleanup(self) -> None:
        """清理过期条目 + LRU 淘汰超量条目。"""
        with self._lock, self._get_conn() as conn:
            # 清理过期
            expired = conn.execute(
                """DELETE FROM instruction_cache
                   WHERE (strftime('%s', 'now') - last_hit_at) >= ?""",
                (self.TTL_SECONDS,),
            ).rowcount

            # 如果仍超量，淘汰最久未命中的
            count = conn.execute("SELECT COUNT(*) FROM instruction_cache").fetchone()[0]
            if count > self.MAX_ENTRIES:
                excess = count - self.MAX_ENTRIES
                conn.execute(
                    """DELETE FROM instruction_cache
                       WHERE content_hash IN (
                           SELECT content_hash FROM instruction_cache
                           ORDER BY last_hit_at ASC LIMIT ?
                       )""",
                    (excess,),
                )

            conn.commit()

        if expired > 0:
            logger.info(f"InstructionCache cleanup: {expired} expired, size={self.size}")

    def clear(self) -> None:
        """清空全部缓存。"""
        with self._lock, self._get_conn() as conn:
            conn.execute("DELETE FROM instruction_cache")
            conn.commit()
        self._write_count = 0

    @property
    def size(self) -> int:
        """当前缓存条目数。"""
        with self._lock, self._get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM instruction_cache").fetchone()[0]

    @property
    def stats(self) -> dict:
        """缓存统计信息。"""
        with self._lock, self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM instruction_cache").fetchone()[0]
            total_hits = conn.execute(
                "SELECT COALESCE(SUM(hit_count), 0) FROM instruction_cache"
            ).fetchone()[0]
            avg_hits = conn.execute(
                "SELECT COALESCE(AVG(hit_count), 0) FROM instruction_cache"
            ).fetchone()[0]
            return {
                "size": total,
                "total_hits": total_hits,
                "avg_hits_per_entry": round(avg_hits, 1),
                "max_entries": self.MAX_ENTRIES,
                "ttl_days": 30,
            }

    # ---- 内部方法 ----

    @staticmethod
    def _hash(content: str) -> str:
        """SHA256 哈希（前 32 位）。"""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]


# 全局单例
instruction_cache = InstructionCache()
