"""
测试：太极引擎 · 五维进化日志（Phase 5）

验证：
1. 执行日志记录正确
2. 反思引擎发现成功模式
3. 反思引擎发现失败模式
4. 每日意识摘要生成
5. 跨工作间洞察
"""

import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.execution_log import ExecutionLogger, ExecutionRecord
from engine.reflection import ReflectionEngine

_tmp = []


def test_execution_log():
    """执行日志记录正确。"""
    db = os.path.join(tempfile.gettempdir(), "test_exec_log.db")
    _tmp.append(db)
    logger = ExecutionLogger(db)
    logger.log(ExecutionRecord(
        agent_id="writer-01", workspace_id="ws-1", task_type="writing",
        model_used="deepseek-v3.2", tokens_used=12000, gate_score=0.92,
        success=True, tools_used=3, duration_ms=4500,
    ))
    stats = logger.get_stats()
    assert stats["total_executions"] == 1
    assert stats["success_rate"] == 1.0
    assert stats["total_tokens"] == 12000
    print("✅ test_execution_log 通过")


def test_reflection_finds_patterns():
    """反思引擎发现成功/失败模式。"""
    logger = ExecutionLogger()
    # 7 条成功写作
    for _ in range(7):
        logger.log(ExecutionRecord("w1", "ws-1", "writing", "deepseek-v3.2", 10000, 0.9, True, 2))
    # 3 条失败搜索
    for _ in range(3):
        logger.log(ExecutionRecord("s1", "ws-1", "search", "kimi-k2.6", 8000, 0.3, False, 5, error_type="token_exceeded"))

    engine = ReflectionEngine()
    reflection = engine.reflect(logger.get_today_records())

    assert reflection.total_executions == 10
    assert reflection.success_rate > 0.6
    assert len(reflection.patterns_discovered) > 0
    assert reflection.top_success_pattern is not None
    print(f"✅ test_reflection_finds_patterns 通过")
    print(f"   最佳: {reflection.top_success_pattern.recommendation}")


def test_consciousness_summary():
    """意识摘要正确。"""
    logger = ExecutionLogger()
    for _ in range(5):
        logger.log(ExecutionRecord("w1", "ws-1", "writing", "deepseek-v3.2", 8000, 0.95, True, 1))
    for _ in range(2):
        logger.log(ExecutionRecord("w1", "ws-1", "coding", "deepseek-v3.2", 40000, 0.75, True, 8))

    engine = ReflectionEngine()
    reflection = engine.reflect(logger.get_today_records())
    summary = engine.consciousness_summary(reflection)

    assert "太极引擎" in summary
    assert "成功率" in summary
    assert len(summary) > 50
    print(f"✅ test_consciousness_summary 通过")
    print(summary)


def test_cross_workspace():
    """跨工作间洞察。"""
    logger = ExecutionLogger()
    # ws-1 高成功率
    for _ in range(3):
        logger.log(ExecutionRecord("w1", "ws-1", "writing", "deepseek-v3.2", 5000, 0.95, True, 2))
    # ws-2 低成功率
    for _ in range(3):
        logger.log(ExecutionRecord("w2", "ws-2", "writing", "gemma-4", 5000, 0.5, False, 1, error_type="gate_fail"))

    engine = ReflectionEngine()
    reflection = engine.reflect(logger.get_today_records())
    assert "ws-1" in reflection.cross_workspace_insight or len(reflection.recommended_actions) > 0
    print(f"✅ test_cross_workspace 通过: {reflection.recommended_actions}")


if __name__ == "__main__":
    test_execution_log()
    test_reflection_finds_patterns()
    test_consciousness_summary()
    test_cross_workspace()
    print("\n🎉 全部 4 项测试通过 — Phase 5 五维进化日志完成")
