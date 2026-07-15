"""
太极引擎 · OpenTelemetry 标准化追踪

将太极引擎的关键路径注入 OpenTelemetry Span，与现有 traceId/sessionId/agentId 体系对接。

设计原则：
  1. 零依赖——OpenTelemetry SDK 未安装时自动 fallback 到 no-op
  2. 非侵入——通过 context manager 和装饰器注入，不影响业务逻辑
  3. 克制——只追踪关键路径，不放大 span 爆炸

关键路径：
  - pre_chat_check → span "chat.pre_check"
  - post_chat_record → span "chat.post_record"
  - swarm.decompose → span "swarm.decompose"
  - swarm.validate_gate → span "swarm.validate_gate"
  - swarm.synthesize → span "swarm.synthesize"
  - swarm.execute_parallel → span "swarm.execute"
  - execution_log.log → span "execution.log"
  - daily_reflection → span "reflection.daily"

用法：
  from engine.otel_tracer import tracer

  with tracer.span("swarm.decompose", {"complexity": "high"}) as span:
      result = orchestrator.decompose(content)
      span.set_attribute("subtasks", len(result))
"""

from __future__ import annotations
from contextlib import contextmanager
from typing import Optional, Any
import time
import uuid
import logging

logger = logging.getLogger(__name__)

# ============================================================
# No-Op Span（OpenTelemetry 未安装时的空实现）
# ============================================================

class _NoOpSpan:
    """空 Span——零开销的 no-op 实现。"""
    def __enter__(self) -> _NoOpSpan:
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_status(self, code: int, description: str = "") -> None:
        pass

    def add_event(self, name: str, attributes: dict | None = None) -> None:
        pass

    def record_exception(self, exception: Exception) -> None:
        pass

    def end(self) -> None:
        pass


# ============================================================
# OTel Tracer——自动检测 + 优雅降级
# ============================================================

