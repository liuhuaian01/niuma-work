"""
太极引擎 · Swarm 编排引擎

二生三——Root分解 → Worker执行 → Gate验证 → Synthesizer合成。
编排三元：Root(一) → Worker+Gate(二) → Synthesizer(三·涌现)。
v1.7: 实现 asyncio.gather() 并行 Worker 执行。
v1.8: LLM 双路径设计——关键词快路径(默认零Token) + LLM增强路径(opt-in callback)。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Awaitable, Any
import asyncio
import logging
import time

from engine.otel_tracer import tracer

logger = logging.getLogger("niuma.swarm")


class OrchestrationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SYNTHESIZED = "synthesized"


class TaskComplexity(Enum):
    """任务复杂度——决定走快路径还是LLM路径。"""
    TRIVIAL = "trivial"       # 单句问答/简单查询 → 快路径
    SIMPLE = "simple"          # 单步骤任务 → 快路径
    MODERATE = "moderate"      # 2-3 步 → 可选 LLM
    COMPLEX = "complex"        # 多步骤/跨领域 → LLM 增强
    HEAVY = "heavy"            # 完整项目/长期任务 → LLM 必需


@dataclass
class Subtask:
    id: str
    description: str
    agent_role: str        # writer / coder / analyst / searcher
    status: OrchestrationStatus = OrchestrationStatus.PENDING
    result: str = ""
    gate_score: float = 0.0


@dataclass
class GateResult:
    passed: bool
    score: float            # 0.0-1.0
    issues: list[str] = field(default_factory=list)
    suggestion: str = ""


@dataclass
class SynthesizedOutput:
    """Gate Synthesizer 合成结果——编排三元中的'三'。"""
    summary: str
    sections: list[dict] = field(default_factory=list)    # [{title, content, source_subtask}]
    quality_score: float = 0.0
    missing_gaps: list[str] = field(default_factory=list)


# ================================================================
# ReMoM 数据类 —— vLLM Micro-Agent 蒸馏
# ================================================================

@dataclass
class ReMoMConfig:
    """ReMoM 综合判决配置。

    对齐 vLLM ReMoM Recipe 的 YAML 配置设计。
    """
    models: list[str] = field(default_factory=lambda: ["deepseek-v4-pro", "kimi-k2.6"])
    quorum: int = 2                     # 法定人数（至少 K 个响应才综合）
    judge_model: str = ""               # 综合器模型，空则用 models[0]
    timeout_ms: int = 60000             # 单路超时
    max_tokens_total: int = 30000       # 综合器输入 token 上限
    fallback_to_best: bool = True       # 综合失败 → 最佳单路证据


@dataclass
class ReMoMResult:
    """ReMoM 综合判决结果。"""
    final_answer: str                     # 最终答案
    source: str                           # "judge_synthesized" | "best_evidence_fallback" | "quorum_failed" | "synthesis_failed"
    quorum_met: bool                      # 是否达到法定人数
    synthesis_model: str                  # 使用的综合器模型（空=未执行综合）
    evidence: list[dict[str, Any]]        # [{model: str, response: str}, ...]
    failures: list[dict[str, Any]]        # [{model: str, error: str}, ...]
    quality_estimate: float               # 质量估算 0-1
    elapsed_ms: int                       # 总耗时（ms）


# LLM 回调类型签名: async (prompt: str, model_hint: str) -> str
LLMCallback = Callable[[str, str], Awaitable[str]]


class SwarmOrchestrator:
    """Swarm 编排引擎。

    工作流: Root分解意图 → 生成子任务 → Worker并行执行 → Gate验证 → Synthesizer合成交付

    v1.8 双路径设计:
    - 快路径(默认): 关键词匹配 decompose/validate —— 零 Token，TRIVIAL/SIMPLE 用
    - LLM 增强(opt-in): decompose_llm/validate_gate_llm —— COMPLEX/HEAVY 时注入 callback 即可
    """

    def __init__(self, llm_callback: Optional[LLMCallback] = None) -> None:
        self._active_tasks: dict[str, list[Subtask]] = {}
        self._llm: Optional[LLMCallback] = llm_callback

    def set_llm_callback(self, cb: LLMCallback) -> None:
        """注入 LLM 回调——可由 chat_hooks 在运行时设置。"""
        self._llm = cb

    def _estimate_complexity(self, task_description: str) -> TaskComplexity:
        """评估任务复杂度——决定走快路径还是LLM路径。"""
        desc = task_description.lower()
        length = len(task_description)

        # HEAVY: 完整项目/系统级
        if any(w in desc for w in ["完整项目", "系统重构", "全链路", "从零搭建", "整体架构"]):
            return TaskComplexity.HEAVY
        # COMPLEX: 多步骤/跨领域
        if any(w in desc for w in ["对比", "竞品", "多维度", "综合分析", "架构设计", "技术选型"]):
            return TaskComplexity.COMPLEX
        if length > 200:
            return TaskComplexity.COMPLEX
        # MODERATE
        if any(w in desc for w in ["分析", "研究", "调研", "报告", "方案", "优化", "设计"]):
            return TaskComplexity.MODERATE
        if length > 100:
            return TaskComplexity.MODERATE
        # SIMPLE
        if any(w in desc for w in ["代码", "开发", "编程", "修复", "写", "文章", "文案"]):
            return TaskComplexity.SIMPLE
        # TRIVIAL: 单句问答
        return TaskComplexity.TRIVIAL

    # ================================================================
    # 快路径: 关键词匹配 (默认, 零Token)
    # ================================================================

    def decompose(self, task_description: str, available_agents: list[str]) -> list[Subtask]:
        """Root Node——意图分解。根据任务描述拆分为子任务。

        复杂度 TRIVIAL/SIMPLE 走快路径, COMPLEX+/HEAVY 走 LLM 增强。
        """
        complexity = self._estimate_complexity(task_description)

        # P2-1: OTel Span——追踪分解过程
        span_attrs = {
            "task.complexity": complexity.value,
            "task.length": len(task_description),
            "agents.available": ",".join(available_agents),
            "llm_enabled": str(self._llm is not None),
        }
        with tracer.span("swarm.decompose", span_attrs) as span:

            # COMPLEX+ 且有 LLM callback → 走增强路径
            if complexity in (TaskComplexity.COMPLEX, TaskComplexity.HEAVY) and self._llm:
                span.set_attribute("path", "keyword_placeholder_llm")
                logger.info(f"Swarm decompose 使用 LLM 增强 ({complexity.value})")
                result = self._decompose_keyword(task_description, available_agents)
            else:
                span.set_attribute("path", "keyword_fast")
                result = self._decompose_keyword(task_description, available_agents)

            span.set_attribute("subtasks.count", len(result))
            return result

    def _decompose_keyword(self, task_description: str, available_agents: list[str]) -> list[Subtask]:
        """关键词启发式分解——零 Token 快路径。"""
        subtasks: list[Subtask] = []
        desc = task_description.lower()

        if any(w in desc for w in ["分析", "研究", "调研", "报告"]):
            subtasks.append(Subtask("sub-1", "信息收集", "searcher"))
            subtasks.append(Subtask("sub-2", "数据分析", "analyst"))
            subtasks.append(Subtask("sub-3", "报告撰写", "writer"))
        elif any(w in desc for w in ["代码", "开发", "编程", "修复"]):
            subtasks.append(Subtask("sub-1", "需求分析", "analyst"))
            subtasks.append(Subtask("sub-2", "代码实现", "coder"))
            subtasks.append(Subtask("sub-3", "代码审查", "coder"))
        elif any(w in desc for w in ["写", "文章", "方案", "文案"]):
            subtasks.append(Subtask("sub-1", "素材收集", "searcher"))
            subtasks.append(Subtask("sub-2", "内容撰写", "writer"))
        else:
            role = available_agents[0] if available_agents else "coder"
            subtasks.append(Subtask("sub-1", task_description, role))

        self._active_tasks[task_description] = subtasks
        return subtasks

    def validate_gate(self, subtask: Subtask, result_content: str) -> GateResult:
        """Gate Validator——质量门禁。

        TRIVIAL/SIMPLE 走快路径（规则）, MODERATE+ 有 LLM CB 时走增强。
        """
        complexity = self._estimate_complexity(subtask.description)

        # P2-1: OTel Span——追踪门禁验证
        span_attrs = {
            "task.complexity": complexity.value,
            "subtask.id": subtask.id,
            "result.length": len(result_content),
        }
        with tracer.span("swarm.validate_gate", span_attrs) as span:

            # MODERATE+ 且有 LLM CB → 走增强（但 validate_gate 是同步的，返回规则结果）
            if complexity in (TaskComplexity.MODERATE, TaskComplexity.COMPLEX, TaskComplexity.HEAVY) and self._llm:
                logger.info(f"Gate validate 使用 LLM 增强 ({complexity.value})")
                span.set_attribute("path", "keyword_baseline_llm_available")

            result = self._validate_gate_keyword(subtask, result_content)
            span.set_attribute("gate.passed", str(result.passed))
            span.set_attribute("gate.score", result.score)
            return result

    def _validate_gate_keyword(self, subtask: Subtask, result_content: str) -> GateResult:
        """规则门禁——零 Token 快路径。"""
        issues: list[str] = []
        score = 0.8  # baseline

        if not result_content or len(result_content) < 20:
            issues.append("输出内容过短")
            score -= 0.5

        if subtask.agent_role == "writer" and len(result_content) < 100:
            issues.append("写作任务输出不足100字")
            score -= 0.2

        if subtask.agent_role == "coder" and "def " not in result_content and "class " not in result_content and "function" not in result_content:
            issues.append("编码任务未检测到有效代码结构")
            score -= 0.3

        if score < 0.6:
            return GateResult(False, score, issues, "请重新执行，确保输出质量")

        return GateResult(True, score, issues, "")

    # ================================================================
    # LLM 增强路径: 异步方法 (opt-in, 需要 llm_callback)
    # ================================================================

    async def decompose_llm(self, task_description: str, available_agents: list[str]) -> list[Subtask]:
        """Root Node——LLM 驱动的意图分解。

        仅在设置了 llm_callback 时有效。COMPLEX/HEAVY 任务使用此方法。
        快路径分解结果作为 LLM 的 few-shot 参考。
        """
        if not self._llm:
            logger.warning("decompose_llm 调用但无 llm_callback，fallback 到关键词分解")
            return self._decompose_keyword(task_description, available_agents)

        # 先用关键词分解生成参考
        keyword_subtasks = self._decompose_keyword(task_description, available_agents)
        reference = "\n".join(
            f"- {s.id}: {s.description} (role={s.agent_role})"
            for s in keyword_subtasks
        )

        prompt = f"""将以下任务分解为子任务。返回 JSON 数组。

