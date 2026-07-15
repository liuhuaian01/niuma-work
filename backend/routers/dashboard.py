"""看板数据路由 - 真实数据"""

from fastapi import APIRouter, Request, Query
from sqlalchemy import text

from db.database import get_engine
from schemas.common import make_response
from config.settings import settings
from utils import calculate_offset

router = APIRouter()


@router.get("/dashboard/overview")
async def api_overview(request: Request):
    rid = getattr(request.state, "request_id", "")
    engine = get_engine()

    async with engine.connect() as conn:
        # 活跃 Agent 数
        active_agents = await conn.execute(
            text("SELECT COUNT(*) FROM agents WHERE deleted_at IS NULL AND status = 'online'")
        )
        active_count = active_agents.scalar() or 0

        # 总 Agent 数
        total_agents = await conn.execute(
            text("SELECT COUNT(*) FROM agents WHERE deleted_at IS NULL")
        )
        total_agent_count = total_agents.scalar() or 0

        # 今日 Token 消耗
        today = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%d")
        today_tokens_result = await conn.execute(
            text(
                "SELECT COALESCE(SUM(token_count), 0) FROM chat_messages "
                "WHERE role = 'assistant' AND status IN ('completed', 'stopped') "
                "AND created_at >= :today_start"
            ),
            {"today_start": f"{today}T00:00:00Z"},
        )
        today_tokens = today_tokens_result.scalar() or 0

        # 今日任务数
        today_tasks = await conn.execute(
            text(
                "SELECT COUNT(*) FROM chat_messages "
                "WHERE role = 'user' AND created_at >= :today_start"
            ),
            {"today_start": f"{today}T00:00:00Z"},
        )
        today_task_count = today_tasks.scalar() or 0

        token_budget = settings.DEFAULT_TOKEN_BUDGET
        token_percent = round((today_tokens / token_budget * 100), 2) if token_budget > 0 else 0

        return make_response(
            {
                "active_agents": active_count,
                "total_agents": total_agent_count,
                "today_tokens": today_tokens,
                "token_limit": token_budget,
                "token_percent": token_percent,
                "today_tasks": today_task_count,
                "security_score": 100,  # Phase 2: 从审计模块计算
            },
            request_id=rid,
        )


@router.get("/dashboard/token-trends")
async def api_token_trends(
    request: Request,
    workspace_id: str = Query(None),
    days: int = Query(7, ge=1, le=30),
):
    rid = getattr(request.state, "request_id", "")
    engine = get_engine()

    async with engine.connect() as conn:
        # 按日期和模型分组统计 Token
        if workspace_id:
            result = await conn.execute(
                text(
                    "SELECT DATE(created_at) as date, model, COALESCE(SUM(token_count), 0) as tokens "
                    "FROM chat_messages "
                    "WHERE role = 'assistant' AND status IN ('completed', 'stopped') "
                    "AND workspace_id = :ws_id "
                    "AND created_at >= datetime('now', :interval) "
                    "GROUP BY DATE(created_at), model "
                    "ORDER BY date"
                ),
                {"ws_id": workspace_id, "interval": f"-{days} days"},
            )
        else:
            result = await conn.execute(
                text(
                    "SELECT DATE(created_at) as date, model, COALESCE(SUM(token_count), 0) as tokens "
                    "FROM chat_messages "
                    "WHERE role = 'assistant' AND status IN ('completed', 'stopped') "
                    "AND created_at >= datetime('now', :interval) "
                    "GROUP BY DATE(created_at), model "
                    "ORDER BY date"
                ),
                {"interval": f"-{days} days"},
            )

        # 按日期聚合
        daily_data: dict[str, dict] = {}
        for row in result:
            date = row.date
            if date not in daily_data:
                daily_data[date] = {"date": date, "deepseek": 0, "kimi": 0, "hunyuan": 0, "glm": 0, "total": 0}

            model = row.model or "deepseek-v4-pro"
            tokens = row.tokens or 0

            # 模型名映射到简短名
            if "deepseek" in model:
                daily_data[date]["deepseek"] += tokens
            elif "moonshot" in model or model == "kimi":
                daily_data[date]["kimi"] += tokens
            elif "hunyuan" in model:
                daily_data[date]["hunyuan"] += tokens
            elif "glm" in model:
                daily_data[date]["glm"] += tokens
            else:
                daily_data[date]["deepseek"] += tokens  # 默认归入 deepseek

            daily_data[date]["total"] += tokens

        return make_response(list(daily_data.values()), request_id=rid)


