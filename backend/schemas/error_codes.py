"""超级牛马工作台 · 集中错误码定义

所有 API 错误码统一在此枚举中定义，避免散落各处。
"""

from enum import Enum


class ErrorCode(str, Enum):
    """API 错误码枚举"""

    # ===== 资源未找到 =====
    WORKSPACE_NOT_FOUND = "WORKSPACE_NOT_FOUND"        # 工作间不存在
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"                # Agent 不存在
    SKILL_NOT_FOUND = "SKILL_NOT_FOUND"                # 技能不存在
    TASK_NOT_FOUND = "TASK_NOT_FOUND"                  # 任务不存在
    MESSAGE_NOT_FOUND = "MESSAGE_NOT_FOUND"            # 消息不存在
    MEMORY_NOT_FOUND = "MEMORY_NOT_FOUND"              # 记忆条目/会话不存在
    STREAM_NOT_FOUND = "STREAM_NOT_FOUND"              # 流式连接不存在或已结束

    # ===== 模型相关 =====
    MODEL_ALL_DOWN = "MODEL_ALL_DOWN"                  # 所有模型不可用
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"            # 指定模型不可用
    NOT_LOCAL = "NOT_LOCAL"                            # 非本地模型

    # ===== 资源限制 =====
    WORKSPACE_LIMIT_EXCEEDED = "WORKSPACE_LIMIT_EXCEEDED"  # 工作间数量超限
    AGENT_LIMIT_EXCEEDED = "AGENT_LIMIT_EXCEEDED"          # Agent 数量超限
    AGENT_DUPLICATE_ROLE = "AGENT_DUPLICATE_ROLE"          # Agent 角色重复
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"                    # Token 预算超限

    # ===== 技能相关 =====
    SKILL_ALREADY_INSTALLED = "SKILL_ALREADY_INSTALLED"  # 技能已安装

    # ===== 许可证/认证 =====
    ACTIVATION_FAILED = "ACTIVATION_FAILED"            # 许可证激活失败

    # ===== 太极引擎 =====
    CAPABILITY_BLOCKED = "CAPABILITY_BLOCKED"          # 能力开关已关闭

    # ===== 备份 =====
    BACKUP_FAILED = "BACKUP_FAILED"                    # 备份操作失败

    # ===== 记忆引擎 =====
    MEMORY_ERROR = "MEMORY_ERROR"                      # 记忆引擎运行时错误
    COMPRESS_ERROR = "COMPRESS_ERROR"                  # 上下文压缩失败

    # ===== 通用错误 =====
    INTERNAL_ERROR = "INTERNAL_ERROR"                  # 服务器内部错误
    HTTP_ERROR = "HTTP_ERROR"                          # HTTP 协议层错误
    VALIDATION_ERROR = "VALIDATION_ERROR"              # 请求参数校验失败
