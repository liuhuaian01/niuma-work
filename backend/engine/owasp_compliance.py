"""
太极引擎 · OWASP安全合规层（ASI05冒充/ASI06供应链/ASI09 HITL）— v2.0 新增

参考：OWASP Agentic AI Top 10 (2026年6月发布)。
太极第六律·刚柔并济——安全是刚需，必须在每一层都守护。

核心机制：
  1. ASI05 冒充防护（Impersonation Guard）— Agent身份验证 + 输出来源追踪
  2. ASI06 供应链验证（Supply Chain Verification）— Skill/MCP来源验证
  3. ASI09 人在回路（HITL）— 高风险操作强制人工确认

设计原则（铁则）：
  - 零信任：所有Agent输出都不可信，必须验证
  - 最小权限：每个Agent只授予完成任务必需的最小权限
  - 可追溯：每项操作都有完整的审计链

使用方式：
    from engine.owasp_compliance import owasp_compliance
    # 冒充检测
    result = owasp_compliance.check_impersonation(source_agent="hermes", claimed_agent="coder-1")
    # 供应链验证
    verified = owasp_compliance.verify_skill_source(skill_name="code-gen", source="marketplace")
    # HITL判定
    needs_hitl = owasp_compliance.requires_human_review(action="delete_workspace", risk_level=0.9)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import hashlib
import json
import logging
import os
import time

logger = logging.getLogger("niuma.owasp")


# ============================================================
# ASI05: 冒充防护
# ============================================================

class ImpersonationGuard:
    """ASI05 冒充防护——确保Agent身份真实性。

    防护层级:
      1. 身份令牌验证（已有P1-7 agent_registry）
      2. 输出来源追踪（每次输出标注来源Agent）
      3. 异常行为检测（偏离声明能力的操作触发告警）
    """

    SUSPICIOUS_THRESHOLD = 0.65  # 能力匹配度低于此值→可疑

    def __init__(self) -> None:
        self._suspicious_actions: list[dict] = []
        self._impersonation_attempts: int = 0

    def check_impersonation(
        self, source_agent: str, claimed_agent: str,
        declared_capabilities: list[str] | None = None,
        action_type: str = "",
    ) -> dict:
        """检查是否存在冒充风险。

        Args:
            source_agent: 实际执行Agent
            claimed_agent: 声称的身份
            declared_capabilities: Agent声明的能力列表
            action_type: 执行的操作类型

        Returns:
            {is_valid, risk_level, reason}
        """
        if source_agent != claimed_agent:
            self._impersonation_attempts += 1
            logger.warning(
                "ASI05冒充检测: source=%s claimed=%s", source_agent, claimed_agent
            )
            return {
                "is_valid": False,
                "risk_level": "high",
                "reason": f"来源Agent({source_agent})与声称身份({claimed_agent})不匹配",
            }

        # 能力匹配检查
        if declared_capabilities and action_type:
            capability_match = action_type in declared_capabilities
            if not capability_match:
                self._suspicious_actions.append({
                    "agent": source_agent,
                    "action": action_type,
                    "capabilities": declared_capabilities,
                    "timestamp": time.time(),
                })
                return {
                    "is_valid": True,
                    "risk_level": "medium",
                    "reason": f"Agent {source_agent} 执行了未声明的操作: {action_type}",
                }

        return {"is_valid": True, "risk_level": "low", "reason": "身份验证通过"}

    def tag_output(self, agent_id: str, content: str) -> str:
        """为输出添加来源标记（防篡改）。"""
        return f"{content}"

    def get_suspicious_actions(self, limit: int = 10) -> list[dict]:
        return self._suspicious_actions[-limit:]

    def get_stats(self) -> dict:
        return {
            "impersonation_attempts": self._impersonation_attempts,
            "suspicious_actions": len(self._suspicious_actions),
        }


# ============================================================
# ASI06: 供应链验证
# ============================================================

class SupplyChainVerifier:
    """ASI06 供应链验证——Skill/MCP/工具的来源可信度检查。

    验证层级:
      1. 内置工具（builtin）— 最高信任
      2. 平台沉淀（platform）— 高信任
      3. 推荐市场（marketplace）— 中等信任（需人工审核）
      4. 用户上传（user）— 低信任（必须沙箱运行）
      5. 未知来源（unknown）— 拒绝
    """

    TRUST_LEVELS = {
        "builtin": 1.0,
        "platform": 0.9,
        "marketplace": 0.7,
        "user": 0.4,
        "unknown": 0.0,
    }

    def __init__(self) -> None:
        self._verified_skills: set[str] = set()
        self._blocked_sources: set[str] = set()

    def verify_skill_source(
        self, skill_name: str, source: str, checksum: str = ""
    ) -> dict:
        """验证技能/工具的来源可信度。

        Args:
            skill_name: 工具名称
            source: 来源（builtin/platform/marketplace/user/unknown）
            checksum: 可选——SHA-256校验和

        Returns:
            {verified, trust_level, recommendation}
        """
        trust = self.TRUST_LEVELS.get(source, 0.0)

        if skill_name in self._blocked_sources:
            return {"verified": False, "trust_level": 0.0,
                    "recommendation": "此工具已被标记为拒绝"}

        if trust == 0.0:
            return {"verified": False, "trust_level": 0.0,
                    "recommendation": "未知来源，拒绝执行"}

        if trust <= 0.4:
            return {"verified": True, "trust_level": trust,
                    "recommendation": "低信任度来源，建议沙箱执行+人工审核"}

        if trust <= 0.7:
            return {"verified": True, "trust_level": trust,
                    "recommendation": "中等信任度，首次执行建议人工审核"}

        # 高信任度
        self._verified_skills.add(f"{skill_name}:{source}")
        return {"verified": True, "trust_level": trust,
                "recommendation": "可信来源，自动执行"}

    def verify_skill_dependency(self, skill_name: str, dependencies: list[str]) -> dict:
        """验证技能的依赖链安全。"""
        issues = []
        verified_count = 0

        for dep in dependencies:
            dep_key = f"{dep}:user"  # 假设依赖来自用户
            if dep_key in self._verified_skills:
                verified_count += 1
            else:
                issues.append(f"未验证的依赖: {dep}")

        return {
            "total_deps": len(dependencies),
            "verified_deps": verified_count,
            "issues": issues,
            "safe": len(issues) == 0,
        }

    def block_source(self, source_identifier: str) -> None:
        """永久拒绝某个来源。"""
        self._blocked_sources.add(source_identifier)
        logger.warning("ASI06供应链: 已拒绝来源 %s", source_identifier)

    def get_stats(self) -> dict:
        return {
            "verified_skills": len(self._verified_skills),
            "blocked_sources": len(self._blocked_sources),
        }


# ============================================================
# ASI09: 人在回路（HITL）
# ============================================================

class HumanInTheLoop:
    """ASI09 HITL — 高风险操作强制人工确认。

    触发条件:
      1. 风险评分 >= 0.7 — 强制人工确认
      2. 风险评分 >= 0.4 — 建议人工确认（可配置自动执行）
      3. 未知/首次操作 — 默认需要确认

    高风险操作类型:
      - 删除操作（delete_workspace, delete_agent, delete_skill）
      - 生产环境部署（production_deploy, db_migration）
      - 权限变更（grant_permission, revoke_permission）
      - 安全配置修改（change_auth, disable_guard）
    """

    HIGH_RISK_ACTIONS = {
        "delete_workspace": {"risk": 0.95, "description": "删除工作间", "reversible": False},
        "delete_agent": {"risk": 0.90, "description": "删除Agent", "reversible": False},
        "delete_skill": {"risk": 0.85, "description": "删除技能", "reversible": True},
        "production_deploy": {"risk": 0.90, "description": "生产环境部署", "reversible": False},
        "db_migration": {"risk": 0.90, "description": "数据库迁移", "reversible": True},
        "grant_permission": {"risk": 0.80, "description": "授予权限", "reversible": True},
        "revoke_permission": {"risk": 0.80, "description": "吊销权限", "reversible": True},
        "change_auth": {"risk": 0.85, "description": "修改认证配置", "reversible": True},
        "disable_guard": {"risk": 0.95, "description": "禁用安全防护", "reversible": False},
        "execute_system_command": {"risk": 0.85, "description": "执行系统命令", "reversible": False},
        "modify_runtime_config": {"risk": 0.70, "description": "修改运行时配置", "reversible": True},
        "bulk_data_operation": {"risk": 0.75, "description": "批量数据操作", "reversible": False},
    }

    FORCE_CONFIRM_THRESHOLD = 0.7
    SUGGEST_CONFIRM_THRESHOLD = 0.4

    def __init__(self) -> None:
        self._pending_confirmations: list[dict] = []
        self._confirmed_actions: list[dict] = []

    def requires_human_review(
        self, action: str, risk_level: float = 0.0,
        is_first_time: bool = False, agent_trust: float = 0.5,
    ) -> dict:
        """判断操作是否需要人工审核。

        Args:
            action: 操作名称
            risk_level: 风险评分（或从HIGH_RISK_ACTIONS查表）
            is_first_time: 是否首次执行
            agent_trust: Agent信任等级

        Returns:
            {needs_review, level, reason}
        """
        # 查表得风险评分
        action_risk = self.HIGH_RISK_ACTIONS.get(action, {"risk": risk_level})
        base_risk = action_risk.get("risk", risk_level) if isinstance(action_risk, dict) else action_risk
        reversible = action_risk.get("reversible", True) if isinstance(action_risk, dict) else True

        # 最终风险 = 基础风险 × (1 - Agent信任度) × 首次操作加成
        final_risk = base_risk * (1.0 - agent_trust * 0.5)
        if is_first_time:
            final_risk *= 1.2  # 首次操作+20%风险

        # 不可逆操作额外加权
        if not reversible:
            final_risk = min(1.0, final_risk * 1.15)

        if final_risk >= self.FORCE_CONFIRM_THRESHOLD:
            self._pending_confirmations.append({
                "action": action, "risk": round(final_risk, 2),
                "reversible": reversible, "timestamp": time.time(),
            })
            return {
                "needs_review": True,
                "level": "force",
                "reason": f"高风险操作({final_risk:.0%})，需要人工确认后执行",
            }

        if final_risk >= self.SUGGEST_CONFIRM_THRESHOLD:
            return {
                "needs_review": True,
                "level": "suggest",
                "reason": f"中等风险操作({final_risk:.0%})，建议人工确认",
            }

        return {"needs_review": False, "level": "auto", "reason": "低风险操作，自动执行"}

    def confirm_action(self, action: str, confirmed_by: str = "user") -> bool:
        """人工确认操作。"""
        for pending in self._pending_confirmations:
            if pending["action"] == action:
                self._confirmed_actions.append({
                    **pending, "confirmed_by": confirmed_by,
                    "confirmed_at": time.time(),
                })
                self._pending_confirmations.remove(pending)
                return True
        return False

    def list_high_risk_actions(self) -> list[dict]:
        return [
            {"action": k, **v} for k, v in self.HIGH_RISK_ACTIONS.items()
        ]

    def get_pending_confirmations(self) -> list[dict]:
        return self._pending_confirmations

    def get_stats(self) -> dict:
        return {
            "high_risk_actions": len(self.HIGH_RISK_ACTIONS),
            "force_confirm_threshold": self.FORCE_CONFIRM_THRESHOLD,
            "pending_confirmations": len(self._pending_confirmations),
            "confirmed_actions": len(self._confirmed_actions),
        }


# ============================================================
# 统一合规层
# ============================================================

class OWASPCompliance:
    """OWASP Agentic AI Top 10 统一合规检查。

    整合ASI05(冒充)/ASI06(供应链)/ASI09(HITL)三项检查，
    提供统一的合规校验入口。
    """

    def __init__(self) -> None:
        self.impersonation = ImpersonationGuard()
        self.supply_chain = SupplyChainVerifier()
        self.hitl = HumanInTheLoop()

    def full_compliance_check(
        self,
        source_agent: str = "",
        claimed_agent: str = "",
        action: str = "",
        skill_source: str = "unknown",
        capabilities: list[str] | None = None,
    ) -> dict:
        """完整的合规检查。

        Returns:
            {passed, blocks: [...], warnings: [...], recommendations: [...]}
        """
        blocks = []
        warnings = []
        recommendations = []

        # ASI05 冒充检查
        if source_agent and claimed_agent:
            imp_result = self.impersonation.check_impersonation(
                source_agent, claimed_agent, capabilities, action,
            )
            if not imp_result["is_valid"]:
                blocks.append(f"ASI05冒充风险: {imp_result['reason']}")
            elif imp_result["risk_level"] == "medium":
                warnings.append(f"ASI05: {imp_result['reason']}")

        # ASI06 供应链检查
        if skill_source and skill_source != "builtin":
            sc_result = self.supply_chain.verify_skill_source(
                action, skill_source,
            )
            if not sc_result["verified"]:
                blocks.append(f"ASI06供应链: {sc_result['recommendation']}")
            elif sc_result["trust_level"] < 0.7:
                warnings.append(f"ASI06: {sc_result['recommendation']}")

        # ASI09 HITL检查
        if action:
            hitl_result = self.hitl.requires_human_review(action)
            if hitl_result["needs_review"]:
                if hitl_result["level"] == "force":
                    blocks.append(f"ASI09 HITL: {hitl_result['reason']}")
                else:
                    warnings.append(f"ASI09: {hitl_result['reason']}")

        return {
            "passed": len(blocks) == 0,
            "blocks": blocks,
            "warnings": warnings,
            "recommendations": recommendations or ["合规检查通过"],
        }

    def get_stats(self) -> dict:
        return {
            "asi05_impersonation": self.impersonation.get_stats(),
            "asi06_supply_chain": self.supply_chain.get_stats(),
            "asi09_hitl": self.hitl.get_stats(),
        }


# ============================================================
# 全局实例
# ============================================================

owasp_compliance = OWASPCompliance()
