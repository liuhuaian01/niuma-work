# 超级牛马 v3.0 Youth — 设计系统

> 灵感来源：Tencent Ardot (https://ardot.tencent.com/)  
> 调性：青春 · 活力 · 创作力 · 现代 · 年轻  
> 版本：v3.0 Youth · 2026-05-30

---

## 1. 设计哲学

### 1.1 核心理念

超级牛马是一个 **AI Agent 创作力平台**。用户是年轻的创作者、写手、设计师——他们需要的是一个充满能量、激发灵感的工具，而不是一个沉闷的企业软件。

**Ardot 的启发：**
- **浅色底色** — 明亮、开放、不压抑，让创意自由流动
- **大面积亮彩色** — 品牌蓝、荧光绿、活力紫，传递能量感
- **超大圆角** — 友好、亲和、无攻击性
- **柔和弥散阴影** — 轻盈的层级感，不沉重
- **留白与呼吸感** — 信息密度适中，眼睛不累

### 1.2 与 v2.0 的区别

| 维度 | v2.0 (旧) | v3.0 Youth (新) |
|------|-----------|-----------------|
| **底色** | 暖黑 `#0F0E0D` | 浅灰白 `#F0F1F5` |
| **主色** | 暖橙 `#F97316` | 活力蓝 `#3B82F6` |
| **辅色** | 红/绿/蓝辅助 | 荧光绿 `#84CC16` + 紫 `#7C3AED` |
| **卡片** | 实色深色 | 纯白 + 弥散阴影 |
| **圆角** | 4/8/12/16px | 8/12/16/20/24px (更大) |
| **阴影** | 深色厚重 | 柔和轻盈 |
| **调性** | 沉稳科技 | 青春活力创作 |

---

## 2. 色彩系统

### 2.1 主色盘

```
Brand Blue      #3B82F6  ── 主品牌色，按钮、链接、高亮
Brand Hover     #2563EB  ── 悬停态
Brand Active    #1D4ED8  ── 按下态
Brand Muted     rgba(59,130,246,0.08)  ── 背景高亮
```

### 2.2 强调色（青春活力）

```
Lime Green      #84CC16  ── 成功、在线、正能量
Violet          #7C3AED  ── 创意、AI、紫色渐变端点
Cyan            #06B6D4  ── 科技、数据、冷却色
Pink            #EC4899  ── 活力、女性化、温暖
Orange          #F97316  ── 保留作警告/提示（少用）
```

**渐变组合（创作力表达）：**
- 主按钮：`linear-gradient(135deg, #3B82F6, #7C3AED)` 蓝→紫
- 头像/徽章：`linear-gradient(135deg, #3B82F6, #60A5FA)` 蓝→亮蓝
- 特殊标签：`linear-gradient(135deg, #84CC16, #22C55E)` 绿渐变
- 活跃状态：`linear-gradient(135deg, #EC4899, #F97316)` 粉→橙

### 2.3 中性色

```
Text Primary    #111827  ── 标题、正文
Text Secondary  #4B5563  ── 次要信息
Text Tertiary   #9CA3AF  ── 占位、禁用
Text Dim        #D1D5DB  ── 分割线、装饰
Text Inverse    #FFFFFF  ── 深色背景上的文字
```

### 2.4 背景色

```
Bg Root         #F0F1F5  ── 页面底层
Bg Surface      #FFFFFF  ── 卡片、面板
Bg Elevated     #FFFFFF  ── 浮层（同 surface，靠阴影区分）
Bg Hover        #F3F4F6  ── 悬停态
Bg Active       #E5E7EB  ── 按下态
Bg Selected     #EFF6FF  ── 选中态（brand-muted）
Bg Input        #F9FAFB  ── 输入框
```

### 2.5 边框色

```
Border Default  rgba(0,0,0,0.06)  ── 默认边框
Border Subtle   rgba(0,0,0,0.04)  ── 极细边框
Border Strong   rgba(0,0,0,0.10)  ── 强调边框
Border Focus    rgba(59,130,246,0.40)  ── 焦点环
Border Hover    rgba(0,0,0,0.08)  ── 悬停边框
```

---

## 3. 排版系统

### 3.1 字体栈

```
--font-sans: "Inter", -apple-system, BlinkMacSystemFont, "SF Pro Display",
             "Segoe UI", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
--font-mono: "JetBrains Mono", "Cascadia Code", "SF Mono", "Consolas", "Monaco", monospace;
```

### 3.2 字号阶梯

| Token | Size | Usage |
|-------|------|-------|
| `--fs-xs` | 0.6875rem (11px) | 标签、徽章、时间戳 |
| `--fs-sm` | 0.8125rem (13px) | 次要文字、导航项 |
| `--fs-base` | 0.875rem (14px) | 正文、按钮 |
| `--fs-md` | 0.9375rem (15px) | 稍大正文 |
| `--fs-lg` | 1rem (16px) | 小标题 |
| `--fs-xl` | 1.125rem (18px) | 区块标题 |
| `--fs-2xl` | 1.25rem (20px) | 页面标题 |
| `--fs-3xl` | 1.5rem (24px) | 大标题 |
| `--fs-4xl` | 1.875rem (30px) | 展示标题 |

### 3.3 字重

- **Regular (400)** — 正文
- **Medium (500)** — 按钮、导航
- **Semibold (600)** — 标题、强调
- **Bold (700)** — 大标题、数字

### 3.4 行高

- 标题：1.2 — 1.3
- 正文：1.5 — 1.6
- 紧凑：1.25（标签、徽章）

---

## 4. 间距系统

| Token | Value | Usage |
|-------|-------|-------|
| `--s1` | 0.25rem (4px) | 图标间距 |
| `--s2` | 0.5rem (8px) | 紧凑间距 |
| `--s3` | 0.75rem (12px) | 组件内间距 |
| `--s4` | 1rem (16px) | 标准间距 |
| `--s5` | 1.25rem (20px) | 卡片内边距 |
| `--s6` | 1.5rem (24px) | 区块间距 |
| `--s8` | 2rem (32px) | 大间距 |
| `--s10` | 2.5rem (40px) | 页面边距 |
| `--s12` | 3rem (48px) | 超大间距 |

---

## 5. 圆角系统

| Token | Value | Usage |
|-------|-------|-------|
| `--r-xs` | 8px | 小按钮、标签 |
| `--r-sm` | 12px | 输入框、小卡片 |
| `--r-md` | 16px | 卡片、面板 |
| `--r-lg` | 20px | 大卡片、模态框 |
| `--r-xl` | 24px | 特殊展示卡片 |
| `--r-full` | 9999px | 圆形、头像、徽章 |

---

## 6. 阴影系统

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-xs` | `0 1px 2px rgba(0,0,0,0.04)` | 极轻微 |
| `--shadow-sm` | `0 2px 8px rgba(0,0,0,0.06)` | 卡片默认 |
| `--shadow-md` | `0 4px 16px rgba(0,0,0,0.08), 0 0 0 1px rgba(0,0,0,0.02)` | 卡片悬停 |
| `--shadow-lg` | `0 8px 32px rgba(0,0,0,0.10)` | 下拉面板 |
| `--shadow-xl` | `0 12px 48px rgba(0,0,0,0.12)` | 模态框 |
| `--shadow-glow` | `0 0 24px rgba(59,130,246,0.12)` | 品牌辉光 |
| `--shadow-glass` | `0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.80)` | 玻璃拟态 |

---

## 7. 组件规范

### 7.1 按钮

**Primary Button**
```
background: linear-gradient(135deg, #3B82F6, #7C3AED)
color: #FFFFFF
border-radius: var(--r-sm)  /* 12px */
padding: 8px 16px
font-weight: 500
box-shadow: var(--shadow-sm)
transition: all 200ms var(--ease)

:hover {
  background: linear-gradient(135deg, #60A5FA, #8B5CF6)
  box-shadow: var(--shadow-md), var(--shadow-glow)
  transform: translateY(-1px)
}
```

**Secondary Button**
```
background: var(--bg-hover)  /* #F3F4F6 */
color: var(--text-secondary)  /* #4B5563 */
border: 1px solid var(--border-default)
border-radius: var(--r-sm)

:hover {
  background: var(--bg-active)  /* #E5E7EB */
  border-color: var(--border-hover)
}
```

**Ghost Button**
```
background: transparent
color: var(--text-secondary)

:hover {
  background: var(--bg-hover)
}
```

### 7.2 卡片

**Standard Card**
```
background: #FFFFFF
border-radius: var(--r-md)  /* 16px */
border: 1px solid var(--border-default)
box-shadow: var(--shadow-sm)
padding: var(--s5)  /* 20px */

:hover {
  box-shadow: var(--shadow-md)
  transform: translateY(-2px)
}
```

**Elevated Card**
```
background: #FFFFFF
border-radius: var(--r-lg)  /* 20px */
box-shadow: var(--shadow-md)
```

### 7.3 输入框

```
background: var(--bg-input)  /* #F9FAFB */
border: 1px solid var(--border-default)
border-radius: var(--r-sm)  /* 12px */
color: var(--text-primary)
padding: 10px 14px

:focus {
  border-color: var(--brand)
  box-shadow: 0 0 0 3px rgba(59,130,246,0.15)
}
```

### 7.4 导航项

```
color: var(--text-secondary)
border-radius: var(--r-sm)
padding: 8px 12px

:hover {
  background: var(--bg-hover)
  color: var(--text-primary)
}

&.active {
  background: var(--brand-muted)  /* rgba(59,130,246,0.08) */
  color: var(--brand)  /* #3B82F6 */
  border-left: 3px solid var(--brand)
}
```

### 7.5 对话气泡

**User Bubble**
```
background: linear-gradient(135deg, #3B82F6, #7C3AED)
color: #FFFFFF
border-radius: 16px 16px 4px 16px  /* 左下尖角 */
box-shadow: var(--shadow-sm)
```

**AI Bubble**
```
background: #FFFFFF
border: 1px solid var(--border-default)
color: var(--text-primary)
border-radius: 16px 16px 16px 4px  /* 右下尖角 */
box-shadow: var(--shadow-sm)
```

### 7.6 徽章/标签

**Status Badge (Online)**
```
background: var(--green-muted)  /* rgba(34,197,94,0.08) */
color: var(--green)  /* #22C55E */
border-radius: var(--r-full)
padding: 2px 10px
font-size: var(--fs-xs)
```

**Brand Badge**
```
background: linear-gradient(135deg, #3B82F6, #7C3AED)
color: #FFFFFF
border-radius: var(--r-full)
padding: 4px 12px
font-size: var(--fs-xs)
font-weight: 500
```

### 7.7 开关 (Toggle)

```
width: 36px
height: 20px
border-radius: 9999px
background: var(--border-default)

&.on {
  background: linear-gradient(135deg, #3B82F6, #7C3AED)
}

/* Thumb */
width: 16px
height: 16px
border-radius: 9999px
background: #FFFFFF
box-shadow: var(--shadow-xs)
```

---

## 8. 布局规范

### 8.1 三列布局

```
┌─────────────────────────────────────────────────────────────┐
│ Sidebar (240px) │ Main (flex:1) │ Right Panel (0-360px)    │
│                 │               │                            │
│  Assistant Card │   Chat Area   │  Dynamic Content           │
│  Navigation     │               │  (hidden by default)       │
│  User Panel     │   Input Bar   │                            │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 层级规范

| 层级 | Z-Index | 元素 |
|------|---------|------|
| 底层 | 0 | 页面内容 |
| 浮层 | 10 | 下拉面板 |
| 侧边栏 | 20 | 右侧面板 |
| 模态遮罩 | 40 | Cmd+K 遮罩 |
| 模态内容 | 50 | Cmd+K 弹窗 |
| 提示 | 60 | Toast 通知 |
| 拖拽 | 100 | Resize handle |

---

## 9. 动画规范

### 9.1 缓动函数

```
--ease: cubic-bezier(0.16, 1, 0.3, 1)       /* 标准缓出 */
--ease-spring: cubic-bezier(0.175, 0.885, 0.32, 1.275)  /* 弹性 */
```

### 9.2 时长

```
--dur-fast: 150ms   /* 微交互 */
--dur-base: 250ms   /* 标准过渡 */
--dur-slow: 400ms   /* 大动画 */
```

### 9.3 关键动画

**面板展开**
```css
@keyframes panelSlide {
  from { transform: translateX(20px); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
/* duration: 300ms, easing: --ease */
```

**消息出现**
```css
@keyframes msgPop {
  from { transform: scale(0.95); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}
/* duration: 200ms, easing: --ease-spring */
```

**Toast 滑入**
```css
@keyframes toastIn {
  from { transform: translateY(100%); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
/* duration: 300ms, easing: --ease */
```

---

## 10. 暗色模式

暗色模式通过 `[data-theme="dark"]` 属性切换。

**关键变化：**
- 所有背景色反转为深色系列
- 文字色反转为浅色系列
- 边框反转为半透明白色
- 卡片保持深色背景
- 品牌色保持蓝色（略微提亮）

详见 CSS 中的 `[data-theme="dark"]` 块。

---

## 11. 与 Ardot 的对应关系

| Ardot 元素 | 超级牛马对应 |
|-----------|-------------|
| 浅灰白画布背景 | `--bg-root: #F0F1F5` |
| 白色画板卡片 | `--bg-card: #FFFFFF` + shadow |
| 绿色播放按钮/标签 | `--accent-lime: #84CC16` |
| 紫色标注标签 | `--accent-violet: #7C3AED` |
| 蓝色矢量卡片 | `--brand: #3B82F6` |
| 荧光绿宣传卡片 | `--accent-lime` 用于特殊区块 |
| 大圆角卡片 | `--r-lg: 20px, --r-xl: 24px` |
| 柔和弥散阴影 | `--shadow-sm/md/lg` 系列 |
| 深色侧边栏 | 保持白色侧边栏（与 Ardot 一致） |

---

*Design System v3.0 Youth · 超级牛马 · 2026-05-30*
