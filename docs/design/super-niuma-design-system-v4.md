# Super Niuma v4.0 前端 UI/UX 设计系统文档

> 版本：v4.0 · 品牌：Soft Tech · 更新：2026-06-10

---

## 目录

1. [设计哲学与原则](#1-设计哲学与原则)
2. [设计 Token 系统](#2-设计-token-系统)
3. [布局架构](#3-布局架构)
4. [组件库](#4-组件库)
5. [页面设计规范](#5-页面设计规范)
6. [交互设计规范](#6-交互设计规范)
7. [模型与市场策略](#7-模型与市场策略)
8. [无障碍与性能](#8-无障碍与性能)

---

## 1. 设计哲学与原则

### 1.1 品牌定位

Super Niuma（超级牛马）是一款面向 AI 工作流的桌面级平台工具。品牌调性为 **Soft Tech** —— 紫绿色渐变核心，克制不张扬，专业但不冰冷。

### 1.2 11 条产品设计铁则

| # | 原则 | 落地表现 |
|:--|:--|:--|
| 1 | **极致安全** | 数据不出本地，Pi准则100%，API Key本地加密 |
| 2 | **极致性能** | 冷启动<1.5s，TTFB<200ms，页面切换<100ms |
| 3 | **极致轻量** | .exe<50MB，内存<200MB，零常驻 |
| 4 | **极致Token低消耗** | 国产模型优先，上下文压缩率50%+ |
| 5 | **极致高效** | 最少步骤完成任务，键盘可达率100% |
| 6 | **极致简单** | 首次使用→第一条对话<60s |
| 7 | **极致质量** | 每个功能完整闭环，不交付半成品 |
| 8 | **极致审美** | 5色克制色板，动画60fps，干净不脏 |
| 9 | **极致体验** | 反馈<100ms，无打断感 |
| 10 | **极致交互** | 所见即所得，直接操作不中转 |
| 11 | **极致克制（Pi原则）** | 不该做的坚决不做 |

### 1.3 调性关键词

- **干净** — 无冗余装饰
- **安静** — 色彩不喧嚣
- **流动** — 过渡自然，无割裂感
- **可信** — 信息层次清晰，操作结果确定

---

## 2. 设计 Token 系统

### 2.1 色板

#### 品牌主色

| Token | 色值 | 用途 |
|:--|:--|:--|
| `--brand` | `#6c5ce7` | 主按钮、链接、品牌标识 |
| `--brand-hover` | `#5a4bd1` | 主按钮悬停 |
| `--brand-muted` | `rgba(108,92,231,.06)` | 浅色品牌背景 |
| `--brand-glow` | `rgba(108,92,231,.12)` | 发光效果 |

#### 语义辅助色

| Token | 色值 | 用途 |
|:--|:--|:--|
| `--accent` | `#00cec9` | 成功状态、强调色 |
| `--coral` | `#ff6b6b` | 错误/警告/删除 |
| `--green` | `#10b981` | 安全状态、在线标识 |
| `--blue` | `#3b82f6` | 信息提示、链接 |
| `--yellow` | `#fdcb6e` | 警告状态 |

#### 中性色（Text/Border/Background）

| Token | Light | Dark | 用途 |
|:--|:--|:--|:--|
| `--text` | `#18181f` | `#eeeef8` | 主文字 |
| `--text2` | `#5a5a6e` | `#9898b8` | 辅助文字 |
| `--text3` | `#7a7a90` | `#787898` | 三级文字 |
| `--text-dim` | `#b8b8cc` | `#484868` | 占位/禁用文字 |
| `--bg` | `#f8f9fb` | `#0a0a1a` | 主背景 |
| `--bg-alt` | `#f2f3f8` | `#0e0e22` | 次背景 |
| `--bg-card` | `#fff` | `#14142c` | 卡片背景 |
| `--bg-glass` | `rgba(255,255,255,.8)` | `rgba(20,20,44,.88)` | 玻璃面板 |
| `--border` | `rgba(0,0,0,.055)` | `rgba(108,92,231,.12)` | 边框 |
| `--border-light` | `rgba(0,0,0,.035)` | `rgba(108,92,231,.07)` | 浅边框 |

### 2.2 字体系统

```css
--ff: "Inter","Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif;
--ff-display: "Outfit","PingFang SC",sans-serif;
--ff-mono: "JetBrains Mono","SF Mono","Cascadia Code",monospace;
```

| 场景 | 字体 | 级数 |
|:--|:--|:--|
| 页面标题、Hero 数字 | `ff-display` (Outfit) | |
| 正文、标签、按钮 | `ff` (Inter + Noto Sans SC) | |
| 代码、数据 | `ff-mono` (JetBrains Mono) | |

**字号体系（基于 11px = --fs-xs）：**

| Token | 大小 | 用途 |
|:--|:--|:--|
| `--fs-xs` | 11px | 辅助信息、标签 |
| `--fs-sm` | 13px | 正文、列表项 |
| `--fs-md` | 15px | 导航标题、卡片标题 |
| `--fs-lg` | 20px | 页面大标题 |
| `--fs-xl` | 24px | Hero 标题 |
| `--fs-2xl` | 30px | 统计数字 |

### 2.3 间距系统（4px 基准）

| Token | 值 | 用途 |
|:--|:--|:--|
| `--r-sm` | 6px | 小圆角：标签、徽章 |
| `--r-md` | 12px | 中圆角：卡片、输入框 |
| `--r-lg` | 18px | 大圆角：面板、弹窗 |
| `--r-full` | 9999px | 圆形：头像、药丸按钮 |

**页面级间距：**
- 页面内边距：24px
- 卡片间距：8-12px
- 区块间距：24px

### 2.4 阴影系统

| Token | 值 | 场景 |
|:--|:--|:--|
| `--shadow-sm` | `0 1px 3px rgba(0,0,0,.04)` | 卡片默认 |
| `--shadow` | `0 2px 12px rgba(0,0,0,.05)` | 卡片悬停 |
| `--shadow-lg` | `0 8px 32px rgba(108,92,231,.08)` | 弹窗、下拉菜单 |

### 2.5 动效系统

| Token | 值 | 用途 |
|:--|:--|:--|
| `--ease` | `cubic-bezier(.16,1,.3,1)` | 标准过渡（弹性出口） |
| `--spring` | `cubic-bezier(.34,1.56,.64,1)` | 弹性动画（弹窗入场） |

**动效原则：**
- 页面切换：无动画（即时显示）
- 卡片悬停：`.2s` 平滑过渡
- 微交互反馈：`.15s` 即时响应
- 支持 `prefers-reduced-motion`：全部动画可关闭

---

## 3. 布局架构

### 3.1 整体框架

```
┌────┬────────────┬──────────────────────────────┐
│    │            │                              │
│ Nav│  Sidebar   │        Main Content          │
│ 56 │   260px    │          flex:1              │
│ px │ (仅对话页) │                              │
│    │            │                              │
│    │            │                              │
└────┴────────────┴──────────────────────────────┘
```

**4 列布局（仅在 Chat 页面）：**
1. **Nav（56px）** — 左侧固定导航栏，垂直图标排列
2. **Sidebar（260px）** — 对话列表，仅 Chat 页面显示
3. **Main（flex:1）** — 主内容区，承载所有页面
4. **Panel（380px）** — 右侧滑出面板（文件/日历/设置）

**非 Chat 页面：** Sidebar 隐藏，Main 区全宽显示。

### 3.2 页面容器规范

```css
.app {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.page {
  display: none;
  flex-direction: column;
  flex: 1;
  overflow-y: auto;
}

.page.active {
  display: flex !important;
}
```

### 3.3 办公室页面特殊布局（3:2 比例）

```
┌─────────────────────┬──────────────┐
│                     │   Token      │
│   Isometric Scene   │   安全       │
│   5 个工作室同框    │   对话       │
│   flex: 3           │   工作室     │
│                     │   最近       │
│                     │   flex: 2    │
└─────────────────────┴──────────────┘
```

- 场景区 `flex:3`，面板区 `flex:2`
- 面板 `min-width:280px; max-width:420px`
- 场景内含 800×520 SVG 等距插画，自动缩放

---

## 4. 组件库

### 4.1 卡片（Card）

**基础卡片：**
```css
.card {
  padding: 14px 16px;
  border-radius: var(--r-md);
  border: 1px solid var(--border);
  background: var(--bg-card);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: all .2s var(--ease);
}

.card:hover {
  border-color: var(--border-focus);
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}

.card:active {
  transform: translateY(0);
}
```

**统一规则（全站 7 种卡片均遵循）：**
- 默认：`bg-card` + `shadow-sm` + 1px 边框
- 悬停：`translateY(-2px)` + `border-focus` + `shadow`
- 过渡：`.2s var(--ease)`

**卡片变体：**

| 变体 | 使用页面 | 特征 |
|:--|:--|:--|
| `.card` | 通用 | 基础卡片 |
| `.workspace-card` | 工作室 | 大型封面卡，含图标+名称+描述 |
| `.plaza-card` | 广场 | 中型列表卡，含图标+名称+作者+安装按钮 |
| `.plaza-fcard` | 广场 | 特色卡，含左色条+标签组 |
| `.task-item` | 任务 | 紧凑行，含复选框+名称+截止日期 |
| `.agent-item` | 设置 | Agent 列表行，含头像+名称+角色 |
| `.file-item` | 文件 | 文件行，含图标+名称+大小 |

### 4.2 按钮（Button）

```css
.btn-primary {
  /* 品牌紫色填充 */
  background: var(--brand);
  color: #fff;
}

.btn-ghost {
  /* 透明背景，仅 hover 显示底色 */
  background: transparent;
}

.btn-ghost:hover {
  background: var(--bg-hover);
}
```

**状态：**
- Default / Hover / Active（scale(.98)）/ Disabled（opacity:.6）/ Focus-visible（2px outline）

### 4.3 导航栏（Nav）

- 宽度：56px（固定）
- 每项：34×34px 图标按钮，`var(--r-sm)` 圆角
- 激活态：品牌色 + 品牌浅底色 + 左侧 3px 渐变色条
- 悬停态：浅灰底色 + 文字变亮
- Tooltip：伪元素实现，悬停延迟显示
- 分隔线：20px 宽 1px 高

### 4.4 页面头部（Page Header）

```css
.page-header {
  padding: 14px 24px;
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-card);
  flex-shrink: 0;
}
```

- 统一高度：含 padding 约 46px
- 标题：`ff-display` / `fs-md` / `700` / 字间距 `-.01em`
- 右侧：操作按钮区（flex-end 对齐）

### 4.5 搜索栏（Page Search）

```css
.page-search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: var(--r-md);
  background: var(--bg-input);
  border: 1px solid var(--border);
  margin: 12px 24px;
}

.page-search:focus-within {
  border-color: var(--border-focus);
}
```

### 4.6 标签页（Tab Bar）

```css
.tab-bar {
  display: flex;
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
}

.tab-btn {
  padding: 10px 16px;
  font-size: var(--fs-xs);
  color: var(--text2);
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.tab-btn.active {
  color: var(--brand);
  border-bottom-color: var(--brand);
}
```

### 4.7 状态栏（Status Bar）

```css
.statusbar {
  height: 28px;
  padding: 0 16px;
  font-size: 11px;
  color: var(--text3);
  border-top: 1px solid var(--border-light);
  background: var(--bg-glass);
}
```

### 4.8 Toast 通知

- 位置：右下角固定
- 动画：`toastIn`（滑入）250ms + `toastOut`（滑出）300ms
- 最大 4 条，超出自动移除最早的
- 4 种类型：`ok`（✓）、`err`（✕）、`warn`（⚠）、`info`（ℹ）

### 4.9 Modal 弹窗

- 遮罩：`rgba(0,0,0,.25)` + `backdrop-filter:blur(4px)`
- 内容：`bg-card` + `r-lg` 圆角 + `shadow-lg`
- 入场动画：`scaleIn` 弹簧曲线
- 点击遮罩关闭

### 4.10 开关（Toggle）

```css
.toggle {
  width: 40px;
  height: 22px;
  border-radius: 11px;
  background: var(--border);
  cursor: pointer;
}

.toggle.on {
  background: var(--accent);
}
```

### 4.11 上下文栏（Context Bar）

- 位置：输入框上方
- 分段色条展示上下文窗口占用
- 显示百分比

---

## 5. 页面设计规范

### 5.1 页面总览

| 页面 | ID | 类型 | 渲染方式 |
|:--|:--|:--|:--|
| 对话 | `page-chat` | 核心功能 | JS 动态渲染 |
| 连接管理 | `page-connections` | 设置类 | 静态 HTML |
| 办公室 | `page-office` | 仪表盘 | JS + 静态 HTML |
| 工作室大厅 | `page-workspace` | 功能入口 | JS 动态渲染 |
| 工作室详情 | `page-workspace-detail` | 详情 | JS 动态渲染 |
| 广场 | `page-plaza` | 市场 | 静态 HTML |
| 记忆 | `page-memory` | 内容浏览 | 静态 HTML + Tab |
| 文件 | `page-files` | 文件管理 | 静态 HTML |
| 任务 | `page-tasks` | 任务管理 | 静态 HTML |
| 设置 | `page-settings` | 系统配置 | JS 动态渲染 |

### 5.2 对话页（Chat）

**布局：** Sidebar + Chat Area + Input Area

**消息气泡：**
- 用户：`--bubble-user` 底色，右对齐
- AI：`--bubble-ai` 底色，左对齐，支持 Markdown 渲染
- 动画：`msgIn` 上浮淡入
- 操作栏：hover 显示（复制/重新生成）

**输入区：**
- 多行 textarea，自动扩展
- 工具栏：文件上传、模型选择、语音输入、发送按钮
- 上下文窗口指示条

**空白引导：**
- 首次使用：欢迎消息 + Chips 快捷入口
- 统计：技能数、安全评分、平均延迟

### 5.3 办公室页（Office）

**设计参照：** Marvis（腾讯）— 等距 3D 办公场景 + 右侧面板

**场景 SVG（800×520）：**
- 5 个工作室同框等距视图
- Marvis 主控（中）、Code Studio（左上）、Browse Studio（右上）、Data Studio（左下）、File Studio（右下）
- 每个工作室独立配色：紫/蓝/绿/琥珀/玫红
- 动画：浮动 + 屏幕发光 + 粒子流转（reduced-motion 可关闭）
- 连接线：虚线表示 Agent 间通信
- 装饰：时钟、植物

**右侧面板内容：**
1. Token 消耗 — 大数字 + 进度条 + 模型状态
2. 安全中心 — 色点 + 标签（Pi 100%、数据不出本地、沙箱隔离）
3. 对话统计 — 进行中/已完成/总计
4. 工作室在线 — 5 行列表（头像+名称+描述+绿点）
5. 最近对话 — 标题 + 时间戳

### 5.4 广场页（Plaza）

**头部：** 紫绿渐变 Hero Banner + 分类筛选 + 搜索

**内容区三大板块：**

1. **🧠 预装模型（2×2 网格）**
   - Gemma-4-12B（绿色，Google，12B，GGUF Q4）
   - DeepSeek V3.2（紫色，深度求索，671B MoE，128K 上下文）
   - DeepSeek-R1 Writer（珊瑚色，逻辑推理+小说创作，CoT 链式思考）
   - Qwen 多模态（蓝色，阿里通义，图文理解，开源免费）
   - 每张卡片：左色条 + 图标 + 名称 + 标签组 + 模型大小 + "已安装 ✓"

2. **🧠 开源模型市场（网格列表）**
   - Llama 4 Scout / Mistral 3 Small / Yi-1.5-9B / GLM-4-9B / MiniCPM-V-2.6 / InternLM3-8B
   - 点击「安装」→ 进度条动画 → 「已安装 ✓」

3. **热门技能与 Agent（网格列表）**
   - 网文创作、视频制作、Sub-Agent 模板、备份与迁移等

### 5.5 记忆页（Memory）

**Tab 结构：** 日记 | 梦境 | 长期记忆

- **日记：** 日历视图（每月格子 + 标记）+ 时间线列表
- **梦境：** 左侧色条卡片 + 元数据（日期/类型/置信度）
- **长期记忆：** 分类卡片（用户画像/项目约定/安全策略）

### 5.6 文件页（Files）

**筛选 Chip：** 全部 / 模型 / 日志 / 导出

**内容分组：**
1. 预装模型 — 4 行（Gemma / DeepSeek V3.2 / DeepSeek-R1 / Qwen），标注"预装"
2. 已安装模型 — 从广场安装的模型（空态引导）
3. 导出 — 对话总结、周报等
4. 日志 — Hermes 运行日志
5. 磁盘使用 — 环形图表

### 5.7 任务页（Tasks）

**筛选：** 全部 / P0 / P1 / P2 / 已完成

**Tab：** 任务列表 | 历史任务

**每行：**
- 复选框（点击切换完成状态）
- 任务名称 + 优先级标签（P0 红色 / P1 黄色 / P2 默认）
- 截止日期
- 操作：批量完成、同步、快速添加

### 5.8 设置页（Settings）

**布局：** 左侧导航 + 右侧内容（`display:flex; flex:1`）

**导航项：** 通用设置 / 用量统计 / 技能管理 / 远控通道 / 备份与迁移 / 关于我们

**通用设置内容：**
- 个人资料卡（头像+手机号）
- 外观（深色模式开关、字体大小滑块）
- Hermes Agent 状态（版本、技能数、自动启动开关）
- 默认模型选择（卡片列表，选中态边框高亮）
- 可选功能（记忆增强、对话总结、上下文压缩）

### 5.9 连接管理页（Connections）

**分类：** 全部 / 文档知识 / 办公协同 / 开发工具

**已连接：** 企业微信、TAPD、GitHub（每行含 Toggle 开关）

**可用服务：** 腾讯文档、飞书、腾讯 IMA（"连接"按钮）

### 5.10 工作室页（Workspace）

**Hero Banner：** `brand→accent` 渐变 + 几何装饰 + 标题 + 创建按钮

**统计行（3 列）：** 在线 Agent / 活跃对话 / Token 消耗
- Token 列使用品牌渐变文字（`background-clip:text`）

**内容：** 活跃 Agent 列表 + 工作室卡片网格

---

## 6. 交互设计规范

### 6.1 页面切换

- 机制：纯 CSS class toggle（`display:none` ↔ `display:flex`）
- 无过渡动画（即时切换，避免浏览器动画重启 Bug）
- 侧栏仅在 Chat 页面显示

### 6.2 导航反馈

- 点击：即时 class 切换 + 左侧色条指示
- 键盘：可聚焦，Enter/Space 触发

### 6.3 卡片交互

**统一步骤：**
1. Default：静态卡片
2. Hover：`translateY(-2px)` + 边框高亮 + 阴影
3. Active：`translateY(0)`（按下反馈）
4. Click：导航或执行操作

**列表项交互：**
- Hover：浅底色（`bg-hover`）
- Active：无 transform（节省性能）

### 6.4 输入交互

- Chat textarea：Enter 发送，Shift+Enter 换行
- 搜索框：即时过滤，无按钮触发
- Toggle：点击切换，视觉状态同步

### 6.5 弹窗交互

- Modal：点击遮罩关闭
- Panel：点击遮罩关闭，右侧滑入（`.35s spring`）
- Profile Card：点击头像弹出，失焦/点击关闭

### 6.6 键盘快捷键

- `⌘K` / `Ctrl+K` — 命令面板
- `Enter` — 发送消息（Chat）
- `Escape` — 关闭弹窗/面板
- `Tab` — 焦点导航

### 6.7 反馈时间标准

| 操作 | 反馈时间 | 反馈形式 |
|:--|:--|:--|
| 页面切换 | <100ms | 即时显示 |
| 按钮点击 | <50ms | 视觉状态变化 |
| Toast 通知 | 2.6s 后自动消失 | 右下角滑入 |
| 安装模型 | 模拟 3-5s 进度条 | 百分比 + 完成通知 |
| 消息发送 | <100ms | 气泡立即出现 |

### 6.8 空态设计

- 对话页：欢迎卡片 + Chips 快捷入口
- 文件页：「尚无手动安装的模型 · 前往广场浏览」
- 记忆页：日历默认显示当月
- 任务页：默认显示 3 条示例任务

### 6.9 错误处理

- 后端未连接：状态栏显示连接状态，`checkHermes()` catch 兜底
- 模型安装失败：Toast 错误提示
- 搜索无结果：「未找到匹配结果」

---

## 7. 模型与市场策略

### 7.1 部署分级

| 级别 | 模型 | 部署方式 | 目的 |
|:--|:--|:--|:--|
| **内置** | Gemma-4-12B, DeepSeek V3.2, DeepSeek-R1, Qwen 多模态 | 安装包预装 | 开箱即用 |
| **市场** | Llama 4, Mistral 3, Yi-1.5, GLM-4, MiniCPM-V, InternLM3 | 按需下载 | 节约安装包体积 |

### 7.2 安装交互

1. 用户浏览广场 → 点击「安装」
2. 按钮变为百分比进度（模拟 3-5s）
3. 进度条动画填充
4. 完成：按钮变为「已安装 ✓」+ Toast 通知
5. 状态持久化到 localStorage

### 7.3 文件页同步

- 预装模型显示在"预装模型"区，标签为「预装」
- 市场安装的模型显示在"已安装模型"区
- 磁盘图表实时反映占用

---

## 8. 无障碍与性能

### 8.1 无障碍

- 所有交互元素可键盘聚焦（`tabindex="0"`）
- `:focus-visible` 提供 2px 品牌色轮廓
- 语义化 HTML（`<main>`、`<aside>`、`<nav>`、`aria-label`、`role`）
- 支持屏幕阅读器（`aria-live` 消息区域）

### 8.2 响应式

```css
@media (max-width: 768px) {
  .sidebar { display: none !important; }
  .main { margin-left: 0; }
  .panel { --panel-w: 100vw; }
}

@media (max-width: 480px) {
  .nav { width: 44px; }
  .page-header { padding: 8px 10px; }
}
```

### 8.3 动效控制

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    transition-duration: .01ms !important;
  }
}

@media (prefers-reduced-motion: no-preference) {
  /* 仅在此处启用场景动画 */
}
```

### 8.4 性能指标

- **零 CDN 依赖**（已移除 Google Fonts，使用系统字体栈）
- **CSS 总体积** ~61KB（未压缩，含所有页面样式）
- **页面切换** <100ms（纯 CSS class toggle）
- **首次内容绘制** <500ms（跳过 splash 后即时显示）
- **滚动** 使用硬件加速（`transform` 而非 `top/left`）

### 8.5 字体回退策略

```
Outfit → PingFang SC → sans-serif          (display)
Inter → Noto Sans SC → PingFang SC → Microsoft YaHei → sans-serif  (body)
JetBrains Mono → SF Mono → Cascadia Code → monospace  (code)
```

---

## 附录 A：页面 ID 与路由映射

| 页面 | page Id | go() 参数 | nav data-page |
|:--|:--|:--|:--|
| 对话 | `page-chat` | `'chat'` | `chat` |
| 连接管理 | `page-connections` | `'connections'` | `connections` |
| 办公室 | `page-office` | `'office'` | `office` |
| 工作室大厅 | `page-workspace` | `'workspace'` | `workspace` |
| 工作室详情 | `page-workspace-detail` | `'workspace-detail'` | — |
| 广场 | `page-plaza` | `'plaza'` | `plaza` |
| 记忆 | `page-memory` | `'memory'` | `memory` |
| 文件 | `page-files` | `'files'` | `files` |
| 任务 | `page-tasks` | `'tasks'` | `tasks` |
| 设置 | `page-settings` | `'settings'` | `settings` |

## 附录 B：文件结构

```
niuma-ui-v4.0-soft-tech.html    # 单文件 HTML（CSS + JS 内联）
├── <style>                     # 约 61KB CSS
├── <div class="app">           # 整体框架
│   ├── <nav>                   # 左侧导航
│   ├── <aside class="sidebar"> # 对话列表
│   ├── <main class="main">     # 10 个页面
│   │   ├── #page-chat
│   │   ├── #page-connections
│   │   ├── #page-office        # 含 800×520 SVG 场景
│   │   ├── #page-workspace
│   │   ├── #page-workspace-detail
│   │   ├── #page-plaza
│   │   ├── #page-memory
│   │   ├── #page-files
│   │   ├── #page-tasks
│   │   ├── #page-settings
│   │   └── .statusbar
│   └── <aside class="panel">   # 右侧面板
├── <div class="backdrop">
├── <div class="profile-card">
├── <div class="modal-mask">
├── <div class="toast-container">
├── <div class="palette">       # Cmd+K 命令面板
├── <div id="splash">           # 启动画面
└── <script>                    # 约 500 行 JS
    └── const N = { ... }       # 全局命名空间
```

---

> 本文件是 Super Niuma v4.0 前端 UI/UX 设计的权威参考文档。所有视觉实现应以此为基准，确保跨页面一致性和设计语言统一。
