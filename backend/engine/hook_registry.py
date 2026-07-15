"""
太极引擎 · Hook Registry — chat_hooks 的依赖接入层

核心目的：解耦 chat_hooks.py 对 21 个引擎模块的直接依赖。
所有引擎访问器通过本 Registry 懒加载，chat_hooks 只 import 这一个模块。

设计原则：
  1. 懒加载：首次访问时才 import，改善启动时间
  2. 单例：每个访问器全局唯一实例
  3. 显式依赖：Registry 列表一目了然，谁依赖谁可审计
  4. 零魔法：所有 get_xxx() 都显式命名，不靠字符串查找
"""

from __future__ import annotations
from typing import Any, Callable, Awaitable
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("niuma.hooks")

# ============================================================
# 懒加载单例注册器
# ============================================================

class LazyLoader:
    """懒加载包装器——首次 .get() 时实例化，后续返回缓存实例。"""

    def __init__(self, import_path: str, class_name: str, *init_args, **init_kwargs) -> None:
        self._import_path = import_path
        self._class_name = class_name
        self._init_args = init_args
        self._init_kwargs = init_kwargs
        self._instance: Any = None
        self._error: str = ""

    def get(self) -> Any:
        if self._instance is not None:
            return self._instance
        if self._error:
            raise ImportError(f"LazyLoader 之前加载失败: {self._error}")
        try:
            mod = __import__(self._import_path, fromlist=[self._class_name])
            cls = getattr(mod, self._class_name)
            self._instance = cls(*self._init_args, **self._init_kwargs)
            return self._instance
        except Exception as e:
            self._error = str(e)
            logger.warning("LazyLoader 加载失败: %s.%s: %s", self._import_path, self._class_name, e)
            raise


class LazyModuleRef:
    """懒加载模块引用——访问模块级变量/单例。"""

    def __init__(self, import_path: str, attr_name: str) -> None:
        self._import_path = import_path
        self._attr_name = attr_name
        self._value: Any = None
        self._loaded = False
        self._error: str = ""

    def get(self) -> Any:
        if self._loaded:
            return self._value
        if self._error:
            logger.warning("LazyModuleRef 之前加载失败: %s", self._error)
            return None
        try:
            mod = __import__(self._import_path, fromlist=[self._attr_name])
            self._value = getattr(mod, self._attr_name)
            self._loaded = True
            return self._value
        except Exception as e:
            self._error = str(e)
            logger.warning("LazyModuleRef 加载失败: %s.%s: %s", self._import_path, self._attr_name, e)
            return None


# ============================================================
# Hook Registry — 依赖声明（一目了然，可审计）
# ============================================================

@dataclass
class HookRegistryDep:
    """单个依赖的元数据——用于文档生成和审计。"""
    name: str
    module: str
    role: str  # pre_check | post_record | error | reflection | both


# 完整依赖清单（文档用途，不影响运行时）
DEPENDENCY_MAP: list[HookRegistryDep] = [
    # === pre_chat_check 使用 ===
    HookRegistryDep("taiji", "engine.taiji", "pre_check"),
    HookRegistryDep("SmartAllocator", "engine.smart_allocator", "pre_check"),
    HookRegistryDep("token_budget", "engine.token_budget", "pre_check"),
    HookRegistryDep("watchdog", "engine.engine_watchdog", "pre_check"),
    HookRegistryDep("DynamicBalancer", "engine.dynamic_balancer", "pre_check"),
    HookRegistryDep("attention_engine", "engine.attention_engine", "pre_check"),
    HookRegistryDep("LocalAnswerChecker", "engine.local_answer_check", "pre_check"),
    HookRegistryDep("SwarmOrchestrator", "engine.swarm_orchestrator", "pre_check"),
    HookRegistryDep("taiji_mesh", "engine.taiji_mesh", "pre_check"),
    HookRegistryDep("FallbackCostAnalyzer", "engine.fallback_cost", "pre_check"),
    HookRegistryDep("dynamic_degradation", "engine.dynamic_degradation", "pre_check"),

    # === post_chat_record 使用 ===
    HookRegistryDep("ExecutionLogger", "engine.execution_log", "post_record"),
    HookRegistryDep("savings_engine", "engine.token_savings", "post_record"),
    HookRegistryDep("HonchoModeler", "engine.honcho_modeler", "post_record"),
    HookRegistryDep("healing_tracker", "engine.healing_tracker", "post_record"),
    HookRegistryDep("recursive_evolution", "engine.recursive_evolution", "post_record"),
    HookRegistryDep("context_drift", "engine.context_drift", "post_record"),

    # === handle_error 使用 ===
    HookRegistryDep("self_healing", "engine.self_healing", "error"),

    # === daily_reflection 使用 ===
    HookRegistryDep("ReflectionEngine", "engine.reflection", "reflection"),
    HookRegistryDep("ClosureEngine", "engine.closure_engine", "reflection"),
    HookRegistryDep("telemetry_hub", "engine.telemetry_hub", "reflection"),

    # === 全局追踪 ===
    HookRegistryDep("tracer", "engine.otel_tracer", "both"),
]

