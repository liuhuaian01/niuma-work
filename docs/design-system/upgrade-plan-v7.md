                        ██████╗ ███████╗███████╗██╗ ██████╗ ███╗   ██╗    ███████╗██╗   ██╗███████╗████████╗███████╗███╗   ███╗
                        ██╔══██╗██╔════╝██╔════╝██║██╔════╝ ████╗  ██║    ██╔════╝╚██╗ ██╔╝██╔════╝╚══██╔══╝██╔════╝████╗ ████║
                        ██║  ██║█████╗  ███████╗██║██║  ███╗██╔██╗ ██║    ███████╗ ╚████╔╝ ███████╗   ██║   █████╗  ██╔████╔██║
                        ██║  ██║██╔══╝  ╚════██║██║██║   ██║██║╚██╗██║    ╚════██║  ╚██╔╝  ╚════██║   ██║   ██╔══╝  ██║╚██╔╝██║
                        ██████╔╝███████╗███████║██║╚██████╔╝██║ ╚████║    ███████║   ██║   ███████║   ██║   ███████╗██║ ╚═╝ ██║
                        ╚═════╝ ╚══════╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝    ╚══════╝   ╚═╝   ╚══════╝   ╚═╝   ╚══════╝╚═╝     ╚═╝
                        
                        ┌────────────────────────────────── SUPER NIUM A · DS v7.0 ──────────────────────────────────┐
                        │           调性拔高 · 审美跃升 · 极致精致 · 科技时尚 · 丝滑交互 · 年轻潮流                       │
                        └──────────────────────────────────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DESIGN READ: AI Workstation (SaaS/工具平台) for 年轻开发者/创作者, 
with Dark-Tech Neon Pulse + Liquid Glass + Bento Grid language,
leaning toward native CSS + custom cubic-bezier motion + Geist typography.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dials:  VARIANCE=8 | MOTION=7 | DENSITY=4

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VIBE: Ethereal Glass (SaaS/AI/Tech)
LAYOUT: Asymmetrical Bento
TYPOGRAPHY: Geist Sans + Geist Mono
MOTION: GSAP ScrollTrigger + cubic-bezier spring curves
COMPONENTS: Double-Bezel cards, Fluid Island nav, Magnetic buttons

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


▌ 10人产品研发设计团队分工

┌─────────────────────────────────────────────────────┐
│  TEAM LEAD     │ 架构师·设计总监    │ 方案统筹       │
│  UI DESIGNER   │ 视觉设计师         │ Token/CSS/组件  │
│  MOTION ENG    │ 动效工程师         │ GSAP/过渡/微交互│
│  COMPONENT DEV │ 组件开发           │ Cut-UI 选型/移植│
│  PAGE BUILDER  │ 页面重构           │ 9页面逐个翻新   │
│  THEME DEV     │ 主题工程师         │ 三主题精细化     │
│  PERF/A11Y     │ 性能/无障碍        │ WCAG/Lighthouse│
│  QA ENGINEER   │ 质量保证           │ 截图/对照验证   │
│  DOC WRITER    │ 文档撰写           │ DESIGN.md/TOKENS│
│  ASSET ARTIST  │ 素材艺术家         │ SVG/Icon/纹理   │
└─────────────────────────────────────────────────────┘


▌ PHASE 1 — TOKEN & THEME UPGRADE (Theme Dev + UI Designer)

  v6.2 Token → v7.0 Token 升级项：

  【颜色系统升级】
  - 新增 `--bg-glass`: 半透明玻璃态底色，替代部分 `--bg-elevated`
  - 新增 `--border-glow`: 品牌光晕边框，替代硬边框
  - 新增 `--accent-gradient`: 品牌渐变（`linear-gradient(135deg, var(--brand), var(--teal))`）
  - 暗主题 `--bg-root` 微调至 `#070C14`（更深黑蓝，增强OLED沉浸感）
  
  【阴影系统升级】
  - 新增 `--shadow-glass`: 玻璃卡片专属浮动阴影（带品牌色 tint）
  - 新增 `--shadow-glow-lg`: 大范围光晕（悬停拖拽反馈）
  
  【间距系统】
  - 新增 `--space-section`: 120px（页面区块间距）
  - 新增 `--space-bento`: 16px（Bento网格间距）
  
  【字体系统】
  - `--font-display`: Geist（headings）  ※ 非CDN，本地 @font-face
  - `--font-body`: System Font Stack（保留）
  - `--font-mono`: Geist Mono（代码）


