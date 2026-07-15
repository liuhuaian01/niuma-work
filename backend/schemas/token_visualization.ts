/**
 * 超级牛马 Token 三层可视化数据接口定义
 *
 * 三层架构：
 * 1. Topbar Pill 层 - 实时 Token 百分比 + 颜色状态
 * 2. Hover Dropdown 层 - 压缩详情 (当前级别/操作记录/节省量)
 * 3. Statusbar 层 - 压缩状态摘要
 *
 * 作者：超级牛马-数据工程
 * 日期：2026-05-29
 */

// ============================================================
// 通用类型
// ============================================================

/** 压缩级别 */
export type CompressionLevel = 0 | 1 | 2 | 3;

/** 压缩级别标签 */
export const CompressionLevelLabel: Record<CompressionLevel, string> = {
  0: '正常',
  1: '预警',
  2: '裁剪中',
  3: '深度压缩',
};

/** Token Pill 颜色状态 */
export type PillColor = 'green' | 'yellow' | 'orange' | 'red';

/** 压缩操作类型 */
export type CompressionActionType = 'budget' | 'snip' | 'summarize';

/** Observation 18 种类型 */
export type ObservationType =
  | 'bugfix'
  | 'feature'
  | 'refactor'
  | 'architecture'
  | 'domain_knowledge'
  | 'api_usage'
  | 'best_practice'
  | 'trick'
  | 'decision'
  | 'error'
  | 'workaround'
  | 'milestone'
  | 'user_preference'
  | 'user_feedback'
  | 'user_habit'
  | 'agent_capability'
  | 'orchestration_pattern'
  | 'collaboration_note';

/** Schema 类型 (S01-S10) */
export type SchemaType = 'S01' | 'S02' | 'S03' | 'S04' | 'S05' | 'S06' | 'S07' | 'S08' | 'S09' | 'S10';

// ============================================================
// 第一层：Topbar Pill 接口
// ============================================================

/** Topbar Pill 数据 (轮询频率: 2s) */
export interface TokenPillData {
  /** 会话 ID */
  sessionId: string;

  /** 当前 Token 使用量 */
  usedTokens: number;

  /** Token 上限 */
  maxTokens: number;

  /** 使用百分比 (0-100) */
  percentage: number;

  /** Pill 颜色 */
  color: PillColor;

  /** 压缩级别 */
  compressionLevel: CompressionLevel;

  /** 预估剩余对话轮数 */
  estimatedRemainingTurns: number;

  /** 是否正在压缩中 */
  isCompressing: boolean;
}

/** Pill 颜色计算规则 */
export function getPillColor(percentage: number): PillColor {
  if (percentage < 60) return 'green';
  if (percentage < 80) return 'yellow';
  if (percentage < 90) return 'orange';
  return 'red';
}

// ============================================================
// 第二层：Hover Dropdown 接口
// ============================================================

/** Hover Dropdown 数据 (展开时获取) */
export interface TokenDropdownData {
  /** 基础 Pill 数据 */
  pill: TokenPillData;

  /** 压缩详情 */
  compression: CompressionDetail;

  /** 最近压缩操作记录 (最近 10 条) */
  recentActions: CompressionActionRecord[];

  /** Token 使用历史 (最近 30 分钟，每 2 秒一个点) */
  tokenHistory: TokenHistoryPoint[];

  /** 系统消息提示 */
  systemMessages: SystemMessage[];
}

/** 压缩详情 */
export interface CompressionDetail {
  /** 当前压缩级别 */
  level: CompressionLevel;

  /** 级别描述 */
  levelDescription: string;

  /** 本会话累计节省 Token 数 */
  totalSavedTokens: number;

  /** 本会话累计节省比例 */
  totalSavedRatio: number;

  /** 本会话压缩成本估算 (元) */
  costEstimate: number;

  /** Budget 截断次数 */
  budgetCount: number;

  /** Snip 裁剪次数 */
  snipCount: number;

  /** Summarize 摘要次数 */
  summarizeCount: number;

  /** 压缩后 Token 占比 (0-1) */
  currentCompressionRatio: number;
}

/** 压缩操作记录 */
export interface CompressionActionRecord {
  /** 操作类型 */
  type: CompressionActionType;

  /** 节省 Token 数 */
  savedTokens: number;

  /** 节省比例 */
  savedRatio: number;

  /** 操作时间 */
  timestamp: string; // ISO 8601

  /** 操作描述 */
  description: string;
}

/** Token 使用历史点 */
export interface TokenHistoryPoint {
  /** 时间戳 */
  timestamp: string; // ISO 8601

  /** Token 使用量 */
  tokens: number;

  /** 压缩级别 (发生变化时标记) */
  compressionLevel?: CompressionLevel;
}

/** 系统消息 */
export interface SystemMessage {
  /** 消息 ID */
  id: string;

  /** 消息类型 */
  type: 'warning' | 'info' | 'success';

  /** 消息内容 */
  content: string;

  /** 时间戳 */
  timestamp: string;
}

// ============================================================
// 第三层：Statusbar 接口
// ============================================================

