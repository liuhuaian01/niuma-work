"""
记忆引擎服务层

集成 L1 会话工作记忆 + L2 短期档案 + 上下文压缩引擎
对外提供统一 API，对内协调各子模块

按照 security_memory_api.md §3.2 定义内部接口
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from db.database import get_engine
from utils import utc_now, calculate_offset
from config.settings import settings
from services.memory.l1_session_memory import (
    L1MemoryManager, L1SessionMemory,
    ChatMessage, TokenStatus, SessionSummary,
    estimate_tokens,
)
from services.memory.compression_engine import (
    CompressionEngine, CompressionConfig, CompressionReport,
    create_default_engine,
)

logger = logging.getLogger(__name__)


def _utc_now_dt() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================
# L2 短期档案 SQL
# ============================================================

_L2_LIST_SQL = """
    SELECT id, workspace_id, source_session_id, entry_type,
           content, summary, tags, observation_type,
           retrieval_count, expires_at, created_at
    FROM l2_memory_entries
    WHERE workspace_id = :ws_id
      AND expires_at > :now
      {filters}
    ORDER BY created_at DESC
    LIMIT :limit OFFSET :offset
"""

_L2_COUNT_SQL = """
    SELECT COUNT(*) FROM l2_memory_entries
    WHERE workspace_id = :ws_id
      AND expires_at > :now
      {filters}
"""

_L2_SEARCH_SQL = """
    SELECT id, workspace_id, source_session_id, entry_type,
           content, summary, tags, observation_type,
           retrieval_count, expires_at, created_at
    FROM l2_memory_entries
    WHERE workspace_id = :ws_id
      AND expires_at > :now
      AND (content LIKE :kw OR summary LIKE :kw OR tags LIKE :kw)
    ORDER BY created_at DESC
    LIMIT :limit
"""

_L2_INSERT_SQL = """
    INSERT INTO l2_memory_entries
        (id, workspace_id, source_session_id, entry_type,
         content, summary, tags, observation_type,
         retrieval_count, expires_at, created_at)
    VALUES
        (:id, :ws_id, :sid, :entry_type,
         :content, :summary, :tags, :obs_type,
         0, :expires_at, :created_at)
"""

_L2_DELETE_SQL = """
    DELETE FROM l2_memory_entries
    WHERE id = :entry_id AND workspace_id = :ws_id
"""

_L2_INCREMENT_RETRIEVAL_SQL = """
    UPDATE l2_memory_entries
    SET retrieval_count = retrieval_count + 1
    WHERE id = :entry_id
