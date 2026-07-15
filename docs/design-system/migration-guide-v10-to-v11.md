# 超级牛马 — 设计系统迁移指南 v10.0 → v11.0

> 从 NEON PULSE v10.0 升级到 v11.0 的完整迁移路径

---

## 概述

v11.0 将 v10.0 的 11,520 行单体 CSS 拆分为三层令牌架构，新增 39 组件规格和桌面原生层。

### 破坏性变更

| 变更 | v10.0 | v11.0 |
|------|-------|-------|
| 文件结构 | 1 个 11.5K 行文件 | 10 个模块化文件 |
| 主题定义 | 手动复制 200+ 变量 | `themes/*.css` 仅 ~40 行语义覆写 |
| 令牌命名 | 混杂 `--bg-root` / `--color-bg-root` / `--bg-base` | 统一 `--bg-root` |
| Classic 品牌色 | 两处矛盾 (#B8860B vs #467DA8) | 统一为 `#467DA8` |
| `data-theme="light"` | 日间模式标识 | 改为 `data-theme="day"` |
| 动画 | 独立 /src/styles/animations.css | 并入 tokens/animations.css |

### 非破坏性变更（有 compat.css 桥接）

所有 v10.0 旧变量名通过 `compat.css` 向后兼容。例如：

```css
/* 旧代码继续有效 */
.element { background: var(--bg-base); }
.element { color: var(--color-text-primary); }
.element { box-shadow: var(--elevation-2); }
```

---

## 三阶段迁移

### 阶段 1: 引入 v11.0（零改动，即日可用）

1. 确保 `index.html` 加载了新的 `design-tokens.css`（已自动处理）
2. `compat.css` 自动桥接所有旧变量名
3. 删除 `/src/styles/animations.css` 和 `/src/styles/themes.css` 引用
4. **验证**: 所有页面视觉效果与 v10.0 一致

### 阶段 2: 组件迁移（逐个进行）

逐一将 Vue 组件迁移到新命名和组件基类：

#### Button 迁移

```diff
<!-- v10.0 -->
- <button class="btn-primary" style="background: var(--brand-gradient)">

<!-- v11.0 -->
+ <button class="btn">
```

#### Card 迁移

```diff
<!-- v10.0 -->
- <div class="card" style="background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 24px;">

<!-- v11.0 -->
+ <div class="card-elevated">
```

#### 内联 CSS 替换

```diff
- style="color: var(--color-text-secondary)"
+ class="text-secondary"
```

### 阶段 3: 清理 compat.css

所有组件迁移完成后，删除 `compat.css` 和对应的 `<link>` 标签。

---

## 变量映射速查

### 背景

| v10.0 | v11.0 | 说明 |
|-------|-------|------|
| `--bg-base` | `--bg-root` | 更名为 root |
| `--color-bg-root` | `--bg-root` | 去掉 color- 前缀 |
| `--color-bg-surface` | `--bg-surface` | |
| `--color-bg-card` | `--bg-elevated` | |
| `--color-bg-input` | `--bg-input` | |
| `--color-bg-sidebar` | `--bg-root` | 侧栏统一用 root |
| `--color-bg-subtle` | `--bg-subtle` | |
| `--color-bg-hover` | `--bg-hover` | |
| `--color-bg-active` | `--bg-active` | |

### 文字

| v10.0 | v11.0 |
|-------|-------|
| `--color-text-primary` | `--text-primary` |
| `--color-text-secondary` | `--text-secondary` |
| `--color-text-tertiary` | `--text-tertiary` |
| `--color-text-disabled` | `--text-dim` |
| `--color-text-on-brand` | `--text-on-brand` |

### 品牌

| v10.0 | v11.0 |
|-------|-------|
| `--color-brand` | `--brand` |
| `--color-brand-hover` | `--brand-hover` |
| `--color-brand-active` | `--brand-active` |
| `--color-brand-muted` | `--brand-muted` |
| `--color-brand-subtle` | `--brand-glow` |

### 语义色

| v10.0 | v11.0 |
|-------|-------|
| `--color-success` | `--success` |
| `--color-success-bg` | `--success-bg` |
| `--color-error` | `--error` |
| `--color-error-bg` | `--error-bg` |
| `--color-warning` | `--warning` |
| `--color-warning-bg` | `--warning-bg` |
| `--color-info` | `--info` |
| `--color-info-bg` | `--info-bg` |

### 阴影

| v10.0 | v11.0 |
|-------|-------|
| `--elevation-1` | `--shadow-sm` |
| `--elevation-2` | `--shadow-md` |
| `--elevation-3` | `--shadow-lg` |
| `--elevation-4` | `--shadow-xs` |
| `--shadow-niuma` | `--shadow-sm` |
| `--shadow-niuma-lg` | `--shadow-lg` |
| `--shadow-brand` | `--shadow-brand` |
| `--shadow-danger` | `--shadow-danger` |

### 动效

| v10.0 | v11.0 |
|-------|-------|
| `--duration-fast` | `--dur-fast` |
| `--duration-normal` | `--dur-base` |
| `--duration-slow` | `--dur-slow` |

### 字重

| v10.0 | v11.0 |
|-------|-------|
| `--fw-normal` | `--weight-normal` |
| `--fw-medium` | `--weight-medium` |
| `--fw-semibold` | `--weight-semibold` |
| `--fw-bold` | `--weight-bold` |

---

## 主题迁移

```diff
<!-- v10.0 -->
- <html data-theme="light">

<!-- v11.0 -->
+ <html data-theme="day">
```

Day 主题视觉保持一致，仅 `data-theme` 属性值从 `light` 改为 `day`。

---

## 文件清理清单

迁移完成后可删除的 v10.0 遗留文件：

- [ ] `src/styles/animations.css` — 已迁移到 `tokens/animations.css`
- [ ] `src/styles/themes.css` — 已被 `tokens/themes/day.css` + `tokens/themes/classic.css` 替代
- [ ] `public/css/compat.css` — 阶段 3 可删
- [ ] 旧 `design-tokens.css` 备份文件（如有）

---

## 新增能力

v11.0 带来的新能力，迁移后可立即使用：

| 能力 | 使用方式 |
|------|---------|
| 组件基类 | `<button class="btn">` 替代手写渐变样式 |
| 卡片变体 | `card-elevated` / `card-outlined` / `card-gradient` / `card-special` |
| 桌面原生 | `<div class="win-chrome">` 自定义标题栏 |
| 右键菜单 | `<div class="ctx-menu">` 设计系统统一右键菜单 |
| 命令面板 | `<div class="cmd-palette">` Ctrl+K 命令搜索 |
| 新主题 | 复制 `themes/_template.css`，修改 ~40 行语义变量 |
| 键盘标注 | `<span class="kbd"><key>Ctrl</key><key>K</key></span>` |
