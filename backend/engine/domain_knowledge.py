"""
太极引擎 · 领域知识自积累引擎

用户在特定领域（法律/医疗/金融/教育/技术）的持续使用，
会让太极引擎自动积累该领域的专业知识和最佳实践。

不是靠人输入的领域知识库，是从使用中自己长出来的。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from collections import Counter
import json
import os


DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "legal": ["法律", "合同", "诉讼", "判决", "律师", "法规", "条款", "知识产权"],
    "medical": ["医疗", "诊断", "药品", "治疗", "病例", "医院", "患者", "临床"],
    "finance": ["金融", "投资", "股票", "基金", "理财", "银行", "贷款", "保险", "财务"],
    "education": ["教育", "教学", "课程", "考试", "学生", "老师", "培训", "学习"],
    "tech": ["代码", "架构", "部署", "数据库", "API", "算法", "服务器", "编程"],
    "marketing": ["营销", "品牌", "广告", "推广", "用户", "流量", "转化", "文案"],
    "real_estate": ["房产", "建筑", "装修", "租赁", "买卖", "物业"],
}

@dataclass
class DomainKnowledge:
    domain: str
    confidence: float          # 0-1，这个用户有多大可能是该领域的使用者
    interaction_count: int     # 该领域的交互次数
    common_tasks: list[str]    # 该领域常见任务类型
    preferred_models: dict[str, int]  # 该领域偏好的模型
    avg_token_per_task: dict[str, int]  # 该领域各任务类型的平均 Token
    discovered_keywords: list[str]  # 从用户使用中发现的额外领域关键词
    last_updated: str = ""


class DomainAccumulator:
    """领域知识自积累引擎。

    用户在某个领域用得越多，引擎越懂这个领域。
    积累的知识随进化回传共享给平台。
    """

    def __init__(self) -> None:
        self._domains: dict[str, DomainKnowledge] = {}
        self._task_type_counter: Counter = Counter()
        self._model_counter: dict[str, Counter] = {}
        self._token_accumulator: dict[str, list[int]] = {}

    def analyze_task(self, content: str, task_type: str, model: str, tokens: int) -> list[str]:
        """分析一次任务，返回匹配的领域列表。"""
        matched_domains: list[str] = []

        for domain, keywords in DOMAIN_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in content)
            if matches >= 2:
                matched_domains.append(domain)
                self._update_domain(domain, task_type, model, tokens)

        return matched_domains

    def _update_domain(self, domain: str, task_type: str, model: str, tokens: int) -> None:
        """更新领域知识。"""
        if domain not in self._domains:
            self._domains[domain] = DomainKnowledge(
                domain=domain, confidence=0.0, interaction_count=0,
                common_tasks=[], preferred_models={}, avg_token_per_task={},
                discovered_keywords=[], last_updated=datetime.now().isoformat(),
            )

        dk = self._domains[domain]
        dk.interaction_count += 1
        dk.last_updated = datetime.now().isoformat()

        # 更新常见任务
        self._task_type_counter[f"{domain}:{task_type}"] += 1
        dk.common_tasks = [t.split(":", 1)[1] for t, _ in
                          self._task_type_counter.most_common(3)
                          if t.startswith(domain)]

        # 更新偏好模型
        if domain not in self._model_counter:
            self._model_counter[domain] = Counter()
        self._model_counter[domain][model] += 1
        dk.preferred_models = dict(self._model_counter[domain].most_common(3))

        # Token 统计
        key = f"{domain}:{task_type}"
        if key not in self._token_accumulator:
            self._token_accumulator[key] = []
        self._token_accumulator[key].append(tokens)
        if self._token_accumulator[key]:
            dk.avg_token_per_task[task_type] = sum(self._token_accumulator[key]) // len(self._token_accumulator[key])

        # 置信度——互动越多越确定
        dk.confidence = min(1.0, dk.interaction_count / 30)

    def get_top_domains(self, min_confidence: float = 0.3) -> list[DomainKnowledge]:
        """获取用户的主要使用领域。"""
        return [d for d in self._domains.values() if d.confidence >= min_confidence]

    def get_domain_recommendations(self, domain: str) -> dict:
        """获取某领域的使用建议。"""
        dk = self._domains.get(domain)
        if not dk:
            return {}
        return {
            "domain": domain, "confidence": dk.confidence,
            "interactions": dk.interaction_count,
            "common_tasks": dk.common_tasks,
            "preferred_models": dk.preferred_models,
            "avg_tokens": dk.avg_token_per_task,
            "suggestion": f"你是{dk.domain}领域的重度用户（{dk.interaction_count}次交互），推荐优先使用 {list(dk.preferred_models.keys())[:2]}",
        }

    def get_stats(self) -> dict:
        return {
            "domains_discovered": len(self._domains),
            "top_domains": [
                d.domain for d in self.get_top_domains(0.3)
            ],
        }
