"""
太极引擎 · 混合检索引擎（Hybrid Retrieval Engine）— v2.0 新增

参考：腾讯云Agent Memory — 70%向量+30%BM25+MMR去重+时间衰减。
太极第七律·生生不息——检索不是越多越好，精准才是。

核心机制：
  1. BM25 关键词检索 — 基于TF-IDF的词频匹配
  2. 向量语义检索 — 已有（保留兼容）
  3. MMR去重 — 最大边际相关性，避免冗余结果
  4. 时间衰减 — 较新的文档权重更高
  5. 混合加权 — 70%向量 + 30%BM25

设计原则（铁则）：
  - 轻量：纯Python BM25，无向量数据库依赖
  - 可插拔：替代现有纯向量检索，保持API兼容
  - 不烧Token：BM25本地计算，不调用模型

使用方式：
    from engine.hybrid_retrieval import hybrid_retrieval
    results = await hybrid_retrieval.search(
        query="修复登录页面bug",
        documents=[...],  # 已有的文档列表
        limit=5,
    )
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import math
import re
import time


# ============================================================
# BM25 实现（纯Python，零依赖）
# ============================================================

_WORD_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\w]+')

_STOP_WORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "the", "a", "an", "is", "are", "to", "of", "in", "for", "on", "with",
    "at", "by", "from", "as", "this", "that", "it", "and", "or", "but",
}


class BM25:
    """BM25 关键词检索 — Okapi BM25 算法的纯Python实现。

    用于混合检索的30%关键词权重部分。
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._documents: list[dict] = []
        self._doc_terms: list[dict[str, int]] = []   # doc_id → {term: freq}
        self._doc_lengths: list[int] = []
        self._avg_doc_length: float = 0.0
        self._idf: dict[str, float] = {}             # term → IDF
        self._corpus_size: int = 0

    def index(self, documents: list[dict], text_field: str = "content") -> None:
        """索引文档集合。

        Args:
            documents: [{id, content, timestamp, ...}, ...]
            text_field: 文本字段名
        """
        self._documents = documents
        self._doc_terms = []
        self._doc_lengths = []
        self._idf = {}
        self._corpus_size = len(documents)

        # 预处理每篇文档
        for doc in documents:
            text = doc.get(text_field, "")
            terms = [w.lower() for w in _WORD_RE.findall(text) if len(w) > 1 and w.lower() not in _STOP_WORDS]
            term_freqs: dict[str, int] = {}
            for t in terms:
                term_freqs[t] = term_freqs.get(t, 0) + 1
            self._doc_terms.append(term_freqs)
            self._doc_lengths.append(len(terms))

        # 计算平均文档长度
        self._avg_doc_length = (
            sum(self._doc_lengths) / self._corpus_size
            if self._corpus_size > 0 else 0
        )

        # 计算IDF
        for term_freqs in self._doc_terms:
            for term in term_freqs:
                self._idf[term] = self._idf.get(term, 0) + 1

        for term, df in self._idf.items():
            self._idf[term] = math.log(
                (self._corpus_size - df + 0.5) / (df + 0.5) + 1.0
            )

    def search(self, query: str, limit: int = 10) -> list[tuple[int, float]]:
        """搜索文档。

        Returns:
            [(doc_index, bm25_score), ...] 按分数降序
        """
        query_terms = [
            w.lower() for w in _WORD_RE.findall(query)
            if len(w) > 1 and w.lower() not in _STOP_WORDS
        ]

        if not query_terms:
            return []

        scores: list[float] = []
        for i in range(self._corpus_size):
            score = 0.0
            doc_len = self._doc_lengths[i]
            term_freqs = self._doc_terms[i]

            for term in query_terms:
                tf = term_freqs.get(term, 0)
                idf = self._idf.get(term, 0)
                if tf == 0 or idf == 0:
                    continue
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / max(self._avg_doc_length, 1))
                score += idf * numerator / denominator

            scores.append(score)

        # 排序
        ranked = [(i, scores[i]) for i in range(len(scores)) if scores[i] > 0]
        ranked.sort(key=lambda x: -x[1])
        return ranked[:limit]


# ============================================================
# MMR 去重
# ============================================================

