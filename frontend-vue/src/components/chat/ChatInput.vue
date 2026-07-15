<template>
  <div class="input-area" id="inputArea">
    <!-- Hidden file inputs -->
    <input ref="fileInputRef" type="file" hidden @change="onFileSelected" />
    <input ref="folderInputRef" type="file" webkitdirectory hidden @change="onFolderSelected" />

    <!-- Processing Card -->
    <div class="processing-card" id="processingCard" :class="{ active: processingActive }">
      <div class="work-status-bar">
        <div class="work-status-icon"></div>
        <span class="work-status-label">{{ processingLabel }}</span>
        <span class="work-status-timer">{{ processingTimer }}</span>
      </div>
    </div>

    <!-- Suggestion Strip -->
    <div class="suggestion-strip" v-show="showSuggestions">
      <div class="suggestion-strip-label">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
        Agent 建议下一步
      </div>
      <div class="suggestion-chips">
        <button v-for="(s, idx) in suggestions" :key="idx" class="suggestion-chip" @click="$emit('apply-suggestion', s)">{{ s }}</button>
      </div>
    </div>

    <!-- Queue Panel (above input card, shown when tasks exist) -->
    <div class="queue-area" id="queueArea" v-if="queueTasks.length > 0">
      <div class="queue-header" @click="queueExpanded = !queueExpanded">
        <svg class="queue-header-arrow" :class="{ expanded: queueExpanded }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
        <span class="queue-header-count"><span>{{ queueTasks.length }}</span> 个队列任务</span>
      </div>
      <div class="queue-task-list" :class="{ open: queueExpanded }">
        <div v-for="(task, ti) in queueTasks" :key="ti" class="queue-task-item">
          <span class="queue-task-text">{{ task }}</span>
          <div class="queue-task-actions">
            <button class="queue-task-btn" title="上移" @click="moveQueueTask(ti, -1)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="18 15 12 9 6 15"/></svg></button>
            <button class="queue-task-btn close-btn" title="移除" @click="removeQueueTask(ti)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
          </div>
        </div>
      </div>
    </div>

    <!-- Input Card -->
    <div class="input-card" id="inputCard" @click="closeMenus">
      <textarea
        ref="textareaRef"
        v-model="draftText"
        class="input-textarea"
        placeholder="描述任务，/ 快捷调用，@ 添加上下文"
        rows="1"
        aria-label="输入消息"
        maxlength="10000"
        @keydown.enter.exact.prevent="handleSend"
      ></textarea>
      <div class="input-toolbar">
        <!-- [+] Add Menu -->
        <div style="position:relative;">
          <button class="toolbar-plus-btn" title="添加上下文" aria-label="添加上下文" @click.stop="toggleMenu('plus')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
          <div class="plus-menu" role="menu" aria-label="添加上下文菜单" :class="{ open: openMenu === 'plus' }" style="position:absolute;bottom:calc(100% + 6px);left:0;">
            <button class="plus-menu-item" @click="toggleSkillPanel"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>添加技能<span class="menu-arrow">→</span></button>
            <button class="plus-menu-item" @click="handleAddFile"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>添加文件</button>
            <button class="plus-menu-item" @click="handleAddFolder"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>添加文件夹</button>
          </div>
        </div>

        <div class="toolbar-spacer"></div>
        <!-- Context progress icon -->
        <button class="toolbar-context-btn" :title="'上下文占比 ' + contextPct + '%'" aria-label="上下文使用占比" @click="$emit('toast', '上下文占比 ' + contextPct + '%', 'info')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" style="transform:rotate(-90deg)">
            <circle cx="12" cy="12" r="9" opacity="0.15"/>
            <circle cx="12" cy="12" r="9" :stroke-dasharray="56.52" :stroke-dashoffset="56.52 - (contextPct/100) * 56.52"/>
          </svg>
        </button>
        <!-- Model Pill -->
        <div style="position:relative;">
          <button class="model-pill" aria-label="选择AI模型" @click.stop="toggleMenu('model')">
            <span class="model-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg></span>
            <span class="model-name">{{ selectedModel }}</span>
            <span class="model-chevron"></span>
          </button>
          <div class="model-dropdown" role="listbox" aria-label="选择模型" :class="{ open: openMenu === 'model' }">
            <button v-for="m in models" :key="m.id" class="model-dropdown-item" :class="{ active: selectedModel === m.id }" @click="selectModelLocal(m.id)"><span class="model-item-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2"/></svg></span>{{ m.name }}<span v-if="m.tag" class="model-tag">{{ m.tag }}</span></button>
          </div>
        </div>
        <!-- Send / Stop -->
        <button
          :class="processingActive ? 'stop-btn' : ['send-btn', { 'has-content': draftText.trim() }]"
          :title="processingActive ? '停止' : '发送'"
          :aria-label="processingActive ? '停止任务' : '发送消息'"
          @click="handleSendOrStop"
        >
          <svg v-if="!processingActive" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>
          <svg v-else viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
        </button>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'

