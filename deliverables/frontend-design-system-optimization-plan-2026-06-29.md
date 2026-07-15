# 超级牛马 前端UI与设计系统 深度优化迭代方案

> 方案日期：2026-06-29  
> 方案作者：前端&设计系统综合审计团队  
> 基线文档：差距审计 2026-06-26 + 设计系统评估 v5.7 + UX 架构 v2.0  
> 审计范围：前端 3 HTML（~22,600行）+ 设计系统 5 CSS（~7,850行）+ 后端 60+ API + 交付物 4 文档

---

## 一、核心结论

**超级牛马前端当前处于"原型验证完成、亟需工程化重构"的关键节点。**

三份审计交叉印证了同一个核心矛盾：

| 维度 | 现有状态 | 核心问题 |
|:--|:--|:--|
| **设计系统** | 评分 78/100，Token 架构 95 分 | 与前端脱节，未被任何页面引用 |
| **前端代码** | 3 个独立 HTML 单体，~22,600 行 | 无构建系统，CSS 严重重复，品牌色 6 版本 |
| **后端 API** | 60+ 端点，SSE 流式对话完备 | 仅 4 个端点有前端对接，20+ 能力沉睡 |
| **UX 架构** | v2.0 已定义 8 页结构 + 8 条铁则 | 完全未落地，仍是纸上方案 |

**一句话判断：设计系统很强，前端原型很完整，但两者没有连接。现在需要的不是另起炉灶，而是"收敛 + 重构 + 落地"。**

---

## 二、当前状态全景图

### 2.1 设计系统成熟度矩阵

```
Token 架构:  ████████████████████░  95/100  ← 行业优秀
组件覆盖度:  █████████████████░░░░  85/100  ← 良好，缺对话核心组件
视觉一致性:  ██████████████████░░░  90/100  ← 优秀，玻璃态统一语言
可访问性:    ███████████░░░░░░░░░  55/100  ← 严重短板
响应式适配:  ██████████████░░░░░░░  70/100  ← 有断点无系统方案
设计文档化:  ████████████░░░░░░░░  60/100  ← 缺独立组件 API 文档
品牌表达:    █████████████████░░░░  88/100  ← 良好，品牌色 6 版本微差
────────────────────────────────────────
综合评分:    ████████████████░░░░░  78/100
```

### 2.2 前端代码健康度

| 指标 | 数值 | 评级 |
|:--|:--|:--|
| 文件数量 | 3 HTML + 2 JS = 5 文件 | 🟡 极少但单体巨大 |
| 最大文件 | 19,027 行（原型） | 🔴 严重超标 |
| CSS 重复率 | ~500 行 Token 定义 × 3 = 全部重复 | 🔴 严重 |
| 构建系统 | 无（零配置文件） | 🔴 致命 |
| 模块系统 | IIFE 全局挂载（无 ES Module） | 🔴 严重 |
| DS 引用率 | 0%（无页面 link 引用 DS CSS） | 🔴 致命 |
| 状态覆盖 | 25 项缺失 | 🟡 需补全 |
| 可访问性 | 零 | 🔴 致命 |
| Mock 耦合 | 全部页面内联 mock | 🟡 阻碍生产 |

### 2.3 API 对接覆盖率

```
已对接  ████████░░░░░░░░░░░░  4/60+  (7%)
未对接  ████████████████████  56/60+ (93%)
```

仅 Chat（发消息/流式/历史）、Workspace（CRUD）、Health、Models 有前端对接。记忆 L1/L2/L3、技能市场、自化引擎、仪表盘数据、审计、备份、夜巡、清风等 56 个端点无前端界面。

---

## 三、优化迭代路线图

### 总体策略：四阶段 "收敛→重构→补全→打磨"

```
Phase 0  基础就绪           Phase 1  核心链路           Phase 2  页面补全           Phase 3  体验打磨
[1-2天]                    [3-5天]                    [5-8天]                    [3-5天]
    │                         │                         │                         │
    ├─ Vue3 脚手架             ├─ 对话页完整实现           ├─ 工作室/广场/记忆/连接/设置  ├─ 骨架屏全局
    ├─ DS Token 引入           ├─ 3步引导                 ├─ Kanban 嵌入任务页       ├─ 空状态全局
    ├─ Components CSS 引入     ├─ 8图标侧栏导航            ├─ 仪表盘嵌入看板页         ├─ 错误恢复
    ├─ App Shell 布局          ├─ 模型选择器               ├─ 工作间全局切换          ├─ 键盘快捷键
    └─ 主题管理器              └─ SSE 流式对话             └─ 记忆 L1/L2/L3 面板      └─ 右键菜单
```

