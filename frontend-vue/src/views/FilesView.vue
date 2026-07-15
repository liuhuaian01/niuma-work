<template>
<div class="page-view active" id="pageFiles">
  <div class="files-page-header">
    <div class="files-page-header-left">
      <h1>文件</h1>
      <p class="files-page-header-sub">工作台文件管理 · 按 Agent 与项目组织 · 检索即所得</p>
    </div>
    <div class="files-page-header-right">
      <div class="files-search-row">
        <div class="files-search" id="filesSearchBox">
          <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
          <input type="text" placeholder="搜索文件…" id="filesSearchInput" v-model="searchQuery" @input="searchFiles">
          <button class="files-search-clear" id="filesSearchClear" title="清除" :class="{ visible: searchQuery }" @click="clearSearch">×</button>
          <span class="files-search-kbd">⌘K</span>
        </div>
        <button class="files-refresh-btn" title="刷新" @click="refreshFiles">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
        </button>
      </div>
      <div class="files-view-seg" id="filesViewSeg">
        <button class="files-view-seg-btn" :class="{ active: activeView === 'workbench' }" @click="switchView('workbench')">工作台</button>
        <button class="files-view-seg-btn" :class="{ active: activeView === 'local' }" @click="switchView('local')">本地</button>
      </div>
    </div>
  </div>

  <!-- Workbench Panel -->
  <div class="files-panel active" id="filePanelWorkbench" v-show="activeView === 'workbench'">
    <div class="files-layout">
      <!-- 左侧：Agent 树 -->
      <div class="files-tree" id="filesTree">
        <div v-for="group in fileGroups" :key="group.id" class="files-tree-group">
          <div class="files-tree-header" :class="{ collapsed: !expandedFolders[group.id] }" @click="toggleAndLoad(group.id)">
            <svg class="files-tree-arrow" :class="{ expanded: expandedFolders[group.id] }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" @click.stop="toggleFolder(group.id)"><polyline points="6 9 12 15 18 9"/></svg>
            <div class="files-tree-icon" :style="group.iconStyle">{{ group.initial }}</div>
            <span class="files-tree-name">{{ group.name }}</span>
            <span class="files-tree-count">{{ group.count }}</span>
          </div>
          <div class="files-tree-children" :class="{ open: expandedFolders[group.id] }" @click="loadFileGroup(group.id)">
            <div v-for="child in group.children" :key="child" class="files-tree-child" @click="showToast('打开: ' + child, 'info')">
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M10 2H4a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4z"/><polyline points="10 2 10 6 14 6"/></svg> {{ child }}
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：文件列表 -->
      <div class="files-main" id="filesMain">
        <div class="files-table-hdr">
          <span>文件名</span>
          <span>大小</span>
          <span>修改时间</span>
        </div>
        <div class="files-empty" v-if="currentFiles.length === 0" style="grid-column:1/-1;padding:40px;text-align:center;color:var(--text-tertiary)">
          选择左侧工作组查看文件
        </div>
        <div v-for="f in filteredFiles" :key="f.name" class="files-row">
          <div class="files-row-name">
            <div class="files-row-icon" :class="fileIconType(f.name)" v-html="fileIconSvg(f.name)"></div>
            <span class="files-row-name-text">{{ f.name }}</span>
          </div>
          <span class="files-row-meta">{{ f.size }}</span>
          <span class="files-row-time">{{ f.time }}</span>
        </div>
      </div>
    </div>
  </div>

  <!-- Local Panel -->
  <div class="files-panel" id="filePanelLocal" v-show="activeView === 'local'">
    <div class="files-empty">
      <div class="files-empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="20" height="18" rx="2"/><path d="M8 21V3"/></svg>
      </div>
      <h3>本地文件</h3>
      <p>选择本地文件夹后，文件将按目录结构在此展示。支持逐级展开、搜索和预览。</p>
      <button class="files-go-chat-btn" @click="selectLocalFolder">选择文件夹</button>
    </div>
  </div>
</div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useToast } from '@/composables/useToast'
const { showToast } = useToast()
const searchQuery = ref('')
const activeView = ref('workbench')
const expandedFolders = reactive<Record<string, boolean>>({ hermes: true, qclaw: true })
const currentGroup = ref('hermes')

