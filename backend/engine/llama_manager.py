"""
llama.cpp server 进程管理器 — P0-3

负责 llama-server.exe 的生命周期管理：
- 启动/停止/重启
- 健康检查
- 崩溃自动恢复
- 模型切换

集成到 main.py lifespan：启动时自动拉起，关闭时优雅退出。
"""

import asyncio
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import httpx

from config.settings import settings

logger = logging.getLogger("niuma.llama")


class LlamaManager:
    """llama.cpp server 进程管理器"""

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._model_path: Optional[str] = None
        self._port: int = settings.LLAMA_SERVER_PORT
        self._host: str = settings.LLAMA_SERVER_HOST
        self._healthy: bool = False
        self._restart_count: int = 0
        self._max_restarts: int = 3
        self._restart_window: float = 60.0  # 60 秒内最多重启 3 次
        self._first_restart_time: float = 0.0

    # ── properties ──

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    @property
    def is_healthy(self) -> bool:
        return self._healthy

    @property
    def current_model(self) -> Optional[str]:
        return self._model_path

    @property
    def api_url(self) -> str:
        return f"http://{self._host}:{self._port}/v1"

    # ── startup ──

    async def start(self, model_path: Optional[str] = None) -> bool:
        """启动 llama-server。

        Args:
            model_path: GGUF 模型文件的绝对路径。如果为 None，自动扫描。

        Returns:
            True 如果启动成功
        """
        if self.is_running:
            logger.info("llama-server 已在运行 (pid=%s)", self._process.pid)
            return True

        # 找到模型文件
        if model_path:
            model_file = Path(model_path)
        else:
            model_file = self._find_default_model()

        if not model_file or not model_file.exists():
            logger.warning("未找到可用的 GGUF 模型文件，跳过 llama-server 启动")
            return False

        self._model_path = str(model_file)

        # 检查二进制文件
        bin_path = _find_llama_binary()
        if not bin_path:
            logger.error("未找到 llama-server 二进制文件: %s", settings.LLAMA_BIN_PATH)
            return False

        # 构建启动参数
        args = [
            str(bin_path),
            "--model", str(model_file),
            "--host", self._host,
            "--port", str(self._port),
            "--ctx-size", str(settings.LLAMA_SERVER_CTX_SIZE),
            "--n-gpu-layers", str(settings.LLAMA_SERVER_N_GPU_LAYERS),
            "--temp", str(settings.LLAMA_SERVER_TEMP),
            "--top-p", "0.95",
            "--top-k", "64",
            "--no-webui",  # 不启动 llama.cpp 自带的 WebUI
        ]

        logger.info("启动 llama-server: %s (model=%s)", bin_path.name, model_file.name)
        logger.debug("args: %s", " ".join(args))

        try:
            if sys.platform == "win32":
                self._process = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                self._process = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
        except FileNotFoundError:
            logger.error("llama-server 二进制文件不存在: %s", bin_path)
            return False
        except Exception as e:
            logger.error("llama-server 启动失败: %s", e)
            return False

        # 等待健康就绪（最多 30 秒）
        healthy = await self._wait_healthy(timeout=30.0)
        if healthy:
            logger.info("llama-server 就绪 (pid=%s, model=%s)", self._process.pid, model_file.name)
        else:
            logger.error("llama-server 启动超时，超过 30 秒未就绪")
        return healthy

    async def stop(self):
        """停止 llama-server"""
        if self._process is None:
            return

        pid = self._process.pid
        logger.info("停止 llama-server (pid=%s)", pid)

        try:
            if sys.platform == "win32":
                self._process.terminate()
            else:
                self._process.terminate()

            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("llama-server 未响应 SIGTERM，强制终止")
                self._process.kill()
                self._process.wait(timeout=5)
        except Exception as e:
            logger.error("停止 llama-server 时出错: %s", e)
        finally:
            self._process = None
            self._healthy = False
            logger.info("llama-server 已停止")

    async def restart(self, model_path: Optional[str] = None) -> bool:
        """重启 llama-server（切换模型时使用）"""
        await self.stop()
        await asyncio.sleep(1)
        return await self.start(model_path)

    # ── health check ──

    async def check_health(self) -> bool:
        """检查 llama-server 是否响应"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.api_url}/models")
                self._healthy = resp.status_code == 200
                return self._healthy
        except Exception:
            self._healthy = False
            return False

    async def _wait_healthy(self, timeout: float = 30.0) -> bool:
        """轮询等待 llama-server 健康就绪"""
        start = time.time()
        while time.time() - start < timeout:
            if await self.check_health():
                return True
            await asyncio.sleep(0.5)

        # 检查进程是否还活着
        if self._process and self._process.poll() is not None:
            stderr = ""
            try:
                stderr = self._process.stderr.read().decode("utf-8", errors="replace")[-500:]
            except Exception:
                pass
            logger.error("llama-server 进程已退出 (code=%s), stderr: %s",
                         self._process.returncode, stderr)
        return False

    # ── crash recovery ──

    async def handle_crash(self) -> bool:
        """处理 llama-server 崩溃：自动重启（最多 3 次）"""
        now = time.time()

        # 重置重启计数（超过窗口期）
        if now - self._first_restart_time > self._restart_window:
            self._restart_count = 0
            self._first_restart_time = now

        self._restart_count += 1

        if self._restart_count > self._max_restarts:
            logger.critical(
                "llama-server 在 %.0f 秒内崩溃 %d 次，停止自动重启",
                self._restart_window, self._max_restarts,
            )
            return False

        logger.warning(
            "llama-server 崩溃，自动重启 (%d/%d)",
            self._restart_count, self._max_restarts,
        )
        await asyncio.sleep(2)
        return await self.start(self._model_path)

    # ── model discovery ──

    def _find_default_model(self) -> Optional[Path]:
        """扫描模型目录，返回优先级最高的 GGUF 文件。

        优先级: Qwen3 8B > Gemma 4 12B > Gemma 4 E4B > 任意 GGUF
        """
        models_dir = Path(settings.LLAMA_MODELS_DIR)
        if not models_dir.exists():
            return None

        gguf_files = list(models_dir.glob("*.gguf"))
        if not gguf_files:
            return None

        # 按优先级排序
        priority_prefixes = [
            "Qwen3-8B-",
            "Qwen3-14B-",
            "Qwen3-32B-",
            "gemma-4-12B-",
            "gemma-4-E4B-",
            "gemma-4-26B-",
        ]
        for prefix in priority_prefixes:
            for f in gguf_files:
                if f.name.startswith(prefix):
                    return f

        # fallback: 返回第一个 GGUF
        return gguf_files[0]

    def list_models(self) -> list[dict]:
        """列出已下载的本地模型"""
        models_dir = Path(settings.LLAMA_MODELS_DIR)
        if not models_dir.exists():
            return []

        result = []
        for gguf in sorted(models_dir.glob("*.gguf"), key=lambda f: f.stat().st_size, reverse=True):
            stat = gguf.stat()
            result.append({
                "name": gguf.stem,
                "path": str(gguf),
                "size_mb": round(stat.st_size / 1024 / 1024, 1),
                "active": self._model_path and Path(self._model_path).samefile(gguf),
            })
        return result


# ── helper ──

def _find_llama_binary() -> Optional[Path]:
    """查找 llama-server 二进制文件"""
    # 1. 从 config 指定的路径
    bin_path = Path(settings.LLAMA_BIN_PATH)
    if bin_path.exists():
        return bin_path

    # 2. 从 PATH 查找
    import shutil
    found = shutil.which("llama-server")
    if found:
        return Path(found)

    # 3. 常见安装路径
    common_paths = [
        Path(os.environ.get("APPDATA", "")) / "SuperNiuma" / "bin" / "llama-server.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "SuperNiuma" / "bin" / "llama-server.exe",
    ]
    for p in common_paths:
        if p.exists():
            return p

    return None


# 全局单例
llama_manager = LlamaManager()
