"""
OpenClaw Skills 兼容适配层

顺势而为——借力 OpenClaw SKILL.md 生态。
读取 SKILL.md 格式的技能文件，转换为太极引擎可用的技能元数据。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json
import os
import re


@dataclass
class SkillMetadata:
    name: str
    description: str
    version: str = "1.0.0"
    category: str = "general"
    token_level: str = "low"   # low / medium / high
    tags: list[str] = field(default_factory=list)
    source: str = "community"  # community / builtin / custom
    file_path: str = ""
    enabled: bool = True


class SkillsAdapter:
    """OpenClaw SKILL.md 兼容适配器。"""

    def __init__(self, skills_dir: str | None = None) -> None:
        self._dir = Path(skills_dir) if skills_dir else None
        self._cache: dict[str, SkillMetadata] = {}

    def scan(self, directory: str | None = None) -> list[SkillMetadata]:
        """扫描目录，发现所有 SKILL.md 文件。"""
        target = Path(directory) if directory else self._dir
        if not target or not target.exists():
            return []

        skills: list[SkillMetadata] = []
        for skill_md in target.rglob("SKILL.md"):
            meta = self._parse_skill_md(skill_md)
            if meta:
                meta.file_path = str(skill_md)
                self._cache[meta.name] = meta
                skills.append(meta)
        return skills

    def _parse_skill_md(self, path: Path) -> Optional[SkillMetadata]:
        """解析 SKILL.md 文件。提取 frontmatter 和描述。"""
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return None

        name = ""
        description = ""
        version = "1.0.0"
        category = "general"

        # 尝试解析 YAML frontmatter
        def _extract_fm_value(line_text: str, key: str) -> str | None:
            """从 frontmatter 行中提取键值，正确处理引号和冒号。"""
            prefix = f"{key}:"
            if not line_text.startswith(prefix):
                return None
            raw = line_text[len(prefix):].strip()
            # 去除匹配的成对引号
            if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ('"', "'"):
                raw = raw[1:-1]
            return raw

        fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if fm_match:
            fm = fm_match.group(1)
            for line in fm.split("\n"):
                line = line.strip()
                val = _extract_fm_value(line, "name")
                if val is not None:
                    name = val
                    continue
                val = _extract_fm_value(line, "description")
                if val is not None:
                    description = val
                    continue
                val = _extract_fm_value(line, "version")
                if val is not None:
                    version = val
                    continue
                val = _extract_fm_value(line, "category")
                if val is not None:
                    category = val

        # 回退：从标题提取
        if not name:
            title_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
            if title_match:
                name = title_match.group(1).strip()

        if not description:
            # 从第一段提取描述
            para_match = re.search(r'(?:^|\n)\s*([A-Z\u4e00-\u9fff][^\n]{20,200})', content)
            if para_match:
                description = para_match.group(1).strip()

        if not name:
            name = path.parent.name

        # 判断 token 消耗级别
        token_level = "low"
        if any(w in content.lower() for w in ["llm", "gpt", "claude", "ai agent", "code generation"]):
            token_level = "high"
        elif any(w in content.lower() for w in ["search", "analysis", "research"]):
            token_level = "medium"

        return SkillMetadata(
            name=name, description=description or name,
            version=version, category=category, token_level=token_level,
            source="community",
        )

    def install(self, name: str) -> SkillMetadata | None:
        """标记技能为可用。"""
        if name in self._cache:
            self._cache[name].enabled = True
            return self._cache[name]
        return None

    def uninstall(self, name: str) -> None:
        if name in self._cache:
            self._cache[name].enabled = False

    def list_available(self) -> list[SkillMetadata]:
        return [m for m in self._cache.values() if m.enabled]

    def get_stats(self) -> dict:
        total = len(self._cache)
        enabled = sum(1 for m in self._cache.values() if m.enabled)
        return {"total_found": total, "enabled": enabled, "source": "OpenClaw SKILL.md compatible"}
