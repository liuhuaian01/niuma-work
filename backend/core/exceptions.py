"""
统一异常处理体系

解决三种错误模式混用的问题，提供一致的异常层次和错误响应。
所有Service层抛出异常，由中间件统一捕获并转换为HTTP响应。
"""


class NiumaError(Exception):
    """超级牛马基础异常类
    
    所有业务异常的基类，包含错误码、消息和HTTP状态码。
    
    Attributes:
        code: 错误代码（英文大写，如NOT_FOUND）
        message: 错误消息（中文描述）
        status_code: HTTP状态码
        request_id: 请求ID（可选，用于追踪）
    """
    
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        request_id: str | None = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.request_id = request_id
        super().__init__(f"[{code}] {message}")


# ============================================================
# 客户端错误 (4xx)
# ============================================================

class NotFoundError(NiumaError):
    """资源不存在错误 (404)
    
    使用场景：
    - Workspace不存在
    - Message不存在
    - Agent不存在
    """
    
    def __init__(self, resource: str, request_id: str | None = None):
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource}不存在",
            status_code=404,
            request_id=request_id
        )


class ValidationError(NiumaError):
    """参数验证错误 (422)
    
    使用场景：
    - 必填参数缺失
    - 参数格式错误
    - 参数值超出范围
    """
    
    def __init__(self, field: str, message: str, request_id: str | None = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=f"{field}: {message}",
            status_code=422,
            request_id=request_id
        )


class AuthenticationError(NiumaError):
    """认证失败错误 (401)
    
    使用场景：
    - Token过期
    - Token无效
    - 未登录
    """
    
    def __init__(self, message: str = "认证失败", request_id: str | None = None):
        super().__init__(
            code="AUTHENTICATION_ERROR",
            message=message,
            status_code=401,
            request_id=request_id
        )


class PermissionError(NiumaError):
    """权限不足错误 (403)
    
    使用场景：
    - 无权访问资源
    - 无权执行操作
    - 许可证过期
    """
    
    def __init__(self, message: str = "权限不足", request_id: str | None = None):
        super().__init__(
            code="PERMISSION_DENIED",
            message=message,
            status_code=403,
            request_id=request_id
        )


class BudgetExceededError(NiumaError):
    """预算超限错误 (402)
    
    使用场景：
    - Token预算不足
    - 配额用完
    """
    
    def __init__(self, message: str = "预算超限", request_id: str | None = None):
        super().__init__(
            code="BUDGET_EXCEEDED",
            message=message,
            status_code=402,
            request_id=request_id
        )


class CapabilityBlockedError(NiumaError):
    """能力被阻止错误 (403)
    
    使用场景：
    - 功能开关关闭
    - 能力被禁用
    """
    
    def __init__(self, message: str = "功能不可用", request_id: str | None = None):
        super().__init__(
            code="CAPABILITY_BLOCKED",
            message=message,
            status_code=403,
            request_id=request_id
        )


# ============================================================
# 服务器错误 (5xx)
# ============================================================

class ServiceError(NiumaError):
    """服务内部错误 (500)
    
    使用场景：
    - 数据库操作失败
    - 外部API调用失败
    - 未知异常
    """
    
    def __init__(self, message: str = "服务内部错误", request_id: str | None = None):
        super().__init__(
            code="SERVICE_ERROR",
            message=message,
            status_code=500,
            request_id=request_id
        )


class ModelUnavailableError(NiumaError):
    """模型不可用错误 (503)
    
    使用场景：
    - 所有模型都失败
    - 模型API超时
    """
    
    def __init__(self, message: str = "模型不可用", request_id: str | None = None):
        super().__init__(
            code="MODEL_UNAVAILABLE",
            message=message,
            status_code=503,
            request_id=request_id
        )


class DatabaseError(NiumaError):
    """数据库错误 (500)
    
    使用场景：
    - SQL执行失败
    - 连接断开
    - 事务冲突
    """
    
    def __init__(self, message: str = "数据库操作失败", request_id: str | None = None):
        super().__init__(
            code="DATABASE_ERROR",
            message=message,
            status_code=500,
            request_id=request_id
        )


# ============================================================
# 工具函数
# ============================================================

def make_error_response(error: NiumaError) -> dict:
    """将异常转换为标准错误响应格式
    
    Args:
        error: NiumaError实例
        
    Returns:
        标准错误响应字典
    """
    return {
        "success": False,
        "error": {
            "code": error.code,
            "message": error.message,
        },
        "request_id": error.request_id,
    }


def is_niuma_error(exc: Exception) -> bool:
    """判断是否为NiumaError类型
    
    Args:
        exc: 异常实例
        
    Returns:
        是否为NiumaError
    """
    return isinstance(exc, NiumaError)
