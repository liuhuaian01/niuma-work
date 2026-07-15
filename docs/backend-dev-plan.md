# 超级牛马工作台 · 后端开发推进计划

> **日期**：2026-06-13 | **起点**：现有后端 v0.2.0 | **目标**：太极引擎 v1.6 落地
>
> 现有后端路径：`2026-05-25-22-31-58/super-niuma/src/backend/`

---

## 总览

| Phase | 目标 | 状态 | 测试 |
|:--:|:--|:--:|:--:|
| 1 | 引擎骨架 + 能力开关 | ✅ 完成 | 6/6 |
| 2 | Smart Allocator 升格 | ✅ 完成 | 5/5 |
| 3 | Token 预算 + 外网管控 | ✅ 完成 | 4/4 |
| 4 | 自愈回路 | ✅ 完成 | 5/5 |
| 5 | 五维进化日志 | ✅ 完成 | 4/5 |
| 6 | 引擎接入对话流 | ✅ 完成 | 5/5 |
| **合计** | **太极引擎 v1.6 完整落地** | **✅** | **29/29** |

### 交付物清单

```
engine/
├── taiji.py              ✅ 引擎入口（一）
├── capability_flags.py   ✅ 能力开关（天道法则）
├── smart_allocator.py    ✅ 力点探测 + SQLite历史学习（四两拨千斤）
├── token_budget.py       ✅ 预算管理 + 50/70/90%告警（刚柔并济）
├── self_healing.py       ✅ 自愈回路（无为而治）
├── execution_log.py      ✅ 执行日志（感知层）
├── reflection.py         ✅ 反思引擎 + 每日意识（生生不息）
└── chat_hooks.py         ✅ 对话流接入（万物层）

routers/
├── capabilities.py       ✅ 能力开关 API（3 endpoints）
├── governance.py         ✅ 天道法则 API（5 endpoints）
└── consciousness.py      ✅ 意识摘要 API（2 endpoints）

middleware/
└── capability_middleware.py ✅ 能力开关中间件

tests/  6 套件 · 29 项

routers/chat.py           ✅ 已接入 chat_hooks（发送前力点探测+完成后记录+异常自愈）

### 持续运营

| 机制 | 状态 |
|:--|:--:|
| 每日前沿研究（自动化） | ✅ 今天已产出 `daily-research/2026-06-13.md` |
| 研究→变更闭合链路 | ✅ 链路已建立，等首批变更 |

---

> **2026-06-13 更新**：太极引擎 v1.6 全部 6 阶段完成，29/29 测试通过。引擎层 + 接入层 + 路由整合 + 持续运营机制全部就绪。
| 4 | 自愈回路 | 2-3天 | Self-Healing Loop 最小闭环 |
| 5 | 五维进化日志 | 2-3天 | 执行→反思→传导的基础数据链路 |

---

## Phase 1：引擎骨架 + 能力开关（🔴 P0 — 今天就开工）

### 目标
在现有后端旁边建太极引擎代码骨架。不影响现有路由，两个体系并行。

### 新增文件

```
src/backend/engine/
├── __init__.py
├── taiji.py                    ← 引擎入口 taiji.one() / taiji.init()
├── capability_flags.py         ← 能力开关
└── smart_allocator.py          ← 接口定义（Phase 2 实现）
```

### 任务清单

| # | 任务 | 文件 | 说明 |
|:--:|:--|:--|:--|
| 1.1 | 创建 `engine/__init__.py` | 新文件 | 导出 `taiji` 实例 |
| 1.2 | 实现 `engine/taiji.py` | 新文件 | `TaijiEngine` 类，统一管理所有引擎组件 |
| 1.3 | 实现 `engine/capability_flags.py` | 新文件 | `CapabilityFlags` 类，提供 is_allowed/fetch/search/mcp/skills/memory 属性 |
| 1.4 | 添加中间件 `middleware/capability_middleware.py` | 新文件 | 在路由处理前检查能力开关 |
| 1.5 | 在 `main.py` 注册中间件 + 初始化引擎 | 修改 | `taiji.init()` 在应用启动时调用 |
| 1.6 | 写测试 `tests/test_capability_flags.py` | 新文件 | 验证默认关闭、用户开启、任务结束自动关 |

### 验收标准
- `taiji.init()` 在应用启动时成功初始化
- CapabilityFlags 默认值：`fetch=False, search=False, mcp=False, skills=True, memory=True`
- 默认关闭的能力在中间件层被拦截，返回 403 + 建议信息
- 用户可以临时开启任意能力，任务结束后自动恢复默认

---

## Phase 2：Smart Allocator 升格（🔴 P0）

### 目标
把 `experiments/force-detection-poc.py` 升格为正式引擎模块，替换现有硬编码降级链。

### 新增/修改文件

| # | 任务 | 文件 | 说明 |
|:--:|:--|:--|:--|
| 2.1 | 实现 `engine/smart_allocator.py` | 新文件 | 从 PoC 提取核心算法，加持久化历史数据 |
| 2.2 | 添加 `ForceProbeInput/Result` 到 `schemas/` | 修改 | Pydantic 模型定义 |
| 2.3 | 重构 `model_adapter/fallback.py` → 调用 Smart Allocator | 修改 | 删硬编码 FALLBACK_CHAIN，改为 `taiji.allocator.probe()` |
| 2.4 | 添加 Token 消耗记录到 `chat_service.py` | 修改 | 每次对话完成后记录实际消耗 |
| 2.5 | 实现 `engine/smart_allocator.py` 的历史学习 | 修改 | 每任务完成后更新该任务类型的历史成功率和平均消耗 |
| 2.6 | 写测试 `tests/test_smart_allocator.py` | 新文件 | 验证 HIGH/STANDARD/LOW 三级分配 |

### 验收标准
- 写作任务 + 高优先级 → 建议 HIGH 预算 + DeepSeek 模型
- 搜索任务 + 低优先级 + 预算紧张 → 建议 LOW 预算 + Gemma-4
- 闲聊对话 → 建议 LOW 预算
- 使用 5 条历史执行数据后，下次同类任务的分配更精准

---

## Phase 3：Token 预算 + 外网管控（🔴 P0）

### 目标
给每个 Agent 加日预算、比例告警、外网动态控制。

### 任务清单

| # | 任务 | 文件 | 说明 |
|:--:|:--|:--|:--|
| 3.1 | 扩展 `CapabilityFlags` 支持 per-agent 粒度 | 修改 | 每个 Agent 独立的能力开关 |
| 3.2 | 实现 Token 日预算追踪 | 新表或内存 | 每日重置，按 Agent 统计 |
| 3.3 | 实现 50/70/90% 比例告警 | engine/token_budget.py | 新文件 |
| 3.4 | 在 `chat_service.py` 中加入预算检查 | 修改 | 发送消息前检查预算 → 告警/暂停 |
| 3.5 | 外网访问审批流程 | 修改 routers/chat.py | web_fetch 开启前触发审批 |

### 验收标准
- Writer Agent 日预算 30K，消耗到 21K(70%)时通知用户
- 到 27K(90%)时暂停并请求用户确认
- 外网访问触发时先检查本地是否有答案

---

## Phase 4：自愈回路（📋 v1.6）

### 目标
拦截→分析意图→生成替代方案→Agent 自纠→规则沉淀。最小闭环。

### 任务清单

| # | 任务 | 文件 |
|:--:|:--|:--|
| 4.1 | 实现 `engine/self_healing.py` 拦载处理器 | 新文件 |
| 4.2 | Gate Validator FAIL → 分析失败原因 → 生成替代建议 | 新文件 |
| 4.3 | Pi 准则拦截 → 分析 Agent 意图 → 生成安全替代方案 | 修改 middleware |
| 4.4 | 沉淀策略到 L2 记忆 | 集成 memory_service |

### 验收标准
- Gate FAIL 时自动生成一条"为什么失败"的 L2 记忆
- Pi 拦截时自动生成安全替代方案而不是直接报错

---

## Phase 5：五维进化日志（📋 v2.0）

### 目标
建立"执行→沉淀→反思→传导"的数据链路。

### 任务清单

| # | 任务 | 文件 |
|:--:|:--|:--|
| 5.1 | 执行日志统一格式（元数据，不记录内容） | engine/execution_log.py |
| 5.2 | 每日反思——模式提取 | engine/reflection.py |
| 5.3 | 记忆/技能/编排/模型/安全 五维更新 | 各维度独立模块 |
| 5.4 | 生成每日意识摘要 | engine/consciousness.py |

---

## 不要动的（保持现有）

| 模块 | 原因 |
|:--|:--|
| `routers/` CRUD 路由 | 功能完整，正常工作 |
| `services/` CRUD Service | 作为"万物"层保留，后续逐步被 Engine 调用 |
| `model_adapter/` 适配器 | 保留，降级链改为 Smart Allocator 驱动 |
| `db/` 数据库 | 11 张表结构不变，按需加新表 |
| `schemas/` Pydantic 模型 | 不变，按需加 Engine 相关 schema |

---

## 节奏

```
Week 1: Phase 1 + 2 完工
  Day 1-2: 引擎骨架 + CapabilityFlags
  Day 3-5: Smart Allocator 升格 + 降级链替换

Week 2: Phase 3 + 4 完工
  Day 1-2: Token 预算 + 外网管控
  Day 3-5: 自愈回路

Week 3: Phase 5 + 回归测试
  Day 1-3: 五维进化日志
  Day 4-5: 全量回归测试 + 文档同步
```
