<template>
  <div class="toast-container" aria-live="polite">
    <TransitionGroup name="toast">
      <div v-for="t in toasts" :key="t.id" class="toast" :class="t.type">
        <svg v-if="t.type === 'success'" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2" width="16" height="16"><polyline points="20 6 9 17 4 12"/></svg>
        <svg v-else-if="t.type === 'error'" viewBox="0 0 24 24" fill="none" stroke="var(--coral)" stroke-width="2" width="16" height="16"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/></svg>
        <svg v-else-if="t.type === 'warning'" viewBox="0 0 24 24" fill="none" stroke="var(--amber)" stroke-width="2" width="16" height="16"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        <span>{{ t.msg }}</span>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Toast { id: number; msg: string; type: string }
const toasts = ref<Toast[]>([])
let id = 0

defineExpose({
  show(msg: string, type = 'info', duration = 3000) {
    const t: Toast = { id: ++id, msg, type }
    toasts.value.push(t)
    setTimeout(() => { toasts.value = toasts.value.filter(x => x.id !== t.id) }, duration)
  }
})
</script>

<style scoped>
.toast-container { position: fixed; top: 16px; right: 16px; z-index: var(--z-toast); display: flex; flex-direction: column; gap: 8px; }
.toast { display: flex; align-items: center; gap: 10px; padding: 12px 20px; border-radius: var(--radius-md); background: var(--bg-glass-h, var(--bg-elevated)); backdrop-filter: blur(24px); border: 1px solid var(--border-subtle); font-size: 13px; color: var(--text-primary); box-shadow: var(--shadow-md); max-width: 380px; }
.toast.success { border-color: rgba(52,211,153,.20); }
.toast.error { border-color: rgba(248,113,113,.20); }
.toast.warning { border-color: rgba(251,191,36,.20); }
.toast-enter-active { transition: all .3s var(--ease-spring); }
.toast-leave-active { transition: all .2s ease-in; }
.toast-enter-from { opacity: 0; transform: translateX(40px); }
.toast-leave-to { opacity: 0; transform: translateX(-20px); }
</style>
