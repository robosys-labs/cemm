from __future__ import annotations
from inspect import signature
from cemm.v350.significance.engine import SignificanceEngine
from cemm.v350.uol.model import ImpactAssessment


def test_impact_assessment_current_contract_uses_source_event_or_state_ref():
    params=signature(ImpactAssessment).parameters
    assert 'source_event_or_state_ref' in params
    assert 'event_ref' not in params


def test_significance_engine_no_obsolete_event_ref_constructor_keyword():
    import inspect
    source=inspect.getsource(SignificanceEngine.assess)
    assert 'source_event_or_state_ref=' in source
    assert 'event_ref=event_ref' not in source


def test_execute_goal_policy_cannot_omit_capability_gate():
    from pathlib import Path
    source = (Path(__file__).parents[2] / "cemm" / "v350" / "goals" / "policy.py").read_text(encoding="utf-8")
    assert "execute_policy_missing_capability_gate" in source


def test_effective_rule_supersession_is_scoped_per_rule_identity():
    import inspect
    from cemm.v350.significance.engine import ImpactRuleRegistry
    from cemm.v350.goals.policy import ResponsePolicyRegistry
    from cemm.v350.response.planner import ResponseTransformRegistry
    for cls in (ImpactRuleRegistry, ResponsePolicyRegistry, ResponseTransformRegistry):
        source=inspect.getsource(cls.__init__)
        assert 'by_ref' in source
        assert 'setdefault' in source
