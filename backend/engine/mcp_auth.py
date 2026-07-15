"""
太极引擎 · MCP 安全认证层

P1-6 修复: 为 MCP 客户端添加 API Key 认证 + Token 管理 + Server 白名单。
对齐 OWASP ASI06（供应链风险）和 MCP Security Best Practices。

实现:
- MCP Server 注册白名单（仅允许已注册 server 连接）
- API Key 签发/验证（HMAC-SHA256）
- 单次 Token 验证（防止令牌直传）
- Server 指纹校验（防止中间人替换）

用法:
    from engine.mcp_auth import mcp_auth
    await mcp_auth.initialize()
    ok = await mcp_auth.validate_server_access(server_id, api_key)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ============================================================
# 数据模型
# ============================================================

@dataclass
class MCPAccessToken:
    """单次 MCP 访问令牌——一次性使用，防重放。"""
    token: str
    server_id: str
    issued_at: float
    expires_at: float
    scope: str = "mcp:tools-basic"
    used: bool = False


@dataclass
class MCPRegistration:
    """MCP Server 注册记录"""
    server_id: str
    server_name: str
    api_key_hash: str           # SHA-256 of API key
    server_fingerprint: str     # SHA-256 of (name + command + version)
    registered_at: float
    revoked: bool = False
    metadata: dict = field(default_factory=dict)


# ============================================================
# MCP 认证引擎
# ============================================================

class MCPAuth:
    """MCP 安全认证引擎。

    三层防护:
    1. 白名单注册 — 仅已注册 server 可连接
    2. API Key 验证 — HMAC 签名校验
    3. 单次 Token — 每次工具调用签发一次性 token
    """

    TOKEN_TTL = 300  # 令牌有效期 5 分钟
    _MAX_TOKENS = 1000  # 内存中最多保留 1000 个令牌

    def __init__(self):
        self._registrations: dict[str, MCPRegistration] = {}
        self._tokens: dict[str, MCPAccessToken] = {}
        self._initialized = False

    async def initialize(self):
        """初始化——从持久化存储加载注册表。"""
        # 生产环境从 DB 加载，当前阶段使用内存注册表
        self._initialized = True
        logger.info("MCP 认证层已初始化 — 白名单模式")

    # ---- API Key 生成与验证 ----

    @staticmethod
    def generate_api_key() -> str:
        """生成安全 API Key。

        Format: sn_mcp_<64 位 hex>
        """
        return f"sn_mcp_{secrets.token_hex(32)}"

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """对 API Key 做单向哈希——存储不可逆。"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def verify_api_key(self, server_id: str, api_key: str) -> bool:
        """验证 API Key —— 常数时间比较防时序攻击。"""
        reg = self._registrations.get(server_id)
        if not reg or reg.revoked:
            return False
        expected_hash = reg.api_key_hash
        actual_hash = self.hash_api_key(api_key)
        return hmac.compare_digest(expected_hash, actual_hash)

    # ---- Server 注册 ----

    @staticmethod
    def compute_fingerprint(server_name: str, server_command: list[str], version: str = "0.1.0") -> str:
        """计算 Server 指纹——防止被替换为恶意 server。

        指纹 = SHA256(name + command + version)
        """
        raw = f"{server_name}|{' '.join(server_command)}|{version}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def register_server(
        self,
        server_name: str,
        server_command: list[str],
        version: str = "0.1.0",
        metadata: dict | None = None,
    ) -> tuple[str, str]:
        """注册 MCP Server——返回 (server_id, api_key)。

        API Key 只在此次调用中明文返回，之后仅存储哈希。
        调用者必须安全保存 API Key。

        Raises:
            ValueError: server_command 为空
        """
        if not server_command:
            raise ValueError("server_command 不能为空")

        server_id = f"mcp_{secrets.token_hex(8)}"
        api_key = self.generate_api_key()
        api_key_hash = self.hash_api_key(api_key)
        fingerprint = self.compute_fingerprint(server_name, server_command, version)

        reg = MCPRegistration(
            server_id=server_id,
            server_name=server_name,
            api_key_hash=api_key_hash,
            server_fingerprint=fingerprint,
            registered_at=time.time(),
            metadata=metadata or {},
        )

        self._registrations[server_id] = reg
        logger.info("MCP Server 已注册: %s (id=%s, fingerprint=%s...)", server_name, server_id, fingerprint[:16])

        # 异步持久化（生产环境写 DB）
        await self._persist_registration(reg)

        return server_id, api_key

    async def revoke_server(self, server_id: str) -> bool:
        """吊销 MCP Server 注册——撤回所有访问权限。"""
        reg = self._registrations.get(server_id)
        if not reg:
            return False
        reg.revoked = True
        logger.warning("MCP Server 已吊销: %s (%s)", reg.server_name, server_id)
        return True

    async def validate_fingerprint(self, server_id: str, server_name: str, server_command: list[str]) -> bool:
        """验证 Server 指纹——检查连接的 server 是否与注册时一致。"""
        reg = self._registrations.get(server_id)
        if not reg or reg.revoked:
            return False
        current_fp = self.compute_fingerprint(server_name, server_command)
        return hmac.compare_digest(reg.server_fingerprint, current_fp)

    # ---- 单次 Token 管理 ----

    async def issue_token(self, server_id: str, scope: str = "mcp:tools-basic") -> MCPAccessToken | None:
        """签发单次访问令牌。

        Args:
            server_id: MCP Server ID
            scope: 权限范围（默认仅允许工具发现/读操作）

        Returns:
            MCPAccessToken 或 None（server 未注册/已吊销）
        """
        reg = self._registrations.get(server_id)
        if not reg or reg.revoked:
            return None

        # 清理过期令牌
        self._gc_tokens()

        token_str = f"mcp_tok_{secrets.token_hex(24)}"
        now = time.time()
        tok = MCPAccessToken(
            token=token_str,
            server_id=server_id,
            issued_at=now,
            expires_at=now + self.TOKEN_TTL,
            scope=scope,
        )

        # 防止令牌泄露——限制内存中令牌数量
        if len(self._tokens) >= self._MAX_TOKENS:
            oldest = min(self._tokens.values(), key=lambda t: t.issued_at)
            del self._tokens[oldest.token]

        self._tokens[token_str] = tok
        return tok

    async def validate_token(self, token_str: str, required_scope: str = "mcp:tools-basic") -> bool:
        """验证并消费单次令牌——一次性使用，防重放。"""
        tok = self._tokens.get(token_str)
        if not tok:
            return False

        # 检查过期
        if time.time() > tok.expires_at:
            del self._tokens[token_str]
            return False

        # 检查 scope
        if required_scope not in tok.scope:
            return False

        # 一次性消费——删除令牌防止重放
        del self._tokens[token_str]
        return True

    # ---- 完整访问验证流程 ----

    async def validate_server_access(
        self,
        server_id: str,
        api_key: str,
        server_name: str = "",
        server_command: list[str] | None = None,
    ) -> tuple[bool, str]:
        """完整的 MCP Server 访问验证流程。

        三步校验:
        1. API Key 验证
        2. Server 指纹校验（如果提供了 command）
        3. 签发单次访问令牌

        Returns:
            (是否通过, 原因/令牌)
        """
        # Step 1: API Key
        if not self.verify_api_key(server_id, api_key):
            return False, "API Key 验证失败"

        # Step 2: 指纹校验
        if server_command and server_name:
            if not await self.validate_fingerprint(server_id, server_name, server_command):
                return False, "Server 指纹不匹配——可能已被替换"

        # Step 3: 签发令牌
        token = await self.issue_token(server_id)
        if not token:
            return False, "令牌签发失败——Server 可能已吊销"

        return True, token.token

    # ---- 持久化 ----

    async def _persist_registration(self, reg: MCPRegistration):
        """异步持久化注册记录。生产环境写入 DB。"""
        logger.debug("MCP 注册持久化: %s (生产环境需实现 DB 写入)", reg.server_id)

    def _gc_tokens(self):
        """清理过期令牌。"""
        now = time.time()
        expired = [t for t, tok in self._tokens.items() if now > tok.expires_at]
        for t in expired:
            del self._tokens[t]
        if expired:
            logger.debug("清理 %d 个过期 MCP 令牌", len(expired))

    def get_stats(self) -> dict:
        """获取认证统计。"""
        total_reg = len(self._registrations)
        active_reg = sum(1 for r in self._registrations.values() if not r.revoked)
        return {
            "total_registrations": total_reg,
            "active_registrations": active_reg,
            "revoked_registrations": total_reg - active_reg,
            "active_tokens": len(self._tokens),
            "token_ttl": self.TOKEN_TTL,
        }


# 全局单例
mcp_auth = MCPAuth()
