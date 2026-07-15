"""
太极引擎 · 动态降级引擎（Dynamic Degradation Engine）

道生一，一生二，二生三，三生万物。

降级不是 "A→B→C" 的固定序列——
是根据任务类型 × 预算 × 历史质量 × 可用性的动态决策。

Auto 模式下，太极引擎自动感知可用模型池，
为每一次任务动态构建最优降级路径。

核心能力：
  1. 模型池自动发现（Ollama / API Key / 配置文件）
  2. 任务类型感知的质量排名（代码/写作/分析/搜索/对话）
  3. 动态降级路径生成（而非固定序列）
  4. 持续质量学习（从 gate_score + user_feedback + execution 学习）
  5. 成本感知（预算紧张时自动选性价比高的降级路径）
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import asyncio
import json
import logging
import time

from engine.telemetry_hub import telemetry_hub

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# 数据模型
# ════════════════════════════════════════════════════════════════

@dataclass
class ModelCapability:
    """单个模型的能力画像——太极引擎对模型的理解。

    不是简单的"质量分数"，而是每类任务上的独立评分，
    因为同一个模型在不同任务上表现天差地别。
    """
    model_id: str                       # 内部标识（如 "deepseek-v4"）
    registry_name: str                  # 注册中心名称（如 "deepseek-chat"）
    display_name: str                   # 用户可见名称（如 "DeepSeek V4"）
    provider: str                       # 提供商（"deepseek"/"openai"/"ollama"/"hunyuan"/"glm"）
    source: str                         # 来源（"api" = 云端 API, "local" = Ollama本地）
    context_limit: int                  # 上下文窗口上限
    quality_scores: dict[str, float]    # task_type → 质量评分 0-1（示例 {"coding": 0.95, "writing": 0.85}）
    cost_per_1k_tokens: float           # 相对成本系数（deepseek-v4 = 1.0 基准）
    is_local: bool                      # true=本地模型
    available: bool = True              # 当前健康状态
    fail_count: int = 0                 # 连续失败次数
    last_fail_time: float = 0.0         # 最后失败时间戳
    disabled_until: float = 0.0         # 禁用截止时间（0=未禁用）

    def current_quality(self, task_type: str) -> float:
        """获取当前任务类型的质量评分（有学习更新）。"""
        return self.quality_scores.get(task_type, 0.65)

    def is_disabled(self) -> bool:
        """检查是否被暂时禁用（连续失败）。"""
        return time.time() < self.disabled_until

    def mark_failure(self, cooldown_seconds: int = 1800) -> None:
        """记录一次失败。连续失败 3 次触发禁用。"""
        self.fail_count += 1
        self.last_fail_time = time.time()
        if self.fail_count >= 3:
            self.disabled_until = time.time() + cooldown_seconds
            self.available = False
            logger.info("模型 %s 连续失败 %d 次，已禁用至 %s",
                        self.model_id, self.fail_count,
                        time.strftime('%H:%M:%S', time.localtime(self.disabled_until)))

    def mark_success(self) -> None:
        """记录一次成功——重置失败计数。"""
        self.fail_count = 0
        self.available = True

    def update_quality(self, task_type: str, new_score: float) -> None:
        """用指数移动平均更新质量评分。

        最新一次执行的影响最大（α=0.3），
        历史评分平滑衰减。防止单次异常波动。
        """
        alpha = 0.3
        old = self.quality_scores.get(task_type, 0.65)
        self.quality_scores[task_type] = old * (1 - alpha) + new_score * alpha


@dataclass
class DegradationStep:
    """降级路径中的一步。"""
    model_id: str
    quality_loss: float       # 相对首选的质量损失 0-1
    cost_ratio: float         # 相对首选的成本比
    reason: str               # 为什么走到这一步


@dataclass
class DegradationPath:
    """完整的动态降级路径。

    Auto 模式下，太极引擎生成这条路径：
      首选模型 → 二级降级 → 三级降级 → ... → 兜底模型
    """
    primary_model: str                    # 首选模型 ID
    steps: list[DegradationStep]          # 降级步骤（不含首选）
    task_type: str                        # 目标任务类型
    total_quality_loss: float             # 全路径最大质量损失
    estimated_tokens: int                 # 预估 token 消耗
    confidence: float                     # 路径信心指数 0-1

    @property
    def all_model_ids(self) -> list[str]:
        return [self.primary_model] + [s.model_id for s in self.steps]


# ════════════════════════════════════════════════════════════════
# 默认模型基线（兜底用——当没有学习数据时）
# ════════════════════════════════════════════════════════════════

_DEFAULT_QUALITY: dict[str, dict[str, float]] = {
    # 代码天花板（SWE-Bench 80.2% 超GPT-5.4）
    "kimi-k2.6":           {"coding": 0.96, "analysis": 0.92, "writing": 0.90, "search": 0.78, "conversation": 0.85},
    # V4 正式版 Pro — 2026-07-15 上线, SWEBench 96%, DSpark +85% 加速
    "deepseek-v4-pro":     {"coding": 0.96, "analysis": 0.93, "writing": 0.90, "search": 0.80, "conversation": 0.84},
    # 多模态+Agent基准SOTA
    "qwen3.7-max":         {"coding": 0.93, "analysis": 0.94, "writing": 0.88, "search": 0.85, "conversation": 0.88},
    # 推理天花板（IMO/IOI金牌）— 分析专项保留
    "deepseek-v3.2":       {"coding": 0.92, "analysis": 0.95, "writing": 0.85, "search": 0.76, "conversation": 0.82},
    # 旗舰推理层（旧预览版 — → V4 Pro）
    "deepseek-v4":         {"coding": 0.95, "analysis": 0.90, "writing": 0.88, "search": 0.75, "conversation": 0.80},
    # 轻量路由层（$0.28/M极致性价比）
    "deepseek-v4-flash":   {"coding": 0.87, "analysis": 0.82, "writing": 0.84, "search": 0.78, "conversation": 0.85},
    # 开源最强（多尺寸8B-397B，评估中）
    "qwen3.5-397b":        {"coding": 0.94, "analysis": 0.93, "writing": 0.87, "search": 0.84, "conversation": 0.86},
    # 实用级
    "hunyuan":             {"coding": 0.82, "analysis": 0.85, "writing": 0.83, "search": 0.80, "conversation": 0.78},
    "qwen-multimodal":     {"coding": 0.80, "analysis": 0.82, "writing": 0.78, "search": 0.72, "conversation": 0.75},
    "glm":                 {"coding": 0.78, "analysis": 0.80, "writing": 0.80, "search": 0.75, "conversation": 0.76},
    # 免费fallback层（GLM-4-9B开源免费，图像理解）
    "glm-4-9b":            {"coding": 0.72, "analysis": 0.74, "writing": 0.75, "search": 0.70, "conversation": 0.73},
    # 本地模型
    "gemma-4":             {"coding": 0.72, "analysis": 0.70, "writing": 0.75, "search": 0.68, "conversation": 0.70},
    # 遗留兼容（→ V4 Flash）
    "deepseek-chat":       {"coding": 0.93, "analysis": 0.88, "writing": 0.86, "search": 0.74, "conversation": 0.79},
}

_DEFAULT_COST: dict[str, float] = {
    "deepseek-v3.2":       0.03,     # $0.14/M input — 地板价
    "deepseek-v4":         1.0,      # 基准线（旧预览版）
    "deepseek-v4-pro":     0.90,     # V4 正式版 Pro — 对标 Opus 级, 非高峰更便宜
    "deepseek-v4-flash":   0.28,     # $0.28/M — 极致性价比，夜间低谷再降 60%
    "kimi-k2.6":           0.20,     # $0.95/M input — 性价比甜点
    "qwen3.7-max":         0.50,     # $2.50/M input — 顶配逼近闭源
    "qwen3.5-397b":        0.40,     # 开源最强，API定价中等
    "hunyuan":             0.20,     # 混元性价比
    "qwen-multimodal":     0.15,     # 多模态轻量
    "glm":                 0.15,     # GLM轻量
    "glm-4-9b":            0.0,      # 开源免费 — 零API成本fallback
    "gemma-4":             0.0,      # 本地模型——零 API 成本
    "deepseek-chat":       0.05,     # 旧版 V3，极低价（7/24 停用→V4 Flash）
}

_DEFAULT_REGISTRY: dict[str, str] = {
    "deepseek-v3.2":       "deepseek-chat",       # V3.2 兼容同名API端点
    "deepseek-v4":         "deepseek-chat",       # 旧预览版 → V4 Pro
    "deepseek-v4-pro":     "deepseek-chat",       # V4 正式版 Pro（2026-07-15 GA）
    "deepseek-v4-flash":   "deepseek-chat",       # Flash版兼容同名端点
    "kimi-k2.6":           "moonshot-v1",
    "qwen3.7-max":         "qwen-max-2026-05-20",
    "qwen3.5-397b":        "qwen-3.5-397b",
    "qwen-multimodal":     "qwen-multimodal",
    "gemma-4":             "gemma-4",
    "hunyuan":             "hunyuan-turbos",
    "glm":                 "glm-4-flash",
    "glm-4-9b":            "glm-4-9b",
    "deepseek-chat":       "deepseek-chat",        # 旧 V3（7/24 停用）
}

# 任务类型对模型质量的敏感度（越低越能容忍降级）
_TASK_SENSITIVITY: dict[str, float] = {
    "coding": 0.95,       # 代码几乎不能降级
    "analysis": 0.80,     # 分析可以降级但影响精度
    "writing": 0.55,      # 写作可容忍
    "search": 0.40,       # 搜索对模型要求最低
    "conversation": 0.25, # 闲聊无所谓
}

# 默认的模型注册列表（无配置时的初始模型池）
# v2.0: V4 Pro 正式版加入，deepseek-chat 旧接口标记待移除
_DEFAULT_MODEL_IDS = [
    "kimi-k2.6", "deepseek-v4-pro", "deepseek-v3.2", "qwen3.7-max",
    "deepseek-v4-flash",
    "qwen3.5-397b",
    "hunyuan", "qwen-multimodal",
    "gemma-4", "glm", "glm-4-9b",
    "deepseek-chat",  # 7/24 停用后移除
]


# ════════════════════════════════════════════════════════════════
# 核心引擎
# ════════════════════════════════════════════════════════════════

class DynamicDegradationEngine:
    """动态降级引擎——太极引擎的"四两拨千斤"在降级场景的体现。

    Auto 模式下的核心决策器：
      感知 → 排序 → 生成路径 → 持续学习

    使用方式：
        de = DynamicDegradationEngine()
        de.register_known_models()           # 注入已知模型基线
        path = de.build_degradation_path(
            task_type="coding",
            budget_remaining=25000,
            priority=0.8,
        )
        # → DegradationPath(primary="deepseek-v4", steps=[...])

        # 执行后反馈质量
        de.record_quality("deepseek-v4", "coding", 0.92)
    """

    def __init__(self) -> None:
        self._model_pool: dict[str, ModelCapability] = {}
        self._initialized = False
        # 总执行次数统计（每次质量更新时递增）
        self._total_updates: int = 0

    # ────────────────────────────────────────────────────────────
    # 模型池管理
    # ────────────────────────────────────────────────────────────

    def register_known_models(self) -> None:
        """注入已知模型的默认基线数据。

        在无配置文件、无 API Key 时提供兜底的模型信息。
        后续可以通过 discover_models() 自动扩展。
        """
        if self._initialized:
            return

        for mid in _DEFAULT_MODEL_IDS:
            quality = _DEFAULT_QUALITY.get(mid, {})
            cost = _DEFAULT_COST.get(mid, 0.5)
            registry = _DEFAULT_REGISTRY.get(mid, mid)

            # 判断是否本地模型
            is_local = mid in ("gemma-4",)

            # 判断提供商
            provider = mid.split("-")[0] if "-" in mid else mid
            if mid == "deepseek-chat":
                provider = "deepseek"
            elif mid.startswith("qwen"):
                provider = "qwen"
            elif mid.startswith("kimi"):
                provider = "moonshot"
            elif mid.startswith("glm"):
                provider = "glm"

            self._model_pool[mid] = ModelCapability(
                model_id=mid,
                registry_name=registry,
                display_name=self._display_name(mid),
                provider=provider,
                source="local" if is_local else "api",
                context_limit=self._context_limit(mid),
                quality_scores=dict(quality),
                cost_per_1k_tokens=cost,
                is_local=is_local,
                available=True,
            )

        self._initialized = True
        logger.info("动态降级引擎已注册 %d 个已知模型", len(self._model_pool))

    def _display_name(self, model_id: str) -> str:
        names = {
            "kimi-k2.6": "Kimi K2.6",
            "deepseek-v3.2": "DeepSeek V3.2",
            "qwen3.7-max": "通义千问 3.7 Max",
            "deepseek-v4": "DeepSeek V4",
            "deepseek-v4-flash": "DeepSeek V4 Flash",
            "qwen3.5-397b": "通义千问 3.5-397B",
            "qwen-multimodal": "通义千问（多模态）",
            "gemma-4": "Gemma 4（本地）",
            "hunyuan": "腾讯混元",
            "glm": "智谱 GLM",
            "glm-4-9b": "智谱 GLM-4-9B（免费）",
            "deepseek-chat": "DeepSeek Chat",
        }
        return names.get(model_id, model_id)

    def _context_limit(self, model_id: str) -> int:
        limits = {
            "kimi-k2.6": 256000,
            "deepseek-v3.2": 128000,
            "qwen3.7-max": 1_000_000,        # 业界最长 1M 上下文
            "deepseek-v4": 128000,
            "deepseek-v4-flash": 128000,      # Flash版同上下文窗口
            "qwen3.5-397b": 256000,           # 397B参数级支持256K
            "qwen-multimodal": 64000,
            "gemma-4": 32000,
            "hunyuan": 128000,
            "glm": 128000,
            "glm-4-9b": 128000,               # 9B开源版支持128K
            "deepseek-chat": 128000,
        }
        return limits.get(model_id, 64000)

    def register_model(self, capability: ModelCapability) -> None:
        """手动注册或更新一个模型到模型池。

        用于从配置 / API Key 检测 / Ollama 发现等外部来源注入模型。
        """
        self._model_pool[capability.model_id] = capability
        logger.info("动态模型池已注册: %s (%s)", capability.model_id, capability.provider)

    def get_model(self, model_id: str) -> Optional[ModelCapability]:
        """获取模型能力信息。"""
        return self._model_pool.get(model_id)

    def get_registry_name(self, model_id: str) -> str:
        """获取模型在 ModelRegistry 中的实际名称。"""
        m = self._model_pool.get(model_id)
        return m.registry_name if m else model_id

    def list_available_models(self) -> list[ModelCapability]:
        """列出当前可用的模型（未被禁用）。"""
        return [m for m in self._model_pool.values()
                if m.available and not m.is_disabled()]

    def list_all_models(self) -> list[ModelCapability]:
        """列出所有已知模型（含已禁用）。"""
        return list(self._model_pool.values())

    def get_models_for_task(self, task_type: str) -> list[tuple[str, float, float]]:
        """获取某任务类型上所有可用模型的质量排名。

        Returns:
            [(model_id, quality_score, cost_ratio), ...]
            按质量降序排列
        """
        available = self.list_available_models()
        ranked = []
        for m in available:
            q = m.current_quality(task_type)
            ranked.append((m.model_id, q, m.cost_per_1k_tokens))
        # 质量降序
        ranked.sort(key=lambda x: -x[1])
        return ranked

    # ────────────────────────────────────────────────────────────
    # 动态降级路径生成（核心算法）
    # ────────────────────────────────────────────────────────────

    def build_degradation_path(
        self,
        task_type: str,
        budget_remaining: int,
        priority: float,
        preferred_model: str | None = None,
        max_steps: int = 4,
    ) -> DegradationPath:
        """动态构建降级路径——太极引擎的四两拨千斤。

        Auto 模式核心入口。

        Args:
            task_type: "coding" / "writing" / "analysis" / "search" / "conversation"
            budget_remaining: 剩余 Token 预算
            priority: 用户优先级 0-1
            preferred_model: 可选——优先使用此模型
            max_steps: 降级路径最大步数

        Returns:
            完整的 DegradationPath（含首选 + 降级步骤）
        """
        if not self._initialized:
            self.register_known_models()

        # 1) 获取任务类型的所有可用模型排名
        ranked = self.get_models_for_task(task_type)
        if not ranked:
            # 无可用模型——返回空路径
            return DegradationPath(
                primary_model="",
                steps=[],
                task_type=task_type,
                total_quality_loss=1.0,
                estimated_tokens=5000,
                confidence=0.0,
            )

        # 2) 如果有 preferred_model，尝试将其前置
        if preferred_model:
            preferred = self._model_pool.get(preferred_model)
            if preferred and preferred.available and not preferred.is_disabled():
                # 将 preferred 移到首位
                ranked = [(preferred_model, preferred.current_quality(task_type), preferred.cost_per_1k_tokens)] + \
                         [(mid, q, c) for mid, q, c in ranked if mid != preferred_model]

        # 3) 选首选模型
        primary_id, primary_quality, primary_cost = ranked[0]

        # 4) 检查 budget 约束——如果首选模型太贵，看看有没有更省的选择
        daily_budget = _DAILY_BUDGETS.get(task_type, 20000)
        if budget_remaining <= daily_budget * 0.2 and primary_cost > 0.3:
            # 预算低于 20%——优先选便宜的模型
            affordable = [(mid, q, c) for mid, q, c in ranked
                          if c <= primary_cost * 0.7 or c <= 0.3]
            if affordable:
                # 在 affordable 中选质量最高的
                primary_id, primary_quality, primary_cost = affordable[0]

        # 5) 构建降级步骤（从次优开始逐步降级）
        steps: list[DegradationStep] = []
        sensitivity = _TASK_SENSITIVITY.get(task_type, 0.7)

        for mid, quality, cost in ranked[1:max_steps]:
            # 跳过首选模型自己
            if mid == primary_id:
                continue

            quality_loss = max(0.0, primary_quality - quality)
            cost_ratio = cost / max(primary_cost, 0.01) if primary_cost > 0 else 1.0

            # 生成降级原因
            loss_pct = f"{quality_loss:.1%}"
            if quality_loss < 0.05:
                reason = f"平替——质量接近（损失 {loss_pct}）"
            elif quality_loss < 0.15:
                reason = f"轻微降级（质量损失 {loss_pct}）"
            elif quality_loss < 0.25:
                reason = f"中等级降级（质量损失 {loss_pct}）"
            else:
                reason = f"兜底降级（质量损失 {loss_pct}）"

            # 成本说明
            if cost_ratio < 0.5:
                reason += "，成本更低"
            elif cost_ratio > 1.5:
                reason += "，成本更高"

            steps.append(DegradationStep(
                model_id=mid,
                quality_loss=round(quality_loss, 3),
                cost_ratio=round(cost_ratio, 2),
                reason=reason,
            ))

        # 6) 估算 token 消耗
        estimated = self._estimate_tokens(task_type, budget_remaining)

        # 7) 计算信心指数
        # total_loss = max(首选模型与理想的差距, 降级路径的最大质量损失)
        gap_to_ideal = 1.0 - primary_quality
        step_losses = [s.quality_loss for s in steps]
        total_loss = max([gap_to_ideal] + step_losses) if step_losses else gap_to_ideal
        confidence = max(0.1, 1.0 - total_loss * sensitivity)
        if len(ranked) <= 1:
            confidence *= 0.5  # 只有单一选项时降低信心

        return DegradationPath(
            primary_model=primary_id,
            steps=steps,
            task_type=task_type,
            total_quality_loss=total_loss,
            estimated_tokens=estimated,
            confidence=round(confidence, 3),
        )

    def _estimate_tokens(self, task_type: str, budget_remaining: int) -> int:
        """根据任务类型和剩余预算估算 token 消耗。"""
        task_avg = _DEFAULT_TOKENS.get(task_type, 10000)
        return min(budget_remaining, task_avg)

    # ────────────────────────────────────────────────────────────
    # 质量学习
    # ────────────────────────────────────────────────────────────

    def record_quality(
        self,
        model_id: str,
        task_type: str,
        quality_score: float,
        success: bool = True,
    ) -> None:
        """记录一次模型执行质量——持续学习模型在各任务上的真实表现。

        Args:
            model_id: 模型标识
            task_type: 任务类型
            quality_score: 质量评分 0-1（通常来自 gate_score）
            success: 是否执行成功
        """
        model = self._model_pool.get(model_id)
        if not model:
            return

        if success:
            model.mark_success()
            model.update_quality(task_type, quality_score)
        else:
            model.mark_failure()
            # 失败时也更新质量（轻微降低）
            model.update_quality(task_type, quality_score * 0.5)

        self._total_updates += 1

    def record_execution(
        self,
        model_id: str,
        task_type: str,
        tokens_used: int,
        gate_score: float,
        success: bool,
        user_feedback: str = "",
    ) -> None:
        """完整的执行记录——质量学习 + 失败追踪。

        供 ChatIntegration.post_chat_record() 调用。
        """
        # 基本质量记录
        quality = gate_score if success else gate_score * 0.3
        self.record_quality(model_id, task_type, quality, success)

        # 用户反馈修正（如果有）
        if user_feedback == "positive":
            model = self._model_pool.get(model_id)
            if model:
                q = model.current_quality(task_type)
                model.update_quality(task_type, min(1.0, q + 0.05))
        elif user_feedback == "negative":
            model = self._model_pool.get(model_id)
            if model:
                q = model.current_quality(task_type)
                model.update_quality(task_type, max(0.1, q - 0.1))

    # ────────────────────────────────────────────────────────────
    # 降级执行（Auto 模式核心）
    # ────────────────────────────────────────────────────────────

    def degrade(
        self,
        task_type: str,
        budget_remaining: int,
        priority: float,
        preferred_model: str | None = None,
        current_model_failed: str | None = None,
    ) -> tuple[str, str, DegradationPath]:
        """Auto 模式降级执行。

        如果传入了 current_model_failed，表示当前模型调用失败，
        需要立即降级到下一个可用模型。

        Returns:
            (next_model_id, reason, full_path)
        """
        path = self.build_degradation_path(
            task_type=task_type,
            budget_remaining=budget_remaining,
            priority=priority,
            preferred_model=preferred_model,
        )

        if not path.primary_model:
            return ("", "无可用的模型", path)

        # 如果指定了失败的模型，找到降级路径中的下一个
        if current_model_failed:
            all_ids = path.all_model_ids
            try:
                failed_idx = all_ids.index(current_model_failed)
                if failed_idx + 1 < len(all_ids):
                    next_id = all_ids[failed_idx + 1]
                    next_step = path.steps[failed_idx] if failed_idx < len(path.steps) else None
                    reason = f"模型 {current_model_failed} 失败，"
                    reason += next_step.reason if next_step else "自动降级到下一可用模型"
                    return (next_id, reason, path)
                else:
                    return ("", "所有模型均尝试失败", path)
            except ValueError:
                pass  # 不在路径中，退回首选

        return (path.primary_model, "Auto 模式默认推荐", path)

    # ────────────────────────────────────────────────────────────
    # 统计 & 输出
    # ────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """获取降级引擎的统计信息。"""
        alive = sum(1 for m in self._model_pool.values() if m.available and not m.is_disabled())
        disabled = sum(1 for m in self._model_pool.values() if m.is_disabled())
        return {
            "total_models": len(self._model_pool),
            "available_models": alive,
            "disabled_models": disabled,
            "total_updates": self._total_updates,
            "models": [
                {
                    "id": m.model_id,
                    "provider": m.provider,
                    "source": m.source,
                    "available": m.available,
                    "disabled": m.is_disabled(),
                    "fail_count": m.fail_count,
                    "context_limit": m.context_limit,
                    "scores": dict(m.quality_scores),
                    "cost": m.cost_per_1k_tokens,
                }
                for m in self._model_pool.values()
            ],
        }


# ════════════════════════════════════════════════════════════════
# 默认常量
# ════════════════════════════════════════════════════════════════

_DAILY_BUDGETS: dict[str, int] = {
    "coding": 50000,
    "analysis": 40000,
    "writing": 30000,
    "search": 15000,
    "conversation": 10000,
}

_DEFAULT_TOKENS: dict[str, int] = {
    "coding": 15000,
    "analysis": 12000,
    "writing": 10000,
    "search": 5000,
    "conversation": 3000,
}


# ════════════════════════════════════════════════════════════════
# 平台唯一实例
# ════════════════════════════════════════════════════════════════

dynamic_degradation = DynamicDegradationEngine()
