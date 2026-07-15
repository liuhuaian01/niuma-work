"""备份服务

Phase 1: 手动备份/还原（SQLite 文件 + 设置 + 技能定义）
Phase 2: 自动备份 + 增量备份 + 定时调度
"""

import os
import uuid
import hashlib
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from db.database import get_engine
from config.settings import settings
from utils import utc_now


def _get_backup_dir() -> Path:
    """获取备份目录"""
    backup_dir = Path(settings.DATA_DIR) / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def _compute_checksum(filepath: Path) -> str:
    """计算文件 SHA-256 校验和"""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()[:16]


async def list_backups() -> list:
    """列出所有备份"""
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT id, filename, size_bytes, type, checksum, created_at "
                "FROM backup_records ORDER BY created_at DESC"
            ),
        )
        return [dict(r._mapping) for r in result]


async def create_backup() -> dict:
    """创建手动备份"""
    backup_dir = _get_backup_dir()
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%d")
    filename = f"niuma-backup-{timestamp}.zip"
    backup_path = backup_dir / filename

    # 收集需要备份的文件
    db_path = Path(settings.DB_PATH)
    settings_path = Path(settings.DATA_DIR) / "settings.json"
    skills_dir = Path(settings.DATA_DIR) / "skills"

    # 创建 zip
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 数据库文件
        if db_path.exists():
            zf.write(db_path, "data.db")
        # 设置文件
        if settings_path.exists():
            zf.write(settings_path, "settings.json")
        # 技能目录
        if skills_dir.exists():
            for skill_file in skills_dir.rglob("*"):
                if skill_file.is_file():
                    zf.write(skill_file, f"skills/{skill_file.relative_to(skills_dir)}")

    # 计算校验和
    checksum = _compute_checksum(backup_path)
    size_bytes = backup_path.stat().st_size

    # 记录到数据库
    backup_id = f"backup-{uuid.uuid4().hex[:12]}"
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO backup_records (id, filename, size_bytes, type, checksum, created_at) "
                "VALUES (:id, :filename, :size, 'manual', :checksum, :now)"
            ),
            {
                "id": backup_id, "filename": filename,
                "size": size_bytes, "checksum": checksum, "now": utc_now(),
            },
        )

    return {
        "id": backup_id,
        "filename": filename,
        "size_bytes": size_bytes,
        "download_url": f"/api/v1/backup/{backup_id}/download",
    }


async def get_backup_download_path(backup_id: str) -> str | None:
    """获取备份文件路径"""
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT filename FROM backup_records WHERE id = :id"),
            {"id": backup_id},
        )
        row = result.fetchone()
        if not row:
            return None
        backup_path = _get_backup_dir() / row.filename
        return str(backup_path) if backup_path.exists() else None


async def restore_backup(zip_path: str) -> dict:
    """从备份还原

    注意：还原操作会关闭当前数据库连接并替换文件，
    Phase 1 仅做基本实现，Phase 2 加入安全确认和事务保护。
    """
    zip_file = Path(zip_path)
    if not zip_file.exists():
        return {"success": False, "error": "备份文件不存在"}

    data_dir = Path(settings.DATA_DIR)

    try:
        with zipfile.ZipFile(zip_file, "r") as zf:
            # 安全检查：只允许解压预期文件
            for name in zf.namelist():
                if name.startswith("/") or ".." in name:
                    return {"success": False, "error": "备份文件包含不安全路径"}

            # 解压到临时目录
            temp_dir = data_dir / "restore_temp"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            zf.extractall(temp_dir)

            # 替换数据库（需在应用关闭后执行，Phase 2 自动重启）
            temp_db = temp_dir / "data.db"
            if temp_db.exists():
                # 备份当前数据库
                current_db = Path(settings.DB_PATH)
                if current_db.exists():
                    shutil.copy2(current_db, str(current_db) + ".pre_restore")

                # Phase 2: 触发应用重启
                # 当前仅标记需要还原
                return {
                    "success": True,
                    "message": "备份文件验证通过，需要重启应用完成还原",
                    "requires_restart": True,
                }

            return {"success": False, "error": "备份文件中缺少数据库"}

    except zipfile.BadZipFile:
        return {"success": False, "error": "无效的备份文件"}
    except Exception as e:
        return {"success": False, "error": str(e)}
