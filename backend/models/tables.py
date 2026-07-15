"""
SQLAlchemy Core 表定义 + 业务索引

Phase 2: metadata.create_all() 统一管理建表，废弃 db/database.py 中的 _SCHEMA_SQL。
"""

from sqlalchemy import MetaData, Table, Column, String, Integer, Float, Text, ForeignKey, Index

metadata = MetaData()

# ============================================================
# 核心表 (8 张)
# ============================================================

workspaces = Table(
    "workspaces", metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("icon", String, default="📄"),
    Column("theme_color", String, default="#FF6B35"),
    Column("is_default", Integer, default=0),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
    Column("deleted_at", String, nullable=True),
)

agents = Table(
    "agents", metadata,
    Column("id", String, primary_key=True),
    Column("workspace_id", String, ForeignKey("workspaces.id"), nullable=False),
    Column("name", String, nullable=False),
    Column("role", String, nullable=False),
    Column("icon", String, default="🤖"),
    Column("model", String, default="deepseek-v4-pro"),
    Column("system_prompt", Text, nullable=True),
    Column("temperature", Float, default=0.7),
    Column("max_tokens", Integer, default=4096),
    Column("status", String, default="offline"),
    Column("sort_order", Integer, default=0),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
    Column("deleted_at", String, nullable=True),
)

workspace_configs = Table(
    "workspace_configs", metadata,
    Column("id", String, primary_key=True),
    Column("workspace_id", String, ForeignKey("workspaces.id"), unique=True, nullable=False),
    Column("default_model", String, default="deepseek-v4-pro"),
    Column("token_budget", Integer, default=200000),
    Column("security_level", String, default="balanced"),
    Column("context_threshold", Integer, default=6144),
    Column("auto_summary", Integer, default=1),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
)

chat_messages = Table(
    "chat_messages", metadata,
    Column("id", String, primary_key=True),
    Column("workspace_id", String, ForeignKey("workspaces.id"), nullable=True),
    Column("role", String, nullable=False),
    Column("content", Text, nullable=False),
    Column("model", String, nullable=True),
    Column("at_agent_id", String, nullable=True),
    Column("status", String, default="completed"),
    Column("token_count", Integer, nullable=True),
    Column("artifacts", Text, nullable=True),
    Column("parent_message_id", String, nullable=True),
    Column("error_info", Text, nullable=True),
    Column("created_at", String, nullable=False),
)

orchestration_tasks = Table(
    "orchestration_tasks", metadata,
    Column("id", String, primary_key=True),
    Column("workspace_id", String, ForeignKey("workspaces.id"), nullable=False),
    Column("director_agent_id", String, ForeignKey("agents.id"), nullable=False),
    Column("trigger_message_id", String, ForeignKey("chat_messages.id"), nullable=True),
    Column("strategy", String, nullable=False),
    Column("description", Text, nullable=True),
    Column("status", String, default="pending"),
    Column("subtasks", Text, nullable=True),
    Column("qa_gate_results", Text, nullable=True),
    Column("total_tokens", Integer, default=0),
    Column("duration_ms", Integer, nullable=True),
    Column("error_info", Text, nullable=True),
    Column("started_at", String, nullable=True),
    Column("completed_at", String, nullable=True),
    Column("created_at", String, nullable=False),
)

scheduled_reports = Table(
    "scheduled_reports", metadata,
    Column("id", String, primary_key=True),
    Column("workspace_id", String, ForeignKey("workspaces.id"), nullable=False),
    Column("name", String, nullable=False),
    Column("schedule", String, nullable=False),
    Column("template", String, nullable=False),
    Column("config", Text, nullable=True),
    Column("notify", Integer, default=1),
    Column("enabled", Integer, default=1),
    Column("last_run_at", String, nullable=True),
    Column("next_run_at", String, nullable=True),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
)

skill_market = Table(
    "skill_market", metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("description", Text, nullable=False),
    Column("category", String, nullable=False),
    Column("author", String, default="超级牛马团队"),
    Column("version", String, default="1.0.0"),
    Column("icon", String, default="🔧"),
    Column("token_level", String, default="low"),
    Column("install_count", Integer, default=0),
    Column("recommend_reason", Text, nullable=True),
    Column("definition", Text, nullable=True),
    Column("tags", Text, nullable=True),
    Column("is_active", Integer, default=1),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
)

