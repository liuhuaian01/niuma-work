"""
API 路由烟雾测试 — 验证所有路由可访问
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "SUCCESS"
        assert "status" in data["data"]


@pytest.mark.asyncio
async def test_capabilities_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/capabilities/status")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_capabilities_toggle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/capabilities/toggle", json={"capability": "fetch", "enabled": True})
        assert resp.status_code == 200
        resp2 = await client.post("/api/v1/capabilities/reset")


@pytest.mark.asyncio
async def test_governance_web_access():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/web-access/request", json={"capability": "search", "reason": "test"})
        assert resp.status_code == 200
        await client.post("/api/v1/web-access/close")


@pytest.mark.asyncio
async def test_budget_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/budget/test-agent")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_consciousness_today():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/consciousness/today")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_workspaces_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/workspaces")
        assert resp.status_code == 200


if __name__ == "__main__":
    pytest.main(["-v", __file__])
