"""
太极引擎 · 铭心（Memory Loader）

铭刻于心——自动加载 MEMORY.md / USER.md 并注入对话上下文。
与 Hermes 格式完全兼容，用户零迁移成本。

设计原则：
  1. Hermes 兼容：读取 ~/.workbuddy/MEMORY.md（跨项目）和 {workspace}/.workbuddy/memory/MEMORY.md（项目级）
  2. Token 预算：总注入 ≤ 1500 tokens（可配置）
  3. 懒加载 + 缓存：文件变更时自动刷新
  4. 降级安全：文件不存在时静默跳过，不影响对话

v1.0: 铭心初版——MEMORY.md 自动注入
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import logging
import os
import time

logger = logging.getLogger("niuma.memory_loader")

# Token 估算常数（中文：~1.5 char/token，英文：~4 char/token）
_ZH_CHARS_PER_TOKEN = 1.5
_EN_CHARS_PER_TOKEN = 4.0


def _estimate_tokens(text: str) -> int:
    """简单 Token 估算——中文为主，英文为辅。"""
    if not text:
        return 0
    zh_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff' or '\u3000' <= c <= '\u303f')
    en_chars = len(text) - zh_chars
    return int(zh_chars / _ZH_CHARS_PER_TOKEN + en_chars / _EN_CHARS_PER_TOKEN)


@dataclass
class MemoryFile:
    """单个记忆文件的元数据。"""
    path: Path
    content: str = ""
    token_count: int = 0
    last_mtime: float = 0.0
    source: str = ""  # "user_cross_project" / "project_local" / "daily_log"


@dataclass
class MemoryContext:
    """铭心注入的完整上下文。"""
    system_prompt_fragment: str = ""
    total_tokens: int = 0
    sources: list[str] = field(default_factory=list)
    truncated: bool = False


class MemoryLoader:
    """铭心——记忆加载器。

    从多个层级加载记忆文件并组装为 system prompt 片段。
    格式与 Hermes 完全兼容。

    加载优先级（后加载的可覆盖前面的）：
      1. USER.md（用户级跨项目身份）
      2. ~/.workbuddy/MEMORY.md（用户级跨项目偏好）
      3. {workspace}/.workbuddy/memory/MEMORY.md（项目级约定）
      4. {workspace}/.workbuddy/memory/YYYY-MM-DD.md（今日日志）

    Token 预算：1500（可配置），超出则按优先级截断。
    """

    # Token 预算上限
    DEF_MAX_TOKENS = 1500

    # 用户级记忆路径（Hermes 兼容）
    USER_MEMORY_DIR = Path.home() / ".workbuddy"
    USER_MD_PATH = USER_MEMORY_DIR / "USER.md"
    MEMORY_MD_PATH = USER_MEMORY_DIR / "MEMORY.md"

    def __init__(self, max_tokens: int = DEF_MAX_TOKENS) -> None:
        self._max_tokens = max_tokens
        self._cache: dict[str, MemoryFile] = {}
        self._last_scan: float = 0.0
        self._scan_interval: float = 5.0  # 5秒内不重复扫描

    # ════════════════════════════════════════════════════════════
    # 文件加载
    # ════════════════════════════════════════════════════════════

    def _load_file(self, path: Path, source: str) -> Optional[MemoryFile]:
        """加载单个记忆文件（带缓存和 mtime 检测）。"""
        cache_key = str(path)

        # 检查缓存
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            try:
                current_mtime = path.stat().st_mtime if path.exists() else 0
                if current_mtime == cached.last_mtime:
                    return cached if cached.content else None
            except OSError:
                pass

        # 文件不存在
        if not path.exists():
            self._cache.pop(cache_key, None)
            return None

        try:
            content = path.read_text(encoding="utf-8").strip()
            if not content:
                self._cache.pop(cache_key, None)
                return None

            mf = MemoryFile(
                path=path,
                content=content,
                token_count=_estimate_tokens(content),
                last_mtime=path.stat().st_mtime,
                source=source,
            )
            self._cache[cache_key] = mf
            return mf
        except Exception as e:
            logger.warning("铭心加载失败: %s — %s", path, e)
            return None

    def _get_today_log_path(self, workspace_root: Optional[str]) -> Optional[Path]:
        """获取今日日志路径。"""
        if not workspace_root:
            return None
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        log_dir = Path(workspace_root) / ".workbuddy" / "memory"
        log_path = log_dir / f"{today}.md"
        return log_path if log_path.exists() else None

    # ════════════════════════════════════════════════════════════
    # 上下文构建
    # ════════════════════════════════════════════════════════════

    def build_context(
        self, workspace_root: Optional[str] = None, max_tokens: Optional[int] = None
    ) -> MemoryContext:
        """构建铭心上下文——按优先级加载所有记忆文件。

        Args:
            workspace_root: 工作间根目录（项目级记忆路径）
            max_tokens: Token 预算上限（None 使用默认 1500）

        Returns:
            MemoryContext: 组装完成的 system prompt 片段
        """
        budget = max_tokens or self._max_tokens
        files: list[MemoryFile] = []
        sources: list[str] = []

        # 1. USER.md（用户身份——最高优先级，总是最先加载）
        user_md = self._load_file(self.USER_MD_PATH, "user_identity")
        if user_md:
            files.append(user_md)
            sources.append(f"USER.md ({user_md.token_count}t)")

        # 2. ~/.workbuddy/MEMORY.md（跨项目偏好）
        cross_md = self._load_file(self.MEMORY_MD_PATH, "user_cross_project")
        if cross_md:
            files.append(cross_md)
            sources.append(f"MEMORY.md (cross-project, {cross_md.token_count}t)")

        # 3. {workspace}/.workbuddy/memory/MEMORY.md（项目级约定）
        if workspace_root:
            ws_memory_path = Path(workspace_root) / ".workbuddy" / "memory" / "MEMORY.md"
            ws_md = self._load_file(ws_memory_path, "project_local")
            if ws_md:
                files.append(ws_md)
                sources.append(f"MEMORY.md (project, {ws_md.token_count}t)")

            # 4. 今日日志
            today_log = self._get_today_log_path(workspace_root)
            if today_log:
                log_md = self._load_file(today_log, "daily_log")
                if log_md:
                    files.append(log_md)
                    sources.append(f"daily-log ({log_md.token_count}t)")

        # 如果没有加载到任何文件，返回空上下文
        if not files:
            return MemoryContext()

        # Token 预算控制：按优先级累加，超出则截断
        fragments: list[str] = []
        total_tokens = 0
        truncated = False

        for mf in files:
            if total_tokens + mf.token_count <= budget:
                fragments.append(mf.content)
                total_tokens += mf.token_count
            else:
                # 截断：保留头部内容
                remaining = budget - total_tokens
                if remaining > 50:  # 至少保留50个token才有意义
                    # 按行切割，保留前面的行
                    lines = mf.content.split("\n")
                    kept_lines = []
                    kept_tokens = 0
                    for line in lines:
                        line_tokens = _estimate_tokens(line)
                        if kept_tokens + line_tokens > remaining:
                            break
                        kept_lines.append(line)
                        kept_tokens += line_tokens
                    if kept_lines:
                        fragments.append("\n".join(kept_lines) + "\n\n[铭心: 内容已截断，完整版见源文件]")
                        total_tokens += kept_tokens
                truncated = True
                break

        # 组装 system prompt 片段
        prompt_fragment = (
            "<memory_system>\n"
            + "\n---\n".join(fragments)
            + "\n</memory_system>"
        )

        return MemoryContext(
            system_prompt_fragment=prompt_fragment,
            total_tokens=total_tokens,
            sources=sources,
            truncated=truncated,
        )

    def get_stats(self) -> dict:
        """获取铭心统计信息。"""
        return {
            "max_tokens": self._max_tokens,
            "loaded_files": len(self._cache),
            "sources": {
                str(mf.path): {
                    "tokens": mf.token_count,
                    "source": mf.source,
                    "last_loaded": mf.last_mtime,
                }
                for mf in self._cache.values()
            },
        }

    def clear_cache(self) -> None:
        """清除文件缓存——强制下次重新加载。"""
        self._cache.clear()
        self._last_scan = 0.0


# 平台唯一实例
memory_loader = MemoryLoader()
