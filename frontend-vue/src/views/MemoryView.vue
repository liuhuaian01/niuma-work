<template>
<div class="page-view active" id="pageMemory">
  <div class="page-header" style="margin-bottom:20px;padding-bottom:16px;">
    <div><h1>记忆</h1><p class="page-subtitle">日记 · 做梦 · 长期记忆</p></div>
  </div>

  <div class="pg-banner pg-b-memory" style="margin:0 0 20px;min-height:120px">
    <div class="pg-bd"><div class="pg-eyebrow"><span class="pg-eb-dot"></span> 记忆网络</div><div class="pg-title">意识流</div><div class="pg-desc">神经元连接形成记忆网络，每一次对话都在编织认知图谱</div></div>
    <div class="pg-viz"><div class="pg-ring"><div class="pg-rl"></div><div class="pg-rl"></div><div class="pg-rl"></div><div class="pg-core"></div></div></div>
  </div>

  <!-- Tab 导航 -->
  <div class="mem3-nav">
    <button class="mem3-tab" :class="{ active: memTab === 'diary' }" @click="memTab = 'diary'">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg> 日记
    </button>
    <svg class="mem3-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
    <button class="mem3-tab" :class="{ active: memTab === 'dream' }" @click="memTab = 'dream'">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg> 做梦
    </button>
    <svg class="mem3-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
    <button class="mem3-tab" :class="{ active: memTab === 'longterm' }" @click="memTab = 'longterm'">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg> 长期记忆
    </button>
    <svg class="mem3-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
    <button class="mem3-tab" :class="{ active: memTab === 'graph' }" @click="memTab = 'graph'">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="5" cy="5" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="19" r="2"/><line x1="6.5" y1="6.5" x2="11" y2="11"/><line x1="17.5" y1="6.5" x2="13" y2="11"/><line x1="6.5" y1="17.5" x2="11" y2="13"/><line x1="17.5" y1="17.5" x2="13" y2="13"/></svg> 知识图谱
    </button>
  </div>

  <!-- 日记 Tab -->
  <div class="mem3-panel" :class="{ active: memTab === 'diary' }">
    <div class="mem3-diary-layout">
      <div class="mem3-diary-sidebar">
        <div class="mem3-calendar-card">
          <div class="mem3-cal-header">
            <button class="mem3-cal-nav" @click="calPrev">&#8249;</button>
            <span class="mem3-cal-title">{{ calYear }}年{{ calMonth + 1 }}月</span>
            <button class="mem3-cal-nav" @click="calNext">&#8250;</button>
          </div>
          <div class="mem3-cal-weekdays">
            <span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span><span>日</span>
          </div>
          <div class="mem3-cal-grid">
            <span v-for="(d, i) in calDays" :key="i" class="mem3-cal-day" :class="d.cls" @click="selectDay(d)">{{ d.day }}</span>
          </div>
          <div class="mem3-cal-legend">
            <span class="cal-legend-dot auto"></span> 自动化任务
            <span class="cal-legend-dot manual" style="margin-left:12px;"></span> 当日任务
          </div>
        </div>

        <div class="mem3-entity-section">
          <div class="mem3-entity-section-title">Agent & 项目</div>
          <div class="mem3-entity-list">
            <div v-for="e in diaryEntities" :key="e.id" class="mem3-entity-item" :class="{ active: selectedEntity === e.id }" @click="selectedEntity = e.id">
              <div class="mem3-entity-avatar" :class="e.avatarClass">{{ e.avatar }}</div>
              <div class="mem3-entity-info">
                <div class="mem3-entity-name">{{ e.name }}</div>
                <div class="mem3-entity-sub">{{ e.sub }}</div>
              </div>
              <div v-if="e.badge" class="mem3-entity-badge" :class="e.badgeType">{{ e.badge }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="mem3-diary-main">
        <div class="mem3-diary-date-bar">
          <span class="mem3-diary-date-label">{{ calYear }}年{{ calMonth + 1 }}月{{ calSelected }}日</span>
          <span class="mem3-diary-entity-label">{{ selectedEntityName }}</span>
        </div>
        <div class="mem3-diary-section">
          <div class="mem3-diary-section-title">
            <span class="mem3-section-dot auto"></span> 自动化任务
            <span class="mem3-section-count">{{ autoTasks.length }} 项</span>
          </div>
          <div class="mem3-task-list">
            <div v-for="(t, i) in autoTasks" :key="i" class="mem3-task-item">
              <div class="mem3-task-status" :class="t.status"></div>
              <div class="mem3-task-content">
                <div class="mem3-task-name">{{ t.name }}</div>
                <div class="mem3-task-meta">{{ t.meta }}</div>
              </div>
              <span class="mem3-task-tag auto">自动化</span>
            </div>
          </div>
        </div>
        <div class="mem3-diary-section" style="margin-top:20px;">
          <div class="mem3-diary-section-title">
            <span class="mem3-section-dot manual"></span> 当日任务
            <span class="mem3-section-count">{{ manualTasks.length }} 项</span>
            <button class="mem3-add-task-btn" @click="addDiaryTask" :style="showAddTask ? 'background:var(--brand);color:#fff' : ''">{{ showAddTask ? '确定' : '+ 添加' }}</button>
            <button v-if="showAddTask" class="mem3-add-task-btn" style="background:transparent;color:var(--text-tertiary)" @click="cancelAddTask">取消</button>
          </div>
          <div v-if="showAddTask" style="margin-top:8px">
            <input v-model="newTaskText" type="text" class="form-input" placeholder="输入任务名称" style="width:100%" @keyup.enter="addDiaryTask">
          </div>
          <div class="mem3-task-list">
            <div v-for="(t, i) in manualTasks" :key="i" class="mem3-task-item">
              <div class="mem3-task-status" :class="t.status"></div>
              <div class="mem3-task-content">
                <div class="mem3-task-name">{{ t.name }}</div>
                <div class="mem3-task-meta">{{ t.meta }}</div>
              </div>
              <span class="mem3-task-tag manual">手动</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 做梦 Tab -->
  <div class="mem3-panel" :class="{ active: memTab === 'dream' }">
    <div class="mem3-dream-status-bar">
      <div class="mem3-dream-status-info">
        <div class="mem3-dream-avatar">🌙</div>
        <div>
          <div class="mem3-dream-status-title">正在为你整理记忆中...</div>
          <div class="mem3-dream-status-sub">入梦管理日记，沉淀专家专属记忆</div>
        </div>
      </div>
      <div class="mem3-dream-stats">
        <div class="mem3-dream-stat"><div class="mem3-dream-stat-num">0</div><div class="mem3-dream-stat-label">消耗积分</div></div>
        <div class="mem3-dream-stat"><div class="mem3-dream-stat-num">0</div><div class="mem3-dream-stat-label">总结记忆</div></div>
      </div>
      <button class="page-btn page-btn-secondary" style="font-size:12px;" @click="toggleDream">关闭做梦</button>
    </div>

    <div class="mem3-dream-grid">
      <div v-for="card in dreamCards" :key="card.id" class="mem3-dream-card" @click="openDream(card.id)">
        <div class="mem3-dream-card-header">
          <div class="mem3-dream-card-avatar" :class="card.avatarClass">{{ card.avatar }}</div>
          <div class="mem3-dream-card-info">
            <div class="mem3-dream-card-name">{{ card.name }}</div>
            <div class="mem3-dream-card-sub">{{ card.sub }}</div>
          </div>
        </div>
        <div class="mem3-dream-card-stats">
          <span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px;"><circle cx="12" cy="12" r="10"/></svg> 消耗积分: 0.00</span>
          <span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px;"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/></svg> 新增记忆: 0</span>
        </div>
      </div>
    </div>

    <div class="mem3-dream-drawer" v-if="dreamDrawerOpen">
      <div class="mem3-dream-drawer-header">
        <button class="mem3-dream-drawer-back" @click="closeDream">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg> 返回
        </button>
        <span class="mem3-dream-drawer-title">{{ dreamDrawerTitle }} 的日记</span>
      </div>
      <div class="mem3-dream-diary-list">
        <div v-for="(item, i) in dreamDiary" :key="i" class="mem3-dream-diary-item">
          <div class="mem3-dream-diary-date">{{ item.date }}</div>
          <div class="mem3-dream-diary-content">{{ item.content }}</div>
          <div class="mem3-dream-diary-meta">
            <span>消耗 Token: {{ item.tokens }}</span>
            <span>新增记忆: {{ item.memories }} 条</span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 长期记忆 Tab -->
  <div class="mem3-panel" :class="{ active: memTab === 'longterm' }">
    <div class="mem3-lt-layout">
      <div class="mem3-lt-sidebar">
        <div class="mem3-lt-sidebar-title">专家分类</div>
        <div class="mem3-lt-entity-list">
          <div v-for="e in ltEntities" :key="e.id" class="mem3-lt-entity-item" :class="{ active: selectedLtEntity === e.id }" @click="selectLtEntity(e.id)">
            <div class="mem3-lt-entity-avatar" :class="e.avatarClass">{{ e.avatar }}</div>
            <span>{{ e.name }}</span>
          </div>
        </div>
      </div>
      <div class="mem3-lt-editor">
        <div class="mem3-lt-editor-header">
          <span class="mem3-lt-editor-title">长期记忆 · {{ selectedLtEntityName }}</span>
          <div class="mem3-lt-editor-actions">
            <button v-if="!ltEditing" class="mem3-lt-btn secondary" @click="ltEdit">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> 编辑
            </button>
          </div>
        </div>
        <div class="mem3-lt-content-wrap">
          <div class="mem3-lt-preview" v-if="!ltEditing">
            <div class="mem3-lt-date-line">{{ ltInitDate }}</div>
            <div class="mem3-lt-entry" v-html="ltContent"></div>
          </div>
          <textarea v-else class="mem3-lt-textarea" v-model="ltEditText" placeholder="用自然语言描述这个 Agent/项目的长期记忆规则、偏好和背景知识..."></textarea>
        </div>
        <div v-if="ltEditing" class="mem3-lt-editor-footer">
          <button class="mem3-lt-btn secondary" @click="ltCancel">取消</button>
          <button class="mem3-lt-btn primary" @click="ltSave">保存</button>
        </div>
      </div>
    </div>
  </div>

  <!-- 知识图谱 Tab -->
  <div class="mem3-panel mem3-graph-panel" :class="{ active: memTab === 'graph' }">
    <div class="mem3-graph-layout">
      <div class="mem3-graph-canvas">
        <svg class="mem3-graph-svg" viewBox="0 0 600 420">
          <defs>
            <radialGradient id="g-grad-center" cx="50%" cy="50%">
              <stop offset="0%" stop-color="#4DA8F0"/>
              <stop offset="100%" stop-color="#3B8ED0"/>
            </radialGradient>
          </defs>
          <g class="graph-edges">
            <line x1="300" y1="210" x2="110" y2="100" stroke="rgba(77,168,240,0.2)" stroke-width="1.5" opacity="0.6"/>
            <line x1="300" y1="210" x2="480" y2="85" stroke="rgba(77,168,240,0.2)" stroke-width="1.5" opacity="0.5"/>
            <line x1="300" y1="210" x2="140" y2="320" stroke="rgba(77,168,240,0.2)" stroke-width="1.5" opacity="0.5"/>
            <line x1="300" y1="210" x2="460" y2="330" stroke="rgba(77,168,240,0.2)" stroke-width="1.5" opacity="0.5"/>
            <line x1="110" y1="100" x2="480" y2="85" stroke="rgba(77,168,240,0.14)" stroke-width="1" opacity="0.35"/>
            <line x1="140" y1="320" x2="460" y2="330" stroke="rgba(77,168,240,0.14)" stroke-width="1" opacity="0.35"/>
            <line x1="110" y1="100" x2="140" y2="320" stroke="rgba(77,168,240,0.12)" stroke-width="1" opacity="0.3"/>
            <line x1="480" y1="85" x2="460" y2="330" stroke="rgba(77,168,240,0.12)" stroke-width="1" opacity="0.3"/>
          </g>
          <g class="graph-nodes">
            <circle cx="300" cy="210" r="28" fill="url(#g-grad-center)" stroke="var(--brand)" stroke-width="2"/>
            <text x="300" y="214" text-anchor="middle" fill="#fff" font-size="13" font-weight="700" font-family="inherit">H</text>
            <g v-for="(node, ni) in graphNodes" :key="ni">
              <circle :cx="node.x" :cy="node.y" :r="node.r" fill="var(--bg-surface)" stroke="var(--border-default)" stroke-width="1.5"/>
              <text :x="node.x" :y="node.y + 4" text-anchor="middle" fill="var(--text-secondary)" font-size="10" font-weight="600" font-family="inherit">{{ node.label }}</text>
            </g>
          </g>
        </svg>
      </div>
      <div class="mem3-graph-sidebar">
        <div class="mem3-graph-card">
          <div class="mem3-graph-card-title">记忆网络拓扑</div>
          <div class="mem3-graph-card-desc">Hermes 记忆中枢连接各 Agent，形成分布式认知图谱</div>
        </div>
        <div class="mem3-graph-stats">
          <div class="mem3-graph-stat">
            <span class="mem3-graph-stat-num">5</span>
            <span class="mem3-graph-stat-label">Agent 节点</span>
          </div>
          <div class="mem3-graph-stat">
            <span class="mem3-graph-stat-num">8</span>
            <span class="mem3-graph-stat-label">记忆连接</span>
          </div>
          <div class="mem3-graph-stat">
            <span class="mem3-graph-stat-num">1.2K</span>
            <span class="mem3-graph-stat-label">知识条目</span>
          </div>
        </div>
        <div class="mem3-graph-section-label">
          <span>知识源</span>
          <button class="mem3-graph-add-btn" @click="addKbSource" title="添加知识源">{{ showAddKbSource ? '确定' : '+' }}</button>
        </div>
        <div v-if="showAddKbSource" style="margin-bottom:var(--space-3)">
          <div class="form-group" style="margin-bottom:8px"><input v-model="newKbName" type="text" class="form-input" placeholder="知识源名称" style="font-size:12px"></div>
          <div class="form-group" style="margin-bottom:0"><input v-model="newKbMeta" type="text" class="form-input" placeholder="描述" style="font-size:12px"></div>
        </div>
        <div class="mem3-kb-source-list">
          <div v-for="src in kbSources" :key="src.id" class="mem3-kb-source-card" @click="openKbSource(src)">
            <div class="mem3-kb-source-icon" :class="src.iconClass" v-html="src.icon"></div>
            <div class="mem3-kb-source-info">
              <div class="mem3-kb-source-name">{{ src.name }}</div>
              <div class="mem3-kb-source-meta">{{ src.meta }}</div>
            </div>
            <span class="mem3-kb-source-status" :class="src.status" :title="src.statusTitle"></span>
          </div>
        </div>
        <div class="mem3-pipeline-card">
          <div class="mem3-pipeline-title">记忆沉淀 → 同步知识源</div>
          <div class="mem3-pipeline-flow">
            <span class="mem3-pipeline-step diary">日记</span>
            <span class="mem3-pipeline-arrow">→</span>
            <span class="mem3-pipeline-step dream">做梦</span>
            <span class="mem3-pipeline-arrow">→</span>
            <span class="mem3-pipeline-step ltmem">长期记忆</span>
            <span class="mem3-pipeline-arrow">→</span>
            <span class="mem3-pipeline-step graph">知识图谱</span>
            <span class="mem3-pipeline-arrow">→</span>
            <span class="mem3-pipeline-step sync">知识源</span>
          </div>
        </div>
        <div class="mem3-graph-legend">
          <div class="mem3-graph-legend-item"><span class="g-leg-dot center"></span> 中枢节点 Hermes</div>
          <div class="mem3-graph-legend-item"><span class="g-leg-dot agent"></span> Agent / 项目节点</div>
          <div class="mem3-graph-legend-item"><span class="g-leg-dot edge"></span> 记忆关联路径</div>
        </div>
      </div>
    </div>
  </div>
</div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from '@/composables/useToast'
const { showToast } = useToast()

const memTab = ref('diary')

// Calendar
const calYear = ref(2026)
const calMonth = ref(6) // July (0-indexed: 6)
const calSelected = ref(14)
const weekdays = ['一','二','三','四','五','六','日']
function calPrev() { calMonth.value--; if (calMonth.value < 0) { calMonth.value = 11; calYear.value-- } }
function calNext() { calMonth.value++; if (calMonth.value > 11) { calMonth.value = 0; calYear.value++ } }
function selectDay(d: { day: number; cls: string }) { if (!d.cls.includes('dim')) calSelected.value = d.day }

const calDays = computed(() => {
  const firstDay = new Date(calYear.value, calMonth.value, 1).getDay()
  const daysInMonth = new Date(calYear.value, calMonth.value + 1, 0).getDate()
  const prevDays = new Date(calYear.value, calMonth.value, 0).getDate()
  const days: { day: number; cls: string }[] = []
  const sunFirst = firstDay === 0 ? 6 : firstDay - 1 // mon-first
  for (let i = sunFirst - 1; i >= 0; i--) days.push({ day: prevDays - i, cls: 'dim' })
  for (let d = 1; d <= daysInMonth; d++) {
    let cls = ''
    if (d === calSelected.value) cls += ' active'
    days.push({ day: d, cls })
  }
  const remaining = 7 - (days.length % 7 || 7)
  if (remaining < 7) for (let d = 1; d <= remaining; d++) days.push({ day: d, cls: 'dim' })
  return days
})

// Diary - entities
const selectedEntity = ref('hermes')
const diaryEntities = [
  { id: 'hermes', name: 'Hermes', sub: '平台大管家', avatar: 'H', avatarClass: 'hermes', badge: '3', badgeType: 'auto' },
  { id: 'qclaw', name: 'QClaw', sub: '网文创作助手', avatar: 'Q', avatarClass: 'qclaw', badge: '1', badgeType: 'manual' },
  { id: 'niuma', name: '超级牛马工作台', sub: '项目', avatar: '牛', avatarClass: 'niuma', badge: '5', badgeType: 'auto' },
  { id: 'video', name: 'Video Agent', sub: '视频创作', avatar: 'V', avatarClass: 'video', badge: null, badgeType: '' },
  { id: 'taichu', name: '太初 CMS', sub: '项目', avatar: '太', avatarClass: 'taichu', badge: '2', badgeType: 'manual' },
]
const selectedEntityName = computed(() => diaryEntities.find(e => e.id === selectedEntity.value)?.name || '')

// Diary - tasks
const autoTasks = [
  { name: '每日前沿研究报告', meta: '09:00 · 已完成 · 输出至 daily-research/2026-06-18.md', status: 'done' },
  { name: '记忆压缩与整理', meta: '06:00 · 已完成 · 压缩率 57.3%', status: 'done' },
  { name: '用户画像模型更新', meta: '22:00 · 待执行', status: 'pending' },
]
const manualTasks = [
  { name: '完成记忆页面重设计', meta: '已完成 · 刘老爷指定任务', status: 'done' },
  { name: '前端原型整体 UI 精致化', meta: '进行中 · 预计今日完成', status: 'in-progress' },
]
const showAddTask = ref(false)
const newTaskText = ref('')
function addDiaryTask() {
  if (showAddTask.value) {
    if (newTaskText.value.trim()) {
      autoTasks.push({ name: newTaskText.value.trim(), status: 'pending' })
      showToast('任务已添加', 'success')
    }
    newTaskText.value = ''
    showAddTask.value = false
  } else {
    showAddTask.value = true
  }
}
function cancelAddTask() { showAddTask.value = false; newTaskText.value = '' }

// Dream
const dreamDrawerOpen = ref(false)
const dreamDrawerTitle = ref('')
const dreamCards = [
  { id: 'hermes', name: 'Hermes', sub: '由你定义的全新Agent', avatar: 'H', avatarClass: 'hermes' },
  { id: 'qclaw', name: 'QClaw', sub: '你的AI网文助手', avatar: 'Q', avatarClass: 'qclaw' },
  { id: 'niuma', name: '超级牛马工作台', sub: '6大平台原生风格创作', avatar: '牛', avatarClass: 'niuma' },
  { id: 'video', name: 'Video Agent', sub: '视频创作 · 三阶段管道', avatar: 'V', avatarClass: 'video' },
  { id: 'taichu', name: '太初 CMS', sub: 'AI Agent 原生 CMS', avatar: '太', avatarClass: 'taichu' },
]
const dreamDiary = [
  { date: '2026-06-18', content: '今天完成了记忆页面的重新设计，参考了 Qclaw 的三段式日记逻辑，实现了日记/做梦/长期记忆三个模块。新增了日历组件和任务列表，整体 UI 与 Neon Pulse 设计系统保持一致。', tokens: '12,480', memories: 3 },
  { date: '2026-06-17', content: '完成了品牌色从绿色迁移到牛马蓝（#4DA8F0）的全量替换，并修复了页面内容下移900px问题。', tokens: '8,230', memories: 2 },
]
function toggleDream() {
  dreamOpen.value = !dreamOpen.value
  showToast(dreamOpen.value ? '做梦模式已开启' : '做梦模式已关闭', 'success')
}
function openDream(id: string) { dreamDrawerOpen.value = true; dreamDrawerTitle.value = dreamCards.find(c => c.id === id)?.name || '' }
function closeDream() { dreamDrawerOpen.value = false }

// Long-term memory
const selectedLtEntity = ref('hermes')
const ltEditing = ref(false)
const ltEditText = ref('')
interface LtMemory { id: string; name: string; avatar: string; avatarClass: string; initDate: string; content: string }
const ltEntities = [
  { id: 'hermes', name: 'Hermes', avatar: 'H', avatarClass: 'hermes' },
  { id: 'qclaw', name: 'QClaw', avatar: 'Q', avatarClass: 'qclaw' },
  { id: 'niuma', name: '超级牛马', avatar: '牛', avatarClass: 'niuma' },
  { id: 'video', name: 'Video Agent', avatar: 'V', avatarClass: 'video' },
  { id: 'taichu', name: '太初 CMS', avatar: '太', avatarClass: 'taichu' },
]
const ltMemories: Record<string, LtMemory> = {
  hermes: { id: 'hermes', name: 'Hermes', avatar: 'H', avatarClass: 'hermes', initDate: '2026-05-25：记忆系统启用', content: '<p>Hermes 是超级牛马工作台的平台大管家，采用被动式全平台管理策略。</p><ul><li><strong>用户身份</strong>：刘老爷，起点LV5作者</li><li><strong>沟通风格</strong>：中文为主，简短直接</li><li><strong>前端技术栈</strong>：Vue3 + Vite + TypeScript</li></ul>' },
  qclaw: { id: 'qclaw', name: 'QClaw', avatar: 'Q', avatarClass: 'qclaw', initDate: '2026-05-20：记忆系统启用', content: '<p>QClaw 是 AI 网文创作助手，专注于小说创作辅助。</p>' },
  niuma: { id: 'niuma', name: '超级牛马', avatar: '牛', avatarClass: 'niuma', initDate: '2026-05-15：记忆系统启用', content: '<p>超级牛马工作台 v1.5，AI 驱动的个人工作站。</p>' },
  video: { id: 'video', name: 'Video Agent', avatar: 'V', avatarClass: 'video', initDate: '2026-05-10：记忆系统启用', content: '<p>Video Agent 视频创作助手，三阶段管道。</p>' },
  taichu: { id: 'taichu', name: '太初 CMS', avatar: '太', avatarClass: 'taichu', initDate: '2026-05-08：记忆系统启用', content: '<p>太初 CMS，AI Agent 原生内容管理系统。</p>' },
}
const selectedLtEntityName = computed(() => ltMemories[selectedLtEntity.value]?.name || '')
const ltInitDate = computed(() => ltMemories[selectedLtEntity.value]?.initDate || '')
const ltContent = computed(() => ltMemories[selectedLtEntity.value]?.content || '')
function selectLtEntity(id: string) { selectedLtEntity.value = id; ltEditing.value = false }
function ltEdit() { ltEditing.value = true; ltEditText.value = ltInitDate.value + '\n\n' + ltMemories[selectedLtEntity.value]?.content.replace(/<[^>]*>/g, '') || '' }
function ltCancel() { ltEditing.value = false }
function ltSave() { ltEditing.value = false; showToast('长期记忆已保存', 'success') }

// Knowledge graph
function openKbSource(src: any) {
  memTab.value = 'graph'
  showToast(src.name + ': ' + src.meta, 'info')
}

const graphNodes = [
  { id: 'kb', label: 'KB', x: 110, y: 100, r: 20 },
  { id: 'qc', label: 'QC', x: 480, y: 85, r: 20 },
  { id: 'nm', label: '牛', x: 140, y: 320, r: 22 },
  { id: 'vi', label: 'VI', x: 460, y: 330, r: 20 },
  { id: 'tc', label: '太', x: 300, y: 355, r: 18 },
]
const showAddKbSource = ref(false)
const newKbName = ref('')
const newKbMeta = ref('')
function addKbSource() {
  if (showAddKbSource.value) {
    if (newKbName.value.trim()) {
      kbSources.value.push({
        id: 'kb-' + Date.now(), name: newKbName.value.trim(), meta: newKbMeta.value || '新知识源',
        iconClass: 'local', 
        icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>',
        action: '查看: ' + newKbName.value.trim(), status: 'available', statusTitle: '可用'
      })
      showToast('已添加知识源: ' + newKbName.value.trim(), 'success')
    }
    newKbName.value = ''; newKbMeta.value = ''; showAddKbSource.value = false
  } else {
    showAddKbSource.value = true
  }
}
const kbSources = ref([
  { id: 'local', name: '本地知识库', meta: '文件索引 · 向量检索 · 2.4K 文档', iconClass: 'local', icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>', action: '本地知识库 — 管理本地文件索引', status: 'connected', statusTitle: '已连接' },
  { id: 'feishu', name: '飞书知识库', meta: '文档同步 · 多维表格 · 1.8K 条目', iconClass: 'feishu', icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>', action: '飞书知识库 — 同步中', status: 'connected', statusTitle: '已连接' },
  { id: 'notion', name: 'Notion', meta: '数据库读写 · 页面管理 · 856 条目', iconClass: 'notion', icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>', action: 'Notion 集成 — 已授权', status: 'connected', statusTitle: '已连接' },
  { id: 'obsidian', name: 'Obsidian', meta: 'Markdown Vault · 双向链接 · 待配置', iconClass: 'obsidian', icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 12l3 3 7-7 7 7 3-3L12 2z"/><path d="M5 15l7 7 7-7"/></svg>', action: 'Obsidian Vault — 配置本地路径', status: 'available', statusTitle: '可用' },
])
</script>
