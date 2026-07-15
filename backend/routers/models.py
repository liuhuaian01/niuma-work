"""
模型管理路由

四个核心能力：
1. 模型市场 — 定期评测推荐的常用模型，非专业用户也能直接选
2. 硬件检查 — 本地模型部署时检测用户电脑是否跑得动
3. 一键添加 — 常用模型提供预设配置模板
4. 停用管理 — 停用本地模型时询问是否清理文件
"""

import re
import subprocess

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from schemas.common import make_response, make_error
from model_adapter.registry import model_registry
from model_adapter.fallback import fallback_manager
from engine.model_router import model_router, RouteInput

router = APIRouter(prefix="/api/v1/models", tags=["模型"])

# ===== P2-13/P2-16: Ollama 模型名安全验证 =====
# 白名单正则：字母数字开头+结尾，中间允许 . _ : -
# 示例: qwen2.5-coder:7b → ✅ ; rm -rf / → ❌ ; $(whoami) → ❌
_OLLAMA_MODEL_RE = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9._:-]*[a-zA-Z0-9])?$')


def _validate_ollama_model_name(name: str) -> bool:
    """验证 Ollama 模型名是否安全（P2-16: 命令注入防护白名单）。
    
    仅允许标准 Ollama 模型名格式：
    - 字母、数字、点、下划线、冒号、短横线
    - 不能以特殊字符开头或结尾
    - 长度限制防止缓冲区攻击
    """
    if not name or len(name) > 256:
        return False
    return bool(_OLLAMA_MODEL_RE.match(name))


def _safe_ollama_rm(model_name: str) -> str:
    """安全执行 ollama rm 命令（P2-16: 命令白名单校验后执行）。"""
    import subprocess as _sp
    if not _validate_ollama_model_name(model_name):
        return f"模型名称格式异常，已拒绝删除: {model_name}"
    try:
        result = _sp.run(
            ["ollama", "rm", model_name],
            capture_output=True, text=True, timeout=30,
        )
        return result.stdout.strip() or f"已删除 {model_name}"
    except FileNotFoundError:
        return "Ollama 未安装，请手动删除"
    except Exception as e:
        return f"删除失败: {e}"


# ===== 模型市场 — 按场景推荐当下最好用的模型 =====
# 不限数量。只要是当下开源模型里最好用的，都推荐。
# 每个模型标注：场景评分、硬件要求、协议类型。

SCENARIOS = [
    {"id": "coding", "name": "写代码", "icon": "💻", "description": "代码生成、审查、重构、Debug"},
    {"id": "writing", "name": "写文章", "icon": "✍️", "description": "中文写作、文案、长文、润色"},
    {"id": "analysis", "name": "分析研究", "icon": "🔬", "description": "数据分析、竞品研究、策略推演"},
    {"id": "multimodal", "name": "图片·文档", "icon": "🖼️", "description": "图片理解、OCR、图表分析"},
    {"id": "audio", "name": "语音·声音", "icon": "🎤", "description": "语音识别、语音合成、音频处理"},
    {"id": "video", "name": "视频生成", "icon": "🎬", "description": "文生视频、视频理解、视频编辑"},
    {"id": "embedding", "name": "向量·检索", "icon": "🔍", "description": "文本向量化、语义搜索、RAG"},
    {"id": "translation", "name": "翻译", "icon": "🌐", "description": "多语言翻译、本地化"},
    {"id": "everyday", "name": "日常对话", "icon": "💬", "description": "随口问、闲聊、简单任务"},
    {"id": "reasoning", "name": "深度推理", "icon": "🧠", "description": "数学、逻辑、复杂推理、思维链"},
]

