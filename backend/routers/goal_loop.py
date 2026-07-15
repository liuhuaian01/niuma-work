"""
目标循环 — 路由

GoalLoopEngine API:
  - GET  /status          → 引擎状态
  - GET  /rules           → 规则列表
  - POST /rules           → 创建规则
  - PUT  /rules/{id}      → 更新规则
  - DELETE /rules/{id}    → 删除规则
  - GET  /targets         → 目标列表
  - POST /targets         → 创建目标
  - PUT  /targets/{id}    → 更新目标进度
  - DELETE /targets/{id}  → 删除目标
  - POST /review          → 手动触发周期性审视
"""
from fastapi import APIRouter, Request, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from schemas.common import make_response, make_error
from engine.lazy_loader import lazy_get

router = APIRouter(prefix="/api/v1/goal-loop", tags=["目标循环"])


# ============================================================
# 请求模型
# ============================================================

class RuleCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="规则名称"
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="规则描述"
    )
    category: str = Field(
        default="behavior",
        pattern=r'^(behavior|workflow|security|performance)$',
        description="规则分类"
    )
    priority: int = Field(
        default=50,
        ge=0,
        le=100,
        description="优先级 0-100"
    )
    conditions: dict = Field(default_factory=dict)
    action: str = Field(
        default="",
        max_length=1000,
        description="触发动作"
    )


class RuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    category: Optional[str] = Field(
        None,
        pattern=r'^(behavior|workflow|security|performance)$'
    )
    priority: Optional[int] = Field(None, ge=0, le=100)
    conditions: Optional[dict] = None
    action: Optional[str] = Field(None, max_length=1000)
    enabled: Optional[bool] = None


class TargetCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="目标名称"
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="目标描述"
    )
    target_value: float = Field(
        ...,
        gt=0,
        description="目标值（必须大于0）"
    )
    unit: str = Field(
        default="",
        max_length=50,
        description="单位"
    )


class TargetUpdate(BaseModel):
    current_value: Optional[float] = Field(None, ge=0)
    status: Optional[str] = Field(
        None,
        pattern=r'^(active|completed|paused|cancelled)$'
    )


# ============================================================
# 状态
# ============================================================

@router.get("/status")
async def get_status(request: Request):
    """获取目标循环引擎状态。"""
    return make_response(lazy_get("engine.goal_loop_engine", "goal_loop").get_status())


# ============================================================
# 规则 CRUD
# ============================================================

@router.get("/rules")
async def list_rules(
    request: Request,
    category: str = Query(""),
    enabled_only: bool = Query(True),
):
    """获取规则列表。"""
    rules = lazy_get("engine.goal_loop_engine", "goal_loop").get_rules(category=category, enabled_only=enabled_only)
    return make_response({
        "rules": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "category": r.category,
                "priority": r.priority,
                "conditions": r.conditions,
                "action": r.action,
                "enabled": r.enabled,
                "source": r.source,
                "hit_count": r.hit_count,
                "last_hit": r.last_hit,
                "created_at": r.created_at,
            }
            for r in rules
        ],
        "total": len(rules),
    })


@router.post("/rules", status_code=201)
async def create_rule(request: Request, body: RuleCreate):
    """创建新规则。"""
    rule = lazy_get("engine.goal_loop_engine", "goal_loop").add_rule(
        name=body.name,
        description=body.description,
        category=body.category,
        priority=body.priority,
        conditions=body.conditions,
        action=body.action,
    )
    return make_response({
        "id": rule.id,
        "name": rule.name,
        "created_at": rule.created_at,
    })


@router.put("/rules/{rule_id}")
async def update_rule(request: Request, rule_id: str, body: RuleUpdate):
    """更新规则。"""
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return make_error("NO_UPDATES", "没有提供更新字段")

    rule = lazy_get("engine.goal_loop_engine", "goal_loop").update_rule(rule_id, **updates)
    if not rule:
        return make_error("RULE_NOT_FOUND", f"规则不存在或不可修改: {rule_id}")
    return make_response({"id": rule.id, "updated_at": rule.updated_at})


@router.delete("/rules/{rule_id}")
async def delete_rule(request: Request, rule_id: str):
    """删除规则。"""
    if lazy_get("engine.goal_loop_engine", "goal_loop").delete_rule(rule_id):
        return make_response({"deleted": rule_id})
    return make_error("RULE_NOT_FOUND", f"规则不存在或不可删除: {rule_id}")


# ============================================================
# 目标 CRUD
# ============================================================

@router.get("/targets")
async def list_targets(request: Request):
    """获取所有目标。"""
    targets = lazy_get("engine.goal_loop_engine", "goal_loop").get_targets()
    return make_response({
        "targets": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "target_value": t.target_value,
                "current_value": t.current_value,
                "unit": t.unit,
                "progress": round(t.progress, 3),
                "status": t.status,
                "created_at": t.created_at,
                "last_checked": t.last_checked,
            }
            for t in targets
        ],
        "total": len(targets),
    })


@router.post("/targets", status_code=201)
async def create_target(request: Request, body: TargetCreate):
    """创建新目标。"""
    target = lazy_get("engine.goal_loop_engine", "goal_loop").add_target(
        name=body.name,
        description=body.description,
        target_value=body.target_value,
        unit=body.unit,
    )
    return make_response({
        "id": target.id,
        "name": target.name,
        "created_at": target.created_at,
    })


@router.put("/targets/{target_id}")
async def update_target(request: Request, target_id: str, body: TargetUpdate):
    """更新目标进度。"""
    target = lazy_get("engine.goal_loop_engine", "goal_loop").update_target(
        target_id=target_id,
        current_value=body.current_value,
        status=body.status,
    )
    if not target:
        return make_error("TARGET_NOT_FOUND", f"目标不存在: {target_id}")
    return make_response({
        "id": target.id,
        "progress": round(target.progress, 3),
        "status": target.status,
    })


@router.delete("/targets/{target_id}")
async def delete_target(request: Request, target_id: str):
    """删除目标。"""
    if lazy_get("engine.goal_loop_engine", "goal_loop").delete_target(target_id):
        return make_response({"deleted": target_id})
    return make_error("TARGET_NOT_FOUND", f"目标不存在: {target_id}")


# ============================================================
# 周期性审视
# ============================================================

@router.post("/review")
async def trigger_review(request: Request):
    """手动触发周期性规则审视。"""
    result = await lazy_get("engine.goal_loop_engine", "goal_loop").periodic_review()
    return make_response(result)


# ============================================================
# 检查点（Checkpoint）— 断点恢复
# ============================================================

@router.get("/checkpoints")
async def list_checkpoints(request: Request):
    """列出所有可用检查点。"""
    return make_response({
        "checkpoints": lazy_get("engine.goal_loop_engine", "goal_loop").list_checkpoints(),
    })


@router.post("/checkpoints/resume")
async def resume_checkpoint(request: Request):
    """从指定检查点恢复状态。

    Body:
        checkpoint_file: 指定检查点文件名（可选，不指定时使用最新）
    """
    body = await request.json()
    checkpoint_file = body.get("checkpoint_file")
    success = await lazy_get("engine.goal_loop_engine", "goal_loop").resume_from_checkpoint(checkpoint_file)
    return make_response({
        "success": success,
        "restored": True,
    })
