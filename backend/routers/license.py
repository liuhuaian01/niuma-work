"""
许可证激活 API
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from schemas.common import make_response, make_error
from services.user_manager import user_manager, PLANS

router = APIRouter(tags=["许可证"])


class ActivateRequest(BaseModel):
    activation_key: str = Field(..., min_length=8, description="激活 Key")


@router.get("/status")
async def get_license_status(request: Request):
    """获取当前许可证状态。"""
    return make_response(user_manager.get_status())


@router.get("/plans")
async def get_plans(request: Request):
    """获取可购买套餐列表。"""
    return make_response({
        "plans": [
            {"id": k, "name": v["name"], "days": v["days"]}
            for k, v in PLANS.items() if k != "lifetime"
        ],
    })


@router.post("/activate")
async def activate_license(request: Request, body: ActivateRequest):
    """激活许可证。"""
    success, msg = user_manager.activate_license(body.activation_key)
    if success:
        return make_response({"status": "activated", "message": msg})
    return make_error("ACTIVATION_FAILED", msg)


@router.post("/init")
async def init_user(request: Request):
    """首次启动——初始化用户 + 开始试用。"""
    user = user_manager.init_device()
    return make_response({
        "device_id": user.device_id[:8],
        "trial_days": 3,
        "message": "欢迎使用超级牛马工作台。3天免费试用已开始。",
    })
