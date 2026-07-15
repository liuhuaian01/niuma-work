"""
太极引擎 · 技能自化引擎 (SkillForge) v2.1

"物之自化" — 从使用模式中自动发现、提议、生成可复用技能。
v2.0: 半自动模式（建议+人工确认）+ 质量评分 + SKILL.md 生成。
v2.1: v1.8新增 — 迭代淘汰机制（参考SkillEvolver: 轨迹监测→标准化封装→迭代淘汰）

三步法:
  1. observe()  — 轨迹监测：记录使用模式
  2. propose()  — 标准化封装：生成技能建议
  3. prune()    — 迭代淘汰：低效技能自动降级→归档
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import json
import os
import re
import uuid


# ════════════════════════════════════════════════════════════════
# 数据模型
# ════════════════════════════════════════════════════════════════

class SkillSuggestionStatus(Enum):
    PENDING = "pending"           # 待审核
    APPROVED = "approved"          # 已采纳（生成 SKILL.md）
    REJECTED = "rejected"          # 已拒绝
    MODIFIED = "modified"          # 用户修改后采纳
    ARCHIVED = "archived"          # 已归档（不活跃）
    DEPRECATED = "deprecated"      # v2.1: 已淘汰（成功率过低或长期不使用）


@dataclass
class SkillSuggestion:
    """技能提议——由引擎发起，等待人工确认"""
    id: str
    name: str
    description: str
    trigger_pattern: str           # 触发关键词/模式
    recommended_model: str
    suggested_token_budget: int
    pre_checks: list[str] = field(default_factory=list)
    post_actions: list[str] = field(default_factory=list)
    success_rate: float = 0.0
    sample_count: int = 0
    quality_score: float = 0.0     # 0-1 质量评分
    status: str = "pending"
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    approved_at: str = ""
    approved_by: str = ""
    feedback: str = ""             # 审批者的反馈
    version: int = 1
    # v2.1: 淘汰机制追踪
    last_used_at: str = ""          # 最后一次使用时间
    deprecation_reason: str = ""    # 淘汰原因
    post_approval_success: int = 0  # 采纳后成功次数
    post_approval_failure: int = 0  # 采纳后失败次数


@dataclass
class SkillQualityReport:
    """技能质量评估报告"""
    skill_id: str
    overall_score: float            # 0-1
    naming_score: float             # 命名清晰度
    description_score: float        # 描述完整性
    uniqueness_score: float         # 与现有技能的重叠度（1=完全独特）
    safety_score: float             # 安全性（无危险操作）
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ════════════════════════════════════════════════════════════════
# 自化引擎
# ════════════════════════════════════════════════════════════════

class SkillForge:
    """
    技能自化引擎 v2.1

    三步法（参考SkillEvolver）:
    1. observe() — 轨迹监测：记录使用模式
    2. propose() — 标准化封装：生成技能建议
    3. prune()   — 迭代淘汰：低效技能自动降级→归档

    半自动模式：
    1. observe() — 监控使用模式，收集统计
    2. propose() — 当模式足够稳定时，生成技能建议
    3. approve() / reject() — 人工确认/拒绝
    4. forge() — 采纳后生成完整 SKILL.md
    5. prune() — v2.1: 淘汰低效技能
    """

    SKILLS_DIR = "data/generated_skills"
    SUGGESTIONS_DIR = "data/skill_suggestions"
    MIN_SAMPLE_COUNT = 5
    MIN_SUCCESS_RATE = 0.70
    MAX_AUTO_SCORE = 0.60           # 自动生成技能的最高质量分（需要人工提升）
    # v2.1: 淘汰阈值
    DEPRECATE_SUCCESS_RATE = 0.50   # 成功率低于50% → 淘汰
    DEPRECATE_INACTIVE_DAYS = 30    # 30天未使用 → 淘汰
    DEPRECATE_MIN_POST_APPROVAL = 5 # 采纳后至少5次执行才评估淘汰

    def __init__(self, base_dir: str | None = None) -> None:
        self._base = base_dir or "data"
        self._skills_path = os.path.join(self._base, "generated_skills")
        self._suggestions_path = os.path.join(self._base, "skill_suggestions")
        self._patterns: dict[str, dict] = {}        # 模式统计
        self._suggestions: dict[str, SkillSuggestion] = {}
        self._approved_skills: dict[str, SkillSuggestion] = {}
        os.makedirs(self._skills_path, exist_ok=True)
        os.makedirs(self._suggestions_path, exist_ok=True)
        self._load_existing()

    def _load_existing(self) -> None:
        """加载已有的建议和技能"""
        for d, container in [
            (self._suggestions_path, self._suggestions),
        ]:
            if not os.path.exists(d):
                continue
            for fname in os.listdir(d):
                if fname.endswith(".json"):
                    try:
                        with open(os.path.join(d, fname), "r", encoding="utf-8") as f:
                            data = json.load(f)
                        suggestion = SkillSuggestion(**data)
                        container[suggestion.id] = suggestion
                    except Exception:
                        pass

    # ════════════════════════════════════════════════════════════
    # 观察阶段：收集使用模式
    # ════════════════════════════════════════════════════════════

    def observe(
        self, task_type: str, model: str, success: bool,
        tokens_used: int = 0, duration_ms: int = 0,
        workspace_id: str = "default",
    ) -> None:
        """
        记录一次任务执行，累积模式统计。

        Args:
            task_type: 任务类型 (writing/coding/analysis/chat/research)
            model: 使用的模型名称
            success: 是否成功
            tokens_used: 消耗的 token 数
            duration_ms: 执行耗时（毫秒）
            workspace_id: 工作间 ID
        """
        pattern_key = f"{task_type}+{model}+{workspace_id}"
        if pattern_key not in self._patterns:
            self._patterns[pattern_key] = {
                "task_type": task_type,
                "model": model,
                "workspace_id": workspace_id,
                "total": 0,
                "successes": 0,
                "total_tokens": 0,
                "total_duration": 0,
                "avg_tokens": 0,
                "avg_duration": 0,
                "last_used": "",
            }

        p = self._patterns[pattern_key]
        p["total"] += 1
        if success:
            p["successes"] += 1
        p["total_tokens"] += tokens_used
        p["total_duration"] += duration_ms
        if p["total"] > 0:
            p["avg_tokens"] = p["total_tokens"] // p["total"]
            p["avg_duration"] = p["total_duration"] // p["total"]
        p["last_used"] = datetime.now().isoformat()

    # ════════════════════════════════════════════════════════════
    # 提议阶段：生成技能建议
    # ════════════════════════════════════════════════════════════

    def propose(self, pattern_key: str) -> Optional[SkillSuggestion]:
        """
        从观察到的模式生成技能建议。

        只有满足以下条件才生成：
        - 样本量 >= MIN_SAMPLE_COUNT
        - 成功率 >= MIN_SUCCESS_RATE
        - 同一模式尚未生成过建议
        """
        if pattern_key not in self._patterns:
            return None

        p = self._patterns[pattern_key]
        if p["total"] < self.MIN_SAMPLE_COUNT:
            return None

        success_rate = p["successes"] / max(p["total"], 1)
        if success_rate < self.MIN_SUCCESS_RATE:
            return None

        # 检查是否已存在相同建议
        suggestion_id = f"sug-{pattern_key.replace('+', '-')}"
        if suggestion_id in self._suggestions:
            existing = self._suggestions[suggestion_id]
            # 更新统计数据
            existing.success_rate = success_rate
            existing.sample_count = p["total"]
            existing.version += 1
            return existing

        # 构建技能描述
        task_type = p["task_type"]
        model = p["model"]
        name, desc = self._build_skill_metadata(task_type, model, success_rate)

        # 质量评分
        quality = self._assess_quality(task_type, model, success_rate, p["total"])

        suggestion = SkillSuggestion(
            id=suggestion_id,
            name=name,
            description=desc,
            trigger_pattern=task_type,
            recommended_model=model,
            suggested_token_budget=p["avg_tokens"] or 20000,
            pre_checks=self._build_pre_checks(task_type, model),
            post_actions=self._build_post_actions(task_type),
            success_rate=round(success_rate, 3),
            sample_count=p["total"],
            quality_score=round(quality.overall_score, 2),
        )

        self._suggestions[suggestion_id] = suggestion
        self._save_suggestion(suggestion)
        return suggestion

    def propose_all_ready(self) -> list[SkillSuggestion]:
        """对所有满足条件的模式生成建议"""
        suggestions = []
        for key in self._patterns:
            s = self.propose(key)
            if s:
                suggestions.append(s)
        return suggestions

    # ════════════════════════════════════════════════════════════
    # 审批阶段：人工确认
    # ════════════════════════════════════════════════════════════

    def approve(self, suggestion_id: str, approved_by: str = "user") -> Optional[SkillSuggestion]:
        """
        采纳技能建议。
        采纳后自动生成 SKILL.md 并移动到技能市场。
        """
        if suggestion_id not in self._suggestions:
            return None

        s = self._suggestions[suggestion_id]
        s.status = SkillSuggestionStatus.APPROVED.value
        s.approved_at = datetime.now().isoformat()
        s.approved_by = approved_by
        self._approved_skills[suggestion_id] = s

        # 生成 SKILL.md
        self._forge_skill_md(s)

        self._save_suggestion(s)
        return s

    def reject(self, suggestion_id: str, feedback: str = "") -> Optional[SkillSuggestion]:
        """拒绝技能建议"""
        if suggestion_id not in self._suggestions:
            return None

        s = self._suggestions[suggestion_id]
        s.status = SkillSuggestionStatus.REJECTED.value
        s.feedback = feedback
        self._save_suggestion(s)
        return s

    def modify_and_approve(
        self, suggestion_id: str, modifications: dict, approved_by: str = "user"
    ) -> Optional[SkillSuggestion]:
        """
        用户修改后采纳。
        modifications 可以覆盖 name, description, trigger_pattern,
        recommended_model, suggested_token_budget 等。
        """
        if suggestion_id not in self._suggestions:
            return None

        s = self._suggestions[suggestion_id]
        for key, val in modifications.items():
            if hasattr(s, key) and val is not None:
                setattr(s, key, val)

        s.status = SkillSuggestionStatus.MODIFIED.value
        s.approved_at = datetime.now().isoformat()
        s.approved_by = approved_by
        self._approved_skills[suggestion_id] = s

        # 重新评估质量
        quality = self._assess_quality(
            s.trigger_pattern, s.recommended_model, s.success_rate, s.sample_count
        )
        s.quality_score = round(quality.overall_score, 2)

        # 生成 SKILL.md
        self._forge_skill_md(s)

        self._save_suggestion(s)
        return s

    # ════════════════════════════════════════════════════════════
    # 铸造阶段：生成 SKILL.md
    # ════════════════════════════════════════════════════════════

    def _forge_skill_md(self, suggestion: SkillSuggestion) -> str:
        """从建议生成完整的 SKILL.md 文件"""
        skill_md = self._render_skill_md(suggestion)
        skill_dir = os.path.join(self._skills_path, suggestion.id)
        os.makedirs(skill_dir, exist_ok=True)

        md_path = os.path.join(skill_dir, "SKILL.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(skill_md)

        # 同时保存 JSON 元数据
        meta_path = os.path.join(skill_dir, "meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(suggestion.__dict__, f, ensure_ascii=False, indent=2, default=str)

        return md_path

    def _render_skill_md(self, s: SkillSuggestion) -> str:
        """渲染 SKILL.md 模板"""
        pre_checks_md = "\n".join(f"- {c}" for c in s.pre_checks) if s.pre_checks else "- 无"
        post_actions_md = "\n".join(f"- {a}" for a in s.post_actions) if s.post_actions else "- 无"

        return f"""# {s.name}