### 3.1 Phase 0：基础就绪（1-2 天）—— P0 致命

> **目标**：消灭"无构建系统"这一致命问题，建立前端工程化基础

| # | 任务 | 产出 | 验收标准 |
|:--:|:--|:--|:--|
| 0.1 | 搭建 Vue3 + Vite + TypeScript 项目 | 前端脚手架 | `npm run dev` 正常启动 |
| 0.2 | 引入 design-tokens.css（532行） | 全局 Token 可用 | `var(--color-brand)` 可解析 |
| 0.3 | 引入 components.css（5023行） | 组件基类可用 | `.btn`, `.card`, `.input` 样式正确 |
| 0.4 | 引入 layout-app.css（470行） | App Shell 三栏布局 | 侧栏 56px + 主区 + 可选面板 |
| 0.5 | 引入 theme-manager.js（164行） | 三主题切换 | Light/Dark/System 切换正常 |
| 0.6 | 迁移 niuma-api.js（221行）→ ES Module | API 层 TS 化 | 类型安全，可 import |
| 0.7 | 迁移 niuma-chat-bridge.js（283行）→ Vue Composable | 对话状态管理 | 响应式消息流 |

**关键决策**：
- 使用 hash 路由（`createWebHashHistory`），适配 WebView2 环境
- 所有页面在一个 SPA 内切换，无整页刷新
- CSS 加载顺序：tokens → components → layout-app → 页面样式
- 禁止内联 `<style>` 中重复定义 Token

### 3.2 Phase 1：打通核心链路（3-5 天）—— P0 产品可用

> **目标**：新用户从打开应用 → 引导 → 第一条对话 → 收到 AI 回复，全程 ≤ 60 秒

| # | 任务 | 产出 | 验收标准 |
|:--:|:--|:--|:--|
| 1.1 | **对话页完整实现** | ChatView.vue | 消息列表 + 输入框 + SSE 流式 |
| 1.2 | 3步引导流程 | OnboardingWizard.vue | ≤ 60秒完成，可跳过 |
| 1.3 | 8图标侧栏导航 | NavRail.vue + Vue Router | 8 页切换无闪烁 |
| 1.4 | 模型选择器 | ModelSelector.vue | Auto 默认 + 下拉选模型 |
| 1.5 | 消息气泡系统 | MessageBubble.vue | Markdown + 代码高亮 + 打字机 |
| 1.6 | 对话列表侧栏 | ChatList.vue | 对话项 + 搜索 + 新建 |
| 1.7 | 空状态处理 | 对话引导消息 | 首次无对话时展示引导 |

**关键决策**：
- 输入框自动聚焦，不弹引导（有工作间则跳过）
- 默认模型 Auto，不弹模型选择器
- 输入区固定在底部，使用 `position: sticky`

### 3.3 Phase 2：页面补全（5-8 天）—— P1 能力释放

> **目标**：8 个页面全部可用，60+ API 端点对接率从 7% → 60%+

#### 阶段 2a：嵌入已有独立面板（2-3 天）

| # | 任务 | 父页面 | 来源 |
|:--:|:--|:--|:--|
| 2a.1 | Kanban 看板 | 任务页（TasksView.vue） | kanban-panel.html → Vue |
| 2a.2 | Token 仪表盘 | 看板页（DashboardView.vue） | token-dashboard.html → Vue |

迁移要点：
- Kanban：保留拖拽功能 + 4列状态 + 优先级标签 + Agent 头像
- 仪表盘：保留 Canvas 趋势图 + 环形图 + 数字滚动动画
- 两页的数据源从 Mock → 后端 API（`/dashboard/overview`、`/dashboard/token-trends` 等）
- 后端不可用时自动回退 Demo 数据 + 显示"演示数据"徽章

