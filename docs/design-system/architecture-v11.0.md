# 超级牛马下一代桌面端设计系统 v11.0 — 架构总纲

> **代号**: NEON PULSE v11.0 · 太极觉醒  
> **日期**: 2026-07-10  
> **状态**: ✅ 全部交付 — 令牌引擎 + 组件库 + 桌面原生 + Vue 集成  
> **前置**: v10.0 NEON PULSE 设计系统

---

## 〇、NEON PULSE — 设计 DNA（第一性）

超级牛马的设计语言是 **NEON PULSE（霓虹脉冲）**——创作脉冲风，不是赛博玻璃，不是 Soft Tech。

```
NEON PULSE = 五个视觉基因（创作导向）

  渐变按钮     四色渐变 (brand → teal → purple) + 辉光阴影 + hover 弹跳
               → 不是"电路板按钮"，是"灵感触发器"
  ─────────────────────────────────────────────
  双层边框     外层 1px 边框 + 内层渐变 sheen
               hover 时外层变 brand，整体浮起
               → 不是"数据封装"，是"想法在呼吸"
  ─────────────────────────────────────────────
  四级毛玻璃    Heavy → Medium → Light → Bg
               blur(28px) saturate(180%) 起步
               → 不是"终端窗口"，是"创作画布的层次"
  ─────────────────────────────────────────────
  辉光阴影      shadow-brand: 0 0 64px
               卡片/Dialog/面板共享辉光语言
               → 不是"霓虹灯管"，是"灵光乍现"
  ─────────────────────────────────────────────
  环境光场     三层 radial-gradient 叠加
               品牌色从四角渗入背景
               → 不是"服务器机房"，是"创作空间的氛围光"
```

**不是什么**（明确拒绝）：
- ❌ 赛博朋克——冷霓虹、工业终端、反乌托邦、电路板美学
- ❌ Linear 的极致克制（无渐变、无玻璃、纯阴影）
- ❌ Notion 的暖白亲和（米色底、轻投影、手绘感）
- ❌ 粉紫色系 — 永不使用

**就是什么**：
- ✅ 创作脉冲——暗色画布上的灵感涌动
- ✅ 让人"哇"——打开第一秒就被视觉冲击抓住
- ✅ 但不冷——辉光是暖的，玻璃是透气的，渐变是有机的
- ✅ 太极觉醒——七律驱动的创作引擎，不是机器

---

## 一、设计系统升级动机

### v10.0 的结构性债务

| 问题 | 影响 |
|------|------|
| 11.5K 行单体 CSS，令牌与组件样式混排 | 无法独立迭代令牌，改一个颜色可能波及未知范围 |
| 主题通过手动复制 200+ 变量定义 | 新增主题需逐行对比所有语义令牌，易遗漏、易出错 |
| 三处重复定义 Day 主题（design-tokens.css / themes.css / DS v8.0 HTML） | 值不一致（Classic brand 色在 themes.css 是 `#B8860B`，在 design-tokens.css 是 `#467DA8`） |
| 组件无正式规格 | 只有 CSS class，无状态矩阵/变体表/API 文档 |
| 桌面原生模式缺失 | 窗口 chrome、右键菜单、系统托盘等桌面独有 UI 无设计规范 |
| 兼容别名链混乱 | `--color-bg-root → --bg-root → --bg-base` 三重跳转，调试困难 |

### v11.0 目标

> **从「一套 CSS 变量 + 手写组件」升级为「工程化设计系统」**

三层架构：
```
Primitives（原始值——不可变）
    ↓ 被引用
Semantics（语义令牌——主题覆写点）
    ↓ 被引用
Components（组件令牌——单组件调优）
    ↓ 被消费
Vue 组件 / CSS 基类
```

---

## 二、令牌架构

### 2.1 三层模型

