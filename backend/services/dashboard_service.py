"""看板数据聚合服务

Phase 1: 基础数据聚合
Phase 2: Token 趋势、模型分布、时间线
"""

from datetime import datetime, timezone, timedelta

from sqlalchemy import text

from db.database import get_engine
from utils import calculate_offset


async def get_overview() -> dict:
    """办公室概览数据"""
    engine = get_engine()

    async with engine.connect() as conn:
        # 活跃 Agent 数
        active_result = await conn.execute(
            text("SELECT COUNT(*) FROM agents WHERE status = 'online' AND deleted_at IS NULL")
        )
        active_agents = active_result.scalar() or 0

        # 总 Agent 数
        total_result = await conn.execute(
            text("SELECT COUNT(*) FROM agents WHERE deleted_at IS NULL")
        )
        total_agents = total_result.scalar() or 0

        # 今日 Token 消耗
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_tokens_result = await conn.execute(
            text(
                "SELECT COALESCE(SUM(token_count), 0) FROM chat_messages "
                "WHERE role = 'assistant' AND created_at LIKE :today"
            ),
            {"today": f"{today}%"},
        )
        today_tokens = today_tokens_result.scalar() or 0

        # 今日任务数
        today_tasks_result = await conn.execute(
            text(
                "SELECT COUNT(*) FROM orchestration_tasks "
                "WHERE status = 'completed' AND completed_at LIKE :today"
            ),
            {"today": f"{today}%"},
        )
        today_tasks = today_tasks_result.scalar() or 0

    return {
        "active_agents": active_agents,
        "total_agents": total_agents,
        "today_tokens": today_tokens,
        "token_limit": 200000,
        "token_percent": round(today_tokens / 200000 * 100, 1) if today_tokens else 0.0,
        "today_tasks": today_tasks,
        "security_score": 100,  # Phase 2 从审计引擎获取
    }


async def get_token_trends(workspace_id: str | None = None, days: int = 7) -> list:
    """Token 消耗趋势（近 N 天）"""
    engine = get_engine()

    async with engine.connect() as conn:
        # 生成日期序列
        now = datetime.now(timezone.utc)
        date_list = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]

        results = []
        for date_str in date_list:
            ws_filter = "AND workspace_id = :ws_id" if workspace_id else ""
            params = {"date": f"{date_str}%"}
            if workspace_id:
                params["ws_id"] = workspace_id

            # 按模型分组
            model_result = await conn.execute(
                text(
                    f"SELECT model, COALESCE(SUM(token_count), 0) as tokens "
                    f"FROM chat_messages WHERE role = 'assistant' "
                    f"AND created_at LIKE :date {ws_filter} "
                    f"GROUP BY model"
                ),
                params,
            )

            day_data = {
                "date": date_str,
                "deepseek": 0, "kimi": 0, "hunyuan": 0, "glm": 0,
                "total": 0,
            }
            for row in model_result:
                model_key = row.model or "deepseek"
                # 归一化模型名称
                if "deepseek" in model_key:
                    day_data["deepseek"] = row.tokens
                elif "moonshot" in model_key or "kimi" in model_key:
                    day_data["kimi"] = row.tokens
                elif "hunyuan" in model_key:
                    day_data["hunyuan"] = row.tokens
                elif "glm" in model_key:
                    day_data["glm"] = row.tokens
                day_data["total"] += row.tokens

            results.append(day_data)

        return results


async def get_model_distribution() -> dict:
    """模型调用分布"""
    engine = get_engine()

    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT model, COALESCE(SUM(token_count), 0) as tokens "
                "FROM chat_messages WHERE role = 'assistant' AND model IS NOT NULL "
                "GROUP BY model"
            ),
        )

        distribution = {}
        total = 0
        for row in result:
            model_key = row.model
            if "deepseek" in model_key:
                key = "deepseek"
            elif "moonshot" in model_key or "kimi" in model_key:
                key = "kimi"
            elif "hunyuan" in model_key:
                key = "hunyuan"
            elif "glm" in model_key:
                key = "glm"
            else:
                key = model_key

            distribution[key] = distribution.get(key, 0) + row.tokens
            total += row.tokens

        # 构建响应
        response = {}
        for model in ["deepseek", "kimi", "hunyuan", "glm"]:
            tokens = distribution.get(model, 0)
            response[model] = {
                "tokens": tokens,
                "percent": round(tokens / total * 100, 1) if total > 0 else 0,
            }
        response["total"] = total

        return response


async def get_timeline(workspace_id: str | None = None, page: int = 1, page_size: int = 20) -> list:
    """工作间动态时间线"""
    engine = get_engine()
    offset = calculate_offset(page, page_size)

    async with engine.connect() as conn:
        ws_filter = "AND ot.workspace_id = :ws_id" if workspace_id else ""
        params: dict = {"limit": page_size, "offset": offset}
        if workspace_id:
            params["ws_id"] = workspace_id

        # 从编排任务获取时间线
        result = await conn.execute(
            text(
                f"SELECT ot.id, ot.workspace_id, w.name as workspace_name, "
                f"ot.strategy as event_type, ot.description as title, "
                f"ot.status, ot.total_tokens as tokens_used, "
                f"ot.completed_at as created_at "
                f"FROM orchestration_tasks ot "
                f"LEFT JOIN workspaces w ON ot.workspace_id = w.id "
                f"WHERE ot.status = 'completed' {ws_filter} "
                f"ORDER BY ot.completed_at DESC "
                f"LIMIT :limit OFFSET :offset"
            ),
            params,
        )

        timeline = []
        for row in result:
            timeline.append({
                "id": row.id,
                "workspace_id": row.workspace_id,
                "workspace_name": row.workspace_name or "",
                "event_type": "task_completed",
                "title": row.title or f"编排任务完成 ({row.strategy})",
                "description": "",
                "agent_name": "Director",
                "tokens_used": row.tokens_used or 0,
                "created_at": row.created_at,
            })

        return timeline
