<template>
  <aside class="side-panel" :class="{ open: modelValue }" id="sidePanel" aria-label="侧边面板">
    <!-- Agent Settings -->
    <div class="panel-page" :class="{ active: panelType === 'settings' }" v-show="panelType === 'settings'">
      <div class="panel-page-header"><span class="panel-page-header-title">Agent设置</span><button class="panel-close-btn" @click="$emit('update:modelValue', false)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div>
      <div class="as-profile-section">
        <div class="as-profile-avatar">H</div>
        <template v-if="agentEditOpen">
          <input class="as-edit-input" v-model="agentName" placeholder="Agent名称" @keydown.enter="saveAgent" />
          <textarea class="as-edit-input as-edit-textarea" v-model="agentBio" placeholder="简介" rows="2"></textarea>
          <div class="as-edit-actions">
            <button class="as-edit-btn" @click="saveAgent">保存</button>
            <button class="as-edit-btn as-edit-cancel" @click="cancelAgentEdit">取消</button>
          </div>
        </template>
        <template v-else>
          <div class="as-profile-name">{{ agentName }}</div>
          <div class="as-profile-bio">{{ agentBio }}</div>
          <button class="as-edit-btn" @click="openAgentEdit">修改Agent信息</button>
        </template>
      </div>
      <div class="as-section-label">能力与资源</div>
      <div class="as-card" @click="$emit('toast', '技能列表展开', 'info')">
        <div class="as-card-header">
          <div class="as-card-icon" style="background:rgba(99,145,237,.10);color:var(--brand)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg></div>
          <span class="as-card-title">技能</span><svg class="as-card-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
        </div>
        <div class="as-card-sub">查看当前Agent拥有的技能</div>
      </div>
      <div class="as-card" style="margin-top:6px" @click="$emit('toast', '授权文件夹管理面板', 'info')">
        <div class="as-card-header">
          <div class="as-card-icon" style="background:rgba(139,92,246,.10);color:var(--purple)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg></div>
          <span class="as-card-title">已授权的文件夹</span><svg class="as-card-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
        </div>
        <div class="as-card-sub">管理Agent可操作的个人电脑文件夹，支持调整授权范围或取消授权</div>
      </div>
      <div class="as-card" style="margin-top:6px">
        <div class="as-card-header">
          <div class="as-card-icon" style="background:rgba(45,212,191,.10);color:var(--teal)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg></div>
          <span class="as-card-title">渠道</span>
          <button class="as-edit-btn" @click.stop="$emit('toast', '添加渠道', 'info')">添加</button>
        </div>
        <div class="as-card-sub">连接到不同的聊天产品，帮助你随时随地对话</div>
        <div class="as-card-extra">
          <div class="as-channel-row">
            <span class="as-channel-name">飞书</span>
            <div style="display:flex;align-items:center;gap:4px">
              <span class="as-channel-status">正常</span>
              <button class="toggle-switch on" type="button" role="switch" aria-checked="true" @click="toggleChannel($event)"></button>
            </div>
          </div>
        </div>
      </div>
      <div class="as-card" style="margin-top:6px">
        <div class="as-card-header">
          <div class="as-card-icon" style="background:rgba(251,191,36,.10);color:var(--amber)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg></div>
          <span class="as-card-title">模型设置</span>
          <span class="as-model-select" @click.stop="$emit('toast', '模型列表', 'info')">DeepSeek-V4-Pro <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg></span>
        </div>
        <div class="as-model-row"><span class="as-model-current">当前模型: <span>DeepSeek-V4-Pro</span></span></div>
      </div>
      <div class="as-card" style="margin-top:6px">
        <div class="as-card-header">
          <div class="as-card-icon" style="background:rgba(248,113,113,.10);color:var(--coral)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg></div>
          <span class="as-card-title">TOKEN用量</span>
        </div>
        <div style="padding-left:44px;margin-top:4px">
          <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-tertiary);margin-bottom:4px"><span>已使用</span><span>67,420 / 128,000</span></div>
          <div class="v8-progress-track"><div class="v8-progress-fill" style="width:52.7%"></div></div>
        </div>
      </div>
      <div class="as-card" style="margin-top:6px">
        <div class="as-card-header" style="margin-bottom:8px">
          <div class="as-card-icon" style="background:rgba(34,211,238,.10);color:var(--cyan)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div>
          <span class="as-card-title">最近活动</span>
        </div>
        <div style="padding-left:44px;display:flex;flex-direction:column;gap:8px">
          <div class="v8-activity-item"><div class="v8-activity-dot br"></div><div><div class="v8-activity-text">递归进化引擎完成第8次自检</div><div class="v8-activity-time">2分钟前</div></div></div>
          <div class="v8-activity-item"><div class="v8-activity-dot pu"></div><div><div class="v8-activity-text">涌现引擎检测到新能力 自动摘要生成</div><div class="v8-activity-time">18分钟前</div></div></div>
          <div class="v8-activity-item"><div class="v8-activity-dot cr"></div><div><div class="v8-activity-text">太极网络完成负载均衡重分配</div><div class="v8-activity-time">1小时前</div></div></div>
          <div class="v8-activity-item"><div class="v8-activity-dot gn"></div><div><div class="v8-activity-text">Token压缩层节省22%上下文预算</div><div class="v8-activity-time">3小时前</div></div></div>
        </div>
      </div>
    </div>

    <!-- Calendar -->
    <div class="panel-page" :class="{ active: panelType === 'calendar' }" v-show="panelType === 'calendar'">
      <div class="panel-page-header"><span class="panel-page-header-title">日历</span><button class="panel-close-btn" @click="$emit('update:modelValue', false)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div>
      <div class="panel-calendar-placeholder">
        <div class="calendar-month-nav">
          <button class="calendar-nav-btn" @click="calMonth--">&lt;</button>
          <span class="calendar-month-label">{{ calYear }}年{{ calMonth + 1 }}月</span>
          <button class="calendar-nav-btn" @click="calMonth++">&gt;</button>
        </div>
        <div class="calendar-grid" style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px;text-align:center;font-size:12px;padding:4px 0">
          <span v-for="h in ['日','一','二','三','四','五','六']" :key="h" class="calendar-day-head" style="font-size:10px;color:var(--text-tertiary);padding:4px 0">{{ h }}</span>
          <span v-for="(d, i) in calDays" :key="i" class="calendar-day" :class="d.cls" style="padding:6px 0;border-radius:6px;cursor:pointer" @click="calSelected = d.day">{{ d.day }}</span>
        </div>
      </div>
      <div class="panel-section">
        <div class="panel-section-title" style="margin-bottom:4px">{{ calYear }}年{{ calMonth + 1 }}月{{ calSelected }}日行程</div>
        <div v-for="ev in calEvents" :key="ev.title" class="calendar-event-item" style="display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid var(--border-subtle)">
          <div class="calendar-event-dot" :style="{ background: ev.color }" style="width:8px;height:8px;border-radius:50%;flex-shrink:0"></div>
          <div style="flex:1"><div style="font-size:13px;font-weight:500">{{ ev.title }}</div><div style="font-size:11px;color:var(--text-tertiary)">{{ ev.time }}</div></div>
        </div>
      </div>
    </div>

    <!-- Files -->
    <div class="panel-page" :class="{ active: panelType === 'files' }" v-show="panelType === 'files'">
      <div class="panel-page-header"><span class="panel-page-header-title">超级牛马的文件</span><button class="panel-close-btn" @click="$emit('update:modelValue', false)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div>
      <div class="files-tabs">
        <button class="files-tab" :class="{ active: fileTab === 'work' }" @click="fileTab = 'work'">工作文件</button>
        <button class="files-tab" :class="{ active: fileTab === 'memory' }" @click="fileTab = 'memory'">记忆</button>
      </div>
      <div class="files-search" style="margin-bottom:12px;display:flex;align-items:center;gap:8px;padding:0 12px;height:34px;border-radius:8px;background:var(--bg-elevated)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="15" height="15" style="color:var(--text-tertiary);flex-shrink:0"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input type="text" placeholder="搜索文件..." v-model="fileSearch" style="flex:1;border:none;background:none;color:var(--text-primary);font-size:12px;outline:none;font-family:inherit">
        <span class="files-search-kbd" style="font-size:10px;color:var(--text-tertiary)">Cmd+K</span>
      </div>
      <div v-if="fileTab === 'work'" class="files-tree">
        <div class="files-section-label" style="font-size:10px;text-transform:uppercase;color:var(--text-tertiary);padding:4px 0">对话文件</div>
        <div class="files-tree-item active" style="display:flex;align-items:center;gap:6px;padding:6px 8px;border-radius:6px;cursor:pointer;font-size:13px;background:var(--bg-hover)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" style="transition:transform .15s"><polyline points="9 18 15 12 9 6"/></svg>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="15" height="15"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          主对话
        </div>
        <div class="files-tree-item" style="display:flex;align-items:center;gap:6px;padding:6px 8px;border-radius:6px;cursor:pointer;font-size:13px" @click="fileTreeAll = !fileTreeAll">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" :style="{ transform: fileTreeAll ? 'rotate(90deg)' : '', transition: 'transform .15s' }"><polyline points="9 18 15 12 9 6"/></svg>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="15" height="15"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
          所有对话
        </div>
        <div v-if="fileTreeAll" style="padding-left:22px">
          <div v-for="name in ['赛博工坊','代码重构 - React模块','产品文档 - 营销方案']" :key="name" style="padding:4px 8px;font-size:12px;color:var(--text-secondary);cursor:pointer;border-radius:4px" @click="$emit('toast', '打开对话文件', 'info')"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--text-tertiary);margin-right:6px;vertical-align:middle"></span>{{ name }}</div>
        </div>
        <div class="files-tree-item" style="display:flex;align-items:center;gap:6px;padding:6px 8px;border-radius:6px;cursor:pointer;font-size:13px" @click="fileTreeBasic = !fileTreeBasic">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" :style="{ transform: fileTreeBasic ? 'rotate(90deg)' : '', transition: 'transform .15s' }"><polyline points="9 18 15 12 9 6"/></svg>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="15" height="15"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
          基础设定
        </div>
        <div v-if="fileTreeBasic" style="padding-left:22px">
          <div style="padding:4px 8px;font-size:12px;color:var(--text-secondary);cursor:pointer;border-radius:4px" @click="$emit('toast', '打开 TOOLS.MD', 'info')"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--text-tertiary);margin-right:6px;vertical-align:middle"></span>TOOLS.MD <span style="margin-left:auto;font-size:10px;color:var(--text-dim)">2.4KB</span></div>
          <div style="padding:4px 8px;font-size:12px;color:var(--text-secondary);cursor:pointer;border-radius:4px" @click="$emit('toast', '打开 SOUL.MD', 'info')"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--text-tertiary);margin-right:6px;vertical-align:middle"></span>SOUL.MD <span style="margin-left:auto;font-size:10px;color:var(--text-dim)">1.8KB</span></div>
        </div>
      </div>
      <div v-else class="files-tree">
        <div class="files-section-label" style="font-size:10px;text-transform:uppercase;color:var(--text-tertiary);padding:4px 0">记忆文件</div>
        <div class="files-tree-item" style="display:flex;align-items:center;gap:6px;padding:6px 8px;border-radius:6px;cursor:pointer;font-size:13px" @click="$emit('toast', '打开记忆', 'info')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polyline points="9 18 15 12 9 6"/></svg>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="15" height="15"><path d="M12 2a4 4 0 0 1 4 4c0 1.1-.9 2-2 2h-4c-1.1 0-2-.9-2-2a4 4 0 0 1 4-4z"/></svg>
          MEMORY.md
        </div>
      </div>
    </div>

    <!-- Project Settings -->
    <div class="panel-page" :class="{ active: panelType === 'project-settings' }" v-show="panelType === 'project-settings'">
      <div class="panel-page-header"><span class="panel-page-header-title">项目设置</span><button class="panel-close-btn" @click="$emit('update:modelValue', false)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div>
      <div class="as-profile-section" style="margin-top:4px">
        <div class="as-profile-avatar">S</div>
        <template v-if="projectEditOpen">
          <input class="as-edit-input" v-model="projectName" placeholder="项目名称" @keydown.enter="saveProject" />
          <textarea class="as-edit-input as-edit-textarea" v-model="projectDesc" placeholder="项目描述" rows="2"></textarea>
          <div class="as-edit-actions">
            <button class="as-edit-btn" @click="saveProject">保存</button>
            <button class="as-edit-btn as-edit-cancel" @click="cancelProjectEdit">取消</button>
          </div>
        </template>
        <template v-else>
          <div class="as-profile-name">{{ projectName }}</div>
          <div class="as-profile-bio">{{ projectDesc }}</div>
          <button class="as-edit-btn" @click="openProjectEdit">修改设置</button>
        </template>
      </div>
      <div class="v8-section-card" style="margin-top:10px">
        <div class="v8-section-card-title" style="font-size:11px;font-weight:600;color:var(--text-tertiary);margin-bottom:8px">项目配置</div>
        <div v-for="opt in projectConfigOptions" :key="opt.label" style="display:flex;align-items:center;justify-content:space-between;padding:13px 0;border-bottom:1px solid var(--border-subtle)">
          <div><div style="font-size:13px;font-weight:500">{{ opt.label }}</div><div style="font-size:11px;color:var(--text-tertiary)">{{ opt.desc }}</div></div>
          <button class="toggle-switch" :class="{ on: opt.on }" type="button" role="switch" :aria-checked="opt.on" @click="opt.on = !opt.on"></button>
        </div>
      </div>
      <div class="v8-section-card" style="margin-top:10px">
        <div class="v8-section-card-title" style="font-size:11px;font-weight:600;color:var(--text-tertiary);margin-bottom:8px">Token用量统计</div>
        <div style="margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-tertiary);margin-bottom:4px"><span>项目总计</span><span>487,320 / 1,280,000</span></div>
          <div class="v8-progress-track" style="height:6px;border-radius:3px;background:var(--bg-overlay);overflow:hidden"><div class="v8-progress-fill" style="width:38%;height:100%;border-radius:3px;background:var(--brand)"></div></div>
        </div>
        <div><div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-tertiary);margin-bottom:4px"><span>本月</span><span>142,800 / 400,000</span></div><div class="v8-progress-track" style="height:6px;border-radius:3px;background:var(--bg-overlay);overflow:hidden"><div class="v8-progress-fill" style="width:35.7%;height:100%;border-radius:3px;background:var(--brand)"></div></div></div>
      </div>
      <div class="v8-section-card" style="margin-top:10px">
        <div class="v8-section-card-title" style="font-size:11px;font-weight:600;color:var(--text-tertiary);margin-bottom:8px">最近活动</div>
        <div v-for="act in projectActivities" :key="act.text" style="display:flex;align-items:flex-start;gap:10px;padding:6px 0">
          <div :style="{ width:'7px',height:'7px',borderRadius:'50%',background:act.color,marginTop:'4px',flexShrink:0 }"></div>
          <div><div style="font-size:12px">{{ act.text }}</div><div style="font-size:10px;color:var(--text-tertiary)">{{ act.time }}</div></div>
        </div>
      </div>
    </div>

    <!-- Background Tasks -->
    <div class="panel-page" :class="{ active: panelType === 'bg-tasks' }" v-show="panelType === 'bg-tasks'">
      <div class="panel-page-header"><span class="panel-page-header-title">后台任务</span><button class="panel-close-btn" @click="$emit('update:modelValue', false)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div>
      <div class="panel-section-subtitle" style="font-size:12px;color:var(--text-tertiary);padding:0 18px;margin-bottom:8px">异步任务执行状态，实时追踪进度</div>
      <div v-for="task in bgTasks" :key="task.name" style="display:flex;align-items:center;gap:10px;padding:12px 18px;border-bottom:1px solid var(--border-subtle)">
        <div style="width:34px;height:34px;border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0" :style="{ background: task.statusClr + '15', color: task.statusClr }">
          <svg v-if="task.status === 'running'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
          <svg v-else-if="task.status === 'done'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="15" height="15"><polyline points="20 6 9 17 4 12"/></svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
        </div>
        <div style="flex:1;min-width:0">
          <div style="font-size:13px;font-weight:500">{{ task.name }}</div>
          <div style="font-size:11px;color:var(--text-tertiary)">{{ task.desc }}</div>
          <div v-if="task.progress != null" style="margin-top:4px;height:4px;border-radius:2px;background:var(--bg-overlay);overflow:hidden"><div :style="{ width: task.progress + '%', height:'100%',background:task.statusClr,borderRadius:'2px' }"></div></div>
        </div>
        <span v-if="task.status === 'done'" style="font-size:11px;color:var(--green)">成功</span>
        <span v-else-if="task.status === 'failed'" style="font-size:11px;color:var(--coral)">失败</span>
        <button v-else style="width:22px;height:22px;border:none;background:var(--bg-hover);border-radius:4px;color:var(--text-tertiary);cursor:pointer;font-size:10px" title="终止" @click="task.progress = null">&#9632;</button>
      </div>
    </div>

    <!-- Search History -->
    <div class="panel-page" :class="{ active: panelType === 'search-history' }" v-show="panelType === 'search-history'">
      <div class="panel-page-header"><span class="panel-page-header-title">搜索历史对话</span><button class="panel-close-btn" @click="$emit('update:modelValue', false)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div>
      <div class="panel-section-subtitle" style="font-size:12px;color:var(--text-tertiary);padding:0 18px;margin-bottom:8px">跨对话全文搜索，快速定位上下文</div>
      <div style="margin:0 18px 12px;display:flex;align-items:center;gap:8px;padding:0 12px;height:36px;border-radius:8px;background:var(--bg-elevated)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="16" height="16" style="color:var(--text-tertiary)"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input type="text" placeholder="搜索消息、Agent 或关键词" v-model="historySearch" style="flex:1;border:none;background:none;color:var(--text-primary);font-size:12px;outline:none;font-family:inherit">
        <span style="font-size:10px;color:var(--text-tertiary)">Cmd+K</span>
      </div>
      <div v-for="item in historyCards" :key="item.title" style="display:flex;gap:12px;padding:12px 18px;cursor:pointer;border-radius:8px;margin:0 4px" @click="$emit('toast', '打开历史对话', 'info')">
        <div style="width:34px;height:34px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;flex-shrink:0" :style="{ background: item.avatarBg, color: item.avatarColor }">{{ item.avatar }}</div>
        <div style="flex:1;min-width:0">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:2px"><span style="font-size:13px;font-weight:500">{{ item.title }}</span><span style="font-size:10px;padding:1px 6px;border-radius:4px;background:var(--bg-overlay);color:var(--text-tertiary)">{{ item.agent }}</span></div>
          <div style="font-size:11px;color:var(--text-tertiary);margin-bottom:4px">{{ item.excerpt }}</div>
          <div style="display:flex;align-items:center;gap:6px;font-size:10px;color:var(--text-tertiary)">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" width="11" height="11"><path d="M2 4h12M2 8h8M2 12h5"/></svg>
            {{ item.msgs }} 条消息 <span>·</span> {{ item.time }}
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

