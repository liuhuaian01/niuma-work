# 超级牛马下一代桌面端设计系统 — 实施计划

> **For Hermes:** 按阶段顺序推进，每阶段交付一个独立可验证的产出物。

**Goal:** 将 v10.0 NEON PULSE 升级为工程化、桌面原生的下一代设计系统 v11.0  
**Architecture:** 三层令牌引擎 + 组件规格体系 + 桌面原生层 + 可运行展示页  
**Tech Stack:** CSS Custom Properties + Vue 3 组件基类 + 纯 HTML/CSS 展示页（零依赖）

---

## 总览路线图

```
Phase 1 ████████ 令牌引擎重构        → design-tokens-v2.css (~2K行, 替代11.5K)
Phase 2 ████████ 组件规格 + 展示页    → super-niuma-ds-v11.0.html (可运行组件库)
Phase 3 ████████ 桌面原生层设计       → desktop-native-patterns.md + CSS
Phase 4 ████████ frontend-vue 集成    → 组件基类 + 令牌迁移
Phase 5 ████████ 主题工厂 + 扩展       → 主题创作工具 + 文档收尾
```

---

## Phase 1: 令牌引擎重构

**目标:** 建立 Primitives → Semantics → Components 三层令牌架构，替代现有 11.5K 巨型单体 CSS

### 架构

```
Primitives (原始值——不直接消费)
  ├── colors: 灰度色阶 / 品牌色阶 / 语义色阶
  ├── spacing: 4px 基 12 级
  ├── typography: font family / size / weight / leading
  ├── radius: 6 级标量
  └── shadow: 5 级 + glow

Semantics (语义令牌——主题覆写层)
  ├── bg-root, bg-surface, bg-elevated, bg-overlay, bg-input
  ├── text-primary, text-secondary, text-tertiary
  ├── border-subtle, border-default, border-strong
  ├── brand, brand-hover, brand-muted
  └── success / warning / error / info + bg

Components (组件令牌——单个组件 tweak)
  ├── button-padding, button-radius, button-gap
  ├── input-height, input-radius
  ├── card-padding, card-gap
  └── ...
```

### 文件结构

```
public/css/
  ├── tokens/
  │   ├── primitives.css    ← 原始值（不随主题变化）
  │   ├── semantics.css     ← 语义令牌（:root 默认 = Night）
  │   ├── components.css    ← 组件令牌
  │   └── themes/
  │       ├── night.css     ← 仅覆写语义令牌
  │       ├── day.css
  │       └── classic.css
  └── design-tokens.css     ← 入口：@import 上述所有
```

### 任务清单

- [ ] T1.1 提取 Primitives（颜色阶/间距/字号/圆角/阴影）
- [ ] T1.2 建立 Semantics 令牌体系（Night 默认）
- [ ] T1.3 定义 Component 令牌（按钮/输入框/卡片/徽章等核心组件）
- [ ] T1.4 Night 主题验证（确保视觉效果与 v10.0 一致）
- [ ] T1.5 Day 主题适配（覆写语义令牌）
- [ ] T1.6 Classic 主题适配（覆写语义令牌）
- [ ] T1.7 建立向后兼容别名（v10.0 旧名 → v11.0 新名映射）
- [ ] T1.8 清理冗余：删除重复声明、死代码、未消费变量

---

## Phase 2: 组件规格 + 展示页

**目标:** 交付 super-niuma-ds-v11.0.html —— 可运行的组件库展示页

### 组件清单（对标 v8.0 的 80+ 组件）

**基础组件 (Atoms)**
- [ ] Button (5 variants: primary/secondary/ghost/danger/icon)
- [ ] Button sizes (sm/md/lg)
- [ ] Input (text/textarea/select/search)
- [ ] Badge (6 semantic colors)
- [ ] Dot (online/warning/offline)
- [ ] Avatar (4 sizes + online indicator + stacked)
- [ ] Toggle switch
- [ ] Checkbox / Radio
- [ ] Tag / Chip
- [ ] Spinner / Progress bar / Skeleton
- [ ] Icon (SVG system)

**复合组件 (Molecules)**
- [ ] Card (elevated/outlined/gradient/special — 4 variants)
- [ ] Glass container (heavy/medium/light — 3 levels)
- [ ] Double-bezel card
- [ ] Tabs (horizontal)
- [ ] Dropdown / Select menu
- [ ] Dialog / Modal
- [ ] Tooltip
- [ ] Toast / Notification
- [ ] Context menu (右键菜单)
- [ ] File item
- [ ] Table
- [ ] Timeline
- [ ] Empty state
- [ ] Code block
- [ ] Message bubble (user/ai)

**布局组件 (Organisms)**
- [ ] Nav rail (sidebar — 收起/展开)
- [ ] App shell (sidebar + header + content + panels)
- [ ] Split pane (三栏布局)

### 展示页结构
```
super-niuma-ds-v11.0.html
├── 主题切换器 (Night/Day/Classic)
├── Section: 色板 (调色盘展示)
├── Section: 排版 (字号/字重/行高示例)
├── Section: 间距 (spacing scale 可视化)
├── Section: 圆角 + 阴影
├── Section: 基础组件 (Atoms)
├── Section: 复合组件 (Molecules)
├── Section: 布局 (Organisms)
└── Section: 桌面原生 (Phase 3 产物)
```

---

## Phase 3: 桌面原生层设计

**目标:** 定义桌面端独有的 UI 模式和交互规范

### 桌面原生组件
- [ ] Window Chrome (标题栏 / 窗口控制按钮 / 拖拽区)
- [ ] System Menu Bar (应用菜单)
- [ ] Context Menu (右键菜单 — 分层/分组/快捷键标注)
- [ ] System Tray (托盘图标 + 菜单)
- [ ] Native Notification (系统通知)
- [ ] File Drag & Drop Zone
- [ ] Keyboard Shortcuts 体系 (全局 + 上下文)
- [ ] Native Dialog Bridge (文件选择器/另存为)
- [ ] Resize Handles (窗口边缘拖拽)
- [ ] Touch Bar / Command Palette (可选)

---

## Phase 4: frontend-vue 集成

**目标:** 将新设计系统集成到 Vue 3 前端

- [ ] 替换 design-tokens.css 为新令牌系统
- [ ] 建立组件基类 CSS (components/base/)
- [ ] 逐个迁移现有组件 (Badge → Toggle → Button → ...)
- [ ] 统一主题切换逻辑 (data-theme 属性驱动)
- [ ] 清理各 View 中内联的重复样式

---

## Phase 5: 主题工厂 + 文档收尾

- [ ] 主题创作指南 (如何新增一个主题)
- [ ] design-tokens.md (令牌参考文档)
- [ ] component-specs.md (组件 API 文档)
- [ ] migration-guide-v10-to-v11.md
- [ ] 性能基准测试 (CSS 体积对比)

---

## 设计铁则（不可违背）

1. **品牌色不变** — #4DA8F0 牛马蓝
2. **禁用粉紫色系** — 永不使用 #E0B0FF, #D8B4FE 等
3. **全 SVG 图标** — 零 emoji
4. **零第三方 UI 库** — 纯 CSS Custom Properties
5. **Night 默认主题** — data-theme="night"
6. **呼吸感** — 充足留白，不拥挤
7. **桌面优先** — WebView2 壳内运行，不是响应式网站
8. **三层令牌不可逆** — 组件只消费 Semantics，不直接引用 Primitives
