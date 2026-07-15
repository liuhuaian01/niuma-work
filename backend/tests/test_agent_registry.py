"""
P2-14: Agent 身份注册表 — 单元测试

覆盖：
1. Agent 注册/重复注册/注销
2. 令牌签发/验证/过期/吊销
3. 密钥轮换
4. Workspace 隔离
5. 统计信息
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import time
import pytest
from engine.agent_registry import AgentRegistry, AgentIdentityToken, agent_registry


# ---- helpers ----

def _new_registry():
    """创建全新注册表实例——隔离每个测试的状态。"""
    return AgentRegistry()


async def _init(r: AgentRegistry):
    await r.initialize()


@pytest.mark.asyncio
async def test_register_agent():
    """注册 Agent 成功。"""
    r = _new_registry()
    await _init(r)
    rec = await r.register_agent("agent-1", "ws-default", "Hermes", "director")
    assert rec.agent_id == "agent-1"
    assert rec.name == "Hermes"
    assert rec.role == "director"
    assert rec.revoked is False
    assert r.is_agent_registered("agent-1")


@pytest.mark.asyncio
async def test_register_duplicate_agent():
    """重复注册同一 agent_id 应抛出 ValueError。"""
    r = _new_registry()
    await _init(r)
    await r.register_agent("dup-agent", "ws-1", "AgentX", "coder")
    with pytest.raises(ValueError, match="已注册且未吊销"):
        await r.register_agent("dup-agent", "ws-1", "AgentY", "writer")


@pytest.mark.asyncio
async def test_register_after_revoke():
    """吊销后重新注册应成功。"""
    r = _new_registry()
    await _init(r)
    await r.register_agent("reborn", "ws-1", "OldName", "coder")
    await r.revoke_agent("reborn")
    # 吊销后重新注册
    rec = await r.register_agent("reborn", "ws-2", "NewName", "writer")
    assert rec.name == "NewName"


@pytest.mark.asyncio
async def test_revoke_agent():
    """吊销 Agent: is_agent_registered 返回 False。"""
    r = _new_registry()
    await _init(r)
    await r.register_agent("kill-me", "ws-1", "Temp", "custom")
    assert r.is_agent_registered("kill-me")
    ok = await r.revoke_agent("kill-me")
    assert ok
    assert not r.is_agent_registered("kill-me")


@pytest.mark.asyncio
async def test_revoke_nonexistent():
    """吊销不存在的 Agent 返回 False。"""
    r = _new_registry()
    await _init(r)
    ok = await r.revoke_agent("ghost")
    assert not ok


@pytest.mark.asyncio
async def test_issue_identity_token():
    """签发令牌——返回三段式字符串。"""
    r = _new_registry()
    await _init(r)
    await r.register_agent("tok-agent", "ws-1", "TokenTest", "reviewer")
    token = await r.issue_identity_token("tok-agent")
    assert token is not None
    parts = token.split(".")
    assert len(parts) == 3
    assert all(p for p in parts)


@pytest.mark.asyncio
async def test_issue_token_unregistered():
    """未注册 Agent 签发返回 None。"""
    r = _new_registry()
    await _init(r)
    token = await r.issue_identity_token("nobody")
    assert token is None


@pytest.mark.asyncio
async def test_verify_token():
    """签发后立即验证——通过。"""
    r = _new_registry()
    await _init(r)
    await r.register_agent("valid-agent", "ws-1", "Valid", "researcher")
    token = await r.issue_identity_token("valid-agent")
    valid, reason, info = await r.verify_token(token)
    assert valid, f"Expected valid token, got: {reason}"
    assert info["agent_id"] == "valid-agent"
    assert info["name"] == "Valid"


@pytest.mark.asyncio
async def test_verify_invalid_token():
    """篡改签名——验证失败。"""
    r = _new_registry()
    await _init(r)
    await r.register_agent("sig-agent", "ws-1", "Sig", "coder")
    token = await r.issue_identity_token("sig-agent")
    # 修改 payload 中的 agent_id（签名不匹配）
    parts = token.split(".")
    tampered = parts[0] + "." + parts[1] + "." + "0" * 64
    valid, reason, info = await r.verify_token(tampered)
    assert not valid
    assert "签名无效" in reason


@pytest.mark.asyncio
async def test_verify_garbage_token():
    """完全无效的字符串——验证失败。"""
    r = _new_registry()
    await _init(r)
    valid, reason, info = await r.verify_token("not.a.token")
    assert not valid


@pytest.mark.asyncio
async def test_verify_expired_token():
    """过期令牌——验证失败。"""
    r = _new_registry()
    await _init(r)
    await r.register_agent("exp-agent", "ws-1", "Expired", "coder")
    # 签发负 TTL（立即过期）
    token = await r.issue_identity_token("exp-agent", ttl=-1)
    # 无需等待，expires_at = now - 1 已经过去
    valid, reason, info = await r.verify_token(token)
    assert not valid
    assert "已过期" in reason


@pytest.mark.asyncio
async def test_revoke_token():
    """吊销单个令牌——后续验证失败。"""
    r = _new_registry()
    await _init(r)
    await r.register_agent("rev-tok", "ws-1", "RevokeTest", "writer")
    token = await r.issue_identity_token("rev-tok")
    # 先用一次确认有效
    valid, _, _ = await r.verify_token(token)
    assert valid
    # 吊销
    ok = await r.revoke_token(token)
    assert ok
    # 再次验证
    valid, reason, _ = await r.verify_token(token)
    assert not valid
    assert "已被吊销" in reason


@pytest.mark.asyncio
async def test_revoke_agent_blocks_tokens():
    """吊销 Agent 后其令牌失效。"""
    r = _new_registry()
    await _init(r)
    await r.register_agent("bye-agent", "ws-1", "Bye", "custom")
    token = await r.issue_identity_token("bye-agent")
    valid, _, _ = await r.verify_token(token)
    assert valid
    # 吊销 Agent
    await r.revoke_agent("bye-agent")
    valid, reason, _ = await r.verify_token(token)
    assert not valid
    assert "未注册或已吊销" in reason


@pytest.mark.asyncio
async def test_rotate_secret_invalidates_tokens():
    """密钥轮换——旧令牌全部失效。"""
    r = _new_registry()
    await _init(r)
    await r.register_agent("rotate-agent", "ws-1", "Rotate", "director")
    token = await r.issue_identity_token("rotate-agent")
    valid, _, _ = await r.verify_token(token)
    assert valid
    # 轮换密钥
    r.rotate_secret()
    valid, reason, _ = await r.verify_token(token)
    assert not valid
    assert "签名无效" in reason


@pytest.mark.asyncio
async def test_workspace_isolation_in_list():
    """list_agents 按 workspace 过滤。"""
    r = _new_registry()
    await _init(r)
    await r.register_agent("ws-a-1", "workspace-A", "Alpha1", "coder")
    await r.register_agent("ws-a-2", "workspace-A", "Alpha2", "writer")
    await r.register_agent("ws-b-1", "workspace-B", "Beta1", "reviewer")

    # 无过滤：3 个
    assert len(r.list_agents()) == 3
    # workspace-A: 2 个
    assert len(r.list_agents("workspace-A")) == 2
    # workspace-B: 1 个
    assert len(r.list_agents("workspace-B")) == 1


@pytest.mark.asyncio
async def test_agent_info():
    """get_agent_info 返回正确信息。"""
    r = _new_registry()
    await _init(r)
    await r.register_agent("info-agent", "w", "Info", "coder",
                           metadata={"lang": "python", "version": "1.0"})
    info = r.get_agent_info("info-agent")
    assert info is not None
    assert info["agent_id"] == "info-agent"
    assert info["role"] == "coder"
    assert info["metadata"]["lang"] == "python"


@pytest.mark.asyncio
async def test_get_stats():
    """统计信息正确。"""
    r = _new_registry()
    await _init(r)
    await r.register_agent("s1", "w1", "Stats1", "coder")
    await r.register_agent("s2", "w1", "Stats2", "writer")
    await r.revoke_agent("s2")
    stats = r.get_stats()
    assert stats["total_registrations"] == 2
    assert stats["active_agents"] == 1
    assert stats["revoked_agents"] == 1


@pytest.mark.asyncio
async def test_workspace_isolation_in_verify():
    """验证时返回正确的 workspace_id。"""
    r = _new_registry()
    await _init(r)
    await r.register_agent("ws-test", "isolated-ws", "Isolated", "researcher")
    token = await r.issue_identity_token("ws-test")
    valid, _, info = await r.verify_token(token)
    assert valid
    assert info["workspace_id"] == "isolated-ws"
    assert info["agent_id"] == "ws-test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