user_skills = Table(
    "user_skills", metadata,
    Column("id", String, primary_key=True),
    Column("skill_id", String, nullable=False),
    Column("name", String, nullable=False),
    Column("description", Text, nullable=True),
    Column("category", String, nullable=True),
    Column("author", String, nullable=True),
    Column("version", String, nullable=True),
    Column("icon", String, default="🔧"),
    Column("source", String, default="market"),
    Column("definition", Text, nullable=True),
    Column("enabled", Integer, default=1),
    Column("is_custom", Integer, default=0),
    Column("installed_at", String, nullable=False),
    Column("updated_at", String, nullable=True),
)

# ============================================================
# Agent 身份表 (P1-7: 身份注册表)
# ============================================================

agent_identities = Table(
    "agent_identities", metadata,
    Column("id", String, primary_key=True),
    Column("agent_id", String, nullable=False, unique=True),
    Column("workspace_id", String, ForeignKey("workspaces.id"), nullable=False),
    Column("name", String, nullable=False),
    Column("role", String, nullable=False),
    Column("public_key_hash", String, default=""),
    Column("revoked", Integer, default=0),
    Column("metadata", Text, nullable=True),
    Column("registered_at", String, nullable=False),
    Column("revoked_at", String, nullable=True),
)

# ============================================================
# 辅助表 (3 张，Phase 1 预留)
# ============================================================

l2_memory_entries = Table(
    "l2_memory_entries", metadata,
    Column("id", String, primary_key=True),
    Column("workspace_id", String, ForeignKey("workspaces.id"), nullable=False),
    Column("source_session_id", String, nullable=True),
    Column("entry_type", String, nullable=False),
    Column("content", Text, nullable=False),
    Column("summary", Text, nullable=True),
    Column("tags", Text, nullable=True),
    Column("observation_type", String, nullable=True),
    Column("retrieval_count", Integer, default=0),
    Column("expires_at", String, nullable=False),
    Column("created_at", String, nullable=False),
)

audit_logs = Table(
    "audit_logs", metadata,
    Column("id", String, primary_key=True),
    Column("workspace_id", String, nullable=True),
    Column("agent_id", String, nullable=True),
    Column("operation", String, nullable=False),
    Column("target", Text, nullable=True),
    Column("detail", Text, nullable=True),
    Column("result", String, nullable=False),
    Column("ip_address", String, nullable=True),
    Column("user_agent", String, nullable=True),
    Column("created_at", String, nullable=False),
)

backup_records = Table(
    "backup_records", metadata,
    Column("id", String, primary_key=True),
    Column("filename", String, nullable=False),
    Column("size_bytes", Integer, nullable=False),
    Column("type", String, default="manual"),
    Column("checksum", String, nullable=True),
    Column("created_at", String, nullable=False),
)

background_tasks = Table(
    "background_tasks", metadata,
    Column("id", String, primary_key=True),
    Column("workspace_id", String, ForeignKey("workspaces.id"), nullable=False),
    Column("agent_id", String, ForeignKey("agents.id"), nullable=False),
    Column("trigger_message_id", String, ForeignKey("chat_messages.id"), nullable=True),
    Column("title", String, nullable=False),
    Column("description", Text, nullable=True),
    Column("status", String, default="pending"),
    Column("progress", Integer, default=0),
    Column("result_summary", Text, nullable=True),
    Column("result_message_id", String, nullable=True),
    Column("error_info", Text, nullable=True),
    Column("total_tokens", Integer, default=0),
    Column("duration_ms", Integer, nullable=True),
    Column("started_at", String, nullable=True),
    Column("completed_at", String, nullable=True),
    Column("created_at", String, nullable=False),
)

# ============================================================
# 业务索引(加速查询)
# ============================================================

# workspaces 表索引
idx_workspaces_deleted = Index("idx_workspaces_deleted", workspaces.c.deleted_at)
idx_workspaces_created_at = Index("idx_workspaces_created_at", workspaces.c.created_at)

# agents 表索引
idx_agents_workspace = Index("idx_agents_workspace", agents.c.workspace_id)
idx_agents_role = Index("idx_agents_role", agents.c.workspace_id, agents.c.role)
idx_agents_status = Index("idx_agents_status", agents.c.workspace_id, agents.c.status)
idx_agents_deleted = Index("idx_agents_deleted", agents.c.deleted_at)

# workspace_configs 表索引
idx_workspace_configs_workspace = Index("idx_workspace_configs_workspace", workspace_configs.c.workspace_id)

