"""
太极引擎 · 漂移感知路由（Drift-Aware Routing — DAR）— v2.0 新增

参考：ASI论文DAR策略（63.0%漂移减少）。
太极第五律·无为而治——不是每次都用最强者，而是选择最合适的。

核心机制：
  1. 漂移感知委派 — 稳定Agent优先委派，漂移Agent触发重置
  2. 稳定性评分 — 结合drift_score+成功率的综合评分
  3. 自动重置 — 严重漂移时自动触发agent上下文重置
  4. 路由集成 — 与DynamicBalancer无缝衔接

使用方式：
    from engine.dar_router import dar_router
    route = dar_router.route_task(agent_id="coder-1", task_type="coding", session_id="s1")
    if route["should_reset"]:
        # 触发agent上下文重置
        pass
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import logging
import time

logger = logging.getLogger("niuma.dar")


# ============================================================
# 数据模型
# ============================================================

@dataclass
class AgentStability:
    """Agent稳定性画像。"""
    agent_id: str
    success_rate: float = 0.8      # 历史成功率（滑动窗口）
    avg_drift_score: float = 0.1   # 平均漂移分数（越低越稳定）
    total_calls: int = 0
    consecutive_failures: int = 0
    last_drift_severity: str = "green"
    last_active: float = field(default_factory=time.time)
    stability_rank: float = 0.5    # 综合稳定性排名 0-1


@dataclass
class DARDecision:
    """DAR路由决策。"""
    agent_id: str
    should_delegate: bool           # 是否委派给此Agent
    should_reset: bool              # 是否需要重置Agent上下文
    reason: str                     # 决策原因
    fallback_id: str = ""           # 备选Agent
    stability: AgentStability | None = None


# ============================================================
# DAR路由引擎
# ============================================================

class DARRouter:
    """漂移感知路由引擎。

    与DynamicBalancer配合：Balancer负责性能路由，DAR负责稳定性路由。
    太极哲学：刚柔并济——Balancer为刚，追求最优性能；DAR为柔，避免不稳定运行。
    """

    RECENT_WINDOW = 20             # 滑动窗口大小
    RESET_THRESHOLD = 0.6          # drift_score > 0.6 → 触发重置
    ALERT_THRESHOLD = 0.35         # drift_score > 0.35 → 降低委派优先级

    def __init__(self) -> None:
        self._agents: dict[str, AgentStability] = {}
        self._session_agents: dict[str, str] = {}    # session_id → agent_id
        self._drift_cache: dict[str, list[float]] = {}  # agent_id → recent drift scores

    # ----------------------------------------------------------
    # 稳定性更新
    # ----------------------------------------------------------

    def update_stability(
        self,
        agent_id: str,
        drift_score: float = 0.0,
        drift_severity: str = "green",
        success: bool = True,
    ) -> AgentStability:
        """更新Agent稳定性画像——每次任务完成后调用。"""
        if agent_id not in self._agents:
            self._agents[agent_id] = AgentStability(agent_id=agent_id)

        agent = self._agents[agent_id]
        agent.total_calls += 1
        agent.last_active = time.time()
        agent.last_drift_severity = drift_severity

        if success:
            agent.consecutive_failures = 0
        else:
            agent.consecutive_failures += 1

        # 更新成功率（滑动窗口）
        n = min(agent.total_calls, self.RECENT_WINDOW)
        agent.success_rate = ((agent.success_rate * (n - 1) + (1.0 if success else 0.0)) / n)

        # 更新平均漂移分数
        self._drift_cache.setdefault(agent_id, []).append(drift_score)
        if len(self._drift_cache[agent_id]) > self.RECENT_WINDOW:
            self._drift_cache[agent_id] = self._drift_cache[agent_id][-self.RECENT_WINDOW:]
        agent.avg_drift_score = (
            sum(self._drift_cache[agent_id]) / len(self._drift_cache[agent_id])
            if self._drift_cache[agent_id] else 0
        )

        # 综合稳定性排名
        # 成功率越高 + 漂移越低 = 越稳定
        stability_raw = agent.success_rate * (1.0 - agent.avg_drift_score)
        agent.stability_rank = max(0.1, min(1.0, stability_raw))

        # 连续失败惩罚
        if agent.consecutive_failures >= 3:
            agent.stability_rank *= 0.5  # 减半

        return agent

    # ----------------------------------------------------------
    # 路由决策
    # ----------------------------------------------------------

    def route_task(
        self,
        agent_id: str,
        task_type: str,
        session_id: str = "",
        drift_score: float = 0.0,
    ) -> DARDecision:
        """为任务做路由决策——判断Agent是否适合承接此任务。

        Args:
            agent_id: 目标Agent
            task_type: 任务类型
            session_id: 会话ID
            drift_score: 最新的漂移分数

        Returns:
            DARDecision — 包含委派/重置/备选建议
        """
        agent = self._agents.get(agent_id)

        # 无画像的新Agent——默认通过
        if not agent or agent.total_calls < 5:
            self._session_agents[session_id] = agent_id
            return DARDecision(
                agent_id=agent_id,
                should_delegate=True,
                should_reset=False,
                reason="新Agent或样本不足，默认通过",
                stability=agent,
            )

        # 决策1: 严重漂移 → 触发重置
        if drift_score > self.RESET_THRESHOLD:
            self._session_agents[session_id] = agent_id
            return DARDecision(
                agent_id=agent_id,
                should_delegate=True,
                should_reset=True,
                reason=f"漂移分数{drift_score:.2f}超过重置阈值{RESET_THRESHOLD}",
                stability=agent,
            )

        # 决策2: 连续失败 → 阻拦
        if agent.consecutive_failures >= 3:
            fallback = self._find_fallback(agent_id)
            return DARDecision(
                agent_id=agent_id,
                should_delegate=False,
                should_reset=True,
                reason=f"连续{agent.consecutive_failures}次失败，建议切换到{fallback}",
                fallback_id=fallback,
                stability=agent,
            )

        # 决策3: 中度漂移 → 降低优先级但仍可委派
        if drift_score > self.ALERT_THRESHOLD and agent.avg_drift_score > 0.3:
            fallback = self._find_fallback(agent_id)
            if fallback:
                return DARDecision(
                    agent_id=fallback,
                    should_delegate=True,
                    should_reset=False,
                    reason=f"Agent {agent_id} 近期稳定性偏低({agent.stability_rank:.2f})，切换到 {fallback}",
                    fallback_id=agent_id,
                    stability=agent,
                )

        # 决策4: 正常通过
        self._session_agents[session_id] = agent_id
        return DARDecision(
            agent_id=agent_id,
            should_delegate=True,
            should_reset=False,
            reason="Agent稳定性正常",
            stability=agent,
        )

    def _find_fallback(self, agent_id: str) -> str:
        """找到同类型最稳定的备选Agent。"""
        candidates = [
            (aid, a) for aid, a in self._agents.items()
            if aid != agent_id and a.stability_rank > 0.3
        ]
        if not candidates:
            return ""
        candidates.sort(key=lambda x: -x[1].stability_rank)
        return candidates[0][0]

    # ----------------------------------------------------------
    # 查询接口
    # ----------------------------------------------------------

    def get_agent_stability(self, agent_id: str) -> AgentStability | None:
        return self._agents.get(agent_id)

    def list_stable_agents(self, min_rank: float = 0.5) -> list[str]:
        return [
            aid for aid, a in self._agents.items()
            if a.stability_rank >= min_rank
        ]

    def list_drifting_agents(self, min_drift: float = 0.3) -> list[dict]:
        return [
            {
                "agent_id": aid,
                "avg_drift_score": round(a.avg_drift_score, 3),
                "stability_rank": round(a.stability_rank, 3),
                "success_rate": round(a.success_rate, 3),
                "consecutive_failures": a.consecutive_failures,
            }
            for aid, a in self._agents.items()
            if a.avg_drift_score >= min_drift
        ]

    def get_stats(self) -> dict:
        agents = len(self._agents)
        stable = len(self.list_stable_agents())
        drifting = len(self.list_drifting_agents())
        return {
            "total_agents": agents,
            "stable_agents": stable,
            "drifting_agents": drifting,
            "sessions_mapped": len(self._session_agents),
        }


# ============================================================
# 全局实例
# ============================================================

dar_router = DARRouter()