#### 阶段 2b：新建页面（3-5 天）

| # | 任务 | 产物 | 对接 API |
|:--:|:--|:--|:--|
| 2b.1 | 工作室管理页 | WorkspaceView.vue | CRUD `/workspaces`，Agent `/workspaces/{id}/agents` |
| 2b.2 | 广场页 | PlazaView.vue | `/models/marketplace`，`/skills/market`，`/skills/my` |
| 2b.3 | 记忆页 | MemoryView.vue | `/memory/l1/{ws_id}`，`/memory/l2/{ws_id}`，`/memory/l3/{ws_id}` |
| 2b.4 | 连接页 | ConnectView.vue | MCP + API Key（管理接口开发中） |
| 2b.5 | 设置页 | SettingsView.vue | `/settings`，`/settings/privacy`，`/license/status` |
| 2b.6 | 首页 | HomeView.vue | 数据聚合面板，快速入口 |

**关键决策**：
- 记忆页采用三 Tab 结构：L1 会话快照 / L2 短期档案 / L3 太虚境知识库
- 广场页三个分区：Skills（已安装 + 市场）/ Models（14个模型）/ Experts（未来）
- 设置页整合许可证、偏好、主题、隐私、关于

### 3.4 Phase 3：体验打磨（3-5 天）—— P2 完整体验

> **目标**：状态覆盖 100%，可访问性 WCAG AA 达标

| # | 任务 | 适用范围 | 验收标准 |
|:--:|:--|:--|:--|
| 3.1 | **骨架屏全局部署** | 对话/工作室/任务/广场/记忆/连接/看板 | 首屏加载 < 500ms 出现骨架 |
| 3.2 | **空状态全局覆盖** | 同上 7 页面 | 每个空状态有引导按钮 |
| 3.3 | 错误恢复三层机制 | 全局 | 自动重试→Toast+重试→Mock回退 |
| 3.4 | 键盘快捷键系统 | 全局 | Ctrl+K 搜索，Ctrl+N 新对话，Escape 关闭 |
| 3.5 | 右键菜单泛化 | 消息/卡片/文件 | 复制/删除/重新生成/导出 |
| 3.6 | 可访问性补全 | 全局 | focus-visible / aria-label / role / skip-link |
| 3.7 | prefers-reduced-motion | 全局 | 动画/过渡尊重系统偏好 |
| 3.8 | 响应式 1280px 降级 | 全局 | 1280px 以下侧栏收起，面板切换 |

---

## 四、设计系统收敛方案（同步实施）

> 此部分与 Phase 0-3 并行推进，在 Phase 0 期间完成基础收敛。

### 4.1 Token 体系统一（P0）

**当前问题**：`--color-bg-*` vs `--bg-*`、`--fw-*` vs `--weight-*`、`--dur-*` vs `--duration-*`

**方案**：在 design-tokens.css 末尾建立**映射别名层**

```css
/* 映射别名层 - 向后兼容原型旧命名 */
:root {
  /* 背景色 */
  --bg-root: var(--color-bg-root);
  --bg-surface: var(--color-bg-surface);
  --bg-card: var(--color-bg-card);
  --bg-elevated: var(--color-bg-elevated);
  --bg-input: var(--color-bg-input);
  --bg-sidebar: var(--color-bg-sidebar);
  
  /* 品牌色 */
  --brand: var(--color-brand);
  --brand-hover: var(--color-brand-hover);
  --brand-active: var(--color-brand-active);
  --brand-muted: var(--color-brand-muted);
  --brand-subtle: var(--color-brand-subtle);
  
  /* 文字 */
  --text-primary: var(--color-text-primary);
  --text-secondary: var(--color-text-secondary);
  --text-tertiary: var(--color-text-tertiary);
  
  /* 字重 */
  --weight-normal: var(--fw-normal);
  --weight-medium: var(--fw-medium);
  --weight-semibold: var(--fw-semibold);
  --weight-bold: var(--fw-bold);
  
  /* 动画时长 */
  --dur-instant: var(--dur-xs);
  --dur-fast: var(--dur-sm);
  --dur-base: var(--dur-normal);
  --dur-slow: var(--dur-lg);
  --dur-slower: var(--dur-xl);
}
```

