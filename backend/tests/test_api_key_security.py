"""
API密钥管理测试

测试API密钥验证和脱敏功能
"""

import pytest
from utils import validate_api_key, mask_api_key


class TestValidateApiKey:
    """API密钥格式验证测试"""

    def test_valid_api_key(self):
        """测试有效的API密钥"""
        # 长度足够的有效密钥
        assert validate_api_key("sk-abc123def456ghi789jkl012mno345pqr") is True
        assert validate_api_key("abcdefghijklmnopqrstuvwxyz123456") is True
        assert validate_api_key("ABCDEF_123456-ghijklmnopqrstuvwxyz") is True

    def test_invalid_short_key(self):
        """测试过短的密钥"""
        assert validate_api_key("short") is False
        assert validate_api_key("a" * 31) is False  # 31个字符，不足32

    def test_invalid_empty_key(self):
        """测试空密钥"""
        assert validate_api_key("") is False
        assert validate_api_key(None) is False

    def test_invalid_characters(self):
        """测试包含非法字符的密钥"""
        assert validate_api_key("key@with#special$chars%1234567890abcdef") is False
        assert validate_api_key("key with spaces 12345678901234567890") is False
        assert validate_api_key("key\nwith\nnewlines12345678901234567") is False

    def test_boundary_length(self):
        """测试边界长度"""
        assert validate_api_key("a" * 32) is True  # 正好32个字符
        assert validate_api_key("a" * 31) is False  # 31个字符


class TestMaskApiKey:
    """API密钥脱敏测试"""

    def test_mask_normal_key(self):
        """测试正常密钥脱敏"""
        key = "sk-abc123def456ghi789jkl012mno345pqr"
        masked = mask_api_key(key)
        assert masked == "sk-a...5pqr"
        assert key not in masked  # 完整密钥不应出现在脱敏结果中

    def test_mask_empty_key(self):
        """测试空密钥脱敏"""
        assert mask_api_key("") == "****"
        assert mask_api_key(None) == "****"

    def test_mask_short_key(self):
        """测试短密钥脱敏"""
        assert mask_api_key("short") == "****"
        assert mask_api_key("12345678") == "****"  # 正好8个字符

    def test_mask_min_length_key(self):
        """测试最小可脱敏长度密钥"""
        key = "123456789"  # 9个字符
        masked = mask_api_key(key)
        assert masked == "1234...6789"
        assert len(masked) < len(key)  # 脱敏后应该更短或相等

    def test_mask_preserves_format(self):
        """测试脱敏保留前后缀格式"""
        key = "prefix-suffix1234567890abcdefghijklmnop"
        masked = mask_api_key(key)
        assert masked.startswith("pref")
        assert masked.endswith("mnop")
        assert "..." in masked


class TestIntegration:
    """集成测试"""

    def test_validate_then_mask(self):
        """测试验证后脱敏的流程"""
        key = "valid-api-key-1234567890abcdefghijklmn"
        
        # 先验证
        assert validate_api_key(key) is True
        
        # 再脱敏
        masked = mask_api_key(key)
        assert masked != key
        assert len(masked) < len(key)

    def test_invalid_key_not_masked_detail(self):
        """测试无效密钥不会泄露详细信息"""
        invalid_key = "invalid@key"
        
        # 验证失败
        assert validate_api_key(invalid_key) is False
        
        # 脱敏后不显示原始内容
        masked = mask_api_key(invalid_key)
        assert "@" not in masked  # 特殊字符不应出现在脱敏结果中


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