/** Statusbar 数据 (轮询频率: 5s) */
export interface TokenStatusbarData {
  /** 压缩是否启用 */
  compressionEnabled: boolean;

  /** 当前压缩级别描述 */
  compressionStatus: string;

  /** 本会话节省 Token 数 */
  savedTokens: number;

  /** 本会话节省成本估算 */
  costSaved: string; // 格式化后的金额，如 "约 ¥0.003"

  /** 记忆层级摘要 */
  memory: MemorySummary;
}

/** 记忆层级摘要 */
export interface MemorySummary {
  /** L1 当前会话状态 */
  l1: L1Summary;

  /** L2 短期档案状态 */
  l2: L2Summary;

  /** L3 长期知识库状态 */
  l3: L3Summary;
}

/** L1 摘要 */
export interface L1Summary {
  /** 已用 Token / 上限 */
  usage: string; // "7680/8192"

  /** 百分比 */
  percentage: number;

  /** 消息数 */
  messageCount: number;

  /** 决策数 */
  decisionCount: number;
}

/** L2 摘要 */
export interface L2Summary {
  /** 档案数 */
  archiveCount: number;

  /** Observation 数 */
  observationCount: number;

  /** 按类型分布 (Top 5) */
  topTypes: Array<{
    type: ObservationType;
    count: number;
  }>;

  /** 最早过期时间 */
  earliestExpiry: string | null;
}

/** L3 摘要 */
export interface L3Summary {
  /** 知识条目数 */
  knowledgeCount: number;

  /** 按 Schema 分布 */
  schemaDistribution: Array<{
    schema: SchemaType;
    name: string;
    count: number;
  }>;

  /** 最近更新时间 */
  lastUpdated: string | null;
}

// ============================================================
// 记忆管理页面接口
// ============================================================

/** 记忆列表查询参数 */
export interface MemoryListParams {
  /** 工作间 ID */
  workspaceId: string;

  /** 记忆层级过滤 */
  level?: 'L1' | 'L2' | 'L3';

  /** Schema 类型过滤 */
  schemaType?: SchemaType;

  /** Observation 类型过滤 */
  observationType?: ObservationType;

  /** 搜索关键词 */
  search?: string;

  /** 分页 */
  page?: number;

  /** 每页数量 */
  pageSize?: number;
}

/** 记忆条目 (统一格式) */
export interface MemoryEntry {
  /** 条目 ID */
  id: string;

  /** 记忆层级 */
  level: 'L1' | 'L2' | 'L3';

  /** 标题 */
  title: string;

  /** 内容预览 (前 200 字符) */
  preview: string;

  /** 类型 */
  type: ObservationType | SchemaType;

  /** 类型标签 */
  typeLabel: string;

  /** 置信度 */
  confidence: number;

  /** 创建时间 */
  createdAt: string;

  /** 过期时间 (L2) */
  expiresAt?: string;

  /** 标签 */
  tags: string[];

  /** 检索次数 */
  retrievalCount: number;

  /** 可用操作 */
  actions: MemoryAction[];
}

/** 记忆操作 */
export type MemoryAction = 'view' | 'edit' | 'delete' | 'upgrade' | 'cite' | 'restore';

/** 记忆清理参数 */
export interface MemoryClearParams {
  /** 工作间 ID */
  workspaceId: string;

  /** 清理层级 */
  level?: 'L1' | 'L2' | 'L3';

  /** Observation 类型 (L2 清理) */
  observationType?: ObservationType;

  /** 是否确认 */
  confirm: boolean;
}

/** 记忆清理结果 */
export interface MemoryClearResult {
  /** 清理的条目数 */
  clearedCount: number;

  /** 释放的空间 (字节) */
  freedBytes: number;

  /** 清理的层级 */
  level: string;
}

// ============================================================
// 后端 API 路由规范
// ============================================================

/**
 * API 路由定义
 *
 * 所有接口遵循 RESTful 规范，返回统一格式：
 * { code: 0, data: T, message: "ok" }
 *
 * 错误码：
 * - 0: 成功
 * - 400: 参数错误
 * - 404: 资源不存在
 * - 500: 服务器错误
 */
export interface TokenApiRoutes {
  // ---- Topbar Pill (轮询 2s) ----

  /**
   * GET /api/memory/token-pill
   * 获取 Topbar Pill 数据
   *
   * Query: { session_id: string }
   * Response: TokenPillData
   */
  'GET /api/memory/token-pill': {
    query: { session_id: string };
    response: TokenPillData;
  };

  // ---- Hover Dropdown (展开时请求) ----

  /**
   * GET /api/memory/token-detail
   * 获取 Hover Dropdown 详细数据
   *
   * Query: { session_id: string }
   * Response: TokenDropdownData
   */
  'GET /api/memory/token-detail': {
    query: { session_id: string };
    response: TokenDropdownData;
  };

  // ---- Statusbar (轮询 5s) ----

