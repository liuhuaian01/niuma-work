"""
Agent 身份相关 Pydantic 模型 (P1-7: Agent 身份注册表)
"""

from typing import Optional
from pydantic import BaseModel, Field


class AgentIdentityRegister(BaseModel):
    """Agent 身份注册请求"""
    agent_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Agent 唯一标识符"
    )
    workspace_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="所属工作间 ID"
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r'^[\u4e00-\u9fa5a-zA-Z0-9_\s-]+$',
    )
    role: str = Field(
        ...,
        pattern=r'^(director|writer|editor|coder|researcher|reviewer|custom)$',
        description="Agent 角色"
    )
    public_key_hash: str = Field(
        default="",
        max_length=128,
        description="Agent 公钥 SHA-256 指纹（可选）"
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="附加元数据"
    )


class AgentIdentityRevoke(BaseModel):
    """Agent 身份吊销请求"""
    agent_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
    )


class AgentTokenRequest(BaseModel):
    """身份令牌签发请求"""
    agent_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
    )
    ttl: Optional[int] = Field(
        default=None,
        ge=60,
        le=604800,
        description="令牌有效期（秒），默认 86400（24小时），最大 604800（7天）"
    )
    metadata: Optional[dict] = Field(
        default=None,
    )


class AgentTokenVerify(BaseModel):
    """令牌验证请求"""
    token: str = Field(
        ...,
        min_length=1,
        max_length=4096,
    )


class TokenResponse(BaseModel):
    """令牌签发响应"""
    token: str
    agent_id: str
    agent_name: str
    agent_role: str
    issued_at: int
    expires_at: int


class VerifyResponse(BaseModel):
    """令牌验证响应"""
    valid: bool
    reason: str = ""
    agent_info: Optional[dict] = None


class AgentIdentityInfo(BaseModel):
    """Agent 身份信息"""
    agent_id: str
    workspace_id: str
    name: str
    role: str
    registered_at: float
    revoked: bool = False
    metadata: Optional[dict] = None


class RegistryStats(BaseModel):
    """注册表统计"""
    total_registrations: int
    active_agents: int
    revoked_agents: int
    revoked_tokens: int
    token_ttl: int
