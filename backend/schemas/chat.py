"""对话相关 Pydantic 模型"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class MessageCreate(BaseModel):
    workspace_id: Optional[str] = Field(
        None, 
        description="工作间 ID，null=全局对话",
        max_length=64,
        pattern=r'^[a-zA-Z0-9_-]+$'
    )
    content: str = Field(..., min_length=1, max_length=50000, description="消息内容")
    model: Optional[str] = Field(
        None, 
        max_length=100,
        pattern=r'^[a-zA-Z0-9._-]+$',
        description="模型名称或auto"
    )
    at_agent_id: Optional[str] = Field(
        None, 
        max_length=64,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Agent ID"
    )
    context_mode: Optional[str] = Field(
        default="auto", 
        description="auto / minimal / full",
        pattern=r'^(auto|minimal|full)$'
    )
    
    @field_validator('content')
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('消息内容不能为空')
        return v.strip()
    
    @field_validator('model')
    @classmethod
    def validate_model(cls, v: Optional[str]) -> Optional[str]:
        if v and v.lower() == 'auto':
            return 'auto'
        return v


class MessageResponse(BaseModel):
    id: str
    workspace_id: Optional[str]
    role: str
    content: str
    model: Optional[str]
    at_agent_id: Optional[str]
    status: str
    token_count: Optional[int]
    artifacts: Optional[list]
    parent_message_id: Optional[str]
    error_info: Optional[str]
    created_at: str


class MessageSearchResult(BaseModel):
    message_id: str
    workspace_id: Optional[str]
    agent_name: Optional[str]
    content_preview: str
    highlight_range: list = []
    created_at: str


class ContextStats(BaseModel):
    total_tokens: int
    token_limit: int
    usage_percent: float
    message_count: int
    l1_memory_size: int
    l2_injections: int
    compression: dict
