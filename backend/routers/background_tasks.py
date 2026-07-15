"""后台任务路由

v1.5 简化版：Director 指令 → 子 Agent 异步执行 → Toast + 对话插入
不支持定时/Cron/Webhook
"""

from fastapi import APIRouter, Request, Query

from schemas.common import make_response, make_paginated_response, make_error
from schemas.background_task import BackgroundTaskCreate, BackgroundTaskUpdate
from services.background_task_service import (
    create_background_task, list_background_tasks,
    get_background_task, update_task_status, cancel_background_task,
)

router = APIRouter()


@router.post("/workspaces/{workspace_id}/background-tasks", status_code=201)
async def api_create_background_task(request: Request, workspace_id: str, body: BackgroundTaskCreate):
    """创建后台任务"""
    rid = getattr(request.state, "request_id", "")

    task = await create_background_task(
        workspace_id=workspace_id,
        agent_id=body.agent_id,
        title=body.title,
        description=body.description,
        trigger_message_id=body.trigger_message_id,
    )
    return make_response(task, request_id=rid)


@router.get("/workspaces/{workspace_id}/background-tasks")
async def api_list_background_tasks(
    request: Request,
    workspace_id: str,
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """列出后台任务"""
    rid = getattr(request.state, "request_id", "")
    tasks, total = await list_background_tasks(workspace_id, status, page, page_size)
    return make_paginated_response(tasks, page, page_size, total, request_id=rid)


@router.get("/background-tasks/{task_id}")
async def api_get_background_task(request: Request, task_id: str):
    """获取后台任务详情"""
    rid = getattr(request.state, "request_id", "")
    task = await get_background_task(task_id)
    if not task:
        return make_error("TASK_NOT_FOUND", "任务不存在", request_id=rid)
    return make_response(task, request_id=rid)


@router.put("/background-tasks/{task_id}")
async def api_update_background_task(request: Request, task_id: str, body: BackgroundTaskUpdate):
    """更新任务状态（Agent 内部调用）"""
    rid = getattr(request.state, "request_id", "")

    kwargs = body.model_dump(exclude_none=True, exclude={"status"})
    task = await update_task_status(task_id, body.status, **kwargs)
    if not task:
        return make_error("TASK_NOT_FOUND", "任务不存在", request_id=rid)
    return make_response(task, request_id=rid)


@router.post("/background-tasks/{task_id}/cancel")
async def api_cancel_background_task(request: Request, task_id: str):
    """取消后台任务"""
    rid = getattr(request.state, "request_id", "")
    task = await cancel_background_task(task_id)
    if not task:
        return make_error("TASK_NOT_FOUND", "任务不存在或无法取消", request_id=rid)
    return make_response(task, request_id=rid)
