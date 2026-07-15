# HTML原型 vs Vue前端 100%还原对比报告

> 生成时间: 2026-07-13 | 原型文件: `frontend/niuma-neon-pulse-prototype.html` (0.9MB/~11K行CSS)

---

## 一、CSS/Style 还原度评估

### 1.1 CSS文件体积对比

| 来源 | 行数 | 文件数 | 状态 |
|------|------|--------|:--:|
| HTML原型 `<style>` | ~11,000行 | 1个 | 唯一真相源 |
| Vue `public/css/` | ~4,300行 | 7个 | 约39% |

### 1.2 缺失的CSS变量（首批关键）

| 变量名 | 用途 | 影响 |
|--------|------|------|
| `--gn` (短变量) | 多处硬编码使用 | 多处颜色丢失 |
| `--am` / `--cr` / `--cy` / `--te` / `--pu` | 5个短变量，标签/状态色 | 活跃标签颜色丢失 |
| `--interactive-gradient` | `.nav-create-btn` 背景 | 按钮无渐变 |
| `--icon-bg-purple/green/cyan/amber/wip` | 应用图标背景 | Icon卡片背景异常 |
| `--icon-ollama/gbrain/mcp/rag` | 图标渐变 | 连接器图标异常 |
| `--brand-active` | 品牌激活色 | 按钮按下态异常 |
| `--silver` / `--silver-light` / `--silver-dark` | 银色系 | Tab切换等效果缺失 |
| `--glass-bg-nav` | 导航底栏毛玻璃 | 导航栏背景异常 |
| `--energy-gradient` | 能量脉冲渐变 | 徽章动画异常 |

### 1.3 主题层差异

| 属性 | HTML原型 | Vue | 差异 |
|------|----------|-----|------|
| Night默认 | `data-theme="night"` CSS在`:root` | `data-theme="night"` CSS在`semantics.css` | 基本一致 |
| Day切换 | `data-theme="day"` | `data-theme="light"` | **属性名不一致** |
| Classic配色 | `#F2EDE5`底色,暖米纸本感 | `#FDF8F0`底色,更亮白 | **色值不同** |
| Classic品牌色 | `#467DA8`蓝色调 | `#B8860B`金色调 | **完全不同的设计语言** |

### 1.4 缺失的CSS组件类（关键）

以下CSS类在HTML原型中存在，但Vue的`components-base.css` / `chat-components.css`中缺失：

| 缺失CSS类 | 影响组件 |
|-----------|----------|
| `.agent-info-popup` 全套样式 | Agent信息弹窗 |
| `.compressed-banner` 全套样式 | 消息压缩横幅 |
| `.load-earlier-entry` 样式 | 加载更早按钮 |
| `.input-attach-strip` 样式 | 附件缩略图区 |
| `.queue-area` 样式 | 队列任务面板 |
| `.mention-section-label` / `.plus-menu-sep` | @提及菜单分隔 |
| `.as-card-extra` / `.as-channel-row` 样式 | Side Panel渠道行 |
| `.conn-status-bar` 样式 | 连接状态栏 |
| `.plaza-banner-bar` 样式 | 广场过滤Tab |
| `.lab-hero` / `.lab-pulse-ring` 全套 | 实验室内核动画 |
| `.wf-metric` / `.wf-right` 细节间距 | 底部状态栏 |

---

## 二、交互逻辑还原度

### 2.1 已正确还原的交互

| 交互 | Vue实现 | 还原度 |
|------|---------|:--:|
| 7个导航Tab切换 | router-view + nav-btn | 100% |
| 主题循环切换 | cycleTheme() + data-theme | 90% |
| 账户面板开闭 | accountOpen ref | 100% |
| 对话Sidebar创建菜单 | createOpen ref | 100% |
| Side Panel开闭 | v-model | 100% |
| Resize Handle拖拽 | mousedown events | 100% |
| 消息右键菜单 | ContextMenu组件 | 100% |
| 输入区模型选择 | model-dropdown | 100% |

### 2.2 缺失的交互（HTML原型有，Vue缺失）

| 交互 | 原型实现 | 严重度 | Vue缺失内容 |
|------|----------|:--:|------|
| **Agent头像点击弹窗** | `agent-info-popup` + `openPanelPage()` | P0 | 整个`agent-info-popup` DOM完全缺失 |
| **消息压缩横幅** | `compressed-banner` 可展开摘要 | P0 | 压缩横幅和扩展交互完全缺失 |
| **队列任务面板** | `queue-area` + 上下移/关闭 | P1 | 队列系统未实现 |
| **输入区[@]提及菜单** | `mentionMenu` + `insertMention()` | P1 | 只保留[+]菜单，@和连接器菜单缺失 |
| **输入区连接器菜单** | `connectorMenu` + 状态指示 | P1 | 同上 |
| **工作目录选择** | `work-dir-trigger` 展开文件树 | P1 | 仅占位按钮，无实际功能 |
| **语音输入** | 录音状态切换 | P2 | 仅占位按钮 |
| **加载更早对话** | `load-earlier-btn` + 滚动监听 | P1 | 按钮完全缺失 |
| **项目搜索过滤(N.filterProjects)** | 实时过滤 | P1 | 搜索框无过滤逻辑 |
| **项目卡片删除(N.deleteProject)** | 确认弹窗+DOM移除 | P1 | 删除仅Toast提示 |
| **多处toggle交互** | `classList.toggle('open')` | P1 | 内联DOM操作替代响应式 |

