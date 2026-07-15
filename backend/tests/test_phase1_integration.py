"""
阶段一集成测试：铭心 + 缩龙成寸 + 太虚境 + 夜巡 联合验收

验证四个已吸收模块在无 Hermes 依赖下协同工作。
"""
import pytest
import asyncio
import os
import tempfile
from pathlib import Path

# ─────────────────────────────────────────────
# 1. 铭心 (Memory Loader) 测试
# ─────────────────────────────────────────────

class TestMingXin:
    """铭心：MEMORY.md + USER.md 自动注入"""

    def test_memory_loader_exists(self):
        from engine.memory_loader import memory_loader
        assert memory_loader is not None

    @pytest.mark.asyncio
    async def test_load_memory_files(self, tmp_path):
        """测试 MEMORY.md 和 USER.md 加载"""
        # 模拟 HERMES_MEMORY_DIR 环境
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        (memory_dir / "MEMORY.md").write_text("# Test Memory\n- Item 1\n- Item 2")
        (memory_dir / "USER.md").write_text("# Test User\n- Name: Test")

        from engine.memory_loader import memory_loader

        # 设置临时路径
        import os
        original = os.environ.get("HERMES_MEMORY_DIR")
        os.environ["HERMES_MEMORY_DIR"] = str(memory_dir)

        try:
            # 使用 build_context（实际 API），返回 MemoryContext 命名元组
            result = memory_loader.build_context(workspace_root=str(memory_dir))
            assert result is not None
            assert hasattr(result, 'system_prompt_fragment')
            assert len(result.system_prompt_fragment) > 0
        finally:
            if original:
                os.environ["HERMES_MEMORY_DIR"] = original

    @pytest.mark.asyncio
    async def test_memory_files_not_found(self, tmp_path):
        """测试无文件时的优雅降级"""
        memory_dir = tmp_path / "empty"
        memory_dir.mkdir()

        from engine.memory_loader import memory_loader
        import os
        original = os.environ.get("HERMES_MEMORY_DIR")
        os.environ["HERMES_MEMORY_DIR"] = str(memory_dir)

        try:
            result = memory_loader.build_context(workspace_root=str(memory_dir))
            # 应该返回 MemoryContext 对象，不抛异常
            assert result is not None
            assert hasattr(result, 'system_prompt_fragment')
        finally:
            if original:
                os.environ["HERMES_MEMORY_DIR"] = original


# ─────────────────────────────────────────────
# 2. 缩龙成寸 (Context Compression) 测试
# ─────────────────────────────────────────────

class TestSuoLong:
    """缩龙成寸：上下文自动压缩"""

    @pytest.mark.asyncio
    async def test_compression_engine_exists(self):
        """验证压缩引擎可导入"""
        from services.memory.compression_engine import (
            CompressionEngine, CompressionConfig, CompressionReport
        )
        assert CompressionEngine is not None
        assert CompressionConfig is not None

    @pytest.mark.asyncio
    async def test_compress_simple_messages(self):
        """测试压缩引擎实例化"""
        from services.memory.compression_engine import CompressionEngine
        engine = CompressionEngine()
        assert engine is not None
        assert hasattr(engine, 'check_and_compress')


# ─────────────────────────────────────────────
# 3. 太虚境 (Taixu Semantic Memory) 测试
# ─────────────────────────────────────────────

class TestTaiXu:
    """太虚境：语义记忆系统"""

    def test_taixu_core_exists(self):
        """验证太虚境核心可导入"""
        from engine.taixu_core import get_taixu, init_taixu
        assert get_taixu is not None
        assert init_taixu is not None

    def test_embedding_engine_exists(self):
        """验证嵌入引擎可导入"""
        from engine.embedding_engine import EmbeddingEngine
        assert EmbeddingEngine is not None


# ─────────────────────────────────────────────
# 4. 夜巡 (Night Patrol) 测试
# ─────────────────────────────────────────────

class TestNightPatrol:
    """夜巡：后台内容审查"""

    def test_patrol_exists(self):
        """验证夜巡可导入"""
        from engine.night_patrol import get_patrol
        patrol = get_patrol()
        assert patrol is not None

    def test_patrol_router_exists(self):
        """验证夜巡路由"""
        from routers.patrol import router
        assert router is not None


# ─────────────────────────────────────────────
# 5. 中间件安全链集成测试
# ─────────────────────────────────────────────

