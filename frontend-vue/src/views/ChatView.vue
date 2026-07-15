<template>

  <ChatSidebar
    :active-conv="activeConv"
    :conversations="conversations"
    @select="selectConv"
    @create="handleCreate"
  />
  <main class="chat-area" aria-label="Chat Area" @click="closeMenusOnClick">
    <input ref="hiddenFileInput" type="file" hidden @change="onFileInputChange" />
    <input ref="hiddenFolderInput" type="file" webkitdirectory hidden @change="onFolderInputChange" />
    <div class="chat-header">
      <div class="chat-header-agent-area" style="position:relative;" @click.stop="agentPopupOpen = !agentPopupOpen">
        <div class="chat-header-avatar" role="button" tabindex="0">{{ activeConvAvatar }}</div>
        <div class="chat-header-info">
          <div class="chat-header-name">{{ activeConvName }}</div>
          <div class="chat-header-status"><span class="dot"></span>{{ activeConvStatus }}</div>
        </div>
        <AgentPopup
          :visible="agentPopupOpen"
          :agent-name="activeConvName"
          :agent-status="'在线 · 赛博工坊主控'"
          :skills="['全栈开发','架构设计','代码审查','任务编排','技术调研']"
          @settings="agentPopupOpen = false; openSidePanel('settings')"
          @focus-input="agentPopupOpen = false; document.querySelector('.input-textarea')?.focus()"
          @new-project="agentPopupOpen = false; showToast('已新建项目','success')"
          @toast="(m,t) => showToast(m,t)"
        />
      </div>
      <div class="chat-header-actions">
        <button class="header-action-btn" title="文件" data-tooltip="文件" @click="openSidePanel('files')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        </button>
        <button class="header-action-btn" title="日历" data-tooltip="日历" @click="openSidePanel('calendar')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        </button>
        <button class="header-action-btn" title="设置" data-tooltip="设置" @click="openSettingsBasedOnConv">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        </button>
        <div class="more-menu-trigger">
          <button class="header-action-btn" title="更多" data-tooltip="更多" @click.stop="toggleMenu('moreMenu')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="5" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="12" cy="19" r="1.6"/></svg>
          </button>
          <div class="more-menu-float" :class="{ open: openMenu === 'moreMenu' }" @click.stop>
            <button class="more-menu-item" @click="showToast('分享','info'); openMenu = null"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>分享</button>
            <button class="more-menu-item" @click="openSidePanel('search-history'); openMenu = null"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>搜索历史对话</button>
            <button class="more-menu-item" @click="openSidePanel('bg-tasks'); openMenu = null"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>后台任务</button>
          </div>
        </div>
      </div>
    </div>
    <div class="chat-search-panel" :class="{ open: searchOpen }">
      <input type="text" class="chat-search-input" v-model="searchQuery" placeholder="Search..." @keydown.enter="searchMessages" />
      <span class="chat-search-count" v-if="searchResults.total">{{ searchResults.current }}/{{ searchResults.total }}</span>
      <button class="chat-search-close" @click="searchOpen = false; searchQuery = ''"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
    </div>
    <ChatMessages :messages="convMessages[activeConv] || []" :compressed-banner="compressedBannerData" @contextmenu="onMsgContextMenu" @expand-compressed="showToast('查看原始记录','info')" />
    <ChatInput
      :selected-model="selectedModel"
      :processing-active="processingActive"
      :processing-label="processingLabel"
      :processing-timer="processingTimer"
      :show-suggestions="showSuggestionsFlag"
      :suggestions="suggestions"
      :context-pct="contextPct"
      @send="sendMessage"
      @stop="stopProcessing"
      @apply-suggestion="applySuggestion"
      @add-skill="openSidePanel('settings')"
      @add-file="onAddFile"
      @add-folder="onAddFolder"
      @toast="showToast"
      @select-model="(id) => selectedModel = id"
    />
  </main>
  <div class="resize-handle" :class="{ active: sidePanelOpen }" @mousedown="startResize" ref="resizeHandle"></div>
  <SidePanel v-model="sidePanelOpen" :panel-type="sidePanelType" @toast="showToast" />
  <ContextMenu ref="contextMenuRef" />
  <NewAgentModal v-model="showNewAgentModal" @create="onCreateAgent" />
  <NewProjectModal v-model="showNewProjectModal" :agents="availableAgents" @create="onCreateProject" @open-agent-modal="showNewProjectModal = false; showNewAgentModal = true" />
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue';
import { useRouter } from 'vue-router';
import ChatSidebar, { type Conversation } from '@/components/chat/ChatSidebar.vue';
import ChatMessages, { type ChatMessage } from '@/components/chat/ChatMessages.vue';
import ChatInput from '@/components/chat/ChatInput.vue';
import SidePanel from '@/components/chat/SidePanel.vue';
import AgentPopup from '@/components/chat/AgentPopup.vue';
import NewAgentModal from '@/components/chat/NewAgentModal.vue';
import NewProjectModal from '@/components/chat/NewProjectModal.vue';
import ContextMenu from '@/components/common/ContextMenu.vue';
import { useToast } from '@/composables/useToast';
import { chatApi } from '@/services/api';
import DOMPurify from 'dompurify';

