"""
补全模块集成测试：Attention + Swarm + Honcho + CrossWorkspace + Closure
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.attention_engine import attention_engine, TriggerType
from engine.swarm_orchestrator import SwarmOrchestrator, OrchestrationStatus
from engine.honcho_modeler import HonchoModeler
from engine.cross_workspace import CrossWorkspaceHub
from engine.closure_engine import ClosureEngine, ChangeType, ChangeStatus


def test_attention_7_triggers():
    ae = attention_engine
    # 破冰
    events = ae.evaluate({"user_id": "test-01"})
    assert any(e.trigger == TriggerType.ICEBREAK for e in events)
    # 预警
    events = ae.evaluate({"warning": "token 70%", "warn_type": "token_critical"})
    assert any(e.trigger == TriggerType.WARNING for e in events)
    # 错误
    events = ae.evaluate({"error": "Gate FAIL", "error_type": "gate_fail", "has_healing": True})
    assert any(e.trigger == TriggerType.ERROR for e in events)
    # 总结
    events = ae.evaluate({"task_count": 10, "success_rate": 0.9, "total_tokens": 50000})
    assert any(e.trigger == TriggerType.SUMMARY for e in events)
    # 模式发现
    events = ae.evaluate({"pattern": "writing+deepseek-v3.2", "sample_count": 8})
    assert any(e.trigger == TriggerType.PATTERN for e in events)
    # 建议
    events = ae.evaluate({"suggestion": "考虑提升 Writer 预算"})
    assert any(e.trigger == TriggerType.SUGGESTION for e in events)
    print("✅ Attention Engine — 6/7 triggers")


def test_swarm_decompose_and_synthesize():
    sw = SwarmOrchestrator()
    # 分解
    subs = sw.decompose("写一份竞品分析报告", ["writer", "analyst", "searcher"])
    assert len(subs) >= 2
    # Gate
    gate = sw.validate_gate(subs[0], "DeepSeek在Token效率上领先Kimi30%")
    assert gate.passed
    subs[0].status = OrchestrationStatus.PASSED
    subs[0].result = "DeepSeek在Token效率上领先Kimi30%"
    subs[0].gate_score = gate.score
    if len(subs) > 1:
        subs[1].status = OrchestrationStatus.PASSED
        subs[1].result = "详细分析数据如下..."
        subs[1].gate_score = 0.85
    # Synthesize
    synth = sw.synthesize(subs)
    assert synth.quality_score > 0
    print(f"✅ Swarm — {synth.summary}")


def test_honcho_learning():
    hm = HonchoModeler()
    hm.learn_from_execution("user-01", "writing", "kimi-k2.6", True)
    hm.learn_from_execution("user-01", "writing", "deepseek-v3.2", True)
    hm.learn_from_execution("user-01", "coding", "deepseek-v3.2", True)
    model = hm.recommend_model("user-01", "writing", ["kimi-k2.6", "deepseek-v3.2"])
    assert model in ("kimi-k2.6", "deepseek-v3.2")
    profile = hm.get_profile("user-01")
    assert profile.total_interactions == 3
    print(f"✅ Honcho — {len(profile.preferred_models)} preferred models")


def test_cross_workspace():
    hub = CrossWorkspaceHub()
    session = hub.create_session("太极引擎开发协作", ["ws-1", "ws-2"])
    msg = hub.send_message(session.id, "ws-1", "hermes", "ws-2", "coder", "L3知识库需要向量检索？")
    assert msg and msg.status == "pending"
    sessions = hub.list_sessions("ws-1")
    assert len(sessions) == 1
    print(f"✅ CrossWorkspace — {len(session.messages)} messages")


def test_closure_auto_update():
    ce = ClosureEngine()
    proposals = ce.evaluate_from_reflection("writing+deepseek-v3.2 成功率95%", 0.92)
    assert len(proposals) >= 1
    assert proposals[0].change_type in (ChangeType.MODEL, ChangeType.BUDGET)
    ce.approve(proposals[0].id)
    stats = ce.get_stats()
    assert stats["applied"] >= 1
    print(f"✅ Closure — {stats['applied']} applied, {stats['pending']} pending")


if __name__ == "__main__":
    test_attention_7_triggers()
    test_swarm_decompose_and_synthesize()
    test_honcho_learning()
    test_cross_workspace()
    test_closure_auto_update()
    print("\n🎉 补全 5 模块全部通过 — 太极引擎架构完整")
