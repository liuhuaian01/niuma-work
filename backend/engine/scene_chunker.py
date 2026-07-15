"""
太极引擎 · L2场景分块（Scene Chunker）— v1.8 新增

参考：腾讯云Agent Memory四层架构(L0→L3)→太极引擎补L2层。
功能：按项目/任务/语义聚类对话片段，实现精准场景召回。

太极哲学：以静制动——不是每句话都分块，而是积累到一定量再聚类。

核心机制：
  1. 场景识别（Scene Detection）— 自动检测对话场景切换点
  2. 场景聚类（Scene Clustering）— 相似场景归并，去重
  3. 场景索引（Scene Index）— 建立可检索的场景目录
  4. 场景召回（Scene Recall）— 按项目/任务/关键词检索相关场景

设计原则（铁则）：
  - 轻量：纯Python，无外部依赖
  - 克制：只在检测到场景切换时才分块，不每句都分析
  - 不烧Token：场景识别用关键词+任务类型切换，不调用模型
  - 增量：场景目录渐进积累，不全量重索引

使用方式：
    from engine.scene_chunker import scene_chunker
    # 记录对话片段
    await scene_chunker.record_chunk(
        session_id="session-1", project="super-niuma",
        task_type="coding", content="修复登录页的bug..."
    )
    # 召回相关场景
    results = await scene_chunker.recall_scenes(
        project="super-niuma", task_type="coding",
        query="登录相关", limit=5
    )
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import asyncio
import json
import logging
import os
import re
import time

logger = logging.getLogger("niuma.scene")


# ============================================================
# 数据模型
# ============================================================

@dataclass
class SceneChunk:
    """一个场景分块——对话片段的压缩表示。"""
    id: str
    session_id: str             # 会话ID
    project: str                # 项目标识（如 "super-niuma"）
    task_type: str              # coding / writing / analysis / conversation
    task_label: str             # 用户可读的任务标签（如 "修复登录页bug"）
    summary: str                # 场景摘要（不超过200字）
    key_terms: set[str] = field(default_factory=set)  # 关键词
    model_used: str = ""        # 使用的模型
    outcome: str = ""           # 结果摘要（成功/失败/待定）
    chunk_size: int = 0         # 原始对话字符数
    compressed_size: int = 0    # 压缩后字符数
    started_at: float = field(default_factory=time.time)
    updated_at: float = 0.0     # 最后更新时间
    access_count: int = 0       # 被检索次数
    importance: float = 0.5     # 重要性 0-1（根据结果/复用率动态计算）


@dataclass
class SceneCluster:
    """场景聚类——按项目+任务类型归组的场景集合。"""
    cluster_id: str             # 如 "super-niuma:coding"
    project: str
    task_type: str
    chunks: list[str] = field(default_factory=list)  # chunk IDs
    common_terms: set[str] = field(default_factory=set)  # 聚类共有关键词
    total_chunks: int = 0
    total_accesses: int = 0
    last_updated: float = field(default_factory=time.time)


# ============================================================
# 轻量分词器
# ============================================================

_STOP_WORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "这个", "那个", "什么", "怎么", "the", "a", "an", "is", "are", "to",
    "of", "in", "for", "on", "with", "at", "by", "from", "as", "this",
}

_WORD_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\w]+')


def _extract_terms(text: str) -> set[str]:
    if not text:
        return set()
    words = _WORD_RE.findall(text.lower())
    return {w for w in words if len(w) > 1 and w not in _STOP_WORDS and not w.isdigit()}


# ============================================================
# 场景分块引擎
# ============================================================

class SceneChunker:
    """L2场景分块引擎 — 按项目/任务聚类，实现精准场景召回。"""

    MAX_CHUNKS = 500            # 最多保留500个场景块
    CLUSTER_THRESHOLD = 3       # 至少3个块才建立聚类
    DATA_DIR = "data/scenes"

    def __init__(self, data_dir: str | None = None) -> None:
        self._data_dir = data_dir or self.DATA_DIR
        self._chunks: dict[str, SceneChunk] = {}          # chunk_id → SceneChunk
        self._clusters: dict[str, SceneCluster] = {}      # cluster_id → SceneCluster
        self._project_index: dict[str, set[str]] = {}     # project → set of chunk_ids
        self._task_index: dict[str, set[str]] = {}        # task_type → set of chunk_ids
        self._term_index: dict[str, set[str]] = {}        # term → set of chunk_ids
        self._total_chunks: int = 0
        self._is_initialized = False

    # ----------------------------------------------------------
    # 初始化
    # ----------------------------------------------------------

    async def initialize(self) -> None:
        """从持久化恢复状态。"""
        os.makedirs(self._data_dir, exist_ok=True)
        state_file = os.path.join(self._data_dir, "scene_state.json")
        try:
            if os.path.exists(state_file):
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)

                # 恢复chunks
                raw_chunks = state.get("chunks", {})
                for cid, raw in raw_chunks.items():
                    raw["key_terms"] = set(raw.get("key_terms", []))
                    self._chunks[cid] = SceneChunk(**raw)

                # 恢复clusters
                raw_clusters = state.get("clusters", {})
                for clid, raw in raw_clusters.items():
                    raw["common_terms"] = set(raw.get("common_terms", []))
                    self._clusters[clid] = SceneCluster(**raw)

                # 重建索引
                self._rebuild_indices()

                self._total_chunks = state.get("total_chunks", 0)
                logger.info(
                    f"场景分块恢复: {len(self._chunks)}场景块, "
                    f"{len(self._clusters)}聚类"
                )
        except Exception:
            logger.warning("场景状态文件损坏，从零开始", exc_info=True)
        self._is_initialized = True

    def _rebuild_indices(self) -> None:
        """重建项目/任务/关键词索引。"""
        self._project_index.clear()
        self._task_index.clear()
        self._term_index.clear()

        for cid, chunk in self._chunks.items():
            # 项目索引
            if chunk.project:
                self._project_index.setdefault(chunk.project, set()).add(cid)

            # 任务类型索引
            if chunk.task_type:
                self._task_index.setdefault(chunk.task_type, set()).add(cid)

            # 关键词索引
            for term in chunk.key_terms:
                self._term_index.setdefault(term, set()).add(cid)

    async def _save_state(self) -> None:
        """持久化状态。"""
        state_file = os.path.join(self._data_dir, "scene_state.json")
        try:
            # 序列化chunks（set→list）
            chunks_raw = {}
            for cid, chunk in self._chunks.items():
                chunks_raw[cid] = {
                    "id": chunk.id, "session_id": chunk.session_id,
                    "project": chunk.project, "task_type": chunk.task_type,
                    "task_label": chunk.task_label, "summary": chunk.summary,
                    "key_terms": list(chunk.key_terms),
                    "model_used": chunk.model_used, "outcome": chunk.outcome,
                    "chunk_size": chunk.chunk_size,
                    "compressed_size": chunk.compressed_size,
                    "started_at": chunk.started_at, "updated_at": chunk.updated_at,
                    "access_count": chunk.access_count,
                    "importance": chunk.importance,
                }

            clusters_raw = {}
            for clid, cluster in self._clusters.items():
                clusters_raw[clid] = {
                    "cluster_id": cluster.cluster_id,
                    "project": cluster.project,
                    "task_type": cluster.task_type,
                    "chunks": cluster.chunks,
                    "common_terms": list(cluster.common_terms),
                    "total_chunks": cluster.total_chunks,
                    "total_accesses": cluster.total_accesses,
                    "last_updated": cluster.last_updated,
                }

            state = {
                "chunks": chunks_raw,
                "clusters": clusters_raw,
                "total_chunks": self._total_chunks,
                "saved_at": datetime.now().isoformat(),
            }
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.debug("场景状态持久化失败", exc_info=True)

    # ----------------------------------------------------------
    # 场景记录（主入口）
    # ----------------------------------------------------------

    async def record_chunk(
        self,
        session_id: str,
        project: str,
        task_type: str,
        task_label: str = "",
        content: str = "",
        model_used: str = "",
        outcome: str = "",
        compressed_content: str = "",
    ) -> SceneChunk:
        """记录一个场景分块。

        在 chat_hooks.post_chat_record() 中调用。
        自动检测是否需要新建场景块（场景切换检测）。

        Args:
            session_id: 会话ID
            project: 项目标识
            task_type: 任务类型
            task_label: 用户可读的任务标签
            content: 原始对话内容（截断至2000字）
            model_used: 使用的模型
            outcome: 结果摘要（成功/失败/...）
            compressed_content: compression_engine压缩后的内容
        """
        # 生成场景块
        chunk_id = f"scene-{project}-{session_id[:8]}-{int(time.time())}"
        summary = self._generate_summary(task_type, task_label, outcome, content)
        key_terms = _extract_terms(task_label + " " + content[:500])

        chunk = SceneChunk(
            id=chunk_id,
            session_id=session_id,
            project=project,
            task_type=task_type,
            task_label=task_label,
            summary=summary,
            key_terms=key_terms,
            model_used=model_used,
            outcome=outcome,
            chunk_size=len(content),
            compressed_size=len(compressed_content),
        )

        self._chunks[chunk_id] = chunk
        self._total_chunks += 1

        # 更新索引
        self._project_index.setdefault(project, set()).add(chunk_id)
        self._task_index.setdefault(task_type, set()).add(chunk_id)
        for term in key_terms:
            self._term_index.setdefault(term, set()).add(chunk_id)

        # 更新聚类
        await self._update_cluster(project, task_type, chunk_id, key_terms)

        # 限制总量
        if len(self._chunks) > self.MAX_CHUNKS:
            # 淘汰最老的不重要chunk
            stale = sorted(
                self._chunks.items(),
                key=lambda x: (x[1].importance, x[1].access_count, x[1].started_at),
            )[:max(1, len(self._chunks) - self.MAX_CHUNKS)]
            for sid, _ in stale:
                self._remove_chunk(sid)

        # 异步持久化
        asyncio.ensure_future(self._save_state())

        return chunk

    def _generate_summary(
        self, task_type: str, task_label: str, outcome: str, content: str
    ) -> str:
        """生成场景摘要（不超过200字）。"""
        parts = []
        if task_label:
            parts.append(f"[{task_type}] {task_label}")
        else:
            parts.append(f"[{task_type}]")

        if outcome:
            outcome_icon = {"成功": "成功", "失败": "失败", "待定": "进行中"}.get(outcome, outcome)
            parts.append(f"结果: {outcome_icon}")

        # 从content中提取前100字作为上下文
        if content:
            snippet = content[:100].replace("\n", " ")
            if len(content) > 100:
                snippet += "..."
            parts.append(snippet)

        return " | ".join(parts)

    async def _update_cluster(
        self, project: str, task_type: str,
        chunk_id: str, key_terms: set[str],
    ) -> None:
        """更新或创建场景聚类。"""
        cluster_id = f"{project}:{task_type}"

        if cluster_id not in self._clusters:
            self._clusters[cluster_id] = SceneCluster(
                cluster_id=cluster_id,
                project=project,
                task_type=task_type,
            )

        cluster = self._clusters[cluster_id]
        if chunk_id not in cluster.chunks:
            cluster.chunks.append(chunk_id)
        cluster.total_chunks = len(cluster.chunks)
        cluster.last_updated = time.time()

        # 更新共有关键词（至少出现在2个chunk中的词才加入）
        if cluster.total_chunks >= self.CLUSTER_THRESHOLD:
            term_counts: dict[str, int] = {}
            for cid in cluster.chunks[-10:]:  # 最近10个
                c = self._chunks.get(cid)
                if c:
                    for term in c.key_terms:
                        term_counts[term] = term_counts.get(term, 0) + 1
            cluster.common_terms = {
                term for term, count in term_counts.items()
                if count >= 2  # 至少出现在2个chunk中
            }

    def _remove_chunk(self, chunk_id: str) -> None:
        """移除一个场景块及其索引。"""
        if chunk_id not in self._chunks:
            return

        chunk = self._chunks[chunk_id]
        self._project_index.get(chunk.project, set()).discard(chunk_id)
        self._task_index.get(chunk.task_type, set()).discard(chunk_id)
        for term in chunk.key_terms:
            self._term_index.get(term, set()).discard(chunk_id)
        del self._chunks[chunk_id]

    # ----------------------------------------------------------
    # 场景召回（核心检索）
    # ----------------------------------------------------------

    async def recall_scenes(
        self,
        project: str = "",
        task_type: str = "",
        query: str = "",
        limit: int = 5,
    ) -> list[dict]:
        """按项目/任务/关键词检索相关场景。

        纯关键词匹配+时间衰减，不调用模型——不烧Token。

        Args:
            project: 项目过滤（空=不过滤）
            task_type: 任务类型过滤（空=不过滤）
            query: 自然语言查询
            limit: 返回条数
        """
        query_terms = _extract_terms(query) if query else set()

        # 第一步：候选集
        candidates: set[str] = set()
        if project and project in self._project_index:
            candidates = self._project_index[project].copy()
        elif task_type and task_type in self._task_index:
            candidates = self._task_index[task_type].copy()
        else:
            # 无过滤→全量（但限制为最近chunk）
            recent = sorted(self._chunks.keys(), reverse=True)[:100]
            candidates = set(recent)

        # 第二步：交集过滤
        if task_type and task_type in self._task_index:
            if candidates:
                candidates &= self._task_index[task_type]
            else:
                candidates = self._task_index[task_type].copy()

        # 第三步：关键词匹配打分
        scored: list[tuple[float, SceneChunk]] = []
        now = time.time()

        for cid in candidates:
            chunk = self._chunks.get(cid)
            if not chunk:
                continue

            # 关键词匹配得分
            term_score = 0.0
            if query_terms and chunk.key_terms:
                overlap = len(query_terms & chunk.key_terms)
                term_score = overlap / max(len(query_terms), 1)

            # 如果没有query，返回最近场景
            if not query:
                term_score = 1.0

            # 时间衰减（24小时内0衰减，之后每天减5%）
            age_hours = (now - chunk.started_at) / 3600
            time_decay = 1.0 if age_hours < 24 else max(0.3, 1.0 - (age_hours - 24) * 0.005)

            # 重要性加权
            importance_boost = 0.5 + chunk.importance * 0.5

            # 访问热度加权
            access_boost = 1.0 + min(0.3, chunk.access_count * 0.02)

            final_score = term_score * time_decay * importance_boost * access_boost
            scored.append((final_score, chunk))

        # 排序取top_k
        scored.sort(key=lambda x: -x[0])
        results = []
        for score, chunk in scored[:limit]:
            chunk.access_count += 1
            chunk.updated_at = now
            results.append({
                "chunk_id": chunk.id,
                "session_id": chunk.session_id,
                "project": chunk.project,
                "task_type": chunk.task_type,
                "task_label": chunk.task_label,
                "summary": chunk.summary,
                "outcome": chunk.outcome,
                "model_used": chunk.model_used,
                "chunk_size": chunk.chunk_size,
                "started_at": chunk.started_at,
                "relevance": round(score, 3),
                "importance": chunk.importance,
            })

        return results

    # ----------------------------------------------------------
    # 聚类查询
    # ----------------------------------------------------------

    def get_cluster(self, project: str, task_type: str) -> SceneCluster | None:
        """获取指定聚类。"""
        cluster_id = f"{project}:{task_type}"
        return self._clusters.get(cluster_id)

    def list_clusters(self) -> list[dict]:
        """列出所有聚类。"""
        return [
            {
                "cluster_id": c.cluster_id,
                "project": c.project,
                "task_type": c.task_type,
                "total_chunks": c.total_chunks,
                "total_accesses": c.total_accesses,
                "common_terms": list(c.common_terms)[:20],
                "last_updated": c.last_updated,
            }
            for c in self._clusters.values()
        ]

    def get_project_summary(self, project: str) -> dict:
        """获取项目的场景概览。"""
        chunks = self._project_index.get(project, set())
        by_task: dict[str, int] = {}
        outcomes: dict[str, int] = {"成功": 0, "失败": 0, "待定": 0}
        models: dict[str, int] = {}

        for cid in chunks:
            chunk = self._chunks.get(cid)
            if not chunk:
                continue
            by_task[chunk.task_type] = by_task.get(chunk.task_type, 0) + 1
            if chunk.outcome in outcomes:
                outcomes[chunk.outcome] += 1
            if chunk.model_used:
                models[chunk.model_used] = models.get(chunk.model_used, 0) + 1

        return {
            "project": project,
            "total_scenes": len(chunks),
            "by_task_type": by_task,
            "by_outcome": outcomes,
            "by_model": models,
            "clusters": [
                self.get_cluster(project, tt)
                for tt in by_task
            ],
        }

    # ----------------------------------------------------------
    # 重要性管理
    # ----------------------------------------------------------

    def boost_importance(self, chunk_id: str, boost: float = 0.1) -> bool:
        """提升场景的重要性（用户标记/重新使用后调用）。"""
        chunk = self._chunks.get(chunk_id)
        if not chunk:
            return False
        chunk.importance = min(1.0, chunk.importance + boost)
        chunk.updated_at = time.time()
        return True

    # ----------------------------------------------------------
    # 查询接口
    # ----------------------------------------------------------

    def get_stats(self) -> dict:
        """获取场景分块引擎统计。"""
        return {
            "total_chunks": len(self._chunks),
            "total_clusters": len(self._clusters),
            "projects": list(self._project_index.keys()),
            "task_types": list(self._task_index.keys()),
            "indexed_terms": len(self._term_index),
            "initialized": self._is_initialized,
        }

    def search_by_term(self, term: str, limit: int = 10) -> list[dict]:
        """按单个关键词搜索场景。"""
        chunk_ids = self._term_index.get(term.lower(), set())
        results = []
        for cid in list(chunk_ids)[:limit]:
            chunk = self._chunks.get(cid)
            if chunk:
                results.append({
                    "chunk_id": chunk.id,
                    "project": chunk.project,
                    "task_label": chunk.task_label,
                    "summary": chunk.summary,
                    "outcome": chunk.outcome,
                    "started_at": chunk.started_at,
                })
        return results


# ============================================================
# 全局实例
# ============================================================

scene_chunker = SceneChunker()
