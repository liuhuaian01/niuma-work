"""
太极引擎 · 太虚境核心（Taixu Core）

太虚者，无形无象，万化之根。记忆系统的最终归宿。

功能：
  1. L3 知识库 CRUD（结构化 + 向量双索引）
  2. 语义搜索（TF-IDF 向量 + FTS5 全文混合检索）
  3. L2→L3 自动升级（retrieval_count ≥ 10 触发）
  4. 知识图谱关系管理
  5. 知识版本追踪

与 Hermes CLOUD.md 的对应关系：
  Hermes CLOUD.md (云记忆) → 太虚境 (本地化，隐私优先)
  Hermes MEMORY.md (用户管理) → 铭心 (memory_loader.py)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import json
import logging
import math
import sqlite3
import uuid

from engine.embedding_engine import embedding_engine

logger = logging.getLogger("niuma.taixu")

# ============================================================
# 知识类型
# ============================================================

class KnowledgeSchema(str, Enum):
    """S01-S10 知识 Schema（家纺领域 10 个核心 Schema）。"""
    S01_MATERIAL = "S01_材质"
    S02_CRAFT = "S02_工艺"
    S03_STYLE = "S03_款式"
    S04_PATTERN = "S04_花型"
    S05_TEXTURE = "S05_质感"
    S06_STYLE_ANALYSIS = "S06_风格分析"
    S07_CONSUMER_TREND = "S07_消费趋势"
    S08_ECOMMERCE_TREND = "S08_电商趋势"
    S09_SOCIAL_TREND = "S09_社媒趋势"
    S10_GENERAL = "S10_通用"

    @classmethod
    def from_string(cls, s: str) -> KnowledgeSchema:
        for item in cls:
            if item.value == s or item.name == s:
                return item
        return cls.S10_GENERAL


class KnowledgeStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DRAFT = "draft"
    DEPRECATED = "deprecated"


# ============================================================
# 数据模型
# ============================================================

@dataclass
class KnowledgeEntry:
    """L3 知识条目。"""
    id: str
    schema_type: KnowledgeSchema
    title: str
    content: str
    summary: str = ""
    source: str = ""                    # 数据来源（官方PR稿/用户喂入/飞书知识库/...）
    source_url: str = ""
    tags: list[str] = field(default_factory=list)
    confidence: float = 1.0             # 置信度 0-1
    status: KnowledgeStatus = KnowledgeStatus.ACTIVE
    retrieval_count: int = 0
    version: int = 1
    embedding: Optional[list[float]] = None
    metadata_json: str = ""
    workspace_id: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "schema_type": self.schema_type.value,
            "title": self.title,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "summary": self.summary,
            "source": self.source,
            "tags": self.tags,
            "confidence": self.confidence,
            "status": self.status.value,
            "retrieval_count": self.retrieval_count,
            "version": self.version,
            "workspace_id": self.workspace_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class KnowledgeRelation:
    """知识图谱关系。"""
    id: str
    source_id: str
    target_id: str
    relation_type: str              # "related_to" / "derived_from" / "contradicts" / "supersedes"
    weight: float = 1.0
    notes: str = ""
    created_at: str = ""


@dataclass
class SearchResult:
    """搜索结果。"""
    entry: KnowledgeEntry
    score: float                    # 综合评分 0-1
    match_type: str                 # "semantic" / "keyword" / "hybrid"
    highlights: list[str] = field(default_factory=list)


@dataclass
class UpgradeCandidate:
    """L2→L3 升级候选。"""
    l2_entry_id: str
    content: str
    retrieval_count: int
    schema_type: KnowledgeSchema
    confidence: float
    reason: str


# ============================================================
# SQLite 太虚境存储
# ============================================================

CREATE_L3_TABLES = """
-- L3 知识条目主表
CREATE TABLE IF NOT EXISTS l3_knowledge (
    id TEXT PRIMARY KEY,
    schema_type TEXT NOT NULL DEFAULT 'S10_通用',
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT DEFAULT '',
    source TEXT DEFAULT '',
    source_url TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    confidence REAL DEFAULT 1.0,
    status TEXT DEFAULT 'active',
    retrieval_count INTEGER DEFAULT 0,
    version INTEGER DEFAULT 1,
    workspace_id TEXT DEFAULT '',
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- L3 向量索引表（独立表，便于增量更新）
CREATE TABLE IF NOT EXISTS l3_embeddings (
    knowledge_id TEXT PRIMARY KEY,
    embedding_json TEXT NOT NULL,
    dim INTEGER DEFAULT 256,
    model_version TEXT DEFAULT 'tfidf-v1',
    created_at TEXT NOT NULL,
    FOREIGN KEY (knowledge_id) REFERENCES l3_knowledge(id) ON DELETE CASCADE
);

-- FTS5 全文索引
CREATE VIRTUAL TABLE IF NOT EXISTS l3_fts USING fts5(
    title, content, summary, tags,
    content='l3_knowledge',
    content_rowid='rowid'
);

-- 知识图谱关系表
CREATE TABLE IF NOT EXISTS l3_relations (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation_type TEXT NOT NULL DEFAULT 'related_to',
    weight REAL DEFAULT 1.0,
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES l3_knowledge(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES l3_knowledge(id) ON DELETE CASCADE
);

-- L2→L3 升级队列
CREATE TABLE IF NOT EXISTS l2_upgrade_queue (
    id TEXT PRIMARY KEY,
    l2_entry_id TEXT NOT NULL,
    schema_type TEXT DEFAULT 'S10_通用',
    confidence REAL DEFAULT 0.5,
    reason TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL,
    processed_at TEXT
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_l3_schema ON l3_knowledge(schema_type);
CREATE INDEX IF NOT EXISTS idx_l3_status ON l3_knowledge(status);
CREATE INDEX IF NOT EXISTS idx_l3_workspace ON l3_knowledge(workspace_id);
CREATE INDEX IF NOT EXISTS idx_l3_source ON l3_knowledge(source);
CREATE INDEX IF NOT EXISTS idx_l3_relations_src ON l3_relations(source_id);
CREATE INDEX IF NOT EXISTS idx_l3_relations_tgt ON l3_relations(target_id);
CREATE INDEX IF NOT EXISTS idx_l3_upgrade_status ON l2_upgrade_queue(status);
"""

# FTS5 触发器：保持 l3_knowledge 与 l3_fts 同步
L3_FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS l3_fts_insert AFTER INSERT ON l3_knowledge BEGIN
    INSERT INTO l3_fts(rowid, title, content, summary, tags)
    VALUES (new.rowid, new.title, new.content, new.summary, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS l3_fts_delete AFTER DELETE ON l3_knowledge BEGIN
    INSERT INTO l3_fts(l3_fts, rowid, title, content, summary, tags)
    VALUES ('delete', old.rowid, old.title, old.content, old.summary, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS l3_fts_update AFTER UPDATE ON l3_knowledge BEGIN
    INSERT INTO l3_fts(l3_fts, rowid, title, content, summary, tags)
    VALUES ('delete', old.rowid, old.title, old.content, old.summary, old.tags);
    INSERT INTO l3_fts(rowid, title, content, summary, tags)
    VALUES (new.rowid, new.title, new.content, new.summary, new.tags);
END;
"""


# ============================================================
# SQLite 连接管理
# ============================================================

class TaixuDB:
    """太虚境 SQLite 连接管理器。"""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_tables(self) -> None:
        """初始化所有太虚境表。"""
        with self._connect() as conn:
            conn.executescript(CREATE_L3_TABLES)
            try:
                conn.executescript(L3_FTS_TRIGGERS)
            except sqlite3.OperationalError:
                pass  # FTS 触发器可能已存在
            conn.commit()
        logger.info("太虚境表初始化完成: %s", self._db_path)

    def execute(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall()

    def execute_write(self, sql: str, params: tuple = ()) -> int:
        with self._connect() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.lastrowid


# ============================================================
# 太虚境核心引擎
# ============================================================

class TaixuCore:
    """太虚境核心——L3 知识库的统一入口。

    架构：
      l3_knowledge (结构化) + l3_embeddings (向量) + l3_fts (全文)
      → 混合检索（语义 + 关键词融合排序）
    """

    # L2→L3 自动升级阈值
    UPGRADE_RETRIEVAL_THRESHOLD = 10
    UPGRADE_MIN_CONFIDENCE = 0.4

    def __init__(self, db_path: str) -> None:
        self._db = TaixuDB(db_path)
        self._initialized = False

    async def init(self) -> None:
        """初始化太虚境——建表 + 加载已有 embeddings 到向量引擎。"""
        if self._initialized:
            return

        self._db.init_tables()

        # 加载已有 embeddings 到向量引擎
        try:
            rows = self._db.execute(
                "SELECT knowledge_id, embedding_json FROM l3_embeddings"
            )
            for row in rows:
                vec = json.loads(row["embedding_json"])
                # 将已有向量注入 embedding_engine
                pass  # TF-IDF 引擎暂不支持直接注入，通过 rebuild 方式
        except Exception as e:
            logger.warning("太虚境加载已有 embeddings 失败: %s", e)

        # 初始化嵌入引擎
        await embedding_engine.init()
        self._initialized = True
        logger.info("太虚境核心初始化完成")

    # ════════════════════════════════════════════════════════════
    # L3 CRUD
    # ════════════════════════════════════════════════════════════

    async def add_knowledge(
        self,
        title: str,
        content: str,
        schema_type: str = "S10_通用",
        source: str = "",
        source_url: str = "",
        tags: list[str] | None = None,
        confidence: float = 1.0,
        workspace_id: str = "",
        summary: str = "",
    ) -> KnowledgeEntry:
        """添加知识条目——同时建立结构化索引 + 向量索引 + FTS 索引。"""
        now = datetime.now().isoformat()
        kid = f"l3_{uuid.uuid4().hex[:12]}"

        tags_json = json.dumps(tags or [], ensure_ascii=False)
        if not summary:
            summary = content[:120] + "..." if len(content) > 120 else content

        # 1) 写入结构化表
        self._db.execute_write(
            """INSERT INTO l3_knowledge
               (id, schema_type, title, content, summary, source, source_url,
                tags, confidence, status, workspace_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)""",
            (kid, schema_type, title, content, summary, source, source_url,
             tags_json, confidence, workspace_id, now, now),
        )

        # 2) 生成 embedding
        vec = embedding_engine.embed(content, doc_id=kid)
        vec_json = json.dumps(vec)

        # 3) 写入向量表
        self._db.execute_write(
            "INSERT INTO l3_embeddings (knowledge_id, embedding_json, dim, created_at) VALUES (?, ?, ?, ?)",
            (kid, vec_json, len(vec), now),
        )

        return KnowledgeEntry(
            id=kid, schema_type=KnowledgeSchema.from_string(schema_type),
            title=title, content=content, summary=summary,
            source=source, source_url=source_url,
            tags=tags or [], confidence=confidence,
            workspace_id=workspace_id, created_at=now, updated_at=now,
            embedding=vec,
        )

    async def update_knowledge(self, kid: str, **kwargs) -> Optional[KnowledgeEntry]:
        """更新知识条目。"""
        existing = await self.get_knowledge(kid)
        if not existing:
            return None

        now = datetime.now().isoformat()

        # 标题
        if "title" in kwargs:
            self._db.execute_write(
                "UPDATE l3_knowledge SET title=?, updated_at=? WHERE id=?",
                (kwargs["title"], now, kid),
            )
        # 内容
        if "content" in kwargs:
            self._db.execute_write(
                "UPDATE l3_knowledge SET content=?, summary=?, updated_at=? WHERE id=?",
                (kwargs["content"],
                 kwargs["content"][:120] + "..." if len(kwargs["content"]) > 120 else kwargs["content"],
                 now, kid),
            )
            # 更新 embedding
            vec = embedding_engine.embed(kwargs["content"], doc_id=kid)
            vec_json = json.dumps(vec)
            self._db.execute_write(
                "INSERT OR REPLACE INTO l3_embeddings (knowledge_id, embedding_json, dim, created_at) VALUES (?, ?, ?, ?)",
                (kid, vec_json, len(vec), now),
            )
        # 标签
        if "tags" in kwargs:
            tags_json = json.dumps(kwargs["tags"], ensure_ascii=False)
            self._db.execute_write(
                "UPDATE l3_knowledge SET tags=?, updated_at=? WHERE id=?",
                (tags_json, now, kid),
            )
        # 版本号 +1
        self._db.execute_write(
            "UPDATE l3_knowledge SET version=version+1, updated_at=? WHERE id=?",
            (now, kid),
        )

        return await self.get_knowledge(kid)

    async def get_knowledge(self, kid: str) -> Optional[KnowledgeEntry]:
        """获取单条知识。"""
        rows = self._db.execute(
            "SELECT * FROM l3_knowledge WHERE id=? AND status!='archived'", (kid,)
        )
        if not rows:
            return None
        return self._row_to_entry(rows[0])

    async def delete_knowledge(self, kid: str, soft: bool = True) -> bool:
        """删除知识条目（默认软删除）。"""
        if soft:
            self._db.execute_write(
                "UPDATE l3_knowledge SET status='archived', updated_at=? WHERE id=?",
                (datetime.now().isoformat(), kid),
            )
        else:
            self._db.execute_write("DELETE FROM l3_knowledge WHERE id=?", (kid,))
            embedding_engine.remove(kid)
        return True

    async def increment_retrieval(self, kid: str) -> int:
        """增加检索计数并检查升级条件。"""
        self._db.execute_write(
            "UPDATE l3_knowledge SET retrieval_count=retrieval_count+1 WHERE id=?", (kid,)
        )
        rows = self._db.execute(
            "SELECT retrieval_count FROM l3_knowledge WHERE id=?", (kid,)
        )
        return rows[0]["retrieval_count"] if rows else 0

    # ════════════════════════════════════════════════════════════
    # 语义搜索（混合：向量 + FTS5）
    # ════════════════════════════════════════════════════════════

    async def search(
        self,
        query: str,
        top_k: int = 10,
        schema_type: Optional[str] = None,
        workspace_id: Optional[str] = None,
        min_confidence: float = 0.0,
    ) -> list[SearchResult]:
        """混合搜索：向量相似度 + FTS5 全文检索融合排序。

        流程：
          1. 向量搜索（TF-IDF 余弦相似度）
          2. FTS5 全文搜索（BM25 评分）
          3. RRF (Reciprocal Rank Fusion) 融合排序
        """
        # 1) 向量搜索
        docs = embedding_engine.search(query, top_k=top_k * 2)
        semantic_scores = {doc_id: score for doc_id, score in docs}

        # 2) FTS5 全文搜索
        fts_scores = {}
        try:
            fts_rows = self._db.execute(
                "SELECT rowid, rank FROM l3_fts WHERE l3_fts MATCH ? ORDER BY rank LIMIT ?",
                (query, top_k * 2),
            )
            for row in fts_rows:
                # BM25 rank: 越小越好 → 转换为 0-1 分数
                rank = abs(row["rank"])
                fts_score = 1.0 / (1.0 + math.log(1 + rank))
                fts_scores[str(row["rowid"])] = fts_score
        except Exception as e:
            logger.debug("FTS5 搜索跳过: %s", e)

        # 3) RRF 融合
        all_ids = set(semantic_scores.keys()) | set(fts_scores.keys())
        fused: list[tuple[str, float]] = []

        k = 60  # RRF 参数

        for kid in all_ids:
            # 向量排名倒数
            sem_rank = 0
            if kid in semantic_scores:
                # 按分数排序，取倒数排名
                sorted_sem = sorted(semantic_scores.items(), key=lambda x: x[1], reverse=True)
                for rank_i, (sid, _) in enumerate(sorted_sem):
                    if sid == kid:
                        sem_rank = rank_i + 1
                        break
            sem_rrf = 1.0 / (k + sem_rank) if sem_rank > 0 else 0

            # FTS 排名倒数
            fts_rank = 0
            if kid in fts_scores:
                sorted_fts = sorted(fts_scores.items(), key=lambda x: x[1], reverse=True)
                for rank_i, (sid, _) in enumerate(sorted_fts):
                    if sid == kid:
                        fts_rank = rank_i + 1
                        break
            fts_rrf = 1.0 / (k + fts_rank) if fts_rank > 0 else 0

            # 融合分数
            fused_score = sem_rrf * 0.6 + fts_rrf * 0.4
            fused.append((kid, fused_score))

        fused.sort(key=lambda x: x[1], reverse=True)
        fused = fused[:top_k]

        # 4) 获取完整条目
        results = []
        for kid, score in fused[:top_k]:
            entry = await self.get_knowledge(kid)
            if entry is None:
                continue

            # 领域过滤
            if schema_type and entry.schema_type.value != schema_type:
                continue
            if workspace_id and entry.workspace_id != workspace_id:
                continue
            if entry.confidence < min_confidence:
                continue

            match_type = "hybrid"
            if kid in semantic_scores and kid in fts_scores:
                match_type = "hybrid"
            elif kid in semantic_scores:
                match_type = "semantic"
            else:
                match_type = "keyword"

            # 高亮片段
            highlights = self._extract_highlights(entry.content, query)

            results.append(SearchResult(
                entry=entry,
                score=round(score * 100) / 100,
                match_type=match_type,
                highlights=highlights,
            ))

        return results

    def _extract_highlights(self, content: str, query: str, window: int = 80) -> list[str]:
        """提取查询关键词附近的上下文片段。"""
        highlights = []
        query_chars = set(query)
        for i, ch in enumerate(content):
            if ch in query_chars:
                start = max(0, i - window // 2)
                end = min(len(content), i + window // 2)
                snippet = content[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(content):
                    snippet = snippet + "..."
                if snippet not in highlights:
                    highlights.append(snippet)
                if len(highlights) >= 3:
                    break
        return highlights

    # ════════════════════════════════════════════════════════════
    # L2 → L3 自动升级
    # ════════════════════════════════════════════════════════════

    async def check_upgrade_candidates(self, workspace_id: Optional[str] = None) -> list[UpgradeCandidate]:
        """扫描 L2 记忆条目，找出满足升级条件的候选项。

        条件：retrieval_count ≥ UPGRADE_RETRIEVAL_THRESHOLD 且条目未过期。
        """
        candidates = []

        try:
            rows = self._db.execute(
                """SELECT id, content, retrieval_count, observation_type, summary
                   FROM l2_memory_entries
                   WHERE retrieval_count >= ?
                     AND (expires_at > ? OR expires_at IS NULL)
                     AND (? IS NULL OR workspace_id = ?)
                   ORDER BY retrieval_count DESC
                   LIMIT 50""",
                (self.UPGRADE_RETRIEVAL_THRESHOLD,
                 datetime.now().isoformat(),
                 workspace_id, workspace_id),
            )
        except sqlite3.OperationalError:
            # l2_memory_entries 表可能在 SQLAlchemy 管理的 DB 中，不在太虚境 DB 中
            return []

        for row in rows:
            schema_type = self._infer_schema(row["content"], row.get("observation_type", ""))
            confidence = min(0.9, row["retrieval_count"] / 20.0)

            candidates.append(UpgradeCandidate(
                l2_entry_id=row["id"],
                content=row["content"],
                retrieval_count=row["retrieval_count"],
                schema_type=schema_type,
                confidence=confidence,
                reason=f"已检索 {row['retrieval_count']} 次，达到升级阈值",
            ))

        return candidates

    def _infer_schema(self, content: str, observation_type: str) -> KnowledgeSchema:
        """根据内容推断 Schema 类型（简单关键词匹配）。"""
        content_lower = content.lower()

        schemas_map = {
            KnowledgeSchema.S01_MATERIAL: ["材质", "面料", "棉", "丝", "麻", "纤维", "支数", "material", "fabric"],
            KnowledgeSchema.S02_CRAFT: ["工艺", "织造", "印染", "后整理", "craft", "weave"],
            KnowledgeSchema.S03_STYLE: ["款式", "版型", "裁剪", "style", "cut"],
            KnowledgeSchema.S04_PATTERN: ["花型", "图案", "印花", "pattern", "print"],
            KnowledgeSchema.S05_TEXTURE: ["质感", "手感", "触感", "texture", "feel"],
            KnowledgeSchema.S06_STYLE_ANALYSIS: ["风格", "调性", "美学", "aesthetic"],
            KnowledgeSchema.S07_CONSUMER_TREND: ["消费", "趋势", "用户", "consumer", "trend"],
            KnowledgeSchema.S08_ECOMMERCE_TREND: ["电商", "直播", "线上", "ecommerce"],
            KnowledgeSchema.S09_SOCIAL_TREND: ["社交", "小红书", "抖音", "social"],
        }

        for schema, keywords in schemas_map.items():
            for kw in keywords:
                if kw in content_lower:
                    return schema

        return KnowledgeSchema.S10_GENERAL

    async def execute_upgrade(self, candidates: list[UpgradeCandidate]) -> list[str]:
        """执行 L2→L3 升级——将候选条目写入 L3。

        Returns:
            已升级的 L3 知识 ID 列表
        """
        upgraded = []

        for cand in candidates:
            if cand.confidence < self.UPGRADE_MIN_CONFIDENCE:
                continue

            # 检查是否已存在相似条目（避免重复升级）
            existing = await self.search(cand.content, top_k=1)
            if existing and existing[0].score > 0.8:
                logger.info("跳过重复升级: %s → 相似条目已存在 (%s, score=%.2f)",
                           cand.l2_entry_id, existing[0].entry.id, existing[0].score)
                continue

            # 添加知识
            entry = await self.add_knowledge(
                title=f"L2升级: {cand.content[:60]}",
                content=cand.content,
                schema_type=cand.schema_type.value,
                source="l2_auto_upgrade",
                confidence=cand.confidence,
                summary=f"从 L2 记忆自动升级（检索 {cand.retrieval_count} 次）",
            )

            # 记录升级队列
            now = datetime.now().isoformat()
            self._db.execute_write(
                """INSERT OR REPLACE INTO l2_upgrade_queue
                   (id, l2_entry_id, schema_type, confidence, reason, status, created_at, processed_at)
                   VALUES (?, ?, ?, ?, ?, 'completed', ?, ?)""",
                (f"upg_{cand.l2_entry_id}", cand.l2_entry_id,
                 cand.schema_type.value, cand.confidence,
                 cand.reason, now, now),
            )

            upgraded.append(entry.id)
            logger.info("L2→L3 升级完成: %s → %s (schema=%s, confidence=%.2f)",
                       cand.l2_entry_id, entry.id, cand.schema_type.value, cand.confidence)

        return upgraded

    # ════════════════════════════════════════════════════════════
    # 知识图谱
    # ════════════════════════════════════════════════════════════

    async def add_relation(self, source_id: str, target_id: str,
                          relation_type: str = "related_to",
                          weight: float = 1.0,
                          notes: str = "") -> KnowledgeRelation:
        """添加知识图谱关系。"""
        now = datetime.now().isoformat()
        rid = f"rel_{uuid.uuid4().hex[:8]}"

        self._db.execute_write(
            """INSERT INTO l3_relations (id, source_id, target_id, relation_type, weight, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (rid, source_id, target_id, relation_type, weight, notes, now),
        )

        return KnowledgeRelation(
            id=rid, source_id=source_id, target_id=target_id,
            relation_type=relation_type, weight=weight, notes=notes, created_at=now,
        )

    async def get_related(self, kid: str, depth: int = 1) -> list[KnowledgeEntry]:
        """获取相关知识条目（图谱遍历）。"""
        related = []
        seen = {kid}

        current_ids = {kid}
        for _ in range(depth):
            next_ids = set()
            for cid in current_ids:
                # 正向关系
                rows = self._db.execute(
                    "SELECT target_id FROM l3_relations WHERE source_id=? AND weight > 0.3", (cid,)
                )
                for row in rows:
                    if row["target_id"] not in seen:
                        next_ids.add(row["target_id"])
                        seen.add(row["target_id"])
                # 反向关系
                rows = self._db.execute(
                    "SELECT source_id FROM l3_relations WHERE target_id=? AND weight > 0.3", (cid,)
                )
                for row in rows:
                    if row["source_id"] not in seen:
                        next_ids.add(row["source_id"])
                        seen.add(row["source_id"])

            for nid in next_ids:
                entry = await self.get_knowledge(nid)
                if entry:
                    related.append(entry)

            current_ids = next_ids

        return related

    # ════════════════════════════════════════════════════════════
    # 统计 & 管理
    # ════════════════════════════════════════════════════════════

    async def get_stats(self, workspace_id: Optional[str] = None) -> dict:
        """获取太虚境统计。"""
        where = "WHERE status='active'" + (f" AND workspace_id='{workspace_id}'" if workspace_id else "")

        rows = self._db.execute(f"SELECT COUNT(*) as cnt FROM l3_knowledge {where}")
        total = rows[0]["cnt"] if rows else 0

        rows = self._db.execute(
            "SELECT schema_type, COUNT(*) as cnt FROM l3_knowledge WHERE status='active' GROUP BY schema_type"
        )
        by_schema = {row["schema_type"]: row["cnt"] for row in rows}

        rows = self._db.execute("SELECT COUNT(*) as cnt FROM l3_relations")
        relations = rows[0]["cnt"] if rows else 0

        rows = self._db.execute(
            "SELECT COUNT(*) as cnt FROM l2_upgrade_queue WHERE status='pending'"
        )
        pending_upgrades = rows[0]["cnt"] if rows else 0

        vec_stats = embedding_engine.get_stats()

        return {
            "total_entries": total,
            "by_schema": by_schema,
            "total_relations": relations,
            "pending_upgrades": pending_upgrades,
            "vector_engine": vec_stats,
        }

    # ════════════════════════════════════════════════════════════
    # 辅助
    # ════════════════════════════════════════════════════════════

    def _row_to_entry(self, row: sqlite3.Row) -> KnowledgeEntry:
        """将 SQLite Row 转为 KnowledgeEntry。"""
        try:
            tags = json.loads(row["tags"])
        except (json.JSONDecodeError, TypeError):
            tags = []

        return KnowledgeEntry(
            id=row["id"],
            schema_type=KnowledgeSchema.from_string(row["schema_type"]),
            title=row["title"],
            content=row["content"],
            summary=row.get("summary", ""),
            source=row.get("source", ""),
            source_url=row.get("source_url", ""),
            tags=tags,
            confidence=row.get("confidence", 1.0),
            status=KnowledgeStatus(row.get("status", "active")),
            retrieval_count=row.get("retrieval_count", 0),
            version=row.get("version", 1),
            workspace_id=row.get("workspace_id", ""),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )

    async def shutdown(self) -> None:
        """关闭太虚境。"""
        self._initialized = False
        logger.info("太虚境核心已关闭")


# ============================================================
# 全局单例
# ============================================================

_taixu_instance: Optional[TaixuCore] = None


def get_taixu(db_path: Optional[str] = None) -> TaixuCore:
    """获取太虚境全局实例。"""
    global _taixu_instance
    if _taixu_instance is None:
        from config.settings import settings
        db_path = db_path or str(settings.TAIJI_DB_PATH)
        _taixu_instance = TaixuCore(db_path)
    return _taixu_instance


async def init_taixu() -> TaixuCore:
    """初始化太虚境（应用启动时调用一次）。"""
    taixu = get_taixu()
    await taixu.init()
    return taixu