const { showToast } = useToast();
const router = useRouter();
const contextMenuRef = ref<InstanceType<typeof ContextMenu> | null>(null);

function makeMsg(role: 'user' | 'ai', content: string, extra: Partial<ChatMessage> = {}): ChatMessage {
  const now = new Date();
  const timeStr = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');
  const avatars: Record<string, { char: string; style: string; name: string }> = {
    ai: { char: 'H', style: 'background:linear-gradient(135deg,#4DA8F0,#8B5CF6)', name: 'Hermes' },
    user: { char: '刘', style: 'background:linear-gradient(135deg,#F87171,#FBBF24)', name: '刘淮安' },
  };
  const a = avatars[role] || avatars.ai;
  return {
    role, avatar: a.char, avatarStyle: a.style, name: a.name, time: timeStr,
    content, thinking: false, streaming: false, ...extra,
  };
}

const activeConv = ref('agent-hermes');
const agentPopupOpen = ref(false);
const compressedBannerData = computed(() => {
  const count = 42
  const ratio = 68
  const beforeTokens = count * 297
  const afterTokens = Math.round(beforeTokens * (1 - ratio / 100))
  return {
    count, ratio,
    summary: '用户正在开发\'超级牛马\'AI工作站前端工程，已完成项目初始化和技术栈确认（Vue3 + Vite + TS / FastAPI）。',
    keywords: ['vue3', 'vite', 'typescript', 'fastapi', '前端工程化'],
    afterTokens: '~' + afterTokens.toLocaleString(),
  }
});
const sidePanelOpen = ref(false);
const showNewAgentModal = ref(false);
const showNewProjectModal = ref(false);
const availableAgents = ref([
  { id: 'agent-hermes', name: '超级牛马', avatar: '🤖', color: 'linear-gradient(135deg,#6391ED,#5ED6C0,#8B5CF6)', role: '赛博工坊 · 主智能体 v2.4' },
  { id: 'agent-小章鱼', name: '小章鱼', avatar: '🧵', color: 'linear-gradient(135deg,#F59E0B,#EF4444)', role: '家纺研究员 · 网文工具开发' },
]);
const sidePanelType = ref('settings');
const openMenu = ref<string | null>(null);
const selectedModel = ref('Qwen3.7-Max');
const processingActive = ref(false);
const processingLabel = ref('');
const processingTimer = ref('0.0s');
const showSuggestionsFlag = ref(false);
const suggestions = ref<string[]>([]);
const contextPct = ref(0);
const activeStreamId = ref<string | null>(null);
const streamAbort = ref<AbortController | null>(null);
let processingTimerInterval: ReturnType<typeof setInterval> | null = null;
let processingStartTime = 0;
const searchOpen = ref(false);
const searchQuery = ref('');
const searchResults = ref({ total: 0, current: 0 });

