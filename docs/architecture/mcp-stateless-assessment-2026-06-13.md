# MCP 无状态化更新评估 — 超级牛马工具调用层架构调整

> 评估日期：2026-06-13 | MCP 更新日期：2026年5月（史上最大更新）

## 一、更新摘要

| 变更 | 影响级别 | 超级牛马必须跟进？ |
|------|:--:|:--:|
| 无状态核心（移除 Session） | 🔴 架构级 | 是 |
| MCP Apps（SEP-1865，工具内嵌 HTML） | 🟡 交互级 | 建议跟进 |
| Tasks 扩展（长时异步） | 🟡 能力级 | 建议跟进 |
| OpenAI Secure MCP Tunnel | 🟢 部署级 | 观察 |
| JSON Schema 2020-12 | 🟢 格式级 | 自动跟进 |
| 正式废弃旧协议（12个月缓冲） | 🟡 兼容级 | 12个月内 |

## 二、无状态核心 — 架构影响分析

### 2.1 变化

```
旧协议 (有状态):
  Client → initialize → Server
  Client → Mcp-Session-Id: abc123 → Server (绑定)
  Client → 任意请求 → 必须路由到同一实例
  
  问题: 无法水平扩展、重启丢失会话、网关路由复杂

新协议 (无状态):
  Client → 任意请求 → 任意 Server 实例
  无 initialize 握手
  无 Mcp-Session-Id
  无会话亲和性路由
  
  优势: 水平扩展、故障转移、简单网关
```

### 2.2 对超级牛马的影响

```
当前设计:
  超级牛马 → [MCP Client] → initialize → [MCP Server 1]
           └── 绑定会话 ──→ 所有后续请求 → [MCP Server 1]

需调整为:
  超级牛马 → [MCP Client] → 直接请求 → [MCP Server N]
           └── 无状态 ──→ 任意实例处理
```

### 2.3 调整方案

```python
# 旧版（有状态）
class MCPClient:
    def __init__(self):
        self.session_id = None  # ❌ 不再需要
    
    async def connect(self, server):
        result = await server.initialize()  # ❌ 不再需要
        self.session_id = result.session_id
    
    async def call_tool(self, tool_name, args):
        headers = {"Mcp-Session-Id": self.session_id}  # ❌ 不再需要
        return await self.server.call(tool_name, args, headers)

# 新版（无状态）
class MCPClient:
    def __init__(self):
        pass  # ✅ 无会话状态
    
    async def call_tool(self, server, tool_name, args):
        # ✅ 直接调用，无握手无会话
        return await server.call_tool(tool_name, args)
```

**调整工作量：移除 initialize 握手 + 移除 Session-Id 传递 = 半天。**

## 三、MCP Apps（SEP-1865）— 交互升级

### 3.1 能力

```
工具定义新增 ui 字段:
{
  "name": "file_preview",
  "ui": {
    "type": "html",
    "url": "http://server/preview.html?file=xxx"
  }
}

Host 端:
  ┌──────────────────────────────┐
  │  超级牛马 UI                  │
  │  ┌────────────────────────┐  │
  │  │  sandbox iframe        │  │
  │  │  ← Server 提供的 HTML   │  │
  │  │     文件预览/编辑/图表   │  │
  │  └────────────────────────┘  │
  └──────────────────────────────┘
```

### 3.2 超级牛马应用场景

| 场景 | MCP Apps 实现 |
|------|------|
| 文件面板预览 | Server 返回 HTML 预览器（PDF/图片/代码高亮） |
| 数据可视化 | Server 返回 Chart.js 图表 |
| 知识库浏览 | Server 返回树形浏览器 |
| 代码 Diff | Server 返回并排对比视图 |

### 3.3 实施建议

```
Phase 1（MVP）: 不引入 MCP Apps，保持文本交互
Phase 2（v1.5）: 文件面板增加 iframe 渲染能力
Phase 3（v2.0）: 全面支持 MCP Apps 协议
```

**当前影响：观察即可，不阻塞 MVP。**

## 四、Tasks 扩展 — 长时异步任务

### 4.1 协议

```
Client → Server: call_tool(long_running_task)
Server → Client: { status: "accepted", task_id: "abc" }

Client → Server: get_task_status("abc")
Server → Client: { status: "running", progress: 45% }

Client → Server: get_task_status("abc")
Server → Client: { status: "completed", result: {...} }
```

### 4.2 超级牛马应用场景

```
自动化任务 → MCP Tasks:
  每日前沿研究 → task_id → 9:00触发 → 轮询进度 → 完成通知
  知识库索引 → task_id → 后台运行 → 不阻塞前端
  大文件处理 → task_id → 异步处理 → 完成后提醒
```

### 4.3 实施建议

**当前影响**：超级牛马的自动化任务系统可以直接基于 MCP Tasks 实现，而非依赖 WorkBuddy 平台调度。

```
Priority: P1（两周内评估可行性）
工作量: 1天（协议适配 + 轮询逻辑）
```

## 五、JSON Schema 2020-12 — 工具参数定义升级

```
旧版 (draft-07):
  不支持 oneOf/anyOf/$ref
  复杂参数需要人工拆分多个工具

新版 (2020-12):
  ✅ oneOf: 参数类型联合
  ✅ anyOf: 参数多选
  ✅ $ref: 参数定义复用

示例:
{
  "type": "object",
  "properties": {
    "output_format": {
      "oneOf": [
        {"type": "string", "enum": ["json", "csv"]},
        {"type": "object", "properties": {...}}  // 自定义格式
      ]
    }
  }
}
```

**当前影响**：自动跟随，SDK 升级即可。

## 六、Secure MCP Tunnel — 企业部署

```
场景: 企业内网 MCP Server → 公网 Agent

方案: 纯出站 WebSocket 隧道
  ┌─────────────┐     出站连接     ┌─────────────┐
  │ 内网 MCP    │ ──────────────→ │ Cloudflare   │
  │ Server      │   (无入站端口)    │ Tunnel       │
  └─────────────┘                  └──────┬──────┘
                                          │
                                   ┌──────▼──────┐
                                   │ 超级牛马     │
                                   │ Agent       │
                                   └─────────────┘
```

**当前影响**：超级牛马 v1.0 本地运行不需要，v2.0 企业版部署时参考。

## 七、行动清单

| # | 事项 | 优先级 | 工作量 | 状态 |
|:--:|------|:--:|:--:|:--:|
| 1 | 移除 initialize 握手 | P0 | 半天 | ⬜ |
| 2 | 移除 Session-Id 传递 | P0 | 小时 | ⬜ |
| 3 | 更新 MCP SDK 依赖 | P0 | 小时 | ⬜ |
| 4 | 评估 MCP Tasks 集成 | P1 | 1天 | ⬜ |
| 5 | 预留 MCP Apps iframe 接口 | P2 | 半天 | ⬜ |
| 6 | 跟踪废弃时间线 | P2 | 持续 | ⬜ |

## 八、结论

**MCP 无状态化是减负而非加负。** 对超级牛马的影响是正面的——移除复杂的会话管理代码，简化工具调用层。唯一需要新增的是 Tasks 扩展（长时异步任务），但那是增值能力。

- 立即收益：代码简化（移除 50+ 行会话管理代码）
- 短期成本：半天适配
- 长期收益：水平扩展、故障转移、MCP Apps 交互升级
