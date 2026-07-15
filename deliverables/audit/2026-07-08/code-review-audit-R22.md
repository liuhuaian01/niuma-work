# 超级牛马·AI WORK 代码审查审计报告 R22

**日期**: 2026-07-08 08:50 GMT+8  
**审计范围**: `E:/05-超级牛马/super-niuma/`（backend/ + frontend/ + frontend-vue/）  
**审计方法**: 反幻觉验证 / OWASP Agentic Top 10 2026 对标 / MCP Security Best Practices / NIST AI Agent Standards Initiative / 安全扫描 / 指标统计  
**上一轮**: [R21 (2026-07-08)](../2026-07-08/code-review-audit-R21.md)

---

## 总体评级: A- （R21 A → R22 A-，发现1个新P1）

| 维度 | 得分 | 说明 |
|------|------|------|
| 安全扫描 | 🟢 绿 | P0 危险调用全零，连续 16 轮零阻断 |
| 认证覆盖 | 🟢 绿 | 26/26 HTTP 路由器受保护，覆盖率 100%（P1-16 已修复） |
| 代码健康 | 🟡 黄 | P2-15 死路由仍在；frontend/public/ 存在重复文件 |
| 最佳实践 | 🟡 黄 | OWASP 4绿/6黄/0红；新增 NIST HITL/可解释性缺口 |
| 密钥管理 | 🟡 黄 | **新发现 P1-17：Agent 身份令牌签名密钥每次重启重新生成** |

**本轮关键变化**: 在 R21 基础上进行独立复核，修正 R21 两处计数误差，并新增 **P1-17 Agent 身份签名密钥不持久化** 风险。

---

## 1. 反幻觉验证——逐文件确认

> 不依赖历史报告或记忆，每次审计重新逐文件验证。R15 指标幻觉已修正，本轮同时复核 R21 指标。

### 1.1 引擎模块 (engine/)

| 指标 | 数值 | 状态 |
|------|:----:|:----:|
| 文件数 | 68 | ✅ |
| 总行数 | 23,730 | ✅ |
| 子目录 | recipes/ | ✅ |

全部 68 个 `.py` 文件逐文件确认存在且非空。最大文件：`model_router.py` (899行)、`taixu_core.py` (838行)、`context_drift.py` (811行)。

关键模块抽样验证：

| 模块 | class | def | 状态 |
|------|-------|-----|:----:|
| agent_registry.py | 2 | 16 | ✅ |
| mcp_auth.py | 2 | 12 | ✅ |
| owasp_compliance.py | 4 | 17 | ✅ |
| swarm_orchestrator.py | 2 | 20 | ✅ |
| recursive_evolution.py | 2 | 15 | ✅ |
| meta_team.py | 3 | 14 | ✅ |
| taiji_mesh.py | 4 | 22 | ✅ |
| agent_card.py | 4 | 18 | ✅ |

### 1.2 路由模块 (routers/)

| 指标 | R21 声称 | R22 复核 | 差异 |
|------|:--------:|:--------:|:----:|
| 文件数 | 33 | 33 | — |
| 总行数 | 5,408 | 5,408 | — |
| API 端点 | **181** | **186** | **+5** |

**R21 端点计数误差说明**: R21 报告统计为 181 端点，但经 `@router.(get|post|put|delete|patch|head|options)` 正则逐文件精确匹配，实际为 **186 端点**。差异原因可能是 R21 计数时遗漏了部分路由装饰器（如 `goal_loop.py` 的 12 个端点或 `agent_identity.py` 的 8 个端点）。R22 采用逐行打印验证，结果可复现。

逐文件端点数：

