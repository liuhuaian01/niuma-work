<template>
  <div class="agent-info-popup" :class="{ open: visible }" @click.stop>
    <!-- Avatar + Name + Status -->
    <div class="agent-popup-avatar-section">
      <div class="agent-popup-avatar-big">
        H
        <div class="avatar-hover-mask" title="Agent设置" @click="$emit('settings')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
        </div>
      </div>
      <div class="agent-popup-name">{{ agentName }}</div>
      <div class="agent-popup-status-row">
        <span class="agent-popup-status-dot"></span>
        {{ agentStatus }}
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="agent-popup-btn-row">
      <button class="agent-popup-action-btn primary" @click="$emit('focus-input')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        发送消息
      </button>
      <button class="agent-popup-action-btn" @click="$emit('new-project')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        新建项目
      </button>
    </div>

    <!-- Skills -->
    <div class="agent-popup-section-label">拥有技能</div>
    <div class="agent-popup-skills-grid">
      <span v-for="skill in skills" :key="skill" class="agent-popup-skill-tag">{{ skill }}</span>
      <span class="agent-popup-skill-tag more" @click="$emit('toast', '全部技能：共12项', 'info')">全部 <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg></span>
    </div>

    <!-- Channels -->
    <div class="agent-popup-section-label">连接渠道</div>
    <div class="agent-popup-channels-row">
      <span class="agent-popup-channel">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
        飞书
      </span>
      <span class="agent-popup-channel">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
        Notion
      </span>
      <span class="agent-popup-channel add" title="添加渠道" @click="$emit('toast', '渠道管理开发中', 'info')">+</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  visible: boolean
  agentName?: string
  agentStatus?: string
  skills?: string[]
}>()

defineEmits<{
  settings: []
  'focus-input': []
  'new-project': []
  toast: [msg: string, type?: string]
}>()
</script>