@router.get("/dashboard/model-distribution")
async def api_model_distribution(request: Request):
    rid = getattr(request.state, "request_id", "")
    engine = get_engine()

    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT model, COALESCE(SUM(token_count), 0) as tokens "
                "FROM chat_messages "
                "WHERE role = 'assistant' AND status IN ('completed', 'stopped') "
                "GROUP BY model"
            ),
        )

        model_data = {"deepseek": 0, "kimi": 0, "hunyuan": 0, "glm": 0}
        total = 0

        for row in result:
            model = row.model or ""
            tokens = row.tokens or 0
            total += tokens

            if "deepseek" in model:
                model_data["deepseek"] += tokens
            elif "moonshot" in model or model == "kimi":
                model_data["kimi"] += tokens
            elif "hunyuan" in model:
                model_data["hunyuan"] += tokens
            elif "glm" in model:
                model_data["glm"] += tokens
            else:
                model_data["deepseek"] += tokens

        distribution = {}
        for name, tokens in model_data.items():
            pct = round((tokens / total * 100), 1) if total > 0 else 0
            distribution[name] = {"tokens": tokens, "percent": pct}

        distribution["total"] = total
        return make_response(distribution, request_id=rid)


@router.get("/dashboard/savings")
async def api_token_savings(request: Request):
    """Token 节约报告。"""
    rid = getattr(request.state, "request_id", "")
    from engine.token_savings import savings_engine
    return make_response(savings_engine.get_stats(), request_id=rid)


@router.get("/dashboard/timeline")
async def api_timeline(
    request: Request,
    workspace_id: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    rid = getattr(request.state, "request_id", "")
    engine = get_engine()
    offset = calculate_offset(page, page_size)

    async with engine.connect() as conn:
        # 组合消息和任务事件
        if workspace_id:
            result = await conn.execute(
                text(
                    "SELECT cm.id, cm.workspace_id, cm.role, cm.content, cm.model, "
                    "cm.token_count, cm.created_at, "
                    "w.name as workspace_name "
                    "FROM chat_messages cm "
                    "LEFT JOIN workspaces w ON cm.workspace_id = w.id "
                    "WHERE cm.workspace_id = :ws_id AND cm.role = 'assistant' "
                    "AND cm.status IN ('completed', 'stopped') "
                    "ORDER BY cm.created_at DESC "
                    "LIMIT :limit OFFSET :offset"
                ),
                {"ws_id": workspace_id, "limit": page_size, "offset": offset},
            )
        else:
            result = await conn.execute(
                text(
                    "SELECT cm.id, cm.workspace_id, cm.role, cm.content, cm.model, "
                    "cm.token_count, cm.created_at, "
                    "w.name as workspace_name "
                    "FROM chat_messages cm "
                    "LEFT JOIN workspaces w ON cm.workspace_id = w.id "
                    "WHERE cm.role = 'assistant' "
                    "AND cm.status IN ('completed', 'stopped') "
                    "ORDER BY cm.created_at DESC "
                    "LIMIT :limit OFFSET :offset"
                ),
                {"limit": page_size, "offset": offset},
            )

        events = []
        for row in result:
            content_preview = (row.content or "")[:100]
            events.append({
                "id": row.id,
                "workspace_id": row.workspace_id,
                "workspace_name": row.workspace_name or "全局对话",
                "event_type": "message_completed",
                "title": f"AI 回复 ({row.model or 'unknown'})",
                "description": content_preview,
                "tokens_used": row.token_count or 0,
                "created_at": row.created_at,
            })

        return make_response(events, request_id=rid)


# ===== P1-22: SSRF 防护统计 =====

@router.get("/dashboard/ssrf-stats")
async def api_ssrf_stats(request: Request):
    """获取 SSRF 防护统计——被拦截次数、白名单、DNS 缓存 """
    rid = getattr(request.state, "request_id", "")
    from engine.ssrf_guard import ssrf_guard
    return make_response(ssrf_guard.get_stats(), request_id=rid)
