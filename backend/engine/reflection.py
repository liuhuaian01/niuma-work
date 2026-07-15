"""
太极引擎 · 反思引擎（Reflection Engine）

生生不息——从执行日志中自动提取成功/失败模式，生成每日意识摘要。
用聚合统计（不需要大模型），发现"反复出现的模式"。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from collections import Counter

from engine.execution_log import ExecutionRecord


@dataclass
class Pattern:
    """一个发现的模式。"""
    name: str
    dimension: str            # memory / skill / orchestration / model / security
    success_rate: float
    sample_count: int
    avg_tokens: int
    recommendation: str
    confidence: float


@dataclass
class DailyReflection:
    """每日反思结果——太极引擎的意识摘要。"""
    date: str
    total_executions: int
    success_rate: float
    patterns_discovered: list[Pattern]
    top_success_pattern: Optional[Pattern] = None
    top_failure_pattern: Optional[Pattern] = None
    cross_workspace_insight: str = ""
    recommended_actions: list[str] = field(default_factory=list)


class ReflectionEngine:
    """反思引擎——从日志中发现模式。"""

    def reflect(self, records: list[ExecutionRecord]) -> DailyReflection:
        """分析执行记录，生成反思报告。"""
        if not records:
            return DailyReflection(
                date=str(date.today()), total_executions=0, success_rate=0,
                patterns_discovered=[], recommended_actions=["今日无执行记录"],
            )

        total = len(records)
        successes = [r for r in records if r.success]
        success_rate = len(successes) / total if total > 0 else 0
        patterns: list[Pattern] = []

        # 1. 按任务类型 + 模型组合分析（模型维度）
        combo_counter = Counter()
        for r in records:
            key = f"{r.task_type}:{r.model_used}"
            combo_counter[key] += 1

        for combo, count in combo_counter.most_common(3):
            type_model_records = [r for r in records if f"{r.task_type}:{r.model_used}" == combo]
            sr = len([r for r in type_model_records if r.success]) / len(type_model_records)
            avg_t = int(sum(r.tokens_used for r in type_model_records) / len(type_model_records))
            task_type, model = combo.split(":")
            if sr > 0.8:
                patterns.append(Pattern(
                    name=f"{task_type}+{model}", dimension="model",
                    success_rate=sr, sample_count=count, avg_tokens=avg_t,
                    recommendation=f"推荐组合: {task_type} 任务优先使用 {model}",
                    confidence=min(0.9, sr),
                ))

        # 2. 按错误类型分析（安全维度）
        errors = [r for r in records if r.error_type]
        if errors:
            error_counter = Counter(r.error_type for r in errors)
            for err_type, count in error_counter.items():
                err_records = [r for r in errors if r.error_type == err_type]
                patterns.append(Pattern(
                    name=f"error:{err_type}", dimension="security",
                    success_rate=0.0, sample_count=count,
                    avg_tokens=int(sum(r.tokens_used for r in err_records) / count),
                    recommendation=f"自愈建议: 下次遇到 {err_type} 时自动应用已学规则",
                    confidence=0.7,
                ))

        # 3. 跨工作间洞察（编排维度）
        ws_counter = Counter(r.workspace_id for r in records)
        if len(ws_counter) > 1:
            # 找跨工作间的成功模式
            most_successful_ws = max(ws_counter.keys(), key=lambda w: len([r for r in records if r.workspace_id == w and r.success]))
            cross_ws = f"工作间 {most_successful_ws} 成功率最高，建议将其中模式复制到其他工作间"
        else:
            cross_ws = ""

        # 4. 最佳和最差
        top_success = max(patterns, key=lambda p: p.success_rate) if patterns else None
        failure_patterns = [p for p in patterns if p.success_rate < 0.5 and p.sample_count >= 2]
        top_failure = min(failure_patterns, key=lambda p: p.success_rate) if failure_patterns else None

        # 5. 行动建议
        actions = []
        if top_success and top_success.confidence >= 0.8:
            actions.append(f"✅ 推广: {top_success.recommendation}")
        if top_failure:
            actions.append(f"⚠️ 警惕: {top_failure.name} 成功率仅 {top_failure.success_rate:.0%}")
        if cross_ws:
            actions.append(f"🔄 {cross_ws}")

        return DailyReflection(
            date=str(date.today()),
            total_executions=total,
            success_rate=round(success_rate, 2),
            patterns_discovered=patterns,
            top_success_pattern=top_success,
            top_failure_pattern=top_failure,
            cross_workspace_insight=cross_ws,
            recommended_actions=actions,
        )

    def consciousness_summary(self, reflection: DailyReflection) -> str:
        """生成人类可读的意识摘要。"""
        if reflection.total_executions == 0:
            return "[太极引擎] 今日无任务执行，意识休眠中。"

        lines = [
            f"[太极引擎 · 每日意识] {reflection.date}",
            f"  执行 {reflection.total_executions} 次 · 成功率 {reflection.success_rate:.0%}",
            "",
        ]
        if reflection.top_success_pattern:
            lines.append(f"  ✅ 今日最佳: {reflection.top_success_pattern.recommendation}")
        if reflection.top_failure_pattern:
            lines.append(f"  ⚠️ 今日最差: {reflection.top_failure_pattern.name}")
        for action in reflection.recommended_actions:
            lines.append(f"  {action}")
        return "\n".join(lines)