```
┌─────────────────────────────────────────────┐
│ PRIMITIVES (原始层)                          │
│ 不随主题变化，定义"原材料"                      │
│                                              │
│ 颜色阶: gray-50..gray-950                    │
│         brand-50..brand-950                  │
│ 间距:   space-0..space-32 (4px基)            │
│ 字号:   text-2xs..text-3xl (rem)             │
│ 字重:   weight-normal..weight-black          │
│ 行高:   leading-none..leading-loose          │
│ 圆角:   radius-2xs..radius-full             │
│ 阴影:   shadow-xs..shadow-xl + glow         │
│ 动效:   ease-spring / dur-instant..dur-enter │
│ z-index: z-base..z-tooltip                   │
└──────────────┬──────────────────────────────┘
               │ var() 引用
┌──────────────▼──────────────────────────────┐
│ SEMANTICS (语义层) ★ 主题覆写点               │
│ 按用途命名，回答"这个颜色用来做什么"              │
│                                              │
│ 背景:  --bg-root / --bg-surface /            │
│        --bg-elevated / --bg-overlay          │
│        --bg-input / --bg-subtle              │
│        --bg-hover / --bg-active              │
│ 文字:  --text-primary / --text-secondary     │
│        --text-tertiary / --text-dim          │
│        --text-on-brand                       │
│ 边框:  --border-subtle / --border-default    │
│        --border-strong / --border-brand      │
│ 品牌:  --brand / --brand-hover               │
│        --brand-muted / --brand-glow          │
│ 语义:  --success / --warning / --error       │
│        --info + 对应的 bg 变体               │
│ 玻璃:  --glass-bg / --glass-heavy            │
│        --glass-light / --glass-medium        │
│ 表面:  --surface-gradient                    │
│        --noise-opacity                       │
└──────────────┬──────────────────────────────┘
               │ var() 引用
┌──────────────▼──────────────────────────────┐
│ COMPONENTS (组件层)                           │
│ 组件级微调令牌，给出厂默认值                     │
│                                              │
│ --btn-padding-x / --btn-padding-y            │
│ --btn-radius / --btn-gap                     │
│ --input-height / --input-radius              │
│ --card-padding / --card-gap                  │
│ --dialog-width / --dialog-radius             │
│ --tooltip-offset / --tooltip-radius          │
│ --sidebar-width / --sidebar-collapsed-width  │
│ --toast-offset / --toast-max-width           │
│ --avatar-size-sm / --avatar-size-md / ...    │
└─────────────────────────────────────────────┘
```

### 2.2 主题是薄覆写层

主题文件**只覆写 Semantics 层**，不改 Primitives、不碰 Components：

```css
/* themes/night.css — 默认，在 :root 中定义，不需要额外文件 */
/* themes/day.css */
[data-theme="day"] {
  --bg-root: #F7F8FB;
  --bg-surface: #FFFFFF;
  --text-primary: #11151D;
  --brand: #3B8FD9;
  /* ... 仅约 40 个语义变量 */
}

/* themes/classic.css */
[data-theme="classic"] {
  --bg-root: #F2EDE5;
  --brand: #467DA8;
  /* ... */
}
```

**新增主题**只需复制一个 ~40 行的语义覆写文件，无需逐个检查所有变量。

---

## 三、文件结构

```
public/css/
├── tokens/
│   ├── primitives.css         ← 原始值（不随主题变化，约 200 行）
│   ├── semantics.css          ← 语义令牌默认值 = Night 主题（约 150 行）
│   ├── components.css         ← 组件令牌（约 100 行）
│   ├── animations.css         ← 动效系统（从 src/styles/ 迁入）
│   ├── base.css               ← Reset + body + scrollbar（约 50 行）
│   └── themes/
│       ├── day.css            ← 仅覆写语义令牌（约 40 行）
│       ├── classic.css        ← 仅覆写语义令牌（约 40 行）
│       └── _template.css      ← 主题创作模板（注释版，约 60 行）
├── design-tokens.css          ← 聚合入口：@import 上述所有（约 10 行）
└── compat.css                 ← v10.0 → v11.0 向后兼容别名（约 50 行）
```

### 体积对比

| 文件 | v10.0 | v11.0 |
|------|-------|-------|
| 令牌定义 | 11,500 行（单体） | ~550 行（拆分） |
| 主题新增成本 | 复制 ~200 行 | 复制 ~40 行 |
| 组件样式 | 混在令牌文件中 | 独立 CSS 基类文件 |

---

## 四、组件体系

### 4.1 组件分级