const fileGroups = [
  {
    id: 'hermes', name: 'Hermes', initial: 'H', count: 15,
    iconStyle: 'background:linear-gradient(135deg,#4DA8F0,#6BBFFC)',
    children: ['config.yaml', 'hermes_core.py', 'tasks_2026-06.csv']
  },
  {
    id: 'qclaw', name: 'QClaw', initial: 'Q', count: 8,
    iconStyle: 'background:linear-gradient(135deg,#8B5CF6,#A78BFA)',
    children: ['创意工坊_设定.md', '人物数据库.json']
  },
  {
    id: 'niuma', name: '超级牛马', initial: '牛', count: 12,
    iconStyle: 'background:linear-gradient(135deg,#34D399,#10B981)',
    children: ['太极引擎_11铁则.md', 'DS_v5.7_组件规范.pdf', '前端工程化重构.md']
  },
  {
    id: 'video', name: 'Video Agent', initial: 'V', count: 6,
    iconStyle: 'background:linear-gradient(135deg,#06B6D4,#0891B2)',
    children: ['转码pipeline.py', '剪辑脚本_template.json']
  },
  {
    id: 'taichu', name: '太初 CMS', initial: '太', count: 4,
    iconStyle: 'background:linear-gradient(135deg,#8895AB,#5B6A80)',
    children: ['CMS发布工作流.md']
  },
]

interface FileItem { name: string; size: string; time: string }

const fileData: Record<string, FileItem[]> = {
  hermes: [
    { name: 'MEMORY.md', size: '3.2 KB', time: '6/27 10:30' },
    { name: '2026-06-27.md', size: '8.4 KB', time: '6/27 13:05' },
    { name: '2026-06-26.md', size: '6.8 KB', time: '6/26 16:08' },
    { name: 'skills/', size: '—', time: '—' },
    { name: 'IDENTITY.md', size: '2.1 KB', time: '6/25 14:20' },
    { name: 'SOUL.md', size: '4.5 KB', time: '6/25 12:00' },
  ],
  qclaw: [
    { name: 'chapter-draft-v3.md', size: '15.2 KB', time: '6/26 22:00' },
    { name: 'outline.md', size: '3.1 KB', time: '6/25 18:00' },
    { name: 'characters/', size: '—', time: '—' },
  ],
  niuma: [
    { name: 'design-tokens.css', size: '19.6 KB', time: '6/27 11:00' },
    { name: 'components.css', size: '136 KB', time: '6/27 09:30' },
    { name: 'prototype.html', size: '—', time: '6/27 13:00' },
  ],
  video: [
    { name: 'script-v2.md', size: '5.8 KB', time: '6/24 16:00' },
    { name: 'assets/', size: '—', time: '—' },
  ],
  taichu: [
    { name: 'config.yml', size: '1.2 KB', time: '6/23 10:00' },
    { name: 'docker-compose.yml', size: '2.3 KB', time: '6/22 15:00' },
  ],
}

const currentFiles = ref<FileItem[]>(fileData['hermes'])

const filteredFiles = computed(() => {
  const q = searchQuery.value.toLowerCase()
  if (!q) return currentFiles.value
  return currentFiles.value.filter(f => f.name.toLowerCase().includes(q))
})

function loadFileGroup(group: string) {
  currentGroup.value = group
  currentFiles.value = fileData[group] || []
}

function switchView(view: string) { activeView.value = view }

function toggleFolder(name: string) {
  expandedFolders[name] = !expandedFolders[name]
}

function toggleAndLoad(group: string) {
  toggleFolder(group)
  loadFileGroup(group)
}

function searchFiles() {
  // Reactively handled by filteredFiles computed
}

function clearSearch() { 
  searchQuery.value = ''
  const input = document.getElementById('filesSearchInput')
  if (input) input.focus()
}

function refreshFiles() {
  loadFileGroup('hermes')
  showToast('文件列表已刷新', 'success')
}

function selectLocalFolder() {
  switchView('local')
  showToast('请选择本地文件夹', 'info')
}

function fileIconType(name: string) {
  if (name.endsWith('/')) return 'folder'
  const ext = name.split('.').pop()?.toLowerCase() || ''
  const m: Record<string, string> = { js:'code', ts:'code', py:'code', css:'css', html:'html', yml:'yml', yaml:'yml', json:'code', png:'img', jpg:'img', svg:'img', gif:'img', webp:'img', md:'md', txt:'md', csv:'md', pdf:'md' }
  return m[ext] || 'md'
}

function fileIconSvg(name: string) {
  const type = fileIconType(name)
  const icons: Record<string, string> = {
    folder: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>',
    md: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
    code: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
    img: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
    css: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 3h16l-1.5 17L12 22 5.5 20z"/></svg>',
    yml: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="20" rx="3"/><line x1="7" y1="8" x2="17" y2="8"/><line x1="7" y1="12" x2="14" y2="12"/><line x1="7" y1="16" x2="10" y2="16"/></svg>',
    html: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 3h16l-1.5 17L12 22 5.5 20z"/></svg>'
  }
  return icons[type] || icons.md
}
</script>
