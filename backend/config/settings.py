"""
全局配置模块

优先级: 环境变量 > .env 文件 > 默认值
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据目录 (开发阶段用项目目录，发布后切 %LOCALAPPDATA%/SuperNiuma/)
DATA_DIR = Path(os.getenv("NIUMA_DATA_DIR", BASE_DIR / "data"))

logger = logging.getLogger("niuma.settings")


class Settings:
    """全局配置单例"""

    # 数据目录
    DATA_DIR: Path = DATA_DIR
    TAIJI_DB_PATH: Path = DATA_DIR / "taiji.db"

    # L3 知识库（LanceDB）路径
    LANCEDB_PATH: Path = DATA_DIR / "lancedb"

    # Skills 目录 — 社区+自开发
    SKILLS_DIR: Path = DATA_DIR / "skills"

    # 服务
    HOST: str = "127.0.0.1"
    PORT: int = int(os.getenv("NIUMA_PORT", "18080"))
    DEBUG: bool = os.getenv("NIUMA_DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("NIUMA_LOG_LEVEL", "debug" if DEBUG else "info")

    # 数据库
    DB_PATH: str = str(DATA_DIR / "superniuma.db")
    DB_URL: str = f"sqlite+aiosqlite:///{DB_PATH}"

    # SQLite 连接池配置
    # 注意: SQLite 使用 StaticPool（单连接模式），这些参数作为文档保留
    # 如果未来切换到 PostgreSQL/MySQL，可直接启用这些参数
    DB_POOL_SIZE: int = 5          # 连接池大小（SQLite 模式下无效）
    DB_MAX_OVERFLOW: int = 10      # 最大溢出连接数（SQLite 模式下无效）
    DB_POOL_TIMEOUT: int = 30      # 获取连接的超时时间（秒）
    DB_POOL_RECYCLE: int = 3600    # 连接回收时间（秒），防止 stale connections

    # 模型 API（环境变量，不设默认值）
    # 优先从环境变量读取，确保敏感信息不硬编码
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

    KIMI_API_KEY: str = os.getenv("KIMI_API_KEY", "")
    KIMI_BASE_URL: str = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")

    HUNYUAN_API_KEY: str = os.getenv("HUNYUAN_API_KEY", "")
    HUNYUAN_BASE_URL: str = os.getenv("HUNYUAN_BASE_URL", "https://api.hunyuan.cloud.tencent.com/v1")

    GLM_API_KEY: str = os.getenv("GLM_API_KEY", "")
    GLM_BASE_URL: str = os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")

    # 模型名称映射 — v2.0: V4 正式版已上线 2026-07-15, 旧接口 7/24 停用
    MODEL_NAMES: dict = {
        "deepseek-v4-pro": "deepseek-chat",          # V4 正式版 Pro（2026-07-15 已上线）
        "deepseek-v4-flash": "deepseek-chat",        # V4 正式版 Flash
        # "deepseek-chat": 旧接口别名 — 7/24 停用后自动降级到 V4 Flash
        "deepseek-chat": "deepseek-chat",            # ⚠️ 旧接口（7/24 停用），运行时自动路由到 V4 Flash
        "moonshot-v1": "moonshot-v1-8k",
        "hunyuan-turbos": "hunyuan-turbos-latest",
        "glm-4-flash": "glm-4-flash",
        "glm-4-9b": "glm-4-9b",                      # 开源免费版
        "qwen-3.5-397b": "qwen-3.5-397b",
    }
    
    # V4 正式版上线日期
    DEEPSEEK_V4_GA_DATE: str = "2026-07-15"

    # DeepSeek V4 峰谷定价配置
    PEAK_HOURS_MORNING: tuple = (9, 12)              # 早高峰 9:00-12:00
    PEAK_HOURS_AFTERNOON: tuple = (14, 18)           # 晚高峰 14:00-18:00
    PEAK_PRICE_MULTIPLIER: float = 2.0               # 高峰时段价格翻倍
    DEEPSEEK_OLD_DEPRECATION_DATE: str = "2026-07-24"  # 旧接口 deepseek-chat 停用日期

    # 降级链（已废弃——DynamicDegradationEngine 动态决策）
    # TODO v2.0: 移除，仅作为静态兜底保留
    # v2.0: V4 Pro 升为首选，deepseek-chat 旧接口移除
    FALLBACK_CHAIN: list = ["deepseek-v4-pro", "deepseek-v4-flash", "moonshot-v1", "hunyuan-turbos", "glm-4-9b"]

    # ── v2.1: llama.cpp 本地推理引擎配置 ──
    LLAMA_SERVER_HOST: str = os.getenv("NIUMA_LLAMA_HOST", "127.0.0.1")
    LLAMA_SERVER_PORT: int = int(os.getenv("NIUMA_LLAMA_PORT", "8080"))
    LLAMA_SERVER_CTX_SIZE: int = int(os.getenv("NIUMA_LLAMA_CTX", "32768"))
    LLAMA_SERVER_N_GPU_LAYERS: int = int(os.getenv("NIUMA_LLAMA_GPU_LAYERS", "999"))  # 999=auto
    LLAMA_SERVER_TEMP: float = float(os.getenv("NIUMA_LLAMA_TEMP", "1.0"))
    LLAMA_MODELS_DIR: str = os.getenv("NIUMA_MODELS_DIR",
        str(Path(BASE_DIR).parent / "data" / "models"))  # 默认: super-niuma/data/models/
    LLAMA_BIN_PATH: str = os.getenv("NIUMA_LLAMA_BIN",
        str(Path(BASE_DIR).parent / "bin" / "llama-server.exe"))

    # MCP 安全配置 (P1-6: MCP 认证层)
    MCP_AUTH_ENABLED: bool = os.getenv("NIUMA_MCP_AUTH_ENABLED", "true").lower() != "false"
    MCP_TOKEN_TTL: int = int(os.getenv("NIUMA_MCP_TOKEN_TTL", "300"))  # 令牌有效期 5 分钟
    MCP_ALLOW_MOCK_UNAUTHENTICATED: bool = os.getenv("NIUMA_MCP_ALLOW_MOCK", "true").lower() != "false"  # 本地开发时允许 mock 模式

    # Agent 身份注册配置 (P1-7: Agent 身份注册表)
    AGENT_IDENTITY_ENABLED: bool = os.getenv("NIUMA_AGENT_IDENTITY_ENABLED", "true").lower() != "false"
    AGENT_TOKEN_TTL: int = int(os.getenv("NIUMA_AGENT_TOKEN_TTL", "86400"))  # 令牌有效期 24 小时

    # 限额
    FREE_WORKSPACE_LIMIT: int = 2
    AGENT_LIMIT_PER_WORKSPACE: int = 5

    # 默认配置
    DEFAULT_TOKEN_BUDGET: int = 200000
    DEFAULT_CONTEXT_THRESHOLD: int = 6144
    DEFAULT_SECURITY_LEVEL: str = "balanced"

    # 上下文压缩阈值
    CTX_WARNING_PCT: float = 0.60
    CTX_SNIP_PCT: float = 0.80
    CTX_SUMMARIZE_PCT: float = 0.90
    CTX_FORCE_PCT: float = 0.95
    CTX_BUDGET_CHARS: int = 2000

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_TIMEOUT: int = 10
    WS_MAX_RETRIES: int = 5

    # 软删除保留天数
    SOFT_DELETE_DAYS: int = 30

    # ===== 太极引擎配置 =====
    # Token 节约冷启动阈值
    SAVINGS_COLD_START: int = 5
    # Skill 唤醒最低匹配度
    SKILL_WAKE_THRESHOLD: float = 0.30
    # 自愈规则最低成功率
    HEALING_MIN_RATE: float = 0.30
    # Smart Allocator 权重
    ALLOCATOR_PRIORITY_WEIGHT: float = 0.4
    ALLOCATOR_ROI_WEIGHT: float = 0.35
    ALLOCATOR_BUDGET_WEIGHT: float = 0.25
    # 模型超时（秒）
    MODEL_TIMEOUT: float = 120.0
    # 模型禁用冷却时间（秒）
    MODEL_DISABLE_SECONDS: int = 1800
    # 模型连续失败阈值
    MODEL_MAX_FAILURES: int = 3
    # 本地答案匹配阈值
    LOCAL_ANSWER_L3_THRESHOLD: float = 0.55
    LOCAL_ANSWER_L2_THRESHOLD: float = 0.65
    LOCAL_ANSWER_CHAT_THRESHOLD: float = 0.80
    # 对话上下文消息上限
    CONTEXT_MESSAGE_LIMIT: int = 20

    # 分页默认值
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100


settings = Settings()
