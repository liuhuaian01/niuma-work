"""Auto模型选择验证"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 验证 AgentCreate 默认值为 auto
from schemas.agent import AgentCreate
a = AgentCreate(name="测试Agent", role="writer")
assert a.model == "auto", f"期望 'auto', 实际 '{a.model}'"
print("✅ AgentCreate 默认模型: auto")

# 验证手动指定模型
b = AgentCreate(name="手动Agent", role="coder", model="deepseek-v3.2")
assert b.model == "deepseek-v3.2"
print("✅ 手动指定模型: deepseek-v3.2")

print("\n🎉 Auto 模式 + 手动选择 后端就绪")
