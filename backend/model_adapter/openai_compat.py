"""
OpenAI 兼容协议模型适配器

支持 DeepSeek / Kimi(月之暗面) / 混元(腾讯) / GLM(智谱)
统一使用 OpenAI Chat Completions API 格式
"""

import json
import time
from typing import AsyncGenerator

import httpx

from model_adapter.base import AbstractModelAdapter
from config.settings import settings
from engine.ssrf_guard import SSRFTransport  # P1-22: SSRF 防护


class OpenAICompatAdapter(AbstractModelAdapter):
    """OpenAI 兼容协议适配器"""

    def __init__(
        self,
        model_name: str,
        api_key: str,
        base_url: str,
        display_name: str = "",
        max_context: int = 8192,
    ):
        self._model_name = model_name
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._display_name = display_name or model_name
        self._max_context = max_context
        self._fail_count = 0  # 连续失败计数
        self._last_fail_time = 0.0

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def api_base_url(self) -> str:
        return self._base_url

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def max_context(self) -> int:
        return self._max_context

    @property
    def is_configured(self) -> bool:
        """是否有 API Key 配置"""
        return bool(self._api_key)

    @property
    def fail_count(self) -> int:
        return self._fail_count

    def record_success(self):
        """记录成功调用，重置失败计数"""
        self._fail_count = 0

    def record_failure(self):
        """记录失败调用"""
        self._fail_count += 1
        self._last_fail_time = time.time()

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self, messages: list[dict], temperature: float = 0.7,
        max_tokens: int = 4096, stream: bool = False, **kwargs
    ) -> dict:
        payload = {
            "model": self._model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if kwargs.get("top_p") is not None:
            payload["top_p"] = kwargs["top_p"]
        if kwargs.get("frequency_penalty") is not None:
            payload["frequency_penalty"] = kwargs["frequency_penalty"]
        return payload

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> dict:
        """同步对话（一次性返回完整响应）"""
        if not self._api_key:
            return {"error": "API Key 未配置", "model": self._model_name}

        payload = self._build_payload(messages, temperature, max_tokens, stream=False, **kwargs)

        async with httpx.AsyncClient(
            timeout=120.0,
            transport=SSRFTransport(),  # P1-22: SSRF 防护
        ) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                self.record_success()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})

                return {
                    "content": content,
                    "model": data.get("model", self._model_name),
                    "usage": {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    },
                    "finish_reason": data["choices"][0].get("finish_reason", "stop"),
                }
            except httpx.HTTPStatusError as e:
                self.record_failure()
                # Token 用完检测：429(频率限制) / 402(欠费) / 429(额度耗尽)
                if e.response.status_code in (402, 429):
                    from model_adapter.fallback import fallback_manager
                    fallback_manager.record_quota_exhausted(self._model_name)
                return {
                    "error": f"HTTP {e.response.status_code}",
                    "detail": f"Upstream API error (status={e.response.status_code})",
                    "model": self._model_name,
                }
            except httpx.RequestError as e:
                self.record_failure()
                return {
                    "error": f"请求失败: {type(e).__name__}",
                    "detail": str(e)[:200],
                    "model": self._model_name,
                }

    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncGenerator[dict, None]:
        """流式对话（逐个 token 返回 SSE 格式事件字典）"""
        if not self._api_key:
            yield {"event": "error", "data": {"code": "MODEL_UNAVAILABLE", "message": "API Key 未配置"}}
            return

        payload = self._build_payload(messages, temperature, max_tokens, stream=True, **kwargs)

        async with httpx.AsyncClient(
            timeout=120.0,
            transport=SSRFTransport(),  # P1-22: SSRF 防护
        ) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    total_tokens = 0
                    collected_content = ""
                    real_usage = None  # 真实Token数（从usage中提取，不用chunk数冒充）

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue

                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            self.record_success()
                            # 使用API返回的真实usage，没有则fallback到chunk数
                            final_tokens = real_usage.get("total_tokens", total_tokens) if real_usage else total_tokens
                            yield {
                                "event": "done",
                                "data": {
                                    "content": collected_content,
                                    "total_tokens": final_tokens,
                                    "model": self._model_name,
                                    "finish_reason": "stop",
                                },
                            }
                            return

                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        token = delta.get("content", "")

                        # 捕获真实usage（OpenAI流式在最后一个chunk可能带usage字段）
                        if "usage" in chunk:
                            real_usage = chunk["usage"]

                        if token:
                            total_tokens += 1
                            collected_content += token
                            yield {
                                "event": "token",
                                "data": {"content": token, "index": total_tokens - 1},
                            }

                    # 如果没收到 [DONE]
                    self.record_success()
                    yield {
                        "event": "done",
                        "data": {
                            "content": collected_content,
                            "total_tokens": total_tokens,
                            "model": self._model_name,
                            "finish_reason": "stop",
                        },
                    }

            except httpx.HTTPStatusError as e:
                self.record_failure()
                yield {
                    "event": "error",
                    "data": {
                        "code": "MODEL_UNAVAILABLE",
                        "message": f"HTTP {e.response.status_code}",
                        "detail": e.response.text[:300],
                    },
                }
            except httpx.RequestError as e:
                self.record_failure()
                yield {
                    "event": "error",
                    "data": {
                        "code": "MODEL_UNAVAILABLE",
                        "message": f"请求失败: {type(e).__name__}",
                    },
                }

    async def is_available(self) -> bool:
        """检查模型是否可用（有 API Key 且未被禁用）"""
        if not self._api_key:
            return False
        if self._fail_count >= 3:
            # 5 分钟冷却期
            if time.time() - self._last_fail_time < 300:
                return False
            self._fail_count = 0  # 冷却期后重置
        return True


