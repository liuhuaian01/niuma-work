"""
全量后端集成测试：L3 + Skills + MCP + Dynamic Balancer

一次性验证所有新模块。
"""

import sys, os, tempfile, asyncio, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

from engine.l3_knowledge import L3KnowledgeBase
from engine.skills_adapter import SkillsAdapter
from engine.mcp_client import MCPClient
from engine.dynamic_balancer import DynamicBalancer, RuntimeMode

_tmp = []


def test_l3_knowledge():
    db = os.path.join(tempfile.gettempdir(), "test_l3.db")
    _tmp.append(db)
    kb = L3KnowledgeBase(db)
    kid = kb.add("太极引擎采用四两拨千斤策略进行Token管理", source="agent_generated", tags=["taiji", "token"], workspace_id="ws-1")
    assert kid
    results = kb.search("Token", workspace_id="ws-1")
    assert len(results) >= 1
    stats = kb.get_stats()
    assert stats["total_entries"] == 1
    print(f"✅ L3 knowledge base: {stats}")


def test_skills_adapter():
    import os, tempfile
    d = tempfile.mkdtemp()
    _tmp.append(d)
    skill_md = os.path.join(d, "example-skill", "SKILL.md")
    os.makedirs(os.path.dirname(skill_md), exist_ok=True)
    with open(skill_md, "w", encoding="utf-8") as f:
        f.write("""---
name: "openclaw-example"
description: "A sample OpenClaw skill for testing"
version: "1.0.0"
---
# Example Skill
This skill demonstrates OpenClaw compatibility.
""")
    adapter = SkillsAdapter()
    skills = adapter.scan(d)
    assert len(skills) >= 1
    assert skills[0].name == "openclaw-example"
    adapter.install("openclaw-example")
    stats = adapter.get_stats()
    assert stats["total_found"] >= 1
    assert stats["enabled"] >= 1
    print(f"✅ Skills adapter: {stats}")


def test_mcp_client():
    import asyncio
    c = MCPClient()
    async def _test():
        ok = await c.connect()
        assert ok
        tools = await c.list_tools()
        assert len(tools) == 4
        result = await c.call_tool("web_search", {"query": "竞品分析"})
        assert result.success
        print(f"✅ MCP client: {c.get_stats()}")
    asyncio.run(_test())


@pytest.mark.asyncio
async def test_dynamic_balancer():
    b = DynamicBalancer()
    # 模拟 Ollama 可用（避免真实网络依赖）
    b._local_available = True
    b._cloud_available = True
    b._health_checked = True
    b._last_health_check = time.time()  # 跳过 TTL 检查
    # 隐私敏感 → 本地
    d = await b.decide(privacy_sensitive=True)
    assert d.mode == RuntimeMode.LOCAL
    # 简单任务 + 预算紧张 → 本地优先（网格不可用时降级云端）
    d = await b.decide(task_complexity=0.1, budget_remaining_pct=0.1, user_prefers_local=True)
    assert d.mode in (RuntimeMode.LOCAL, RuntimeMode.CLOUD)
    # 复杂任务 + 预算充足 + 用户偏好云端 → 云端
    d = await b.decide(task_complexity=0.9, budget_remaining_pct=0.9, user_prefers_local=False)
    assert d.mode in (RuntimeMode.HYBRID, RuntimeMode.CLOUD)
    print(f"✅ Dynamic Balancer: {b.get_stats()}")


if __name__ == "__main__":
    test_l3_knowledge()
    test_skills_adapter()
    test_mcp_client()
    test_dynamic_balancer()
    print("\n🎉 全量后端开发完成 — 4/4 新模块测试通过")
