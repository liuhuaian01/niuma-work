# 超级牛马前端 · 原型 vs Vue 迁移版 对比测试报告

> 组建跨职能产品团队（PM / QA / UX / UI / Tech Lead）对 `frontend/public/app.html`（方案一，唯一真相源）与 `frontend-vue/src/views/` 迁移版做整体比对测试。
> 审计日期：2026-07-06
> 结论摘要：导航结构（7 Tab + 设置）100% 落地，视觉还原度 ~99.8%，构建/类型检查健康；**但交互逻辑大面积停留在"占位 toast / 无事件绑定"阶段，ChatView 内大量原型函数未迁移，存在 XSS 安全与内存泄漏隐患。**

---

## 一、总体结论

| 维度 | 评分 | 说明 |
|------|------|------|
| 导航/信息架构 | ✓ 完整 | 7 Tab + 设置路由齐全，路由可直达可后退（优于原型） |
| 视觉还原度 | ⭐ 99.8% | design-tokens.css 与原型内联 CSS 仅 51 行差异，63 个 @keyframes 全对齐；Vue 还修了原型 `--gn` 未定义、折叠态漏光两处缺陷 |
| 动效还原度 | ⭐ 100% | Toast/Processing/Thinking/消息出现动画触发逻辑与 CSS 一一对应 |
| 交互完整性 | ✗ 严重缺失 | ChatView 内 40+ 处交互死按钮/仅 toast；6 个占位页面几乎全为 toast 空壳 |
| 代码质量 | ⚠ 待补强 | 命令式 DOM 替代 ref/v-model、v-html XSS、定时器未清理、ChatView 超 1000 行未拆分 |
| 可访问性 | ⚠ 退化 | 缺 aria-expanded/role/tabindex；菜单无外部关闭/Esc |

**核心判断**：迁移处于"骨架已搭、视觉已还原、逻辑未迁"的中途状态。发布前必须把"占位 toast"逐条替换为真实逻辑，并补齐安全/生命周期短板。

---

## 二、统一问题清单（按严重程度）

### 🔴 P0 · 阻塞核心体验（必须修）

**P0-1 侧栏「+ 新建」按钮死按钮 + 缺"新建项目"项**
- 证据：QA / PM / UX / UI / QA-A1 交叉确认
- 原型：`app.html:11733` `sidebarCreateBtn.onclick` 展开菜单（新建 Agent / 新建项目）
- Vue：`ChatView.vue:7` 无 `@click`；`#sidebarCreateMenu`(10-21) 无 `:class="{open}"`；"新建项目"整项缺失
- 影响：创建是最高频任务，点击零反馈，用户判定功能损坏

**P0-2 「+」菜单 添加文件/文件夹/技能 仅 toast**
- 原型：`app.html:12195-12197` 触发 `hiddenFileInput/HiddenFolderInput.click()` → `handleFileSelect`；技能面板 `openSkillPanel`
- Vue：`ChatView.vue:163-165` 仅 `showToast(...)`；无隐藏 input 与选择逻辑
- 影响：上下文上传、技能装配能力缺失

**P0-3 Agent 设置面板全部编辑交互未绑定**
- 原型：`app.html:12343-12403` 修改/保存/取消/头像/渠道开关
- Vue：`ChatView.vue:256/262/269/270/316` 均无 `@click`
- 影响：用户信息编辑、头像上传、渠道开关全失效

**P0-4 项目设置面板编辑交互未绑定**
- 原型：`app.html:12572-12603`
- Vue：`ChatView.vue:485/491/498/499/509-517` 均无 `@click`

**P0-5 后台任务「终止」按钮无事件**
- 原型：`app.html:12638/12652` 终止视觉反馈
- Vue：`ChatView.vue:553/567` 无 `@click`

**P0-6 文件面板 Tab/搜索/树展开全失效**
- 原型：`app.html:12504-12540` `switchFileTab/fileSearchInputChanged/clearFileSearch/树 toggle`
- Vue：`ChatView.vue:417-425/434/441/453` 均无绑定

