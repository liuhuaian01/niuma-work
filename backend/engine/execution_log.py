"""
太极引擎 · 执行日志（Execution Log）

记录每次 Agent 执行的元数据（不记录内容数据）。
元数据 = Token消耗 / 成功失败 / Gate评分 / 工具调用 / 模型 / 耗时。
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import Optional
import asyncio
import json
import threading

from engine.otel_tracer import tracer
from engine.execution_repository import ExecutionRepository

# P2-3: 持久化后台事件循环——避免每次 asyncio.run() 创建/销毁事件循环的开销
_background_loop: asyncio.AbstractEventLoop | None = None
_background_loop_lock = threading.Lock()


def _get_background_loop() -> asyncio.AbstractEventLoop:
    """获取或创建持久化后台事件循环（线程安全）。"""
    global _background_loop
    if _background_loop is None or _background_loop.is_closed():
        with _background_loop_lock:
            if _background_loop is None or _background_loop.is_closed():
                _background_loop = asyncio.new_event_loop()
                thread = threading.Thread(
                    target=_background_loop.run_forever,
                    daemon=True,
                    name="execution-log-bg-loop",
                )
                thread.start()
    return _background_loop


def _run_async(coro):
    """在持久化后台事件循环中执行协程，返回结果。
    
    替代 asyncio.run()——复用同一事件循环，避免每次重新创建。
    """
    loop = _get_background_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()


@dataclass
class ExecutionRecord:
    """一次 Agent 执行的元数据。"""

    agent_id: str
    workspace_id: str
    task_type: str              # writing/coding/analysis/search/conversation
    model_used: str             # deepseek-v3.2 / gemma-4 / ...
    tokens_used: int
    gate_score: float           # 0.0-1.0, Gate Validator 评分
    success: bool               # 最终是否成功
    tools_used: int = 0         # 工具调用次数
    duration_ms: int = 0        # 执行耗时（毫秒）
    error_type: str = ""        # gate_fail / pi_intercept / token_exceeded / empty=无错误
    user_feedback: str = ""     # positive / negative / neutral
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ExecutionLogger:
    """执行日志——只记录元数据。
    
    P0修复: 迁移到SQLAlchemy异步Repository模式，消除双重数据库系统。
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path
        self._repo: Optional[ExecutionRepository] = None
        self._records: list[ExecutionRecord] = []
        if db_path:
            self._init_repo_sync()
    
    def _init_repo_sync(self) -> None:
        """同步初始化Repository（兼容现有同步调用）"""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._async_init())
        except RuntimeError:
            _run_async(self._async_init())
    
    async def _async_init(self) -> None:
        """异步初始化Repository"""
        if self._repo is None:
            self._repo = ExecutionRepository()
            await self._repo.init_tables()

    def log(self, record: ExecutionRecord) -> None:
        """记录一条执行日志。
        
        P0修复: 使用异步Repository，支持SQLAlchemy事务管理。
        P2-1: OTel Span——追踪日志写入。
        """
        span_attrs = {
            "agent.id": record.agent_id,
            "task.type": record.task_type,
            "model.used": record.model_used,
            "tokens.used": record.tokens_used,
        }
        with tracer.span("execution.log", span_attrs) as span:
            self._records.append(record)
            if self._repo:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._log_async(record))
                except RuntimeError:
                    _run_async(self._log_async(record))
            span.set_attribute("outcome", "success" if record.success else "error")
    
    async def _log_async(self, record: ExecutionRecord) -> None:
        """异步记录日志"""
        await self._repo.insert_record({
            "agent_id": record.agent_id,
            "workspace_id": record.workspace_id,
            "task_type": record.task_type,
            "model_used": record.model_used,
            "tokens_used": record.tokens_used,
            "gate_score": record.gate_score,
            "success": int(record.success),
            "tools_used": record.tools_used,
            "duration_ms": record.duration_ms,
            "error_type": record.error_type,
            "user_feedback": record.user_feedback,
            "timestamp": record.timestamp
        })

    def get_today_records(self) -> list[ExecutionRecord]:
        """获取今日记录。
        
        P0修复: 使用异步Repository查询。
        """
        today = str(date.today())
        if self._repo:
            try:
                loop = asyncio.get_running_loop()
                rows = loop.run_until_complete(self._repo.get_today_records(today))
            except RuntimeError:
                rows = _run_async(self._repo.get_today_records(today))
            if rows:
                return [self._dict_to_record(r) for r in rows]
        return [r for r in self._records if r.timestamp.startswith(today)]

    def get_recent(self, days: int = 7) -> list[ExecutionRecord]:
        """获取近 N 天的记录。
        
        P0修复: 使用异步Repository查询。
        """
        if self._repo:
            try:
                loop = asyncio.get_running_loop()
                rows = loop.run_until_complete(self._repo.get_recent_records(days))
            except RuntimeError:
                rows = _run_async(self._repo.get_recent_records(days))
            return [self._dict_to_record(r) for r in rows]
        return [r for r in self._records[-100:]]

    def get_stats(self) -> dict:
        """执行统计。
        
        P0修复: 使用异步Repository查询。
        """
        today = str(date.today())
        if self._repo:
            try:
                loop = asyncio.get_running_loop()
                return loop.run_until_complete(self._repo.get_stats(today))
            except RuntimeError:
                return _run_async(self._repo.get_stats(today))
        
        # Fallback到内存记录
        today_records = self.get_today_records()
        if not today_records:
            return {"today": today, "total_executions": 0}
        successes = [r for r in today_records if r.success]
        return {
            "today": today,
            "total_executions": len(today_records),
            "success_count": len(successes),
            "success_rate": round(len(successes) / len(today_records), 2) if today_records else 0,
            "total_tokens": sum(r.tokens_used for r in today_records),
            "avg_tokens": int(sum(r.tokens_used for r in today_records) / len(today_records)) if today_records else 0,
        }
    
    def _dict_to_record(self, data: dict) -> ExecutionRecord:
        """将字典转换为ExecutionRecord"""
        return ExecutionRecord(
            agent_id=data["agent_id"],
            workspace_id=data["workspace_id"],
            task_type=data["task_type"],
            model_used=data["model_used"],
            tokens_used=data["tokens_used"],
            gate_score=data["gate_score"] or 0,
            success=bool(data["success"]),
            tools_used=data["tools_used"] or 0,
            duration_ms=data["duration_ms"] or 0,
            error_type=data["error_type"] or "",
            user_feedback=data["user_feedback"] or "",
            timestamp=data["timestamp"]
        )
