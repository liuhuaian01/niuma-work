"""
太极引擎 · Agent 身份注册表

P1-7 修复: Agent 身份令牌签发/验证/吊销。
对齐 OWASP ASI05（Agent冒充）和 NIST AI Agent 身份认证标准。

核心功能:
- Agent 身份注册/注销
- JWT-like 身份令牌签发（HMAC-SHA256）
- 令牌验证与过期管理
- 令牌吊销列表
- 身份信息查询

用法:
    from engine.agent_registry import agent_registry
    await agent_registry.initialize()
    token = await agent_registry.issue_identity_token(agent_id)
    ok = await agent_registry.verify_token(token)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import time
from base64 import urlsafe_b64encode, urlsafe_b64decode
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ============================================================
# 数据模型
# ============================================================

class AgentIdentityToken:
    """Agent 身份令牌（类 JWT 结构）。

    三段式: header.payload.signature
    - header: {"alg":"HS256","typ":"AIT"}
    - payload: base64(json)
    - signature: HMAC-SHA256(header.payload, secret)
    """

    def __init__(
        self,
        agent_id: str,
        workspace_id: str,
        agent_name: str,
        agent_role: str,
        issued_at: float,
        expires_at: float,
        token_id: str = "",
        metadata: dict | None = None,
    ):
        self.agent_id = agent_id
        self.workspace_id = workspace_id
        self.agent_name = agent_name
        self.agent_role = agent_role
        self.issued_at = issued_at
        self.expires_at = expires_at
        self.token_id = token_id or f"ait_{secrets.token_hex(8)}"
        self.metadata = metadata or {}

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_payload(self) -> dict:
        return {
            "sub": self.agent_id,
            "wid": self.workspace_id,
            "name": self.agent_name,
            "role": self.agent_role,
            "iat": int(self.issued_at),
            "exp": int(self.expires_at),
            "jti": self.token_id,
            "meta": self.metadata,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "AgentIdentityToken":
        meta = payload.get("meta", {})
        if not isinstance(meta, dict):
            meta = {}
        return cls(
            agent_id=payload["sub"],
            workspace_id=payload.get("wid", ""),
            agent_name=payload.get("name", ""),
            agent_role=payload.get("role", "unknown"),
            issued_at=float(payload["iat"]),
            expires_at=float(payload["exp"]),
            token_id=payload.get("jti", ""),
            metadata=meta,
        )


@dataclass
class AgentIdentityRecord:
    """Agent 身份注册记录"""
    agent_id: str
    workspace_id: str
    name: str
    role: str
    registered_at: float
    revoked: bool = False
    revoked_at: float = 0.0
    public_key_hash: str = ""  # 可选：Agent 公钥指纹
    metadata: dict = field(default_factory=dict)


# ============================================================
# Agent 身份注册引擎
# ============================================================

class AgentRegistry:
    """Agent 身份注册表引擎。

    职责:
    - 注册/注销 Agent 身份
    - 签发/验证/吊销身份令牌
    - 令牌过期清扫
    """

    TOKEN_TTL = 86400   # 默认令牌有效期 24 小时
    LONG_TTL = 604800   # 长期令牌 7 天
    _MAX_TOKENS = 5000
    _REVOKED_MAX = 10000

    def __init__(self):
        self._secret: str = ""
        self._registrations: dict[str, AgentIdentityRecord] = {}
        self._revoked_tokens: dict[str, float] = {}  # token_id → revoked_at
        self._initialized = False

    async def initialize(self) -> None:
        """初始化——生成签名密钥 + 从 DB 加载注册表。"""
        if self._initialized:
            return

        # 生成签名密钥（生产环境应持久化并在多实例间共享）
        self._secret = secrets.token_hex(32)
        self._initialized = True
        logger.info("Agent 身份注册表已初始化 — %d 注册记录", len(self._registrations))

    # ---- 身份注册 ----

    async def register_agent(
        self,
        agent_id: str,
        workspace_id: str,
        name: str,
        role: str,
        public_key_hash: str = "",
        metadata: dict | None = None,
    ) -> AgentIdentityRecord:
        """注册 Agent 身份。

        Args:
            agent_id: Agent 唯一标识
            workspace_id: 所属工作间
            name: Agent 名称
            role: 角色 (director/writer/coder/researcher/reviewer/custom)
            public_key_hash: 公钥指纹（可选，用于高级认证）
            metadata: 附加元数据

        Returns:
            注册记录

        Raises:
            ValueError: agent_id 已存在
        """
        if agent_id in self._registrations:
            existing = self._registrations[agent_id]
            if not existing.revoked:
                raise ValueError(f"Agent {agent_id} 已注册且未吊销")

        record = AgentIdentityRecord(
            agent_id=agent_id,
            workspace_id=workspace_id,
            name=name,
            role=role,
            registered_at=time.time(),
            public_key_hash=public_key_hash,
            metadata=metadata or {},
        )

        self._registrations[agent_id] = record
        logger.info("Agent 身份已注册: %s (%s, role=%s)", name, agent_id, role)

        # 生产环境写 DB
        await self._persist_registration(record)
        return record

    async def revoke_agent(self, agent_id: str) -> bool:
        """吊销 Agent 身份——该 agent 的令牌立即失效。"""
        record = self._registrations.get(agent_id)
        if not record or record.revoked:
            return False

        record.revoked = True
        record.revoked_at = time.time()
        logger.warning("Agent 身份已吊销: %s (%s)", record.name, agent_id)

        # 清理该 agent 的已签发令牌
        self._gc_revoked()
        return True

    def is_agent_registered(self, agent_id: str) -> bool:
        """检查 Agent 是否已注册且未吊销。"""
        record = self._registrations.get(agent_id)
        return record is not None and not record.revoked

    def get_agent_info(self, agent_id: str) -> dict | None:
        """获取 Agent 身份信息。"""
        record = self._registrations.get(agent_id)
        if not record or record.revoked:
            return None
        return {
            "agent_id": record.agent_id,
            "workspace_id": record.workspace_id,
            "name": record.name,
            "role": record.role,
            "registered_at": record.registered_at,
            "metadata": record.metadata,
        }

    def list_agents(self, workspace_id: str = "") -> list[dict]:
        """列出所有活跃 Agent。"""
        agents = []
        for record in self._registrations.values():
            if record.revoked:
                continue
            if workspace_id and record.workspace_id != workspace_id:
                continue
            agents.append({
                "agent_id": record.agent_id,
                "workspace_id": record.workspace_id,
                "name": record.name,
                "role": record.role,
                "registered_at": record.registered_at,
            })
        return agents

    # ---- 身份令牌签发 ----

    async def issue_identity_token(
        self,
        agent_id: str,
        ttl: int | None = None,
        metadata: dict | None = None,
    ) -> str | None:
        """签发 Agent 身份令牌。

        Args:
            agent_id: Agent ID
            ttl: 有效期（秒），None 使用默认 TOKEN_TTL
            metadata: 令牌附加元数据

        Returns:
            序列化令牌字符串，如果 agent 未注册返回 None
        """
        record = self._registrations.get(agent_id)
        if not record or record.revoked:
            logger.warning("令牌签发拒绝: Agent %s 未注册或已吊销", agent_id)
            return None

        ttl = ttl or self.TOKEN_TTL
        now = time.time()

        token_obj = AgentIdentityToken(
            agent_id=agent_id,
            workspace_id=record.workspace_id,
            agent_name=record.name,
            agent_role=record.role,
            issued_at=now,
            expires_at=now + ttl,
            metadata=metadata or {},
        )

        return self._encode_token(token_obj)

    def _encode_token(self, token_obj: AgentIdentityToken) -> str:
        """序列化令牌为三段式字符串。"""
        header = {"alg": "HS256", "typ": "AIT"}

        header_b64 = urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
        payload_b64 = urlsafe_b64encode(json.dumps(token_obj.to_payload()).encode()).rstrip(b"=").decode()

        signing_input = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            self._secret.encode(),
            signing_input.encode(),
            hashlib.sha256,
        ).hexdigest()

        return f"{header_b64}.{payload_b64}.{signature}"

    def _decode_token(self, token_str: str) -> AgentIdentityToken | None:
        """解析并验证令牌。"""
        try:
            parts = token_str.split(".")
            if len(parts) != 3:
                return None

            header_b64, payload_b64, signature = parts

            # 验证签名
            signing_input = f"{header_b64}.{payload_b64}"
            expected_sig = hmac.new(
                self._secret.encode(),
                signing_input.encode(),
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(expected_sig, signature):
                return None

            # 解析 payload
            # 补回 base64 padding
            payload_b64_padded = payload_b64 + "=" * (-len(payload_b64) % 4)
            payload = json.loads(urlsafe_b64decode(payload_b64_padded.encode()).decode())

            return AgentIdentityToken.from_payload(payload)

        except Exception:
            return None

    # ---- 令牌验证 ----

    async def verify_token(self, token_str: str) -> tuple[bool, str, dict | None]:
        """验证 Agent 身份令牌。

        三步校验:
        1. 签名验证
        2. 过期检查
        3. 吊销检查

        Returns:
            (是否通过, 原因, Agent 信息字典)
        """
        # Step 1: 解码 + 签名验证
        token_obj = self._decode_token(token_str)
        if token_obj is None:
            return False, "令牌解析失败或签名无效", None

        # Step 2: 过期检查
        if token_obj.is_expired():
            return False, "令牌已过期", None

        # Step 3: 吊销检查
        if token_obj.token_id in self._revoked_tokens:
            return False, "令牌已被吊销", None

        # Step 4: Agent 身份检查
        record = self._registrations.get(token_obj.agent_id)
        if not record or record.revoked:
            return False, "Agent 身份未注册或已吊销", None

        agent_info = {
            "agent_id": token_obj.agent_id,
            "workspace_id": token_obj.workspace_id,
            "name": token_obj.agent_name,
            "role": token_obj.agent_role,
            "metadata": token_obj.metadata,
        }

        return True, "验证通过", agent_info

    async def revoke_token(self, token_str: str) -> bool:
        """吊销指定令牌——加入吊销列表。"""
        token_obj = self._decode_token(token_str)
        if token_obj is None:
            return False

        self._revoked_tokens[token_obj.token_id] = time.time()
        self._gc_revoked()
        logger.info("令牌已吊销: %s (Agent: %s)", token_obj.token_id, token_obj.agent_id)
        return True

    # ---- 批量操作 ----

    async def revoke_all_agent_tokens(self, agent_id: str) -> int:
        """吊销指定 Agent 的所有令牌——用于安全事件响应。"""
        count = 0
        # 我们无法回溯已签发的令牌，但可以通过吊销身份来阻止后续使用
        # 实际生产环境应维护 agent_token_map
        if agent_id in self._registrations:
            await self.revoke_agent(agent_id)
            count += 1
        logger.warning("已吊销 Agent %s 的所有令牌（%d 条记录）", agent_id, count)
        return count

    # ---- 持久化 ----

    async def _persist_registration(self, record: AgentIdentityRecord):
        """持久化注册记录。生产环境写入 DB。"""
        logger.debug("Agent 注册持久化: %s", record.agent_id)

    def _gc_revoked(self):
        """清理旧吊销记录——保留最近 10000 条。"""
        if len(self._revoked_tokens) > self._REVOKED_MAX:
            sorted_revoked = sorted(self._revoked_tokens.items(), key=lambda x: x[1])
            to_remove = len(self._revoked_tokens) - self._REVOKED_MAX
            for token_id, _ in sorted_revoked[:to_remove]:
                del self._revoked_tokens[token_id]

    def get_stats(self) -> dict:
        """获取注册统计。"""
        total = len(self._registrations)
        active = sum(1 for r in self._registrations.values() if not r.revoked)
        return {
            "total_registrations": total,
            "active_agents": active,
            "revoked_agents": total - active,
            "revoked_tokens": len(self._revoked_tokens),
            "token_ttl": self.TOKEN_TTL,
        }

    def rotate_secret(self) -> str:
        """轮换签名密钥。

        旧密钥失效，所有已签发令牌作废。
        生产环境应支持密钥版本化以允许平滑过渡。
        """
        old_secret = self._secret
        self._secret = secrets.token_hex(32)
        logger.warning("签名密钥已轮换——旧令牌全部失效")
        return self._secret


# 全局单例
agent_registry = AgentRegistry()
