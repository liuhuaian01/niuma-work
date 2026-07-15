# 超级牛马 Super Niuma

> 太极引擎驱动的 AI Agent 工作台 — "不烧Token、不打扰用户、不越界、但越用越强"
>
> **当前版本：v0.9.0-dev（开发者内测版）** | 2026-07-15

---

## 项目概述

超级牛马是一个本地优先的 AI Agent 协作工作台。核心理念是让 AI Agent 像"牛马"一样高效干活，而用户不需要理解复杂的模型选择、Token预算、降级链等技术概念。

**产品定位**：AI 工作室（Studio），不是 AI 工厂（Factory）。

**技术底座**：太极引擎（Taiji Engine）驱动，llama.cpp 本地推理，Gemma 4 + Qwen3 双模型系列。安装包 ~186MB 纯壳，首次启动自动下载推荐模型。

---

## 项目结构

```
super-niuma/
├── backend/                    # FastAPI 后端
│   ├── engine/                 # 太极引擎
│   │   ├── llama_manager.py    # llama.cpp 进程管理 (v0.9)
│   │   ├── taiji.py            # 太极引擎核心——七元体系
│   │   ├── smart_allocator.py  # 四两拨千斤：智能模型选择
│   │   └── ...                 # 50+ 模块
│   ├── routers/                # API路由 (36个)
│   ├── model_adapter/          # 模型适配层 (llama.cpp + 云端)
│   ├── middleware/              # 中间件（9层安全防护）
│   ├── launcher.py             # 桌面壳启动器
│   ├── main.py                 # 应用入口
│   └── pyproject.toml
├── frontend-vue/               # Vue3 前端 (v0.9)
│   ├── src/
│   │   ├── views/              # 10个页面 + Onboarding 引导
│   │   ├── components/         # 13个组件
│   │   └── services/api.ts     # API 客户端
│   └── package.json
├── data/                       # 运行时数据
│   ├── bin/llama-server.exe    # llama.cpp 推理引擎
│   └── models/                 # GGUF 模型文件
├── deliverables/               # 方案文档
│   ├── installer-packaging-spec-v1.0.md    # 安装包方案
│   └── install-management-platform-spec-v1.0.md  # 管理平台方案
├── CHANGELOG.md                # 变更日志
└── README.md
```

---

## 快速开始

### 环境要求

- Python ≥ 3.11
- Windows 10+ (WebView2 内置)

### 安装与运行

```bash
# 1. 安装后端依赖
cd backend
.venv/Scripts/pip install -r requirements.txt
# 或: uv sync

# 2. 下载推理引擎（首次）
# 从 https://github.com/ggml-org/llama.cpp/releases 下载 Windows CPU 版
# 解压 llama-server.exe 到 data/bin/

# 3. 下载模型（首次）
# 自动: 启动后端后访问 /#/onboarding 引导下载
# 手动: python -c "from huggingface_hub import hf_hub_download; hf_hub_download('unsloth/Qwen3-8B-GGUF', 'Qwen3-8B-Q4_K_M.gguf', local_dir='data/models')"

# 4. 启动后端
python main.py  # → http://127.0.0.1:18080

# 5. 启动前端开发服务器
cd ../frontend-vue && npm run dev  # → http://localhost:5173
```

---

## 本地模型

| 系列 | 模型 | 体积 | 最低内存 | 推荐场景 |
|------|------|------|---------|---------|
| **Gemma 4** | E4B / 12B / 26B-A4B | 3-18GB | 6-22GB | 多语言、编程、多模态 |
| **Qwen3** | 8B / 14B / 32B | 5-19GB | 10-24GB | 中文对话、创作 |

首次启动自动检测硬件推荐最佳模型，断点续传下载，支持 hf-mirror.com 国内镜像。

---

## 太极引擎七律

| 定律 | 哲学 | 引擎模块 | 实现度 |
|:--|:--|:--|:--:|
| 阴阳平衡 | 本地←→云端+太极网格动态均衡 | Dynamic Balancer + TaijiMesh | 80% |
| 四两拨千斤 | 精准用力，不烧Token | Smart Allocator + CCR 压缩层 | 90% |
| 以静制动 | 关键时刻才说话 | Attention Engine + 夜巡 | 85% |
| 无为而治 | 自动修复，无需干预 | Self-Healing + 递归自进化 | 85% |
| 顺势而为 | 借力开源生态 | Leverage Arch + Hermes适配器 | 80% |
| 刚柔并济 | 硬开关+软积累 | Dual-Track + 能力开关 | 85% |
| 生生不息 | 越用越强，永续进化 | GoalLoop + 涌现引擎 + 递归进化 | 80% |

*当前综合实现度：约 83%（截至 2026-06-29）*

---

## 11条产品设计开发铁则

1. **极致安全** — 双向安全：数据不出本地 + 不可被破解
2. **极致性能** — 本地友好，8GB笔记本流畅运行
3. **极致轻量** — 大师50行解决的问题不写100行
4. **极致高效** — 走最优路径、最快速度
5. **极致简单** — 60岁大妈都能用
6. **极致质量** — 产品×开发×产出物三重质量
7. **极致审美** — 看得见和看不见的都美
8. **极致体验** — 用了就不想换别的平台
9. **极致交互** — 超简单、超友好、超好用
10. **极致Token低消耗** — 国产模型优先，能省则省
11. **极致克制（Pi原则）** — 该做的一件不少，不该做的一件不多

---

## 预装模型

| 系列 | 模型 | 体积 | 最低内存 | 推荐场景 |
|------|------|------|---------|---------|
| **Gemma 4** | E4B / 12B / 26B-A4B | 3-18GB | 6-22GB | 多语言、编程、多模态 |
| **Qwen3** | 8B / 14B / 32B | 5-19GB | 10-24GB | 中文对话、创作 |

首次启动自动检测硬件推荐最佳模型，断点续传下载，支持 hf-mirror.com 国内镜像。

---

## 许可证

本项目为商业软件。
- 内测阶段：免费使用
- 正式版：激活码制，Pro/Enterprise 订阅

---

## 作者

**刘淮安 LIUHUAIAN**

起点LV5网文作者 · ACGN自媒体BBGTALK运营者 · AI开发者

---

## 版本历史

| 版本 | 日期 | 里程碑 |
|:--|:--|:--|
| **v0.9.0-dev** | **2026-07-15** | **前后端打通，Chat 全链路验证，首次启动引导，准备 PyInstaller 打包** |
| v0.3.0 | 2026-06-14 | 太极引擎 v1.7，36 引擎模块，33 路由，Neon Pulse v10.0 |
