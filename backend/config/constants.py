"""
全局常量定义

集中管理所有魔法数字和硬编码值，便于维护和调整。
"""

# ============================================================
# Token 预算相关
# ============================================================

# 默认Agent Token预算
DEFAULT_AGENT_BUDGETS = {
    "writer-default": 30000,
    "coder-default": 50000,
    "analyst-default": 40000,
}

# Token使用率阈值（用于上下文压缩）
CTX_WARNING_PCT = 0.60      # 60% - 预警
CTX_SNIP_PCT = 0.80         # 80% - 裁剪中
CTX_SUMMARIZE_PCT = 0.90    # 90% - 已压缩
CTX_FORCE_PCT = 0.95        # 95% - 强制截断

# ============================================================
# 对话上下文相关
# ============================================================

# 上下文消息数量限制
CONTEXT_MESSAGE_LIMIT = 20

# 分页配置
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
DEFAULT_CHAT_PAGE_SIZE = 50

# ============================================================
# SSE 流式响应相关
# ============================================================

# 活跃流最大数量（防止资源耗尽）
MAX_ACTIVE_STREAMS = 100

# 流超时时间（秒）
STREAM_TIMEOUT_SECONDS = 300  # 5分钟

# ============================================================
# 模型相关
# ============================================================

# 模型超时时间（秒）
MODEL_TIMEOUT_SECONDS = 120.0

# 模型禁用冷却时间（秒）
MODEL_DISABLE_COOLDOWN_SECONDS = 1800  # 30分钟

# 模型连续失败阈值
MODEL_MAX_FAILURES = 3

# 降级链顺序（已废弃——DynamicDegradationEngine 动态决策）
# v2.0: V4 Pro 升为首选，移除 deepseek-chat 旧接口
FALLBACK_CHAIN_ORDER = ["deepseek-v4-pro", "deepseek-v4-flash", "moonshot-v1", "hunyuan-turbos", "glm-4-flash"]

# ============================================================
# L3 知识库相关
# ============================================================

# 本地答案匹配阈值
LOCAL_ANSWER_L3_THRESHOLD = 0.55
LOCAL_ANSWER_L2_THRESHOLD = 0.65
LOCAL_ANSWER_CHAT_THRESHOLD = 0.80

# 搜索返回结果数量
L3_SEARCH_DEFAULT_LIMIT = 5
L3_RECENT_DEFAULT_LIMIT = 10

# ============================================================
# 太极引擎配置
# ============================================================

# Skill唤醒最低匹配度
SKILL_WAKE_THRESHOLD = 0.30

# 自愈规则最低成功率
HEALING_MIN_RATE = 0.30

# Smart Allocator权重
ALLOCATOR_PRIORITY_WEIGHT = 0.4
ALLOCATOR_ROI_WEIGHT = 0.35
ALLOCATOR_BUDGET_WEIGHT = 0.25

# Token节约冷启动阈值
SAVINGS_COLD_START_THRESHOLD = 5

# Dynamic Balancer决策阈值
BALANCER_LOCAL_THRESHOLD = 0.65   # >0.65 选择本地
BALANCER_HYBRID_THRESHOLD = 0.35  # >0.35 选择混合，否则云端

# Dynamic Balancer权重系数
BALANCER_USER_PREF_WEIGHT = 0.3
BALANCER_COMPLEXITY_WEIGHT = 0.3
BALANCER_BUDGET_WEIGHT = 0.4

# v1.9: DeepSeek V4 峰谷定价 — 错峰调度阈值
SMART_ALLOCATOR_DEFER_COST_SAVING_THRESHOLD = 0.0005  # 错峰至少省 $0.0005 才建议推迟
PEAK_HOURS_MORNING = (9, 12)        # 早高峰 9:00-12:00 (北京时间)
PEAK_HOURS_AFTERNOON = (14, 18)     # 晚高峰 14:00-18:00 (北京时间)
PEAK_PRICE_MULTIPLIER = 2.0         # 高峰时段价格倍率

# ============================================================
# WebSocket 相关
# ============================================================

WS_HEARTBEAT_INTERVAL_SECONDS = 30
WS_TIMEOUT_SECONDS = 10
WS_MAX_RETRIES = 5

# ============================================================
# 软删除相关
# ============================================================

SOFT_DELETE_RETENTION_DAYS = 30

# ============================================================
# 工作空间限制
# ============================================================

FREE_WORKSPACE_LIMIT = 2
AGENT_LIMIT_PER_WORKSPACE = 5

# ============================================================
# 日志相关
# ============================================================

LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_FILE_BACKUP_COUNT = 5
ERROR_LOG_BACKUP_COUNT = 90  # 错误日志保留更久

# ============================================================
# 健康检查相关
# ============================================================

OLLAMA_HEALTH_URL = "http://localhost:11434/api/tags"
CLOUD_HEALTH_URL = "https://api.deepseek.com/v1/models"
HEALTH_CHECK_TIMEOUT_SECONDS = 3
