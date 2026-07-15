# 超级牛马 — 桌面原生层设计规范 v11.0

> 本文档定义超级牛马在 WebView2 壳内运行时的桌面独有 UI 模式和交互规范。  
> 配套 CSS: `public/css/desktop-native.css`

---

## 一、窗口 Chrome（自定义标题栏）

### 设计目标
- 替代系统默认标题栏，提供统一的品牌视觉
- 支持拖拽移动窗口
- 兼容 Windows（右侧控制按钮）和 macOS（左侧红绿灯）

### 组件规格

| 属性 | 值 |
|------|-----|
| 高度 | 38px |
| 背景 | `var(--bg-surface)` |
| 底边框 | `1px solid var(--border-default)` |
| 拖拽区域 | 整个标题栏 `-webkit-app-region: drag` |
| 按钮区域 | `-webkit-app-region: no-drag` |

### Windows 风格（右侧控制按钮）
```
┌──────────────────────────────────────────────┐
│ ⚡ 超级牛马 Super Niuma            ─  □  ✕  │
└──────────────────────────────────────────────┘
```

- 按钮尺寸：46×32px
- 关闭按钮 hover 背景色：`#E81123`（系统红）
- 图标使用 SVG，不依赖系统字体

### macOS 风格（左侧红绿灯）
```
┌──────────────────────────────────────────────┐
│ 🔴 🟡 🟢   ⚡ 超级牛马 Super Niuma           │
└──────────────────────────────────────────────┘
```

- 红绿灯间距：8px
- 红绿灯大小：14×14px
- hover 时降低亮度

---

## 二、右键菜单（Context Menu）

### 设计规格

| 属性 | 值 |
|------|-----|
| 最小宽度 | 180px |
| 最大宽度 | 280px |
| 内边距 | 4px |
| 圆角 | `var(--radius-sm)` |
| 入场动画 | `scaleIn` 150ms spring |
| 层级 | `z-modal` |

### 菜单项规格

| 状态 | 样式 |
|------|------|
| 默认 | `color: text-secondary` |
| Hover | `background: bg-hover`, `color: text-primary` |
| Active（按下） | `background: bg-active` |
| Danger hover | `background: error-bg`, `color: error` |
| Disabled | `opacity: 0.4`, `pointer-events: none` |
| Selected | `background: brand-muted`, `color: brand` + ✓ 标记 |

### 菜单结构

```
┌──────────────────────────┐
│ ✂️  Cut        Ctrl+X   │  ← 图标 + 标签 + 快捷键
│ 📋  Copy       Ctrl+C   │
│ 📌  Paste      Ctrl+V   │
├──────────────────────────┤  ← 分隔线
│ 🔍  Search...           │
│ 🔄  Refresh             │
├──────────────────────────┤
│ 🗑  Delete      Del     │  ← 危险操作（hover 变红）
└──────────────────────────┘
```

### 行为规范
- 点击菜单项后立即关闭菜单
- 点击菜单外部区域关闭菜单
- 按 Escape 关闭菜单
- 子菜单向右展开（> 箭头指示），延迟 300ms 打开
- 菜单不超出视口边界（自动翻转到另一侧）

---

## 三、命令面板（Command Palette）

### 触发方式
- 快捷键：`Ctrl+K`
- 菜单入口：Help → Command Palette

### 设计规格

| 属性 | 值 |
|------|-----|
| 宽度 | 560px |
| 最大高度 | 420px |
| 圆角 | `var(--radius-lg)` |
| 遮罩背景 | `var(--overlay-bg)` |
| 面板背景 | Glass Heavy + blur(32px) |
| 垂直位置 | 距顶部 15vh |

### 交互行为

| 操作 | 行为 |
|------|------|
| ↑↓ | 导航结果列表 |
| Enter | 执行选中命令 |
| Escape | 关闭面板 |
| 输入过滤 | 实时模糊匹配（标题 + 描述） |
| 点击遮罩 | 关闭面板 |

### 结果分组
```
┌──────────────────────────────────────┐
│ 🔍  new                               │
├──────────────────────────────────────┤
│ NAVIGATION                           │
│ 💬  New Chat            Ctrl+N       │
│ 🏠  Go to Workspace     Ctrl+1       │
├──────────────────────────────────────┤
│ ACTIONS                              │
│ 🔍  Search Files        Ctrl+G       │
│ ⚙   Settings            Ctrl+,       │
└──────────────────────────────────────┘
```

### 预置命令列表（首批）

