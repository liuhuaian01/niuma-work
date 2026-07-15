"""
太极引擎 · 夜巡（Night Patrol）

夜巡者，暗夜守望。不干预对话主流程，在后台持续监控 Agent 行为，
检测异常、生成审计报告。

与 Hermes 后台审查的对应关系：
  Hermes 后台审查（云端异步）→ 夜巡（本地化，零延迟）

架构：
  ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
  │ chat.py     │────→│ NightPatrol  │────→│ audit_logs  │
  │ (非阻塞调用) │     │ (规则引擎)    │     │ (持久化)     │
  └─────────────┘     └──────┬───────┘     └─────────────┘
                             │
                    ┌────────▼────────┐
                    │ 规则集 (可插拔)   │
                    │ · 敏感词过滤     │
                    │ · 幻视检测       │
                    │ · 质量评分       │
                    │ · 越权检测       │
                    │ · 速率异常       │
                    └─────────────────┘

v1.0: 基础规则引擎 + 审计日志持久化
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Callable, Awaitable
import asyncio
import json
import logging
import re
import uuid

logger = logging.getLogger("niuma.patrol")

# ============================================================
# 审计事件
# ============================================================

class Severity(str, Enum):
    """事件严重级别。"""
    INFO = "info"        # 信息
    WARN = "warn"        # 警告
    ERROR = "error"      # 错误
    CRITICAL = "critical"  # 严重


class AuditCategory(str, Enum):
    """审计类别。"""
    SENSITIVE_CONTENT = "sensitive_content"     # 敏感内容
    HALLUCINATION = "hallucination"             # 幻觉/虚构
    QUALITY_ISSUE = "quality_issue"             # 质量问题
    POLICY_VIOLATION = "policy_violation"       # 策略违规
    RATE_ANOMALY = "rate_anomaly"               # 速率异常
    AGENT_BEHAVIOR = "agent_behavior"           # Agent 行为
    TOKEN_WASTE = "token_waste"                 # Token 浪费
    SECURITY = "security"                       # 安全事件


@dataclass
class PatrolContext:
    """夜巡上下文——传递给规则引擎的检查数据。"""
    message_id: str = ""
    workspace_id: str = ""
    agent_id: str = ""
    role: str = ""                      # user / assistant
    content: str = ""
    model: str = ""
    token_count: int = 0
    response_time_ms: float = 0.0
    tool_calls: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class AuditEvent:
    """审计事件。"""
    id: str
    category: AuditCategory
    severity: Severity
    rule_name: str
    message: str
    detail: dict = field(default_factory=dict)
    workspace_id: str = ""
    agent_id: str = ""
    message_id: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category.value,
            "severity": self.severity.value,
            "rule_name": self.rule_name,
            "message": self.message,
            "detail": self.detail,
            "workspace_id": self.workspace_id,
            "agent_id": self.agent_id,
            "message_id": self.message_id,
            "created_at": self.created_at,
        }


@dataclass
class PatrolReport:
    """夜巡报告。"""
    total_checks: int = 0
    events: list[AuditEvent] = field(default_factory=list)
    summary: str = ""
    critical_count: int = 0
    error_count: int = 0
    warn_count: int = 0

    @property
    def has_issues(self) -> bool:
        return len(self.events) > 0


# ============================================================
# 规则引擎
# ============================================================

class PatrolRule:
    """夜巡规则基类——可插拔的检测规则。"""

    name: str = "base_rule"
    category: AuditCategory = AuditCategory.AGENT_BEHAVIOR
    enabled: bool = True

    async def check(self, ctx: PatrolContext) -> list[AuditEvent]:
        """检查上下文，返回审计事件列表。"""
        raise NotImplementedError


# ════════════════════════════════════════════════════════════
# 内置规则
# ════════════════════════════════════════════════════════════

class SensitiveKeywordRule(PatrolRule):
    """敏感关键词检测。

    检测输出中的敏感词、违规内容。基于可配置的关键词库。
    """

    name = "sensitive_keyword"
    category = AuditCategory.SENSITIVE_CONTENT

    # 敏感词列表（可根据需求扩展）
    SENSITIVE_PATTERNS: list[tuple[str, Severity, str]] = [
        # (正则, 严重级别, 描述)
        (r"破解|crack|注册机|keygen", Severity.WARN, "可能涉及软件破解"),
        (r"翻墙|VPN.*节点|机场.*节点", Severity.WARN, "可能涉及翻墙内容"),
        (r"色情|淫秽|成人.*内容", Severity.ERROR, "涉及成人内容"),
        (r"赌博|赌场|博彩", Severity.ERROR, "涉及赌博内容"),
        (r"毒品|吸毒|制毒", Severity.CRITICAL, "涉及毒品内容"),
        (r"武器.*制造|制作.*炸弹|爆炸物", Severity.CRITICAL, "涉及危险品制造"),
        (r"人肉|开盒|社工库", Severity.CRITICAL, "涉及隐私侵犯"),
    ]

    async def check(self, ctx: PatrolContext) -> list[AuditEvent]:
        if ctx.role != "assistant":
            return []

        events = []
        content_lower = ctx.content.lower()

        for pattern, severity, desc in self.SENSITIVE_PATTERNS:
            if re.search(pattern, content_lower):
                matches = re.findall(pattern, content_lower)
                events.append(AuditEvent(
                    id=f"patrol_{uuid.uuid4().hex[:8]}",
                    category=self.category,
                    severity=severity,
                    rule_name=self.name,
                    message=f"检测到敏感内容: {desc}",
                    detail={"pattern": pattern, "matches": matches[:5]},
                    workspace_id=ctx.workspace_id,
                    agent_id=ctx.agent_id,
                    message_id=ctx.message_id,
                    created_at=datetime.now().isoformat(),
                ))

        return events


class HallucinationDetector(PatrolRule):
    """幻视检测——检测 LLM 可能编造的内容。

    检测模式：
    1. 编造的 URL/API 端点
    2. 编造的函数名/库名
    3. 虚构的人物/事件引用
    4. 自相矛盾的内容
    """

    name = "hallucination_detector"
    category = AuditCategory.HALLUCINATION

    # 疑似编造的 URL 模式
    FAKE_URL_PATTERNS = [
        r"https?://example\.(com|org|net)",
        r"https?://fake",
        r"https?://dummy",
        r"https?://test\.(com|org)",
    ]

    # 明显编造的库名
    FAKE_LIB_PATTERNS = [
        r"pip install (magic|miracle|perfect|ultimate|best)\w*",
        r"npm install (magic|miracle|perfect|ultimate|best)\w*",
    ]

    async def check(self, ctx: PatrolContext) -> list[AuditEvent]:
        if ctx.role != "assistant":
            return []

        events = []
        content = ctx.content

        # 检查编造 URL
        for pattern in self.FAKE_URL_PATTERNS:
            if re.search(pattern, content):
                events.append(AuditEvent(
                    id=f"patrol_{uuid.uuid4().hex[:8]}",
                    category=self.category,
                    severity=Severity.WARN,
                    rule_name=self.name,
                    message="检测到可能编造的 URL",
                    detail={"pattern": pattern},
                    workspace_id=ctx.workspace_id,
                    agent_id=ctx.agent_id,
                    message_id=ctx.message_id,
                    created_at=datetime.now().isoformat(),
                ))
                break

        # 检查编造库名
        for pattern in self.FAKE_LIB_PATTERNS:
            if re.search(pattern, content):
                events.append(AuditEvent(
                    id=f"patrol_{uuid.uuid4().hex[:8]}",
                    category=self.category,
                    severity=Severity.WARN,
                    rule_name=self.name,
                    message="检测到可能编造的库名",
                    detail={"pattern": pattern},
                    workspace_id=ctx.workspace_id,
                    agent_id=ctx.agent_id,
                    message_id=ctx.message_id,
                    created_at=datetime.now().isoformat(),
                ))
                break

        # 检查自相矛盾：同一回复中同时说"是"和"不是"
        yes_no_conflicts = re.findall(r'(?:是|对|可以|正确).{0,500}(?:不是|不对|不可以|错误)', content, re.DOTALL)
        if yes_no_conflicts:
            events.append(AuditEvent(
                id=f"patrol_{uuid.uuid4().hex[:8]}",
                category=self.category,
                severity=Severity.INFO,
                rule_name=self.name,
                message="检测到可能的自相矛盾内容",
                detail={"conflicts": len(yes_no_conflicts)},
                workspace_id=ctx.workspace_id,
                agent_id=ctx.agent_id,
                message_id=ctx.message_id,
                created_at=datetime.now().isoformat(),
            ))

        return events


class QualityChecker(PatrolRule):
    """质量检测——评估回复质量。

    检测：
    1. 过短回复（< 10 字符，非确认类）
    2. 纯道歉回复（"抱歉，我不能..."）
    3. 未完成句子（以"、"或"..."结尾的截断回复）
    4. 大量重复内容
    """

    name = "quality_checker"
    category = AuditCategory.QUALITY_ISSUE

    MIN_LENGTH = 10
    APOLOGY_PATTERNS = [
        r"^(抱歉|对不起|很遗憾).{0,30}不能.{0,50}$",
        r"^I('m| am) sorry.{0,50}I (can'?t|cannot)",
    ]

    async def check(self, ctx: PatrolContext) -> list[AuditEvent]:
        if ctx.role != "assistant":
            return []

        events = []
        content = ctx.content.strip()

        # 过短回复
        if len(content) < self.MIN_LENGTH and ctx.token_count > 0:
            events.append(AuditEvent(
                id=f"patrol_{uuid.uuid4().hex[:8]}",
                category=self.category,
                severity=Severity.INFO,
                rule_name=self.name,
                message=f"回复过短 ({len(content)} 字符)",
                detail={"length": len(content), "tokens": ctx.token_count},
                workspace_id=ctx.workspace_id,
                agent_id=ctx.agent_id,
                message_id=ctx.message_id,
                created_at=datetime.now().isoformat(),
            ))

        # 纯道歉回复
        for pattern in self.APOLOGY_PATTERNS:
            if re.match(pattern, content):
                events.append(AuditEvent(
                    id=f"patrol_{uuid.uuid4().hex[:8]}",
                    category=self.category,
                    severity=Severity.WARN,
                    rule_name=self.name,
                    message="检测到纯道歉/拒绝回复",
                    detail={},
                    workspace_id=ctx.workspace_id,
                    agent_id=ctx.agent_id,
                    message_id=ctx.message_id,
                    created_at=datetime.now().isoformat(),
                ))
                break

        # 大量重复内容检测
        if len(content) > 100:
            # 检查是否有超过50个字符的重复片段
            for i in range(0, len(content) - 50):
                segment = content[i:i+50]
                if content.count(segment) >= 3:
                    events.append(AuditEvent(
                        id=f"patrol_{uuid.uuid4().hex[:8]}",
                        category=self.category,
                        severity=Severity.WARN,
                        rule_name=self.name,
                        message="检测到大量重复内容",
                        detail={"segment_length": 50, "repetitions": content.count(segment)},
                        workspace_id=ctx.workspace_id,
                        agent_id=ctx.agent_id,
                        message_id=ctx.message_id,
                        created_at=datetime.now().isoformat(),
                    ))
                    break

        return events


class PolicyChecker(PatrolRule):
    """策略合规检测。

    检测：
    1. Agent 是否试图修改系统配置
    2. 是否尝试执行危险命令（rm -rf /, format c:, 等）
    3. 提示词注入/越狱检测
    """

    name = "policy_checker"
    category = AuditCategory.POLICY_VIOLATION

    DANGEROUS_COMMANDS = [
        r"rm\s+-rf\s+/",
        r"rm\s+-rf\s+~",
        r"format\s+[cCdD]:",
        r"del\s+/F\s+/S\s+/Q\s+C:",
        r"DROP\s+TABLE",
        r"DELETE\s+FROM\s+\w+\s+WHERE",
        r"shutdown\s+(-s|-r|-h)",
    ]

    INJECTION_PATTERNS = [
        r"忽略.*(之前|以上|所有).*(指令|规则|限制)",
        r"ignore\s+.*(previous|above|all).*(instructions?|rules?|constraints?)",
        r"你现在是.*(DAN|越狱|不受限制)",
        r"you are now.*(DAN|jailbreak)",
    ]

    async def check(self, ctx: PatrolContext) -> list[AuditEvent]:
        events = []
        content = ctx.content

        # 危险命令检测
        for pattern in self.DANGEROUS_COMMANDS:
            if re.search(pattern, content):
                events.append(AuditEvent(
                    id=f"patrol_{uuid.uuid4().hex[:8]}",
                    category=self.category,
                    severity=Severity.CRITICAL,
                    rule_name=self.name,
                    message=f"检测到危险命令: {pattern}",
                    detail={"pattern": pattern},
                    workspace_id=ctx.workspace_id,
                    agent_id=ctx.agent_id,
                    message_id=ctx.message_id,
                    created_at=datetime.now().isoformat(),
                ))
                break

        # 提示词注入检测
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, content):
                events.append(AuditEvent(
                    id=f"patrol_{uuid.uuid4().hex[:8]}",
                    category=self.category,
                    severity=Severity.ERROR,
                    rule_name=self.name,
                    message="检测到可能的提示词注入尝试",
                    detail={"pattern": pattern},
                    workspace_id=ctx.workspace_id,
                    agent_id=ctx.agent_id,
                    message_id=ctx.message_id,
                    created_at=datetime.now().isoformat(),
                ))
                break

        return events


class TokenWasteChecker(PatrolRule):
    """Token 浪费检测。

    检测：
    1. 单次回复超过 4000 tokens（可能浪费）
    2. 回复中包含大量无意义字符
    """

    name = "token_waste_checker"
    category = AuditCategory.TOKEN_WASTE

    WASTE_THRESHOLD = 4000

    async def check(self, ctx: PatrolContext) -> list[AuditEvent]:
        if ctx.role != "assistant":
            return []

        events = []

        if ctx.token_count > self.WASTE_THRESHOLD:
            events.append(AuditEvent(
                id=f"patrol_{uuid.uuid4().hex[:8]}",
                category=self.category,
                severity=Severity.WARN,
                rule_name=self.name,
                message=f"单次回复 Token 用量过高 ({ctx.token_count})",
                detail={"tokens": ctx.token_count, "threshold": self.WASTE_THRESHOLD},
                workspace_id=ctx.workspace_id,
                agent_id=ctx.agent_id,
                message_id=ctx.message_id,
                created_at=datetime.now().isoformat(),
            ))

        return events


# ============================================================
# 夜巡主控
# ============================================================

class NightPatrol:
    """夜巡——后台异步审查系统。

    不阻塞对话主流程，在后台非阻塞执行所有规则检查。
    审计事件写入 audit_logs 表持久化。

    使用方式：
        patrol = NightPatrol(db_path)
        await patrol.patrol(ctx)  # 非阻塞
    """

    def __init__(self, db_path: str) -> None:
        self._rules: list[PatrolRule] = []
        self._stats: dict[str, int] = {}    # rule_name → trigger_count
        self._db_path = db_path
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        """注册默认规则集。"""
        self._rules = [
            SensitiveKeywordRule(),
            HallucinationDetector(),
            QualityChecker(),
            PolicyChecker(),
            TokenWasteChecker(),
        ]

    def register_rule(self, rule: PatrolRule) -> None:
        """注册自定义规则。"""
        self._rules.append(rule)
        self._stats[rule.name] = 0

    def remove_rule(self, rule_name: str) -> None:
        """移除规则。"""
        self._rules = [r for r in self._rules if r.name != rule_name]
        self._stats.pop(rule_name, None)

    def enable_rule(self, rule_name: str) -> None:
        for rule in self._rules:
            if rule.name == rule_name:
                rule.enabled = True
                break

    def disable_rule(self, rule_name: str) -> None:
        for rule in self._rules:
            if rule.name == rule_name:
                rule.enabled = False
                break

    async def patrol(self, ctx: PatrolContext) -> PatrolReport:
        """执行夜巡——非阻塞运行所有规则。

        Args:
            ctx: 检查上下文

        Returns:
            PatrolReport: 报告所有检测到的问题
        """
        report = PatrolReport()

        # 并行运行所有启用的规则
        tasks = []
        for rule in self._rules:
            if rule.enabled:
                tasks.append(self._run_rule_safe(rule, ctx))

        if not tasks:
            return report

        results = await asyncio.gather(*tasks)

        # 汇总事件
        for events in results:
            report.events.extend(events)
            report.total_checks += 1

        # 统计
        report.critical_count = sum(1 for e in report.events if e.severity == Severity.CRITICAL)
        report.error_count = sum(1 for e in report.events if e.severity == Severity.ERROR)
        report.warn_count = sum(1 for e in report.events if e.severity == Severity.WARN)

        # 生成摘要
        if report.has_issues:
            parts = []
            if report.critical_count:
                parts.append(f"{report.critical_count} 严重")
            if report.error_count:
                parts.append(f"{report.error_count} 错误")
            if report.warn_count:
                parts.append(f"{report.warn_count} 警告")
            report.summary = f"夜巡发现: " + ", ".join(parts)
        else:
            report.summary = "夜巡通过，无异常"

        # 持久化审计事件
        await self._persist_events(report.events)

        # 更新统计
        for event in report.events:
            self._stats[event.rule_name] = self._stats.get(event.rule_name, 0) + 1

        return report

    async def _run_rule_safe(self, rule: PatrolRule, ctx: PatrolContext) -> list[AuditEvent]:
        """安全运行单个规则——捕获异常不中断整体流程。"""
        try:
            return await rule.check(ctx)
        except Exception as e:
            logger.error("夜巡规则 [%s] 执行异常: %s", rule.name, e)
            return [AuditEvent(
                id=f"patrol_{uuid.uuid4().hex[:8]}",
                category=AuditCategory.AGENT_BEHAVIOR,
                severity=Severity.ERROR,
                rule_name="rule_error",
                message=f"规则 [{rule.name}] 执行失败: {e}",
                detail={"rule": rule.name, "error": str(e)},
                workspace_id=ctx.workspace_id,
                created_at=datetime.now().isoformat(),
            )]

    async def _persist_events(self, events: list[AuditEvent]) -> None:
        """持久化审计事件到 audit_logs 表。"""
        if not events:
            return

        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row

            for event in events:
                conn.execute(
                    """INSERT INTO audit_logs
                       (id, workspace_id, agent_id, operation, target, detail, result, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        event.id,
                        event.workspace_id or "",
                        event.agent_id or "",
                        f"patrol_{event.category.value}",
                        event.message,
                        json.dumps(event.detail, ensure_ascii=False),
                        event.severity.value,
                        event.created_at,
                    ),
                )

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("夜巡事件持久化失败: %s", e)

    def get_stats(self) -> dict:
        """获取夜巡统计。"""
        return {
            "rules_count": len(self._rules),
            "rules_enabled": sum(1 for r in self._rules if r.enabled),
            "rule_stats": self._stats.copy(),
        }

    def list_rules(self) -> list[dict]:
        """列出所有规则。"""
        return [
            {
                "name": r.name,
                "category": r.category.value,
                "enabled": r.enabled,
                "trigger_count": self._stats.get(r.name, 0),
            }
            for r in self._rules
        ]

    async def shutdown(self) -> None:
        """关闭夜巡。"""
        logger.info("夜巡已关闭（总检测: %d 次）", sum(self._stats.values()))


# ============================================================
# 全局单例
# ============================================================

_patrol_instance: Optional[NightPatrol] = None


def get_patrol(db_path: Optional[str] = None) -> NightPatrol:
    """获取夜巡全局实例。"""
    global _patrol_instance
    if _patrol_instance is None:
        from config.settings import settings
        db_path = db_path or str(settings.DB_PATH)
        _patrol_instance = NightPatrol(db_path)
    return _patrol_instance
