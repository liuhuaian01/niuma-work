"""
太极引擎 · Token 预算管理器

Agent 维度日预算 + 50/70/90% 比例告警 + 降级链自动切换。

天道法则——预算不是枷锁，是帮用户看清代价。
用户有权提高或取消限制（人遁其一）。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from utils import is_new_day
from typing import Optional
import asyncio
import logging

from engine import async_db

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    NONE = "none"           # 0-50%: 正常
    WARNING = "warning"     # 50-70%: ⚠️ 上下文压力警告
    CAUTION = "caution"     # 70-90%: 🔶 预算预警
    CRITICAL = "critical"   # 90-100%: 🔴 任务暂停
    EXCEEDED = "exceeded"   # 100%+: ❌ 自动降级


@dataclass
class BudgetStatus:
    agent_id: str
    daily_budget: int
    used_today: int
    remaining: int
    alert_level: AlertLevel
    percentage: float
    can_continue: bool
    message: str


class TokenBudgetManager:
    """Token 预算管理器。
    
    P0修复: 为全局状态添加线程安全保护，使用asyncio.Lock防止竞态条件。
    """

    def __init__(self) -> None:
        self._budgets: dict[str, int] = {}       # agent_id → daily_budget (系统默认)
        self._original: dict[str, int] = {}       # agent_id → 原始预算（覆盖前保存）
        self._usage: dict[str, int] = {}          # agent_id → used_today
        _, self._today = is_new_day("")           # 初始化为今天
        self._user_overrides: dict[str, int] = {}  # 用户手动设置的预算
        self._db_ready: bool = False               # SQLite 持久化是否就绪
        
        # P0修复: 添加异步锁保护全局状态
        self._lock: Optional[asyncio.Lock] = None
    
    async def _get_lock(self) -> asyncio.Lock:
        """获取锁（延迟初始化）"""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    # ---- SQLite 持久化 ----

    async def init_persistence(self) -> None:
        """初始化持久化：建表 + 从 DB 加载状态。应在启动时调用一次。"""
        await async_db.execute("""
            CREATE TABLE IF NOT EXISTS token_budgets (
                agent_id TEXT PRIMARY KEY,
                daily_budget INTEGER NOT NULL DEFAULT 20000,
                user_override INTEGER DEFAULT NULL
            )
        """)
        await async_db.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                date TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                tokens_used INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (date, agent_id)
            )
        """)
        self._db_ready = True
        await self._load_from_db()

    async def _load_from_db(self) -> None:
        """从 DB 加载预算和今日用量到内存。
        
        P0修复: 使用锁保护共享状态写入。
        """
        rows = await async_db.fetch_all("SELECT agent_id, daily_budget, user_override FROM token_budgets")
        lock = await self._get_lock()
        async with lock:
            for row in rows:
                aid = row["agent_id"]
                self._budgets[aid] = row["daily_budget"]
                self._original[aid] = row["daily_budget"]
                if row["user_override"] is not None:
                    self._user_overrides[aid] = row["user_override"]
                    self._budgets[aid] = row["user_override"]

        _, today = is_new_day("")
        usage_rows = await async_db.fetch_all(
            "SELECT agent_id, tokens_used FROM token_usage WHERE date = ?", (today,)
        )
        async with lock:
            for row in usage_rows:
                self._usage[row["agent_id"]] = row["tokens_used"]

    def _schedule_save(self, coro) -> None:
        """如果事件循环正在运行，调度一个异步保存任务。"""
        if not self._db_ready:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            pass

    async def _save_budget(self, agent_id: str) -> None:
        """持久化单个 Agent 的预算设置。"""
        await async_db.execute(
            """INSERT OR REPLACE INTO token_budgets (agent_id, daily_budget, user_override)
               VALUES (?, ?, ?)""",
            (agent_id, self._original.get(agent_id, 20000),
             self._user_overrides.get(agent_id)),
        )

    async def _save_usage(self, agent_id: str) -> None:
        """持久化单个 Agent 的今日用量。"""
        _, today = is_new_day(self._today)
        await async_db.execute(
            """INSERT OR REPLACE INTO token_usage (date, agent_id, tokens_used)
               VALUES (?, ?, ?)""",
            (today, agent_id, self._usage.get(agent_id, 0)),
        )

    def _reset_if_new_day(self) -> None:
        is_new, self._today = is_new_day(self._today)
        if is_new:
            self._usage = {}

    def set_agent_budget(self, agent_id: str, daily_budget: int) -> bool:
        """设置 Agent 日预算（系统默认）。

        如果用户已手动设置覆盖值，系统默认将被忽略。
        返回 True 表示设置成功，False 表示被用户覆盖忽略。
        
        P0修复: 使用锁保护共享状态写入。
        """
        import asyncio
        
        # 同步调用，使用asyncio.run
        async def _set():
            lock = await self._get_lock()
            async with lock:
                self._original[agent_id] = daily_budget
                if agent_id not in self._user_overrides:
                    self._budgets[agent_id] = daily_budget
                    return True
                else:
                    logger.warning(
                        "Agent %s 的系统默认预算 %d 被忽略：用户已手动设置为 %d",
                        agent_id, daily_budget, self._user_overrides[agent_id],
                    )
                    return False
        
        try:
            loop = asyncio.get_running_loop()
            return loop.run_until_complete(_set())
        except RuntimeError:
            return asyncio.run(_set())

    def set_user_budget(self, agent_id: str, daily_budget: int | None) -> None:
        """用户手动设置预算（人遁其一）。None = 恢复默认。
        
        P0修复: 使用锁保护共享状态写入。
        """
        import asyncio
        
        async def _set():
            lock = await self._get_lock()
            async with lock:
                if daily_budget is None:
                    self._user_overrides.pop(agent_id, None)
                    self._budgets[agent_id] = self._original.get(agent_id, 20000)
                else:
                    self._user_overrides[agent_id] = daily_budget
                    self._budgets[agent_id] = daily_budget
        
        try:
            loop = asyncio.get_running_loop()
            loop.run_until_complete(_set())
        except RuntimeError:
            asyncio.run(_set())
        
        self._schedule_save(self._save_budget(agent_id))

    def get_effective_budget(self, agent_id: str) -> int:
        """获取有效预算。优先用户设置。
        
        P0修复: 使用锁保护共享状态读取。
        """
        import asyncio
        
        async def _get():
            lock = await self._get_lock()
            async with lock:
                return self._user_overrides.get(agent_id, self._budgets.get(agent_id, 20000))
        
        try:
            loop = asyncio.get_running_loop()
            return loop.run_until_complete(_get())
        except RuntimeError:
            return asyncio.run(_get())

    def record_usage(self, agent_id: str, tokens: int) -> None:
        """记录 Token 消耗。
        
        P0修复: 使用锁保护共享状态写入。
        """
        import asyncio
        
        async def _record():
            lock = await self._get_lock()
            async with lock:
                self._reset_if_new_day()
                self._usage[agent_id] = self._usage.get(agent_id, 0) + tokens
        
        try:
            loop = asyncio.get_running_loop()
            loop.run_until_complete(_record())
        except RuntimeError:
            asyncio.run(_record())
        
        self._schedule_save(self._save_usage(agent_id))

    def check(self, agent_id: str) -> BudgetStatus:
        """检查预算状态，返回告警级别。
        
        P0修复: 使用锁保护共享状态读取。
        """
        import asyncio
        
        async def _check():
            lock = await self._get_lock()
            async with lock:
                self._reset_if_new_day()
                budget = self.get_effective_budget(agent_id)
                used = self._usage.get(agent_id, 0)
                remaining = max(0, budget - used)
                pct = used / budget if budget > 0 else 1.0

                if pct < 0.50:
                    level, can_continue, msg = AlertLevel.NONE, True, "Token 消耗正常"
                elif pct < 0.70:
                    level, can_continue, msg = AlertLevel.WARNING, True, \
                        f"⚠️ Token 消耗已达 {pct:.0%}（{used}/{budget}）"
                elif pct < 0.90:
                    level, can_continue, msg = AlertLevel.CAUTION, True, \
                        f"🔶 Token 消耗已达 {pct:.0%}（{used}/{budget}），建议确认是否继续"
                elif pct < 0.95:
                    level, can_continue, msg = AlertLevel.CRITICAL, False, \
                        f"🔴 Token 消耗已达 {pct:.0%}（{used}/{budget}），任务已暂停。继续请提高预算。"
                else:
                    level, can_continue, msg = AlertLevel.EXCEEDED, False, \
                        f"❌ Token 已超限（{used}/{budget}）。已自动降级到 Gemma-4 兜底。"

                return BudgetStatus(
                    agent_id=agent_id, daily_budget=budget, used_today=used,
                    remaining=remaining, alert_level=level, percentage=pct,
                    can_continue=can_continue, message=msg,
                )
        
        try:
            loop = asyncio.get_running_loop()
            # P1-2 关联修复：事件循环已运行时，通过线程池执行以避免
            # "asyncio.run() cannot be called from a running event loop"
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, _check())
                return future.result(timeout=30)
        except RuntimeError:
            return asyncio.run(_check())

    def get_stats(self) -> dict:
        """获取统计信息。
        
        P0修复: 使用锁保护共享状态读取。
        """
        import asyncio
        
        async def _get_stats():
            lock = await self._get_lock()
            async with lock:
                self._reset_if_new_day()
                return {
                    "today": self._today,
                    "agents": {
                        aid: {
                            "budget": self.get_effective_budget(aid),
                            "used": self._usage.get(aid, 0),
                            "remaining": max(0, self.get_effective_budget(aid) - self._usage.get(aid, 0)),
                            "has_user_override": aid in self._user_overrides,
                        }
                        for aid in set(list(self._budgets.keys()) + list(self._usage.keys()))
                    },
                }
        
        try:
            loop = asyncio.get_running_loop()
            return loop.run_until_complete(_get_stats())
        except RuntimeError:
            return asyncio.run(_get_stats())


# ================================================================
# 请求级硬上限 —— vLLM Micro-Agent 蒸馏
# ================================================================

# 单次请求 Token 上限（含 context + response）
PER_REQUEST_MAX_TOKENS: int = 40_000

# 单次请求延迟硬上限（毫秒），超时直接 abort
PER_REQUEST_MAX_LATENCY_MS: int = 30_000

# 请求级预算超限后的拦截原因标识
PER_REQUEST_ABORT_REASON: str = "request_budget_exceeded"


def check_per_request(
    estimated_tokens: int,
    max_tokens: int = PER_REQUEST_MAX_TOKENS,
) -> tuple[bool, str]:
    """请求级硬上限检查。

    在 daily budget 检查之后、LLM 调用之前执行。
    单次请求超过上限 → 直接拒绝，不等到发出去才发现。

    Returns:
        (可继续, 原因)
    """
    if estimated_tokens > max_tokens:
        return False, (
            f"请求级预算超限: 预估 {estimated_tokens} tokens，"
            f"超过单次上限 {max_tokens} tokens。"
            f"请拆分任务或提高上限。"
        )
    return True, "ok"


# 平台唯一实例
token_budget = TokenBudgetManager()
