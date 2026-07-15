"""
太极引擎 · Honcho 用户建模

记忆三元中的"三"——从 L1/L2/L3 中自然涌现的用户理解。
不是规则集，是从对话和执行的积累中自己长出的用户画像。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class UserProfile:
    """用户画像——从积累中自然涌现。"""
    user_id: str
    preferred_models: list[str] = field(default_factory=list)          # 偏好模型
    frequent_task_types: list[str] = field(default_factory=list)        # 高频任务类型
    preferred_language: str = "zh"                                       # 语言偏好
    work_hours: tuple[int, int] = (9, 18)                               # 工作时间段
    topic_interests: list[str] = field(default_factory=list)             # 话题兴趣
    learning_history: list[dict] = field(default_factory=list)           # 学习历史
    last_active: str = ""
    total_interactions: int = 0
    skill_levels: dict[str, float] = field(default_factory=dict)         # 技能熟练度


class HonchoModeler:
    """Honcho 辩证式用户建模。

    从 L1 会话记忆、L2 档案、L3 知识库中学习。
    越用越懂用户——不是预设的面谱，是长出来的理解。
    """

    def __init__(self) -> None:
        self._profiles: dict[str, UserProfile] = {}

    def get_or_create(self, user_id: str) -> UserProfile:
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(user_id=user_id)
        return self._profiles[user_id]

    def learn_from_execution(
        self, user_id: str, task_type: str, model_used: str, success: bool
    ) -> None:
        """从每次执行中学习用户偏好。"""
        profile = self.get_or_create(user_id)
        profile.total_interactions += 1
        profile.last_active = datetime.now().isoformat()

        # 模型偏好——出现3次以上才纳入
        if success:
            if model_used not in profile.preferred_models and model_used != "unknown":
                profile.preferred_models.append(model_used)

        # 任务类型频率
        if task_type not in profile.frequent_task_types:
            profile.frequent_task_types.append(task_type)

    def learn_from_feedback(self, user_id: str, feedback: str) -> None:
        """从用户反馈中学习。"""
        profile = self.get_or_create(user_id)
        profile.learning_history.append({
            "timestamp": datetime.now().isoformat(),
            "feedback": feedback[:200],
        })

    def recommend_model(self, user_id: str, task_type: str, candidates: list[str]) -> Optional[str]:
        """根据用户历史推荐模型。"""
        profile = self.get_or_create(user_id)
        for pref in profile.preferred_models:
            if pref in candidates:
                return pref
        return candidates[0] if candidates else None

    def infer_skill_level(self, user_id: str, task_type: str) -> float:
        """推断用户在某领域的熟练度。"""
        profile = self.get_or_create(user_id)
        # 基于交互次数粗略估算
        task_count = sum(1 for h in profile.learning_history
                        if task_type in str(h.get("feedback", "")))
        base = 0.3
        bonus = min(0.7, task_count * 0.05)
        return base + bonus

    def get_profile(self, user_id: str) -> UserProfile:
        return self.get_or_create(user_id)

    def get_stats(self) -> dict:
        return {
            "users_modeled": len(self._profiles),
            "total_interactions": sum(p.total_interactions for p in self._profiles.values()),
        }
