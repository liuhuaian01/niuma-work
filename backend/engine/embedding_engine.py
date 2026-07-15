"""
太极引擎 · 太虚境 — Embedding 引擎

零外部依赖的文本向量化引擎。使用本地 TF-IDF + 字符 n-gram 方案，
无需安装 sentence-transformers / OpenAI API，开箱即用。

特性：
  1. 字符级 bigram + trigram + 词级 TF-IDF 混合特征
  2. 余弦相似度检索
  3. 可配置维度 (默认 256)
  4. 增量索引（add / remove / rebuild）
  5. 内置中文分词简化支持（字粒度 + jieba 可选）

v1.0: TF-IDF 方案，零安装依赖。后续可替换为 ONNX 模型。
"""

from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional
import hashlib
import json
import logging
import math
import re
import time

logger = logging.getLogger("niuma.embedding")

# ============================================================
# 文本预处理
# ============================================================

# 中文字符范围
_ZH_CHAR = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]')
# 英文单词
_EN_WORD = re.compile(r'[a-zA-Z]+')
# 数字
_DIGIT = re.compile(r'\d+')


def _tokenize(text: str) -> list[str]:
    """简单中文+英文分词。

    中文：逐字 token（字符级）
    英文：小写词 token
    数字：占位符 [NUM]

    返回：token 列表。
    """
    if not text:
        return []

    tokens = []
    i = 0
    while i < len(text):
        ch = text[i]

        # 中文字符 → 单独 token
        if _ZH_CHAR.match(ch):
            tokens.append(ch)
            i += 1
            continue

        # 英文单词 → 整体小写 token
        en_match = _EN_WORD.match(text, i)
        if en_match:
            tokens.append(en_match.group().lower())
            i = en_match.end()
            continue

        # 数字 → [NUM]
        d_match = _DIGIT.match(text, i)
        if d_match:
            tokens.append('[NUM]')
            i = d_match.end()
            continue

        # 空白和其他 → 跳过
        i += 1

    return tokens


