from __future__ import annotations

import pytest

from cemm.v350.learning.model import PinnedRecord
from cemm.v350.schema.model import SchemaLifecycleStatus, UseDecision
from cemm.v350.significance.engine import ImportanceAggregator, ImpactRuleRegistry
from cemm.v350.significance.model import (
    ImpactRuleRecord, ImportanceEvidencePolarity, ImportanceEvidenceRecord, ImportancePolicyRecord,
)
from cemm.v350.storage.model import RecordKind


def test_candidate_impact_rule_is_not_executable_authority():
    rule = ImpactRuleRecord(
        rule_ref="impact-rule:test", source_record_kinds=(RecordKind.EVENT_OCCURRENCE,),
        fixed_stakeholder_refs=("ref:stakeholder",), fixed_affected_refs=("ref:affected",),
        lifecycle_status=SchemaLifecycleStatus.CANDIDATE, use_decision=UseDecision.ALLOW,
    )
    assert not rule.executable
    assert ImpactRuleRegistry((rule,))._rules == ()


def test_importance_policy_pins_channel_revision_and_preserves_opposition():
    source_pin = PinnedRecord(RecordKind.EVIDENCE, "evidence:source", 1, "f" * 64)
    policy = ImportancePolicyRecord(
        policy_ref="importance-policy:test", channel_weights=(("importance-channel:relation", 3, 1.0),),
        low_threshold=0.2, high_threshold=0.7, lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_decision=UseDecision.ALLOW,
    )
    support = ImportanceEvidenceRecord(
        evidence_ref="importance-evidence:support", subject_ref="event:x", stakeholder_ref="ref:user",
        channel_schema_ref="importance-channel:relation", channel_schema_revision=3, source_pin=source_pin,
        polarity=ImportanceEvidencePolarity.SUPPORT, weight=1.0, context_ref="actual", permission_ref="conversation",
    )
    oppose = ImportanceEvidenceRecord(
        evidence_ref="importance-evidence:oppose", subject_ref="event:x", stakeholder_ref="ref:user",
        channel_schema_ref="importance-channel:relation", channel_schema_revision=3, source_pin=source_pin,
        polarity=ImportanceEvidencePolarity.OPPOSE, weight=0.5, context_ref="actual", permission_ref="conversation",
    )
    assessment, used = ImportanceAggregator().assess(
        subject_ref="event:x", stakeholder_ref="ref:user", context_ref="actual", permission_ref="conversation",
        evidence=(support, oppose), policy=policy,
    )
    assert assessment is not None
    assert {item.evidence_ref for item in used} == {support.evidence_ref, oppose.evidence_ref}
    assert assessment.score < 1.0


def test_importance_evidence_from_other_stakeholder_cannot_leak():
    pin = PinnedRecord(RecordKind.EVIDENCE, "evidence:source", 1, "a" * 64)
    policy = ImportancePolicyRecord(
        policy_ref="importance-policy:test", channel_weights=(("channel:x", 1, 1.0),), low_threshold=0.2, high_threshold=0.7,
        lifecycle_status=SchemaLifecycleStatus.ACTIVE, use_decision=UseDecision.ALLOW,
    )
    other = ImportanceEvidenceRecord(
        evidence_ref="importance-evidence:other", subject_ref="event:x", stakeholder_ref="ref:other",
        channel_schema_ref="channel:x", channel_schema_revision=1, source_pin=pin,
        polarity=ImportanceEvidencePolarity.SUPPORT, weight=1.0, context_ref="actual", permission_ref="conversation",
    )
    assessment, used = ImportanceAggregator().assess(
        subject_ref="event:x", stakeholder_ref="ref:user", context_ref="actual", permission_ref="conversation",
        evidence=(other,), policy=policy,
    )
    assert assessment is None
    assert used == ()


def test_importance_policy_rejects_duplicate_channel_revision_pin():
    with pytest.raises(ValueError):
        ImportancePolicyRecord(
            policy_ref="importance-policy:bad",
            channel_weights=(("channel:x", 1, 1.0), ("channel:x", 1, 0.5)),
            low_threshold=0.2, high_threshold=0.7,
        )