| 路由器 | 端点数 | 实际 URL 前缀 | 认证状态 |
|--------|:------:|--------------|:--------:|
| agent_card.py | 10 | /api/v1/agent-cards | Agent |
| agent_identity.py | 8 | /api/v1/agent-identity | Agent |
| agents.py | 4 | /api/v1/agents | Agent |
| api_keys.py | 3 | /api/v1/api-keys | Agent |
| audit.py | 2 | /api/v1/audit | Agent (P1-16 修复) |
| background_tasks.py | 5 | /api/v1/workspaces | Agent |
| backup.py | 5 | /api/v1/backup | Agent (P1-16 修复) |
| capabilities.py | 3 | /api/v1/capabilities | Agent |
| chat.py | 7 | /api/v1/chat | Agent |
| consciousness.py | 3 | /api/v1/consciousness | Agent |
| dashboard.py | 5 | /api/v1/dashboard | 公开 |
| data_lifecycle.py | 8 | /api/v1/lifecycle | **未注册（P2-15）** |
| drift.py | 7 | /api/v1/drift | Agent |
| emergence.py | 9 | /api/v1/emergence | Agent |
| evolution.py | 10 | /api/v1/evolution | Agent |
| goal_loop.py | 12 | /api/v1/goal-loop | Agent |
| governance.py | 5 | /api/v1/web-access + /api/v1/budget | Agent |
| health.py | 1 | /api/v1/health | 公开 |
| license.py | 4 | /api/v1/license | 公开 |
| mcp.py | 11 | /api/v1/mcp | MCP 令牌 |
| memory.py | 12 | /api/v1/memory | Agent |
| mesh.py | 8 | /api/v1/mesh | Agent |
| models.py | 8 | /api/v1/models | Agent |
| onboarding.py | 5 | /api/v1/onboarding | 公开 |
| patrol.py | 4 | /api/v1/patrol | Agent |
| skill_forge.py | 7 | /api/v1/skills | Agent |
| skills.py | 5 | /api/v1/skills | Agent |
| swarm.py | 2 | /api/v1/swarm | Agent |
| user_settings.py | 5 | /api/v1/settings | 公开 |
| workspace_config.py | 2 | /api/v1/workspaces | Agent |
| workspaces.py | 6 | /api/v1/workspaces | Agent |
| ws.py | 0 | /api/v1 | N/A |

### 1.3 中间件 (middleware/)

| 文件 | 行数 | 状态 |
|------|------|:----:|
| agent_auth.py | 634 | ✅ P1-16 已修复 |
| capability_middleware.py | — | ✅ |
| error_handler.py | — | ✅ |
| license_middleware.py | — | ✅ |
| rate_limit.py | — | ✅ |
| request_id.py | — | ✅ |
| request_size.py | — | ✅ |
| workspace_isolation.py | — | ✅ |
| __init__.py | 0 | ✅ |

9/9 文件真实存在。

### 1.4 安全模块真实存在性

| 模块 | 文件 | 状态 | 说明 |
|------|------|:----:|------|
| Agent 身份注册表 | engine/agent_registry.py | ✅ | P1-7 修复存在 |
| MCP 安全认证 | engine/mcp_auth.py | ✅ | P1-6 修复存在 |
| OWASP 合规 | engine/owasp_compliance.py | ✅ | ASI05/06/09 三项存在 |
| Agent 认证中间件 | middleware/agent_auth.py | ✅ | P1-12/P1-16 修复存在 |
| 工作间隔离 | middleware/workspace_isolation.py | ✅ | 存在 |
| 速率限制 | middleware/rate_limit.py | ✅ | 存在 |
| 请求大小限制 | middleware/request_size.py | ✅ | 存在 |
| 隐私同意 | engine/privacy_consent.py | ✅ | 存在 |

---

## 2. 安全扫描

### 2.1 P0 危险调用全量扫描

| 危险模式 | 命中 | 详情 |
|----------|:----:|------|
| eval() | 0 | — |
| exec() | 0 | — |
| os.system() | 0 | — |
| pickle.loads / pickle.dumps | 0 | — |
| marshal.loads | 0 | — |
| compile() | 0 | — |
| ctypes.CDLL / WinDLL | 0 | — |
| code.interact | 0 | — |
| builtins.compile | 0 | — |
| subprocess (非安全上下文) | 8 | 见下方分析 |
| __import__ | 7 | 见下方分析 |

