"""
逻辑断层修复集成测试：Token节约 + 本地答案 + 完整链路
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.token_savings import savings_engine, SavingsRecord
from engine.local_answer_check import LocalAnswerChecker


def test_token_savings_cold_start():
    """冷启动——不足5次不计算节约。"""
    se = savings_engine
    se._history.clear()
    se._records.clear()
    for i in range(4):
        r = se.record_execution("writing", 12000, "deepseek-v3.2")
    assert r is None  # 第4次还在冷启动
    # 第6次——可以算了
    se.record_execution("writing", 12000, "deepseek-v3.2")
    r = se.record_execution("writing", 8000, "deepseek-v3.2")
    assert r is not None
    assert r.saved > 0   # 比历史平均12000省了4000
    print(f"✅ Token节约: saved={r.saved} tokens, rate={r.savings_rate:.1%}")


def test_token_savings_report():
    """日报告正确。"""
    se = savings_engine
    se._history.clear()
    se._records.clear()
    for _ in range(10):
        se.record_execution("writing", 10000, "kimi-k2.6")
    se.record_execution("writing", 6000, "gemma-4")

    r = se.record_execution("writing", 7000, "kimi-k2.6")
    report = se.daily_report()
    assert report.total_tasks >= 1
    print(f"✅ 日报告: tasks={report.total_tasks}, saved={report.total_saved}, rate={report.savings_rate:.1%}, {report.trend}")


def test_local_answer_found():
    """本地有答案——L3 匹配。"""
    c = LocalAnswerChecker()
    result = c.check(
        "Token 优化策略",
        l3_results=[{"content": "太极引擎采用四两拨千斤策略进行Token管理，包括力点探测和Smart Allocator"}],
    )
    assert result.found
    assert result.source == "l3_knowledge"
    print(f"✅ 本地答案: found={result.found}, score={result.match_score:.0%}")


def test_local_answer_not_found():
    """本地无答案。"""
    c = LocalAnswerChecker()
    result = c.check("量子计算最新进展", l3_results=[{"content": "Token管理是指..."}])
    assert not result.found
    should_skip, reason = c.should_skip_web_search("量子计算最新进展", l3_results=[{"content": "无关内容..."}])
    assert not should_skip
    print(f"✅ 本地无答案: found={result.found}, should_skip={should_skip}")


if __name__ == "__main__":
    test_token_savings_cold_start()
    test_token_savings_report()
    test_local_answer_found()
    test_local_answer_not_found()
    print("\n🎉 逻辑断层修复完成 — 核心卖点可自证")
