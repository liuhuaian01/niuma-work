"""
Agent 相关 Pydantic 模型
"""

from typing import Optional
from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=50,
        pattern=r'^[\u4e00-\u9fa5a-zA-Z0-9_\s-]+$'
    )
    role: str = Field(
        ..., 
        description="director/writer/editor/coder/researcher/reviewer/custom",
        pattern=r'^(director|writer|editor|coder|researcher|reviewer|custom)$'
    )
    icon: str = Field(default="🤖", max_length=10)
    model: str = Field(
        default="auto", 
        description="auto=太极引擎自动推荐, 或指定模型名",
        max_length=100,
        pattern=r'^(auto|[a-zA-Z0-9._-]+)$'
    )
    system_prompt: Optional[str] = Field(None, max_length=10000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=32768)


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=50,
        pattern=r'^[\u4e00-\u9fa5a-zA-Z0-9_\s-]+$'
    )
    icon: Optional[str] = Field(None, max_length=10)
    model: Optional[str] = Field(
        None,
        max_length=100,
        pattern=r'^(auto|[a-zA-Z0-9._-]+)$'
    )
    system_prompt: Optional[str] = Field(None, max_length=10000)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=32768)


class AgentResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    role: str
    icon: str
    model: str
    system_prompt: Optional[str]
    temperature: float
    max_tokens: int
    status: str
    sort_order: int
    created_at: str
    updated_at: str
