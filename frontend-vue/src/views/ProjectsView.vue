<template>
<div class="page-view active" id="pageProjects">
  <div class="projects-hero">
    <div class="projects-hero-left">
      <h1>项目</h1>
      <p class="projects-hero-sub">多人协同，打造超级团队</p>
      <button class="page-btn page-btn-primary" @click="showCreateProject = true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        新建项目
      </button>
    </div>
  </div>

  <div class="projects-section">
    <div class="projects-section-header">
      <h2>我的项目</h2>
      <div class="projects-search-box">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input type="text" placeholder="搜索项目" v-model="searchQuery">
      </div>
    </div>
    <div class="projects-grid">
      <div v-for="p in filteredProjects" :key="p.id" class="project-card" :data-project="p.id">
        <div class="project-card-main" @click="openProject(p.id)">
          <div class="project-card-icon" v-html="p.icon"></div>
          <div class="project-card-info">
            <div class="project-card-name">{{ p.name }}</div>
            <div class="project-card-meta">{{ p.meta }}</div>
          </div>
        </div>
        <div style="position:relative;">
          <button class="project-card-menu" aria-label="更多" @click.stop="($event.target as HTMLElement).closest('.project-card')?.querySelector('.project-card-dropdown')?.classList.toggle('open')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>
          </button>
          <div class="project-card-dropdown">
            <button class="project-card-dropdown-item" @click="openProject(p.id)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg> 打开</button>
            <button class="project-card-dropdown-item" @click="startRename(p)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> 重命名</button>
            <button class="project-card-dropdown-item" @click="archiveProject(p.id)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 8v13H3V8"/><path d="M1 3h22v5H1z"/><line x1="10" y1="12" x2="14" y2="12"/></svg> 归档</button>
            <div class="project-card-dropdown-divider"></div>
            <button class="project-card-dropdown-item danger" @click="confirmDelete(p)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg> 删除</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="projects-section">
    <h2 class="projects-section-title">从模板创建</h2>
    <div class="template-grid">
      <div v-for="t in templates" :key="t.id" class="template-card" @click="openCreateWithTemplate(t.name)">
        <div class="template-card-icon" v-html="t.icon"></div>
        <div class="template-card-name">{{ t.name }}</div>
        <div class="template-card-desc">{{ t.desc }}</div>
      </div>
    </div>
  </div>

  <!-- Create Project Modal — 按原型 15205 行还原 -->
  <div class="new-project-modal" :class="{ open: showCreateProject }" @click.self="showCreateProject = false">
    <div class="new-project-modal-card">
      <div class="new-project-modal-header">
        <h3>新建项目</h3>
        <button class="new-project-modal-close" @click="showCreateProject = false">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>
      </div>
      <div class="new-project-modal-body">
        <div class="np-field">
          <label class="np-field-label">项目名称</label>
          <input type="text" class="np-name-input" v-model="newProjectName" placeholder="请输入项目名称" maxlength="30">
        </div>
        <div class="np-field">
          <div class="np-field-header">
            <label class="np-field-label">指令</label>
            <select class="np-template-select" v-model="newProjectTemplate">
              <option value="">选择模板</option>
              <option v-for="t in templates" :key="t.id" :value="t.name">{{ t.name }}</option>
            </select>
          </div>
          <textarea class="np-textarea" v-model="newProjectPrompt" placeholder="提供当前项目的背景信息和规范，让 Agent 的回复更精准、更符合要求。比如：项目目标、团队习惯、风格偏好、输出约束等" rows="3"></textarea>
        </div>
        <div class="np-field">
          <label class="np-field-label">连接器 <span class="np-optional">（可选）</span></label>
          <div class="np-tag-row">
            <span v-for="(c, i) in newConnectors" :key="i" class="np-tag">{{ c }} <button class="np-tag-remove" @click="newConnectors.splice(i,1)">&times;</button></span>
            <div style="position:relative">
              <button class="np-add-btn" @click="toggleSelectPanel('connector')">+ 添加</button>
              <div class="np-select-panel" v-if="activeSelectPanel === 'connector'">
                <div class="np-select-search">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                  <input type="text" v-model="selectSearch" placeholder="搜索…" autofocus>
                </div>
                <div class="np-select-list">
                  <div v-for="opt in filteredSelectOptions('connector')" :key="opt.id" class="np-select-item" :class="{ selected: newConnectors.includes(opt.label) }" @click="toggleSelectItem('connector', opt.label)">
                    <div class="np-select-check"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>
                    {{ opt.label }}
                  </div>
                  <div v-if="filteredSelectOptions('connector').length === 0" class="np-select-empty">无匹配项</div>
                </div>
                <div class="np-select-footer">
                  <button class="np-select-cancel" @click="activeSelectPanel = null">取消</button>
                  <button class="np-select-confirm" @click="confirmSelectPanel">确定</button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="np-field">
          <label class="np-field-label">专家 <span class="np-optional">（可选）</span></label>
          <div class="np-tag-row">
            <span v-for="(e, i) in newExperts" :key="i" class="np-tag">{{ e }} <button class="np-tag-remove" @click="newExperts.splice(i,1)">&times;</button></span>
            <div style="position:relative">
              <button class="np-add-btn" @click="toggleSelectPanel('expert')">+ 添加</button>
              <div class="np-select-panel" v-if="activeSelectPanel === 'expert'">
                <div class="np-select-search">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                  <input type="text" v-model="selectSearch" placeholder="搜索…" autofocus>
                </div>
                <div class="np-select-list">
                  <div v-for="opt in filteredSelectOptions('expert')" :key="opt.id" class="np-select-item" :class="{ selected: newExperts.includes(opt.label) }" @click="toggleSelectItem('expert', opt.label)">
                    <div class="np-select-check"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>
                    {{ opt.label }}
                  </div>
                  <div v-if="filteredSelectOptions('expert').length === 0" class="np-select-empty">无匹配项</div>
                </div>
                <div class="np-select-footer">
                  <button class="np-select-cancel" @click="activeSelectPanel = null">取消</button>
                  <button class="np-select-confirm" @click="confirmSelectPanel">确定</button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="np-field">
          <label class="np-field-label">技能 <span class="np-optional">（可选）</span></label>
          <div class="np-tag-row">
            <span v-for="(s, i) in newSkills" :key="i" class="np-tag">{{ s }} <button class="np-tag-remove" @click="newSkills.splice(i,1)">&times;</button></span>
            <div style="position:relative">
              <button class="np-add-btn" @click="toggleSelectPanel('skill')">+ 添加</button>
              <div class="np-select-panel" v-if="activeSelectPanel === 'skill'">
                <div class="np-select-search">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                  <input type="text" v-model="selectSearch" placeholder="搜索…" autofocus>
                </div>
                <div class="np-select-list">
                  <div v-for="opt in filteredSelectOptions('skill')" :key="opt.id" class="np-select-item" :class="{ selected: newSkills.includes(opt.label) }" @click="toggleSelectItem('skill', opt.label)">
                    <div class="np-select-check"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg></div>
                    {{ opt.label }}
                  </div>
                  <div v-if="filteredSelectOptions('skill').length === 0" class="np-select-empty">无匹配项</div>
                </div>
                <div class="np-select-footer">
                  <button class="np-select-cancel" @click="activeSelectPanel = null">取消</button>
                  <button class="np-select-confirm" @click="confirmSelectPanel">确定</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="new-project-modal-footer">
        <span class="np-footer-hint">切换模板会覆盖当前指令内容</span>
        <div class="np-footer-actions">
          <button class="np-btn np-btn-secondary" @click="showCreateProject = false">取消</button>
          <button class="np-btn np-btn-primary" @click="confirmCreateProject">确定</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Rename Modal -->
  <div class="modal-overlay" v-if="renameTarget" @click.self="renameTarget = null">
    <div class="modal" style="max-width:400px">
      <div class="modal-hd"><h3>重命名</h3><button class="modal-close" @click="renameTarget = null">×</button></div>
      <div class="modal-body">
        <div class="form-group"><input v-model="renameText" type="text" class="form-input" placeholder="新名称" @keyup.enter="confirmRename"></div>
      </div>
      <div class="modal-ft">
        <button class="modal-btn-cancel" @click="renameTarget = null">取消</button>
        <button class="modal-btn-confirm" @click="confirmRename">确定</button>
      </div>
    </div>
  </div>

  <!-- Delete Confirm -->
  <div class="modal-overlay" v-if="deleteTarget" @click.self="deleteTarget = null">
    <div class="modal" style="max-width:400px">
      <div class="modal-hd"><h3>确认删除</h3><button class="modal-close" @click="deleteTarget = null">×</button></div>
      <div class="modal-body"><p>确定要删除项目 <strong>{{ deleteTarget.name }}</strong> 吗？此操作不可撤销。</p></div>
      <div class="modal-ft">
        <button class="modal-btn-cancel" @click="deleteTarget = null">取消</button>
        <button class="modal-btn-confirm" style="background:var(--coral);border-color:var(--coral)" @click="doDeleteProject">删除</button>
      </div>
    </div>
  </div>
