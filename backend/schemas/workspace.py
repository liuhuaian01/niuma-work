"""
工作间相关 Pydantic 模型
"""

from typing import Optional
from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=50, 
        description="工作间名称",
        pattern=r'^[\u4e00-\u9fa5a-zA-Z0-9_\s-]+$'
    )
    icon: str = Field(
        default="📄", 
        description="Emoji 图标",
        max_length=10
    )
    theme_color: str = Field(
        default="#FF6B35", 
        description="主题色 HEX",
        pattern=r'^#[0-9A-Fa-f]{6}$'
    )
    template: Optional[str] = Field(
        default=None,
        description="模板: novel-writing / self-media / code-dev / blank",
        pattern=r'^(novel-writing|self-media|code-dev|blank)$'
    )


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=50,
        pattern=r'^[\u4e00-\u9fa5a-zA-Z0-9_\s-]+$'
    )
    icon: Optional[str] = Field(None, max_length=10)
    theme_color: Optional[str] = Field(
        None,
        pattern=r'^#[0-9A-Fa-f]{6}$'
    )


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    icon: str
    theme_color: str
    is_default: bool
    created_at: str
    updated_at: str


class WorkspaceDetailResponse(WorkspaceResponse):
    agents: list = []
    config: Optional[dict] = None
    stats: Optional[dict] = None


class WorkspaceConfigUpdate(BaseModel):
    default_model: Optional[str] = Field(None, description="默认模型")
    token_budget: Optional[int] = Field(None, ge=0, le=500000, description="日 Token 预算")
    security_level: Optional[str] = Field(None, description="strict/balanced/fast/guarded")
    context_threshold: Optional[int] = Field(None, ge=2048, le=16384, description="上下文长度阈值")
    auto_summary: Optional[bool] = Field(None, description="自动摘要开关")


class TemplateAgentInfo(BaseModel):
    name: str
    role: str
    system_prompt: Optional[str] = None


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    default_model: str
    agents: list = []
