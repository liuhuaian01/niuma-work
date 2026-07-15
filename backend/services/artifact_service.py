"""
产出物自动识别服务

对话消息发出后，自动检测代码块/表格/图片/文件链接等产出物，
填充 chat_messages.artifacts 字段。

太极引擎 Pi 原则：不做过度识别——只识别有实际价值的产出物类型。
"""

import re
from typing import Optional


# 产出物类型
ARTIFACT_TYPE_CODE = "code"
ARTIFACT_TYPE_TABLE = "table"
ARTIFACT_TYPE_IMAGE = "image"
ARTIFACT_TYPE_FILE = "file"
ARTIFACT_TYPE_LIST = "list"
ARTIFACT_TYPE_DIAGRAM = "diagram"  # mermaid / graphviz 等


def detect_artifacts(content: str) -> Optional[list[dict]]:
    """
    从 AI 回复文本中识别产出物。

    返回: list of {type, title, language?, lines?, url?} 或 None (无产出物)
    """
    if not content:
        return None

    artifacts = []

    # 1. 代码块检测 (```xxx```)
    code_blocks = _detect_code_blocks(content)
    artifacts.extend(code_blocks)

    # 2. Markdown 表格检测
    tables = _detect_tables(content)
    artifacts.extend(tables)

    # 3. Mermaid 图表检测
    diagrams = _detect_diagrams(content)
    artifacts.extend(diagrams)

    # 4. 图片/文件链接检测
    links = _detect_links(content)
    artifacts.extend(links)

    # 5. 有序/无序列表检测
    lists = _detect_lists(content)
    artifacts.extend(lists)

    return artifacts if artifacts else None


def _detect_code_blocks(content: str) -> list[dict]:
    """检测代码块"""
    artifacts = []
    pattern = r"```(\w*)\n(.*?)```"
    for match in re.finditer(pattern, content, re.DOTALL):
        language = match.group(1) or "text"
        code = match.group(2).strip()
        lines = code.count("\n") + 1
        title = _code_title(code, language)
        artifacts.append({
            "type": ARTIFACT_TYPE_CODE,
            "language": language,
            "lines": lines,
            "title": title,
        })
    return artifacts


def _detect_tables(content: str) -> list[dict]:
    """检测 Markdown 表格"""
    artifacts = []
    # 表格最少 2 行: 表头 + 分隔行
    table_pattern = r"^\|(.+)\|\s*$\n^\|[-| :]+\|\s*$\n(\|.+\|\s*$\n?)*"
    for match in re.finditer(table_pattern, content, re.MULTILINE):
        table_text = match.group(0).strip()
        rows = table_text.count("\n") + 1
        # 提取表头作为标题
        header_line = match.group(1).strip()
        columns = [c.strip() for c in header_line.split("|") if c.strip()]
        artifacts.append({
            "type": ARTIFACT_TYPE_TABLE,
            "rows": rows,
            "columns": len(columns),
            "title": f"表格 ({', '.join(columns[:3])}{'...' if len(columns) > 3 else ''})",
        })
    return artifacts


def _detect_diagrams(content: str) -> list[dict]:
    """检测 Mermaid/graphviz 图表"""
    artifacts = []
    # Mermaid
    mermaid_pattern = r"```mermaid\n(.*?)```"
    for match in re.finditer(mermaid_pattern, content, re.DOTALL):
        diagram = match.group(1).strip()
        first_line = diagram.split("\n")[0].strip() if diagram else ""
        artifacts.append({
            "type": ARTIFACT_TYPE_DIAGRAM,
            "format": "mermaid",
            "title": f"Mermaid: {first_line}",
        })
    return artifacts


def _detect_links(content: str) -> list[dict]:
    """检测图片/文件链接"""
    artifacts = []
    # 图片 ![](url)
    img_pattern = r"!\[([^\]]*)\]\(([^)]+)\)"
    for match in re.finditer(img_pattern, content):
        alt_text = match.group(1) or "图片"
        url = match.group(2)
        artifacts.append({
            "type": ARTIFACT_TYPE_IMAGE,
            "title": alt_text,
            "url": url,
        })

    # 文件链接 [name](url) 但排除普通链接（只认有文件扩展名的）
    file_pattern = r"\[([^\]]+)\]\(([^)]+\.(pdf|docx|xlsx|pptx|zip|tar|gz|py|js|ts|json|yaml|yml|md|txt|html|css|png|jpg|jpeg|gif|svg))\)"
    for match in re.finditer(file_pattern, content, re.IGNORECASE):
        name = match.group(1)
        url = match.group(2)
        ext = match.group(3).lower()
        artifacts.append({
            "type": ARTIFACT_TYPE_FILE,
            "title": name,
            "extension": ext,
            "url": url,
        })
    return artifacts


def _detect_lists(content: str) -> list[dict]:
    """检测结构化列表（6 项以上算产出物）"""
    result = []
    # 有序列表: 1. 2. 3.
    ordered_items = re.findall(r"^\d+[.、]\s+.+", content, re.MULTILINE)
    # 无序列表: - * +
    unordered_items = re.findall(r"^[-*+]\s+.+", content, re.MULTILINE)

    items = ordered_items or unordered_items
    if len(items) >= 6:
        first_item = re.sub(r"^[\d\-. *+]+\s*", "", items[0]).strip()
        result.append({
            "type": ARTIFACT_TYPE_LIST,
            "item_count": len(items),
            "title": first_item[:30] + ("..." if len(first_item) > 30 else ""),
        })
    return result


def _code_title(code: str, language: str) -> str:
    """代码块标题提取——取第一行注释或语言名"""
    comment_patterns = {
        "python": r"^#\s*(.+)",
        "javascript": r"^//\s*(.+)",
        "typescript": r"^//\s*(.+)",
        "java": r"^//\s*(.+)",
        "rust": r"^//\s*(.+)",
        "go": r"^//\s*(.+)",
        "html": r"^<!--\s*(.+)\s*-->",
        "yaml": r"^#\s*(.+)",
        "toml": r"^#\s*(.+)",
    }
    first_line = code.split("\n")[0].strip() if code else ""
    if language in comment_patterns:
        match = re.match(comment_patterns[language], first_line)
        if match:
            return match.group(1).strip()
    # 没有注释 → 用语言名
    return f"{language} 代码" if language else "代码"
