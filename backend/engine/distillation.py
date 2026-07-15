"""
太极引擎 · 经验蒸馏层（Experience Distillation）— v1.8 新增

参考论文：EvolveR (ICML 2026) — 三段闭环：在线采样→离线蒸馏→上线规则复用。
太极第七律·生生不息——从成功和失败的轨迹中提炼决策规则，越用越强。

核心机制：
  1. 轨迹记录（Record）— 记录每次任务执行的上下文+结果
  2. 规则蒸馏（Distill）— 从轨迹中提取决策规则（成功模式/失败模式）
  3. 规则检索（Retrieve）— 新任务时检索匹配规则，注入决策上下文
  4. 规则淘汰（Prune）— 低效规则自动降级

设计原则（铁则）：
  - 轻量：纯Python，无外部向量数据库依赖
  - 克制：只蒸馏有明确因果的规则，不猜测
  - 不烧Token：规则检索用关键词匹配，不调用模型
  - 增量：规则库渐进积累，不全量重构

使用方式：
    from engine.distillation import distillation
    # 记录轨迹
    await distillation.record_trajectory(
        task_type="coding", task_desc="修复登录bug",
        model_used="deepseek-v4", tools_used=["file_read", "edit"],
        success=True, gate_score=0.9, tokens_used=5000
    )
    # 蒸馏规则（微周期触发）
    rules = await distillation.distill_rules()
    # 检索匹配规则
    matched = await distillation.retrieve_rules("coding", "修复bug")
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import asyncio
import json
import logging
import os
import re
import time

logger = logging.getLogger("niuma.distillation")


# ============================================================
# 数据模型
# ============================================================

@dataclass
class Trajectory:
    """一次任务执行的完整轨迹。"""
    id: str
    timestamp: float
    task_type: str                # coding / writing / analysis / search / conversation
    task_desc: str                # 任务描述（截断至200字）
    model_used: str               # 使用的模型
    tools_used: list[str]         # 使用的工具列表
    success: bool                 # 是否成功
    gate_score: float             # 质量评分 0-1
    tokens_used: int              # Token消耗
    duration_ms: int = 0          # 执行耗时
    key_terms: set[str] = field(default_factory=set)  # 从task_desc提取的关键词


@dataclass
class DistilledRule:
    """从轨迹中蒸馏出的决策规则。"""
    id: str
    rule_type: str                # success_pattern / failure_pattern / cost_optimization
    task_type: str                # 适用任务类型
    condition: str                # 规则条件（自然语言描述）
    action: str                   # 建议行动
    confidence: float             # 置信度 0-1
    sample_count: int = 0         # 支撑样本数
    success_rate: float = 0.0     # 关联成功率
    avg_tokens: int = 0           # 关联平均Token
    created_at: float = field(default_factory=time.time)
    last_used_at: float = 0.0     # 最后一次被检索使用的时间
    use_count: int = 0            # 被检索使用次数
    key_terms: set[str] = field(default_factory=set)  # 匹配关键词


# ============================================================
# 轻量分词器（复用context_drift的逻辑）
# ============================================================

_STOP_WORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "什么",
    "the", "a", "an", "is", "are", "was", "were", "be", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "this", "that", "it",
}

_WORD_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\w]+')


def _extract_terms(text: str) -> set[str]:
    """从文本中提取关键词。"""
    if not text:
        return set()
    words = _WORD_RE.findall(text.lower())
    return {w for w in words if len(w) > 1 and w not in _STOP_WORDS and not w.isdigit()}


def _term_overlap(a: set[str], b: set[str]) -> float:
    """计算关键词重叠度。"""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


# ============================================================
# 经验蒸馏引擎
# ============================================================

class ExperienceDistillation:
    """经验蒸馏引擎 — v1.8 新增。

    太极哲学：以静制动——不是每次都蒸馏，而是积累足够样本后批量提炼。
    """

    MAX_TRAJECTORIES = 500      # 最多保留500条轨迹
    MAX_RULES = 100             # 最多保留100条规则
    DISTILL_THRESHOLD = 10      # 至少10条轨迹才触发蒸馏
    PRUNE_AFTER_DAYS = 30       # 30天未使用的规则降级
    DATA_DIR = "data/distillation"

    def __init__(self, data_dir: str | None = None) -> None:
        self._data_dir = data_dir or self.DATA_DIR
        self._trajectories: list[Trajectory] = []
        self._rules: list[DistilledRule] = []
        self._total_distilled: int = 0
        self._total_retrievals: int = 0
        self._is_initialized = False

    # ----------------------------------------------------------
    # 初始化
    # ----------------------------------------------------------

    async def initialize(self) -> None:
        """从持久化恢复状态。"""
        os.makedirs(self._data_dir, exist_ok=True)
        state_file = os.path.join(self._data_dir, "distillation_state.json")
        try:
            if os.path.exists(state_file):
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                # 恢复轨迹
                raw_trajs = state.get("trajectories", [])
                self._trajectories = []
                for t in raw_trajs[-self.MAX_TRAJECTORIES:]:
                    t["key_terms"] = set(t.get("key_terms", []))
                    self._trajectories.append(Trajectory(**t))
                # 恢复规则
                raw_rules = state.get("rules", [])
                self._rules = []
                for r in raw_rules[-self.MAX_RULES:]:
                    r["key_terms"] = set(r.get("key_terms", []))
                    self._rules.append(DistilledRule(**r))
                self._total_distilled = state.get("total_distilled", 0)
                self._total_retrievals = state.get("total_retrievals", 0)
                logger.info(
                    f"经验蒸馏恢复: {len(self._trajectories)}条轨迹, "
                    f"{len(self._rules)}条规则"
                )
        except Exception:
            logger.warning("蒸馏状态文件损坏，从零开始", exc_info=True)
        self._is_initialized = True

    async def _save_state(self) -> None:
        """持久化状态。"""
        state_file = os.path.join(self._data_dir, "distillation_state.json")
        try:
            trajs_raw = [
                {
                    "id": t.id, "timestamp": t.timestamp,
                    "task_type": t.task_type, "task_desc": t.task_desc,
                    "model_used": t.model_used, "tools_used": t.tools_used,
                    "success": t.success, "gate_score": t.gate_score,
                    "tokens_used": t.tokens_used, "duration_ms": t.duration_ms,
                    "key_terms": list(t.key_terms),
                }
                for t in self._trajectories[-self.MAX_TRAJECTORIES:]
            ]
            rules_raw = [
                {
                    "id": r.id, "rule_type": r.rule_type,
                    "task_type": r.task_type, "condition": r.condition,
                    "action": r.action, "confidence": r.confidence,
                    "sample_count": r.sample_count, "success_rate": r.success_rate,
                    "avg_tokens": r.avg_tokens, "created_at": r.created_at,
                    "last_used_at": r.last_used_at, "use_count": r.use_count,
                    "key_terms": list(r.key_terms),
                }
                for r in self._rules[-self.MAX_RULES:]
            ]
            state = {
                "trajectories": trajs_raw,
                "rules": rules_raw,
                "total_distilled": self._total_distilled,
                "total_retrievals": self._total_retrievals,
                "saved_at": datetime.now().isoformat(),
            }
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.debug("蒸馏状态持久化失败", exc_info=True)

    # ----------------------------------------------------------
    # 轨迹记录
    # ----------------------------------------------------------

    async def record_trajectory(
        self,
        task_type: str,
        task_desc: str,
        model_used: str,
        tools_used: list[str] | None = None,
        success: bool = True,
        gate_score: float = 0.0,
        tokens_used: int = 0,
        duration_ms: int = 0,
    ) -> Trajectory:
        """记录一次任务执行轨迹。

        在 increment_chat() 中调用，每次对话完成后记录。
        """
        traj = Trajectory(
            id=f"traj-{int(time.time() * 1000)}-{len(self._trajectories)}",
            timestamp=time.time(),
            task_type=task_type,
            task_desc=task_desc[:200],
            model_used=model_used,
            tools_used=tools_used or [],
            success=success,
            gate_score=gate_score,
            tokens_used=tokens_used,
            duration_ms=duration_ms,
            key_terms=_extract_terms(task_desc),
        )

        self._trajectories.append(traj)
        if len(self._trajectories) > self.MAX_TRAJECTORIES:
            self._trajectories = self._trajectories[-self.MAX_TRAJECTORIES:]

        # 每10条存一次
        if len(self._trajectories) % 10 == 0:
            asyncio.ensure_future(self._save_state())

        return traj

    # ----------------------------------------------------------
    # 规则蒸馏（核心算法）
    # ----------------------------------------------------------

    async def distill_rules(self) -> list[DistilledRule]:
        """从轨迹中蒸馏决策规则。

        在微周期触发时调用。分析近期轨迹，提取成功/失败模式。

        蒸馏策略：
          1. 按任务类型分组
          2. 成功模式：高成功率+低Token的组合
          3. 失败模式：低成功率或低gate_score的组合
          4. 成本优化：同任务不同模型的Token对比
        """
        if len(self._trajectories) < self.DISTILL_THRESHOLD:
            return []

        new_rules: list[DistilledRule] = []
        now = time.time()

        # 按任务类型分组
        by_type: dict[str, list[Trajectory]] = {}
        for t in self._trajectories:
            by_type.setdefault(t.task_type, []).append(t)

        for task_type, trajs in by_type.items():
            if len(trajs) < 3:
                continue  # 样本不足

            # --- 策略1: 成功模式 ---
            success_trajs = [t for t in trajs if t.success and t.gate_score >= 0.8]
            if len(success_trajs) >= 3:
                # 找出最常出现的模型
                model_counts: dict[str, int] = {}
                model_tokens: dict[str, list[int]] = {}
                for t in success_trajs:
                    model_counts[t.model_used] = model_counts.get(t.model_used, 0) + 1
                    model_tokens.setdefault(t.model_used, []).append(t.tokens_used)

                best_model = max(model_counts, key=model_counts.get)
                best_count = model_counts[best_model]
                best_tokens = model_tokens[best_model]
                avg_tokens = sum(best_tokens) / len(best_tokens) if best_tokens else 0

                if best_count >= 3:
                    # 提取关键词
                    all_terms: set[str] = set()
                    for t in success_trajs:
                        if t.model_used == best_model:
                            all_terms.update(t.key_terms)

                    rule = DistilledRule(
                        id=f"rule-success-{task_type}-{best_model}-{int(now)}",
                        rule_type="success_pattern",
                        task_type=task_type,
                        condition=f"任务类型={task_type}, 关键词匹配",
                        action=f"优先使用 {best_model}（成功率{best_count/len(success_trajs):.0%}, 均Token {avg_tokens:.0f}）",
                        confidence=min(1.0, best_count / len(success_trajs)),
                        sample_count=best_count,
                        success_rate=best_count / len(success_trajs),
                        avg_tokens=int(avg_tokens),
                        key_terms=all_terms,
                    )
                    new_rules.append(rule)

            # --- 策略2: 失败模式 ---
            failure_trajs = [t for t in trajs if not t.success or t.gate_score < 0.5]
            if len(failure_trajs) >= 3:
                # 找出失败时最常出现的模型
                fail_model_counts: dict[str, int] = {}
                for t in failure_trajs:
                    fail_model_counts[t.model_used] = fail_model_counts.get(t.model_used, 0) + 1

                worst_model = max(fail_model_counts, key=fail_model_counts.get)
                worst_count = fail_model_counts[worst_model]

                if worst_count >= 3:
                    all_terms = set()
                    for t in failure_trajs:
                        if t.model_used == worst_model:
                            all_terms.update(t.key_terms)

                    rule = DistilledRule(
                        id=f"rule-failure-{task_type}-{worst_model}-{int(now)}",
                        rule_type="failure_pattern",
                        task_type=task_type,
                        condition=f"任务类型={task_type}, 模型={worst_model}",
                        action=f"避免使用 {worst_model}（失败率{worst_count/len(failure_trajs):.0%}）",
                        confidence=min(1.0, worst_count / len(failure_trajs)),
                        sample_count=worst_count,
                        success_rate=1.0 - worst_count / len(failure_trajs),
                        key_terms=all_terms,
                    )
                    new_rules.append(rule)

            # --- 策略3: 成本优化 ---
            if len(trajs) >= 5:
                # 比较同任务不同模型的Token消耗
                model_avg_tokens: dict[str, float] = {}
                model_avg_score: dict[str, float] = {}
                for t in trajs:
                    model_avg_tokens.setdefault(t.model_used, []).append(t.tokens_used)
                    model_avg_score.setdefault(t.model_used, []).append(t.gate_score)

                for model, tokens_list in model_avg_tokens.items():
                    avg_t = sum(tokens_list) / len(tokens_list)
                    scores = model_avg_score[model]
                    avg_s = sum(scores) / len(scores) if scores else 0

                    # 如果质量接近但Token更省
                    if avg_s >= 0.7 and avg_t < sum(sum(v) for v in model_avg_tokens.values()) / sum(len(v) for v in model_avg_tokens.values()):
                        rule = DistilledRule(
                            id=f"rule-cost-{task_type}-{model}-{int(now)}",
                            rule_type="cost_optimization",
                            task_type=task_type,
                            condition=f"任务类型={task_type}, 预算紧张",
                            action=f"使用 {model} 省Token（均{avg_t:.0f}Token, 质量{avg_s:.0%}）",
                            confidence=0.6,
                            sample_count=len(tokens_list),
                            success_rate=avg_s,
                            avg_tokens=int(avg_t),
                        )
                        new_rules.append(rule)

        # 合并新规则（去重：同类型+同模型→更新而非新增）
        for new_rule in new_rules:
            existing = None
            for r in self._rules:
                if r.rule_type == new_rule.rule_type and r.task_type == new_rule.task_type:
                    # 同类型同任务→更新
                    if new_rule.rule_type in ("success_pattern", "failure_pattern"):
                        if new_rule.condition == r.condition:
                            existing = r
                            break
                    elif new_rule.rule_type == "cost_optimization":
                        if new_rule.action.split(" ")[1] == r.action.split(" ")[1] if len(r.action.split(" ")) > 1 else False:
                            existing = r
                            break

            if existing:
                # 更新已有规则
                existing.confidence = max(existing.confidence, new_rule.confidence)
                existing.sample_count = max(existing.sample_count, new_rule.sample_count)
                existing.success_rate = new_rule.success_rate
                existing.avg_tokens = new_rule.avg_tokens
                existing.key_terms.update(new_rule.key_terms)
            else:
                self._rules.append(new_rule)

        # 规则淘汰：超过30天未使用的规则降级
        self._prune_rules()

        # 限制规则数量
        if len(self._rules) > self.MAX_RULES:
            # 按置信度×使用次数排序，淘汰最低的
            self._rules.sort(key=lambda r: r.confidence * (r.use_count + 1), reverse=True)
            self._rules = self._rules[:self.MAX_RULES]

        self._total_distilled += 1
        asyncio.ensure_future(self._save_state())

        if new_rules:
            logger.info("经验蒸馏: 提取 %d 条新规则（共 %d 条轨迹）", len(new_rules), len(self._trajectories))

        return new_rules

    def _prune_rules(self) -> None:
        """淘汰低效规则。"""
        now = time.time()
        stale_threshold = self.PRUNE_AFTER_DAYS * 86400  # 30天

        for rule in self._rules:
            if rule.last_used_at > 0 and (now - rule.last_used_at) > stale_threshold:
                # 30天未使用→降级置信度
                rule.confidence *= 0.7
                if rule.confidence < 0.2:
                    rule.confidence = 0.0  # 标记为待删除

        # 移除零置信度规则
        self._rules = [r for r in self._rules if r.confidence > 0.0]

    # ----------------------------------------------------------
    # 规则检索
    # ----------------------------------------------------------

    async def retrieve_rules(
        self,
        task_type: str,
        task_desc: str = "",
        top_k: int = 5,
    ) -> list[dict]:
        """检索匹配的决策规则。

        新任务执行前调用，将匹配规则注入决策上下文。
        纯关键词匹配，不调用模型——不烧Token。
        """
        self._total_retrievals += 1
        query_terms = _extract_terms(task_desc) if task_desc else set()

        scored: list[tuple[float, DistilledRule]] = []
        for rule in self._rules:
            if rule.task_type != task_type and rule.task_type != "general":
                continue

            # 关键词匹配得分
            term_score = _term_overlap(query_terms, rule.key_terms) if query_terms else 0.0

            # 综合得分：关键词匹配 × 置信度 × (使用次数加成)
            use_boost = 1.0 + min(0.5, rule.use_count * 0.05)
            final_score = (term_score * 0.5 + rule.confidence * 0.5) * use_boost

            if final_score > 0.1:
                scored.append((final_score, rule))

        # 排序取top_k
        scored.sort(key=lambda x: -x[0])
        results = []
        for score, rule in scored[:top_k]:
            rule.use_count += 1
            rule.last_used_at = time.time()
            results.append({
                "rule_id": rule.id,
                "rule_type": rule.rule_type,
                "condition": rule.condition,
                "action": rule.action,
                "confidence": round(rule.confidence, 3),
                "match_score": round(score, 3),
                "sample_count": rule.sample_count,
            })

        return results

    # ----------------------------------------------------------
    # 查询接口
    # ----------------------------------------------------------

    def get_stats(self) -> dict:
        """获取蒸馏引擎统计。"""
        return {
            "trajectories_count": len(self._trajectories),
            "rules_count": len(self._rules),
            "total_distilled": self._total_distilled,
            "total_retrievals": self._total_retrievals,
            "rules_by_type": self._rules_by_type(),
            "initialized": self._is_initialized,
        }

    def _rules_by_type(self) -> dict[str, int]:
        dist: dict[str, int] = {}
        for r in self._rules:
            dist[r.rule_type] = dist.get(r.rule_type, 0) + 1
        return dist

    def get_recent_trajectories(self, limit: int = 20) -> list[dict]:
        """获取最近的轨迹记录。"""
        return [
            {
                "id": t.id,
                "task_type": t.task_type,
                "task_desc": t.task_desc[:50],
                "model_used": t.model_used,
                "success": t.success,
                "gate_score": t.gate_score,
                "tokens_used": t.tokens_used,
                "timestamp": t.timestamp,
            }
            for t in self._trajectories[-limit:]
        ]

    def get_all_rules(self) -> list[dict]:
        """获取所有规则。"""
        return [
            {
                "id": r.id,
                "rule_type": r.rule_type,
                "task_type": r.task_type,
                "condition": r.condition,
                "action": r.action,
                "confidence": r.confidence,
                "sample_count": r.sample_count,
                "success_rate": r.success_rate,
                "avg_tokens": r.avg_tokens,
                "use_count": r.use_count,
                "last_used_at": r.last_used_at,
            }
            for r in self._rules
        ]


# ============================================================
# 全局实例
# ============================================================

distillation = ExperienceDistillation()