MARKETPLACE_MODELS = [
    # ===== 文本·代码·推理 =====
    {
        "id": "deepseek-v4",
        "name": "DeepSeek V4",
        "provider": "DeepSeek",
        "type": "cloud",
        "license": "Apache 2.0",
        "description": "1.6T MoE，1M上下文。当前综合能力最强的开源模型。代码/分析/推理场景碾压级表现。V4-Flash可用低成本。",
        "scenarios": ["coding", "analysis", "reasoning", "writing"],
        "requires_api_key": True,
        "api_base_url": "https://api.deepseek.com/v1",
        "pricing": "$0.87/M 输出（Flash 更低）",
        "evaluation": {"score": 9.5, "coding": 9.8, "writing": 9.0, "analysis": 9.7, "reasoning": 9.6, "everyday": 9.0, "updated": "2026-04"},
    },
    {
        "id": "kimi-k2.6",
        "name": "Kimi K2.6",
        "provider": "月之暗面",
        "type": "cloud",
        "license": "Apache 2.0（K2.7 Code 开源）",
        "description": "中文写作场景最强。K2.7 Code 编程版已开源，可本地部署。API降价趋势。",
        "scenarios": ["writing", "coding", "analysis"],
        "requires_api_key": True,
        "api_base_url": "https://api.moonshot.cn/v1",
        "pricing": "$1.50/M 输出",
        "evaluation": {"score": 9.2, "coding": 8.5, "writing": 9.8, "analysis": 9.0, "reasoning": 8.8, "everyday": 9.0, "updated": "2026-05"},
    },
    {
        "id": "qwen-coder",
        "name": "Qwen2.5-Coder",
        "provider": "阿里巴巴",
        "type": "local",
        "license": "Apache 2.0",
        "description": "阿里开源编程专用模型。7B/32B 可选，消费级 GPU 可跑。代码补全、生成、审查。",
        "scenarios": ["coding"],
        "requires_api_key": False,
        "ollama_model": "qwen2.5-coder",
        "min_ram": 8, "min_vram": 4, "disk_gb": 5,
        "evaluation": {"score": 8.5, "coding": 9.0, "writing": 5.0, "analysis": 6.0, "reasoning": 6.5, "updated": "2026-03"},
    },
    {
        "id": "deepseek-r1",
        "name": "DeepSeek R1",
        "provider": "DeepSeek",
        "type": "cloud",
        "license": "Apache 2.0",
        "description": "专用推理模型。思维链（Chain-of-Thought）原生支持。数学、逻辑、复杂推理场景首选。",
        "scenarios": ["reasoning", "coding", "analysis"],
        "requires_api_key": True,
        "api_base_url": "https://api.deepseek.com/v1",
        "pricing": "$0.55/M 输入 $2.19/M 输出",
        "evaluation": {"score": 9.3, "coding": 9.2, "analysis": 9.4, "reasoning": 9.8, "updated": "2026-02"},
    },
    # ===== 多模态·视觉 =====
    {
        "id": "qwen-vl",
        "name": "Qwen2.5-VL（通义千问视觉）",
        "provider": "阿里巴巴",
        "type": "local",
        "license": "Apache 2.0",
        "description": "阿里开源多模态模型。图片理解、文档OCR、图表分析。本地部署零成本。",
        "scenarios": ["multimodal", "everyday"],
        "requires_api_key": False,
        "ollama_model": "qwen2.5-vl",
        "min_ram": 8, "min_vram": 4, "disk_gb": 5,
        "evaluation": {"score": 8.8, "multimodal": 9.0, "everyday": 8.0, "updated": "2026-04"},
    },
    {
        "id": "gemma-4",
        "name": "Gemma-4",
        "provider": "Google",
        "type": "local",
        "license": "Apache 2.0",
        "description": "预装开箱即用。Google 开源轻量多模态模型。零配置零成本。消费级 GPU 可流畅运行。",
        "scenarios": ["everyday", "multimodal"],
        "requires_api_key": False,
        "ollama_model": "gemma4",
        "min_ram": 8, "min_vram": 4, "disk_gb": 4,
        "evaluation": {"score": 8.3, "multimodal": 8.0, "everyday": 9.0, "updated": "2026-05"},
    },
    {
        "id": "hunyuan",
        "name": "混元",
        "provider": "腾讯",
        "type": "cloud",
        "license": "商业许可",
        "description": "腾讯自研。中文深度好，多媒体场景覆盖广。微信生态集成。",
        "scenarios": ["writing", "analysis"],
        "requires_api_key": True,
        "api_base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "pricing": "按量计费",
        "evaluation": {"score": 8.5, "coding": 7.5, "writing": 8.8, "analysis": 8.5, "everyday": 8.5, "updated": "2026-03"},
    },
    {
        "id": "glm",
        "name": "GLM-4",
        "provider": "智谱 AI",
        "type": "cloud",
        "license": "开源/商业双许可",
        "description": "清华系。通用能力强，支持本地部署量化版。中文对话流畅。",
        "scenarios": ["coding", "everyday"],
        "requires_api_key": True,
        "api_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "pricing": "免费额度 + 按量",
        "evaluation": {"score": 8.0, "coding": 8.0, "writing": 7.5, "analysis": 7.8, "everyday": 8.5, "updated": "2026-04"},
    },
    # ===== 语音·声音 =====
    {
        "id": "whisper",
        "name": "Whisper Large v3",
        "provider": "OpenAI",
        "type": "local",
        "license": "MIT",
        "description": "OpenAI 开源语音识别模型。支持 99 种语言。中文识别优秀。本地运行零成本。",
        "scenarios": ["audio"],
        "requires_api_key": False,
        "ollama_model": None,
        "min_ram": 4, "min_vram": 2, "disk_gb": 3,
        "evaluation": {"score": 9.0, "audio": 9.5, "updated": "2025-11"},
    },
    {
        "id": "bark",
        "name": "Bark（语音合成）",
        "provider": "Suno",
        "type": "local",
        "license": "MIT",
        "description": "Suno 开源语音合成。支持笑声、叹息等非语言声音。多语言支持。",
        "scenarios": ["audio"],
        "requires_api_key": False,
        "ollama_model": None,
        "min_ram": 4, "min_vram": 4, "disk_gb": 2,
        "evaluation": {"score": 7.5, "audio": 8.0, "updated": "2025-06"},
    },
    # ===== 向量·检索 =====
    {
        "id": "bge-m3",
        "name": "BGE-M3（文本向量）",
        "provider": "BAAI（智源）",
        "type": "local",
        "license": "MIT",
        "description": "智源开源多语言向量模型。中英双语最佳，支持稠密+稀疏混合检索。RAG 知识库首选。",
        "scenarios": ["embedding"],
        "requires_api_key": False,
        "ollama_model": "bge-m3",
        "min_ram": 4, "min_vram": 2, "disk_gb": 2,
        "evaluation": {"score": 9.0, "embedding": 9.5, "updated": "2026-01"},
    },
    {
        "id": "nomic-embed",
        "name": "Nomic Embed Text",
        "provider": "Nomic AI",
        "type": "local",
        "license": "Apache 2.0",
        "description": "英文向量检索基准第一。适合英文场景 RAG。轻量快速。",
        "scenarios": ["embedding"],
        "requires_api_key": False,
        "ollama_model": "nomic-embed-text",
        "min_ram": 4, "min_vram": 2, "disk_gb": 1,
        "evaluation": {"score": 8.5, "embedding": 9.0, "updated": "2025-12"},
    },
    # ===== 翻译 =====
    {
        "id": "opus-mt",
        "name": "Opus-MT（翻译）",
        "provider": "Helsinki NLP",
        "type": "local",
        "license": "CC-BY-4.0",
        "description": "专用神经机器翻译模型。支持 100+ 语言对。翻译准确度高。",
        "scenarios": ["translation"],
        "requires_api_key": False,
        "ollama_model": None,
        "min_ram": 2, "min_vram": 1, "disk_gb": 1,
        "evaluation": {"score": 8.0, "translation": 8.5, "updated": "2025-08"},
    },
]


