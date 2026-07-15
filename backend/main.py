"""
超级牛马 (Super Niuma) — FastAPI 应用入口

太极引擎 v1.7: Phase 2 — 智能进化区 + 递归自进化 + GoalLoop
启动方式: python main.py
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from config.settings import settings
from config.logging_config import setup_logging
from db.database import init_db, log_pool_status_periodically
from engine.taiji import taiji
from middleware.request_id import RequestIDMiddleware
from middleware.error_handler import register_exception_handlers
from middleware.capability_middleware import CapabilityMiddleware
from middleware.license_middleware import LicenseMiddleware
from middleware.rate_limit import RateLimitMiddleware
from middleware.request_size import RequestSizeMiddleware
from middleware.workspace_isolation import WorkspaceIsolationMiddleware
from middleware.agent_auth import AgentAuthMiddleware
from engine.agent_registry import agent_registry
from engine.lazy_loader import lazy_get
from model_adapter.registry import model_registry
from routers import (
    health,
    workspaces,
    agents,
    workspace_config,
    chat,
    onboarding,
    skills,
    user_settings,
    dashboard,
    capabilities,
    audit,
    backup,
    ws,
    background_tasks,
    memory,
    license,
    consciousness,
    models,
    evolution,
    goal_loop,
    mesh,
    emergence,
    drift,
    patrol,
    skill_forge,
    api_keys,
    agent_identity,
    swarm,
    mcp,
    agent_card,   # v2.0: Agent Card
    files,        # v2.1: 文件管理
    connections,  # v2.1: 连接管理
    experts,      # v2.1: 专家广场
    model_download,  # P0-4: 模型下载服务
)
# P2-15: governance 拆分为两个独立路由器
from routers.governance import web_access_router, budget_router
from version import VERSION

# 应用启动时间
_start_time = time.time()

# 进化引擎锁（防止竞态条件）
_evolution_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 初始化日志系统(最先执行)
    setup_logging()
    
    # 启动时初始化
    await init_db()

    # 数据库迁移检查
    from schema_migrations.migrator import check_and_migrate
    await check_and_migrate()

    model_registry.initialize()

    # v2.1: llama.cpp 本地推理引擎启动
    from engine.llama_manager import llama_manager
    app.state.llama_manager = llama_manager
    llama_ok = await llama_manager.start()
    if llama_ok:
        from model_adapter.openai_compat import register_local_models
        registered = register_local_models(settings.LLAMA_MODELS_DIR, model_registry._adapters)
        startup_logger = logging.getLogger("niuma.startup")
        startup_logger.info("llama.cpp: 本地模型注册完成 (%d 个)", registered)
    else:
        startup_logger = logging.getLogger("niuma.startup")
        startup_logger.info("llama.cpp: 无本地模型可用，跳过（用户可使用云端 API）")

    # OTel Exporter 初始化（惰性加载——非核心能力，失败不阻塞）
    try:
        otel_tracer = lazy_get("engine.otel_tracer", "tracer")
        otel_tracer.setup_exporter()
    except Exception:
        startup_logger.debug("OTel 初始化跳过（非核心模块）")

    await taiji.init(contributing=False)   # 太极网格默认关闭，用户主动开启

    # 太极网格实例存入 app.state（供 mesh router 使用）
    app.state.taiji_mesh = taiji.mesh

    # 太极引擎持久化（修复 Bug：返回值不能丢弃）
    from engine.chat_hooks import get_chat_integration
    ci = get_chat_integration(str(settings.TAIJI_DB_PATH))
    app.state.chat_integration = ci

    # Token 预算初始化默认值（在独立线程中执行，避免事件循环冲突）
    from engine.token_budget import token_budget
    for agent_id, budget in [("writer-default", 30000), ("coder-default", 50000), ("analyst-default", 40000)]:
        await asyncio.to_thread(token_budget.set_agent_budget, agent_id, budget)

    # 用户初始化——如果没有用户数据则创建（首次启动开始试用）
    from services.user_manager import user_manager
    if not user_manager.current_user:
        user_manager.init_device()

    # 隐私同意——加载现有状态（首次启动时触发通知）
    from engine.privacy_consent import privacy_consent
    privacy_consent.load()  # 不阻塞——加载持久化状态
    onboarding_data = privacy_consent.get_onboarding_data()
    startup_logger = logging.getLogger("niuma.startup")
    
    # P1-22: SSRF 防护初始化
    from engine.ssrf_guard import ssrf_guard, add_allowlist_host
    # 白名单: llama.cpp server + 本地服务
    add_allowlist_host("localhost")
    add_allowlist_host("127.0.0.1")
    app.state.ssrf_guard = ssrf_guard
    startup_logger.info("SSRF 防护已就绪 | allowlist=%s", ssrf_guard.get_stats())
    
    if onboarding_data:
        startup_logger.info(f"首次启动——需要用户隐私确认: {onboarding_data['title']}")
        startup_logger.info("用户可在设置页面随时开关")
    else:
        consented = privacy_consent.is_consented()
        startup_logger.info(f"隐私同意状态: {'已同意' if consented else '已拒绝/未选择'}")

    # 递归自进化引擎（惰性加载——v2.0+ 能力，启动不阻塞）
    _recursive_evolution = None
    try:
        _recursive_evolution = lazy_get("engine.recursive_evolution", "recursive_evolution")
        await _recursive_evolution.initialize()
        evolution_status = _recursive_evolution.get_status()
        startup_logger.info(f"递归自进化: {evolution_status['chat_counter']}次对话, "
              f"{evolution_status['micro_cycles_completed']}微周期, "
              f"{evolution_status['daily_cycles_completed']}日周期")
    except Exception:
        startup_logger.debug("递归自进化初始化跳过（非核心模块）")

    # 上下文漂移检测引擎——从持久化恢复
    from engine.context_drift import context_drift
    await context_drift.initialize()
    drift_status = context_drift.get_status()
    startup_logger.info(f"上下文漂移检测: {drift_status['total_checks']}次检测, "
          f"{drift_status['active_sessions']}活跃会话, {drift_status['red_alerts']}次红色告警")

    # GoalLoop 引擎（惰性加载——v2.0 能力，启动不阻塞）
    _goal_loop = None
    try:
        _goal_loop = lazy_get("engine.goal_loop_engine", "goal_loop")
        await _goal_loop.initialize()
    except Exception:
        startup_logger.debug("GoalLoop 初始化跳过（非核心模块）")

    # 涌现引擎（惰性加载——v2.0+ 能力，启动不阻塞）
    try:
        emergence_engine = lazy_get("engine.emergence", "emergence_engine")
        await emergence_engine.init()
        app.state.emergence = emergence_engine
    except Exception:
        startup_logger.debug("涌现引擎初始化跳过（非核心模块）")
        app.state.emergence = None

    # Agent 身份注册表——初始化（P1-7）
    await agent_registry.initialize()
    app.state.agent_registry = agent_registry
    startup_logger.info(f"Agent 身份注册表已初始化: {agent_registry.get_stats()['active_agents']} active")

    # MCP 安全认证层（惰性加载——v2.0 能力，启动不阻塞）
    try:
        mcp_auth = lazy_get("engine.mcp_auth", "mcp_auth")
        await mcp_auth.initialize()
        app.state.mcp_auth = mcp_auth
        startup_logger.info(f"MCP 认证层已初始化: {mcp_auth.get_stats()['active_registrations']} registered servers")
    except Exception:
        startup_logger.debug("MCP 认证层初始化跳过（非核心模块）")
        app.state.mcp_auth = None

    # MCP Registry（惰性加载——v2.0 能力，启动不阻塞）
    try:
        mcp_registry = lazy_get("engine.mcp_client", "mcp_registry")
        await mcp_registry.initialize()
        app.state.mcp_registry = mcp_registry
        startup_logger.info(f"MCP Registry 已初始化: {len(mcp_registry.list_servers())} registered servers")
    except Exception:
        startup_logger.debug("MCP Registry 初始化跳过（非核心模块）")
        app.state.mcp_registry = None

    # 太虚境核心（惰性加载——L3 知识库，启动不阻塞）
    try:
        init_taixu = lazy_get("engine.taixu_core", "init_taixu")
        await init_taixu()
        app.state.taixu = "ready"
    except Exception:
        startup_logger.debug("太虚境初始化跳过（非核心模块）")
        app.state.taixu = None

    # 工作间隔离缓存——从 DB 加载合法工作间列表
    from middleware.workspace_isolation import refresh_workspace_cache
    await refresh_workspace_cache()

    # Hermes 适配器——初始化兼容性检查
    from engine.hermes_adapter import hermes_adapter
    report = hermes_adapter.get_absorption_report()
    startup_logger.info(f"HermesAdapter: {report['absorbed']} absorbed + {report['taiji_only']} exclusive "
          f"= {report['independence_score']} independence, {report['pending']} pending")

    startup_logger.info(f"TaiJi Engine v1.7 — DB={settings.TAIJI_DB_PATH} · evolution=ON goalloop=ON mesh=READY emergence=ON taixu=ON · flags: fetch=OFF search=OFF mcp=OFF")

    # 保存启动时间
    app.state.start_time = _start_time

    # 后台任务：每小时检查是否需要执行日周期
    async def _daily_evolution_loop():
        """每小时检查一次：如果今天还没跑日周期且引擎已初始化，触发。"""
        import logging
        logger = logging.getLogger("niuma.evolution")
        while True:
            await asyncio.sleep(3600)  # 每小时
            try:
                async with _evolution_lock:  # 加锁保护共享状态
                    if _recursive_evolution is not None and _recursive_evolution._is_initialized:
                        await _recursive_evolution.trigger_daily_cycle()
                    if _goal_loop is not None:
                        await _goal_loop.periodic_review()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Daily evolution loop error: {e}", exc_info=True)

    app.state._daily_evolution_task = asyncio.create_task(_daily_evolution_loop())

    # 后台任务：连接池监控（每5分钟记录一次）
    # 仅在 DEBUG 模式下启用，生产环境可通过环境变量控制
    if settings.DEBUG or os.getenv("NIUMA_POOL_MONITOR", "false").lower() == "true":
        app.state._pool_monitor_task = asyncio.create_task(
            log_pool_status_periodically(interval_seconds=300)
        )
        print("[Niuma] Connection pool monitor enabled (interval: 300s)")
    else:
        app.state._pool_monitor_task = None

    yield

    # 优雅关闭——确保数据不丢失
    logger = logging.getLogger("niuma.shutdown")
    logger.info("Shutting down Taiji Engine...")

    # 1. 停止后台进化任务
    try:
        task = getattr(app.state, "_daily_evolution_task", None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("Daily evolution task stopped")
    except Exception:
        logger.exception("Failed to cancel daily evolution task")

    # 1.5 停止连接池监控任务
    try:
        task = getattr(app.state, "_pool_monitor_task", None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            logger.info("Pool monitor task stopped")
    except Exception:
        logger.exception("Failed to cancel pool monitor task")

    # 1.6 停止 llama.cpp 推理引擎
    llama_mgr = getattr(app.state, "llama_manager", None)
    if llama_mgr:
        try:
            await llama_mgr.stop()
            logger.info("llama.cpp server stopped")
        except Exception:
            logger.exception("Failed to stop llama.cpp server")

    # 2. 停止 EngineWatchdog（如果存在且可停止）
    try:
        from engine.engine_watchdog import watchdog
        # EngineWatchdog 无后台线程，记录统计即可
        stats = watchdog.get_stats()
        logger.info(f"Watchdog stats on shutdown: {json.dumps(stats)}")
    except Exception:
        logger.exception("Failed to collect watchdog stats")

    # 2. 清除活跃的 SSE 流
    from routers.chat import _active_streams
    for mid, event in list(_active_streams.items()):
        try:
            event.set()
        except Exception:
            logger.exception(f"Failed to clear stream {mid}")
    _active_streams.clear()
    logger.info(f"Cleared {len(_active_streams)} active streams")

    # 3. 执行日志 flush
    if ci:
        try:
            today_records = len(ci.logger.get_today_records())
            logger.info(f"Flushed {today_records} execution records")
        except Exception:
            logger.exception("Failed to flush execution records")

    # 4. DB 引擎关闭
    from db.database import get_engine
    try:
        await get_engine().dispose()
    except Exception:
        logger.exception("Failed to dispose DB engine")

    # 5. 太极网格优雅退出
    try:
        await taiji.shutdown()
    except Exception:
        logger.exception("Failed to drain Taiji Mesh")


app = FastAPI(
    title="Super Niuma API",
    description="超级牛马 AI 工作台 — 后端 API",
    version=VERSION,
    lifespan=lifespan,
)

# ============================================================
# 中间件注册（顺序严格：CORS 必须在第一个处理 OPTIONS 预检）
# ============================================================
# 1. CORS — 生产环境通过 NIAMA_CORS_ORIGINS 配置
_cors_origins = os.getenv("NIAMA_CORS_ORIGINS", "").split(",") if os.getenv("NIAMA_CORS_ORIGINS") else [
    "http://localhost:18080",
    "http://127.0.0.1:18080",
    "http://localhost:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)
# 2. 请求ID追踪
app.add_middleware(RequestIDMiddleware)
# 3. 请求速率限制——防止暴力/DDoS
app.add_middleware(RateLimitMiddleware)
# 4. 请求体大小限制——防止大载荷攻击
app.add_middleware(RequestSizeMiddleware)
# 5. 许可证检查——所有API保护
app.add_middleware(LicenseMiddleware)
# 6. 工作间隔离——校验workspace_id合法性
app.add_middleware(WorkspaceIsolationMiddleware)
# 7. 太极引擎: 能力开关
app.add_middleware(CapabilityMiddleware)
# 8. Agent 身份认证 (P1-7: Agent 身份注册表)
app.add_middleware(AgentAuthMiddleware, agent_registry=agent_registry)
# 9. GZip压缩（最后一个压缩响应体）
app.add_middleware(GZipMiddleware, minimum_size=1024)

# 异常处理
register_exception_handlers(app)

# 路由注册
app.include_router(health.router, prefix="/api/v1", tags=["健康检查"])
app.include_router(workspaces.router, prefix="/api/v1", tags=["工作间"])
app.include_router(agents.router, prefix="/api/v1", tags=["Agent"])
app.include_router(workspace_config.router, prefix="/api/v1", tags=["工作间配置"])
app.include_router(chat.router, prefix="/api/v1", tags=["对话"])
app.include_router(skills.router, prefix="/api/v1", tags=["技能"])
app.include_router(user_settings.router, prefix="/api/v1", tags=["设置"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["看板"])
app.include_router(audit.router, prefix="/api/v1", tags=["审计"])
app.include_router(backup.router, prefix="/api/v1", tags=["备份"])
app.include_router(ws.router, prefix="/api/v1", tags=["WebSocket"])
app.include_router(background_tasks.router, prefix="/api/v1", tags=["后台任务"])
app.include_router(memory.router, prefix="/api/v1", tags=["记忆引擎"])
app.include_router(license.router, prefix="/api/v1/license", tags=["许可证"])
app.include_router(capabilities.router, tags=["能力开关"])
# P2-15: governance 拆分为精确前缀的 web_access + budget 路由器
app.include_router(web_access_router, tags=["天道法则·外网访问"])
app.include_router(budget_router, tags=["天道法则·Token预算"])
app.include_router(consciousness.router, tags=["意识"])
app.include_router(models.router, tags=["模型"])
app.include_router(evolution.router, tags=["进化回传"])
app.include_router(goal_loop.router, tags=["目标循环"])
app.include_router(onboarding.router, prefix="/api/v1", tags=["引导"])
app.include_router(mesh.router, tags=["太极网格"])
app.include_router(emergence.router, tags=["涌现引擎"])
app.include_router(drift.router, tags=["上下文漂移"])
app.include_router(patrol.router, tags=["夜巡"])
app.include_router(skill_forge.router, tags=["自化·技能创建"])
app.include_router(api_keys.router, tags=["API密钥管理"])
app.include_router(agent_identity.router, tags=["Agent 身份"])
app.include_router(swarm.router, tags=["Swarm 编排"])
app.include_router(mcp.router, tags=["MCP工具接入"])
app.include_router(agent_card.router, tags=["Agent Card"])
# v2.1: 前端对接路由
app.include_router(files.router, prefix="/api/v1", tags=["文件管理"])
app.include_router(connections.router, prefix="/api/v1", tags=["连接管理"])
app.include_router(experts.router, prefix="/api/v1", tags=["专家广场"])
app.include_router(model_download.router, prefix="/api/v1", tags=["模型下载"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL,
    )
