<template>
  <div class="skeleton" :class="[variant]" :style="{ width, height }">
    <div class="skeleton-shimmer"></div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  variant?: 'text' | 'circle' | 'card'
  width?: string
  height?: string
}>(), {
  variant: 'text',
  width: '100%',
  height: '16px'
})
</script>

<style scoped>
.skeleton { position: relative; overflow: hidden; border-radius: var(--radius-sm); background: var(--bg-overlay); }
.skeleton.text { height: 14px; border-radius: 4px; }
.skeleton.circle { border-radius: 50%; }
.skeleton.card { border-radius: var(--radius-md); min-height: 120px; }
.skeleton-shimmer {
  position: absolute; inset: 0;
  background: linear-gradient(90deg, transparent 25%, var(--bg-hover) 50%, transparent 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
@keyframes shimmer { 0% { background-position: 200% 0 } 100% { background-position: -200% 0 } }
</style>
