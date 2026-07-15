<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="context-menu-overlay"
      @click="close"
      @contextmenu.prevent="close"
    ></div>
    <div
      v-if="visible"
      class="context-menu"
      :style="{ left: pos.x + 'px', top: pos.y + 'px' }"
      role="menu"
    >
      <button
        v-for="item in items"
        :key="item.action"
        class="context-item"
        :class="{ danger: item.danger }"
        @click="handleAction(item.action)"
      >
        <svg v-if="item.icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="15" height="15" v-html="item.icon"></svg>
        {{ item.label }}
      </button>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface MenuItem { action: string; label: string; icon?: string; danger?: boolean }
interface Position { x: number; y: number }

const visible = ref(false)
const pos = ref<Position>({ x: 0, y: 0 })
const items = ref<MenuItem[]>([])
let actionCallback: ((action: string) => void) | null = null

const iconPaths: Record<string, string> = {
  copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  quote: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  retry: '<polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>',
  edit: '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
  delete: '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  pin: '<line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24z"/>',
  archive: '<path d="M21 8v13H3V8"/><path d="M1 3h22v5H1z"/><line x1="10" y1="12" x2="14" y2="12"/>',
}

function open(menuItems: MenuItem[], position: Position, cb: (action: string) => void) {
  items.value = menuItems.map(item => ({ ...item, icon: item.icon ? iconPaths[item.icon] || '' : '' }))
  pos.value = position
  visible.value = true
  actionCallback = cb
}

function close() {
  visible.value = false
  actionCallback = null
}

function handleAction(action: string) {
  actionCallback?.(action)
  close()
}

defineExpose({ open, close })
</script>

<style scoped>
.context-menu-overlay { position: fixed; inset: 0; z-index: 900; }
.context-menu {
  position: fixed; z-index: 901; min-width: 160px;
  background: var(--bg-elevated); backdrop-filter: blur(24px);
  border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  padding: 4px; box-shadow: var(--shadow-md);
}
.context-item {
  display: flex; align-items: center; gap: 10px; width: 100%;
  padding: 9px 14px; border: none; background: none; border-radius: var(--radius-xs);
  font-size: 13px; color: var(--text-secondary); cursor: pointer; text-align: left; font-family: inherit;
}
.context-item:hover { background: var(--bg-hover); color: var(--text-primary); }
.context-item.danger:hover { background: rgba(248,113,113,.10); color: var(--coral); }
</style>
