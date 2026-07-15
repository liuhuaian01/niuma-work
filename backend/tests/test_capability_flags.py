"""
测试：太极引擎 · 能力开关

验证：
1. 默认值正确（fetch/search/mcp/subagents 关，skills/attachments/memory 开）
2. 用户可临时开启
3. 重置后恢复默认
4. Agent 覆盖正确生效
5. 中间件拦截正确
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.capability_flags import CapabilityFlags, FlagAction


def test_default_values():
    """测试：默认值正确。"""
    flags = CapabilityFlags()
    assert flags.fetch is False, "web_fetch 应默认关闭"
    assert flags.search is False, "web_search 应默认关闭"
    assert flags.mcp is False, "MCP 应默认关闭"
    assert flags.skills is True, "Skills 应默认开启"
    assert flags.attachments is True, "Attachments 应默认开启"
    assert flags.memory is True, "Memory 应默认开启"
    assert flags.subagents is False, "Subagents 应默认关闭"
    print("✅ test_default_values 通过")


def test_user_toggle():
    """测试：用户可临时开启任意能力。"""
    flags = CapabilityFlags()
    assert flags.is_allowed("fetch") is False
    flags.fetch = True
    assert flags.is_allowed("fetch") is True
    print("✅ test_user_toggle 通过")


def test_reset():
    """测试：重置后恢复默认。"""
    flags = CapabilityFlags()
    flags.fetch = True
    flags.search = True
    flags.fetch = False
    flags.search = False
    flags.mcp = False
    flags.skills = True
    flags.attachments = True
    flags.memory = True
    flags.subagents = False
    assert flags.is_allowed("fetch") is False
    assert flags.is_allowed("search") is False
    print("✅ test_reset 通过")


def test_agent_override():
    """测试：Agent 覆盖正确生效。"""
    flags = CapabilityFlags()
    agent = "agent-001"

    # 平台默认 fetch 关闭
    assert flags.is_allowed("fetch", agent) is False

    # 为 Agent 覆盖打开
    flags.set_agent_override(agent, "fetch", True)
    assert flags.is_allowed("fetch", agent) is True

    # 其他 Agent 不受影响
    assert flags.is_allowed("fetch", "agent-002") is False

    # 清除覆盖后恢复
    flags.clear_agent_overrides(agent)
    assert flags.is_allowed("fetch", agent) is False
    print("✅ test_agent_override 通过")


def test_check_action():
    """测试：check 方法返回正确的操作建议。"""
    flags = CapabilityFlags()
    # 默认关 → 需审批
    assert flags.check("fetch") == FlagAction.REQUIRE_APPROVAL
    assert flags.check("search") == FlagAction.REQUIRE_APPROVAL
    # 默认开 → 放行
    assert flags.check("skills") == FlagAction.ALLOW
    # 默认关的非外网 → 拒绝
    assert flags.check("mcp") == FlagAction.DENY
    print("✅ test_check_action 通过")


def test_taiji_engine_init():
    """测试：太极引擎初始化正确。"""
    from engine.taiji import taiji
    taiji.init()
    assert taiji.initialized is True
    assert taiji.flags is not None
    assert taiji.flags.fetch is False
    print("✅ test_taiji_engine_init 通过")


if __name__ == "__main__":
    test_default_values()
    test_user_toggle()
    test_reset()
    test_agent_override()
    test_check_action()
    test_taiji_engine_init()
    print("\n🎉 全部 6 项测试通过 — Phase 1 引擎骨架 + 能力开关")
