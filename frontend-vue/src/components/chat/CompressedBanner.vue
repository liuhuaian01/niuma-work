<template>
  <div class="compressed-banner">
    <div class="compressed-banner-header" role="button" tabindex="0" @click="expanded = !expanded">
      <div class="compressed-banner-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      </div>
      <div class="compressed-banner-info">
        <div class="compressed-banner-title">已自动压缩 <span>{{ count }}</span> 条历史消息</div>
        <div class="compressed-banner-sub">节省约 {{ ratio }}% 上下文窗口 · 点击展开摘要</div>
      </div>
      <svg class="compressed-banner-arrow" :class="{ expanded }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
    </div>
    <div class="compressed-banner-body" :class="{ open: expanded }">
      <div class="compressed-summary-text">
        <strong style="color:var(--text-primary)">对话摘要：</strong>{{ summary }}
      </div>
      <div class="compressed-keywords">
        <span v-for="kw in keywords" :key="kw" class="compressed-keyword">{{ kw }}</span>
      </div>
    </div>
    <div class="compressed-banner-footer">
      <span class="compressed-stat">压缩前 <b>{{ count }} 条</b> · 约 <b>{{ beforeTokens.toLocaleString() }}</b> tokens → 压缩后 <b>~{{ afterTokens.toLocaleString() }}</b> tokens</span>
      <button class="compressed-expand-btn" @click.stop="$emit('expand')">查看原始记录</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  count?: number
  ratio?: number
  summary?: string
  keywords?: string[]
}>()

defineEmits<{
  expand: []
}>()

const expanded = ref(false)
const beforeTokens = computed(() => Math.round((props.count || 42) * 297))
const afterTokens = computed(() => Math.round(beforeTokens.value * (1 - (props.ratio || 68) / 100)))
</script>
