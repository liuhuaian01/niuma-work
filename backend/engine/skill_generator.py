"""
太极引擎 · 技能自生成引擎

当反思引擎发现高成功率的执行模式时，自动生成可复用的 Skill。

模式 → Skill 的转化：
  "writing+deepseek 连续15天成功率95%" → 自动生成一个 SKILL.md
  内容是："写作任务优先用 deepseek-v4，Token 预算 30K+，启动前先查本地知识库"
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json
import os


@dataclass
class GeneratedSkill:
    """从执行模式中自动生成的技能。"""
    id: str
    name: str
    description: str
    trigger_pattern: str          # 触发条件："当用户请求写作时"
    recommended_model: str
    suggested_token_budget: int
    pre_checks: list[str] = field(default_factory=list)  # ["先查本地知识库", "避免外网搜索"]
    success_rate: float = 0.0
    sample_count: int = 0
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: int = 1
    active: bool = True


class SkillGenerator:
    """技能自生成引擎——从执行模式中自动创造技能。

    不是等用户去社区下载，是太极引擎自己长出新技能。
    """

    SKILLS_DIR = "data/generated_skills"

    def __init__(self, skills_dir: str | None = None) -> None:
        self._dir = skills_dir or self.SKILLS_DIR
        self._generated: dict[str, GeneratedSkill] = {}
        os.makedirs(self._dir, exist_ok=True)
        self._load_existing()

    def _load_existing(self) -> None:
        """加载已生成的技能。"""
        if not os.path.exists(self._dir):
            return
        for fname in os.listdir(self._dir):
            if fname.endswith(".json"):
                path = os.path.join(self._dir, fname)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    skill = GeneratedSkill(**data)
                    self._generated[skill.id] = skill
                except Exception:
                    pass

    def generate_from_pattern(
        self, pattern_name: str, success_rate: float, sample_count: int,
        avg_tokens: int = 10000,
    ) -> Optional[GeneratedSkill]:
        """从反思引擎发现的模式中生成技能。

        模式名格式: "writing+deepseek-v4"
        """
        if sample_count < 5 or success_rate < 0.75:
            return None  # 样本不足或成功率太低

        parts = pattern_name.split("+", 1)
        if len(parts) != 2:
            return None
        task_type, model = parts[0].strip(), parts[1].strip()

        # 技能命名
        skill_id = f"auto-{task_type}-{model}".replace(" ", "-").lower()
        if skill_id in self._generated:
            # 已有这个技能——更新版本和参数
            existing = self._generated[skill_id]
            existing.success_rate = success_rate
            existing.sample_count = sample_count
            existing.suggested_token_budget = avg_tokens
            existing.version += 1
            return existing

        # 生成新技能
        descriptions = {
            "writing": "自动发现：写作任务优选此模型组合",
            "coding": "自动发现：编码任务优选此模型组合",
            "analysis": "自动发现：分析任务优选此模型组合",
        }

        pre_checks = ["启动前检查 Token 预算"]
        if "deepseek" in model.lower():
            pre_checks.append("利用 1M 上下文窗口，带上完整背景")
        if "kimi" in model.lower():
            pre_checks.append("中文写作场景可用更简洁的系统提示")

        skill = GeneratedSkill(
            id=skill_id,
            name=f"自动技巧：{task_type} 用 {model}",
            description=descriptions.get(task_type, f"自动发现的{task_type}最优方案"),
            trigger_pattern=task_type,
            recommended_model=model,
            suggested_token_budget=avg_tokens,
            pre_checks=pre_checks,
            success_rate=success_rate,
            sample_count=sample_count,
        )
        self._generated[skill_id] = skill
        self._save(skill)
        return skill

    def _save(self, skill: GeneratedSkill) -> None:
        path = os.path.join(self._dir, f"{skill.id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(skill.__dict__, f, ensure_ascii=False, indent=2)

    def list_generated(self) -> list[GeneratedSkill]:
        return [s for s in self._generated.values() if s.active]

    def get_stats(self) -> dict:
        active = self.list_generated()
        return {
            "total_generated": len(self._generated),
            "active": len(active),
            "skills": [
                {"name": s.name, "success_rate": s.success_rate, "version": s.version}
                for s in active
            ],
        }


# 平台唯一实例
skill_generator = SkillGenerator()
