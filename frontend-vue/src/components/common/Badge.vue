<template>
  <span class="badge" :class="type">{{ text }}</span>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ text: string; type?: 'brand' | 'success' | 'warning' | 'danger' | 'info' | 'purple' | 'muted' }>(), { type: 'brand' })
</script>

<style scoped>
.badge { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: var(--radius-xs); font-size: 11px; font-weight: 550; letter-spacing: .02em; }
.badge.brand { background: var(--brand-muted); color: var(--brand); }
.badge.success { background: rgba(52,211,153,.10); color: var(--green); }
.badge.warning { background: rgba(251,191,36,.10); color: var(--amber); }
.badge.danger { background: rgba(248,113,113,.10); color: var(--coral); }
.badge.info { background: rgba(34,211,238,.10); color: var(--cyan); }
.badge.purple { background: rgba(139,92,246,.10); color: var(--purple); }
.badge.muted { background: var(--bg-overlay); color: var(--text-tertiary); }
</style>
