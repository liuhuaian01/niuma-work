"""
L1 会话工作记忆管理器

三层记忆架构的 L1 层：进程内内存存储，保存当前会话完整上下文。
Token 阈值机制：60% 预警 / 80% 裁剪 / 90% 压缩

依赖：compression_engine.py
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional

from model_adapter.token_counter import estimate_tokens as _estimate_tokens

logger = logging.getLogger(__name__)


# ============================================================
# 数据结构
# ============================================================

class CompressionLevel(IntEnum):
    """压缩级别"""
    NORMAL = 0       # 正常
    WARNING = 1      # 预警 (60%)
    BUDGET = 2       # 裁剪 (80%)
    SUMMARIZE = 3    # 压缩 (90%)


class MessageRole:
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ToolCall:
    """工具调用信息"""
    call_id: str
    tool_name: str
    arguments: Dict[str, Any]
    result_preview: Optional[str] = None


@dataclass
class ChatMessage:
    """对话消息"""
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    role: str = MessageRole.USER
    content: str = ""
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    token_count: int = 0
    importance_score: float = 0.5

    # 特殊标记
    # -1.0 = Snip 已裁剪
    # -2.0 = Summarize 已摘要
    # 0.0-1.0 = 正常重要性评分


@dataclass
class ToolResult:
    """工具调用结果"""
    tool_name: str = ""
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    content: str = ""
    full_content_hash: str = ""
    token_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    importance: float = 0.3
    compressed: bool = False

    def compute_hash(self) -> str:
        self.full_content_hash = hashlib.md5(self.content.encode()).hexdigest()
        return self.full_content_hash


@dataclass
class Decision:
    """关键决策记录"""
    decision_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    context: str = ""
    decision: str = ""
    rationale: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    importance: float = 0.8


@dataclass
class TokenSnapshot:
    """Token 使用快照"""
    timestamp: datetime = field(default_factory=datetime.now)
    total_tokens: int = 0
    max_tokens: int = 8192
    message_count: int = 0
    compression_level: int = 0


@dataclass
class TokenStatus:
    """Token 状态信息"""
    total_tokens: int = 0
    max_tokens: int = 8192
    usage_ratio: float = 0.0
    compression_level: int = 0
    recent_snapshots: List[TokenSnapshot] = field(default_factory=list)
    estimated_remaining_turns: int = 0

    @property
    def percentage(self) -> float:
        return round(self.usage_ratio * 100, 1)


@dataclass
class SessionSummary:
    """会话摘要 (L1→L2 归档用)"""
    session_id: str = ""
    workspace_id: str = ""
    duration_seconds: int = 0
    message_count: int = 0
    total_tokens: int = 0
    decisions: List[Decision] = field(default_factory=list)
    tool_results_summary: Dict[str, int] = field(default_factory=dict)
    requests: List[Dict] = field(default_factory=list)
    key_observations: List[Dict] = field(default_factory=list)


# ============================================================
# Token 计数器
# ============================================================

# Token 计数（统一使用 model_adapter/token_counter.py）
estimate_tokens = _estimate_tokens


# ============================================================
# L1 会话工作记忆
# ============================================================

@dataclass
class L1SessionMemory:
    """
    会话级工作记忆，进程内存存储

    生命周期：从 create_session 到 close_session
    会话结束后 L1 数据丢失，但会被压缩存档至 L2
    """
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    workspace_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    # 核心队列
    messages: List[ChatMessage] = field(default_factory=list)
    tool_results: Dict[str, List[ToolResult]] = field(default_factory=dict)
    decision_chain: List[Decision] = field(default_factory=list)

    # Token 管理
    total_tokens: int = 0
    max_tokens: int = 8192
    token_history: List[TokenSnapshot] = field(default_factory=list)

    # 压缩状态
    compression_level: int = 0
    last_compressed_at: Optional[datetime] = None

    # 被截断内容的恢复映射 (result_id -> full_content)
    _truncated_store: Dict[str, str] = field(default_factory=dict)

    # 内部标记
    _closed: bool = False


class L1MemoryManager:
    """
    L1 会话工作记忆管理器

    核心职责：
    1. 创建/销毁会话
    2. 消息追加 + Token 自动计数
    3. Token 阈值检查 (60%/80%/90%)
    4. 会话关闭时生成摘要 (L1→L2)
    """

    # Token 阈值常量
    WARN_THRESHOLD = 0.60
    BUDGET_THRESHOLD = 0.80
    SUMMARIZE_THRESHOLD = 0.90

    def __init__(
        self,
        max_tokens: int = 8192,
        on_threshold: Optional[Callable[[str, int], None]] = None,
    ):
        """
        Args:
            max_tokens: 单会话 Token 上限 (默认 8K，可配置 2K-16K)
            on_threshold: Token 阈值回调 (session_id, level)
        """
        self._sessions: Dict[str, L1SessionMemory] = {}
        self._max_tokens = max(2048, min(16384, max_tokens))
        self._on_threshold = on_threshold
        self._sessions_lock = asyncio.Lock()  # 保护 _sessions 字典

    # ----------------------------------------------------------
    # 会话生命周期
    # ----------------------------------------------------------

    async def create_session(self, workspace_id: str, max_tokens: Optional[int] = None) -> str:
        """
        创建新会话，返回 session_id

        Args:
            workspace_id: 所属工作间 ID
            max_tokens: 会话 Token 上限 (默认使用全局配置)
        """
        session = L1SessionMemory(
            workspace_id=workspace_id,
            max_tokens=max_tokens or self._max_tokens,
        )
        async with self._sessions_lock:
            self._sessions[session.session_id] = session

        logger.info(
            "L1 会话创建: session=%s workspace=%s max_tokens=%d",
            session.session_id, workspace_id, session.max_tokens,
        )
        return session.session_id

    def close_session(self, session_id: str) -> Optional[SessionSummary]:
        """
        关闭会话，触发 L1→L2 存档，返回摘要

        流程：
        1. 生成结构化摘要 (request/learned/completed)
        2. 标记会话为已关闭
        3. 返回摘要供 L2 写入
        """
        session = self._get_session(session_id)
        if session is None or session._closed:
            return None

        session._closed = True
        duration = (datetime.now() - session.created_at).total_seconds()

        # 生成摘要
        summary = SessionSummary(
            session_id=session_id,
            workspace_id=session.workspace_id,
            duration_seconds=int(duration),
            message_count=len(session.messages),
            total_tokens=session.total_tokens,
            decisions=session.decision_chain.copy(),
            tool_results_summary={
                name: len(results)
                for name, results in session.tool_results.items()
            },
            requests=self._extract_requests(session),
            key_observations=self._extract_observations(session),
        )

        logger.info(
            "L1 会话关闭: session=%s duration=%ds tokens=%d",
            session_id, int(duration), session.total_tokens,
        )

        # 清理内存
        session.messages.clear()
        session.tool_results.clear()
        session.decision_chain.clear()
        session._truncated_store.clear()

        return summary

    # ----------------------------------------------------------
    # 消息管理
    # ----------------------------------------------------------

    def add_message(self, session_id: str, message: ChatMessage) -> None:
        """
        添加消息，自动更新 Token 计数，检查阈值
        """
        session = self._get_session(session_id)
        if session is None or session._closed:
            return

        # 自动估算 token (如果未提供)
        if message.token_count == 0 and message.content:
            message.token_count = estimate_tokens(message.content)

        session.messages.append(message)
        session.total_tokens += message.token_count

        self._check_threshold(session)

    def add_tool_result(self, session_id: str, tool_result: ToolResult) -> None:
        """
        添加工具调用结果，检查是否需要 Budget 截断
        """
        session = self._get_session(session_id)
        if session is None or session._closed:
            return

        # 自动估算 token
        if tool_result.token_count == 0 and tool_result.content:
            tool_result.token_count = estimate_tokens(tool_result.content)

        # 计算 hash
        if not tool_result.full_content_hash:
            tool_result.compute_hash()

        # 存入对应 tool_name 分组
        if tool_result.tool_name not in session.tool_results:
            session.tool_results[tool_result.tool_name] = []
        session.tool_results[tool_result.tool_name].append(tool_result)

        session.total_tokens += tool_result.token_count

        self._check_threshold(session)

    def add_decision(self, session_id: str, decision: Decision) -> None:
        """
        记录关键决策 (优先级 1，压缩时不裁剪)
        """
        session = self._get_session(session_id)
        if session is None or session._closed:
            return

        session.decision_chain.append(decision)

    # ----------------------------------------------------------
    # 上下文获取
    # ----------------------------------------------------------

    def get_context(
        self,
        session_id: str,
        max_tokens: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取当前上下文，返回可注入模型的消息列表

        按保留优先级排序：
        1. 用户显式指令 (必保留)
        2. 关键决策记录 (必保留)
        3. 最近 3 轮完整对话
        4. Tool 关键结果
        5. 其余消息 (按重要性降序)
        """
        session = self._get_session(session_id)
        if session is None:
            return []

        budget = max_tokens or session.max_tokens
        result: List[Dict[str, Any]] = []
        used_tokens = 0

        # 1. 决策记录 (必保留)
        for d in session.decision_chain:
            entry = {
                "role": "system",
                "content": f"[决策] {d.decision} | 理由: {d.rationale}",
            }
            tok = estimate_tokens(entry["content"])
            result.append(entry)
            used_tokens += tok

        # 2. 消息 (从最新到最旧，优先保留新消息)
        recent_count = 6  # 最近 3 轮 ≈ 6 条消息
        messages = list(reversed(session.messages))

        # 分区：最近消息 vs 历史消息
        recent_msgs = messages[:recent_count]
        old_msgs = messages[recent_count:]

        # 先放最近消息 (必保留)
        for msg in recent_msgs:
            if msg.importance_score == -1.0:  # 已裁剪
                continue
            entry = self._message_to_dict(msg)
            tok = msg.token_count
            result.append(entry)
            used_tokens += tok

        # 再放历史消息 (按重要性降序，在预算内)
        old_msgs_sorted = sorted(old_msgs, key=lambda m: m.importance_score, reverse=True)
        for msg in old_msgs_sorted:
            if msg.importance_score == -1.0:  # 已裁剪
                continue
            if used_tokens + msg.token_count > budget:
                continue
            entry = self._message_to_dict(msg)
            result.append(entry)
            used_tokens += msg.token_count

        return result

    def get_token_status(self, session_id: str) -> Optional[TokenStatus]:
        """获取 Token 状态：总量/已用/百分比/压缩级别"""
        session = self._get_session(session_id)
        if session is None:
            return None

        ratio = session.total_tokens / session.max_tokens if session.max_tokens > 0 else 0.0

        # 估算剩余轮数 (每轮约 500 tokens)
        remaining = max(0, session.max_tokens - session.total_tokens)
        estimated_turns = int(remaining / 500)

        return TokenStatus(
            total_tokens=session.total_tokens,
            max_tokens=session.max_tokens,
            usage_ratio=ratio,
            compression_level=session.compression_level,
            recent_snapshots=session.token_history[-5:],
            estimated_remaining_turns=estimated_turns,
        )

    # ----------------------------------------------------------
    # 截断内容恢复
    # ----------------------------------------------------------

    def store_truncated_content(self, session_id: str, result_id: str, full_content: str) -> None:
        """存储被截断的完整内容 (仅 L1 内存)"""
        session = self._get_session(session_id)
        if session is not None:
            session._truncated_store[result_id] = full_content

    def restore_truncated(self, session_id: str, result_id: str) -> Optional[str]:
        """从内存恢复被截断的完整内容"""
        session = self._get_session(session_id)
        if session is None:
            return None
        return session._truncated_store.get(result_id)

    # ----------------------------------------------------------
    # Token 快照
    # ----------------------------------------------------------

    def take_snapshot(self, session_id: str) -> None:
        """记录当前 Token 使用快照"""
        session = self._get_session(session_id)
        if session is None:
            return

        snapshot = TokenSnapshot(
            total_tokens=session.total_tokens,
            max_tokens=session.max_tokens,
            message_count=len(session.messages),
            compression_level=session.compression_level,
        )
        session.token_history.append(snapshot)

        # 限制快照数量
        if len(session.token_history) > 100:
            session.token_history = session.token_history[-50:]

    # ----------------------------------------------------------
    # 内部方法
    # ----------------------------------------------------------

    def _get_session(self, session_id: str) -> Optional[L1SessionMemory]:
        """获取会话（线程安全）"""
        # 读操作不需要锁，因为只是读取引用
        session = self._sessions.get(session_id)
        if session is None:
            logger.warning("L1 会话不存在: %s", session_id)
        return session

    def _check_threshold(self, session: L1SessionMemory) -> None:
        """检查 Token 阈值，触发回调"""
        ratio = session.total_tokens / session.max_tokens if session.max_tokens > 0 else 0.0

        old_level = session.compression_level

        if ratio >= self.SUMMARIZE_THRESHOLD:
            new_level = CompressionLevel.SUMMARIZE
        elif ratio >= self.BUDGET_THRESHOLD:
            new_level = CompressionLevel.BUDGET
        elif ratio >= self.WARN_THRESHOLD:
            new_level = CompressionLevel.WARNING
        else:
            new_level = CompressionLevel.NORMAL

        if new_level > old_level:
            session.compression_level = new_level
            logger.info(
                "Token 阈值触发: session=%s level=%d ratio=%.1f%%",
                session.session_id, new_level, ratio * 100,
            )
            if self._on_threshold:
                self._on_threshold(session.session_id, new_level)

    def _message_to_dict(self, msg: ChatMessage) -> Dict[str, Any]:
        """将 ChatMessage 转为模型可用的 dict"""
        d: Dict[str, Any] = {"role": msg.role, "content": msg.content}
        if msg.tool_calls:
            d["tool_calls"] = [
                {
                    "id": tc.call_id,
                    "type": "function",
                    "function": {
                        "name": tc.tool_name,
                        "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                    },
                }
                for tc in msg.tool_calls
            ]
        if msg.tool_call_id:
            d["tool_call_id"] = msg.tool_call_id
        return d

    def _extract_requests(self, session: L1SessionMemory) -> List[Dict]:
        """从消息中提取用户请求"""
        requests = []
        for msg in session.messages:
            if msg.role == MessageRole.USER and msg.content:
                requests.append({
                    "request": msg.content[:200],
                    "timestamp": msg.timestamp.isoformat(),
                    "importance": msg.importance_score,
                })
        return requests

    def _extract_observations(self, session: L1SessionMemory) -> List[Dict]:
        """从消息和决策中提取关键观察"""
        obs = []
        for d in session.decision_chain:
            obs.append({
                "type": "decision",
                "content": f"{d.decision} (理由: {d.rationale})",
                "importance": d.importance,
            })
        for tool_name, results in session.tool_results.items():
            for r in results:
                if r.importance >= 0.5:
                    obs.append({
                        "type": "tool_result",
                        "tool": tool_name,
                        "content": r.content[:200],
                        "importance": r.importance,
                    })
        return obs

    # ----------------------------------------------------------
    # 调试/管理 API
    # ----------------------------------------------------------

    async def list_sessions(self, workspace_id: Optional[str] = None) -> List[str]:
        """列出活跃会话 ID"""
        async with self._sessions_lock:
            sessions = list(self._sessions.values())
        if workspace_id:
            sessions = [s for s in sessions if s.workspace_id == workspace_id]
        return [s.session_id for s in sessions if not s._closed]

    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """获取会话信息 (调试用)"""
        session = self._get_session(session_id)
        if session is None:
            return None
        return {
            "session_id": session.session_id,
            "workspace_id": session.workspace_id,
            "created_at": session.created_at.isoformat(),
            "message_count": len(session.messages),
            "decision_count": len(session.decision_chain),
            "tool_result_count": sum(len(r) for r in session.tool_results.values()),
            "total_tokens": session.total_tokens,
            "max_tokens": session.max_tokens,
            "usage_ratio": round(session.total_tokens / session.max_tokens, 3) if session.max_tokens > 0 else 0,
            "compression_level": session.compression_level,
            "closed": session._closed,
        }