### 2.3 文字/标签差异

| 位置 | HTML原型 (中文) | Vue (英文/不同) | 影响 |
|------|----------------|-----------------|------|
| 账户面板名称 | `刘淮安` | `Liu Huai An` | 品牌一致性 |
| 账户设置项1 | `系统设置` | `Settings` | 语言不统一 |
| 账户设置项2 | `个性偏好` | `Preferences` | 同上 |
| 账户设置项3 | `个人资料` | 缺失 | 缺1项 |
| 账户设置项4 | `订阅管理` | `Subscription` | 语言不统一 |
| 主题切换标签 | `切换主题` / `深色` | `Theme` / `Dark` | 同上 |
| 退出按钮 | `退出登录` | `Logout` | 同上 |
| 底部品牌名 | `超级牛马` | `Super Niuma` | 同上 |
| 底部状态 | `在线` / `当前·默认工作区` | `Online` / `Current: Default` | 同上 |
| 输入框placeholder | `描述任务，/ 快捷调用，@ 添加上下文` | `描述任务 / @ 快捷调用 / + 添加上下文` | 轻微差异 |
| HTML title | `超级牛马` | `瓒呭骇鐗涢┈` (编码乱码) | P0 乱码 |

---

## 三、页面级对比

### ChatView — 核心对话页

| 原型组件 | Vue状态 | 差距 |
|----------|---------|:--:|
| Chat Sidebar (对话列表+搜索) | 基本还原 | 缺搜索框、平台Agent卡片、section分隔线 |
| Chat Header | 基本还原 | 缺Agent信息弹窗、缺"分享"菜单项 |
| Messages Area (消息列表) | 基本还原 | 缺压缩横幅、缺加载更早按钮 |
| Input Area (输入区域) | 部分还原 | 缺队列面板、缺@提及菜单、缺连接器菜单 |
| Side Panel | 基本还原 | 缺项目设置面板细节 |

### ProjectsView

| 功能 | Vue | 差距 |
|------|-----|:--:|
| 项目卡片网格 | ✅ | - |
| 实时搜索过滤 | ❌ 无逻辑 | searchQuery未绑定到filteredProjects |
| 项目下拉菜单 | ⚠️ 内联DOM | 用classList.toggle，非响应式 |
| 删除项目 | ❌ 仅Toast | 原型有N.deleteProject()确认弹窗 |
| 从模板创建 | ✅ | - |
| 10个模板 | ✅ | 全部还原 |

### PlazaView

| 功能 | Vue | 差距 |
|------|-----|:--:|
| 过滤Tab (全部/技能/专家/模型) | ⚠️ 无逻辑 | activeFilter未绑定过滤 |
| 搜索 | ❌ 无逻辑 | searchQuery未绑定 |
| 卡片展示 | ✅ | - |

### MemoryView

| 功能 | Vue | 差距 |
|------|-----|:--:|
| SVG知识图谱 | ✅ | - |
| 4个Tab切换 | ❌ 无交互 | 点击无切换 |
| 日记/做梦/长期记忆内容 | ❌ 缺失 | 无对应面板 |

### FilesView

| 功能 | Vue | 差距 |
|------|-----|:--:|
| Agent文件树 | ✅ | - |
| 工作台/本地视图切换 | ⚠️ 不完整 | 两个panel显隐依赖CSS .active，未用Vue控制 |
| 本地文件面板 | ❌ 空状态 | 无数据 |
| 搜索 | ❌ 无逻辑 | - |

### ConnectionsView

| 功能 | Vue | 差距 |
|------|-----|:--:|
| 连接卡片 | ✅ | - |
| Toggle开关 | ✅ | - |
| 开关持久化 | ❌ | 刷新丢失 |

### LabView

| 功能 | Vue | 差距 |
|------|-----|:--:|
| 太极动画 | ✅ | - |
| Token图表 | ✅ | - |
| 引擎模块拓扑 | ✅ | - |

### SettingsView

| 功能 | Vue | 差距 |
|------|-----|:--:|
| 9个设置面板 | ✅ | - |
| 设置持久化 | ❌ | 刷新丢失 |
| 主题设置在设置页 | ⚠️ 仅前端 | 与App.vue中cycleTheme分离 |

---

## 四、编码级别问题

