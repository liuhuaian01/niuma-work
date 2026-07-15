"""
太极引擎 · 语义评分层

6 级语义价值评分（CRITICAL → FILLER），4 维度规则引擎。

评分维度：
1. factual_density — 信息密度（名词/数字/实体密度）
2. action_content — 行动含量（动词/指令/任务密度）
3. contextual_relevance — 上下文相关性（与当前任务关联度）
4. information_novelty — 信息新颖度（是否引入新信息 vs 重复已知）

集成点：_build_context 阶段，对消息进行语义评分，配合 Token 预算做剪枝决策。
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

logger = logging.getLogger(__name__)


class SemanticScore(IntEnum):
    """语义价值等级（6 级，越高越重要）"""
    FILLER = 1       # 填充词、寒暄、无信息量
    LOW = 2          # 低价值：简单确认、重复已知
    MEDIUM = 3       # 中等：常规情报、一般性讨论
    MEDIUM_HIGH = 4  # 中高：含具体信息、可操作建议
    HIGH = 5         # 高价值：核心分析、关键决策依据
    CRITICAL = 6     # 关键：用户指令、硬性约束、安全相关


# 分数 → 中文标签
SCORE_LABELS = {
    SemanticScore.CRITICAL: "关键",
    SemanticScore.HIGH: "高价值",
    SemanticScore.MEDIUM_HIGH: "中高",
    SemanticScore.MEDIUM: "中等",
    SemanticScore.LOW: "低价值",
    SemanticScore.FILLER: "填充",
}


@dataclass
class DimensionScores:
    """四维得分"""
    factual_density: float = 0.0      # 0.0-1.0
    action_content: float = 0.0       # 0.0-1.0
    contextual_relevance: float = 0.0  # 0.0-1.0
    information_novelty: float = 0.0   # 0.0-1.0

    @property
    def composite(self) -> float:
        """加权综合分 = 0.35*factual + 0.30*action + 0.20*context + 0.15*novelty"""
        return (
            0.35 * self.factual_density
            + 0.30 * self.action_content
            + 0.20 * self.contextual_relevance
            + 0.15 * self.information_novelty
        )


@dataclass
class GradeResult:
    """评分结果"""
    score: SemanticScore
    label: str
    dimensions: DimensionScores
    reason: str = ""
    confidence: float = 0.5

    @property
    def should_preserve(self) -> bool:
        """是否应保留（>= MEDIUM 保留，LOW/FILLER 可剪枝）"""
        return self.score >= SemanticScore.MEDIUM

    @property
    def is_filler(self) -> bool:
        """是否为可安全丢弃的填充内容"""
        return self.score <= SemanticScore.LOW


class SemanticGrader:
    """语义评分引擎。

    纯规则引擎，零 LLM 调用，单次评分 < 5ms。
    基于正则 + 启发式规则 + 上下文感知的组合策略。
    """

    # 信息密度关键词（权重 0.8-1.0）
    _HIGH_DENSITY_PATTERNS = [
        (r'\b\d{4,}\b', 0.9),           # 4位以上数字
        (r'\b\d+(\.\d+)?%', 0.8),        # 百分比
        (r'[\u4e00-\u9fff]{10,}', 0.7),  # 长中文片段（连续 10+ 汉字）
    ]

    # 行动指令关键词（权重 1.0）
    _ACTION_KEYWORDS_RE = re.compile(
        r'必须|禁止|务必|立即|马上|执行|生成|创建|删除|修改|更新|'
        r'配置|部署|启动|停止|重启|回滚|提交|发布|审批|通过|拒绝|'
        r'强制|绝对|严禁|保证|确保|确认'
    )

    # 关键/约束性关键词（直接标记为 CRITICAL）
    _CRITICAL_KEYWORDS_RE = re.compile(
        r'安全|漏洞|攻击|泄露|权限|认证|加密|脱敏|备份|恢复|'
        r'生产环境|线上|数据库|支付|资金|合同|法律|合规|'
        r'P0|P1|阻断|崩溃|宕机|数据丢失'
    )

    # 填充/寒暄模式
    _FILLER_PATTERNS = [
        re.compile(p) for p in [
            r'^(好的|嗯|哦|行|可以|没问题|收到|明白|了解|知道了)\s*$',
            r'^(谢谢|感谢|辛苦了|麻烦[你了]?)\s*$',
            r'^(你好|嗨|哈喽|在吗|在不在|有空吗)\s*$',
            r'^(这个|那个|嗯+)\s*$',
            r'^(我看看|让我想想|稍等|等一下)\s*$',
        ]
    ]

    # 新颖度信号：疑问/探索性前缀
    _NOVELTY_SIGNALS_RE = re.compile(
        r'怎么做|如何实现|能不能|是否可能|有没有办法|'
        r'设计方案|推荐|建议|分析|评估|对比|差异|'
        r'新的|最新|最近|刚发布|刚更新'
    )

    def __init__(self) -> None:
        self._stats = {"graded": 0, "critical": 0, "filler": 0, "total_time_ms": 0.0}

    # ---- 主入口 ----

    def grade(self, content: str, context_hint: Optional[str] = None) -> GradeResult:
        """对单条内容进行语义评分。

        Args:
            content: 待评分文本
            context_hint: 上下文提示（当前任务描述、前一条消息摘要等）

        Returns:
            GradeResult 包含评分、维度分解、理由
        """
        import time as _time
        t0 = _time.monotonic()

        if not content or not content.strip():
            result = GradeResult(
                score=SemanticScore.FILLER,
                label="填充",
                dimensions=DimensionScores(),
                reason="空内容",
            )
            self._record(result)
            return result

        content_len = len(content)

        # 1. 快速路径：CRITICAL 关键词
        if self._CRITICAL_KEYWORDS_RE.search(content):
            result = GradeResult(
                score=SemanticScore.CRITICAL,
                label="关键",
                dimensions=DimensionScores(
                    factual_density=1.0,
                    action_content=1.0,
                    contextual_relevance=1.0,
                    information_novelty=0.8,
                ),
                reason="包含安全/关键约束关键词",
                confidence=0.95,
            )
            self._record(result)
            return result

        # 2. 快速路径：FILLER 模式
        for pattern in self._FILLER_PATTERNS:
            if pattern.search(content.strip()):
                result = GradeResult(
                    score=SemanticScore.FILLER,
                    label="填充",
                    dimensions=DimensionScores(information_novelty=0.1),
                    reason="匹配填充/寒暄模式",
                    confidence=0.90,
                )
                self._record(result)
                return result

        # 3. 短文本（<20 字符）默认 LOW
        if content_len < 20:
            result = GradeResult(
                score=SemanticScore.LOW,
                label="低价值",
                dimensions=DimensionScores(),
                reason=f"文本过短 ({content_len} 字符)",
                confidence=0.70,
            )
            self._record(result)
            return result

        # 4. 全维度评分
        dims = DimensionScores(
            factual_density=self._score_factual_density(content),
            action_content=self._score_action_content(content),
            contextual_relevance=self._score_contextual(content, context_hint),
            information_novelty=self._score_novelty(content),
        )

        composite = dims.composite

        # 5. 综合分 → 等级映射
        score, reason = self._map_composite(composite, content_len)

        result = GradeResult(
            score=score,
            label=SCORE_LABELS[score],
            dimensions=dims,
            reason=reason,
            confidence=min(composite + 0.2, 1.0),
        )

        elapsed_ms = (_time.monotonic() - t0) * 1000
        self._stats["total_time_ms"] += elapsed_ms

        self._record(result)
        return result

    def grade_batch(self, items: list[str], context_hint: Optional[str] = None) -> list[GradeResult]:
        """批量评分。"""
        return [self.grade(item, context_hint) for item in items]

    # ---- 四维评分方法 ----

    def _score_factual_density(self, content: str) -> float:
        """信息密度评分。

        指标：数字含量、专有名词含量、结构化信息含量。
        """
        score = 0.0

        # 数字密度
        digit_count = sum(1 for c in content if c.isdigit())
        digit_ratio = digit_count / max(len(content), 1)
        score += min(digit_ratio * 10, 0.4)

        # 百分比/数值模式
        if re.search(r'\b\d+(\.\d+)?%', content):
            score += 0.1
        if re.search(r'\b\d{4,}\b', content):
            score += 0.1

        # 英文专有名词（大写开头）
        proper_nouns = len(re.findall(r'\b[A-Z][a-z]{2,}\b', content))
        score += min(proper_nouns * 0.05, 0.2)

        # 结构化标记（列表、JSON、代码块）
        if re.search(r'```|^\s*[-*]\s|\{\s*"|<\w+', content, re.MULTILINE):
            score += 0.15

        # 长连续中文（信息密度高）
        long_chinese = re.findall(r'[\u4e00-\u9fff]{15,}', content)
        score += min(len(long_chinese) * 0.05, 0.1)

        return min(score, 1.0)

    def _score_action_content(self, content: str) -> float:
        """行动含量评分。

        指标：指令性动词密度、行动项数量。
        """
        # 行动关键词匹配
        action_matches = len(self._ACTION_KEYWORDS_RE.findall(content))
        word_count = max(len(content.split()), 1)
        action_ratio = action_matches / word_count

        score = min(action_ratio * 15, 0.6)

        # 链式指令（多个连续行动词）
        if action_matches >= 3:
            score += 0.2

        # 代码/命令模式
        if re.search(r'```|`[^`]+`|\bcurl\b|\bgit\b|\bnpm\b|\bpip\b|\bdocker\b', content):
            score += 0.15

        # 量化指令（有明确数量的任务）
        if re.search(r'\d+\s*(个|项|条|次|步|阶段)', content):
            score += 0.1

        return min(score, 1.0)

    def _score_contextual(self, content: str, context_hint: Optional[str]) -> float:
        """上下文相关性评分。

        指标：与当前任务/上下文提示的重叠度。
        """
        if not context_hint:
            return 0.5  # 无上下文时默认中等

        # 词重叠度（简单 Jaccard）
        content_words = set(content)
        hint_words = set(context_hint)
        if not hint_words:
            return 0.5

        overlap = len(content_words & hint_words)
        jaccard = overlap / max(len(content_words | hint_words), 1)

        # 关键 token 重叠加分
        key_tokens = self._extract_key_tokens(context_hint)
        if key_tokens:
            key_overlap = sum(1 for t in key_tokens if t in content)
            jaccard += key_overlap * 0.1

        return min(jaccard * 3, 1.0)

    def _score_novelty(self, content: str) -> float:
        """信息新颖度评分。

        指标：是否引入新信息、新方案、新问题。
        """
        score = 0.3  # 默认基础分（不是全旧信息）

        # 探索/疑问信号
        if self._NOVELTY_SIGNALS_RE.search(content):
            score += 0.3

        # 新方案/新观点信号
        new_patterns = [
            (r'方案\s*[一二三1-9]', 0.1),
            (r'替代|替代方案|备选|plan\s*b', 0.1),
            (r'还有一种|换个角度|重新|不妨', 0.1),
            (r'研究发现|最新|刚|据报道', 0.15),
        ]
        for pattern, weight in new_patterns:
            if re.search(pattern, content):
                score += weight

        # 长文本天然新颖度更高
        if len(content) > 200:
            score += 0.1

        return min(score, 1.0)

    # ---- 辅助方法 ----

    def _map_composite(self, composite: float, content_len: int) -> tuple[SemanticScore, str]:
        """综合分 → 等级映射。"""
        # 极长文本（>500 字符）默认至少 MEDIUM
        if content_len > 500 and composite < 0.4:
            composite = 0.4

        if composite >= 0.85:
            return SemanticScore.CRITICAL, f"综合分 {composite:.2f} → 关键"
        elif composite >= 0.65:
            return SemanticScore.HIGH, f"综合分 {composite:.2f} → 高价值"
        elif composite >= 0.45:
            return SemanticScore.MEDIUM_HIGH, f"综合分 {composite:.2f} → 中高"
        elif composite >= 0.25:
            return SemanticScore.MEDIUM, f"综合分 {composite:.2f} → 中等"
        elif composite >= 0.10:
            return SemanticScore.LOW, f"综合分 {composite:.2f} → 低价值"
        else:
            return SemanticScore.FILLER, f"综合分 {composite:.2f} → 填充"

    @staticmethod
    def _extract_key_tokens(text: str, top_n: int = 8) -> list[str]:
        """从上下文提示中提取关键词 token。"""
        # 简单版：提取 2+ 字符的中文词（实际可用 jieba 分词，这里保持零依赖）
        tokens = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        # 按长度降序，取前 N 个
        tokens_sorted = sorted(set(tokens), key=len, reverse=True)
        return tokens_sorted[:top_n]

    def _record(self, result: GradeResult) -> None:
        """内部统计。"""
        self._stats["graded"] += 1
        if result.score == SemanticScore.CRITICAL:
            self._stats["critical"] += 1
        elif result.score <= SemanticScore.LOW:
            self._stats["filler"] += 1

    # ---- 集成接口 ----

    def filter_messages(
        self,
        messages: list[dict],
        max_keep: int = 20,
        context_hint: Optional[str] = None,
    ) -> list[dict]:
        """对消息列表评分并剪枝。

        保留策略：CRITICAL 全保留 → HIGH/MEDIUM_HIGH 优先 → MEDIUM 按需 → LOW/FILLER 可丢弃。

        Args:
            messages: 消息列表（含 content 字段）
            max_keep: 最大保留条数
            context_hint: 上下文提示

        Returns:
            排序 + 剪枝后的消息列表
        """
        if not messages:
            return []

        # 评分
        graded = []
        for msg in messages:
            content = msg.get("content", "")
            result = self.grade(content, context_hint)
            # 将评分存入 metadata
            msg_copy = dict(msg)
            msg_copy["_grade"] = {
                "score": int(result.score),
                "label": result.label,
                "dimensions": {
                    "factual_density": result.dimensions.factual_density,
                    "action_content": result.dimensions.action_content,
                    "contextual_relevance": result.dimensions.contextual_relevance,
                    "information_novelty": result.dimensions.information_novelty,
                },
            }
            graded.append((result, msg_copy))

        # 排序：优先保留高价值 + 关键
        graded.sort(key=lambda x: (int(x[0].score), len(x[1].get("content", ""))), reverse=True)

        # 剪枝：保留 max_keep 条，但 CRITICAL 强制全保留
        critical_count = sum(1 for r, _ in graded if r.score == SemanticScore.CRITICAL)
        keep_count = max(max_keep, critical_count)

        kept = [msg for _, msg in graded[:keep_count]]

        if len(graded) > keep_count:
            logger.debug(
                f"SemanticGrader filtered {len(graded)} → {len(kept)} messages "
                f"(critical={critical_count}, max_keep={max_keep})"
            )

        return kept

    @property
    def stats(self) -> dict:
        """评分统计信息。"""
        return {
            **self._stats,
            "avg_time_ms": round(
                self._stats["total_time_ms"] / max(self._stats["graded"], 1), 2
            ),
        }


# 全局单例
semantic_grader = SemanticGrader()
