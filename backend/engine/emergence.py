"""
太极引擎 · 涌现引擎（Emergence Engine）—— "三生万物"

太极七元中的三个三元（算力/认知/连接）在运转中自然产生新模式。
涌现引擎不创建模块，它观察模块间的交互，发现"本应存在但尚未被定义的规则/行为"。

核心理念：
  - 不是"我需要什么模块"，而是"模块之间已经自发形成了什么模式"
  - 发现 → 命名 → 提议 → 人类/Hermes 审批 → 创建规则
  - 零 Token 浪费：只在对话间隙（post_chat）异步运行

三大涌现路径：
  1. 模块互发现——43个模块各自独立，哪些模块在"偷偷协作"？
  2. 行为模式识别——用户连续N次做某操作，自动建议规则
  3. 跨模块协同——一个模块变强，该唤醒哪些关联模块？

v1.0 (2026-06-24): 模块注册表 + 模式检测 + 协同日志 + RecursiveEvolution 集成
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
import asyncio
import json
import logging
import time
import uuid

logger = logging.getLogger("niuma.emergence")


# ============================================================
# 数据模型
# ============================================================

@dataclass
class ModuleRecord:
    """太极引擎模块的注册信息。"""
    name: str
    file: str = ""
    version: str = "1.0"
    status: str = "active"          # active | degraded | disabled | stub
    category: str = "core"          # core | balancer | evolution | mesh | security | memory | skill
    dependencies: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)
    signals_emitted: list[str] = field(default_factory=list)   # 本模块发出的事件
    signals_listened: list[str] = field(default_factory=list)  # 本模块监听的事件
    last_active_at: float = 0.0
    invocation_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0


@dataclass
class BehaviorPattern:
    """检测到的用户行为模式。"""
    id: str = field(default_factory=lambda: f"bp-{uuid.uuid4().hex[:8]}")
    name: str = ""                           # 人类可读的模式名，如 "连续3次用 DeepSeek 写代码"
    description: str = ""
    category: str = "unknown"                # model_switch | task_repeat | time_pattern | tool_usage
    occurrences: int = 0                     # 出现次数
    first_seen_at: float = 0.0
    last_seen_at: float = 0.0
    confidence: float = 0.0                  # 0-1，模式可信度
    suggested_rule: Optional[str] = None     # 基于此模式建议的 GoalLoop 规则
    status: str = "observing"                # observing | confirmed | rejected | rule_created


@dataclass
class CrossModuleEvent:
    """跨模块协同事件记录。"""
    id: str = field(default_factory=lambda: f"cme-{uuid.uuid4().hex[:8]}")
    from_module: str = ""
    to_module: str = ""
    event_type: str = ""                     # invocation | fallback | recovery | optimization | handoff
    detail: str = ""
    timestamp: float = field(default_factory=time.time)
    session_id: str = ""
    performance_delta: float = 0.0           # 正数=改善了，负数=变差了


@dataclass
class EmergenceInsight:
    """涌现洞察——引擎自己发现的"应该存在的规则"。"""
    id: str = field(default_factory=lambda: f"ei-{uuid.uuid4().hex[:8]}")
    title: str = ""
    body: str = ""                           # 完整描述
    source: str = ""                         # pattern | cross_module | anomaly | optimization
    modules_involved: list[str] = field(default_factory=list)
    suggested_action: str = ""               # "建议创建规则: 当X时自动Y"
    created_at: float = field(default_factory=time.time)
    status: str = "new"                      # new | reviewed | accepted | rejected | implemented


# ============================================================
# 涌现引擎
# ============================================================

class EmergenceEngine:
    """涌现引擎——"三生万物"的核心。

    不主动创造模块，观察已有的模块间协作，
    发现模式、命名规则、提出建议。
    """

    # 检测阈值
    PATTERN_MIN_OCCURRENCES = 3         # 最少出现次数才触发模式
    PATTERN_MIN_CONFIDENCE = 0.6        # 最小置信度
    CROSS_MODULE_LOG_MAX = 200          # 协同日志最大条数
    INSIGHT_LOG_MAX = 100               # 洞察日志最大条数

    def __init__(self) -> None:
        # 模块注册表
        self._modules: dict[str, ModuleRecord] = {}

        # 行为模式检测
        self._patterns: dict[str, BehaviorPattern] = {}
        self._action_history: list[dict[str, object]] = []     # 近期用户行为

        # 跨模块协同日志
        self._cross_module_events: list[CrossModuleEvent] = []

        # 涌现洞察
        self._insights: list[EmergenceInsight] = []

        # 统一信号总线（模块间松耦合通信用）
        self._signal_handlers: dict[str, list[Callable]] = {}

        self._initialized: bool = False

    # ================================================================
    # 初始化
    # ================================================================

    async def init(self) -> None:
        """初始化涌现引擎——扫描所有已加载的引擎模块。"""
        if self._initialized:
            return

        await self._scan_modules()
        self._initialized = True
        logger.info("涌现引擎初始化完成: %d 个模块已注册", len(self._modules))

    async def _scan_modules(self) -> None:
        """自动扫描 engine/ 目录下的所有模块并注册。

        不依赖显式手动注册——任何放在 engine/ 下的 .py 文件都会被发现。
        """
        try:
            from pathlib import Path
            engine_dir = Path(__file__).parent
            for py_file in engine_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                module_name = py_file.stem
                if module_name in ("emergence",):
                    continue  # 自己不算

                # 读取文件获取版本号（简单 grep）
                version = self._extract_version(py_file)

                record = ModuleRecord(
                    name=module_name,
                    file=py_file.name,
                    version=version,
                    status="active",
                    category=self._guess_category(module_name),
                    last_active_at=time.time(),
                )
                self._modules[module_name] = record
        except Exception as e:
            logger.warning("模块扫描失败: %s", e)

    @staticmethod
    def _extract_version(filepath: Any) -> str:
        """从文件注释中提取版本号。"""
        try:
            content = filepath.read_text(encoding="utf-8")
            for line in content.split("\n")[:10]:
                if "v1." in line or "v2." in line:
                    # 尝试提取版本号
                    import re
                    match = re.search(r"v(\d+\.\d+)", line)
                    if match:
                        return f"v{match.group(1)}"
        except Exception:
            pass
        return "1.0"

    @staticmethod
    def _guess_category(name: str) -> str:
        """根据模块名猜测分类。"""
        categories = {
            "balancer": ["dynamic_balancer", "fallback", "smart_allocator"],
            "evolution": ["recursive_evolution", "evolution_scheduler", "reflection", "closure"],
            "mesh": ["taiji_mesh"],
            "security": ["circuit_breaker", "healing", "watchdog", "capabilities"],
            "memory": ["execution_log", "ccr_store", "semantic_grader", "rule_router", "instruction_cache"],
            "skill": ["skill_adapter", "skill_registry"],
            "agent": ["swarm", "honcho"],
        }
        for cat, names in categories.items():
            if name in names:
                return cat
        return "core"

    # ================================================================
    # 信号总线——模块间松耦合通信
    # ================================================================

    def emit(self, signal: str, payload: dict[str, object] | None = None) -> None:
        """发出一个信号。监听该信号的所有模块将被通知。"""
        handlers = self._signal_handlers.get(signal, [])
        payload = payload or {}
        payload["_timestamp"] = time.time()
        for handler in handlers:
            try:
                handler(signal, payload)
            except Exception:
                pass

    def listen(self, signal: str, handler: Callable[[str, dict[str, object]], None]) -> None:
        """监听一个信号。"""
        if signal not in self._signal_handlers:
            self._signal_handlers[signal] = []
        self._signal_handlers[signal].append(handler)

    # ================================================================
    # 模块管理与互发现
    # ================================================================

    def register_module(self, record: ModuleRecord) -> None:
        """手动注册一个模块。"""
        self._modules[record.name] = record
        logger.debug("涌现引擎: 注册模块 %s (v%s)", record.name, record.version)

    def update_module_activity(
        self, name: str, latency_ms: float = 0.0, error: bool = False
    ) -> None:
        """更新模块活跃度。"""
        if name not in self._modules:
            return
        mod = self._modules[name]
        mod.last_active_at = time.time()
        mod.invocation_count += 1
        if error:
            mod.error_count += 1
        if latency_ms > 0 and mod.avg_latency_ms > 0:
            mod.avg_latency_ms = (mod.avg_latency_ms * 0.9) + (latency_ms * 0.1)
        elif latency_ms > 0:
            mod.avg_latency_ms = latency_ms

    def discover_collaborators(self, module_name: str) -> list[ModuleRecord]:
        """发现与指定模块"暗中协作"的其他模块——通过协同日志推断。

        Returns:
            按协同频率排序的关联模块列表。
        """
        related_events = [
            e for e in self._cross_module_events
            if e.from_module == module_name or e.to_module == module_name
        ]
        collaborator_counts: dict[str, int] = {}
        for event in related_events:
            other = event.to_module if event.from_module == module_name else event.from_module
            collaborator_counts[other] = collaborator_counts.get(other, 0) + 1

        sorted_names = sorted(collaborator_counts, key=collaborator_counts.get, reverse=True)
        return [
            self._modules[name]
            for name in sorted_names[:5]
            if name in self._modules
        ]

    def get_orphan_modules(self) -> list[str]:
        """找出从未与任何其他模块交互的"孤岛模块"。"""
        connected: set[str] = set()
        for event in self._cross_module_events:
            connected.add(event.from_module)
            connected.add(event.to_module)
        return [name for name in self._modules if name not in connected]

    # ================================================================
    # 行为模式识别——"用户连续N次做X"
    # ================================================================

    def record_action(self, action: dict[str, object]) -> None:
        """记录一次用户行为。由 chat_hooks 调用。"""
        self._action_history.append(action)
        # 限制历史长度
        if len(self._action_history) > 500:
            self._action_history = self._action_history[-500:]

    async def detect_patterns(self) -> list[BehaviorPattern]:
        """检测行为模式——在进化周期中调用。

        当前支持的检测类型：
        - model_switch: 用户连续使用同一模型
        - task_repeat: 用户重复相同类型的任务
        """
        new_patterns: list[BehaviorPattern] = []

        # 检测模型偏好模式
        model_pattern = self._detect_model_preference()
        if model_pattern:
            new_patterns.append(model_pattern)

        # 检测任务重复模式
        task_pattern = self._detect_task_repetition()
        if task_pattern:
            new_patterns.append(task_pattern)

        # 存储并返回新发现的模式
        for p in new_patterns:
            existing_key = self._pattern_key(p)
            if existing_key in self._patterns:
                existing = self._patterns[existing_key]
                existing.occurrences += 1
                existing.last_seen_at = time.time()
                existing.confidence = min(1.0, existing.confidence + 0.1)
                if existing.occurrences >= 5 and existing.status == "observing":
                    existing.status = "confirmed"
                    self._generate_insight_from_pattern(existing)
            else:
                self._patterns[existing_key] = p
                p.first_seen_at = time.time()
                p.last_seen_at = time.time()
                p.confidence = 0.3

        return [p for p in new_patterns if p.confidence >= self.PATTERN_MIN_CONFIDENCE]

    @staticmethod
    def _pattern_key(pattern: BehaviorPattern) -> str:
        """生成模式的唯一键——用于去重。"""
        return f"{pattern.category}:{pattern.name}"

    def _detect_model_preference(self) -> Optional[BehaviorPattern]:
        """检测模型偏好模式：最近N次对话使用了同一模型。"""
        recent = self._action_history[-20:]
        model_actions = [
            a for a in recent
            if isinstance(a.get("action"), str) and str(a["action"]) in ("chat", "send_message")
            and isinstance(a.get("model"), str)
        ]
        if len(model_actions) < self.PATTERN_MIN_OCCURRENCES:
            return None

        # 统计最近5次的模型
        last_5 = model_actions[-5:]
        model_counts: dict[str, int] = {}
        for a in last_5:
            model = str(a["model"])
            model_counts[model] = model_counts.get(model, 0) + 1

        dominant = max(model_counts, key=model_counts.get)
        count = model_counts[dominant]
        if count >= 3:  # 5次中至少3次用同一模型
            return BehaviorPattern(
                name=f"偏好模型: {dominant}",
                description=f"最近5次对话中{count}次使用了 {dominant}",
                category="model_switch",
                occurrences=count,
                confidence=count / 5.0,
                suggested_rule=f"默认模型切换到 {dominant}",
            )
        return None

    def _detect_task_repetition(self) -> Optional[BehaviorPattern]:
        """检测任务重复模式：用户连续执行同类型任务。"""
        recent = self._action_history[-30:]
        task_actions = [
            a for a in recent
            if isinstance(a.get("task_type"), str)
        ]
        if len(task_actions) < self.PATTERN_MIN_OCCURRENCES:
            return None

        # 统计最近10次的任务类型
        last_10 = task_actions[-10:]
        task_counts: dict[str, int] = {}
        for a in last_10:
            tt = str(a["task_type"])
            task_counts[tt] = task_counts.get(tt, 0) + 1

        dominant = max(task_counts, key=task_counts.get)
        count = task_counts[dominant]
        if count >= 4:  # 10次中至少4次同类型
            return BehaviorPattern(
                name=f"重复任务: {dominant}",
                description=f"最近10次任务中{count}次是 {dominant}",
                category="task_repeat",
                occurrences=count,
                confidence=count / 10.0,
                suggested_rule=f"为 {dominant} 创建快捷指令或自动化规则",
            )
        return None

    # ================================================================
    # 跨模块协同记录
    # ================================================================

    def log_cross_module(
        self,
        from_module: str,
        to_module: str,
        event_type: str,
        detail: str = "",
        performance_delta: float = 0.0,
    ) -> None:
        """记录一次跨模块协同事件。

        Args:
            from_module: 发起模块
            to_module: 目标模块
            event_type: invocation | fallback | recovery | optimization | handoff
            detail: 事件描述
            performance_delta: 性能变化（正数=改善）
        """
        event = CrossModuleEvent(
            from_module=from_module,
            to_module=to_module,
            event_type=event_type,
            detail=detail,
            performance_delta=performance_delta,
        )
        self._cross_module_events.append(event)

        # 更新模块依赖关系
        if from_module in self._modules and to_module in self._modules:
            from_mod = self._modules[from_module]
            to_mod = self._modules[to_module]
            if to_module not in from_mod.signals_emitted:
                from_mod.signals_emitted.append(to_module)
            if from_module not in to_mod.signals_listened:
                to_mod.signals_listened.append(from_module)

        # 限制日志大小
        if len(self._cross_module_events) > self.CROSS_MODULE_LOG_MAX:
            self._cross_module_events = self._cross_module_events[-self.CROSS_MODULE_LOG_MAX:]

    def get_cross_module_stats(self) -> dict[str, object]:
        """跨模块协同统计。"""
        module_pairs: dict[str, int] = {}
        for event in self._cross_module_events[-200:]:
            pair = f"{event.from_module}→{event.to_module}"
            module_pairs[pair] = module_pairs.get(pair, 0) + 1

        top_pairs = sorted(module_pairs.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_events": len(self._cross_module_events),
            "unique_pairs": len(module_pairs),
            "top_collaborations": [{"pair": p, "count": c} for p, c in top_pairs],
            "orphan_modules": self.get_orphan_modules(),
        }

    # ================================================================
    # 涌现洞察——"本应存在的规则"
    # ================================================================

    def _generate_insight_from_pattern(self, pattern: BehaviorPattern) -> None:
        """从确认的行为模式中生成洞察。"""
        insight = EmergenceInsight(
            title=f"涌现: {pattern.name}",
            body=f"涌现引擎观察到: {pattern.description}。置信度: {pattern.confidence:.2f}。\n\n"
                 f"建议: {pattern.suggested_rule}",
            source="pattern",
            modules_involved=[],
            suggested_action=pattern.suggested_rule or "",
        )
        self._insights.append(insight)

        # 限制洞察数量
        if len(self._insights) > self.INSIGHT_LOG_MAX:
            self._insights = self._insights[-self.INSIGHT_LOG_MAX:]

    def _generate_insights_from_cross_module(self) -> None:
        """从跨模块协同中检测异常并生成洞察。"""
        stats = self.get_cross_module_stats()
        orph_mods = stats.get("orphan_modules", [])

        # 洞察1: 孤岛模块——从未与任何人交互的模块
        if orph_mods and isinstance(orph_mods, list):
            for mod_name in orph_mods[:3]:
                insight = EmergenceInsight(
                    title=f"孤岛模块: {mod_name}",
                    body=f"模块 {mod_name} 自注册以来从未与其他模块交互。可能是：\n"
                          f"1. 该模块功能尚未被激活\n"
                          f"2. 该模块的集成点未被发现\n"
                          f"3. 该模块是冗余的，可以安全移除",
                    source="cross_module",
                    modules_involved=[mod_name],
                    suggested_action=f"审查模块 {mod_name}：激活集成点或标记为候选删除",
                )
                self._insights.append(insight)

        # 洞察2: 高频协同对——可能应该合并或建立显式依赖
        top = stats.get("top_collaborations", [])
        if top and isinstance(top, list):
            for item in top[:2]:
                pair = str(item["pair"])
                count = int(item["count"])
                if count >= 10:
                    parts = pair.split("→")
                    if len(parts) == 2:
                        insight = EmergenceInsight(
                            title=f"高频协同: {parts[0]} ↔ {parts[1]}",
                            body=f"最近200次记录中，{pair} 发生了 {count} 次。"
                                  f"这两个模块紧密耦合，建议建立显式依赖或合并为子模块。",
                            source="cross_module",
                            modules_involved=parts,
                            suggested_action=f"在两个模块间建立信号总线连接，减少直接调用",
                        )
                        self._insights.append(insight)

    # ================================================================
    # 进化集成
    # ================================================================

    async def run_emergence_cycle(self) -> dict[str, object]:
        """运行一次涌现周期。

        由 RecursiveEvolutionEngine 的微型周期触发。
        扫描所有已注册模块，检测新模式，生成洞察。
        """
        start = time.time()

        # 1. 行为模式检测
        patterns = await self.detect_patterns()
        new_patterns = len([p for p in patterns if p.confidence >= self.PATTERN_MIN_CONFIDENCE])

        # 2. 跨模块协同洞察
        self._generate_insights_from_cross_module()

        # 3. 模块健康扫描
        self._scan_module_health()

        elapsed = time.time() - start
        new_insights = sum(1 for i in self._insights[-10:] if i.status == "new")

        return {
            "cycle": "emergence",
            "modules_registered": len(self._modules),
            "patterns_total": len(self._patterns),
            "new_patterns": new_patterns,
            "new_insights": new_insights,
            "cross_module_events": len(self._cross_module_events),
            "orphans": len(self.get_orphan_modules()),
            "elapsed_ms": round(elapsed * 1000, 1),
        }

    def _scan_module_health(self) -> None:
        """扫描模块健康状态——标记长期未活动的模块。"""
        now = time.time()
        for name, mod in self._modules.items():
            if mod.status == "active":
                hours_inactive = (now - mod.last_active_at) / 3600
                if hours_inactive > 48:
                    mod.status = "degraded"
                    logger.info("涌现引擎: %s 48h未活动，标记为 degraded", name)

    # ================================================================
    # 查询接口——供前端/API使用
    # ================================================================

    def get_status(self) -> dict[str, object]:
        """引擎状态概览。"""
        return {
            "initialized": self._initialized,
            "modules": len(self._modules),
            "patterns": len(self._patterns),
            "cross_module_events": len(self._cross_module_events),
            "insights": len(self._insights),
            "orphan_modules": self.get_orphan_modules(),
        }

    def get_modules(self) -> list[dict[str, object]]:
        """所有已注册模块的详情。"""
        return [
            {
                "name": m.name,
                "version": m.version,
                "status": m.status,
                "category": m.category,
                "invocations": m.invocation_count,
                "errors": m.error_count,
                "avg_latency_ms": round(m.avg_latency_ms, 2),
                "dependencies": m.dependencies,
                "collaborators": [c.name for c in self.discover_collaborators(m.name)],
            }
            for m in self._modules.values()
        ]

    def get_patterns(self, status_filter: str = "all") -> list[dict[str, object]]:
        """检测到的行为模式。"""
        patterns = list(self._patterns.values())
        if status_filter != "all":
            patterns = [p for p in patterns if p.status == status_filter]
        patterns.sort(key=lambda p: p.confidence, reverse=True)
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "category": p.category,
                "occurrences": p.occurrences,
                "confidence": round(p.confidence, 2),
                "status": p.status,
                "suggested_rule": p.suggested_rule,
            }
            for p in patterns[:20]
        ]

    def get_insights(self, status_filter: str = "all") -> list[dict[str, object]]:
        """涌现洞察。"""
        insights = list(self._insights)
        if status_filter != "all":
            insights = [i for i in insights if i.status == status_filter]
        insights.sort(key=lambda i: i.created_at, reverse=True)
        return [
            {
                "id": i.id,
                "title": i.title,
                "body": i.body,
                "source": i.source,
                "modules_involved": i.modules_involved,
                "suggested_action": i.suggested_action,
                "status": i.status,
                "created_at": i.created_at,
            }
            for i in insights[:30]
        ]

    def get_cross_module_graph(self) -> dict[str, object]:
        """跨模块协同关系图（用于前端可视化）。"""
        nodes: list[dict[str, object]] = []
        edges: list[dict[str, object]] = []

        for name, mod in self._modules.items():
            nodes.append({
                "id": name,
                "label": name,
                "category": mod.category,
                "status": mod.status,
                "invocations": mod.invocation_count,
            })

        pair_counts: dict[tuple[str, str], int] = {}
        for event in self._cross_module_events[-500:]:
            pair = (event.from_module, event.to_module)
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

        for (src, dst), count in pair_counts.items():
            edges.append({
                "source": src,
                "target": dst,
                "weight": count,
            })

        return {"nodes": nodes, "edges": edges}

    def approve_insight(self, insight_id: str) -> bool:
        """标记一个洞察为已接受。"""
        for i in self._insights:
            if i.id == insight_id:
                i.status = "accepted"
                return True
        return False

    def reject_insight(self, insight_id: str) -> bool:
        """标记一个洞察为已拒绝。"""
        for i in self._insights:
            if i.id == insight_id:
                i.status = "rejected"
                return True
        return False


# 全局单例
emergence_engine = EmergenceEngine()