**标准写法**：Vue 组件中强制使用新命名 `--color-*`，原型旧命名仅保留别名不删除。

**Day 主题补齐**：补充 ~30 个遗漏 Token（Silver 色系、渐变、滚动条、输入框背景）。

### 4.2 品牌色收敛（P0）

**当前 6 版本差异** → **统一为牛马蓝 `#4DA8F0`**

| 主题 | 主色 | 悬停 | 激活 | 
|:--|:--|:--|:--|
| **Night** | `#4DA8F0` | `#6BBFFC` | `#2B7AB8` |
| **Day** | `#4DA8F0`（修正，原 `#3B8FD9`） | `#3B96E0` | `#236DAE` |
| **Classic** | `#4DA8F0`（修正，原 `#467DA8`） | `#5D96C0` | `#326088` |

Day 和 Classic 主题的品牌主色修正为与 Night 一致的标准 `#4DA8F0`，仅调整 hover/active 的深浅对比度以适配各自背景。

Dashboard 的 `--brand-primary-light: #7ABEF8` 和 `--brand-primary-dark: #2E8AD8` → 替换为 DS 标准的 `--color-brand-hover` / `--color-brand-active`。

### 4.3 组件收敛（P0 + P1）

> **不新增组件**，而是将原型中已验证的组件提取到 components.css

**P0 立即提取（对话核心 13 个）**：

```
.send-btn / .input-textarea / .input-area / .input-toolbar 
.input-status-bar / .input-attach-strip / .chat-item / .chat-item__avatar
.chat-item__info / .chat-item__name / .chat-item__preview / .chat-item__meta
.chat-item__time / .chat-item__badge / .message / .msg-bubble 
.msg-avatar / .msg-content / .msg-meta / .chat-header
```

**P1 后续提取（面板 + 项目管理 10 个）**：

```
.account-panel / .side-panel / .panel-page / .panel-page-header
.page-view / .chat-search-panel / .project-card / .agent-card
.agent-info-popup / .model-dropdown
```

**P2 冗余清理（25+ 未使用组件）**：

| 组件 | 处理方式 |
|:--|:--|
| `.app-shell` | 删除（原型用 `.workspace`） |
| 营销页组件（hero/navbar/feature/pricing） | 移入独立 `marketing.css` |
| 文档展示组件（entity-card/detail-card/color-swatch） | 保留在 design-system.html 专用区 |
| 后台管理组件（data-table/pagination/breadcrumb/steps 等） | 保留在 admin-components.css |

### 4.4 组件状态补全（P0）

在 components.css 中补齐以下 25 项缺失状态：

| 组件 | 缺失状态 | 新增选择器 |
|:--|:--|:--|
| `.nav-btn` | :focus-visible, :disabled | `.nav-btn:focus-visible`, `.nav-btn:disabled` |
| `.input` | :disabled, .success | 已有，校验覆盖 |
| `.textarea` | :hover, :disabled, .error, :focus-visible | 补齐 4 个伪类 |
| `.send-btn` | :disabled, .loading | `.send-btn:disabled`, `.send-btn--loading` |
| `.btn-*` | .loading（全局） | `.btn--loading` + spinner 动画 |
| `.dropdown-item` | .loading | `.dropdown-item--loading` |
| `.task-card` | :focus-visible | `.task-card:focus-visible` |

### 4.5 新建文件：error-and-empty.css（P0）

```css
/* 空状态组件 */
.empty-state { /* icon + title + desc + action 垂直居中 */ }
.empty-state__icon { /* 品牌色 15% 透明度 */ }
.empty-state__title { /* 16px/500 */ }
.empty-state__desc { /* 13px/--color-text-secondary */ }
.empty-state__action { /* margin-top: 16px */ }

/* 错误状态组件 */
.error-state { /* 同 empty-state 布局 */ }
.error-state__icon { /* --color-error 15% */ }
.error-state__retry { /* outline 品牌色按钮 */ }
.error-state__message { /* 13px/--color-text-tertiary */ }

/* 加载骨架屏 */
.skeleton { /* shimmer 动画 + 品牌色微光 */ }
@keyframes skeleton-shimmer { /* 标准 shimmer */ }
.skeleton--text { /* 行级骨架 */ }
.skeleton--card { /* 卡片骨架 */ }
.skeleton--avatar { /* 圆形骨架 */ }
.skeleton--chart { /* 图表区域骨架 */ }
```