</div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const { showToast } = useToast()
const searchQuery = ref('')

interface Project { id: string; name: string; meta: string; icon: string }
interface Template { id: string; name: string; desc: string; icon: string }

const icon = (d: string) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">${d}</svg>`

const projects: Project[] = [
  { id: 'cyber', name: '赛博工坊 v2.0', meta: '添加于 2小时前', icon: icon('<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>') },
  { id: 'copy', name: '产品文案生成', meta: '添加于 5小时前', icon: icon('<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>') },
  { id: 'api', name: 'API 网关优化', meta: '添加于 1天前', icon: icon('<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>') },
  { id: 'research', name: '用户调研报告', meta: '添加于 3天前', icon: icon('<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>') },
  { id: 'dashboard', name: '数据看板设计', meta: '添加于 1周前', icon: icon('<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>') },
]

const templates: Template[] = [
  { id: 'product', name: '产品需求全流程', desc: '从需求规划、PRD 到研发测试验收', icon: icon('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>') },
  { id: 'research', name: '市场调研与竞品分析', desc: '深度调研、竞品拆解、报告评审', icon: icon('<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>') },
  { id: 'content', name: '内容运营工作台', desc: '从选题、写稿、审核到发布复盘', icon: icon('<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>') },
  { id: 'knowledge', name: '团队知识库', desc: '持续沉淀 SOP、经验和 FAQ', icon: icon('<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>') },
  { id: 'delivery', name: '项目交付', desc: '管理客户需求、计划、风险和周报', icon: icon('<rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>') },
  { id: 'bug', name: 'Bug 跟踪/测试验收', desc: '持续跟踪Bug，统一测试用例和验收结论', icon: icon('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>') },
  { id: 'newmedia', name: '新媒体运营', desc: '选题策划、内容排期、多平台分发与数据复盘', icon: icon('<rect x="2" y="2" width="20" height="20" rx="3"/><circle cx="12" cy="12" r="4"/><path d="M2 8h20M8 2v20"/>') },
  { id: 'novel', name: '网络小说创作', desc: '世界观构建、大纲设计、角色管理、章节创作与质量评审', icon: icon('<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>') },
  { id: 'ecommerce', name: '电商运营', desc: '商品策划、活动运营、投放管理、订单分析与客服协同', icon: icon('<path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/>') },
  { id: 'shortvideo', name: '短视频制作', desc: '创意策划、分镜脚本、拍摄剪辑、平台发布与效果分析', icon: icon('<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>') },
]

