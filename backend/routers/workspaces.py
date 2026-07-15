"""工作间管理路由"""

from fastapi import APIRouter, Request, Query

from schemas.common import make_response, make_paginated_response, make_error
from schemas.workspace import WorkspaceCreate, WorkspaceUpdate
from services.workspace_service import (
    list_workspaces, create_workspace, get_workspace,
    update_workspace, soft_delete_workspace, get_templates,
)

router = APIRouter()


@router.get("/workspaces")
async def api_list_workspaces(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    rid = getattr(request.state, "request_id", "")
    workspaces, total = await list_workspaces(page, page_size)
    return make_paginated_response(workspaces, page, page_size, total, request_id=rid)


@router.post("/workspaces", status_code=201)
async def api_create_workspace(request: Request, body: WorkspaceCreate):
    rid = getattr(request.state, "request_id", "")
    try:
        ws = await create_workspace(
            name=body.name, icon=body.icon,
            theme_color=body.theme_color, template=body.template,
        )
        return make_response(ws, request_id=rid)
    except Exception as e:
        if hasattr(e, "detail") and isinstance(e.detail, dict):
            return make_error(**e.detail, request_id=rid)
        raise


@router.get("/workspaces/{workspace_id}")
async def api_get_workspace(request: Request, workspace_id: str):
    rid = getattr(request.state, "request_id", "")
    ws = await get_workspace(workspace_id)
    if not ws:
        return make_error("WORKSPACE_NOT_FOUND", "工作间不存在", request_id=rid)
    return make_response(ws, request_id=rid)


@router.put("/workspaces/{workspace_id}")
async def api_update_workspace(request: Request, workspace_id: str, body: WorkspaceUpdate):
    rid = getattr(request.state, "request_id", "")
    updates = body.model_dump(exclude_none=True)
    ws = await update_workspace(workspace_id, updates)
    if not ws:
        return make_error("WORKSPACE_NOT_FOUND", "工作间不存在", request_id=rid)
    return make_response(ws, request_id=rid)


@router.delete("/workspaces/{workspace_id}", status_code=204)
async def api_delete_workspace(request: Request, workspace_id: str):
    rid = getattr(request.state, "request_id", "")
    deleted = await soft_delete_workspace(workspace_id)
    if not deleted:
        return make_error("WORKSPACE_NOT_FOUND", "工作间不存在", request_id=rid)
    return None


@router.get("/workspaces/templates")
async def api_get_templates(request: Request):
    rid = getattr(request.state, "request_id", "")
    templates = await get_templates()
    return make_response(templates, request_id=rid)
