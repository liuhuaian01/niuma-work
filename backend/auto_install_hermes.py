#!/usr/bin/env python3
"""
Niuma Agent 自动安装脚本

用途:
- 工作台启动时自动检测 Niuma Agent 是否已安装
- 如果未安装,自动执行安装流程
- 支持国内镜像源加速
- 无需用户手动操作

使用方法:
  python auto_install_hermes.py
"""

import sys
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime

# 进度文件路径(与脚本同目录)
PROGRESS_FILE = Path(__file__).parent / ".hermes_install_progress.json"


def update_progress(stage, status, progress_percent, message="", detail=""):
    """更新安装进度到 JSON 文件
    
    Args:
        stage: 当前阶段 (checking/installing/verifying/completed/failed)
        status: 状态 (running/success/error)
        progress_percent: 进度百分比 (0-100)
        message: 简短消息
        detail: 详细信息
    """
    progress_data = {
        "stage": stage,
        "status": status,
        "progress": progress_percent,
        "message": message,
        "detail": detail,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] 无法写入进度文件: {e}")


def print_step(step_num, message):
    """打印步骤信息"""
    print(f"\n{'=' * 60}")
    print(f"[{step_num}] {message}")
    print('=' * 60)


def check_hermes_installed():
    """检查 Niuma Agent 是否已安装"""
    update_progress("checking", "running", 5, "正在检测 Niuma Agent...")
    
    try:
        result = subprocess.run(
            ["hermes", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version_info = result.stdout.strip().split('\n')[0]
            print(f"[OK] 检测到 Niuma Agent: {version_info}")
            update_progress("completed", "success", 100, "Niuma Agent 已安装", version_info)
            return True
        else:
            update_progress("installing", "running", 10, "未检测到 Niuma Agent,准备安装...")
            return False
    except FileNotFoundError:
        update_progress("installing", "running", 10, "未检测到 Niuma Agent,准备安装...")
        return False
    except Exception as e:
        print(f"[WARN] 检查失败: {e}")
        update_progress("installing", "running", 10, f"检查异常: {e}")
        return False


def get_python_executable():
    """获取当前 Python 可执行文件路径"""
    return sys.executable


def install_hermes_cn():
    """使用国内镜像源安装 Hermes Agent"""
    print_step(1, "准备安装 Hermes Agent")
    update_progress("installing", "running", 15, "正在使用国内镜像源安装...")

    # 定义镜像源列表（按优先级）
    mirrors = [
        ("https://pypi.tuna.tsinghua.edu.cn/simple", "清华大学"),
        ("https://mirrors.aliyun.com/pypi/simple", "阿里云"),
        ("https://mirrors.cloud.tencent.com/pypi/simple", "腾讯云"),
    ]

    python_exe = get_python_executable()
    print(f"Python 路径: {python_exe}")
    print()

    for idx, (mirror_url, mirror_name) in enumerate(mirrors, 1):
        progress = 20 + (idx - 1) * 20  # 20%, 40%, 60%
        print(f"[尝试] 使用 {mirror_name} 镜像源...")
        print(f"       URL: {mirror_url}")
        update_progress("installing", "running", progress, f"尝试 {mirror_name} 镜像源...")

        try:
            # 先升级 pip
            print("\n[1/2] 升级 pip...")
            subprocess.run(
                [python_exe, "-m", "pip", "install", "--upgrade", "pip",
                 "-i", mirror_url],
                capture_output=True,
                timeout=120
            )

            # 安装 hermes-agent
            print("[2/2] 安装 hermes-agent (这可能需要几分钟)...")
            update_progress("installing", "running", progress + 10, f"正在从 {mirror_name} 下载...")
            
            result = subprocess.run(
                [python_exe, "-m", "pip", "install",
                 "hermes-agent>=0.14.0,<1.0.0",
                 "-i", mirror_url,
                 "--trusted-host", mirror_url.replace("https://", "").replace("/simple", "")],
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )

            if result.returncode == 0:
                print(f"\n[OK] 使用 {mirror_name} 安装成功!")
                update_progress("installing", "running", 80, f"{mirror_name} 安装成功")
                return True
            else:
                print(f"[FAIL] {mirror_name} 安装失败")
                if result.stderr:
                    print(f"       错误: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            print(f"[TIMEOUT] {mirror_name} 安装超时")
        except Exception as e:
            print(f"[ERROR] {mirror_name} 安装异常: {e}")

        print()

    return False


def install_hermes_official():
    """使用官方 PyPI 安装 Niuma Agent"""
    print_step(2, "尝试官方 PyPI 源")
    update_progress("installing", "running", 70, "尝试官方 PyPI 源...")

    python_exe = get_python_executable()

    try:
        print("安装 niuma-agent...")
        result = subprocess.run(
            [python_exe, "-m", "pip", "install", "hermes-agent>=0.14.0,<1.0.0"],
            capture_output=True,
            text=True,
            timeout=600
        )

        if result.returncode == 0:
            print("[OK] 官方源安装成功!")
            update_progress("installing", "running", 80, "官方源安装成功")
            return True
        else:
            print("[FAIL] 官方源安装失败")
            return False

    except Exception as e:
        print(f"[ERROR] 官方源安装异常: {e}")
        update_progress("failed", "error", 0, f"官方源安装异常: {e}")
        return False


def verify_installation():
    """验证安装是否成功"""
    print_step(3, "验证安装")
    update_progress("verifying", "running", 85, "正在验证安装...")

    if check_hermes_installed():
        print("\n[OK] Niuma Agent 已成功安装并可用!")

        # 显示版本信息
        try:
            result = subprocess.run(
                ["hermes", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            version_info = result.stdout.strip()
            print(f"\n版本信息:")
            for line in version_info.split('\n'):
                print(f"  {line}")
            
            update_progress("completed", "success", 100, "Niuma Agent 安装完成!", version_info)
        except subprocess.TimeoutExpired as e:
            # 超时异常，静默处理，不影响安装成功状态
            pass
        except FileNotFoundError:
            # hermes命令不存在，静默处理
            pass
        except OSError as e:
            # 其他系统错误，记录但继续
            print(f"\n[WARN] 获取版本信息失败: {e}")
        except Exception as e:
            # 未知异常，记录日志但不影响主流程
            print(f"\n[WARN] 获取版本信息时发生未知错误: {e}")
        
        update_progress("completed", "success", 100, "Niuma Agent 安装完成")

        return True
    else:
        print("\n[FAIL] 安装验证失败")
        update_progress("failed", "error", 0, "安装验证失败")
        return False


def main():
    """主函数"""
    start_time = time.time()

    print()
    print("=" * 60)
    print("  Niuma Agent 自动安装向导")
    print("=" * 60)
    print()
    print("此脚本将自动安装 Niuma Agent (超级牛马智能体引擎)")
    print("使用国内镜像源加速，无需 VPN")
    print()

    # 步骤 1: 检查是否已安装
    print_step(0, "检查安装状态")

    if check_hermes_installed():
        print("\n[OK] Niuma Agent 已安装，跳过安装流程")
        elapsed = time.time() - start_time
        print(f"\n耗时: {elapsed:.1f} 秒")
        return True

    print("[INFO] Niuma Agent 未安装，开始自动安装...")

    # 步骤 2: 尝试国内镜像源
    success = install_hermes_cn()

    # 步骤 3: 如果国内镜像失败，尝试官方源
    if not success:
        print("\n[INFO] 国内镜像源均失败，尝试官方 PyPI...")
        success = install_hermes_official()

    # 步骤 4: 验证安装
    if success:
        verified = verify_installation()
        if verified:
            print("\n" + "=" * 60)
            print("  [OK] Niuma Agent 自动安装完成！")
            print("=" * 60)
            elapsed = time.time() - start_time
            print(f"\n总耗时: {elapsed:.1f} 秒")
            return True
        else:
            update_progress("failed", "error", 0, "安装验证失败")
            print("\n" + "=" * 60)
            print("  [FAIL] 安装验证失败")
            print("=" * 60)
            print("\n建议操作:")
            print("  1. 手动运行: install_cn.bat (Windows) 或 ./install_cn.sh (Linux/Mac)")
            print("  2. 查看日志文件获取详细错误信息")
            return False
    else:
        update_progress("failed", "error", 0, "所有安装方式均失败")
        print("\n" + "=" * 60)
        print("  [FAIL] 所有安装方式均失败")
        print("=" * 60)
        print("\n建议操作:")
        print("  1. 检查网络连接")
        print("  2. 手动运行: install_cn.bat (Windows) 或 ./install_cn.sh (Linux/Mac)")
        print("  3. 查看文档: docs/INSTALL.md")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n安装被用户中断")
        sys.exit(1)