def mmr_rerank(
    candidates: list[dict],
    selected: list[dict],
    lambda_param: float = 0.7,
    key_field: str = "content",
    limit: int = 5,
) -> list[dict]:
    """MMR (Maximum Marginal Relevance) 去重重排。

    平衡相关性与多样性——避免返回5条几乎相同的结果。

    Args:
        candidates: 候选文档列表 [{score, content, ...}]
        selected: 已选文档列表
        lambda_param: 相关性vs多样性权重（0.7=偏相关性，0.3=偏多样性）
        key_field: 文本字段名
        limit: 返回条数

    Returns:
        重排后的文档列表
    """
    if len(candidates) <= 1:
        return candidates

    result = list(selected)
    remaining = list(candidates)

    while remaining and len(result) < limit:
        mmr_scores = []

        for i, doc in enumerate(remaining):
            # 相关性分数
            relevance = doc.get("score", doc.get("relevance", 0.5))

            # 多样性惩罚（与已选文档的最大相似度）
            max_similarity = 0.0
            if result:
                doc_terms = _extract_terms(doc.get(key_field, ""))
                for selected_doc in result:
                    selected_terms = _extract_terms(selected_doc.get(key_field, ""))
                    similarity = _jaccard(doc_terms, selected_terms)
                    max_similarity = max(max_similarity, similarity)

            mmr = lambda_param * relevance - (1 - lambda_param) * max_similarity
            mmr_scores.append((i, mmr))

        # 选MMR最高的
        mmr_scores.sort(key=lambda x: -x[1])
        if mmr_scores and mmr_scores[0][1] > 0:
            best_idx = mmr_scores[0][0]
            result.append(remaining[best_idx])
            remaining.pop(best_idx)
        else:
            break

    return result[len(selected):]


def _extract_terms(text: str) -> set[str]:
    return {w.lower() for w in _WORD_RE.findall(text) if len(w) > 1}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ============================================================
# 混合检索引擎
# ============================================================

class HybridRetrieval:
    """混合检索引擎 — 70%向量 + 30%BM25 + MMR + 时间衰减。"""

    def __init__(self) -> None:
        self._bm25 = BM25()

    def index_documents(self, documents: list[dict], text_field: str = "content") -> None:
        """索引文档（BM25侧）。向量侧由现有模块负责。"""
        self._bm25.index(documents, text_field)

    def search(
        self,
        query: str,
        documents: list[dict],
        vector_scores: dict[str, float] | None = None,
        text_field: str = "content",
        id_field: str = "id",
        timestamp_field: str = "timestamp",
        limit: int = 5,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3,
        time_decay_rate: float = 0.005,
    ) -> list[dict]:
        """混合检索。

        Args:
            query: 查询文本
            documents: 文档列表 [{id, content, timestamp, ...}]
            vector_scores: 已有的向量检索分数 {doc_id: score}（可选）
            text_field: 文本字段名
            id_field: ID字段名
            timestamp_field: 时间戳字段名
            limit: 返回条数
            vector_weight: 向量检索权重（默认0.7）
            bm25_weight: BM25权重（默认0.3）
            time_decay_rate: 时间衰减率（每小时衰减0.5%）

        Returns:
            混合打分后的结果列表
        """
        # 索引文档
        self._bm25.index(documents, text_field)

        # BM25 检索
        bm25_results = self._bm25.search(query, limit=max(limit * 3, 10))
        bm25_scores: dict[int, float] = {idx: score for idx, score in bm25_results}

        # 混合打分
        now = time.time()
        scored: list[dict] = []

        for i, doc in enumerate(documents):
            doc_id = doc.get(id_field, str(i))

            # BM25 分数
            bm25_score = bm25_scores.get(i, 0.0)

            # 向量分数
            vector_score = 0.0
            if vector_scores:
                vector_score = vector_scores.get(doc_id, 0.0)

            # 混合加权
            if vector_scores:
                combined = vector_weight * vector_score + bm25_weight * bm25_score
            else:
                # 无向量分数时，纯BM25
                combined = bm25_score

            # 时间衰减
            ts = doc.get(timestamp_field, now)
            if isinstance(ts, str):
                try:
                    ts = float(ts)
                except (ValueError, TypeError):
                    ts = now
            age_hours = (now - ts) / 3600 if ts else 0
            time_decay = 1.0 if age_hours < 24 else max(0.3, 1.0 - (age_hours - 24) * time_decay_rate)

            final_score = combined * time_decay

            if final_score > 0.001:
                scored.append({
                    "document": doc,
                    "score": round(final_score, 4),
                    "bm25_score": round(bm25_score, 4),
                    "vector_score": round(vector_score, 4) if vector_scores else None,
                    "time_decay": round(time_decay, 3),
                })

        # 排序
        scored.sort(key=lambda x: -x["score"])

        # MMR去重
        result = mmr_rerank(
            [{"score": s["score"], "content": s["document"].get(text_field, ""),
              "document": s["document"]} for s in scored],
            selected=[],
            key_field="content",
            limit=limit,
        )

        return [r["document"] for r in result]


# ============================================================
# 全局实例
# ============================================================

hybrid_retrieval = HybridRetrieval()
