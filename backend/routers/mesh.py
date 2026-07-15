"""
太极网格 API 路由 — 算力三元暴露层

端点:
  GET  /api/v1/mesh/status         — 网格整体状态
  GET  /api/v1/mesh/peers          — 邻居节点列表
  GET  /api/v1/mesh/contributions  — 贡献摘要
  GET  /api/v1/mesh/resources      — 本机资源探测
  POST /api/v1/mesh/join           — 加入网格（开启算力贡献）
  POST /api/v1/mesh/leave          — 离开网格（关闭算力贡献）
  POST /api/v1/mesh/register-peer  — 手动注册邻居节点
  POST /api/v1/mesh/route          — 查询路由决策（不实际执行）
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/mesh", tags=["太极网格"])


# ============================================================
# 数据模型
# ============================================================

class RegisterPeerRequest(BaseModel):
    node_id: str
    hostname: str
    ip_address: str = ""
    port: int = 19527
    supported_models: list[str] = []


class RouteRequest(BaseModel):
    model_name: str = "deepseek-v4-pro"
    estimated_tokens: int = 1000
    priority: float = 0.5


# ============================================================
# 辅助函数
# ============================================================

def _get_mesh(request: Request):
    """从 app.state 获取太极网格实例。"""
    app_state = request.app.state
    if hasattr(app_state, "taiji_mesh"):
        return app_state.taiji_mesh
    # fallback: 直接从模块获取
    from engine.taiji_mesh import taiji_mesh
    return taiji_mesh


# ============================================================
# 端点
# ============================================================

@router.get("/status")
async def mesh_status(request: Request):
    """网格整体状态——节点数、健康邻居、覆盖模型数。"""
    mesh = _get_mesh(request)
    return {
        "initialized": mesh.is_initialized,
        "contributing": mesh.contributing,
        "stats": mesh.get_mesh_stats() if mesh.is_initialized else {},
    }


@router.get("/peers")
async def list_peers(request: Request):
    """邻居节点列表——健康状态、资源、支持模型。"""
    mesh = _get_mesh(request)
    if not mesh.is_initialized:
        return {"peers": [], "message": "太极网格未初始化"}

    peers = []
    for node in mesh.peers.values():
        peers.append({
            "node_id": node.node_hash,
            "hostname": node.hostname,
            "ip": node.ip_address,
            "port": node.port,
            "status": node.status.value,
            "tier": node.resources.tier.value,
            "cpu_cores": node.resources.cpu_cores,
            "gpus": len(node.resources.gpus),
            "supported_models": node.resources.supported_models[:10],
            "last_heartbeat_ago": f"{node.last_heartbeat:.0f}" if node.last_heartbeat else "never",
            "healthy": node.is_healthy(),
        })

    return {
        "peers": peers,
        "total": len(peers),
        "healthy": sum(1 for p in peers if p["healthy"]),
        "contributing": mesh.contributing,
    }


@router.get("/contributions")
async def contribution_summary(request: Request):
    """本节点算力贡献摘要——积分、服务次数、等级。"""
    mesh = _get_mesh(request)
    if not mesh.is_initialized:
        return {"contributing": False, "message": "太极网格未初始化"}

    return mesh.get_contribution_summary()


@router.get("/resources")
async def local_resources(request: Request):
    """本机算力资源探测——GPU/CPU/内存/已拉取模型。"""
    mesh = _get_mesh(request)
    if not mesh.is_initialized:
        return {"message": "太极网格未初始化，资源信息不可用"}

    resources = mesh.self_node.resources
    return {
        "cpu": {
            "cores": resources.cpu_cores,
            "available_pct": f"{resources.cpu_available:.0%}",
        },
        "memory": {
            "total_mb": resources.memory_mb,
            "available_mb": resources.memory_available_mb,
        },
        "gpus": [
            {
                "name": g.name,
                "vram_mb": g.vram_mb,
                "available_mb": g.available_mb,
                "utilization": f"{g.utilization_pct:.0%}",
            }
            for g in resources.gpus
        ],
        "supported_models": resources.supported_models,
        "tier": resources.tier.value,
    }


@router.post("/join")
async def join_mesh(request: Request):
    """加入太极网格——开启算力贡献。"""
    mesh = _get_mesh(request)
    if not mesh.is_initialized:
        await mesh.init(contributing=True)
    else:
        # 已在运行，切换状态
        from engine.taiji_mesh import MeshPrivacyLevel
        await mesh.init(contributing=True, privacy=MeshPrivacyLevel.STRICT)

    return {
        "status": "joined",
        "node_id": mesh.self_node.node_hash,
        "resources": {
            "tier": mesh.self_node.resources.tier.value,
            "gpus": len(mesh.self_node.resources.gpus),
            "cpu_cores": mesh.self_node.resources.cpu_cores,
        },
    }


@router.post("/leave")
async def leave_mesh(request: Request):
    """离开太极网格——关闭算力贡献。"""
    mesh = _get_mesh(request)
    if mesh.is_initialized:
        await mesh.drain()

    return {"status": "left", "node_id": mesh.self_node.node_hash}


@router.post("/register-peer")
async def register_peer(request: Request, body: RegisterPeerRequest):
    """手动注册邻居节点——用于 POC 阶段的手动组网。

    生产环境 v2.0 将替换为 mDNS 自动发现。
    """
    mesh = _get_mesh(request)
    if not mesh.is_initialized:
        return {"error": "太极网格未初始化，请先调用 /api/v1/mesh/join"}

    from engine.taiji_mesh import MeshNode, NodeResources, NodeStatus, ResourceTier
    node = MeshNode(
        node_id=body.node_id,
        hostname=body.hostname,
        ip_address=body.ip_address,
        port=body.port,
        resources=NodeResources(
            supported_models=body.supported_models,
            tier=ResourceTier.MODERATE,
        ),
        status=NodeStatus.ONLINE,
    )
    mesh.register_peer(node)

    return {
        "status": "registered",
        "node_id": node.node_hash,
        "hostname": node.hostname,
    }


@router.post("/route")
async def query_route(request: Request, body: RouteRequest):
    """查询路由决策——不实际执行推理，仅返回推荐的算力层。

    用于前端展示"当前请求将走哪条路"。
    """
    mesh = _get_mesh(request)
    if not mesh.is_initialized:
        return {"chosen_layer": "cloud", "reason": "太极网格未初始化"}

    result = await mesh.route_inference(
        model_name=body.model_name,
        estimated_tokens=body.estimated_tokens,
        priority=body.priority,
    )

    return {
        "chosen_layer": result.chosen_layer,
        "model": result.model,
        "peer": result.node.hostname if result.node else None,
        "reason": result.reason,
        "estimated_latency_ms": result.estimated_latency_ms,
        "estimated_cost": result.estimated_cost,
    }
