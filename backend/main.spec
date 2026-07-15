# -*- mode: python ; coding: utf-8 -*-
"""
Super Niuma Backend — PyInstaller Spec
v0.9.0-dev → v1.0.0-alpha
"""
import sys
from pathlib import Path

_block_cipher = None

# Paths
ROOT = Path(SPECPATH)
FRONTEND_DIST = ROOT.parent / "frontend-vue" / "dist"
DATA_DIR = ROOT / "data"
ENGINE_DIR = ROOT / "engine"

a = Analysis(
    ['main.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(FRONTEND_DIST), 'frontend'),
        (str(ROOT / 'schema_migrations' / 'V001__migration.sql'), 'schema_migrations'),
        (str(ROOT / 'db' / 'knowledge_schema.sql'), 'db'),
    ],
    hiddenimports=[
        # === config ===
        "config.settings", "config.logging_config", "config.constants",
        # === db ===
        "db.database",
        # === engine — all 72 modules ===
        "engine", "engine.aba", "engine.aba_anchor", "engine.agent_card",
        "engine.agent_registry", "engine.allocator_repository", "engine.asi_index",
        "engine.async_db", "engine.attention_engine", "engine.capability_flags",
        "engine.ccr_store", "engine.chat_hooks", "engine.closure_engine",
        "engine.context_drift", "engine.cross_workspace", "engine.dar_router",
        "engine.data_lifecycle", "engine.distillation", "engine.domain_knowledge",
        "engine.dynamic_balancer", "engine.dynamic_degradation",
        "engine.embedding_engine", "engine.emergence", "engine.engine_watchdog",
        "engine.execution_log", "engine.execution_repository", "engine.failure_driver",
        "engine.fallback_cost", "engine.goal_loop_engine", "engine.healing_tracker",
        "engine.hermes_adapter", "engine.honcho_modeler", "engine.hook_registry",
        "engine.hybrid_retrieval", "engine.instruction_cache",
        "engine.knowledge_quality", "engine.knowledge_repository",
        "engine.l3_knowledge", "engine.l3_profile", "engine.lazy_loader",
        "engine.llama_manager", "engine.local_answer_check",
        "engine.mcp_auth", "engine.mcp_client", "engine.memory_loader",
        "engine.meta_team", "engine.model_router", "engine.night_patrol",
        "engine.otel_tracer", "engine.owasp_compliance", "engine.privacy_consent",
        "engine.recursive_evolution", "engine.reflection", "engine.rule_router",
        "engine.runtime_interface", "engine.scene_chunker",
        "engine.self_evolution", "engine.self_healing", "engine.semantic_grader",
        "engine.skill_forge", "engine.skill_generator", "engine.skills_adapter",
        "engine.smart_allocator", "engine.ssrf_guard", "engine.swarm_orchestrator",
        "engine.taiji", "engine.taiji_mesh", "engine.taixu_core",
        "engine.telemetry_hub", "engine.time_graph", "engine.token_budget",
        "engine.token_savings",
        # === middleware ===
        "middleware.agent_auth", "middleware.capability_middleware",
        "middleware.error_handler", "middleware.license_middleware",
        "middleware.rate_limit", "middleware.request_id",
        "middleware.request_size", "middleware.workspace_isolation",
        # === model_adapter ===
        "model_adapter", "model_adapter.base", "model_adapter.fallback",
        "model_adapter.openai_compat", "model_adapter.registry",
        "model_adapter.token_counter",
        # === routers ===
        "routers.agent_card", "routers.agent_identity", "routers.agents",
        "routers.api_keys", "routers.audit", "routers.background_tasks",
        "routers.backup", "routers.capabilities", "routers.chat",
        "routers.connections", "routers.consciousness", "routers.dashboard",
        "routers.data_lifecycle", "routers.drift", "routers.emergence",
        "routers.evolution", "routers.experts", "routers.files",
        "routers.goal_loop", "routers.governance", "routers.health",
        "routers.license", "routers.mcp", "routers.memory", "routers.mesh",
        "routers.model_download", "routers.models", "routers.onboarding",
        "routers.patrol", "routers.skill_forge", "routers.skills",
        "routers.swarm", "routers.user_settings", "routers.workspace_config",
        "routers.workspaces", "routers.ws",
        # === services ===
        "services", "services.agent_service", "services.artifact_service",
        "services.audit_service", "services.background_task_service",
        "services.backup_service", "services.chat_service",
        "services.dashboard_service", "services.skill_service",
        "services.user_manager", "services.workspace_service",
        "services.memory", "services.memory.compression_engine",
        "services.memory.l1_session_memory", "services.memory.memory_service",
        # === schema_migrations ===
        "schema_migrations", "schema_migrations.migrator",
        # === schemas ===
        "schemas", "schemas.common", "schemas.chat", "schemas.workspace",
        "schemas.skill", "schemas.settings_schema",
        # === top-level ===
        "version", "utils",
        # === third-party ===
        "huggingface_hub", "httpx", "aiofiles", "aiosqlite",
        "sqlalchemy", "fastapi", "uvicorn", "pydantic",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'PyQt5', 'PyQt6', 'wx', 'IPython',
        'jupyter', 'notebook', 'matplotlib', 'numpy', 'scipy',
        'pandas', 'PIL', 'cv2', 'torch', 'tensorflow',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=_block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=_block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SuperNiuma-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Optional: generate a single-folder bundle for debugging
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='SuperNiuma-backend',
# )
