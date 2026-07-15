# 🔍 超级牛马设计系统差距审计报告

> 审计日期：2026-06-26  
> 审计团队：Token 审计员 + 组件审计员 + 页面/交互审计员（三线并行）  
> 审计目标：评估现有设计系统（design-tokens.css v16 + components.css v17）与前端原型（niuma-neon-pulse-prototype.html v10）之间的差距，提出提升路线图  
> 基准：品牌色 #4DA8F0 保持不变，原型 v10 为 UI 事实标准

---

## 一、核心结论

**设计系统与原型是两套独立演进的体系。** 原型 v10（内联，17,571行）承载了 11 个页面 + 12 个设置面板 + 100+ 种自定义组件类的完整交互体验，但独立的设计系统文件（design-tokens.css + components.css + admin-components.css，合计约 5,664行）与原型缺乏映射关系。两者的 Token 命名、组件命名、布局方式均不统一。

**一句话：原型很完整，但设计系统没跟上。现在需要把原型中的精华——组件、Token、布局——反向收敛到独立的设计系统文件中。**

---

## 二、差距总览

### 2.1 量化统计

| 维度 | 现状 | 差距 |
|------|------|------|
| **Token 体系** | 原型 v10 内联 Token ≈ 120 个；独立 DS v16 Token ≈ 130 个 | 命名前缀不统一、Day/Classic 缺失 ~30 个重写、布局 Token（L2）为零 |
| **组件覆盖** | 原型使用 100+ 种自定义 CSS 类；独立 DS 含 37 个模块 | 原型中有 **40+ 组件族** 未进入独立 DS；独立 DS 有 **25+ 组件族** 原型未使用 |
| **状态完整性** | 缺乏系统化状态管理 | **25 项状态缺失**（focus-visible x5、disabled x4、loading x3、error x3、success x2 等） |
| **交互模式** | 13 项标准清单 | 完全实现 2 项、部分实现 6 项、**完全缺失 5 项** |
| **响应式** | 18 处 @media 断点 | 无系统性移动端方案、无触控适配 |
| **无障碍** | 部分 aria 标注 | role/aria-selected/焦点管理不完整 |

---

## 三、P0 级差距——立即修复

### 3.1 核心组件库迁移（40+ 组件族缺失）

原型中使用的以下核心组件在独立 design system CSS 中完全不存在，**必须抽取**：

**对话核心（13 个组件族）：**
| 组件 | 行号（原型） | 说明 |
|------|-------------|------|
| `.send-btn` | 5 处使用 | 发送按钮，缺 disabled/loading 态 |
| `.input-textarea` | 4 个输入区 | 对话核心输入控件 |
| `.input-area / .input-toolbar / .input-status-bar / .input-attach-strip` | 多处 | 输入区容器体系 |
| `.chat-item` + 子类（avatar/info/name/preview/meta/time/badge） | 8 个实例 | 对话列表项 |
| `.message / .msg-bubble / .msg-avatar / .msg-content / .msg-meta` | 多处 | 消息气泡系统 |
| `.chat-header` + 子类 | 多处 | 对话顶部栏 |

**设置系统（5 个组件族）：**
| 组件 | 行号 | 说明 |
|------|------|------|
| `.settings-row` | 40+ 处 | 设置行（label/desc/control 三段式） |
| `.settings-select` | 20+ 处 | 设置下拉框 |
| `.settings-toggle-pill` | 15+ 处 | 设置开关胶囊 |
| `.settings-nav-card / .settings-nav-item` | 13700+ | 设置导航侧栏 |
| `.settings-btn` | 25+ 处 | 设置页按钮，缺 danger/primary 变体 |

**项目管理（6 个组件族）：**
| 组件 | 说明 |
|------|------|
| `.project-card` + 子类（main/icon/info/name/meta/menu/popup/dropdown） | 项目卡片 + 右键菜单 |
| `.project-detail-tab-nav` + 子类 | 项目详情 Tab 导航 |
| `.agent-card` + 子类（top/avatar/name/role/desc/status） | Agent 卡片 |
| `.agent-info-popup` + 子类（avatar-section/status-row/skills-grid 等） | Agent 信息弹窗 |
| `.template-card` | 模板卡片 |
| `.model-dropdown` + 子类（model-item-icon/model-tag） | 模型选择下拉 |

