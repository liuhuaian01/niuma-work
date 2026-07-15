"""通用工具函数

提供项目中常用的工具函数，包括：
- 日期时间处理
- 错误响应构造
- 数据验证
- 分页参数标准化
- 字典安全访问
"""

import re
from datetime import datetime, timezone, date
from typing import Any, Optional, TypeVar, Union

T = TypeVar('T')


def utc_now() -> str:
    """返回 ISO 8601 格式的 UTC 时间。"""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def escape_like(value: str) -> str:
    """转义 SQL LIKE 查询中的特殊字符。"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def is_new_day(last_date: str) -> tuple[bool, str]:
    """检查是否跨天。
    
    返回 (is_new_day, current_date_string)。
    用于 TokenBudget / TokenSavings / SmartAllocator 的每日重置逻辑。
    
    Usage:
        is_new, self._today = is_new_day(self._today)
        if is_new:
            self._records = []
    """
    today = str(date.today())
    return (today != last_date, today)


def validate_api_key(key: str) -> bool:
    """验证API密钥格式
    
    Args:
        key: API密钥字符串
        
    Returns:
        bool: 密钥格式是否有效
        
    Validation Rules:
        - 不能为空或None
        - 长度至少32个字符
        - 仅允许字母、数字、下划线、连字符
    """
    if not key or len(key) < 32:
        return False
    # 仅允许字母、数字、下划线、连字符
    if not re.match(r'^[a-zA-Z0-9_-]+$', key):
        return False
    return True


def mask_api_key(key: str) -> str:
    """脱敏API密钥，仅显示前4位和后4位
    
    Args:
        key: API密钥字符串
        
    Returns:
        str: 脱敏后的密钥字符串
        
    Examples:
        >>> mask_api_key("sk-abc123def456ghi789jkl012mno345pqr")
        'sk-a...5pqr'
        >>> mask_api_key("")
        '****'
        >>> mask_api_key(None)
        '****'
    """
    if not key or len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


# ============================================================================
# 错误响应工具
# ============================================================================

def error_response(
    message: str,
    code: str = "ERROR",
    status: int = 400,
    detail: str = "",
    request_id: str = ""
) -> tuple[dict, int]:
    """构造统一的错误响应
    
    Args:
        message: 错误消息
        code: 错误代码，默认为 "ERROR"
        status: HTTP状态码，默认为 400
        detail: 详细错误信息，默认为空
        request_id: 请求ID，用于追踪，默认为空
        
    Returns:
        tuple[dict, int]: 包含错误响应字典和HTTP状态码的元组
        
    Examples:
        >>> error_response("资源不存在", "NOT_FOUND", 404)
        ({'success': False, 'error': {'code': 'NOT_FOUND', 'message': '资源不存在', 'detail': ''}, ...}, 404)
    """
    response = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "detail": detail,
        },
        "meta": {
            "request_id": request_id,
            "timestamp": utc_now(),
        },
    }
    return response, status


# ============================================================================
# 日期时间工具
# ============================================================================

def format_datetime(
    dt: Optional[datetime],
    fmt: str = "%Y-%m-%d %H:%M:%S"
) -> Optional[str]:
    """格式化日期时间对象为字符串
    
    Args:
        dt: 日期时间对象，如果为None则返回None
        fmt: 格式化字符串，默认为 "%Y-%m-%d %H:%M:%S"
        
    Returns:
        Optional[str]: 格式化后的日期时间字符串，如果dt为None则返回None
        
    Examples:
        >>> from datetime import datetime
        >>> dt = datetime(2026, 6, 29, 12, 30, 0)
        >>> format_datetime(dt)
        '2026-06-29 12:30:00'
        >>> format_datetime(dt, "%Y/%m/%d")
        '2026/06/29'
        >>> format_datetime(None)
        None
    """
    return dt.strftime(fmt) if dt else None


def parse_datetime(
    date_str: str,
    fmt: str = "%Y-%m-%d %H:%M:%S"
) -> Optional[datetime]:
    """解析日期时间字符串为datetime对象
    
    Args:
        date_str: 日期时间字符串
        fmt: 格式化字符串，默认为 "%Y-%m-%d %H:%M:%S"
        
    Returns:
        Optional[datetime]: 解析后的datetime对象，如果解析失败则返回None
        
    Examples:
        >>> parse_datetime("2026-06-29 12:30:00")
        datetime(2026, 6, 29, 12, 30, 0)
        >>> parse_datetime("invalid")
        None
    """
    try:
        return datetime.strptime(date_str, fmt)
    except (ValueError, TypeError):
        return None


def get_date_string(days_ago: int = 0) -> str:
    """获取指定天数前的日期字符串（YYYY-MM-DD格式）
    
    Args:
        days_ago: 距离今天的天数，0表示今天，默认为0
        
    Returns:
        str: 日期字符串，格式为 "YYYY-MM-DD"
        
    Examples:
        >>> get_date_string(0)  # 今天
        '2026-06-29'
        >>> get_date_string(1)  # 昨天
        '2026-06-28'
    """
    from datetime import timedelta
    target_date = date.today() - timedelta(days=days_ago)
    return target_date.strftime("%Y-%m-%d")


# ============================================================================
# 分页工具
# ============================================================================

def normalize_pagination(
    page: int,
    page_size: int,
    max_page_size: int = 100
) -> tuple[int, int]:
    """标准化分页参数
    
    确保分页参数在合理范围内：
    - page >= 1
    - 1 <= page_size <= max_page_size
    
    Args:
        page: 页码，会自动调整为至少1
        page_size: 每页数量，会自动限制在 [1, max_page_size] 范围内
        max_page_size: 最大每页数量，默认为100
        
    Returns:
        tuple[int, int]: 标准化后的 (page, page_size) 元组
        
    Examples:
        >>> normalize_pagination(0, 10)
        (1, 10)
        >>> normalize_pagination(1, 200)
        (1, 100)
        >>> normalize_pagination(-1, 0)
        (1, 1)
    """
    page = max(1, page)
    page_size = min(max(1, page_size), max_page_size)
    return page, page_size


def calculate_offset(page: int, page_size: int) -> int:
    """计算数据库查询的OFFSET值
    
    Args:
        page: 页码（从1开始）
        page_size: 每页数量
        
    Returns:
        int: OFFSET值，确保非负
        
    Examples:
        >>> calculate_offset(1, 20)
        0
        >>> calculate_offset(2, 20)
        20
        >>> calculate_offset(0, 20)  # page会被视为1
        0
    """
    page = max(1, page)
    return (page - 1) * page_size


def calculate_total_pages(total: int, page_size: int) -> int:
    """计算总页数
    
    Args:
        total: 总记录数
        page_size: 每页数量
        
    Returns:
        int: 总页数，至少为1
        
    Examples:
        >>> calculate_total_pages(100, 20)
        5
        >>> calculate_total_pages(101, 20)
        6
        >>> calculate_total_pages(0, 20)
        1
    """
    if total <= 0 or page_size <= 0:
        return 1
    return max(1, (total + page_size - 1) // page_size)


# ============================================================================
# 数据验证工具
# ============================================================================

def is_valid_email(email: str) -> bool:
    """验证邮箱地址格式
    
    Args:
        email: 待验证的邮箱地址
        
    Returns:
        bool: 邮箱格式是否有效
        
    Examples:
        >>> is_valid_email("user@example.com")
        True
        >>> is_valid_email("invalid-email")
        False
        >>> is_valid_email("")
        False
    """
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_url(url: str) -> bool:
    """验证URL格式
    
    Args:
        url: 待验证的URL地址
        
    Returns:
        bool: URL格式是否有效
        
    Examples:
        >>> is_valid_url("https://example.com")
        True
        >>> is_valid_url("http://localhost:8000/api")
        True
        >>> is_valid_url("not-a-url")
        False
    """
    if not url:
        return False
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """清理字符串，去除首尾空格并限制长度
    
    Args:
        value: 待清理的字符串
        max_length: 最大长度，默认为1000
        
    Returns:
        str: 清理后的字符串
        
    Examples:
        >>> sanitize_string("  hello world  ")
        'hello world'
        >>> sanitize_string("x" * 2000, max_length=100)
        'x' * 100
    """
    if not value:
        return ""
    cleaned = value.strip()
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned


# ============================================================================
# 字典安全访问工具
# ============================================================================

def safe_get(
    data: dict,
    key: str,
    default: Optional[T] = None,
    expected_type: Optional[type] = None
) -> Optional[T]:
    """安全地从字典中获取值
    
    支持类型检查，如果值的类型不符合预期则返回默认值。
    
    Args:
        data: 字典数据
        key: 要获取的键
        default: 默认值，默认为None
        expected_type: 期望的类型，如果提供则进行类型检查
        
    Returns:
        Optional[T]: 获取到的值，如果键不存在或类型不匹配则返回default
        
    Examples:
        >>> safe_get({"name": "Alice"}, "name")
        'Alice'
        >>> safe_get({}, "name", "Unknown")
        'Unknown'
        >>> safe_get({"age": "25"}, "age", 0, int)  # 类型不匹配
        0
        >>> safe_get({"age": 25}, "age", 0, int)
        25
    """
    if not isinstance(data, dict):
        return default
    
    value = data.get(key, default)
    
    if expected_type is not None and value is not None:
        if not isinstance(value, expected_type):
            return default
    
    return value


def safe_get_list(
    data: dict,
    key: str,
    default: Optional[list] = None
) -> list:
    """安全地从字典中获取列表
    
    Args:
        data: 字典数据
        key: 要获取的键
        default: 默认列表，默认为空列表
        
    Returns:
        list: 获取到的列表，如果键不存在或值不是列表则返回default
        
    Examples:
        >>> safe_get_list({"items": [1, 2, 3]}, "items")
        [1, 2, 3]
        >>> safe_get_list({}, "items")
        []
        >>> safe_get_list({"items": "not a list"}, "items")
        []
    """
    if default is None:
        default = []
    value = data.get(key, default)
    return value if isinstance(value, list) else default


def safe_get_dict(
    data: dict,
    key: str,
    default: Optional[dict] = None
) -> dict:
    """安全地从字典中获取嵌套字典
    
    Args:
        data: 字典数据
        key: 要获取的键
        default: 默认字典，默认为空字典
        
    Returns:
        dict: 获取到的字典，如果键不存在或值不是字典则返回default
        
    Examples:
        >>> safe_get_dict({"config": {"key": "value"}}, "config")
        {'key': 'value'}
        >>> safe_get_dict({}, "config")
        {}
        >>> safe_get_dict({"config": "not a dict"}, "config")
        {}
    """
    if default is None:
        default = {}
    value = data.get(key, default)
    return value if isinstance(value, dict) else default


# ============================================================================
# 数值范围限制工具
# ============================================================================

def clamp(value: Union[int, float], min_value: Union[int, float], max_value: Union[int, float]) -> Union[int, float]:
    """将数值限制在指定范围内
    
    Args:
        value: 待限制的数值
        min_value: 最小值
        max_value: 最大值
        
    Returns:
        Union[int, float]: 限制后的数值
        
    Examples:
        >>> clamp(5, 0, 10)
        5
        >>> clamp(-5, 0, 10)
        0
        >>> clamp(15, 0, 10)
        10
    """
    return max(min_value, min(value, max_value))


def clamp_percentage(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    """将百分比数值限制在 [0, 1] 范围内
    
    Args:
        value: 百分比数值（0-1之间）
        min_value: 最小值，默认为0.0
        max_value: 最大值，默认为1.0
        
    Returns:
        float: 限制后的百分比数值
        
    Examples:
        >>> clamp_percentage(0.5)
        0.5
        >>> clamp_percentage(-0.1)
        0.0
        >>> clamp_percentage(1.5)
        1.0
    """
    return clamp(value, min_value, max_value)
