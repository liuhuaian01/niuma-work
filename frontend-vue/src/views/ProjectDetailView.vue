<template>
<div class="page-view active" id="pageProjectDetail">
  <div class="project-detail-body">
    <!-- Embedded Project Chat View (shown when user sends message) -->
    <div class="project-chat-view" :class="{ active: inProjectChat }" v-show="inProjectChat">
      <div class="project-chat-header">
        <button class="project-chat-back" @click="goBackToProject" title="返回项目">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
        </button>
        <div class="project-chat-info">
          <div class="project-chat-name">项目对话</div>
          <div class="project-chat-subtitle">项目内对话 · 自动同步到动态</div>
        </div>
      </div>
      <div class="project-chat-messages" ref="chatMessagesRef">
        <div class="project-chat-empty" v-if="chatMessages.length === 0">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          <div class="project-chat-empty-title">项目对话</div>
          <div class="project-chat-empty-desc">在此与项目 AI 助手进行对话，所有消息将同步到项目动态。</div>
        </div>
        <div v-for="(msg, i) in chatMessages" :key="i" class="project-chat-msg">
          <div class="msg-avatar" :style="msg.role === 'ai' ? 'background:linear-gradient(135deg,#8B5CF6,#06B6D4)' : 'background:var(--brand-gradient)'">{{ msg.role === 'ai' ? 'AI' : 'U' }}</div>
          <div class="msg-content">
            <div class="msg-meta"><span class="msg-name">{{ msg.role === 'ai' ? 'Hermes' : '你' }}</span><span class="msg-time">刚刚</span></div>
            <div class="msg-text">{{ msg.text }}</div>
          </div>
        </div>
      </div>
      <div class="project-chat-input-wrap">
        <div class="input-area" style="padding:0;">
          <div class="input-card">
            <textarea class="input-textarea" v-model="chatDraft" placeholder="在项目中对话..." rows="1" aria-label="输入消息" maxlength="10000" @keydown.enter.exact.prevent="sendChatMessage"></textarea>
            <div class="input-toolbar">
              <div class="toolbar-spacer"></div>
              <button class="send-btn" :class="{ 'has-content': chatDraft.trim() }" title="发送" aria-label="发送消息" @click="sendChatMessage">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- Vertical Tab Nav (left) -->
    <div class="project-detail-tab-nav" v-show="!inProjectChat">
      <div class="project-detail-nav-header">
        <div class="project-name">{{ project.name }}</div>
        <div class="project-desc">项目对话与工作区</div>
      </div>
      <nav class="project-detail-tab-list">
        <button v-for="tab in tabs" :key="tab.id" class="project-detail-tab-nav-item" :class="{ active: activeTab === tab.id }" @click="switchTab(tab.id)">
          <svg class="tab-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" v-html="tab.iconPath"></svg>
          <span class="tab-label">{{ tab.label }}</span>
        </button>
      </nav>
    </div>

    <!-- Main Content (center) -->
    <div class="project-detail-main" v-show="!inProjectChat">
      <div class="project-detail-content">
        <!-- Activity Panel -->
        <div class="project-detail-panel" :class="{ active: activeTab === 'activity' }">
          <div class="panel-title-bar">动态</div>
          <div class="project-activity-list">
            <div class="project-activity-empty" v-if="!activities.length">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              <div class="project-activity-empty-title">暂无动态</div>
              <div class="project-activity-empty-desc">项目中的 Agent 操作、成员活动、系统事件将在此处展示。</div>
              <button class="project-activity-cta" @click="startFirstTask">发起第一个任务</button>
            </div>
            <div class="activity-card-list" v-else>
              <div v-for="(act, i) in activities" :key="i" class="activity-card">
                <div class="activity-avatar" :style="act.avatarStyle">{{ act.avatar }}</div>
                <div class="activity-body">
                  <div class="activity-title-row">
                    <span class="activity-name">{{ act.name }}</span>
                    <span class="activity-type-tag" :class="act.type">{{ act.typeLabel }}</span>
                  </div>
                  <div class="activity-desc" v-html="act.desc"></div>
                  <div class="activity-time">{{ act.time }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- SOP Panel -->
        <div class="project-detail-panel" :class="{ active: activeTab === 'sop' }">
          <div class="panel-title-bar">
            <span>SOP</span>
            <div class="panel-title-actions">
              <button class="panel-action-btn panel-action-btn-primary" @click="startSopConversation">
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><polygon points="11 2 2 13 10 13 9 18 18 7 10 7 11 2"/></svg> AI 构建
              </button>
              <button class="panel-action-btn" @click="sopAdding = true">
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><line x1="10" y1="4" x2="10" y2="16"/><line x1="4" y1="10" x2="16" y2="10"/></svg> 添加步骤
              </button>
            </div>
          </div>
          <div class="project-sop-steps">
            <!-- 内联添加步骤 -->
            <div v-if="sopAdding" class="sop-add-inline">
              <input class="sop-add-input" v-model="sopNewTitle" placeholder="步骤名称" @keydown.enter="confirmAddSopStep" />
              <input class="sop-add-input" v-model="sopNewDesc" placeholder="步骤描述（可选）" @keydown.enter="confirmAddSopStep" />
              <div class="sop-add-actions">
                <button class="np-btn np-btn-primary" @click="confirmAddSopStep">添加</button>
                <button class="np-btn np-btn-secondary" @click="cancelAddSopStep">取消</button>
              </div>
            </div>
            <!-- 步骤列表 -->
            <div v-for="(step, i) in sopSteps" :key="step.id" class="sop-step-row" :class="step.status">
              <div class="sop-step-num" :class="step.status">{{ i + 1 }}</div>
              <template v-if="sopEditingIndex === i">
                <div class="sop-step-body">
                  <input class="sop-step-edit-input" v-model="sopEditTitle" placeholder="步骤名称" />
                  <input class="sop-step-edit-input" v-model="sopEditDesc" placeholder="步骤描述" @keydown.enter="confirmEditSopStep" />
                  <div class="sop-add-actions" style="margin-top:6px">
                    <button class="np-btn np-btn-primary" @click="confirmEditSopStep">保存</button>
                    <button class="np-btn np-btn-secondary" @click="cancelEditSopStep">取消</button>
                  </div>
                </div>
              </template>
              <template v-else>
                <div class="sop-step-body">
                  <div class="sop-step-title">{{ step.title }}</div>
                  <div class="sop-step-desc">{{ step.desc }}</div>
                  <div class="sop-step-state" :class="step.status">{{ step.stateLabel }}</div>
                </div>
                <div class="sop-step-actions-inline">
                  <button class="sop-inline-btn" title="编辑" @click="openEditSopStep(i)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg></button>
                  <button class="sop-inline-btn danger" title="删除" @click="deleteSopStep(i)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="6" y1="12" x2="18" y2="12"/></svg></button>
                </div>
              </template>
            </div>
          </div>
        </div>

        <!-- Tasks Panel -->
        <div class="project-detail-panel" :class="{ active: activeTab === 'tasks' }">
          <div class="panel-title-bar">
            <span>后台任务</span>
            <div class="panel-title-actions">
              <button class="panel-action-btn" @click="addProjectTask">
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><line x1="10" y1="4" x2="10" y2="16"/><line x1="4" y1="10" x2="16" y2="10"/></svg> 新建任务
              </button>
            </div>
          </div>
          <div class="bg-tasks-list">
            <div v-for="task in bgTasks" :key="task.id" class="bg-task-card" :class="task.status">
              <div class="bg-task-icon" :class="task.status">
                <svg v-if="task.status === 'running'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                <svg v-else-if="task.status === 'completed'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="15" height="15"><polyline points="20 6 9 17 4 12"/></svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
              </div>
              <div class="bg-task-body">
                <div class="bg-task-name">{{ task.name }}</div>
                <div class="bg-task-desc">{{ task.desc }}</div>
              </div>
              <div class="bg-task-right">
                <div v-if="task.status === 'running'" class="bg-task-progress-bar"><div class="bg-task-progress-fill" :style="{ width: task.progress + '%' }"></div></div>
                <span v-if="task.status === 'completed'" class="bg-task-status completed">✓ 成功</span>
                <span v-else-if="task.status === 'failed'" class="bg-task-status failed">⚠ 失败</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Assets Panel -->
        <div class="project-detail-panel" :class="{ active: activeTab === 'assets' }">
          <div class="panel-title-bar">
            <span>资产</span>
            <div class="panel-title-actions">
              <button class="panel-action-btn" @click="newAssetFolder">
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M2 4l4-2 2 2h10a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4z"/><line x1="10" y1="8" x2="10" y2="16"/><line x1="6" y1="12" x2="14" y2="12"/></svg> 新建文件夹
              </button>
              <button class="panel-action-btn" @click="uploadAssetFile">
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M10 3v10"/><path d="M6 7l4-4 4 4"/><path d="M3 14v3a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-3"/></svg> 上传文件
              </button>
            </div>
          </div>
          <div class="asset-toolbar">
            <div class="asset-filter-group">
              <button v-for="f in assetFilters" :key="f.id" class="asset-filter-btn" :class="{ active: activeAssetFilter === f.id }" @click="activeAssetFilter = f.id">{{ f.label }}</button>
            </div>
            <div class="asset-search-box">
              <svg class="asset-search-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="7" cy="7" r="5"/><line x1="11" y1="11" x2="14" y2="14"/></svg>
              <input type="text" class="asset-search-input" placeholder="搜索文件..." v-model="assetSearch">
            </div>
          </div>
          <div class="asset-file-list">
            <div v-for="file in filteredAssets" :key="file.name" class="asset-file-item" :class="'asset-' + file.type" @click="openAssetFile(file)">
              <svg class="asset-file-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" v-html="fileIcon(file.type)"></svg>
              <div class="asset-file-info">
                <div class="asset-file-name">{{ file.name }}</div>
                <div class="asset-file-meta">{{ file.meta }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Bottom Input -->
      <div class="project-detail-input-wrap">
        <div class="input-area" style="width:100%;padding:0 0 4px 0;margin:0;max-width:100%">
          <div class="input-card">
            <textarea v-model="draft" class="input-textarea" placeholder="描述任务，/ 快捷调用，@ 添加上下文" rows="1" aria-label="输入消息" maxlength="10000" @keydown.enter.exact.prevent="sendFromProject"></textarea>
            <div class="input-toolbar">
              <div class="toolbar-spacer"></div>
              <button class="send-btn" :class="{ 'has-content': draft.trim() }" title="发送" aria-label="发送消息" @click="sendFromProject">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right: Config Panel -->
    <div class="project-detail-config" v-show="!inProjectChat">
      <div class="project-config-title">项目配置</div>

      <div class="project-config-section">
        <div class="project-config-header">
          <span>指令</span>
          <button class="project-config-add" @click="toggleInstructionEditor" title="编辑项目指令">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
        </div>
        <template v-if="instructionEditing">
          <textarea class="project-config-editor-input" v-model="instructionText" rows="3" placeholder="描述项目的需求、目标和约束条件..."></textarea>
          <div class="project-config-editor-actions">
            <button class="np-btn np-btn-secondary" @click="cancelInstructionEdit">取消</button>
            <button class="np-btn np-btn-primary" @click="saveInstruction">保存</button>
          </div>
        </template>
        <div v-else class="project-config-desc">{{ instructionText || '点击 + 添加项目指令' }}</div>
      </div>

      <div class="project-config-section">
        <div class="project-config-header">
          <span>连接器</span>
          <div style="position:relative">
            <button class="project-config-add" @click="toggleConfigDropdown('connector')" title="添加连接器">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            </button>
            <div class="config-dropdown" v-if="openDropdown === 'connector'">
              <button class="config-dropdown-item" @click="addConnector('GitHub MCP')">GitHub MCP</button>
              <button class="config-dropdown-item" @click="addConnector('飞书')">飞书</button>
              <button class="config-dropdown-item" @click="addConnector('Notion')">Notion</button>
            </div>
          </div>
        </div>
        <div class="project-config-desc">连接外部服务，扩展 AI 能力</div>
        <div class="project-config-items">
          <div v-for="(c, i) in connectors" :key="i" class="project-config-item">
            <span class="project-config-item-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/></svg></span>{{ c }}
            <button class="config-item-remove" @click="removeConnector(i)" title="移除"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" width="12" height="12"><line x1="6" y1="12" x2="18" y2="12"/></svg></button>
          </div>
        </div>
      </div>

      <div class="project-config-section">
        <div class="project-config-header">
          <span>专家</span>
          <div style="position:relative">
            <button class="project-config-add" @click="toggleConfigDropdown('expert')" title="添加专家">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            </button>
            <div class="config-dropdown" v-if="openDropdown === 'expert'">
              <button class="config-dropdown-item" @click="addExpert('Hermes')"><span class="project-config-item-icon agent-hermes" style="display:inline-flex;width:18px;height:18px;border-radius:5px;font-size:9px;color:#fff">H</span>Hermes</button>
              <button class="config-dropdown-item" @click="addExpert('超级牛马')"><span class="project-config-item-icon" style="display:inline-flex;width:18px;height:18px;border-radius:5px;background:linear-gradient(135deg,#6391ED,#5ED6C0);font-size:9px;color:#fff">牛</span>超级牛马</button>
            </div>
          </div>
        </div>
        <div class="project-config-desc">配置项目专家，为成员提供更专业的服务</div>
        <div class="project-config-items">
          <div v-for="(e, i) in experts" :key="i" class="project-config-item">
            <span class="project-config-item-icon agent-hermes">{{ e === 'Hermes' ? 'H' : '牛' }}</span>{{ e }}
            <button class="config-item-remove" @click="removeExpert(i)" title="移除"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" width="12" height="12"><line x1="6" y1="12" x2="18" y2="12"/></svg></button>
          </div>
        </div>
      </div>

      <!-- Skills: popover列表（对齐原型 N.showSkillList） -->
      <div class="project-config-section" style="position:relative;">
        <div class="project-config-header">
          <span>技能</span>
          <button class="project-config-add" @click="openSkillPopover" title="添加技能">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
        </div>
        <div class="project-config-desc">配置项目技能，让 AI 精准执行任务</div>
        <div class="project-config-items">
          <div v-for="(s, i) in skills" :key="i" class="project-config-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="14" height="14" style="flex-shrink:0;color:var(--text-tertiary)"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>{{ s }}
            <button class="config-item-remove" @click="removeSkill(i)" title="移除"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" width="12" height="12"><line x1="6" y1="12" x2="18" y2="12"/></svg></button>
          </div>
        </div>
        <!-- Popover -->
        <div class="project-config-popover open" v-if="skillPopoverOpen">
          <div class="project-config-popover-header">
            <span>选择技能</span>
            <button @click="skillPopoverOpen = false" style="width:22px;height:22px;border-radius:50%;border:1px solid var(--border-default);background:transparent;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" width="12" height="12"><line x1="6" y1="12" x2="18" y2="12"/></svg></button>
          </div>
          <div class="project-config-popover-list">
            <button v-for="sk in predefinedSkills" :key="sk.name" class="project-config-popover-item" :class="{ disabled: skills.includes(sk.name) }" @click="pickSkill(sk.name)">
              <span class="popover-item-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg></span>
              <span>{{ sk.name }}</span>
              <span style="margin-left:auto;font-size:10px;color:var(--text-tertiary)">{{ sk.desc }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const { showToast } = useToast()
const activeTab = ref('activity')
const draft = ref('')
const chatDraft = ref('')
const inProjectChat = ref(false)
const chatMessages = ref<Array<{ role: string; text: string }>>([])
const chatMessagesRef = ref<HTMLElement | null>(null)
const activeAssetFilter = ref('all')
const assetSearch = ref('')

const project = ref({ id: 'cyber', name: '赛博工坊 v2.0' })

// ===== Config panel — 指令 =====
const instructionEditing = ref(false)
const instructionText = ref('根据项目需求手册，策划一条产品宣传片。')
const instructionBackup = ref('')
function toggleInstructionEditor() {
  if (!instructionEditing.value) {
    instructionBackup.value = instructionText.value
    instructionEditing.value = true
  }
}
function cancelInstructionEdit() {
  instructionText.value = instructionBackup.value
  instructionEditing.value = false
}
function saveInstruction() {
  instructionEditing.value = false
  showToast('项目指令已保存', 'success')
}

// ===== Config panel — 连接器/专家 =====
const connectors = ref<string[]>(['GitHub MCP'])
const experts = ref<string[]>(['Hermes'])
const skills = ref<string[]>([])
const openDropdown = ref<string | null>(null)

function toggleConfigDropdown(type: string) {
  openDropdown.value = openDropdown.value === type ? null : type
  if (type !== 'skill') { skillPickerOpen.value = false }
}
function addConnector(name: string) {
  if (!connectors.value.includes(name)) connectors.value.push(name)
  openDropdown.value = null
  showToast('已添加: ' + name, 'success')
}
function removeConnector(i: number) {
  connectors.value.splice(i, 1)
  showToast('已移除连接器', 'info')
}
function addExpert(name: string) {
  if (!experts.value.includes(name)) experts.value.push(name)
  openDropdown.value = null
  showToast('已添加: ' + name, 'success')
}
function removeExpert(i: number) {
  experts.value.splice(i, 1)
  showToast('已移除专家', 'info')
}

// ===== Config panel — 技能 (popover列表, 对齐原型 N.showSkillList) =====
const predefinedSkills = [
  { name: 'code-review', desc: '代码审查与优化建议' },
  { name: 'api-design', desc: 'API 设计与文档生成' },
  { name: 'ui-generation', desc: 'UI 组件自动生成' },
  { name: 'test-automation', desc: '自动化测试用例编写' },
  { name: 'deploy-pipeline', desc: '部署流水线配置' },
  { name: 'doc-generator', desc: '项目文档自动生成' },
]
const skillPopoverOpen = ref(false)
function openSkillPopover() {
  skillPopoverOpen.value = !skillPopoverOpen.value
  openDropdown.value = null
}
function pickSkill(name: string) {
  if (!skills.value.includes(name)) {
    skills.value.push(name)
    showToast(name + ' 已添加到项目', 'success')
  }
  skillPopoverOpen.value = false
}
function removeSkill(i: number) { skills.value.splice(i, 1); showToast('已移除技能', 'info') }

// ===== Tabs =====
const tabs = [
  { id: 'activity', label: '动态', iconPath: '<circle cx="10" cy="10" r="8"/><polyline points="10 5 10 10 14 10"/>' },
  { id: 'sop', label: 'SOP', iconPath: '<rect x="2" y="3" width="16" height="14" rx="2"/><line x1="6" y1="8" x2="14" y2="8"/><line x1="6" y1="12" x2="12" y2="12"/>' },
  { id: 'tasks', label: '自动化', iconPath: '<circle cx="10" cy="10" r="8"/><polyline points="10 6 10 12 14"/>' },
  { id: 'assets', label: '资产', iconPath: '<rect x="3" y="4" width="14" height="12" rx="2"/><line x1="10" y1="4" x2="10" y2="16"/><line x1="3" y1="10" x2="17" y2="10"/>' },
]
function switchTab(tab: string) { activeTab.value = tab }

// ===== Activity =====
const activities = ref<Array<{ avatar: string; avatarStyle: string; name: string; type: string; typeLabel: string; desc: string; time: string }>>([
  { avatar: 'H', avatarStyle: 'background:var(--gradient-brand);', name: 'Hermes', type: 'ai', typeLabel: 'AI 动作', desc: '完成了 <b>SOP 步骤 2：开发执行</b>，生成代码审查报告', time: '3 分钟前' },
  { avatar: '刘', avatarStyle: 'background:rgba(139,92,246,.15);color:#8B5CF6;', name: '刘老爷', type: 'file', typeLabel: '文件', desc: '上传了 <b>需求文档_v3.pdf</b> (2.4 MB)', time: '1 小时前' },
  { avatar: '系', avatarStyle: 'background:rgba(251,191,36,.15);color:var(--amber);font-size:14px;', name: '系统', type: 'event', typeLabel: '事件', desc: '项目 <b>赛博工坊 v2.0</b> 创建成功，3个 Agent 已加入', time: '2026-06-27 14:32' },
])
function startFirstTask() { draft.value = '@Hermes 开始第一个任务' }
function sendFromProject() {
  if (!draft.value.trim()) return
  const text = draft.value.trim()
  activities.value.unshift({ avatar: '刘', avatarStyle: 'background:rgba(139,92,246,.15);color:#8B5CF6;', name: '刘老爷', type: 'member', typeLabel: '成员', desc: text, time: '刚刚' })
  // 切换到项目对话视图
  chatMessages.value.push({ role: 'user', text })
  inProjectChat.value = true
  draft.value = ''
  setTimeout(() => {
    chatMessages.value.push({ role: 'ai', text: '收到消息：「' + text + '」\n\n请继续描述你的需求。' })
    activities.value.unshift({ avatar: 'H', avatarStyle: 'background:var(--gradient-brand);', name: 'Hermes', type: 'ai', typeLabel: 'AI 动作', desc: '收到消息并回复', time: '刚刚' })
  }, 500)
}

function sendChatMessage() {
  if (!chatDraft.value.trim()) return
  const text = chatDraft.value.trim()
  chatMessages.value.push({ role: 'user', text })
  chatDraft.value = ''
  setTimeout(() => {
    chatMessages.value.push({ role: 'ai', text: '收到！已记录到项目动态中。' })
  }, 600)
}

function goBackToProject() {
  inProjectChat.value = false
}

// ===== SOP =====
const sopAdding = ref(false)
const sopNewTitle = ref('')
const sopNewDesc = ref('')
const sopEditingIndex = ref<number | null>(null)
const sopEditTitle = ref('')
const sopEditDesc = ref('')

function startSopConversation() {
  draft.value = '帮我创建一个标准化的项目 SOP 工作流：'
  showToast('在输入框中描述你想要的 SOP 流程', 'info')
}

const sopSteps = ref<Array<{ id: string; status: string; title: string; desc: string; stateLabel: string }>>([
  { id: 's1', status: 'active', title: '需求分析与方案设计', desc: '梳理核心需求、竞品分析、技术方案初稿', stateLabel: '● 进行中' },
  { id: 's2', status: 'completed', title: '开发执行', desc: '按照方案进行编码实现，定期代码审查和测试', stateLabel: '✓ 已完成' },
  { id: 's3', status: 'pending', title: '部署上线', desc: 'CI/CD 流水线配置，灰度发布与监控', stateLabel: '待执行' },
])
let sopCounter = 4

function confirmAddSopStep() {
  if (!sopNewTitle.value.trim()) return
  sopSteps.value.push({ id: 's' + sopCounter++, status: 'pending', title: sopNewTitle.value.trim(), desc: sopNewDesc.value.trim() || '新步骤 — 待补充描述', stateLabel: '待执行' })
  sopAdding.value = false
  sopNewTitle.value = ''
  sopNewDesc.value = ''
  showToast('已添加步骤', 'success')
}
function cancelAddSopStep() { sopAdding.value = false; sopNewTitle.value = ''; sopNewDesc.value = '' }

function openEditSopStep(i: number) {
  sopEditingIndex.value = i
  sopEditTitle.value = sopSteps.value[i].title
  sopEditDesc.value = sopSteps.value[i].desc
}
function confirmEditSopStep() {
  if (sopEditingIndex.value === null) return
  if (sopEditTitle.value.trim()) sopSteps.value[sopEditingIndex.value].title = sopEditTitle.value.trim()
  if (sopEditDesc.value.trim()) sopSteps.value[sopEditingIndex.value].desc = sopEditDesc.value.trim()
  sopEditingIndex.value = null
  showToast('步骤已更新', 'success')
}
function cancelEditSopStep() { sopEditingIndex.value = null }
function deleteSopStep(i: number) { sopSteps.value.splice(i, 1); showToast('步骤已删除', 'info') }

// ===== Tasks =====
function addProjectTask() { showToast('新建任务 — 从对话创建', 'info') }

// ===== Assets =====
const assetFilters = [
  { id: 'all', label: '全部' }, { id: 'folder', label: '文件夹' }, { id: 'doc', label: '文档' },
  { id: 'image', label: '图片' }, { id: 'code', label: '代码' },
]
const allAssets = [
  { name: '设计稿', type: 'folder', meta: '12 个文件 · 2026-06-22' },
  { name: '产品需求规格书_v3.2.docx', type: 'doc', meta: '2.4 MB · 2026-06-21' },
  { name: 'UI_首页设计稿_final.png', type: 'image', meta: '3.1 MB · 2026-06-19' },
  { name: 'agent_core.py', type: 'code', meta: '45 KB · 2026-06-18' },
  { name: '模型训练数据_v2.zip', type: 'other', meta: '156 MB · 2026-06-15' },
]
const filteredAssets = computed(() => {
  let list = allAssets
  if (activeAssetFilter.value !== 'all') list = list.filter(f => f.type === activeAssetFilter.value)
  if (assetSearch.value.trim()) { const q = assetSearch.value.toLowerCase(); list = list.filter(f => f.name.toLowerCase().includes(q)) }
  return list
})
function fileIcon(type: string) {
  if (type === 'folder') return '<path d="M3 6l7-4 7 4v8l-7 4-7-4V6z"/><path d="M3 6l7 4 7-4"/><path d="M10 10v8"/>'
  if (type === 'doc') return '<path d="M14 2H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z"/><polyline points="14 2 14 8 20 8"/>'
  if (type === 'code') return '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>'
  if (type === 'image') return '<rect x="3" y="2" width="14" height="16" rx="2" ry="2"/><circle cx="8.5" cy="7.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>'
  return '<path d="M14 2H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z"/><rect x="8" y="6" width="4" height="4" rx="1"/><path d="M8 12h4"/>'
}
function newAssetFolder() { showToast('新建文件夹', 'info') }
function uploadAssetFile() { showToast('上传文件', 'info') }
function openAssetFile(file: { name: string; type: string }) { showToast('打开: ' + file.name, 'info') }
</script>
