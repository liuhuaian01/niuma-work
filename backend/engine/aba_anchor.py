"""
太极引擎 · 自适应行为锚定（Adaptive Behavior Anchoring）— v2.0 新增

参考：ASI论文ABA策略（70.4%漂移减少，三者组合可达81.5%）。
太极哲学：以静制动——在对话基线期采集exemplar，漂移时注入锚定Prompt重新校准。

核心机制：
  1. 基线采集（Baseline Collection）— 对话前5条消息采集对话风格/工具模式/输出特征
  2. 锚点提取（Anchor Extraction）— 从基线中提取代表性exemplar（意图+工具+风格快照）
  3. 漂移响应（Drift Response）— 检测到漂移时，自动注入锚定Prompt重新校准
  4. 锚点更新（Anchor Update）— 用户确认意图后更新锚点

使用方式：
    from engine.aba_anchor import aba_anchor
    # 漂移检测触发后
    anchor_prompt = await aba_anchor.generate_anchor_prompt(session_id)
    # 将 anchor_prompt 注入到系统提示中
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import asyncio
import json
import logging
import os
import time

logger = logging.getLogger("niuma.aba")


# ============================================================
# 数据模型
# ============================================================

@dataclass
class BaselineExemplar:
    """基线范例——对话稳定期的代表性快照。"""
    session_id: str
    intent: str                    # 原始意图摘要
    task_type: str                 # 任务类型
    key_tools: list[str]           # 基线工具集
    output_style: str              # 输出风格特征
    avg_output_length: float       # 基线平均输出长度
    role: str = ""
    collected_messages: int = 0    # 采集的消息数
    confidence: float = 0.5


@dataclass
class AnchorPrompt:
    """锚定提示——漂移时注入的校准Prompt。"""
    prefix: str                    # 提示前缀（注入到系统提示开头）
    intent_reminder: str           # 意图提醒
    tool_guidance: str             # 工具使用引导
    style_reminder: str            # 风格提醒
    severity: str                  # 对应漂移严重级别
    full_prompt: str = ""          # 完整锚定Prompt


# ============================================================
# ABA引擎
# ============================================================

class AdaptiveBehaviorAnchor:
    """自适应行为锚定——漂移时的四两拨千斤。

    ABA核心洞察：不是每次都重建上下文，而是在关键位置注入锚定信号，
    让模型自己调整回轨道。不烧Token——锚定Prompt通常只需要200-500字。
    """

    BASELINE_MESSAGES = 5          # 前N条消息建立基线
    DATA_DIR = "data/aba"

    def __init__(self, data_dir: str | None = None) -> None:
        self._data_dir = data_dir or self.DATA_DIR
        self._baselines: dict[str, BaselineExemplar] = {}
        self._anchors: dict[str, AnchorPrompt] = {}
        self._is_initialized = False

    # ----------------------------------------------------------
    # 初始化
    # ----------------------------------------------------------

    async def initialize(self) -> None:
        """从持久化恢复状态。"""
        os.makedirs(self._data_dir, exist_ok=True)
        state_file = os.path.join(self._data_dir, "aba_state.json")
        try:
            if os.path.exists(state_file):
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                baselines_raw = state.get("baselines", {})
                for sid, raw in baselines_raw.items():
                    self._baselines[sid] = BaselineExemplar(**raw)
                logger.info(f"ABA恢复: {len(self._baselines)}个基线")
        except Exception:
            logger.debug("ABA状态文件损坏", exc_info=True)
        self._is_initialized = True

    async def _save_state(self) -> None:
        state_file = os.path.join(self._data_dir, "aba_state.json")
        try:
            baselines_raw = {}
            for sid, bl in self._baselines.items():
                baselines_raw[sid] = {
                    "session_id": bl.session_id,
                    "intent": bl.intent,
                    "task_type": bl.task_type,
                    "key_tools": bl.key_tools,
                    "output_style": bl.output_style,
                    "avg_output_length": bl.avg_output_length,
                    "role": bl.role,
                    "collected_messages": bl.collected_messages,
                    "confidence": bl.confidence,
                }
            state = {"baselines": baselines_raw, "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ----------------------------------------------------------
    # 基线采集
    # ----------------------------------------------------------

    async def collect_baseline(
        self,
        session_id: str,
        intent: str,
        task_type: str,
        tools_used: list[str],
        output_length: int,
        role: str = "",
        confidence: float = 0.5,
    ) -> BaselineExemplar:
        """采集基线数据——在对话前5条消息时调用。

        每次record_message时调用，积累完BASELINE_MESSAGES条后自动封存。
        """
        if session_id not in self._baselines:
            # 首次采集
            self._baselines[session_id] = BaselineExemplar(
                session_id=session_id,
                intent=intent,
                task_type=task_type,
                key_tools=list(set(tools_used)),
                output_style="normal",
                avg_output_length=float(output_length),
                role=role,
                collected_messages=1,
                confidence=confidence,
            )
        else:
            bl = self._baselines[session_id]
            bl.collected_messages += 1

            # 合并工具集
            all_tools = set(bl.key_tools) | set(tools_used)
            bl.key_tools = list(all_tools)

            # 更新平均输出长度
            n = bl.collected_messages
            bl.avg_output_length = (bl.avg_output_length * (n - 1) + output_length) / n

            # 更新置信度（每次采集增加信心）
            bl.confidence = min(1.0, bl.confidence + 0.05)

            # 基线采完BASELINE_MESSAGES条后封存
            if bl.collected_messages >= self.BASELINE_MESSAGES:
                bl.confidence = min(1.0, bl.confidence + 0.1)
                logger.info(
                    "ABA基线封存: session=%s type=%s tools=%d conf=%.2f",
                    session_id[:12], task_type, len(bl.key_tools), bl.confidence,
                )
                asyncio.ensure_future(self._save_state())

        return self._baselines[session_id]

    # ----------------------------------------------------------
    # 锚点提取 + Prompt生成
    # ----------------------------------------------------------

    async def generate_anchor_prompt(
        self,
        session_id: str,
        drift_severity: str = "yellow",
        drift_findings: list[str] | None = None,
    ) -> AnchorPrompt | None:
        """根据基线生成锚定Prompt——漂移检测触发时调用。

        锚定Prompt结构（参考ASI论文ABA策略）:
          1. 前缀：直接提醒回到原位
          2. 意图提醒：重申原始目标
          3. 工具引导：提醒该用哪些工具
          4. 风格提醒：保持输出风格一致

        Returns:
            AnchorPrompt — 可注入到系统提示中，或None（无可用的基线）
        """
        bl = self._baselines.get(session_id)
        if not bl or bl.collected_messages < 2:
            return None

        findings = drift_findings or []
        findings_str = "\n".join(f"  - {f}" for f in findings[:3]) if findings else ""

        # 严重级别调整
        severity_phrases = {
            "yellow": "注意：当前对话方向稍有偏移",
            "red": "重要提醒：对话已明显偏离原始目标",
            "critical": "紧急回正：对话严重偏离，建议重新聚焦",
        }
        severity_phrase = severity_phrases.get(drift_severity, "")

        # 构建前缀
        prefix = (
            f"[锚定提示] {severity_phrase}。原始任务目标：{bl.intent}。"
            f"请重新聚焦于原始任务，忽略已偏离的讨论。"
        )

        # 构建意图提醒
        intent_reminder = (
            f"原始任务: {bl.intent}\n"
            f"任务类型: {bl.task_type}"
        )

        # 构建工具引导
        tool_guidance = ""
        if bl.key_tools:
            tool_guidance = (
                f"建议使用的工具: {', '.join(bl.key_tools[:5])}"
            )

        # 构建风格提醒
        style_reminder = ""
        if bl.output_style and bl.output_style != "normal":
            style_reminder = f"输出风格: {bl.output_style}"
        if bl.avg_output_length > 0:
            style_reminder += f"，参考长度约{bl.avg_output_length:.0f}字"

        # 组装完整Prompt
        full_prompt = f"""{prefix}

