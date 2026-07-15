"""
太极引擎 · Hermes 适配器（HermesAdapter）

使命：作为太极引擎与 Hermes Agent 之间的翻译层，
确保"你吸收的是能力语义，不是代码实现"。

关键原则：
- 太极定义接口（Interface），Hermes 作为实现（Implementation）
- Hermes API 变更时，只改适配器，不改太极核心
- 此层是阶段一建立的"抽象层"，缓解 Hermes 方向漂移风险
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ════════════════════════════════════════════════════════════════
# 概念映射：Hermes → 太极
# ════════════════════════════════════════════════════════════════

class TaiJiConcept(Enum):
    """太极引擎能力概念"""
    MEMORY_INJECTION = "memory_injection"       # 铭心：MEMORY.md → system prompt
    CONTEXT_COMPRESSION = "context_compression"  # 缩龙成寸：上下文自动压缩
    SEMANTIC_RETRIEVAL = "semantic_retrieval"    # 太虚境：语义记忆检索
    BEHAVIOR_AUDIT = "behavior_audit"            # 夜巡：行为审查
    MODEL_ROUTING = "model_routing"              # 分流调度：智能模型路由
    SKILL_CREATION = "skill_creation"             # 自化：技能自动创建
    DATA_LIFECYCLE = "data_lifecycle"             # 清风：数据生命周期
    TASK_ORCHESTRATION = "task_orchestration"    # 经纬：任务编排
    MULTI_PLATFORM = "multi_platform"            # 万川：多平台连接
    CONSCIOUSNESS = "consciousness"              # 意识：自我感知
    SELF_EVOLUTION = "self_evolution"            # 进化：递归自进化
    EMERGENCE = "emergence"                      # 涌现：跨模块协同


# Hermes Agent → 太极引擎 概念映射表
# 格式: {hermes_module_or_concept: (taiji_concept, absorption_status)}
HERMES_TO_TAIJI_MAP: dict[str, tuple[TaiJiConcept, str]] = {
    # 已完全吸收（太极原生实现）
    "memory_loader":            (TaiJiConcept.MEMORY_INJECTION, "absorbed"),
    "context_compression":      (TaiJiConcept.CONTEXT_COMPRESSION, "absorbed"),
    "semantic_search":          (TaiJiConcept.SEMANTIC_RETRIEVAL, "absorbed"),
    "behavior_audit":           (TaiJiConcept.BEHAVIOR_AUDIT, "absorbed"),

    # 部分吸收（太极实现中，Hermes 兜底）
    "auxiliary_router":         (TaiJiConcept.MODEL_ROUTING, "partial"),
    "skill_autocreate":         (TaiJiConcept.SKILL_CREATION, "partial"),
    "curator":                  (TaiJiConcept.DATA_LIFECYCLE, "partial"),

    # 继续依赖 Hermes
    "task_orchestration":       (TaiJiConcept.TASK_ORCHESTRATION, "pending"),
    "platform_gateway":         (TaiJiConcept.MULTI_PLATFORM, "pending"),

    # Hermes 无对应——太极独有能力
    "consciousness_engine":     (TaiJiConcept.CONSCIOUSNESS, "taiji_only"),
    "recursive_evolution":      (TaiJiConcept.SELF_EVOLUTION, "taiji_only"),
    "emergence_engine":         (TaiJiConcept.EMERGENCE, "taiji_only"),
}


# ════════════════════════════════════════════════════════════════
# Hermes API 版本监控
# ════════════════════════════════════════════════════════════════

@dataclass
class HermesVersion:
    """Hermes Agent 版本信息"""
    version: str = "0.17.0"
    api_revision: str = ""
    last_checked: str = ""
    breaking_changes: list[str] = field(default_factory=list)


@dataclass
class CompatibilityReport:
    """太极 ↔ Hermes 兼容性报告"""
    hermes_version: str = ""
    taiji_version: str = ""
    compatible: bool = True
    warnings: list[str] = field(default_factory=list)
    breaking_changes: list[str] = field(default_factory=list)
    required_actions: list[str] = field(default_factory=list)


# ════════════════════════════════════════════════════════════════
# 抽象接口层：太极侧定义接口
# ════════════════════════════════════════════════════════════════

class MemoryInjectionInterface:
    """铭心：记忆注入接口。

    太极定义此接口。Hermes（或任意兼容运行时）通过适配器实现。
    当前：太极原生实现（engine/memory_loader.py），不经过 Hermes。
    """
    @staticmethod
    async def load_memory_files(workspace_id: str) -> str:
        """加载 MEMORY.md 和 USER.md，返回 system prompt 片段"""
        from engine.memory_loader import memory_loader
        return await memory_loader.load(workspace_id)


class ContextCompressionInterface:
    """缩龙成寸：上下文压缩接口。"""
    @staticmethod
    async def compress(messages: list[dict], token_limit: int) -> list[dict]:
        """压缩消息列表到 token_limit 以内"""
        from services.memory.compression_engine import compress_messages
        return await compress_messages(messages, token_limit)


class SemanticRetrievalInterface:
    """太虚境：语义检索接口。"""
    @staticmethod
    async def search(query: str, workspace_id: str, top_k: int = 5) -> list[dict]:
        """语义搜索 L3 知识库"""
        from engine.taixu_core import get_taixu
        taixu = get_taixu()
        if taixu:
            return await taixu.search(query, workspace_id, top_k)
        return []


class BehaviorAuditInterface:
    """夜巡：行为审查接口。"""
    @staticmethod
    async def audit(workspace_id: str, content: str, agent_id: str = "") -> dict:
        """审查 Agent 输出"""
        from engine.night_patrol import get_patrol
        patrol = get_patrol()
        if patrol:
            return await patrol.check(workspace_id, content, agent_id)
        return {"passed": True, "flags": []}


# ════════════════════════════════════════════════════════════════
# HermesAdapter 主类
# ════════════════════════════════════════════════════════════════

class HermesAdapter:
    """
    Hermes 适配器——太极与 Hermes 之间的翻译层。

    职责：
    1. 概念映射：Hermes 术语 → 太极术语
    2. 版本兼容性检查
    3. 能力吸收状态追踪
    4. 兜底策略：太极不可用时，回退到 Hermes

    原则："不继承 Hermes，凌驾于 Hermes 之上。"
    """

    def __init__(self):
        self._hermes_version = HermesVersion()
        self._concept_map = HERMES_TO_TAIJI_MAP.copy()

    # ── 概念映射 ──

    def translate_concept(self, hermes_term: str) -> Optional[TaiJiConcept]:
        """将 Hermes 术语翻译为太极概念"""
        entry = self._concept_map.get(hermes_term)
        return entry[0] if entry else None

    def get_absorption_status(self, concept: TaiJiConcept) -> str:
        """获取指定太极概念的吸收状态"""
        for entry in self._concept_map.values():
            if entry[0] == concept:
                return entry[1]
        return "unknown"

    def list_absorbed_capabilities(self) -> list[str]:
        """列出已完全吸收的能力"""
        return [
            k for k, v in self._concept_map.items()
            if v[1] == "absorbed"
        ]

    def list_taiji_only_capabilities(self) -> list[str]:
        """列出太极独有的能力（Hermes 无对应）"""
        return [
            k for k, v in self._concept_map.items()
            if v[1] == "taiji_only"
        ]

    def list_pending_capabilities(self) -> list[str]:
        """列出仍依赖 Hermes 的能力"""
        return [
            k for k, v in self._concept_map.items()
            if v[1] in ("partial", "pending")
        ]

    # ── 兼容性检查 ──

    def check_hermes_compatibility(self, hermes_version: str) -> CompatibilityReport:
        """
        检查 Hermes 版本是否与当前太极兼容。

        返回兼容性报告。如果有 breaking changes，
        报告会列出受影响的太极概念和需要的适配动作。
        """
        report = CompatibilityReport(
            hermes_version=hermes_version,
            taiji_version="2.0",
        )

        # 基础版本检查
        self._hermes_version.version = hermes_version

        # 检查已知的 breaking changes
        # Hermes 0.18+ 预计可能变更 auxiliary 管道 API
        major = int(hermes_version.split(".")[0]) if hermes_version else 0
        minor = int(hermes_version.split(".")[1]) if "." in hermes_version else 0

        if major > 0 or (major == 0 and minor >= 18):
            report.warnings.append(
                "Hermes >= 0.18 可能变更 auxiliary 管道 API。"
                "若分流调度尚未完成吸收，需检查兼容性。"
            )

        # 检查吸收状态一致性
        absorbed = self.list_absorbed_capabilities()
        partial = self.list_pending_capabilities()

        if absorbed:
            report.warnings.append(
                f"已吸收 {len(absorbed)} 项能力不再依赖 Hermes，不受其 API 变更影响。"
            )
        if partial:
            report.warnings.append(
                f"仍有 {len(partial)} 项能力部分依赖 Hermes：{', '.join(partial)}"
            )

        return report

    # ── 能力吸收报告 ──

    def get_absorption_report(self) -> dict[str, Any]:
        """生成完整的吸收状态报告"""
        total = len(self._concept_map)
        absorbed = len(self.list_absorbed_capabilities())
        taiji_only = len(self.list_taiji_only_capabilities())
        partial = len([c for c in self.list_pending_capabilities()
                      if self._concept_map.get(c, ("", ""))[1] == "partial"])
        pending = len([c for c in self.list_pending_capabilities()
                      if self._concept_map.get(c, ("", ""))[1] == "pending"])

        return {
            "taiji_version": "v2.0 · 记忆觉醒",
            "hermes_version": self._hermes_version.version,
            "total_capabilities": total,
            "absorbed": absorbed,
            "taiji_only": taiji_only,
            "partial": partial,
            "pending": pending,
            "absorption_rate": f"{absorbed / max(total, 1):.0%}",
            "independence_score": f"{(absorbed + taiji_only) / max(total, 1):.0%}",
            "absorbed_capabilities": self.list_absorbed_capabilities(),
            "taiji_only_capabilities": self.list_taiji_only_capabilities(),
            "pending_capabilities": self.list_pending_capabilities(),
        }


# 平台唯一实例
hermes_adapter = HermesAdapter()
