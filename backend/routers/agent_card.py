"""
Agent Card 路由 — v2.0 新增

A2A v1.0标准Agent Card API。
Agent能力声明、发现、匹配的端点。

API:
  - POST /register        → 注册/更新Agent Card
  - DELETE /unregister/{id} → 注销Agent Card
  - GET  /{agent_id}      → 获取Agent Card详情
  - GET  /{agent_id}/a2a  → 获取A2A v1.0标准格式
  - GET  /discover        → 按条件发现Agent
  - GET  /match/{task}    → 为任务匹配Agent
  - GET  /capabilities    → 列出所有已知能力
  - GET  /roles           → 列出所有已知角色
  - GET  /stats           → 注册表统计
  - GET  /list            → 列出所有Agent Card
"""
from fastapi import APIRouter, Request, Query
from schemas.common import make_response
from engine.agent_card import agent_card_registry, AgentCard, AgentCapability

router = APIRouter(prefix="/api/v1/agent-cards", tags=["Agent Card"])


@router.on_event("startup")
async def _startup():
    await agent_card_registry.initialize()


@router.post("/register")
async def register_card(request: Request):
    """注册或更新Agent Card。"""
    body = await request.json()

    # 解析capabilities
    caps_raw = body.get("capabilities", [])
    capabilities = [
        AgentCapability(
            name=c.get("name", ""),
            category=c.get("category", "conversation"),
            proficiency=c.get("proficiency", 0.5),
            description=c.get("description", ""),
            supported_languages=c.get("supported_languages", []),
            max_complexity=c.get("max_complexity", 0.5),
        )
        for c in caps_raw
    ]

    card = AgentCard(
        agent_id=body.get("agent_id", ""),
        display_name=body.get("display_name", ""),
        role=body.get("role", "custom"),
        capabilities=capabilities,
        capability_tags=body.get("capability_tags", [c.name for c in capabilities]),
        recommended_models=body.get("recommended_models", []),
        token_budget=body.get("token_budget", 20000),
        sla_max_latency_ms=body.get("sla_max_latency_ms", 30000),
        context_window=body.get("context_window", 128000),
        input_formats=body.get("input_formats", ["text"]),
        output_formats=body.get("output_formats", ["text"]),
        auth_methods=body.get("auth_methods", ["token"]),
        trust_level=body.get("trust_level", 0.5),
        require_hitl=body.get("require_hitl", False),
        workspace_id=body.get("workspace_id", ""),
        tags=body.get("tags", []),
        description=body.get("description", ""),
    )

    if not card.agent_id or not card.display_name:
        return make_response({"error": "agent_id and display_name required"}, status_code=400)

    result = await agent_card_registry.register(card)
    return make_response(result.to_dict())


@router.delete("/unregister/{agent_id}")
async def unregister_card(agent_id: str):
    """注销Agent Card。"""
    success = await agent_card_registry.unregister(agent_id)
    return make_response({"agent_id": agent_id, "unregistered": success})


@router.get("/{agent_id}")
async def get_card(agent_id: str):
    """获取Agent Card详情。"""
    card = await agent_card_registry.get_card(agent_id)
    if not card:
        return make_response({"error": "Agent Card not found"}, status_code=404)
    return make_response(card)


@router.get("/{agent_id}/a2a")
async def get_a2a_card(agent_id: str):
    """获取A2A v1.0标准格式的Agent Card。"""
    card = await agent_card_registry.get_a2a_card(agent_id)
    if not card:
        return make_response({"error": "Agent Card not found"}, status_code=404)
    return make_response(card)


@router.get("/discover")
async def discover_agents(
    role: str = Query("", description="角色过滤"),
    capability: str = Query("", description="能力标签过滤"),
    workspace_id: str = Query("", description="工作间过滤"),
    trust_level_min: float = Query(0.0, description="最低信任等级"),
    limit: int = Query(20, description="返回条数上限"),
):
    """按条件发现Agent。"""
    results = await agent_card_registry.discover(
        role=role,
        capability=capability,
        workspace_id=workspace_id,
        trust_level_min=trust_level_min,
        limit=limit,
    )
    return make_response({"agents": results, "count": len(results)})


@router.get("/match/{task_type}")
async def match_agent_for_task(
    task_type: str,
    required_capabilities: str = Query("", description="逗号分隔的所需能力"),
    min_trust: float = Query(0.0, description="最低信任等级"),
):
    """为指定任务类型匹配最合适的Agent。"""
    req_caps = [c.strip() for c in required_capabilities.split(",") if c.strip()] if required_capabilities else None
    results = await agent_card_registry.match_agent_for_task(
        task_type=task_type,
        required_capabilities=req_caps,
        min_trust=min_trust,
    )
    return make_response({"matches": results, "count": len(results)})


@router.get("/capabilities")
async def list_capabilities():
    """列出所有已知能力标签。"""
    return make_response({"capabilities": agent_card_registry.list_capabilities()})


@router.get("/roles")
async def list_roles():
    """列出所有已知角色。"""
    return make_response({"roles": agent_card_registry.list_roles()})


@router.get("/stats")
async def get_stats():
    """Agent Card注册表统计。"""
    return make_response(agent_card_registry.get_stats())


@router.get("/list")
async def list_all():
    """列出所有Agent Card。"""
    cards = await agent_card_registry.list_all()
    return make_response({"cards": cards, "count": len(cards)})
