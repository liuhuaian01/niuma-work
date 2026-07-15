"""
太极引擎 · 目标循环引擎（Goal Loop Engine）

太极第六律·刚柔并济——目标驱动+规则兜底。
不是为了控制用户，而是为了让引擎记住"用户在乎什么"。

核心机制：
  1. 规则管理：CRUD 操作，每条规则有优先级、触发条件、动作建议
  2. 目标追踪：定义长期目标 → 定期检查进度 → 自适应调整
  3. 上下文注入：对话中自动注入相关规则到 system prompt
  4. 周期性审视：每日检查规则有效性，自动淘汰过期规则

与递归自进化的关系：
  递归自进化（生生不息）发现模式 → GoalLoop（刚柔并济）将模式固化为规则
  → 规则驱动行为 → 行为产生数据 → 递归自进化再发现新模式
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional
import asyncio
import json
import logging
import os

logger = logging.getLogger("niuma.goalloop")


# ============================================================
# 数据模型
# ============================================================

@dataclass
class GoalRule:
    """一条目标规则——定义引擎应该遵守的行为准则。

    规则来源：
      - 用户显式设置（优先级最高）
      - 递归自进化发现（中优先级）
      - 系统内置默认（低优先级）
    """
    id: str
    name: str                          # 规则名称
    description: str                   # 规则描述
    category: str                      # token / model / behavior / security / quality
    priority: int = 50                 # 1(最低)-100(最高)
    conditions: dict = field(default_factory=dict)  # 触发条件 {"field": "op", "value"}
    action: str = ""                   # 触发后执行的动作建议
    enabled: bool = True
    source: str = "user"              # user / evolution / system
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    hit_count: int = 0                # 命中次数
    last_hit: str = ""


@dataclass
class GoalTarget:
    """一个长期目标——引擎追踪的对象。"""
    id: str
    name: str
    description: str
    target_value: float = 0.0          # 目标值
    current_value: float = 0.0         # 当前值
    unit: str = ""                     # 单位（%, tokens, etc）
    progress: float = 0.0              # 0.0-1.0
    status: str = "active"             # active / achieved / abandoned
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_checked: str = ""


# ============================================================
# 目标循环引擎
# ============================================================

class GoalLoopEngine:
    """目标循环引擎。

    规则是"刚"——明确的触发条件和动作。
    目标是"柔"——长期追踪、自适应调整。
    """

    DATA_DIR = "data/goalloop"
    CHECKPOINT_DIR = "data/goalloop/checkpoints"
    CHECKPOINT_INTERVAL = 5     # 每5次操作保存一次检查点
    MAX_CHECKPOINTS = 10        # 最多保留10个检查点

    # 内置默认规则
    BUILTIN_RULES = [
        {
            "id": "sys-token-thrifty",
            "name": "Token节俭",
            "description": "优先使用最省Token的模型组合完成任务",
            "category": "token",
            "priority": 30,
            "conditions": {"task_type": "any"},
            "action": "prefer_efficient_model",
            "enabled": True,
            "source": "system",
        },
        {
            "id": "sys-local-first",
            "name": "本地优先",
            "description": "能用本地模型完成的任务不调云端API",
            "category": "model",
            "priority": 25,
            "conditions": {"hardware": "capable", "task_complexity": "simple|moderate"},
            "action": "prefer_local_model",
            "enabled": True,
            "source": "system",
        },
        {
            "id": "sys-privacy-guard",
            "name": "隐私守卫",
            "description": "涉及敏感内容时自动使用本地模型",
            "category": "security",
            "priority": 90,
            "conditions": {"content_type": "sensitive"},
            "action": "force_local_model",
            "enabled": True,
            "source": "system",
        },
        {
            "id": "sys-quality-gate",
            "name": "质量门禁",
            "description": "复杂任务启用Gate质量检查",
            "category": "quality",
            "priority": 60,
            "conditions": {"task_complexity": "complex"},
            "action": "enable_gate_check",
            "enabled": True,
            "source": "system",
        },
    ]

    def __init__(self, data_dir: str | None = None) -> None:
        self._data_dir = data_dir or self.DATA_DIR
        self._checkpoint_dir = os.path.join(self._data_dir, "checkpoints")
        self._rules: dict[str, GoalRule] = {}
        self._targets: dict[str, GoalTarget] = {}
        self._is_initialized = False
        self._operation_count: int = 0   # 操作计数器——用于触发检查点

    # ============================================================
    # 初始化
    # ============================================================

    async def initialize(self) -> None:
        """加载规则和目标。"""
        os.makedirs(self._data_dir, exist_ok=True)

        # 加载内置规则
        for rule_data in self.BUILTIN_RULES:
            rid = rule_data["id"]
            if rid not in self._rules:
                self._rules[rid] = GoalRule(**rule_data)

        # 从文件恢复用户规则
        rules_file = os.path.join(self._data_dir, "rules.json")
        try:
            if os.path.exists(rules_file):
                with open(rules_file, "r", encoding="utf-8") as f:
                    raw_rules = json.load(f)
                for r in raw_rules:
                    if r["id"] not in self._rules:
                        self._rules[r["id"]] = GoalRule(**r)
                logger.info(f"GoalLoop: 加载 {len(self._rules)} 条规则")
        except Exception:
            logger.warning("规则文件读取失败", exc_info=True)

        # 从文件恢复目标
        targets_file = os.path.join(self._data_dir, "targets.json")
        try:
            if os.path.exists(targets_file):
                with open(targets_file, "r", encoding="utf-8") as f:
                    raw_targets = json.load(f)
                for t in raw_targets:
                    self._targets[t["id"]] = GoalTarget(**t)
                logger.info(f"GoalLoop: 加载 {len(self._targets)} 个目标")
        except Exception:
            logger.warning("目标文件读取失败", exc_info=True)

        self._is_initialized = True

    async def _save_rules(self) -> None:
        """持久化用户规则（只存非系统规则）。"""
        rules_file = os.path.join(self._data_dir, "rules.json")
        try:
            user_rules = [
                {
                    "id": r.id, "name": r.name, "description": r.description,
                    "category": r.category, "priority": r.priority,
                    "conditions": r.conditions, "action": r.action,
                    "enabled": r.enabled, "source": r.source,
                    "created_at": r.created_at, "updated_at": r.updated_at,
                    "hit_count": r.hit_count, "last_hit": r.last_hit,
                }
                for r in self._rules.values()
                if r.source != "system"
            ]
            with open(rules_file, "w", encoding="utf-8") as f:
                json.dump(user_rules, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.debug("规则持久化失败", exc_info=True)

    async def _save_targets(self) -> None:
        """持久化目标。"""
        targets_file = os.path.join(self._data_dir, "targets.json")
        try:
            raw_targets = [
                {
                    "id": t.id, "name": t.name, "description": t.description,
                    "target_value": t.target_value, "current_value": t.current_value,
                    "unit": t.unit, "progress": t.progress, "status": t.status,
                    "created_at": t.created_at, "last_checked": t.last_checked,
                }
                for t in self._targets.values()
            ]
            with open(targets_file, "w", encoding="utf-8") as f:
                json.dump(raw_targets, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.debug("目标持久化失败", exc_info=True)

    # ============================================================
    # 检查点（Checkpoint）— 断点恢复
    # ============================================================

    async def _checkpoint(self) -> None:
        """增量检查点——保存当前状态快照。

        每 CHECKPOINT_INTERVAL 次操作自动保存。
        保留最近 MAX_CHECKPOINTS 个检查点。
        """
        self._operation_count += 1
        if self._operation_count % self.CHECKPOINT_INTERVAL != 0:
            return

        os.makedirs(self._checkpoint_dir, exist_ok=True)
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            cp_file = os.path.join(
                self._checkpoint_dir,
                f"checkpoint_{timestamp}_op{self._operation_count}.json",
            )

            checkpoint_data = {
                "operation_count": self._operation_count,
                "created_at": datetime.now().isoformat(),
                "rules_count": len(self._rules),
                "targets_count": len(self._targets),
                "rules": [
                    {
                        "id": r.id, "name": r.name, "description": r.description,
                        "category": r.category, "priority": r.priority,
                        "conditions": r.conditions, "action": r.action,
                        "enabled": r.enabled, "source": r.source,
                        "created_at": r.created_at, "updated_at": r.updated_at,
                        "hit_count": r.hit_count, "last_hit": r.last_hit,
                    }
                    for r in self._rules.values()
                ],
                "targets": [
                    {
                        "id": t.id, "name": t.name, "description": t.description,
                        "target_value": t.target_value, "current_value": t.current_value,
                        "unit": t.unit, "progress": t.progress, "status": t.status,
                        "created_at": t.created_at, "last_checked": t.last_checked,
                    }
                    for t in self._targets.values()
                ],
            }
            with open(cp_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)

            # 清理过量检查点
            await self._cleanup_old_checkpoints()

            logger.debug("检查点已保存: %s (%d条规则, %d个目标)",
                         cp_file, len(checkpoint_data["rules"]), len(checkpoint_data["targets"]))
        except Exception:
            logger.debug("检查点保存失败", exc_info=True)

    async def _cleanup_old_checkpoints(self) -> None:
        """清理过期检查点——只保留最近 MAX_CHECKPOINTS 个。"""
        try:
            if not os.path.exists(self._checkpoint_dir):
                return
            files = sorted([
                f for f in os.listdir(self._checkpoint_dir)
                if f.startswith("checkpoint_") and f.endswith(".json")
            ])
            while len(files) > self.MAX_CHECKPOINTS:
                oldest = files.pop(0)
                os.remove(os.path.join(self._checkpoint_dir, oldest))
        except Exception:
            logger.debug("检查点清理失败", exc_info=True)

    async def resume_from_checkpoint(self, checkpoint_file: str | None = None) -> bool:
        """从检查点恢复状态。

        Args:
            checkpoint_file: 指定检查点文件路径。如果为 None，使用最新的。

        Returns:
            bool: 是否成功恢复
        """
        try:
            if not os.path.exists(self._checkpoint_dir):
                logger.warning("检查点目录不存在，无法恢复")
                return False

            if checkpoint_file is None:
                # 找最新的检查点
                files = sorted([
                    f for f in os.listdir(self._checkpoint_dir)
                    if f.startswith("checkpoint_") and f.endswith(".json")
                ])
                if not files:
                    logger.info("无可用检查点")
                    return False
                checkpoint_file = os.path.join(self._checkpoint_dir, files[-1])
            elif not os.path.isabs(checkpoint_file):
                checkpoint_file = os.path.join(self._checkpoint_dir, checkpoint_file)

            if not os.path.exists(checkpoint_file):
                logger.warning("检查点文件不存在: %s", checkpoint_file)
                return False

            with open(checkpoint_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 恢复规则（不覆盖系统规则）
            restored_rules = 0
            for r_data in data.get("rules", []):
                rid = r_data["id"]
                if rid in self._rules and self._rules[rid].source == "system":
                    continue  # 不恢复会覆盖系统规则
                self._rules[rid] = GoalRule(**r_data)
                restored_rules += 1

            # 恢复目标
            restored_targets = 0
            for t_data in data.get("targets", []):
                tid = t_data["id"]
                self._targets[tid] = GoalTarget(**t_data)
                restored_targets += 1

            self._operation_count = data.get("operation_count", 0)

            logger.info(
                "从检查点恢复: %s (%d条规则, %d个目标)",
                os.path.basename(checkpoint_file), restored_rules, restored_targets,
            )
            return True

        except Exception:
            logger.exception("检查点恢复失败")
            return False

    def list_checkpoints(self) -> list[dict]:
        """列出所有可用检查点。"""
        if not os.path.exists(self._checkpoint_dir):
            return []
        try:
            files = sorted([
                f for f in os.listdir(self._checkpoint_dir)
                if f.startswith("checkpoint_") and f.endswith(".json")
            ])
            result = []
            for fname in files:
                fpath = os.path.join(self._checkpoint_dir, fname)
                try:
                    size = os.path.getsize(fpath)
                    mtime = os.path.getmtime(fpath)
                    result.append({
                        "file": fname,
                        "path": fpath,
                        "size": size,
                        "modified_at": datetime.fromtimestamp(mtime).isoformat(),
                    })
                except Exception:
                    pass
            return result
        except Exception:
            return []

    # ============================================================
    # 规则 CRUD
    # ============================================================

    def add_rule(self, name: str, description: str, category: str,
                 priority: int = 50, conditions: dict | None = None,
                 action: str = "", source: str = "user") -> GoalRule:
        """添加用户规则。"""
        rid = f"rule-{datetime.now().strftime('%Y%m%d%H%M%S')}-{name[:20]}"
        rule = GoalRule(
            id=rid, name=name, description=description,
            category=category, priority=max(1, min(100, priority)),
            conditions=conditions or {}, action=action,
            source=source,
        )
        self._rules[rid] = rule
        asyncio.ensure_future(self._save_rules())
        asyncio.ensure_future(self._checkpoint())  # 检查点
        logger.info(f"GoalLoop: 新增规则 '{name}' (优先级={priority})")
        return rule

    def update_rule(self, rule_id: str, **kwargs) -> GoalRule | None:
        """更新规则。不允许修改系统规则。"""
        rule = self._rules.get(rule_id)
        if not rule:
            return None
        if rule.source == "system":
            logger.warning(f"不允许修改系统规则: {rule_id}")
            return None

        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        rule.updated_at = datetime.now().isoformat()
        asyncio.ensure_future(self._save_rules())
        asyncio.ensure_future(self._checkpoint())  # 检查点
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        """删除规则。系统规则不可删。"""
        rule = self._rules.get(rule_id)
        if not rule:
            return False
        if rule.source == "system":
            return False
        del self._rules[rule_id]
        asyncio.ensure_future(self._save_rules())
        asyncio.ensure_future(self._checkpoint())  # 检查点
        return True

    def get_rules(self, category: str = "", enabled_only: bool = True) -> list[GoalRule]:
        """获取规则列表，按优先级降序。"""
        rules = list(self._rules.values())
        if category:
            rules = [r for r in rules if r.category == category]
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        rules.sort(key=lambda r: r.priority, reverse=True)
        return rules

    def get_rule(self, rule_id: str) -> GoalRule | None:
        """获取单条规则。"""
        return self._rules.get(rule_id)

    # ============================================================
    # 上下文注入 — chat集成
    # ============================================================

    def get_context_rules(self, task_type: str = "", content_hint: str = "",
                          max_rules: int = 5) -> list[dict]:
        """获取应在当前对话上下文中注入的规则。

        匹配逻辑：
          1. 按优先级排序所有启用的规则
          2. 检查 conditions 是否匹配当前上下文
          3. 返回最相关的 max_rules 条
        """
        if not self._is_initialized:
            return []

        matched = []
        for rule in sorted(self._rules.values(), key=lambda r: r.priority, reverse=True):
            if not rule.enabled:
                continue

            # 条件匹配
            if self._match_conditions(rule.conditions, task_type, content_hint):
                matched.append({
                    "id": rule.id,
                    "name": rule.name,
                    "description": rule.description,
                    "action": rule.action,
                    "priority": rule.priority,
                    "source": rule.source,
                })
                # 记录命中
                rule.hit_count += 1
                rule.last_hit = datetime.now().isoformat()

            if len(matched) >= max_rules:
                break

        return matched

    def _match_conditions(self, conditions: dict, task_type: str, content_hint: str) -> bool:
        """简单的条件匹配检查。"""
        if not conditions:
            return True

        # task_type 匹配
        if "task_type" in conditions:
            expected = conditions["task_type"]
            if expected == "any":
                pass
            elif "|" in str(expected):
                if task_type not in str(expected).split("|"):
                    return False
            elif task_type != str(expected):
                return False

        # 内容敏感度
        if "content_type" in conditions and conditions["content_type"] == "sensitive":
            sensitive_keywords = ["密码", "密钥", "私钥", "token", "secret", "password",
                                  "隐私", "身份证", "银行卡", "地址", "电话"]
            if not any(kw.lower() in content_hint.lower() for kw in sensitive_keywords):
                return False

        # 复杂度匹配
        if "task_complexity" in conditions:
            expected = conditions["task_complexity"]
            if "|" in str(expected):
                pass  # 多值匹配，放行
            elif task_type not in ("complex", "moderate", "simple", "trivial"):
                pass  # 无法判断，放行

        return True

    # ============================================================
    # 目标追踪
    # ============================================================

    def add_target(self, name: str, description: str,
                   target_value: float, unit: str = "") -> GoalTarget:
        """添加长期目标。"""
        tid = f"target-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        target = GoalTarget(
            id=tid, name=name, description=description,
            target_value=target_value, unit=unit,
        )
        self._targets[tid] = target
        asyncio.ensure_future(self._save_targets())
        asyncio.ensure_future(self._checkpoint())  # 检查点
        return target

    def update_target(self, target_id: str, current_value: float | None = None,
                      status: str | None = None) -> GoalTarget | None:
        """更新目标进度。"""
        target = self._targets.get(target_id)
        if not target:
            return None

        if current_value is not None:
            target.current_value = current_value
            if target.target_value > 0:
                target.progress = min(1.0, current_value / target.target_value)
        if status:
            target.status = status
        target.last_checked = datetime.now().isoformat()

        asyncio.ensure_future(self._save_targets())
        return target

    def get_targets(self) -> list[GoalTarget]:
        """获取所有目标。"""
        return list(self._targets.values())

    def get_target(self, target_id: str) -> GoalTarget | None:
        """获取单个目标。"""
        return self._targets.get(target_id)

    def delete_target(self, target_id: str) -> bool:
        """删除目标。"""
        if target_id in self._targets:
            del self._targets[target_id]
            asyncio.ensure_future(self._save_targets())
            asyncio.ensure_future(self._checkpoint())  # 检查点
            return True
        return False

    # ============================================================
    # 周期性审视
    # ============================================================

    async def periodic_review(self) -> dict:
        """周期性规则审视——淘汰过期规则，更新目标进度。

        由自动化任务或手动触发。
        """
        today = date.today().isoformat()
        findings = []
        changes = []

        # 1. 标记已完成目标
        for target in self._targets.values():
            if target.progress >= 1.0 and target.status == "active":
                target.status = "achieved"
                findings.append(f"目标已达成: {target.name}")
                changes.append(f"mark_achieved:{target.id}")

        # 2. 淘汰长期未命中的低优先级用户规则
        for rule in list(self._rules.values()):
            if rule.source == "system":
                continue
            if rule.hit_count == 0 and rule.priority < 40:
                days_since = 0
                try:
                    created = datetime.fromisoformat(rule.created_at)
                    days_since = (datetime.now() - created).days
                except Exception:
                    pass
                if days_since > 30:
                    findings.append(f"规则 '{rule.name}' 30天未命中，建议淘汰")
                    changes.append(f"suggest_remove:{rule.id}")

        # 3. 基于递归自进化发现添加规则
        try:
            from engine.recursive_evolution import recursive_evolution
            trend = recursive_evolution.get_trend()
            if trend.get("success_rate", {}).get("trend") == "down":
                # 如果成功率下降，自动添加质量强化规则
                if "sys-quality-gate" in self._rules:
                    self._rules["sys-quality-gate"].priority = min(100, 
                        self._rules["sys-quality-gate"].priority + 5)
                findings.append("成功率下降趋势 → 自动提升质量门禁优先级")
        except Exception:
            pass

        await self._save_rules()
        await self._save_targets()

        return {
            "date": today,
            "findings": findings,
            "changes": changes,
            "rules_count": len(self._rules),
            "targets_count": len(self._targets),
        }

    # ============================================================
    # 状态查询
    # ============================================================

    def get_status(self) -> dict:
        """获取引擎状态。"""
        active_rules = sum(1 for r in self._rules.values() if r.enabled)
        active_targets = sum(1 for t in self._targets.values() if t.status == "active")
        achieved_targets = sum(1 for t in self._targets.values() if t.status == "achieved")

        return {
            "initialized": self._is_initialized,
            "total_rules": len(self._rules),
            "active_rules": active_rules,
            "system_rules": sum(1 for r in self._rules.values() if r.source == "system"),
            "user_rules": sum(1 for r in self._rules.values() if r.source == "user"),
            "evolution_rules": sum(1 for r in self._rules.values() if r.source == "evolution"),
            "total_targets": len(self._targets),
            "active_targets": active_targets,
            "achieved_targets": achieved_targets,
            "operation_count": self._operation_count,
            "checkpoints_available": len(self.list_checkpoints()),
        }


# ============================================================
# 全局实例
# ============================================================

goal_loop = GoalLoopEngine()
