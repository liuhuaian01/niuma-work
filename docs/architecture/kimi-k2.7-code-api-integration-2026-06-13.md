# Kimi K2.7 Code API 接入方案

> 版本：v1.0 | 日期：2026-06-13

## 一、接入概述

| 维度 | 值 |
|------|-----|
| 模型 | `kimi-k2.7-code` |
| API 格式 | 完全兼容 OpenAI Chat Completions |
| Base URL | `https://api.moonshot.cn/v1` |
| 上下文 | 256K tokens |
| 定价 | 输入 ~$0.95/1M | 输出 ~$4/1M |
| 认证 | API Key（环境变量 `MOONSHOT_API_KEY`） |
| SDK | Python `openai>=1.0` / Node.js `openai` |

## 二、注册 & 获取 API Key

```
1. 访问 https://platform.kimi.com
2. 注册/登录（手机号）
3. 进入 https://platform.kimi.com/console/api-keys
4. 创建 API Key → 复制保存
5. 充值（按量计费）
```

## 三、Python 接入代码（超级牛马适配层）

```python
# models/kimi_k27.py
import os
import json
from openai import OpenAI

class KimiK27CodeClient:
    """Kimi K2.7 Code API 客户端 — 超级牛马编程 Sub-Agent"""

    def __init__(self, api_key=None, base_url="https://api.moonshot.cn/v1"):
        self.client = OpenAI(
            api_key=api_key or os.environ.get("MOONSHOT_API_KEY"),
            base_url=base_url
        )
        self.model = "kimi-k2.7-code"
        self.total_tokens = 0  # 用量追踪
    
    def chat(self, messages, tools=None, max_tokens=32768):
        """标准对话"""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        
        response = self.client.chat.completions.create(**kwargs)
        
        # 用量追踪
        usage = response.usage
        self.total_tokens += usage.total_tokens
        
        return {
            "content": response.choices[0].message.content,
            "tool_calls": response.choices[0].message.tool_calls,
            "reasoning": getattr(response.choices[0].message, "reasoning_content", None),
            "usage": {
                "input": usage.prompt_tokens,
                "output": usage.completion_tokens,
                "total": usage.total_tokens
            }
        }
    
    def agent_loop(self, system_prompt, user_task, tools=None):
        """Agent 循环 — 自动处理工具调用"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_task}
        ]
        
        max_rounds = 20
        for _ in range(max_rounds):
            result = self.chat(messages, tools)
            
            if not result["tool_calls"]:
                return result["content"], self.total_tokens
            
            # 记录 assistant message
            msg = {"role": "assistant", "content": result["content"]}
            if result["reasoning"]:
                msg["reasoning_content"] = result["reasoning"]  # ⚠️ 必须保留
            if result["tool_calls"]:
                msg["tool_calls"] = result["tool_calls"]
            messages.append(msg)
            
            # 执行工具（由外部注入的工具执行器处理）
            for tc in result["tool_calls"]:
                tool_result = self._execute_tool(tc)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_result)
                })
        
        raise RuntimeError("Agent loop exceeded max rounds")
    
    def _execute_tool(self, tool_call):
        """占位 — 实际由超级牛马工具层注入"""
        return {"result": "tool_executed"}

    def get_cost(self):
        """估算费用"""
        input_cost = self.total_tokens * 0.7 * 0.95 / 1_000_000  # 70%输入
        output_cost = self.total_tokens * 0.3 * 4 / 1_000_000     # 30%输出
        return round(input_cost + output_cost, 4)
```

## 四、超级牛马多模型路由配置

```python
# config/model_router.py
MODEL_ROUTER = {
    "local": {
        "default": "deepseek-v3.2",       # Ollama 本地推理
        "flash": "deepseek-v4-flash",      # 简单任务
        "multimodal": "qwen3.7-plus",      # 多模态
    },
    "api": {
        "kimi_k27_code": {                 # Kimi K2.7 Code（新增）
            "provider": "moonshot",
            "model": "kimi-k2.7-code",
            "base_url": "https://api.moonshot.cn/v1",
            "scenarios": ["code", "mcp_tool_use", "complex_debug"],
            "priority": 1,                  # 复杂编程场景次选
            "fallback": "deepseek-v3.2",    # 降级到本地
        },
        "deepseek_v4": {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "base_url": "https://api.deepseek.com/v1",
            "scenarios": ["code", "chat", "research", "agent"],
            "priority": 0,                  # 默认首选
        }
    }
}

def route_model(task_type, prefer_local=True):
    """太极引擎 Smart Allocator — 模型路由"""
    if prefer_local:
        return MODEL_ROUTER["local"]["default"]
    
    # 复杂编程 → Kimi K2.7 Code（MCP Bench 81.1 > Claude Opus 76.4）
    if task_type in ["code", "mcp_tool_use", "complex_debug"]:
        return MODEL_ROUTER["api"]["kimi_k27_code"]
    
    # 其他任务 → DeepSeek
    return MODEL_ROUTER["api"]["deepseek_v4"]
```

## 五、使用场景

| 场景 | 路由 | 理由 |
|------|------|------|
| 简单问答 | DeepSeek Flash 本地 | 零成本，低延迟 |
| 日常编程 | DeepSeek V3.2 本地 | 数据不出本地 |
| **复杂代码重构** | **Kimi K2.7 Code API** | MCP Mark 81.1，超越Claude Opus |
| **多步工具编排** | **Kimi K2.7 Code API** | MCP Atlas 76.0，-30%思考Token |
| 长文档处理 | MiniMax M3 (待评估) | 1M上下文 |
| 多模态分析 | Qwen 本地 | 免费多模态 |

## 六、接入清单

| # | 事项 | 状态 | 负责 |
|:--:|------|:--:|:--:|
| 1 | 注册 Kimi 开放平台，获取 API Key | ⬜ | 刘老爷 |
| 2 | 充值（建议先充 ¥50 测试） | ⬜ | 刘老爷 |
| 3 | 实现 `KimiK27CodeClient` 类 | ⬜ | 超级牛马适配层 |
| 4 | 更新模型路由配置 | ⬜ | 超级牛马适配层 |
| 5 | 端到端测试（编程任务） | ⬜ | 自动化测试 |
| 6 | Token 用量监控看板 | ⬜ | Phase 2 |

## 七、注意事项

1. **API Key 安全**：必须本地加密存储（符合"极致安全"铁则），走环境变量或加密文件，不进代码仓库
2. **thinking 模式强制**：K2.7 Code 无法关闭思考模式，所有调用都有推理开销——简单任务不路由到此模型
3. **temperature 固定 1.0**：输出多样性不可控，不适合创意写作
4. **reasoning_content 必须保留**：多步工具调用间必须传递此字段，否则报错
5. **备用方案**：API 不可用时自动降级到 DeepSeek V3.2 本地推理
