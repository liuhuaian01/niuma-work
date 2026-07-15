-- ============================================================
-- 超级牛马 知识库完整建表脚本 v1.0
--
-- 覆盖：L2 短期档案 + L3 长期知识库 + FTS5 全文索引
-- 数据库：SQLite 3.39+ (支持 FTS5)
-- 作者：超级牛马-数据工程
-- 日期：2026-05-29
-- ============================================================

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA busy_timeout=5000;

-- ============================================================
-- Schema 版本管理
-- ============================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 记录初始版本
INSERT OR IGNORE INTO schema_version (version, description)
VALUES (1, '初始 Schema: L2 短期档案 + L3 长期知识库 + FTS5 + 10 Schema 矩阵');

-- ============================================================
-- L2 短期档案 (P1)
-- ============================================================

-- L2 会话档案表
CREATE TABLE IF NOT EXISTS l2_session_archives (
    archive_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL,  -- created_at + 30 days
    summary TEXT NOT NULL,     -- 结构化 JSON 摘要 (见下方 JSON 结构注释)
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    duration_seconds INTEGER DEFAULT 0,

    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);

-- summary JSON 结构参考：
-- {
--   "session_title": "str",
--   "duration_seconds": 0,
--   "message_count": 0,
--   "total_tokens": 0,
--   "requests": [{"request": "str", "timestamp": "ISO", "agent": "str", "outcome": "completed|partial|failed"}],
--   "learned": [{"topic": "str", "content": "str", "confidence": 0.5, "observation_type": "str"}],
--   "completed": [{"task": "str", "deliverable": "str", "quality": "good|acceptable|needs_revision"}],
--   "key_decisions": [{"decision": "str", "rationale": "str", "context": "str"}]
-- }

-- L2 Observation 表 (独立出来便于检索)
CREATE TABLE IF NOT EXISTS l2_observations (
    obs_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    archive_id TEXT REFERENCES l2_session_archives(archive_id) ON DELETE CASCADE,
    obs_type TEXT NOT NULL,              -- 18 种类型 (见下方枚举)
    topic TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence REAL DEFAULT 0.5,
    retrieval_count INTEGER DEFAULT 0,   -- 被检索次数 (>=10 触发 L3 升级)
    source_session_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL,

    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);

-- Observation 18 种类型：
-- 技术类: bugfix, feature, refactor, architecture
-- 知识类: domain_knowledge, api_usage, best_practice, trick
-- 过程类: decision, error, workaround, milestone
-- 人机交互类: user_preference, user_feedback, user_habit
-- 协作类: agent_capability, orchestration_pattern, collaboration_note

-- L2 增量快照表 (防崩溃丢失，每 5 分钟一次)
CREATE TABLE IF NOT EXISTS l2_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    captured_at TEXT NOT NULL DEFAULT (datetime('now')),
    snapshot_data TEXT NOT NULL,  -- 当前会话状态的 JSON 快照

    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);

-- L2 索引
CREATE INDEX IF NOT EXISTS idx_l2_archives_workspace
    ON l2_session_archives(workspace_id, expires_at);

CREATE INDEX IF NOT EXISTS idx_l2_archives_session
    ON l2_session_archives(session_id);

CREATE INDEX IF NOT EXISTS idx_l2_observations_workspace
    ON l2_observations(workspace_id, obs_type, expires_at);

CREATE INDEX IF NOT EXISTS idx_l2_observations_topic
    ON l2_observations(topic);

CREATE INDEX IF NOT EXISTS idx_l2_observations_retrieval
    ON l2_observations(retrieval_count)
    WHERE retrieval_count >= 10;

CREATE INDEX IF NOT EXISTS idx_l2_snapshots_session
    ON l2_snapshots(session_id, captured_at);

-- L2 过期数据清理触发器 (INSERT 时检查)
CREATE TRIGGER IF NOT EXISTS trg_l2_cleanup_archives
AFTER INSERT ON l2_session_archives
BEGIN
    DELETE FROM l2_session_archives
    WHERE expires_at < datetime('now');
END;

CREATE TRIGGER IF NOT EXISTS trg_l2_cleanup_observations
AFTER INSERT ON l2_observations
BEGIN
    DELETE FROM l2_observations
    WHERE expires_at < datetime('now');
END;


-- ============================================================
-- L3 长期知识库 (P2)
-- ============================================================