def create_adapters() -> dict[str, OpenAICompatAdapter]:
    """创建所有模型适配器实例（v2.1: llama.cpp server 替代 Ollama）"""
    adapters = {}

    llama_base = f"http://{settings.LLAMA_SERVER_HOST}:{settings.LLAMA_SERVER_PORT}/v1"
    llama_key = "not-needed"  # llama.cpp server 不需要 API Key

    # ── Gemma 4 系列 (Google, Apache 2.0) · llama.cpp server ──
    adapters["gemma-4-e4b"] = OpenAICompatAdapter(
        model_name="gemma-4-e4b",
        api_key=llama_key,
        base_url=llama_base,
        display_name="Gemma 4 E4B（本地）",
        max_context=131072,
    )
    adapters["gemma-4-12b"] = OpenAICompatAdapter(
        model_name="gemma-4-12b",
        api_key=llama_key,
        base_url=llama_base,
        display_name="Gemma 4 12B（本地）",
        max_context=262144,
    )
    adapters["gemma-4-26b"] = OpenAICompatAdapter(
        model_name="gemma-4-26b",
        api_key=llama_key,
        base_url=llama_base,
        display_name="Gemma 4 26B-A4B（本地）",
        max_context=262144,
    )
    adapters["gemma-4"] = adapters["gemma-4-12b"]  # 兼容旧 ID

    # ── Qwen3 千问系列 (阿里, Apache 2.0) · llama.cpp server ──
    adapters["qwen3-8b"] = OpenAICompatAdapter(
        model_name="qwen3-8b",
        api_key=llama_key,
        base_url=llama_base,
        display_name="Qwen3 8B（本地）",
        max_context=131072,
    )
    adapters["qwen3-14b"] = OpenAICompatAdapter(
        model_name="qwen3-14b",
        api_key=llama_key,
        base_url=llama_base,
        display_name="Qwen3 14B（本地）",
        max_context=131072,
    )
    adapters["qwen3-32b"] = OpenAICompatAdapter(
        model_name="qwen3-32b",
        api_key=llama_key,
        base_url=llama_base,
        display_name="Qwen3 32B（本地）",
        max_context=131072,
    )

    # DeepSeek V4 正式版（2026-07-15 已上线）
    # 峰谷定价: 工作日 9-12/14-18 价格 2x, 夜间低谷降 60%
    adapters["deepseek-v4-pro"] = OpenAICompatAdapter(
        model_name="deepseek-chat",        # V4 正式版复用同一端点，模型选择由 API 侧参数控制
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        display_name="DeepSeek V4 Pro",
        max_context=1000000,               # 1M 上下文
    )
    adapters["deepseek-v4-flash"] = OpenAICompatAdapter(
        model_name="deepseek-chat",
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        display_name="DeepSeek V4 Flash",
        max_context=1000000,               # 1M 上下文
    )

    # DeepSeek（旧接口——将于 2026-07-24 永久停用）
    # v2.0: 降级为兼容别名，实际会被 DynamicDegradationEngine 路由到 V4 Flash
    adapters["deepseek-chat"] = OpenAICompatAdapter(
        model_name="deepseek-chat",
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        display_name="DeepSeek V3 (旧, 7/24 停用→V4 Flash)",
        max_context=65536,
    )

    # Kimi (月之暗面)
    adapters["moonshot-v1"] = OpenAICompatAdapter(
        model_name="moonshot-v1-8k",
        api_key=settings.KIMI_API_KEY,
        base_url=settings.KIMI_BASE_URL,
        display_name="Kimi",
        max_context=8192,
    )

    # 混元 (腾讯)
    adapters["hunyuan-turbos"] = OpenAICompatAdapter(
        model_name="hunyuan-turbos-latest",
        api_key=settings.HUNYUAN_API_KEY,
        base_url=settings.HUNYUAN_BASE_URL,
        display_name="混元",
        max_context=32768,
    )

    # GLM (智谱)
    adapters["glm-4-flash"] = OpenAICompatAdapter(
        model_name="glm-4-flash",
        api_key=settings.GLM_API_KEY,
        base_url=settings.GLM_BASE_URL,
        display_name="GLM",
        max_context=128000,
    )

    return adapters


