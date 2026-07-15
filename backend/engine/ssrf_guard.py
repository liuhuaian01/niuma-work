"""
SSRF 防护模块 (P1-22) — MCP Security Best Practices MUST 要求

RFC 1918 / RFC 6598 / RFC 5735 / RFC 3927 私有 IP 阻断 + DNS 重绑定检测。

实现:
  1. IP 地址分类：私有 vs 公网 vs 回环 vs 链路本地
  2. URL 安全验证：解析 URL 后检查目标 IP
  3. DNS 重绑定防护：缓存解析结果，检测 TTL 异常
  4. httpx Transport 适配：透明拦截所有出站 HTTP 请求

使用方式:
    from engine.ssrf_guard import ssrf_guard, SSRFTransport

    # 方式1: 直接验证 URL
    result = ssrf_guard.validate_url("https://192.168.1.1/api")
    if not result["safe"]: raise SSRFBlockedError(result["reason"])

    # 方式2: httpx transport（推荐，透明拦截）
    transport = SSRFTransport()
    async with httpx.AsyncClient(transport=transport) as client:
        resp = await client.get("https://api.example.com/data")
"""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger("niuma.ssrf")

# ============================================================
# 私有/保留 IP 范围（RFC 定义）
# ============================================================

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),        # RFC 1918 (Class A)
    ipaddress.ip_network("172.16.0.0/12"),     # RFC 1918 (Class B)
    ipaddress.ip_network("192.168.0.0/16"),    # RFC 1918 (Class C)
    ipaddress.ip_network("127.0.0.0/8"),       # RFC 5735 (Loopback)
    ipaddress.ip_network("169.254.0.0/16"),    # RFC 3927 (Link-Local)
    ipaddress.ip_network("100.64.0.0/10"),     # RFC 6598 (CGNAT)
    ipaddress.ip_network("0.0.0.0/8"),         # RFC 5735 ("This" network)
    ipaddress.ip_network("224.0.0.0/4"),       # RFC 5771 (Multicast)
    ipaddress.ip_network("240.0.0.0/4"),       # RFC 1112 (Reserved)
    ipaddress.ip_network("::1/128"),           # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 Unique Local
    ipaddress.ip_network("fe80::/10"),         # IPv6 Link-Local
]

# DNS 重绑定检测：解析结果缓存
_DNS_CACHE: dict[str, tuple[list[str], float]] = {}
_DNS_CACHE_TTL = 300  # 5 分钟

# 白名单域名（允许访问的私有网络主机）
_ALLOWED_HOSTS: set[str] = set()


# ============================================================
# IP 分类
# ============================================================

def is_private_ip(ip_str: str) -> bool:
    """判断 IP 是否属于私有/保留范围。

    Args:
        ip_str: IPv4 或 IPv6 地址字符串

    Returns:
        True 表示该 IP 属于私有/保留地址，应被 SSRF 防护拦截。
    """
    try:
        addr = ipaddress.ip_address(ip_str.strip())
    except ValueError:
        return False

    for network in _PRIVATE_NETWORKS:
        if addr in network:
            return True
    return False


def classify_ip(ip_str: str) -> str:
    """分类 IP 地址类型。

    Returns:
        "private" | "loopback" | "link_local" | "multicast" | "public" | "invalid"
    """
    try:
        addr = ipaddress.ip_address(ip_str.strip())
    except ValueError:
        return "invalid"

    if addr.is_loopback:
        return "loopback"
    if addr.is_link_local:
        return "link_local"
    if addr.is_multicast:
        return "multicast"
    if addr.is_private:
        return "private"
    return "public"


# ============================================================
# URL 安全验证
# ============================================================

@dataclass
class SSRFCheckResult:
    safe: bool
    reason: str = ""
    resolved_ips: list[str] = field(default_factory=list)
    elapsed_ms: float = 0.0