**连续 16 轮 P0 零阻断**（R06-R22）。

#### subprocess 使用分析（均为合法上下文）

| 文件 | 行 | 用途 | 风险 |
|------|----|------|:----:|
| auto_install_hermes.py | 64,117,128,166,197 | 安装器子进程管理 | ✅ 工具脚本 |
| engine/mcp_client.py | 149 | MCP 服务器子进程管理 | ✅ 命令白名单 |
| routers/models.py | 288,382 | Ollama 模型管理 | ✅ 管理员操作 |
| engine/taiji_mesh.py | 288,314 | asyncio.subprocess 节点通信 | ✅ 受限环境 |

#### __import__ 使用分析

| 文件 | 行 | 用途 | 风险 |
|------|----|------|:----:|
| hook_registry.py | 42,69 | 动态加载 Hook 类/属性 | ✅ 内部类发现 |
| model_adapter/registry.py | 99 | `__import__("time")` | 💭 可改为 `import time` |
| routers/backup.py | 68 | `__import__('datetime')` | 💭 可改为标准 import |
| routers/dashboard.py | 33 | `__import__("datetime")` | 💭 可改为标准 import |
| tests/test_phase1_integration.py | 230 | 测试动态模块加载 | ✅ 测试代码 |
| engine/mcp_client.py | 408 | 出现在 `dangerous_patterns` 列表字符串中 | ✅ 误报 |

### 2.2 硬编码密钥扫描

扫描模式：`api_key/secret/password/token = '...'`（长度 ≥ 8）

| 文件 | 行 | 内容 | 结论 |
|------|----|------|:----:|
| backend/test_api_endpoint_validation.py | 144 | `export DEEPSEEK_API_KEY='your-key'` | ✅ 注释说明 |
| backend/engine/mcp_client.py | 71 | `api_key="sn_mcp_..."` | ✅ 文档字符串示例 |
| backend/model_adapter/openai_compat.py | 269 | `api_key="ollama"` | ✅ Ollama 占位，无真实密钥 |

**结论**: 无实际硬编码密钥。

### 2.3 SQL 注入扫描

| 文件 | 行 | 模式 | 风险 |
|------|----|------|:----:|
| engine/data_lifecycle.py | 218,226 | `f"SELECT ... FROM {table_name}"` | 🟡 表名来自内部枚举，无用户输入路径，但模式不推荐 |
| services/memory/memory_service.py | 316,324 | `_L2_COUNT_SQL.format(filters=filters)` | ✅ filters 由预定义字段名组成，用户输入参数化并转义 LIKE 通配符 |

**结论**: 无实际 SQL 注入漏洞。`data_lifecycle.py` 的 f-string SQL 为代码质量债，建议改为参数化表名白名单校验。

### 2.4 前端 XSS/危险模式扫描

对 `frontend/*.html` 扫描 `innerHTML`、`document.write`、`eval(`：

**结果**: 0 命中。

---

## 3. 行业最佳实践对标

### 3.1 OWASP Top 10 for Agentic Applications 2026

| ID | 风险 | 状态 | 现有防护 / 缺口 |
|----|------|:----:|-----------------|
| ASI01 | 提示注入 | 🟢 | mcp_client 命令白名单 + model_router 输入验证 |
| ASI02 | 不安全输出处理 | 🟡 | chat_hooks 后处理存在，但缺少 HTML/Markdown 输出消毒 |
| ASI03 | 训练/微调投毒 | 🟢 | L3 知识库隔离 + 数据溯源 |
| ASI04 | Agent 拒绝服务 | 🟡 | rate_limit 存在，但 swarm 场景缺少协同限流 |
| ASI05 | Agent 身份盗窃 | 🟢 | AgentAuthMiddleware + agent_registry 令牌管理 |
| ASI06 | 供应链漏洞 | 🟢 | MCP Server 注册白名单 + 指纹校验 |
| ASI07 | 不安全插件设计 | 🟡 | skill_forge 输入验证不足；swarm 消息认证缺失（P1-14） |
| ASI08 | 过度代理权限 | 🟡 | 能力开关 + Token 预算；但 goal-loop 允许无上限循环 |
| ASI09 | 人在回路 (HITL) | 🟡 | owasp_compliance.hitl 存在，但未与 routers 集成 |
| ASI10 | 过度依赖 | 🟡 | local_answer_check 缓解，但未强制本地验证 |

