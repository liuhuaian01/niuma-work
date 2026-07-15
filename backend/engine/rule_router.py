"""
太极引擎 · 内容路由层

6 种内容类型识别 + 4 级复杂度评估，纯规则引擎零额外开销。

集成点：_build_context 阶段，在 SemanticGrader 之前运行。
根据内容类型路由到不同的处理策略（JSON→结构化解析, Code→保留完整, Log→错误优先等）。

内容类型：
  - CODE: 代码/脚本（完整保留，不压缩）
  - JSON: 结构化数据（解析后按字段压缩）
  - LOG: 日志输出（错误优先提取）
  - QUERY: 查询/问题（语义路由）
  - DOCUMENT: 长文档（分段处理）
  - CHAT: 对话消息（常规处理）

复杂度等级：
  - TRIVIAL: < 100 字符，无需压缩
  - SIMPLE: 100-500 字符，轻度处理
  - MODERATE: 500-2000 字符，标准处理
  - COMPLEX: > 2000 字符，需分段/摘要
"""
from __future__ import annotations

import re
import json as _json
import logging
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Optional

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """内容类型"""
    CHAT = "chat"           # 对话消息
    CODE = "code"           # 代码/脚本
    JSON = "json"           # 结构化 JSON 数据
    LOG = "log"             # 日志输出
    QUERY = "query"         # 查询/问题
    DOCUMENT = "document"   # 长文档


class Complexity(IntEnum):
    """复杂度等级"""
    TRIVIAL = 1     # < 100 字符
    SIMPLE = 2      # 100-500 字符
    MODERATE = 3    # 500-2000 字符
    COMPLEX = 4     # > 2000 字符


@dataclass
class RouteResult:
    """路由结果"""
    content_type: ContentType
    complexity: Complexity
    char_count: int
    # 压缩策略建议
    should_compress: bool       # 是否应压缩
    compression_strategy: str   # 推荐压缩策略
    priority: int               # 处理优先级 1-10（越高越优先保留）
    # 元数据
    code_language: Optional[str] = None
    json_keys_count: int = 0
    is_error_log: bool = False


# 内容类型 → 压缩策略
STRATEGY_MAP = {
    ContentType.CODE: "preserve",          # 代码完整保留
    ContentType.LOG: "error_first",        # 日志：错误优先提取
    ContentType.JSON: "field_compress",    # JSON：按字段压缩
    ContentType.QUERY: "semantic_route",   # 查询：语义路由
    ContentType.DOCUMENT: "chunk",         # 文档：分段处理
    ContentType.CHAT: "standard",          # 对话：常规压缩
}

# 复杂度 → 默认优先级
COMPLEXITY_PRIORITY = {
    Complexity.TRIVIAL: 3,
    Complexity.SIMPLE: 5,
    Complexity.MODERATE: 7,
    Complexity.COMPLEX: 9,
}


