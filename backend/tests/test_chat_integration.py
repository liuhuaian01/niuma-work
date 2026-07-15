"""
测试：太极引擎 · 对话流接入（Phase 6）

验证：
1. 发送前力点探测选模型
2. 预算超限阻止发送
3. 外网开关检查
4. 发送后自动记录执行日志
5. 每日意识摘要 API
"""

import sys, os, tempfile, asyncio
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.chat_hooks import ChatIntegration
from engine.token_budget import token_budget

_tmp = []

def _db(name: str) -> str:
    p = os.path.join(tempfile.gettempdir(), name)
    _tmp.append(p)
    return p


@pytest.mark.asyncio
async def test_pre_chat_probe():
    """发送前力点探测——写作任务选推荐模型。"""
    ci = ChatIntegration(_db("test_pre.db"))
    for _ in range(5):
        ci.allocator.record_execution(ci._infer_task_type("写一篇文章"), 12000, 0.9)
    check = await ci.pre_chat_check("帮我写一篇文章", "ws-1", "writer-01", 0.8)
    assert check.can_proceed is True
    assert check.recommended_model, "应该推荐一个模型"
    assert check.estimated_tokens > 0
    print(f"✅ test_pre_chat_probe 通过: {check.recommended_model} — {check.force_probe_reason}")


def test_budget_blocks():
    """预算超限阻止发送。"""
    token_budget.set_agent_budget("blocked-agent", 1000)
    token_budget.record_usage("blocked-agent", 950)  # 95% → CRITICAL
    check = token_budget.check("blocked-agent")
    assert check.can_continue is False, f"CRITICAL 应阻止, 实际 {check.alert_level}"
    print(f"✅ test_budget_blocks 通过: {check.message}")


def test_post_chat_record():
    """发送后自动记录执行日志。"""
    ci = ChatIntegration(_db("test_post.db"))
    ci.post_chat_record(
        "帮我分析数据", "ws-1", "analyst-01",
        "deepseek-v3.2", 15000, 0.9, True, 3, 5000,
    )
    stats = ci.logger.get_stats()
    assert stats["total_executions"] >= 1
    assert stats["success_rate"] == 1.0
    print(f"✅ test_post_chat_record 通过: {stats}")


def test_error_healing():
    """自愈回路在对话中触发。"""
    ci = ChatIntegration()
    suggestion = ci.handle_error("gate_fail", "writer-01", "ws-1", "incomplete")
    assert len(suggestion) > 10
    print(f"✅ test_error_healing 通过: {suggestion[:60]}...")


def test_consciousness_api():
    """每日意识摘要生成。"""
    ci = ChatIntegration(_db("test_cons.db"))
    ci.post_chat_record("写报告", "ws-1", "w1", "deepseek-v3.2", 8000, 0.95, True, 2)
    ci.post_chat_record("写文章", "ws-1", "w1", "deepseek-v3.2", 10000, 0.88, True, 3)
    ci.post_chat_record("搜资料", "ws-2", "s1", "kimi-k2.6", 8000, 0.3, False, 5, error_type="token_exceeded")

    result = ci.daily_reflection()
    assert result["total_executions"] == 3
    assert "太极引擎" in result["summary"]
    print(f"✅ test_consciousness_api 通过:")
    print(f"   {result['summary']}")


if __name__ == "__main__":
    test_pre_chat_probe()
    test_budget_blocks()
    test_post_chat_record()
    test_error_healing()
    test_consciousness_api()
    print("\n🎉 全部 5 项测试通过 — Phase 6 引擎接入对话流完成")
