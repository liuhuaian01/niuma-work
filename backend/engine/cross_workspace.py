"""
太极引擎 · 跨工作间协作（群聊）

平台三元中的"三"——Hermes(一) → Swarm+Work间(二) → 群聊(三·涌现)。
Agent 间不可直接跨工作间通信，必须经 Hermes 中转。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class CollaborationMessage:
    id: str
    from_workspace: str
    from_agent: str
    to_workspace: str
    to_agent: str
    content: str
    status: str = "pending"         # pending / delivered / responded
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CollaborationSession:
    """一个跨工作间协作会话。"""
    id: str
    workspaces: list[str]
    topic: str
    messages: list[CollaborationMessage] = field(default_factory=list)
    status: str = "active"          # active / archived
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class CrossWorkspaceHub:
    """跨工作间协作中枢——Hermes 大管家统一中转。

    工作间沙盒隔离——Agent 不可直接跨工作间通信。
    所有跨工作间消息必经 Hermes 中转和审批。
    """

    def __init__(self) -> None:
        self._sessions: dict[str, CollaborationSession] = {}
        self._message_log: list[CollaborationMessage] = []

    def create_session(self, topic: str, workspace_ids: list[str]) -> CollaborationSession:
        """创建协作会话。"""
        sid = f"collab-{uuid.uuid4().hex[:8]}"
        session = CollaborationSession(id=sid, workspaces=workspace_ids, topic=topic)
        self._sessions[sid] = session
        return session

    def send_message(
        self, session_id: str, from_ws: str, from_agent: str,
        to_ws: str, to_agent: str, content: str,
    ) -> Optional[CollaborationMessage]:
        """Agent 通过 Hermes 中转发送跨工作间消息。"""
        if session_id not in self._sessions:
            return None
        session = self._sessions[session_id]
        if from_ws not in session.workspaces or to_ws not in session.workspaces:
            return None

        msg = CollaborationMessage(
            id=f"msg-{uuid.uuid4().hex[:6]}",
            from_workspace=from_ws, from_agent=from_agent,
            to_workspace=to_ws, to_agent=to_agent,
            content=content,
        )
        session.messages.append(msg)
        self._message_log.append(msg)
        return msg

    def get_session(self, session_id: str) -> Optional[CollaborationSession]:
        return self._sessions.get(session_id)

    def list_sessions(self, workspace_id: str) -> list[CollaborationSession]:
        return [s for s in self._sessions.values() if workspace_id in s.workspaces]

    def get_stats(self) -> dict:
        return {
            "active_sessions": len([s for s in self._sessions.values() if s.status == "active"]),
            "total_messages": len(self._message_log),
            "participating_workspaces": list(set(w for s in self._sessions.values() for w in s.workspaces)),
        }
