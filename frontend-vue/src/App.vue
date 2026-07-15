<template>
  <div class="workspace" :class="'page-' + activeTab" id="mainContent">
    <!-- Navigation Rail -->
    <nav class="nav-rail" aria-label="Navigation">
      <a href="#" class="nav-brand-logo" title="超级牛马 — 回到对话" data-tooltip="超级牛马 — 回到对话" @click.prevent="navigate('chat')">
        <img src="/assets/icon.jpg" alt="超级牛马" width="36" height="36" />
      </a>
      <div class="nav-items">
        <button v-for="item in navItems" :key="item.page"
          class="nav-btn" :class="{ active: activeTab === item.page }"
          :data-page="item.page" :title="item.label" :data-tooltip="item.label"
          :aria-label="item.label"
          @click="navigate(item.page)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"
            stroke-linecap="round" stroke-linejoin="round" v-html="item.icon"></svg>
        </button>
      </div>
      <div class="nav-spacer"></div>
      <div class="nav-account">
        <button class="nav-account-btn" :aria-expanded="accountOpen" title="账号" data-tooltip="账号" @click="accountOpen = !accountOpen">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
        </button>
        <div class="account-panel" :class="{ active: accountOpen }">
          <div class="account-panel-header">
            <div class="account-panel-avatar">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
                stroke-linecap="round" stroke-linejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <div class="account-panel-info">
              <div class="account-panel-name">刘淮安</div>
              <div class="account-plan-badge">Pro Plan</div>
            </div>
          </div>
          <div class="account-panel-divider"></div>
          <button class="account-panel-item" @click="navigate('settings'); accountOpen = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
            <span>系统设置</span>
          </button>
          <button class="account-panel-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/>
              <path d="M2 12h20"/>
            </svg>
            <span>个性偏好</span>
          </button>
          <button class="account-panel-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round">
              <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
              <line x1="1" y1="10" x2="23" y2="10"/>
            </svg>
            <span>订阅管理</span>
          </button>
          <div class="account-panel-divider"></div>
          <button class="account-panel-item theme-toggle-row" @click="cycleTheme">
            <svg class="icon-sun-acct" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round"
              :style="{ display: currentTheme === 'day' ? '' : 'none' }">
              <circle cx="12" cy="12" r="5"/>
              <line x1="12" y1="1" x2="12" y2="3"/>
              <line x1="12" y1="21" x2="12" y2="23"/>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
              <line x1="1" y1="12" x2="3" y2="12"/>
              <line x1="21" y1="12" x2="23" y2="12"/>
            </svg>
            <svg class="icon-moon-acct" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round"
              :style="{ display: currentTheme === 'night' ? '' : 'none' }">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
            <svg class="icon-book-acct" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round"
              :style="{ display: currentTheme === 'classic' ? '' : 'none' }">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
              <path d="M20 2v20H6.5A2.5 2.5 0 0 1 4 19.5V4a2 2 0 0 1 2-2h14z"/>
            </svg>
            <span>切换主题</span>
            <span class="theme-label">{{ themeLabel }}</span>
          </button>
          <button class="account-panel-item logout-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            <span>退出登录</span>
          </button>
        </div>
      </div>
    </nav>

    <!-- Main Content Area -->
    <div class="main-content">
      <div class="content-area">
        <router-view />
      </div>
    </div>

    <!-- Workspace Footer -->
    <div class="workspace-footer">
      <div class="wf-brand">
        <div class="wf-brand-icon">牛</div>
        <span class="wf-brand-name">超级牛马</span>
      </div>
      <div class="wf-divider"></div>
      <div class="wf-metrics">
        <div class="wf-metric"><span class="wf-dot"></span> Hermes <strong>在线</strong></div>
        <div class="wf-metric"><span class="wf-dot"></span> Workers <strong>8</strong></div>
        <div class="wf-metric"><span class="wf-dot off"></span> Token <strong>12.4k</strong></div>
        <div class="wf-metric"><span class="wf-dot"></span> SPI <strong>0.93</strong></div>
      </div>
      <div class="wf-right">
        <span class="wf-group">当前 · <strong>默认工作区</strong></span>
        <span class="wf-pulse"></span>
        <span class="wf-timer">00:00:00</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';