  /**
   * GET /api/memory/status
   * 获取 Statusbar 摘要数据
   *
   * Query: { workspace_id: string, session_id?: string }
   * Response: TokenStatusbarData
   */
  'GET /api/memory/status': {
    query: { workspace_id: string; session_id?: string };
    response: TokenStatusbarData;
  };

  // ---- 压缩操作 ----

  /**
   * POST /api/compression/trigger
   * 手动触发压缩 (调试用)
   *
   * Body: { session_id: string, level: CompressionActionType }
   * Response: CompressionReport
   */
  'POST /api/compression/trigger': {
    body: { session_id: string; level: CompressionActionType };
    response: CompressionReport;
  };

  /**
   * GET /api/compression/history
   * 获取压缩历史
   *
   * Query: { session_id?: string, workspace_id?: string, period_hours?: number }
   * Response: CompressionHistoryResponse
   */
  'GET /api/compression/history': {
    query: { session_id?: string; workspace_id?: string; period_hours?: number };
    response: CompressionHistoryResponse;
  };

  // ---- 记忆管理 ----

  /**
   * GET /api/memory/list
   * 获取记忆列表 (管理页面)
   *
   * Query: MemoryListParams
   * Response: { items: MemoryEntry[], total: number }
   */
  'GET /api/memory/list': {
    query: MemoryListParams;
    response: { items: MemoryEntry[]; total: number };
  };

  /**
   * DELETE /api/memory/clear
   * 清理记忆
   *
   * Body: MemoryClearParams
   * Response: MemoryClearResult
   */
  'DELETE /api/memory/clear': {
    body: MemoryClearParams;
    response: MemoryClearResult;
  };

  /**
   * GET /api/memory/l2/observations
   * 获取 L2 Observation 列表
   *
   * Query: { workspace_id: string, obs_type?: ObservationType, limit?: number }
   * Response: ObservationEntry[]
   */
  'GET /api/memory/l2/observations': {
    query: { workspace_id: string; obs_type?: ObservationType; limit?: number };
    response: ObservationEntry[];
  };

  /**
   * GET /api/memory/l3/knowledge
   * 获取 L3 知识条目
   *
   * Query: { workspace_id: string, schema_type?: SchemaType, search?: string, limit?: number }
   * Response: KnowledgeEntry[]
   */
  'GET /api/memory/l3/knowledge': {
    query: { workspace_id: string; schema_type?: SchemaType; search?: string; limit?: number };
    response: KnowledgeEntry[];
  };

  /**
   * POST /api/memory/l3/upgrade
   * 手动触发 L2→L3 升级
   *
   * Body: { obs_ids: string[], schema_type: SchemaType }
   * Response: { upgraded_count: number, knowledge_ids: string[] }
   */
  'POST /api/memory/l3/upgrade': {
    body: { obs_ids: string[]; schema_type: SchemaType };
    response: { upgraded_count: number; knowledge_ids: string[] };
  };

  // ---- 压缩配置 ----

  /**
   * GET /api/workspaces/{ws_id}/config/compression
   * 获取工作间压缩配置
   */
  'GET /api/workspaces/{ws_id}/config/compression': {
    response: CompressionConfigResponse;
  };

  /**
   * PATCH /api/workspaces/{ws_id}/config/compression
   * 更新工作间压缩配置
   */
  'PATCH /api/workspaces/{ws_id}/config/compression': {
    body: Partial<CompressionConfigResponse>;
    response: CompressionConfigResponse;
  };
}

// ============================================================
// API 响应子类型
// ============================================================

/** 压缩报告 */
export interface CompressionReport {
  level: CompressionLevel;
  preTokens: number;
  postTokens: number;
  totalSaved: number;
  savingRatio: number;
  actions: Array<{
    type: CompressionActionType;
    savedTokens: number;
  }>;
  warnings: string[];
}

/** 压缩历史响应 */
export interface CompressionHistoryResponse {
  events: Array<{
    level: CompressionLevel;
    preTokens: number;
    postTokens: number;
    savingRatio: number;
    actions: CompressionActionType[];
    timestamp: string;
  }>;
  summary: {
    totalCompressions: number;
    totalTokensSaved: number;
    costSaved: number;
    avgSavingRatio: number;
  };
}

/** Observation 条目 */
export interface ObservationEntry {
  obsId: string;
  workspaceId: string;
  obsType: ObservationType;
  topic: string;
  content: string;
  confidence: number;
  retrievalCount: number;
  createdAt: string;
  expiresAt: string;
}

/** 知识条目 */
export interface KnowledgeEntry {
  knowledgeId: string;
  workspaceId: string;
  schemaType: SchemaType;
  title: string;
  content: string;
  tags: string[];
  confidence: number;
  totalRetrievals: number;
  version: number;
  sourceType: string;
  createdAt: string;
  updatedAt: string;
}

/** 压缩配置 */
export interface CompressionConfigResponse {
  enabled: boolean;
  autoSummarize: boolean;
  warnThreshold: number;
  budgetThreshold: number;
  summarizeThreshold: number;
  budgetMaxResultLength: number;
  snipPreserveRecent: number;
  summarizeModel: string;
}
