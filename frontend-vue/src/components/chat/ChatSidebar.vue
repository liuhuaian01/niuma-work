<template>
  <aside class="chat-sidebar" aria-label="对话列表">
    <div class="sidebar-header">
      <div class="sidebar-title">
        <span>对话</span>
        <div style="position: relative;">
          <button class="sidebar-create-btn" title="新建" data-tooltip="新建" aria-label="新建" @click="toggleCreate">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
          <div class="sidebar-create-menu" role="menu" aria-label="新建菜单" :class="{ open: createOpen }">
            <div class="sidebar-create-menu-header">新建</div>
            <button class="sidebar-create-item" @click="createOpen = false; $emit('create', 'agent')">
              <span class="sidebar-create-item-icon" style="background:linear-gradient(135deg,#6391ED,#06B6D4)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 4-7 8-7s8 3 8 7"/></svg>
              </span>
              <div class="sidebar-create-item-body">
                <div class="sidebar-create-item-title">新建 Agent</div>
                <div class="sidebar-create-item-desc">创建独立智能体，配置专属模型与技能</div>
              </div>
            </button>
            <button class="sidebar-create-item" @click="createOpen = false; $emit('create', 'project')">
              <span class="sidebar-create-item-icon" style="background:linear-gradient(135deg,#F59E0B,#EF4444)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="9" x2="15" y2="9"/><line x1="9" y1="13" x2="13" y2="13"/></svg>
              </span>
              <div class="sidebar-create-item-body">
                <div class="sidebar-create-item-title">新建项目</div>
                <div class="sidebar-create-item-desc">创建新项目，组织团队协作与知识库</div>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
    <div class="chat-list">
      <div
        v-for="conv in conversations"
        :key="conv.id"
        class="chat-item"
        :class="[conv.type === 'platform' ? 'agent-platform-item' : '', { active: activeConv === conv.id }]"
        @click="$emit('select', conv.id)"
      >
        <div class="chat-item-avatar" :style="conv.avatarStyle">{{ conv.avatar }}</div>
        <div class="chat-item-info">
          <div class="chat-item-name">{{ conv.name }}</div>
          <div class="chat-item-preview">{{ conv.preview }}</div>
        </div>
        <div class="chat-item-meta">
          <span class="chat-item-time" :style="conv.timeStyle">{{ conv.time }}</span>
          <span v-if="conv.badge" class="chat-item-badge" :style="conv.badgeStyle"></span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'

export interface Conversation {
  id: string
  type: 'platform' | 'group' | 'individual'
  avatar: string
  avatarStyle: string
  name: string
  preview: string
  time: string
  timeStyle?: string
  badge?: boolean
  badgeStyle?: string
}

defineProps<{
  activeConv: string
  conversations: Conversation[]
}>()

defineEmits<{
  select: [id: string]
  create: [type: 'agent' | 'project']
}>()

const createOpen = ref(false)
function toggleCreate() { createOpen.value = !createOpen.value }
</script>
