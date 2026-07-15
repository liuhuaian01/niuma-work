"""Engine 模块惰性加载器

将非核心引擎模块从启动时预加载改为按需加载。
降低启动时间、崩溃风险面和内存占用。

Python 的 import 系统自带缓存，第二次调用无额外开销。

用法:
    from engine.lazy_loader import lazy_get
    # 等价于: from engine.goal_loop_engine import goal_loop
    goal_loop = lazy_get("engine.goal_loop_engine", "goal_loop")
"""

import importlib
import logging
from typing import Any

logger = logging.getLogger("niuma.lazy")


def lazy_get(module_path: str, attr: str | None = None) -> Any:
    """惰性导入引擎模块，首次访问时加载，后续返回 Python 缓存。

    Args:
        module_path: 完整模块路径，如 "engine.goal_loop_engine"
        attr: 模块内的属性/实例名称，如 "goal_loop"

    Returns:
        模块对象（attr=None 时）或模块内的指定属性

    示例:
        emergence_engine = lazy_get("engine.emergence", "emergence_engine")
        # 等价: from engine.emergence import emergence_engine
    """
    mod = importlib.import_module(module_path)
    if attr:
        return getattr(mod, attr)
    return mod
