"""
上下文压缩引擎 Python 原型

三级压缩策略：Budget → Snip → Summarize
- Budget (80%): 单工具结果截断，释放 ~10%
- Snip (90%): 移除无决策中间推理，释放 ~15%
- Summarize (90%): cheap 模型语义摘要，释放 ~30%

核心目标：压缩率 ≥ 50%，质量不退化
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


# ============================================================
# 数据结构
# ============================================================

@dataclass
class CompressedResult:
    """Budget 截断结果"""
    content: str = ""
    original_hash: str = ""
    truncated: bool = False
    saved_tokens: int = 0
    restore_info: Optional[Dict] = None


@dataclass
class BudgetResult:
    """Budget 层批量截断结果"""
    total_saved_tokens: int = 0
    compressed_count: int = 0
    release_ratio: float = 0.0


@dataclass
class SnipResult:
    """Snip 层裁剪结果"""
    snipped_messages: int = 0
    saved_tokens: int = 0
    release_ratio: float = 0.0
    remaining_candidates: int = 0


@dataclass
class SummarizeResult:
    """Summarize 层摘要结果"""
    saved_tokens: int = 0
    batches: int = 0
    release_ratio: float = 0.0
    cost_estimate: float = 0.0


@dataclass
class CompressionAction:
    """单次压缩操作记录"""
    type: str = ""          # 'budget' | 'snip' | 'summarize'
    saved_tokens: int = 0
    details: Any = None


@dataclass
class CompressionReport:
    """压缩报告"""
    level: int = 0
    pre_tokens: int = 0
    post_tokens: int = 0
    total_saved: int = 0
    saving_ratio: float = 0.0
    actions: List[CompressionAction] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """质量验证结果"""
    passed: bool = True
    issues: List[str] = field(default_factory=list)
    compression_ratio: float = 0.0


@dataclass
class CompressionMetricsEvent:
    """压缩度量事件"""
    timestamp: datetime = field(default_factory=datetime.now)
    level: int = 0
    pre_tokens: int = 0
    post_tokens: int = 0
    saving_ratio: float = 0.0
    actions: List[str] = field(default_factory=list)


@dataclass
class MetricsSummary:
    """度量摘要"""
    total_compressions: int = 0
    total_tokens_saved: int = 0
    avg_saving_ratio: float = 0.0
    budget_triggers: int = 0
    snip_triggers: int = 0
    summarize_triggers: int = 0
    cost_saved: float = 0.0

    @classmethod
    def empty(cls) -> 'MetricsSummary':
        return cls()


# ============================================================
# 模型适配器协议
# ============================================================

class ModelAdapter(Protocol):
    """模型适配器接口，用于 Summarize 层调用 cheap 模型"""

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 300,
        temperature: float = 0.1,
    ) -> str:
        ...


class MockModelAdapter:
    """
    Mock 模型适配器 (原型阶段)
    生产环境替换为真实的多模型适配层
    """

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 300,
        temperature: float = 0.1,
    ) -> str:
        """模拟摘要生成"""
        user_msg = messages[-1]["content"] if messages else ""
        # 简单模拟：截取前 200 字符作为摘要
        return json.dumps({
            "summary": user_msg[:100] + "...",
            "key_points": ["关键信息已保留"],
            "decisions": [],
            "pending": [],
            "important_context": "",
            "compression_ratio": "0.3"
        }, ensure_ascii=False)


# ============================================================
# Budget 层：单结果截断
# ============================================================

class BudgetCompressor:
    """
    Budget 层压缩器：对单个工具调用结果做长度截断

    规则：
    - 单结果 > 2000 字符：截取前 500 + 后 500 + 截断标记
    - 单结果 ≤ 2000 字符：不截断
    - 截断内容 hash 存储，可按需恢复
    """

    MAX_RESULT_LENGTH = 2000
    PREVIEW_HEAD = 500
    PREVIEW_TAIL = 500
    TRUNCATION_MARKER = "... [已截断 {n} 字符，可点击展开]"

    def compress(self, tool_result_content: str, tool_result_id: str = "") -> CompressedResult:
        """
        截断单个工具调用结果

        Args:
            tool_result_content: 原始内容
            tool_result_id: 结果 ID (用于恢复)

        Returns:
            CompressedResult 包含截断后的内容和恢复信息
        """
        content = tool_result_content

        if len(content) <= self.MAX_RESULT_LENGTH:
            return CompressedResult(
                content=content,
                original_hash=hashlib.md5(content.encode()).hexdigest(),
                truncated=False,
                saved_tokens=0,
            )

        # 触发截断
        full_hash = hashlib.md5(content.encode()).hexdigest()
        truncated_chars = len(content) - self.PREVIEW_HEAD - self.PREVIEW_TAIL
        marker = self.TRUNCATION_MARKER.format(n=truncated_chars)

        compressed = (
            content[:self.PREVIEW_HEAD]
            + marker
            + content[-self.PREVIEW_TAIL:]
        )

        # 估算节省 token (中文: 1 token ≈ 1.5 字符)
        saved_tokens = int(truncated_chars / 1.5)

        return CompressedResult(
            content=compressed,
            original_hash=full_hash,
            truncated=True,
            saved_tokens=saved_tokens,
            restore_info={
                "tool_result_id": tool_result_id,
                "full_content_hash": full_hash,
            },
        )

    def apply_to_session(self, l1_memory: Any) -> BudgetResult:
        """
        对会话中所有工具结果执行 Budget 截断

        Args:
            l1_memory: L1SessionMemory 实例

        Returns:
            BudgetResult: 包含压缩详情和释放的 Token 数量
        """
        total_saved = 0
        compressed_count = 0

        for tool_name, results in l1_memory.tool_results.items():
            for tool_result in results:
                if tool_result.compressed:
                    continue

                result = self.compress(tool_result.content, tool_result.result_id)
                if result.truncated:
                    # 存储完整内容用于恢复
                    l1_memory.store_truncated(
                        tool_result.result_id, tool_result.content,
                    )
                    # 更新内容
                    tool_result.content = result.content
                    tool_result.compressed = True
                    total_saved += result.saved_tokens
                    compressed_count += 1

        release_ratio = total_saved / l1_memory.max_tokens if l1_memory.max_tokens > 0 else 0.0
        l1_memory.total_tokens -= total_saved

        return BudgetResult(
            total_saved_tokens=total_saved,
            compressed_count=compressed_count,
            release_ratio=release_ratio,
        )


# ============================================================
# Snip 层：无决策片段裁剪
# ============================================================

def snippable_score(
    message: Any,
    context: list,
    current_index: int,
) -> float:
    """
    计算消息的可裁剪评分 (0.0-1.0)

    评分越高 → 越应该被裁剪

    因素：
    - 消息角色：system > assistant > tool > user
    - 消息距离：越旧越高 (超出最近 3 轮后线性增加)
    - 内容长度：越长越高 (按比例加权)
    - 重要性评分：高重要性降低评分
    - 是否包含 tool_calls：包含则降低评分
    """
    score = 0.0

    # 1. 角色权重
    role_weights = {"system": 0.6, "assistant": 0.3, "tool": 0.4, "user": 0.0}
    score += role_weights.get(getattr(message, "role", "assistant"), 0.3)

    # 2. 距离因子：最近 3 轮 (6 条消息) 不裁剪
    total_msgs = len(context)
    if total_msgs - current_index <= 6:
        return 0.0

    distance_factor = min((total_msgs - current_index - 6) / 20, 1.0)
    score += distance_factor * 0.3

    # 3. 长度因子
    content_len = len(getattr(message, "content", ""))
    length_factor = min(content_len / 500, 1.0)
    score += length_factor * 0.1

    # 4. 重要性因子 (负相关)
    importance = getattr(message, "importance_score", 0.5)
    score -= importance * 0.4

    # 5. 包含 tool_calls → 降低评分
    if getattr(message, "tool_calls", None):
        score -= 0.3

    return max(0.0, min(1.0, score))


class SnipCompressor:
    """
    Snip 层压缩器：移除无决策价值的中间推理片段

    裁剪对象：
    1. assistant 纯思考/推理消息 (无 tool_calls, 无最终输出)
    2. 重复的工具调用结果 (连续相同 tool_name)
    3. 已完成的子步骤消息 (最后 3 轮对话保留)

    保留对象：
    1. 用户直接指令 (user 消息)
    2. 包含 tool_calls 的 assistant 消息
    3. 错误信息 (importance > 0.5)
    4. 最近 3 轮完整对话
    """

    SNIP_THRESHOLD = 0.5
    MAX_SNIP_RATIO = 0.30

    def execute(self, l1_memory: Any) -> SnipResult:
        """
        执行 Snip 层裁剪

        流程：
        1. 遍历所有消息，计算 snippable_score
        2. 标记评分 > SNIP_THRESHOLD 的消息
        3. 按时间从旧到新执行裁剪
        4. 检查裁剪比例，不超 MAX_SNIP_RATIO
        5. 被裁剪消息内容替换为 "[已裁剪]"
        """
        messages = l1_memory.messages
        candidates = []

        for i, msg in enumerate(messages):
            score = snippable_score(msg, messages, i)
            if score >= self.SNIP_THRESHOLD:
                candidates.append((i, msg, score))

        # 按时间从旧到新排序
        candidates.sort(key=lambda x: x[0])

        total_msgs = len(messages)
        max_snip_count = int(total_msgs * self.MAX_SNIP_RATIO)

        snipped_count = 0
        total_saved_tokens = 0

        for idx, msg, score in candidates:
            if snipped_count >= max_snip_count:
                break

            total_saved_tokens += msg.token_count
            msg.content = f"[已裁剪 {msg.token_count} tokens]"
            msg.importance_score = -1.0  # 标记为已裁剪
            snipped_count += 1

        release_ratio = total_saved_tokens / l1_memory.max_tokens if l1_memory.max_tokens > 0 else 0.0
        l1_memory.total_tokens -= total_saved_tokens

        return SnipResult(
            snipped_messages=snipped_count,
            saved_tokens=total_saved_tokens,
            release_ratio=release_ratio,
            remaining_candidates=len(candidates) - snipped_count,
        )


# ============================================================
# Summarize 层：语义摘要生成
# ============================================================

SUMMARIZE_SYSTEM_PROMPT = """你是一个高效的对话摘要引擎。请将以下对话历史压缩为结构化摘要。

