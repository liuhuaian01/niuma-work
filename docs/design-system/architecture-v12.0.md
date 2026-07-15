 # 超级牛马 下一代桌面端设计系统 v12.0 — 架构总纲
 
 > **代号**: MORPHIC RESONANCE v12.0 · 形态共鸣
 > **日期**: 2026-07-11
 > **状态**: ✅ 全新设计 · 先天架构 · 完全颠覆
 > **前置**: v11.0 NEON PULSE
 
 ---
 
 ## 零. MORPHIC RESONANCE — 设计 DNA（第一性）
 
 NEON PULSE 是"灵感迸发的创作脉冲"，而 **MORPHIC RESONANCE** 是"有生命感的响应式界面"。
 
 ```
 MORPHIC RESONANCE = 五个视觉基因：
 
   活体表面 (Living Membrane)
      表面有微妙的"呼吸"— 不是静态色块，是活的介质
      hover 时表面像被触碰的水面泛起涟漪
      → 不是"按钮"，是"可触发的区域"
 
   环境光场 (Ambient Field)
      无传统阴影，代以环境光对场景的响应
      物体抬高时，下方产生"光晕"，不是"影子"
      → 不是"卡片层级"，是"磁场强度"
 
   自适应色度 (Adaptive Chroma)
      颜色根据用户情境自动调整色温
      早晨偏暖，深夜偏冷，工作聚焦时饱和度提升
      → 不是"固定色板"，是"活的光谱"
 
   场域线 (Field Lines)
      元素之间通过"场线"建立空间关系
      不是分割线/边框，是元素间的"引力场"
      → 不是"border"，是"connection"
 
   零手势 (Zero Ceremony)
      UI 在不需要时隐退，需要时自然浮现
      没有多余步骤，没有固定导航栏
      → 不是"界面"，是"能力场"
 ```
 
 ---
 
 ## 一. 设计系统升级动机
 
 ### v11.0 的结构性债务
 
 | 问题 | 影响 |
 |------|------|
 | NEON PULSE 过于强烈的视觉语言干扰功能性 | 用户反馈"界面太抢戏" |
 | 39 个组件缺乏统一的"生命力"特征 | 组件各自为政，无跨组件DNA |
 | 三主题设计但夜间模式依然有"死色块" | 暗模式下背景缺乏深度感 |
 | 动画系统过于"机械"（spring/ease 公式化） | 缺乏有机感、自然感 |
 | 无 AI 原生设计考虑 | 界面仍以"菜单驱动"而非"意图驱动" |
 
 ### v12.0 目标
 
 > **从"有漂亮皮肤的工具"进化为"有生命感的工作伙伴"**
 
 ---
 
 ## 二. 令牌架构
 
 ### 2.1 四层模型（v11.0 三层 → v12.0 四层）
 
 v12.0 在 v11.0 三层基础上增加第四层 **AI Context**，实现自适应 UI。
 
 **选代颜色系统** — 四品牌色系：Brand Blue (#3B82F6) 作为主线，配以 Cyan、Amber、Pink 作为辅助色系，强化品牌识别度的同时提供灵活配色空间。
 
 **呼吸节奏系统** — 通过 `--breathe-duration` 控制 idle/thinking/focus/error 四种状态的呼吸周期（2.5s–6s），赋予界面"生物钟"。
 
 **活体膜层 (Membrane)** — 全新材质层，替代 v11.0 的 glass。Membrane 表面带有微妙渐变动画，hover 时产生涟漪反馈。
 
 **场域线系统 (Field Line)** — 替代 border。元素之间通过"场力线"连接，使用 `--field-color` 和 `--field-width` 控制。
 
 **无向后兼容** — v12.0 是完全推倒重来的架构，从视觉基因到运动系统全部革新。
 
 ---
 
 ## 三. 组件体系
 
 ### 3.1 组件分级
 
 | 层级 | 定义 | 示例 | 数量 |
 |------|------|------|------|
 | **Atoms** | 不可再分的 UI 原子 | Button, Input, Badge, Avatar | 14 |
 | **Molecules** | 原子组合 | Card, Dialog, Dropdown, Toast | 14 |
 | **Organisms** | 完整功能区块 | AppShell, NavRail, ChatInput | 8 |
 | **Desktop** | 桌面原生 | WindowChrome, ContextMenu | 7 |
 | **Living** | ⭐ 活体组件 (全新) | Membrane, FieldLine, BreathOverlay | 4 |
 | | | **总计** | **47** |
 
 ### 3.2 全新 "Living" 层 (4 个)
 1. **Membrane** — 活体表面容器，带呼吸动画和涟漪 hover 反馈
 2. **FieldLine** — 场力线连接器，在元素间建立空间关系
 3. **BreathOverlay** — 呼吸光晕覆盖层，赋予容器生命力
 4. **ChromaIndicator** — 自适应色度指示器，显示当前色温状态
 
 ---
 
 ## 四. 运动系统
 
 ### 4.1 运动哲学
 
 v12.0 的动画是"有机生物的"，而非"机械弹簧的"：
 
 ```css
 --ease-breathe: cubic-bezier(0.35, 0.05, 0.20, 0.95);
 --ease-ripple: cubic-bezier(0.25, 0.46, 0.45, 0.94);
 --ease-field: cubic-bezier(0.22, 1, 0.36, 1);
 --ease-organic: cubic-bezier(0.60, 0.00, 0.40, 1.00);
 ```
 
 ### 4.2 呼吸节奏
 
 | 状态 | 周期 | 说明 |
 |------|------|------|
 | idle | 4s | 默认呼吸 |
 | attentive | 2.5s | 检测到用户注意力 |
 | thinking | 1.5-3s | AI思考时加速 |
 | error | 5s | 错误状态放缓 |
 | focus | 6s | 专注模式极慢呼吸 |
 
 ---
 
 ## 五. 设计原则（不可违背）
 
 1. **品牌色不可变** — #3B82F6 超级牛马蓝
 2. **禁止紫色系** — 永不使用 #E0B0FF, #D8B4FE 等
 3. **零第三方 UI 库** — 纯 CSS Custom Properties
 4. **Night 默认主题** — 始终 data-theme="night"
 5. **呼吸感** — 每个组件必须有 idle 状态下的微妙运动
 6. **桌面优先** — WebView2 壳内运行
 7. **四层令牌不可违** — 组件只能消费 Semantics + AI Context
 
 ---
 
 ## 六. 颜色系统
 
 ```
 Brand Blue:     #3B82F6 (主品牌蓝)
 Brand Accent:   #06B6D4 (青金石)
 Brand Warmth:   #F59E0B (琥珀暖)
 Brand Energy:   #EC4899 (能量粉)
 ```
 
 ---
 
 ## 七. 文件结构
 
 ```
 design system/
 ├── morphic-resonance-v12.0.html     # 完整设计系统展示页
 ├── tokens/
 │   ├── primitives.css
 │   ├── semantics.css
 │   ├── components.css
 │   ├── ai-context.css
 │   ├── living.css
 │   ├── animations.css
 │   └── base.css
 └── themes/
     ├── dawn.css
     ├── day.css
     ├── dusk.css
     ├── night.css
     ├── focus.css
     └── _template.css
 ```