const conversations = ref<Conversation[]>([
  { id: 'agent-hermes', type: 'platform', avatar: '牛', avatarStyle: 'background:linear-gradient(135deg,#6391ED,#5ED6C0,#8B5CF6);color:#fff;font-weight:800;font-size:14px;box-shadow:0 4px 12px rgba(99,145,237,.25)', name: '超级牛马', preview: '平台助手 · 运行中', time: '运行中', timeStyle: 'color:var(--green);font-size:10px', badge: true, badgeStyle: 'background:var(--green);box-shadow:0 0 8px rgba(52,211,153,.40)' },
  { id: 'conv-1', type: 'group', avatar: '赛', avatarStyle: 'background:linear-gradient(135deg,#6391ED,#5ED6C0,#8B5CF6);color:#fff;font-weight:800;font-size:14px', name: '赛博工坊', preview: 'Hermes · 数据分析 · 创意写作 · 项目管理', time: '刚刚', badge: true, badgeStyle: 'background:var(--green);box-shadow:0 0 6px var(--green)' },
  { id: 'conv-2', type: 'group', avatar: '用', avatarStyle: 'background:linear-gradient(135deg,#06B6D4,#3B82F6);color:#fff;font-weight:800;font-size:14px', name: '用户中心 v2', preview: '架构设计 · 翻译助手', time: '10:32' },
  { id: 'conv-3', type: 'group', avatar: '技', avatarStyle: 'background:linear-gradient(135deg,#F59E0B,#EF4444);color:#fff;font-weight:800;font-size:14px', name: '技术重构', preview: '代码助手 · 技术调研', time: '昨天' },
  { id: 'conv-4', type: 'individual', avatar: '章', avatarStyle: 'background:linear-gradient(135deg,#52C47A,#34D399);color:#fff;font-weight:800;font-size:14px', name: '小章鱼', preview: '家纺知识库更新完成', time: '昨天' },
  { id: 'conv-5', type: 'individual', avatar: '刘', avatarStyle: 'background:linear-gradient(135deg,#EC4899,#8B5CF6);color:#fff;font-weight:800;font-size:14px', name: '刘淮安', preview: '新书大纲已生成', time: '3天前' },
]);

const convMessages = reactive<Record<string, ChatMessage[]>>({
  'agent-hermes': [
    makeMsg('ai', '你好！我是 Hermes，你的 AI 助手。有什么可以帮你的？'),
    makeMsg('user', '帮我分析一下这个项目'),
    makeMsg('ai', '好的！我看到你正在开发一个微供应电商平台。让我来帮你分析。', { toolCalls: [{ name: '读取项目文件', status: 'done' as const }] }),
  ],
  'conv-1': [makeMsg('ai', '你好！赛博工坊已就绪。')],
  'conv-2': [makeMsg('ai', '用户中心 v2 已启动。')],
  'conv-3': [makeMsg('ai', '技术重构对话已准备好。')],
});

const activeConvName = computed(() => conversations.value.find(x => x.id === activeConv.value)?.name || 'Chat');
const activeConvAvatar = computed(() => conversations.value.find(x => x.id === activeConv.value)?.avatar || 'H');
const activeConvStatus = computed(() => {
  const c = conversations.value.find(x => x.id === activeConv.value);
  return c?.type === 'platform' ? '在线' : (c?.badge ? '活跃' : '');
});

