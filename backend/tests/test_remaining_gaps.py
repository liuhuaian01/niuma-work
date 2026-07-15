"""
剩余断层修复测试：自愈追踪 + 降级成本 + 知识衰减 + Skill匹配
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.healing_tracker import healing_tracker
from engine.fallback_cost import FallbackCostAnalyzer
from engine.knowledge_quality import FreshnessScorer, SkillMatcher


def test_healing_tracker():
    ht = healing_tracker
    ht._records.clear()
    ht._rule_success.clear()

    ht.record("gate_fail", "incomplete", "提高Token预算后重试")
    ht.record_result("提高Token预算后重试", True)
    ht.record("gate_fail", "incomplete", "提高Token预算后重试")
    ht.record_result("提高Token预算后重试", True)
    ht.record("pi_intercept", "file_delete", "移动到回收站")
    ht.record_result("移动到回收站", False)

    eff = ht.get_healing_effectiveness()
    stats = ht.get_stats()
    print(f"✅ 自愈追踪: events={stats['total_events']}, succeeded={stats['succeeded']}")


def test_fallback_cost():
    fc = FallbackCostAnalyzer()
    # 写作降级——可接受
    r1 = fc.analyze("deepseek-v3.2", "gemma-4", "writing")
    assert r1.acceptable
    # 编码降级——不可接受
    r2 = fc.analyze("deepseek-v3.2", "gemma-4", "coding")
    assert not r2.acceptable
    print(f"✅ 降级成本: writing_loss={r1.quality_loss:.0%}(OK) coding_loss={r2.quality_loss:.0%}(X)")


def test_freshness():
    fs = FreshnessScorer()
    # 3天前——新鲜
    from datetime import datetime, timedelta
    recent = (datetime.now() - timedelta(days=3)).isoformat()
    assert fs.score(recent) == 1.0
    # 60天前——可用
    old = (datetime.now() - timedelta(days=60)).isoformat()
    assert 0.3 <= fs.score(old) <= 0.6
    print(f"✅ 知识衰减: fresh={fs.score(recent)}, old={fs.score(old)}")


def test_skill_matcher():
    sm = SkillMatcher()
    # 高匹配——写作任务 + 写作技能
    score = sm.match("帮我写一篇文章", "写作润色工具，支持格式化和结构优化", "writing-polish", 0.9)
    assert score >= 0.2
    assert sm.should_wake("帮我写一篇文章", "写作润色工具，支持格式化", "writing-polish", 0.85)
    # 完全不搭的技能不应唤醒
    assert not sm.should_wake("帮我写Python代码", "风景摄影技巧分享", "photo-tips", 0.80)
    print(f"✅ Skill匹配: writing_match={score:.2f}")


if __name__ == "__main__":
    test_healing_tracker()
    test_fallback_cost()
    test_freshness()
    test_skill_matcher()
    print("\n🎉 剩余断层全部修复")