def validate_url(url: str, allow_private: bool = False) -> SSRFCheckResult:
    """验证 URL 是否存在 SSRF 风险。

    检查步骤:
      1. 解析 URL 提取 hostname
      2. DNS 解析 hostname → IP 列表
      3. 检查每个 IP 是否为私有地址
      4. DNS 重绑定检测（缓存 TTL）

    Args:
        url: 待验证的 URL
        allow_private: 是否允许访问私有 IP（默认 False）

    Returns:
        SSRFCheckResult
    """
    t0 = time.monotonic()

    try:
        parsed = urlparse(url)
    except Exception:
        return SSRFCheckResult(safe=False, reason=f"无法解析 URL: {url}")

    hostname = parsed.hostname
    if not hostname:
        return SSRFCheckResult(safe=False, reason=f"URL 缺少主机名: {url}")

    # 白名单检查
    if hostname in _ALLOWED_HOSTS:
        return SSRFCheckResult(safe=True, reason="白名单主机", elapsed_ms=(time.monotonic() - t0) * 1000)

    # 先检查 hostname 本身是否为 IP
    if is_private_ip(hostname):
        if allow_private:
            logger.info("SSRF: 允许访问私有 IP %s (allow_private=True)", hostname)
            return SSRFCheckResult(
                safe=True, reason=f"允许私有 IP（显式放行）: {hostname}",
                resolved_ips=[hostname],
                elapsed_ms=(time.monotonic() - t0) * 1000,
            )
        logger.warning("SSRF_BLOCKED: 私有 IP 直连 %s → %s", url, hostname)
        return SSRFCheckResult(
            safe=False,
            reason=f"禁止访问私有 IP: {hostname} (URL: {url})",
            resolved_ips=[hostname],
            elapsed_ms=(time.monotonic() - t0) * 1000,
        )

    # DNS 解析
    try:
        resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        ips = list({r[4][0] for r in resolved})
    except socket.gaierror:
        return SSRFCheckResult(safe=False, reason=f"DNS 解析失败: {hostname}")

    # DNS 重绑定检测
    cached = _DNS_CACHE.get(hostname)
    if cached:
        cached_ips, cached_at = cached
        if time.time() - cached_at < _DNS_CACHE_TTL:
            if set(ips) != set(cached_ips):
                logger.warning(
                    "SSRF_DNS_REBINDING: %s 解析结果变化 %s → %s",
                    hostname, cached_ips, ips,
                )
                return SSRFCheckResult(
                    safe=False,
                    reason=f"DNS 重绑定检测: {hostname} 解析结果已变更 (旧: {cached_ips}, 新: {ips})",
                    resolved_ips=ips,
                    elapsed_ms=(time.monotonic() - t0) * 1000,
                )
    _DNS_CACHE[hostname] = (ips, time.time())

    # 检查每个解析 IP
    for ip in ips:
        if is_private_ip(ip) or ip.startswith("0."):
            if allow_private:
                logger.info("SSRF: 允许解析到私有 IP %s → %s (allow_private=True)", hostname, ip)
                continue
            logger.warning("SSRF_BLOCKED: %s 解析到私有 IP %s", hostname, ip)
            return SSRFCheckResult(
                safe=False,
                reason=f"禁止访问解析到私有 IP 的主机: {hostname} → {ip} (URL: {url})",
                resolved_ips=ips,
                elapsed_ms=(time.monotonic() - t0) * 1000,
            )

    return SSRFCheckResult(
        safe=True, reason="通过",
        resolved_ips=ips,
        elapsed_ms=(time.monotonic() - t0) * 1000,
    )


# ============================================================
# 白名单管理
# ============================================================

def add_allowlist_host(hostname: str) -> None:
    """将主机名加入 SSRF 白名单（如内部 API）。"""
    _ALLOWED_HOSTS.add(hostname)
    logger.info("SSRF 白名单添加: %s", hostname)


def remove_allowlist_host(hostname: str) -> None:
    """从白名单中移除主机名。"""
    _ALLOWED_HOSTS.discard(hostname)


def get_allowlist() -> list[str]:
    """获取当前白名单列表。"""
    return sorted(_ALLOWED_HOSTS)


# ============================================================
# httpx Transport 适配器（透明 SSRF 拦截）
# ============================================================

import httpx  # noqa: E402


class SSRFTransport(httpx.AsyncHTTPTransport):
    """httpx 传输层适配器——透明拦截所有出站请求的 SSRF 风险。

    使用方式:
        transport = SSRFTransport()
        async with httpx.AsyncClient(transport=transport) as client:
            resp = await client.get("https://safe.example.com/data")
    """

    def __init__(self, allow_private: bool = False, **kwargs):
        super().__init__(**kwargs)
        self._allow_private = allow_private

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)

        # SSRF 检查
        check = validate_url(url, allow_private=self._allow_private)
        if not check.safe:
            logger.warning(
                "SSRFTransport BLOCKED: %s [%s]",
                url, check.reason,
            )
            # 返回 403，而不是真正发出请求
            return httpx.Response(
                status_code=403,
                json={
                    "code": "ssrf_blocked",
                    "message": check.reason,
                    "url": url,
                },
                request=request,
            )

        logger.debug("SSRFTransport PASS: %s → %s", url, check.resolved_ips)
        return await super().handle_async_request(request)


# ============================================================
# 单例
# ============================================================

class SSRFGuard:
    """SSRF 防护门面（单例）。"""

    def __init__(self):
        self._blocked_count: int = 0
        self._passed_count: int = 0

    def check(self, url: str, allow_private: bool = False) -> SSRFCheckResult:
        result = validate_url(url, allow_private=allow_private)
        if result.safe:
            self._passed_count += 1
        else:
            self._blocked_count += 1
        return result

    def add_allowlist(self, hostname: str) -> None:
        add_allowlist_host(hostname)

    def get_stats(self) -> dict:
        return {
            "blocked": self._blocked_count,
            "passed": self._passed_count,
            "allowlist": sorted(_ALLOWED_HOSTS),
            "dns_cache_size": len(_DNS_CACHE),
        }


ssrf_guard = SSRFGuard()