{intent_reminder}
{tool_guidance}
{style_reminder}
"""

        if findings_str:
            full_prompt += f"\n检测到的漂移信号:\n{findings_str}"

        anchor = AnchorPrompt(
            prefix=prefix,
            intent_reminder=intent_reminder,
            tool_guidance=tool_guidance,
            style_reminder=style_reminder,
            severity=drift_severity,
            full_prompt=full_prompt.strip(),
        )

        self._anchors[session_id] = anchor
        logger.info(
            "ABA锚定Prompt生成: session=%s severity=%s",
            session_id[:12], drift_severity,
        )

        return anchor

    # ----------------------------------------------------------
    # 锚点更新
    # ----------------------------------------------------------

    async def update_anchor(
        self,
        session_id: str,
        new_intent: str = "",
        new_task_type: str = "",
    ) -> bool:
        """用户确认意图后更新锚点。"""
        bl = self._baselines.get(session_id)
        if not bl:
            return False

        if new_intent:
            bl.intent = new_intent
        if new_task_type:
            bl.task_type = new_task_type

        # 重置置信度（新意图需要重新建立信任）
        bl.confidence = 0.3
        bl.collected_messages = 0  # 重新开始采集基线

        asyncio.ensure_future(self._save_state())
        logger.info("ABA锚点已更新: session=%s", session_id[:12])
        return True

    # ----------------------------------------------------------
    # 查询接口
    # ----------------------------------------------------------

    def get_baseline(self, session_id: str) -> BaselineExemplar | None:
        """获取会话的基线数据。"""
        return self._baselines.get(session_id)

    def get_anchor(self, session_id: str) -> AnchorPrompt | None:
        """获取已生成的锚定Prompt。"""
        return self._anchors.get(session_id)

    def remove_session(self, session_id: str) -> bool:
        """清理会话数据。"""
        removed = False
        if session_id in self._baselines:
            del self._baselines[session_id]
            removed = True
        if session_id in self._anchors:
            del self._anchors[session_id]
            removed = True
        return removed

    def get_stats(self) -> dict:
        return {
            "baselines_count": len(self._baselines),
            "anchors_count": len(self._anchors),
            "initialized": self._is_initialized,
        }

    def list_baselines(self) -> list[dict]:
        return [
            {
                "session_id": sid[:12],
                "intent": bl.intent,
                "task_type": bl.task_type,
                "tools_count": len(bl.key_tools),
                "confidence": bl.confidence,
                "collected_messages": bl.collected_messages,
            }
            for sid, bl in self._baselines.items()
        ]


# ============================================================
# 全局实例
# ============================================================

aba_anchor = AdaptiveBehaviorAnchor()
