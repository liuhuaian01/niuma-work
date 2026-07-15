# 超级牛马 Super Niuma

> 本地优先的 AI 工作台。太极引擎元大脑驱动，本地模型与云端 API 随心组合 —— 不烧 Token、数据不出门。

---

## 快速开始

### 环境要求

- Python >= 3.11
- Windows 10+ (WebView2 内置)

### 安装与运行

```bash
# 1. 安装后端依赖
cd backend
.venv/Scripts/pip install -r requirements.txt

# 2. 下载推理引擎（首次）
# 从 https://github.com/ggml-org/llama.cpp/releases 下载 Windows CPU 版
# 解压 llama-server.exe 到 data/bin/

# 3. 下载模型（首次）
# 自动: 启动后端后访问 /#/onboarding 引导下载
# 手动: 从 HuggingFace 下载 GGUF 模型到 data/models/

# 4. 启动后端
python main.py  # -> http://127.0.0.1:18080

# 5. 启动前端开发服务器
cd ../frontend-vue && npm run dev  # -> http://localhost:5173
```

---

## 本地模型

| 系列 | 模型 | 体积 | 最低内存 | 推荐场景 |
|------|------|------|---------|---------|
| **Gemma 4** | E4B / 12B / 26B-A4B | 3-18GB | 6-22GB | 多语言、编程、多模态 |
| **Qwen3** | 8B / 14B / 32B | 5-19GB | 10-24GB | 中文对话、创作 |

首次启动自动检测硬件推荐最佳模型，断点续传下载，支持 hf-mirror.com 国内镜像。

---

## 许可证

本项目为商业软件。内测阶段免费使用，正式版激活码制。

---

## 作者

刘淮安 LIUHUAIAN
