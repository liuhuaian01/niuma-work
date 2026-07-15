# 超级牛马 v3.0 — 设计系统

> **灵感来源**: Figma (精准黑白+多彩渐变) × Linear (暗色原生+单色强调) × Raycast (琉璃深度+红色点睛) × Ardot (年轻时尚+圆润友好)
> **目标调性**: 年轻 · 时尚 · 精准 · 温暖 · AI原生

---

## 1. 视觉主题

**深空蓝黑基底 + 靛紫渐变强调 + 琉璃态玻璃效果**

超级牛马不是又一个冷冰冰的企业工具。它是一个有温度的 AI 协作伙伴。视觉语言应当: 深邃但不清冷、精准但不刻板、年轻但不幼稚。

核心手法:
- **深空底色** `#07080D` — 带微妙蓝调的纯黑，比 Linear 更暖，比 Raycast 更深邃
- **靛紫渐变** `#6366F1 → #8B5CF6 → #06B6D4` — 活力的三色渐变，来自 Ardot 式的年轻感
- **琉璃态表面** — 半透明卡片 + backdrop-blur，营造 macOS 原生应用的晶莹质感
- **负字距排版** — 借鉴 Figma，标题 -0.5px ~ -1.0px 紧凑字距
- **圆润几何** — 8/12/16px 三级圆角，pill 按钮 9999px

---

## 2. 色彩系统

### 基础底色 (Deep Space)

| Token | Hex | HSL | 用途 |
|------|------|-----|------|
| `--bg-root` | `#07080D` | 228° 30% 4% | 最深底色，全屏画布 |
| `--bg-surface` | `#0D0F15` | 225° 24% 7% | 卡片/面板表面 |
| `--bg-elevated` | `#13151E` | 229° 23% 10% | 弹窗/浮层 |
| `--bg-overlay` | `#1A1D28` | 228° 21% 13% | 模态遮罩 |
| `--bg-hover` | `#1E2130` | 230° 23% 15% | 悬停态 |
| `--bg-active` | `#262A3D` | 230° 24% 19% | 激活态 |
| `--bg-selected` | `#1E1B3A` | 246° 36% 17% | 选中态(靛紫底) |
| `--bg-input` | `#0D0F15` | 225° 24% 7% | 输入框 |

### 琉璃态表面 (Glass)

| Token | Hex/RGBA | 用途 |
|------|------|------|
| `--glass-bg` | `rgba(19,21,30,0.85)` | 琉璃卡片底 |
| `--glass-border` | `rgba(99,102,241,0.10)` | 琉璃描边(靛色) |
| `--glass-blur` | `20px` | 背景模糊 |

### 文字色阶

| Token | Hex | 用途 |
|------|------|------|
| `--text-primary` | `#EEEEF5` | 主文字 |
| `--text-secondary` | `#9B9DB8` | 辅助文字 |
| `--text-tertiary` | `#6B6D88` | 三级文字 |
| `--text-dim` | `#484A62` | 置灰 |

### 品牌强调 (Indigo-Violet Gradient)

| Token | Hex | 用途 |
|------|------|------|
| `--brand` | `#6366F1` | 品牌主色(靛蓝) |
| `--brand-hover` | `#818CF8` | 悬停亮色 |
| `--brand-active` | `#4F46E5` | 按压暗色 |
| `--brand-muted` | `rgba(99,102,241,0.12)` | 弱化底色 |
| `--brand-glow` | `rgba(99,102,241,0.25)` | 辉光 |

### 辅助色

| Token | Hex | 用途 |
|------|------|------|
| `--accent-violet` | `#8B5CF6` | 紫罗兰强调 |
| `--accent-cyan` | `#06B6D4` | 青色信息 |
| `--green` | `#22C55E` | 成功/在线 |
| `--yellow` | `#F59E0B` | 警告/思考中 |
| `--red` | `#EF4444` | 错误/危险 |
| `--pink` | `#EC4899` | 粉色心跳(特殊强调) |

### 图表色

| Token | Hex |
|------|------|
| `--chart-1` | `#6366F1` |
| `--chart-2` | `#06B6D4` |
| `--chart-3` | `#8B5CF6` |

### 渐变系统

```
--gradient-brand: linear-gradient(135deg, #6366F1, #8B5CF6)
--gradient-energetic: linear-gradient(135deg, #6366F1, #06B6D4)
--gradient-warm: linear-gradient(135deg, #EC4899, #F97316)
--gradient-glass: linear-gradient(180deg, rgba(99,102,241,0.06), rgba(139,92,246,0.02))
```

### 用户消息气泡

```
--bubble-user-bg: linear-gradient(135deg, #6366F1, #8B5CF6)
--bubble-user-text: #FFFFFF
--bubble-ai-bg: #13151E
--bubble-ai-border: rgba(99,102,241,0.08)
```

### 浅色主题

```css
[data-theme="light"] {
  --bg-root: #F5F5FA;
  --bg-surface: #FFFFFF;
  --bg-elevated: #F8F8FD;
  --bg-hover: #EEEEF5;
  --bg-active: #E4E4F0;
  --bg-selected: #EEECFF;
  --bg-input: #F5F5FA;
  --text-primary: #12132A;
  --text-secondary: #5B5D78;
  --text-tertiary: #8B8DA5;
  --text-dim: #C5C6D8;
  --border-default: #E2E3F0;
  --border-focus: #6366F1;
}
```

---

## 3. 字体系统

### 字体栈 (零CDN)