@router.get("/marketplace")
async def list_marketplace(request: Request, scenario: str = None):
    """模型市场 — 按场景推荐当下最好用的模型。

    可选参数 scenario=coding/writing/analysis/multimodal/everyday
    不传则按综合评分排序，传了则按该场景评分排序。
    """
    rid = getattr(request.state, "request_id", "")

    configured = {m["id"]: m.get("configured", False) for m in model_registry.list_models_status()}

    # 按场景筛选并排序
    if scenario:
        models = sorted(
            MARKETPLACE_MODELS,
            key=lambda m: m["evaluation"].get(scenario, 0) if scenario in m.get("scenarios", []) else 0,
            reverse=True,
        )
        scene_info = next((s for s in SCENARIOS if s["id"] == scenario), None)
    else:
        models = sorted(MARKETPLACE_MODELS, key=lambda m: m["evaluation"]["score"], reverse=True)
        scene_info = None

    result = []
    for m in models:
        result.append({
            **m,
            "installed": configured.get(m["id"], False),
            "scenario_score": m["evaluation"].get(scenario) if scenario else None,
        })

    return make_response({
        "scenario": scene_info,
        "scenarios_available": [{"id": s["id"], "name": s["name"], "icon": s["icon"]} for s in SCENARIOS],
        "total": len(result),
        "models": result,
        "updated": "2026-06",
        "tip": "每个场景推荐一个主模型 + 几个备选。选模型 → 系统帮填配置。",
    }, request_id=rid)


# ===== 硬件检查 =====

