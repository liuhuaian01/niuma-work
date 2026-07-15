# 超级牛马 · 开发者实施指南

> 给前端开发者的上手指南，基于 UX 架构 v2.0

---

## 1. 技术决策速查

| 决策 | 结论 | 不要做 |
|:--|:--|:--|
| 框架 | Vue 3 + Vite + TypeScript | 不要原生 JS 单文件 HTML |
| 路由 | Vue Router hash 模式 | 不要多 HTML 文件 |
| CSS | 全部通过 Token 变量引用 | 不要裸色值、不要内联 style |
| 品牌色 | `#4DA8F0` 牛马蓝 | 不要用薄荷绿、不要用紫色 |
| 主题 | Day/Night/System 三选一 | 不要仅深色 |
| 字体 | DM Sans + PingFang SC | 不要引入 CDN 字体 |
| 图标 | Lucide Icons (SVG) | 不要用 emoji |
| 分辨率 | 桌面 1280×720+ | 不做移动端适配 |
| API | 后端 localhost:18080 | — |

---

## 2. 文件结构（新建项目）

```
frontend/
├── index.html                     # SPA 入口
├── package.json
├── vite.config.ts
├── tsconfig.json
├── src/
│   ├── main.ts                    # Vue 挂载入口
│   ├── App.vue                    # App Shell 根组件
│   ├── router/
│   │   └── index.ts               # 路由定义（8页）
│   ├── stores/
│   │   ├── workspace.ts           # 工作间状态
│   │   ├── chat.ts                # 对话状态
│   │   ├── theme.ts               # 主题状态
│   │   └── api.ts                 # API 连接状态
│   ├── composables/
│   │   ├── useSSE.ts              # SSE 流式接收
│   │   ├── useTheme.ts            # 主题切换逻辑
│   │   └── useKanban.ts           # 拖拽逻辑
│   ├── components/
│   │   ├── nav-rail/
│   │   │   └── NavRail.vue        # 左侧导航栏
│   │   ├── chat/
│   │   │   ├── ChatSidebar.vue    # 对话列表
│   │   │   ├── ChatMessages.vue   # 消息区
│   │   │   ├── ChatInput.vue      # 输入框
│   │   │   └── ChatBubble.vue     # 消息气泡
│   │   ├── kanban/
│   │   │   ├── KanbanBoard.vue    # 看板容器
│   │   │   ├── KanbanColumn.vue   # 列
│   │   │   └── KanbanCard.vue     # 卡片
│   │   ├── dashboard/
│   │   │   ├── TokenStats.vue     # 统计卡片
│   │   │   ├── TrendChart.vue     # 趋势图
│   │   │   └── ModelPie.vue       # 模型分布
│   │   ├── shared/
│   │   │   ├── ThemeToggle.vue    # 主题切换按钮组
│   │   │   ├── EmptyState.vue     # 空状态组件
│   │   │   ├── SkeletonLoader.vue # 骨架屏
│   │   │   ├── Toast.vue          # Toast 通知
│   │   │   └── Spinner.vue        # 加载旋转
│   │   └── onboarding/
│   │       └── OnboardingFlow.vue # 3步引导
│   ├── pages/
│   │   ├── ChatPage.vue           # 对话页
│   │   ├── WorkspacePage.vue      # 工作室页
│   │   ├── PlazaPage.vue          # 广场页
│   │   ├── MemoryPage.vue         # 记忆页
│   │   ├── ConnectPage.vue        # 连接页
│   │   └── SettingsPage.vue       # 设置页（含5tab：许可证/偏好/看板/任务/关于）
│   ├── api/
│   │   └── index.ts               # API 客户端（TypeScript 版）
│   └── utils/
│       ├── theme.ts               # 主题工具函数
│       ├── format.ts              # 格式化工具
│       └── animate.ts             # 动画工具
├── public/
│   └── css/
│       ├── design-tokens.css      # Token 系统（从 DS 复制）
│       ├── components.css         # 组件样式库（从 DS 复制）
│       └── layout-app.css         # App 布局（新建）
```