---

## 五、文件结构重组

### 最终目标结构

```
frontend/
├── index.html                  # SPA 入口
├── package.json                # 依赖管理
├── vite.config.ts              # 构建配置
├── tsconfig.json               # 类型配置
│
├── src/
│   ├── main.ts                 # Vue 应用入口
│   ├── App.vue                 # 根组件（App Shell）
│   ├── router/
│   │   └── index.ts            # 8 页路由配置
│   │
│   ├── views/                  # 页面组件
│   │   ├── HomeView.vue        # 首页
│   │   ├── ChatView.vue        # 对话
│   │   ├── WorkspaceView.vue   # 工作室
│   │   ├── TasksView.vue       # 任务（嵌入 Kanban）
│   │   ├── PlazaView.vue       # 广场
│   │   ├── MemoryView.vue      # 记忆
│   │   ├── ConnectView.vue     # 连接
│   │   ├── DashboardView.vue   # 看板（嵌入仪表盘）
│   │   └── SettingsView.vue    # 设置
│   │
│   ├── components/             # 共享组件
│   │   ├── NavRail.vue         # 侧栏导航
│   │   ├── ModelSelector.vue   # 模型选择器
│   │   ├── MessageBubble.vue   # 消息气泡
│   │   ├── ChatList.vue        # 对话列表
│   │   ├── OnboardingWizard.vue # 3步引导
│   │   ├── WorkspaceSelector.vue # 全局工作间选择器
│   │   ├── ThemeToggle.vue     # 主题切换
│   │   ├── ToastContainer.vue  # Toast 管理
│   │   ├── EmptyState.vue      # 通用空状态
│   │   ├── ErrorState.vue      # 通用错误状态
│   │   ├── SkeletonLoader.vue  # 通用骨架屏
│   │   └── ContextMenu.vue     # 通用右键菜单
│   │
│   ├── composables/            # 组合式函数
│   │   ├── useApi.ts           # API 调用封装（← niuma-api.js）
│   │   ├── useChat.ts          # 对话状态管理（← niuma-chat-bridge.js）
│   │   ├── useTheme.ts         # 主题管理（← theme-manager.js）
│   │   ├── useSSE.ts           # SSE 流式处理
│   │   └── useKeyboard.ts      # 键盘快捷键
│   │
│   ├── stores/                 # Pinia 状态管理
│   │   ├── workspace.ts        # 当前工作间
│   │   ├── chat.ts             # 对话消息
│   │   └── settings.ts         # 用户设置
│   │
│   ├── types/                  # TypeScript 类型
│   │   ├── api.ts              # API 响应类型
│   │   ├── chat.ts             # 消息类型
│   │   ├── workspace.ts        # 工作间类型
│   │   └── settings.ts         # 设置类型
│   │
│   └── assets/                 # 静态资源
│       └── icons/              # SVG 图标
│
├── css/                        # CSS（从 design system/ 引入）
│   ├── design-tokens.css       # L0-L2 Token（← DS v16.0，+别名层 +Day补齐）
│   ├── components.css          # 组件样式（← DS v17.0，+P0对话13组件）
│   ├── admin-components.css    # 后台组件（保留）
│   ├── layout-app.css          # App Shell 布局（保留）
│   ├── error-and-empty.css     # 空状态/错误/骨架屏（新建）
│   └── pages/
│       ├── chat.css            # 对话页专属
│       ├── tasks.css           # Kanban 专属
│       └── dashboard.css       # 仪表盘专属
│
└── public/
    └── favicon.ico
```

### 旧文件处置

| 旧文件 | 行数 | 处理 |
|:--|--:|:--|
| `niuma-neon-pulse-prototype.html` | 19,027 | 归档到 `_archive/`，拆解提取逻辑后删除 |
| `kanban-panel.html` | 1,528 | 同上 |
| `token-dashboard.html` | 1,050 | 同上 |
| `niuma-api.js` | 221 | → `src/composables/useApi.ts` |
| `niuma-chat-bridge.js` | 283 | → `src/composables/useChat.ts` |
| `theme-manager.js`（deliverables/） | 164 | → `src/composables/useTheme.ts` |
| `layout-app.css`（deliverables/） | 470 | → `frontend/css/layout-app.css` |