@router.get("/hardware-check")
async def check_hardware(request: Request):
    """检查当前设备硬件是否满足本地模型的最低要求。"""
    import platform

    rid = getattr(request.state, "request_id", "")
    ram_gb, vram_gb = _get_hardware_specs()

    return make_response({
        "os": platform.system(),
        "ram_gb": ram_gb,
        "vram_gb": round(vram_gb, 1),
        "has_gpu": vram_gb > 0,
        "recommendation": _hardware_recommendation(ram_gb, vram_gb),
    }, request_id=rid)


def _get_hardware_specs() -> tuple[float, float]:
    """检测设备硬件：返回 (ram_gb, vram_gb)。"""
    try:
        import psutil
        mem = psutil.virtual_memory()
        ram_gb = round(mem.total / (1024**3), 1)
    except Exception:
        ram_gb = 0.0

    try:
        # 固定命令，无用户输入，安全
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        vram_gb = sum(float(line.strip()) for line in result.stdout.strip().split("\n") if line.strip()) / 1024
    except Exception:
        vram_gb = 0.0

    return ram_gb, vram_gb


def _hardware_recommendation(ram_gb: float, vram_gb: float) -> str:
    if vram_gb >= 8:
        return "高端配置 — 可运行 7B 及以上模型（Qwen-VL、Gemma-4 等）"
    if vram_gb >= 4:
        return "中等配置 — 可运行 7B 量化模型，推荐 Gemma-4"
    if ram_gb >= 16:
        return "入门配置 — 无独立显卡，可运行 CPU 推理的 1-3B 模型"
    return "硬件不足 — 建议使用云端 API 模型"


class HardwareFitCheck(BaseModel):
    model_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r'^[a-zA-Z0-9._-]+$',
        description="模型ID"
    )


@router.post("/hardware-check/fit")
async def check_model_fit(request: Request, body: HardwareFitCheck):
    """检查某个本地模型是否能在此设备上运行。"""
    rid = getattr(request.state, "request_id", "")

    model = next((m for m in MARKETPLACE_MODELS if m["id"] == body.model_id and m["type"] == "local"), None)
    if not model:
        return make_error("NOT_LOCAL", "此模型不是本地模型，无需硬件检查", request_id=rid)

    ram_gb, vram_gb = _get_hardware_specs()

    min_ram = model.get("min_ram", 8)
    min_vram = model.get("min_vram", 4)
    ok = ram_gb >= min_ram and vram_gb >= min_vram

    return make_response({
        "model_id": body.model_id,
        "model_name": model["name"],
        "requirements": {"min_ram_gb": min_ram, "min_vram_gb": min_vram, "disk_gb": model.get("disk_gb", 0)},
        "current": {"ram_gb": ram_gb, "vram_gb": vram_gb},
        "can_run": ok,
        "suggestion": f"可以运行" if ok else f"你的设备 RAM={ram_gb}GB VRAM={vram_gb}GB，不满足最低要求 RAM≥{min_ram}GB VRAM≥{min_vram}GB。建议使用云端 API 版本。",
    }, request_id=rid)


# ===== 模型管理（停用/清理） =====

class DisableModelRequest(BaseModel):
    model_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r'^[a-zA-Z0-9._-]+$',
        description="模型ID"
    )
    delete_local_files: bool = Field(
        default=False,
        description="是否同时删除本地模型文件"
    )


@router.post("/disable")
async def disable_model(request: Request, body: DisableModelRequest):
    """停用模型。如果是本地模型，询问是否清理文件。"""
    rid = getattr(request.state, "request_id", "")

    model = next((m for m in MARKETPLACE_MODELS if m["id"] == body.model_id), None)
    is_local = model and model.get("type") == "local"

    model_registry.disable_model(body.model_id)

    deleted_files_info = ""
    if body.delete_local_files and is_local:
        ollama_model = model.get("ollama_model", "").strip()
        if ollama_model:
            # P2-13/P2-16: 安全删除——白名单校验防止命令注入
            deleted_files_info = _safe_ollama_rm(ollama_model)

    return make_response({
        "model_id": body.model_id,
        "status": "disabled",
        "is_local": is_local,
        "files_deleted": body.delete_local_files and is_local,
        "detail": deleted_files_info if deleted_files_info else "已停用",
    }, request_id=rid)


# ===== 已有模型列表 =====