---

## 3. 关键代码示例

### 3.1 App.vue (App Shell)

```vue
<template>
  <div class="app-shell">
    <!-- 左侧导航栏 -->
    <NavRail 
      :items="navItems" 
      :active="currentRoute" 
      @navigate="handleNavigate" 
    />

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- Toast 全局通知 -->
    <Toast />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import NavRail from './components/nav-rail/NavRail.vue';
import Toast from './components/shared/Toast.vue';

const route = useRoute();
const router = useRouter();

const currentRoute = computed(() => route.name as string);

const navItems = [
  { id: 'chat',      icon: 'MessageCircle',     label: '对话' },
  { id: 'workspace', icon: 'Building2',         label: '工作室' },
  { id: 'plaza',     icon: 'Store',             label: '广场' },
  { id: 'memory',    icon: 'Brain',             label: '记忆' },
  { id: 'connect',   icon: 'PlugZap',           label: '连接' },
  { id: 'settings',  icon: 'Settings',           label: '设置' },
];

function handleNavigate(id: string) {
  router.push({ name: id });
}
</script>
```

### 3.2 路由定义

```typescript
// src/router/index.ts
import { createRouter, createWebHashHistory } from 'vue-router';

const routes = [
  {
    path: '/',
    redirect: '/chat'
  },
  {
    path: '/chat',
    name: 'chat',
    component: () => import('../pages/ChatPage.vue'),
    meta: { title: '对话' }
  },
  {
    path: '/workspace',
    name: 'workspace',
    component: () => import('../pages/WorkspacePage.vue'),
    meta: { title: '工作室' }
  },
  {
    path: '/tasks',
    name: 'tasks',
    component: () => import('../pages/TasksPage.vue'),
    meta: { title: '任务' }
  },
  {
    path: '/plaza',
    name: 'plaza',
    component: () => import('../pages/PlazaPage.vue'),
    meta: { title: '广场' }
  },
  {
    path: '/memory',
    name: 'memory',
    component: () => import('../pages/MemoryPage.vue'),
    meta: { title: '记忆' }
  },
  {
    path: '/connect',
    name: 'connect',
    component: () => import('../pages/ConnectPage.vue'),
    meta: { title: '连接' }
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('../pages/SettingsPage.vue'),
    meta: { title: '设置' }
  }
];

const router = createRouter({
  history: createWebHashHistory(),
  routes
});

export default router;
```

### 3.3 主题切换组件

```vue
<!-- src/components/shared/ThemeToggle.vue -->
<template>
  <div class="theme-toggle" role="radiogroup" aria-label="主题切换">
    <button
      v-for="option in options"
      :key="option.value"
      :data-theme-toggle="option.value"
      :class="['theme-toggle__option', { 
        'theme-toggle__option--active': currentTheme === option.value 
      }]"
      :aria-checked="String(currentTheme === option.value)"
    >
      <component :is="option.icon" :size="16" />
      <span>{{ option.label }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Sun, Moon, Monitor } from 'lucide-vue-next';

const currentTheme = computed(() => window.NiumaTheme?.getTheme() || 'system');

const options = [
  { value: 'day',    label: '浅色', icon: Sun },
  { value: 'night',  label: '深色', icon: Moon },
  { value: 'system', label: '系统', icon: Monitor },
];
</script>
```

### 3.4 SSE 流式对话