**P0-7 日历翻月失效**
- 原型：`app.html:12459/12461` `shiftCalendarMonth(±1)`
- Vue：`ChatView.vue:372/374` 无 `@click`，月份标签静态

**P0-8 搜索历史 输入过滤 + 卡片点击失效**
- 原型：`app.html:12696` `filterSearchHistory` + 卡片打开历史
- Vue：`ChatView.vue:611/615+` 无绑定

**P0-9 所有下拉菜单无外部点击/Esc 关闭（系统性）**
- 原型：`app.html` 12 处 `document.addEventListener('click', close)`
- Vue：`ChatView.vue:826` `toggleMenu` 仅切 `openMenu`；grep 确认全文件无 outside-click 监听
- 影响：更多/+ @ /连接器/模型 任一菜单打开后常驻遮挡

**P0-10 项目设置面板不可达（死代码）**
- `ChatView.vue:477` `panelPageProjectSettings` 已实现，但全代码无分支将 `sidePanelType` 设为 `'project-settings'`（UX-P4）

**P0-11 XSS：消息内容 `v-html` 无消毒**
- `ChatView.vue:122` `v-html="msg.content"`，来源 `textarea.value` 直接 push（Tech）
- 风险：用户注入 `<img onerror=...>` 等脚本

**P0-12 命令式 DOM 操作替代 Vue 响应式**
- `ChatView.vue:837/843/938/960/1006` 用 `getElementById().querySelector()` 读写；`App.vue:130-153` 手动 classList
- 风险：Vue 无法跟踪、双源真相、可测试性差

---

### 🟠 P1 · 交互完整性与稳定性（应修）

**P1-1 工作目录按钮无响应**
- `ChatView.vue:227` `workDirTrigger` 无 `@click`，无 `hiddenWorkDirInput`/`handleWorkDirSelect`（QA）

**P1-2 语音输入无"录音中"态**
- 原型：`app.html:16397-16411` 切 `.recording` + 波形
- Vue：`ChatView.vue:211` 仅 `showToast('开发中')`，无波形元素（QA/UX/UI/QA-A3）

**P1-3 对话头部 Agent 头像死按钮**
- `ChatView.vue:79-85` 无 `@click`、无 role/tabindex（QA/UX/UI/QA-A2）

**P1-4 发送无防连点；停止/发送按钮可见性不切换**
- `ChatView.vue:836` 仅判断空输入；`stopBtn` 恒 hidden（QA）

**P1-5 stopProcessing 后已排程 setTimeout 链仍改写状态**
- `ChatView.vue:922-930` 无状态锁（QA，低危逻辑泄漏）

**P1-6 Agent 信息面板被删除**
- `ChatView.vue:245` 注释 `PANEL v5.5 PAGE: Agent Info (deleted)`；原型 15 处引用（PM/Tech）

**P1-7 添加技能选择面板缺失**
- 原型 `app.html:12195-12225` 12 技能多选；Vue 仅 toast（PM）

**P1-8 全局搜索命令面板（⌘K）整体缺失**
- `app.html:11516-11535`；Vue 全工程无入口（PM，高）

**P1-9 项目详情页整体缺失**
- `app.html:12800` → `openProjectDetail` + 4 Tab(activity/sop/tasks/assets)；Vue 仅 `ProjectsView` toast（PM，高）

**P1-10 设置页 10/11 面板为"待迁移"空壳**
- `SettingsView.vue:74-108`；仅主题可用（PM，高）

**P1-11 记忆/广场/实验室/文件 占位页面交互全 toast**
- `MemoryView.vue` / `PlazaView.vue` / `LabView.vue` / `FilesView.vue` 卡片动作、日历、图谱、安装流程均 toast（PM）

**P1-12 定时器/超时未清理（内存泄漏）**
- `ChatView.vue:865-891` `setInterval` + 多 `setTimeout`；全项目无 `onUnmounted`（Tech）