@router.get("/available")
async def list_available_models(request: Request):
    """列出用户已配置的所有模型。"""
    rid = getattr(request.state, "request_id", "")

    all_models = model_registry.list_models_status()
    fallback_info = fallback_manager.get_fallback_info()

    configured = [m for m in all_models if m.get("configured", False)]

    return make_response({
        "default": "auto",
        "total": len(configured),
        "models": [
            {
                "id": m["id"],
                "name": m["display_name"],
                "best_for": _best_for(m["id"]),
                "context_window": m.get("context", 0),
                "status": _model_status(
                    m["id"],
                    fallback_info.get(m["id"], {}).get("disabled", False),
                    fallback_info.get(m["id"], {}).get("quota_exhausted", False),
                ),
            }
            for m in configured
        ],
    }, request_id=rid)


# ===== 模型路由 =====

@router.get("/route")
async def route_model(
    request: Request,
    task_type: str = "chat",
    budget: int = 50000,
    cost_per_token: float = 0.0,
    latency_ms: int = 5000,
    quality: float = 0.0,
    agent_id: str = "default",
):
    """模型路由 — 三维路由引擎智能推荐最优模型。

    维度1: 任务类型 (creative/coding/analysis/chat/summary)
    维度2: 成本约束 (budget=预算上限, cost_per_token=单token成本上限)
    维度3: 质量要求 (latency_ms=延迟上限, quality=最低质量阈值)

    路由策略:
      - 简单任务 → 便宜模型 (GLM-4-Flash / 混元TurboS)
      - 创作任务 → 高质量模型 (Kimi K2.6 / DeepSeek)
      - 代码任务 → 代码优化模型 (DeepSeek / Kimi)
      - Token预算<10%时 → 自动切换最便宜模型
    """
    rid = getattr(request.state, "request_id", "")

    route_input = RouteInput(
        task_type=task_type,
        budget_limit=budget,
        cost_per_token=cost_per_token,
        latency_ms=latency_ms,
        quality_threshold=quality,
        agent_id=agent_id,
    )

    result = model_router.route(route_input)

    return make_response({
        "recommended": {
            "model_id": result.model_id,
            "model_name": result.model_name,
            "confidence": result.confidence,
            "reason": result.reason,
        },
        "cost_estimate": {
            "estimated_tokens": result.estimated_tokens,
            "estimated_cost_usd": result.estimated_cost,
        },
        "task_category": result.task_category,
        "is_emergency": result.is_emergency,
        "alternatives": result.alternatives,
    }, request_id=rid)


class RouteStatsRequest(BaseModel):
    history_limit: int = Field(default=50, ge=1, le=200, description="返回历史记录上限")


@router.get("/route/models")
async def list_route_models(request: Request):
    """列出路由引擎注册的所有模型及其性能画像。"""
    rid = getattr(request.state, "request_id", "")
    models = model_router.get_available_models()

    return make_response({
        "total": len(models),
        "models": list(models.values()),
    }, request_id=rid)


@router.post("/route/stats")
async def get_route_stats(request: Request, body: RouteStatsRequest):
    """路由统计 — 查询路由决策统计和预算状态。"""
    rid = getattr(request.state, "request_id", "")

    stats = model_router.get_stats()
    history = await model_router.get_route_history(limit=body.history_limit)

    # 转换分类统计为可序列化格式
    by_category_serializable = {}
    for cat, data in stats.get("by_category", {}).items():
        by_category_serializable[cat] = {
            "total": data["total"],
            "models": dict(data["models"]),
        }

    return make_response({
        "summary": {
            "total_decisions": stats["total_decisions"],
            "by_category": by_category_serializable,
            "emergency_threshold": stats["emergency_threshold"],
        },
        "budget_status": stats["budget_status"],
        "recent_history": [
            {
                "id": h["id"],
                "task_category": h["task_category"],
                "model_id": h["model_id"],
                "model_name": h["model_name"],
                "confidence": h["confidence"],
                "reason": h["reason"],
                "estimated_tokens": h["estimated_tokens"],
                "estimated_cost": h["estimated_cost"],
                "is_emergency": bool(h["is_emergency"]),
                "created_at": h["created_at"],
            }
            for h in history
        ],
    }, request_id=rid)


def _model_status(model_id: str, disabled: bool, quota_exhausted: bool) -> str:
    if quota_exhausted:
        return "quota_exhausted"
    if disabled:
        return "temporarily_unavailable"
    return "ready"


def _best_for(model_id: str) -> str:
    mapping = {
        "deepseek-v4": "代码·分析",
        "kimi-k2.6": "中文写作",
        "qwen-vl": "图片·文档",
        "gemma-4": "日常·多模态",
        "hunyuan": "中文写作",
        "glm": "通用对话",
    }
    return mapping.get(model_id, "通用")
