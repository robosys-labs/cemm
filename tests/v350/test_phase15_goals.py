from __future__ import annotations

import pytest

from cemm.v350.goals.model import (
    GoalCandidateRecord, ResponsePolicyRuleRecord, TargetSelector, TargetSelectorMode,
)
from cemm.v350.goals.policy import GoalArbitrator, ResponsePolicyRegistry
from cemm.v350.learning.model import PinnedRecord
from cemm.v350.schema.model import SchemaLifecycleStatus, UseDecision, UseOperation
from cemm.v350.storage.model import RecordKind


def _pin(kind=RecordKind.SEMANTIC_APPLICATION, ref="application:x"):
    return PinnedRecord(kind, ref, 1, "f" * 64)


def test_targetless_goal_candidate_is_structurally_rejected():
    with pytest.raises(ValueError):
        GoalCandidateRecord(
            goal_ref="goal:bad", goal_schema_ref="goal-schema:ack", goal_schema_revision=1,
            operation=UseOperation.PLAN, target_refs=(), obligation_refs=("obligation:x",),
            policy_rule_pins=(_pin(RecordKind.RESPONSE_POLICY_RULE, "policy:x"),), source_pins=(_pin(),),
            authorization_refs=(),
        )


def test_candidate_response_policy_cannot_execute():
    rule = ResponsePolicyRuleRecord(
        rule_ref="policy:test", trigger_record_kinds=(RecordKind.SEMANTIC_APPLICATION,), trigger_schema_pins=(),
        goal_schema_ref="goal-schema:test", goal_schema_revision=1, goal_operation=UseOperation.PLAN,
        target_selectors=(TargetSelector(TargetSelectorMode.SOURCE),),
        lifecycle_status=SchemaLifecycleStatus.CANDIDATE, use_decision=UseDecision.ALLOW,
    )
    assert not rule.executable
    assert ResponsePolicyRegistry((rule,))._rules == ()


def test_authorization_precedes_utility():
    base = dict(
        goal_schema_ref="goal-schema:test", goal_schema_revision=1, operation=UseOperation.PLAN,
        target_refs=("target:x",), obligation_refs=("obligation:x",),
        policy_rule_pins=(_pin(RecordKind.RESPONSE_POLICY_RULE, "policy:x"),), source_pins=(_pin(),),
        authorization_refs=(),
    )
    unauthorized = GoalCandidateRecord(goal_ref="goal:unauthorized", authorized=False, utility_score=1000.0, **base)
    authorized = GoalCandidateRecord(goal_ref="goal:authorized", authorized=True, utility_score=0.1, **base)
    selected, rejected, deferred = GoalArbitrator().select((unauthorized, authorized), ())
    assert selected == (authorized.goal_ref,)
    assert unauthorized.goal_ref in rejected
    assert not deferred


def test_response_policy_axis_is_independent_from_plan_axis():
    rule = ResponsePolicyRuleRecord(
        rule_ref="policy:active", trigger_record_kinds=(RecordKind.SEMANTIC_APPLICATION,), trigger_schema_pins=(),
        goal_schema_ref="goal-schema:test", goal_schema_revision=1, goal_operation=UseOperation.PLAN,
        target_selectors=(TargetSelector(TargetSelectorMode.SOURCE),),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE, use_decision=UseDecision.ALLOW,
    )
    assert rule.use_operation == UseOperation.RESPONSE_POLICY
    assert rule.goal_operation == UseOperation.PLAN
    assert rule.executable
