"""
模型下载服务 — P0-4

提供模型发现、下载、进度追踪、本地管理的 REST API。
依赖 huggingface_hub 实现断点续传。
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, Query
from pydantic import BaseModel, Field

from schemas.common import make_response, make_error
from config.settings import settings
from engine.llama_manager import llama_manager
from model_adapter.openai_compat import register_local_models

logger = logging.getLogger("niuma.models.download")
router = APIRouter()

# 下载任务状态: {task_id: {status, progress, ...}}
_download_tasks: dict[str, dict] = {}

# 可下载模型定义
DOWNLOADABLE_MODELS = [
    # ── Qwen3 千问系列 ──
    {
        "id": "qwen3-8b",
        "name": "Qwen3 8B（128K）",
        "desc": "阿里通义千问，中文能力业界领先",
        "series": "qwen3",
        "repo": "unsloth/Qwen3-8B-GGUF",
        "file": "Qwen3-8B-Q4_K_M.gguf",
        "size_gb": 5.0,
        "min_ram_gb": 10,
        "recommended": True,
        "tags": ["中文", "日常对话", "创作"],
    },
    {
        "id": "qwen3-14b",
        "name": "Qwen3 14B（128K）",
        "desc": "更大参数，中文深度创作与分析",
        "series": "qwen3",
        "repo": "unsloth/Qwen3-14B-GGUF",
        "file": "Qwen3-14B-Q4_K_M.gguf",
        "size_gb": 8.5,
        "min_ram_gb": 16,
        "recommended": False,
        "tags": ["中文", "深度创作", "分析"],
    },
    # ── Gemma 4 系列 ──
    {
        "id": "gemma-4-e4b",
        "name": "Gemma 4 E4B（128K）",
        "desc": "Google 轻量多模态模型，支持文本+图像",
        "series": "gemma4",
        "repo": "unsloth/gemma-4-E4B-it-GGUF",
        "file": "gemma-4-E4B-it-Q8_0.gguf",
        "size_gb": 3.0,
        "min_ram_gb": 6,
        "recommended": False,
        "tags": ["多模态", "轻量", "低配"],
    },
    {
        "id": "gemma-4-12b",
        "name": "Gemma 4 12B（256K）",
        "desc": "Google 主力桌面模型，256K 长上下文",
        "series": "gemma4",
        "repo": "unsloth/gemma-4-12B-it-GGUF",
        "file": "gemma-4-12B-it-Q4_K_M.gguf",
        "size_gb": 7.0,
        "min_ram_gb": 12,
        "recommended": False,
        "tags": ["多语言", "编程", "长上下文"],
    },
    {
        "id": "gemma-4-26b",
        "name": "Gemma 4 26B-A4B（256K）",
        "desc": "Google MoE 高质量模型，速度与质量最优比",
        "series": "gemma4",
        "repo": "unsloth/gemma-4-26B-A4B-it-GGUF",
        "file": "gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf",
        "size_gb": 18.0,
        "min_ram_gb": 22,
        "recommended": False,
        "tags": ["最强", "MoE", "高端"],
    },
]

# 下载镜像源（按优先级）
_DOWNLOAD_MIRRORS = [
    {"name": "hf-mirror.com（国内）", "endpoint": "https://hf-mirror.com"},
    {"name": "HuggingFace 官方", "endpoint": "https://huggingface.co"},
    {"name": "ModelScope（阿里）", "endpoint": "https://modelscope.cn"},
]


class DownloadRequest(BaseModel):
    model_id: str = Field(..., description="模型 ID，如 qwen3-8b")
    mirror: str = Field(default="hf-mirror.com", description="镜像源 endpoint")


# ── 可下载列表 ──

@router.get("/models/downloadable")
async def api_downloadable_models(request: Request):
    """获取可下载模型列表"""
    rid = getattr(request.state, "request_id", "")

    # 标记已下载的状态
    local_models = llama_manager.list_models()
    local_names = {m["name"] for m in local_models}

    result = []
    for m in DOWNLOADABLE_MODELS:
        item = {**m}
        item["downloaded"] = m["id"] in local_names or any(
            lm["name"].startswith(m["id"]) for lm in local_models
        )
        # 检查是否有活跃的下载任务
        for tid, task in _download_tasks.items():
            if task.get("model_id") == m["id"] and task["status"] in ("downloading", "pending"):
                item["downloading"] = True
                item["download_task_id"] = tid
                item["download_progress"] = task.get("progress", 0)
                break
        result.append(item)

    return make_response({
        "models": result,
        "mirrors": _DOWNLOAD_MIRRORS,
    }, request_id=rid)


# ── 触发下载 ──

@router.post("/models/download")
async def api_download_model(request: Request, body: DownloadRequest):
    """触发模型下载（异步后台任务）"""
    rid = getattr(request.state, "request_id", "")

    # 查找模型定义
    model_def = next((m for m in DOWNLOADABLE_MODELS if m["id"] == body.model_id), None)
    if not model_def:
        return make_error("MODEL_NOT_FOUND", f"未知模型: {body.model_id}", request_id=rid)

    # 检查是否已下载
    dest_dir = Path(settings.LLAMA_MODELS_DIR)
    dest_file = dest_dir / model_def["file"]
    if dest_file.exists():
        return make_response({
            "status": "already_downloaded",
            "model_id": body.model_id,
            "path": str(dest_file),
        }, request_id=rid)

    # 检查是否有正在进行的下载
    for tid, task in _download_tasks.items():
        if task.get("model_id") == body.model_id and task["status"] in ("downloading", "pending"):
            return make_response({
                "status": "already_downloading",
                "task_id": tid,
                "progress": task.get("progress", 0),
            }, request_id=rid)

    # 找到镜像 endpoint
    mirror = next((m["endpoint"] for m in _DOWNLOAD_MIRRORS if m["endpoint"] == body.mirror),
                  _DOWNLOAD_MIRRORS[0]["endpoint"])

    # 创建下载任务
    task_id = f"{body.model_id}-{os.urandom(4).hex()}"
    _download_tasks[task_id] = {
        "model_id": body.model_id,
        "status": "pending",
        "progress": 0,
        "speed_mbps": 0,
        "mirror": mirror,
        "started_at": "",
    }

    # 启动后台下载
    asyncio.create_task(_do_download(task_id, model_def, dest_dir, mirror))

    return make_response({
        "status": "started",
        "task_id": task_id,
        "model_id": body.model_id,
        "mirror": mirror,
    }, request_id=rid)


# ── 下载进度 SSE ──

@router.get("/models/download/{task_id}/progress")
async def api_download_progress(request: Request, task_id: str):
    """SSE 推送下载进度"""
    from fastapi.responses import StreamingResponse

    async def event_stream():
        last_progress = -1
        while True:
            task = _download_tasks.get(task_id)
            if not task:
                yield f"event: error\ndata: {json.dumps({'message': '任务不存在'})}\n\n"
                break

            progress = task.get("progress", 0)
            status = task["status"]

            if status in ("completed", "failed", "cancelled"):
                yield f"event: {status}\ndata: {json.dumps(task)}\n\n"
                break

            if progress != last_progress:
                yield f"event: progress\ndata: {json.dumps(task)}\n\n"
                last_progress = progress

            await asyncio.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── 取消下载 ──

@router.post("/models/download/{task_id}/cancel")
async def api_cancel_download(request: Request, task_id: str):
    """取消下载任务"""
    rid = getattr(request.state, "request_id", "")
    task = _download_tasks.get(task_id)
    if not task:
        return make_error("TASK_NOT_FOUND", "任务不存在", request_id=rid)

    task["status"] = "cancelled"
    task["_cancel"] = True
    return make_response({"status": "cancelled", "task_id": task_id}, request_id=rid)


# ── 本地模型管理 ──

@router.get("/models/local")
async def api_local_models(request: Request):
    """列出已下载的本地模型"""
    rid = getattr(request.state, "request_id", "")
    models = llama_manager.list_models()
    return make_response({"models": models, "count": len(models)}, request_id=rid)


@router.post("/models/local/{model_name}/activate")
async def api_activate_model(request: Request, model_name: str):
    """切换当前使用的本地模型"""
    rid = getattr(request.state, "request_id", "")
    local_models = llama_manager.list_models()
    target = next((m for m in local_models if m["name"] == model_name), None)
    if not target:
        return make_error("MODEL_NOT_FOUND", f"本地模型 {model_name} 不存在", request_id=rid)

    success = await llama_manager.restart(target["path"])
    if success:
        return make_response({
            "status": "activated",
            "model": target["name"],
            "path": target["path"],
        }, request_id=rid)
    return make_error("ACTIVATE_FAILED", "切换模型失败", request_id=rid)


@router.delete("/models/local/{model_name}")
async def api_delete_model(request: Request, model_name: str):
    """删除本地模型文件"""
    rid = getattr(request.state, "request_id", "")
    local_models = llama_manager.list_models()
    target = next((m for m in local_models if m["name"] == model_name), None)
    if not target:
        return make_error("MODEL_NOT_FOUND", f"本地模型 {model_name} 不存在", request_id=rid)

    # 不能删除正在使用的模型
    if target.get("active"):
        return make_error("MODEL_ACTIVE", "无法删除正在使用的模型，请先切换到其他模型", request_id=rid)

    try:
        os.remove(target["path"])
        return make_response({"status": "deleted", "model": model_name}, request_id=rid)
    except OSError as e:
        return make_error("DELETE_FAILED", str(e), request_id=rid)


# ── 下载执行 ──

async def _do_download(task_id: str, model_def: dict, dest_dir: Path, mirror: str):
    """后台执行模型下载"""
    task = _download_tasks.get(task_id)
    if not task:
        return

    task["status"] = "downloading"
    task["started_at"] = str(asyncio.get_event_loop().time())

    dest_dir.mkdir(parents=True, exist_ok=True)

    # 清理中间文件
    temp_file = dest_dir / f".{model_def['file']}.download"

    try:
        from huggingface_hub import hf_hub_download
        import time

        last_bytes = [0]
        last_time = [time.time()]

        def progress_callback(current: int, total: int):
            if task.get("_cancel"):
                raise asyncio.CancelledError("用户取消")

            pct = round(current / total * 100, 1) if total > 0 else 0
            now = time.time()
            elapsed = now - last_time[0]
            if elapsed >= 1.0:
                speed = (current - last_bytes[0]) / elapsed / 1024 / 1024
                task["speed_mbps"] = round(speed, 1)
                last_bytes[0] = current
                last_time[0] = now
            task["progress"] = pct

        loop = asyncio.get_event_loop()
        filepath = await loop.run_in_executor(
            None,
            lambda: hf_hub_download(
                repo_id=model_def["repo"],
                filename=model_def["file"],
                local_dir=str(dest_dir),
                endpoint=mirror,
                resume_download=True,
            )
        )

        # 下载完成
        task["status"] = "completed"
        task["progress"] = 100
        task["path"] = filepath

        # 动态注册模型
        try:
            from model_adapter.registry import model_registry
            register_local_models(str(dest_dir), model_registry._adapters)
        except Exception as e:
            logger.warning("模型注册失败: %s", e)

        logger.info("模型下载完成: %s → %s", model_def["id"], filepath)

    except asyncio.CancelledError:
        task["status"] = "cancelled"
        logger.info("模型下载已取消: %s", model_def["id"])
    except Exception as e:
        task["status"] = "failed"
        task["error"] = str(e)[:500]
        logger.error("模型下载失败: %s — %s", model_def["id"], e)
    finally:
        # 清理临时文件
        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass
