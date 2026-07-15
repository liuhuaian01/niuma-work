<template>
  <div
    class="new-agent-overlay"
    :class="{ open: modelValue }"
    @click.self="$emit('update:modelValue', false)"
  >
    <div class="na-db-outer" @click.stop>
      <div class="na-db-inner">
        <!-- Header -->
        <div class="na-header">
          <div class="na-header-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="4"/>
              <line x1="8" y1="12" x2="16" y2="12"/>
              <line x1="12" y1="8" x2="12" y2="16"/>
            </svg>
          </div>
          <div class="na-header-title">新建智能体</div>
          <div class="na-header-desc">配置你的专属 AI 助手，设定性格与能力边界</div>
        </div>

        <!-- Body -->
        <div class="na-body">
          <!-- Avatar Ring + Mask -->
          <div class="na-avatar-wrap">
            <div class="na-avatar-ring" @click="cycleAvatar">
              <div class="na-avatar-img" :style="{ background: selectedColor }" v-html="avatars[avatarIdx]"></div>
              <div class="na-avatar-mask">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
              </div>
            </div>
            <div class="na-avatar-hint">点击切换头像</div>
            <div class="na-palette">
              <span
                v-for="(c, i) in paletteColors"
                :key="i"
                class="na-palette-dot"
                :class="{ selected: selectedColor === c }"
                :style="{ background: c }"
                @click="selectedColor = c"
              ></span>
            </div>
          </div>

          <!-- Name -->
          <div class="na-field">
            <label class="na-field-label">名称</label>
            <input class="na-input" v-model="form.name" type="text" placeholder="给你的智能体起个名字" maxlength="20">
          </div>

          <!-- Role -->
          <div class="na-field">
            <label class="na-field-label">角色</label>
            <input class="na-input" v-model="form.role" type="text" placeholder="一句话描述它擅长什么" maxlength="40">
          </div>

          <!-- Soul -->
          <div class="na-field">
            <label class="na-field-label">Soul · 灵魂设定</label>
            <textarea class="na-textarea" v-model="form.soul" placeholder="描述它的性格、说话风格和工作方式..."></textarea>
          </div>

          <!-- Model -->
          <div class="na-field">
            <label class="na-field-label">默认模型</label>
            <div class="na-models">
              <span
                v-for="m in models"
                :key="m"
                class="na-model-chip"
                :class="{ selected: form.model === m }"
                @click="form.model = m"
              >{{ m }}</span>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="na-footer">
          <button class="na-submit-btn" @click="create">
            创建 Agent
            <span class="btn-arrow-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>
            </span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'

defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  create: [data: AgentFormData]
}>()

export interface AgentFormData {
  name: string
  role: string
  soul: string
  avatar: string
  color: string
  model: string
}

const avatars = [
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 4-7 8-7s8 3 8 7"/></svg>`,
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>`,
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>`,
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"/><line x1="16" y1="8" x2="2" y2="22"/><line x1="17.5" y1="15" x2="9" y2="15"/></svg>`,
]
const avatarIdx = ref(0)
const selectedColor = ref('linear-gradient(135deg,#6391ED,#5ED6C0,#8B5CF6)')
const paletteColors = [
  'linear-gradient(135deg,#6391ED,#5ED6C0,#8B5CF6)',
  'linear-gradient(135deg,#8B5CF6,#F87171)',
  'linear-gradient(135deg,#34D399,#2DD4BF)',
  'linear-gradient(135deg,#FBBF24,#F87171)',
  'linear-gradient(135deg,#A78BFA,#6391ED)',
]

const models = ['DeepSeek-V4-Pro', 'Kimi-K2.6', 'Qwen3.7-Max', 'Claude-4-Sonnet']

const form = reactive({
  name: '',
  role: '',
  soul: '',
  model: 'DeepSeek-V4-Pro',
})

function cycleAvatar() {
  avatarIdx.value = (avatarIdx.value + 1) % avatars.length
}

function create() {
  if (!form.name.trim()) return
  emit('create', {
    name: form.name.trim(),
    role: form.role.trim() || '未指定',
    soul: form.soul.trim() || '通用智能助手',
    avatar: avatars[avatarIdx.value],
    color: selectedColor.value,
    model: form.model,
  })
  emit('update:modelValue', false)
  // Reset
  form.name = ''
  form.role = ''
  form.soul = ''
  form.model = 'DeepSeek-V4-Pro'
  avatarIdx.value = 0
  selectedColor.value = paletteColors[0]
}
</script>
