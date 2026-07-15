"""
太极引擎 · CCR 可逆压缩存储层

CCR = Compressed Content Retrieval（压缩内容可逆检索）

原理：
1. 压缩前：将原始内容的 content_hash → original_text 存入 LRU 缓存
2. 压缩后：摘要中嵌入 content_hash，LLM 可通过 headroom_retrieve 工具取回原文
3. 零额外 LLM 调用，100% 可逆，不丢信息

集成点：SummarizeCompressor._replace_with_summary 调用前存入，LLM tool call 时取出
"""
from __future__ import annotations
import hashlib
import time
import logging
from collections import OrderedDict
from typing import Optional

logger = logging.getLogger(__name__)


class CCRStore:
    """压缩内容可逆存储。

    使用 OrderedDict 实现 LRU 淘汰策略，纯内存操作，零 I/O 开销。
    """

    # 默认最大缓存条目数（约占用 5-10MB 内存）
    DEFAULT_MAX_ENTRIES = 500

    def __init__(self, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        self._cache: OrderedDict[str, _CCREntry] = OrderedDict()
        self._max_entries = max_entries
        self._hits: int = 0
        self._misses: int = 0
        self._stores: int = 0
        self._evictions: int = 0

    # ---- 存储 ----

    def store(self, content: str, metadata: Optional[dict] = None) -> str:
        """存储原始内容，返回 content_hash 供嵌入摘要。

        Args:
            content: 被压缩的原始文本
            metadata: 可选元数据（来源消息 ID、时间戳等）

        Returns:
            SHA256 content_hash，供 LLM 通过 headroom_retrieve 取回
        """
        content_hash = self._hash_content(content)

        # 已存在则更新访问时间
        if content_hash in self._cache:
            self._cache.move_to_end(content_hash)
            entry = self._cache[content_hash]
            entry.last_access = time.time()
            if metadata:
                entry.metadata.update(metadata)
            return content_hash

        # LRU 淘汰
        if len(self._cache) >= self._max_entries:
            self._cache.popitem(last=False)
            self._evictions += 1

        self._cache[content_hash] = _CCREntry(
            content=content,
            metadata=metadata or {},
            stored_at=time.time(),
        )
        self._cache.move_to_end(content_hash)
        self._stores += 1

        return content_hash

    def store_batch(self, items: list[tuple[str, Optional[dict]]]) -> list[str]:
        """批量存储，返回 content_hash 列表。"""
        return [self.store(content, meta) for content, meta in items]

    # ---- 检索 ----

    def retrieve(self, content_hash: str) -> Optional[str]:
        """根据 content_hash 检索原始内容。

        LRU 语义：检索同时更新访问时间，防止热数据被淘汰。
        """
        entry = self._cache.get(content_hash)
        if entry is None:
            self._misses += 1
            return None

        self._cache.move_to_end(content_hash)
        entry.last_access = time.time()
        self._hits += 1
        return entry.content

    def retrieve_metadata(self, content_hash: str) -> Optional[dict]:
        """检索附带元数据。"""
        entry = self._cache.get(content_hash)
        if entry is None:
            return None
        self._cache.move_to_end(content_hash)
        return entry.metadata

    # ---- 查询 ----

    def has(self, content_hash: str) -> bool:
        """检查 content_hash 是否在缓存中。"""
        return content_hash in self._cache

    @property
    def stats(self) -> dict:
        """缓存统计信息。"""
        return {
            "size": len(self._cache),
            "max_entries": self._max_entries,
            "hits": self._hits,
            "misses": self._misses,
            "stores": self._stores,
            "evictions": self._evictions,
            "hit_rate": round(self._hits / max(1, self._hits + self._misses), 3),
        }

    @property
    def size(self) -> int:
        """当前缓存条目数。"""
        return len(self._cache)

    # ---- 管理 ----

    def clear(self) -> None:
        """清空缓存。"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        self._stores = 0
        self._evictions = 0

    def prune_expired(self, ttl_seconds: int = 3600) -> int:
        """淘汰超过 TTL 的条目。返回淘汰数。"""
        now = time.time()
        expired = [
            h for h, e in self._cache.items()
            if now - e.last_access > ttl_seconds
        ]
        for h in expired:
            del self._cache[h]
            self._evictions += 1
        return len(expired)

    # ---- 内部方法 ----

    @staticmethod
    def _hash_content(content: str) -> str:
        """生成内容哈希（SHA256 前 16 位，足够防冲突）。"""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def make_headroom_prompt(self, content_hash: str) -> str:
        """生成嵌入摘要的检索提示。

        格式：`[压缩: {hash}]` — LLM 通过 headroom_retrieve(hash) 取回原文。
        """
        return f"[压缩: {content_hash}]"


class _CCREntry:
    """缓存条目。"""
    __slots__ = ("content", "metadata", "stored_at", "last_access")

    def __init__(self, content: str, metadata: dict, stored_at: float) -> None:
        self.content = content
        self.metadata = metadata
        self.stored_at = stored_at
        self.last_access = stored_at


# 全局单例
ccr_store = CCRStore()
