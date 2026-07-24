from __future__ import annotations

from cemm.v350.learning.frontier import EvidenceSummary
from cemm.v350.learning.model import CompetenceOutcome, CompetenceResultRecord, LearningPackageRecord, PinnedRecord
from cemm.v350.learning.promotion import PromotionPolicyEngine
from cemm.v350.schema.model import UseAuthorization, UseDecision, UseOperation
from cemm.v350.storage.model import RecordDependency, RecordKind


def test_per_use_missing_competence_does_not_block_independent_grant():
    pin = PinnedRecord(RecordKind.SCHEMA, "schema:test", 1, "a" * 64)
    package = LearningPackageRecord(
        package_ref="package:test", package_family="test", candidate_pins=(pin,), dependency_pins=(), frontier_refs=(),
        evidence_link_refs=(), counterexample_link_refs=(), competence_case_refs=("case:x",),
        requested_use_authorizations=(
            UseAuthorization(UseOperation.GROUND, UseDecision.ALLOW),
            UseAuthorization(UseOperation.REALIZE, UseDecision.ALLOW),
        ), promotion_policy_ref="policy:test",
    )
    result = CompetenceResultRecord(
        result_ref="result:ground", package_ref=package.package_ref, package_revision=1, use_operation=UseOperation.GROUND,
        candidate_pins=(pin,), dependency_pins=(), case_refs=("case:x",), outcome=CompetenceOutcome.PASSED,
        passed_case_refs=("case:x",), failed_case_refs=(), counterexample_refs=(), proof_refs=("proof:x",),
        failure_frontier_refs=(), snapshot_revision=0, boot_fingerprint="none", overlay_fingerprint="none",
        runner_ref="runner:test", runner_revision="1", independent_lineage_refs=("lineage:independent",), environment_refs=("env:test",),
    )
    evaluation = PromotionPolicyEngine().evaluate(
        package, (result,), EvidenceSummary((), (), (), (), (), (), 0.0, 0.0)
    )
    assert evaluation.decision.value == "promote"
    assert any(grant.operation == UseOperation.GROUND for grant in evaluation.use_grants)
    assert all(grant.operation != UseOperation.REALIZE for grant in evaluation.use_grants)
    assert any("missing_passed_competence:realize" in reason for reason in evaluation.blocked_reasons)


def test_dependency_identity_is_not_bare_record_ref():
    left = RecordDependency(RecordKind.EVIDENCE, "same-ref", 1, "a" * 64, "evidence")
    right = RecordDependency(RecordKind.SCHEMA, "same-ref", 1, "b" * 64, "schema")
    assert (left.record_kind, left.record_ref) != (right.record_kind, right.record_ref)
