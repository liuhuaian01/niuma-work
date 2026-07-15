"""用户设置相关 Pydantic 模型"""

from typing import Optional
from pydantic import BaseModel, Field


class ProfileSettings(BaseModel):
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        pattern=r'^[\u4e00-\u9fa5a-zA-Z0-9_\s-]+$'
    )
    avatar: Optional[str] = Field(None, max_length=10)
    bio: Optional[str] = Field(None, max_length=500)


class AppearanceSettings(BaseModel):
    theme: Optional[str] = Field(
        None,
        pattern=r'^(light|dark|system)$',
        description="主题: light / dark / system"
    )
    font_size: Optional[str] = Field(
        None,
        pattern=r'^(small|medium|large)$',
        description="字体大小: small / medium / large"
    )
    language: Optional[str] = Field(
        None,
        pattern=r'^(zh-CN|en-US)$',
        description="语言: zh-CN / en-US"
    )


class FeatureSettings(BaseModel):
    pi_rules: Optional[bool] = None
    agent_always_on: Optional[bool] = None
    memory_sync: Optional[bool] = None


class SettingsUpdate(BaseModel):
    profile: Optional[ProfileSettings] = None
    appearance: Optional[AppearanceSettings] = None
    features: Optional[FeatureSettings] = None


class SettingsResponse(BaseModel):
    profile: ProfileSettings
    appearance: AppearanceSettings
    features: FeatureSettings
    limits: dict