const router = useRouter();
const route = useRoute();

const activeTab = ref('chat');
const accountOpen = ref(false);
const currentTheme = ref('night');

const themes = ['night', 'day', 'classic'];
const themeNames: Record<string, string> = { night: '深色', day: '浅色', classic: '经典' };
const themeLabel = computed(() => themeNames[currentTheme.value] || 'Dark');

const navItems = [
  { page: 'chat', label: '对话', icon: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>' },
  { page: 'projects', label: '项目', icon: '<rect x="3" y="3" width="10" height="8" rx="1.5"/><rect x="11" y="7" width="10" height="10" rx="1.5"/><line x1="6" y1="7" x2="9" y2="7"/><line x1="6" y1="9" x2="8" y2="9"/><line x1="14" y1="11" x2="18" y2="11"/><line x1="14" y1="13" x2="16" y2="13"/><line x1="14" y1="15" x2="17" y2="15"/>' },
  { page: 'plaza', label: '广场', icon: '<rect x="2" y="4" width="7" height="6" rx="1.5"/><rect x="15" y="4" width="7" height="6" rx="1.5"/><rect x="2" y="14" width="7" height="6" rx="1.5"/><rect x="15" y="14" width="7" height="6" rx="1.5"/><circle cx="12" cy="12" r="1.5"/><line x1="8.5" y1="7" x2="10.5" y2="10.5"/><line x1="15.5" y1="7" x2="13.5" y2="10.5"/><line x1="8.5" y1="17" x2="10.5" y2="13.5"/><line x1="15.5" y1="17" x2="13.5" y2="13.5"/>' },
  { page: 'memory', label: '记忆', icon: '<circle cx="12" cy="12" r="10"/><polyline points="8 12 10 9 12 11 14 7 16 10"/>' },
  { page: 'files', label: '文件', icon: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="14" y2="17"/>' },
  { page: 'connections', label: '连接', icon: '<circle cx="18" cy="5" r="2.5"/><circle cx="5" cy="12" r="2.5"/><circle cx="18" cy="19" r="2.5"/><line x1="7.5" y1="12" x2="15.5" y2="5" opacity=".8"/><line x1="7.5" y1="12" x2="15.5" y2="19" opacity=".8"/>' },
  { page: 'lab', label: '实验室', icon: '<path d="M9 3h6"/><path d="M10 3v6l-5 9a2 2 0 0 0 1.73 3h10.54a2 2 0 0 0 1.73-3l-5-9V3"/>' },
];

watch(() => route.path, (path) => {
  const tab = path.replace('/', '').split('/')[0] || 'chat';
  activeTab.value = tab;
}, { immediate: true });

function navigate(page: string) {
  activeTab.value = page;
  accountOpen.value = false;
  router.push('/' + page);
}

function cycleTheme() {
  const idx = themes.indexOf(currentTheme.value);
  const next = themes[(idx + 1) % 3];
  currentTheme.value = next;
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('niuma_theme', next);
}

// Init theme (also handle legacy "light" → "day" migration)
const saved = localStorage.getItem('niuma_theme');
if (saved) {
  const theme = saved === 'light' ? 'day' : saved;
  currentTheme.value = themes.includes(theme) ? theme : 'night';
  document.documentElement.setAttribute('data-theme', currentTheme.value);
}
// Close account panel on outside click
function onClick(e: MouseEvent) {
  const t = e.target as HTMLElement;
  if (accountOpen.value && !t.closest('.nav-account')) {
    accountOpen.value = false;
  }
}
if (typeof window !== 'undefined') {
  document.addEventListener('click', (e) => {
    if (accountOpen.value && !(e.target as HTMLElement).closest('.nav-account')) {
      accountOpen.value = false;
    }
  });
}
</script>