"""


# ============================================================
# MemoryEngine
# ============================================================

class MemoryEngine:
    """
    记忆引擎统一门面

    内部接口（按 security_memory_api.md §3.2）：
    - get_context(ws_id) → 构建上下文消息列表
    - append_message(ws_id, role, content) → L1 添加消息
    - inject_l2(ws_id, query) → L2 记忆注入
    - archive_session(ws_id) → 会话归档到 L2
    - compress_context(ws_id) → 上下文压缩
    - l2_list/l2_add/l2_delete → L2 CRUD
    """

    def __init__(
        self,
        max_tokens: int = 8192,
        compression_config: Optional[CompressionConfig] = None,
    ):
        self.l1 = L1MemoryManager(max_tokens=max_tokens)
        self.compression = create_default_engine(config=None)
        self._ws_sessions: Dict[str, str] = {}  # workspace_id → session_id
        self._last_compress: Dict[str, datetime] = {}  # workspace_id → last compress time
        self._sessions_lock = asyncio.Lock()  # 保护 _ws_sessions 和 _last_compress

    # ----------------------------------------------------------
    # 会话管理
    # ----------------------------------------------------------

    async def get_or_create_session(self, workspace_id: str,
                               max_tokens: Optional[int] = None) -> str:
        """获取或创建工作间的 L1 会话"""
        async with self._sessions_lock:
            if workspace_id not in self._ws_sessions:
                sid = await self.l1.create_session(workspace_id, max_tokens)
                self._ws_sessions[workspace_id] = sid
                logger.info("创建 L1 会话: ws=%s sid=%s", workspace_id, sid)
            return self._ws_sessions[workspace_id]

    # ----------------------------------------------------------
    # 消息操作
    # ----------------------------------------------------------

    async def append_message(self, workspace_id: str, role: str,
                        content: str, importance: float = 0.5) -> int:
        """
        向 L1 添加消息，返回当前 Token 使用量
        """
        session_id = await self.get_or_create_session(workspace_id)
        msg = ChatMessage(
            role=role,
            content=content,
            token_count=estimate_tokens(content),
            importance_score=importance,
        )
        self.l1.add_message(session_id, msg)
        return self.l1._sessions[session_id].total_tokens

    # ----------------------------------------------------------
    # 上下文构建 (核心：供 chat.py _build_context 使用)
    # ----------------------------------------------------------

    async def get_context(self, workspace_id: str,
                     mode: str = "auto",
                     max_tokens: Optional[int] = None) -> list[dict]:
        """
        构建对话上下文消息列表

        Phase 2 模式：
        1. 如果 L1 有活跃会话，使用 L1 的智能上下文 (含 Token 预算)
        2. 否则从 DB 回退获取最近消息
        3. 返回可直接注入模型的消息列表

        """
        import asyncio

        # 尝试使用 L1 会话
        session_id = await self.get_or_create_session(workspace_id)

        if session_id in self.l1._sessions:
            session = self.l1._sessions[session_id]

            # 先检查 Token 是否超阈值，触发压缩
            ratio = session.total_tokens / session.max_tokens if session.max_tokens > 0 else 0.0

            # 异步触发压缩（不阻塞上下文构建）
            if ratio >= 0.80:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self._async_compress(workspace_id))
                except RuntimeError:
                    pass

            # 从 L1 获取智能上下文
            messages = self.l1.get_context(session_id, max_tokens)

            # 将 L1 上下文消息转为标准 dict
            result = []
            for msg in messages:
                if isinstance(msg, dict):
                    result.append(msg)
                elif hasattr(msg, 'role') and hasattr(msg, 'content'):
                    result.append({"role": msg.role, "content": msg.content})

            if result:
                return result

        # 回退：从 DB 获取历史消息
        return self._get_context_from_db(workspace_id)

    async def _get_context_from_db(self, workspace_id: str) -> list[dict]:
        """从 DB 获取最近消息作为上下文回退"""
        engine = get_engine()
        messages = []

        async with engine.connect() as conn:
            if workspace_id:
                result = await conn.execute(
                    text(
                        "SELECT role, content FROM chat_messages "
                        "WHERE workspace_id = :ws_id AND status IN ('completed', 'stopped') "
                        "ORDER BY created_at DESC LIMIT 20"
                    ),
                    {"ws_id": workspace_id},
                )
            else:
                result = await conn.execute(
                    text(
                        "SELECT role, content FROM chat_messages "
                        "WHERE status IN ('completed', 'stopped') "
                        "ORDER BY created_at DESC LIMIT 20"
                    ),
                )

            rows = list(result.fetchall())
            rows.reverse()
            for row in rows:
                messages.append({"role": row.role, "content": row.content})

        return messages

    async def _async_compress(self, workspace_id: str) -> None:
        """异步执行压缩（不阻塞上下文构建）"""
        try:
            report = await self.compress_context(workspace_id)
            logger.info(
                "压缩完成: ws=%s level=%d saved=%d",
                workspace_id, report.level, report.total_saved,
            )
        except Exception as e:
            logger.error("压缩失败: ws=%s error=%s", workspace_id, e)

    # ----------------------------------------------------------
    # L2 短期档案 CRUD
    # ----------------------------------------------------------

    async def l2_list(
        self,
        workspace_id: str,
        entry_type: Optional[str] = None,
        keyword: Optional[str] = None,
        observation_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list, int]:
        """
        列出工作间的 L2 记忆条目

        Args:
            workspace_id: 工作间 ID
            entry_type: 过滤类型
            keyword: 关键词搜索
            observation_type: Observation 类型过滤
            page: 页码
            page_size: 每页数量
        """
        engine = get_engine()
        now = utc_now()

        offset = calculate_offset(page, page_size)

        # 构建条件
        filters = ""
        params: dict = {
            "ws_id": workspace_id,
            "now": now,
            "limit": page_size,
            "offset": offset,
        }

        if entry_type:
            filters += " AND entry_type = :entry_type"
            params["entry_type"] = entry_type

        if observation_type:
            filters += " AND observation_type = :obs_type"
            params["obs_type"] = observation_type

        if keyword:
            # 安全处理：使用参数化查询 + LIKE转义，防止SQL注入
            # _escape_like() 转义 %、_、\ 等特殊字符
            # ESCAPE '\' 指定反斜杠为转义字符
            kw_pattern = f"%{_escape_like(keyword)}%"
            filters += " AND (content LIKE :kw ESCAPE '\\' OR summary LIKE :kw ESCAPE '\\' OR tags LIKE :kw ESCAPE '\\')"
            params["kw"] = kw_pattern

        async with engine.connect() as conn:
            # 总数查询
            # 安全审计说明：
            # 1. .format(filters) 仅用于注入内部受控的filters字符串
            # 2. filters由预定义字段名组成（entry_type/observation_type），不含用户输入
            # 3. 所有用户输入（keyword/ws_id/entry_type/observation_type）均通过:param参数化传递
            # 4. keyword经_escape_like()转义LIKE通配符，无SQL注入风险
            count_sql = _L2_COUNT_SQL.format(filters=filters)
            count_params = {k: v for k, v in params.items()
                           if k not in ("limit", "offset")}

            count_result = await conn.execute(text(count_sql), count_params)
            total = count_result.scalar() or 0

            # 列表查询（安全审计同上）
            list_sql = _L2_LIST_SQL.format(filters=filters)
            result = await conn.execute(text(list_sql), params)
            entries = []

            for row in result:
                entry = dict(row._mapping)
                entry["tags"] = json.loads(entry["tags"]) if entry.get("tags") and isinstance(entry["tags"], str) else entry.get("tags", [])
                entries.append(entry)

        return entries, total

    async def l2_add(
        self,
        workspace_id: str,
        entry_type: str,
        content: str,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        observation_type: Optional[str] = None,
        source_session_id: Optional[str] = None,
        expires_days: int = 30,
    ) -> dict:
        """
        手动添加 L2 记忆条目

        Args:
            workspace_id: 工作间 ID
            entry_type: 条目类型 (request|learned|completed|decision|error|custom)
            content: 内容
            summary: 摘要
            tags: 标签列表
            observation_type: Observation 类型 (18 种)
            source_session_id: 来源会话 ID
            expires_days: 过期天数
        """
        engine = get_engine()
        entry_id = f"l2-{uuid.uuid4().hex[:12]}"
        now = _utc_now()
        expires_at = (_utc_now_dt() + timedelta(days=expires_days)).isoformat().replace("+00:00", "Z")

        tags_json = json.dumps(tags, ensure_ascii=False) if tags else None

        async with engine.begin() as conn:
            await conn.execute(
                text(_L2_INSERT_SQL),
                {
                    "id": entry_id,
                    "ws_id": workspace_id,
                    "sid": source_session_id,
                    "entry_type": entry_type,
                    "content": content,
                    "summary": summary or content[:200],
                    "tags": tags_json,
                    "obs_type": observation_type,
                    "expires_at": expires_at,
                    "created_at": now,
                },
            )

        logger.info("L2 条目创建: id=%s ws=%s type=%s", entry_id, workspace_id, entry_type)
        return {
            "id": entry_id,
            "workspace_id": workspace_id,
            "entry_type": entry_type,
            "content": content,
            "summary": summary or content[:200],
            "tags": tags or [],
            "observation_type": observation_type,
            "retrieval_count": 0,
            "expires_at": expires_at,
            "created_at": now,
        }

    async def l2_delete(self, workspace_id: str, entry_id: str) -> bool:
        """
        删除指定 L2 记忆条目
        """
        engine = get_engine()
        async with engine.begin() as conn:
            result = await conn.execute(
                text(_L2_DELETE_SQL),
                {"entry_id": entry_id, "ws_id": workspace_id},
            )
            deleted = result.rowcount > 0

        if deleted:
            logger.info("L2 条目删除: id=%s ws=%s", entry_id, workspace_id)
        return deleted

    async def l2_increment_retrieval(self, entry_id: str) -> int:
        """增加 L2 条目的检索计数"""
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(
                text(_L2_INCREMENT_RETRIEVAL_SQL),
                {"entry_id": entry_id},
            )

            result = await conn.execute(
                text("SELECT retrieval_count FROM l2_memory_entries WHERE id = :eid"),
                {"eid": entry_id},
            )
            row = result.fetchone()
            return row.retrieval_count if row else 0

    # ----------------------------------------------------------
    # 压缩引擎集成
    # ----------------------------------------------------------

    async def compress_context(
        self,
        workspace_id: str,
        strategy: str = "auto",
        force: bool = False,
    ) -> CompressionReport:
        """
        对工作间执行上下文压缩

        Args:
            workspace_id: 工作间 ID
            strategy: 'auto' | 'budget' | 'snip' | 'summarize'
            force: 是否强制执行

        Returns:
            CompressionReport 压缩报告
        """
        session_id = await self.get_or_create_session(workspace_id)
        session = self.l1._get_session(session_id)

        if session is None:
            logger.warning("压缩失败：会话不存在 ws=%s", workspace_id)
            from services.memory.compression_engine import CompressionReport
            return CompressionReport(warnings=["会话不存在"])

        # 频率控制 (默认 30s 内不重复压缩)
        if not force:
            async with self._sessions_lock:
                if workspace_id in self._last_compress:
                    elapsed = (_utc_now_dt() - self._last_compress[workspace_id]).total_seconds()
                    if elapsed < 30:
                        logger.info("压缩跳过：间隔不足 30s ws=%s", workspace_id)
                        from services.memory.compression_engine import CompressionReport
                        return CompressionReport(
                            level=session.compression_level,
                            pre_tokens=session.total_tokens,
                            post_tokens=session.total_tokens,
                            warnings=[f"距离上次压缩仅 {elapsed:.0f}s，跳过"],
                        )

        before_tokens = session.total_tokens
        async with self._sessions_lock:
            self._last_compress[workspace_id] = _utc_now_dt()

        report = CompressionReport(
            level=session.compression_level,
            pre_tokens=session.total_tokens,
        )

        if strategy == "budget":
            # 仅 Budget
            result = self.compression.budget.apply_to_session(session)
            report.actions.append(
                CompressionAction(type="budget", saved_tokens=result.total_saved_tokens, details=result)
            )
            report.level = 2
            session.compression_level = 2

        elif strategy == "snip":
            # 仅 Snip
            result = self.compression.snip.execute(session)
            report.actions.append(
                CompressionAction(type="snip", saved_tokens=result.saved_tokens, details=result)
            )
            report.level = 3
            session.compression_level = 3

        elif strategy == "summarize":
            # 仅 Summarize
            result = await self.compression.summarize.compress_session(session)
            report.actions.append(
                CompressionAction(type="summarize", saved_tokens=result.saved_tokens, details=result)
            )
            report.level = 3
            session.compression_level = 3

        else:
            # auto: 三级自动压缩
            report = await self.compression.check_and_compress(session)

        report.post_tokens = session.total_tokens
        report.total_saved = before_tokens - session.total_tokens
        report.saving_ratio = report.total_saved / before_tokens if before_tokens > 0 else 0.0

        # 压缩结果存入 L2
        if report.total_saved > 0:
            await self._archive_compress_event(workspace_id, session_id, report)

        logger.info(
            "压缩完成: ws=%s strategy=%s level=%d before=%d after=%d saved=%d",
            workspace_id, strategy, report.level,
            before_tokens, session.total_tokens, report.total_saved,
        )

        return report

    async def _archive_compress_event(
        self, workspace_id: str, session_id: str, report: CompressionReport,
    ) -> None:
        """将压缩事件归档到 L2"""
        try:
            action_types = [a.type for a in report.actions]
            await self.l2_add(
                workspace_id=workspace_id,
                entry_type="compress_event",
                content=json.dumps({
                    "level": report.level,
                    "pre_tokens": report.pre_tokens,
                    "post_tokens": report.post_tokens,
                    "saved_tokens": report.total_saved,
                    "saving_ratio": report.saving_ratio,
                    "actions": action_types,
                }, ensure_ascii=False),
                summary=f"压缩 L{report.level}: 节省 {report.total_saved} tokens",
                tags=["compression"] + action_types,
                source_session_id=session_id,
                expires_days=7,
            )
        except Exception as e:
            logger.warning("压缩事件归档失败: %s", e)

    # ----------------------------------------------------------
    # 上下文统计
    # ----------------------------------------------------------

    async def get_context_stats(self, workspace_id: str) -> dict:
        """
        获取工作间上下文统计（按 security_memory_api.md §2.2）
        """
        session_id = await self.get_or_create_session(workspace_id)
        token_status = self.l1.get_token_status(session_id)

        l1_info = {
            "message_count": 0,
            "total_tokens": 0,
            "token_limit": settings.DEFAULT_CONTEXT_THRESHOLD,
            "usage_percent": 0.0,
            "status": "green",
        }

        if token_status:
            percentage = token_status.percentage
            if percentage < 60:
                color = "green"
            elif percentage < 80:
                color = "yellow"
            elif percentage < 90:
                color = "orange"
            else:
                color = "red"

            session = self.l1._get_session(session_id)
            l1_info = {
                "message_count": len(session.messages) if session else 0,
                "total_tokens": token_status.total_tokens,
                "token_limit": token_status.max_tokens,
                "usage_percent": percentage,
                "status": color,
            }

        # L2 统计
        l2_entries, l2_total = await self.l2_list(workspace_id, page=1, page_size=1)
        l2_info = {
            "entries_count": l2_total,
            "injections_today": 0,
            "last_archive": None,
        }

        # 压缩统计
        engine = get_engine()
        compression_info = {
            "budget_applied": False,
            "snip_applied": False,
            "summarize_applied": False,
            "freed_tokens": 0,
            "last_compression": None,
        }

        if session_id in self.l1._sessions:
            session = self.l1._sessions[session_id]
            compression_info["budget_applied"] = session.compression_level >= 2
            compression_info["snip_applied"] = session.compression_level >= 3
            compression_info["summarize_applied"] = session.compression_level >= 3
            if session.last_compressed_at:
                compression_info["last_compression"] = session.last_compressed_at.isoformat()

        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT SUM(json_extract(summary, '$.saved_tokens')) as total "
                    "FROM l2_memory_entries "
                    "WHERE workspace_id = :ws_id AND entry_type = 'compress_event'"
                ),
                {"ws_id": workspace_id},
            )
            row = result.fetchone()
            if row and row.total:
                compression_info["freed_tokens"] = row.total

        return {
            "workspace_id": workspace_id,
            "l1": l1_info,
            "l2": l2_info,
            "l3": {"knowledge_count": 0, "last_update": None},
            "compression": compression_info,
        }

    # ----------------------------------------------------------
    # 会话归档 (L1 → L2)
    # ----------------------------------------------------------

    async def archive_session(self, workspace_id: str) -> int:
        """将 L1 会话归档到 L2"""
        async with self._sessions_lock:
            session_id = self._ws_sessions.pop(workspace_id, None)
        if not session_id:
            return 0

        summary = self.l1.close_session(session_id)
        if not summary:
            return 0

        # 请求记录
        archived = 0
        for req in summary.requests:
            await self.l2_add(
                workspace_id=workspace_id,
                entry_type="request",
                content=req.get("request", ""),
                summary=req.get("request", "")[:200],
                source_session_id=session_id,
            )
            archived += 1

        # 决策记录
        for d in summary.decisions:
            await self.l2_add(
                workspace_id=workspace_id,
                entry_type="decision",
                content=f"{d.decision} (理由: {d.rationale})",
                summary=d.decision,
                source_session_id=session_id,
            )
            archived += 1

        # 观察记录
        for obs in summary.key_observations:
            await self.l2_add(
                workspace_id=workspace_id,
                entry_type="learned",
                content=obs.get("content", ""),
                observation_type=obs.get("type"),
                source_session_id=session_id,
            )
            archived += 1

        logger.info(
            "会话归档: ws=%s sid=%s archived=%d tokens=%d",
            workspace_id, session_id, archived, summary.total_tokens,
        )
        return archived


def _escape_like(s: str) -> str:
    """转义 SQL LIKE 通配符"""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# ============================================================
# 全局单例
# ============================================================

_memory_engine: Optional[MemoryEngine] = None


def get_memory_engine() -> MemoryEngine:
    """获取记忆引擎全局单例"""
    global _memory_engine
    if _memory_engine is None:
        _memory_engine = MemoryEngine(
            max_tokens=settings.DEFAULT_CONTEXT_THRESHOLD,
        )
    return _memory_engine
