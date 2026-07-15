"""
测试：太极引擎 · Self-Healing Loop（Phase 4）

验证：
1. Gate FAIL → 生成替代方案
2. Pi 拦截 → 生成安全替代方案
3. Token 超限 → 自动降级
4. 工具去重 → 缓存建议
5. 规则沉淀
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.self_healing import (
    SelfHealingLoop, InterceptEvent, HealingAction,
)

_mem_log = []

def memory_callback(event, result):
    _mem_log.append(f"{event.event_type}: {result.learned_rule}")


def test_gate_fail_heal():
    """Gate FAIL → 生成替代方案。"""
    sh = SelfHealingLoop(memory_callback)
    event = InterceptEvent(
        event_type="gate_fail",
        agent_id="writer-01",
        workspace_id="ws-1",
        detail="incomplete",
        context={"task_type": "writing", "model_used": "gemma-4", "tools_called": 3},
    )
    result = sh.heal(event)
    assert result.action == HealingAction.RETRY_WITH_ALT
    assert "Token 预算" in result.suggestion
    assert result.alternative is not None  # Gemma-4 → DeepSeek suggestion
    assert len(sh.rules) == 1
    print(f"✅ test_gate_fail_heal 通过: {result.alternative}")


def test_pi_intercept_heal():
    """Pi 拦截 → 生成安全替代方案。"""
    sh = SelfHealingLoop()
    event = InterceptEvent(
        event_type="pi_intercept",
        agent_id="coder-01",
        workspace_id="ws-2",
        detail="file_delete",
        context={},
    )
    result = sh.heal(event)
    assert result.action == HealingAction.RETRY_WITH_ALT
    assert "备份" in result.suggestion
    assert "回收站" in (result.alternative or "")
    print(f"✅ test_pi_intercept_heal 通过: {result.alternative}")


def test_token_exceeded_degrade():
    """Token 超限 → 自动降级。"""
    sh = SelfHealingLoop()
    event = InterceptEvent(
        event_type="token_exceeded",
        agent_id="analyst-01",
        workspace_id="ws-3",
        detail="over_budget",
        context={"percentage": 1.05, "task_type": "analysis"},
    )
    result = sh.heal(event)
    assert result.action == HealingAction.DEGRADE_AND_CONTINUE
    assert "gemma-4" in result.alternative
    print(f"✅ test_token_exceeded_degrade 通过: {result.suggestion}")


def test_tool_duplicate():
    """工具去重 → 缓存建议。"""
    sh = SelfHealingLoop()
    event = InterceptEvent(
        event_type="tool_duplicate",
        agent_id="searcher-01",
        workspace_id="ws-4",
        detail="web_search:q=竞品分析",
        context={},
    )
    result = sh.heal(event)
    assert result.action == HealingAction.RECORD_AND_LEARN
    assert "缓存" in result.suggestion
    print(f"✅ test_tool_duplicate 通过")


def test_rules_accumulate():
    """规则持续沉淀。"""
    sh = SelfHealingLoop()
    for i in range(3):
        sh.heal(InterceptEvent(
            event_type="gate_fail", agent_id=f"a{i}", workspace_id="ws",
            detail="quality_low", context={"task_type": "writing"},
        ))
    assert sh.event_count == 3
    assert len(sh.rules) >= 1
    stats = sh.get_stats()
    assert stats["total_events"] == 3
    print(f"✅ test_rules_accumulate 通过: {len(sh.rules)} 条规则")


if __name__ == "__main__":
    test_gate_fail_heal()
    test_pi_intercept_heal()
    test_token_exceeded_degrade()
    test_tool_duplicate()
    test_rules_accumulate()
    print("\n🎉 全部 5 项测试通过 — Phase 4 Self-Healing Loop 自愈回路完成")