**面板系统（4 个组件族）：**
| 组件 | 说明 |
|------|------|
| `.account-panel` + 子类 | 账号管理面板 |
| `.side-panel / .panel-page / .panel-page-header` | 侧边面板系统 |
| `.page-view` | 页面视图容器 |
| `.chat-search-panel` + 子类（search-input/search-nav/search-count） | 对话搜索面板 |

### 3.2 组件状态补全（25 项缺失）

设计系统 CSS 中以下核心组件缺关键交互状态：

| 组件 | 缺失状态 | 位置 |
|------|---------|------|
| `.nav-btn` | :focus-visible, :disabled | components.css |
| `.input` | :disabled, .success | components.css |
| `.textarea` | :hover, :disabled, .error, :focus-visible | components.css |
| `.send-btn`（原型独有） | :disabled, .loading | 原型内联 |
| `.settings-btn`（原型独有） | danger/primary 变体 | 原型内联 |

### 3.3 交互模式缺项（5 项完全缺失）

| 模式 | 现状 | 影响 |
|------|------|------|
| **空状态实例化** | CSS 有 `.empty-state`，但所有 11 页面均无空状态 DOM | 新用户看到空白页 |
| **错误状态** | 完全无 error-state 组件和恢复路径（重试按钮） | 用户遇到错误不知所措 |
| **键盘快捷键** | 快捷键面板展示但不绑定事件、无 Ctrl+K 命令面板、无 Escape 全局关闭 | 键盘用户无法高效操作 |
| **Skeleton 加载** | CSS 定义了 skeleton 样式，但零处使用 | 加载过程闪白 |
| **触控适配** | 按钮 mini 尺寸 28px（远低于 44px 最小标准） | 触屏用户无法使用 |

---

## 四、P1 级差距——近期规划

### 4.1 命名体系统一

原型与独立 DS 的 Token 命名存在系统性差异：

| 功能域 | 原型命名 | 独立 DS 命名 | 建议 |
|--------|---------|-------------|------|
| 背景 | `--bg-root` | `--color-bg-root` | 统一加 `--color-` 前缀 |
| 品牌色 | `--brand` | `--color-brand` | 统一加 `--color-` 前缀 |
| 玻璃 | `--bg-glass` | `--color-glass-bg` | 统一词序 |
| 字重 | `--weight-normal` | `--fw-normal` | 统一缩写 |
| 时长 | `--dur-base` | `--dur-normal` | 统一语义 |

**解决方式：** 建立映射别名层，12 个核心 Token 同时注册两个版本。

### 4.2 布局 Token 体系（零→40+）

原型中所有布局常量分散硬编码——**需要新建 L2 层**：

```
--layout-nav-rail-width: 56px;           /* nav-rail */
--layout-nav-rail-expanded: 200px;       /* 展开态 */
--layout-content-max: 1200px;            /* 内容最大宽 */
--layout-content-narrow: 740px;          /* 窄内容（设置等） */
--layout-page-padding: 24px;             /* 页面内边距 */
--layout-section-gap: 32px;              /* 区块间距 */
--layout-card-min-width: 280px;          /* 卡片最小宽 */
--layout-card-gap: 12px;                 /* 卡片间距 */
--layout-header-height: 56px;            /* 顶部栏高 */
--layout-sidebar-width: 260px;           /* 侧栏宽 */
```

### 4.3 Day 主题补全（~30 个 Token）

Day 模式中以下 Token 仍使用 Night 值（导致亮色模式下出现暗色元素）：

- Silver 色系（--silver, --silver-light, --silver-dark, --silver-glow）
- 渐变系统（--gradient-pulse, --gradient-glass-dark, --gradient-glass-light, --energy-gradient）
- 滚动条（--scrollbar-thumb）
- 输入框（--input-bg）

### 4.4 冗余组件清理

独立 DS 中有 25+ 组件族原型完全未使用，建议分类处理：

