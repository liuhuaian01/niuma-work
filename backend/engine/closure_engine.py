"""
太极引擎 · 闭合链路引擎

生生不息——研究发现 → 自动评估 → 生成变更建议 → 审批 → 自动更新。
这是太极引擎的终极闭环：从感知到更新，全自动。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable
import asyncio

from engine import async_db


class ChangeType(Enum):
    CONFIG = "config"           # 配置更新
    BUDGET = "budget"           # 预算调整
    MODEL = "model"             # 模型推荐更新
    RULE = "rule"               # 规则新增
    SKILL = "skill"             # 技能优化
    DOCUMENT = "document"       # 文档同步


class ChangeStatus(Enum):
    PROPOSED = "proposed"       # 已提出
    APPROVED = "approved"       # 已审批
    REJECTED = "rejected"       # 已拒绝
    APPLIED = "applied"         # 已应用
    ROLLED_BACK = "rolled_back" # 已回滚


@dataclass
class ChangeProposal:
    """一个架构变更建议。"""
    id: str
    change_type: ChangeType
    title: str
    description: str
    reason: str                       # 为什么需要变更——来自研究发现/反思
    target_file: str = ""             # 要更新的文件路径
    old_value: str = ""               # 旧值
    new_value: str = ""               # 新值
    confidence: float = 0.5           # 0.0-1.0
    status: ChangeStatus = ChangeStatus.PROPOSED
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ClosureEngine:
    """闭合链路引擎。

    研究发现 → Smart Allocator 评估影响 → 生成变更建议 → 审批 → 自动更新。
    人从决策者变成守门人——只审"道"有没有偏离。
    """

    def __init__(self) -> None:
        self._proposals: list[ChangeProposal] = []
        self._applied: list[ChangeProposal] = []
        self._rollbacks: list[ChangeProposal] = []
        self._approval_handler: Optional[Callable] = None       # 审批回调
        self._apply_handler: Optional[Callable] = None          # 应用回调
        self._db_ready: bool = False

    # ---- SQLite 持久化 ----

    async def init_persistence(self) -> None:
        """初始化持久化：建表 + 从 DB 加载。应在启动时调用一次。"""
        await async_db.execute("""
            CREATE TABLE IF NOT EXISTS closure_proposals (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 0.5,
                status TEXT NOT NULL DEFAULT 'proposed',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        self._db_ready = True
        await self._load_from_db()

    async def _load_from_db(self) -> None:
        """从 DB 加载提案到内存。"""
        rows = await async_db.fetch_all(
            "SELECT id, type, description, confidence, status, created_at FROM closure_proposals"
        )
        for row in rows:
            try:
                proposal = ChangeProposal(
                    id=row["id"],
                    change_type=ChangeType(row["type"]),
                    title=row["description"][:50],
                    description=row["description"],
                    reason="",
                    confidence=row["confidence"],
                    status=ChangeStatus(row["status"]),
                    timestamp=row["created_at"],
                )
                self._proposals.append(proposal)
                if proposal.status == ChangeStatus.APPLIED:
                    self._applied.append(proposal)
                elif proposal.status == ChangeStatus.ROLLED_BACK:
                    self._rollbacks.append(proposal)
            except (ValueError, KeyError):
                continue

    def _schedule_save(self, coro) -> None:
        """如果事件循环正在运行，调度一个异步保存任务。"""
        if not self._db_ready:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            pass

    async def _save_proposal(self, proposal: ChangeProposal) -> None:
        """持久化单个提案。"""
        await async_db.execute(
            """INSERT OR REPLACE INTO closure_proposals
               (id, type, description, confidence, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (proposal.id, proposal.change_type.value, proposal.description,
             proposal.confidence, proposal.status.value, proposal.timestamp),
        )

    def propose(
        self, change_type: ChangeType, title: str, description: str,
        reason: str = "", target_file: str = "", old_value: str = "",
        new_value: str = "", confidence: float = 0.5,
    ) -> ChangeProposal:
        """生成变更建议。"""
        proposal = ChangeProposal(
            id=f"change-{len(self._proposals)+1}",
            change_type=change_type, title=title, description=description,
            reason=reason, target_file=target_file,
            old_value=old_value, new_value=new_value, confidence=confidence,
        )
        self._proposals.append(proposal)
        self._schedule_save(self._save_proposal(proposal))
        return proposal

    def evaluate_from_reflection(self, success_pattern: str, confidence: float) -> list[ChangeProposal]:
        """从反思引擎的发现中自动评估并生成变更。"""
        proposals: list[ChangeProposal] = []

        # 模型组合推荐 → 自动更新 Smart Allocator 偏好
        if "deepseek" in success_pattern.lower() and confidence > 0.8:
            proposals.append(self.propose(
                ChangeType.MODEL, "模型偏好更新",
                f"反思发现 {success_pattern} 高成功率，建议更新模型偏好",
                reason=success_pattern, confidence=confidence,
                old_value="kimi-k2.6", new_value="deepseek-v4",
            ))

        # Token 预算调整
        if confidence > 0.85:
            proposals.append(self.propose(
                ChangeType.BUDGET, "Token 预算优化",
                f"高成功率任务类型建议提升预算",
                reason=success_pattern, confidence=confidence,
            ))

        return proposals

    def approve(self, proposal_id: str) -> bool:
        """审批通过——应用变更。"""
        for p in self._proposals:
            if p.id == proposal_id:
                p.status = ChangeStatus.APPROVED
                try:
                    self._apply_handler(p) if self._apply_handler else None
                    p.status = ChangeStatus.APPLIED
                    self._applied.append(p)
                    self._schedule_save(self._save_proposal(p))
                except Exception:
                    p.status = ChangeStatus.ROLLED_BACK
                    self._rollbacks.append(p)
                    self._schedule_save(self._save_proposal(p))
                    return False
                return True
        return False

    def reject(self, proposal_id: str) -> None:
        for p in self._proposals:
            if p.id == proposal_id:
                p.status = ChangeStatus.REJECTED
                self._schedule_save(self._save_proposal(p))

    def set_apply_handler(self, handler: Callable) -> None:
        self._apply_handler = handler

    def get_pending(self) -> list[ChangeProposal]:
        return [p for p in self._proposals if p.status == ChangeStatus.PROPOSED]

    def get_stats(self) -> dict:
        return {
            "total_proposals": len(self._proposals),
            "applied": len(self._applied),
            "rolled_back": len(self._rollbacks),
            "pending": len(self.get_pending()),
        }

    def auto_apply_safe_changes(self) -> dict:
        """自动应用安全类变更（预算、权重——不需要人工审批）。
        返回 {applied: N, rolled_back: N, skipped: N}。
        """
        result = {"applied": 0, "rolled_back": 0, "skipped": 0}
        for p in self.get_pending():
            # 只自动应用安全类型
            if p.change_type not in (ChangeType.BUDGET, ChangeType.MODEL, ChangeType.CONFIG):
                result["skipped"] += 1
                continue

            # 置信度不够的不自动应用
            if p.confidence < 0.80:
                result["skipped"] += 1
                continue

            success = self.approve(p.id)
            if success:
                result["applied"] += 1
            else:
                result["rolled_back"] += 1

        return result