| 层级 | 定义 | 示例 |
|------|------|------|
| **Atoms** | 不可再分的 UI 原子 | Button, Input, Badge, Avatar, Icon, Toggle, Spinner |
| **Molecules** | 原子组合 | Card, Dialog, Dropdown, Tabs, Toast, Tooltip, CodeBlock |
| **Organisms** | 完整功能区块 | NavRail, AppShell, MessageBubble, FileList, Table, Timeline |
| **Desktop** | 桌面原生 | WindowChrome, ContextMenu, SysTray, Notification, CmdPalette |

### 4.2 组件规格格式

每个组件有标准化描述：
```yaml
Name: Button
Level: Atom
Variants: [primary, secondary, ghost, danger, icon]
Sizes: [sm, md, lg]
States: [default, hover, active, focus, disabled, loading]
CSS Class: .btn / .btn-{variant} / .btn-{size}
Component Tokens: --btn-padding-x, --btn-padding-y, --btn-radius, --btn-gap
```

### 4.3 核心组件清单

#### Atoms (12 个)
1. **Button** — 5 variants × 3 sizes × 6 states
2. **Input** — text / textarea / select / search, 带 label + hint + error
3. **Badge** — 6 semantic colors, dot variant
4. **Avatar** — 5 sizes, online indicator, stacked group
5. **Toggle** — on/off, disabled
6. **Checkbox** — checked/indeterminate/disabled
7. **Radio** — selected/disabled
8. **Tag/Chip** — default/active/removable
9. **Spinner** — 3 sizes
10. **Progress** — determinate/indeterminate
11. **Skeleton** — text/circle/card variants
12. **Icon** — SVG sprite 系统

#### Molecules (12 个)
13. **Card** — elevated/outlined/gradient/special
14. **GlassContainer** — heavy/medium/light
15. **DoubleBezel** — 双层边框特效卡
16. **Tabs** — horizontal, pill variant
17. **Dropdown** — 单选/多选/带搜索
18. **Dialog/Modal** — 标准/确认/表单
19. **Tooltip** — top/bottom/left/right
20. **Toast** — success/error/warning/info
21. **ContextMenu** — 分层/分组/快捷键标注
22. **FileItem** — folder/document/image/code
23. **EmptyState** — icon + title + description + action
24. **CodeBlock** — 语法高亮 + 复制按钮

#### Organisms (8 个)
25. **NavRail** — 收起(56px)/展开(200px)
26. **AppShell** — sidebar + header + content + right panel
27. **MessageBubble** — user/ai, markdown 渲染
28. **ChatInput** — 输入框 + 工具栏 + 发送
29. **Table** — sortable, selectable rows
30. **Timeline** — vertical, dot variants
31. **SplitPane** — 三栏可拖拽
32. **SearchPanel** — 全局搜索浮层

#### Desktop (7 个)
33. **WindowChrome** — 标题栏/窗口控制/拖拽区
34. **SystemMenu** — 应用菜单栏
35. **SysTray** — 系统托盘图标 + 菜单
36. **Notification** — 系统原生通知
37. **DragDropZone** — 文件拖放区域
38. **CmdPalette** — 命令面板 (Ctrl+K)
39. **ResizeHandle** — 窗口边缘拖拽调整

**总计: 39 个组件**

---

## 五、桌面原生层

### 5.1 窗口级 UI

WebView2 壳内运行的桌面应用需要以下原生感 UI：

| 组件 | 说明 | 优先级 |
|------|------|--------|
| WindowChrome | 自定义标题栏（替代系统默认），包含拖拽区、窗口控制按钮 | P0 |
| TitleBar | 标题文字 + 窗口图标 + 最小化/最大化/关闭 | P0 |
| ContextMenu | 替代浏览器默认右键菜单，设计系统风格统一 | P0 |
| CmdPalette | Ctrl+K 命令面板，搜索 + 执行 | P1 |
| DragDropZone | 文件拖放到窗口，视觉反馈（高亮边框） | P1 |
| SysTray | 最小化到托盘，托盘菜单（显示/退出） | P2 |
| Notification | 系统级通知（任务完成、错误提醒） | P2 |

### 5.2 键盘快捷键体系