def _ngrams(tokens: list[str], n: int = 2) -> list[str]:
    """从 token 列表生成 n-gram 特征。"""
    if len(tokens) < n:
        return []
    return ['_'.join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


# ============================================================
# TF-IDF 向量化器
# ============================================================

@dataclass
class TFIDFIndex:
    """TF-IDF 索引——词汇表 + 文档频率。"""
    vocab: dict[str, int] = field(default_factory=dict)  # term → id
    df: Counter = field(default_factory=Counter)          # term → doc_freq
    n_docs: int = 0
    idf_cache: dict[str, float] = field(default_factory=dict)
    dirty: bool = False


class TFIDFVectorizer:
    """轻量级 TF-IDF 向量化器。

    特征：
    - 词级 unigram + bigram + trigram 混合
    - 维度可配置（hash trick 降维）
    - 增量更新（add_document / remove_document）
    """

    DEF_DIM = 256
    MIN_DF = 1          # 最少文档频率
    MAX_DF_RATIO = 0.9  # 最大文档频率比（过滤高频停用词）

    def __init__(self, dim: int = DEF_DIM) -> None:
        self._dim = dim
        self._index = TFIDFIndex()
        self._documents: dict[str, list[str]] = {}  # doc_id → tokens
        self._vectors: dict[str, list[float]] = {}  # doc_id → vector
        self._hash_seeds: list[int] = [i * 2654435761 % (2**31) for i in range(dim)]

    # ── 公共 API ────────────────────────────────────────────

    def add_document(self, doc_id: str, text: str) -> list[float]:
        """添加文档并返回 TF-IDF 向量。"""
        tokens = _tokenize(text)
        bigrams = _ngrams(tokens, 2)
        trigrams = _ngrams(tokens, 3)

        all_features = tokens + bigrams + trigrams

        # 更新 document-term 计数
        term_counts = Counter(all_features)

        # 更新全局词汇表 + 文档频率
        idx = self._index
        for term in term_counts:
            if term not in idx.vocab:
                idx.vocab[term] = len(idx.vocab)
            idx.df[term] += 1

        idx.n_docs += 1
        self._documents[doc_id] = all_features
        idx.dirty = True

        # 计算 TF-IDF 向量
        vec = self._compute_tfidf(term_counts)
        self._vectors[doc_id] = vec
        return vec

    def remove_document(self, doc_id: str) -> None:
        """移除文档。"""
        if doc_id not in self._documents:
            return

        all_features = self._documents.pop(doc_id)
        term_set = set(all_features)

        for term in term_set:
            if term in self._index.df:
                self._index.df[term] -= 1
                if self._index.df[term] <= 0:
                    del self._index.df[term]

        self._index.n_docs -= 1
        self._index.dirty = True
        self._vectors.pop(doc_id, None)

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """语义搜索：计算查询向量与所有文档的余弦相似度。

        Returns:
            [(doc_id, similarity_score)] 按相似度降序排列
        """
        query_tokens = _tokenize(query)
        query_bigrams = _ngrams(query_tokens, 2)
        query_trigrams = _ngrams(query_tokens, 3)
        all_features = query_tokens + query_bigrams + query_trigrams

        query_vec = self._compute_tfidf(Counter(all_features))

        # 计算余弦相似度
        results = []
        for doc_id, doc_vec in self._vectors.items():
            sim = _cosine_similarity(query_vec, doc_vec)
            if sim > 0.01:  # 过滤噪声
                results.append((doc_id, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def rebuild_idf(self) -> None:
        """重建 IDF 缓存（词汇表变更后调用）。"""
        idx = self._index
        idx.idf_cache.clear()
        for term, doc_freq in idx.df.items():
            if doc_freq < self.MIN_DF:
                continue
            if doc_freq / max(idx.n_docs, 1) > self.MAX_DF_RATIO:
                continue
            idx.idf_cache[term] = math.log(
                (idx.n_docs + 1) / (doc_freq + 1)
            ) + 1.0
        idx.dirty = False

    def _compute_tfidf(self, term_counts: Counter) -> list[float]:
        """计算 TF-IDF 向量（使用 hash trick 降维）。"""
        idx = self._index
        if idx.dirty:
            self.rebuild_idf()

        # 初始化向量
        vec = [0.0] * self._dim

        for term, count in term_counts.items():
            tf = 1.0 + math.log(max(count, 1))
            idf = idx.idf_cache.get(term, 0.0)
            weight = tf * idf

            if weight < 0.001:
                continue

            # Hash trick: 将 term 哈希到多个维度
            term_hash = int(hashlib.md5(term.encode()).hexdigest(), 16)
            for seed in self._hash_seeds:
                bucket = abs((term_hash ^ seed)) % self._dim
                vec[bucket] += weight * 0.01  # 小权重分散

        # L2 归一化
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        return vec

    def get_stats(self) -> dict:
        return {
            "dim": self._dim,
            "n_docs": self._index.n_docs,
            "vocab_size": len(self._index.vocab),
            "dirty": self._index.dirty,
        }


# ============================================================
# 相似度计算
# ============================================================

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """余弦相似度。"""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a < 1e-10 or norm_b < 1e-10:
        return 0.0
    return dot / (norm_a * norm_b)


# ============================================================
# Embedding 引擎主控
# ============================================================

class EmbeddingEngine:
    """太虚境 Embedding 引擎——文本向量化的统一入口。

    当前使用 TF-IDF 方案（零依赖），后续可切换为 ONNX 模型。
    """

    def __init__(self, dim: int = 256) -> None:
        self._vectorizer = TFIDFVectorizer(dim=dim)
        self._initialized = False

    @property
    def vectorizer(self) -> TFIDFVectorizer:
        return self._vectorizer

    @property
    def dim(self) -> int:
        return self._vectorizer._dim

    async def init(self) -> None:
        """初始化引擎——从数据库加载已有文档。"""
        if self._initialized:
            return
        # 后续从 DB 加载已有 embeddings
        self._initialized = True

    def embed(self, text: str, doc_id: Optional[str] = None) -> list[float]:
        """嵌入文本并可选地加入索引。

        Args:
            text: 需要向量化的文本
            doc_id: 文档 ID（如果提供，则加入索引）

        Returns:
            float 列表（默认为 256 维）
        """
        if doc_id:
            return self._vectorizer.add_document(doc_id, text)

        # 临时嵌入（不加入索引）：使用相同的 TF-IDF 公式
        tokens = _tokenize(text)
        bigrams = _ngrams(tokens, 2)
        trigrams = _ngrams(tokens, 3)
        all_features = tokens + bigrams + trigrams
        return self._vectorizer._compute_tfidf(Counter(all_features))

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """语义搜索。"""
        return self._vectorizer.search(query, top_k)

    def remove(self, doc_id: str) -> None:
        """移除文档。"""
        self._vectorizer.remove_document(doc_id)

    def get_stats(self) -> dict:
        return {
            "dim": self.dim,
            **self._vectorizer.get_stats(),
        }


# 全局单例
embedding_engine = EmbeddingEngine()
