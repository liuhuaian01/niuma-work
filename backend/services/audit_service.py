"""审计服务

Phase 1: Token 消耗审计 + 安全配置审计（基础版）
Phase 2: 完整审计引擎（代码审计/流程审计/防蒸馏）
"""

from datetime import datetime, timezone, timedelta

from sqlalchemy import text

from db.database import get_engine


async def audit_token(days: int = 7, workspace_id: str | None = None) -> dict:
    """Token 消耗审计"""
    engine = get_engine()
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")

    async with engine.connect() as conn:
        ws_filter = "AND workspace_id = :ws_id" if workspace_id else ""
        params: dict = {"since": since}
        if workspace_id:
            params["ws_id"] = workspace_id

        # 总消耗
        total_result = await conn.execute(
            text(
                f"SELECT COALESCE(SUM(token_count), 0) FROM chat_messages "
                f"WHERE role = 'assistant' AND created_at >= :since {ws_filter}"
            ),
            params,
        )
        total_tokens = total_result.scalar() or 0

        # 每日明细
        daily_result = await conn.execute(
            text(
                f"SELECT DATE(created_at) as day, COALESCE(SUM(token_count), 0) as tokens "
                f"FROM chat_messages WHERE role = 'assistant' "
                f"AND created_at >= :since {ws_filter} "
                f"GROUP BY DATE(created_at) ORDER BY day"
            ),
            params,
        )
        daily_breakdown = [
            {"date": str(row.day), "tokens": row.tokens}
            for row in daily_result
        ]

        # 模型分布
        model_result = await conn.execute(
            text(
                f"SELECT model, COALESCE(SUM(token_count), 0) as tokens "
                f"FROM chat_messages WHERE role = 'assistant' "
                f"AND created_at >= :since {ws_filter} "
                f"GROUP BY model"
            ),
            params,
        )
        model_distribution = {}
        for row in model_result:
            key = row.model or "unknown"
            model_distribution[key] = row.tokens

        # 异常检测：单条消息 Token 过高
        anomalies = []
        avg_result = await conn.execute(
            text(
                f"SELECT AVG(token_count) as avg_tokens FROM chat_messages "
                f"WHERE role = 'assistant' AND token_count > 0 "
                f"AND created_at >= :since {ws_filter}"
            ),
            params,
        )
        avg_tokens = avg_result.scalar() or 0

        if avg_tokens > 0:
            anomaly_result = await conn.execute(
                text(
                    f"SELECT id, token_count FROM chat_messages "
                    f"WHERE role = 'assistant' AND token_count > :threshold "
                    f"AND created_at >= :since {ws_filter} LIMIT 5"
                ),
                {**params, "threshold": int(avg_tokens * 5)},
            )
            for row in anomaly_result:
                anomalies.append({
                    "type": "session_oversize",
                    "message_id": row.id,
                    "tokens": row.token_count,
                    "avg_daily": int(avg_tokens),
                    "severity": "warning" if row.token_count < avg_tokens * 10 else "critical",
                })

        # 优化建议
        suggestions = []
        if total_tokens > 0:
            # 检测是否有更贵的模型被频繁使用
            for model, tokens in model_distribution.items():
                if "kimi" in (model or "") and tokens > total_tokens * 0.3:
                    suggestions.append({
                        "text": f"Kimi消耗占{round(tokens/total_tokens*100)}%，建议切回DeepSeek节省成本",
                        "estimated_save_tokens": int(tokens * 0.2),
                    })

    return {
        "total_tokens": total_tokens,
        "daily_breakdown": daily_breakdown,
        "model_distribution": model_distribution,
        "anomalies": anomalies,
        "suggestions": suggestions,
    }


async def audit_security() -> dict:
    """安全配置审计"""
    engine = get_engine()

    checks = []
    score = 100

    async with engine.connect() as conn:
        # 检查1: Pi 准则覆盖
        ws_result = await conn.execute(
            text("SELECT id, name FROM workspaces WHERE deleted_at IS NULL")
        )
        workspaces = list(ws_result)
        if not workspaces:
            checks.append({
                "name": "Pi准则覆盖",
                "status": "warn",
                "detail": "无活跃工作间",
            })
            score -= 5
        else:
            # 检查所有工作间的安全级别
            sec_result = await conn.execute(
                text(
                    "SELECT wc.security_level, COUNT(*) as cnt "
                    "FROM workspace_configs wc "
                    "JOIN workspaces w ON wc.workspace_id = w.id "
                    "WHERE w.deleted_at IS NULL GROUP BY wc.security_level"
                ),
            )
            security_levels = {row.security_level: row.cnt for row in sec_result}
            if security_levels.get("fast", 0) > 0:
                checks.append({
                    "name": "Pi准则覆盖",
                    "status": "warn",
                    "detail": f"有{security_levels['fast']}个工作间使用fast模式，建议balanced以上",
                })
                score -= 10
            else:
                checks.append({
                    "name": "Pi准则覆盖",
                    "status": "pass",
                    "detail": f"balanced模式覆盖所有{len(workspaces)}个工作间",
                })

        # 检查2: API Key 配置状态
        from config.settings import settings
        configured_keys = sum(1 for key in [
            settings.DEEPSEEK_API_KEY, settings.KIMI_API_KEY,
            settings.HUNYUAN_API_KEY, settings.GLM_API_KEY,
        ] if key)
        total_keys = 4
        if configured_keys == total_keys:
            checks.append({
                "name": "API Key过期",
                "status": "pass",
                "detail": f"{configured_keys}/{total_keys} 密钥已配置",
            })
        else:
            checks.append({
                "name": "API Key过期",
                "status": "warn",
                "detail": f"{configured_keys}/{total_keys} 密钥已配置，降级链可能中断",
            })
            score -= 15

        # 检查3: 审计日志完整性
        log_result = await conn.execute(
            text("SELECT COUNT(*) FROM audit_logs")
        )
        log_count = log_result.scalar() or 0
        checks.append({
            "name": "审计日志",
            "status": "pass" if log_count > 0 else "warn",
            "detail": f"已记录 {log_count} 条审计日志",
        })
        if log_count == 0:
            score -= 5

    # 评级
    if score >= 90:
        level = "healthy"
    elif score >= 70:
        level = "warning"
    else:
        level = "critical"

    return {
        "score": score,
        "level": level,
        "checks": checks,
        "suggestions": [],
    }
