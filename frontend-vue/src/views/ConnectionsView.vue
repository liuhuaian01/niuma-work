<template>
<div class="page-view active" id="pageConnections">
  <div class="page-header">
    <div><h1>连接</h1><p class="page-subtitle">MCP 服务 · API 集成 · 外部工具</p></div>
    <div class="page-header-actions">
      <button class="page-btn page-btn-primary" @click="openAddModal">+ 添加连接</button>
    </div>
  </div>
  <div class="page-body">
    <div class="conn-hero">
      <div class="conn-hero-info">
        <h2>集成枢纽</h2>
        <p>连接外部世界，MCP 服务与 API 在此汇聚，脉冲即是心跳</p>
      </div>
      <div class="conn-hero-stats">
        <div class="conn-hero-stat"><div class="conn-hero-stat-value">{{ connectedCount }}</div><div class="conn-hero-stat-label">已连接</div></div>
        <div class="conn-hero-stat"><div class="conn-hero-stat-value">{{ connectors.length }}</div><div class="conn-hero-stat-label">总计</div></div>
        <div class="conn-hero-stat"><div class="conn-hero-stat-value">{{ pendingCount }}</div><div class="conn-hero-stat-label">待配置</div></div>
      </div>
    </div>
    <div class="conn-status-bar">
      <div class="conn-status-item"><span class="conn-status-dot on"></span>已连接 <strong>{{ connectedCount }}</strong>/{{ connectors.length }}</div>
      <div class="conn-status-item"><span class="conn-status-dot sync"></span>最近同步 <strong>3 分钟前</strong></div>
      <div class="conn-status-item"><span class="conn-status-dot off"></span>{{ pendingCount }} 个待配置</div>
    </div>
    <div class="conn-grid">
      <div v-for="conn in connectors" :key="conn.id" class="entity-card">
        <div class="entity-card-header">
          <div class="entity-card-icon" :class="conn.iconClass" v-html="conn.icon"></div>
          <div class="entity-card-info">
            <div class="entity-card-name">{{ conn.name }}</div>
            <div class="entity-card-meta">{{ conn.meta }}</div>
          </div>
          <label class="entity-card-toggle">
            <input type="checkbox" v-model="conn.connected">
            <span class="toggle-track"></span>
          </label>
        </div>
        <div class="entity-card-footer-conn">
          <span class="entity-tag" :class="{ active: conn.connected }">{{ conn.connected ? '已连接' : '未连接' }}</span>
          <span class="conn-version">{{ conn.version }}</span>
          <button class="conn-action-btn" :class="{ primary: conn.connected }" @click.stop="openConfig(conn)">配置</button>
        </div>
      </div>
    </div>

    <!-- Add Connection Modal -->
    <div class="modal-overlay" v-if="showAddModal" @click.self="closeAddModal">
      <div class="modal" style="max-width:480px">
        <div class="modal-hd"><h3>添加连接</h3><button class="modal-close" @click="closeAddModal">×</button></div>
        <div class="modal-body">
          <div class="form-group"><label>连接名称</label><input v-model="addForm.name" type="text" placeholder="如：飞书 MCP" class="form-input"></div>
          <div class="form-group"><label>连接类型</label>
            <select v-model="addForm.type" class="form-input"><option>MCP 服务</option><option>API 集成</option><option>数据库</option></select>
          </div>
          <div class="form-group"><label>描述</label><input v-model="addForm.meta" type="text" placeholder="简要描述" class="form-input"></div>
        </div>
        <div class="modal-ft">
          <button class="modal-btn-cancel" @click="closeAddModal">取消</button>
          <button class="modal-btn-confirm" @click="doAddConnection">添加</button>
        </div>
      </div>
    </div>

    <!-- Config Modal -->
    <div class="modal-overlay" v-if="showConfigModal" @click.self="closeConfig">
      <div class="modal" style="max-width:480px">
        <div class="modal-hd"><h3>配置 {{ configTarget?.name }}</h3><button class="modal-close" @click="closeConfig">×</button></div>
        <div class="modal-body">
          <div class="form-group"><label>连接状态</label>
            <label class="toggle-row"><input type="checkbox" v-model="configTarget.connected"> {{ configTarget.connected ? '已连接' : '未连接' }}</label>
          </div>
          <div class="form-group"><label>版本</label><span class="form-static">{{ configTarget?.version }}</span></div>
          <div class="form-group"><label>描述</label><span class="form-static">{{ configTarget?.meta }}</span></div>
        </div>
        <div class="modal-ft">
          <button class="modal-btn-cancel" @click="closeConfig">关闭</button>
        </div>
      </div>
    </div>
  </div>
</div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useToast } from '@/composables/useToast'
const { showToast } = useToast()

const showAddModal = ref(false)
const showConfigModal = ref(false)
const configTarget = ref<any>(null)
const addForm = reactive({ name: '', type: 'MCP 服务', meta: '' })

const connectors = ref([
  { id: 'github', name: 'GitHub MCP', meta: 'Issues · PRs · CI Runs · Repository API', version: 'v2.1.0', connected: true, iconClass: 'gl-brand', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="22" height="22"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/></svg>' },
  { id: 'notion', name: 'Notion MCP', meta: '数据库读写 · 页面创建与管理 · 块操作', version: 'v1.3.2', connected: true, iconClass: 'gl-purple', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="22" height="22"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>' },
  { id: 'iwiki', name: 'iWiki MCP', meta: '腾讯内部wiki · 文档搜索、创建、编辑', version: 'v1.0.1', connected: false, iconClass: 'gl-cyan', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="22" height="22"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/><path d="M9 7h7"/><path d="M9 11h5"/></svg>' },
  { id: 'postgresql', name: 'PostgreSQL', meta: '本地数据持久化 · SQLite→Pg 迁移中', version: '—', connected: false, iconClass: 'gl-red', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="22" height="22"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>' },
  { id: 'websearch', name: '互联网搜索', meta: 'DuckDuckGo / Google 搜索 API · Agent联网查询', version: 'v2.0.0', connected: true, iconClass: 'gl-amber', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="22" height="22"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>' },
  { id: 'playwright', name: 'Playwright MCP', meta: '浏览器自动化 · 页面截图、表单填充、数据提取', version: 'v1.0.5', connected: true, iconClass: 'gl-green', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="22" height="22"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>' },
])

const connectedCount = computed(() => connectors.value.filter(c => c.connected).length)
const pendingCount = computed(() => connectors.value.filter(c => !c.connected).length)

function openAddModal() { addForm.name = ''; addForm.type = 'MCP 服务'; addForm.meta = ''; showAddModal.value = true }
function closeAddModal() { showAddModal.value = false }
function doAddConnection() {
  if (!addForm.name.trim()) return showToast('请输入连接名称', 'warning')
  connectors.value.push({
    id: 'conn-' + Date.now(), name: addForm.name.trim(), meta: addForm.meta || '新连接', version: '—',
    connected: false, iconClass: 'gl-cyan',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="22" height="22"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>'
  })
  showAddModal.value = false
  showToast(addForm.name + ' 已添加', 'success')
}
function openConfig(conn: any) { configTarget.value = conn; showConfigModal.value = true }
function closeConfig() { showConfigModal.value = false }
</script>
