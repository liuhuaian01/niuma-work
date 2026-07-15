"""
太极引擎 · Meta-Team 协同进化 — v2.5 新增

参考：Meta-Team (Meta 2026.5) — 个体→交互→团队三层协同进化，无预设分工。
太极第七律·生生不息——最好的分工不是预设的，而是从协同中生长出来的。

核心机制：
  1. 个体层（Individual）— 单Agent自我进化，从任务经验中学习
  2. 交互层（Interaction）— Agent间交互模式优化，交接效率+共识质量
  3. 团队层（Team）— 动态分工，根据任务特征自适应调整团队结构
  4. 适应度评估 — 三层联合适应度，驱动自然选择式进化

设计原则：
  - 无预设分工：不硬编码Agent角色，从任务执行中涌现最优分工
  - 柔性格局：团队结构可随时间+任务类型动态变化
  - 最小干预：只在检测到协同效率下降时触发重组

使用方式：
    from engine.meta_team import meta_team
    team = meta_team.get_team("coding")
    assignment = meta_team.assign_task(team_id="coding", task="修复登录bug", complexity=0.7)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import logging
import math
import time

logger = logging.getLogger("niuma.meta_team")


# ============================================================
# 数据模型
# ============================================================

@dataclass
class TeamMember:
    """团队成员——一个Agent在团队中的画像。"""
    agent_id: str
    role: str                     # director/coder/writer/researcher/reviewer
    capabilities: list[str] = field(default_factory=list)
    success_rate: float = 0.8
    avg_drift_score: float = 0.1
    trust_level: float = 0.5
    work_load: int = 0            # 当前任务负载
    joined_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    fitness: float = 0.5          # 个体适应度


@dataclass
class InteractionPair:
    """Agent间交互对——两个Agent的协作模式。"""
    pair_id: str                  # "agent_a:agent_b"
    cooperation_count: int = 0
    success_count: int = 0
    avg_handoff_time_ms: int = 0
    consensus_quality: float = 0.8
    last_interaction: float = field(default_factory=time.time)
    synergy_score: float = 0.5    # 协同效应分


@dataclass
class TeamConfig:
    """团队配置——一个任务类型的"梦之队"。"""
    team_id: str                  # 如 "coding:squad"
    task_type: str                # coding / writing / analysis
    members: list[str]            # agent_id列表
    leader: str = ""              # 团队Leader
    reviewer: str = ""            # 审查者（可选）
    interactions: dict[str, InteractionPair] = field(default_factory=dict)
    formation_round: int = 1      # 形成轮次
    avg_success_rate: float = 0.8
    team_fitness: float = 0.5     # 团队适应度
    last_reshuffled: float = 0.0  # 上次重组时间
    created_at: float = field(default_factory=time.time)


# ============================================================
# Meta-Team 协同进化引擎
# ============================================================

class MetaTeamEngine:
    """Meta-Team三层协同进化引擎。

    太极哲学：无为而治——不是每轮都重组，只在适应度下降时干预。
    """

    TEAM_MAX_SIZE = 5                 # 团队人数上限
    TEAM_MIN_SIZE = 2                 # 团队人数下限
    RESHUFFLE_COOLDOWN = 300          # 重组冷却期5分钟
    RESHUFFLE_THRESHOLD = 0.15        # 适应度下降15%→触发重组
    EVOLUTION_INTERVAL = 20           # 每20次任务→评估一次团队进化

    def __init__(self) -> None:
        self._members: dict[str, TeamMember] = {}
        self._teams: dict[str, TeamConfig] = {}
        self._global_interactions: dict[str, InteractionPair] = {}
        self._task_counter: int = 0

    # ----------------------------------------------------------
    # 个体层（Individual Evolution）
    # ----------------------------------------------------------

    def register_member(
        self, agent_id: str, role: str,
        capabilities: list[str] | None = None,
        trust_level: float = 0.5,
    ) -> TeamMember:
        """注册团队成员。"""
        member = TeamMember(
            agent_id=agent_id,
            role=role,
            capabilities=capabilities or [],
            trust_level=trust_level,
        )
        self._members[agent_id] = member
        logger.info("Meta-Team成员注册: %s (%s)", agent_id, role)
        return member

    def update_member_fitness(
        self, agent_id: str, task_success: bool,
        task_complexity: float = 0.5,
        drift_score: float = 0.0,
        tokens_used: int = 0,
    ) -> float:
        """更新个体适应度——每次任务完成后调用。

        适应度 = (成功率 × 0.4) + ((1-漂移) × 0.3) + (效率 × 0.15) + (信任 × 0.15)
        """
        member = self._members.get(agent_id)
        if not member:
            return 0.5

        # 更新成功率
        n = min(member.success_rate * 10, 20)  # 模拟滑动窗口
        member.success_rate = (member.success_rate * n + (1.0 if task_success else 0.0)) / (n + 1)
        member.avg_drift_score = (member.avg_drift_score * n + drift_score) / (n + 1)
        member.last_active = time.time()

        # 效率分（简化：复杂度/Token比）
        efficiency = min(1.0, task_complexity / max(tokens_used / 1000, 0.01))

        # 计算适应度
        member.fitness = round(
            member.success_rate * 0.40 +
            (1.0 - member.avg_drift_score) * 0.30 +
            efficiency * 0.15 +
            member.trust_level * 0.15,
            3,
        )

        return member.fitness

    # ----------------------------------------------------------
    # 交互层（Interaction Evolution）
    # ----------------------------------------------------------

    def record_interaction(
        self, from_agent: str, to_agent: str,
        success: bool, handoff_time_ms: int = 0,
        consensus_quality: float = 0.8,
    ) -> InteractionPair:
        """记录一次Agent间交互。"""
        pair_id = f"{from_agent}:{to_agent}"

        if pair_id not in self._global_interactions:
            self._global_interactions[pair_id] = InteractionPair(
                pair_id=pair_id,
            )

        pair = self._global_interactions[pair_id]
        pair.cooperation_count += 1
        if success:
            pair.success_count += 1
        pair.avg_handoff_time_ms = (
            (pair.avg_handoff_time_ms * (pair.cooperation_count - 1) + handoff_time_ms)
            / pair.cooperation_count
        )
        pair.consensus_quality = (
            (pair.consensus_quality * (pair.cooperation_count - 1) + consensus_quality)
            / pair.cooperation_count
        )
        pair.last_interaction = time.time()

        # 协同效应 = 成功率 × 共识质量 × (1-交接延迟惩罚)
        handoff_penalty = min(0.3, handoff_time_ms / 10000)  # 10秒以上开始惩罚
        pair.synergy_score = round(
            (pair.success_count / pair.cooperation_count) *
            pair.consensus_quality *
            (1.0 - handoff_penalty),
            3,
        )

        return pair

    # ----------------------------------------------------------
    # 团队层（Team Evolution）
    # ----------------------------------------------------------

    def form_team(
        self, task_type: str, available_agents: list[str],
        team_size: int = 3,
    ) -> TeamConfig:
        """组建新团队——基于适应度+协同效应。

        选择策略:
          1. 按个体适应度排序
          2. 检查交互对的协同效应
          3. 选最优{team_size}人团队
        """
        # 按适应度排序
        candidates = [
            (aid, self._members.get(aid)) for aid in available_agents
            if aid in self._members
        ]
        candidates.sort(key=lambda x: -(x[1].fitness if x[1] else 0))

        selected = []
        leader = ""

        for aid, member in candidates[:team_size]:
            selected.append(aid)
            if not leader and (member.role == "director" or member.trust_level > 0.7):
                leader = aid

        if not leader and selected:
            leader = selected[0]

        team_id = f"{task_type}:squad-{len(self._teams) + 1}"

        # 加载已知交互对
        interactions: dict[str, InteractionPair] = {}
        for a in selected:
            for b in selected:
                if a != b:
                    pair_id = f"{a}:{b}"
                    if pair_id in self._global_interactions:
                        interactions[pair_id] = self._global_interactions[pair_id]

        team = TeamConfig(
            team_id=team_id,
            task_type=task_type,
            members=selected,
            leader=leader,
            interactions=interactions,
        )

        # 计算初始团队适应度
        team.team_fitness = self._compute_team_fitness(team)

        self._teams[team_id] = team
        logger.info(
            "Meta-Team组建: %s (%d人, leader=%s, fitness=%.2f)",
            team_id, len(selected), leader, team.team_fitness,
        )

        return team

    def _compute_team_fitness(self, team: TeamConfig) -> float:
        """计算团队整体适应度。

        团队适应度 = 个体平均适应度 × 0.4 + 交互协同均值 × 0.35 + 团队成功率 × 0.25
        """
        if not team.members:
            return 0.0

        # 个体平均适应度
        indiv_avg = sum(
            self._members.get(mid, TeamMember(agent_id=mid, role="unknown")).fitness
            for mid in team.members
        ) / len(team.members)

        # 交互协同均值
        synergy_avg = 0.0
        if team.interactions:
            synergy_avg = sum(
                p.synergy_score for p in team.interactions.values()
            ) / len(team.interactions)

        return round(
            indiv_avg * 0.40 +
            synergy_avg * 0.35 +
            team.avg_success_rate * 0.25,
            3,
        )

    def reshuffle_team(self, team_id: str) -> TeamConfig | None:
        """重组团队——适应度下降时触发。

        策略:
          1. 移除适应度最低的成员（不低于TEAM_MIN_SIZE）
          2. 从候选人池中选最高适应度补充
          3. 如有交互破坏者（synergy<0.3），强制移除
        """
        team = self._teams.get(team_id)
        if not team:
            return None

        now = time.time()
        if now - team.last_reshuffled < self.RESHUFFLE_COOLDOWN:
            logger.debug("团队%s在重组冷却期，跳过", team_id)
            return team

        # 检查适应度
        current_fitness = self._compute_team_fitness(team)
        if current_fitness >= team.team_fitness * (1 - self.RESHUFFLE_THRESHOLD):
            return team  # 还OK

        # 找最差成员
        worst_score = 1.0
        worst_member = ""
        for mid in team.members:
            m = self._members.get(mid)
            if m and m.fitness < worst_score:
                worst_score = m.fitness
                worst_member = mid

        # 找交互破坏者
        synergy_villain = ""
        for pair_id, pair in team.interactions.items():
            if pair.synergy_score < 0.3 and pair.cooperation_count >= 5:
                # 找出这个交互对中适应度较低的
                agents = pair_id.split(":")
                for aid in agents:
                    if aid in team.members and aid != team.leader:
                        synergy_villain = aid
                        break

        # 移除
        removed = ""
        if synergy_villain:
            removed = synergy_villain
        elif worst_member and len(team.members) > self.TEAM_MIN_SIZE:
            removed = worst_member

        if removed:
            team.members.remove(removed)
            team.last_reshuffled = now
            team.formation_round += 1

            # 补充新成员
            available = [
                aid for aid in self._members
                if aid not in team.members and aid not in team.members
            ]
            if available:
                candidates = sorted(available, key=lambda a: -self._members[a].fitness)
                team.members.append(candidates[0])
                logger.info(
                    "Meta-Team重组: %s -%s +%s",
                    team_id, removed, candidates[0],
                )

        team.team_fitness = self._compute_team_fitness(team)
        return team

    # ----------------------------------------------------------
    # 任务分配
    # ----------------------------------------------------------

    def assign_task(
        self, team_id: str, task: str, complexity: float = 0.5,
    ) -> dict:
        """在团队内分配任务。

        Returns:
            {assignee, backup, reason}
        """
        team = self._teams.get(team_id)
        if not team or not team.members:
            return {"assignee": "", "backup": "", "reason": "团队不存在或为空"}

        # 按适应度排序
        members = sorted(
            team.members,
            key=lambda mid: (
                -self._members[mid].fitness if mid in self._members else 0,
                self._members[mid].work_load if mid in self._members else 0,
            ),
        )

        assignee = members[0]
        backup = members[1] if len(members) > 1 else ""

        # 更新负载
        if assignee in self._members:
            self._members[assignee].work_load += 1

        return {
            "assignee": assignee,
            "backup": backup,
            "reason": f"最高适应度({self._members[assignee].fitness:.2f})优先分配",
        }

    # ----------------------------------------------------------
    # 进化评估
    # ----------------------------------------------------------

    def evaluate_evolution(self) -> dict:
        """整体进化评估——定期触发。

        Returns:
            {teams_to_reshuffle, teams_healthy, global_fitness}
        """
        self._task_counter += 1

        if self._task_counter % self.EVOLUTION_INTERVAL != 0:
            return {"triggered": False, "next_at": self.EVOLUTION_INTERVAL - (self._task_counter % self.EVOLUTION_INTERVAL)}

        to_reshuffle = []
        healthy = []

        for team_id, team in self._teams.items():
            current = self._compute_team_fitness(team)
            if current < team.team_fitness * (1 - self.RESHUFFLE_THRESHOLD):
                to_reshuffle.append({
                    "team_id": team_id,
                    "current_fitness": current,
                    "previous_fitness": team.team_fitness,
                })
            else:
                healthy.append(team_id)

        global_fitness = 0.0
        if self._members:
            global_fitness = sum(m.fitness for m in self._members.values()) / len(self._members)

        return {
            "triggered": True,
            "teams_to_reshuffle": to_reshuffle,
            "teams_healthy": healthy,
            "global_fitness": round(global_fitness, 3),
        }

    # ----------------------------------------------------------
    # 查询接口
    # ----------------------------------------------------------

    def get_team(self, team_id: str) -> TeamConfig | None:
        return self._teams.get(team_id)

    def list_teams(self) -> list[dict]:
        return [
            {
                "team_id": t.team_id,
                "task_type": t.task_type,
                "members": t.members,
                "leader": t.leader,
                "size": len(t.members),
                "fitness": t.team_fitness,
                "formation_round": t.formation_round,
            }
            for t in self._teams.values()
        ]

    def get_top_interactions(self, limit: int = 10) -> list[dict]:
        """获取最佳Agent交互对。"""
        pairs = sorted(
            self._global_interactions.values(),
            key=lambda p: -p.synergy_score,
        )
        return [
            {
                "pair": p.pair_id,
                "cooperations": p.cooperation_count,
                "success_rate": round(p.success_count / max(p.cooperations, 1), 3),
                "synergy": p.synergy_score,
            }
            for p in pairs[:limit]
        ]

    def get_stats(self) -> dict:
        return {
            "members": len(self._members),
            "teams": len(self._teams),
            "interactions": len(self._global_interactions),
            "global_fitness": round(
                sum(m.fitness for m in self._members.values()) / max(len(self._members), 1),
                3,
            ) if self._members else 0.0,
            "top_members": sorted(
                [(aid, m.fitness) for aid, m in self._members.items()],
                key=lambda x: -x[1],
            )[:5],
        }


# ============================================================
# 全局实例
# ============================================================

meta_team = MetaTeamEngine()
