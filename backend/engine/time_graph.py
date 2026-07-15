"""
太极引擎 · 时间图谱引擎（Temporal Graph Engine）— v2.5 新增

参考：腾讯云Agent Memory时间感知层 — 时间戳+因果边+事件网络。
太极第七律·生生不息——记忆不是存储，是在时间中编织因果的网。

核心机制：
  1. 事件节点 — 每个重要操作/决策都是图中的一个节点
  2. 因果边 — 事件之间的因果关系（触发/依赖/替代）
  3. 时间线查询 — 按时间范围回溯事件链
  4. 因果回溯 — 从错误追溯根因（沿因果边反向遍历）
  5. 影响传播 — 评估一个事件对其他事件的连锁影响

设计原则：
  - 轻量：内存图结构，无外部图数据库依赖
  - 渐进衰减：超过30天的事件自动压缩为摘要节点
  - 因果推断：自动建立"触发"边（时间上相邻+语义相关的事件）

使用方式：
    from engine.time_graph import time_graph
    time_graph.add_event(project="super-niuma", event_type="bug_fix", summary="修复登录页")
    events = time_graph.query_timeline("super-niuma", hours_ago=24)
    cause = time_graph.trace_root_cause("session-123-error")
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import logging
import time

logger = logging.getLogger("niuma.timegraph")


# ============================================================
# 数据模型
# ============================================================

@dataclass
class EventNode:
    """事件节点——时间图中的一个事件。"""
    id: str
    timestamp: float
    event_type: str               # bug_fix / feature / deploy / decision / error / insight / task
    summary: str                  # 事件摘要
    project: str = ""
    session_id: str = ""
    agent_id: str = ""
    importance: float = 0.5       # 重要性 0-1
    compressed: bool = False      # 是否为压缩摘要节点
    original_ids: list[str] = field(default_factory=list)  # 压缩节点的原始ID列表

    # 因果关系（双向链接）
    caused_by: list[str] = field(default_factory=list)    # 哪些事件导致了它
    causes: list[str] = field(default_factory=list)       # 它导致了哪些事件
    related_to: list[str] = field(default_factory=list)   # 相关但非因果的事件


@dataclass
class CausalEdge:
    """因果边——两个事件之间的因果关系。"""
    from_event: str
    to_event: str
    relation: str                 # triggers / depends_on / fixes / replaces / relates_to
    confidence: float = 0.7       # 因果推断置信度
    created_at: float = field(default_factory=time.time)


# ============================================================
# 时间图谱引擎
# ============================================================

class TemporalGraphEngine:
    """时间图谱引擎——在时间中编织因果网络。

    太极哲学：顺势而为——不是强行加因果边，而是通过时间相邻性+语义相关自然形成。
    """

    MAX_EVENTS = 5000             # 总事件上限
    COMPRESS_AFTER_DAYS = 30      # 压缩阈值
    MAX_CAUSAL_DEPTH = 10         # 因果追溯最大深度

    def __init__(self) -> None:
        self._events: dict[str, EventNode] = {}
        self._edges: dict[str, CausalEdge] = {}           # "from:to" → CausalEdge
        self._timeline_index: dict[str, list[str]] = {}   # project → sorted event_ids
        self._total_events: int = 0

    # ----------------------------------------------------------
    # 事件添加
    # ----------------------------------------------------------

    def add_event(
        self,
        project: str,
        event_type: str,
        summary: str,
        session_id: str = "",
        agent_id: str = "",
        caused_by: list[str] | None = None,
        importance: float = 0.5,
    ) -> EventNode:
        """添加一个新事件到时间图。

        Args:
            project: 项目标识
            event_type: 事件类型
            summary: 摘要
            session_id: 会话ID
            agent_id: Agent ID
            caused_by: 显式指定的原因事件ID列表
            importance: 重要性

        Returns:
            新创建的EventNode
        """
        event_id = f"evt-{project}-{int(time.time() * 1000)}-{self._total_events}"

        event = EventNode(
            id=event_id,
            timestamp=time.time(),
            event_type=event_type,
            summary=summary[:200],
            project=project,
            session_id=session_id,
            agent_id=agent_id,
            importance=importance,
        )

        # 显式因果关系
        if caused_by:
            for cause_id in caused_by:
                event.caused_by.append(cause_id)
                # 反向链接
                if cause_id in self._events:
                    self._events[cause_id].causes.append(event_id)
                # 创建因果边
                edge_id = f"{cause_id}:{event_id}"
                self._edges[edge_id] = CausalEdge(
                    from_event=cause_id,
                    to_event=event_id,
                    relation="triggers",
                    confidence=0.8,
                )

        # 自动推断因果边（时间相邻+同project事件）
        self._auto_infer_causal(event)

        self._events[event_id] = event
        self._timeline_index.setdefault(project, []).append(event_id)
        self._total_events += 1

        # 压缩检查
        if self._total_events > self.MAX_EVENTS:
            self._compress_old_events()

        return event

    def _auto_infer_causal(self, event: EventNode) -> None:
        """自动推断因果关系——时间相邻的同项目事件。

        启发式规则:
          - 同项目+同session → 高概率因果关系
          - error/error → 可能相关
          - bug_fix/fix → 修复关系
          - deploy/error → 部署可能引起错误
        """
        same_project = self._timeline_index.get(event.project, [])
        if len(same_project) < 2:
            return

        # 取最近3个同项目事件
        recent = []
        for eid in reversed(same_project[-10:]):
            if eid != event.id:
                recent.append(self._events.get(eid))
                if len(recent) >= 3:
                    break

        for prev in recent:
            if not prev:
                continue
            confidence = 0.3

            # 同session → +0.3
            if event.session_id and prev.session_id == event.session_id:
                confidence += 0.3

            # 类型推断
            if prev.event_type == "deploy" and event.event_type == "error":
                confidence += 0.3
                relation = "triggers"
            elif prev.event_type == "error" and event.event_type == "bug_fix":
                confidence += 0.35
                relation = "fixes"
            elif prev.event_type == "decision" and event.event_type in ("feature", "task"):
                confidence += 0.2
                relation = "triggers"
            else:
                relation = "relates_to"

            if confidence >= 0.5:
                event.caused_by.append(prev.id)
                prev.causes.append(event.id)
                edge_id = f"{prev.id}:{event.id}"
                self._edges[edge_id] = CausalEdge(
                    from_event=prev.id,
                    to_event=event.id,
                    relation=relation,
                    confidence=confidence,
                )

    # ----------------------------------------------------------
    # 事件查询
    # ----------------------------------------------------------

    def query_timeline(
        self, project: str, hours_ago: int = 24,
        limit: int = 50, event_type: str = "",
    ) -> list[dict]:
        """查询项目时间线——按时间范围。

        Args:
            project: 项目标识
            hours_ago: 最近N小时
            limit: 返回条数
            event_type: 过滤事件类型（空=不过滤）
        """
        cutoff = time.time() - hours_ago * 3600
        events = []

        for eid in self._timeline_index.get(project, []):
            event = self._events.get(eid)
            if not event or event.timestamp < cutoff:
                continue
            if event_type and event.event_type != event_type:
                continue
            events.append(event)

        events.sort(key=lambda e: -e.timestamp)
        return [
            {
                "id": e.id,
                "timestamp": e.timestamp,
                "event_type": e.event_type,
                "summary": e.summary,
                "importance": e.importance,
                "causes_count": len(e.causes),
                "caused_by_count": len(e.caused_by),
            }
            for e in events[:limit]
        ]

    def get_event(self, event_id: str) -> dict | None:
        """获取事件详情（含因果链）。"""
        event = self._events.get(event_id)
        if not event:
            return None

        return {
            "id": event.id,
            "timestamp": event.timestamp,
            "event_type": event.event_type,
            "summary": event.summary,
            "project": event.project,
            "session_id": event.session_id,
            "agent_id": event.agent_id,
            "importance": event.importance,
            "compressed": event.compressed,
            "causal_chain": {
                "caused_by": [
                    {
                        "id": eid,
                        "summary": self._events[eid].summary if eid in self._events else "(已压缩)",
                        "relation": self._edges.get(f"{eid}:{event_id}", CausalEdge(eid, event_id, "unknown")).relation,
                    }
                    for eid in event.caused_by[:5]
                ],
                "causes": [
                    {
                        "id": eid,
                        "summary": self._events[eid].summary if eid in self._events else "(已压缩)",
                        "relation": self._edges.get(f"{event_id}:{eid}", CausalEdge(event_id, eid, "unknown")).relation,
                    }
                    for eid in event.causes[:5]
                ],
            },
        }

    # ----------------------------------------------------------
    # 因果回溯
    # ----------------------------------------------------------

    def trace_root_cause(
        self, event_id: str, max_depth: int = 5,
    ) -> dict:
        """从错误事件反向追溯根因。

        沿caused_by边反向遍历，找最早的触发事件。
        """
        event = self._events.get(event_id)
        if not event:
            return {"error": "事件不存在"}

        chain = []
        visited: set[str] = set()
        queue = [(event_id, 0)]

        while queue and len(chain) < max_depth:
            current_id, depth = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            current = self._events.get(current_id)
            if not current:
                chain.append({"id": current_id, "depth": depth, "summary": "(已压缩)"})
                continue

            chain.append({
                "id": current_id,
                "depth": depth,
                "event_type": current.event_type,
                "summary": current.summary,
                "timestamp": current.timestamp,
            })

            # 寻找原因
            for cause_id in current.caused_by:
                if cause_id not in visited and depth < max_depth:
                    queue.append((cause_id, depth + 1))

        # 找最深的原因
        root = chain[-1] if chain else None
        return {
            "event_id": event_id,
            "event_type": event.event_type,
            "chain": chain,
            "root_cause": root,
            "depth": len(chain),
        }

    def trace_impact(
        self, event_id: str, max_depth: int = 5,
    ) -> dict:
        """正向追踪事件影响——从源事件沿causes边传播。"""
        event = self._events.get(event_id)
        if not event:
            return {"error": "事件不存在"}

        impacted = []
        visited: set[str] = set()
        queue = [(event_id, 0)]

        while queue and len(impacted) < max_depth:
            current_id, depth = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            current = self._events.get(current_id)
            if not current:
                impacted.append({"id": current_id, "depth": depth, "summary": "(已压缩)"})
                continue

            if depth > 0:  # 不包含自身
                impacted.append({
                    "id": current_id,
                    "depth": depth,
                    "event_type": current.event_type,
                    "summary": current.summary,
                    "timestamp": current.timestamp,
                })

            for caused_id in current.causes:
                if caused_id not in visited and depth < max_depth:
                    queue.append((caused_id, depth + 1))

        return {
            "event_id": event_id,
            "event_type": event.event_type,
            "impacted_events": impacted,
            "total_impacted": len(impacted),
        }

    # ----------------------------------------------------------
    # 压缩
    # ----------------------------------------------------------

    def _compress_old_events(self) -> None:
        """压缩超过30天的事件——保留摘要但合并为单个节点。"""
        now = time.time()
        threshold = self.COMPRESS_AFTER_DAYS * 86400

        by_project: dict[str, list[EventNode]] = {}
        for eid, event in list(self._events.items()):
            if now - event.timestamp > threshold and not event.compressed:
                by_project.setdefault(event.project, []).append(event)

        for project, events in by_project.items():
            if len(events) < 3:
                continue

            # 按类型分组压缩
            by_type: dict[str, list[EventNode]] = {}
            for e in events:
                by_type.setdefault(e.event_type, []).append(e)

            for etype, group in by_type.items():
                if len(group) < 5:
                    continue

                original_ids = [e.id for e in group]
                compressed = EventNode(
                    id=f"comp-{project}-{etype}-{int(now)}",
                    timestamp=now,
                    event_type=f"compressed_{etype}",
                    summary=f"压缩了{len(group)}个{etype}事件（{project}）",
                    project=project,
                    importance=0.3,
                    compressed=True,
                    original_ids=original_ids,
                )

                self._events[compressed.id] = compressed
                self._timeline_index.setdefault(project, []).append(compressed.id)

                # 移除原始事件（但保留在events中标记为compressed）
                for e in group:
                    e.compressed = True

                logger.info("事件压缩: %s %d个%s事件", project, len(group), etype)

    # ----------------------------------------------------------
    # 查询接口
    # ----------------------------------------------------------

    def get_project_overview(self, project: str) -> dict:
        """获取项目的时序概览。"""
        events = []
        for eid in self._timeline_index.get(project, []):
            e = self._events.get(eid)
            if e and not e.compressed:
                events.append(e)

        by_type: dict[str, int] = {}
        for e in events:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1

        return {
            "project": project,
            "total_events": len(events),
            "by_type": by_type,
            "recent_events": [
                {"id": e.id, "type": e.event_type, "summary": e.summary, "timestamp": e.timestamp}
                for e in sorted(events, key=lambda x: -x.timestamp)[:10]
            ],
        }

    def search_events(
        self, project: str = "", query: str = "", limit: int = 20,
    ) -> list[dict]:
        """搜索事件（纯文本匹配）。"""
        results = []
        query_lower = query.lower()
        for event in self._events.values():
            if project and event.project != project:
                continue
            if query and query_lower not in event.summary.lower():
                continue
            results.append({
                "id": event.id,
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "summary": event.summary,
                "importance": event.importance,
            })

        results.sort(key=lambda x: -x["timestamp"])
        return results[:limit]

    def get_stats(self) -> dict:
        return {
            "total_events": len(self._events),
            "projects": list(self._timeline_index.keys()),
            "events_by_project": {p: len(ids) for p, ids in self._timeline_index.items()},
            "compressed_events": sum(1 for e in self._events.values() if e.compressed),
            "causal_edges": len(self._edges),
        }


# ============================================================
# 全局实例
# ============================================================

time_graph = TemporalGraphEngine()
