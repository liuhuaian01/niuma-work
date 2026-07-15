<template>
  <div class="messages-area">
    <div class="messages-inner" ref="messagesInnerRef">
      <!-- Compressed Banner — 与气泡同级，在消息流内部 -->
      <div v-if="compressedBanner" class="compressed-banner">
        <div class="compressed-banner-header" role="button" tabindex="0" @click="compressedExpanded = !compressedExpanded">
          <div class="compressed-banner-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          </div>
          <div class="compressed-banner-info">
            <div class="compressed-banner-title">已自动压缩 <span>{{ compressedBanner.count }}</span> 条历史消息</div>
            <div class="compressed-banner-sub">节省约 {{ compressedBanner.ratio }}% 上下文窗口 · 点击展开摘要</div>
          </div>
          <svg class="compressed-banner-arrow" :class="{ expanded: compressedExpanded }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
        </div>
        <div class="compressed-banner-body" :class="{ open: compressedExpanded }">
          <div class="compressed-summary-text">
            <strong>对话摘要：</strong>{{ compressedBanner.summary }}
          </div>
          <div class="compressed-keywords">
            <span v-for="kw in compressedBanner.keywords" :key="kw" class="compressed-keyword">{{ kw }}</span>
          </div>
        </div>
        <div class="compressed-banner-footer">
          <span class="compressed-stat">压缩前 <b>{{ compressedBanner.count }} 条</b> · 约 <b>~{{ compressedBanner.afterTokens }}</b> tokens</span>
          <button class="compressed-expand-btn" @click.stop="$emit('expandCompressed')">查看原始记录</button>
        </div>
      </div>

      <template v-for="(msg, idx) in messages" :key="idx">
        <!-- Context Compression Indicator -->
        <div v-if="msg.compression" class="msg-compression-bar">
          <div class="compression-dot"></div>
          <span>上下文已压缩 · 节省 {{ msg.compression.saved }} tokens</span>
          <span class="compression-pct">{{ msg.compression.ratio }}%</span>
        </div>

        <div class="message" :class="[msg.role, { thinking: msg.thinking, streaming: msg.streaming }]" @contextmenu.prevent="$emit('contextmenu', $event, msg, idx)">
          <div class="msg-avatar" :style="msg.avatarStyle">{{ msg.avatar }}</div>
          <div class="msg-content">
            <div class="msg-meta">
              <span class="msg-name">{{ msg.name }}</span>
              <span class="msg-time">{{ msg.time }}</span>
            </div>

            <!-- Thinking Block (expandable) -->
            <div v-if="msg.thinking" class="msg-thinking-block" @click="msg.thinkingExpanded = !msg.thinkingExpanded">
              <div class="thinking-header">
                <div class="thinking-spinner"><span></span><span></span><span></span></div>
                <span class="thinking-label">{{ msg.thinkingText || '思考中...' }}</span>
                <svg class="thinking-chevron" :class="{ expanded: msg.thinkingExpanded }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polyline points="6 9 12 15 18 9"/></svg>
              </div>
              <div v-if="msg.thinkingExpanded && msg.thinkingContent" class="thinking-body">
                {{ msg.thinkingContent }}
              </div>
            </div>

            <!-- Tool Calls -->
            <div v-if="msg.toolCalls && msg.toolCalls.length" class="msg-toolcalls">
              <div v-for="(tc, tci) in msg.toolCalls" :key="tci" class="toolcall-pill" :class="tc.status">
                <span class="toolcall-icon">
                  <svg v-if="tc.status === 'running'" viewBox="0 0 16 16" class="toolcall-spinner"><circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="28" stroke-dashoffset="10"/></svg>
                  <svg v-else-if="tc.status === 'done'" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="4 8 7 11 12 5"/></svg>
                  <svg v-else viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="8" cy="8" r="5"/><line x1="5" y1="5" x2="11" y2="11"/><line x1="11" y1="5" x2="5" y2="11"/></svg>
                </span>
                <span class="toolcall-name">{{ tc.name }}</span>
                <span v-if="tc.args" class="toolcall-args">{{ tc.args }}</span>
              </div>
            </div>

            <!-- Message Content -->
            <div class="msg-bubble" :class="{ 'streaming-text': msg.streaming }">
              <div v-if="msg.role === 'ai'" class="msg-content-html" v-html="sanitize(msg.content)"></div>
              <div v-else class="msg-content-html" v-html="sanitize(msg.content)"></div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, onMounted, onBeforeUnmount } from 'vue'
import DOMPurify from 'dompurify'

export interface ToolCall {
  name: string
  args?: string
  status: 'running' | 'done' | 'error'
}

export interface CompressionEvent {
  saved: number
  ratio: number
}

export interface ChatMessage {
  role: 'user' | 'ai'
  avatar: string
  avatarStyle: string
  name: string
  time: string
  content: string
  thinking?: boolean
  thinkingText?: string
  thinkingContent?: string
  thinkingExpanded?: boolean
  streaming?: boolean
  toolCalls?: ToolCall[]
  compression?: CompressionEvent
}

export interface CompressedBannerData {
  count: number
  ratio: number
  summary: string
  keywords: string[]
  afterTokens: string
}

const props = defineProps<{
  messages: ChatMessage[]
  compressedBanner?: CompressedBannerData | null
}>()

const emit = defineEmits<{
  contextmenu: [e: MouseEvent, msg: ChatMessage, idx: number]
  expandCompressed: []
}>()

const compressedExpanded = ref(false)
const messagesInnerRef = ref<HTMLElement | null>(null)

// Auto-scroll + paste/click hooks
watch(() => props.messages.length, scrollToBottom)
watch(() => {
  const msgs = props.messages
  if (msgs.length > 0) {
    return msgs[msgs.length - 1].streaming && (msgs[msgs.length - 1] as any).content?.length
  }
  return null
}, () => {
  const last = props.messages[props.messages.length - 1]
  if (last && last.streaming) scrollToBottom()
})

function scrollToBottom() {
  nextTick(() => {
    if (messagesInnerRef.value) {
      const el = messagesInnerRef.value.parentElement
      if (el) el.scrollTop = el.scrollHeight
    }
  })
}

// Initialize copy buttons for code blocks after DOM updates
let codeClickHandler: ((e: Event) => void) | null = null;

onMounted(() => {
  codeClickHandler = (e: Event) => {
    const btn = (e.target as HTMLElement).closest('.code-copy-btn') as HTMLElement
    if (!btn) return
    const pre = btn.closest('.msg-content-html')?.querySelector('pre')
    if (pre) {
      navigator.clipboard.writeText(pre.textContent || '').then(() => {
        btn.classList.add('copied')
        btn.textContent = 'Copied!'
        setTimeout(() => { btn.classList.remove('copied'); btn.textContent = 'Copy' }, 2000)
      })
    }
  }
  document.addEventListener('click', codeClickHandler)
})

onBeforeUnmount(() => {
  if (codeClickHandler) {
    document.removeEventListener('click', codeClickHandler)
  }
})

// DOMPurify sanitize with code block enhancement
function sanitize(html: string): string {
  let safe = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'code', 'pre', 'br', 'p', 'ul', 'ol', 'li', 'blockquote', 'hr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'span', 'div'],
    ALLOWED_ATTR: ['href', 'target', 'rel', 'class', 'style'],
  })
  // Add copy button to code blocks
  safe = safe.replace(/<pre>/g, '<div class="code-block-wrapper"><button class="code-copy-btn" title="Copy code">Copy</button><pre>')
  safe = safe.replace(/<\/pre>/g, '</pre></div>')
  return safe
}
</script>