| 类别 | 组件 | 处理 |
|------|------|------|
| **布局冲突** | `.app-shell`（原型用 `.workspace`） | 统一为 `.workspace`，删除 `.app-shell` |
| **表单重复** | `.input/.textarea/.toggle/.form-group` | 评估后决定保留哪个变体 |
| **文档展示** | `.entity-card/.detail-card/.color-swatch-*` | 移到 design-system.html 专用区 |
| **营销页** | `.hero/.navbar/.feature-grid/.pricing` | 移到独立 marketing.css（当前不需要） |
| **后台管理** | `.data-table/.pagination/.breadcrumb/.form-horizontal/.steps` | 保留在 admin-components.css 作为扩展库 |

---

## 五、P2 级差距——迭代改进

- **响应式移动端方案**：目前有断点无系统性方案，需整理为 4 断点体系（mobile/tablet/desktop/wide）
- **虚拟列表**：messages-area 和 chat-item 列表需引入 IntersectionObserver
- **拖拽排序**：chat list、project grid 实现完整 DnD
- **引导流程**：Onboarding wizard 组件（admin-system.html 已有 steps 组件可改造）
- **prefers-reduced-motion 全覆盖**：当前仅 3 处覆盖，需向 skeleton/typing/spinner/float 扩展
- **右键菜单泛化**：记忆/文件/消息气泡/连接器卡片均需右键菜单

---

## 六、提升路线图

### 第一阶段：收敛（1-2 周）
**目标：原型与设计系统建立单一事实来源**

```
□ P0-1: 抽取原型 P0 组件族（13个）→ components.css（新增 500-800 行）
□ P0-2: 补齐 25 项组件状态（:focus-visible、:disabled、.loading等）
□ P0-3: 建立映射别名层（12 个核心 Token 双注册）
□ P0-4: Day 主题补全 30 个遗漏 Token
□ P0-5: 为所有 11 页面添加空状态 DOM 实例
□ P0-6: 新建 error-state 错误状态组件 + 恢复 UI
```

### 第二阶段：补全（2-3 周）
**目标：覆盖所有核心模式和组件**

```
□ P1-1: 建立 L2 布局 Token 层（15-20 个核心 Token）
□ P1-2: 抽取 P1 辅助组件族（15个）→ components.css
□ P1-3: 实现全局键盘快捷键管理器（Escape/Ctrl+K/Ctrl+N）
□ P1-4: Skeleton 加载态实例化（chat list/project grid/memory list）
□ P1-5: 清理/合并冗余组件（5-8 个冲突组件统一）
□ P1-6: 确认弹窗强化（info/warning/danger 三类型）
```

### 第三阶段：打磨（3-4 周）
**目标：体验完整闭环**

```
□ P2-1: 4 断点响应式方案（移动端/平板/桌面/宽屏）
□ P2-2: messages-area 虚拟列表
□ P2-3: 拖拽排序（chat list + project grid）
□ P2-4: 右键菜单泛化（6 个实体类型覆盖）
□ P2-5: Onboarding 引导流程（3 步 × ≤60 秒）
□ P2-6: prefers-reduced-motion 全覆盖（补充 5 处缺失）
□ P2-7: 无障碍补充（role/aria-selected/焦点陷阱/live region）
```

---

## 七、文件清单

| 文件 | 当前行数 | 建议变更 |
|------|:------:|------|
| `design-tokens.css` | 436 | +60 行（L2 布局 Token + 映射别名）+ 30 项 Day/Classic 补全 |
| `components.css` | 3,388 | +1,000-1,500 行（P0+P1 组件迁移） |
| `admin-components.css` | 1,840 | 不变（保留为扩展库，部分组件可标记 deprecated） |
| `design-system.html` | 1,748 | +300 行（新增组件展示） |
| *新建* `layout-tokens.css` | 0 | ~50 行（L2 页面布局 Token） |
| *新建* `error-and-empty.css` | 0 | ~100 行（空状态/错误状态通用组件） |

---

> **审计签署**：token-auditor ✓ | component-auditor ✓ | page-auditor ✓  
> **下一步**：确认优先级和范围，启动第一阶段——开始抽取 P0 组件族到设计系统文件。
