# 超级牛马安装包打包方案 v1.0

> 状态：方案确认 | 日期：2026-07-15
>
> 本文档定义超级牛马工作台的安装包打包策略、预装组件清单、首次启动模型下载机制。
> 目标：安装包不内置模型，150-200MB 纯壳，首次启动自动下载推荐模型。

---

## 目录

1. [总体设计](#1-总体设计)
2. [安装包预装清单](#2-安装包预装清单)
3. [模型策略](#3-模型策略)
4. [首次启动流程](#4-首次启动流程)
5. [下载机制](#5-下载机制)
6. [目录结构](#6-目录结构)
7. [打包流水线](#7-打包流水线)
8. [后续规划](#8-后续规划)

---

## 1. 总体设计

### 1.1 设计原则

| 原则 | 说明 |
|------|------|
| **装完即引导** | 安装后立即弹出引导页，自动检测硬件推荐模型 |
| **壳不塞肉** | 安装包只有运行时框架，模型首次启动从网络下载 |
| **一次下载终身离线** | 模型下载到本地后永久可用，无需联网 |
| **双模型策略** | Gemma 4（Google）+ 千问 Qwen3（阿里），用户自选 |

### 1.2 首发平台

| 平台 | 壳方案 | 状态 |
|------|--------|:--:|
| **Windows 10/11** | WebView2 + PyInstaller | v1.0 首发 |
| macOS | 待定（Electron / Tauri） | v1.1 |
| Linux | AppImage / Flatpak | v1.2 |

### 1.3 安装包体积预算

| 组件 | 体积 |
|------|------|
| 嵌入式 Python 3.11 | ~30MB |
| FastAPI 后端 (PyInstaller) | ~80MB |
| Vue 前端静态文件 | ~500KB |
| Hermes Agent CLI | ~15MB |
| llama-server.exe (llama.cpp) | ~50MB |
| 启动引导页 UI | 内嵌前端 |
| 运行时库（VC++ Redist 等） | ~10MB |
| **总计** | **~186MB** |

---

## 2. 安装包预装清单

### 2.1 Python 运行时

```
来源: python.org Windows embeddable package (3.11)
体积: ~30MB
安装位置: %APPDATA%/SuperNiuma/runtime/python/
说明: 嵌入式 Python，不需要用户单独安装 Python
```

### 2.2 后端 (FastAPI)

```
来源: PyInstaller 打包
入口: backend/main.py
体积: ~80MB（含所有引擎/路由/适配器/中间件）
安装位置: %APPDATA%/SuperNiuma/backend/
依赖:
  - FastAPI + Uvicorn
  - SQLAlchemy + aiosqlite
  - httpx (SSRF 检查)
  - Pydantic v2
  - huggingface_hub (模型下载)
  - 太极引擎全部七元模块
  - 记忆系统 L1/L2/L3
  - MCP Registry + Agent Card v2.0
打包工具: PyInstaller --onefile 或 --onedir
```

### 2.3 前端

```
来源: frontend-vue/ vite build
体积: ~500KB（gzip 后更小）
路由: Hash 模式，10 条路由
安装位置: 嵌入后端，由 FastAPI serve 静态文件
         （开发期 Vite dev server 代理到 :18080）
```

### 2.4 Hermes Agent CLI

```
来源: PyPI hermes-agent>=0.14.0
体积: ~15MB
安装位置: %APPDATA%/SuperNiuma/bin/hermes.exe
说明: Hermes Agent 多实例架构基座，预装到嵌入式 Python 环境中
自动安装: auto_install_hermes.py 已有完整逻辑
```

### 2.5 推理引擎 (llama.cpp)

```
来源: llama.cpp GitHub Release (b9549+)
二进制: llama-server.exe
体积: ~50MB
安装位置: %APPDATA%/SuperNiuma/bin/llama-server.exe
说明: llama.cpp server 模式，提供 OpenAI 兼容 API (/v1/chat/completions)
      后端通过 OpenAICompatAdapter 对接，无需 Ollama
版本要求: b9549+ (支持 Gemma 4 MTP 多令牌预测)
```

### 2.6 启动引导页

```
实现: WebView2 加载内嵌 Vue 页面
功能:
  - 硬件检测（CPU/内存/显存）
  - 模型推荐
  - 下载进度展示
  - 断点续传状态恢复
  - 国内镜像切换 (hf-mirror.com)
```

### 2.7 不需要预装的

| 组件 | 原因 |
|------|------|
| Ollama | 直接用 llama.cpp server，不需要中间层 |
| WebView2 | Windows 10+ 系统内置 |
| VC++ Runtime | Windows 10+ 系统内置，仅 Win7/8 需额外打包 |
| 任何模型文件 | 首次启动下载 |
| DeepSeek/云端 API Key | 用户首次启动后在设置里配置 |

---

## 3. 模型策略

### 3.1 Gemma 4 系列 (Google, Apache 2.0)

| 变体 | 推荐量化 | 文件大小 | 最低内存 | 上下文 | 定位 |
|------|---------|---------|---------|--------|------|
| **E4B** | Q8_0 | ~3GB | 6GB | 128K | 低配笔记本兜底 |
| **12B** | Q4_K_M | ~7GB | 12GB | 256K | 主流桌面，平衡之选 |
| **26B-A4B** | UD-Q4_K_XL | ~18GB | 22GB | 256K | 高端，MoE 速度/质量最优 |

特性：
- 全系列多模态（文本 + 图像），E2B/E4B 额外支持音频
- 支持 MTP 多令牌预测（需 llama.cpp b9549+）
- HuggingFace: `unsloth/gemma-4-XX-it-GGUF`

### 3.2 千问 Qwen3 系列 (阿里, Apache 2.0)

| 变体 | 推荐量化 | 文件大小 | 最低内存 | 上下文 | 定位 |
|------|---------|---------|---------|--------|------|
| **8B (128K)** | Q4_K_M | ~5.0GB | 10GB | 128K | 中文日常主力 |
| **14B** | Q4_K_M | ~8.5GB | 16GB | 128K | 中文创作/分析 |
| **32B** | Q4_K_M | ~19GB | 24GB | 128K | 中文旗舰 |

特性：
- 中文能力业界领先（阿里自研 + 中文预训练）
- 支持思维链 (thinking mode)
- HuggingFace: `unsloth/Qwen3-XX-GGUF`
- 国内下载友好 (ModelScope 镜像)

### 3.3 推荐策略

```
[硬件检测]
      ↓
  ├── 内存 < 8GB
  │     → 推荐 Gemma 4 E4B (3GB) 或 Qwen3 8B IQ3 (3.4GB)
  │     → 标注"基础体验，建议升级内存"
  │
  ├── 内存 8-16GB  ← 主流用户
  │     → 优先推荐 Qwen3 8B Q4_K_M (5GB)
  │     → 备选 Gemma 4 12B Q4_K_M (7GB)
  │     → 默认勾选 Qwen3 8B（中文用户）
  │
  └── 内存 > 16GB
        → 推荐 Gemma 4 26B-A4B (18GB) 或 Qwen3 32B (19GB)
        → 标注"高端体验，需要充裕内存"
```

### 3.4 广场模型（后续可下载）

| 模型 | 体积 | 用途 |
|------|------|------|
| Gemma 4 E2B Q8_0 | ~2GB | 极低配机器 |
| Gemma 4 31B Q4_K_M | ~20GB | 终极质量 |
| Qwen3.5 9B Q4_K_M | ~5.6GB | 新一代中文模型 |
| Qwen3.5 35B-A3B Q4_K_M | ~21GB | MoE 超大中文 |
| DeepSeek V3 系列 | 云端 | API Key 配置 |
| GLM-4 系列 | 云端 | API Key 配置 |

---

## 4. 首次启动流程

### 4.1 流程图

```
[用户双击桌面图标]
         ↓
[WebView2 窗口打开]
         ↓
[加载内嵌引导页]
         ↓
    ┌──────────────────────────────────┐
    │  欢迎使用超级牛马工作台          │
    │                                  │
    │  [检测硬件中...]                 │
    │  CPU: Intel i7-13700             │
    │  内存: 16GB                      │
    │  显存: 6GB (RTX 3060)           │
    │                                  │
    │  📌 推荐模型: Qwen3 8B (5.0GB)  │
    │  预计下载时间: ~3 分钟           │
    │                                  │
    │  [ ] Gemma 4 12B (7GB)          │
    │  [x] Qwen3 8B (5GB)  ← 推荐    │
    │                                  │
    │  [ 开始下载 ]   [ 跳过，稍后 ]   │
    └──────────────────────────────────┘
         ↓ [开始下载]
    ┌──────────────────────────────────┐
    │  正在下载 Qwen3 8B...           │
    │  ████████████░░░░░░ 65%         │
    │  3.2GB / 5.0GB                  │
    │  速度: 12 MB/s   剩余: 2 分钟   │
    │  来源: hf-mirror.com (国内镜像) │
    │                                  │
    │  [ 暂停 ]    [ 切换镜像 ]        │
    └──────────────────────────────────┘
         ↓ [下载完成]
    ┌──────────────────────────────────┐
    │  ✓ 下载完成                      │
    │  校验: SHA256 通过               │
    │                                  │
    │  [ 启动超级牛马 ]                │
    └──────────────────────────────────┘
         ↓
[启动后端 → 加载模型 → 进入对话页]
```

### 4.2 异常处理

| 场景 | 处理 |
|------|------|
| 无网络 | 提示"首次使用需要联网下载模型"，提供离线安装包下载链接 |
| 下载中断 | 断点续传，下次启动从断点继续 |
| 磁盘不足 | 提前检查可用空间，不足时提示清理 |
| 所有镜像失败 | 提供手动下载指引（浏览器下载 + 手动放置） |
| 模型校验失败 | 自动重新下载，不跳过校验 |
| 用户选择跳过 | 进入设置页，可随时触发下载；云端 API Key 配置立即可用 |

### 4.3 跳过模型下载的用户路径

```
[跳过下载]
    ↓
[进入设置页]
    ↓
┌────────────────────────────────────┐
│  配置 AI 模型                      │
│                                    │
│  ○ 本地模型（推荐，隐私优先）     │
│    [下载 Qwen3 8B (5GB)]          │
│    [下载 Gemma 4 12B (7GB)]       │
│                                    │
│  ● 云端 API                        │
│    DeepSeek: [填入 API Key]       │
│    Kimi:     [填入 API Key]       │
│    混元:     [填入 API Key]       │
│                                    │
│  [保存]                            │
└────────────────────────────────────┘
```

---

## 5. 下载机制

### 5.1 下载源

| 源 | URL | 适用 |
|------|-----|------|
| HuggingFace | huggingface.co | 海外用户，直连 |
| hf-mirror.com | hf-mirror.com | 国内用户，首选镜像 |
| ModelScope | modelscope.cn | 阿里模型首选，速度快 |

### 5.2 技术实现

```python
# 使用 huggingface_hub 库
# 特点：自带断点续传、进度回调、校验

from huggingface_hub import hf_hub_download

model_path = hf_hub_download(
    repo_id="unsloth/Qwen3-8B-GGUF",
    filename="Qwen3-8B-Q4_K_M.gguf",
    local_dir=f"{appdata}/SuperNiuma/models/",
    endpoint="https://hf-mirror.com",  # 国内镜像
    resume_download=True,               # 断点续传
)
```

### 5.3 镜像切换策略

```
优先级: hf-mirror.com → huggingface.co → modelscope.cn
超时: 30 秒内无数据 → 自动切下一个镜像
用户可手动切换
```

### 5.4 模型校验

```
每个模型文件附带 .sha256 校验文件
下载完成后自动校验
不通过 → 删除 → 重新下载
```

---

## 6. 目录结构

### 6.1 安装目录

```
C:\Program Files\SuperNiuma\
  ├── SuperNiuma.exe          ← 主程序（WebView2 壳 + 后端启动器）
  ├── uninstall.exe
  └── runtime/                ← 嵌入式运行时
      ├── python/             ← 嵌入式 Python 3.11
      ├── backend/            ← PyInstaller 打包的后端
      └── frontend/           ← Vue 静态文件
```

### 6.2 数据目录

```
%APPDATA%/SuperNiuma/
  ├── bin/
  │   ├── hermes.exe          ← Hermes Agent CLI
  │   └── llama-server.exe    ← llama.cpp 推理引擎
  │
  ├── models/                 ← 下载的模型文件
  │   ├── Qwen3-8B-Q4_K_M.gguf       (~5.0GB)
  │   ├── Qwen3-8B-Q4_K_M.gguf.sha256
  │   ├── gemma-4-12B-Q4_K_M.gguf    (~7.0GB)
  │   ├── gemma-4-12B-Q4_K_M.gguf.sha256
  │   └── .download_progress.json    ← 断点续传进度
  │
  ├── backend/                ← 数据库 + 日志 + 配置
  │   ├── data/
  │   │   ├── superniuma.db   ← SQLite 主库
  │   │   ├── taiji.db        ← 太极引擎库
  │   │   └── lancedb/        ← L3 知识库
  │   ├── logs/               ← 应用日志
  │   ├── settings.json       ← 用户设置
  │   └── config/
  │       ├── agents.json
  │       ├── models.json
  │       └── skills/
  │
  ├── workspaces/             ← 工作间沙盒目录
  │   ├── ws-1/
  │   └── ws-2/
  │
  └── cache/                  ← 运行时缓存
```

### 6.3 启动快捷方式

```
桌面:    SuperNiuma.lnk
开始菜单: SuperNiuma/SuperNiuma.lnk
```

---

## 7. 打包流水线

### 7.1 构建步骤

```
[1] 前端构建
    cd frontend-vue && npm run build
    → dist/ 产物

[2] 后端打包
    cd backend
    pyinstaller main.spec
    → dist/SuperNiuma-backend.exe

[3] 运行时准备
    - 嵌入式 Python 3.11
    - llama-server.exe (从 llama.cpp Release 下载)
    - hermes-agent (pip install 到嵌入式 Python)

[4] 壳打包
    - WebView2 壳窗口 (Python + pywebview 或 C# + WebView2)
    - 内嵌引导页 (Vue 静态页面)
    - 启动逻辑 (拉起后端 → 等待就绪 → 加载前端)

[5] 安装包制作
    - NSIS / Inno Setup
    - 数字签名
    - 自动更新检查 (WinSparkle)
```

### 7.2 PyInstaller 配置

```python
# backend/main.spec
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../frontend-vue/dist/', 'frontend/'),
        ('config/', 'config/'),
        ('assets/', 'assets/'),
    ],
    hiddenimports=[
        'engine.taiji',
        'engine.memory_loader',
        'engine.taixu_core',
        'engine.recursive_evolution',
        'engine.context_drift',
        'engine.agent_registry',
        'engine.agent_card',
        'engine.goal_loop_engine',
        'engine.emergence',
        'engine.hermes_adapter',
        'model_adapter.openai_compat',
        'model_adapter.fallback',
        'services.memory.memory_service',
        'middleware.workspace_isolation',
        'middleware.agent_auth',
        'routers.*',
        'schemas.*',
        'huggingface_hub',
        'aiofiles',
    ],
    ...
)
```

### 7.3 自动更新

```
方案: WinSparkle (Windows)
检查: 启动时检查 GitHub Release 最新版本
下载: 增量更新包 (.delta)
静默: 下载完成后下次启动自动安装
```

---

## 8. 后续规划

### v1.0 (Windows 首发)

- [x] 安装包不内置模型
- [x] 首次启动引导下载
- [x] Gemma 4 + Qwen3 双系列
- [x] 断点续传 + 镜像切换
- [x] 跳过下载，使用云端 API
- [x] llama.cpp 替代 Ollama
- [x] 模型适配器动态注册
- [x] llama.cpp 进程管理
- [x] 模型下载 REST API + SSE
- [x] 桌面壳启动器
- [x] 首次启动引导 Vue 页面
- [x] 认证鸡生蛋修复
- [ ] PyInstaller 打包
- [ ] NSIS 安装包
- [ ] 数字签名

### v1.1 (macOS)

- [ ] Electron / Tauri 壳
- [ ] Metal 加速支持
- [ ] DMG 打包 + 公证

### v1.2 (Linux)

- [ ] AppImage / Flatpak
- [ ] CUDA/Vulkan 自动检测

### v2.0

- [ ] 模型广场内下载更多模型
- [ ] 自动更新检查
- [ ] Electron 替代 WebView2（跨平台统一）
- [ ] Docker 部署模式

---

## 9. 遗漏项与补齐计划

> 2026-07-15 全量审查，按 P0（阻断）/ P1（高优）/ P2（体验）分级。

### 9.1 P0 — 必须补齐，否则装不了

#### 9.1.1 模型适配器从 Ollama 切换到 llama.cpp server

**现状**: `model_adapter/openai_compat.py` 中 `gemma-4` 硬编码 `base_url="http://localhost:11434/v1"`（Ollama），且没有 Qwen3 适配器。

**需要改**:
```python
# openai_compat.py — 改为动态注册本地模型

def register_local_models(models_dir: str):
    """扫描 %APPDATA%/SuperNiuma/models/ 目录，
    自动注册已下载的 GGUF 模型"""
    for gguf_path in Path(models_dir).glob("*.gguf"):
        model_id = gguf_path.stem  # e.g., "Qwen3-8B-Q4_K_M"
        adapters[model_id] = OpenAICompatAdapter(
            model_name=gguf_path.name,
            api_key="not-needed",
            base_url="http://localhost:8080/v1",  # llama.cpp server
            display_name=model_id,
            max_context=131072,
        )
```

**涉及的适配器**:
| 注册 ID | 模型文件 | base_url |
|---------|---------|----------|
| `qwen3-8b` | Qwen3-8B-Q4_K_M.gguf | localhost:8080 |
| `qwen3-14b` | Qwen3-14B-Q4_K_M.gguf | localhost:8080 |
| `qwen3-32b` | Qwen3-32B-Q4_K_M.gguf | localhost:8080 |
| `gemma-4-e4b` | gemma-4-E4B-it-Q8_0.gguf | localhost:8080 |
| `gemma-4-12b` | gemma-4-12B-it-Q4_K_M.gguf | localhost:8080 |
| `gemma-4-26b` | gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf | localhost:8080 |

#### 9.1.2 llama.cpp server 进程管理

**现状**: 不存在。后端不知道 llama-server 的存在。

**需要新增**:
```
backend/engine/llama_manager.py

class LlamaManager:
    - start(model_path, port=8080, n_gpu_layers=auto) → 启动 llama-server
    - stop()          → 优雅关闭
    - is_healthy()    → GET /v1/models 健康检查
    - restart(model)  → 切换模型
    - get_logs()      → 获取 server 日志

启动参数:
  llama-server
    --model <model.gguf>
    --host 127.0.0.1
    --port 8080
    --ctx-size 32768
    --n-gpu-layers 999    # 自动卸载到 GPU（无 GPU 则 CPU）
    --temp 1.0
    --top-p 0.95
    --top-k 64
```

**生命周期集成到 main.py lifespan**:
```
startup:
  1. 扫描 models/ 目录
  2. 找到默认模型 → 启动 llama-server
  3. 注册适配器
  4. 等待 llama-server 健康就绪

shutdown:
  1. 关闭 llama-server
  2. 清理临时文件
```

#### 9.1.3 桌面壳启动器

**现状**: `pywebview` 在 pyproject.toml 中但没有任何实际代码。

**需要新增**:
```
backend/launcher.py  (或 top-level super_niuma.py)

class NiumaLauncher:
    1. 检查运行时环境 (Python/llama-server/hermes)
    2. 启动 FastAPI 后端 (uvicorn 子进程)
    3. 等待后端健康检查通过
    4. 如果是首次启动 → 加载引导页
    5. 否则 → 加载主应用
    6. 打开 WebView2 窗口
```

#### 9.1.4 模型下载服务

**现状**: 不存在。没有后端端点可以触发下载。

**需要新增**:
```
backend/routers/model_download.py

GET  /api/v1/models/downloadable    → 可下载模型列表（含体积、推荐硬件）
POST /api/v1/models/download        → 触发下载
       { "model": "Qwen3-8B-Q4_K_M", "source": "hf-mirror" }
GET  /api/v1/models/download/{id}/progress → SSE 下载进度
POST /api/v1/models/download/{id}/cancel   → 取消下载
GET  /api/v1/models/local           → 已下载的本地模型列表
POST /api/v1/models/local/{id}/activate   → 切换默认模型
DELETE /api/v1/models/local/{id}    → 删除本地模型

下载采用 huggingface_hub.hf_hub_download:
  - resume_download=True (断点续传)
  - 进度回调 → SSE 推送给前端
  - 下载完自动 SHA256 校验
  - 校验通过 → 写入 models/ 目录 → 调用 register_local_models()
```

#### 9.1.5 首次启动引导页

**现状**: 不存在。

**需要新增**:
```
frontend-vue/src/views/OnboardingView.vue

步骤:
  1. 欢迎页 (logo + 产品介绍)
  2. 硬件检测 (CPU/内存/显存)
  3. 模型推荐 (根据硬件推荐)
  4. 模型下载 (进度条 + 镜像切换)
  5. 完成 (进入主应用)

路由: /onboarding
首次启动自动跳转，非首次跳过
```

#### 9.1.6 认证鸡生蛋修复

**现状**: `POST /api/v1/agent-identity/token` 本身被 AgentAuthMiddleware 保护，需要 token 才能拿 token。

**修复**: 将 token 端点加入 `_PUBLIC_PATHS`，或新增独立公开的 `/api/v1/auth/login` 端点。

### 9.2 P1 — 高优，影响体验

#### 9.2.1 硬件检测引擎

```
backend/engine/hardware_probe.py

class HardwareProbe:
    - cpu_info()    → {model, cores, arch}
    - ram_total()   → 总内存 GB
    - gpu_info()    → [{name, vram_gb, cuda_support}]
    - recommend()   → 根据硬件返回推荐模型列表
    - disk_free()   → 检查 models/ 目录所在磁盘的剩余空间
```

#### 9.2.2 端口冲突处理

- 后端默认 18080，备用 18081/18082
- llama-server 默认 8080，备用 8081/8082
- 启动时检测 → 占用了自动找下一个

#### 9.2.3 Crash 恢复

- llama-server 崩溃 → 自动重启（最多 3 次）
- 连续 3 次崩溃 → 提示用户"模型运行异常，建议切换模型或检查内存"
- 后端崩溃 → WebView2 壳展示错误页 + 重启按钮

#### 9.2.4 卸载清理

- 卸载时弹窗："是否同时删除已下载的模型文件 (X.X GB)？"
- 勾选 → 删除 %APPDATA%/SuperNiuma/
- 不勾选 → 保留数据，下次安装自动恢复

#### 9.2.5 多模型管理 UI

```
SettingsView 新增"模型管理"面板:
  ┌─────────────────────────────────────┐
  │  已下载模型                          │
  │  ● Qwen3 8B (5.0GB) — 当前使用     │
  │  ○ Gemma 4 12B (7.0GB)             │
  │                                      │
  │  [+ 下载更多模型]                    │
  │                                      │
  │  云端模型                            │
  │  DeepSeek V4: [API Key 配置]        │
  │  Kimi:        [API Key 配置]        │
  └─────────────────────────────────────┘
```

#### 9.2.6 模型广场 UI (Plaza 扩展)

PlazaView 新增"模型" Tab，展示可下载的模型卡片：
- 模型名称、体积、推荐硬件
- 下载按钮 + 进度条
- 已下载 vs 未下载状态区分

### 9.3 P2 — 体验优化

#### 9.3.1 GPU 加速检测

- 检测 CUDA/ROCm/Vulkan 可用性
- 自动传 `--n-gpu-layers 999` 给 llama-server
- 前端显示"GPU 加速已启用"标识

#### 9.3.2 系统托盘

- 最小化到托盘
- 托盘菜单：显示/退出/快速对话
- 可选开机自启

#### 9.3.3 自动更新

- 启动时检查 GitHub Release
- 后台下载增量更新
- 下次启动自动安装

#### 9.3.4 安装注册表

- 注册到 Windows 添加/删除程序
- 关联 `.niuma` 工作间文件（v2.0）

### 9.4 补齐工作量估算

| 优先级 | 项目 | 估时 | 状态 |
|:------:|------|:----:|:----:|
| P0 | 模型适配器改造 + 动态注册 | 1d | ✅ |
| P0 | llama.cpp 进程管理 | 1.5d | ✅ |
| P0 | 桌面壳启动器 | 2d | ✅ |
| P0 | 模型下载服务 (后端) | 2d | ✅ |
| P0 | 首次启动引导页 (前端) | 2d | ✅ |
| P0 | 认证鸡生蛋修复 | 0.5d | ✅ |
| P1 | 硬件检测 | 0.5d | |
| P1 | 端口冲突/Crash恢复 | 1d | |
| P1 | 卸载清理逻辑 | 0.5d | |
| P1 | 多模型管理 UI | 1.5d | |
| P1 | Plaza 模型卡片 | 1d | |
| P2 | GPU 检测/托盘/更新 | 3d | |
| | **P0 合计** | **9d** | **✅ 全部完成** |
| | **P0+P1 合计** | **13.5d** | |
| | **全量** | **16.5d** | |

### 9.5 P0 交付物清单

| # | 文件 | 说明 |
|---|------|------|
| 1 | `middleware/agent_auth.py` | +3 公开路径 (token/download) |
| 2 | `model_adapter/openai_compat.py` | Ollama → llama.cpp, +Qwen3 系列, +动态注册 |
| 3 | `config/settings.py` | +LLAMA_SERVER_* 配置项 |
| 4 | `engine/llama_manager.py` | llama.cpp 进程生命周期管理 (新建) |
| 5 | `routers/model_download.py` | 模型下载 REST API + SSE (新建) |
| 6 | `launcher.py` | 桌面壳启动编排 (新建) |
| 7 | `frontend-vue/src/views/OnboardingView.vue` | 首次启动引导页 (新建) |
| 8 | `frontend-vue/src/router/index.ts` | +onboarding 路由 |
| 9 | `main.py` | 集成 llama_manager 启动/关闭 + 注册 model_download |

---

## 附录 A：模型下载量估算

### 典型用户选择分布

| 选择 | 占比估计 | 下载量 |
|------|:------:|------|
| Qwen3 8B (推荐) | 60% | 5.0GB × 0.6 = 3.0GB |
| Gemma 4 12B | 25% | 7.0GB × 0.25 = 1.75GB |
| 跳过（用云端） | 10% | 0 |
| 高配大模型 | 5% | 19GB × 0.05 = 0.95GB |

**人均首次下载量：~5.7GB**

> 若使用 hf-mirror.com 国内镜像，100Mbps 宽带约需 7-8 分钟。

---

## 附录 B：模型对比速查

| 维度 | Gemma 4 12B | Qwen3 8B |
|------|------------|----------|
| 开发商 | Google DeepMind | 阿里通义 |
| 许可证 | Apache 2.0 | Apache 2.0 |
| 参数量 | 12B | 8B |
| Q4_K_M 体积 | ~7GB | ~5GB |
| 最低内存 | 12GB | 10GB |
| 中文能力 | 多语言支持 | **中文专优** |
| 多模态 | 文本+图像 | 文本 |
| 上下文 | 256K | 128K |
| MTP 加速 | 支持 | 不支持 |
| 最佳场景 | 多语言/编程 | 中文对话/创作 |

---

> **文档维护**：本文档随打包方案演进更新。
>
> **变更日志**：
> - 2026-07-15 v1.0 — 初版，定义安装包不内置模型、首次启动下载策略、Gemma 4 + Qwen3 双系列
