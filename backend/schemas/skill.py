"""技能相关 Pydantic 模型"""

from typing import Optional
from pydantic import BaseModel, Field


class SkillInstallRequest(BaseModel):
    skill_id: str


class SkillToggleRequest(BaseModel):
    enabled: bool


class SkillMarketResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    author: str
    version: str
    icon: str
    token_level: str
    install_count: int
    recommend_reason: Optional[str]
    installed: bool = False


class UserSkillResponse(BaseModel):
    id: str
    skill_id: str
    name: str
    description: Optional[str]
    category: Optional[str]
    author: Optional[str]
    version: Optional[str]
    icon: str
    source: str
    enabled: bool
    is_custom: bool
    installed_at: str


class SkillUploadResult(BaseModel):
    skill_id: Optional[str]
    name: str
    dedup_result: str  # no_conflict / high_similarity / partial_similar
    similar_skill: Optional[dict] = None
    installed: bool = False
    action_required: Optional[str] = None