# ── v2.1: 动态 GGUF 模型注册 ──

_GGUF_MODEL_MAP: dict[str, tuple[str, int]] = {
    # filename_prefix → (adapter_id, max_context)
    "Qwen3-8B-":    ("qwen3-8b",  131072),
    "Qwen3-14B-":   ("qwen3-14b", 131072),
    "Qwen3-32B-":   ("qwen3-32b", 131072),
    "gemma-4-E4B-": ("gemma-4-e4b", 131072),
    "gemma-4-12B-": ("gemma-4-12b", 262144),
    "gemma-4-26B-": ("gemma-4-26b", 262144),
}


def register_local_models(models_dir: str, adapters: dict) -> int:
    """扫描 GGUF 目录，动态注册已下载的本地模型。

    返回注册成功的模型数量。
    如果 llama.cpp server 未启动，适配器仍可注册，
    但调用时会因连接失败而触发降级。
    """
    import os
    from pathlib import Path

    count = 0
    model_dir = Path(models_dir)
    if not model_dir.exists():
        return 0

    from config.settings import settings

    llama_base = f"http://{settings.LLAMA_SERVER_HOST}:{settings.LLAMA_SERVER_PORT}/v1"
    llama_key = "not-needed"

    for gguf_file in model_dir.glob("*.gguf"):
        basename = gguf_file.stem  # e.g., "Qwen3-8B-Q4_K_M"

        # 尝试匹配已知模型
        matched = False
        for prefix, (adapter_id, max_ctx) in _GGUF_MODEL_MAP.items():
            if basename.startswith(prefix):
                adapters[adapter_id] = OpenAICompatAdapter(
                    model_name=adapter_id,
                    api_key=llama_key,
                    base_url=llama_base,
                    display_name=f"{adapter_id} ({basename})",
                    max_context=max_ctx,
                )
                matched = True
                count += 1
                break

        # 未匹配的模型也注册，用文件名作为 ID
        if not matched:
            safe_id = basename.replace(".", "-").replace(" ", "-").lower()
            adapters[safe_id] = OpenAICompatAdapter(
                model_name=safe_id,
                api_key=llama_key,
                base_url=llama_base,
                display_name=f"{basename}（本地）",
                max_context=131072,
            )
            count += 1

    # 确保 gemma-4 别名指向活跃的本地模型
    if "gemma-4-12b" in adapters:
        adapters["gemma-4"] = adapters["gemma-4-12b"]
    elif "gemma-4-e4b" in adapters:
        adapters["gemma-4"] = adapters["gemma-4-e4b"]
    elif "gemma-4-26b" in adapters:
        adapters["gemma-4"] = adapters["gemma-4-26b"]

    return count
