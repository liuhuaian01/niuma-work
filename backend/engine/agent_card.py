"""
太极引擎 · Agent Card — v2.0 新增

参考：A2A v1.0 Agent Card JSON Schema + NIST AI 600-1 Agent身份注册。
功能：标准化Agent能力描述、输入格式、认证方式、SLA承诺，支持自动发现。

太极哲学：以静制动——Agent的能力声明像名片，不需要运行时查询，
而是注册时一次性声明，运行时按需发现。

核心机制：
  1. 能力声明（Capabilities）— 声明Agent能做什么任务
  2. 输入/输出格式（IO Schema）— 标准化输入输出格式
  3. 认证方式（Auth Methods）— 声明支持的认证协议
  4. SLA承诺（SLA）— 推荐模型、Token预算、延迟上限
  5. 自动发现（Discovery）— 按能力/角色/项目过滤查找Agent

设计原则（铁则）：
  - 声明式：Agent Card是静态声明，不是运行时推断
  - 标准对齐：参考A2A v1.0 Agent Card + NIST身份注册
  - 可扩展：支持自定义capability tags

使用方式：
    from engine.agent_card import agent_card_registry
    card = AgentCard(
        agent_id="hermes-main",
        display_name="Hermes",
        role="director",
        capabilities=["coding", "analysis", "writing", "orchestration"],
        recommended_models=["deepseek-v4", "kimi-k2.6"],
        token_budget=50000,
        sla_max_latency_ms=30000,
    )
    await agent_card_registry.register(card)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import asyncio
import json
import logging
import os
import time

logger = logging.getLogger("niuma.agent_card")


# ============================================================
# 数据模型 — 对齐 A2A v1.0 Agent Card Schema
# ============================================================

@dataclass
class AgentCapability:
    """Agent的一项能力声明。"""
    name: str                     # 能力名称，如 "code_generation", "bug_fix"
    category: str                 # 能力类别：coding / writing / analysis / search / conversation
    proficiency: float = 0.5      # 熟练度 0-1
    description: str = ""
    supported_languages: list[str] = field(default_factory=list)  # 支持的编程/自然语言
    max_complexity: float = 0.5   # 能处理的任务复杂度上限 0-1


@dataclass
class AgentCard:
    """Agent能力名片 — A2A v1.0标准Agent Card。

    在Agent注册时一次性声明，运行时按需发现。
    """
    agent_id: str                          # 唯一标识
    display_name: str                      # 用户可见名称
    role: str                              # director/writer/editor/coder/researcher/reviewer/custom
    version: str = "1.0"                   # AgentCard版本

    # 核心能力
    capabilities: list[AgentCapability] = field(default_factory=list)
    capability_tags: list[str] = field(default_factory=list)  # 扁平化标签（快速检索）

    # 技术参数
    recommended_models: list[str] = field(default_factory=list)
    token_budget: int = 20000              # 推荐Token预算
    sla_max_latency_ms: int = 30000        # SLA最大延迟（毫秒）
    context_window: int = 128000           # 上下文窗口上限

    # 输入/输出格式
    input_formats: list[str] = field(default_factory=list)    # ["text", "code", "image"]
    output_formats: list[str] = field(default_factory=list)   # ["text", "code", "file"]

    # 认证与信任
    auth_methods: list[str] = field(default_factory=list)     # ["api_key", "token", "mTLS"]
    trust_level: float = 0.5              # 信任等级 0-1
    require_hitl: bool = False            # 是否需要人在回路（HITL）

    # 元数据
    workspace_id: str = ""
    tags: list[str] = field(default_factory=list)             # 自定义标签
    description: str = ""
    registered_at: float = field(default_factory=time.time)
    updated_at: float = 0.0
    active: bool = True                   # 是否启用

    def to_a2a_card(self) -> dict:
        """导出为A2A v1.0标准JSON格式。"""
        return {
            "agentId": self.agent_id,
            "name": self.display_name,
            "description": self.description,
            "version": self.version,
            "capabilities": {
                "native": [c.name for c in self.capabilities],
                "tags": self.capability_tags,
            },
            "skills": [
                {
                    "id": c.name,
                    "name": c.name,
                    "description": c.description,
                    "tags": [c.category],
                    "examples": [],
                }
                for c in self.capabilities
            ],
            "defaultInputModes": self.input_formats,
            "defaultOutputModes": self.output_formats,
            "authentication": {
                "schemes": self.auth_methods,
            },
            "recommendedModels": self.recommended_models,
            "sla": {
                "maxLatencyMs": self.sla_max_latency_ms,
                "tokenBudget": self.token_budget,
                "contextWindow": self.context_window,
            },
            "trust": {
                "level": self.trust_level,
                "requireHITL": self.require_hitl,
            },
        }

    def to_dict(self) -> dict:
        """轻量导出（用于API响应）。"""
        return {
            "agent_id": self.agent_id,
            "display_name": self.display_name,
            "role": self.role,
            "version": self.version,
            "capabilities": [
                {
                    "name": c.name,
                    "category": c.category,
                    "proficiency": c.proficiency,
                    "description": c.description,
                }
                for c in self.capabilities
            ],
            "capability_tags": self.capability_tags,
            "recommended_models": self.recommended_models,
            "token_budget": self.token_budget,
            "sla_max_latency_ms": self.sla_max_latency_ms,
            "context_window": self.context_window,
            "input_formats": self.input_formats,
            "output_formats": self.output_formats,
            "auth_methods": self.auth_methods,
            "trust_level": self.trust_level,
            "require_hitl": self.require_hitl,
            "workspace_id": self.workspace_id,
            "tags": self.tags,
            "description": self.description,
            "active": self.active,
            "registered_at": self.registered_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentCard:
        """从字典反序列化。"""
        caps_raw = data.pop("capabilities", [])
        capabilities = []
        for c in caps_raw:
            if isinstance(c, dict):
                capabilities.append(AgentCapability(**c))
            elif isinstance(c, AgentCapability):
                capabilities.append(c)

        card = cls(**{k: v for k, v in data.items() if k != "capabilities"})
        card.capabilities = capabilities
        return card

    @classmethod
    def from_agent_identity(cls, identity: dict, workspace_id: str = "") -> AgentCard:
        """从Agent身份注册信息生成Agent Card。"""
        role_caps = {
            "director": ["orchestration", "task_decomposition", "agent_coordination"],
            "writer": ["content_generation", "creative_writing", "editing"],
            "editor": ["review", "quality_check", "content_optimization"],
            "coder": ["code_generation", "bug_fix", "refactoring", "testing"],
            "researcher": ["web_search", "data_analysis", "report_generation"],
            "reviewer": ["code_review", "security_audit", "performance_analysis"],
            "custom": [],
        }

        role = identity.get("role", "custom")
        name = identity.get("name", identity.get("agent_id", "unknown"))
        agent_id = identity.get("agent_id", "")

        capabilities = [
            AgentCapability(
                name=cap_name,
                category=_infer_category(cap_name),
                proficiency=0.7,
                description=f"Auto-generated capability from role: {role}",
            )
            for cap_name in role_caps.get(role, [])
        ]

        return cls(
            agent_id=agent_id,
            display_name=name,
            role=role,
            capabilities=capabilities,
            capability_tags=role_caps.get(role, []),
            workspace_id=workspace_id or identity.get("workspace_id", ""),
            description=identity.get("description", f"{name} — {role}"),
            auth_methods=["token"],
            input_formats=["text"],
            output_formats=["text"],
        )


def _infer_category(cap_name: str) -> str:
    """从能力名推断类别。"""
    categories = {
        "orchestration": "coding",
        "task_decomposition": "coding",
        "agent_coordination": "coding",
        "content_generation": "writing",
        "creative_writing": "writing",
        "editing": "writing",
        "review": "analysis",
        "quality_check": "analysis",
        "content_optimization": "analysis",
        "code_generation": "coding",
        "bug_fix": "coding",
        "refactoring": "coding",
        "testing": "coding",
        "web_search": "search",
        "data_analysis": "analysis",
        "report_generation": "writing",
        "code_review": "analysis",
        "security_audit": "analysis",
        "performance_analysis": "analysis",
    }
    return categories.get(cap_name, "conversation")


# ============================================================
# Agent Card Registry — 名片注册与发现
# ============================================================

class AgentCardRegistry:
    """Agent Card注册表 — 统一管理所有Agent的能力名片。

    v2.0: 参考A2A v1.0标准，提供声明式能力发现。
    """

    DATA_DIR = "data/agent_cards"
    CACHE_TTL = 300               # 缓存有效期5分钟

    def __init__(self, data_dir: str | None = None) -> None:
        self._data_dir = data_dir or self.DATA_DIR
        self._cards: dict[str, AgentCard] = {}           # agent_id → AgentCard
        self._by_role: dict[str, set[str]] = {}          # role → set of agent_ids
        self._by_capability: dict[str, set[str]] = {}    # capability_tag → set of agent_ids
        self._by_workspace: dict[str, set[str]] = {}     # workspace_id → set of agent_ids
        self._cache: dict[str, tuple[float, list[dict]]] = {}  # query → (expires_at, results)
        self._is_initialized = False

    # ----------------------------------------------------------
    # 初始化
    # ----------------------------------------------------------

    async def initialize(self) -> None:
        """从持久化恢复Agent Card。"""
        os.makedirs(self._data_dir, exist_ok=True)
        cards_dir = os.path.join(self._data_dir, "cards")
        os.makedirs(cards_dir, exist_ok=True)

        try:
            for fname in os.listdir(cards_dir):
                if fname.endswith(".json"):
                    filepath = os.path.join(cards_dir, fname)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        card = AgentCard.from_dict(data)
                        self._cards[card.agent_id] = card
                        self._update_indices(card)
                    except Exception:
                        logger.debug(f"Agent Card文件损坏: {fname}", exc_info=True)

            logger.info(f"Agent Card注册表恢复: {len(self._cards)}个Agent")
        except Exception:
            logger.warning("Agent Card目录读取失败", exc_info=True)

        self._is_initialized = True

    def _update_indices(self, card: AgentCard) -> None:
        """更新角色/能力/工作间索引。"""
        self._by_role.setdefault(card.role, set()).add(card.agent_id)
        for tag in card.capability_tags:
            self._by_capability.setdefault(tag, set()).add(card.agent_id)
        if card.workspace_id:
            self._by_workspace.setdefault(card.workspace_id, set()).add(card.agent_id)

    def _remove_indices(self, card: AgentCard) -> None:
        """移除索引。"""
        self._by_role.get(card.role, set()).discard(card.agent_id)
        for tag in card.capability_tags:
            self._by_capability.get(tag, set()).discard(card.agent_id)
        self._by_workspace.get(card.workspace_id, set()).discard(card.agent_id)

    async def _save_card(self, card: AgentCard) -> None:
        """持久化单个Agent Card。"""
        cards_dir = os.path.join(self._data_dir, "cards")
        os.makedirs(cards_dir, exist_ok=True)
        filepath = os.path.join(cards_dir, f"{card.agent_id}.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(card.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception:
            logger.debug(f"Agent Card持久化失败: {card.agent_id}", exc_info=True)

    # ----------------------------------------------------------
    # 注册/更新/注销
    # ----------------------------------------------------------

    async def register(self, card: AgentCard) -> AgentCard:
        """注册或更新一个Agent Card。"""
        card.updated_at = time.time()

        # 如果已存在，先移除旧索引
        old = self._cards.get(card.agent_id)
        if old:
            self._remove_indices(old)

        self._cards[card.agent_id] = card
        self._update_indices(card)
        self._invalidate_cache()

        # 持久化
        asyncio.ensure_future(self._save_card(card))

        logger.info(
            "Agent Card注册: %s (%s, %d个能力)",
            card.agent_id, card.role, len(card.capabilities),
        )
        return card

    async def unregister(self, agent_id: str) -> bool:
        """注销Agent Card。"""
        card = self._cards.pop(agent_id, None)
        if not card:
            return False

        self._remove_indices(card)
        self._invalidate_cache()

        # 删除持久化文件
        cards_dir = os.path.join(self._data_dir, "cards")
        filepath = os.path.join(cards_dir, f"{agent_id}.json")
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass

        logger.info("Agent Card注销: %s", agent_id)
        return True

    # ----------------------------------------------------------
    # 发现（核心检索）
    # ----------------------------------------------------------

    def _invalidate_cache(self) -> None:
        """清除过期缓存。"""
        now = time.time()
        self._cache = {
            k: v for k, v in self._cache.items()
            if v[0] > now
        }

    async def discover(
        self,
        role: str = "",
        capability: str = "",
        workspace_id: str = "",
        tags: list[str] | None = None,
        trust_level_min: float = 0.0,
        active_only: bool = True,
        limit: int = 20,
    ) -> list[dict]:
        """按条件发现Agent。

        支持多维度过滤：角色、能力标签、工作间、自定义标签、信任等级。
        """
        self._invalidate_cache()

        # 候选集
        candidates: set[str] = set(self._cards.keys())

        if role:
            candidates &= self._by_role.get(role, set())
        if capability:
            candidates &= self._by_capability.get(capability, set())
        if workspace_id:
            candidates &= self._by_workspace.get(workspace_id, set())

        # 过滤
        results = []
        for agent_id in candidates:
            card = self._cards.get(agent_id)
            if not card:
                continue
            if active_only and not card.active:
                continue
            if card.trust_level < trust_level_min:
                continue
            if tags:
                if not any(t in card.tags for t in tags):
                    continue

            results.append(card.to_dict())

        # 按信任等级 + 能力数排序
        results.sort(key=lambda c: (
            -c["trust_level"],
            -len(c.get("capabilities", [])),
        ))

        return results[:limit]

    async def find_by_capability(
        self, capability: str, limit: int = 10
    ) -> list[dict]:
        """按能力标签快速查找Agent。"""
        return await self.discover(capability=capability, limit=limit)

    async def find_by_role(
        self, role: str, limit: int = 10
    ) -> list[dict]:
        """按角色查找Agent。"""
        return await self.discover(role=role, limit=limit)

    async def get_a2a_card(self, agent_id: str) -> dict | None:
        """获取A2A v1.0标准格式的Agent Card。"""
        card = self._cards.get(agent_id)
        return card.to_a2a_card() if card and card.active else None

    async def get_card(self, agent_id: str) -> dict | None:
        """获取Agent Card详情。"""
        card = self._cards.get(agent_id)
        return card.to_dict() if card else None

    async def list_all(self) -> list[dict]:
        """列出所有Agent Card。"""
        return [card.to_dict() for card in self._cards.values()]

    # ----------------------------------------------------------
    # 能力匹配（用于任务路由）
    # ----------------------------------------------------------

    async def match_agent_for_task(
        self,
        task_type: str,
        required_capabilities: list[str] | None = None,
        min_trust: float = 0.0,
    ) -> list[dict]:
        """为指定任务类型匹配最合适的Agent。

        在DynamicBalancer / SwarmOrchestrator中调用，
        替代硬编码的Agent路由表。
        """
        candidates = await self.discover(
            capability=task_type,
            trust_level_min=min_trust,
            active_only=True,
        )

        if required_capabilities:
            # 按所需能力数量排序（越多匹配越好）
            candidates.sort(
                key=lambda c: len(
                    set(required_capabilities) & set(c.get("capability_tags", []))
                ),
                reverse=True,
            )

        return candidates

    # ----------------------------------------------------------
    # 查询接口
    # ----------------------------------------------------------

    def get_stats(self) -> dict:
        """获取注册表统计。"""
        active = sum(1 for c in self._cards.values() if c.active)
        return {
            "total_cards": len(self._cards),
            "active_cards": active,
            "by_role": {r: len(ids) for r, ids in self._by_role.items()},
            "by_capability": {
                cap: len(ids)
                for cap, ids in sorted(
                    self._by_capability.items(),
                    key=lambda x: -len(x[1]),
                )[:20]
            },
            "top_capabilities": sorted(
                self._by_capability.items(),
                key=lambda x: -len(x[1]),
            )[:10],
        }

    def list_capabilities(self) -> list[str]:
        """列出所有已知能力标签。"""
        return sorted(self._by_capability.keys())

    def list_roles(self) -> list[str]:
        """列出所有已知角色。"""
        return sorted(self._by_role.keys())


# ============================================================
# 全局实例
# ============================================================

agent_card_registry = AgentCardRegistry()
