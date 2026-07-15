"""
太极引擎 · 失败驱动进化引擎（Failure-Driven Evolution）— v2.0 新增

参考：EvoSkill (Sentient 2026.3) — 双层故障溯源+三类优化。
太极第七律·生生不息——失败不是结束，是进化的燃料。

核心机制：
  1. 故障溯源（Fault Triage）— 双层分类：根本原因层 → 具体类型层
  2. 优化方案（Optimization）— 三类行动：缺能力→新建，场景窄→扩容，规划缺陷→补辅助
  3. 失败模式库（Failure Pattern DB）— 积累失败模式，防止同类错误重复发生
  4. 自愈触发（Self-Healing Trigger）— 检测到已知模式→自动应用修复方案

设计原则（铁则）：
  - 只从真实失败中学习，不臆造"可能失败"
  - 修复方案必须有验证，不盲改
  - 失败模式库渐进积累，不全量重建

使用方式：
    from engine.failure_driver import failure_driver
    # 记录失败
    await failure_driver.record_failure(
        task_type="coding", error_type="timeout", model="deepseek-v4",
        context="API调用超过30秒无响应", tools_used=["code_execute"]
    )
    # 获取建议
    suggestions = await failure_driver.get_suggestions("coding")
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import asyncio
import json
import logging
import os
import re
import time

logger = logging.getLogger("niuma.failure_driver")


# ============================================================
# 数据模型
# ============================================================

@dataclass
class FailureRecord:
    """一次失败的完整记录。"""
    id: str
    timestamp: float
    task_type: str                # coding/writing/analysis
    error_type: str               # timeout/parse_error/model_unavailable/permission_denied/low_quality
    root_cause: str               # 根本原因分类（L1）
    sub_cause: str                # 具体类型（L2）
    model: str
    tools_used: list[str]
    context: str                  # 失败上下文摘要
    resolved: bool = False        # 是否已解决
    resolution: str = ""          # 解决方案
    resolution_type: str = ""     # create_capability / expand_scope / add_guard
    frequency: int = 1            # 同类失败次数
    last_seen: float = field(default_factory=time.time)


# ============================================================
# L1 根本原因分类
# ============================================================

_L1_CAUSE_MAP = {
    "timeout": "infrastructure",
    "rate_limit": "infrastructure",
    "connection_error": "infrastructure",
    "crash": "infrastructure",
    "out_of_memory": "infrastructure",
    "parse_error": "capability_gap",
    "invalid_output": "capability_gap",
    "missing_tool": "capability_gap",
    "tool_error": "capability_gap",
    "model_unavailable": "routing",
    "model_degraded": "routing",
    "low_quality": "quality",
    "gate_rejection": "quality",
    "user_complaint": "quality",
    "permission_denied": "policy",
    "access_violation": "policy",
    "token_exhausted": "budget",
    "context_overflow": "budget",
}


_L2_DIAGNOSIS = {
    "capability_gap": {
        "missing_tool": "缺少必要的工具/技能",
        "parse_error": "输出格式解析失败",
        "invalid_output": "输出不符合预期格式",
        "tool_error": "工具调用失败",
    },
    "infrastructure": {
        "timeout": "API超时或subprocess超时",
        "rate_limit": "API限流",
        "connection_error": "网络连接中断",
        "crash": "进程崩溃",
        "out_of_memory": "OOM",
    },
    "routing": {
        "model_unavailable": "模型不可用（禁用/下线）",
        "model_degraded": "模型性能退化",
    },
    "quality": {
        "low_quality": "输出质量不达标",
        "gate_rejection": "Gate验证不通过",
        "user_complaint": "用户负面反馈",
    },
    "policy": {
        "permission_denied": "权限不足",
        "access_violation": "安全策略拦截",
    },
    "budget": {
        "token_exhausted": "Token预算耗尽",
        "context_overflow": "上下文溢出",
    },
}


# ============================================================
# 三类优化方案
# ============================================================

@dataclass
class FailureResolution:
    """失败驱动的优化方案。"""
    failure_type: str             # 对应 error_type
    resolution_type: str          # create_capability / expand_scope / add_guard
    description: str
    action: str                   # 执行动作
    auto_applicable: bool         # 是否可自动应用
    confidence: float = 0.5
    times_resolved: int = 0       # 成功解决的次数


# ============================================================
# 失败驱动引擎
# ============================================================

class FailureDriver:
    """失败驱动进化引擎——EvoSkill双层故障溯源。

    太极哲学：顺势而为——失败是环境反馈，听懂环境才能进化。
    """

    MAX_RECORDS = 200
    DATA_DIR = "data/failure_driver"

    def __init__(self, data_dir: str | None = None) -> None:
        self._data_dir = data_dir or self.DATA_DIR
        self._records: list[FailureRecord] = []
        self._patterns: dict[str, int] = {}       # error_type → frequency
        self._resolutions: list[FailureResolution] = []
        self._total_failures: int = 0
        self._is_initialized = False

    async def initialize(self) -> None:
        os.makedirs(self._data_dir, exist_ok=True)
        state_file = os.path.join(self._data_dir, "failure_state.json")
        try:
            if os.path.exists(state_file):
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                records_raw = state.get("records", [])
                self._records = [FailureRecord(**r) for r in records_raw[-self.MAX_RECORDS:]]
                self._patterns = state.get("patterns", {})
                self._total_failures = state.get("total_failures", 0)
                logger.info(f"失败驱动引擎恢复: {len(self._records)}条记录")
        except Exception:
            logger.debug("失败状态文件损坏", exc_info=True)

        # 初始化默认解决方案
        self._resolutions = [
            FailureResolution("timeout", "expand_scope", "任务超时", "增加超时时间/启用重试", True, 0.7),
            FailureResolution("missing_tool", "create_capability", "缺少工具", "建议创建新Skill或安装MCP工具", False, 0.5),
            FailureResolution("parse_error", "add_guard", "输出格式错误", "增加输出格式验证Gate", True, 0.6),
            FailureResolution("model_unavailable", "expand_scope", "模型不可用", "自动降级到备用模型", True, 0.9),
            FailureResolution("low_quality", "add_guard", "输出质量低", "增加Gate质量阈值或换模型", True, 0.5),
            FailureResolution("permission_denied", "add_guard", "权限不足", "提示用户授权或跳过此操作", True, 0.7),
        ]

        self._is_initialized = True

    async def _save_state(self) -> None:
        state_file = os.path.join(self._data_dir, "failure_state.json")
        try:
            records_raw = [
                {
                    "id": r.id, "timestamp": r.timestamp,
                    "task_type": r.task_type, "error_type": r.error_type,
                    "root_cause": r.root_cause, "sub_cause": r.sub_cause,
                    "model": r.model, "tools_used": r.tools_used,
                    "context": r.context, "resolved": r.resolved,
                    "resolution": r.resolution, "resolution_type": r.resolution_type,
                    "frequency": r.frequency, "last_seen": r.last_seen,
                }
                for r in self._records[-self.MAX_RECORDS:]
            ]
            state = {
                "records": records_raw,
                "patterns": self._patterns,
                "total_failures": self._total_failures,
                "saved_at": datetime.now().isoformat(),
            }
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ----------------------------------------------------------
    # 故障记录 + 双层溯源
    # ----------------------------------------------------------

    async def record_failure(
        self,
        task_type: str,
        error_type: str,
        model: str = "",
        context: str = "",
        tools_used: list[str] | None = None,
    ) -> FailureRecord:
        """记录一次失败——自动执行双层故障溯源。

        L1: 根本原因分类（infrastructure/capability_gap/routing/quality/policy/budget）
        L2: 具体类型诊断（从_L2_DIAGNOSIS查表）
        """
        # L1 分类
        root_cause = _L1_CAUSE_MAP.get(error_type, "capability_gap")

        # L2 诊断
        l2_map = _L2_DIAGNOSIS.get(root_cause, {})
        sub_cause = l2_map.get(error_type, f"{root_cause}:{error_type}")

        # 去重：同类失败累计频率
        for r in self._records[-20:]:
            if r.error_type == error_type and r.task_type == task_type and r.model == model:
                r.frequency += 1
                r.last_seen = time.time()
                self._patterns[error_type] = self._patterns.get(error_type, 0) + 1
                return r

        record = FailureRecord(
            id=f"fail-{int(time.time())}-{len(self._records)}",
            timestamp=time.time(),
            task_type=task_type,
            error_type=error_type,
            root_cause=root_cause,
            sub_cause=sub_cause,
            model=model,
            tools_used=tools_used or [],
            context=context[:300],
        )

        self._records.append(record)
        self._patterns[error_type] = self._patterns.get(error_type, 0) + 1
        self._total_failures += 1

        if len(self._records) > self.MAX_RECORDS:
            self._records = self._records[-self.MAX_RECORDS:]

        asyncio.ensure_future(self._save_state())

        logger.info(
            "失败记录: %s/%s → %s (%s)",
            task_type, error_type, root_cause, sub_cause[:50],
        )

        return record

    # ----------------------------------------------------------
    # 优化方案匹配
    # ----------------------------------------------------------

    async def get_suggestions(self, task_type: str) -> list[dict]:
        """为特定任务类型获取失败驱动优化建议。

        Returns:
            [{resolution_type, action, confidence, related_failures}, ...]
        """
        # 过滤相关失败
        related = [r for r in self._records if r.task_type == task_type and not r.resolved]
        if not related:
            return []

        # 按频率排序的错误类型
        error_counts: dict[str, int] = {}
        for r in related:
            error_counts[r.error_type] = error_counts.get(r.error_type, 0) + 1

        suggestions = []
        for error_type, count in sorted(error_counts.items(), key=lambda x: -x[1]):
            # 匹配预设方案
            for res in self._resolutions:
                if res.failure_type == error_type:
                    suggestions.append({
                        "error_type": error_type,
                        "frequency": count,
                        "resolution_type": res.resolution_type,
                        "action": res.action,
                        "description": res.description,
                        "confidence": res.confidence,
                        "auto_applicable": res.auto_applicable,
                    })
                    break
            else:
                # 无预设方案——生成通用建议
                root_cause = _L1_CAUSE_MAP.get(error_type, "capability_gap")
                suggestions.append({
                    "error_type": error_type,
                    "frequency": count,
                    "resolution_type": "add_guard",
                    "action": f"分析{error_type}错误模式，增加对应的防护措施",
                    "description": f"未知失败模式，已出现{count}次",
                    "confidence": 0.3,
                    "auto_applicable": False,
                })

        return suggestions

    async def get_auto_fixes(self, task_type: str) -> list[dict]:
        """获取可自动应用的修复方案。"""
        all_suggestions = await self.get_suggestions(task_type)
        return [s for s in all_suggestions if s.get("auto_applicable")]

    # ----------------------------------------------------------
    # 模式分析
    # ----------------------------------------------------------

    async def analyze_patterns(self) -> dict:
        """分析失败模式——微周期触发时调用。"""
        if len(self._records) < 5:
            return {"patterns": [], "summary": "样本不足"}

        # 热点错误类型
        hot_errors = sorted(self._patterns.items(), key=lambda x: -x[1])[:5]

        # 按任务类型统计
        by_task: dict[str, int] = {}
        for r in self._records[-100:]:
            by_task[r.task_type] = by_task.get(r.task_type, 0) + 1

        # 按根本原因统计
        by_cause: dict[str, int] = {}
        for r in self._records[-100:]:
            by_cause[r.root_cause] = by_cause.get(r.root_cause, 0) + 1

        # 未解决的失败数
        unresolved = sum(1 for r in self._records if not r.resolved)

        patterns = []
        for error_type, count in hot_errors:
            root_cause = _L1_CAUSE_MAP.get(error_type, "capability_gap")
            examples = [r.context for r in self._records if r.error_type == error_type and r.context][:2]
            patterns.append({
                "error_type": error_type,
                "count": count,
                "root_cause": root_cause,
                "examples": examples,
            })

        return {
            "total_failures": self._total_failures,
            "unresolved": unresolved,
            "hot_errors": patterns,
            "by_task_type": by_task,
            "by_root_cause": by_cause,
        }

    # ----------------------------------------------------------
    # 查询接口
    # ----------------------------------------------------------

    def get_stats(self) -> dict:
        return {
            "total_failures": self._total_failures,
            "records_count": len(self._records),
            "patterns": dict(sorted(self._patterns.items(), key=lambda x: -x[1])[:10]),
            "unresolved": sum(1 for r in self._records if not r.resolved),
            "top_root_causes": self._top_root_causes(),
            "initialized": self._is_initialized,
        }

    def _top_root_causes(self) -> list[str]:
        causes: dict[str, int] = {}
        for r in self._records[-50:]:
            causes[r.root_cause] = causes.get(r.root_cause, 0) + 1
        return [c[0] for c in sorted(causes.items(), key=lambda x: -x[1])[:5]]

    def get_recent_failures(self, limit: int = 20) -> list[dict]:
        return [
            {
                "id": r.id,
                "task_type": r.task_type,
                "error_type": r.error_type,
                "root_cause": r.root_cause,
                "sub_cause": r.sub_cause,
                "model": r.model,
                "context": r.context[:100],
                "frequency": r.frequency,
                "resolved": r.resolved,
                "timestamp": r.timestamp,
            }
            for r in self._records[-limit:]
        ]


# ============================================================
# 全局实例
# ============================================================

failure_driver = FailureDriver()
