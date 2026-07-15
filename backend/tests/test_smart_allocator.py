"""
测试：太极引擎 · Smart Allocator（Phase 2）

验证：
1. 无历史数据时返回保守默认
2. 学习后分配更精准
3. HIGH/STANDARD/LOW 三级正确区分
4. 高优先级+预算充裕 → HIGH
5. 低优先级+预算紧张 → LOW
6. 低价值闲聊 → LOW
"""

import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.smart_allocator import (
    SmartAllocator, TaskType, BudgetLevel, ForceProbeInput,
)

_tmp_files = []

def _tmp_db(name: str) -> str:
    path = os.path.join(tempfile.gettempdir(), name)
    _tmp_files.append(path)
    return path


def test_no_history_default():
    """无历史数据 → 保守默认。"""
    a = SmartAllocator()
    r = a.probe(ForceProbeInput(TaskType.WRITING, 25000, 0.5))
    assert r.budget_level == BudgetLevel.STANDARD
    assert r.confidence == 0.3
    print("✅ test_no_history_default 通过")


def test_learn_and_improve():
    """学习后分配更精准。"""
    a = SmartAllocator(_tmp_db("test_sa_learn.db"))

    for _ in range(8):
        a.record_execution(TaskType.WRITING, 12000, 0.88)

    r = a.probe(ForceProbeInput(TaskType.WRITING, 25000, 0.8))
    assert r.budget_level == BudgetLevel.HIGH, f"期望 HIGH, 实际 {r.budget_level}"
    print(f"✅ test_learn_and_improve 通过: {r.reason}")

    for _ in range(10):
        a.record_execution(TaskType.SEARCH, 8000, 0.55)

    r = a.probe(ForceProbeInput(TaskType.SEARCH, 5000, 0.2))
    assert r.budget_level == BudgetLevel.LOW, f"期望 LOW, 实际 {r.budget_level}"
    print(f"✅ test_low_priority_search 通过: {r.reason}")


def test_conversation_low():
    """低价值闲聊 → LOW。"""
    a = SmartAllocator(_tmp_db("test_sa_conv.db"))
    for _ in range(5):
        a.record_execution(TaskType.CONVERSATION, 4000, 0.95)
    r = a.probe(ForceProbeInput(TaskType.CONVERSATION, 8000, 0.3))
    assert r.budget_level == BudgetLevel.LOW, f"期望 LOW, 实际 {r.budget_level}"
    print(f"✅ test_conversation_low 通过: {r.reason}")


def test_budget_remaining():
    """验证预算追踪正确。"""
    a = SmartAllocator(_tmp_db("test_sa_budget.db"))
    assert a.get_budget_remaining(TaskType.WRITING) == 30000
    a.record_execution(TaskType.WRITING, 10000, 0.8)
    remaining = a.get_budget_remaining(TaskType.WRITING)
    assert remaining == 20000, f"期望 20000, 实际 {remaining}"
    print(f"✅ test_budget_remaining 通过: 剩余 {remaining}")


def test_recommend_model():
    """推荐模型接口。"""
    a = SmartAllocator(_tmp_db("test_sa_model.db"))
    for _ in range(5):
        a.record_execution(TaskType.CODING, 45000, 0.72)
    model, tokens = a.recommend_model(TaskType.CODING, 45000, 0.9)
    assert model == "deepseek-v4", f"期望 deepseek-v4, 实际 {model}"
    assert tokens > 0
    print(f"✅ test_recommend_model 通过: {model}, {tokens} tokens")


if __name__ == "__main__":
    test_no_history_default()
    test_learn_and_improve()
    test_conversation_low()
    test_budget_remaining()
    test_recommend_model()
    print("\n🎉 全部 5 项测试通过 — Phase 2 Smart Allocator 升格完成")

