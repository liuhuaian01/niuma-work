"""
太极引擎 · 知识新鲜度评分 + Skill 匹配

知识有保质期——去年的竞品分析今年参考价值下降。
Skill 唤醒需要匹配度判断——不是装了就该开。
"""

from __future__ import annotations
from datetime import datetime, date, timedelta
from typing import Optional


class FreshnessScorer:
    """知识新鲜度评分。

    衰减曲线：
      7 天内：   权重 1.0（新鲜）
      30 天内：  权重 0.8（近期）
      90 天内：  权重 0.5（可用）
      180 天内： 权重 0.3（旧知识）
      365 天+：  权重 0.1（仅供参考）
    """

    DECAY_CURVE = [
        (7, 1.0),
        (30, 0.8),
        (90, 0.5),
        (180, 0.3),
        (365, 0.1),
    ]

    def score(self, created_at: str, today: str | None = None) -> float:
        """计算知识新鲜度分数 0-1。"""
        try:
            cdate = datetime.fromisoformat(created_at[:10])
            tdate = datetime.fromisoformat(today) if today else datetime.now()
            delta = (tdate - cdate).days
        except (ValueError, TypeError):
            return 0.5  # 无法解析日期，中性

        if delta < 0:
            return 1.0

        for days, weight in self.DECAY_CURVE:
            if delta <= days:
                return weight
        return self.DECAY_CURVE[-1][1]

    def should_boost_new(self, created_at: str) -> bool:
        """新知识应被提升权重。"""
        return self.score(created_at) > 0.7


class SkillMatcher:
    """Skill 匹配度判断——不是装了就该唤醒。

    匹配因子：
      1. 关键词覆盖：任务描述中的关键词与 Skill 描述的重叠度
      2. 历史成功率：该 Skill 在此类任务上的历史表现
      3. 相关性：是否明确关联到该任务类型
    """

    WAKE_THRESHOLD = 0.30   # 匹配度 ≥ 0.3 才唤醒（中文关键词稀疏，阈值不宜过高）

    def match(self, task_description: str, skill_description: str,
              skill_name: str, history_success_rate: float = 0.5) -> float:
        """计算 Skill 与当前任务的匹配度。中文用字级，英文用词级。"""
        td = task_description.lower()
        sd = skill_description.lower()

        import re
        # 中文：字级匹配
        cn_td = set(c for c in re.findall(r'[\u4e00-\u9fff]', td))
        cn_sd = set(c for c in re.findall(r'[\u4e00-\u9fff]', sd))
        # 英文：词级匹配
        en_td = set(w for w in re.findall(r'[a-z]{3,}', td))
        en_sd = set(w for w in re.findall(r'[a-z]{3,}', sd))

        td_chars = cn_td | en_td
        sd_chars = cn_sd | en_sd

        if not td_chars:
            keyword_score = 0.3
        else:
            overlap = td_chars & sd_chars
            keyword_score = min(1.0, len(overlap) / max(len(td_chars), 1))

        name_bonus = 0.15 if skill_name.lower().replace("-", " ") in td.replace("-", " ") else 0

        score = keyword_score * 0.5 + history_success_rate * 0.3 + name_bonus * 0.2
        return min(1.0, score)

    def should_wake(self, task: str, skill_desc: str, skill_name: str,
                    history_rate: float = 0.5) -> bool:
        """判断是否应唤醒此 Skill。"""
        return self.match(task, skill_desc, skill_name, history_rate) >= self.WAKE_THRESHOLD

    def get_stats(self) -> dict:
        return {"wake_threshold": self.WAKE_THRESHOLD}