# ============================================================
# 懒加载访问器集合
# ============================================================

class HookRegistry:
    """chat_hooks 的统一依赖接入层。

    chat_hooks.py 从此类获取所有引擎实例，不再直接 import 21 个模块。
    所有访问器懒加载——首次 .get() 时才真正 import。
    """

    def __init__(self) -> None:
        # === 模块级单例（懒加载包装）===
        self._taiji = LazyModuleRef("engine.taiji", "taiji")
        self._token_budget = LazyModuleRef("engine.token_budget", "token_budget")
        self._watchdog = LazyModuleRef("engine.engine_watchdog", "watchdog")
        self._attention_engine = LazyModuleRef("engine.attention_engine", "attention_engine")
        self._savings_engine = LazyModuleRef("engine.token_savings", "savings_engine")
        self._healing_tracker = LazyModuleRef("engine.healing_tracker", "healing_tracker")
        self._dynamic_degradation = LazyModuleRef("engine.dynamic_degradation", "dynamic_degradation")
        self._recursive_evolution = LazyModuleRef("engine.recursive_evolution", "recursive_evolution")
        self._context_drift = LazyModuleRef("engine.context_drift", "context_drift")
        self._telemetry_hub = LazyModuleRef("engine.telemetry_hub", "telemetry_hub")
        self._tracer = LazyModuleRef("engine.otel_tracer", "tracer")
        self._taiji_mesh = LazyModuleRef("engine.taiji_mesh", "taiji_mesh")

        # === 类实例（懒加载包装）===
        self._smart_allocator = LazyLoader("engine.smart_allocator", "SmartAllocator")
        self._execution_logger = LazyLoader("engine.execution_log", "ExecutionLogger")
        self._dynamic_balancer = LazyLoader("engine.dynamic_balancer", "DynamicBalancer")
        self._local_answer_checker = LazyLoader("engine.local_answer_check", "LocalAnswerChecker")
        self._swarm_orchestrator = LazyLoader("engine.swarm_orchestrator", "SwarmOrchestrator")
        self._fallback_cost = LazyLoader("engine.fallback_cost", "FallbackCostAnalyzer")
        self._reflection_engine = LazyLoader("engine.reflection", "ReflectionEngine")
        self._honcho_modeler = LazyLoader("engine.honcho_modeler", "HonchoModeler")
        self._closure_engine = LazyLoader("engine.closure_engine", "ClosureEngine")
        self._self_healing = LazyLoader("engine.self_healing", "self_healing")

        # === 数据类型（直接导入，不算耦合）===
        from engine.smart_allocator import TaskType, ForceProbeInput, BudgetLevel, get_registry_name  # noqa
        from engine.token_budget import AlertLevel  # noqa
        from engine.execution_log import ExecutionRecord  # noqa
        from engine.self_healing import InterceptEvent, HealingAction  # noqa
        from engine.dynamic_balancer import RuntimeMode  # noqa
        from engine.swarm_orchestrator import TaskComplexity  # noqa

        self.TaskType = TaskType
        self.ForceProbeInput = ForceProbeInput
        self.BudgetLevel = BudgetLevel
        self.get_registry_name = get_registry_name
        self.AlertLevel = AlertLevel
        self.ExecutionRecord = ExecutionRecord
        self.InterceptEvent = InterceptEvent
        self.HealingAction = HealingAction
        self.RuntimeMode = RuntimeMode
        self.TaskComplexity = TaskComplexity

    # ------------------------------------------------------------
    # 访问器属性
    # ------------------------------------------------------------

    @property
    def taiji(self): return self._taiji.get()
    @property
    def token_budget(self): return self._token_budget.get()
    @property
    def watchdog(self): return self._watchdog.get()
    @property
    def attention_engine(self): return self._attention_engine.get()
    @property
    def savings_engine(self): return self._savings_engine.get()
    @property
    def healing_tracker(self): return self._healing_tracker.get()
    @property
    def dynamic_degradation(self): return self._dynamic_degradation.get()
    @property
    def recursive_evolution(self): return self._recursive_evolution.get()
    @property
    def context_drift(self): return self._context_drift.get()
    @property
    def telemetry_hub(self): return self._telemetry_hub.get()
    @property
    def tracer(self): return self._tracer.get()
    @property
    def taiji_mesh(self): return self._taiji_mesh.get()

    @property
    def smart_allocator(self): return self._smart_allocator.get()
    @property
    def execution_logger(self): return self._execution_logger.get()
    @property
    def dynamic_balancer(self): return self._dynamic_balancer.get()
    @property
    def local_answer_checker(self): return self._local_answer_checker.get()
    @property
    def swarm_orchestrator(self): return self._swarm_orchestrator.get()
    @property
    def fallback_cost(self): return self._fallback_cost.get()
    @property
    def reflection_engine(self): return self._reflection_engine.get()
    @property
    def honcho_modeler(self): return self._honcho_modeler.get()
    @property
    def closure_engine(self): return self._closure_engine.get()
    @property
    def self_healing(self): return self._self_healing.get()

    # ------------------------------------------------------------
    # 批量创建（供 ChatIntegration.__init__ 使用）
    # ------------------------------------------------------------

    def create_engines(self) -> dict[str, Any]:
        """一次性创建所有 ChatIntegration 需要的引擎实例。"""
        result: dict[str, Any] = {}
        for name in [
            "smart_allocator", "execution_logger", "dynamic_balancer",
            "local_answer_checker", "swarm_orchestrator", "fallback_cost",
            "reflection_engine", "honcho_modeler", "closure_engine", "self_healing",
        ]:
            try:
                result[name] = getattr(self, name)
            except Exception as e:
                logger.warning("HookRegistry 引擎 %s 创建失败: %s", name, e)
                result[name] = None
        return result

    def get_static_refs(self) -> dict[str, Any]:
        """获取模块级单例引用。"""
        refs: dict[str, Any] = {}
        for name in [
            "taiji", "token_budget", "watchdog", "attention_engine",
            "savings_engine", "healing_tracker", "dynamic_degradation",
            "recursive_evolution", "telemetry_hub", "tracer", "taiji_mesh",
        ]:
            refs[name] = getattr(self, name)
        return refs

    def get_audit_report(self) -> dict:
        """生成依赖审计报告。"""
        return {
            "total_deps": len(DEPENDENCY_MAP),
            "by_role": {
                "pre_check": len([d for d in DEPENDENCY_MAP if d.role in ("pre_check", "both")]),
                "post_record": len([d for d in DEPENDENCY_MAP if d.role in ("post_record", "both")]),
                "error": len([d for d in DEPENDENCY_MAP if d.role == "error"]),
                "reflection": len([d for d in DEPENDENCY_MAP if d.role == "reflection"]),
            },
            "deps": [{"name": d.name, "module": d.module, "role": d.role} for d in DEPENDENCY_MAP],
        }


# 全局单例
hook_registry = HookRegistry()