class OtelTracer:
    """OpenTelemetry 追踪器。

    自动检测 opentelemetry-api 是否安装：
      - 已安装 → 创建真实 Span
      - 未安装 → 返回 NoOpSpan（零开销）
    """

    def __init__(self) -> None:
        self._otel_available: bool | None = None
        self._tracer: Any = None
        self._otel_trace: Any = None
        self._StatusCode: Any = None

    # ------------------------------------------------------------------
    # Lazy init——首次调用时才检测 OTel
    # ------------------------------------------------------------------

    def _ensure_init(self) -> None:
        if self._otel_available is not None:
            return
        try:
            from opentelemetry import trace
            from opentelemetry.trace import StatusCode, SpanKind
            self._otel_trace = trace
            self._StatusCode = StatusCode
            self._tracer = trace.get_tracer("super-niuma.taiji", "1.6.0")
            self._otel_available = True
            logger.info("OpenTelemetry 已启用（super-niuma.taiji v1.6.0）")
        except ImportError:
            self._otel_available = False
            logger.info("OpenTelemetry 未安装，追踪已降级为 no-op")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @contextmanager
    def span(
        self,
        name: str,
        attributes: dict | None = None,
        parent_span: Any = None,
    ):
        """创建追踪 Span。

        Args:
            name: Span 名称（如 "chat.pre_check"）
            attributes: 初始属性（如 {"agent_id": "xxx"}）
            parent_span: 可选父 Span 引用

        Yields:
            真实 Span 或 NoOpSpan（降级时）
        """
        self._ensure_init()

        if not self._otel_available:
            yield _NoOpSpan()
            return

        ctx = None
        if parent_span is not None:
            from opentelemetry import trace as t
            # noinspection PyProtectedMember
            ctx = t.set_span_in_context(parent_span)

        span_instance = self._tracer.start_span(name, context=ctx)
        if attributes:
            for k, v in attributes.items():
                span_instance.set_attribute(k, str(v)[:256])

        try:
            yield span_instance
        except Exception as exc:
            span_instance.record_exception(exc)
            span_instance.set_status(
                self._StatusCode.ERROR, str(exc)[:256]
            )
            raise
        finally:
            span_instance.end()

    @contextmanager
    def root_span(
        self,
        name: str,
        agent_id: str = "",
        workspace_id: str = "",
        session_id: str = "",
    ):
        """创建带标准属性的根 Span。

        自动注入 agent_id / workspace_id / session_id / trace_id。
        """
        attrs: dict = {}
        if agent_id:
            attrs["agent.id"] = agent_id
        if workspace_id:
            attrs["workspace.id"] = workspace_id
        if session_id:
            attrs["session.id"] = session_id
        attrs["trace.id"] = str(uuid.uuid4())[:8]

        with self.span(name, attrs) as sp:
            yield sp

    def generate_trace_id(self) -> str:
        """生成本地 trace ID（即使 OTel 未安装也可用）。"""
        return str(uuid.uuid4())[:12]

    def generate_span_id(self) -> str:
        """生成本地 span ID。"""
        return str(uuid.uuid4())[:8]

    # ------------------------------------------------------------------
    # 便捷方法——用于需要手动创建 Span 的场景
    # ------------------------------------------------------------------

    def wrap(self, name: str, attrs: dict | None = None):
        """装饰器——将函数调用包装在 Span 中。

        @tracer.wrap("swarm.decompose", {"module": "swarm"})
        async def decompose(content): ...
        """
        def decorator(func):
            from functools import wraps
            import asyncio

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.span(name, attrs) as span:
                    try:
                        result = await func(*args, **kwargs)
                        span.set_attribute("status", "ok")
                        return result
                    except Exception as e:
                        span.set_attribute("status", "error")
                        span.set_attribute("error.type", type(e).__name__)
                        raise

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.span(name, attrs) as span:
                    try:
                        result = func(*args, **kwargs)
                        span.set_attribute("status", "ok")
                        return result
                    except Exception as e:
                        span.set_attribute("status", "error")
                        span.set_attribute("error.type", type(e).__name__)
                        raise

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator

    # ------------------------------------------------------------------
    # OTLP Exporter 设置（P1-3 修复）
    # ------------------------------------------------------------------

    def setup_exporter(self, endpoint: str | None = None) -> bool:
        """配置 OTLP Exporter 使 Span 落地。

        Args:
            endpoint: OTLP HTTP 端点，默认从 OTEL_EXPORTER_OTLP_ENDPOINT
                      环境变量读取，兜底 http://localhost:4318/v1/traces

        Returns:
            True 配置成功，False 降级（SDK 未安装或配置失败）
        """
        self._ensure_init()
        if not self._otel_available:
            logger.info("OTel SDK 未安装，跳过 Exporter 配置")
            return False

        try:
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )
        except ImportError:
            logger.warning(
                "OTel Exporter SDK 未安装，Span 不落地。"
                "安装: pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http"
            )
            return False

        try:
            otlp_endpoint = (
                endpoint
                or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
                or "http://localhost:4318/v1/traces"
            )
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            processor = BatchSpanProcessor(exporter)
            provider = TracerProvider()
            provider.add_span_processor(processor)
            self._otel_trace.set_tracer_provider(provider)

            # 重新获取绑定了 Exporter 的 Tracer
            self._tracer = self._otel_trace.get_tracer(
                "super-niuma.taiji", "1.6.0"
            )

            logger.info(
                "OTel Exporter 已配置 → %s · Span 将落地",
                otlp_endpoint,
            )
            return True
        except Exception as exc:
            logger.warning(
                "OTel Exporter 配置失败: %s · Span 仅内存中",
                exc,
            )
            return False

    @property
    def is_available(self) -> bool:
        """OTel 是否已安装并可用。"""
        self._ensure_init()
        return bool(self._otel_available)


# ============================================================
# 全局单例
# ============================================================

tracer = OtelTracer()