defineProps<{ modelValue: boolean; panelType: string }>()
const emit = defineEmits<{ 'update:modelValue': [val: boolean]; toast: [msg: string, type?: string] }>()

const fileTab = ref('work')
const fileSearch = ref('')
const historySearch = ref('')
const fileTreeAll = ref(true)
const fileTreeBasic = ref(false)

// Agent Settings — inline edit
const agentEditOpen = ref(false)
const agentName = ref('超级牛马')
const agentBio = ref('赛博工坊 - 主智能体 v2.4')
const agentNameBackup = ref('')
const agentBioBackup = ref('')
function saveAgent() {
  agentEditOpen.value = false
  emit('toast', 'Agent信息已更新', 'success')
}
function cancelAgentEdit() {
  agentName.value = agentNameBackup.value
  agentBio.value = agentBioBackup.value
  agentEditOpen.value = false
}
function openAgentEdit() {
  agentNameBackup.value = agentName.value
  agentBioBackup.value = agentBio.value
  agentEditOpen.value = true
}

// Project Settings — inline edit
const projectEditOpen = ref(false)
const projectName = ref('超级牛马 Super Niuma')
const projectDesc = ref('赛博工坊 - AI Workstation')
const projectNameBackup = ref('')
const projectDescBackup = ref('')
function saveProject() {
  projectEditOpen.value = false
  emit('toast', '项目设置已更新', 'success')
}
function cancelProjectEdit() {
  projectName.value = projectNameBackup.value
  projectDesc.value = projectDescBackup.value
  projectEditOpen.value = false
}
function openProjectEdit() {
  projectNameBackup.value = projectName.value
  projectDescBackup.value = projectDesc.value
  projectEditOpen.value = true
}