-- L3 知识条目表 (核心表，覆盖 S01-S10 十个 Schema)
CREATE TABLE IF NOT EXISTS l3_knowledge_items (
    knowledge_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    schema_type TEXT NOT NULL,          -- Schema 类型标识 (S01-S10)

    -- 核心字段
    title TEXT NOT NULL,
    content TEXT NOT NULL,              -- 主要内容 (Markdown)
    content_format TEXT NOT NULL DEFAULT 'markdown',  -- markdown|json|table|code|link

    -- 标签与分类
    tags TEXT,                          -- JSON 数组：通用标签
    category_tags TEXT,                 -- JSON 数组：分类标签 (与 Schema 子分类相关)

    -- 来源与质量
    source_type TEXT NOT NULL,          -- auto_upgrade|manual_mark|retrieval_upgrade
    source_obs_ids TEXT,                -- JSON 数组：关联的 L2 Observation IDs
    upgrade_count INTEGER DEFAULT 1,    -- 升级触发次数
    total_retrievals INTEGER DEFAULT 0, -- 总检索次数
    confidence REAL DEFAULT 0.5,        -- 置信度 0.0-1.0

    -- 扩展属性 (EAV 模型)
    metadata TEXT,                      -- JSON：Schema 特有扩展属性 (见 knowledge_base_schema.md)

    -- 版本与生命周期
    version INTEGER DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT DEFAULT 'auto',     -- auto|user:{id}|agent:{id}
    is_active INTEGER DEFAULT 1,        -- 软删除标记

    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);

-- L3 知识关系表 (知识图谱)
CREATE TABLE IF NOT EXISTS l3_knowledge_relations (
    relation_id TEXT PRIMARY KEY,
    source_knowledge_id TEXT NOT NULL REFERENCES l3_knowledge_items(knowledge_id) ON DELETE CASCADE,
    target_knowledge_id TEXT NOT NULL REFERENCES l3_knowledge_items(knowledge_id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,        -- parent_of|related_to|prerequisite_of|derived_from|contradicts|supersedes|exemplifies
    weight REAL DEFAULT 0.5,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),

    -- 防止自环
    CHECK(source_knowledge_id != target_knowledge_id)
);

-- L3 引用历史
CREATE TABLE IF NOT EXISTS l3_citation_history (
    citation_id TEXT PRIMARY KEY,
    knowledge_id TEXT NOT NULL REFERENCES l3_knowledge_items(knowledge_id) ON DELETE CASCADE,
    session_id TEXT,
    cited_at TEXT NOT NULL DEFAULT (datetime('now')),
    context_snippet TEXT               -- 引用时的上下文片段
);

-- L3 版本历史表
CREATE TABLE IF NOT EXISTS knowledge_versions (
    version_id TEXT PRIMARY KEY,
    knowledge_id TEXT NOT NULL REFERENCES l3_knowledge_items(knowledge_id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    snapshot TEXT NOT NULL,             -- 该版本的完整 JSON 快照
    change_summary TEXT,               -- 变更摘要
    changed_by TEXT DEFAULT 'auto',     -- auto|user:{id}|agent:{id}
    created_at TEXT NOT NULL DEFAULT (datetime('now')),

    UNIQUE(knowledge_id, version_number)
);

-- L3 索引
CREATE INDEX IF NOT EXISTS idx_l3_knowledge_workspace
    ON l3_knowledge_items(workspace_id, schema_type);

CREATE INDEX IF NOT EXISTS idx_l3_knowledge_tags
    ON l3_knowledge_items(tags);

CREATE INDEX IF NOT EXISTS idx_l3_knowledge_active
    ON l3_knowledge_items(workspace_id, is_active)
    WHERE is_active = 1;

CREATE INDEX IF NOT EXISTS idx_l3_knowledge_confidence
    ON l3_knowledge_items(confidence)
    WHERE confidence >= 0.6;

CREATE INDEX IF NOT EXISTS idx_l3_knowledge_schema
    ON l3_knowledge_items(schema_type);

CREATE INDEX IF NOT EXISTS idx_l3_relations_source
    ON l3_knowledge_relations(source_knowledge_id);

CREATE INDEX IF NOT EXISTS idx_l3_relations_target
    ON l3_knowledge_relations(target_knowledge_id);

CREATE INDEX IF NOT EXISTS idx_l3_relations_type
    ON l3_knowledge_relations(relation_type);

CREATE INDEX IF NOT EXISTS idx_l3_citations_knowledge
    ON l3_citation_history(knowledge_id, cited_at);

CREATE INDEX IF NOT EXISTS idx_knowledge_versions
    ON knowledge_versions(knowledge_id, version_number DESC);


-- ============================================================
-- FTS5 全文索引
-- ============================================================

-- 统一全文索引表 (跨 Schema 检索)
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    title,
    content,
    tags,
    schema_type,
    metadata_json,                      -- 所有扩展属性的 JSON 文本
    tokenize='unicode61 remove_diacritics 2'
);

