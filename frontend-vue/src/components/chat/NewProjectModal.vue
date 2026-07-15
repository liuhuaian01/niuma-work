<template>
  <div
    class="new-agent-overlay"
    :class="{ open: modelValue }"
    @click.self="$emit('update:modelValue', false)"
  >
    <div class="na-db-outer np-redesign" @click.stop>
      <div class="na-db-inner">
        <!-- Header -->
        <div class="np-header">
          <div class="np-header-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="4"/>
              <line x1="12" y1="8" x2="12" y2="16"/>
              <line x1="8" y1="12" x2="16" y2="12"/>
            </svg>
          </div>
          <div class="np-header-title">新建项目</div>
          <div class="np-header-desc">配置你的 AI 协作工作空间，选择模板与 Agent 团队</div>
        </div>

        <!-- Body -->
        <div class="np-body">
          <!-- Project Name -->
          <div class="np-section">
            <div class="np-section-label">项目名称</div>
            <div class="np-name-input-wrap">
              <input class="np-name-input" v-model="form.name" type="text" placeholder="给你的项目起个名字…" maxlength="30">
            </div>
          </div>

          <!-- Template Grid -->
          <div class="np-section">
            <div class="np-section-label">
              项目模板
              <span class="np-optional-tag">可选</span>
            </div>
            <div class="np-template-grid">
              <div
                v-for="tpl in templates"
                :key="tpl.id"
                class="np-template-card"
                :class="{ 'np-template-custom': tpl.id === 'blank', selected: form.template === tpl.id }"
                @click="form.template = tpl.id"
              >
                <div class="np-template-icon" v-html="tpl.icon"></div>
                <div class="np-template-name">{{ tpl.name }}</div>
                <div class="np-template-desc">{{ tpl.desc }}</div>
                <div class="np-template-check"></div>
              </div>
            </div>
          </div>

          <!-- Prompt -->
          <div class="np-section">
            <div class="np-section-label">
              项目指令
              <span class="np-optional-tag">可选</span>
            </div>
            <textarea class="np-textarea" v-model="form.prompt" placeholder="提供当前项目的背景信息和规范，让 Agent 的回复更精准、更符合要求。比如：项目目标、团队习惯、风格偏好、输出约束等"></textarea>
          </div>

          <!-- Agent Team -->
          <div class="np-section" style="margin-bottom:0">
            <div class="np-section-label">
              协作 Agent
              <span class="np-min-badge">最少2个</span>
            </div>

            <!-- Agent Grid -->
            <div v-if="agents.length === 0" class="np-empty-card">
              <div class="np-empty-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              </div>
              <div class="np-empty-title">还没有 Agent</div>
              <div class="np-empty-desc">当前没有任何 Agent，无法创建协作项目。请先创建你的第一个 Agent。</div>
              <div class="np-empty-actions">
                <button class="np-empty-btn primary" @click="$emit('update:modelValue', false); $emit('openAgentModal')">立即创建 Agent</button>
              </div>
            </div>

            <div v-else class="np-agent-grid">
              <div
                v-for="agent in agents"
                :key="agent.id"
                class="np-agent-card"
                :class="{ selected: form.agents.includes(agent.id) }"
                @click="toggleAgent(agent.id)"
              >
                <div class="np-agent-dot" :style="{ background: agent.color }">{{ agent.avatar }}</div>
                <div class="np-agent-info">
                  <div class="np-agent-name">{{ agent.name }}</div>
                  <div class="np-agent-role">{{ agent.role }}</div>
                </div>
                <div class="np-agent-check"></div>
              </div>

              <!-- Add Agent Card -->
              <div class="np-agent-card np-add-agent" @click="$emit('update:modelValue', false); $emit('openAgentModal')">
                <div class="np-add-agent-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                </div>
                <div class="np-add-agent-text">新建 Agent</div>
              </div>
            </div>

            <!-- Hint -->
            <div v-if="agents.length > 0" class="np-hint" :class="{ warn: agents.length < 2 }">
              <span v-if="agents.length < 2">当前仅有 <b>{{ agents.length }}</b> 个 Agent · 需要 <b>至少 2 个</b> 才能创建项目</span>
              <span v-else>已选择 <b>{{ form.agents.length }}</b> 个 Agent · 请选择至少 <b>2</b> 个</span>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="np-footer">
          <span class="np-footer-hint">{{ footerHint }}</span>
          <div class="np-footer-actions">
            <button class="np-btn np-btn-secondary" @click="$emit('update:modelValue', false)">取消</button>
            <button class="np-btn np-btn-primary" :disabled="!canCreate" @click="create">确定</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, computed } from 'vue'

export interface AgentInfo {
  id: string
  name: string
  avatar: string
  color: string
  role: string
}

export interface ProjectFormData {
  name: string
  template: string
  prompt: string
  agents: string[]
}

const props = defineProps<{ modelValue: boolean; agents: AgentInfo[] }>()
const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  create: [data: ProjectFormData]
  openAgentModal: []
}>()

const templates = [
  {
    id: 'product',
    name: '产品研发',
    desc: 'PRD 撰写、技术方案、迭代管理',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>',
  },
  {
    id: 'research',
    name: '市场调研',
    desc: '竞品分析、行业趋势、用户洞察',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="16.5" y1="16.5" x2="21" y2="21"/></svg>',
  },
  {
    id: 'content',
    name: '内容运营',
    desc: '文案创作、多平台分发、数据分析',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
  },
  {
    id: 'knowledge',
    name: '知识库',
    desc: '文档沉淀、团队Wiki、检索问答',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
  },
  {
    id: 'delivery',
    name: '项目交付',
    desc: '任务追踪、里程碑、交付验收',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
  },
  {
    id: 'blank',
    name: '空白项目',
    desc: '从零开始，自由定义一切',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="3"/><line x1="8" y1="12" x2="16" y2="12"/></svg>',
  },
]

const form = reactive({
  name: '',
  template: '',
  prompt: '',
  agents: [] as string[],
})

const canCreate = computed(() => form.name.trim() && form.agents.length >= 2)
const footerHint = computed(() => {
  if (!form.name.trim()) return '请输入项目名称'
  if (form.agents.length < 2) return `请选择至少 2 个协作 Agent（已选 ${form.agents.length}）`
  return form.template ? '已选择模板' : '未选模板，将创建空白项目'
})

function toggleAgent(id: string) {
  const idx = form.agents.indexOf(id)
  if (idx === -1) {
    form.agents.push(id)
  } else {
    form.agents.splice(idx, 1)
  }
}

function create() {
  if (!form.name.trim() || form.agents.length < 2) return
  emit('create', {
    name: form.name.trim(),
    template: form.template || 'blank',
    prompt: form.prompt.trim(),
    agents: [...form.agents],
  })
  emit('update:modelValue', false)
  form.name = ''
  form.template = ''
  form.prompt = ''
  form.agents = []
}
</script>