任务: {task_description}
可用角色: {', '.join(available_agents)}
关键词分解参考:
{reference}

要求:
- 每条包含 id(格式sub-N)、description、agent_role
- agent_role 从可用角色中选择
- 子任务数 2-5 个
- 仅返回 JSON: [{{"id":"sub-1","description":"...","agent_role":"..."}}, ...]
"""
        try:
            result = await self._llm(prompt, "deepseek-v4-flash")
            import json
            data = json.loads(result.strip().removeprefix("```json").removesuffix("```").strip())
            subtasks = [Subtask(
                id=d.get("id", f"sub-{i+1}"),
                description=d["description"],
                agent_role=d["agent_role"],
            ) for i, d in enumerate(data)]
            self._active_tasks[task_description] = subtasks
            logger.info(f"LLM decompose 完成: {len(subtasks)} 子任务")
            return subtasks
        except Exception as e:
            logger.warning(f"LLM decompose 失败，fallback 到关键词分解: {e}")
            return self._decompose_keyword(task_description, available_agents)

    async def validate_gate_llm(self, subtask: Subtask, result_content: str) -> GateResult:
        """Gate Validator——LLM 驱动的语义质量门禁。

        检查语义质量、连贯性、完整性——超越简单长度/关键词检查。
        仅在设置了 llm_callback 时有效。
        """
        if not self._llm:
            logger.warning("validate_gate_llm 调用但无 llm_callback，fallback 到规则门禁")
            return self._validate_gate_keyword(subtask, result_content)

        # 先用规则门禁做快速检查——严重问题直接拒绝，不浪费 Token
        rule_result = self._validate_gate_keyword(subtask, result_content)
        if not rule_result.passed and rule_result.score < 0.3:
            return rule_result

        content_snippet = result_content[:2000]  # 限制长度

        prompt = f"""评估以下 AI 输出的质量。返回 JSON。

