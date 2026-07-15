"""
太极引擎 · L3用户画像层（User Profile Engine）— v2.0 新增

参考：腾讯云Agent Memory L3层设计 — 从原子记忆中提取稳定偏好/约束/决策模式。
太极第五律·无为而治——不追问用户，从行为中静默学习偏好。

核心机制：
  1. 偏好提取（Preference Mining）— 从交互轨迹中提取稳定偏好
  2. 约束学习（Constraint Learning）— 学习用户的项目规范和约束
  3. 决策模式（Decision Pattern）— 识别用户的决策倾向
  4. 画像检索（Profile Retrieval）— 新任务时注入相关偏好

设计原则（铁则）：
  - 隐私至上：画像数据仅本地存储，不含敏感信息
  - 渐进学习：偏好置信度随验证次数逐步提升
  - 可遗忘：超过30天未验证的偏好自动降级

使用方式：
    from engine.l3_profile import l3_profile
    await l3_profile.learn_preference(
        user_id="claud", category="project_structure",
        preference="前端组件放在 src/components/", confidence=0.6
    )
    profile = await l3_profile.get_profile("claud", context="写一个React组件")
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import asyncio
import json
import logging
import os
import re
import time

logger = logging.getLogger("niuma.l3")


# ============================================================
# 数据模型
# ============================================================

@dataclass
class UserPreference:
    """用户偏好——一条从交互中学习的偏好记录。"""
    id: str
    category: str                # project_structure / naming / code_style / model_choice / interaction
    key: str                     # 偏好键（如 "component_path"）
    value: str                   # 偏好值（如 "src/components/"）
    confidence: float            # 置信度 0-1（随验证次数提升）
    verified_count: int = 0      # 被验证次数
    source: str = ""             # 来源（从哪条对话中学到的）
    first_seen: float = field(default_factory=time.time)
    last_seen: float = 0.0
    stale_after_days: int = 30   # 超过30天未验证→降级


@dataclass
class UserConstraint:
    """用户约束——必须遵守的规则。"""
    id: str
    category: str                # security / quality / naming / budget
    rule: str                    # 约束规则描述
    priority: str = "normal"     # critical / high / normal
    active: bool = True
    first_seen: float = field(default_factory=time.time)
    validated_count: int = 0


@dataclass
class DecisionPattern:
    """决策模式——用户做选择时的倾向。"""
    id: str
    category: str                # model_selection / framework_choice / approach
    pattern: str                 # 模式描述（如 "prefer_local_models"）
    strength: float = 0.5        # 倾向强度 0-1
    sample_size: int = 0         # 支撑样本数
    last_seen: float = field(default_factory=time.time)


# ============================================================
# L3画像引擎
# ============================================================

class L3ProfileEngine:
    """L3用户画像引擎——从L1原子记忆中提取稳定画像。"""

    MAX_PREFERENCES = 100
    MAX_CONSTRAINTS = 50
    MAX_PATTERNS = 30
    PRUNE_AFTER_DAYS = 30
    DATA_DIR = "data/profiles"

    def __init__(self, data_dir: str | None = None) -> None:
        self._data_dir = data_dir or self.DATA_DIR
        self._preferences: dict[str, UserPreference] = {}
        self._constraints: dict[str, UserConstraint] = {}
        self._patterns: dict[str, DecisionPattern] = {}
        self._is_initialized = False

    async def initialize(self) -> None:
        os.makedirs(self._data_dir, exist_ok=True)
        state_file = os.path.join(self._data_dir, "l3_state.json")
        try:
            if os.path.exists(state_file):
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                for p in state.get("preferences", []):
                    self._preferences[p["id"]] = UserPreference(**p)
                for c in state.get("constraints", []):
                    self._constraints[c["id"]] = UserConstraint(**c)
                for dp in state.get("patterns", []):
                    self._patterns[dp["id"]] = DecisionPattern(**dp)
                logger.info(
                    f"L3画像恢复: {len(self._preferences)}偏好, "
                    f"{len(self._constraints)}约束, {len(self._patterns)}模式"
                )
        except Exception:
            logger.debug("L3状态文件损坏", exc_info=True)
        self._is_initialized = True

    async def _save_state(self) -> None:
        state_file = os.path.join(self._data_dir, "l3_state.json")
        try:
            state = {
                "preferences": [
                    {"id": p.id, "category": p.category, "key": p.key,
                     "value": p.value, "confidence": p.confidence,
                     "verified_count": p.verified_count, "source": p.source,
                     "first_seen": p.first_seen, "last_seen": p.last_seen}
                    for p in self._preferences.values()
                ],
                "constraints": [
                    {"id": c.id, "category": c.category, "rule": c.rule,
                     "priority": c.priority, "active": c.active,
                     "first_seen": c.first_seen, "validated_count": c.validated_count}
                    for c in self._constraints.values()
                ],
                "patterns": [
                    {"id": dp.id, "category": dp.category, "pattern": dp.pattern,
                     "strength": dp.strength, "sample_size": dp.sample_size,
                     "last_seen": dp.last_seen}
                    for dp in self._patterns.values()
                ],
                "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ----------------------------------------------------------
    # 偏好学习
    # ----------------------------------------------------------

    async def learn_preference(
        self, user_id: str, category: str, preference: str,
        confidence: float = 0.5, source: str = "",
    ) -> UserPreference:
        """学习一个用户偏好——从交互中静默提取。"""
        pref_id = f"{user_id}:{category}:{preference[:30]}"

        existing = self._preferences.get(pref_id)
        if existing:
            existing.confidence = min(1.0, existing.confidence + 0.1)
            existing.verified_count += 1
            existing.last_seen = time.time()
            existing.source = source or existing.source
            return existing

        pref = UserPreference(
            id=pref_id,
            category=category,
            key=category,
            value=preference,
            confidence=confidence,
            verified_count=1,
            source=source,
            last_seen=time.time(),
        )

        self._preferences[pref_id] = pref
        if len(self._preferences) > self.MAX_PREFERENCES:
            # 淘汰低置信度偏好
            stale = sorted(self._preferences.values(), key=lambda p: p.confidence)
            for s in stale[:max(1, len(self._preferences) - self.MAX_PREFERENCES)]:
                del self._preferences[s.id]

        asyncio.ensure_future(self._save_state())
        return pref

    async def verify_preference(self, pref_id: str) -> bool:
        """验证一个偏好——用户主动确认或行为验证后调用。"""
        existing = self._preferences.get(pref_id)
        if not existing:
            return False
        existing.confidence = min(1.0, existing.confidence + 0.15)
        existing.verified_count += 1
        existing.last_seen = time.time()
        return True

    # ----------------------------------------------------------
    # 约束学习
    # ----------------------------------------------------------

    async def learn_constraint(
        self, user_id: str, category: str, rule: str,
        priority: str = "normal",
    ) -> UserConstraint:
        """学习一个用户约束。"""
        constraint_id = f"{user_id}:constraint:{category}:{rule[:30]}"

        existing = self._constraints.get(constraint_id)
        if existing:
            existing.validated_count += 1
            return existing

        constraint = UserConstraint(
            id=constraint_id,
            category=category,
            rule=rule,
            priority=priority,
        )
        self._constraints[constraint_id] = constraint
        if len(self._constraints) > self.MAX_CONSTRAINTS:
            stale = sorted(self._constraints.values(), key=lambda c: c.validated_count)
            for s in stale[:max(1, len(self._constraints) - self.MAX_CONSTRAINTS)]:
                del self._constraints[s.id]

        asyncio.ensure_future(self._save_state())
        return constraint

    # ----------------------------------------------------------
    # 画像检索
    # ----------------------------------------------------------

    async def get_profile(
        self, user_id: str, context: str = "",
    ) -> dict:
        """获取用户画像——新任务执行前注入决策上下文。

        Returns:
            {preferences, constraints, patterns, summary}
        """
        now = time.time()
        stale_threshold = self.PRUNE_AFTER_DAYS * 86400

        # 过滤活跃偏好（非stale，置信度>0.4）
        active_prefs = [
            {
                "id": p.id,
                "category": p.category,
                "value": p.value,
                "confidence": p.confidence,
                "verified_count": p.verified_count,
            }
            for p in self._preferences.values()
            if p.confidence >= 0.4 and (now - (p.last_seen or p.first_seen)) < stale_threshold
        ]

        # 活跃约束
        active_constraints = [
            {"id": c.id, "category": c.category, "rule": c.rule, "priority": c.priority}
            for c in self._constraints.values()
            if c.active
        ]

        # 按类别分组偏好
        by_category: dict[str, list[dict]] = {}
        for p in active_prefs:
            by_category.setdefault(p["category"], []).append(p)

        # 生成摘要
        summary_parts = []
        for cat, items in by_category.items():
            best = max(items, key=lambda x: x["confidence"])
            summary_parts.append(f"[{cat}] {best['value']} (置信度{best['confidence']:.0%})")

        constraints_summary = []
        for c in active_constraints:
            if c["priority"] == "critical":
                constraints_summary.append(f"规则: {c['rule']}")

        return {
            "user_id": user_id,
            "preferences": by_category,
            "constraints": constraints_summary,
            "summary": " | ".join(summary_parts) if summary_parts else "尚无稳定画像",
            "total_preferences": len(active_prefs),
            "total_constraints": len(active_constraints),
        }

    async def get_context_injection(
        self, user_id: str, context: str = "",
    ) -> str:
        """生成可注入到系统提示的画像上下文。

        不超过300字——克制，不烧Token。
        """
        profile = await self.get_profile(user_id, context)
        if profile["total_preferences"] == 0 and profile["total_constraints"] == 0:
            return ""

        injection = "[用户画像] "
        parts = [profile["summary"]]

        for c in profile.get("constraints", []):
            parts.append(c["rule"])

        injection += " | ".join(parts[:3])  # 最多3条
        return injection[:300]

    # ----------------------------------------------------------
    # 查询接口
    # ----------------------------------------------------------

    def get_stats(self) -> dict:
        return {
            "preferences_count": len(self._preferences),
            "constraints_count": len(self._constraints),
            "patterns_count": len(self._patterns),
            "high_confidence_prefs": sum(1 for p in self._preferences.values() if p.confidence >= 0.8),
            "initialized": self._is_initialized,
        }

    def list_preferences(self, category: str = "") -> list[dict]:
        prefs = self._preferences.values()
        if category:
            prefs = [p for p in prefs if p.category == category]
        return [
            {"id": p.id, "category": p.category, "value": p.value,
             "confidence": p.confidence, "verified_count": p.verified_count}
            for p in sorted(prefs, key=lambda x: -x.confidence)
        ]

    def list_constraints(self) -> list[dict]:
        return [
            {"id": c.id, "category": c.category, "rule": c.rule,
             "priority": c.priority, "active": c.active}
            for c in self._constraints.values()
        ]


# ============================================================
# 全局实例
# ============================================================

l3_profile = L3ProfileEngine()
