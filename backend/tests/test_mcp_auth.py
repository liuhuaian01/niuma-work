"""
P2-14: MCP 安全认证层 — 单元测试

覆盖：
1. API Key 生成/哈希/验证
2. MCP Server 注册/注销
3. Server 指纹校验
4. 单次 Token 签发/验证/防重放/过期
5. 完整访问验证流程
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import time
import pytest
from engine.mcp_auth import MCPAuth, MCPAccessToken, MCPRegistration, mcp_auth


# ---- helpers ----

def _new_auth():
    return MCPAuth()


async def _init(a: MCPAuth):
    await a.initialize()


# ============================================================
# API Key
# ============================================================

@pytest.mark.asyncio
async def test_generate_api_key():
    """生成的 API Key 格式正确。"""
    key = MCPAuth.generate_api_key()
    assert key.startswith("sn_mcp_")
    assert len(key) == 7 + 64  # "sn_mcp_" + 64 hex chars
    # 不可逆——每次不同
    key2 = MCPAuth.generate_api_key()
    assert key != key2


@pytest.mark.asyncio
async def test_hash_api_key():
    """哈希长度固定 64 位 hex。"""
    h = MCPAuth.hash_api_key("sn_mcp_abcdef")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


@pytest.mark.asyncio
async def test_hash_is_deterministic():
    """相同输入产生相同哈希。"""
    a = MCPAuth.hash_api_key("test-key-123")
    b = MCPAuth.hash_api_key("test-key-123")
    assert a == b


@pytest.mark.asyncio
async def test_hash_is_different():
    """不同输入产生不同哈希。"""
    a = MCPAuth.hash_api_key("test-key-123")
    b = MCPAuth.hash_api_key("test-key-456")
    assert a != b


# ============================================================
# Server 注册
# ============================================================

@pytest.mark.asyncio
async def test_register_server():
    """注册 MCP Server——返回 (server_id, api_key)。"""
    a = _new_auth()
    await _init(a)
    sid, key = await a.register_server("filesystem", ["uvx", "mcp-server-filesystem", "/tmp"])
    assert sid.startswith("mcp_")
    assert len(sid) == 4 + 16  # "mcp_" + 16 hex
    assert key.startswith("sn_mcp_")
    assert len(key) == 71  # "sn_mcp_" + 64 hex


@pytest.mark.asyncio
async def test_register_server_empty_command():
    """空 command 抛出 ValueError。"""
    a = _new_auth()
    await _init(a)
    with pytest.raises(ValueError, match="不能为空"):
        await a.register_server("bad", [])


@pytest.mark.asyncio
async def test_revoke_server():
    """吊销后 verify_api_key 失败。"""
    a = _new_auth()
    await _init(a)
    sid, key = await a.register_server("to-revoke", ["echo", "hello"])
    assert a.verify_api_key(sid, key)
    await a.revoke_server(sid)
    assert not a.verify_api_key(sid, key)


@pytest.mark.asyncio
async def test_revoke_nonexistent_server():
    """吊销不存在的 server 返回 False。"""
    a = _new_auth()
    await _init(a)
    result = await a.revoke_server("mcp_ghost")
    assert not result


# ============================================================
# API Key 验证
# ============================================================

@pytest.mark.asyncio
async def test_verify_api_key():
    """正确 API Key 验证通过。"""
    a = _new_auth()
    await _init(a)
    sid, key = await a.register_server("test-srv", ["python", "-m", "test"])
    assert a.verify_api_key(sid, key)


@pytest.mark.asyncio
async def test_verify_wrong_api_key():
    """错误 API Key 验证失败。"""
    a = _new_auth()
    await _init(a)
    sid, key = await a.register_server("test-srv", ["python", "-m", "test"])
    assert not a.verify_api_key(sid, "sn_mcp_" + "0" * 64)


@pytest.mark.asyncio
async def test_verify_wrong_server_id():
    """不存在的 server_id 验证失败。"""
    a = _new_auth()
    await _init(a)
    sid, key = await a.register_server("test-srv", ["python", "-m", "test"])
    assert not a.verify_api_key("mcp_doesnotexist", key)


# ============================================================
# 指纹校验
# ============================================================

@pytest.mark.asyncio
async def test_compute_fingerprint():
    """同参数指纹一致。"""
    fp1 = MCPAuth.compute_fingerprint("test", ["python", "script.py"])
    fp2 = MCPAuth.compute_fingerprint("test", ["python", "script.py"])
    assert fp1 == fp2
    assert len(fp1) == 64


@pytest.mark.asyncio
async def test_fingerprint_differs_by_name():
    """不同名称指纹不同。"""
    fp1 = MCPAuth.compute_fingerprint("server-A", ["python", "s.py"])
    fp2 = MCPAuth.compute_fingerprint("server-B", ["python", "s.py"])
    assert fp1 != fp2


@pytest.mark.asyncio
async def test_fingerprint_differs_by_command():
    """不同命令指纹不同。"""
    fp1 = MCPAuth.compute_fingerprint("srv", ["python", "a.py"])
    fp2 = MCPAuth.compute_fingerprint("srv", ["python", "b.py"])
    assert fp1 != fp2


@pytest.mark.asyncio
async def test_validate_fingerprint():
    """正确指纹验证通过。"""
    a = _new_auth()
    await _init(a)
    cmd = ["uvx", "mcp-server-filesystem", "/workspace"]
    sid, key = await a.register_server("filesystem", cmd)
    assert await a.validate_fingerprint(sid, "filesystem", cmd)


@pytest.mark.asyncio
async def test_validate_fingerprint_mismatch():
    """替换命令——指纹不匹配。"""
    a = _new_auth()
    await _init(a)
    cmd = ["uvx", "mcp-server-filesystem", "/workspace"]
    sid, key = await a.register_server("filesystem", cmd)
    evil_cmd = ["uvx", "evil-server", "/"]
    assert not await a.validate_fingerprint(sid, "filesystem", evil_cmd)


# ============================================================
# Token 签发与验证
# ============================================================

@pytest.mark.asyncio
async def test_issue_token():
    """签发单次 Token 成功。"""
    a = _new_auth()
    await _init(a)
    sid, key = await a.register_server("tok-server", ["echo", "ok"])
    tok = await a.issue_token(sid)
    assert tok is not None
    assert tok.token.startswith("mcp_tok_")
    assert tok.server_id == sid
    assert tok.used is False


@pytest.mark.asyncio
async def test_issue_token_unregistered():
    """未注册 server 签发返回 None。"""
    a = _new_auth()
    await _init(a)
    tok = await a.issue_token("mcp_nobody")
    assert tok is None


@pytest.mark.asyncio
async def test_validate_token():
    """有效 Token 验证通过。"""
    a = _new_auth()
    await _init(a)
    sid, key = await a.register_server("val-server", ["echo", "ok"])
    tok = await a.issue_token(sid)
    assert await a.validate_token(tok.token)


@pytest.mark.asyncio
async def test_validate_token_replay_attack():
    """Token 一次性使用——第二次验证失败（防重放）。"""
    a = _new_auth()
    await _init(a)
    sid, key = await a.register_server("replay-server", ["echo", "ok"])
    tok = await a.issue_token(sid)
    # 第一次使用
    assert await a.validate_token(tok.token)
    # 重放攻击
    assert not await a.validate_token(tok.token)
    assert not await a.validate_token(tok.token)


@pytest.mark.asyncio
async def test_validate_token_expired():
    """过期 Token 验证失败。"""
    a = _new_auth()
    await _init(a)
    sid, key = await a.register_server("exp-server", ["echo", "ok"])
    # 临时缩短 TTL
    original_ttl = a.TOKEN_TTL
    a.TOKEN_TTL = 0  # 立即过期
    tok = await a.issue_token(sid)
    await asyncio.sleep(0.1)
    assert not await a.validate_token(tok.token)
    a.TOKEN_TTL = original_ttl


@pytest.mark.asyncio
async def test_validate_nonexistent_token():
    """不存在的 Token 验证失败。"""
    a = _new_auth()
    await _init(a)
    assert not await a.validate_token("mcp_tok_garbage12345")


@pytest.mark.asyncio
async def test_validate_token_scope():
    """scope 不匹配验证失败。"""
    a = _new_auth()
    await _init(a)
    sid, key = await a.register_server("scope-server", ["echo", "ok"])
    tok = await a.issue_token(sid, scope="mcp:tools-basic")
    # 正确 scope
    assert await a.validate_token(tok.token, required_scope="mcp:tools-basic")
    # 但 token 已消费，需要新 token
    tok2 = await a.issue_token(sid, scope="mcp:tools-basic")
    # 请求更高 scope
    assert not await a.validate_token(tok2.token, required_scope="mcp:tools-admin")


# ============================================================
# 完整访问验证
# ============================================================

@pytest.mark.asyncio
async def test_validate_server_access():
    """完整验证流程通过——返回 (True, token)。"""
    a = _new_auth()
    await _init(a)
    cmd = ["uvx", "mcp-server-filesystem", "/workspace"]
    sid, key = await a.register_server("full-server", cmd)
    ok, result = await a.validate_server_access(sid, key, "full-server", cmd)
    assert ok
    assert result.startswith("mcp_tok_")


@pytest.mark.asyncio
async def test_validate_server_access_wrong_key():
    """错误 API Key——验证失败。"""
    a = _new_auth()
    await _init(a)
    cmd = ["uvx", "mcp-server-filesystem", "/workspace"]
    sid, key = await a.register_server("wrong-key", cmd)
    ok, result = await a.validate_server_access(sid, "sn_mcp_" + "0" * 64, "wrong-key", cmd)
    assert not ok
    assert "API Key" in result


@pytest.mark.asyncio
async def test_validate_server_access_fingerprint_mismatch():
    """指纹不匹配——验证失败。"""
    a = _new_auth()
    await _init(a)
    cmd = ["uvx", "mcp-server-filesystem", "/workspace"]
    sid, key = await a.register_server("fp-test", cmd)
    evil_cmd = ["uvx", "evil-server", "/"]
    ok, result = await a.validate_server_access(sid, key, "fp-test", evil_cmd)
    assert not ok
    assert "指纹" in result


@pytest.mark.asyncio
async def test_validate_server_access_no_fingerprint():
    """不传 command 时跳过指纹校验——仍成功。"""
    a = _new_auth()
    await _init(a)
    cmd = ["uvx", "mcp-server-filesystem", "/workspace"]
    sid, key = await a.register_server("nofp", cmd)
    ok, result = await a.validate_server_access(sid, key)
    assert ok
    assert result.startswith("mcp_tok_")


# ============================================================
# 统计
# ============================================================

@pytest.mark.asyncio
async def test_get_stats():
    """统计信息正确。"""
    a = _new_auth()
    await _init(a)
    sid1, k1 = await a.register_server("s1", ["echo", "1"])
    sid2, k2 = await a.register_server("s2", ["echo", "2"])
    await a.revoke_server(sid2)
    stats = a.get_stats()
    assert stats["total_registrations"] == 2
    assert stats["active_registrations"] == 1
    assert stats["revoked_registrations"] == 1


@pytest.mark.asyncio
async def test_token_gc_evicts_oldest():
    """令牌数量超过上限时驱逐最旧令牌。"""
    a = _new_auth()
    await _init(a)
    # 降低上限以便测试
    a._MAX_TOKENS = 5
    sid, key = await a.register_server("gc-test", ["echo", "ok"])
    tokens = []
    for i in range(7):
        tok = await a.issue_token(sid)
        tokens.append(tok)
    # 前 2 个最旧的应被驱逐
    assert not await a.validate_token(tokens[0].token)
    assert not await a.validate_token(tokens[1].token)
    # 后 5 个仍可用
    assert await a.validate_token(tokens[6].token)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