**P1-13 showToast 8 份重复，6 视图为 console.log 空实现**
- `App.vue` / `ConnectionsView` / `FilesView` / `LabView` / `MemoryView` / `PlazaView` / `ProjectsView` 的 toast 静默失效（Tech）

**P1-14 侧栏"搜索对话"内联框被移除**
- 原型 `app.html:11754`；Vue 仅保留更深的"更多→搜索历史"路径（UX）

---

### 🟡 P2 · 健壮性 / 可访问性 / 一致性（建议）

- **P2-1** textarea 应改 `v-model` + `ref`，避免 id 重构后静默失效（Tech）
- **P2-2** `convMessages[activeConv]` 缺防御性取值（Tech）
- **P2-3** 代码块复制按钮缺失（QA）
- **P2-4** 侧栏菜单缺 `aria-expanded`/`role` 同步（UX/UI）
- **P2-5** 4 个 Vue 新增类无 CSS：`mem3-dream-card-info` / `mem3-lt-preview` / `graph-edges` / `plaza-empty`（Tech/UI）
- **P2-6** `console.log` 残留 14 处（Tech）
- **P2-7** `--glass-bg` / `--bg-glass-h` / `--side-panel` 两版均未定义，玻璃底色未生效（UI，共同缺口）
- **P2-8** Side Panel 内聚于 ChatView，未来跨 Tab 复用需重复实现（UX/Tech 架构）
- **P2-9** Pinia 已挂载但无 store；会话/模型状态应外提（Tech）

---

## 三、修复路线图（建议）

### 阶段 A · 对话页交互闭环（优先级最高，聚焦 ChatView）
1. 补齐 P0-1~P0-10 全部事件绑定，把 toast 占位替换为真实逻辑（参考原型同名函数）
2. 加统一 `useDropdown` composable：open/close + click-outside + Esc（解决 P0-9 / P1-3 / P1-14 a11y）
3. 文本框改 `ref` + `v-model`，消除 `getElementById`（P0-12）
4. `v-html` 引入 DOMPurify 消毒（P0-11）
5. 头部分流设置：按 `activeConv` 类型开 Agent/Project 设置面板（P0-10）

### 阶段 B · 安全与生命周期基建
6. `onBeforeUnmount` 清理 interval/timeout（P1-12）
7. 抽 `composables/useToast.ts`，删除 8 份重复（P1-13）
8. 拆分 ChatView 为 `ChatSidebar/MessageList/ChatInput/SidePanel + panels/*`（P0-12 架构）

### 阶段 C · 缺失页面补齐
9. 全局搜索 ⌘K 命令面板（P1-8）
10. 项目详情页 + 4 Tab（P1-9）
11. 设置页 10 面板落地，优先 模型管理/个人资料/安全中心（P1-10）
12. 记忆/广场/实验室/文件 占位页交互（P1-11）

### 阶段 D · 打磨
13. a11y 基线（role/tabindex/aria-live）、4 个缺失类补 CSS、glass 令牌、console 清理（P2）

---

## 四、附：五维审计要点速查

| 角色 | 一句话结论 |
|------|-----------|
| PM | 7 Tab 导航 100% 覆盖，但除 Chat 外全是 toast 空壳；3 个原型级功能（⌘K/项目详情/设置10面板）整体缺失 |
| QA | 构建通过但 40+ 交互死按钮/仅 toast；事件绑定大面积漏迁，运行期无法发现 |
| UX | 新建入口死、语音无态、头像死、菜单不关、项目设置不可达；信息架构主体一致 |
| UI | 视觉 99.8% 还原、动效 100%、CSS 仅 51 行差异；问题在行为接线而非样式 |
| Tech Lead | 类型/构建健康；但命令式 DOM、v-html XSS、定时器泄漏、千行组件未拆分、toast 8 份重复 |

> 根因共识：迁移是"整段内联 JS 平移"而非"Vue 范式重写"——响应式、组合式函数、生命周期、无障碍、安全性尚未到位，是最该优先补强的方向。