function handleCreate(type: 'agent' | 'project') {
  if (type === 'agent') {
    showNewAgentModal.value = true
  } else {
    showNewProjectModal.value = true
  }
}
function onCreateAgent(data: any) {
  const id = 'agent-' + Date.now()
  // Add to available agents pool for project creation
  availableAgents.value.push({
    id, name: data.name, avatar: data.avatar, color: data.color, role: data.role,
  })
  conversations.value.push({
    id, type: 'platform', avatar: data.avatar,
    avatarStyle: `background:${data.color};color:#fff;font-weight:800;font-size:14px`,
    name: data.name, preview: data.role, time: '刚刚',
  })
  convMessages[id] = [makeMsg('ai', `你好！我是 ${data.name}，${data.role}。有什么可以帮你的？`)]
  activeConv.value = id
  showToast(`已创建 Agent: ${data.name}`, 'success')
}
function onCreateProject(data: any) {
  const id = 'proj-' + Date.now()
  const agentNames = data.agents.map((aid: string) => availableAgents.value.find(a => a.id === aid)?.name || aid).join(', ')
  conversations.value.push({
    id, type: 'group', avatar: data.name.charAt(0),
    avatarStyle: 'background:linear-gradient(135deg,#A78BFA,#EC4899);color:#fff;font-weight:800;font-size:14px',
    name: data.name, preview: `${data.template ? `模板: ${tplName(data.template)}` : '空白项目'} · ${data.agents.length}个Agent`,
    time: '刚刚',
  })
  convMessages[id] = [makeMsg('ai', `项目「${data.name}」已创建。协作Agent: ${agentNames}。开始协作吧。`)]
  activeConv.value = id
  showToast(`已创建项目: ${data.name}`, 'success')
}
function tplName(id: string) {
  const map: Record<string, string> = { product: '产品研发', research: '市场调研', content: '内容运营', knowledge: '知识库', delivery: '项目交付', blank: '空白项目' }
  return map[id] || id
}
function selectConv(id: string) { activeConv.value = id; if (!convMessages[id]) convMessages[id] = [makeMsg('ai', 'Started.')]; }

