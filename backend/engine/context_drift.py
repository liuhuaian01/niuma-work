"""
太极引擎 · 上下文漂移检测（Context Drift Detector）— v1.8: 6维扩展

行业数据：65%企业Agent失败源于上下文漂移而非Token耗尽。
2%的早期偏差 → 40%的末段失败率（QSAF框架，2025）。
v1.8参考：ASI论文12维Agent Stability Index，太极引擎取其中最关键的6维落地。

太极哲学：顺势而为不是"随波逐流"——注意到方向偏移，才有机会纠正。

核心机制:
  1. 意图锚定（Intent Anchor）— 记录对话初始目标
  2. 滑动窗口检测（Sliding Window）— 定期比对当前上下文 vs 原始意图
  3. 六维漂移评分（v1.8扩展）:
     - 词汇漂移（Term Drift）          权重0.20
     - 任务漂移（Task Drift）          权重0.25
     - 范围蔓延（Scope Drift）         权重0.15
     - 工具使用模式漂移（Tool Pattern） 权重0.15 [新]
     - 角色遵循度漂移（Role Adherence） 权重0.15 [新]
     - 输出长度稳定性（Output Length）   权重0.10 [新]
  4. 告警 → 建议 → 回滚（GoalLoop规则集成）
  5. 持久化 + 意识流事件

使用方式:
    from engine.context_drift import context_drift
    await context_drift.record_intent("session-1", "coding", "修复登录页bug", agent_role="代码助手")
    report = await context_drift.record_message(
        "session-1", "修复这个函数", assistant_message="已修复...",
        tools_used=["read_file", "edit_file"]
    )
    if report and report.severity == "red":
        # 触发GoalLoop规则建议
        ...
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import asyncio
import json
import logging
import os
import re
import time

logger = logging.getLogger("niuma.drift")


# ============================================================
# 配置
# ============================================================

class DriftThreshold:
    """漂移阈值——三段告警体系。"""
    GREEN = 0.20      # ≤ 0.20: 正常，无动作
    YELLOW = 0.40     # > 0.20: 轻度漂移，记录 + 可选警告
    RED = 0.60        # > 0.40: 明显漂移，触发GoalLoop规则建议
    CRITICAL = 0.80   # > 0.80: 严重漂移，建议用户确认任务是否已变更


# ============================================================
# 数据模型
# ============================================================

@dataclass
class IntentAnchor:
    """意图锚点——对话初始目标的快照。

    太极引擎记录的"出发时的方向"。
    """
    session_id: str
    task_type: str                     # coding / writing / analysis / search / conversation
    user_query: str                    # 用户的原始输入
    key_terms: set[str] = field(default_factory=set)  # 从query提取的关键词
    explicit_goals: list[str] = field(default_factory=list)  # 用户明示的目标
    scope_boundary: str = ""           # "本次对话的范围"——自然语言描述
    started_at: float = field(default_factory=time.time)
    message_count: int = 0
    last_reaffirmed_at: float = 0.0    # 用户最后一次确认"还在做这个"


@dataclass
class DriftReport:
    """一次漂移检测的结果。 — v1.8: 6维扩展（参考ASI论文12维框架）"""
    session_id: str
    drift_score: float                 # 0.0 ~ 1.0 综合漂移度
    # 原有3维
    term_drift: float                  # 词汇漂移（关键词重叠度下降）
    task_drift: float                  # 任务类型漂移
    scope_drift: float                 # 范围蔓延（话题扩散）
    # v1.8 新增3维 — 参考ASI Agent Stability Index
    tool_pattern_drift: float = 0.0    # 工具使用模式漂移（工具集变化）
    role_adherence_drift: float = 0.0  # 角色遵循度漂移（偏离指定角色）
    output_length_drift: float = 0.0   # 输出长度稳定性漂移（长度异常波动）
    findings: list[str] = field(default_factory=list)
    severity: str = "green"            # green / yellow / red / critical
    suggested_action: str = ""
    checked_at: float = field(default_factory=time.time)


@dataclass
class SessionContext:
    """一个对话会话的完整漂移上下文。 — v1.8: 6维扩展"""
    anchor: IntentAnchor
    message_count: int = 0
    drift_history: list[DriftReport] = field(default_factory=list)
    last_check_at: float = 0.0
    recent_messages: list[str] = field(default_factory=list)  # 最近N条用户消息缓存
    max_recent: int = 20               # 最多缓存20条用户消息
    # v1.8 新增: 工具使用模式追踪
    tool_calls_history: list[list[str]] = field(default_factory=list)  # 每条消息调用的工具列表
    baseline_tool_pattern: set[str] = field(default_factory=set)       # 前5条消息的基线工具集
    # v1.8 新增: 输出长度追踪
    output_lengths: list[int] = field(default_factory=list)            # 最近N次输出字符数
    baseline_output_length: float = 0.0                                # 基线平均输出长度
    # v1.8 新增: 角色追踪
    agent_role: str = ""                                               # Agent指定角色


# ============================================================
# 轻量分词器（零依赖）
# ============================================================

_STOP_WORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "什么",
    "怎么", "为什么", "如何", "怎样", "这个", "那个", "这些", "那些",
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "about", "up", "an", "the", "and", "but", "or", "if", "because",
    "this", "that", "it", "its", "also",
}

# 中英文词汇分隔的正则
_WORD_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\w]+')


def _extract_key_terms(text: str) -> set[str]:
    """从文本中提取关键词（去停用词、去单字）。"""
    if not text:
        return set()
    words = _WORD_RE.findall(text.lower())
    filtered = {
        w for w in words
        if len(w) > 1 and w not in _STOP_WORDS and not w.isdigit()
    }
    return filtered


def _compute_overlap(set_a: set[str], set_b: set[str]) -> float:
    """计算 set_a 中有多少比例出现在 set_b 中。"""
    if not set_a:
        return 1.0
    if not set_b:
        return 0.0
    overlap = len(set_a & set_b) / len(set_a)
    return overlap


def _classify_task_type(text: str) -> str:
    """从文本中推测任务类型。"""
    text_lower = text.lower()
    coding_hints = [
        "代码", "bug", "函数", "class", "def ", "import", "api", "git",
        "部署", "编译", "调试", "报错", "pr", "merge", "commit",
        "code", "function", "error", "fix", "implement", "refactor",
    ]
    analysis_hints = [
        "分析", "对比", "统计", "趋势", "报告", "review", "审计",
        "analyze", "compare", "report", "review", "summary",
    ]
    writing_hints = [
        "写", "文章", "文案", "小说", "内容", "大纲", "写作",
        "write", "article", "content", "story", "draft",
    ]
    search_hints = [
        "搜索", "查找", "查询", "find", "search", "look up",
        "get information", "what is", "tell me about",
    ]

    # 计算各类型的命中数
    scores = {
        "coding": sum(1 for h in coding_hints if h in text_lower),
        "analysis": sum(1 for h in analysis_hints if h in text_lower),
        "writing": sum(1 for h in writing_hints if h in text_lower),
        "search": sum(1 for h in search_hints if h in text_lower),
    }

    max_type = max(scores, key=scores.get)
    return max_type if scores[max_type] > 0 else "conversation"


# ============================================================
# 上下文漂移检测引擎
# ============================================================

class ContextDriftDetector:
    """上下文漂移检测引擎。

    太极七元·认知三元——"个体→群体→涌现"的守护者。
    检测个体对话是否偏离了意图锚点，防止"越聊越偏"。
    """

    MAX_RECENT = 20          # 缓存最近N条用户消息
    CHECK_INTERVAL = 5       # 每N条消息检测一次
    DATA_DIR = "data/drift"

    def __init__(self, data_dir: str | None = None) -> None:
        self._data_dir = data_dir or self.DATA_DIR
        self._sessions: dict[str, SessionContext] = {}
        self._anchors: dict[str, object] = {}  # v2.0: ABA锚定Prompt缓存
        self._total_checks: int = 0
        self._red_alerts: int = 0
        self._is_initialized: bool = False

    # ----------------------------------------------------------
    # 初始化
    # ----------------------------------------------------------

    async def initialize(self) -> None:
        """恢复持久化的漂移数据。"""
        os.makedirs(self._data_dir, exist_ok=True)
        state_file = os.path.join(self._data_dir, "drift_state.json")
        try:
            if os.path.exists(state_file):
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                self._total_checks = state.get("total_checks", 0)
                self._red_alerts = state.get("red_alerts", 0)
                logger.info(
                    f"上下文漂移检测恢复: {len(state.get('sessions', {}))}会话, "
                    f"{self._total_checks}次检测, {self._red_alerts}次红色告警"
                )
        except Exception:
            logger.debug("漂移状态文件读取失败", exc_info=True)
        self._is_initialized = True

    async def _save_state(self) -> None:
        """持久化当前状态。"""
        state_file = os.path.join(self._data_dir, "drift_state.json")
        try:
            # 只保存会话元数据（不缓存消息内容）
            session_meta = {}
            for sid, ctx in self._sessions.items():
                session_meta[sid] = {
                    "task_type": ctx.anchor.task_type,
                    "user_query": ctx.anchor.user_query[:100],
                    "started_at": ctx.anchor.started_at,
                    "message_count": ctx.message_count,
                    "drift_checks": len(ctx.drift_history),
                    "severity": (
                        max(d.severity for d in ctx.drift_history[-3:])
                        if ctx.drift_history else "green"
                    ),
                }
            state = {
                "total_checks": self._total_checks,
                "red_alerts": self._red_alerts,
                "sessions": session_meta,
                "saved_at": datetime.now().isoformat(),
            }
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.debug("漂移状态持久化失败", exc_info=True)

    # ----------------------------------------------------------
    # 意图锚定
    # ----------------------------------------------------------

    async def record_intent(
        self,
        session_id: str,
        task_type: str = "",
        user_query: str = "",
        explicit_goals: list[str] | None = None,
        agent_role: str = "",
    ) -> IntentAnchor:
        """记录一个对话会话的初始意图锚点。

        每次新对话开始时调用。
        如果会话已存在，会更新锚点（覆盖原有）。

        Args:
            session_id: 会话ID
            task_type: 任务类型（自动检测如果为空）
            user_query: 用户的原始输入
            explicit_goals: 用户明示的目目标
            agent_role: v1.8新增 — Agent指定角色（如"代码助手"/"创作搭档"）
        """
        detected_type = task_type or _classify_task_type(user_query)
        key_terms = _extract_key_terms(user_query)

        anchor = IntentAnchor(
            session_id=session_id,
            task_type=detected_type,
            user_query=user_query[:500],  # 截断防爆
            key_terms=key_terms,
            explicit_goals=explicit_goals or [],
            scope_boundary=f"任务类型: {detected_type}, 初始关键词: {', '.join(list(key_terms)[:10])}",
        )

        ctx = SessionContext(anchor=anchor, max_recent=self.MAX_RECENT)
        ctx.agent_role = agent_role
        self._sessions[session_id] = ctx

        logger.info(
            "意图锚定: session=%s type=%s terms=%d",
            session_id[:12], detected_type, len(key_terms),
        )

        asyncio.ensure_future(self._save_state())
        return anchor

    # ----------------------------------------------------------
    # 消息跟踪
    # ----------------------------------------------------------

    async def record_message(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str = "",
        tools_used: list[str] | None = None,
        agent_role: str = "",
    ) -> DriftReport | None:
        """记录一条用户消息，达到检测间隔时自动触发漂移检查。

        v1.8: 新增 tools_used / agent_role 参数，支撑6维检测。

        Args:
            session_id: 会话ID
            user_message: 用户输入
            assistant_message: 助手回复
            tools_used: v1.8新增 — 本次调用的工具列表
            agent_role: v1.8新增 — 当前Agent角色

        Returns:
            DriftReport — 如果触发了检测，否则 None
        """
        ctx = self._sessions.get(session_id)
        if not ctx:
            return None

        ctx.message_count += 1
        ctx.anchor.message_count = ctx.message_count

        # 缓存最近用户消息
        ctx.recent_messages.append(user_message)
        if len(ctx.recent_messages) > ctx.max_recent:
            ctx.recent_messages = ctx.recent_messages[-ctx.max_recent:]

        # v1.8: 记录工具使用模式
        tools = tools_used or []
        ctx.tool_calls_history.append(tools)
        if len(ctx.tool_calls_history) > ctx.max_recent:
            ctx.tool_calls_history = ctx.tool_calls_history[-ctx.max_recent:]

        # 前5条消息建立基线工具集
        if ctx.message_count <= 5 and tools:
            ctx.baseline_tool_pattern.update(tools)

        # v1.8: 记录输出长度
        output_len = len(assistant_message) if assistant_message else 0
        ctx.output_lengths.append(output_len)
        if len(ctx.output_lengths) > ctx.max_recent:
            ctx.output_lengths = ctx.output_lengths[-ctx.max_recent:]

        # 前5条消息建立基线平均输出长度
        if ctx.message_count <= 5 and output_len > 0:
            recent_valid = [l for l in ctx.output_lengths if l > 0]
            if recent_valid:
                ctx.baseline_output_length = sum(recent_valid) / len(recent_valid)

        # v1.8: 更新角色
        if agent_role:
            ctx.agent_role = agent_role

        # 达到检测间隔（每N条消息）
        if ctx.message_count % self.CHECK_INTERVAL == 0:
            report = await self._detect_drift(session_id)
            ctx.drift_history.append(report)
            ctx.last_check_at = report.checked_at

            # v2.0: ABA行为锚定 — 漂移时自动生成锚定Prompt
            if report and report.severity in ("yellow", "red", "critical"):
                try:
                    from engine.aba_anchor import aba_anchor
                    # 采集基线数据（如果还在基线期内）
                    if ctx.message_count <= 10:
                        await aba_anchor.collect_baseline(
                            session_id=session_id,
                            intent=ctx.anchor.user_query,
                            task_type=ctx.anchor.task_type,
                            tools_used=list(set().union(*(h for h in ctx.tool_calls_history[-5:]))) if ctx.tool_calls_history else [],
                            output_length=sum(ctx.output_lengths[-5:]) / max(1, len([l for l in ctx.output_lengths[-5:] if l > 0])) if ctx.output_lengths else 0,
                            role=ctx.agent_role,
                        )
                    # 生成锚定Prompt（注入到回复中）
                    anchor = await aba_anchor.generate_anchor_prompt(
                        session_id=session_id,
                        drift_severity=report.severity,
                        drift_findings=report.findings,
                    )
                    if anchor:
                        self._anchors[session_id] = anchor
                        logger.info("ABA锚定已就绪: session=%s", session_id[:12])
                except Exception:
                    logger.debug("ABA集成不可用，跳过", exc_info=True)

            return report

        # v2.0: 非检测时，持续采集ABA基线数据（前BASELINE_MESSAGES条）
        else:
            try:
                from engine.aba_anchor import aba_anchor
                if ctx.message_count <= aba_anchor.BASELINE_MESSAGES + 2:
                    await aba_anchor.collect_baseline(
                        session_id=session_id,
                        intent=ctx.anchor.user_query,
                        task_type=ctx.anchor.task_type,
                        tools_used=list(set().union(*(h for h in ctx.tool_calls_history[-3:]))) if ctx.tool_calls_history else [],
                        output_length=ctx.output_lengths[-1] if ctx.output_lengths else 0,
                        role=ctx.agent_role,
                    )
            except Exception:
                pass

        return None

    # ----------------------------------------------------------
    # 显式触发漂移检测
    # ----------------------------------------------------------

    async def check_drift(
        self,
        session_id: str,
        recent_messages: list[str] | None = None,
    ) -> DriftReport | None:
        """显式触发漂移检测。

        Args:
            session_id: 会话ID
            recent_messages: 可选——覆盖缓存的最近消息
        """
        if session_id in self._sessions and recent_messages is not None:
            self._sessions[session_id].recent_messages = recent_messages[-self.MAX_RECENT:]

        report = await self._detect_drift(session_id)
        if report:
            ctx = self._sessions.get(session_id)
            if ctx:
                ctx.drift_history.append(report)
                ctx.last_check_at = report.checked_at
        return report

    # ----------------------------------------------------------
    # 核心检测算法
    # ----------------------------------------------------------

    async def _detect_drift(self, session_id: str) -> DriftReport | None:
        """执行一次漂移检测。 — v1.8: 6维扩展（参考ASI论文12维框架）"""
        ctx = self._sessions.get(session_id)
        if not ctx or not ctx.recent_messages:
            return None

        anchor = ctx.anchor
        recent_text = " ".join(ctx.recent_messages)
        recent_terms = _extract_key_terms(recent_text)

        # --------------------------------------------------
        # 维度一：词汇漂移（Term Drift）
        # 当前关键词与意图锚点关键词的重叠度
        # --------------------------------------------------
        overlap = _compute_overlap(anchor.key_terms, recent_terms)
        term_drift = max(0.0, 1.0 - overlap)

        # --------------------------------------------------
        # 维度二：任务漂移（Task Drift）
        # 当前话题是否已偏离原始任务类型
        # --------------------------------------------------
        current_task = _classify_task_type(recent_text)
        task_drift = 0.0
        if current_task != anchor.task_type:
            if anchor.task_type != "conversation":
                task_drift = 0.5 if current_task == "conversation" else 0.8
            else:
                task_drift = 0.0

        # --------------------------------------------------
        # 维度三：范围蔓延（Scope Drift）
        # 如果当前关键词数量远超单一话题的合理范围
        # --------------------------------------------------
        scope_drift = 0.0
        if anchor.key_terms and recent_terms:
            new_terms = recent_terms - anchor.key_terms
            if len(anchor.key_terms) > 0:
                expansion_ratio = len(new_terms) / len(anchor.key_terms)
                scope_drift = max(0.0, min(1.0, (expansion_ratio - 1.5) / 5.0))

        # --------------------------------------------------
        # 维度四（v1.8新增）：工具使用模式漂移（Tool Pattern Drift）
        # 参考 ASI: Tool Selection Stability + Tool Call Sequence Consistency
        # 检测工具集是否偏离基线模式
        # --------------------------------------------------
        tool_pattern_drift = 0.0
        if ctx.tool_calls_history and ctx.baseline_tool_pattern:
            # 取最近5条消息的工具使用
            recent_tools: set[str] = set()
            for tools in ctx.tool_calls_history[-5:]:
                recent_tools.update(tools)

            if ctx.baseline_tool_pattern:
                # 新出现的工具（不在基线中）
                new_tools = recent_tools - ctx.baseline_tool_pattern
                # 基线中消失的工具（近期不再使用）
                abandoned_tools = ctx.baseline_tool_pattern - recent_tools

                # 工具集变化比例
                total_baseline = len(ctx.baseline_tool_pattern)
                changes = len(new_tools) + len(abandoned_tools)
                tool_pattern_drift = min(1.0, changes / max(total_baseline, 1))

                # 新工具出现比消失更值得关注（可能跑偏到新领域）
                if new_tools:
                    tool_pattern_drift = min(1.0, tool_pattern_drift * 1.2)

        # --------------------------------------------------
        # 维度五（v1.8新增）：角色遵循度漂移（Role Adherence Drift）
        # 参考 ASI: Role Compliance
        # 检测Agent是否偏离指定角色（如代码助手开始写小说）
        # --------------------------------------------------
        role_adherence_drift = 0.0
        if ctx.agent_role and ctx.recent_messages:
            # 通过任务类型检测推断当前角色是否匹配
            expected_task = _classify_task_type(ctx.agent_role)
            actual_task = _classify_task_type(recent_text)

            if expected_task != "conversation" and actual_task != "conversation":
                if expected_task != actual_task:
                    # 角色与实际任务类型不匹配
                    role_adherence_drift = 0.6

            # 检测角色关键词是否在近期消息中消失
            role_terms = _extract_key_terms(ctx.agent_role)
            if role_terms:
                role_overlap = _compute_overlap(role_terms, recent_terms)
                if role_overlap < 0.2:
                    # 角色关键词几乎消失
                    role_adherence_drift = max(role_adherence_drift, 0.5)

        # --------------------------------------------------
        # 维度六（v1.8新增）：输出长度稳定性漂移（Output Length Drift）
        # 参考 ASI: Output Length Stability + Error Pattern Emergence
        # 检测输出长度是否异常波动
        # --------------------------------------------------
        output_length_drift = 0.0
        if ctx.output_lengths and ctx.baseline_output_length > 0:
            recent_lengths = [l for l in ctx.output_lengths[-5:] if l > 0]
            if len(recent_lengths) >= 3:
                avg_recent = sum(recent_lengths) / len(recent_lengths)
                baseline = ctx.baseline_output_length

                # 计算偏离比例
                if baseline > 0:
                    deviation = abs(avg_recent - baseline) / baseline
                    # 偏离50%以上算明显漂移
                    output_length_drift = min(1.0, max(0.0, (deviation - 0.3) / 0.7))

                # 计算变异系数（CV）— 波动过大也算漂移
                if len(recent_lengths) >= 3:
                    mean_val = sum(recent_lengths) / len(recent_lengths)
                    if mean_val > 0:
                        variance = sum((l - mean_val) ** 2 for l in recent_lengths) / len(recent_lengths)
                        cv = (variance ** 0.5) / mean_val
                        # CV > 0.5 表示高度不稳定
                        if cv > 0.5:
                            output_length_drift = min(1.0, output_length_drift + cv * 0.3)

        # --------------------------------------------------
        # 综合评分 — v1.8: 6维加权（参考ASI权重分配）
        # --------------------------------------------------
        drift_score = (
            term_drift * 0.20 +
            task_drift * 0.25 +
            scope_drift * 0.15 +
            tool_pattern_drift * 0.15 +
            role_adherence_drift * 0.15 +
            output_length_drift * 0.10
        )
        drift_score = min(1.0, max(0.0, drift_score))

        # --------------------------------------------------
        # 严重级别 & 建议
        # --------------------------------------------------
        severity = "green"
        action_parts = []

        if drift_score >= DriftThreshold.CRITICAL:
            severity = "critical"
            action_parts.append("上下文严重漂移，建议新建对话或将当前任务拆分为独立会话")
        elif drift_score >= DriftThreshold.RED:
            severity = "red"
            action_parts.append("上下文明显偏离原始目标，建议回顾意图或分割任务")
        elif drift_score >= DriftThreshold.YELLOW:
            severity = "yellow"
            action_parts.append("上下文轻微扩展，关注是否还在原始轨道上")
        else:
            action_parts.append("上下文稳定，保持当前方向")

        # 具体发现
        findings = []
        if term_drift > 0.5:
            findings.append(f"关键词重叠度仅 {1.0 - term_drift:.0%}，话题词汇大量替换")
        if task_drift > 0.5:
            findings.append(f"任务类型从 {anchor.task_type} 变为 {current_task}")
        if scope_drift > 0.3:
            findings.append(f"话题范围扩展了 {len(recent_terms - anchor.key_terms)} 个新关键词")
        # v1.8 新增发现
        if tool_pattern_drift > 0.3:
            new_tools = set()
            for tools in ctx.tool_calls_history[-5:]:
                new_tools.update(tools)
            new_tools = new_tools - ctx.baseline_tool_pattern
            if new_tools:
                findings.append(f"工具使用模式漂移：新增工具 {', '.join(list(new_tools)[:5])}")
            else:
                findings.append("工具使用模式漂移：基线工具使用频率下降")
        if role_adherence_drift > 0.3:
            findings.append(f"角色遵循度下降：Agent可能偏离了'{ctx.agent_role}'角色")
        if output_length_drift > 0.3:
            recent_lengths = [l for l in ctx.output_lengths[-5:] if l > 0]
            if recent_lengths:
                avg_recent = sum(recent_lengths) / len(recent_lengths)
                findings.append(
                    f"输出长度异常波动：基线{ctx.baseline_output_length:.0f}字 → "
                    f"近期均值{avg_recent:.0f}字"
                )
        if not findings:
            if drift_score > 0.1:
                findings.append("上下文与原始意图基本一致")
            else:
                findings.append("上下文与原始意图完全一致")

        # 构造完整建议
        suggested_action = " · ".join(action_parts)

        self._total_checks += 1
        if severity in ("red", "critical"):
            self._red_alerts += 1

        report = DriftReport(
            session_id=session_id,
            drift_score=round(drift_score, 3),
            term_drift=round(term_drift, 3),
            task_drift=round(task_drift, 3),
            scope_drift=round(scope_drift, 3),
            tool_pattern_drift=round(tool_pattern_drift, 3),
            role_adherence_drift=round(role_adherence_drift, 3),
            output_length_drift=round(output_length_drift, 3),
            findings=findings,
            severity=severity,
            suggested_action=suggested_action,
        )

        if severity != "green":
            log_level = logger.warning if severity in ("yellow",) else logger.error
            log_level(
                "漂移检测: session=%s score=%.2f severity=%s %s",
                session_id[:12], drift_score, severity,
                "; ".join(findings),
            )

        return report

    # ----------------------------------------------------------
    # 意图重确认
    # ----------------------------------------------------------

    async def reaffirm_intent(self, session_id: str) -> bool:
        """用户确认'还在做这个'——重置漂移检测状态。

        被确认后，当前上下文成为新的意图锚点。
        """
        ctx = self._sessions.get(session_id)
        if not ctx:
            return False

        # 以最近消息重建锚点
        recent_text = " ".join(ctx.recent_messages[-3:]) if ctx.recent_messages else ctx.anchor.user_query
        new_task = _classify_task_type(recent_text)
        new_terms = _extract_key_terms(recent_text)

        ctx.anchor.task_type = new_task
        ctx.anchor.key_terms = new_terms
        ctx.anchor.last_reaffirmed_at = time.time()
        ctx.anchor.scope_boundary = f"用户确认 - 任务类型: {new_task}"

        # 清除漂移历史
        ctx.drift_history.clear()

        logger.info("意图已确认重置: session=%s type=%s", session_id[:12], new_task)
        asyncio.ensure_future(self._save_state())
        return True

    # ----------------------------------------------------------
    # 会话管理
    # ----------------------------------------------------------

    def remove_session(self, session_id: str) -> bool:
        """删除会话记录（对话结束时调用）。"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            asyncio.ensure_future(self._save_state())
            return True
        return False

    # ----------------------------------------------------------
    # 查询接口
    # ----------------------------------------------------------

    def get_status(self) -> dict:
        """获取检测器状态。"""
        active_sessions = sum(
            1 for ctx in self._sessions.values()
            if ctx.drift_history and ctx.drift_history[-1].severity != "green"
        )
        return {
            "initialized": self._is_initialized,
            "active_sessions": len(self._sessions),
            "warn_sessions": active_sessions,
            "total_checks": self._total_checks,
            "red_alerts": self._red_alerts,
            "check_interval": self.CHECK_INTERVAL,
            "severity_distribution": self._severity_distribution(),
        }

    def _severity_distribution(self) -> dict[str, int]:
        dist: dict[str, int] = {"green": 0, "yellow": 0, "red": 0, "critical": 0}
        for ctx in self._sessions.values():
            if ctx.drift_history:
                sev = ctx.drift_history[-1].severity
                dist[sev] = dist.get(sev, 0) + 1
        return dist

    def get_latest_report(self, session_id: str) -> DriftReport | None:
        """获取某会话的最新漂移报告。"""
        ctx = self._sessions.get(session_id)
        if ctx and ctx.drift_history:
            return ctx.drift_history[-1]
        return None

    def get_session_drift_history(self, session_id: str) -> list[dict]:
        """获取某会话的完整漂移历史。 — v1.8: 包含6维数据"""
        ctx = self._sessions.get(session_id)
        if not ctx:
            return []
        return [
            {
                "drift_score": r.drift_score,
                "severity": r.severity,
                "dimensions": {
                    "term_drift": r.term_drift,
                    "task_drift": r.task_drift,
                    "scope_drift": r.scope_drift,
                    "tool_pattern_drift": r.tool_pattern_drift,
                    "role_adherence_drift": r.role_adherence_drift,
                    "output_length_drift": r.output_length_drift,
                },
                "findings": r.findings,
                "suggested_action": r.suggested_action,
                "checked_at": r.checked_at,
            }
            for r in ctx.drift_history
        ]

    def get_drift_summary(self) -> list[dict]:
        """获取所有活跃会话的漂移摘要。"""
        return [
            {
                "session_id": sid[:12],
                "task_type": ctx.anchor.task_type,
                "message_count": ctx.message_count,
                "drift_checks": len(ctx.drift_history),
                "latest_severity": (
                    ctx.drift_history[-1].severity
                    if ctx.drift_history else "unknown"
                ),
                "latest_drift_score": (
                    ctx.drift_history[-1].drift_score
                    if ctx.drift_history else 0.0
                ),
                "started_at": ctx.anchor.started_at,
            }
            for sid, ctx in self._sessions.items()
        ]


# ============================================================
# 全局实例
# ============================================================

context_drift = ContextDriftDetector()
