"""引导系统测试"""
import pytest
from httpx import AsyncClient, ASGITransport


pytestmark = pytest.mark.asyncio


async def test_onboarding_status(client: AsyncClient):
    """测试引导状态查询"""
    resp = await client.get("/api/v1/onboarding/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    ob = data["data"]
    assert "completed" in ob
    assert ob["completed"] is False  # 默认未完成


async def test_onboarding_steps(client: AsyncClient):
    """测试引导步骤配置"""
    resp = await client.get("/api/v1/onboarding/steps")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    steps = data["data"]
    assert len(steps) >= 4  # 至少 4 步
    step_ids = [s["id"] for s in steps]
    assert "welcome" in step_ids
    assert "scene" in step_ids
    assert "model" in step_ids
    assert "create" in step_ids


async def test_onboarding_skip(client: AsyncClient):
    """测试跳过引导"""
    resp = await client.post("/api/v1/onboarding/skip")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    ob = data["data"]
    assert ob["completed"] is True
    assert ob["skipped"] is True


async def test_onboarding_step_scene(client: AsyncClient):
    """测试场景选择步骤"""
    resp = await client.post("/api/v1/onboarding/step", json={
        "step": "scene",
        "data": {"scene": "novel-writing"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["scene"] == "novel-writing"


async def test_onboarding_step_model(client: AsyncClient):
    """测试模型偏好步骤"""
    resp = await client.post("/api/v1/onboarding/step", json={
        "step": "model",
        "data": {"preference": "cloud-first"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["model_preference"] == "cloud-first"


async def test_onboarding_create_workspace(client: AsyncClient):
    """测试创建场景→创建步骤"""
    # 先设场景
    await client.post("/api/v1/onboarding/step", json={
        "step": "scene",
        "data": {"scene": "code-dev"},
    })
    # 设模型
    await client.post("/api/v1/onboarding/step", json={
        "step": "model",
        "data": {"preference": "auto"},
    })
    # 创建
    resp = await client.post("/api/v1/onboarding/step", json={
        "step": "create",
        "data": {},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "workspace_id" in data["data"]

    # 完成
    resp = await client.post("/api/v1/onboarding/step", json={
        "step": "done",
        "data": {},
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["completed"] is True


async def test_onboarding_reset(client: AsyncClient):
    """测试重置引导"""
    # 先跳过
    await client.post("/api/v1/onboarding/skip")
    # 再重置
    resp = await client.post("/api/v1/onboarding/reset")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["completed"] is False