---

## 六、可访问性路线图

> 当前状态：55/100 → 目标：85/100（WCAG AA）

### P0 立即修复（Phase 0-1 期间）

| # | 措施 | 适用范围 |
|:--:|:--|:--|
| A1 | 所有交互组件添加 `:focus-visible` 标准样式 | 按钮/输入框/导航/卡片 |
| A2 | 自定义表单组件添加 `role` + `aria-*` | Toggle/Switch/Checkbox/Radio |
| A3 | Toggle 添加 `role="switch"` + `aria-checked` | 所有开关 |
| A4 | Modal 打开时 `aria-modal="true"` + 焦点捕获 | 所有弹窗 |
| A5 | 表单 label 使用 `<label for="...">` 关联 | 所有表单 |
| A6 | 全局 skip-link 组件 | 键盘导航 |

### P1 近期完成（Phase 2 期间）

| # | 措施 | 适用范围 |
|:--:|:--|:--|
| A7 | 所有图标按钮添加 `aria-label` | 导航/操作按钮 |
| A8 | 表格/列表添加 `role` 属性 | 数据展示 |
| A9 | Toast 添加 `aria-live="polite"` | 状态通知 |
| A10 | 颜色对比度审计（≥ 4.5:1 正文 / 3:1 大文本） | 全站 Day/Night |

### P2 持续完善（Phase 3 期间）

| # | 措施 | 适用范围 |
|:--:|:--|:--|
| A11 | 屏幕阅读器完整测试 | 所有页面 |
| A12 | 键盘导航完整路径测试 | 所有流程 |
| A13 | prefers-reduced-motion 全覆盖 | 动画/过渡/spinner/typing |

---

## 七、验收标准

### P0：不通过 = 不可发布

- [ ] 新用户打开 → 引导 → 第一条 AI 回复 ≤ 60 秒
- [ ] 8 个导航图标均可点击切换页面
- [ ] Light/Dark/System 三主题切换正常，刷新保持
- [ ] 对话 SSE 流式输出无卡顿，停止按钮可用
- [ ] 品牌色全站一致 `#4DA8F0`（含 Day/Classic 修正）
- [ ] CSS 零裸色值，100% 通过 Token 引用
- [ ] 后端不可用时页面不白屏（Mock 回退 + 提示徽章）
- [ ] `npm run build` 无错误
- [ ] 设计系统文件被前端正确引用（`<link>` 标签）

### P1：不通过 = 不可推广

- [ ] Kanban 和 Token 仪表盘功能与独立 HTML 版本一致
- [ ] 工作间切换全局生效（对话/任务/记忆跟随）
- [ ] 所有空状态有引导操作按钮
- [ ] 骨架屏在所有列表页实现
- [ ] 引导流程 ≤ 3 步且可跳过
- [ ] API 对接率 ≥ 60%（38/60+ 端点）

### P2：不通过 = 体验不完整

- [ ] 键盘快捷键可用（Ctrl+K / Ctrl+N / Escape）
- [ ] 右键菜单集成（消息/卡片/文件）
- [ ] 响应式 1280px 以下合理降级
- [ ] prefers-reduced-motion 尊重用户偏好
- [ ] WCAG AA 关键项达标（对比度 / 焦点 / aria）

---

## 八、资源估算

| 阶段 | 工时 | 人天 | 关键风险 |
|:--|:--|:--|:--|
| Phase 0：基础就绪 | 1-2 天 | 1-2 | 脚手架搭建顺畅度取决于工具链 |
| Phase 1：核心链路 | 3-5 天 | 3-5 | SSE 流式与 Vue 响应式集成是核心难点 |
| Phase 2：页面补全 | 5-8 天 | 5-8 | 60+ API 对接中部分端点可能需后端调整 |
| Phase 3：体验打磨 | 3-5 天 | 3-5 | 骨架屏 / 空状态 / 可访问性细节多 |
| 设计系统收敛 | 2-3 天 | 2-3 | 与 Phase 0 并行，Token 别名 + 组件提取 |
| **合计** | **14-23 天** | **14-23** | 总范围 3-5 周 |