-- 触发器：知识条目创建时自动更新 FTS
CREATE TRIGGER IF NOT EXISTS knowledge_fts_insert
AFTER INSERT ON l3_knowledge_items
WHEN NEW.is_active = 1
BEGIN
    INSERT INTO knowledge_fts(rowid, title, content, tags, schema_type, metadata_json)
    VALUES (
        NEW.rowid,
        NEW.title,
        NEW.content,
        COALESCE(NEW.tags, ''),
        NEW.schema_type,
        COALESCE(NEW.metadata, '')
    );
END;

-- 触发器：更新时同步 FTS
CREATE TRIGGER IF NOT EXISTS knowledge_fts_update
AFTER UPDATE ON l3_knowledge_items
WHEN NEW.is_active = 1
BEGIN
    -- 先删旧记录
    DELETE FROM knowledge_fts WHERE rowid = OLD.rowid;
    -- 再插新记录
    INSERT INTO knowledge_fts(rowid, title, content, tags, schema_type, metadata_json)
    VALUES (
        NEW.rowid,
        NEW.title,
        NEW.content,
        COALESCE(NEW.tags, ''),
        NEW.schema_type,
        COALESCE(NEW.metadata, '')
    );
END;

-- 触发器：删除/软删除时同步 FTS
CREATE TRIGGER IF NOT EXISTS knowledge_fts_delete
AFTER UPDATE ON l3_knowledge_items
WHEN OLD.is_active = 1 AND NEW.is_active = 0
BEGIN
    DELETE FROM knowledge_fts WHERE rowid = OLD.rowid;
END;

CREATE TRIGGER IF NOT EXISTS knowledge_fts_hard_delete
AFTER DELETE ON l3_knowledge_items
BEGIN
    DELETE FROM knowledge_fts WHERE rowid = OLD.rowid;
END;


-- ============================================================
-- Observation → Schema 映射表
-- ============================================================

CREATE TABLE IF NOT EXISTS obs_schema_mapping (
    obs_type TEXT PRIMARY KEY,          -- Observation 类型
    schema_type TEXT NOT NULL,          -- 对应的 Schema (S01-S10)
    auto_upgrade_threshold INTEGER DEFAULT 3,  -- 自动升级需要的引用次数
    description TEXT
);

-- 初始化映射数据 (18 种 Observation → Schema)
INSERT OR IGNORE INTO obs_schema_mapping (obs_type, schema_type, auto_upgrade_threshold, description) VALUES
    -- 技术类 → S05
    ('bugfix', 'S05', 3, 'Bug 修复'),
    ('feature', 'S05', 3, '新增功能'),
    ('refactor', 'S05', 3, '重构'),
    ('architecture', 'S05', 2, '架构决策'),
    -- 知识类
    ('domain_knowledge', 'S01', 2, '领域知识 → 家纺 Schema'),
    ('api_usage', 'S05', 3, 'API 使用模式 → 技术栈'),
    ('best_practice', 'S05', 3, '最佳实践 → 技术栈'),
    ('trick', 'S05', 5, '技巧/窍门 → 技术栈'),
    -- 过程类
    ('decision', 'S06', 2, '关键决策 → 项目管理'),
    ('error', 'S09', 2, '错误记录 → 安全合规'),
    ('workaround', 'S05', 3, '临时方案 → 技术栈'),
    ('milestone', 'S06', 2, '里程碑 → 项目管理'),
    -- 人机交互类 → S10
    ('user_preference', 'S10', 2, '用户偏好 → 个人工作流'),
    ('user_feedback', 'S10', 3, '用户反馈 → 个人工作流'),
    ('user_habit', 'S10', 3, '用户习惯 → 个人工作流'),
    -- 协作类
    ('agent_capability', 'S10', 3, 'Agent 能力发现 → 个人工作流'),
    ('orchestration_pattern', 'S06', 3, '编排模式 → 项目管理'),
    ('collaboration_note', 'S06', 3, '协作记录 → 项目管理');


-- ============================================================
-- Schema 类型定义表 (S01-S10 元数据)
-- ============================================================

CREATE TABLE IF NOT EXISTS schema_definitions (
    schema_type TEXT PRIMARY KEY,       -- S01-S10
    name TEXT NOT NULL,                 -- Schema 名称
    domain TEXT NOT NULL,               -- 领域: 家纺行业|通用
    description TEXT NOT NULL,          -- 用途说明
    priority TEXT NOT NULL DEFAULT 'P1',-- P0|P1|P2
    metadata_template TEXT,             -- JSON 模板 (扩展属性结构)
    tag_tree TEXT,                      -- JSON 标签树
    fts_fields TEXT                     -- 全文索引涉及的字段列表
);

