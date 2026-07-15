"""Agent 管理路由"""

from fastapi import APIRouter, Request

from schemas.common import make_response, make_error
from schemas.agent import AgentCreate, AgentUpdate
from services.agent_service import list_agents, add_agent, update_agent, remove_agent

router = APIRouter()


@router.get("/workspaces/{workspace_id}/agents")
async def api_list_agents(request: Request, workspace_id: str):
    rid = getattr(request.state, "request_id", "")
    agents = await list_agents(workspace_id)
    return make_response(agents, request_id=rid)


@router.post("/workspaces/{workspace_id}/agents", status_code=201)
async def api_add_agent(request: Request, workspace_id: str, body: AgentCreate):
    rid = getattr(request.state, "request_id", "")
    try:
        agent = await add_agent(workspace_id, body.model_dump())
        return make_response(agent, request_id=rid)
    except Exception as e:
        if hasattr(e, "detail") and isinstance(e.detail, dict):
            return make_error(**e.detail, request_id=rid)
        raise


@router.put("/workspaces/{workspace_id}/agents/{agent_id}")
async def api_update_agent(request: Request, workspace_id: str, agent_id: str, body: AgentUpdate):
    rid = getattr(request.state, "request_id", "")
    updates = body.model_dump(exclude_none=True)
    agent = await update_agent(workspace_id, agent_id, updates)
    if not agent:
        return make_error("AGENT_NOT_FOUND", "Agent 不存在", request_id=rid)
    return make_response(agent, request_id=rid)


@router.delete("/workspaces/{workspace_id}/agents/{agent_id}", status_code=204)
async def api_remove_agent(request: Request, workspace_id: str, agent_id: str):
    rid = getattr(request.state, "request_id", "")
    removed = await remove_agent(workspace_id, agent_id)
    if not removed:
        return make_error("AGENT_NOT_FOUND", "Agent 不存在", request_id=rid)
    return None