**4 绿 / 6 黄 / 0 红**（持平 R21）。

### 3.2 MCP Security Best Practices

| 实践 | 状态 | 说明 |
|------|:----:|------|
| 服务器认证 | 🟢 | AgentAuthMiddleware + MCP 单次 Token |
| 工具能力最小化 | 🟢 | 能力开关 + 外网审批 |
| 输入消毒 | 🟡 | mcp_client 有白名单，但缺少结构化输入 Schema |
| 输出限制 | 🟡 | 无工具调用结果大小上限 |
| 审计日志 | 🟢 | patrol/audit 模块记录事件 |
| 令牌轮换 | 🟢 | agent_identity revoke-token 支持 |
| 认证失败降级 | 🟡 | `MCP_ALLOW_MOCK_UNAUTHENTICATED` 默认 `true`，生产环境可能绕过认证 |

### 3.3 NIST AI Agent Standards Initiative

| 领域 | 覆盖 | 说明 |
|------|:----:|------|
| 身份与认证 | 🟢 | agent_registry + AgentAuthMiddleware |
| 可解释性 | 🟡 | emergence + execution_log 记录决策，但无终端用户解释界面 |
| 安全韧性 | 🟢 | self_healing + dynamic_degradation + failure_driver |
| 隐私保护 | 🟢 | privacy_consent + workspace_isolation |
| 人在回路 | 🟡 | HITL 模块存在，但未集成到业务路由 |
| 测试与验证 | 🟡 | 196 测试函数，但引擎模块覆盖不均（swarm 无测试） |

---

## 4. 指标统计

> **R15 指标幻觉已修正**。全部指标经反幻觉验证，排除 `.venv`/`__pycache__`/`.pytest_cache`。

### 4.1 后端规模

| 目录 | 文件数 | 行数 | 占比 |
|------|:------:|------:|-----:|
| engine/ | 68 | 23,730 | 55.7% |
| routers/ | 33 | 5,408 | 12.7% |
| services/ | 15 | 4,413 | 10.4% |
| tests/ | 26 | 3,436 | 8.1% |
| (root) | 7 | 1,593 | 3.7% |
| db/ | 5 | 1,025 | 2.4% |
| model_adapter/ | 6 | 692 | 1.6% |
| middleware/ | 9 | 634 | 1.5% |
| schemas/ | 10 | 608 | 1.4% |
| config/ | 4 | 431 | 1.0% |
| models/ | 2 | 302 | 0.7% |
| core/ | 1 | 234 | 0.5% |
| schema_migrations/ | 2 | 94 | 0.2% |
| **总计** | **188** | **42,600** | 100% |

### 4.2 引擎规模

| 指标 | 数值 |
|------|:----:|
| 引擎文件 | 68 |
| 引擎行数 | 23,730 |
| API 端点 | **186** |
| 测试文件 | 26 |
| 测试行数 | 3,436 |
| 中间件文件 | 9 |

### 4.3 前端规模

**R22 复核发现**: `frontend/public/` 目录下存在 `app.html` 和 `js/` 的重复副本，与 `frontend/` 根目录文件内容一致。实际唯一代码量低于表面统计。

| 项目 | 文件数 | 行数 | 说明 |
|------|:------:|-----:|------|
| 原型 HTML（去重后） | 4 | 21,179 | app.html + niuma-neon-pulse-prototype + kanban + token-dashboard |
| 原型 JS（去重后） | 2 | 531 | niuma-api.js + niuma-chat-bridge.js |
| Vue SPA (SFC) | 11 | 3,391 | ChatView 1,191 行 |
| Vue SPA (TS/JS/CSS) | 8 | 192 | composables + router + types + design tokens |
| **Vue 小计** | **19** | **3,583** | |

