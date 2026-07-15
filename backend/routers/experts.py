"""
专家广场路由 — 前端 Plaza API 对接

提供专家/Agent 列表的基础端点。
从 Agent Card 注册表和 Agent Identity 注册表获取数据。
"""

from fastapi import APIRouter, Request

from schemas.common import make_response

router = APIRouter()


@router.get("/experts")
async def api_list_experts(request: Request):
    """列出可用专家/Agent"""
    rid = getattr(request.state, "request_id", "")

    experts = []

    # 从 Agent Card 注册表获取
    try:
        from engine.agent_card import agent_card_registry
        if agent_card_registry and hasattr(agent_card_registry, '_initialized') and agent_card_registry._initialized:
            cards = agent_card_registry.list_all() if hasattr(agent_card_registry, 'list_all') else []
            for c in cards:
                experts.append({
                    "id": str(c.id) if hasattr(c, 'id') else str(hash(c)),
                    "name": getattr(c, 'name', 'Unknown'),
                    "desc": getattr(c, 'description', ''),
                    "role": getattr(c, 'role', 'expert'),
                    "capabilities": [cap.name for cap in getattr(c, 'capabilities', [])] if hasattr(c, 'capabilities') else [],
                    "downloads": getattr(c, 'usage_count', 0) if hasattr(c, 'usage_count') else 0,
                })
    except Exception:
        pass

    # 从 Agent Identity 注册表补充
    try:
        from engine.agent_registry import agent_registry
        if agent_registry:
            stats = agent_registry.get_stats()
            agents = getattr(agent_registry, '_agents', {})
            existing_ids = {e["id"] for e in experts}
            for aid, agent in agents.items():
                if str(aid) not in existing_ids:
                    experts.append({
                        "id": str(aid),
                        "name": getattr(agent, 'name', str(aid)),
                        "desc": getattr(agent, 'description', ''),
                        "role": getattr(agent, 'role', 'agent'),
                        "capabilities": [],
                        "downloads": 0,
                    })
    except Exception:
        pass

    # 如果没有注册专家，返回内置默认列表
    if not experts:
        experts = [
            {"id": "writer-default", "name": "写作助手", "desc": "小说写作与创作辅助", "role": "expert", "capabilities": ["writing", "creative"], "downloads": 0},
            {"id": "coder-default", "name": "编程助手", "desc": "代码编写与调试", "role": "expert", "capabilities": ["coding", "debugging"], "downloads": 0},
            {"id": "analyst-default", "name": "分析助手", "desc": "数据分析与洞察", "role": "expert", "capabilities": ["analysis", "insights"], "downloads": 0},
        ]

    return make_response(experts, request_id=rid)
