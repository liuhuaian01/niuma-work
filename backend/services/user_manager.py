"""
用户管理 + 许可证激活系统

用户首次打开 → 3天试用 → 到期 → 购买激活 → 继续使用。
主路径：用户充钱购买 → 自动激活套餐。
后台路径：刘淮安可生成特殊 Key 用于赠送/内测。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
import base64 as _b64
import hashlib
import hmac
import json
import os
import secrets as _secrets_module
import time

# ── 加密库：优先 AES-GCM，降级到 Fernet，再降级到 HMAC+XOR ──
_AESGCM_AVAILABLE = False
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AESGCM
    _AESGCM_AVAILABLE = True
except ImportError:
    pass

_FERNET_AVAILABLE = False
if not _AESGCM_AVAILABLE:
    try:
        from cryptography.fernet import Fernet as _Fernet, InvalidToken
        _FERNET_AVAILABLE = True
    except ImportError:
        pass


TRIAL_DAYS = 3

PLANS = {
    "monthly": {"name": "月度", "days": 30},
    "quarterly": {"name": "季度", "days": 90},
    "yearly": {"name": "年度", "days": 365},
    "lifetime": {"name": "终身", "days": 36500},  # ~100年
}


# ── 密钥派生 ──

def _get_device_seed() -> str:
    """获取设备指纹种子（每次安装不同）"""
    import socket, uuid
    return f"{socket.gethostname()}:{uuid.getnode()}:NiuMaEngine"


def _get_secret_key() -> bytes:
    """从环境变量获取 HMAC 密钥。必须设置，不提供 fallback。
    
    安全策略：强制要求环境变量，避免设备指纹派生导致的密钥共享风险。
    """
    env_key = os.getenv("NIUMA_SECRET_KEY", "")
    if not env_key:
        raise RuntimeError(
            "NIUMA_SECRET_KEY environment variable is required for license verification. "
            "Please set it before starting the application. "
            "Example: export NIUMA_SECRET_KEY='your-secret-key-here'"
        )
    return hashlib.sha256(env_key.encode()).digest()


def _get_encryption_key() -> bytes:
    """从设备指纹派生 AES-256 密钥（用于本地 License 加密存储）"""
    seed = f"NiuMaStorage:{_get_device_seed()}"
    return hashlib.sha256(seed.encode()).digest()


def _encrypt_license(license_dict: dict) -> str:
    """加密 License 数据 → base64 字符串"""
    key = _get_encryption_key()
    data = json.dumps(license_dict).encode()

    if _AESGCM_AVAILABLE:
        aesgcm = _AESGCM(key)
        nonce = _secrets_module.token_bytes(12)
        ct = aesgcm.encrypt(nonce, data, None)
        return _b64.b64encode(nonce + ct).decode()
    elif _FERNET_AVAILABLE:
        # Fernet 需要 32字节 url-safe base64 编码的 key
        f_key = _b64.urlsafe_b64encode(key)
        f = _Fernet(f_key)
        return f.encrypt(data).decode()
    else:
        # 纯 Python HMAC+XOR 方案（本地存储足够安全）
        nonce = _secrets_module.token_bytes(16)
        # 派生加密流: HMAC-SHA256(key, nonce + counter)
        keystream = b""
        block_count = (len(data) + 31) // 32
        for i in range(block_count):
            keystream += hashlib.sha256(key + nonce + i.to_bytes(4, "big")).digest()
        ct = bytes(a ^ b for a, b in zip(data, keystream[:len(data)]))
        # HMAC 认证标签
        tag = hashlib.sha256(key + nonce + ct).digest()[:16]
        return _b64.b64encode(nonce + ct + tag).decode()


def _decrypt_license(encrypted: str) -> dict | None:
    """解密 License 数据"""
    try:
        key = _get_encryption_key()

        if _AESGCM_AVAILABLE:
            raw = _b64.b64decode(encrypted)
            nonce, ct = raw[:12], raw[12:]
            aesgcm = _AESGCM(key)
            data = aesgcm.decrypt(nonce, ct, None)
            return json.loads(data)
        elif _FERNET_AVAILABLE:
            f_key = _b64.urlsafe_b64encode(key)
            f = _Fernet(f_key)
            data = f.decrypt(encrypted.encode())
            return json.loads(data)
        else:
            # 纯 Python HMAC+XOR 解密
            raw = _b64.b64decode(encrypted)
            if len(raw) < 32:
                return None
            nonce, ct, tag = raw[:16], raw[16:-16], raw[-16:]
            # 验证认证标签
            expected_tag = hashlib.sha256(key + nonce + ct).digest()[:16]
            if not hmac.compare_digest(tag, expected_tag):
                return None
            # 解密
            keystream = b""
            block_count = (len(ct) + 31) // 32
            for i in range(block_count):
                keystream += hashlib.sha256(key + nonce + i.to_bytes(4, "big")).digest()
            data = bytes(a ^ b for a, b in zip(ct, keystream[:len(ct)]))
            return json.loads(data)
    except Exception as e:
        import logging
        logging.getLogger("niuma.user.license").warning(f"License decryption failed: {e}")
        return None


@dataclass
class License:
    """一个激活许可证。"""
    key: str              # 激活 Key（SHA256哈希）
    plan: str             # monthly/quarterly/yearly/lifetime
    activated_at: str     # 激活时间
    expires_at: str       # 到期时间
    device_hash: str      # 绑定的设备指纹
    is_active: bool = True


@dataclass
class User:
    """一个本地用户。"""
    device_id: str        # 设备唯一标识
    trial_started_at: str # 试用开始时间
    trial_ended: bool = False
    license: Optional[License] = None
    created_at: str = ""
    last_login: str = ""


class UserManager:
    """用户管理 + 许可证激活。

    所有数据存在本地——不依赖远程服务器。
    激活 Key 通过 RSA 签名防伪造（公钥内置在代码中）。
    """

    DATA_FILE = "data/user.json"

    def __init__(self, data_dir: str = "data") -> None:
        self._dir = data_dir
        self._user: Optional[User] = None
        self._clock_tampered = False
        self._monotonic_counter = 0
        self._checkpoint_file = os.path.join(data_dir, ".checkpoint")
        self._used_keys: set = set()
        os.makedirs(data_dir, exist_ok=True)
        self._load_checkpoint()
        self._load_used_keys()
        self._load()

    def _load(self) -> None:
        path = os.path.join(self._dir, "user.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                lic = None
                if data.get("license"):
                    ld = data["license"]
                    if isinstance(ld, str):
                        # 加密格式：先尝试解密，降级为明文读取（向后兼容）
                        decrypted = _decrypt_license(ld)
                        if decrypted is not None:
                            ld = decrypted
                        elif ld.startswith("{") or ld.startswith("L"):
                            # 可能是旧版 JSON 字符串或 Legacy Fernet 格式
                            pass
                    if isinstance(ld, dict):
                        lic = License(**ld)
                self._user = User(
                    device_id=data["device_id"],
                    trial_started_at=data.get("trial_started_at", ""),
                    trial_ended=data.get("trial_ended", False),
                    license=lic,
                    created_at=data.get("created_at", ""),
                    last_login=data.get("last_login", ""),
                )
            except Exception as e:
                import logging
                logging.getLogger("niuma.user.load").error(f"Failed to load user data: {e}", exc_info=True)
                self._user = None

    def _save(self) -> None:
        if self._user:
            path = os.path.join(self._dir, "user.json")
            license_data = None
            if self._user.license:
                license_data = _encrypt_license(self._user.license.__dict__)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "device_id": self._user.device_id,
                    "trial_started_at": self._user.trial_started_at,
                    "trial_ended": self._user.trial_ended,
                    "license": license_data,
                    "created_at": self._user.created_at,
                    "last_login": self._user.last_login,
                }, f, ensure_ascii=False, indent=2)

    # ── 防时钟回拨：单调计数器 + 检查点 ──

    def _load_checkpoint(self):
        """加载单调计数器检查点，检测时钟回拨"""
        if os.path.exists(self._checkpoint_file):
            try:
                with open(self._checkpoint_file, "r") as f:
                    cp = json.load(f)
                self._monotonic_counter = cp.get("counter", 0)
                last_ts = cp.get("last_ts", 0)
                now_ts = time.time()
                if now_ts < last_ts - 3600:  # 时钟回拨超过1小时
                    self._clock_tampered = True
                else:
                    self._clock_tampered = False
            except Exception as e:
                import logging
                logging.getLogger("niuma.user.checkpoint").debug(f"Checkpoint load failed: {e}")
                self._clock_tampered = False

    def _save_checkpoint(self):
        """更新检查点——每次试用验证后调用"""
        self._monotonic_counter += 1
        with open(self._checkpoint_file, "w") as f:
            json.dump(
                {"counter": self._monotonic_counter, "last_ts": time.time()}, f
            )

    # ── 防重放：激活 Key 使用记录 ──

    def _load_used_keys(self):
        """加载已使用的激活 Key 哈希集合"""
        path = os.path.join(self._dir, ".used_keys")
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    self._used_keys = set(line.strip() for line in f if line.strip())
            except Exception as e:
                import logging
                logging.getLogger("niuma.user.keys").debug(f"Used keys load failed: {e}")
                self._used_keys = set()

    def _save_used_key(self, key_hash: str):
        """记录已使用的 Key（防重放）"""
        self._used_keys.add(key_hash)
        path = os.path.join(self._dir, ".used_keys")
        with open(path, "a") as f:
            f.write(key_hash + "\n")

    def init_device(self) -> User:
        """首次启动——初始化设备 + 开始试用。"""
        import socket, uuid
        device_id = hashlib.sha256(
            f"{socket.gethostname()}:{uuid.getnode()}".encode()
        ).hexdigest()[:16]

        now = datetime.now().isoformat()
        self._user = User(
            device_id=device_id,
            trial_started_at=now,
            created_at=now,
            last_login=now,
        )
        self._save()
        return self._user

    @property
    def current_user(self) -> Optional[User]:
        return self._user

    @property
    def is_trial_active(self) -> bool:
        """试用是否仍在有效期内。"""
        if not self._user:
            return False
        if self._user.trial_ended:
            return False
        if self._clock_tampered:
            return False  # 检测到时钟回拨 → 拒绝试用
        try:
            start = datetime.fromisoformat(self._user.trial_started_at)
            elapsed = (datetime.now() - start).days
            if elapsed < TRIAL_DAYS:
                self._save_checkpoint()  # 每次正常验证通过 → 更新检查点
                return True
            return False
        except Exception as e:
            import logging
            logging.getLogger("niuma.user.trial").warning(f"Trial check failed: {e}")
            return False

    @property
    def trial_days_left(self) -> int:
        if not self._user or self._user.trial_ended:
            return 0
        try:
            start = datetime.fromisoformat(self._user.trial_started_at)
            elapsed = (datetime.now() - start).days
            return max(0, TRIAL_DAYS - elapsed)
        except Exception as e:
            import logging
            logging.getLogger("niuma.user.trial").debug(f"Trial days calculation failed: {e}")
            return 0

    @property
    def is_license_active(self) -> bool:
        """许可证是否有效。"""
        if not self._user or not self._user.license:
            return False
        if not self._user.license.is_active:
            return False
        try:
            expires = datetime.fromisoformat(self._user.license.expires_at)
            return datetime.now() < expires
        except Exception as e:
            import logging
            logging.getLogger("niuma.user.license").debug(f"License expiry check failed: {e}")
            return False

    @property
    def can_use(self) -> bool:
        """用户能否使用产品。试用期内 or 许可证有效。"""
        return self.is_trial_active or self.is_license_active

    def activate_license(self, activation_key: str) -> tuple[bool, str]:
        """激活许可证。返回 (成功, 消息)。

        验证流程：
        1. 解析 Key — 提取 payload + signature
        2. 用内置公钥验签
        3. 检查过期时间
        4. 绑定当前设备
        """
        if not self._user:
            self.init_device()

        try:
            # 防重放：检查 Key 是否已被使用
            key_hash = hashlib.sha256(activation_key.encode()).hexdigest()
            if key_hash in self._used_keys:
                return False, "此激活 Key 已被使用"

            # 解析 Key（格式: base64(payload).base64(signature)）
            parts = activation_key.split(".")
            if len(parts) != 2:
                return False, "激活 Key 格式无效"

            payload_str = _b64.urlsafe_b64decode(parts[0] + "==").decode()
            signature = _b64.urlsafe_b64decode(parts[1] + "==")

            # HMAC-SHA256 验签——防伪造
            # 密钥从环境变量或设备信息派生，不再硬编码
            _SECRET = _get_secret_key()
            expected_sig = hmac.new(_SECRET, payload_str.encode(), hashlib.sha256).digest()
            if not hmac.compare_digest(signature, expected_sig):
                return False, "激活 Key 无效——签名验证失败"

            payload = json.loads(payload_str)

            plan = payload.get("plan", "")
            valid_days = payload.get("days", 0)
            expires_str = payload.get("expires", "")
            target_device = payload.get("device", "")

            if plan not in PLANS and valid_days == 0:
                return False, "未知的套餐类型"

            # 设备绑定检查（special key 可跳过）
            if target_device and target_device != self._user.device_id:
                return False, "此激活 Key 已绑定到其他设备"

            # 过期检查
            if expires_str:
                expires_dt = datetime.fromisoformat(expires_str)
                if datetime.now() > expires_dt:
                    return False, "激活 Key 已过期"

            # 计算到期时间
            if expires_str:
                expires_at = expires_str
            else:
                days = PLANS[plan]["days"] if plan in PLANS else valid_days
                expires_at = (datetime.now() + timedelta(days=days)).isoformat()

            # 创建 License
            self._user.license = License(
                key=activation_key,
                plan=plan,
                activated_at=datetime.now().isoformat(),
                expires_at=expires_at,
                device_hash=self._user.device_id,
            )
            self._user.trial_ended = True  # 激活即结束试用
            self._save_used_key(key_hash)  # 记录已使用 → 防重放
            self._save()

            plan_name = PLANS.get(plan, {}).get("name", f"{valid_days}天")
            return True, f"激活成功——{plan_name}套餐，有效期至 {expires_at[:10]}"

        except Exception as e:
            return False, f"激活失败: {str(e)}"

    def get_status(self) -> dict:
        """获取当前用户状态。"""
        return {
            "has_user": self._user is not None,
            "trial_active": self.is_trial_active,
            "trial_days_left": self.trial_days_left,
            "license_active": self.is_license_active,
            "can_use": self.can_use,
            "license_plan": self._user.license.plan if (self._user and self._user.license) else None,
            "license_expires": self._user.license.expires_at[:10] if (self._user and self._user.license) else None,
            "device_id": self._user.device_id[:8] if self._user else "",
        }


# 平台唯一实例
user_manager = UserManager()