class TestSecurityMiddleware:
    """安全中间件链测试"""

    def test_rate_limit_middleware(self):
        """验证限流中间件可导入"""
        from middleware.rate_limit import RateLimitMiddleware
        assert RateLimitMiddleware is not None

    def test_request_size_middleware(self):
        """验证请求大小限制中间件可导入"""
        from middleware.request_size import RequestSizeMiddleware
        assert RequestSizeMiddleware is not None

    def test_workspace_isolation_middleware(self):
        """验证工作间隔离中间件可导入"""
        from middleware.workspace_isolation import WorkspaceIsolationMiddleware
        assert WorkspaceIsolationMiddleware is not None

    def test_workspace_id_validation(self):
        """验证工作间 ID 格式校验"""
        from middleware.workspace_isolation import _is_valid_ws_id
        assert _is_valid_ws_id("ws-abc123") is True
        assert _is_valid_ws_id("ws-valid_id-01") is True
        assert _is_valid_ws_id("../etc/passwd") is False
        assert _is_valid_ws_id("a" * 65) is False
        assert _is_valid_ws_id("ws<script>alert(1)</script>") is False


# ─────────────────────────────────────────────
# 6. Hermes 适配器测试
# ─────────────────────────────────────────────

class TestHermesAdapter:
    """Hermes 适配器测试"""

    @pytest.fixture
    def adapter(self):
        from engine.hermes_adapter import hermes_adapter
        return hermes_adapter

    def test_concept_translation(self, adapter):
        """测试概念翻译"""
        from engine.hermes_adapter import TaiJiConcept
        concept = adapter.translate_concept("memory_loader")
        assert concept == TaiJiConcept.MEMORY_INJECTION

    def test_absorbed_capabilities(self, adapter):
        """测试已吸收能力列表"""
        absorbed = adapter.list_absorbed_capabilities()
        assert "memory_loader" in absorbed
        assert "context_compression" in absorbed
        assert "semantic_search" in absorbed
        assert "behavior_audit" in absorbed

    def test_absorption_report(self, adapter):
        """测试吸收报告"""
        report = adapter.get_absorption_report()
        assert report["taiji_version"] == "v2.0 · 记忆觉醒"
        assert report["absorbed"] >= 4
        assert report["independence_score"] is not None
        assert "absorbed_capabilities" in report
        assert "pending_capabilities" in report

    def test_compatibility_check(self, adapter):
        """测试兼容性检查"""
        report = adapter.check_hermes_compatibility("0.17.0")
        assert report.compatible is True
        assert report.taiji_version == "2.0"


# ─────────────────────────────────────────────
# 7. 端到端集成流程
# ─────────────────────────────────────────────

class TestE2EIntegration:
    """端到端集成流程测试"""

    @pytest.mark.asyncio
    async def test_full_memory_pipeline_imports(self):
        """验证完整记忆管道所有模块可导入"""
        modules = [
            "engine.memory_loader",
            "services.memory.compression_engine",
            "engine.taixu_core",
            "engine.embedding_engine",
            "engine.night_patrol",
            "engine.hermes_adapter",
            "middleware.rate_limit",
            "middleware.request_size",
            "middleware.workspace_isolation",
        ]
        for mod_name in modules:
            try:
                __import__(mod_name)
                assert True, f"Module {mod_name} imported successfully"
            except ImportError as e:
                pytest.fail(f"Failed to import {mod_name}: {e}")

    @pytest.mark.asyncio
    async def test_engine_modules_independent_of_hermes(self):
        """验证四个已吸收模块不依赖 Hermes 运行时"""
        import subprocess
        import sys

        # 检查关键模块是否包含 Hermes 硬依赖的 import
        hermes_imports = [
            "from hermes",
            "import hermes",
            "hermes_agent",
            "hermes.core",
        ]

        engine_files = [
            "engine/memory_loader.py",
            "engine/taixu_core.py",
            "engine/embedding_engine.py",
            "engine/night_patrol.py",
            "engine/hermes_adapter.py",
        ]

        backend_dir = Path(__file__).parent.parent

        for f in engine_files:
            filepath = backend_dir / f
            if not filepath.exists():
                continue

            content = filepath.read_text()
            for hi in hermes_imports:
                # hermes_adapter 本身是适配层，允许包含 "hermes" 引用
                if f == "engine/hermes_adapter.py":
                    continue
                if hi in content:
                    pytest.fail(
                        f"{f} 包含 Hermes 硬依赖 '{hi}'。"
                        "已吸收模块应独立于 Hermes 运行时。"
                    )
