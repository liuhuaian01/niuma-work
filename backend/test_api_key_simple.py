"""简单测试API密钥功能"""
import sys
sys.path.insert(0, '.')

from utils import validate_api_key, mask_api_key

print("=" * 60)
print("测试 validate_api_key()")
print("=" * 60)

# 测试有效密钥
test_cases_valid = [
    "sk-abc123def456ghi789jkl012mno345pqr",
    "abcdefghijklmnopqrstuvwxyz123456",
    "ABCDEF_123456-ghijklmnopqrstuvwxyz",
    "a" * 32,  # 边界测试：正好32个字符
]

for key in test_cases_valid:
    result = validate_api_key(key)
    status = "✓ PASS" if result else "✗ FAIL"
    print(f"{status}: 长度{len(key):2d} -> {result}")

print()

# 测试无效密钥
test_cases_invalid = [
    ("short", "太短"),
    ("a" * 31, "31个字符"),
    ("", "空字符串"),
    (None, "None"),
    ("key@with#special$chars%1234567890abcdef", "特殊字符"),
    ("key with spaces 12345678901234567890", "包含空格"),
]

for key, desc in test_cases_invalid:
    result = validate_api_key(key)
    status = "✓ PASS" if not result else "✗ FAIL"
    display_key = repr(key) if key else "None"
    print(f"{status}: {desc:10s} ({display_key[:30]:30s}) -> {result}")

print()
print("=" * 60)
print("测试 mask_api_key()")
print("=" * 60)

# 测试脱敏
mask_tests = [
    ("sk-abc123def456ghi789jkl012mno345pqr", "正常密钥"),
    ("", "空字符串"),
    (None, "None"),
    ("short", "短密钥"),
    ("12345678", "8个字符"),
    ("123456789", "9个字符"),
]

for key, desc in mask_tests:
    masked = mask_api_key(key)
    display_key = repr(key) if key else "None"
    print(f"{desc:10s}: {display_key[:40]:40s} -> {masked}")

print()
print("=" * 60)
print("集成测试")
print("=" * 60)

# 测试验证+脱敏流程
test_key = "valid-api-key-1234567890abcdefghijklmn"
is_valid = validate_api_key(test_key)
masked = mask_api_key(test_key)
print(f"原始密钥: {test_key}")
print(f"验证结果: {'有效' if is_valid else '无效'}")
print(f"脱敏结果: {masked}")
print(f"安全保护: {'✓ 完整密钥已隐藏' if test_key not in masked else '✗ 密钥泄露'}")

print()
print("所有测试完成！")