// Toggle switch for channel
function toggleChannel(e: Event) {
  const btn = e.currentTarget as HTMLElement
  btn.classList.toggle('on')
  const on = btn.classList.contains('on')
  btn.setAttribute('aria-checked', String(on))
  emit('toast', on ? '渠道已开启' : '渠道已关闭', 'info')
}

// Calendar
const calYear = ref(2026)
const calMonth = ref(5)
const calSelected = ref(26)
const calDays = computed(() => {
  const firstDay = new Date(calYear.value, calMonth.value, 1).getDay()
  const daysInMonth = new Date(calYear.value, calMonth.value + 1, 0).getDate()
  const prevDays = new Date(calYear.value, calMonth.value, 0).getDate()
  const days: { day: number; cls: string }[] = []
  for (let i = firstDay - 1; i >= 0; i--) days.push({ day: prevDays - i, cls: 'dim' })
  for (let d = 1; d <= daysInMonth; d++) {
    let cls = ''
    if (d === 25) cls = 'today'
    if (d === calSelected.value) cls += ' active'
    days.push({ day: d, cls })
  }
  const remaining = 7 - (days.length % 7 || 7)
  if (remaining < 7) for (let d = 1; d <= remaining; d++) days.push({ day: d, cls: 'dim' })
  return days
})
const calEvents = [
  { title: 'Sprint 24 代码审查', time: '10:00 - 11:30', color: 'var(--brand)' },
  { title: '产品需求评审', time: '14:00 - 15:00', color: '#8B5CF6' },
  { title: '太极引擎性能调优', time: '16:00 - 17:30', color: '#34D399' },
]

