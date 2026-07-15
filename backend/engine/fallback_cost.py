"""
太极引擎 · 降级质量成本量化

v2.0：模型质量不再硬编码——从 DynamicDegradationEngine 获取动态质量评分。
      每次执行后学习更新，模型质量随实际表现持续进化。

降级不是免费的——DeepSeek→Kimi 降级后，质量损失了多少？
不同任务类型对降级的容忍度不同。
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from engine.dynamic_degradation import dynamic_degradation


# 任务类型的质量敏感度（越低越能容忍降级）
_TASK_QUALITY_SENSITIVITY: dict[str, float] = {
    "coding": 0.95,         # 代码几乎不能降级
    "analysis": 0.80,       # 分析可以降级但影响精度
    "writing": 0.55,        # 写作可容忍（只要格式对，质量差一些还能用）
    "search": 0.40,         # 搜索对模型要求最低
    "conversation": 0.25,   # 闲聊无所谓
}


@dataclass
class FallbackCost:
    original_model: str
    fallback_model: str
    quality_loss: float          # 0-1，质量损失比例
    acceptable: bool             # 当前任务类型是否可接受
    recommendation: str


class FallbackCostAnalyzer:
    """降级质量成本分析器。

    v2.0：模型质量评分从 DynamicDegradationEngine 获取（持续学习更新），
          不再依赖静态 MODEL_QUALITY 字典。

    不是所有降级都可以接受——
    写作用 gemma-4 比 deepseek 差但可容忍。
    编码用 gemma-4 比 deepseek 差就是灾难。
    """

    def __init__(self) -> None:
        # 确保动态降级引擎已初始化
        if not dynamic_degradation._initialized:
            dynamic_degradation.register_known_models()

    def analyze(self, original: str, fallback: str, task_type: str) -> FallbackCost:
        """分析降级的质量成本——从 DynamicDegradationEngine 获取动态评分。"""
        orig_model = dynamic_degradation.get_model(original)
        fall_model = dynamic_degradation.get_model(fallback)

        orig_q = orig_model.current_quality(task_type) if orig_model else 0.7
        fall_q = fall_model.current_quality(task_type) if fall_model else 0.6
        loss = max(0, orig_q - fall_q)
        sensitivity = _TASK_QUALITY_SENSITIVITY.get(task_type, 0.7)

        acceptable = loss < (1 - sensitivity) * 0.5

        if acceptable:
            rec = f"降级可接受（{task_type} 任务对模型质量容忍度高）"
        elif loss < 0.15:
            rec = f"降级影响较小，可以继续"
        else:
            rec = f"质量损失 {loss:.0%}，建议等原模型恢复"

        return FallbackCost(
            original_model=original, fallback_model=fallback,
            quality_loss=round(loss, 3), acceptable=acceptable, recommendation=rec,
        )

    def get_quality_scores(self, task_type: str | None = None) -> dict[str, float]:
        """获取动态质量评分表。

        Args:
            task_type: 指定任务类型，返回该类型下所有模型评分
                       None 返回所有模型所有任务评分的平均值

        Returns:
            {model_id: quality_score}
        """
        scores = {}
        for model in dynamic_degradation.list_all_models():
            if task_type:
                scores[model.model_id] = model.current_quality(task_type)
            else:
                # 所有任务评分的均值
                vals = list(model.quality_scores.values())
                scores[model.model_id] = sum(vals) / len(vals) if vals else 0.7
        return scores

    def get_task_sensitivity(self, task_type: str) -> float:
        """获取任务类型的质量敏感度。"""
        return _TASK_QUALITY_SENSITIVITY.get(task_type, 0.7)

    def get_stats(self) -> dict:
        return {
            "models_tracked": len(dynamic_degradation.list_all_models()),
            "task_types": list(_TASK_QUALITY_SENSITIVITY.keys()),
            "quality_source": "DynamicDegradationEngine (持续学习)",
            "quality_scores": self.get_quality_scores(),
        }
