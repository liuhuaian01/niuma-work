"""
太极引擎 · 本地答案检测器

"天道法则"——外网访问前，先检查本地是否有答案。
避免明知故问、重复搜索、浪费 Token。
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class LocalAnswerResult:
    found: bool
    source: str = ""           # "l3_knowledge" / "l2_memory" / "recent_chat" / "none"
    match_score: float = 0.0    # 0.0-1.0 匹配度
    snippet: str = ""           # 匹配到的内容片段
    suggestion: str = ""        # 如果找到，给用户的建议


class LocalAnswerChecker:
    """本地答案检测——外网审批的前置判断。

    优先查 L3 知识库 → L2 档案 → 近期对话 → 如果都匹配不到，才建议开外网。
    """

    # 匹配阈值
    MIN_SCORE_L3 = 0.55          # L3 知识库匹配 — 中高阈值
    MIN_SCORE_L2 = 0.65          # L2 档案匹配 — 更高阈值（短期记忆）
    MIN_SCORE_CHAT = 0.80        # 近期对话匹配 — 最高阈值（上下文最相关）

    def check(
        self, query: str, l3_results: list[dict] | None = None,
        l2_results: list[dict] | None = None,
        recent_chat: list[dict] | None = None,
    ) -> LocalAnswerResult:
        """检查本地是否有答案。按 L3 → L2 → Chat 顺序。"""

        # 1. L3 知识库
        if l3_results:
            for entry in l3_results:
                score = self._keyword_match(query, entry.get("content", ""))
                if score >= self.MIN_SCORE_L3:
                    return LocalAnswerResult(
                        found=True, source="l3_knowledge", match_score=score,
                        snippet=entry.get("content", "")[:200],
                        suggestion="本地知识库已有相关信息",
                    )

        # 2. L2 档案
        if l2_results:
            for entry in l2_results:
                score = self._keyword_match(query, entry.get("content", "") if isinstance(entry, dict) else str(entry))
                if score >= self.MIN_SCORE_L2:
                    return LocalAnswerResult(
                        found=True, source="l2_memory", match_score=score,
                        snippet=str(entry)[:200],
                        suggestion="近期档案中已有相关信息",
                    )

        # 3. 近期对话
        if recent_chat:
            combined = " ".join(
                str(m.get("content", "")) for m in recent_chat
                if isinstance(m, dict) and m.get("role") != "system"
            )
            score = self._keyword_match(query, combined)
            if score >= self.MIN_SCORE_CHAT:
                return LocalAnswerResult(
                    found=True, source="recent_chat", match_score=score,
                    snippet=combined[:200],
                    suggestion="最近对话中已讨论过相关内容",
                )

        return LocalAnswerResult(found=False, source="none")

    def _keyword_match(self, query: str, content: str) -> float:
        """关键词覆盖度匹配。中文用字级重叠，英文用词级重叠。"""
        if not query or not content:
            return 0.0
        ql = query.lower()
        cl = content.lower()

        # 中文：提取连续中文字符段（任意长度）
        cn_query = set(c for c in re.findall(r'[\u4e00-\u9fff]', ql))
        cn_content = set(c for c in re.findall(r'[\u4e00-\u9fff]', cl))

        # 英文：词级匹配
        en_query = set(w for w in re.findall(r'[a-z]{3,}', ql))
        en_content = set(w for w in re.findall(r'[a-z]{3,}', cl))

        all_query = cn_query | en_query
        all_content = cn_content | en_content

        if not all_query:
            return 0.0

        matches = all_query & all_content
        score = len(matches) / len(all_query)

        # 查询词很短时降低阈值（短查询容易误匹配）
        if len(all_query) < 2:
            score *= 0.8

        return min(1.0, score)

    def should_skip_web_search(
        self, query: str, l3_results: list[dict] | None = None,
        l2_results: list[dict] | None = None,
        recent_chat: list[dict] | None = None,
    ) -> tuple[bool, str]:
        """判断是否应跳过外网搜索。返回 (应跳过, 原因)。"""
        result = self.check(query, l3_results, l2_results, recent_chat)
        if result.found:
            return True, f"{result.suggestion}（匹配度 {result.match_score:.0%}）"
        return False, ""
