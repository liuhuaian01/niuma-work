"""夜巡 API 路由

审计日志查询、规则管理、巡逻报告。
"""

from fastapi import APIRouter, Request, Query
from typing import Optional

from schemas.common import make_response, make_paginated_response, make_error
from utils import calculate_offset

router = APIRouter(prefix="/api/v1/patrol", tags=["夜巡"])


@router.get("/rules")
async def api_list_rules(request: Request):
    """列出所有夜巡规则及其状态。

    GET /api/v1/patrol/rules
    """
    rid = getattr(request.state, "request_id", "")

    try:
        from engine.night_patrol import get_patrol
        patrol = get_patrol()
        rules = patrol.list_rules()
        return make_response({"rules": rules, "total": len(rules)}, request_id=rid)
    except Exception as e:
        return make_error("PATROL_ERROR", str(e), request_id=rid)


@router.post("/rules/{rule_name}/toggle")
async def api_toggle_rule(request: Request, rule_name: str):
    """启用/禁用指定规则。

    POST /api/v1/patrol/rules/{rule_name}/toggle
    """
    rid = getattr(request.state, "request_id", "")

    try:
        from engine.night_patrol import get_patrol
        patrol = get_patrol()
        rules = patrol.list_rules()
        target = next((r for r in rules if r["name"] == rule_name), None)

        if not target:
            return make_error("RULE_NOT_FOUND", f"规则 '{rule_name}' 不存在", request_id=rid)

        if target["enabled"]:
            patrol.disable_rule(rule_name)
            return make_response({"rule": rule_name, "enabled": False}, request_id=rid)
        else:
            patrol.enable_rule(rule_name)
            return make_response({"rule": rule_name, "enabled": True}, request_id=rid)
    except Exception as e:
        return make_error("PATROL_ERROR", str(e), request_id=rid)


@router.get("/stats")
async def api_get_stats(request: Request):
    """获取夜巡统计信息。

    GET /api/v1/patrol/stats
    """
    rid = getattr(request.state, "request_id", "")

    try:
        from engine.night_patrol import get_patrol
        patrol = get_patrol()
        stats = patrol.get_stats()
        return make_response(stats, request_id=rid)
    except Exception as e:
        return make_error("PATROL_ERROR", str(e), request_id=rid)


@router.get("/events")
async def api_list_events(
    request: Request,
    workspace_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """查询审计事件。

    GET /api/v1/patrol/events?workspace_id=xxx&severity=error&category=sensitive_content
    """
    rid = getattr(request.state, "request_id", "")

    try:
        import sqlite3
        from config.settings import settings

        conn = sqlite3.connect(str(settings.DB_PATH))
        conn.row_factory = sqlite3.Row

        conditions = ["operation LIKE 'patrol_%'"]
        params: list = []

        if workspace_id:
            conditions.append("workspace_id = ?")
            params.append(workspace_id)
        if severity:
            conditions.append("result = ?")
            params.append(severity)
        if category:
            conditions.append("operation = ?")
            params.append(f"patrol_{category}")

        where = "WHERE " + " AND ".join(conditions)

        # 计数
        count_rows = conn.execute(f"SELECT COUNT(*) as cnt FROM audit_logs {where}", params)
        total = count_rows.fetchone()["cnt"]

        # 分页
        offset = calculate_offset(page, page_size)
        rows = conn.execute(
            f"SELECT * FROM audit_logs {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        )

        events = []
        for row in rows:
            import json
            detail = {}
            try:
                detail = json.loads(row["detail"]) if row["detail"] else {}
            except (json.JSONDecodeError, TypeError):
                pass

            events.append({
                "id": row["id"],
                "workspace_id": row["workspace_id"],
                "agent_id": row["agent_id"],
                "category": row["operation"].replace("patrol_", ""),
                "severity": row["result"],
                "message": row["target"],
                "detail": detail,
                "created_at": row["created_at"],
            })

        conn.close()

        return make_paginated_response(events, page, page_size, total, request_id=rid)
    except Exception as e:
        return make_error("PATROL_ERROR", str(e), request_id=rid)
