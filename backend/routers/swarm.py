"""
Swarm 编排路由 —— vLLM Micro-Agent 蒸馏

ReMoM 综合判决: N路并行推理 → 法定人数等待 → Judge综合 → 降级到最佳证据。
这是 vLLM ReMoM 模式在 Agent 编排层的 API 暴露。
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from schemas.common import make_response, make_error
from engine.chat_hooks import get_chat_integration

router = APIRouter(prefix="/api/v1/swarm", tags=["Swarm 编排"])


# ============================================================
# 请求/响应模型
# ============================================================

class ReMoMRequest(BaseModel):
    """ReMoM 综合判决请求。"""
    task: str = Field(..., min_length=10, max_length=8000,
                      description="任务描述（完整的 prompt 文本）")
    models: list[str] = Field(
        default=["deepseek-v4", "kimi-k2.6"],
        min_length=2, max_length=5,
        description="并行推理的模型列表（N 路），至少 2 个",
    )
    quorum: int = Field(default=2, ge=1, le=5,
                        description="法定人数（至少 K 个响应才进行综合）")
    judge_model: str = Field(default="",
                             description="综合器模型，留空则用 models[0]")
    timeout_ms: int = Field(default=60000, ge=5000, le=120000,
                            description="单路推理超时（毫秒）")
    max_tokens_total: int = Field(default=30000, ge=5000, le=100000,
                                  description="综合器输入 token 上限")
    fallback_to_best: bool = Field(default=True,
                                    description="综合失败时是否降级到最佳单路证据")


class ReMoMResponse(BaseModel):
    """ReMoM 综合判决响应。"""
    final_answer: str
    source: str               # "judge_synthesized" | "best_evidence_fallback" | ...
    quorum_met: bool
    synthesis_model: str
    quality_estimate: float
    elapsed_ms: int
    evidence_count: int = 0
    failure_count: int = 0
    evidence: list[dict] = []
    failures: list[dict] = []


# ============================================================
# 端点
# ============================================================

@router.post("/remom", response_model=dict)
async def remom_synthesize(request: Request, body: ReMoMRequest):
    """ReMoM 综合判决——多模型并行推理 + Judge 综合。

    使用场景：
    - 关键决策：架构选型、技术方案对比
    - 安全审计：代码审查、漏洞分析
    - 高风险：数据迁移、生产部署前检查

    工作流：
    1. N 路模型并行推理（asyncio.gather）
    2. 法定人数等待（至少 K 路成功才进行综合）
    3. Judge 模型综合各路证据，生成统一答案
    4. 综合失败 → 降级到最佳单路证据（best_evidence_fallback）
    """
    ci = get_chat_integration()
    if not ci or not ci.orchestrator:
        raise HTTPException(status_code=503, detail="Swarm 编排引擎未就绪")

    orchestrator = ci.orchestrator
    if not orchestrator._llm:
        raise HTTPException(status_code=503,
                           detail="LLM 回调未注入，无法执行 ReMoM。请检查 chat_hooks 初始化。")

    try:
        result = await orchestrator.synthesize_remom(
            task=body.task,
            models=body.models,
            quorum=body.quorum,
            judge_model=body.judge_model,
            timeout_ms=body.timeout_ms,
            max_tokens_total=body.max_tokens_total,
            fallback_to_best=body.fallback_to_best,
        )

        return make_response({
            "final_answer": result.final_answer,
            "source": result.source,
            "quorum_met": result.quorum_met,
            "synthesis_model": result.synthesis_model,
            "quality_estimate": result.quality_estimate,
            "elapsed_ms": result.elapsed_ms,
            "evidence_count": len(result.evidence),
            "failure_count": len(result.failures),
            "evidence": [
                {"model": e["model"], "response": e["response"][:500]}
                for e in result.evidence
            ],
            "failures": [
                {"model": f["model"], "error": f["error"]}
                for f in result.failures
            ],
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ReMoM 执行异常: {e}")


@router.get("/remom/config", response_model=dict)
async def remom_config():
    """查看 ReMoM 默认配置（从 Recipe 加载）。"""
    from engine.model_router import load_recipe

    recipe = load_recipe()
    remom_config = recipe.get("remom", {}).get("default", {}) if recipe else {}

    return make_response({
        "default": remom_config or {
            "models": ["deepseek-v4", "kimi-k2.6", "qwen-coder"],
            "quorum": 2,
            "judge_model": "deepseek-v4",
            "timeout_ms": 60000,
            "max_tokens_total": 30000,
            "fallback_to_best": True,
        },
        "triggers": recipe.get("remom", {}).get("triggers", []) if recipe else [],
        "available_judge_models": [
            {"id": "deepseek-r1", "name": "DeepSeek R1", "quality": 0.95,
             "note": "最强推理型Judge，适合代码审查、架构决策"},
            {"id": "kimi-k2.6", "name": "Kimi K2.6", "quality": 0.92,
             "note": "创意综合型Judge，适合文案判断、创意输出"},
            {"id": "deepseek-v4", "name": "DeepSeek V4", "quality": 0.90,
             "note": "通用型Judge，性价比最优（$0.003/1K tokens）"},
        ],
        "frontier_judge_note": (
            "vLLM 研究表明：Judge 必须是 frontier 级模型。"
            "用弱模型做 Judge 会退化成'几个弱答案的加权平均'。"
            "建议最低 quality_score ≥ 0.90。"
        ),
    })
