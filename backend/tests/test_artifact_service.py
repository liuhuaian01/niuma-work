"""产出物自动识别服务测试"""
import pytest

from services.artifact_service import detect_artifacts


class TestDetectCodeBlocks:
    def test_python_code_block(self):
        content = "这是代码：\n```python\ndef hello():\n    print('hello')\n```\n结束。"
        result = detect_artifacts(content)
        assert result is not None
        artifacts = [a for a in result if a["type"] == "code"]
        assert len(artifacts) == 1
        assert artifacts[0]["language"] == "python"
        assert artifacts[0]["lines"] >= 3

    def test_multiple_code_blocks(self):
        content = "```python\na=1\n```\n```js\nvar x=2\n```"
        result = detect_artifacts(content)
        assert result is not None
        code_blocks = [a for a in result if a["type"] == "code"]
        assert len(code_blocks) == 2

    def test_no_code_block(self):
        content = "纯文本对话，没有代码块。"
        result = detect_artifacts(content)
        assert result is None

    def test_code_block_no_language(self):
        content = "```\necho hello\n```"
        result = detect_artifacts(content)
        assert result is not None
        code = [a for a in result if a["type"] == "code"][0]
        assert code["language"] == "text"


class TestDetectTables:
    def test_markdown_table(self):
        content = "| 名称 | 数量 |\n|------|------|\n| A | 1 |\n| B | 2 |"
        result = detect_artifacts(content)
        assert result is not None
        tables = [a for a in result if a["type"] == "table"]
        assert len(tables) == 1
        assert tables[0]["columns"] == 2
        assert tables[0]["rows"] >= 3

    def test_no_table(self):
        content = "这里没有表格"
        assert detect_artifacts(content) is None


class TestDetectDiagrams:
    def test_mermaid_diagram(self):
        content = "流程图：\n```mermaid\ngraph TD\nA-->B\n```"
        result = detect_artifacts(content)
        assert result is not None
        diagrams = [a for a in result if a["type"] == "diagram"]
        assert len(diagrams) == 1
        assert diagrams[0]["format"] == "mermaid"


class TestDetectLinks:
    def test_image_link(self):
        content = "看这张图：![截图](/img/snap.png)"
        result = detect_artifacts(content)
        assert result is not None
        images = [a for a in result if a["type"] == "image"]
        assert len(images) >= 1
        assert images[0]["title"] == "截图"

    def test_file_link(self):
        content = "下载：[报告.pdf](/files/report.pdf)"
        result = detect_artifacts(content)
        assert result is not None
        files = [a for a in result if a["type"] == "file"]
        assert len(files) >= 1
        assert files[0]["extension"] == "pdf"


class TestDetectLists:
    def test_ordered_list_6_items(self):
        content = "步骤：\n1. 第一步\n2. 第二步\n3. 第三步\n4. 第四步\n5. 第五步\n6. 第六步"
        result = detect_artifacts(content)
        assert result is not None
        lists = [a for a in result if a["type"] == "list"]
        assert len(lists) >= 1
        assert lists[0]["item_count"] >= 6

    def test_short_list_not_detected(self):
        content = "要点：\n1. 一\n2. 二\n3. 三"
        result = detect_artifacts(content)
        if result:
            lists = [a for a in result if a["type"] == "list"]
            assert len(lists) == 0

    def test_unordered_list_6_items(self):
        content = "- A\n- B\n- C\n- D\n- E\n- F"
        result = detect_artifacts(content)
        assert result is not None
        lists = [a for a in result if a["type"] == "list"]
        assert len(lists) >= 1
        assert lists[0]["item_count"] >= 6


class TestEdgeCases:
    def test_empty_content(self):
        assert detect_artifacts("") is None

    def test_none_content(self):
        assert detect_artifacts(None) is None

    def test_mixed_artifacts(self):
        content = "代码：\n```python\nx=1\n```\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
        result = detect_artifacts(content)
        assert result is not None
        types = {a["type"] for a in result}
        assert "code" in types
        assert "table" in types