| 命令 | 快捷键 | 分组 |
|------|--------|------|
| New Chat | `Ctrl+N` | Navigation |
| Go to Workspace | `Ctrl+1` | Navigation |
| Go to Projects | `Ctrl+2` | Navigation |
| Go to Plaza | `Ctrl+3` | Navigation |
| Go to Memory | `Ctrl+4` | Navigation |
| Go to Files | `Ctrl+5` | Navigation |
| Go to Connections | `Ctrl+6` | Navigation |
| Go to Lab | `Ctrl+7` | Navigation |
| Search Files | `Ctrl+G` | Actions |
| Settings | `Ctrl+,` | Actions |
| Toggle Theme | `Ctrl+T` | Actions |
| Toggle Sidebar | `Ctrl+\` | Actions |
| Clear Chat | `Ctrl+L` | Actions |

---

## 四、系统托盘（System Tray）

### 行为设计

| 场景 | 行为 |
|------|------|
| 点击关闭按钮 | 最小化到托盘（不退出） |
| 双击托盘图标 | 显示主窗口 |
| 右键托盘图标 | 显示托盘菜单 |
| 托盘菜单"退出" | 完全退出应用 |

### 托盘菜单结构
```
┌──────────────────────┐
│ ⚡ 超级牛马           │  ← 品牌标识行（不可点击）
├──────────────────────┤
│ 📊 显示主窗口        │
│ 💬 新对话    Ctrl+N  │
├──────────────────────┤
│ ⚙ 设置              │
│ 🔔 通知设置          │
├──────────────────────┤
│ 🚪 退出              │  ← 危险操作
└──────────────────────┘
```

### 托盘通知气泡
- 新消息到达时：托盘图标叠加未读标记（红色圆点）
- Agent 任务完成时：气泡通知"任务完成：{任务名}"
- 错误时：气泡通知"错误：{简述}"

---

## 五、系统通知（Native Notification）

### 触发场景

| 场景 | 类型 | 自动消失 |
|------|------|---------|
| AI 回复完成 | Info | 5s |
| Token 预算告警 | Warning | 8s |
| 连接断开 | Error | 手动关闭 |
| 文件处理完成 | Success | 5s |
| 新版本可用 | Info | 手动关闭 |

### 通知卡片规格

```
┌─────────────────────────────────────┐
│ ✓ 文件处理完成                    ✕ │
│    design-tokens.css 已保存         │
└─────────────────────────────────────┘
```

- 位于屏幕右下角
- 多个通知纵向堆叠，间隔 8px
- 最新通知在最上方
- 最多同时显示 3 条（超出则移除最旧的）

---

## 六、键盘快捷键完整体系

### 全局快捷键

| 快捷键 | 操作 | 说明 |
|--------|------|------|
| `Ctrl+N` | 新对话 | 创建空白对话 |
| `Ctrl+Shift+N` | 新工作间 | 创建新 workspace |
| `Ctrl+K` | 命令面板 | 搜索并执行任意命令 |
| `Ctrl+G` | 全局搜索 | 搜索文件/消息/设置 |
| `Ctrl+,` | 设置 | 打开设置页面 |
| `Ctrl+T` | 切换主题 | 循环 Night → Day → Classic |
| `Ctrl+\` | 切换侧栏 | 收起/展开侧栏 |
| `Ctrl+1..7` | 页面导航 | 跳转到各 Tab |
| `Escape` | 关闭/取消 | 关闭弹窗/面板/下拉菜单 |

### 对话快捷键

| 快捷键 | 操作 | 说明 |
|--------|------|------|
| `Enter` | 发送消息 | 输入框聚焦时 |
| `Shift+Enter` | 换行 | 在输入框中插入换行 |
| `Ctrl+Enter` | 强制发送 | 忽略自动补全 |
| `↑` | 上一条历史 | 输入框为空时，加载上一条已发送消息 |
| `↓` | 下一条历史 | 导航历史消息 |
| `Ctrl+L` | 清空对话 | 清除当前对话历史 |
| `Ctrl+Shift+C` | 复制最后回复 | 复制 AI 最后一条回复 |
| `Ctrl+/` | 显示快捷键帮助 | 弹出快捷键速查表 |

### 编辑快捷键（输入框内）

| 快捷键 | 操作 |
|--------|------|
| `Ctrl+B` | 加粗 |
| `Ctrl+I` | 斜体 |
| `Ctrl+Shift+K` | 代码块 |
| `Ctrl+Z` | 撤销 |
| `Ctrl+Shift+Z` | 重做 |
| `Tab` | 缩进 |

---

## 七、拖放区域（Drag & Drop Zone）

### 行为规范

| 状态 | 视觉 |
|------|------|
| 默认 | dashed 边框，bg-elevated |
| Hover（无文件） | 边框变 brand，背景微 tint |
| Drag-over（有文件拖入） | 边框实色 brand，brand glow 阴影，scale(1.01) |
| 释放文件 | 触发上传，恢复默认状态 |

### 支持的文件格式

```
PDF · DOCX · XLSX · PPTX · TXT · MD · CSV · JSON
PNG · JPG · GIF · SVG · WebP
PY · JS · TS · VUE · HTML · CSS · RS · GO · JAVA
ZIP · TAR · GZ
```

### 多文件处理
- 拖入多个文件 → 批量上传
- 拖入文件夹 → 递归读取（显示文件数量）
- 超大文件（>100MB） → 显示警告"文件过大，将仅索引元数据"

---

## 八、窗口调整大小（Resize Handles）

### 边缘拖拽区域

```
┌──┬──────────────────────────┬──┐
│↖│          ↑ 4px           │↗│
├──┼──────────────────────────┼──┤
│← │                          │→ │
│8 │     主内容区域            │8 │
│px│                          │px│
├──┼──────────────────────────┼──┤
│↙│          ↓ 4px           │↘│
└──┴──────────────────────────┴──┘
```

- 四边拖拽区域：4px
- 四角拖拽区域：8×8px
- z-index: `--z-sticky`
- 仅当窗口非最大化时显示

---

## 九、磁盘/文件操作原生对话框

### 调用的系统对话框

| 场景 | 对话框类型 | API |
|------|-----------|-----|
| 打开文件 | 文件选择器 | `window.showOpenFilePicker()` |
| 保存文件 | 另存为 | `window.showSaveFilePicker()` |
| 选择文件夹 | 目录选择器 | `window.showDirectoryPicker()` |
| 确认操作 | 确认对话框 | 自定义 Dialog（非原生） |

### 设计原则
- 文件选择使用系统原生对话框（用户熟悉）
- 应用内确认使用自定义 Dialog（保持视觉一致性）
- 错误提示优先使用 Toast（不打断流程）
- 致命错误使用 Dialog（必须用户确认）