| 编号 | 问题 | 文件 | 严重度 |
|:--:|------|------|:--:|
| B1 | `index.html` title编码乱码 | `index.html` | P0 |
| B2 | ChatMessages.vue第8行乱码 | `ChatMessages.vue:8` | P0 |
| B3 | `cleanupListener` 未声明 | `ChatMessages.vue:122` | P0 |
| B4 | Conversation接口不匹配 | ChatView ↔ ChatSidebar | P0 |
| B5 | `chatApi.sendMessage` 签名不匹配 | ChatView ↔ api.ts | P0 |
| B6 | `connectStream` 回调签名不匹配 | ChatView ↔ api.ts | P0 |
| B7 | `src/styles/themes.css` 未被任何文件引入 | 全局 | P1 |
| B8 | `src/styles/animations.css` 未被任何文件引入 | 全局 | P1 |
| B9 | ToastContainer/Badge/Toggle/Skeleton/GlobalSearch被定义但未使用 | 全局 | P1 |
| B10 | useSSE/useDropdown composable未被使用 | 全局 | P1 |
| B11 | Pinia已安装但无store | 全局 | P2 |
| B12 | 无404路由 | router | P2 |

---

## 五、还原度总结

| 维度 | 还原度 | 说明 |
|------|:--:|------|
| **整体CSS Token** | 60% | 核心Token已迁移，但短变量、玻璃效果、图标渐变缺失 |
| **主题系统** | 70% | Night基本一致，Light/Day属性名不一致，Classic色值完全不同 |
| **导航&布局** | 90% | 结构完整，仅中文文字替换为英文 |
| **Chat对话页** | 65% | 核心框架完整，缺Agent弹窗、压缩横幅、@提及、连接器菜单、队列 |
| **Projects页** | 80% | 结构完整，缺搜索过滤逻辑、项目删除交互 |
| **Plaza页** | 60% | 缺过滤和搜索功能 |
| **Memory页** | 40% | 知识图谱OK，但Tab切换和内容面板缺失 |
| **Files页** | 50% | 文件树OK，但列表数据缺失，视图切换不完整 |
| **Connections页** | 85% | 基本完整，缺持久化 |
| **Lab页** | 85% | 基本完整 |
| **Settings页** | 80% | 面板完整，缺持久化 |
| **Footer** | 85% | 结构完整，中文改英文 |
| **整体平均** | **~72%** |  |

---

## 六、优化路线图（按P0→P2排序）

### P0 — 阻断级（必须立即修复）

| 编号 | 任务 | 预估 |
|:--:|------|:--:|
| P0-1 | 修复 `index.html` title 和 ChatMessages 编码乱码 | 5min |
| P0-2 | 修复 `cleanupListener` 未声明错误 | 10min |
| P0-3 | 统一 Conversation 接口定义，补齐 `type/preview/avatarStyle/time` | 30min |
| P0-4 | 修复 `chatApi.sendMessage` / `connectStream` 签名和返回值不匹配 | 1h |
| P0-5 | 统一三主题CSS变量体系，将Day/Classic色值对齐原型 | 2h |

### P1 — 高优先（影响核心体验）

| 编号 | 任务 | 预估 |
|:--:|------|:--:|
| P1-1 | 补齐缺失CSS变量（--gn/am/cr/cy/te/pu/interactive-gradient/icon-*/silver*/glass-bg-nav等） | 1h |
| P1-2 | 补齐缺失CSS组件类（agent-info-popup/compressed-banner/queue-area/conn-status-bar等） | 2h |
| P1-3 | ChatView: 实现Agent头像点击弹窗交互 | 1.5h |
| P1-4 | ChatView: 实现消息压缩横幅组件 | 1h |
| P1-5 | ChatView: 实现输入区[@]提及菜单 + 连接器菜单 | 1.5h |
| P1-6 | ChatView: 实现加载更早对话按钮 | 30min |
| P1-7 | ChatView: 恢复队列任务面板 | 1h |
| P1-8 | 统一全站中文文字标签（账户面板/底部/footer等） | 30min |
| P1-9 | 删除项目时添加确认弹窗交互 | 30min |
| P1-10 | Plaza页：实现过滤Tab + 搜索功能 | 1h |
| P1-11 | Memory页：实现4个Tab切换 + 日记/做梦/长期记忆面板内容 | 1.5h |
| P1-12 | Files页：实现视图切换完整逻辑 + 本地文件面板 | 1h |

### P2 — 中优先（增强完善）

| 编号 | 任务 | 预估 |
|:--:|------|:--:|
| P2-1 | 引入 `src/styles/themes.css` 和 `animations.css` 到构建流程 | 20min |
| P2-2 | 挂载 GlobalSearch 全局搜索组件到 App.vue | 30min |
| P2-3 | 替换视图中的 toggle 内联DOM操作为响应式 | 30min |
| P2-4 | 创建 Pinia store 用于主题/设置持久化 | 1h |
| P2-5 | 添加 404 路由 | 10min |
| P2-6 | 引入 useSSE / useDropdown composable 减少重复代码 | 30min |
| P2-7 | 修复 ChatMessages 中 `v-html` 的 XSS 风险（收紧 DOMPurify 白名单） | 20min |
| P2-8 | Footer 计时器实现 | 10min |

---

**总计**: P0: 5项(~4h) | P1: 12项(~13h) | P2: 8项(~3.5h) | **合计 ~20.5h (约2.5人天)**
