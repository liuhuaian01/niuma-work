# 超级牛马工作台 · 前端开发文档 v1.0

> 版本：v1.0 | 日期：2026-07-01 | 基于：Neon Pulse 原型 v10.0 + DS v18.0  
> 本文档为 Vue 前端开发的唯一技术参考。所有组件实现、路由设计、状态管理、API 对接，以此为准。

---

## 目录

1. [技术栈与工程搭建](#一技术栈与工程搭建)
2. [项目结构](#二项目结构)
3. [设计系统与 Token 架构](#三设计系统与-token-架构)
4. [主题引擎实现](#四主题引擎实现)
5. [路由设计](#五路由设计)
6. [布局体系](#六布局体系)
7. [组件架构](#七组件架构)
8. [状态管理](#八状态管理)
9. [API 对接](#九api-对接)
10. [页面实现指引](#十页面实现指引)
11. [动画系统](#十一动画系统)
12. [响应式与无障碍](#十二响应式与无障碍)
13. [构建与部署](#十三构建与部署)
14. [迁移指南：原型 → Vue](#十四迁移指南原型--vue)

---

## 一、技术栈与工程搭建

### 1.1 技术栈

| 技术 | 版本 | 用途 |
|:---|:---:|:---|
| Vue | ^3.5.38 | 前端框架（Composition API + `<script setup>`） |
| Vue Router | ^4.6.4 | 路由管理（Hash 模式） |
| Vite | ^8.1.0 | 构建工具 |
| TypeScript | ~6.0.2 | 类型安全 |
| DOMPurify | ^3.4.11 | XSS 防护（处理流式HTML渲染） |
| vue-tsc | ^3.3.5 | 类型检查 |

**严格禁止的依赖：**
- 任何第三方 UI 组件库（Element Plus / Naive UI / Ant Design Vue）
- Tailwind CSS（与设计系统 Token 冲突）
- emoji（全部使用 SVG 图标）
- 粉紫色系（#E0B0FF 及其衍生）

### 1.2 工程初始化

```bash
# 进入前端工程目录
cd frontend-vue

# 安装依赖（已在 package.json 中声明）
npm install

# 启动开发服务器
npm run dev
# → http://localhost:5173

# 生产构建
npm run build
# → dist/ 目录输出

# 预览构建产物
npm run preview
```

### 1.3 Vite 配置 (`vite.config.ts`)

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    host: true  // 局域网可访问，方便桌面壳
  },
  // 建议在生产环境下配置 CSS 代码分割
  build: {
    cssCodeSplit: false,  // DS Token 需要全局注入，不拆分
    rollupOptions: {
      output: {
        manualChunks: {
          'design-system': ['./src/styles/tokens.css']
        }
      }
    }
  }
})
```

### 1.4 TypeScript 配置 (`tsconfig.app.json`)

```json
{
  "extends": "@vue/tsconfig/tsconfig.dom.json",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    },
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": [
    "src/**/*.ts",
    "src/**/*.tsx",
    "src/**/*.vue",
    "src/**/*.d.ts"
  ]
}
```

---

## 二、项目结构

### 2.1 推荐目录结构

```
frontend-vue/
├── index.html                 # 入口 HTML
├── package.json               # 依赖与脚本
├── vite.config.ts             # 构建配置
├── tsconfig.json              # TS 根配置
├── tsconfig.app.json          # 应用 TS 配置
├── tsconfig.node.json         # Node TS 配置
├── env.d.ts                   # 环境类型声明
│
├── public/
│   └── favicon.svg             # SVG 图标
│
├── src/
│   ├── main.ts                 # 应用入口
│   ├── App.vue                 # 根组件
│   │
│   ├── router/
│   │   └── index.ts            # 路由配置（Hash 模式）
│   │
│   ├── types/
│   │   ├── index.d.ts          # 全局类型声明
│   │   ├── api.ts              # API 请求/响应类型
│   │   ├── chat.ts             # 对话相关类型
│   │   ├── project.ts          # 项目/工作间类型
│   │   ├── memory.ts           # 记忆类型
│   │   └── plaza.ts            # 广场类型
│   │
│   ├── styles/
│   │   ├── tokens.css          # L0 + L1 设计令牌（三主题）
│   │   ├── components.css      # L2 组件 Token + 基础组件样式
│   │   ├── animations.css      # 全局动画
│   │   └── utilities.css       # 工具类
│   │
│   ├── composables/
│   │   ├── useTheme.ts         # 主题管理
│   │   ├── useSSE.ts           # SSE 流式接收
│   │   ├── useToast.ts         # Toast 通知
│   │   ├── useGlobalSearch.ts  # 全局搜索
│   │   ├── useContextMenu.ts   # 右键菜单
│   │   └── useLayout.ts        # 布局状态
│   │
│   ├── services/
│   │   ├── api.ts              # API 客户端封装
│   │   ├── chatService.ts      # 对话 API
│   │   ├── projectService.ts   # 项目 API
│   │   ├── plazaService.ts     # 广场 API
│   │   ├── memoryService.ts    # 记忆 API
│   │   ├── fileService.ts      # 文件 API
│   │   ├── connectionService.ts # 连接 API
│   │   └── labService.ts       # 实验室 API
│   │
│   ├── components/
│   │   ├── common/
│   │   │   ├── NavRail.vue           # 左侧 56px 导航栏
│   │   │   ├── SidebarContainer.vue   # 侧边栏容器（可调宽）
│   │   │   ├── ConfigPanel.vue        # 右侧配置面板
│   │   │   ├── ToastContainer.vue     # Toast 通知容器
│   │   │   ├── GlobalSearch.vue       # 全局搜索（Cmd+K）
│   │   │   ├── ContextMenu.vue        # 右键菜单
│   │   │   ├── Dropdown.vue           # 下拉选择器
│   │   │   ├── Modal.vue              # 模态框
│   │   │   ├── Skeleton.vue           # 骨架屏
│   │   │   ├── Badge.vue              # 徽标
│   │   │   ├── Toggle.vue             # 开关
│   │   │   └── Pill.vue               # 胶囊标签
│   │   │
│   │   ├── chat/
│   │   │   ├── ChatMessage.vue         # 单条消息（用户/AI）
│   │   │   ├── ChatInput.vue           # 输入区（6态）
│   │   │   ├── ChatSidebar.vue         # 对话列表侧栏
│   │   │   ├── MessageSearch.vue       # 消息搜索
│   │   │   ├── StreamRenderer.vue      # 流式渲染器
│   │   │   ├── ThinkingIndicator.vue   # 思考指示器
│   │   │   ├── ToolCallIndicator.vue   # 工具调用指示
│   │   │   └── CodeBlock.vue           # 代码块+复制
│   │   │
│   │   ├── project/
│   │   │   ├── ProjectCard.vue         # 项目卡片
│   │   │   ├── ProjectActivity.vue     # 项目 Activity 标签
│   │   │   ├── ProjectSOP.vue          # 项目 SOP 标签
│   │   │   ├── ProjectTasks.vue        # 项目 Tasks/Kanban
│   │   │   ├── ProjectAssets.vue       # 项目资源
│   │   │   └── ProjectConfig.vue       # 项目配置面板
│   │   │
│   │   ├── plaza/
│   │   │   ├── PlazaCard.vue           # 广场卡片
│   │   │   └── PlazaCategoryFilter.vue # 分类标签
│   │   │
│   │   ├── memory/
│   │   │   ├── MemoryCard.vue          # 记忆卡片
│   │   │   ├── MemoryCalendar.vue      # 日历视图
│   │   │   └── EntityGraph.vue         # 实体图
│   │   │
│   │   └── settings/
│   │       ├── ApiKeysPanel.vue        # API Keys 管理
│   │       ├── PreferencePanel.vue     # 偏好设置
│   │       ├── ShortcutPanel.vue       # 快捷键
│   │       └── AboutPanel.vue          # 关于
│   │
│   ├── views/
│   │   ├── ChatView.vue               # 对话页
│   │   ├── ProjectsView.vue            # 项目列表页
│   │   ├── ProjectDetailView.vue       # 项目详情页（含子标签）
│   │   ├── PlazaView.vue               # 广场页
│   │   ├── MemoryView.vue              # 记忆页
│   │   ├── FilesView.vue               # 文件页
│   │   ├── ConnectionsView.vue         # 连接页
│   │   ├── LabView.vue                 # 实验室页
│   │   └── SettingsView.vue            # 设置页
│   │
│   └── utils/
│       ├── dompurify.ts          # XSS 过滤配置
│       ├── storage.ts            # localStorage 封装
│       ├── icons.ts              # SVG 图标常量
│       └── format.ts             # 格式化工具
```

### 2.2 入口文件 (`src/main.ts`)

```typescript
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './styles/tokens.css'
import './styles/components.css'
import './styles/animations.css'
import './styles/utilities.css'

const app = createApp(App)
app.use(router)
app.mount('#app')
```

---

## 三、设计系统与 Token 架构

### 3.1 三层 Token 体系

```
L0 Theme Seeds ─── 三组种子变量（Night / Day / Classic）
    ↓ CSS 变量 + color-mix() 自动派生
L1 Semantic Tokens ─── 语义化变量（--color-bg-*, --text-*, --shadow-*）
    ↓ 组合引用
L2 Component Tokens ─── 组件级变量（--btn-*, --table-*, --modal-*）
```

**核心原则：切换主题只改 L0 种子，全系统自动派生。**

### 3.2 文件组织

| 文件 | Token 层级 | 内容 |
|:---|:---:|:---|
| `tokens.css` | L0 + L1 | 三主题种子变量 + 语义 Token |
| `components.css` | L2 + 组件样式 | 组件 Token + 基础组件类 |
| `animations.css` | — | 动画 keyframes + 过渡类 |

### 3.3 L0 种子变量结构

```css
/* ── Night 主题种子 ── */
:root, [data-theme="night"] {
  --theme-bg-seed: #080B12;
  --theme-surface-seed: #0E131F;
  --theme-card-seed: #131928;
  --theme-elevated-seed: #192237;
  --theme-input-seed: #131928;
  --theme-sidebar-seed: #0A0E17;
  
  --theme-foreground: #EDF0F5;
  --theme-midground: #8895AB;
  --theme-dim: #8895AB;
  
  --theme-accent: #4DA8F0;
  --theme-accent-soft: #6BBFFC;
  --theme-accent-muted: #2B7AB8;
  
  --theme-success: #34D399;
  --theme-warning: #FBBF24;
  --theme-error: #F87171;
  --theme-info: #60A5FA;
}

/* ── Day 主题种子 ── */
[data-theme="day"] {
  --theme-bg-seed: #F7F8FB;
  --theme-surface-seed: #FFFFFF;
  --theme-card-seed: #F2F4F8;
  --theme-elevated-seed: #EBEEF4;
  --theme-input-seed: #FFFFFF;
  --theme-sidebar-seed: #F0F2F7;
  
  --theme-foreground: #11151D;
  --theme-midground: #657083;
  --theme-dim: #6B758A;
  
  --theme-accent: #3B8FD9;
  --theme-accent-soft: #4DA8F0;
  --theme-accent-muted: #236DAE;
  
  --theme-success: #10B981;
  --theme-warning: #D97706;
  --theme-error: #DC2626;
  --theme-info: #2563EB;
}

/* ── Classic 主题种子 ── */
[data-theme="classic"] {
  --theme-bg-seed: #FDF8F0;
  --theme-surface-seed: #FFFBF5;
  --theme-card-seed: #F5EDE0;
  --theme-elevated-seed: #EDE3D2;
  --theme-input-seed: #FFFBF5;
  --theme-sidebar-seed: #FAF3E8;
  
  --theme-foreground: #2C2416;
  --theme-midground: #7A6B54;
  --theme-dim: #9A8B74;
  
  --theme-accent: #B8860B;
  --theme-accent-soft: #D4A843;
  --theme-accent-muted: #8B6914;
  
  --theme-success: #6B8F71;
  --theme-warning: #C9953B;
  --theme-error: #B34A4A;
  --theme-info: #5B7FA5;
}
```

### 3.4 L1 语义 Token 派生规则

```css
/* 在 L0 种子之后，通过 var() 引用派生 L1 语义 Token */
:root {
  /* 背景色系 */
  --color-bg-root:      var(--theme-bg-seed);
  --color-bg-surface:   var(--theme-surface-seed);
  --color-bg-card:      var(--theme-card-seed);
  --color-bg-elevated:  var(--theme-elevated-seed);
  --color-bg-input:     var(--theme-input-seed);
  --color-bg-sidebar:   var(--theme-sidebar-seed);
  --color-bg-subtle:    color-mix(in srgb, var(--theme-foreground) 4%, transparent);
  --color-bg-hover:     color-mix(in srgb, var(--theme-foreground) 6%, transparent);
  --color-bg-active:    color-mix(in srgb, var(--theme-foreground) 9%, transparent);

  /* 文字色系 */
  --color-text-primary:   var(--theme-foreground);
  --color-text-secondary: var(--theme-midground);
  --color-text-tertiary:  var(--theme-dim);

  /* 品牌色 */
  --color-brand:       var(--theme-accent);
  --color-brand-hover: var(--theme-accent-soft);
  --color-brand-muted: color-mix(in srgb, var(--theme-accent) 8%, transparent);
  --color-brand-glow:  color-mix(in srgb, var(--theme-accent) 10%, transparent);

  /* 语义色 */
  --color-success:     var(--theme-success);
  --color-success-bg:  color-mix(in srgb, var(--theme-success) 10%, transparent);
  --color-warning:     var(--theme-warning);
  --color-warning-bg:  color-mix(in srgb, var(--theme-warning) 10%, transparent);
  --color-error:       var(--theme-error);
  --color-error-bg:    color-mix(in srgb, var(--theme-error) 10%, transparent);
  --color-info:        var(--theme-info);
  --color-info-bg:     color-mix(in srgb, var(--theme-info) 10%, transparent);

  /* 边框 */
  --border-subtle:  color-mix(in srgb, var(--theme-foreground) 6%, transparent);
  --border-default: color-mix(in srgb, var(--theme-foreground) 10%, transparent);
  --border-strong:  color-mix(in srgb, var(--theme-foreground) 16%, transparent);

  /* 阴影（使用 theme-shadow-strength 调节透明度） */
  --shadow-xs: 0 1px 2px -1px rgba(0,0,0,calc(var(--theme-shadow-strength,0.18))),
               0 2px 4px -2px rgba(0,0,0,calc(var(--theme-shadow-strength,0.18)-0.06));
  /* ... 更多阴影层级 */

  /* 渐变背景（theme-aware） */
  --bg-gradient: radial-gradient(ellipse 120% 80% at 50% 0%,
                  color-mix(in srgb, var(--theme-accent) 4%, transparent) 0%, transparent 50%);
}
```

### 3.5 字号与间距（跨主题一致，不随主题变）

```css
/* 字号 (rem) */
--text-2xs: 0.6875rem;   /* 11px */
--text-xs: 0.75rem;      /* 12px */
--text-sm: 0.8125rem;    /* 13px */
--text-base: 0.9375rem;  /* 15px */
--text-md: 1.0625rem;    /* 17px */
--text-lg: 1.25rem;      /* 20px */
--text-xl: 1.5rem;       /* 24px */
--text-2xl: 1.875rem;    /* 30px */
--text-3xl: 2.5rem;      /* 40px */

/* 间距 (4px 基) */
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-6: 24px;
--space-8: 32px;
--space-12: 48px;
--space-16: 64px;

/* 圆角 (标量 0.6) */
--radius-scalar: 0.6;
--radius-xs: 3.6px;
--radius-sm: 7.2px;
--radius-md: 10.8px;
--radius-lg: 14.4px;
--radius-xl: 19.2px;
--radius-full: 9999px;
```

### 3.6 字体栈

```css
--font-display: "Space Grotesk", "PingFang SC", "Microsoft YaHei", sans-serif;
--font-sans:    "DM Sans", -apple-system, BlinkMacSystemFont, "Segoe UI",
                "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
--font-mono:    "JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", monospace;
```

---

## 四、主题引擎实现

### 4.1 主题切换原理

修改 `<html>` 标签的 `data-theme` 属性，CSS 变量自动响应：

```typescript
// src/composables/useTheme.ts
import { ref, watch, onMounted } from 'vue'

type Theme = 'night' | 'day' | 'classic'

const currentTheme = ref<Theme>('night')

export function useTheme() {
  function setTheme(theme: Theme) {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('niuma-theme', theme)
    currentTheme.value = theme
  }

  function toggleTheme() {
    const themes: Theme[] = ['night', 'day', 'classic']
    const nextIndex = (themes.indexOf(currentTheme.value) + 1) % themes.length
    setTheme(themes[nextIndex])
  }

  onMounted(() => {
    const saved = localStorage.getItem('niuma-theme') as Theme | null
    if (saved && ['night', 'day', 'classic'].includes(saved)) {
      setTheme(saved)
    } else {
      setTheme('night')
    }
  })

  return { currentTheme, setTheme, toggleTheme }
}
```

### 4.2 SVG 图标主题切换

为每个主题提供对应的 SVG 图标（NavRail 底部的主题切换按钮用三态图标）。

### 4.3 持久化

- 主题偏好存储到 `localStorage`，key: `niuma-theme`
- 可选同步到后端用户偏好（API → `/api/v1/user/preferences`）

---

## 五、路由设计

### 5.1 路由配置

**使用 Hash 模式**（兼容桌面 WebView2 客户端，无需服务端回退）：

```typescript
// src/router/index.ts
import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/chat'
  },
  {
    path: '/chat',
    name: 'chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { title: '对话', icon: 'chat', navIndex: 0 }
  },
  {
    path: '/projects',
    name: 'projects',
    component: () => import('@/views/ProjectsView.vue'),
    meta: { title: '项目', icon: 'projects', navIndex: 1 }
  },
  {
    path: '/projects/:id',
    name: 'project-detail',
    component: () => import('@/views/ProjectDetailView.vue'),
    meta: { title: '项目详情', icon: 'projects', navIndex: 1 },
    props: true
  },
  {
    path: '/plaza',
    name: 'plaza',
    component: () => import('@/views/PlazaView.vue'),
    meta: { title: '广场', icon: 'plaza', navIndex: 2 }
  },
  {
    path: '/memory',
    name: 'memory',
    component: () => import('@/views/MemoryView.vue'),
    meta: { title: '记忆', icon: 'memory', navIndex: 3 }
  },
  {
    path: '/files',
    name: 'files',
    component: () => import('@/views/FilesView.vue'),
    meta: { title: '文件', icon: 'files', navIndex: 4 }
  },
  {
    path: '/connections',
    name: 'connections',
    component: () => import('@/views/ConnectionsView.vue'),
    meta: { title: '连接', icon: 'connections', navIndex: 5 }
  },
  {
    path: '/lab',
    name: 'lab',
    component: () => import('@/views/LabView.vue'),
    meta: { title: '实验室', icon: 'lab', navIndex: 6 }
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { title: '设置', icon: 'settings', navIndex: -1 }
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
```

### 5.2 路由懒加载

所有页面使用 `() => import(...)` 动态导入，Vite 自动代码分割。

### 5.3 路由守卫

```typescript
// 可选：页面切换动画钩子
router.beforeEach((to, from) => {
  // 可以在这里设置页面过渡动画类型
  if (to.meta.navIndex !== undefined && from.meta.navIndex !== undefined) {
    const direction = (to.meta.navIndex as number) > (from.meta.navIndex as number)
      ? 'forward' : 'backward'
    document.documentElement.style.setProperty('--page-transition-direction', direction)
  }
})
```

---

## 六、布局体系

### 6.1 App.vue 根布局

```vue
<!-- src/App.vue -->
<template>
  <div class="workspace" :class="`page-${currentPage}`">
    <!-- L0: NavRail 固定 56px -->
    <NavRail />

    <!-- L1: 侧边栏（按页面切换显示） -->
    <SidebarContainer v-if="hasSidebar">
      <component :is="sidebarComponent" />
    </SidebarContainer>

    <!-- L2: 主内容区 -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- L3: 配置面板（可选） -->
    <ConfigPanel v-if="hasConfigPanel" />

    <!-- 浮动层 -->
    <ToastContainer />
    <GlobalSearch />
  </div>
</template>
```

### 6.2 4列布局

```
┌────────┬────────────┬────────────────────────┬──────────┐
│NavRail │  Sidebar   │     Main Content       │  Config  │
│ 56px   │ 260-320px  │     flex: 1            │ 320px    │
│ 固定   │ 可调宽度   │     弹性               │ 可选收起  │
└────────┴────────────┴────────────────────────┴──────────┘
```

**CSS 实现：**

```css
.workspace {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--color-bg-root);
}

.main-content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  position: relative;
}
```

**Config 面板 CSS：**

```css
.config-panel {
  width: 320px;
  min-width: 320px;
  max-width: 400px;
  border-left: 1px solid var(--border-subtle);
  background: var(--color-bg-surface);
  overflow-y: auto;
  transition: width 0.25s var(--ease-out);
}

.config-panel.collapsed {
  width: 0;
  min-width: 0;
  overflow: hidden;
}
```

### 6.3 侧边栏可调整宽度

```vue
<!-- SidebarContainer 实现分隔条拖拽 -->
<script setup lang="ts">
import { ref } from 'vue'

const sidebarWidth = ref(280)
const isResizing = ref(false)

function startResize(e: MouseEvent) {
  isResizing.value = true
  const startX = e.clientX
  const startWidth = sidebarWidth.value

  function onMouseMove(e: MouseEvent) {
    const delta = e.clientX - startX
    sidebarWidth.value = Math.max(260, Math.min(320, startWidth + delta))
  }

  function onMouseUp() {
    isResizing.value = false
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}
</script>
```

### 6.4 页面 vs 侧边栏映射表

| 页面路由 | 显示 Sidebar | Sidebar 内容 | 显示 Config |
|:---|:---:|:---|:---:|
| `/chat` | ✅ | 对话列表 | ✅ |
| `/projects` | ✅ | 工作间列表 | ❌ |
| `/projects/:id` | ❌ | — | ✅ |
| `/plaza` | ✅ | 广场分类 | ❌ |
| `/memory` | ✅ | 记忆类型筛选 | ❌ |
| `/files` | ✅ | 文件列表 | ❌ |
| `/connections` | ✅ | 连接列表 | ❌ |
| `/lab` | ✅ | 模块列表 | ❌ |
| `/settings` | ❌ | — | ❌ |

---

## 七、组件架构

### 7.1 通用组件规格

#### NavRail.vue（左侧固定导航栏）

```
Props: none (使用 router)
Emits: none
功能:
  - 7 个 Tab 图标导航（对话/项目/广场/记忆/文件/连接/实验室）
  - 底部：主题切换 + 账号菜单（设置/关于/退出）
  - 当前页高亮：2px 左侧品牌色竖线
  - 悬停 300ms tooltip 显示名称
  - 底部品牌呼吸动画（SVG Logo 脉冲）
```

#### ToastContainer.vue（全局通知系统）

```
组成:
  - 顶部居中的 Toast 列表
  - 每条 Toast：图标 + 文本 + 关闭按钮
  - 4 类型：success(绿) / error(珊瑚红) / warning(琥珀) / info(青)
  - 3s(success/info) / 4s(warning) / 5s(error) 自动消失
  - fadeIn + slideDown 动画
```

#### GlobalSearch.vue（Cmd+K 搜索）

```
触发: Cmd+K / Ctrl+K
行为:
  - 全屏半透明遮罩 + 顶部搜索输入框
  - 实时搜索：对话/文件/记忆/连接/技能
  - 结果分组展示，方向键导航，Enter 跳转
  - Escape 关闭
```

#### ContextMenu.vue（右键菜单）

```
Props:
  - items: MenuItem[] (label / icon / action / divider / disabled)
  - x, y: 位置坐标
使用:
  - 通过 composable useContextMenu 派发
  - 点击其他区域关闭
```

#### Dropdown.vue（下拉选择器）

```
Props:
  - items: DropdownItem[] (label / value / icon / description)
  - modelValue: 选中值
  - placement: 'bottom' | 'bottom-start' | 'bottom-end'
Emits:
  - update:modelValue
使用场景: 模型选择 / 连接器选择 / 专家选择
```

#### Modal.vue（模态框）

```
Props:
  - visible: boolean
  - title: string
  - width?: string (默认 480px)
  - showClose?: boolean
  - maskClosable?: boolean
Slots: default / footer
动画: 遮罩 fadeIn + 内容 scale+fade
```

### 7.2 对话组件规格

#### ChatInput.vue（6态输入区）

```
状态机:
  idle → focused → attached → processing → queue → voice
  ↓        ↓
  idle    idle

状态描述:
  idle:      默认态，placeholder + 工具栏按钮
  focused:   输入框获得焦点，显示底部辅助文字
  attached:  有附件，显示缩略预览条
  processing: 正在流式输出，显示暂停按钮
  queue:     任务进入队列，显示队列条数
  voice:     语音录制模式，显示波形动画

工具栏按钮: 上传文件 / 录制语音 / 模型选择器
快捷键: Enter 发送 / Shift+Enter 换行
```

#### StreamRenderer.vue（流式渲染器）

```
输入 Props:
  - content: string (流式累积文本)
  - isStreaming: boolean
  - metadata?: { model, tokens, tool_calls }

功能:
  - 实时渲染 Markdown（代码块/表格/列表/公式）
  - 代码块自动添加语言标签 + 复制按钮
  - DOMPurify 过滤 HTML
  - 流式完成后的 Tool 调用指示
```

### 7.3 项目组件规格

#### ProjectTasks.vue（Kanban 看板）

```
Props:
  - tasks: Task[]
  - columns: TaskColumn[]

功能:
  - 3 列看板: 待处理 / 进行中 / 已完成
  - 卡片拖拽排序（跨列）
  - 拖拽动画（ghost 卡片 + placeholder）
Col 宽度: 等分父容器宽度
数据: 通过 projectService 对接后端 API
```

---

## 八、状态管理

### 8.1 技术选型

**不使用 Pinia/Vuex 等全局状态库。** 采用 **Composition API + provide/inject + 单例 composable**，保持极致轻量。

### 8.2 状态分类

| 状态域 | composable | 存储 | 说明 |
|:---|:---|:---:|:---|
| 主题 | `useTheme` | localStorage + ref | 全局主题切换 |
| 聊天 | `useChat` | ref + API | 消息列表、流式状态、输入状态 |
| 项目 | `useProjects` | API () | 工作间列表、当前工作间 |
| 广场 | `usePlaza` | API | Skills/Experts/Models 数据 |
| 记忆 | `useMemory` | API | L1/L2/L3 记忆数据 |
| 连接 | `useConnections` | API | 连接列表与健康状态 |
| 文件 | `useFiles` | API | 文件列表与操作 |
| 实验室 | `useLab` | API | 引擎数据与仪表盘 |
| 通知 | `useToast` | ref | Toast 队列 |
| 搜索 | `useGlobalSearch` | ref | 搜索状态 |
| 布局 | `useLayout` | ref | 侧栏宽度、Config 展开状态 |

### 8.3 Composable 示例

```typescript
// src/composables/useToast.ts
import { ref } from 'vue'

interface Toast {
  id: number
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  duration?: number
}

const toasts = ref<Toast[]>([])
let nextId = 0

export function useToast() {
  function addToast(type: Toast['type'], message: string, duration?: number) {
    const id = nextId++
    const toast: Toast = { id, type, message, duration }
    toasts.value.push(toast)

    setTimeout(() => {
      removeToast(id)
    }, duration || (type === 'error' ? 5000 : type === 'warning' ? 4000 : 3000))
  }

  function removeToast(id: number) {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index !== -1) toasts.value.splice(index, 1)
  }

  return { toasts, addToast, removeToast }
}
```

---

## 九、API 对接

### 9.1 API 客户端

```typescript
// src/services/api.ts
const API_BASE = `${window.location.protocol}//${window.location.hostname || '127.0.0.1'}:18080`

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options
  })
  if (!response.ok) {
    throw new ApiError(response.status, `API error: ${response.status}`)
  }
  return response.json()
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' })
}
```

### 9.2 SSE 流式接收

```typescript
// src/composables/useSSE.ts
export function useSSE() {
  function streamResponse(
    messageId: string,
    callbacks: {
      onToken: (content: string, fullContent: string) => void
      onDone: (metadata: Record<string, unknown>) => void
      onError: (error: { code: string; message: string }) => void
      onProgress?: (data: unknown) => void
    }
  ) {
    const abortController = new AbortController()

    fetch(`${API_BASE}/api/v1/chat/stream/${messageId}`, {
      headers: { Accept: 'text/event-stream' },
      signal: abortController.signal
    }).then(async (response) => {
      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullContent = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let currentEvent = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              switch (currentEvent) {
                case 'token':
                  fullContent += data.content || ''
                  callbacks.onToken(data.content || '', fullContent)
                  break
                case 'done':
                  callbacks.onDone(data)
                  break
                case 'progress':
                  callbacks.onProgress?.(data)
                  break
                case 'error':
                  callbacks.onError(data)
                  break
              }
            } catch { /* skip malformed */ }
          }
        }
      }
    }).catch((err) => {
      if (err.name !== 'AbortError') {
        callbacks.onError({ code: 'FETCH_ERROR', message: err.message })
      }
    })

    return {
      stop: () => {
        abortController.abort()
        fetch(`${API_BASE}/api/v1/chat/stream/${messageId}/stop`, { method: 'POST' })
          .catch(() => {})
      }
    }
  }

  return { streamResponse }
}
```

### 9.3 API 端点对照表

| 域 | 方法 | Endpoint | 请求体 | 响应 |
|:---|:---|:---|:---|:---|
| 对话 | POST | `/api/v1/chat/messages` | `{workspace_id, content, model}` | `{message_id}` |
| 对话 | GET | `/api/v1/chat/stream/:id` | — | SSE 流 |
| 对话 | POST | `/api/v1/chat/stream/:id/stop` | — | `{ok}` |
| 对话 | GET | `/api/v1/chat/messages` | `?workspace_id&page&page_size` | `{messages[]}` |
| 工作间 | GET | `/api/v1/workspaces` | — | `{workspaces[]}` |
| 工作间 | POST | `/api/v1/workspaces` | `{name, template}` | `{workspace}` |
| 广场 | GET | `/api/v1/plaza/skills` | — | `{skills[]}` |
| 广场 | GET | `/api/v1/plaza/experts` | — | `{experts[]}` |
| 广场 | GET | `/api/v1/plaza/models` | — | `{models[]}` |
| 记忆 | GET | `/api/v1/memory/l1` | `?query&page` | `{memories[]}` |
| 记忆 | GET | `/api/v1/memory/l2` | `?date` | `{memories[]}` |
| 记忆 | GET | `/api/v1/memory/l3` | `?schema` | `{entities[]}` |
| 文件 | GET | `/api/v1/files` | — | `{files[]}` |
| 文件 | POST | `/api/v1/files/backup` | — | `{task_id}` |
| 连接 | GET | `/api/v1/connections` | — | `{connections[]}` |
| 连接 | GET | `/api/v1/connections/:id/health` | — | `{status}` |
| 实验室 | GET | `/api/v1/lab/dashboard` | — | `{stats}` |
| 实验室 | GET | `/api/v1/lab/modules` | — | `{modules[]}` |
| 健康 | GET | `/health` | — | `{status, version}` |
| 模型 | GET | `/api/v1/models/available` | — | `{models[]}` |

---

## 十、页面实现指引

### 10.1 ChatView.vue（对话页）

**原型参考：** `niuma-neon-pulse-prototype.html` 第 12452-12618 行附近（对话面板）

**组件组合：**

```
ChatView
├── ChatSidebar         ← 左侧对话列表（按时间分组+搜索+新建）
├── 消息流程             ← 核心区域
│   ├── messages-inner  ← 滚动容器
│   │   ├── ChatMessage (user)  ← 用户消息气泡
│   │   └── ChatMessage (ai)    ← AI 回复（含 StreamRenderer）
│   └── ThinkingIndicator       ← 思考中动画
├── ChatInput           ← 底部 6 态输入区
└── ConfigPanel          ← 右侧配置面板（连接器/专家/Skill）
```

**关键实现细节：**
- 消息列表使用反向虚拟滚动（保留底部位置）
- SSE 流式接收 → StreamRenderer 增量渲染
- 消息右键 ContextMenu（复制/重试/编辑/删除）
- 代码块自动高亮 + 语言标签 + 一键复制
- 加载更早消息按钮（滚动到顶部时触发）

### 10.2 ProjectsView.vue + ProjectDetailView.vue（项目页）

**原型参考：** `niuma-neon-pulse-prototype.html` pageProjects / pageProjectDetail

**ProjectsView（列表）：**
```
ProjectsView
├── Sidebar: 工作间树形列表（分组 + 新建按钮）
├── Main: 项目卡片 Grid / 空状态
└── Kanban 面板（内嵌在项目主视图）
```

**ProjectDetailView（详情）：**
```
ProjectDetailView
├── 返回按钮 + 项目标题栏
├── Tab 导航 (Activity / SOP / Tasks / Assets)
├── Activity 标签: 项目内对话（复用 ChatMessage + ChatInput）
├── SOP 标签: 标准流程卡片列表
├── Tasks 标签: Kanban 看板（可拖拽）
├── Assets 标签: 资源文件列表
└── 右侧: ProjectConfig 面板
```

### 10.3 PlazaView.vue（广场页）

**原型参考：** `niuma-neon-pulse-prototype.html` pagePlaza

```
PlazaView
├── Sidebar: 分类标签（全部/创作/开发/分析/效率）
├── Main: 3 列卡片 Grid
│   ├── Skills 分类: 技能卡片（名称/描述/安装量/评分）
│   ├── Experts 分类: 专家 Agent 卡片
│   └── Models 分类: 模型卡片（提供商/能力/速率限制）
└── 卡片 hover: 展开详情 + 安装按钮
```

**数据已对接后端 API。**

### 10.4 MemoryView.vue（记忆页）

**原型参考：** `niuma-neon-pulse-prototype.html` pageMemory

```
MemoryView
├── Tab 导航 (L1 会话 / L2 短期 / L3 知识库)
├── L1 标签: 对话记忆检索（搜索框 + 结果列表）
├── L2 标签: 日历导航 + 每日记忆卡片
└── L3 标签: Schema 分类 + 实体网格 + 梦境详情
```

### 10.5 SettingsView.vue（设置页）

**原型参考：** `niuma-neon-pulse-prototype.html` pageSettings（8 面板）

```
SettingsView
├── Tab 导航 (API Keys / 偏好 / 快捷键 / 关于)
├── API Keys: 3提供商卡片 + 新增按钮 + 测试连接
├── 偏好: 语言/默认模型/主题切换
├── 快捷键: 搜索 + 类别分组表格
└── 关于: 版本号/引擎状态/版权
```

### 10.6 LabView.vue（实验室页）

**原型参考：** `niuma-neon-pulse-prototype.html` pageLab

```
LabView
├── Hero 区块: 引擎状态/运行时间/模块计数
├── Token 趋势图表
├── 引擎网格: 6 大模块状态卡片（铭心/缩龙成寸/太虚境/夜巡/自化/清风）
└── 涌现视图: 跨模块协同关系
```

### 10.7 ConnectionsView.vue（连接页）

**原型参考：** `niuma-neon-pulse-prototype.html` pageConnections

```
ConnectionsView
├── 分类标签（数据源/通信/存储/开发/其他）
├── 连接卡片 Grid
│   ├── 连接名称 + 类型图标
│   ├── 连接状态指示灯（在线/离线/错误）
│   └── 配置按钮
└── 健康检测定时刷新（每 30s）
```

### 10.8 FilesView.vue（文件页）

**原型参考：** `niuma-neon-pulse-prototype.html` pageFiles

```
FilesView
├── Tab 导航（工作文件 / 记忆文件）
├── 文件列表（名称/大小/日期/类型/操作）
├── 上传按钮 + 拖拽上传区域
├── 导出/备份操作
└── 文件预览（点击展开）
```

---

## 十一、动画系统

### 11.1 动画 Token

```css
/* 缓动函数 */
--ease-spring: cubic-bezier(.34,1.56,.64,1);   /* 弹性 */
--ease-out: cubic-bezier(0,0,.2,1);             /* 减速 */
--ease-in-out: cubic-bezier(.4,0,.2,1);          /* 标准 */
--ease-smooth: cubic-bezier(0.16,1,0.3,1);      /* 柔和 */