输出格式（JSON）：
{
  "summary": "整体要点的一句话总结",
  "key_points": ["关键点1", "关键点2"],
  "decisions": [{"what": "决定内容", "why": "决定理由"}],
  "pending": ["尚未完成的事项"],
  "important_context": "需要保留的重要上下文信息",
  "compression_ratio": "原始 / 摘要 tokens 比"
}

规则：
1. 用最少的 tokens 保留最多的信息
2. 决策和结论必须保留
3. 中间推理过程可以省略
4. 错误和异常必须标注
5. 工具调用的最终结果比过程更重要
"""

SUMMARIZE_USER_PROMPT = """请压缩以下对话历史片段（{original_tokens} tokens），生成最多 {max_summary_tokens} tokens 的摘要。

对话历史：
---
{conversation_history}
---

请输出 JSON 格式的摘要。"""


class SummarizeCompressor:
    """
    Summarize 层压缩器：用 cheap 模型生成语义摘要

    使用模型：GLM-4-flash (便宜 + 快速)
    估计成本：~0.1 元/百万 tokens
    """

    SUMMARIZE_MODEL = "glm-4-flash"
    MAX_SUMMARY_TOKENS = 300
    BATCH_SIZE = 8
    TARGET_COMPRESSION_RATIO = 0.3

    def __init__(self, model_adapter: Optional[ModelAdapter] = None):
        self.model = model_adapter or MockModelAdapter()

    async def compress_session(self, l1_memory: Any) -> SummarizeResult:
        """
        执行 Summarize 层压缩

        流程：
        1. 识别可压缩的消息范围 (最近 3 轮对话除外)
        2. 按 BATCH_SIZE 分批
        3. 每批调用 GLM-4-flash 生成摘要
        4. 用摘要替换原始消息
        """
        messages = l1_memory.messages

        compressible = self._find_compressible_range(messages)
        if not compressible:
            return SummarizeResult()

        total_saved = 0
        batch_count = 0

        for i in range(0, len(compressible), self.BATCH_SIZE):
            batch = compressible[i:i + self.BATCH_SIZE]
            if not batch:
                continue

            original_tokens = sum(getattr(msg, "token_count", 0) for msg in batch)

            # 生成摘要
            summary = await self._summarize_batch(batch)
            summary_tokens = self._estimate_tokens(summary)

            # 替换原消息为摘要
            self._replace_with_summary(l1_memory, batch, summary)

            total_saved += max(0, original_tokens - summary_tokens)
            batch_count += 1

        release_ratio = total_saved / l1_memory.max_tokens if l1_memory.max_tokens > 0 else 0.0
        l1_memory.total_tokens -= total_saved

        return SummarizeResult(
            saved_tokens=total_saved,
            batches=batch_count,
            release_ratio=release_ratio,
            cost_estimate=self._estimate_cost(total_saved),
        )

    def _find_compressible_range(self, messages: list) -> list:
        """
        找出可压缩的消息范围

        排除：最近 6 条消息、用户消息、已被 Summarize 过的消息
        """
        min_preserve = 6
        compressible = []

        for msg in messages[:-min_preserve] if len(messages) > min_preserve else []:
            if getattr(msg, "role", "") == "user":
                continue
            if getattr(msg, "importance_score", 0) == -2.0:
                continue
            compressible.append(msg)

        return compressible

    async def _summarize_batch(self, batch: list) -> str:
        """调用 cheap 模型生成批次摘要"""
        conversation_history = "\n".join(
            f"[{getattr(msg, 'role', 'unknown')}] {getattr(msg, 'content', '')[:500]}"
            for msg in batch
        )

        original_tokens = sum(getattr(msg, "token_count", 0) for msg in batch)

        prompt = SUMMARIZE_USER_PROMPT.format(
            original_tokens=original_tokens,
            max_summary_tokens=self.MAX_SUMMARY_TOKENS,
            conversation_history=conversation_history,
        )

        response = await self.model.chat(
            messages=[
                {"role": "system", "content": SUMMARIZE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.MAX_SUMMARY_TOKENS,
            temperature=0.1,
        )

        return response

    def _replace_with_summary(self, l1_memory: Any, batch: list, summary: str) -> None:
        """用摘要替换原始消息批次。

        CCR 集成: 压缩前将原始内容存入 CCRStore，摘要中嵌入 content_hash。
        LLM 后续可通过 headroom_retrieve(hash) 取回完整原文。
        """
        if not batch:
            return

        # 找到第一条消息的插入位置
        try:
            insert_pos = l1_memory.messages.index(batch[0])
        except ValueError:
            insert_pos = 0

        # CCR 可逆存储：保存原始内容
        ccr_stub = ""
        try:
            from engine.ccr_store import ccr_store
            original_text = "\n---\n".join(
                f"[{getattr(msg, 'role', 'unknown')}] {getattr(msg, 'content', '')}"
                for msg in batch
            )
            content_hash = ccr_store.store(original_text, {
                "batch_size": len(batch),
                "original_tokens": sum(getattr(msg, "token_count", 0) for msg in batch),
            })
            ccr_stub = ccr_store.make_headroom_prompt(content_hash)
        except Exception:
            pass

        summary_msg_dict = {
            "message_id": f"summary_{uuid.uuid4().hex[:8]}",
            "role": "system",
            "content": f"[上下文摘要] {summary}{ccr_stub}",
            "token_count": self._estimate_tokens(summary),
            "importance_score": -2.0,  # Summarize 特殊标记
            "timestamp": datetime.now().isoformat(),
        }

        # 移除被压缩的消息
        for msg in batch:
            if msg in l1_memory.messages:
                l1_memory.messages.remove(msg)

        # 插入摘要消息 (使用简单 dict 代替 ChatMessage，避免循环导入)
        # 实际集成时会使用 ChatMessage dataclass
        from services.memory.l1_session_memory import ChatMessage
        summary_msg = ChatMessage(
            message_id=summary_msg_dict["message_id"],
            role=summary_msg_dict["role"],
            content=summary_msg_dict["content"],
            token_count=summary_msg_dict["token_count"],
            importance_score=summary_msg_dict["importance_score"],
        )
        l1_memory.messages.insert(insert_pos, summary_msg)

    def _estimate_tokens(self, text: str) -> int:
        """估算 token 数量 (中文: 1 字符 ≈ 1.5 tokens)"""
        if not text:
            return 0
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars * 0.5)

    def _estimate_cost(self, saved_tokens: int) -> float:
        """估算压缩成本 (元) - GLM-4-flash 约 0.1 元/百万 tokens"""
        return saved_tokens * 0.1 / 1_000_000


# ============================================================
# 质量验证
# ============================================================

class QualityValidator:
    """
    压缩后质量验证器

    确保压缩后不丢失关键信息
    """

    CRITICAL_KEYWORDS = [
        "bug", "错误", "失败", "异常", "危险",
        "API Key", "密钥", "密码",
        "删除", "不可恢复", "永久",
    ]

    def validate_compression(
        self,
        original_contents: List[str],
        compressed_contents: List[str],
        compression_type: str,
    ) -> ValidationResult:
        """
        验证压缩后的上下文是否保留了关键信息

        Args:
            original_contents: 原始消息内容列表
            compressed_contents: 压缩后消息内容列表
            compression_type: 压缩类型 ('budget' | 'snip' | 'summarize')
        """
        issues = []

        # 1. 检查关键信息
        for keyword in self.CRITICAL_KEYWORDS:
            original_has = any(keyword in c for c in original_contents)
            compressed_has = any(keyword in c for c in compressed_contents)

            if original_has and not compressed_has:
                issues.append(f"关键词 '{keyword}' 在压缩后丢失")

        # 2. 检查压缩比
        original_total = sum(len(c) for c in original_contents)
        compressed_total = sum(len(c) for c in compressed_contents)
        ratio = compressed_total / original_total if original_total > 0 else 0.0

        if compression_type == "summarize" and ratio > 0.5:
            issues.append(f"Summarize 压缩比仅 {ratio:.0%}，未达预期 50%+")

        if ratio > 0.8:
            issues.append(f"压缩比 {ratio:.0%} 过低，压缩效果不明显")

        return ValidationResult(
            passed=len(issues) == 0,
            issues=issues,
            compression_ratio=ratio,
        )


# ============================================================
# 压缩效果度量
# ============================================================

class CompressionMetrics:
    """压缩效果度量"""

    def __init__(self):
        self.events: List[CompressionMetricsEvent] = []

    def record(self, report: CompressionReport) -> None:
        """记录一次压缩事件"""
        self.events.append(CompressionMetricsEvent(
            level=report.level,
            pre_tokens=report.pre_tokens,
            post_tokens=report.post_tokens,
            saving_ratio=report.saving_ratio,
            actions=[a.type for a in report.actions],
        ))

    def get_summary(self, period_hours: int = 24) -> MetricsSummary:
        """获取过去 N 小时的压缩效果摘要"""
        now = datetime.now()
        cutoff = now.timestamp() - period_hours * 3600

        recent = [
            e for e in self.events
            if e.timestamp.timestamp() >= cutoff
        ]

        if not recent:
            return MetricsSummary.empty()

        total_saved = sum(e.pre_tokens - e.post_tokens for e in recent)
        avg_ratio = sum(e.saving_ratio for e in recent) / len(recent)

        return MetricsSummary(
            total_compressions=len(recent),
            total_tokens_saved=total_saved,
            avg_saving_ratio=avg_ratio,
            budget_triggers=sum(1 for e in recent if "budget" in e.actions),
            snip_triggers=sum(1 for e in recent if "snip" in e.actions),
            summarize_triggers=sum(1 for e in recent if "summarize" in e.actions),
            cost_saved=total_saved * 1.0 / 1_000_000,  # DeepSeek 约 1 元/百万 tokens
        )


# ============================================================
# 压缩引擎配置
# ============================================================

@dataclass
class CompressionConfig:
    """压缩引擎可配置参数"""

    # Token 阈值
    WARN_THRESHOLD: float = 0.60
    BUDGET_THRESHOLD: float = 0.80
    SNIP_THRESHOLD: float = 0.90
    SUMMARIZE_THRESHOLD: float = 0.90

    # Budget 层配置
    budget_max_result_length: int = 2000
    budget_preview_head: int = 500
    budget_preview_tail: int = 500

    # Snip 层配置
    snip_score_threshold: float = 0.5
    snip_max_ratio: float = 0.30
    snip_preserve_recent: int = 6

    # Summarize 层配置
    summarize_model: str = "glm-4-flash"
    summarize_max_tokens: int = 300
    summarize_batch_size: int = 8
    summarize_target_ratio: float = 0.30

    # 频率控制
    min_interval_seconds: int = 30

    @classmethod
    def from_workspace_config(cls, config: Dict) -> 'CompressionConfig':
        """从工作间配置加载"""
        return cls(
            WARN_THRESHOLD=config.get("warn_threshold", 0.60),
            BUDGET_THRESHOLD=config.get("budget_threshold", 0.80),
            SUMMARIZE_THRESHOLD=config.get("summarize_threshold", 0.90),
        )


# ============================================================
# 压缩引擎主控
# ============================================================

class CompressionEngine:
    """
    上下文压缩引擎主控

    在每个对话回合后检查 Token 阈值，自动触发相应级别压缩
    """

    def __init__(
        self,
        config: Optional[CompressionConfig] = None,
        model_adapter: Optional[ModelAdapter] = None,
    ):
        self.config = config or CompressionConfig()
        self.budget = BudgetCompressor()
        self.snip = SnipCompressor()
        self.summarize = SummarizeCompressor(model_adapter)
        self.metrics = CompressionMetrics()
        self.validator = QualityValidator()

        # 更新 Budget 参数
        self.budget.MAX_RESULT_LENGTH = self.config.budget_max_result_length
        self.budget.PREVIEW_HEAD = self.config.budget_preview_head
        self.budget.PREVIEW_TAIL = self.config.budget_preview_tail

        # 更新 Snip 参数
        self.snip.SNIP_THRESHOLD = self.config.snip_score_threshold
        self.snip.MAX_SNIP_RATIO = self.config.snip_max_ratio

    async def check_and_compress(self, l1_memory: Any) -> CompressionReport:
        """
        检查 Token 使用量并执行对应级别压缩

        调用时机：
        - 每次用户消息发送后 (异步)
        - 每次 tool_result 返回后 (异步)
        - 断线重连恢复时 (同步)

        Returns:
            CompressionReport: 压缩报告，包含操作详情和 UI 更新信息
        """
        report = CompressionReport(
            level=l1_memory.compression_level,
            pre_tokens=l1_memory.total_tokens,
        )

        usage_ratio = l1_memory.total_tokens / l1_memory.max_tokens if l1_memory.max_tokens > 0 else 0.0

        # 60% 预警
        if usage_ratio >= self.config.WARN_THRESHOLD:
            if l1_memory.compression_level < 1:
                l1_memory.compression_level = 1
                report.level = 1
                report.warnings.append("上下文使用超过 60%")

        # 80% Budget 截断
        if usage_ratio >= self.config.BUDGET_THRESHOLD:
            if l1_memory.compression_level < 2:
                result = self.budget.apply_to_session(l1_memory)
                l1_memory.compression_level = 2
                report.level = 2
                report.actions.append(CompressionAction(
                    type="budget",
                    saved_tokens=result.total_saved_tokens,
                    details=result,
                ))

        # 90% Snip + Summarize
        if usage_ratio >= self.config.SUMMARIZE_THRESHOLD:
            if l1_memory.compression_level < 3:
                # 先 Snip
                snip_result = self.snip.execute(l1_memory)
                report.actions.append(CompressionAction(
                    type="snip",
                    saved_tokens=snip_result.saved_tokens,
                    details=snip_result,
                ))

                # 再 Summarize (如果 Snip 后仍超 90%)
                current_ratio = l1_memory.total_tokens / l1_memory.max_tokens if l1_memory.max_tokens > 0 else 0.0
                if current_ratio >= self.config.SUMMARIZE_THRESHOLD:
                    summarize_result = await self.summarize.compress_session(l1_memory)
                    report.actions.append(CompressionAction(
                        type="summarize",
                        saved_tokens=summarize_result.saved_tokens,
                        details=summarize_result,
                    ))

                l1_memory.compression_level = 3
                report.level = 3

        report.post_tokens = l1_memory.total_tokens
        report.total_saved = report.pre_tokens - report.post_tokens
        report.saving_ratio = report.total_saved / report.pre_tokens if report.pre_tokens > 0 else 0.0

        # 记录度量
        self.metrics.record(report)

        return report

    def on_reconnect(
        self,
        l1_memory: Any,
        last_session_context: Dict,
    ) -> Any:
        """
        断线重连时的上下文恢复

        流程：
        1. 从 L2 获取上次会话的结构化摘要
        2. 保留最近 3 轮完整对话
        3. 组合为新的 L1 上下文
        """
        from services.memory.l1_session_memory import ChatMessage, estimate_tokens

        summary = last_session_context.get("summary", "")
        recent_messages = last_session_context.get("recent_messages", [])

        # 注入摘要作为 system 消息
        if summary:
            l1_memory.messages.insert(0, ChatMessage(
                role="system",
                content=f"[从上次会话恢复] {summary}",
                token_count=estimate_tokens(summary),
                importance_score=0.8,
            ))

        # 添加最近的用户消息
        for msg_data in recent_messages[-6:]:
            if isinstance(msg_data, dict):
                l1_memory.messages.append(ChatMessage(**msg_data))

        return l1_memory


# ============================================================
# 便捷函数
# ============================================================

def create_default_engine(
    model_adapter: Optional[ModelAdapter] = None,
    config: Optional[Dict] = None,
) -> CompressionEngine:
    """创建默认压缩引擎"""
    compression_config = CompressionConfig.from_workspace_config(config) if config else CompressionConfig()
    return CompressionEngine(
        config=compression_config,
        model_adapter=model_adapter,
    )
