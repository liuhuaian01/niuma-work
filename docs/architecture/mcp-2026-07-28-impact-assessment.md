# MCP 2026-07-28 RC 影响评估

> 评估日期: 2026-07-15 | RC 定稿: 2026-07-28 | 剩余: 13 天 | 状态: ✅ 评估完成

## 一句话结论

**超级牛马 MCP 实现受影响较小。** 核心改动仅在 `mcp_client.py` 的 `connect()` 握手逻辑（~30 行）。`mcp_auth` 已无状态化，`routers/mcp.py` 无会话依赖。适配工作量约 2-3 小时。

---

## 一、受影响模块清单

| 模块 | 文件 | 受影响 | 改动量 | 优先级 |
|:--|:--|:--|:--|:--|
| MCP Client 连接 | `engine/mcp_client.py` | ⚠️ 是 | ~30 行 | P0 |
| MCP 认证层 | `engine/mcp_auth.py` | ✅ 否 | 0 | — |
| MCP API 路由 | `routers/mcp.py` | ✅ 否 | 0 | — |
| MCP Server 注册表 | `engine/mcp_client.py:MCPServerRegistry` | ✅ 否 | 0 | — |

---

## 二、逐项分析

### 2.1 协议无状态化 — 移除 initialize/McP-Session-Id

**当前状态**：`mcp_client.py:158-164` 在 `connect()` 中执行标准 initialize 握手：
```python
init_response = await self._rpc_call("initialize", {
    "protocolVersion": "0.1.0",
    "capabilities": {},
    "clientInfo": {"name": "super-niuma", "version": "2.0.0"},
})
```

**2026-07-28 要求**：
- 移除 initialize/initialized 握手对
- 移除 Mcp-Session-Id 头
- 每个请求在 `_meta` 中携带协议版本+能力声明

**影响**：仅 `connect()` 方法需要重写。`_rpc_call()` 无需改（已无状态化——每次调用独立构建 JSON-RPC 请求）。

**迁移方案**：
1. 移除 initialize 握手调用
2. 在 `_rpc_call()` 的 JSON-RPC 请求体中注入 `_meta` 字段
3. `_meta` 包含：`protocolVersion: "2026-07-28"`, `clientInfo`, `capabilities`
4. `connect()` 直接调用 `_discover_tools()` 完成工具发现（server/discover）

### 2.2 路由头 — Mcp-Method/Mcp-Name 必选

**当前状态**：超级牛马 MCP 使用 stdio 子进程模式，不走 HTTP 传输。无需 HTTP 头。

**影响**：无。stdio 模式不受 HTTP 路由头影响。

### 2.3 JSON Schema 2020-12 — 工具 Schema 严格校验

**当前状态**：`mcp_client.py` 中的 `MCPTool.input_schema` 字段存储工具的输入 Schema。目前为 pass-through（不做校验）。

**影响**：低。工具 Schema 由 MCP Server 侧提供，超级牛马作为客户端不做 Schema 校验。但如果集成了外部 MCP Server，需要确认对方已适配 2020-12。

### 2.4 Roots/Sampling/Logging 弃用

**当前状态**：超级牛马未使用 Roots/Sampling/Logging 特性。

**影响**：无。12 个月缓冲期内无需行动。

### 2.5 MCP Apps 扩展

**当前状态**：未使用。

**影响**：可选。MCP Apps（Server 返回沙箱 UI）是未来的交互增强方向。P2 评估。

### 2.6 Tasks 扩展迁移

**当前状态**：未使用实验性 Tasks API。

**影响**：无。

### 2.7 认证强化 — OAuth/OIDC

**当前状态**：`mcp_auth.py` 使用自建 API Key + HMAC + 单次 Token 认证。无 OAuth/OIDC 依赖。

**影响**：低。自建认证方案不与 OAuth 增强冲突。但若未来需要对接外部 OAuth MCP Server，需补充 OAuth 支持。

### 2.8 标准化追踪 — W3C Trace Context

**当前状态**：无分布式追踪。

**影响**：可选项。P2 评估。

---

## 三、迁移计划

### Week 1 (7/14-20): 代码适配

| 日期 | 任务 | 负责人 |
|:--|:--|:--|
| 7/14 | 本评估完成 | ✅ |
| 7/15 | 评估更新 + DeepSeek V4 集成（同日完成） | ✅ |
| 7/15-16 | `mcp_client.py` 无状态化改造：移除 initialize → 注入 _meta → server/discover | 🟡 计划中 |
| 7/17-18 | 集成测试：MCP Server 注册 → 连接 → 工具发现 → 工具调用 | — |
| 7/19-20 | 降级模式（mock）兼容性验证 | — |

### Week 2 (7/21-27): 测试 + 回归

| 日期 | 任务 |
|:--|:--|
| 7/21-23 | 完整回归测试（所有 MCP 端点） |
| 7/24-25 | 旧 API deepseek-chat 停用日 — 独立验证 |
| 7/26-27 | 缓冲期，修复测试发现的任何问题 |

### 7/28: RC 定稿 → 发布

---

## 四、受影响的 API 端点

以下端点依赖 `MCPServerRegistry.connect_server()` → `MCPClient.connect()`（受影响）：

| 端点 | 方法 | 路径 | 影响 |
|:--|:--|:--|:--|
| 连接 Server | POST | `/api/v1/mcp/servers/{id}/connect` | ⚠️ |
| 工具列表 | GET | `/api/v1/mcp/servers/{id}/tools` | 间接（依赖连接） |
| 工具调用 | POST | `/api/v1/mcp/servers/{id}/call` | 间接（依赖连接） |
| 聚合工具 | GET | `/api/v1/mcp/tools` | 间接 |
| 聚合调用 | POST | `/api/v1/mcp/call` | 间接 |

**不受影响的端点**：
- Server CRUD（注册/注销/列表）
- Health/Stats（健康检查/统计）

---

## 五、风险评估

| 风险 | 等级 | 说明 |
|:--|:--|:--|
| MCP Server 兼容性 | 🟡 中 | 外部 Server 迁移到 2026-07-28 的时间线不确定，可能用到旧协议 |
| 降级模式 | 🟢 低 | mock 模式已在代码中作为 fallback |
| 认证层 | 🟢 低 | mcp_auth 已无状态化 |
| SDK v2 依赖 | 🟢 低 | 超级牛马使用自建 JSON-RPC 实现，不依赖 MCP SDK |

---

## 六、结论

- 实际影响很小：仅 `mcp_client.py connect()` 约 30 行需改动
- 无阻塞性依赖：mcp_auth、routers、MCPServerRegistry 均无会话状态
- 迁移窗口充足：14 天 → 改动只需 1 天 + 1 周测试缓冲
- 建议：7/15 开始适配，7/20 前完成测试
