"""
太极引擎 · 能力开关（CapabilityFlags）

天道法则——"大道五十，天衍四十九，人遁其一"

默认值：
- web_fetch  → ❌ 关闭（如非必要，绝不访问外网）
- web_search → ❌ 关闭（优先本地知识库和记忆系统）
- mcp        → ❌ 关闭（按 Agent 粒度审批）
- skills     → ✅ 开启（默认开放，使用 Hermes 技能生态）
- attachments→ ✅ 开启（图片附件开放）
- memory     → ✅ 开启（跨会话记忆开放）
- subagents  → ❌ 关闭（有 Token 预算上限）
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class FlagAction(Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


@dataclass
class CapabilityFlags:
    """平台级能力开关。每个 Agent 在工作间内可有覆盖。"""

    fetch: bool = False           # web_fetch —— 如非必要，绝不开启
    search: bool = False           # web_search —— 国产搜索引擎优先
    mcp: bool = False              # MCP 外部工具——按 Agent 审批
    skills: bool = True            # 技能调用——默认开放
    attachments: bool = True       # 图片附件——默认开放
    memory: bool = True            # 跨会话记忆——默认开放
    subagents: bool = False        # 子 Agent 委派——有 Token 预算上限

    # per-agent 覆盖（可选）
    _agent_overrides: dict[str, dict[str, bool]] = field(default_factory=dict, repr=False)

    def is_allowed(self, capability: str, agent_id: str | None = None) -> bool:
        """检查能力是否被允许。先查 agent 覆盖，再查平台默认。"""
        if agent_id and agent_id in self._agent_overrides:
            override = self._agent_overrides[agent_id].get(capability)
            if override is not None:
                return override
        return getattr(self, capability, False)

    def set_agent_override(self, agent_id: str, capability: str, value: bool) -> None:
        """为特定 Agent 设置能力覆盖。"""
        if agent_id not in self._agent_overrides:
            self._agent_overrides[agent_id] = {}
        self._agent_overrides[agent_id][capability] = value

    def clear_agent_overrides(self, agent_id: str) -> None:
        """清除 Agent 级别覆盖，恢复平台默认。任务结束后调用。"""
        self._agent_overrides.pop(agent_id, None)

    def check(self, capability: str, agent_id: str | None = None) -> FlagAction:
        """检查并返回操作建议。"""
        if self.is_allowed(capability, agent_id):
            return FlagAction.ALLOW
        if capability in ("fetch", "search"):
            return FlagAction.REQUIRE_APPROVAL
        return FlagAction.DENY


# 每个能力被拦截时给出的建议信息
CAPABILITY_ADVICES: dict[str, str] = {
    "fetch": "外网抓取默认关闭。如任务确实需要，请手动开启。本地知识库和记忆已有替代信息。",
    "search": "外网搜索默认关闭。如任务确实需要，请手动开启。",
    "mcp": "MCP 外部工具默认关闭，请先完成 Agent 审批。",
    "subagents": "子 Agent 委派默认关闭，请确认 Token 预算后再开启。",
}