const props = defineProps<{
  selectedModel: string
  processingActive: boolean
  processingLabel: string
  processingTimer: string
  showSuggestions: boolean
  suggestions: string[]
  contextPct: number
}>()

const emit = defineEmits<{
  send: [text: string]
  stop: []
  'apply-suggestion': [text: string]
  'add-skill': []
  'add-file': [file: File]
  'add-folder': [files: File[]]
  toast: [msg: string, type?: string]
  navigate: [page: string]
  'select-model': [modelId: string]
}>()

const models = [
  { id: 'Auto', name: 'Auto', tag: '推荐' },
  { id: 'Qwen3.7-Max', name: 'Qwen3.7-Max', tag: '' },
  { id: 'Qwen3.7-Plus', name: 'Qwen3.7-Plus', tag: '' },
  { id: 'DeepSeek-V4-Pro', name: 'DeepSeek-V4-Pro', tag: '' },
  { id: 'Kimi-K2.6', name: 'Kimi-K2.6', tag: '' },
]

const draftText = ref('')
const openMenu = ref<string | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const folderInputRef = ref<HTMLInputElement | null>(null)
const queueTasks = ref<string[]>(['自然景 亚藤给到的感觉的 美图要多一点'])
const queueExpanded = ref(false)

function moveQueueTask(idx: number, dir: number) { const to = idx + dir; if (to < 0 || to >= queueTasks.value.length) return; const t = queueTasks.value; [t[idx], t[to]] = [t[to], t[idx]] }
function removeQueueTask(idx: number) { queueTasks.value.splice(idx, 1) }

function toggleMenu(name: string) { openMenu.value = openMenu.value === name ? null : name }
function closeMenus() { openMenu.value = null }
function selectModelLocal(id: string) { emit('select-model', id); openMenu.value = null }

function handleSend() {
  if (!draftText.value.trim()) return
  emit('send', draftText.value)
  draftText.value = ''
  nextTick(() => textareaRef.value?.focus())
}

function handleSendOrStop() {
  if (props.processingActive) {
    emit('stop')
  } else {
    handleSend()
  }
}

function handleAddFile() {
  fileInputRef.value?.click()
  openMenu.value = null
}

function handleAddFolder() {
  folderInputRef.value?.click()
  openMenu.value = null
}

function toggleSkillPanel() {
  emit('add-skill')
  openMenu.value = null
}

function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    emit('add-file', input.files[0])
    emit('toast', '已添加文件: ' + input.files[0].name)
  }
  input.value = '' // allow re-selecting same file
}

function onFolderSelected(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    emit('add-folder', Array.from(input.files))
    emit('toast', '已添加文件夹: ' + input.files.length + ' 个文件')
  }
  input.value = ''
}

function insertMention(text: string) {
  draftText.value += text
  nextTick(() => textareaRef.value?.focus())
}
</script>