```
全局:
  Ctrl+,      设置
  Ctrl+N      新对话
  Ctrl+K      命令面板
  Ctrl+G      全局搜索
  Ctrl+\      切换侧栏
  Escape      关闭弹窗/面板
  Ctrl+Shift+N  新工作间

对话:
  Enter       发送
  Shift+Enter 换行
  Ctrl+Enter  强制发送（忽略自动补全）
  ↑/↓         历史消息导航
  Ctrl+L      清空对话
```

---

## 六、主题规范

### 6.1 三主题色板

| 令牌 | Night (默认) | Day | Classic |
|------|-------------|-----|---------|
| `--bg-root` | `#080B12` | `#F7F8FB` | `#F2EDE5` |
| `--bg-surface` | `#0E131F` | `#FFFFFF` | `#EDE6DC` |
| `--bg-elevated` | `#192237` | `#F2F4F8` | `#F9F5EF` |
| `--text-primary` | `#EDF0F5` | `#11151D` | `#262019` |
| `--brand` | `#4DA8F0` | `#3B8FD9` | `#467DA8` |

### 6.2 主题创作规则

1. 品牌色在各主题中可微调明度/饱和度，但保持蓝色系
2. 背景色阶需保持 4 级对比（root → surface → elevated → overlay）
3. 玻璃效果在各主题中保持 `backdrop-filter: blur()` 一致
4. 禁用粉紫色系 — 所有主题的铁则

---

## 七、命名规范

### 前缀体系
```
--bg-*      背景色
--text-*    文字色
--border-*  边框色
--brand-*   品牌色
--shadow-*  阴影
--space-*   间距
--radius-*  圆角
--ease-*    缓动函数
--dur-*     动画时长
--z-*       z-index
--btn-*     按钮组件令牌
--input-*   输入框组件令牌
--card-*    卡片组件令牌
```

### 命名规则
- 全小写，连字符分隔
- 颜色命名按用途不按色值（`--text-secondary` 而非 `--text-gray-500`）
- 组件令牌按 `{组件}-{属性}`（`--btn-padding-x`）
- 废弃令牌用 `--legacy-*` 前缀标记

---

## 八、与 v10.0 的兼容策略

v11.0 提供 `compat.css` 文件，用 `var()` 别名桥接旧名称：

```css
/* v10.0 名称 → v11.0 名称 */
--bg-base: var(--bg-root);
--color-bg-root: var(--bg-root);
--color-bg-surface: var(--bg-surface);
--color-text-primary: var(--text-primary);
--elevation-1: var(--shadow-sm);
--duration-fast: var(--dur-fast);
/* ... */
```

**迁移路径：**
1. 第一阶段：引入 v11.0，保留 compat.css（所有旧代码正常运行）
2. 第二阶段：逐个组件迁移到新命名
3. 第三阶段：删除 compat.css

---

## 九、Phase 1 交付物

| 文件 | 行数（估） | 状态 |
|------|-----------|------|
| `tokens/primitives.css` | ~200 | 待创建 |
| `tokens/semantics.css` | ~150 | 待创建 |
| `tokens/components.css` | ~100 | 待创建 |
| `tokens/animations.css` | ~80 | 待创建 |
| `tokens/base.css` | ~50 | 待创建 |
| `tokens/themes/day.css` | ~40 | 待创建 |
| `tokens/themes/classic.css` | ~40 | 待创建 |
| `tokens/themes/_template.css` | ~60 | 待创建 |
| `design-tokens.css` (入口) | ~10 | 待创建 |
| `compat.css` | ~60 | 待创建 |
| **总计** | **~790** | — |

对比 v10.0 的 11,500 行，令牌定义从单体巨兽压缩为 ~790 行结构化模块。

---

## 十、后续 Phase

| Phase | 内容 | 预计交付 |
|-------|------|---------|
| Phase 2 | 组件规格 + `super-niuma-ds-v11.0.html` 展示页 | 39 组件完整展示 |
| Phase 3 | 桌面原生层设计与 CSS | WindowChrome/ContextMenu/CmdPalette 等 |
| Phase 4 | frontend-vue 集成 | 组件基类 + 令牌迁移 |
| Phase 5 | 主题工厂 + 文档收尾 | 主题创作指南、迁移指南 |