> 注：若按原始文件（含 public/ 重复）统计，前端 HTML/JS 为 61,097 行，但该数值会因重复文件重复计算而虚高。

---

## 5. 风险面板

### 🔴 P0 — 阻断级 (0)

无。连续 16 轮零阻断。

### 🟡 P1 — 应修复 (4)

| ID | 类别 | 描述 | 首次发现 |
|----|------|------|----------|
| ~~P1-16~~ | ~~认证旁路~~ | ~~audit/backup/agent-cards/lifecycle 4 个路由器认证旁路~~ | ~~R20~~ ✅ **已修复 (2026-07-08)** |
| **P1-17** | **密钥管理** | **Agent 身份注册表签名密钥每次初始化重新生成（`agent_registry.py:145` `self._secret = secrets.token_hex(32)`），未持久化。后果：后端重启后所有已签发 Agent 令牌失效；多实例部署时实例间无法互认令牌。** | **R22 新发现** |
| P1-13 | 前端工程 | Vue SPA 视图层搬运推进中。ChatView 1,191 行，其余复杂交互页面尚未完整搬运。 | R19 |
| P1-14 | Agent 安全 | Swarm 编排缺少消息级 HMAC 签名，恶意节点可冒充其他 Agent。 | R19 |
| P1-15 | 测试覆盖 | meta_team / recursive_evolution / swarm_orchestrator / engine_watchdog / closure_engine 等引擎模块无对应测试。 | R19 |

### 💭 P2 — 改进建议 (7)

| ID | 类别 | 描述 |
|----|------|------|
| P2-10 | 代码质量 | `__import__("time")` 和 `__import__("datetime")` 可改为标准 import（3 处） |
| P2-11 | 安全加固 | agent_auth 中间件采用"默认放行"策略，建议改为"默认拒绝" |
| P2-12 | 最佳实践 | MCP 工具调用缺少结果大小上限 |
| P2-13 | 文档 | 无 186 端点的完整 API 清单文档 |
| P2-14 | 可观测性 | otel_tracer 已就绪但未在 main.py 激活 |
| P2-15 | 代码健康 | `routers/data_lifecycle.py` 定义 8 个端点但未在 `main.py` 注册，属于死代码；agent_auth 已保护一个不存在的路由 |
| **P2-16** | **安全加固** | **MCP `code_execute` 工具的危险操作检测为简单字符串匹配，可被空格、换行、属性访问等绕过（如 `eval ('code')`、`getattr(__import__('os'), 'system')`）。建议改用 AST 静态分析或受限执行环境。** |

---

## 6. R15 指标幻觉问题——持续验证

**R15 问题回顾**（2026-07-01 及之前）:
- 报告声称"200+ Python 文件" → 实际 188
- 声称"60+ 引擎模块" → 实际 68
- 声称"200+ API 端点" → 实际 **186**（R21 误报为 181，R22 修正）
- 声称"Vue 完整工程" → 实际仍在搬运阶段

**R18 纠正措施**: 引入反幻觉验证 SOP——每次审计前逐文件确认，排除 `__pycache__`/.venv/migrations，使用 Python 脚本精确计数。

**R22 验证结果**:
- 后端: 188 文件 / 42,600 行（Python 逐文件计数）
- 引擎: 68 文件 / 23,730 行（与文件系统对账）
- 路由: 33 文件 / **186 端点**（正则精确匹配，修正 R21 的 181）
- 中间件: 9 文件（全部确认存在）
- 前端: 11 SFC + 8 TS/JS/CSS = 19 Vue 文件 / 3,583 行

**R21 自身误差**:
1. API 端点少计 5 个（181 vs 186）
2. 未指出 `frontend/public/` 与 `frontend/` 根目录的重复文件
3. 未识别 `agent_registry.py` 签名密钥不持久化问题

---

## 7. 新增风险详细分析

### P1-17: Agent 身份签名密钥不持久化