const filteredProjects = computed(() =>
  searchQuery.value ? projects.filter(p => p.name.includes(searchQuery.value)) : projects
)

function openProject(id: string) { router.push('/projects/' + id) }

const showCreateProject = ref(false)
const newProjectName = ref('')
const newProjectTemplate = ref('')
const newProjectPrompt = ref('')
const newConnectors = ref<string[]>([])
const newExperts = ref<string[]>([])
const newSkills = ref<string[]>([])
const activeSelectPanel = ref<string | null>(null)
const selectSearch = ref('')
const selectPending: Record<string, string[]> = { connector: [], expert: [], skill: [] }

const connectorOptions = [
  { id: 'github', label: 'GitHub' }, { id: 'notion', label: 'Notion' },
  { id: 'tencent-docs', label: '腾讯文档' }, { id: 'lexiang', label: '乐享知识库' },
  { id: 'dingtalk', label: '钉钉' }, { id: 'wecom', label: '企业微信' },
  { id: 'feishu', label: '飞书' }, { id: 'tapd', label: 'TAPD' },
]
const expertOptions = [
  { id: 'knowledge-mgr', label: '知识管理专家' }, { id: 'doc-writer', label: '文档生成专家' },
  { id: 'code-review', label: '代码审查专家' }, { id: 'data-analyst', label: '数据分析专家' },
  { id: 'ui-designer', label: 'UI设计专家' }, { id: 'architect', label: '架构师' },
  { id: 'qa-tester', label: '测试专家' }, { id: 'product-mgr', label: '产品经理专家' },
]
const skillOptions = [
  { id: 'deep-research', label: '深度研究' }, { id: 'code-gen', label: '代码生成' },
  { id: 'copywriting', label: '文案创作' }, { id: 'data-viz', label: '数据可视化' },
  { id: 'meeting-notes', label: '会议纪要' }, { id: 'translation', label: '翻译' },
  { id: 'qa-analysis', label: '问答分析' }, { id: 'workflow-auto', label: '工作流自动化' },
]

