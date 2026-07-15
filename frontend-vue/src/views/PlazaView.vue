<template>
<div class="page-view active" id="pagePlaza">
  <div class="page-header">
    <div><h1>广场</h1></div>
    <div style="display:flex;align-items:center;gap:10px;flex:1;max-width:420px;margin-left:auto">
      <div class="plaza-search" style="flex:1;margin-bottom:0">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input type="text" placeholder="搜索技能、专家或模型..." v-model="searchQuery" @input="searchPlaza">
      </div>
      <button class="page-btn page-btn-primary" style="white-space:nowrap;flex-shrink:0;height:38px;padding:0 16px;font-size:13px;font-weight:600;border-radius:10px;border:none;background:var(--brand);color:#fff;cursor:pointer;font-family:inherit" @click="addPlazaItem">+ 添加</button>
    </div>
  </div>
  <div class="page-body">
    <div class="plaza-banner-bar">
      <div class="plaza-banner-tabs">
        <button class="plaza-filter-btn" :class="{ active: activeFilter === 'all' }" @click="filterPlaza('all')">全部</button>
        <button class="plaza-filter-btn" :class="{ active: activeFilter === 'skill' }" @click="filterPlaza('skill')">技能</button>
        <button class="plaza-filter-btn" :class="{ active: activeFilter === 'agent' }" @click="filterPlaza('agent')">专家</button>
        <button class="plaza-filter-btn" :class="{ active: activeFilter === 'model' }" @click="filterPlaza('model')">模型</button>
      </div>
    </div>

    <!-- 推荐技能 -->
    <div class="plaza-section" data-plaza-cat="skill" v-show="activeFilter === 'all' || activeFilter === 'skill'">
      <div class="plaza-section-header"><div class="plaza-section-title">推荐技能</div></div>
      <div class="entity-card-grid">
        <div v-for="(item, i) in skillItems" :key="i" class="entity-card" data-plaza="skill" @click="openPlazaDetail('skill', i)">
          <div class="entity-card-header">
            <div class="entity-card-icon skill"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="22" height="22" v-html="skillIcon(i)"></svg></div>
            <div class="entity-card-info">
              <div class="entity-card-name-row"><div class="entity-card-name">{{ item.name }}</div><span class="entity-card-tag" :class="item.tagClass">{{ item.tag }}</span></div>
              <div class="entity-card-meta">{{ item.meta }}</div>
            </div>
            <button class="entity-card-btn-inline" :class="{ installed: item.installed }" @click.stop="item.installed ? openPlazaDetail('skill', i) : installSkill(i)" :disabled="item.installing">
              <svg class="btn-plus-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>{{ item.installed ? '已添加' : item.installing ? '添加中...' : '添加' }}
            </button>
          </div>
          <div class="entity-card-desc">{{ item.desc }}</div>
          <div class="entity-card-footer">
            <span v-for="t in item.tags" :key="t.name" class="entity-tag" :class="{ active: t.active }">{{ t.name }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 精选专家 -->
    <div class="plaza-section" data-plaza-cat="agent" v-show="activeFilter === 'all' || activeFilter === 'agent'">
      <div class="plaza-section-header"><div class="plaza-section-title">精选专家</div></div>
      <div class="entity-card-grid">
        <div v-for="(item, i) in agentItems" :key="i" class="entity-card" data-plaza="agent" @click="openPlazaDetail('agent', i)">
          <div class="entity-card-header">
            <div class="entity-card-icon agent"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="22" height="22" v-html="agentIcon(i)"></svg></div>
            <div class="entity-card-info"><div class="entity-card-name">{{ item.name }}</div><div class="entity-card-meta">{{ item.meta }}</div></div>
            <button class="entity-card-btn-inline" :class="{ installed: item.installed }" @click.stop="item.installed ? openPlazaDetail('agent', i) : summonAgent(i)" :disabled="item.installing">
              <svg class="btn-plus-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>{{ item.installed ? '已召唤' : item.installing ? '召唤中...' : '召唤' }}
            </button>
          </div>
          <div class="entity-card-desc">{{ item.desc }}</div>
          <div class="entity-card-footer">
            <span v-for="t in item.tags" :key="t.name" class="entity-tag" :class="{ active: t.active }">{{ t.name }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 优质模型 -->
    <div class="plaza-section" data-plaza-cat="model" v-show="activeFilter === 'all' || activeFilter === 'model'">
      <div class="plaza-section-header"><div class="plaza-section-title">优质模型</div></div>
      <div class="entity-card-grid">
        <div v-for="(item, i) in modelItems" :key="i" class="entity-card" data-plaza="model" @click="openPlazaDetail('model', i)">
          <div class="entity-card-header">
            <div class="entity-card-icon model"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="22" height="22" v-html="modelIcon(i)"></svg></div>
            <div class="entity-card-info">
              <div class="entity-card-name-row"><div class="entity-card-name">{{ item.name }}</div><span class="entity-card-tag" :class="item.tagClass">{{ item.tag }}</span></div>
              <div class="entity-card-meta">{{ item.meta }}</div>
            </div>
            <button class="entity-card-btn-inline" :class="{ installed: item.installed }" @click.stop="item.installed ? openPlazaDetail('model', i) : connectModel(i)" :disabled="item.installing">
              <svg class="btn-plus-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>{{ item.installed ? (item.tagClass === 'local-deploy' ? '已部署' : '已接入') : (item.tagClass === 'local-deploy' ? '添加' : 'API配置') }}
            </button>
          </div>
          <div class="entity-card-desc">{{ item.desc }}</div>
          <div class="entity-card-footer">
            <span v-for="t in item.tags" :key="t.name" class="entity-tag" :class="{ active: t.active }">{{ t.name }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 详情面板 (原型 openPlazaDetail) -->
  <div class="plaza-detail-overlay" v-if="detailOpen" @click.self="closePlazaDetail">
    <div class="detail-card" @click.stop>
      <div class="detail-card-hero">
        <div class="detail-card-avatar" :class="detailData?.avatarClass" v-html="detailData?.icon"></div>
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
          <div class="detail-card-title" style="margin-bottom:0">{{ detailData?.name }}</div>
          <span v-if="detailData?.tag" class="entity-card-tag" :style="detailData?.tagStyle">{{ detailData?.tag }}</span>
        </div>
        <div class="detail-card-subtitle">{{ detailData?.subtitle }}</div>
        <div class="detail-card-stats">
          <div v-for="s in detailData?.stats" :key="s.l" class="detail-stat"><div class="detail-stat-value">{{ s.v }}</div><div class="detail-stat-label">{{ s.l }}</div></div>
        </div>
      </div>
      <div class="detail-card-body">
        <div v-for="sec in detailData?.sections" :key="sec.title" class="detail-section">
          <div class="detail-section-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg> {{ sec.title }}</div>
          <p v-if="sec.body" style="font-size:13px;color:var(--text-secondary);line-height:1.6;margin-bottom:16px">{{ sec.body }}</p>
          <div v-if="sec.specs" class="spec-grid" style="margin-bottom:0">
            <div v-for="s in sec.specs" :key="s.l" class="spec-item"><div class="spec-item-label">{{ s.l }}</div><div class="spec-item-value">{{ s.v }}</div></div>
          </div>
        </div>
      </div>
      <div class="detail-card-actions">
        <button v-if="canRemove" class="btn btn-delete" @click="removePlazaItem">删除</button>
        <button v-if="canInstall" class="btn btn-install" @click="installCurrent">{{ installBtnLabel }}</button>
        <button class="btn btn-close" @click="closePlazaDetail">关闭</button>
      </div>
    </div>
  </div>

  <!-- API配置弹窗 (原型 openApiConfigModal) -->
  <div class="modal-overlay" v-if="apiConfigOpen" @click.self="closeApiConfig">
    <div class="plaza-api-modal" @click.stop>
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
        <div style="width:44px;height:44px;border-radius:50%;background:rgba(245,158,11,.08);color:#f59e0b;display:flex;align-items:center;justify-content:center;flex-shrink:0">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="22" height="22"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
        </div>
        <div><div style="font-weight:700;font-size:16px;color:var(--text-primary)">配置 API 接入</div><div style="font-size:12px;color:var(--text-secondary)">{{ apiConfigItem?.name }} · 云端 API</div></div>
      </div>
      <div class="form-group"><label style="display:block;font-size:11px;font-weight:600;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">API Key</label><input v-model="apiKey" type="password" placeholder="sk-..." class="form-input" style="font-family:JetBrains Mono,monospace"></div>
      <div class="form-group"><label style="display:block;font-size:11px;font-weight:600;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">API 端点</label><input v-model="apiEndpoint" type="text" class="form-input" style="font-family:JetBrains Mono,monospace"></div>
      <div class="form-group"><label style="display:block;font-size:11px;font-weight:600;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">模型 ID</label><input v-model="apiModelId" type="text" class="form-input" style="font-family:JetBrains Mono,monospace"></div>
      <div style="display:flex;gap:10px;margin-top:20px;justify-content:flex-end">
        <button class="modal-btn-cancel" @click="closeApiConfig">取消</button>
        <button class="modal-btn-confirm" @click="submitApiConfig">确认接入</button>
      </div>
    </div>
  </div>
</div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useToast } from '@/composables/useToast'
const { showToast } = useToast()

const activeFilter = ref('all')
const searchQuery = ref('')
const detailOpen = ref(false)
const detailType = ref('')
const detailIdx = ref(0)

// Detail data matching prototype plazaDetailData
interface PlazaDetailData {
  name: string; tag?: string; tagStyle?: string; subtitle: string;
  avatarClass: string; icon: string;
  stats: { v: string; l: string }[];
  sections: { title: string; body?: string; specs?: { l: string; v: string }[] }[];
}
const plazaDetailData: Record<string, PlazaDetailData[]> = {
  skill: [
    { name: '市场调研助手', tag: '内置', tagStyle: 'background:var(--brand);color:#fff', subtitle: 'Skill · v2.1 · 8 源采集', avatarClass: 'skill', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="28" height="28"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>',
      stats: [{ v: '2.1', l: '版本' }, { v: '8', l: '数据源' }, { v: '12K', l: '用户' }, { v: '4.8', l: '评分' }],
      sections: [{ title: '功能概览', body: '自动抓取行业数据，覆盖金融、科技、医疗等八大行业。一键生成结构化 Markdown 报告，支持自定义模板与数据筛选。' },
        { title: '技术规格', specs: [{ l: '框架', v: '太极引擎 v1.0' }, { l: '数据源', v: '8 大行业 API' }, { l: '输出格式', v: 'Markdown / PDF' }, { l: '更新频率', v: '每小时' }]}] },
    { name: '深度研究', tag: '自创建', tagStyle: 'background:var(--purple);color:#fff', subtitle: 'Skill · v1.7 · 太极沉淀', avatarClass: 'skill', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="28" height="28"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
      stats: [{ v: '1.7', l: '版本' }, { v: '3', l: 'Agent' }, { v: '2.1K', l: '用户' }, { v: '4.5', l: '评分' }],
      sections: [{ title: '功能概览', body: '结构化深度调研工具，多 Agent 并行搜索与交叉验证。太极引擎自动沉淀生成，持续进化。' }] },
  ],
  agent: [
    { name: '数据析客', subtitle: 'Agent · DeepSeek V4 · 在线', avatarClass: 'agent', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="28" height="28"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 4-7 8-7s8 3 8 7"/></svg>',
      stats: [{ v: 'DeepSeek V4', l: '模型' }, { v: '12K', l: '调用' }, { v: '0.8s', l: '响应' }, { v: '4.9', l: '评分' }],
      sections: [{ title: '能力说明', body: '专精数据清洗与可视化。支持 SQL 查询、Python 数据分析、图表生成。自动识别数据质量，提供清洗建议。' },
        { title: '技术规格', specs: [{ l: '语言', v: 'SQL / Python / R' }, { l: '数据库', v: 'MySQL, Pg, SQLite' }, { l: '可视化', v: 'ECharts / Matplotlib' }]}] },
    { name: '安全审计员', subtitle: 'Agent · Kimi-K2.6 · 离线', avatarClass: 'agent', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="28" height="28"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
      stats: [{ v: 'Kimi-K2.6', l: '模型' }, { v: '3.2K', l: '扫描' }, { v: '98%', l: '检出率' }, { v: '4.7', l: '评分' }],
      sections: [{ title: '能力说明', body: '代码安全扫描、漏洞检测、合规审计专家。支持 CI/CD 集成与自动修复建议生成，覆盖 OWASP Top 10 漏洞。' }] },
  ],
  model: [
    { name: 'DeepSeek V4', tag: 'API接入', tagStyle: 'background:#f59e0b;color:#fff', subtitle: 'Model · MoE 685B · 1M ctx', avatarClass: 'model', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="28" height="28"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
      stats: [{ v: '685B', l: '参数' }, { v: '1M', l: '上下文' }, { v: '128K', l: '输出' }, { v: 'MoE', l: '架构' }],
      sections: [{ title: '模型介绍', body: '685B 参数 MoE 架构旗舰模型，128K 上下文窗口，1M token 最大输出。编程、推理、创作全能，综合评分业界领先。' },
        { title: '技术规格', specs: [{ l: '参数', v: '685B (37B active)' }, { l: '上下文', v: '128K tokens' }, { l: '最大输出', v: '1M tokens' }, { l: '价格', v: '¥0.5/1M tokens' }]}] },
    { name: 'Gemma-4 8B', tag: '本地部署', tagStyle: 'background:var(--green);color:#fff', subtitle: 'Model · GGUF · 本地部署', avatarClass: 'model', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="28" height="28"><circle cx="12" cy="12" r="2"/><path d="M12 2v4M22 12h-4M12 20v4M4 12H2M20 12h2M6 6l2 2M16 16l2 2M6 18l2-2M16 8l2-2"/></svg>',
      stats: [{ v: '8B', l: '参数' }, { v: '4.8GB', l: '大小' }, { v: 'GGUF', l: '格式' }, { v: '开源', l: '许可' }],
      sections: [{ title: '模型介绍', body: 'Google 最新开源模型，8B 参数 4.8GB 内存即可流畅运行。隐私优先、低延迟，适合本地部署场景。' }] },
  ],
}

const detailData = computed(() => {
  const data = plazaDetailData[detailType.value]
  return data ? data[detailIdx.value] : null
})
const canRemove = computed(() => {
  if (detailType.value === 'skill') return skillItems[detailIdx.value]?.installed
  if (detailType.value === 'model') return modelItems[detailIdx.value]?.installed
  return false
})
const canInstall = computed(() => !canRemove.value && detailType.value !== 'agent')
const installBtnLabel = computed(() => {
  if (detailType.value === 'model') return modelItems[detailIdx.value]?.tagClass === 'local-deploy' ? '部署' : '接入'
  return '安装'
})

function filterPlaza(cat: string) { activeFilter.value = cat }

function searchPlaza() {
  const q = searchQuery.value.toLowerCase()
  const cards = document.querySelectorAll('#pagePlaza .entity-card') as NodeListOf<HTMLElement>
  let any = false
  cards.forEach(c => {
    const name = (c.querySelector('.entity-card-name')?.textContent || '').toLowerCase()
    const desc = (c.querySelector('.entity-card-desc')?.textContent || '').toLowerCase()
    const visible = !q || name.includes(q) || desc.includes(q)
    c.style.display = visible ? '' : 'none'; if (visible) any = true
  })
  const empty = document.getElementById('plazaEmpty')
  if (empty) empty.style.display = any ? 'none' : ''
}

function addPlazaItem() { showToast('添加功能开发中，请通过生态广场浏览和安装', 'info') }

const skillItems = reactive([
  { name: '市场调研助手', tag: '内置', tagClass: 'builtin', meta: 'skill · v2.1 · 8源采集', desc: '自动抓取行业数据，生成结构化Markdown报告。支持8大行业数据源。', installed: true, installing: false, tags: [{ name: '已激活', active: true }, { name: '数据采集' }, { name: '分析' }, { name: '报告' }] },
  { name: '深度研究', tag: '自创建', tagClass: 'autocreated', meta: 'skill · v1.7 · 太极沉淀', desc: '结构化深度调研，多 Agent 并行搜索与交叉验证。太极引擎自动沉淀生成。', installed: false, installing: false, tags: [{ name: '多Agent' }, { name: '并行搜索' }, { name: '交叉验证' }] },
])
const agentItems = reactive([
  { name: '数据析客', meta: 'agent · DeepSeek V4 · 在线', desc: '专精数据清洗与可视化。支持 SQL 查询、Python 分析、图表生成。', installed: true, installing: false, tags: [{ name: '在线', active: true }, { name: '数据分析' }, { name: 'Python' }, { name: 'SQL' }] },
  { name: '安全审计员', meta: 'agent · Kimi-K2.6 · 离线', desc: '代码安全扫描、漏洞检测、合规审计。支持 CI 集成与自动修复建议。', installed: false, installing: false, tags: [{ name: '安全' }, { name: '漏洞扫描' }, { name: 'CI' }] },
])
const modelItems = reactive([
  { name: 'DeepSeek V4', tag: 'API接入', tagClass: 'api-cloud', meta: 'model · MoE 685B · 1M ctx', desc: '685B参数MoE架构，128K上下文。编程、推理、创作全能。', installed: false, installing: false, tags: [{ name: '首选', active: true }, { name: '推理' }, { name: '编程' }, { name: '1M ctx' }] },
  { name: 'Gemma-4 8B', tag: '本地部署', tagClass: 'local-deploy', meta: 'model · GGUF · 本地部署', desc: 'Google 最新开源，8GB 内存即可流畅本地运行。隐私优先、低延迟。', installed: true, installing: false, tags: [{ name: '本地' }, { name: 'GGUF' }, { name: '4.8GB' }, { name: '开源' }] },
])

function installSkill(idx: number) {
  const item = skillItems[idx]
  if (item.installed || item.installing) return
  item.installing = true
  setTimeout(() => { item.installing = false; item.installed = true; showToast(item.name + ' 已添加', 'success') }, 1200 + Math.random() * 800)
}
function summonAgent(idx: number) {
  const item = agentItems[idx]
  if (item.installed || item.installing) return
  item.installing = true
  setTimeout(() => { item.installing = false; item.installed = true; showToast(item.name + ' 已召唤', 'success') }, 1200 + Math.random() * 800)
}

// API Config Modal
const apiConfigOpen = ref(false)
const apiConfigIdx = ref(0)
const apiKey = ref('')
const apiEndpoint = ref('https://api.deepseek.com/v1')
const apiModelId = ref('deepseek-v4')
const apiConfigItem = computed(() => modelItems[apiConfigIdx.value])

function connectModel(idx: number) {
  const item = modelItems[idx]
  if (item.installed) { openPlazaDetail('model', idx); return }
  if (item.tagClass === 'local-deploy') {
    item.installing = true
    setTimeout(() => { item.installing = false; item.installed = true; showToast(item.name + ' 部署完成', 'success') }, 1500)
    return
  }
  apiConfigIdx.value = idx
  apiConfigOpen.value = true
}
function closeApiConfig() { apiConfigOpen.value = false }
function submitApiConfig() {
  const item = modelItems[apiConfigIdx.value]
  apiConfigOpen.value = false
  showToast('正在验证 API Key...', 'info')
  setTimeout(() => {
    item.installed = true
    showToast(item.name + ' API 已接入', 'success')
  }, 1200)
}

function openPlazaDetail(type: string, idx: number) { detailType.value = type; detailIdx.value = idx; detailOpen.value = true }
function closePlazaDetail() { detailOpen.value = false }
function removePlazaItem() {
  if (detailType.value === 'skill') skillItems[detailIdx.value].installed = false
  else if (detailType.value === 'model') modelItems[detailIdx.value].installed = false
  detailOpen.value = false
  showToast(detailData.value?.name + ' 已移除', 'success')
}
function installCurrent() {
  if (detailType.value === 'skill') installSkill(detailIdx.value)
  else if (detailType.value === 'model') connectModel(detailIdx.value)
  detailOpen.value = false
}

function skillIcon(i: number) { return i === 0 ? '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>' : '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>' }
function agentIcon(i: number) { return i === 0 ? '<circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 4-7 8-7s8 3 8 7"/>' : '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>' }
function modelIcon(i: number) { return i === 0 ? '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>' : '<circle cx="12" cy="12" r="2"/><path d="M12 2v4M22 12h-4M12 20v4M4 12H2M20 12h2M6 6l2 2M16 16l2 2M6 18l2-2M16 8l2-2"/>' }
</script>
