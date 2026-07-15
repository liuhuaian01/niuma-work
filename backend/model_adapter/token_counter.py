"""Token 计数器

基于字符估算（中文约 1.5 字符/token，英文约 4 字符/token）
精确计数由模型 API 返回的 usage 字段提供
"""


def estimate_tokens(text: str) -> int:
    """估算文本的 Token 数量

    简单估算策略：
    - 中文字符: ~1.5 字符/token
    - 英文/数字: ~4 字符/token
    - 混合文本取加权平均
    """
    if not text:
        return 0

    chinese_chars = 0
    other_chars = 0

    for char in text:
        if '\u4e00' <= char <= '\u9fff' or '\u3000' <= char <= '\u303f':
            chinese_chars += 1
        else:
            other_chars += 1

    # 估算
    estimated = int(chinese_chars / 1.5 + other_chars / 4)
    return max(estimated, 1)


def estimate_messages_tokens(messages: list[dict]) -> int:
    """估算消息列表的总 Token 数"""
    total = 0
    for msg in messages:
        total += estimate_tokens(msg.get("content", ""))
        # 消息元数据开销（role, name 等）
        total += 4
    return total
