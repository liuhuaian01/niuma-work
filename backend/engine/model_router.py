"""
模型路由器 · 三维路由引擎 (ModelRouter)

三维决策：
  维度1: 任务类型 (creative/coding/analysis/chat/summary)
  维度2: 成本约束 (budget_limit, cost_per_token)
  维度3: 质量要求 (latency_ms, quality_threshold)

路由策略：
  - 简单任务 → 便宜模型 (GLM-4-Flash / 混元TurboS)
  - 创作任务 → 高质量模型 (Kimi K2.6 / DeepSeek)
  - 代码任务 → 代码优化模型 (DeepSeek / Kimi)
  - Token 预算<10% → 自动切换最便宜模型
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import asyncio
import logging
import os
from pathlib import Path

from engine.smart_allocator import TaskType
from engine.allocator_repository import AllocatorRepository
from engine.token_budget import token_budget

logger = logging.getLogger(__name__)


# ============================================================
# 任务分类
# ============================================================

class TaskCategory(Enum):
    CREATIVE = "creative"     # → TaskType.WRITING
    CODING = "coding"         # → TaskType.CODING
    ANALYSIS = "analysis"     # → TaskType.ANALYSIS
    CHAT = "chat"             # → TaskType.CONVERSATION
    SUMMARY = "summary"       # → TaskType.WRITING

    @classmethod
    def from_string(cls, s: str) -> "TaskCategory":
        try:
            return cls(s.lower())
        except ValueError:
            return cls.CHAT


# 任务分类 → TaskType 映射 (用于读取 smart_allocator 的枚举)
CATEGORY_TO_TASK_TYPE: dict[TaskCategory, TaskType] = {
    TaskCategory.CREATIVE: TaskType.WRITING,
    TaskCategory.CODING: TaskType.CODING,
    TaskCategory.ANALYSIS: TaskType.ANALYSIS,
    TaskCategory.CHAT: TaskType.CONVERSATION,
    TaskCategory.SUMMARY: TaskType.WRITING,
}


# ============================================================
# 模型注册表
# ============================================================

@dataclass
class ModelInfo:
    """模型性能画像"""
    id: str
    name: str
    cost_per_1k_tokens: float   # 每千 token 成本 (美元)
    quality_score: float         # 综合质量评分 0-1
    avg_latency_ms: int          # 平均延迟 (毫秒)
    best_for: list[str]          # 擅长的任务类型
    provider: str = ""           # 提供商


MODEL_REGISTRY: dict[str, ModelInfo] = {
    # ===== DeepSeek V4 正式版（2026-07-15 已上线）=====
    "deepseek-v4-pro": ModelInfo(
        id="deepseek-v4-pro", name="DeepSeek V4 Pro (正式版)",
        cost_per_1k_tokens=0.0042, quality_score=0.94,       # 正式版质量: SWEBench 96%, 非高峰 $3/$6
        avg_latency_ms=500, best_for=["creative", "coding", "analysis", "summary"],
        provider="DeepSeek",
    ),
    "deepseek-v4-flash": ModelInfo(
        id="deepseek-v4-flash", name="DeepSeek V4 Flash",
        cost_per_1k_tokens=0.0014, quality_score=0.82,       # 非高峰 $1/$2, DSpark +85% 加速
        avg_latency_ms=300, best_for=["chat", "summary", "coding"],
        provider="DeepSeek",
    ),

    # ===== 创意/写作 =====
    "kimi-k2.6": ModelInfo(
        id="kimi-k2.6", name="Kimi K2.6",
        cost_per_1k_tokens=0.005, quality_score=0.92,
        avg_latency_ms=800, best_for=["creative", "coding"],
        provider="月之暗面",
    ),
    # "deepseek-v4": 旧预览版 — 已合并到 deepseek-v4-pro 正式版, 保留兼容
    "deepseek-v4": ModelInfo(
        id="deepseek-v4", name="DeepSeek V4 (旧预览, →V4 Pro)",
        cost_per_1k_tokens=0.003, quality_score=0.90,
        avg_latency_ms=600, best_for=["creative", "coding", "analysis"],
        provider="DeepSeek",
    ),

    # ===== 代码 =====
    "deepseek-r1": ModelInfo(
        id="deepseek-r1", name="DeepSeek R1",
        cost_per_1k_tokens=0.008, quality_score=0.95,
        avg_latency_ms=1200, best_for=["coding", "analysis"],
        provider="DeepSeek",
    ),
    "qwen-coder": ModelInfo(
        id="qwen-coder", name="Qwen2.5-Coder",
        cost_per_1k_tokens=0.0, quality_score=0.85,
        avg_latency_ms=400, best_for=["coding"],
        provider="阿里巴巴（本地）",
    ),

    # ===== 聊天/日常 =====
    "glm-4-flash": ModelInfo(
        id="glm-4-flash", name="GLM-4-Flash",
        cost_per_1k_tokens=0.0001, quality_score=0.65,
        avg_latency_ms=200, best_for=["chat", "summary"],
        provider="智谱 AI",
    ),
    "hunyuan-turbos": ModelInfo(
        id="hunyuan-turbos", name="混元 TurboS",
        cost_per_1k_tokens=0.0005, quality_score=0.70,
        avg_latency_ms=300, best_for=["chat", "summary", "creative"],
        provider="腾讯",
    ),
    "gemma-4": ModelInfo(
        id="gemma-4", name="Gemma-4",
        cost_per_1k_tokens=0.0, quality_score=0.75,
        avg_latency_ms=350, best_for=["chat", "summary"],
        provider="Google（本地）",
    ),

    # ===== 分析/推理 =====
    "hunyuan": ModelInfo(
        id="hunyuan", name="混元",
        cost_per_1k_tokens=0.002, quality_score=0.82,
        avg_latency_ms=500, best_for=["analysis", "creative"],
        provider="腾讯",
    ),
    "glm-4": ModelInfo(
        id="glm-4", name="GLM-4",
        cost_per_1k_tokens=0.001, quality_score=0.78,
        avg_latency_ms=450, best_for=["analysis", "creative", "chat"],
        provider="智谱 AI",
    ),
}

# 预算紧急状态阈值 —— vLLM Micro-Agent 蒸馏：三级 Confidence Looper
# 替代原来的一刀切 EMERGENCY_BUDGET_RATIO = 0.10
BUDGET_TIER_ESCALATION = 0.30    # <30%: 先试便宜模型，置信度不够再升级
BUDGET_TIER_NO_ESCALATION = 0.15  # <15%: 只试一次，不升级
BUDGET_TIER_EMERGENCY = 0.05     # <5%:  预算见底，最小模型保底

# Confidence Looper 升级阈值（semantic_grader 分数 0-1）
CONFIDENCE_ESCALATE_THRESHOLD = 0.7

# 三级模型池 — v2.0: V4 Pro 正式版加入中档
MODEL_TIER_BUDGET = ["deepseek-v4-flash", "glm-4-flash", "gemma-4"]    # 预算档
MODEL_TIER_MID = ["deepseek-v4-pro", "hunyuan-turbos", "glm-4"]           # 中档 (V4 Pro 正式版)
MODEL_TIER_TINY = ["glm-4-flash"]                                        # 紧急档


# ============================================================
# Recipe 加载（vLLM Micro-Agent 蒸馏——声明式配置）
# ============================================================

# Recipe 文件搜索路径
RECIPE_SEARCH_PATHS = [
    Path(__file__).parent / "recipes",            # engine/recipes/
    Path("recipes"),                               # 当前工作目录
]

# 已加载的 Recipe（全局缓存）
_loaded_recipe: dict | None = None


def load_recipe(recipe_name: str = "default") -> dict:
    """从 YAML 文件加载路由 Recipe 配置。

    仅在首次调用时加载并缓存。后续调用返回缓存。
    如果 PyYAML 不可用，返回空 dict（代码中的硬编码常量兜底）。

    vLLM 蒸馏：Recipe 系统让路由策略不需要改代码即可调整。
    """
    global _loaded_recipe
    if _loaded_recipe is not None:
        return _loaded_recipe

    # 尝试导入 yaml
    try:
        import yaml
    except ImportError:
        logger.debug("PyYAML 未安装，Recipe 使用代码硬编码默认值")
        _loaded_recipe = {}
        return _loaded_recipe

    # 搜索 Recipe 文件
    for search_path in RECIPE_SEARCH_PATHS:
        recipe_file = search_path / f"{recipe_name}.yaml"
        if recipe_file.exists():
            try:
                with open(recipe_file, "r", encoding="utf-8") as f:
                    _loaded_recipe = yaml.safe_load(f) or {}
                logger.info("Recipe 已加载: %s", recipe_file)
                return _loaded_recipe
            except Exception as e:
                logger.warning("Recipe 文件加载失败: %s → %s", recipe_file, e)

    logger.debug("未找到 Recipe 文件 '%s.yaml'，使用默认值", recipe_name)
    _loaded_recipe = {}
    return _loaded_recipe


def get_recipe_for_task(task_category: str) -> dict:
    """获取特定任务类型的 Recipe 配置。

    合并全局配置 + 任务特定配置。
    如果 Recipe 不可用，返回空 dict（所有参数由代码管理）。
    """
    recipe = load_recipe()
    if not recipe:
        return {}

    task_recipe = recipe.get("recipes", {}).get(task_category, {})
    global_config = recipe.get("global", {})

    # 合并：任务配置覆盖全局配置
    merged = dict(global_config)
    merged.update(task_recipe)
    return merged

# 三维评分权重 (可在配置中调整)
SCORE_WEIGHTS = {
    "task_fit": 0.40,     # 任务匹配度
    "cost_efficiency": 0.35,  # 成本效率 (对齐 allocator 的 ROI_WEIGHT)
    "quality_match": 0.25,    # 质量匹配 (对齐 allocator 的 BUDGET_WEIGHT)
}

# 各任务类型的高质量模型和廉价模型
HIGH_QUALITY_MODELS = {
    TaskCategory.CREATIVE: ["kimi-k2.6", "deepseek-v4-pro"],
    TaskCategory.CODING: ["deepseek-v4-pro", "deepseek-r1", "kimi-k2.6"],
    TaskCategory.ANALYSIS: ["deepseek-r1", "deepseek-v4-pro"],
    TaskCategory.CHAT: ["glm-4", "hunyuan-turbos"],
    TaskCategory.SUMMARY: ["deepseek-v4-pro", "hunyuan-turbos"],
}

BUDGET_MODELS = {
    TaskCategory.CREATIVE: ["deepseek-v4-flash", "hunyuan-turbos", "glm-4-flash"],
    TaskCategory.CODING: ["deepseek-v4-flash", "qwen-coder", "glm-4-flash"],
    TaskCategory.ANALYSIS: ["deepseek-v4-flash", "glm-4", "hunyuan-turbos"],
    TaskCategory.CHAT: ["deepseek-v4-flash", "glm-4-flash", "gemma-4"],
    TaskCategory.SUMMARY: ["deepseek-v4-flash", "glm-4-flash", "gemma-4"],
}

# 紧急状态下（预算<10%）的兜底模型
EMERGENCY_MODELS = ["glm-4-flash", "gemma-4"]


# ============================================================
# Task-Shape 投影 —— vLLM Micro-Agent 蒸馏
# ============================================================
# 在派给 worker 之前提取 prompt 的元数据信号。
# 不调 LLM，纯分析 prompt 本身的结构特征。
# 信号用于影响模型选择和 Recipe 匹配。

@dataclass
class TaskShape:
    """prompt 元数据——路由前提取的形状信号。"""
    prompt_length: int              # 字符数或估算 token 数
    has_output_schema: bool         # 是否要求结构化输出（JSON/YAML/Schema）
    reasoning_depth: float          # 推理复杂度估算 0-1
    is_sensitive: bool              # 是否含敏感信息
    estimated_complexity: float     # 综合复杂度 0-1


def extract_task_shape(content: str, task_category: str = "") -> TaskShape:
    """从 prompt 内容提取任务形状信号。

    纯规则引擎，零 LLM 调用。vLLM 的信号提取层蒸馏。

    Args:
        content: 用户消息全文
        task_category: 已识别的任务类别（可选，辅助判断）

    Returns:
        TaskShape 包含 prompt_length / has_output_schema / reasoning_depth 等信号
    """
    c = content.lower() if content else ""
    prompt_len = len(content) if content else 0

    # ---- has_output_schema：是否要求结构化输出 ----
    schema_keywords = [
        "json", "yaml", "schema", "格式", "表格", "模板",
        "{", "字段", "key", "value", "array", "dict",
        "返回格式", "输出格式", "结构",
    ]
    has_schema = any(k in c for k in schema_keywords)

    # ---- reasoning_depth：推理复杂度 0-1 ----
    depth_signals = 0.0
    deep_keywords = [
        "分析", "对比", "架构", "系统设计", "重构", "推理", "证明",
        "多步骤", "复杂", "深度", "评估", "诊断", "优化策略",
        "trade-off", "权衡", "根因", "逻辑",
    ]
    moderate_keywords = [
        "代码", "修复", "实现", "检查", "审查", "解释", "方案",
        "编写", "生成", "转换",
    ]

    deep_count = sum(1 for k in deep_keywords if k in c)
    moderate_count = sum(1 for k in moderate_keywords if k in c)
    depth_signals = min(1.0, deep_count * 0.25 + moderate_count * 0.10)

    # 长 prompt 通常意味着更多上下文 → 推理负担更重
    if prompt_len > 500:
        depth_signals = min(1.0, depth_signals + 0.15)
    if prompt_len > 1000:
        depth_signals = min(1.0, depth_signals + 0.15)

    # 特定任务类型自带推理深度
    type_depth_map = {
        "analysis": 0.7,
        "coding": 0.5,
        "creative": 0.4,
        "summary": 0.2,
        "chat": 0.1,
    }
    base_depth = type_depth_map.get(task_category, 0.2)
    reasoning_depth = max(base_depth, depth_signals)

    # ---- is_sensitive：是否含敏感信息 ----
    sensitive_keywords = [
        "密码", "密钥", "token", "secret", "私密", "隐私",
        "机密", "内部", "api_key", "password",
    ]
    is_sensitive = any(k in c for k in sensitive_keywords)

    # ---- estimated_complexity：综合复杂度 ----
    complexity = 0.0
    if reasoning_depth > 0.6:
        complexity += 0.4
    if has_schema:
        complexity += 0.15
    if prompt_len > 500:
        complexity += 0.15
    if prompt_len > 1000:
        complexity += 0.15
    if task_category in ("analysis", "coding"):
        complexity += 0.15
    complexity = min(1.0, complexity)

    return TaskShape(
        prompt_length=prompt_len,
        has_output_schema=has_schema,
        reasoning_depth=round(reasoning_depth, 2),
        is_sensitive=is_sensitive,
        estimated_complexity=round(complexity, 2),
    )


# ============================================================
# 路由输入/输出
# ============================================================

@dataclass
class RouteInput:
    """路由请求"""
    task_type: str                    # creative|coding|analysis|chat|summary
    content: str = ""                 # 用户消息全文（用于 task-shape 提取）
    budget_limit: int = 50000         # Token 预算上限
    cost_per_token: float = 0.0       # 用户偏好成本上限（每 token），0=不限制
    latency_ms: int = 5000            # 用户偏好最大延迟，0=不限制
    quality_threshold: float = 0.0    # 用户偏好最低质量，0=不限制
    agent_id: str = "default"         # 代理 ID（用于读取 token_budget）


@dataclass
class RouteResult:
    """路由结果"""
    model_id: str                     # 推荐模型 ID
    model_name: str                   # 推荐模型名称
    task_category: str                # 任务分类
    confidence: float                 # 置信度 0-1
    reason: str                       # 推荐理由
    estimated_tokens: int             # 预估 token 消耗
    estimated_cost: float             # 预估成本 (美元)
    is_emergency: bool = False        # 是否为紧急兜底
    alternatives: list[str] = field(default_factory=list)  # 备选模型


# ============================================================
# 模型路由器
# ============================================================

class ModelRouter:
    """三维路由引擎。

    使用方式:
        router = ModelRouter()
        result = router.route(RouteInput(task_type="creative", budget_limit=50000))
        # → RouteResult(model_id="kimi-k2.6", confidence=0.85, ...)

        result = router.route(RouteInput(task_type="chat", budget_limit=5000, quality_threshold=0.8))
        # → RouteResult(model_id="glm-4-flash", confidence=0.95, ...)
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path
        self._repo: Optional[AllocatorRepository] = None
        self._routing_stats: dict[str, dict] = {}  # task_category → {total, models: {model_id: count}}
        self._decision_count: int = 0

        # 初始化各任务类型统计
        for cat in TaskCategory:
            self._routing_stats[cat.value] = {"total": 0, "models": {}}

        if db_path:
            self._init_repo_sync()

    def _init_repo_sync(self) -> None:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._async_init())
        except RuntimeError:
            asyncio.run(self._async_init())

    async def _async_init(self) -> None:
        """异步初始化 Repository"""
        if self._repo is None:
            self._repo = AllocatorRepository()
            await self._repo.init_tables()
            await self._init_route_table()

    async def _init_route_table(self) -> None:
        """初始化路由决策记录表"""
        if self._repo:
            await self._repo.execute("""
                CREATE TABLE IF NOT EXISTS route_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_category TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    reason TEXT DEFAULT '',
                    estimated_tokens INTEGER DEFAULT 0,
                    estimated_cost REAL DEFAULT 0.0,
                    is_emergency INTEGER DEFAULT 0,
                    alternatives TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)

    # ---- 路由核心算法 ----

    def route(self, input_data: RouteInput) -> RouteResult:
        """三维路由决策。

        步骤:
          1. 解析任务分类
          2. 提取 Task-Shape 信号（prompt 元数据）
          3. 检查预算紧急状态（三级 Confidence Looper）
          4. 按三维度+Shape 打分
          5. 选出最优模型
          6. 记录决策并返回
        """
        # Step 1: 解析任务分类
        task_category = TaskCategory.from_string(input_data.task_type)
        task_type = CATEGORY_TO_TASK_TYPE[task_category]

        # Step 1.5: 提取 Task-Shape（vLLM Micro-Agent 蒸馏——信号提取层）
        task_shape = extract_task_shape(
            content=input_data.content,
            task_category=task_category.value,
        )

        # Step 2: 检查预算紧急状态（三级 Confidence Looper——vLLM 蒸馏）
        budget_status = token_budget.check(input_data.agent_id)
        remaining_ratio = budget_status.remaining / budget_status.daily_budget if budget_status.daily_budget > 0 else 0

        if remaining_ratio < BUDGET_TIER_EMERGENCY:
            return self._route_emergency(input_data, task_category, task_type, task_shape)
        elif remaining_ratio < BUDGET_TIER_NO_ESCALATION:
            return self._route_no_escalation(input_data, task_category, task_type, task_shape)
        elif remaining_ratio < BUDGET_TIER_ESCALATION:
            return self._route_with_escalation(input_data, task_category, task_type, task_shape)

        # Step 3: 按三维度+Shape 打分
        scored = self._score_models(task_category, input_data, task_shape)

        if not scored:
            # 无可用模型 → 兜底
            return self._route_emergency(input_data, task_category, task_type, task_shape)

        # Step 4: 选出最优
        best_score, best_id, alternatives = scored[0]
        model = MODEL_REGISTRY[best_id]

        # 计算预估——Shape 高复杂度 → 调高 token 预估
        estimated_tokens = self._estimate_tokens(task_category, input_data.budget_limit)
        if task_shape.estimated_complexity > 0.6:
            estimated_tokens = min(int(estimated_tokens * 1.3), input_data.budget_limit)

        estimated_cost = model.cost_per_1k_tokens * (estimated_tokens / 1000)

        result = RouteResult(
            model_id=model.id,
            model_name=model.name,
            task_category=task_category.value,
            confidence=round(best_score, 3),
            reason=self._build_reason(model, task_category, best_score, remaining_ratio, task_shape),
            estimated_tokens=estimated_tokens,
            estimated_cost=round(estimated_cost, 6),
            alternatives=alternatives[:3],  # 最多3个备选
        )

        # Step 5: 记录决策
        self._record_decision(result)

        return result

    # ---- 三级 Confidence Looper（vLLM Micro-Agent 蒸馏） ----

    def _route_with_escalation(
        self, input_data: RouteInput, task_category: TaskCategory, task_type: TaskType,
        task_shape: Optional[TaskShape] = None,
    ) -> RouteResult:
        """预算紧张但还有余量（<30%）——先试便宜模型，置信度不够再升级。
        
        vLLM Confidence Looper 蒸馏：顺序升级循环。
        """
        budget_status = token_budget.check(input_data.agent_id)
        remaining_ratio = budget_status.remaining / budget_status.daily_budget if budget_status.daily_budget > 0 else 0

        # 找适合此任务的便宜模型
        budget_candidates = [m for m in MODEL_TIER_BUDGET
                             if m in MODEL_REGISTRY and task_category.value in MODEL_REGISTRY[m].best_for]
        mid_candidates = [m for m in MODEL_TIER_MID
                          if m in MODEL_REGISTRY and task_category.value in MODEL_REGISTRY[m].best_for]

        if not budget_candidates:
            return self._route_no_escalation(input_data, task_category, task_type)

        first_model_id = budget_candidates[0]
        first_model = MODEL_REGISTRY[first_model_id]
        upgrade_model_id = mid_candidates[0] if mid_candidates else budget_candidates[-1]

        estimated_tokens = self._estimate_tokens(task_category, input_data.budget_limit)
        estimated_cost = first_model.cost_per_1k_tokens * (estimated_tokens / 1000)

        result = RouteResult(
            model_id=first_model.id,
            model_name=first_model.name,
            task_category=task_category.value,
            confidence=0.60,
            reason=(
                f"预算模式（剩余{remaining_ratio:.0%}）→ 先试 {first_model.name}"
                f"，置信度不足时将升级到 {MODEL_REGISTRY[upgrade_model_id].name}"
            ),
            estimated_tokens=estimated_tokens,
            estimated_cost=round(estimated_cost, 6),
            is_emergency=False,
            alternatives=[upgrade_model_id] + [m for m in mid_candidates if m != upgrade_model_id],
        )
        self._record_decision(result)
        return result

    def _route_no_escalation(
        self, input_data: RouteInput, task_category: TaskCategory, task_type: TaskType,
        task_shape: Optional[TaskShape] = None,
    ) -> RouteResult:
        """预算逼近底线（<15%）——只试一次便宜模型，不升级。"""
        budget_status = token_budget.check(input_data.agent_id)
        remaining_ratio = budget_status.remaining / budget_status.daily_budget if budget_status.daily_budget > 0 else 0

        candidates = [m for m in MODEL_TIER_BUDGET
                      if m in MODEL_REGISTRY and task_category.value in MODEL_REGISTRY[m].best_for]

        if not candidates:
            return self._route_emergency(input_data, task_category, task_type, task_shape)

        model = MODEL_REGISTRY[candidates[0]]
        estimated_tokens = min(self._estimate_tokens(task_category, input_data.budget_limit), 4000)
        estimated_cost = model.cost_per_1k_tokens * (estimated_tokens / 1000)

        result = RouteResult(
            model_id=model.id,
            model_name=model.name,
            task_category=task_category.value,
            confidence=0.80,
            reason=f"预算紧张（剩余{remaining_ratio:.0%}），无升级机会，使用 {model.name}",
            estimated_tokens=estimated_tokens,
            estimated_cost=round(estimated_cost, 6),
            is_emergency=True,
            alternatives=candidates[1:3],
        )
        self._record_decision(result)
        return result

    def _route_emergency(
        self, input_data: RouteInput, task_category: TaskCategory, task_type: TaskType,
        task_shape: Optional[TaskShape] = None,
    ) -> RouteResult:
        """预算见底（<5%）——最小模型保底，不再尝试任何升级。"""
        budget_status = token_budget.check(input_data.agent_id)
        remaining_ratio = budget_status.remaining / budget_status.daily_budget if budget_status.daily_budget > 0 else 0

        for mid in MODEL_TIER_TINY:
            if mid in MODEL_REGISTRY:
                model = MODEL_REGISTRY[mid]
                estimated_tokens = 2000
                estimated_cost = model.cost_per_1k_tokens * (estimated_tokens / 1000)

                result = RouteResult(
                    model_id=model.id,
                    model_name=model.name,
                    task_category=task_category.value,
                    confidence=0.95,
                    reason=f"预算见底（剩余{remaining_ratio:.0%}），最小模型 {model.name} 保底",
                    estimated_tokens=estimated_tokens,
                    estimated_cost=round(estimated_cost, 6),
                    is_emergency=True,
                    alternatives=[],
                )
                self._record_decision(result)
                return result

        # 如果 TINY 都不在注册表，用最便宜可用的
        cheapest = min(
            MODEL_REGISTRY.values(),
            key=lambda m: m.cost_per_1k_tokens,
        )
        estimated_tokens = 2000
        result = RouteResult(
            model_id=cheapest.id,
            model_name=cheapest.name,
            task_category=task_category.value,
            confidence=0.40,
            reason=f"预算见底，无合适模型，强制用最便宜 {cheapest.name}",
            estimated_tokens=estimated_tokens,
            estimated_cost=round(cheapest.cost_per_1k_tokens * (estimated_tokens / 1000), 6),
            is_emergency=True,
        )
        self._record_decision(result)
        return result

    def _score_models(
        self, task_category: TaskCategory, input_data: RouteInput,
        task_shape: Optional[TaskShape] = None,
    ) -> list[tuple[float, str, list[str]]]:
        """按三维度+TaskShape 对所有适配模型打分排序。

        维度1: 任务匹配度 (task_fit) — 模型是否擅长此任务
        维度2: 成本效率 (cost_efficiency) — 预算约束下的性价比
        维度3: 质量匹配 (quality_match) — 是否满足质量要求
        维度4: 形状适配 (shape_fit) — Task-Shape 信号对模型选择的微调（vLLM 蒸馏）

        Returns:
            [(score, model_id, [alternatives]), ...] 按分数降序
        """
        scores: list[tuple[float, str]] = []

        for mid, model in MODEL_REGISTRY.items():
            # 过滤：模型需要匹配任务类别
            if task_category.value not in model.best_for:
                continue

            # 用户指定了延迟上限 → 过滤
            if input_data.latency_ms > 0 and model.avg_latency_ms > input_data.latency_ms:
                continue

            # 用户指定了每token成本上限 → 过滤
            cost_per_token = model.cost_per_1k_tokens / 1000
            if input_data.cost_per_token > 0 and cost_per_token > input_data.cost_per_token:
                continue

            # 用户指定了质量下限 → 过滤
            if input_data.quality_threshold > 0 and model.quality_score < input_data.quality_threshold:
                continue

            # === 维度1: 任务匹配度 ===
            # 高质量模型列表中的排位越高，分数越高
            high_quality_list = HIGH_QUALITY_MODELS.get(task_category, [])
            budget_list = BUDGET_MODELS.get(task_category, [])

            if mid in high_quality_list:
                task_fit = 1.0 if mid == high_quality_list[0] else 0.8
            elif mid in budget_list:
                task_fit = 0.6
            else:
                task_fit = 0.4

            # === 维度2: 成本效率 ===
            if model.cost_per_1k_tokens > 0 and input_data.budget_limit > 0:
                max_tokens_affordable = input_data.budget_limit / (model.cost_per_1k_tokens / 1000)
                cost_efficiency = min(1.0, max_tokens_affordable / 100000)  # 归一化到10万 token
            elif model.cost_per_1k_tokens == 0:
                cost_efficiency = 1.0  # 免费模型成本效率满分
            else:
                cost_efficiency = 0.5

            # === 维度3: 质量匹配 ===
            if input_data.quality_threshold > 0:
                quality_match = min(1.0, model.quality_score / input_data.quality_threshold)
            else:
                quality_match = model.quality_score

            # === 维度4: 形状适配（vLLM Task-Shape 蒸馏）===
            # 高推理深度 → 偏好 reasoning/coding 强模型
            # 结构化输出要求 → 偏好指令遵循强的模型（DeepSeek/Kimi）
            # 敏感信息 → 偏好本地模型（qwen-coder/gemma-4）
            shape_fit = 1.0
            if task_shape is not None:
                if task_shape.reasoning_depth > 0.5:
                    # 复杂推理 → 加分给高质量模型，减分给便宜模型
                    if model.quality_score > 0.85:
                        shape_fit = 1.15  # 推理型模型加分
                    elif model.quality_score < 0.7:
                        shape_fit = 0.85  # 低质量模型减分
                if task_shape.has_output_schema:
                    # 结构化输出 → 偏好指令遵循能力强的
                    if mid in ("deepseek-v4-pro", "deepseek-v4-flash", "kimi-k2.6", "deepseek-r1"):
                        shape_fit *= 1.10
                if task_shape.is_sensitive:
                    # 敏感信息 → 大幅偏好本地模型
                    if model.cost_per_1k_tokens == 0:
                        shape_fit *= 1.30
                    elif model.provider in ("DeepSeek", "阿里巴巴"):
                        shape_fit *= 0.85  # 云端模型降权

            # 综合评分（动态权重——Shape 信号影响 task_fit 权重）
            shape_fit = max(0.5, min(1.5, shape_fit))
            score = (
                task_fit * SCORE_WEIGHTS["task_fit"] * shape_fit
                + cost_efficiency * SCORE_WEIGHTS["cost_efficiency"]
                + quality_match * SCORE_WEIGHTS["quality_match"]
            )

            scores.append((score, mid))

        # 按分数降序
        scores.sort(key=lambda x: x[0], reverse=True)

        # 转为带备选列表的格式
        result = []
        for i, (score, mid) in enumerate(scores):
            alternatives = [m[1] for m in scores[i + 1:i + 4]] if i == 0 else []
            result.append((score, mid, alternatives))

        return result

    def _estimate_tokens(self, task_category: TaskCategory, budget_limit: int) -> int:
        """根据任务类型估算 token 消耗。"""
        estimates = {
            TaskCategory.CREATIVE: min(budget_limit, 30000),
            TaskCategory.CODING: min(budget_limit, 25000),
            TaskCategory.ANALYSIS: min(budget_limit, 35000),
            TaskCategory.CHAT: min(budget_limit, 5000),
            TaskCategory.SUMMARY: min(budget_limit, 15000),
        }
        return estimates.get(task_category, min(budget_limit, 20000))

    def _build_reason(
        self, model: ModelInfo, task_category: TaskCategory, score: float, budget_ratio: float,
        task_shape: Optional[TaskShape] = None,
    ) -> str:
        """构建推荐理由。"""
        parts = [f"三维路由推荐 {model.name}（{model.provider}）"]

        if task_category == TaskCategory.CREATIVE and model.id in ("kimi-k2.6", "deepseek-v4-pro", "deepseek-v4"):
            parts.append("创作任务→高质量模型")
        elif task_category == TaskCategory.CODING and model.id in ("deepseek-v4-pro", "deepseek-r1", "qwen-coder"):
            parts.append("代码任务→代码优化模型")
        elif task_category in (TaskCategory.CHAT, TaskCategory.SUMMARY) and model.id in ("glm-4-flash", "hunyuan-turbos", "gemma-4"):
            parts.append("简单任务→低成本模型")

        parts.append(f"综合评分: {score:.2f}")
        parts.append(f"成本: ${model.cost_per_1k_tokens}/1K tokens")
        parts.append(f"延迟: {model.avg_latency_ms}ms")

        # Shape 信号附加说明
        if task_shape is not None:
            if task_shape.reasoning_depth > 0.5:
                parts.append(f"推理深度={task_shape.reasoning_depth:.1f}")
            if task_shape.has_output_schema:
                parts.append("需结构化输出")
            if task_shape.is_sensitive:
                parts.append("含敏感信息")

        if budget_ratio < 0.30:
            parts.append(f"预算剩余 {budget_ratio:.0%}（较低）")

        return " · ".join(parts)

    # ---- 决策记录 ----

    def _record_decision(self, result: RouteResult) -> None:
        """记录和统计路由决策。

        1. 更新内存统计
        2. 异步写入 allocator_repository
        """
        self._decision_count += 1

        # 更新内存统计
        cat_stats = self._routing_stats.get(result.task_category)
        if cat_stats is not None:
            cat_stats["total"] += 1
            cat_stats["models"][result.model_id] = cat_stats["models"].get(result.model_id, 0) + 1

        # 异步写入数据库
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._save_decision_async(result))
        except RuntimeError:
            asyncio.run(self._save_decision_async(result))

    async def _save_decision_async(self, result: RouteResult) -> None:
        """异步写入路由决策到 allocator_repository。"""
        if not self._repo:
            self._repo = AllocatorRepository()
            await self._repo.init_tables()
            await self._init_route_table()

        await self._repo.execute(
            """INSERT INTO route_decisions
               (task_category, task_type, model_id, model_name, confidence,
                reason, estimated_tokens, estimated_cost, is_emergency, alternatives)
               VALUES (:tc, :tt, :mid, :mn, :conf, :reason, :et, :ec, :emerg, :alts)""",
            {
                "tc": result.task_category,
                "tt": result.task_category,
                "mid": result.model_id,
                "mn": result.model_name,
                "conf": result.confidence,
                "reason": result.reason,
                "et": result.estimated_tokens,
                "ec": result.estimated_cost,
                "emerg": 1 if result.is_emergency else 0,
                "alts": ",".join(result.alternatives) if result.alternatives else "",
            },
        )

    # ---- 统计接口 ----

    def get_stats(self) -> dict:
        """获取路由统计信息。

        Returns:
            {
                "total_decisions": int,
                "by_category": {category: {total, models: {model_id: count}}},
                "budget_status": {agent_id: {budget, used, remaining, percentage}},
            }
        """
        budget_stats = token_budget.get_stats()
        return {
            "total_decisions": self._decision_count,
            "by_category": dict(self._routing_stats),
            "budget_status": budget_stats.get("agents", {}),
            "emergency_threshold": f"{BUDGET_TIER_EMERGENCY:.0%}",
        }

    def get_available_models(self) -> dict[str, dict]:
        """获取所有注册模型的基本信息。"""
        return {
            mid: {
                "id": m.id,
                "name": m.name,
                "provider": m.provider,
                "cost_per_1k_tokens": m.cost_per_1k_tokens,
                "quality_score": m.quality_score,
                "avg_latency_ms": m.avg_latency_ms,
                "best_for": m.best_for,
            }
            for mid, m in MODEL_REGISTRY.items()
        }

    async def get_route_history(self, limit: int = 50) -> list[dict]:
        """获取最近的决策历史。

        Args:
            limit: 返回数量上限
        """
        if not self._repo:
            self._repo = AllocatorRepository()
        return await self._repo.fetch_dict_all(
            """SELECT id, task_category, model_id, model_name, confidence,
                      reason, estimated_tokens, estimated_cost, is_emergency,
                      created_at
               FROM route_decisions
               ORDER BY id DESC
               LIMIT :limit""",
            {"limit": limit},
        )


# ============================================================
# 模块级单例
# ============================================================

model_router = ModelRouter()
