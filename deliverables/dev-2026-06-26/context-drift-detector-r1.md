# 上下文漂移检测模块 — v1.0 开发报告

> **日期**: 2026-06-26 18:33
> **动机**: 研究显示65%企业Agent失败源于上下文漂移（2%早期偏差→40%末段失败率）
> **文件**: `backend/engine/context_drift.py` (新模块) + `routers/drift.py` (API路由)

## 架构

```
Intent Anchor (session启动时记录)
    ↓
用户消息缓存 (最近20条)
    ↓ 每5条消息触发检测
Drift Detection
    ├── Term Drift (35%) — 关键词重叠度
    ├── Task Drift (40%) — 任务类型一致性
    └── Scope Drift (25%) — 话题范围蔓延
    ↓
DriftReport → severity: green/yellow/red/critical
    ↓
GoalLoop规则建议 + EmergenceEngine事件
```

## API端点

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/v1/drift/record-intent` | 记录意图锚点 |
| POST | `/api/v1/drift/check` | 显式触发漂移检测 |
| POST | `/api/v1/drift/reaffirm` | 用户确认意图重置 |
| GET | `/api/v1/drift/status` | 检测器全局状态 |
| GET | `/api/v1/drift/session/{id}` | 某会话的漂移历史 |
| GET | `/api/v1/drift/summary` | 所有活跃会话摘要 |

## 集成链路

```
chat_hooks.post_chat_record()
  → context_drift.record_message()
    → 每5条消息自动检测
      → 黄色 alert: 记录日志
      → 红色 alert: 通知 EmergenceEngine 生成跨模块事件
```

## 验证结果

- 同话题消息: drift=0.55 (yellow) — 关键词自然演替
- 话题切换: drift=0.60 (red) — 正确识别任务漂移
- 意图重确认: 重置锚点，清除漂移历史

## 后续优化

1. **P1**: 集成语义向量相似度（替代关键词重叠）
2. **P1**: 漂移发生时自动创建GoalLoop建议规则
3. **P2**: 漂移回滚（回到漂移前的检查点）
4. **P2**: 前端漂移告警UI（Dashboard Tab嵌入）