class RuleRouter:
    """内容路由引擎。

    纯规则引擎，无 LLM 调用，单次路由 < 2ms。
    基于正则匹配 + 启发式特征提取。
    """

    # 代码块检测
    _CODE_BLOCK_RE = re.compile(r'```[\s\S]*?```', re.MULTILINE)
    _INLINE_CODE_RE = re.compile(r'`[^`]+`')

    # 编程语言关键词
    _CODE_KEYWORDS = {
        'def ', 'class ', 'import ', 'from ', 'return ',
        'function', 'const ', 'let ', 'var ', 'export ',
        'async ', 'await ', 'yield ', 'raise ', 'self.',
        'npm ', 'pip ', 'docker ', 'git ', 'curl ',
        'if __name__', '#!/', '<?php', 'using namespace',
    }

    # JSON 检测
    _JSON_START_RE = re.compile(r'^\s*[\[\{]\s*$', re.MULTILINE)
    _JSON_KEY_PATTERN = re.compile(r'"\w+":\s*')

    # 日志模式
    _LOG_TIMESTAMP_RE = re.compile(
        r'\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}:\d{2}'
    )
    _LOG_LEVELS_RE = re.compile(
        r'\b(ERROR|WARN|WARNING|INFO|DEBUG|TRACE|FATAL|CRITICAL|PANIC)\b'
    )
    _LOG_PREFIXES_RE = re.compile(
        r'^\[[\w\.-]+\]|^\d+\s+\d+|^[A-Z]\w+\s+\d{4}'
    )

    # 查询/问题模式
    _QUERY_SIGNALS = {'?', '？', '怎么', '如何', '什么', '为什么', '能不能', '有没有'}
    _QUERY_RE = re.compile(
        r'[?？]|怎么|如何|什么|为什么|能不能|有没有|请问|帮忙|帮我|查一下|搜一下'
    )

    # 文档信号（长结构化文本）
    _DOC_STRUCTURE_RE = re.compile(
        r'^#{1,6}\s|^\*\*.*\*\*\s*$|^\d+[\.\)]\s|^[-*]\s', re.MULTILINE
    )
    _DOC_PATTERNS = [
        r'摘要|概述|引言|目录|第一章|第 1 章|Section \d|附录|参考文献',
        r'报告|文档|说明|规范|指南|手册|白皮书',
    ]

    def __init__(self) -> None:
        self._stats = {"routed": 0, "by_type": {t.value: 0 for t in ContentType}}

    # ---- 主入口 ----

    def route(self, content: str) -> RouteResult:
        """对内容进行类型识别 + 复杂度评估。

        Args:
            content: 待路由文本内容

        Returns:
            RouteResult 包含类型、复杂度、压缩策略
        """
        if not content or not content.strip():
            return RouteResult(
                content_type=ContentType.CHAT,
                complexity=Complexity.TRIVIAL,
                char_count=0,
                should_compress=False,
                compression_strategy="none",
                priority=1,
            )

        char_count = len(content)

        # 1. 复杂度评估
        complexity = self._assess_complexity(char_count, content)

        # 2. 类型识别（优先级：代码 > 日志 > JSON > 查询 > 文档 > 对话）
        content_type = self._detect_type(content, char_count)

        # 3. 构建结果
        strategy = STRATEGY_MAP[content_type]
        priority = self._compute_priority(content_type, complexity)

        result = RouteResult(
            content_type=content_type,
            complexity=complexity,
            char_count=char_count,
            should_compress=content_type not in (ContentType.CODE,),
            compression_strategy=strategy,
            priority=priority,
        )

        # 类型专属元数据
        if content_type == ContentType.CODE:
            result.code_language = self._detect_code_language(content)
        elif content_type == ContentType.JSON:
            result.json_keys_count = self._count_json_keys(content)
        elif content_type == ContentType.LOG:
            result.is_error_log = self._is_error_log(content)

        self._record(result)
        return result

    def route_batch(self, items: list[str]) -> list[RouteResult]:
        """批量路由。"""
        return [self.route(item) for item in items]

    # ---- 类型检测 ----

    def _detect_type(self, content: str, char_count: int) -> ContentType:
        """按优先级检测内容类型。"""

        # 1. 代码检测（最高优先级——代码需完整保留不压缩）
        if self._is_code(content):
            return ContentType.CODE

        # 2. 日志检测
        if self._is_log(content):
            return ContentType.LOG

        # 3. JSON 检测
        if self._is_json(content):
            return ContentType.JSON

        # 4. 查询检测
        if self._is_query(content, char_count):
            return ContentType.QUERY

        # 5. 文档检测
        if self._is_document(content, char_count):
            return ContentType.DOCUMENT

        # 6. 默认对话
        return ContentType.CHAT

    def _is_code(self, content: str) -> bool:
        """检测是否为代码内容。"""
        # 代码块标记
        if self._CODE_BLOCK_RE.search(content):
            return True

        # 高密度内联代码
        inline_codes = self._INLINE_CODE_RE.findall(content)
        if len(inline_codes) >= 3:
            return True

        # 代码关键词密度
        code_keyword_count = sum(1 for kw in self._CODE_KEYWORDS if kw in content)
        if code_keyword_count >= 2:
            return True

        # 缩进模式（连续 4+ 空格或 tab 行）
        lines = content.split('\n')
        indent_lines = sum(1 for l in lines if l.startswith('    ') or l.startswith('\t'))
        if len(lines) > 3 and indent_lines / max(len(lines), 1) > 0.5:
            return True

        return False

    def _is_log(self, content: str) -> bool:
        """检测是否为日志输出。"""
        # 日志时间戳
        if self._LOG_TIMESTAMP_RE.search(content):
            return True

        # 日志级别
        if self._LOG_LEVELS_RE.search(content):
            return True

        # 多行日志前缀
        lines = content.split('\n')
        log_prefix_lines = sum(1 for l in lines if self._LOG_PREFIXES_RE.match(l.strip()))
        if len(lines) > 2 and log_prefix_lines / max(len(lines), 1) > 0.3:
            return True

        return False

    def _is_json(self, content: str) -> bool:
        """检测是否为 JSON 数据。"""
        stripped = content.strip()

        # JSON 起止符
        if not (stripped.startswith(('{', '[')) and stripped.endswith(('}', ']'))):
            return False

        # JSON key 模式
        json_keys = self._JSON_KEY_PATTERN.findall(content)
        if len(json_keys) >= 2:
            return True

        # 尝试解析
        try:
            _json.loads(stripped)
            return True
        except (_json.JSONDecodeError, ValueError):
            pass

        return False

    def _is_query(self, content: str, char_count: int) -> bool:
        """检测是否为查询/问题。"""
        # 短文本 + 问号/疑问词
        if char_count < 300 and self._QUERY_RE.search(content):
            return True

        # 任务请求模式
        task_patterns = ['帮我', '请帮我', '麻烦', '能不能帮我']
        if any(content.strip().startswith(p) for p in task_patterns):
            return True

        return False

    def _is_document(self, content: str, char_count: int) -> bool:
        """检测是否为长文档。"""
        # > 2000 字符 + 文档结构
        if char_count > 2000:
            if self._DOC_STRUCTURE_RE.search(content):
                return True

            for pattern in self._DOC_PATTERNS:
                if re.search(pattern, content):
                    return True

            # 高段落密度（大量换行）
            paragraphs = [l for l in content.split('\n') if len(l.strip()) > 50]
            if len(paragraphs) >= 5:
                return True

        return False

    # ---- 复杂度评估 ----

    def _assess_complexity(self, char_count: int, content: str) -> Complexity:
        """评估内容复杂度。"""
        if char_count < 100:
            return Complexity.TRIVIAL
        elif char_count < 500:
            return Complexity.SIMPLE
        elif char_count < 2000:
            return Complexity.MODERATE

        # >2000 字符：检查是否有结构化子内容
        has_structure = bool(
            self._CODE_BLOCK_RE.search(content)
            or self._DOC_STRUCTURE_RE.search(content)
        )
        if has_structure and char_count > 5000:
            return Complexity.COMPLEX

        return Complexity.COMPLEX if char_count > 2000 else Complexity.MODERATE

    # ---- 元数据提取 ----

    def _detect_code_language(self, content: str) -> Optional[str]:
        """检测代码语言（从 markdown 代码块标记）。"""
        match = re.search(r'```(\w+)', content)
        return match.group(1) if match else None

    def _count_json_keys(self, content: str) -> int:
        """统计 JSON 顶层 key 数量。"""
        try:
            data = _json.loads(content.strip())
            if isinstance(data, dict):
                return len(data)
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                return len(data[0])
        except (_json.JSONDecodeError, ValueError):
            pass
        return len(self._JSON_KEY_PATTERN.findall(content))

    def _is_error_log(self, content: str) -> bool:
        """检测是否为错误日志。"""
        return bool(re.search(r'\b(ERROR|FATAL|CRITICAL|PANIC|Exception|Traceback)\b', content))

    # ---- 优先级计算 ----

    def _compute_priority(self, content_type: ContentType, complexity: Complexity) -> int:
        """综合计算处理优先级（1-10）。"""
        base = COMPLEXITY_PRIORITY[complexity]

        # 代码和 JSON 结构数据优先级略降（可延迟处理）
        if content_type == ContentType.CODE:
            base -= 1
        elif content_type == ContentType.LOG:
            base += 1  # 日志优先查看

        return max(1, min(10, base))

    def _record(self, result: RouteResult) -> None:
        """内部统计。"""
        self._stats["routed"] += 1
        self._stats["by_type"][result.content_type.value] += 1

    @property
    def stats(self) -> dict:
        """路由统计信息。"""
        return dict(self._stats)


# 全局单例
rule_router = RuleRouter()