```typescript
// src/composables/useSSE.ts
import { ref } from 'vue';

export function useSSE() {
  const content = ref('');
  const isStreaming = ref(false);
  const error = ref<string | null>(null);
  let abortController: AbortController | null = null;

  async function startStream(messageId: string) {
    content.value = '';
    isStreaming.value = true;
    error.value = null;
    abortController = new AbortController();

    try {
      const response = await fetch(
        `http://127.0.0.1:18080/api/v1/chat/stream/${messageId}`,
        {
          headers: { 'Accept': 'text/event-stream' },
          signal: abortController.signal
        }
      );

      const reader = response.body?.getReader();
      if (!reader) throw new Error('无法读取流');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'token') {
              content.value += data.content;
            } else if (data.type === 'done') {
              isStreaming.value = false;
              return;
            } else if (data.type === 'error') {
              error.value = data.message;
              isStreaming.value = false;
              return;
            }
          }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        error.value = e.message;
        isStreaming.value = false;
      }
    }
  }

  function stopStream() {
    abortController?.abort();
    isStreaming.value = false;
  }

  return { content, isStreaming, error, startStream, stopStream };
}
```

---

## 4. 实施顺序（按阶段）

### 阶段 0：1-2 天

```
Day 1:
  ├── npm create vite@latest frontend -- --template vue-ts
  ├── npm install vue-router pinia lucide-vue-next
  ├── 复制 design-tokens.css → public/css/
  ├── 复制 components.css → public/css/
  ├── 复制 layout-app.css → public/css/
  └── 在 index.html 中 link 三个 CSS

Day 2:
  ├── 实现 ThemeManager（或直接用 theme-manager.js）
  ├── 搭建 App.vue + NavRail.vue
  ├── 配置路由（8页占位）
  └── 验证：三主题切换 + 8页面路由切换
```

### 阶段 1：3-5 天

```
Day 3-4: 对话页
  ├── ChatMessages.vue (消息列表)
  ├── ChatInput.vue (输入框)
  ├── ChatBubble.vue (Markdown 渲染)
  ├── 集成 niuma-api.js SSE 流式
  └── 验证："你好" → AI 回复

Day 5: 引导流程
  ├── OnboardingFlow.vue (3步)
  ├── 首次检测 → 触发引导
  └── 验证：新用户完整流程 ≤ 60s
```

### 阶段 2-4：见架构文档第八节

---

## 5. 从现有 HTML 迁移指南

### Kanban → 设置页"工作台→任务看板" panel

| 原文件 | 目标 | 迁移内容 |
|:--|:--|:--|
| `kanban-panel.html` 全部 CSS | `<style>` 块 → 合并进 design-tokens 体系 | 4列布局、卡片、拖拽，颜色改用 Token |
| `kanban-panel.html` HTML | 封装为 `settings-panel` 放入 `settingsDetail` | 看板 DOM 结构，挂载到 `#settingPanelKanban` |
| `kanban-panel.html` JS | `switchSetting('kanban')` 时初始化 | 拖拽事件、工作间切换、Mock 数据 |

### Token Dashboard → 设置页"工作台→用量看板" panel

| 原文件 | 目标 | 迁移内容 |
|:--|:--|:--|
| `token-dashboard.html` 全部 CSS | `<style>` 块 → 合并进 design-tokens 体系 | 指标卡片、趋势图、环形图，颜色改用 Token |
| `token-dashboard.html` HTML | 封装为 `settings-panel` 放入 `settingsDetail` | DOM 结构，挂载到 `#settingPanelDashboard` |
| `token-dashboard.html` JS | `switchSetting('dashboard')` 时初始化 | Canvas 图表、30s 刷新、Mock 回退 |

---

## 6. 快速自检清单

完成后逐项核验：

- [ ] 打开应用 → 3秒内看到界面（非白屏）
- [ ] 品牌色全局一致 `#4DA8F0`
- [ ] 浅色/深色/系统 三种主题可切换
- [ ] 6个导航图标可点击切换页面
- [ ] 输入框在对话页自动聚焦
- [ ] 输入文字 + Enter → SSE 流式输出
- [ ] 后端不可用时页面不崩溃
- [ ] 所有 CSS 颜色通过 Token 变量引用
- [ ] `Ctrl+K` 可搜索（如已实现）
- [ ] `prefers-reduced-motion` 下动画关闭
- [ ] 异常状态有 Toast 通知
- [ ] 空状态有引导按钮

---

**ArchitectUX Agent**  
**交付完成**：UX 架构 + CSS 布局 + 主题管理 + 实施指南