**版本**: v{s.version}
**质量评分**: {s.quality_score}/1.0
**成功率**: {s.success_rate*100:.0f}%（基于 {s.sample_count} 次使用）
**自动生成**: {s.generated_at}
**采纳时间**: {s.approved_at}

---

## 描述

{s.description}

## 触发条件

当用户请求包含以下关键词时自动激活：
- `{s.trigger_pattern}`

## 推荐配置

| 参数 | 值 |
|------|-----|
| 推荐模型 | {s.recommended_model} |
| Token 预算 | {s.suggested_token_budget} |

## 前置检查

{pre_checks_md}

## 执行后操作

{post_actions_md}

---

> 此技能由太极引擎「自化」模块自动生成并人工确认。
> 生成依据：{s.sample_count} 次执行记录，成功率 {s.success_rate*100:.0f}%。
"""

    # ════════════════════════════════════════════════════════════
    # 质量评估
    # ════════════════════════════════════════════════════════════

    def _assess_quality(
        self, task_type: str, model: str, success_rate: float, sample_count: int
    ) -> SkillQualityReport:
        """
        评估自动生成技能的质量。
        自动技能最高分 0.60——需要人工确认才能达到 0.80+。
        """
        issues = []
        warnings = []

        # 命名清晰度（0-1）
        naming_score = 0.7
        if len(task_type) < 3:
            naming_score -= 0.2
            issues.append("任务类型名称过短")
        if len(model) < 3:
            naming_score -= 0.2
            issues.append("模型名称过短")

        # 描述完整性（0-1）
        description_score = 0.6
        if sample_count < 10:
            description_score -= 0.2
            warnings.append(f"样本量偏低（{sample_count}），建议积累更多数据")

        # 独特性（0-1）
        uniqueness_score = 1.0
        for existing_id in self._approved_skills:
            existing = self._approved_skills.get(existing_id)
            if existing and existing.trigger_pattern == task_type:
                uniqueness_score -= 0.3
                warnings.append(f"已存在同任务类型技能：{existing.name}")

        # 安全性（0-1）
        safety_score = 1.0
        dangerous_patterns = ["delete", "rm ", "sudo", "exec", "eval", "system"]
        if any(dp in task_type.lower() for dp in dangerous_patterns):
            safety_score -= 0.5
            issues.append("任务类型包含潜在危险操作")
        if any(dp in model.lower() for dp in dangerous_patterns):
            safety_score -= 0.3

        # 综合评分（上限 0.60，人工确认后可达 1.0）
        overall = (
            naming_score * 0.2 +
            description_score * 0.2 +
            uniqueness_score * 0.3 +
            safety_score * 0.3
        ) * min(success_rate + 0.2, 1.0)  # 成功率加成

        overall = min(overall, self.MAX_AUTO_SCORE)

        return SkillQualityReport(
            skill_id="",
            overall_score=round(overall, 2),
            naming_score=round(naming_score, 2),
            description_score=round(description_score, 2),
            uniqueness_score=round(uniqueness_score, 2),
            safety_score=round(safety_score, 2),
            issues=issues,
            warnings=warnings,
        )

    # ════════════════════════════════════════════════════════════
    # 元数据构建
    # ════════════════════════════════════════════════════════════

    def _build_skill_metadata(
        self, task_type: str, model: str, success_rate: float
    ) -> tuple[str, str]:
        """构建技能名称和描述"""
        type_names = {
            "writing": "写作",
            "coding": "编码",
            "analysis": "分析",
            "chat": "对话",
            "research": "研究",
            "creative": "创作",
            "summary": "总结",
        }
        cn_type = type_names.get(task_type, task_type)
        name = f"{cn_type}任务·{model}"
        desc = f"自动发现：{cn_type}类任务使用 {model} 模型效果最优（成功率 {success_rate*100:.0f}%）"
        return name, desc

    def _build_pre_checks(self, task_type: str, model: str) -> list[str]:
        """构建前置检查列表"""
        checks = ["检查 Token 预算是否充足"]
        if task_type in ("writing", "creative"):
            checks.append("加载用户偏好的创作风格")
            checks.append("检查是否存在相关 L3 知识库条目")
        if task_type == "coding":
            checks.append("检查 workspace 代码环境")
        if "deepseek" in model.lower():
            checks.append("可利用 1M 上下文窗口携带完整背景")
        return checks

    def _build_post_actions(self, task_type: str) -> list[str]:
        """构建后置操作列表"""
        actions = ["更新执行统计", "记录 Token 消耗"]
        if task_type in ("writing", "creative"):
            actions.append("自动保存创作快照到 L2 记忆")
        if task_type == "coding":
            actions.append("检查生成代码的安全性")
        return actions

    # ════════════════════════════════════════════════════════════
    # v2.1: 迭代淘汰机制（参考SkillEvolver: 轨迹监测→标准化封装→迭代淘汰）
    # ════════════════════════════════════════════════════════════

    def update_skill_stats(
        self, suggestion_id: str, success: bool
    ) -> Optional[SkillSuggestion]:
        """更新已采纳技能的使用统计。

        在每次技能被执行后调用，跟踪采纳后的实际表现。
        """
        s = self._suggestions.get(suggestion_id) or self._approved_skills.get(suggestion_id)
        if not s:
            return None

        if success:
            s.post_approval_success += 1
        else:
            s.post_approval_failure += 1

        total_post = s.post_approval_success + s.post_approval_failure
        if total_post > 0:
            s.success_rate = s.post_approval_success / total_post

        s.last_used_at = datetime.now().isoformat()
        self._save_suggestion(s)
        return s

    def prune_skills(self) -> dict:
        """淘汰低效技能 — 迭代淘汰核心。

        淘汰条件（两项满足其一即触发）:
          1. 采纳后执行≥{MIN_POST_APPROVAL}次 且 成功率<{DEPRECATE_SUCCESS_RATE}
          2. 距上次使用超过{DEPRECATE_INACTIVE_DAYS}天

        Returns:
            {"deprecated": [...], "warned": [...]}
        """
        result = {"deprecated": [], "warned": []}
        now = datetime.now()

        # 检查所有已采纳技能
        for s in list(self._suggestions.values()):
            if s.status not in (
                SkillSuggestionStatus.APPROVED.value,
                SkillSuggestionStatus.MODIFIED.value,
            ):
                continue

            post_total = s.post_approval_success + s.post_approval_failure

            # 条件1: 低成功率淘汰
            if post_total >= self.DEPRECATE_MIN_POST_APPROVAL:
                current_rate = s.success_rate
                if current_rate < self.DEPRECATE_SUCCESS_RATE:
                    s.status = SkillSuggestionStatus.DEPRECATED.value
                    s.deprecation_reason = (
                        f"成功率过低：{current_rate:.0%}（采纳后{post_total}次执行，"
                        f"成功{s.post_approval_success}次/失败{s.post_approval_failure}次）"
                    )
                    result["deprecated"].append({
                        "id": s.id,
                        "name": s.name,
                        "reason": s.deprecation_reason,
                    })
                    self._save_suggestion(s)
                    self._archive_skill_md(s)
                    continue

            # 条件2: 长期不使用淘汰
            if s.last_used_at:
                try:
                    last_used = datetime.fromisoformat(s.last_used_at)
                    days_inactive = (now - last_used).days
                    if days_inactive > self.DEPRECATE_INACTIVE_DAYS:
                        s.status = SkillSuggestionStatus.ARCHIVED.value
                        s.deprecation_reason = (
                            f"长期未使用：距上次使用已{days_inactive}天"
                        )
                        result["deprecated"].append({
                            "id": s.id,
                            "name": s.name,
                            "reason": s.deprecation_reason,
                        })
                        self._save_suggestion(s)
                        self._archive_skill_md(s)
                        continue
                    elif days_inactive > self.DEPRECATE_INACTIVE_DAYS * 0.5:
                        # 预警：接近淘汰阈值
                        result["warned"].append({
                            "id": s.id,
                            "name": s.name,
                            "days_inactive": days_inactive,
                            "message": f"已{days_inactive}天未使用，{self.DEPRECATE_INACTIVE_DAYS - days_inactive}天后将被淘汰",
                        })
                except (ValueError, TypeError):
                    pass  # 时间解析失败，跳过

        log_msg = f"SkillForge 淘汰周期: {len(result['deprecated'])}个淘汰, {len(result['warned'])}个预警"
        if result["deprecated"] or result["warned"]:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info(log_msg)

        return result

    def _archive_skill_md(self, suggestion: SkillSuggestion) -> None:
        """将已淘汰技能的 SKILL.md 标记为 Archived。"""
        skill_dir = os.path.join(self._skills_path, suggestion.id)
        md_path = os.path.join(skill_dir, "SKILL.md")
        if os.path.exists(md_path):
            try:
                with open(md_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # 在标题下添加归档标记
                if "已淘汰" not in content:
                    archive_marker = (
                        f"\n> ⚠️ **此技能已淘汰** — {suggestion.deprecation_reason}\n>\n"
                    )
                    # 找到第一个 --- 后插入
                    parts = content.split("---\n", 2)
                    if len(parts) >= 3:
                        content = parts[0] + "---\n" + archive_marker + "---\n" + parts[2]
                        with open(md_path, "w", encoding="utf-8") as f:
                            f.write(content)
            except Exception:
                pass

    def get_deprecated_skills(self) -> list[SkillSuggestion]:
        """列出所有已淘汰的技能。"""
        return [
            s for s in self._suggestions.values()
            if s.status in (
                SkillSuggestionStatus.DEPRECATED.value,
                SkillSuggestionStatus.ARCHIVED.value,
            )
        ]

    # ════════════════════════════════════════════════════════════
    # 持久化
    # ════════════════════════════════════════════════════════════

    def _save_suggestion(self, suggestion: SkillSuggestion) -> None:
        path = os.path.join(self._suggestions_path, f"{suggestion.id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(suggestion.__dict__, f, ensure_ascii=False, indent=2, default=str)

    # ════════════════════════════════════════════════════════════
    # 查询接口
    # ════════════════════════════════════════════════════════════

    def list_pending_suggestions(self) -> list[SkillSuggestion]:
        """列出所有待审核的建议"""
        return [
            s for s in self._suggestions.values()
            if s.status == SkillSuggestionStatus.PENDING.value
        ]

    def list_approved_skills(self) -> list[SkillSuggestion]:
        """列出所有已采纳的技能"""
        return [
            s for s in self._suggestions.values()
            if s.status in (
                SkillSuggestionStatus.APPROVED.value,
                SkillSuggestionStatus.MODIFIED.value,
            )
        ]

    def get_suggestion(self, suggestion_id: str) -> Optional[SkillSuggestion]:
        return self._suggestions.get(suggestion_id)

    def get_patterns_summary(self) -> list[dict]:
        """获取所有观察到的模式摘要"""
        return [
            {
                "key": key,
                "task_type": p["task_type"],
                "model": p["model"],
                "workspace_id": p["workspace_id"],
                "total": p["total"],
                "success_rate": round(p["successes"] / max(p["total"], 1), 3),
                "avg_tokens": p["avg_tokens"],
                "last_used": p["last_used"],
            }
            for key, p in self._patterns.items()
        ]

    def get_stats(self) -> dict:
        patterns = self.get_patterns_summary()
        suggestions = self.list_pending_suggestions()
        approved = self.list_approved_skills()
        deprecated = self.get_deprecated_skills()
        return {
            "version": "2.1",
            "mode": "semi-automatic",
            "patterns_tracked": len(patterns),
            "suggestions_pending": len(suggestions),
            "skills_approved": len(approved),
            "skills_deprecated": len(deprecated),  # v2.1
            "top_patterns": sorted(
                patterns, key=lambda x: x["total"], reverse=True
            )[:5],
            "pending_suggestions": [
                {"id": s.id, "name": s.name, "quality_score": s.quality_score}
                for s in suggestions
            ],
            "deprecated_skills": [  # v2.1
                {"id": s.id, "name": s.name, "reason": s.deprecation_reason}
                for s in deprecated
            ],
        }


# 平台唯一实例
skill_forge = SkillForge()