**位置**: `backend/engine/agent_registry.py:139-146`

```python
async def initialize(self) -> None:
    if self._initialized:
        return
    # 生成签名密钥（生产环境应持久化并在多实例间共享）
    self._secret = secrets.token_hex(32)
    self._initialized = True
```

**影响**:
- 每次后端重启都会使所有已登录 Agent 的令牌失效，用户体验差。
- 多实例/容器部署时，实例 A 签发的令牌在实例 B 上无法验证。
- 注释已明确指出这是生产环境问题，但未修复。

**建议**:
- 从环境变量 `NIUMA_AGENT_IDENTITY_SECRET` 读取密钥，或使用密钥管理服务。
- 若环境变量未设置，首次启动时生成并持久化到 `DATA_DIR/.agent_identity_secret`。
- 密钥轮换需有方案，避免直接失效所有会话。

### P2-16: MCP code_execute 危险操作检测可绕过

**位置**: `backend/engine/mcp_client.py:401-419`

当前实现使用字符串子串匹配：
```python
dangerous_patterns = [
    "os.system(", "subprocess.", "eval(", "exec(",
    "__import__(", "open(", "socket.",
    "shutil.rmtree", "os.remove(", "os.unlink(",
]
```

**可绕过方式**:
- `eval ('print(1)')` —— 函数调用加空格仍有效
- `getattr(__import__('os'), 'system')('ls')` —— 字符串拼接绕过子串检测
- `import os; os . system('ls')` —— 空白绕过
- 使用 `compile()` + `exec()` 动态生成

**建议**:
- 短期：使用 AST 解析代码，检查 `ast.Call` 节点中的函数名，并维护禁止调用集合。
- 长期：在受限执行环境（RestrictedPython / sandbox）中运行代码，或完全禁止代码执行工具。

---

## 8. 推荐操作

### 立即（本周内）
1. **[P1-17]** 持久化 Agent 身份签名密钥：从环境变量读取或首次启动后持久化到文件，避免每次重启失效。
2. **[P2-15]** 决定 `data_lifecycle` 路由器去留：要么在 `main.py` 注册，要么删除死代码和 agent_auth 中的保护条目。
3. **[P2-16]** 将 MCP `code_execute` 的字符串黑名单升级为 AST 检测。

### 短期（2 周内）
4. **[P1-14]** 为 Swarm 节点间消息添加 HMAC 签名验证。
5. **[P2-10]** 替换 3 处 `__import__` 为标准 `import`。
6. **[P2-12]** 为 MCP 工具调用添加结果大小上限。

### 中期（1 个月内）
7. **[P1-13]** 继续 Vue SPA 搬运，优先处理复杂交互页面。
8. **[P1-15]** 补充 meta_team / swarm_orchestrator / closure_engine 等引擎模块测试。
9. **[P2-11]** 考虑将 agent_auth 中间件从"默认放行"改为"默认拒绝"。
10. **[ASI09]** 将 `owasp_compliance.hitl` 集成到删除/权限变更等高风险路由。

---

## 9. 附录: 审计方法说明

| 方法 | 工具 | 用途 |
|------|------|------|
| 逐文件验证 | Python `pathlib.rglob` | 确认所有引擎/路由/中间件文件真实存在 |
| 行数精确计数 | Python `len(f.readlines())` | 排除 .venv/__pycache__/.pytest_cache |
| 端点统计 | Python `re.findall(r'@\w+\.(get\|post\|...)')` | 从路由器源码精确匹配装饰器 |
| 危险调用扫描 | Python 正则扫描 | 15 种危险模式全量扫描 |
| 认证覆盖验证 | agent_auth.py 逐路径对账 | 33 路由器 vs 保护路径前缀 |
| 未注册路由检测 | main.py include_router vs routers/ 对比 | 确认 P2-15 |

---

*审计工具: Python 3.13 精确计数 + 正则扫描 + 手动逐文件验证*  
*报告生成: 2026-07-08 08:50 GMT+8*  
*下一轮: R23 预计 2026-07-09*
