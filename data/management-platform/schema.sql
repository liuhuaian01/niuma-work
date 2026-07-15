-- ============================================================
-- Super Niuma 管理平台 — PostgreSQL 数据库初始化
-- Phase 0: 激活码 + 版本管理
-- ============================================================

-- 管理员
CREATE TABLE IF NOT EXISTS admins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'admin',
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 激活码批次
CREATE TABLE IF NOT EXISTS invite_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_name VARCHAR(200) NOT NULL,
    code_type VARCHAR(30) NOT NULL,
    count INT NOT NULL,
    channel VARCHAR(100),
    created_by UUID REFERENCES admins(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 激活码
CREATE TABLE IF NOT EXISTS invite_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(30) UNIQUE NOT NULL,
    type VARCHAR(30) NOT NULL,
    batch_id UUID REFERENCES invite_batches(id),
    status VARCHAR(20) DEFAULT 'unused',
    used_by VARCHAR(255),
    used_at TIMESTAMP,
    expires_at TIMESTAMP,
    plan_duration_days INT DEFAULT 30,
    max_uses INT DEFAULT 1,
    current_uses INT DEFAULT 0,
    created_by UUID REFERENCES admins(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_invite_codes_code ON invite_codes(code);
CREATE INDEX idx_invite_codes_status ON invite_codes(status);
CREATE INDEX idx_invite_codes_batch ON invite_codes(batch_id);

-- 用户
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    nickname VARCHAR(100),
    plan VARCHAR(20) DEFAULT 'free',
    plan_expires_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    invite_code VARCHAR(30) REFERENCES invite_codes(code),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

-- 设备
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    device_id_hash VARCHAR(64) UNIQUE NOT NULL,
    device_name VARCHAR(200),
    platform VARCHAR(20),
    app_version VARCHAR(20),
    last_ping_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_devices_user ON devices(user_id);
CREATE INDEX idx_devices_ping ON devices(last_ping_at);

-- 应用版本
CREATE TABLE IF NOT EXISTS app_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(20) UNIQUE NOT NULL,
    platform VARCHAR(20) DEFAULT 'win32',
    download_url TEXT NOT NULL,
    changelog TEXT,
    size_mb FLOAT,
    required BOOLEAN DEFAULT FALSE,
    rollout_percent INT DEFAULT 100,
    status VARCHAR(20) DEFAULT 'draft',
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_versions_platform ON app_versions(platform, status);

-- 统计 (每日聚合)
CREATE TABLE IF NOT EXISTS daily_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL UNIQUE,
    dau INT DEFAULT 0,
    new_activations INT DEFAULT 0,
    ping_count INT DEFAULT 0,
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 管理端操作日志
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID REFERENCES admins(id),
    action VARCHAR(100),
    target_type VARCHAR(50),
    target_id VARCHAR(255),
    detail JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 默认管理员 (密码: admin123, bcrypt hash)
INSERT INTO admins (email, password_hash, role)
VALUES ('admin@niuma.io', '$2b$12$LJ3m4ys3GZfnYMz8kVsHDOlqJ6VYbUzMQXfHqE1jq5KwWN5VFZo3G', 'super_admin')
ON CONFLICT (email) DO NOTHING;
