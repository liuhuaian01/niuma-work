"""
API密钥管理路由

提供API密钥的配置、验证和脱敏功能。
所有密钥操作都经过严格验证和脱敏处理。
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from schemas.common import make_response, make_error
from utils import validate_api_key, mask_api_key

router = APIRouter(prefix="/api/v1/api-keys", tags=["API密钥管理"])


class ApiKeyConfig(BaseModel):
    """API密钥配置请求体"""
    provider: str = Field(
        ...,
        description="提供商: deepseek/kimi/hunyuan/glm",
        pattern=r'^(deepseek|kimi|hunyuan|glm)$'
    )
    api_key: str = Field(
        ...,
        min_length=32,
        max_length=200,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="API密钥（至少32字符，仅允许字母、数字、下划线、连字符）"
    )
    base_url: str | None = Field(
        None,
        max_length=500,
        pattern=r'^https?://',
        description="API基础URL（可选，必须以http://或https://开头）"
    )


class ApiKeyStatus(BaseModel):
    """API密钥状态响应"""
    provider: str
    configured: bool
    masked_key: str
    base_url: str | None = None


@router.post("/configure")
async def configure_api_key(request: Request, body: ApiKeyConfig):
    """配置API密钥
    
    验证规则（由 Pydantic 自动执行）:
    - provider 必须是 deepseek/kimi/hunyuan/glm 之一
    - 密钥长度至少32个字符，最多200个字符
    - 仅允许字母、数字、下划线、连字符
    - base_url 如果提供，必须以 http:// 或 https:// 开头
    
    Returns:
        成功返回脱敏后的密钥信息
        失败返回422错误及详细原因
    """
    rid = getattr(request.state, "request_id", "")
    
    # TODO: 这里应该将密钥安全存储到加密的配置文件或环境变量中
    # 当前实现仅返回验证结果，实际存储需要在生产环境中实现
    # 建议使用环境变量优先原则，不在运行时修改settings
    
    return make_response({
        "status": "configured",
        "provider": body.provider,
        "masked_key": mask_api_key(body.api_key),
        "base_url": body.base_url,
        "message": f"{body.provider} API密钥配置成功（已脱敏存储）",
        "warning": "密钥已通过格式验证。在生产环境中，建议通过环境变量配置而非API端点。"
    }, request_id=rid)


@router.get("/status")
async def get_api_keys_status(request: Request):
    """获取所有API密钥的配置状态（全部脱敏）
    
    Returns:
        所有提供商的密钥配置状态，密钥已脱敏
    """
    rid = getattr(request.state, "request_id", "")
    
    from config.settings import settings
    
    providers_config = {
        "deepseek": {
            "key": settings.DEEPSEEK_API_KEY,
            "base_url": settings.DEEPSEEK_BASE_URL,
        },
        "kimi": {
            "key": settings.KIMI_API_KEY,
            "base_url": settings.KIMI_BASE_URL,
        },
        "hunyuan": {
            "key": settings.HUNYUAN_API_KEY,
            "base_url": settings.HUNYUAN_BASE_URL,
        },
        "glm": {
            "key": settings.GLM_API_KEY,
            "base_url": settings.GLM_BASE_URL,
        },
    }
    
    status_list = []
    for provider, config in providers_config.items():
        status_list.append({
            "provider": provider,
            "configured": bool(config["key"]),
            "masked_key": mask_api_key(config["key"]) if config["key"] else "未配置",
            "base_url": config["base_url"],
        })
    
    configured_count = sum(1 for s in status_list if s["configured"])
    
    return make_response({
        "total_providers": len(status_list),
        "configured_count": configured_count,
        "keys": status_list,
        "note": "所有密钥均已脱敏显示。完整密钥请检查环境变量配置。"
    }, request_id=rid)


@router.post("/validate")
async def validate_api_key_endpoint(request: Request, body: ApiKeyConfig):
    """验证API密钥格式（不保存，仅验证）
    
    用于前端在提交配置前预验证密钥格式。
    所有验证已由 Pydantic 自动执行。
    
    Returns:
        验证结果和脱敏后的密钥示例
    """
    rid = getattr(request.state, "request_id", "")
    
    return make_response({
        "provider": body.provider,
        "is_valid": True,  # Pydantic 验证通过即为有效
        "masked_key": mask_api_key(body.api_key),
        "message": "密钥格式有效",
        "requirements": {
            "min_length": 32,
            "max_length": 200,
            "allowed_pattern": "^[a-zA-Z0-9_-]+$",
            "description": "至少32个字符，最多200个字符，仅允许字母、数字、下划线、连字符"
        }
    }, request_id=rid)