```
--font-sans: "Inter", -apple-system, BlinkMacSystemFont,
             "SF Pro Display", "Segoe UI", "Noto Sans SC",
             "PingFang SC", "Microsoft YaHei", sans-serif;
--font-mono: "JetBrains Mono", "Cascadia Code", "SF Mono",
             "Consolas", "Monaco", monospace;
```

### 字号阶梯 (负字距排版)

| Token | Size | Weight | Letter-Spacing | Line-Height | 用途 |
|------|------|--------|----------------|-------------|------|
| `--fs-4xl` | 30px | 700 | -0.96px | 1.1 | Hero标题 |
| `--fs-3xl` | 24px | 600 | -0.72px | 1.2 | 页面标题 |
| `--fs-2xl` | 20px | 600 | -0.50px | 1.25 | 区块标题 |
| `--fs-xl` | 18px | 500 | -0.36px | 1.3 | 卡片标题 |
| `--fs-lg` | 16px | 500 | -0.16px | 1.4 | 加大正文 |
| `--fs-base` | 14px | 400 | 0px | 1.5 | 正文 |
| `--fs-sm` | 13px | 400 | 0px | 1.45 | 辅助文字 |
| `--fs-xs` | 11px | 500 | 0.24px | 1.35 | 标签/徽章 |

**原则**:
- 标题使用负字距 (Figma风格)，紧凑有力
- 正文使用中性字距，保证可读性
- 中文文字不加负字距 (中文字符间距不可压缩)

---

## 4. 间距与圆角

### 间距阶梯

```
--s1: 4px / --s2: 8px / --s3: 12px / --s4: 16px
--s5: 20px / --s6: 24px / --s8: 32px / --s10: 40px / --s12: 48px
```

### 圆角

```
--r-xs: 6px (输入框/小按钮)
--r-sm: 10px (卡片/面板)
--r-md: 14px (大面板/弹窗)
--r-lg: 20px (模态)
--r-full: 9999px (Pill/头像)
```

---

## 5. 阴影与深度

```css
--shadow-xs: 0 1px 2px rgba(0,0,0,0.40);
--shadow-sm: 0 2px 8px rgba(0,0,0,0.45);
--shadow-md: 0 4px 16px rgba(0,0,0,0.50), 0 0 0 1px rgba(99,102,241,0.06);
--shadow-lg: 0 8px 32px rgba(0,0,0,0.55), 0 0 0 1px rgba(99,102,241,0.08);
--shadow-glow: 0 0 24px rgba(99,102,241,0.15), 0 0 60px rgba(99,102,241,0.05);
--shadow-glass: 0 8px 32px rgba(0,0,0,0.30), inset 0 1px 0 rgba(255,255,255,0.04);
```

---

## 6. 边框

```css
--border-default: rgba(255,255,255,0.06);
--border-subtle: rgba(255,255,255,0.04);
--border-strong: rgba(255,255,255,0.10);
--border-focus: rgba(99,102,241,0.50);
--border-accent: rgba(99,102,241,0.25);
```

---

## 7. 动画

```css
--ease: cubic-bezier(0.16,1,0.3,1);        /* 更流畅的缓出 */
--ease-spring: cubic-bezier(0.175,0.885,0.32,1.275);
--dur-fast: 120ms;
--dur-base: 200ms;
--dur-slow: 350ms;
```

**原则**: 全部使用 GPU 合成属性 (transform/opacity)，不触发 layout repaint。动画不超过 300ms。

---

## 8. 布局

```
--sidebar-w: 240px;
--topbar-h: 48px;    /* 从52px收紧到48px，更紧凑 */
--statusbar-h: 28px; /* 从32px收紧到28px */
--panel-min-w: 280px;
--panel-default-w: 360px;
--panel-max-w: 50vw;
```

---

## 9. 组件规范

### 按钮

| 变体 | 背景 | 文字 | 圆角 | 高度 |
|------|------|------|------|------|
| Primary | `linear-gradient(135deg, #6366F1, #8B5CF6)` | #FFF | 8px | 36px |
| Secondary | `rgba(255,255,255,0.06)` | --text-primary | 8px | 36px |
| Ghost | transparent | --text-secondary | 8px | 32px |
| Pill | Primary/Secondary | 对应文字 | 9999px | 28px |

### 消息气泡

- 用户: 靛紫渐变 + 白色文字 + 右下角4px圆角
- AI: 琉璃表面(半透明 + 靛色描边) + 左上角4px圆角 + hover时出现操作按钮行

### 导航项

- 默认: 图标 + 文字，hover变亮
- 选中: 靛紫渐变背景 + 左侧3px竖条

### 卡片

- 背景: --bg-surface
- 描边: --border-default
- 悬停: --bg-hover + --border-accent + --shadow-glow

---

## 10. 设计禁令 (Do's & Don'ts)

| ✅ Do | ❌ Don't |
|------|---------|
| 负字距仅用于英文标题 | 中文字符使用负字距 |
| 靛紫渐变作为唯一主色 | 多种品牌色混用 |
| GPU合成属性做动画 | 触发layout的动画(width/height/top/left) |
| 琉璃态卡片用glass token | 硬编码半透明颜色 |
| 系统字体栈 | 引入外部字体CDN |
| 6/10/14/20px阶梯圆角 | 随意使用非标准圆角 |

---

> 此设计系统基于 Figma × Linear × Raycast × Ardot 四家标杆提炼  
> 用于 超级牛马 v3.0 前端原型重构  
> 日期: 2026-05-30