▌ PHASE 2 — CUT-UI 组件选型 (Component Dev)

  从 Cult UI 精选以下组件移植：

  ┌──────────────────┬─────────────────────────────────┐
  │ 组件             │ 用途                            │
  ├──────────────────┼─────────────────────────────────┤
  │ Glass Card       │ 广场卡片 / 项目卡片              │
  │ Bento Grid       │ 实验室面板 / 记忆统计            │
  │ Fluid Nav Pill   │ 顶部导航（浮动玻璃胶囊）          │
  │ Morphing Toggle  │ 技能胶囊开关                     │
  │ Spotlight Border │ 悬停边框光效（卡片hover）         │
  │ Animated Tabs    │ 页面Tab切换指示器                │
  │ Skeleton Shimmer │ 加载占位                         │
  │ Toast Stack      │ 通知堆叠                         │
  │ Context Menu     │ 右键菜单（Phase 4已实现）         │
  │ Magnetic Button  │ 磁吸按钮                         │
  └──────────────────┴─────────────────────────────────┘

  移植策略：提取核心CSS + JS逻辑，简化为纯HTML/CSS/JS（零依赖），
  通过CSS变量注入主题。不做React组件，保持当前架构。


▌ PHASE 3 — 组件翻新 (Component Dev + Motion Eng)

  每个组件按 Double-Bezel 标准重构：

  【卡片组件】
  - 外层：`border border-white/[0.06] bg-white/[0.03] rounded-2xl p-[1.5px]`
  - 内层：`bg-[var(--bg-elevated)] rounded-[calc(1rem-1.5px)] shadow-[var(--shadow-glass)]`
  - Hover：`border-white/[0.12] shadow-[var(--shadow-glow)] translateY(-2px)`
  - Motion：`transition: all 400ms cubic-bezier(0.32, 0.72, 0, 1)`

  【按钮组件】
  - 主按钮：`bg-[var(--accent-gradient)] rounded-full px-6 py-2.5 font-medium text-white`
  - 内部箭头：独立圆形wrapper `w-7 h-7 rounded-full bg-white/15`
  - 按下：`active:scale-[0.97]` 
  - Hover：`translateY(-1px) shadow-[var(--shadow-glow)]`

  【导航栏】
  - Fluid Island：`mx-auto mt-4 w-max rounded-full bg-[var(--bg-glass)] backdrop-blur-2xl`
  - 边框：`border border-white/[0.08]`
  - 高光：`box-shadow: inset 0 1px 0 rgba(255,255,255,0.12)`

  【输入卡片】
  - 玻璃态：`bg-[var(--bg-glass)] backdrop-blur-xl border border-white/[0.08] rounded-2xl`
  - Focus：`border-[var(--brand)] shadow-[var(--shadow-glow)]`
  - 发送按钮：蓝色渐变 + 磁吸效应

  【Tab组件】
  - 激活态：下划线改为 pill-bg（`bg-brand/15 text-brand rounded-full`）
  - 切换动画：`transition: background 250ms, color 250ms`


▌ PHASE 4 — 9页面逐个翻新 (Page Builder)

  优先级顺序：

  P0 - 对话页 (Chat)
    - Glass输入卡片 + Magnetic发送按钮
    - 气泡：双主题优化（用户泡/调度泡视觉分离）
    - 对话列表：Glass卡片hover效果
    - 上下文占比：环形进度指示器 + Tooltip
    
  P0 - 广场页 (Plaza)  
    - Skill卡片：Double-Bezel + Spotlight Border hover
    - 胶囊开关：Morphing Toggle（平滑过渡）
    - 上传按钮：Magnetic Button
    - 4列Bento网格
    
  P0 - 项目详情 (Project)
    - Tab导航：Animated Tabs（pill激活态）
    - 任务卡片：Double-Bezel + 状态光晕
    - 文件浏览器：Glass面板
    
  P1 - 记忆页 (Memory)
    - 统计面板：Bento Grid（4格不对称布局）
    - 日视图：Glass卡片列表
    - 进化动态：迷你折线图
  
  P1 - 实验室 (Lab)
    - 太极引擎面板：Double-Bezel + 实时状态光点
    - 工作间管理：Bento Grid
    - 系统状态：半透明数据卡片
    
  P2 - 文件 / 连接 / 办公室 / 设置
    - 统一应用 Glass + Double-Bezel 标准