# chat_messages 表索引 (高频查询优化)
idx_messages_workspace = Index("idx_messages_workspace", chat_messages.c.workspace_id)
idx_messages_time = Index("idx_messages_time", chat_messages.c.workspace_id, chat_messages.c.created_at)
idx_messages_workspace_desc = Index("idx_messages_workspace_desc", chat_messages.c.workspace_id, chat_messages.c.created_at.desc())
idx_messages_role = Index("idx_messages_role", chat_messages.c.workspace_id, chat_messages.c.role)
idx_messages_parent = Index("idx_messages_parent", chat_messages.c.parent_message_id)
idx_messages_status = Index("idx_messages_status", chat_messages.c.workspace_id, chat_messages.c.status)

# orchestration_tasks 表索引
idx_tasks_workspace = Index("idx_tasks_workspace", orchestration_tasks.c.workspace_id)
idx_tasks_status = Index("idx_tasks_status", orchestration_tasks.c.workspace_id, orchestration_tasks.c.status)
idx_tasks_director = Index("idx_tasks_director", orchestration_tasks.c.director_agent_id)
idx_tasks_trigger = Index("idx_tasks_trigger", orchestration_tasks.c.trigger_message_id)

# scheduled_reports 表索引
idx_reports_workspace = Index("idx_reports_workspace", scheduled_reports.c.workspace_id)
idx_reports_enabled = Index("idx_reports_enabled", scheduled_reports.c.enabled)
idx_reports_next_run = Index("idx_reports_next_run", scheduled_reports.c.next_run_at)

# skill_market 表索引
idx_skill_category = Index("idx_skill_category", skill_market.c.category)
idx_skill_active = Index("idx_skill_active", skill_market.c.is_active)
idx_skill_name = Index("idx_skill_name", skill_market.c.name)

# user_skills 表索引
idx_user_skills_skill_id = Index("idx_user_skills_skill_id", user_skills.c.skill_id)
idx_user_skills_enabled = Index("idx_user_skills_enabled", user_skills.c.enabled)
idx_user_skills_source = Index("idx_user_skills_source", user_skills.c.source)

# l2_memory_entries 表索引 (L2短期档案)
idx_l2_workspace = Index("idx_l2_workspace", l2_memory_entries.c.workspace_id)
idx_l2_expires = Index("idx_l2_expires", l2_memory_entries.c.expires_at)
idx_l2_workspace_expires = Index("idx_l2_workspace_expires", l2_memory_entries.c.workspace_id, l2_memory_entries.c.expires_at)
idx_l2_type = Index("idx_l2_type", l2_memory_entries.c.workspace_id, l2_memory_entries.c.entry_type)
idx_l2_source_session = Index("idx_l2_source_session", l2_memory_entries.c.source_session_id)
idx_l2_retrieval = Index("idx_l2_retrieval", l2_memory_entries.c.retrieval_count)

# audit_logs 表索引
idx_audit_time = Index("idx_audit_time", audit_logs.c.created_at)
idx_audit_operation = Index("idx_audit_operation", audit_logs.c.operation)
idx_audit_workspace = Index("idx_audit_workspace", audit_logs.c.workspace_id)
idx_audit_agent = Index("idx_audit_agent", audit_logs.c.agent_id)
idx_audit_workspace_time = Index("idx_audit_workspace_time", audit_logs.c.workspace_id, audit_logs.c.created_at.desc())

# backup_records 表索引
idx_backup_created = Index("idx_backup_created", backup_records.c.created_at)
idx_backup_type = Index("idx_backup_type", backup_records.c.type)

# background_tasks 表索引
idx_bg_tasks_workspace = Index("idx_bg_tasks_workspace", background_tasks.c.workspace_id)
idx_bg_tasks_status = Index("idx_bg_tasks_status", background_tasks.c.workspace_id, background_tasks.c.status)
idx_bg_tasks_agent = Index("idx_bg_tasks_agent", background_tasks.c.agent_id)
idx_bg_tasks_trigger = Index("idx_bg_tasks_trigger", background_tasks.c.trigger_message_id)
idx_bg_tasks_result = Index("idx_bg_tasks_result", background_tasks.c.result_message_id)

# agent_identities 表索引
idx_agent_identities_agent = Index("idx_agent_identities_agent", agent_identities.c.agent_id)
idx_agent_identities_workspace = Index("idx_agent_identities_workspace", agent_identities.c.workspace_id)
idx_agent_identities_revoked = Index("idx_agent_identities_revoked", agent_identities.c.workspace_id, agent_identities.c.revoked)
