"""
太极引擎 · ASI Agent Stability Index — v2.5 新增

参考：ASI论文12维量化框架（4类×3维）+ 50交互滚动窗口。
太极第七律·生生不息——量化是进化的前提，看不见就改进不了。

核心机制：
  1. 12维指标 — 响应一致性(3维) + 工具使用模式(3维) + Agent间协调(3维) + 行为边界(3维)
  2. 滚动窗口 — 50次交互的滑动窗口，避免早期数据污染
  3. ASI综合评分 — 四类加权求和，0-1分数
  4. 趋势追踪 — 视觉化漂移历史，异常自动告警

使用方式：
    from engine.asi_index import asi_index
    asi_index.record_interaction(session_id="s1", metrics={...})
    asi_score = asi_index.compute_asi(session_id="s1")
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import json
import logging
import math
import os
import time

logger = logging.getLogger("niuma.asi")


# ============================================================
# 数据模型
# ============================================================

@dataclass
class InteractionMetrics:
    """一次交互的完整度量。"""
    session_id: str
    interaction_id: int           # 递增编号
    timestamp: float

    # 响应一致性（权重0.30）
    semantic_similarity: float    # 输出语义相似度（当前vs基线）0-1
    decision_path_stability: float  # 决策路径稳定性 0-1
    confidence_calibration: float  # 置信度校准（实际vs预期）0-1

    # 工具使用模式（权重0.25）
    tool_selection_stability: float  # 工具选择稳定性 0-1
    tool_call_sequence_consistency: float  # 调用序列一致性 0-1
    parameter_drift: float           # 参数漂移 0-1

    # Agent间协调（权重0.25）
    consensus_agreement: float     # 共识同意率 0-1
    handoff_efficiency: float      # 交接效率 0-1
    role_compliance: float         # 角色遵循 0-1

    # 行为边界（权重0.20）
    output_length_stability: float  # 输出长度稳定性 0-1
    error_pattern_emergence: float  # 错误模式涌现率 0-1
    human_intervention_rate: float  # 人工干预率 0-1


@dataclass
class ASIReport:
    """一次ASI计算报告。"""
    session_id: str
    asi_score: float                     # 综合ASI 0-1（1=完全稳定）
    window_size: int                     # 窗口内的交互数
    category_scores: dict[str, float] = field(default_factory=dict)
    severity: str = "green"              # green / yellow / red
    trend: str = "stable"                # improving / stable / declining
    alerts: list[str] = field(default_factory=list)
    computed_at: float = field(default_factory=time.time)


# ============================================================
# ASI计算引擎
# ============================================================

class ASIIndex:
    """ASI Agent Stability Index 计算引擎。

    太极哲学：顺势而为——ASI不是评判好坏，是告诉你在哪儿、往哪走。
    """

    WINDOW_SIZE = 50               # 滚动窗口大小
    MIN_SAMPLES = 10               # 至少10个样本才计算

    def __init__(self) -> None:
        self._sessions: dict[str, list[InteractionMetrics]] = {}
        self._reports: dict[str, list[ASIReport]] = {}
        self._global_asi_history: list[float] = []

    # ----------------------------------------------------------
    # 数据记录
    # ----------------------------------------------------------

    def record_interaction(self, session_id: str, metrics: dict) -> int:
        """记录一次交互的12维指标。

        Args:
            session_id: 会话ID
            metrics: 12维指标字典（缺省字段自动填0）
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        session_metrics = self._sessions[session_id]
        interaction_id = len(session_metrics) + 1

        m = InteractionMetrics(
            session_id=session_id,
            interaction_id=interaction_id,
            timestamp=time.time(),
            semantic_similarity=metrics.get("semantic_similarity", 0.8),
            decision_path_stability=metrics.get("decision_path_stability", 0.8),
            confidence_calibration=metrics.get("confidence_calibration", 0.7),
            tool_selection_stability=metrics.get("tool_selection_stability", 0.8),
            tool_call_sequence_consistency=metrics.get("tool_call_sequence_consistency", 0.8),
            parameter_drift=metrics.get("parameter_drift", 0.0),
            consensus_agreement=metrics.get("consensus_agreement", 1.0),
            handoff_efficiency=metrics.get("handoff_efficiency", 1.0),
            role_compliance=metrics.get("role_compliance", 0.8),
            output_length_stability=metrics.get("output_length_stability", 0.8),
            error_pattern_emergence=metrics.get("error_pattern_emergence", 0.0),
            human_intervention_rate=metrics.get("human_intervention_rate", 0.0),
        )

        session_metrics.append(m)
        if len(session_metrics) > self.WINDOW_SIZE * 3:
            self._sessions[session_id] = session_metrics[-self.WINDOW_SIZE * 2:]

        return interaction_id

    # ----------------------------------------------------------
    # ASI计算
    # ----------------------------------------------------------

    def compute_asi(self, session_id: str) -> ASIReport | None:
        """计算当前ASI综合评分。

        只使用最近WINDOW_SIZE个交互。
        """
        all_metrics = self._sessions.get(session_id, [])
        if not all_metrics:
            return None

        window = all_metrics[-self.WINDOW_SIZE:] if len(all_metrics) > self.WINDOW_SIZE else all_metrics

        if len(window) < self.MIN_SAMPLES:
            return ASIReport(
                session_id=session_id,
                asi_score=0.0,
                window_size=len(window),
                alerts=[f"样本不足（{len(window)}/{self.MIN_SAMPLES}），ASI不可靠"],
                severity="green",
            )

        # 计算四类指标的窗口均值（越高越好，0-1）
        avg = self._compute_averages(window)

        # 类别得分
        responsiveness = (
            _avg_or_1(avg, "semantic_similarity") * 0.40 +
            _avg_or_1(avg, "decision_path_stability") * 0.35 +
            _avg_or_1(avg, "confidence_calibration") * 0.25
        )
        tool_usage = (
            _avg_or_1(avg, "tool_selection_stability") * 0.40 +
            _avg_or_1(avg, "tool_call_sequence_consistency") * 0.35 +
            (1.0 - _avg_or_0(avg, "parameter_drift")) * 0.25  # 漂移越低越好
        )
        coordination = (
            _avg_or_1(avg, "consensus_agreement") * 0.35 +
            _avg_or_1(avg, "handoff_efficiency") * 0.35 +
            _avg_or_1(avg, "role_compliance") * 0.30
        )
        behavioral = (
            _avg_or_1(avg, "output_length_stability") * 0.40 +
            (1.0 - _avg_or_0(avg, "error_pattern_emergence")) * 0.35 +  # 越低越好
            (1.0 - _avg_or_0(avg, "human_intervention_rate")) * 0.25     # 越低越好
        )

        # 四类加权（对齐ASI论文权重）
        asi_score = round(
            responsiveness * 0.30 +
            tool_usage * 0.25 +
            coordination * 0.25 +
            behavioral * 0.20,
            4,
        )

        # 严重级别（参考ASI论文阈值，需要较高基准因为初始值都很高）
        if asi_score < 0.60:
            severity = "red"
        elif asi_score < 0.75:
            severity = "yellow"
        else:
            severity = "green"

        # 趋势分析
        trend = self._compute_trend(session_id, asi_score)

        # 告警
        alerts = self._generate_alerts(avg, asi_score, severity)

        report = ASIReport(
            session_id=session_id,
            asi_score=asi_score,
            window_size=len(window),
            category_scores={
                "responsiveness": round(responsiveness, 3),
                "tool_usage": round(tool_usage, 3),
                "coordination": round(coordination, 3),
                "behavioral": round(behavioral, 3),
            },
            severity=severity,
            trend=trend,
            alerts=alerts,
        )

        # 保存报告
        self._reports.setdefault(session_id, []).append(report)
        self._global_asi_history.append(asi_score)

        if severity != "green":
            logger.warning(
                "ASI=%s session=%.4f severity=%s window=%d alerts=%d",
                session_id[:12], asi_score, severity, len(window), len(alerts),
            )

        return report

    def _compute_averages(self, window: list[InteractionMetrics]) -> dict[str, float]:
        """计算窗口内各维度的平均值。"""
        n = len(window)
        sums: dict[str, float] = {}
        for m in window:
            sums["semantic_similarity"] = sums.get("semantic_similarity", 0) + m.semantic_similarity
            sums["decision_path_stability"] = sums.get("decision_path_stability", 0) + m.decision_path_stability
            sums["confidence_calibration"] = sums.get("confidence_calibration", 0) + m.confidence_calibration
            sums["tool_selection_stability"] = sums.get("tool_selection_stability", 0) + m.tool_selection_stability
            sums["tool_call_sequence_consistency"] = sums.get("tool_call_sequence_consistency", 0) + m.tool_call_sequence_consistency
            sums["parameter_drift"] = sums.get("parameter_drift", 0) + m.parameter_drift
            sums["consensus_agreement"] = sums.get("consensus_agreement", 0) + m.consensus_agreement
            sums["handoff_efficiency"] = sums.get("handoff_efficiency", 0) + m.handoff_efficiency
            sums["role_compliance"] = sums.get("role_compliance", 0) + m.role_compliance
            sums["output_length_stability"] = sums.get("output_length_stability", 0) + m.output_length_stability
            sums["error_pattern_emergence"] = sums.get("error_pattern_emergence", 0) + m.error_pattern_emergence
            sums["human_intervention_rate"] = sums.get("human_intervention_rate", 0) + m.human_intervention_rate

        return {k: v / n for k, v in sums.items()}

    def _compute_trend(self, session_id: str, current_score: float) -> str:
        """计算ASI趋势（与历史对比）。"""
        reports = self._reports.get(session_id, [])
        if len(reports) < 2:
            return "baseline"  # 首次计算

        # 与上一个报告对比
        prev = reports[-1].asi_score
        if prev == 0:
            return "baseline"

        change = (current_score - prev) / prev
        if change > 0.03:
            return "improving"
        elif change < -0.03:
            return "declining"
        return "stable"

    def _generate_alerts(self, avg: dict, asi_score: float, severity: str) -> list[str]:
        """生成告警列表。"""
        alerts = []

        # 单独维度告警
        if _avg_or_0(avg, "parameter_drift") > 0.4:
            alerts.append(f"参数漂移偏高({_avg_or_0(avg, 'parameter_drift'):.0%})")
        if _avg_or_0(avg, "error_pattern_emergence") > 0.3:
            alerts.append(f"错误模式涌现({_avg_or_0(avg, 'error_pattern_emergence'):.0%})")
        if _avg_or_0(avg, "human_intervention_rate") > 0.2:
            alerts.append(f"人工干预率偏高({_avg_or_0(avg, 'human_intervention_rate'):.0%})")
        if _avg_or_1(avg, "role_compliance") < 0.5:
            alerts.append(f"角色遵循度低({_avg_or_1(avg, 'role_compliance'):.0%})")

        if severity in ("red",):
            alerts.append(f"ASI严重退化({asi_score:.0%})，建议重置Agent上下文")

        return alerts

    # ----------------------------------------------------------
    # 自适应阈值
    # ----------------------------------------------------------

    def get_adaptive_threshold(self, session_id: str) -> dict:
        """获取自适应告警阈值（基于历史数据动态调整）。"""
        reports = self._reports.get(session_id, [])
        if len(reports) < 5:
            return {"green": 0.80, "yellow": 0.60, "red": 0.40}

        scores = [r.asi_score for r in reports[-20:]]
        mean_asi = sum(scores) / len(scores)
        std_asi = math.sqrt(sum((s - mean_asi) ** 2 for s in scores) / len(scores)) if len(scores) > 1 else 0.05

        return {
            "mean": round(mean_asi, 3),
            "std": round(std_asi, 3),
            "green": round(mean_asi - 0.5 * std_asi, 3),     # 低于均值0.5σ → 绿色
            "yellow": round(mean_asi - 1.0 * std_asi, 3),    # 低于均值1σ → 黄色
            "red": round(mean_asi - 2.0 * std_asi, 3),       # 低于均值2σ → 红色
        }

    # ----------------------------------------------------------
    # 全局统计
    # ----------------------------------------------------------

    def get_global_asi(self) -> float:
        """获取全局ASI均值。"""
        if not self._global_asi_history:
            return 0.0
        return round(sum(self._global_asi_history) / len(self._global_asi_history), 4)

    def get_session_asi_history(
        self, session_id: str, limit: int = 20
    ) -> list[dict]:
        """获取会话的ASI历史。"""
        reports = self._reports.get(session_id, [])[-limit:]
        return [
            {
                "asi_score": r.asi_score,
                "severity": r.severity,
                "trend": r.trend,
                "categories": r.category_scores,
                "alerts": r.alerts,
                "window_size": r.window_size,
                "computed_at": r.computed_at,
            }
            for r in reports
        ]

    def get_session_timeline(
        self, session_id: str, limit: int = 50
    ) -> list[dict]:
        """获取交互级的时间线（供前端图表）。"""
        all_metrics = self._sessions.get(session_id, [])[-limit:]
        return [
            {
                "interaction_id": m.interaction_id,
                "timestamp": m.timestamp,
                "responsiveness": round(
                    m.semantic_similarity * 0.4 + m.decision_path_stability * 0.35 + m.confidence_calibration * 0.25, 3),
                "tool_usage": round(
                    m.tool_selection_stability * 0.4 + m.tool_call_sequence_consistency * 0.35 + (1 - m.parameter_drift) * 0.25, 3),
                "coordination": round(
                    m.consensus_agreement * 0.35 + m.handoff_efficiency * 0.35 + m.role_compliance * 0.3, 3),
                "behavioral": round(
                    m.output_length_stability * 0.4 + (1 - m.error_pattern_emergence) * 0.35 + (1 - m.human_intervention_rate) * 0.25, 3),
            }
            for m in all_metrics
        ]

    def get_stats(self) -> dict:
        """ASI引擎统计。"""
        sessions = len(self._sessions)
        total_interactions = sum(len(v) for v in self._sessions.values())
        return {
            "sessions": sessions,
            "total_interactions": total_interactions,
            "global_asi": self.get_global_asi(),
            "active_sessions_alert": sum(
                1 for reports in self._reports.values()
                if reports and reports[-1].severity in ("yellow", "red")
            ),
        }


# ============================================================
# 工具函数
# ============================================================

def _avg_or_1(avg: dict, key: str) -> float:
    return avg.get(key, 1.0)

def _avg_or_0(avg: dict, key: str) -> float:
    return avg.get(key, 0.0)


# ============================================================
# 全局实例
# ============================================================

asi_index = ASIIndex()