-- 初始化 Schema 定义
INSERT OR IGNORE INTO schema_definitions (schema_type, name, domain, description, priority) VALUES
    ('S01', '家纺面料与材质', '家纺行业', '面料类型、成分、物理属性、质量标准', 'P1'),
    ('S02', '家纺产品规格', '家纺行业', '产品分类、尺寸、工艺参数、包装', 'P1'),
    ('S03', '家纺生产与供应链', '家纺行业', '工序流程、供应商、成本核算、交期', 'P1'),
    ('S04', '家纺市场与渠道', '家纺行业', '市场分布、竞品分析、定价策略、渠道', 'P2'),
    ('S05', '软件开发技术栈', '通用', '技术选型、API 模式、数据库设计、框架', 'P0'),
    ('S06', '项目管理与流程', '通用', '任务追踪、里程碑、风险管理、复盘', 'P0'),
    ('S07', '文档与知识写作', '通用', '文档结构、内容模板、写作规范、审校', 'P0'),
    ('S08', '数据分析与报表', '通用', '数据模型、指标体系、可视化规范、SQL', 'P1'),
    ('S09', '安全与合规', '通用', '安全策略、威胁模型、Pi 准则、审计', 'P0'),
    ('S10', '个人工作流与偏好', '通用', '用户习惯、快捷键、回复风格、自动化', 'P0');


-- ============================================================
-- 压缩度量表 (可选，用于 /audit-token 看板)
-- ============================================================

CREATE TABLE IF NOT EXISTS compression_events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    level INTEGER NOT NULL,             -- 压缩级别 0-3
    pre_tokens INTEGER NOT NULL,
    post_tokens INTEGER NOT NULL,
    saving_ratio REAL NOT NULL,
    actions TEXT,                       -- JSON 数组: ["budget", "snip", "summarize"]
    created_at TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_compression_events_workspace
    ON compression_events(workspace_id, created_at);

CREATE INDEX IF NOT EXISTS idx_compression_events_session
    ON compression_events(session_id);


-- ============================================================
-- 视图 (常用查询)
-- ============================================================

-- L2 待升级 Observation 视图 (检索次数 >= 10)
CREATE VIEW IF NOT EXISTS v_l2_upgrade_candidates AS
SELECT
    o.obs_id,
    o.workspace_id,
    o.obs_type,
    o.topic,
    o.content,
    o.confidence,
    o.retrieval_count,
    m.schema_type,
    m.auto_upgrade_threshold
FROM l2_observations o
JOIN obs_schema_mapping m ON o.obs_type = m.obs_type
WHERE o.retrieval_count >= m.auto_upgrade_threshold
  AND o.expires_at > datetime('now');

-- L3 知识条目概览视图
CREATE VIEW IF NOT EXISTS v_l3_knowledge_overview AS
SELECT
    k.knowledge_id,
    k.workspace_id,
    k.schema_type,
    s.name AS schema_name,
    k.title,
    k.confidence,
    k.total_retrievals,
    k.version,
    k.source_type,
    k.is_active,
    k.created_at,
    k.updated_at,
    (SELECT COUNT(*) FROM l3_citation_history c WHERE c.knowledge_id = k.knowledge_id) AS citation_count,
    (SELECT COUNT(*) FROM l3_knowledge_relations r WHERE r.source_knowledge_id = k.knowledge_id) AS relation_out_count
FROM l3_knowledge_items k
LEFT JOIN schema_definitions s ON k.schema_type = s.schema_type;

-- 记忆系统全局状态视图
CREATE VIEW IF NOT EXISTS v_memory_status AS
SELECT
    w.id AS workspace_id,
    w.name AS workspace_name,
    (SELECT COUNT(*) FROM l2_session_archives a WHERE a.workspace_id = w.id AND a.expires_at > datetime('now')) AS l2_archive_count,
    (SELECT COUNT(*) FROM l2_observations o WHERE o.workspace_id = w.id AND o.expires_at > datetime('now')) AS l2_obs_count,
    (SELECT COUNT(*) FROM l3_knowledge_items k WHERE k.workspace_id = w.id AND k.is_active = 1) AS l3_knowledge_count
FROM workspaces w
WHERE w.deleted_at IS NULL;


-- ============================================================
-- Schema 迁移模板 (未来版本)
-- ============================================================

-- Version 2: Add embedding support
-- ALTER TABLE l3_knowledge_items ADD COLUMN embedding BLOB;
-- CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_vectors USING vec0(
--     knowledge_id TEXT PRIMARY KEY,
--     embedding float[768]
-- );

-- Version 3: Add multi-language support
-- ALTER TABLE l3_knowledge_items ADD COLUMN language TEXT DEFAULT 'zh-CN';
-- ALTER TABLE l3_knowledge_items ADD COLUMN translated_content TEXT;