function toggleSelectPanel(type: string) {
  if (activeSelectPanel.value === type) { activeSelectPanel.value = null; return }
  activeSelectPanel.value = type
  selectSearch.value = ''
  // Init pending from existing
  const existing = type === 'connector' ? newConnectors.value : type === 'expert' ? newExperts.value : newSkills.value
  selectPending[type] = [...existing]
}

function toggleSelectItem(type: string, label: string) {
  const idx = selectPending[type].indexOf(label)
  if (idx === -1) selectPending[type].push(label)
  else selectPending[type].splice(idx, 1)
}

function filteredSelectOptions(type: string) {
  const opts = type === 'connector' ? connectorOptions : type === 'expert' ? expertOptions : skillOptions
  const q = selectSearch.value.toLowerCase()
  return q ? opts.filter(o => o.label.toLowerCase().includes(q)) : opts
}

function confirmSelectPanel() {
  const type = activeSelectPanel.value
  if (!type) return
  if (type === 'connector') newConnectors.value = [...selectPending[type]]
  else if (type === 'expert') newExperts.value = [...selectPending[type]]
  else newSkills.value = [...selectPending[type]]
  activeSelectPanel.value = null
}

function openCreateWithTemplate(name?: string) {
  newProjectTemplate.value = name || ''
  newProjectName.value = name || ''
  showCreateProject.value = true
}
const renameTarget = ref<string | null>(null)
const renameText = ref('')
const deleteTarget = ref<any>(null)

function startRename(p: any) { renameTarget.value = p.id; renameText.value = p.name }
function confirmRename() {
  if (!renameText.value.trim()) return showToast('名称不能为空', 'warning')
  const proj = projects.value.find(p => p.id === renameTarget.value)
  if (proj) { proj.name = renameText.value.trim(); showToast('已重命名: ' + proj.name, 'success') }
  renameTarget.value = null
}

function archiveProject(id: string) {
  const proj = projects.value.find(p => p.id === id)
  if (proj) { proj.archived = !proj.archived; showToast(proj.archived ? '已归档' : '已取消归档', 'success') }
}

function confirmDelete(p: any) { deleteTarget.value = p }
function doDeleteProject() {
  if (!deleteTarget.value) return
  projects.value = projects.value.filter(p => p.id !== deleteTarget.value.id)
  showToast('已删除: ' + deleteTarget.value.name, 'success')
  deleteTarget.value = null
}

function confirmCreateProject() {
  const name = newProjectName.value.trim()
  if (!name) { showToast('请输入项目名称', 'warning'); return }
  showToast('项目创建成功: ' + name, 'success')
  showCreateProject.value = false
  newProjectName.value = ''
  newProjectTemplate.value = ''
  newProjectPrompt.value = ''
  newConnectors.value = []
  newExperts.value = []
  newSkills.value = []
}
</script>
