"""
测试：Token 预算 + 外网管控（Phase 3）

验证：
1. 预算正常追踪
2. 50/70/90/100% 告警正确
3. 用户可手动设预算
4. 外网访问请求/关闭
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.token_budget import TokenBudgetManager, AlertLevel, BudgetStatus
from engine.taiji import taiji


def test_budget_tracking():
    """预算正常追踪。"""
    tb = TokenBudgetManager()
    tb.set_agent_budget("writer-01", 30000)
    status = tb.check("writer-01")
    assert status.used_today == 0
    assert status.remaining == 30000
    assert status.alert_level == AlertLevel.NONE
    print("✅ test_budget_tracking 通过")


def test_alert_levels():
    """50/70/90/100% 告警正确。"""
    tb = TokenBudgetManager()
    tb.set_agent_budget("test-agent", 30000)

    # 0% — NONE
    assert tb.check("test-agent").alert_level == AlertLevel.NONE

    # 55% — WARNING
    tb.record_usage("test-agent", 16500)
    assert tb.check("test-agent").alert_level == AlertLevel.WARNING

    # 75% — CAUTION
    tb.record_usage("test-agent", 6000)
    assert tb.check("test-agent").alert_level == AlertLevel.CAUTION

    # 95% — CRITICAL, can_continue=False
    tb.record_usage("test-agent", 6000)
    s = tb.check("test-agent")
    assert s.alert_level == AlertLevel.CRITICAL
    assert s.can_continue is False

    # 105% — EXCEEDED
    tb.record_usage("test-agent", 3000)
    assert tb.check("test-agent").alert_level == AlertLevel.EXCEEDED

    print("✅ test_alert_levels 通过")


def test_user_override():
    """用户可手动设置预算。"""
    tb = TokenBudgetManager()
    tb.set_agent_budget("writer-02", 30000)
    assert tb.get_effective_budget("writer-02") == 30000

    # 用户提高到 50000
    tb.set_user_budget("writer-02", 50000)
    assert tb.get_effective_budget("writer-02") == 50000

    # 用户恢复默认
    tb.set_user_budget("writer-02", None)
    assert tb.get_effective_budget("writer-02") == 30000

    print("✅ test_user_override 通过")


def test_flags_toggle():
    """验证能力开关 toggle 和 reset。"""
    taiji.init()

    # 默认关
    assert taiji.flags.is_allowed("fetch") is False

    # 用户开
    taiji.flags.fetch = True
    assert taiji.flags.is_allowed("fetch") is True

    # Agent 覆盖
    taiji.flags.set_agent_override("agent-1", "fetch", True)
    assert taiji.flags.is_allowed("fetch", "agent-1") is True
    assert taiji.flags.is_allowed("fetch", "agent-2") is True  # 平台级已开

    # Agent 覆盖后清除
    taiji.flags.clear_agent_overrides("agent-1")
    assert taiji.flags.is_allowed("fetch", "agent-1") is True  # 回退到平台级

    # 重置
    taiji.flags.fetch = False
    taiji.flags.search = False
    print("✅ test_flags_toggle 通过")


if __name__ == "__main__":
    test_budget_tracking()
    test_alert_levels()
    test_user_override()
    test_flags_toggle()
    print("\n🎉 全部 4 项测试通过 — Phase 3 Token预算 + 外网管控完成")