// Project Settings
const projectConfigOptions = ref([
  { label: '自动压缩上下文', desc: '历史消息自动摘要压缩', on: true },
  { label: '后台预加载', desc: '进入对话时预加载历史', on: true },
  { label: '实时协作', desc: '允许多人同时编辑', on: false },
])
const projectActivities = [
  { text: '架构文档已更新至v3', time: '2小时前', color: 'var(--brand)' },
  { text: '新增3个Agent能力开关', time: '5小时前', color: 'var(--purple)' },
  { text: '完成安全扫描，零漏洞', time: '昨天', color: 'var(--green)' },
]

// Background Tasks
const bgTasks = ref([
  { name: '索引重建', desc: '重建代码库全文搜索索引 · 68%', status: 'running', progress: 68, statusClr: 'var(--brand)' },
  { name: '知识库同步', desc: '同步飞书知识库最新内容 · 45%', status: 'running', progress: 45, statusClr: 'var(--purple)' },
  { name: '依赖安全扫描', desc: '已完成 · 0个严重漏洞 · 耗时 1.8s', status: 'done', progress: null, statusClr: 'var(--green)' },
  { name: '自动备份同步', desc: '连接超时 · 3次重试后失败', status: 'failed', progress: null, statusClr: 'var(--coral)' },
])