/* 时长 */
--dur-instant: 80ms;
--dur-fast: 150ms;
--dur-base: 250ms;
--dur-slow: 350ms;
--dur-page: 500ms;
--dur-enter: 700ms;
```

### 11.2 页面过渡动画

```css
/* 页面切入 */
.page-enter-active {
  animation: pageIn 0.4s var(--ease-out);
}
.page-leave-active {
  animation: pageOut 0.25s var(--ease-out);
}

@keyframes pageIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes pageOut {
  from { opacity: 1; transform: translateY(0); }
  to   { opacity: 0; transform: translateY(-4px); }
}
```

### 11.3 消息渐入动画

```css
.message-enter-active {
  animation: messageIn 0.3s var(--ease-out);
}

@keyframes messageIn {
  from { opacity: 0; transform: translateY(8px) scale(0.97); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
```

### 11.4 骨架屏脉冲

```css
@keyframes skeletonPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.skeleton {
  background: var(--color-bg-elevated);
  border-radius: var(--radius-sm);
  animation: skeletonPulse 1.5s ease-in-out infinite;
}
```

### 11.5 Stagger 卡片动画

```css
/* 通过 CSS 动画延迟实现逐步出现 */
.card-stagger {
  animation: cardIn 0.35s var(--ease-out) both;
}

.card-stagger:nth-child(1) { animation-delay: 0ms; }
.card-stagger:nth-child(2) { animation-delay: 50ms; }
.card-stagger:nth-child(3) { animation-delay: 100ms; }
/* ... 每项 +50ms，最多 300ms */

@keyframes cardIn {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

### 11.6 品牌呼吸动画

```css
@keyframes brandPulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

.nav-brand-logo {
  animation: brandPulse 3s var(--ease-smooth) infinite;
}
```

### 11.7 Toast 滑入动画

```css
.toast-enter-active {
  animation: toastIn 0.25s var(--ease-spring);
}
.toast-leave-active {
  animation: toastOut 0.2s var(--ease-out);
}

@keyframes toastIn {
  from { opacity: 0; transform: translateY(-16px) scale(0.95); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes toastOut {
  from { opacity: 1; transform: translateY(0) scale(1); }
  to   { opacity: 0; transform: translateY(-8px) scale(0.95); }
}
```

---

## 十二、响应式与无障碍

### 12.1 响应式断点

```css
/* 断点 */
--bp-sm: 640px;
--bp-md: 768px;
--bp-lg: 1024px;
--bp-xl: 1280px;

/* 响应式行为 */
@media (max-width: 1024px) {
  .config-panel { display: none; }
}

@media (max-width: 768px) {
  .sidebar-container { display: none; }
}
```

### 12.2 无障碍要求

- 所有交互元素提供 `aria-label`
- 导航栏使用 `<nav>` + `aria-current="page"`
- 模态框使用 `role="dialog"` + `aria-modal="true"`
- Toast 通知使用 `role="alert"` + `aria-live="polite"`
- 支持键盘导航（Tab / Enter / Escape / 方向键）
- 尊重 `prefers-reduced-motion`（关闭动画）

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 十三、构建与部署

### 13.1 开发命令

```bash
npm run dev      # 开发服务器 → http://localhost:5173
npm run build    # 生产构建 → dist/
npm run preview  # 预览构建产物
```

### 13.2 构建产物

```
dist/
├── index.html
├── favicon.svg
└── assets/
    ├── index-{hash}.js       # 应用 JS（路由懒加载分 chunk）
    ├── index-{hash}.css       # DS Token + 组件样式
    └── [chunk-name]-{hash}.js # 页面级 chunk（懒加载）
```

### 13.3 WebView2 嵌入

桌面客户端通过 WebView2 加载构建后的 `dist/index.html`：

```
WebView2 → http://localhost:5173 (开发)
         → file:///dist/index.html (生产)
```

**Hash 路由保障：** 客户端无需配置服务端回退，`#/chat` 格式兼容文件协议。

---

## 十四、迁移指南：原型 → Vue

### 14.1 迁移总策略

```
原型 HTML  →  Vue 组件
├── CSS Token    →  src/styles/tokens.css（保留变量名一致）
├── 页面 HTML    →  src/views/*.vue（拆分独立组件）
├── JS 交互     →  src/composables/*.ts（Composition API）
├── API 调用    →  src/services/*.ts（TypeScript 封装）
└── SVG 图标    →  src/utils/icons.ts（常量集中管理）
```

### 14.2 迁移步骤（按页面）

| 阶段 | 页面 | 原型行号参考 | Vue 文件 | 估计人天 |
|:---|:---|:---:|:---|:---:|
| Phase1 | 布局框架 | 1-800 | App.vue + NavRail.vue + SidebarContainer.vue | 2 |
| Phase1 | 路由 + 空页面壳 | — | router/index.ts + 所有 View 空壳 | 1 |
| Phase2 | 对话页 | 12452+ | ChatView.vue + ChatMessage + ChatInput + SSE | 3 |
| Phase2 | 项目页 | 12452+12619 | ProjectsView + ProjectDetailView | 2 |
| Phase2 | 广场页 | 13967+ | PlazaView.vue + PlazaCard | 1 |
| Phase2 | 记忆页 | 13351+ | MemoryView.vue | 1.5 |
| Phase2 | 文件页 | 13860+ | FilesView.vue | 0.5 |
| Phase2 | 连接页 | 14148+ | ConnectionsView.vue | 0.5 |
| Phase2 | 实验室页 | 14294+ | LabView.vue | 0.5 |
| Phase3 | 设置页 | 14443+ | SettingsView.vue | 1.5 |
| Phase3 | 动画对齐 | — | animations.css | 1 |
| Phase3 | 主题补齐 | — | tokens.css (Day/Classic) | 1 |
| **合计** | | | | **14-15** |

### 14.3 Token 变量迁移对照

| 原型变量 | Vue 变量 | 备注 |
|:---|:---|:---|
| `--bg-root` | `--color-bg-root` | 别名，Vue 优先用 `--color-bg-*` |
| `--bg-surface` | `--color-bg-surface` | 同上 |
| `--bg-elevated` | `--color-bg-card` | 名称统一 |
| `--text-primary` | `--color-text-primary` | 同上 |
| `--brand` | `--color-brand` | 同上 |
| `--border-subtle` | `--border-subtle` | 一致 |
| `--radius-sm` | `--radius-sm` | 一致 |
| `--space-3` | `--space-3` | 一致 |

### 14.4 从原型提取 CSS 的注意事项

原型 `niuma-neon-pulse-prototype.html` 约 19,884 行，提取 CSS 时注意：

1. **Token 定义（1-400行）** → 直接复制到 `tokens.css`，保持变量名一致
2. **布局样式（400-3900行）** → 复制到 `components.css`，删除原型独有选择器
3. **页面独有样式（3900-12450行）** → 提取到对应 Vue 组件的 `<style scoped>` 中
4. **动画 keyframes（12450+行）** → 复制到 `animations.css`
5. **不要从原型 import CSS**——原型 CSS 是基于单文件 HTML 的。必须提取到独立 CSS 文件

### 14.5 常见陷阱

| 问题 | 原因 | 解决方法 |
|:---|:---|:---|
| 页面内容偏移 | 原型是单文件，CSS 选择器互相影响 | Vue 用 scoped CSS 隔离 |
| 主题切换不完全 | Day/Classic 的 CSS 覆盖不足 | 补齐 L0 seed 后，L1/L2 自动派生 |
| 动画不生效 | Vue Transition 与 CSS animation 配合不当 | 使用 `<Transition>` + CSS class |
| SSE 连接断开 | 组件销毁时未清理 stream | `onUnmounted()` 中调用 `abortController.abort()` |
| 右键菜单被截断 | ContextMenu 超出视口 | 动态计算 placement（上/下/左/右） |

---

## 附录 A：关键文件清单

| 文件 | 说明 | 状态 |
|:---|:---|:--:|
| `frontend/niuma-neon-pulse-prototype.html` | 活跃原型 (19,884行, v10.0) | ✅ 已就绪 |
| `design system/design-tokens.css` | DS v16.0 L0+L1 Token | ✅ 已就绪 |
| `design system/components.css` | DS v16.0 L2 组件样式 (136KB) | ✅ 已就绪 |
| `design system/design-system.html` | DS v18.0 设计展示页 | ✅ 已就绪 |
| `frontend/js/niuma-api.js` | API 客户端 (vanilla JS) | 需转 TS |
| `frontend/js/niuma-chat-bridge.js` | SSE 对话桥接 | 需转 TS |
| `deliverables/prototype-vs-vue-gap-analysis-2026-06-30.md` | 差距分析 | ✅ 参考文档 |
| `frontend-vue/src/` | Vue 源目录（当前为空） | ⏳ 待填充 |

## 附录 B：开发规范

1. **文件命名**：PascalCase 组件（`ChatMessage.vue`），camelCase composable（`useTheme.ts`）
2. **CSS 命名**：kebab-case class（`.chat-message`），BEM 风格（`.chat-message__header`）
3. **TypeScript**：尽量为所有 API 响应定义 interface，禁止 `any`
4. **组件通信**：Props down / Events up，复杂状态用 composable 共享
5. **性能**：router 使用懒加载，大列表使用虚拟滚动，流式渲染使用 requestAnimationFrame 节流
6. **安全**：所有用户内容（尤其是流式 AI 回复）必须通过 DOMPurify 过滤
7. **兼容性**：仅在 Chrome/Edge/WebView2 最新版本上运行保证，不做老旧浏览器兼容

## 附录 C：参考文件

| 文档 | 用途 |
|:---|:---|
| `docs/product-spec-v3.0.md` | 产品需求总纲 |
| `docs/architecture-doc.md` | 系统架构设计 |
| `docs/frontend-ui-ux-spec-v1.0.md` | 前端 UI/UX 设计规格 (历史版本) |
| `design system/design-tokens.css` | 设计系统 Token |
| `design system/components.css` | 组件样式 |
| `deliverables/prototype-vs-vue-gap-analysis-2026-06-30.md` | 原型 vs Vue 差距分析 |
| `deliverables/frontend-design-system-optimization-plan-2026-06-29.md` | 前端工程化重构计划 |

---

*本文档由产品通基于超级牛马工作台 v1.7 实际前端状态（原型 v10.0 + DS v18.0）生成，所有路径均对齐项目当前文件结构。*