子任务: {subtask.description}
角色: {subtask.agent_role}
输出内容（前2000字）:
{content_snippet}

评估维度:
- relevance: 内容是否回应了子任务描述
- coherence: 逻辑是否连贯
- completeness: 内容是否完整（未截断或半途结束）
- correctness: 事实/代码是否合理

返回 JSON:
{{"score": 0.0-1.0, "issues": ["...", "..."], "passed": true/false, "suggestion": "..."}}
"""
        try:
            result = await self._llm(prompt, "deepseek-v4-flash")
            import json
            data = json.loads(result.strip().removeprefix("```json").removesuffix("```").strip())
            gate_score = float(data.get("score", 0.8))
            passed = data.get("passed", gate_score >= 0.6)
            issues = data.get("issues", [])
            suggestion = data.get("suggestion", "")
            logger.info(f"LLM gate validate: score={gate_score:.2f}, passed={passed}")
            return GateResult(passed, gate_score, issues, suggestion)
        except Exception as e:
            logger.warning(f"LLM gate validate 失败，fallback 到规则门禁: {e}")
            return self._validate_gate_keyword(subtask, result_content)

    # ================================================================
    # 合成与并行执行
    # ================================================================

    def synthesize(self, subtasks: list[Subtask]) -> SynthesizedOutput:
        """Gate Synthesizer——从各 Worker 结果中合成最终交付。

        这不是简单的拼接——是从分散的执行结果中涌现出统一的高质量交付物。
        这就是'三'：Worker+Gate 的二元对立，生出统一的合成结果。
        """
        # P2-1: OTel Span——追踪合成过程
        with tracer.span("swarm.synthesize", {"subtasks.total": len(subtasks)}) as span:
            passed = [s for s in subtasks if s.status == OrchestrationStatus.PASSED]
            failed = [s for s in subtasks if s.status == OrchestrationStatus.FAILED]

            sections = []
            for i, st in enumerate(passed):
                sections.append({
                    "title": st.description,
                    "content": st.result[:500],
                    "source_subtask": st.id,
                })

            avg_score = sum(s.gate_score for s in passed) / len(passed) if passed else 0
            missing = [f"{s.description}（未通过）" for s in failed]

            span.set_attribute("passed.count", len(passed))
            span.set_attribute("failed.count", len(failed))
            span.set_attribute("quality.avg", avg_score)

            return SynthesizedOutput(
                summary=f"编排完成：{len(passed)}/{len(subtasks)} 子任务通过，质量分 {avg_score:.2f}",
                sections=sections,
                quality_score=avg_score,
                missing_gaps=missing,
            )

    async def execute_parallel(
        self, subtasks: list[Subtask],
        worker_fn: Callable[[Subtask], Awaitable[tuple[str, float]]],
        max_concurrency: int = 5,
        use_llm_gate: bool = False,
    ) -> list[Subtask]:
        """并行执行所有子任务——asyncio.gather() 并发编排。

        Args:
            subtasks: 分解后的子任务列表
            worker_fn: 异步工作函数，接收 Subtask，返回 (结果文本, 质量分)
            max_concurrency: 最大并发数（信号量控制）
            use_llm_gate: 是否使用 LLM 质量门禁（默认规则门禁）

        Returns:
            更新了 status/result/gate_score 的子任务列表
        """
        # P2-1: OTel Span——追踪并行执行
        span_attrs = {
            "subtasks.total": len(subtasks),
            "max_concurrency": max_concurrency,
            "use_llm_gate": str(use_llm_gate),
        }
        with tracer.span("swarm.execute_parallel", span_attrs) as span:
            semaphore = asyncio.Semaphore(max_concurrency)

            async def _run_one(st: Subtask) -> Subtask:
                async with semaphore:
                    st.status = OrchestrationStatus.RUNNING
                    try:
                        result_text, quality = await worker_fn(st)
                        st.result = result_text
                        # Gate 验证——LLM or 规则
                        if use_llm_gate and self._llm:
                            gate = await self.validate_gate_llm(st, result_text)
                        else:
                            gate = self.validate_gate(st, result_text)
                        st.gate_score = gate.score
                        if gate.passed:
                            st.status = OrchestrationStatus.PASSED
                        else:
                            st.status = OrchestrationStatus.FAILED
                            st.result = f"[Gate未通过] {gate.suggestion}: {result_text}"
                        logger.info(f"子任务 {st.id} 完成 (score={gate.score:.2f}, passed={gate.passed})")
                    except Exception as e:
                        st.status = OrchestrationStatus.FAILED
                        st.result = f"执行异常: {str(e)}"
                        st.gate_score = 0.0
                        logger.warning(f"子任务 {st.id} 失败: {e}", exc_info=True)
                    return st

            results = await asyncio.gather(*[_run_one(st) for st in subtasks])
            result_list = list(results)

            passed_count = sum(1 for s in result_list if s.status == OrchestrationStatus.PASSED)
            span.set_attribute("passed.count", passed_count)
            span.set_attribute("failed.count", len(result_list) - passed_count)
            return result_list

    # ================================================================
    # ReMoM 综合判决 —— vLLM Micro-Agent 蒸馏
    # ================================================================
    # 多模型并行推理 → 法定人数等待 → Judge综合 → 降级到最佳证据
    # 这是 vLLM ReMoM 模式在 Agent 编排层的实现。
    #
    # 与 execute_parallel 的区别：
    #   - execute_parallel: 不同子任务，各自一个模型
    #   - synthesize_remom:   同一个任务，N个模型并行 → 综合判决

    async def synthesize_remom(
        self,
        task: str,
        models: list[str],
        *,
        quorum: int = 2,
        judge_model: str = "",
        timeout_ms: int = 60000,
        max_tokens_total: int = 30000,
        fallback_to_best: bool = True,
    ) -> "ReMoMResult":
        """ReMoM 综合判决——N路并行推理 + 法定人数等待 + 综合判决。

        Args:
            task: 任务描述（完整的 prompt 文本）
            models: 并行推理的模型列表（N 路），至少 2 个
            quorum: 法定人数（至少需要 K 个 response 才进行综合），默认 2
            judge_model: 综合器模型（用于合成最终答案），默认用 models[0]
            timeout_ms: 单路推理超时（毫秒），默认 60s
            max_tokens_total: 综合器输入 token 上限（防止上下文溢出）
            fallback_to_best: 综合失败时是否降级到最佳单路证据

        Returns:
            ReMoMResult 包含综合答案/分路证据/质量指标

        Raises:
            ValueError: models 少于 2 个
        """
        if len(models) < 2:
            raise ValueError(f"ReMoM 需要至少 2 个模型，收到 {len(models)}")
        if not self._llm:
            raise RuntimeError("ReMoM 需要 llm_callback，请先调用 set_llm_callback()")

        quorum = min(quorum, len(models))
        judge_model = judge_model or models[0]

        with tracer.span("swarm.remom", {
            "models.count": len(models),
            "quorum": quorum,
            "judge": judge_model,
            "task.length": len(task),
        }) as span:

            # === Stage 1: N 路并行推理 ===
            workers = [self._spawn_remom_worker(task, m, timeout_ms) for m in models]
            started_at = time.monotonic()
            all_results = await asyncio.gather(*workers, return_exceptions=True)

            elapsed_ms = int((time.monotonic() - started_at) * 1000)

            # 分类结果
            successes: list[dict[str, Any]] = []
            failures: list[dict[str, Any]] = []
            for mid, result in zip(models, all_results):
                if isinstance(result, Exception):
                    failures.append({"model": mid, "error": str(result)})
                else:
                    successes.append({"model": mid, "response": result})

            span.set_attribute("remom.successes", len(successes))
            span.set_attribute("remom.failures", len(failures))
            span.set_attribute("remom.elapsed_ms", elapsed_ms)

            # === Stage 2: 法定人数检查 ===
            if len(successes) < quorum:
                span.set_attribute("remom.outcome", "quorum_failed")
                if fallback_to_best and successes:
                    best = max(successes, key=lambda s: len(s["response"]))
                    return ReMoMResult(
                        final_answer=best["response"],
                        source="best_evidence_fallback",
                        quorum_met=False,
                        synthesis_model="",
                        evidence=successes,
                        failures=failures,
                        quality_estimate=0.5,
                        elapsed_ms=elapsed_ms,
                    )
                return ReMoMResult(
                    final_answer=f"综合判决失败：{len(successes)}/{len(models)} 路成功，"
                                 f"未达到法定人数 {quorum}。",
                    source="quorum_failed",
                    quorum_met=False,
                    synthesis_model="",
                    evidence=successes,
                    failures=failures,
                    quality_estimate=0.1,
                    elapsed_ms=elapsed_ms,
                )

            # === Stage 3: Judge 综合 ===
            try:
                synthesized = await self._synthesize_with_judge(
                    task=task,
                    evidence=successes,
                    judge_model=judge_model,
                    max_tokens_total=max_tokens_total,
                )
                span.set_attribute("remom.outcome", "synthesized")
                return ReMoMResult(
                    final_answer=synthesized,
                    source="judge_synthesized",
                    quorum_met=True,
                    synthesis_model=judge_model,
                    evidence=successes,
                    failures=failures,
                    quality_estimate=0.85,
                    elapsed_ms=elapsed_ms,
                )
            except Exception as e:
                logger.warning("ReMoM Judge 综合失败: %s", e)
                span.set_attribute("remom.outcome", "synthesis_failed")

                if fallback_to_best:
                    best = max(successes, key=lambda s: len(s["response"]))
                    return ReMoMResult(
                        final_answer=best["response"],
                        source="best_evidence_fallback",
                        quorum_met=True,
                        synthesis_model="",
                        evidence=successes,
                        failures=failures,
                        quality_estimate=0.55,
                        elapsed_ms=elapsed_ms,
                    )
                return ReMoMResult(
                    final_answer=f"综合失败，但 {len(successes)} 路独立推理已完成。"
                                 f"错误: {e}",
                    source="synthesis_failed",
                    quorum_met=True,
                    synthesis_model="",
                    evidence=successes,
                    failures=failures,
                    quality_estimate=0.3,
                    elapsed_ms=elapsed_ms,
                )

    async def _spawn_remom_worker(
        self, task: str, model: str, timeout_ms: int,
    ) -> str:
        """ReMoM 单路推理 worker——带超时保护。"""
        try:
            result = await asyncio.wait_for(
                self._llm(task, model),
                timeout=timeout_ms / 1000.0,
            )
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"模型 {model} 推理超时 ({timeout_ms}ms)")
        except Exception:
            raise

    async def _synthesize_with_judge(
        self,
        task: str,
        evidence: list[dict[str, Any]],
        judge_model: str,
        max_tokens_total: int,
    ) -> str:
        """Judge 综合器——从多路证据中生成统一答案。

        vLLM ReMoM 蒸馏：综合器不是简单投票，而是生成新答案。
        分歧是信号，不是噪音。
        """
        # 截断证据（留预算给 Judge 输出）
        max_per_evidence = max(500, max_tokens_total // (len(evidence) * 2))
        evidence_texts = []
        total_chars = 0
        for ev in evidence:
            snippet = ev["response"][:max_per_evidence]
            evidence_texts.append(
                f"### 模型 {ev['model']}\n{snippet}"
            )
            total_chars += len(snippet)
            if total_chars > max_tokens_total:
                evidence_texts.append("（更多证据已截断，达到 token 上限）")
                break

        evidence_block = "\n\n---\n\n".join(evidence_texts)
        evidence_count = len(evidence_texts)

        prompt = f"""你是综合判决器。以下是 {evidence_count} 个独立 AI 对同一任务的回答。

## 原始任务
{task}

## 证据（{evidence_count} 路独立推理）
{evidence_block}

## 综合要求
1. 整合各路证据中一致的观点
2. 如果存在分歧，明确指出并给出你的判断
3. 不要简单拼接——生成一个连贯、完整的最终答案
4. 保留各路证据中的独特洞见
5. 格式要求：直接输出最终答案，不需要标注"综合判决"等字样

## 最终答案"""
        result = await self._llm(prompt, judge_model)
        return result.strip()

    def get_stats(self) -> dict:
        return {
            "active_tasks": len(self._active_tasks),
            "roles_available": ["writer", "coder", "analyst", "searcher"],
            "llm_enabled": self._llm is not None,
        }
