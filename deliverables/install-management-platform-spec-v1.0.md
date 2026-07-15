# 超级牛马管理平台 — 产品方案 v1.0

> 状态：方案设计 | 日期：2026-07-15
>
> 定义超级牛马安装包产品的账号体系、激活码管理、付费订阅、网络后台（管理端）。
> 客户端通过轻量 HTTP 协议与管理平台通信，管理平台提供 Web 后台供运营使用。

---

## 目录

1. [产品定位与架构](#1-产品定位与架构)
2. [账号体系](#2-账号体系)
3. [激活码系统](#3-激活码系统)
4. [付费订阅](#4-付费订阅)
5. [客户端上报通道](#5-客户端上报通道)
6. [管理后台 Web](#6-管理后台-web)
7. [管理平台 API](#7-管理平台-api)
8. [数据库设计](#8-数据库设计)
9. [技术选型](#9-技术选型)
10. [分阶段实施计划](#10-分阶段实施计划)

---

## 1. 产品定位与架构

### 1.1 设计目标

**管理平台是超级牛马安装包产品的运营基础设施**。没有它，安装包发出去就是"盲盒"——不知道谁在用、用得怎么样、有没有崩溃。

| 目标 | 衡量标准 |
|------|---------|
| 版本可控 | 客户端主动检查更新，后台灰度发布 |
| 收入闭环 | 激活码 → 订阅 → 续费，全链路可追踪 |
| 质量可见 | 崩溃率、日活、模型下载量实时掌握 |
| 用户可触达 | 紧急问题可推送通知到客户端 |

### 1.2 系统架构

```
┌─────────────────────────────────────────────────────┐
│                   超级牛马客户端                      │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ 激活码验证 │  │ 自动更新  │  │ 匿名统计/崩溃上报 │  │
│  └─────┬─────┘  └─────┬─────┘  └────────┬─────────┘  │
│        │              │                │             │
└────────┼──────────────┼────────────────┼─────────────┘
         │              │                │
         ▼              ▼                ▼
┌─────────────────────────────────────────────────────┐
│               管理平台 API (api.niuma.io)             │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ 账号服务  │  │ 许可服务  │  │ 遥测服务          │  │
│  │ (登录/JWT)│  │ (激活码)  │  │ (统计/崩溃/版本)  │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │              PostgreSQL 数据库                 │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│              管理后台 Web (admin.niuma.io)            │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ 用户管理  │  │ 激活码管理 │  │ 数据看板          │  │
│  │           │  │ (批量生成) │  │ (DAU/崩溃率/下载) │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ 版本管理  │  │ 订阅管理  │  │ 运营通知          │  │
│  │ (灰度发布) │  │ (套餐配置) │  │ (推送)           │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 1.3 Non-goals（v1.0 不做）

- 不做社交功能（好友、分享、评论）
- 不做支付网关（对接第三方：微信支付/支付宝/Stripe）
- 不做内容审核（客户端是本地 AI 工具，无 UGC）
- 不做模型托管（模型从 HuggingFace 下载，管理平台不下发模型）
- 不做 SaaS 多租户（v1.0 单租户，v2.0 考虑企业版多租户）

---

## 2. 账号体系

### 2.1 用户故事

| 角色 | 故事 |
|------|------|
| 新用户 | 打开软件 → 输入邮箱注册 → 输入激活码 → 开始使用 |
| 老用户 | 打开软件 → 静默获取设备凭证 → 无感使用 |
| 付费用户 | 订阅到期前 7 天收到提醒 → 续费 → 权益延续 |

### 2.2 账号模型

```
User
  ├── id            (UUID)
  ├── email         (登录凭证)
  ├── password_hash (bcrypt)
  ├── nickname
  ├── avatar_url
  ├── phone         (可选，找回密码用)
  ├── plan          (free | pro | enterprise)
  ├── plan_expires_at
  ├── created_at
  └── devices[]     → 关联设备列表

Device
  ├── id            (UUID)
  ├── user_id       → User
  ├── device_name   (自动获取: "DESKTOP-XXX")
  ├── device_id     (客户端生成: 硬件指纹哈希)
  ├── platform      (windows | macos | linux)
  ├── last_ping_at
  └── created_at

Subscription
  ├── id
  ├── user_id       → User
  ├── plan           (pro_monthly | pro_yearly | enterprise)
  ├── status         (active | expired | cancelled)
  ├── started_at
  ├── expires_at
  ├── auto_renew
  └── payment_method (wechat | alipay | stripe)
```

### 2.3 注册流程

```
[客户端]                          [管理平台]
   │                                  │
   │ POST /auth/send-code             │
   │ { email }                        │
   │ ──────────────────────────────►  │
   │                                  │ 生成 6 位验证码 (5分钟有效)
   │                                  │ 发送邮件
   │ ◄──────────────────────────────  │
   │ { ok: true }                     │
   │                                  │
   │ POST /auth/register              │
   │ { email, code, password,         │
   │   invite_code }                  │
   │ ──────────────────────────────►  │
   │                                  │ 验证邮箱 + 激活码
   │                                  │ 创建用户 → 绑定设备
   │ ◄──────────────────────────────  │
   │ { token, user, device }          │
   │                                  │
   │ [客户端存储 token 到本地]        │
```

### 2.4 登录流程

```
[客户端]                          [管理平台]
   │                                  │
   │ POST /auth/login                 │
   │ { email, password }              │
   │ ──────────────────────────────►  │
   │                                  │ 验证 → JWT (7天有效)
   │ ◄──────────────────────────────  │
   │ { token, user }                  │
   │                                  │
   │ [后续请求带 Authorization 头]    │
```

### 2.5 设备管理

```
客户端首次激活:
  1. 生成设备指纹: SHA256(CPU序列号 + 主板序列号 + 系统 UUID)
  2. 上报: POST /devices/register { device_id, device_name, platform }
  3. 后台检测:
     - 已有设备数 < 允许上限 → 注册成功
     - 超限 → 提示"已达到设备上限，请先在管理后台解绑旧设备"

设备上限:
  Free:   1 台
  Pro:    3 台
  Enterprise: 10 台
```

---

## 3. 激活码系统

### 3.1 激活码格式

```
格式: NIUA-XXXX-XXXX-XXXX
      4 段，每段 4 位大写字母数字，破折号分隔
      例: NIUA-A3F7-K9M2-Q5W8

生成规则:
  NIUA-{4位随机}-{4位随机}-{4位校验}
  校验码 = CRC16(NIUA+中间8位) % 46656 的 base36 表示

容量: 36^8 ≈ 2.8 万亿个
      去掉脏话/歧义字符 (0/O/1/I/L) 后 ≈ 1.1 万亿个
```

### 3.2 激活码模型

```
InviteCode
  ├── id
  ├── code              (NIUA-XXXX-XXXX-XXXX)
  ├── type              (free_trial | pro_3month | pro_yearly | enterprise)
  ├── batch_id           (批量生成时关联批次)
  ├── status             (unused | used | revoked)
  ├── used_by            → User (谁用了)
  ├── used_at
  ├── expires_at         (激活码本身的有效期)
  ├── plan_duration_days (激活后获得的天数)
  ├── max_uses           (同一个码能用几次，默认 1)
  ├── created_by          (管理员谁生成的)
  └── created_at

InviteBatch
  ├── id
  ├── batch_name         (例: "2026-07 发布会福利码")
  ├── code_type
  ├── count              (生成数量)
  ├── created_by
  └── created_at
```

### 3.3 管理后台操作

```
操作列表:
  ├── 批量生成: 输入数量 → 一键生成 → 导出 CSV
  ├── 单独生成: 自定义套餐/时长
  ├── 查看状态: 按批次/状态/时间筛选
  ├── 批量禁用: 选择批次 → 全部标记 revoked
  ├── 统计分析:
  │   总生成 / 已使用 / 未使用 / 已过期
  │   按批次查看转化率
  │   按渠道追踪 (给不同 KOL 不同批次)
  └── 导出: CSV / Excel
```

### 3.4 激活码渠道追踪

```
每个 InviteBatch 可标记 channel:
  channel: "bilibili-刘淮安" | "公众号-BBGTALK" | "知乎广告" | "线下活动-2026CCF"

统计维度:
  - 各渠道激活码发放量
  - 各渠道激活率
  - 各渠道留存率 (7日/30日)
  - 各渠道付费转化率
```

---

## 4. 付费订阅

### 4.1 套餐设计

| 套餐 | 价格（参考） | 核心权益 |
|------|:-----:|------|
| **Free** | 免费 | 本地 1 个模型, 1 设备, 社区支持 |
| **Pro 月付** | ¥29/月 | 本地 3 模型, 3 设备, 云端 DeepSeek 可用, 优先更新 |
| **Pro 年付** | ¥199/年 (¥16.6/月) | 同上 + 额外 2 个月 |
| **Enterprise** | ¥99/月 | 10 设备, 所有模型, API 接入, 工单支持 |

### 4.2 权益设计

```
权益对比:

                         Free      Pro       Enterprise
本地模型数量               1         3         无限
可同时激活设备             1         3         10
云端模型 (DeepSeek)       ✗         ✓         ✓
API 接口                   ✗         ✗         ✓
优先版本更新               ✗         ✓         ✓
批量激活码                 ✗         ✗         ✓
邮件/工单支持              ✗         邮件       专属
```

### 4.3 订阅生命周期

```
[未激活] → 输入激活码 → [Free 试用]
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
               [付费订阅]           [试用到期]
                    │                    │
            ┌───────┴───────┐    [功能降级为 Free]
            ▼               ▼
      [自动续费成功]   [续费失败/取消]
            │               │
      [订阅延续]      [到期后降级]
```

### 4.4 支付对接

```
v1.0 对接:
  - 微信支付 JSAPI (国内)
  - 支付宝 (国内)
  - Stripe (海外)

客户端 → 管理平台 → 支付网关 → 回调 → 更新订阅状态

简化方案 (v1.0 首发):
  - 先用激活码模式发布
  - 支付放在管理后台 Web 端 (电脑浏览器扫码支付)
  - 客户端不做支付 UI，只做"购买"→ 打开浏览器 → 管理平台支付页
```

---

## 5. 客户端上报通道

### 5.1 上报类型

| 类型 | 频率 | 数据量 | 说明 |
|------|:--:|------|------|
| **心跳 (Ping)** | 启动时 + 每 6 小时 | ~200B | 版本号、OS、在线状态 |
| **事件 (Event)** | 实时 | ~500B/条 | 激活成功、首次对话、下载模型 |
| **统计摘要** | 每天 1 次 | ~2KB | 对话次数、模型使用、功能使用频次 |
| **崩溃上报** | 崩溃时 | ~5KB | 堆栈、OS 信息、后端日志摘要 |
| **版本检查** | 启动时 + 每 12 小时 | ~200B | 当前版本、请求更新信息 |

### 5.2 通信协议

```
Base URL: https://api.niuma.io/v1

认证: Authorization: Bearer <device_token>
      (设备激活后获得，存储在本地)

请求格式: JSON
响应格式: { "success": bool, "data": {...}, "meta": { "request_id": "..." } }
```

### 5.3 客户端 API

```
POST /ping
  → { version, platform, os_version, device_id }
  ← { server_time, latest_version, update_available, messages }
  功能: 心跳 + 版本检查 + 服务端消息推送

POST /events
  → { events: [{ type, timestamp, data }] }
  功能: 批量上报事件
  类型: activation_success | first_chat | model_downloaded | subscription_changed

POST /stats/daily
  → { date, chat_count, model_usage: { qwen3-8b: 120, ... }, feature_usage: {...} }
  功能: 每日匿名统计摘要

POST /crash
  → { version, stack_trace, os_info, backend_log_snippet, device_id }
  功能: 崩溃上报

GET /version/check
  → ?current=1.5.0&platform=win32
  ← { latest: "1.5.1", required: false, download_url, changelog, size_mb }
  功能: 检查更新

GET /notice
  → { notices: [{ id, title, content, level, expires_at }] }
  功能: 拉取服务端通知
```

### 5.4 隐私合规

```
客户端上报遵循最小化原则:
  ✓ 上报: 版本号、OS 类型、功能使用计数、崩溃堆栈（脱敏）
  ✗ 不上报: 对话内容、文件名、个人身份信息、IP 地址精确值
  - 设备指纹只做哈希，不上报原始硬件序列号
  - 统计数据聚合再上报（非每条记录）
  - 崩溃堆栈自动过滤文件路径中的用户名
  - 用户可在设置中关闭统计上报 (GDPR/个保法合规)
```

---

## 6. 管理后台 Web

### 6.1 功能模块

```
admin.niuma.io
  │
  ├── 📊 数据看板 (Dashboard)
  │   ├── 日活用户 (DAU) 趋势图
  │   ├── 新增激活 (按日/周/月)
  │   ├── 模型下载量 Top 5
  │   ├── 崩溃率 (24h)
  │   ├── 订阅收入趋势
  │   └── 渠道转化漏斗
  │
  ├── 👥 用户管理
  │   ├── 用户列表 (搜索/筛选/排序)
  │   ├── 用户详情 (设备列表/订阅状态/激活码来源)
  │   ├── 手动封禁/解封
  │   └── 导出用户数据
  │
  ├── 🎫 激活码管理
  │   ├── 批量生成 (选择套餐/数量/渠道/有效期)
  │   ├── 批次列表 (按渠道/时间筛选)
  │   ├── 批次详情 (使用率/激活用户)
  │   ├── 单独生成/禁用
  │   └── 导出 CSV
  │
  ├── 💰 订阅管理
  │   ├── 套餐配置 (价格/权益/上下架)
  │   ├── 订阅订单列表
  │   ├── 退款处理
  │   └── 收入报表
  │
  ├── 📦 版本管理
  │   ├── 发布新版本 (上传安装包/填写更新日志)
  │   ├── 灰度发布 (按 % 比例逐步推送)
  │   ├── 强制更新标记
  │   ├── 版本历史
  │   └── 更新率统计
  │
  ├── 💥 崩溃监控
  │   ├── 崩溃趋势图
  │   ├── 崩溃详情 (堆栈/版本/OS 分布)
  │   ├── 按版本筛选
  │   └── 标记已修复
  │
  ├── 📢 运营通知
  │   ├── 新建通知 (标题/内容/级别/过期时间)
  │   ├── 推送范围 (全部/按版本/按套餐)
  │   └── 通知历史
  │
  └── ⚙️ 系统设置
      ├── 管理员账号管理
      ├── 操作日志
      └── API 访问密钥管理
```

### 6.2 看板指标定义

| 指标 | 计算方式 | 用途 |
|------|---------|------|
| DAU | 去重 device_id 每日 ping | 衡量活跃度 |
| 激活数 | 每日新增 used 激活码 | 增长速率 |
| 激活率 | used / 生成总量 | 渠道质量 |
| 崩溃率 | 崩溃设备数 / 活跃设备数 | 版本质量 |
| 7 日留存 | 激活后第 7 天仍在 ping | 产品粘性 |
| 模型下载量 | 按模型 ID 聚合 | 用户偏好 |
| MRR | 月经常性收入 | 商业健康度 |

---

## 7. 管理平台 API

### 7.1 公开 API（客户端调用，无需用户登录）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/auth/send-code` | 发送邮箱验证码 |
| POST | `/v1/auth/register` | 注册 + 激活码验证 |
| POST | `/v1/auth/login` | 邮箱密码登录 |
| POST | `/v1/auth/refresh` | 刷新 JWT |
| POST | `/v1/devices/ping` | 心跳 + 版本检查 |
| POST | `/v1/devices/events` | 批量事件上报 |
| POST | `/v1/devices/stats/daily` | 每日统计摘要 |
| POST | `/v1/devices/crash` | 崩溃上报 |
| GET | `/v1/version/check` | 检查更新 |
| GET | `/v1/notice` | 拉取公告 |

### 7.2 认证 API（需用户 JWT）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/v1/user/profile` | 用户信息 |
| PUT | `/v1/user/profile` | 更新信息 |
| GET | `/v1/user/devices` | 设备列表 |
| DELETE | `/v1/user/devices/:id` | 解绑设备 |
| GET | `/v1/user/subscription` | 订阅状态 |
| POST | `/v1/user/subscription/create` | 创建订阅订单 |
| POST | `/v1/user/subscription/cancel` | 取消自动续费 |

### 7.3 管理 API（需管理员 JWT，管理后台调用）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/v1/admin/dashboard` | 看板数据 |
| GET/POST | `/v1/admin/users` | 用户列表/搜索 |
| PUT | `/v1/admin/users/:id` | 封禁/解封 |
| POST | `/v1/admin/codes/generate` | 批量生成激活码 |
| GET | `/v1/admin/codes` | 激活码列表 |
| GET | `/v1/admin/codes/batches` | 批次列表 |
| PUT | `/v1/admin/codes/:id/revoke` | 禁用激活码 |
| POST | `/v1/admin/versions` | 发布新版本 |
| PUT | `/v1/admin/versions/:id/rollout` | 灰度比例调整 |
| GET | `/v1/admin/crashes` | 崩溃列表 |
| POST | `/v1/admin/notices` | 新建通知 |
| GET/PUT | `/v1/admin/plans` | 套餐配置 |

---

## 8. 数据库设计

### 8.1 核心表

```sql
-- 用户
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(100),
    avatar_url TEXT,
    phone VARCHAR(20),
    plan VARCHAR(20) DEFAULT 'free',       -- free | pro_monthly | pro_yearly | enterprise
    plan_expires_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',    -- active | banned | deleted
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 设备
CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    device_id_hash VARCHAR(64) UNIQUE NOT NULL,  -- SHA256(硬件指纹)
    device_name VARCHAR(200),
    platform VARCHAR(20),                        -- windows | macos | linux
    app_version VARCHAR(20),
    last_ping_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 激活码
CREATE TABLE invite_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(30) UNIQUE NOT NULL,            -- NIUA-XXXX-XXXX-XXXX
    type VARCHAR(30) NOT NULL,                   -- free_trial | pro_3month | pro_yearly | enterprise
    batch_id UUID REFERENCES invite_batches(id),
    status VARCHAR(20) DEFAULT 'unused',          -- unused | used | revoked
    used_by UUID REFERENCES users(id),
    used_at TIMESTAMP,
    expires_at TIMESTAMP,                         -- 激活码本身过期时间
    plan_duration_days INT DEFAULT 30,
    max_uses INT DEFAULT 1,
    current_uses INT DEFAULT 0,
    created_by UUID REFERENCES admins(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 激活码批次
CREATE TABLE invite_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_name VARCHAR(200),
    code_type VARCHAR(30),
    count INT,
    channel VARCHAR(100),                         -- bilibili | wechat | zhihu | ...
    created_by UUID REFERENCES admins(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 订阅
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    plan VARCHAR(30) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',          -- active | expired | cancelled
    started_at TIMESTAMP,
    expires_at TIMESTAMP,
    auto_renew BOOLEAN DEFAULT FALSE,
    payment_method VARCHAR(20),
    payment_txn_id VARCHAR(100),
    amount_cents INT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 崩溃报告
CREATE TABLE crash_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id_hash VARCHAR(64),
    app_version VARCHAR(20),
    platform VARCHAR(20),
    os_version VARCHAR(50),
    stack_trace TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 版本发布
CREATE TABLE app_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(20) UNIQUE NOT NULL,          -- 1.5.1
    platform VARCHAR(20),
    download_url TEXT,
    changelog TEXT,
    size_mb FLOAT,
    required BOOLEAN DEFAULT FALSE,                -- 强制更新
    rollout_percent INT DEFAULT 100,              -- 灰度比例
    status VARCHAR(20) DEFAULT 'draft',           -- draft | published | deprecated
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 每日统计
CREATE TABLE daily_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    dau INT DEFAULT 0,
    new_activations INT DEFAULT 0,
    chat_count INT DEFAULT 0,
    model_downloads INT DEFAULT 0,
    crash_count INT DEFAULT 0,
    mrr_cents INT DEFAULT 0,
    payload JSONB,                                 -- 详细维度数据
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date)
);

-- 管理员
CREATE TABLE admins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'admin',             -- admin | super_admin
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 9. 技术选型

### 9.1 管理平台后端

| 层 | 选型 | 理由 |
|------|------|------|
| 语言 | **Go** (推荐) 或 Node.js | 高性能、部署简单、单二进制文件 |
| 框架 | Gin (Go) 或 Fastify (Node) | 轻量 REST API |
| 数据库 | **PostgreSQL 15+** | 事务、JSONB、成熟生态 |
| 缓存 | Redis | Session、验证码 TTL、限流 |
| 对象存储 | S3 兼容 (阿里云 OSS / Cloudflare R2) | 安装包文件托管 |
| 邮件 | Resend / 阿里云邮件推送 | 验证码 + 通知邮件 |
| 部署 | Docker + 阿里云 ECS / Railway | 简单运维 |

### 9.2 管理后台前端

| 层 | 选型 | 理由 |
|------|------|------|
| 框架 | **Vue 3 + Vite**（与主项目统一） | 无需学习新框架 |
| UI 库 | Element Plus 或 Naive UI | 后台管理成熟组件 |
| 图表 | ECharts | 看板数据可视化 |
| 部署 | Nginx 静态托管 + CDN | |

### 9.3 预算估算（月）

| 项目 | 规格 | 月费（参考） |
|------|------|:----:|
| 云服务器 | 2C4G ECS | ¥100 |
| PostgreSQL | 50GB 云数据库 | ¥150 |
| Redis | 1GB | ¥50 |
| 对象存储 + CDN | 100GB 存储 + 流量 | ¥50 |
| 邮件服务 | 1 万封/月 | ¥30 |
| 域名 + SSL | niuma.io | ¥10 |
| **合计** | | **~¥390/月** |

初期 DAU < 1000 时，一台 2C4G 足够。

---

## 10. 分阶段实施计划

### Phase 0: 激活码 + 版本更新 (P0, ~5d)

```
目标: 安装包能卖、能更新

后端:
  - 激活码 CRUD + 批量生成
  - 版本发布 + 更新检查 API

客户端:
  - 激活码输入页面 (OnboardingView 加一步)
  - 启动时版本检查 (GET /version/check)
  - 静默下载更新包 (WinSparkle 集成)

管理后台:
  - 激活码管理页面
  - 版本管理页面
```

### Phase 1: 账号 + 基础统计 (P0, ~7d)

```
目标: 知道谁在用

后端:
  - 注册/登录 (邮箱 + JWT)
  - 设备管理
  - 心跳上报 + 每日统计聚合

客户端:
  - 登录页 (OnboardingView 整合)
  - 心跳定时上报

管理后台:
  - 用户列表
  - 基础看板 (DAU + 激活数)
```

### Phase 2: 付费订阅 (P1, ~5d)

```
目标: 收入闭环

后端:
  - 套餐配置
  - 支付集成 (微信/支付宝)
  - 订阅状态管理 + 自动续费

管理后台:
  - 套餐管理页面
  - 订单列表 + 收入报表
```

### Phase 3: 完整运营 (P1, ~4d)

```
目标: 数据驱动运营

后端:
  - 崩溃聚类分析
  - 渠道转化追踪
  - 运营通知推送

管理后台:
  - 崩溃监控页面
  - 渠道分析漏斗
  - 通知管理页面
  - 完整数据看板
```

### 工作量汇总

| Phase | 内容 | 估时 |
|:-----:|------|:----:|
| 0 | 激活码 + 版本更新 | 5d |
| 1 | 账号 + 基础统计 | 7d |
| 2 | 付费订阅 | 5d |
| 3 | 完整运营 | 4d |
| | **合计** | **21d** |

---

## 附录 A：与竞品对标

| 能力 | Cursor | 超级牛马 | Jan.ai | LM Studio |
|------|:--:|:--:|:--:|:--:|
| 账号体系 | ✓ (强制登录) | Phase 1 可选 | ✗ | ✗ |
| 激活码/付费 | ✓ 订阅制 | Phase 0-2 | ✗ (开源) | ✗ |
| 自动更新 | ✓ 内置 | Phase 0 | ✗ | ✓ |
| 版本灰度 | ✓ | Phase 0 | ✗ | ✗ |
| 崩溃上报 | ✓ | Phase 3 | ✗ | ✗ |
| 管理后台 | (内部) | 自建 | ✗ | ✗ |
| 本地优先 | 否 | **是** | 是 | 是 |

**差异化**: 我们卖的是"本地 AI + 隐私优先"，不是"云端 SaaS"。账号体系是可选的，不强制登录也能用本地模型。

---

## 附录 B：已对齐的客户端改动点

与当前 Super Niuma 代码库的集成计划：

| 现有代码 | 改动 |
|---------|------|
| `license` router | 改为对接管理平台激活码验证 API |
| `api_keys` router | 改为管理平台管理的 token 模式 |
| `launcher.py` | 启动时加入版本检查 + 静默更新 |
| `OnboardingView.vue` | +激活码输入步骤 + 注册登录步骤 |
| `settings.json` | +device_token, +stats_opt_out |
| `main.py` lifespan | +心跳上报任务 + 每日统计上报 |

---

> **文档维护**: 随管理平台开发进度更新。
>
> **变更日志**:
> - 2026-07-15 v1.0 — 初版，账号体系 + 激活码 + 付费订阅 + 管理后台完整方案
