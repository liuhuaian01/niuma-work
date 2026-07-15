"""
超级牛马桌面壳启动器 — P0-5

编排应用启动流程：
1. 检测运行环境（Python/llama-server/hermes）
2. 启动 FastAPI 后端 (uvicorn 子进程)
3. 等待后端健康检查
4. 检测首次启动 → 加载引导页 或 主应用
5. 打开 WebView2 窗口

Windows 依赖: pywebview + WebView2 (Win10+ 内置)
"""

import asyncio
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# ── 路径配置 ──

APP_NAME = "SuperNiuma"
APP_DATA = os.environ.get("NIUMA_DATA_DIR",
                           str(Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / APP_NAME))

BACKEND_PORT = int(os.environ.get("NIUMA_PORT", "18080"))
BACKEND_HOST = os.environ.get("NIUMA_HOST", "127.0.0.1")
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
HEALTH_URL = f"{BACKEND_URL}/api/v1/health"


def setup_logging():
    log_dir = Path(APP_DATA) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "launcher.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


logger = logging.getLogger("niuma.launcher")


# ── 环境检测 ──

def check_environment() -> dict:
    """检测运行环境，返回状态报告"""
    report = {"python": sys.executable, "version": sys.version, "issues": []}

    # WebView2 检测 (Windows)
    if sys.platform == "win32":
        try:
            import webview
            report["webview"] = "ok"
        except ImportError:
            report["webview"] = "missing"
            report["issues"].append("pywebview 未安装，将降级为浏览器模式")

    # llama-server 检测
    llama_bin = os.environ.get("NIUMA_LLAMA_BIN",
                               str(Path(APP_DATA) / "bin" / "llama-server.exe"))
    if Path(llama_bin).exists():
        report["llama_server"] = llama_bin
    else:
        report["llama_server"] = "not_found"
        report["issues"].append(f"llama-server 未找到: {llama_bin}")

    # 模型目录检测
    models_dir = os.environ.get("NIUMA_MODELS_DIR",
                                str(Path(APP_DATA) / "models"))
    gguf_count = len(list(Path(models_dir).glob("*.gguf"))) if Path(models_dir).exists() else 0
    report["models_available"] = gguf_count

    # 首次启动判断
    settings_file = Path(APP_DATA) / "backend" / "settings.json"
    report["first_launch"] = not settings_file.exists()

    return report


# ── 后端管理 ──

def start_backend() -> subprocess.Popen:
    """启动 FastAPI 后端进程"""
    backend_dir = Path(__file__).parent / "backend"

    # 检查是否从 PyInstaller 打包运行
    if getattr(sys, 'frozen', False):
        backend_exe = Path(sys.executable).parent / "SuperNiuma-backend.exe"
        if backend_exe.exists():
            logger.info("启动打包后端: %s", backend_exe)
            return subprocess.Popen(
                [str(backend_exe)],
                cwd=str(backend_dir),
            )

    # 开发模式：直接用 Python
    backend_script = backend_dir / "main.py"
    if backend_script.exists():
        logger.info("启动开发后端: %s", backend_script)
        env = os.environ.copy()
        env["NIUMA_PORT"] = str(BACKEND_PORT)
        env["NIUMA_HOST"] = BACKEND_HOST
        return subprocess.Popen(
            [sys.executable, str(backend_script)],
            cwd=str(backend_dir),
            env=env,
        )

    raise FileNotFoundError(f"未找到后端入口: {backend_script}")


async def wait_backend_ready(timeout: float = 60.0) -> bool:
    """等待后端健康检查通过"""
    import httpx

    start = time.time()
    while time.time() - start < timeout:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(HEALTH_URL)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("data", {}).get("status", "")
                    if status == "healthy":
                        elapsed = time.time() - start
                        logger.info("后端就绪 (%.1fs, status=%s)", elapsed, status)
                        return True
        except Exception:
            pass
        await asyncio.sleep(1)

    logger.error("后端启动超时 (%.0fs)", timeout)
    return False


# ── WebView2 窗口 ──

def open_window(url: str, title: str = "超级牛马工作台"):
    """打开 WebView2 窗口"""
    try:
        import webview
        logger.info("打开 WebView2: %s", url)
        webview.create_window(
            title=title,
            url=url,
            width=1400,
            height=900,
            min_size=(1024, 600),
            resizable=True,
            fullscreen=False,
        )
        webview.start(gui="edgechromium" if sys.platform == "win32" else None)
    except ImportError:
        logger.warning("pywebview 不可用，尝试浏览器模式")
        import webbrowser
        webbrowser.open(url)
    except Exception as e:
        logger.error("WebView2 启动失败: %s", e)


# ── 主流程 ──

async def main():
    setup_logging()
    logger.info("=" * 50)
    logger.info("超级牛马工作台 v1.5")
    logger.info("=" * 50)

    # 1. 环境检测
    env_report = check_environment()
    logger.info("环境检测: python=%s, llama=%s, models=%d, first_launch=%s",
                env_report["version"][:20],
                "ok" if env_report["llama_server"] != "not_found" else "missing",
                env_report["models_available"],
                env_report["first_launch"])
    for issue in env_report["issues"]:
        logger.warning("  ⚠ %s", issue)

    # 2. 启动后端
    logger.info("启动后端服务...")
    backend_proc = start_backend()
    logger.info("后端 PID: %s", backend_proc.pid)

    # 3. 等待就绪
    ready = await wait_backend_ready()
    if not ready:
        logger.error("后端启动失败，退出")
        backend_proc.terminate()
        return 1

    # 4. 决定加载页面
    if env_report["first_launch"]:
        url = f"{BACKEND_URL}/#/onboarding"
    else:
        url = f"{BACKEND_URL}/#/chat"

    # 5. 打开窗口
    open_window(url, "超级牛马工作台")

    # 6. 等待后端退出
    backend_proc.wait()
    logger.info("后端已退出")
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("用户中断")
        sys.exit(0)
