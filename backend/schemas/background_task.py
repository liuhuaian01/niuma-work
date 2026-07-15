"""
后台任务相关 Pydantic 模型
"""

from typing import Optional
from pydantic import BaseModel, Field


class BackgroundTaskCreate(BaseModel):
    agent_id: str = Field(..., min_length=1, description="执行任务的 Agent ID")
    title: str = Field(default="后台任务", min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    trigger_message_id: Optional[str] = None


class BackgroundTaskUpdate(BaseModel):
    status: str = Field(..., description="pending/running/completed/failed/cancelled")
    progress: Optional[int] = Field(None, ge=0, le=100)
    result_summary: Optional[str] = None
    result_message_id: Optional[str] = None
    error_info: Optional[str] = None
    total_tokens: Optional[int] = Field(None, ge=0)
    duration_ms: Optional[int] = Field(None, ge=0)
