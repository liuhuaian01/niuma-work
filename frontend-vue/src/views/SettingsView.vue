<template>
<div class="page-view active" id="pageSettings">
  <div class="settings-layout">
    <!-- Settings Navigation -->
    <div class="settings-nav-card" id="settingsNav">
      <div class="settings-nav-group-label">通用</div>
      <div class="settings-nav-item" :class="{ active: activePanel === 'preferences' }" @click="activePanel = 'preferences'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        <span>偏好设置</span>
      </div>
      <div class="settings-nav-item" :class="{ active: activePanel === 'profile' }" @click="activePanel = 'profile'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
        <span>个人资料</span>
      </div>
      <div class="settings-nav-item" :class="{ active: activePanel === 'system' }" @click="activePanel = 'system'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>
        <span>系统设置</span>
      </div>
      <div class="settings-nav-item" :class="{ active: activePanel === 'shortcuts' }" @click="activePanel = 'shortcuts'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M8 12h.01M12 12h.01M16 12h.01M6 16h.01M10 16h.01M14 16h.01M18 16h.01"/></svg>
        <span>快捷键</span>
      </div>
      <div class="settings-nav-sep"></div>
      <div class="settings-nav-group-label">工作台</div>
      <div class="settings-nav-item" :class="{ active: activePanel === 'kanban' }" @click="activePanel = 'kanban'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
        <span>任务看板</span>
      </div>
      <div class="settings-nav-item" :class="{ active: activePanel === 'dashboard' }" @click="activePanel = 'dashboard'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
        <span>用量看板</span>
      </div>
      <div class="settings-nav-sep"></div>
      <div class="settings-nav-group-label">高级设置</div>
      <div class="settings-nav-item" :class="{ active: activePanel === 'taiji' }" @click="activePanel = 'taiji'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 0 1 0 20"/><circle cx="12" cy="12" r="3"/></svg>
        <span>太极引擎</span>
      </div>
      <div class="settings-nav-item" :class="{ active: activePanel === 'awareness' }" @click="activePanel = 'awareness'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
        <span>意识</span>
      </div>
      <div class="settings-nav-item" :class="{ active: activePanel === 'models' }" @click="activePanel = 'models'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
        <span>模型管理</span>
      </div>
      <div class="settings-nav-item" :class="{ active: activePanel === 'security' }" @click="activePanel = 'security'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
        <span>安全中心</span>
      </div>
      <div class="settings-nav-sep"></div>
      <div class="settings-nav-item" :class="{ active: activePanel === 'archived' }" @click="activePanel = 'archived'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        <span>已归档</span>
      </div>
      <div class="settings-nav-item" :class="{ active: activePanel === 'about' }" @click="activePanel = 'about'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
        <span>关于</span>
      </div>
    </div>

    <!-- Settings Detail Card -->
    <div class="settings-detail-card" id="settingsDetail">
      <!-- 偏好设置 -->
      <div class="settings-panel" :class="{ active: activePanel === 'preferences' }">
        <h2>偏好设置</h2><p class="settings-subtitle">语言、主题、字体与面板布局等个性化偏好。</p>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">语言</div><div class="settings-row-desc">选择界面语言</div></div><div class="settings-row-control"><select class="settings-select"><option>中文</option></select></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">主题亮暗</div><div class="settings-row-desc">浅色、深色、或跟随系统</div></div><div class="settings-row-control"><select class="settings-select" v-model="theme" @change="handleSetTheme(theme)"><option value="night">深色</option><option value="day">浅色</option><option value="classic">经典</option></select></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">界面风格</div><div class="settings-row-desc">默认、玻璃、经典或羊皮纸外观</div></div><div class="settings-row-control"><select class="settings-select"><option>清透</option><option>默认</option><option>玻璃</option><option>经典</option><option>羊皮纸</option></select></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">对话字体</div><div class="settings-row-desc">对话内容使用无衬线或衬线字体</div></div><div class="settings-row-control"><select class="settings-select"><option>无衬线</option><option>衬线</option></select></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">对话字号</div><div class="settings-row-desc">调整对话中的文字大小</div></div><div class="settings-row-control"><select class="settings-select"><option>小</option><option selected>中</option><option>大</option></select></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">对话宽度</div><div class="settings-row-desc">对话区与输入框的最大宽度</div></div><div class="settings-row-control"><select class="settings-select"><option>默认</option><option>窄</option><option>宽</option></select></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">预览方式</div><div class="settings-row-desc">如何预览生成的文件（图片、Markdown）</div></div><div class="settings-row-control"><select class="settings-select"><option>新窗口</option><option>内嵌</option></select></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">提示词建议</div><div class="settings-row-desc">启用后，AI 完成回复后会自动生成下一步建议。需要开启新会话才能生效。</div></div><div class="settings-row-control"><button class="toggle-switch" :class="{ on: toggles.promptSuggest }" @click="toggles.promptSuggest = !toggles.promptSuggest" type="button"></button></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">默认展开工具调用</div><div class="settings-row-desc">关闭时对话中的工具调用默认折叠；开启后新建展示的工具默认展开。</div></div><div class="settings-row-control"><button class="toggle-switch" :class="{ on: toggles.expandTools }" @click="toggles.expandTools = !toggles.expandTools" type="button"></button></div></div>
      </div>

      <!-- 模型管理 -->
      <div class="settings-panel" :class="{ active: activePanel === 'models' }">
        <h2>模型管理</h2><p class="settings-subtitle">管理本地与云端模型、配置 API Key、查看路由策略。</p>
        <div class="settings-info-banner">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="18" height="18"><rect x="2" y="4" width="20" height="14" rx="2"/><line x1="8" y1="10" x2="16" y2="10"/><line x1="8" y1="14" x2="14" y2="14"/></svg>
          <div><div style="font-weight:600;color:var(--text-primary);font-size:13px;margin-bottom:2px">设备硬件状态</div><div style="font-size:12px;color:var(--text-tertiary)">{{ hwStatus }}</div></div>
          <button class="settings-btn" style="margin-left:auto;font-size:11px;padding:4px 10px" @click="checkHardware">重新检测</button>
        </div>
        <div class="settings-section-header"><div class="settings-section-header-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="16" height="16"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg></div>本地推理引擎 · Ollama</div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">Ollama 服务</div><div class="settings-row-desc">运行中</div></div><div class="settings-row-control"><div class="settings-status-row"><span class="settings-status-dot active" style="background:#22C55E"></span><span style="font-size:13px;color:var(--text-secondary)">运行中</span></div></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">已安装模型</div><div class="settings-row-desc">3 个模型可用</div></div><div class="settings-row-control"><button class="settings-btn" style="font-size:12px" @click="scanModels">刷新列表</button></div></div>
        <div style="display:flex;flex-wrap:wrap;gap:6px;padding:0 0 var(--space-4)"><span v-for="m in localModels" :key="m" class="entity-tag" :class="{ active: m === 'gemma4:latest' }" style="font-size:11px;padding:4px 10px;border-radius:99px;border:1px solid var(--border-subtle)">{{ m }}</span></div>
        <div class="settings-row" style="border-bottom:none"><div class="settings-row-info"><div class="settings-row-title">拉取新模型</div><div class="settings-row-desc">输入 Ollama 模型名一键拉取（如 llama3.2:3b）</div></div><div class="settings-row-control" style="display:flex;gap:6px"><input type="text" class="settings-input" v-model="pullModel" placeholder="llama3.2:3b" style="width:160px"><button class="settings-btn" style="font-size:12px;white-space:nowrap" @click="pullOllamaModel">拉取</button></div></div>
        <div class="settings-section-header"><div class="settings-section-header-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="16" height="16"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg></div>云端 API 模型</div>
        <div v-for="p in apiProviders" :key="p.id" class="settings-row"><div class="settings-row-info"><div class="settings-row-title">{{ p.name }}</div><div class="settings-row-desc">{{ p.desc }}</div></div><div class="settings-row-control" style="display:flex;align-items:center;gap:8px"><input type="password" class="settings-api-key-input" v-model="apikeyValues[p.id]" :placeholder="'sk-...'" style="width:240px"><button class="settings-api-test" @click="testAPIKey(p.id)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polyline points="20 6 9 17 4 12"/></svg>测试</button></div></div>
        <button class="settings-add-key" @click="showToast('添加自定义 API 端点','info')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>添加自定义 API 端点</button>
        <div class="settings-section-header" style="margin-top:var(--space-8)"><div class="settings-section-header-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="16" height="16"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg></div>模型路由策略</div>
        <p style="font-size:12px;color:var(--text-tertiary);margin:0 0 var(--space-4);line-height:1.5">太极引擎「分流调度」根据任务类型、成本约束和质量要求，自动选择最优模型。以下为当前路由规则：</p>
        <div v-for="r in routeRules" :key="r.task" class="settings-row"><div class="settings-row-info"><div class="settings-row-title">{{ r.task }}</div><div class="settings-row-desc">{{ r.model }}</div></div><div class="settings-row-control"><span style="font-size:12px;color:var(--text-secondary)">默认</span></div></div>
        <div class="settings-row" style="border-bottom:none"><div class="settings-row-info"><div class="settings-row-title">Token 紧急降级</div><div class="settings-row-desc">预算剩余 &lt; 10% 时自动切换最便宜模型</div></div><div class="settings-row-control"><button class="toggle-switch" :class="{ on: toggles.tokenDowngrade }" @click="toggles.tokenDowngrade = !toggles.tokenDowngrade" type="button"></button></div></div>
      </div>

      <!-- 个人资料 -->
      <div class="settings-panel" :class="{ active: activePanel === 'profile' }">
        <h2>个人资料</h2><p class="settings-subtitle">头像、账号与订阅信息。</p>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">头像</div><div class="settings-row-desc">点击上传自定义图片</div></div><div class="settings-row-control"><label class="settings-avatar-upload" style="cursor:pointer"><div class="settings-avatar-preview">刘</div><div class="settings-avatar-upload-hint"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg></div><input type="file" accept="image/*" style="display:none" @change="onAvatarChange"></label></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">账号名称</div><div class="settings-row-desc">显示在对话中与其他用户可见的名称</div></div><div class="settings-row-control"><input type="text" class="settings-input" v-model="accountName" style="width:180px"></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">背景色</div><div class="settings-row-desc">个性化头像背景颜色</div></div><div class="settings-row-control"><div class="avatar-color-picker"><div v-for="c in avatarColors" :key="c" class="avatar-color-dot" :class="{ active: avatarColor === c }" :style="{ background: c }" @click="avatarColor = c"></div></div></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">账号 UID</div><div class="settings-row-desc">用于问题反馈与技术支持</div></div><div class="settings-row-control" style="display:flex;align-items:center;gap:8px"><code style="font-family:var(--font-mono);font-size:13px;color:var(--text-primary);background:var(--bg-subtle);padding:2px 8px;border-radius:4px">1004565582732688</code><button class="settings-btn" @click="copyUID" style="font-size:12px">复制</button></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">订阅</div><div class="settings-row-desc">当前账户的套餐</div></div><div class="settings-row-control"><span class="security-status-badge encrypted">Pro</span></div></div>
        <div class="settings-row" style="border-bottom:none"><div class="settings-row-info"><div class="settings-row-title">退出登录</div><div class="settings-row-desc">在此设备退出登录，可随时重新登录</div></div><div class="settings-row-control"><button class="settings-btn danger" @click="doLogout">退出</button></div></div>
      </div>

      <!-- 系统设置 -->
      <div class="settings-panel" :class="{ active: activePanel === 'system' }">
        <h2>系统设置</h2><p class="settings-subtitle">开机自启动、保持唤醒、通知等系统级选项。</p>
        <div v-for="s in systemToggles" :key="s.key" class="settings-row"><div class="settings-row-info"><div class="settings-row-title">{{ s.title }}</div><div class="settings-row-desc">{{ s.desc }}</div></div><div class="settings-row-control"><button class="toggle-switch" :class="{ on: settingSystem[s.key] }" @click="settingSystem[s.key] = !settingSystem[s.key]"></button></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">关闭窗口行为</div><div class="settings-row-desc">点击窗口关闭按钮时的默认操作</div></div><div class="settings-row-control"><select class="settings-select"><option>每次询问</option><option>最小化到托盘</option><option>直接退出</option></select></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">网络代理</div><div class="settings-row-desc">配置应用的网络代理方式</div></div><div class="settings-row-control"><select class="settings-select"><option>跟随系统</option><option>手动配置</option></select></div></div>
        <div class="settings-row" style="border-bottom:none"><div class="settings-row-info"><div class="settings-row-title">数据共享</div><div class="settings-row-desc">你的提示词、上下文及使用数据将用于产品改进。更多信息可参考隐私政策。</div></div><div class="settings-row-control"><select class="settings-select"><option>共享改进模式</option><option>不共享</option></select></div></div>
      </div>

      <!-- 快捷键 -->
      <div class="settings-panel" :class="{ active: activePanel === 'shortcuts' }">
        <h2>快捷键</h2><p class="settings-subtitle">自定义通用、任务与会话操作的快捷键。</p>
        <div class="settings-shortcuts-search"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg><input type="text" placeholder="搜索快捷键..."></div>
        <div class="settings-shortcuts-table">
          <div class="settings-shortcuts-group"><div class="settings-shortcuts-group-title">通用</div><div class="settings-shortcut-row"><span>打开设置</span><span class="settings-shortcut-keys"><kbd>Ctrl</kbd><kbd>,</kbd></span></div><div class="settings-shortcut-row"><span>切换侧边栏</span><span class="settings-shortcut-keys"><kbd>Ctrl</kbd><kbd>\</kbd></span></div></div>
          <div class="settings-shortcuts-group"><div class="settings-shortcuts-group-title">任务</div><div class="settings-shortcut-row"><span>快速切换任务</span><span class="settings-shortcut-keys"><kbd>Ctrl</kbd><kbd>Tab</kbd></span></div><div class="settings-shortcut-row"><span>创建新任务</span><span class="settings-shortcut-keys"><kbd>Ctrl</kbd><kbd>N</kbd></span></div><div class="settings-shortcut-row"><span>搜索全部任务</span><span class="settings-shortcut-keys"><kbd>Ctrl</kbd><kbd>G</kbd></span></div><div class="settings-shortcut-row"><span>在当前任务中搜索</span><span class="settings-shortcut-keys"><kbd>Ctrl</kbd><kbd>F</kbd></span></div></div>
          <div class="settings-shortcuts-group"><div class="settings-shortcuts-group-title">会话</div><div class="settings-shortcut-row"><span>发送消息</span><span class="settings-shortcut-keys"><span style="font-size:11px;color:var(--text-dim);margin-right:4px">↵</span><span>/</span><kbd>Ctrl</kbd><span>+</span><kbd>↵</kbd></span></div><div class="settings-shortcut-row"><span>插入换行</span><span class="settings-shortcut-keys"><kbd>Shift</kbd><span>+</span><kbd>↵</kbd></span></div></div>
        </div>
        <div class="settings-card-section"><div class="settings-card-section-header"><div><div class="settings-card-section-title">启用 QuickPick</div><div class="settings-card-section-desc">启用全局快速任务窗口，无需切换到主窗口即可随时提交任务。</div></div><button class="toggle-switch" :class="{ on: toggles.quickPick }" @click="toggles.quickPick = !toggles.quickPick" type="button"></button></div></div>
      </div>

      <!-- 任务看板 -->
      <div class="settings-panel" :class="{ active: activePanel === 'kanban' }">
        <h2>任务看板</h2><p class="settings-subtitle">Swarm 多 Agent 任务编排看板，拖拽卡片管理任务状态。</p>
        <div class="kanban-ws-bar"><button class="kanban-ws-btn" title="选择工作间"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2" width="14" height="14"><rect x="1" y="1" width="14" height="12" rx="2"/><path d="M1 5h14"/><path d="M5 5v8"/></svg><span>默认工作间</span><svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.2" width="10" height="10"><path d="M3 5l3 3 3-3" stroke-linecap="round" stroke-linejoin="round"/></svg></button><button class="kanban-refresh-btn" title="刷新" @click="showToast('看板已刷新','success')"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14"><path d="M2 8a6 6 0 0111.33-2.5M14 8a6 6 0 01-11.33 2.5" stroke-linecap="round"/><path d="M13.5 3v2.5H11M2.5 13v-2.5H5" stroke-linecap="round" stroke-linejoin="round"/></svg></button></div>
        <div class="kanban-board">
          <div class="kanban-col" v-for="col in kanbanCols" :key="col.id"><div class="kanban-col-hdr"><span class="kanban-col-dot" :style="{ background: col.color }"></span><span>{{ col.label }}</span><span class="kanban-col-cnt">0</span></div><div class="kanban-col-list"></div></div>
        </div>
      </div>

      <!-- 太极引擎 -->
      <div class="settings-panel" :class="{ active: activePanel === 'taiji' }">
        <div style="text-align:center;margin-bottom:var(--space-4)"><h2 style="margin:0">太极引擎</h2><p class="settings-subtitle" style="margin-bottom:0">AI 核心引擎运行状态与能力管理。太极七律驱动，九大模块协同。</p></div>
        <div class="settings-section-header"><div class="settings-section-header-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 0 1 0 20"/><circle cx="12" cy="12" r="3"/></svg></div>核心引擎</div>
        <div v-for="m in taijiModules" :key="m.name" class="settings-row"><div class="settings-row-info"><div class="settings-row-title">{{ m.name }}</div><div class="settings-row-desc">{{ m.desc }}</div></div><div class="settings-row-control"><span class="security-status-badge encrypted">运行中</span></div></div>
        <div class="settings-section-header"><div class="settings-section-header-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg></div>太极七律</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--space-3);margin-top:var(--space-2)"><div v-for="(law, i) in taijiLaws" :key="i" style="padding:var(--space-3);background:var(--bg-subtle);border-radius:var(--radius-sm);border:1px solid var(--border-subtle);font-size:12px;color:var(--text-secondary)" :style="i > 5 ? 'grid-column:1/-1;text-align:center' : ''"><span style="font-weight:600;color:var(--brand)">Law {{ String(i + 1).padStart(2, '0') }}</span> {{ law }}</div></div>
      </div>

      <!-- 意识 -->
      <div class="settings-panel" :class="{ active: activePanel === 'awareness' }">
        <h2>意识</h2><p class="settings-subtitle">定制协作风格与工作手册，赋予超级牛马跨会话记忆与技能进化能力。</p>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">意识模式</div><div class="settings-row-desc">启用跨会话记忆与技能进化能力</div></div><div class="settings-row-control"><button class="toggle-switch" :class="{ on: toggles.awarenessMode }" @click="toggles.awarenessMode = !toggles.awarenessMode" type="button"></button></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">自动记忆</div><div class="settings-row-desc">自动维护用户画像与长短期记忆，定期触发记忆反思</div></div><div class="settings-row-control"><button class="toggle-switch" :class="{ on: toggles.autoMemory }" @click="toggles.autoMemory = !toggles.autoMemory" type="button"></button></div></div>
        <div class="settings-section-header"><span class="settings-section-header-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg></span>进化动态</div>
        <div class="awareness-chart-area"><div class="awareness-chart-header"><div class="awareness-chart-title">记忆趋势</div><div class="awareness-chart-tabs"><button class="awareness-chart-tab active">天</button><button class="awareness-chart-tab">周</button><button class="awareness-chart-tab">月</button></div></div><div class="awareness-chart-placeholder">趋势图表将在收集足够数据后显示</div></div>
        <div class="awareness-stats-row"><span>今日：0 次审查 · 0 条记忆 · 0 个技能 · 0 次反思</span></div>
        <div class="settings-section-header"><span class="settings-section-header-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></span>记忆日志</div>
        <div class="awareness-log-list">
          <div class="awareness-log-item"><div class="awareness-log-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></div><div class="awareness-log-content"><div class="awareness-log-text">记忆反思：将设计工作流习惯与品牌设计偏好合并为一条，减少冗余</div><div class="awareness-log-time">4 天前</div></div></div>
          <div class="awareness-log-item"><div class="awareness-log-icon" style="color:var(--brand)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg></div><div class="awareness-log-content"><div class="awareness-log-text">用户画像：品牌设计偏好 — 单主色+黑白辅色，反对多色品牌体系</div><div class="awareness-log-time">4 天前</div></div></div>
        </div>
        <div class="settings-section-header" style="margin-top:var(--space-6)"><span class="settings-section-header-icon" style="background:rgba(239,68,68,.08);color:#ef4444;border-color:rgba(239,68,68,.15)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></span>危险操作</div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">重置协作风格</div><div class="settings-row-desc">清除当前配置，可通过个性化重新选择</div></div><div class="settings-row-control"><button class="settings-btn danger" @click="showToast('协作风格已重置','warning')">重置</button></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">重置工作手册</div><div class="settings-row-desc">恢复为初始模板，当前内容将被覆盖</div></div><div class="settings-row-control"><button class="settings-btn danger" @click="showToast('工作手册已重置','warning')">重置</button></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">清空记忆</div><div class="settings-row-desc">删除所有长短期记忆数据，此操作不可撤销</div></div><div class="settings-row-control"><button class="settings-btn danger" @click="showToast('记忆已清空','error')">清空</button></div></div>
      </div>

      <!-- 安全中心 -->
      <div class="settings-panel" :class="{ active: activePanel === 'security' }">
        <h2>安全中心</h2><p class="settings-subtitle">数据保护、隐私控制、安全防护与实验特性。</p>
        <div class="settings-section-header"><div class="settings-section-header-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></div>安全环境</div>
        <div class="settings-info-banner"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg><span>任务在隔离环境中运行，你的文件和数据始终保留在本地设备。</span></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">安全运行环境</div><div class="settings-row-desc">开启后任务与你的系统隔离</div></div><div class="settings-row-control"><button class="toggle-switch" :class="{ on: toggles.secureEnv }" @click="toggles.secureEnv = !toggles.secureEnv" type="button"></button></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">清理缓存环境</div><div class="settings-row-desc">释放临时文件占用的磁盘空间</div></div><div class="settings-row-control"><button class="settings-btn danger" @click="showToast('缓存已清理','success')">清理</button></div></div>
        <div class="settings-section-header"><div class="settings-section-header-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg></div>数据与隐私</div>
        <div class="settings-info-banner privacy"><svg viewBox="0 0 24 24" fill="none" stroke="var(--brand)" stroke-width="2" width="16" height="16"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg><span>最小数据原则：功能默认关闭，由你主动授权。</span></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">使用情况统计</div><div class="settings-row-desc">匿名发送使用数据帮助改进产品</div></div><div class="settings-row-control"><button class="toggle-switch" :class="{ on: toggles.usageStats }" @click="toggles.usageStats = !toggles.usageStats" type="button"></button></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">工作间数据隔离</div><div class="settings-row-desc">不同Agent之间数据互不干扰</div></div><div class="settings-row-control"><span class="security-status-badge protected">已保护</span></div></div>
        <div class="settings-section-header"><div class="settings-section-header-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></div>安全防护</div>
        <div v-for="s in securityItems" :key="s.title" class="settings-row"><div class="settings-row-info"><div class="settings-row-title">{{ s.title }}</div><div class="settings-row-desc">{{ s.desc }}</div></div><div class="settings-row-control"><span class="security-status-badge" :class="s.badgeClass">{{ s.badge }}</span></div></div>
        <div class="settings-section-header"><div class="settings-section-header-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg></div>实验特性</div>
        <div style="font-size:12px;color:var(--text-tertiary);margin:0 0 var(--space-4)">抢先体验新功能，部分仍在打磨中，可随时关闭。</div>
        <div v-for="exp in experimentItems" :key="exp.title" class="settings-row"><div class="settings-row-info"><div class="settings-row-title">{{ exp.title }}</div><div class="settings-row-desc">{{ exp.desc }}</div></div><div class="settings-row-control"><button class="toggle-switch" :class="{ on: exp.on }" @click="exp.on = !exp.on"></button></div></div>
      </div>

      <!-- 已归档 -->
      <div class="settings-panel" :class="{ active: activePanel === 'archived' }">
        <h2>已归档</h2><p class="settings-subtitle">查看和管理已归档的会话。</p>
        <div class="archived-empty"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg><div class="archived-empty-title">暂无已归档会话</div><div style="font-size:12px;color:var(--text-tertiary);margin-top:4px">在对话列表中右键可归档对话</div></div>
      </div>

      <!-- 关于 -->
      <div class="settings-panel" :class="{ active: activePanel === 'about' }">
        <h2>关于</h2><p class="settings-subtitle">版本信息、检查更新、反馈与帮助。</p>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">超级牛马工作台</div><div class="settings-row-desc">太极引擎 · Hermes Agent · 八个极致</div></div><div class="settings-row-control"><span style="font-size:13px;color:var(--text-primary);font-weight:500">v1.5.0</span></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">检查更新</div><div class="settings-row-desc">有新版本时会自动提示下载与安装</div></div><div class="settings-row-control"><button class="settings-btn" style="background:var(--text-primary);color:var(--bg-surface);border-color:var(--text-primary)" @click="checkVersion">检查更新</button></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">更新日志</div><div class="settings-row-desc">查看版本更新历史</div></div><div class="settings-row-control"><button class="settings-btn" @click="showToast('打开更新日志','info')">查看</button></div></div>
        <div class="settings-row"><div class="settings-row-info"><div class="settings-row-title">反馈与帮助</div><div class="settings-row-desc">遇到问题或有建议？</div></div><div class="settings-row-control"><button class="settings-btn" @click="showToast('已记录反馈，感谢！','success')">反馈</button></div></div>
      </div>
    </div>
  </div>

  <!-- Logout Confirm -->
  <div class="modal-overlay" v-if="confirmLogout" @click.self="confirmLogout = false">
    <div class="modal" style="max-width:360px"><div class="modal-hd"><h3>确认退出</h3><button class="modal-close" @click="confirmLogout = false">×</button></div><div class="modal-body"><p>确定要退出登录吗？</p></div><div class="modal-ft"><button class="modal-btn-cancel" @click="confirmLogout = false">取消</button><button class="modal-btn-confirm" style="background:var(--coral)" @click="confirmLogoutAction">退出</button></div></div>
  </div>
</div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useToast } from '@/composables/useToast'
const { showToast } = useToast()

const activePanel = ref('preferences')
const theme = ref('night')
const hwStatus = ref('CPU: 12核 · RAM: 32GB · GPU: RTX 4060')
const pullModel = ref('')
const accountName = ref('刘淮安')
const avatarColor = ref('#fff')
const confirmLogout = ref(false)

const avatarColors = ['#fff','#F472B6','#A78BFA','#FCD34D','#FB923C','#34D399','#60A5FA','#9CA3AF','#4B5563']
const localModels = ['gemma4:latest', 'qwen2.5:7b', 'bge-m3:latest']

const apiProviders = [
  { id: 'deepseek', name: 'DeepSeek', desc: '1.6T MoE · 1M 上下文 · 代码/分析/推理' },
  { id: 'kimi', name: 'Kimi (月之暗面)', desc: '中文写作场景最强 · K2.6' },
  { id: 'hunyuan', name: '腾讯混元', desc: '中文深度好 · 微信生态集成' },
  { id: 'glm', name: '智谱 GLM-4', desc: '清华系 · 通用能力强 · 本地量化版可选' },
]
const apikeyValues = reactive<Record<string, string>>({})

const routeRules = [
  { task: '写代码', model: 'DeepSeek V4 · 代码生成/审查/重构' },
  { task: '写文章', model: 'Kimi K2.6 · 中文写作/文案/长文' },
  { task: '分析研究', model: 'DeepSeek V4 · 数据分析/策略推演' },
  { task: '日常对话', model: 'Gemma-4（本地）· 零成本随聊' },
  { task: '图片理解', model: 'Qwen2.5-VL（本地）· OCR/图表/文档' },
  { task: '深度推理', model: 'DeepSeek R1 · 数学/逻辑/思维链' },
]

const systemToggles = [
  { key: 'autoStart' as const, title: '开机自动启动', desc: '登录电脑时自动启动超级牛马工作台' },
  { key: 'keepAwake' as const, title: '保持系统唤醒', desc: '防止电脑在 Agent 工作时自动进入睡眠' },
  { key: 'desktopNotify' as const, title: '桌面通知', desc: 'Agent 等待回复或完成工作时，发送系统通知提醒你' },
  { key: 'soundNotify' as const, title: '声音通知', desc: 'Agent 完成工作时播放提示音' },
]
const toggles = reactive({
  promptSuggest: true, expandTools: false, tokenDowngrade: true,
  quickPick: false, awarenessMode: true, autoMemory: true,
  secureEnv: true, usageStats: true
})
const settingSystem = reactive({ autoStart: false, keepAwake: true, desktopNotify: true, soundNotify: true })

const kanbanCols = [{ id: 'backlog', label: '待处理', color: 'var(--text-tertiary)' },{ id: 'in-progress', label: '进行中', color: 'var(--brand)' },{ id: 'review', label: '审查中', color: '#F59E0B' },{ id: 'done', label: '已完成', color: '#22C55E' }]

const taijiModules = [
  { name: '铭心 · 记忆加载', desc: '跨会话记忆自动加载与上下文注入' },
  { name: '缩龙成寸 · 压缩引擎', desc: '智能压缩历史对话，节省 Token 消耗' },
  { name: '太虚境 · 嵌入引擎', desc: '文本向量化与语义检索' },
  { name: '夜巡 · 自动巡检', desc: '定期检查系统健康与异常预警' },
  { name: '分流调度 · 模型路由', desc: '根据任务类型自动选择最优模型' },
  { name: '自化 · 技能锻造', desc: '根据使用习惯自动生成和优化技能' },
  { name: '清风 · 数据生命周期', desc: '自动清理过期缓存与临时数据' },
  { name: 'Hermes 适配层', desc: 'Agent 多实例调度与能力协同' },
  { name: '运行时接口', desc: '统一 API 网关与请求分发' },
]
const taijiLaws = ['极致安全','极致性能','极致自治','极致准确','极致效率','刚柔并济','极致克制 · Pi 原则']

const securityItems = [
  { title: '请求频率保护', desc: '自动防御异常高频访问', badge: '保护中', badgeClass: 'protected' },
  { title: '流量管控', desc: '限制异常请求，保障服务稳定', badge: '保护中', badgeClass: 'protected' },
  { title: '联网权限管控', desc: '联网搜索等外网功能默认关闭', badge: '已管控', badgeClass: 'controlled' },
  { title: '密钥安全存储', desc: 'API密钥本地加密', badge: '已加密', badgeClass: 'encrypted' },
  { title: '安全审计', desc: '定期检查安全配置与运行健康', badge: '良好', badgeClass: 'protected' },
]
const experimentItems = reactive([
  { title: '生成式 UI', desc: 'AI可在聊天中直接渲染图表、仪表盘等交互组件', on: true },
  { title: '独立窗口运行', desc: '任务可弹出为独立窗口，不阻塞主界面操作', on: false },
  { title: '对话列表筛选', desc: '支持按项目、活跃时间和分组过滤对话', on: false },
])

function handleSetTheme(val: string) { document.documentElement.setAttribute('data-theme', val); localStorage.setItem('niuma_theme', val) }
function checkHardware() { showToast('正在检测硬件...','info'); setTimeout(() => showToast('硬件检测完成: 全部正常','success'), 1200) }
function scanModels() { showToast('模型列表已刷新','success') }
function pullOllamaModel() { if (!pullModel.value.trim()) return showToast('请输入模型名','warning'); showToast('正在拉取 ' + pullModel.value + '...','info') }
function testAPIKey(id: string) { const p = apiProviders.find(x=>x.id===id); showToast((p?p.name:id) + ' API Key 测试中...','info'); setTimeout(()=>showToast('验证通过','success'), 1000) }
function copyUID() { navigator.clipboard.writeText('1004565582732688'); showToast('已复制','success') }
function onAvatarChange(e: Event) { const f = (e.target as HTMLInputElement).files?.[0]; if (f) showToast('头像已上传: '+f.name,'success') }
function doLogout() { confirmLogout.value = true }
function confirmLogoutAction() { confirmLogout.value = false; showToast('已退出登录','success') }
function checkVersion() { showToast('正在检查...','info'); setTimeout(()=>showToast('当前已是最新版本 v1.5.0','success'), 1000) }
</script>