### 并行化机会

- Phase 0.6-0.7（API 迁移）→ 可与 Phase 1 对话页并行
- 设计系统收敛 → 与 Phase 0 完全并行
- Phase 2a（Kanban + 仪表盘迁移）→ 可与 Phase 2b 新建页面并行（不同人）

**如果投入 2 人并行，总工期可压缩至 10-14 天。**

---

## 九、关键决策记录

| # | 决策 | 理由 | 日期 |
|:--:|:--|:--|:--|
| D1 | 前端技术栈：Vue3 + Vite + TypeScript + Pinia | UX 架构 v2.0 明确建议，生态完整 | 2026-06-29 |
| D2 | CSS 方案：保留现有 DS CSS 文件 + `<link>` 引入，不迁移到 CSS-in-JS | Token 三层体系已是行业优秀，迁移成本高且无收益 | 2026-06-29 |
| D3 | 品牌色：统一 Day/Classic 主色为 `#4DA8F0` | 原型/Kanban/Dashboard 全部事实使用此色 | 2026-06-29 |
| D4 | 路由模式：hash（`createWebHashHistory`） | WebView2 环境下 history 模式不可靠 | 2026-06-29 |
| D5 | 断点策略：1280×720 最低，不做移动端 | 桌面优先，WebView2 壳本质是桌面应用 | 2026-06-29 |
| D6 | 设计系统文件不改名、不迁移目录 | 保持 `design system/` 目录不变，前端通过相对路径引用 | 2026-06-29 |
| D7 | 不新增 npm UI 组件库（不引入 Ant Design / Element Plus） | 自有 DS v5.7 已覆盖 85% 场景，引入第三方会造成视觉分裂 | 2026-06-29 |
| D8 | 保留 Mock 回退能力 | 后端不可用时前端不白屏，是桌面应用的基本要求 | 2026-06-29 |

---

## 十、与现有文档的关系

| 文档 | 本方案的处理 |
|:--|:--|
| `design-system-gap-audit-2026-06-26.md` | ✅ P0/P1/P2 全部吸收，整合进路线图 |
| `design-system-evaluation-v5.7.md` | ✅ Token 架构评分、可访问性补全、文件组织建议全吸收 |
| `ux-architecture/01-ux-architecture-v2.0.md` | ✅ 8 页结构 + 8 条铁则 + 4 条用户旅程全部采纳 |
| `ux-architecture/02-developer-implementation-guide.md` | ✅ 阶段划分和验收标准与 UX 架构对齐 |
| `deliverables/memory-page-optimization-plan-2026-06-24.md` | ✅ 记忆页三 Tab 结构（L1/L2/L3）采纳 |
| `deliverables/PRD_Hermes_Absorption.md` | ℹ️ 参考，非直接相关 |
| `frontend/niuma-neon-pulse-prototype.html` | 🔄 将拆解为 Vue 组件后归档 |
| `frontend/kanban-panel.html` | 🔄 将迁移到 TasksView.vue 后归档 |
| `frontend/token-dashboard.html` | 🔄 将迁移到 DashboardView.vue 后归档 |

---

## 十一、立即可以开始的行动

以下 5 项无需等待任何前置条件，现在就可以启动：

1. **搭建 Vue3 脚手架** → `npm create vue@latest frontend` → 10 分钟
2. **引入 DS CSS 文件到前端** → 复制 Tokens/Components → 5 分钟
3. **Token 别名层** → 在 design-tokens.css 末尾添加 30 行映射 → 10 分钟
4. **Day 主题品牌色修正** → 改 L0 种子 1 行 → 1 分钟
5. **error-and-empty.css 新建** → 写空状态/错误/骨架屏基础样式 → 30 分钟

**建议刘老爷确认方案后，直接喊"开始"进入 Phase 0 执行。**

---

> **方案签署**：前端审计 agent ✓ | 后端审计 agent ✓ | 文档分析 ✓  
> **下一步**：确认优先级和范围 → 启动 Phase 0（Vue3 脚手架搭建 + DS 文件引入 + Token 收敛）