▌ PHASE 5 — 动效系统 (Motion Eng)

  【微交互】（应用到所有交互元素）
  - Hover：scale(1.02) + 阴影扩散 + 边框增亮
  - Active：scale(0.97) 物理按压感
  - 过渡曲线：`cubic-bezier(0.32, 0.72, 0, 1)`（弹性终止）

  【页面切换】
  - 淡入+上移：`opacity: 0→1, transform: translateY(12px)→0`
  - 持续：400ms
  - 命名动画：`@keyframes pageFadeIn`

  【卡片入场】
  - 交错延迟：`animation-delay: calc(var(--i) * 60ms)`
  - 4张卡片 = 0ms / 60ms / 120ms / 180ms

  【加载状态】
  - Skeleton Shimmer：渐变色条滑动
  - 全局 Loading：顶部细进度条（2px height, brand-gradient）

  【通知/Toast】
  - 从右上滑入：`translateX(100%) → 0`，400ms
  - 自动消失：5s后淡出 300ms

  【Scroll-triggered（实验室页）】
  - 太极面板数字递增动画
  - 统计数字：`IntersectionObserver` + `requestAnimationFrame`


▌ PHASE 6 — 素材与纹理 (Asset Artist)

  【背景纹理】
  - 暗主题：`radial-gradient(ellipse at 30% 20%, rgba(77,168,240,0.04) 0%, transparent 70%)`
  - 额外叠加：`radial-gradient(ellipse at 70% 80%, rgba(168,133,247,0.03) 0%, transparent 70%)`
  - 结果：微妙的双色光晕背景，不纯黑

  【卡片光泽】
  - `::before` 伪元素：`linear-gradient(135deg, rgba(255,255,255,0.06) 0%, transparent 50%)`
  - 模拟玻璃表面高光反射

  【图标系统】
  - 统一使用 `stroke-width: 1.5` 细线风格
  - 颜色：`var(--text-secondary)`，hover时 `var(--brand)`

  【导航栏光晕】
  - `box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.08)`


▌ PHASE 7 — 三主题精细化 (Theme Dev)

  基于v6.2 Tokens，每个主题应用新玻璃态 + 光晕系统：

  【夜间主题】（默认，主要战场）
  - bg-root: #070C14（更深）
  - Glass面板: bg-white/[0.03] + backdrop-blur-2xl + border-white/[0.06]
  - 阴影：品牌蓝光晕

  【日间主题】
  - bg-root: #F5F7FA（保持）
  - Glass面板: bg-white/[0.85] + backdrop-blur-2xl + border-black/[0.06]
  - 阴影：柔和灰

  【经典主题】
  - bg-root: #F8F4ED（保持）
  - Glass面板: bg-[#FCF9F3]/[0.92] + backdrop-blur-xl + border-[#e8e0d5]
  - 阴影：暖棕光晕


▌ PHASE 8 — 性能 & 无障碍 (Perf/A11y)

  - `prefers-reduced-motion` 降级：所有动画→ instant
  - `prefers-reduced-transparency` 降级：Glass→solid fill
  - WCAG AA 对比度验证（所有主题）
  - 键盘导航：Tab → 聚焦可见指示器
  - `prefers-color-scheme` 自动主题切换


▌ 执行路线图

  Week 1  │ Phase 1 Token + Phase 2 Cut-UI 选型 + Phase 3 组件翻新
  Week 2  │ Phase 4 P0页面(对话/广场/项目) + Phase 5 动效
  Week 3  │ Phase 4 P1页面(记忆/实验室) + Phase 6 素材纹理
  Week 4  │ Phase 4 P2页面 + Phase 7 三主题 + Phase 8 性能/A11y

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                           当前优先：Phase 1 开始执行。请确认方案后，我将逐Phase落地。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