async function sendMessage(text: string) {
  const convId = activeConv.value;
  if (!convMessages[convId]) convMessages[convId] = [];
  convMessages[convId].push(makeMsg('user', sanitizeHtml(text)));
  const aiMsg = makeMsg('ai', '', { thinking: true, streaming: true, toolCalls: [] });
  convMessages[convId].push(aiMsg);
  processingActive.value = true; processingLabel.value = 'Thinking...'; processingStartTime = Date.now();
  processingTimerInterval = setInterval(() => { processingTimer.value = ((Date.now() - processingStartTime) / 1000).toFixed(1) + 's'; }, 100);
  try {
    const abort = new AbortController(); streamAbort.value = abort;
    const { streamId } = await chatApi.sendMessage(text, { signal: abort.signal });
    activeStreamId.value = streamId;
    const es = chatApi.connectStream(streamId, {
      onToken(t: string) { aiMsg.content += sanitizeHtml(t); },
      onToolCall(t: { name: string; args?: string }) { if (!aiMsg.toolCalls) aiMsg.toolCalls = []; aiMsg.toolCalls.push({ name: t.name, args: t.args, status: 'running' }); },
      onToolResult(i: number) { if (aiMsg.toolCalls?.[i]) aiMsg.toolCalls[i].status = 'done'; },
      onDone() { es.close(); finishStreaming(); generateSuggestions(); },
      onError(e: Error) { es.close(); aiMsg.content += '\n[Error: ' + e.message + ']'; showToast('Stream error', 'warning'); finishStreaming(); },
    });
    abort.signal.addEventListener('abort', () => { es.close(); finishStreaming(); });
  } catch (err) {
    finishStreaming(); aiMsg.content = sanitizeHtml('[API unavailable] ' + (err instanceof Error ? err.message : ''));
    aiMsg.thinking = false; aiMsg.streaming = false; showToast('Connection failed', 'warning'); generateSuggestions();
  }
}
function finishStreaming() {
  processingActive.value = false; if (processingTimerInterval) { clearInterval(processingTimerInterval); processingTimerInterval = null; }
  activeStreamId.value = null; streamAbort.value = null;
  const msgs = convMessages[activeConv.value]; const ai = msgs?.[msgs.length - 1];
  if (ai?.role === 'ai') { ai.thinking = false; ai.streaming = false; }
}
function stopProcessing() { if (activeStreamId.value) chatApi.stopStream(activeStreamId.value).catch(() => {}); streamAbort.value?.abort(); finishStreaming(); }
function generateSuggestions() { suggestions.value = ['Explain in more detail?','What are next steps?','Show code changes','How does this affect performance?'].sort(() => Math.random() - 0.5).slice(0,3); showSuggestionsFlag.value = true; }
function applySuggestion(text: string) { showSuggestionsFlag.value = false; sendMessage(text); }
function openSidePanel(type: string) { sidePanelType.value = type; sidePanelOpen.value = true; }
function toggleMenu(name: string) { openMenu.value = openMenu.value === name ? null : name; }
function closeMenusOnClick() { openMenu.value = null; }
function openSettingsBasedOnConv() { openSidePanel(activeConv.value.startsWith('conv-') ? 'project-settings' : 'settings'); }
function onAddFile(file: File) { showToast('已添加文件: ' + file.name, 'success'); }
function onAddFolder(files: File[]) { showToast('已添加文件夹: ' + files.length + ' 个文件', 'success'); contextPct.value = Math.min(100, contextPct.value + 5); }
function onFileInputChange(e: Event) { const inp = e.target as HTMLInputElement; if (inp.files?.length) onAddFile(inp.files[0]); inp.value = ''; }
function onFolderInputChange(e: Event) { const inp = e.target as HTMLInputElement; if (inp.files?.length) onAddFolder(Array.from(inp.files)); inp.value = ''; }
function onMsgContextMenu(e: MouseEvent, msg: ChatMessage, idx: number) {
  contextMenuRef.value?.open([
    { action: 'copy', label: 'Copy', icon: 'copy' },
    { action: 'retry', label: 'Retry', icon: 'retry' },
    { action: 'delete', label: 'Delete', icon: 'delete', danger: true },
  ], { x: e.clientX, y: e.clientY }, (action: string) => {
    if (action === 'copy') navigator.clipboard.writeText(msg.content).then(() => showToast('Copied','success'),()=>showToast('Copy failed','error'));
    else if (action === 'retry') { convMessages[activeConv.value]?.splice(idx, 1); sendMessage(msg.content); }
    else if (action === 'delete') { convMessages[activeConv.value]?.splice(idx, 1); showToast('Deleted','success'); }
  });
}
function searchMessages() {
  const q = searchQuery.value.toLowerCase(); const msgs = convMessages[activeConv.value] || [];
  const hits = msgs.filter(m => m.content?.toLowerCase().includes(q));
  searchResults.value = { total: hits.length, current: hits.length > 0 ? 1 : 0 };
  showToast(hits.length > 0 ? 'Found ' + hits.length + ' results' : 'No results', 'info');
}
function startResize(e: MouseEvent) {
  const startX = e.clientX; const panel = document.getElementById('sidePanel'); if (!panel) return;
  const startW = panel.offsetWidth;
  const onMove = (ev: MouseEvent) => { panel.style.width = Math.max(280, Math.min(480, startW - (ev.clientX - startX))) + 'px'; };
  const onUp = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); document.body.style.cursor = ''; document.body.style.userSelect = ''; };
  document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', onUp);
  document.body.style.cursor = 'col-resize'; document.body.style.userSelect = 'none'; e.preventDefault();
}
function sanitizeHtml(html: string): string {
  return DOMPurify.sanitize(html, { ALLOWED_TAGS: ['b','i','em','strong','a','code','pre','br','p','ul','ol','li','blockquote','hr','h1','h2','h3','h4','h5','h6'], ALLOWED_ATTR: ['href','target','rel','class','style'] });
}
</script>