// Search History
const historyCards = [
  { title: '递归进化引擎 P0优化清单', agent: 'Hermes', excerpt: '关于自愈引擎的3个P0级问题修复方案讨论...', msgs: 24, time: '今天 13:42', avatar: 'H', avatarBg: 'var(--gradient-brand)', avatarColor: '#fff' },
  { title: 'API 网关设计方案 v2', agent: 'Niuma', excerpt: '讨论了网关层的限流、鉴权、路由转发策略...', msgs: 18, time: '今天 10:15', avatar: 'N', avatarBg: 'var(--gradient-brand)', avatarColor: '#fff' },
  { title: '前端重构设计方案', agent: '刘老爷', excerpt: 'Super Niuma v1.5 前端重构设计评审...', msgs: 35, time: '昨天 18:30', avatar: '刘', avatarBg: 'rgba(139,92,246,.15)', avatarColor: '#8B5CF6' },
  { title: '去AI味引擎优化方案', agent: 'Hermes', excerpt: '针对网文创作场景的10种AI味特征检测优化...', msgs: 42, time: '昨天 14:08', avatar: 'H', avatarBg: 'var(--gradient-brand)', avatarColor: '#fff' },
  { title: '家人知识库 Schema v3', agent: '小章鱼', excerpt: '10个核心Schema的字段优化与信源验证...', msgs: 28, time: '6月24日', avatar: '章', avatarBg: 'rgba(52,211,153,.15)', avatarColor: '#34D399' },
]
</script>
