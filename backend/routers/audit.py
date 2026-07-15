"""审计命令路由"""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from schemas.common import make_response
from services.audit_service import audit_token, audit_security

router = APIRouter()


class AuditTokenRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=365)
    workspace_id: str | None = None


class AuditSecurityRequest(BaseModel):
    pass


@router.post("/audit/token")
async def api_audit_token(request: Request, body: AuditTokenRequest):
    """Token 消耗审计"""
    rid = getattr(request.state, "request_id", "")
    data = await audit_token(days=body.days, workspace_id=body.workspace_id)
    return make_response(data, request_id=rid)


@router.post("/audit/security")
async def api_audit_security(request: Request, body: AuditSecurityRequest = None):
    """安全配置审计"""
    rid = getattr(request.state, "request_id", "")
    data = await audit_security()
    return make_response(data, request_id=rid)
