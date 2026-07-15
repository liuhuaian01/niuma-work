"""
Agent 身份注册 API 路由 (P1-7)

端点:
- POST   /api/v1/agent-identity/register      — 注册 Agent 身份
- POST   /api/v1/agent-identity/revoke        — 吊销 Agent 身份
- POST   /api/v1/agent-identity/token         — 签发身份令牌
- POST   /api/v1/agent-identity/verify        — 验证令牌
- POST   /api/v1/agent-identity/revoke-token  — 吊销令牌
- GET    /api/v1/agent-identity/agents        — 列出所有 Agent
- GET    /api/v1/agent-identity/agents/{id}   — 查询 Agent 详情
- GET    /api/v1/agent-identity/stats         — 注册统计
"""

from fastapi import APIRouter, HTTPException

from engine.agent_registry import agent_registry
from schemas.agent_identity import (
    AgentIdentityRegister,
    AgentIdentityRevoke,
    AgentTokenRequest,
    AgentTokenVerify,
    TokenResponse,
    VerifyResponse,
    RegistryStats,
)

router = APIRouter(prefix="/api/v1/agent-identity", tags=["Agent 身份"])


@router.post("/register", response_model=dict, status_code=201)
async def register_agent(req: AgentIdentityRegister):
    """注册 Agent 身份"""
    try:
        record = await agent_registry.register_agent(
            agent_id=req.agent_id,
            workspace_id=req.workspace_id,
            name=req.name,
            role=req.role,
            public_key_hash=req.public_key_hash,
            metadata=req.metadata,
        )
        return {
            "status": "registered",
            "agent_id": record.agent_id,
            "name": record.name,
            "role": record.role,
            "workspace_id": record.workspace_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/revoke", response_model=dict)
async def revoke_agent(req: AgentIdentityRevoke):
    """吊销 Agent 身份"""
    ok = await agent_registry.revoke_agent(req.agent_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Agent {req.agent_id} 不存在或已吊销")
    return {"status": "revoked", "agent_id": req.agent_id}


@router.post("/token", response_model=TokenResponse)
async def issue_token(req: AgentTokenRequest):
    """签发 Agent 身份令牌"""
    token_str = await agent_registry.issue_identity_token(
        agent_id=req.agent_id,
        ttl=req.ttl,
        metadata=req.metadata,
    )
    if token_str is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent {req.agent_id} 未注册或已吊销",
        )

    # 解析令牌以获取元数据
    token_obj = agent_registry._decode_token(token_str)
    return TokenResponse(
        token=token_str,
        agent_id=req.agent_id,
        agent_name=token_obj.agent_name if token_obj else "",
        agent_role=token_obj.agent_role if token_obj else "",
        issued_at=int(token_obj.issued_at) if token_obj else 0,
        expires_at=int(token_obj.expires_at) if token_obj else 0,
    )


@router.post("/verify", response_model=VerifyResponse)
async def verify_token(req: AgentTokenVerify):
    """验证 Agent 身份令牌"""
    valid, reason, agent_info = await agent_registry.verify_token(req.token)
    return VerifyResponse(valid=valid, reason=reason, agent_info=agent_info)


@router.post("/revoke-token", response_model=dict)
async def revoke_token(req: AgentTokenVerify):
    """吊销指定令牌（加入黑名单）"""
    ok = await agent_registry.revoke_token(req.token)
    if not ok:
        raise HTTPException(status_code=400, detail="令牌无效或已吊销")
    return {"status": "revoked"}


@router.get("/agents", response_model=list[dict])
async def list_agents(workspace_id: str = ""):
    """列出所有活跃 Agent"""
    return agent_registry.list_agents(workspace_id=workspace_id)


@router.get("/agents/{agent_id}", response_model=dict)
async def get_agent(agent_id: str):
    """查询 Agent 详情"""
    info = agent_registry.get_agent_info(agent_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} 未注册或已吊销")
    return info


@router.get("/stats", response_model=RegistryStats)
async def get_stats():
    """获取注册统计"""
    return RegistryStats(**agent_registry.get_stats())
