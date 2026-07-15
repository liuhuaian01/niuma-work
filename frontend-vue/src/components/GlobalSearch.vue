<template>
  <div class="global-search-overlay" :class="{ open: visible }" role="dialog" aria-modal="true" aria-label="全局搜索" @click.self="close">
    <div class="global-search-panel">
      <div class="global-search-input-row">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input ref="searchInput" type="text" v-model="query" placeholder="搜索 Agent、对话、文件或设置..." @keydown.esc="close" />
        <span class="global-search-kbd">esc</span>
      </div>
      <div class="global-search-results">
        <template v-if="filtered.length">
          <div class="global-search-section-label">{{ filtered[0].section }}</div>
          <div v-for="(item, i) in filtered" :key="i"
            class="global-search-item" :class="{ active: activeIdx === i }"
            @click="select(item)" @mouseenter="activeIdx = i">
            <span v-if="item.avatar" class="gsi-avatar" :style="{ background: item.avatarColor }">{{ item.avatar }}</span>
            <span v-else class="gsi-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="8"/></svg>
            </span>
            {{ item.label }}
            <span v-if="item.tag" class="gsi-tag">{{ item.tag }}</span>
            <span v-if="item.shortcut" class="gsi-kbd">{{ item.shortcut }}</span>
          </div>
        </template>
        <div v-else style="padding:var(--space-4);text-align:center;color:var(--text-tertiary);font-size:13px">
          未找到匹配结果
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const visible = ref(false)
const query = ref('')
const activeIdx = ref(0)
const searchInput = ref<HTMLInputElement | null>(null)

interface SearchItem {
  section: string
  label: string
  avatar?: string
  avatarColor?: string
  tag?: string
  shortcut?: string
  action: () => void
}

const allItems: SearchItem[] = [
  { section: '快速导航', label: '对话', shortcut: 'G H', action: () => router.push('/chat') },
  { section: '快速导航', label: '项目', shortcut: 'G P', action: () => router.push('/projects') },
  { section: '快速导航', label: '广场', shortcut: 'G L', action: () => router.push('/plaza') },
  { section: '快速导航', label: '记忆', shortcut: 'G M', action: () => router.push('/memory') },
  { section: '快速导航', label: '文件', shortcut: 'G F', action: () => router.push('/files') },
  { section: '快速导航', label: '连接', shortcut: 'G C', action: () => router.push('/connections') },
  { section: '快速导航', label: '实验室', shortcut: 'G B', action: () => router.push('/lab') },
  { section: '快速导航', label: '设置', shortcut: 'G ,', action: () => router.push('/settings') },
  { section: 'Agent', label: '超级牛马', avatar: '牛', avatarColor: 'linear-gradient(135deg,#6391ED,#5ED6C0)', tag: '平台助手', action: () => router.push('/chat') },
  { section: 'Agent', label: 'Hermes', avatar: 'H', avatarColor: 'linear-gradient(135deg,#6391ED,#06B6D4)', tag: '主智能体', action: () => router.push('/chat') },
  { section: 'Agent', label: '小章鱼', avatar: '章', avatarColor: 'linear-gradient(135deg,#52C47A,#34D399)', tag: '研究员', action: () => router.push('/chat') },
]

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return allItems
  return allItems.filter(i => i.label.toLowerCase().includes(q) || (i.tag && i.tag.toLowerCase().includes(q)))
})

watch(visible, (v) => {
  if (v) {
    query.value = ''
    activeIdx.value = 0
    setTimeout(() => searchInput.value?.focus(), 50)
  }
})

watch(filtered, () => { activeIdx.value = 0 })

function open() { visible.value = true }
function close() { visible.value = false }

function select(item: SearchItem) {
  item.action()
  close()
}

function onKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    visible.value = !visible.value
    return
  }
  if (!visible.value) return
  if (e.key === 'ArrowDown') { e.preventDefault(); activeIdx.value = Math.min(activeIdx.value + 1, filtered.value.length - 1) }
  if (e.key === 'ArrowUp') { e.preventDefault(); activeIdx.value = Math.max(activeIdx.value - 1, 0) }
  if (e.key === 'Enter' && filtered.value[activeIdx.value]) {
    e.preventDefault()
    select(filtered.value[activeIdx.value])
  }
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))

defineExpose({ open, close })
</script>
