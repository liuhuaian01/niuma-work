# Changelog

## v1.0.0-alpha (2026-07-15) — Alpha 预览版

### 里程碑：PyInstaller 打包成功 + 管理平台 Phase 0 就绪

### 新增

- **PyInstaller 打包** (`backend/main.spec`)
  - 成功打包为 `SuperNiuma-backend.exe` (33MB)
  - 覆盖 72 个 engine 模块 + 36 个 router + 全部 schemas/services
  - 前端 dist/ 内嵌到 exe

- **NSIS 安装包** (`data/installer/niuma-installer.nsi`)
  - 完整的 Windows 安装程序
  - 桌面快捷方式 + 开始菜单 + 卸载程序
  - 模型文件保留选项

- **管理平台 Phase 0** (`data/management-platform/`)
  - Go + Gin + PostgreSQL 完整后端
  - `POST /v1/codes/validate` — 客户端激活码验证
  - `POST /v1/admin/codes/generate` — 批量生成激活码
  - `POST /v1/version/check` — 客户端版本检查
  - `POST /v1/admin/versions` — 管理端发布版本
  - `POST /v1/devices/ping` — 设备心跳上报
  - `GET /v1/admin/dashboard` — 管理看板
  - Docker Compose 一键部署
  - 数据库 schema (10 张表)

---

## v0.9.0-dev (2026-07-15) — 开发者内测版

### 里程碑：前后端打通 + Chat 全链路验证通过

---

### 新增

- **安装包打包方案** (`deliverables/installer-packaging-spec-v1.0.md`)
  - 不内置模型，~186MB 纯壳，首次启动自动下载
  - llama.cpp server 替代 Ollama 作为本地推理引擎
  - Gemma 4 (Google) + Qwen3 (阿里) 双模型系列
  - 硬件检测 → 智能推荐 → 断点续传下载 → 离线可用
  - 国内镜像 hf-mirror.com 加速

- **管理平台方案** (`deliverables/install-management-platform-spec-v1.0.md`)
  - 账号体系：邮箱注册登录、JWT、设备绑定
  - 激活码系统：NIUA-XXXX-XXXX-XXXX、批量生成、渠道追踪
  - 付费订阅：Free/Pro/Enterprise 三档
  - 网络后台：版本管理、崩溃监控、数据看板
  - 4 Phase 实施计划，合计 21 人天

- **llama.cpp 本地推理引擎集成**
  - `engine/llama_manager.py` — 进程生命周期管理
  - `routers/model_download.py` — 模型下载 REST API + SSE 进度
  - `config/settings.py` — LLAMA_SERVER_* 配置项
  - `launcher.py` — 桌面壳启动编排

- **首次启动引导**
  - `OnboardingView.vue` — 3 步引导（欢迎 → 硬件检测+选模型 → 下载进度）
  - `/onboarding` 路由

- **后端路由**
  - `routers/files.py` — 文件管理增删改
  - `routers/connections.py` — MCP 连接管理
  - `routers/experts.py` — 专家广场
  - `routers/memory.py` — +GET /memory 概览 + /memory/search 搜索

- **前端 API 对接**
  - 9 个 API 模块全部对齐后端实际路由
  - Vite proxy `/api` → `127.0.0.1:18080`

### 变更

- **模型适配器重写** (`model_adapter/openai_compat.py`)
  - Ollama → llama.cpp server (`localhost:8080`)
  - Gemma 4 全系列：E4B / 12B / 26B-A4B
  - Qwen3 全系列：8B / 14B / 32B
  - `register_local_models()` — 动态扫描 GGUF 目录

- **认证修复** (`middleware/agent_auth.py`)
  - token 端点不再锁自己（死锁修复）
  - +10 公开端点白名单

- **Bug 修复** (`main.py`)
  - `logging` 变量冲突导致启动崩溃
  - 正确集成 llama_manager 启停

### 验证

- ✅ 后端 36 个路由全部注册
- ✅ 前端 10 个页面构建通过 (70 modules, 3s)
- ✅ Vite proxy → Backend 代理链路
- ✅ llama-server.exe (b9939) 下载 + 启动
- ✅ Qwen3-0.6B-Q4_K_M (378MB) 下载 + 推理 (47 tok/s)
- ✅ SSE 流式 token-by-token 输出
- ✅ llama_manager 自动发现 GGUF + 注册适配器
- ✅ huggingface_hub==1.23.0 模型下载依赖

### 待办（下一迭代）

- [ ] PyInstaller 打包
- [ ] NSIS 安装包制作
- [ ] llama-server 路径从 bin/ 自动查找（当前需手动下载或首次启动拉取）
- [ ] Qwen3 thinking mode 适配（reasoning_content vs content）
- [ ] 前端 Vue 组件 TypeScript 错误修复（15 个预存错误）
- [ ] P1 补齐：硬件检测、端口冲突、Crash 恢复、卸载清理、多模型管理 UI
- [ ] 管理平台 Phase 0（激活码 + 版本更新）

---

## v0.3.0 (2026-06-14) — 太极引擎内部版本

- 太极引擎 v1.7：七元模块 + Hermes 适配器
- 记忆系统 L1/L2/L3 三级架构
- 33 个路由 + 9 个中间件
- 前端 NEON PULSE v11.0 设计系统
- 产品规格文档 v3.0
