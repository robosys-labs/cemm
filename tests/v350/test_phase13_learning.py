from __future__ import annotations

from pathlib import Path

import pytest

from cemm.v350.learning.competence import LearningCompetenceRunner
from cemm.v350.learning.frontier import EvidenceSummary
from cemm.v350.learning.model import (
    CompetenceOutcome,
    CompetenceResultRecord,
    LearningPackageRecord,
    LearningPackageStatus,
    PinnedRecord,
)
from cemm.v350.learning.package import LearningPackageCommitCoordinator
from cemm.v350.learning.promotion import PromotionCoordinator, PromotionPolicyEngine
from cemm.v350.learning.rehydration import LearningRehydrationCoordinator
from cemm.v350.schema.model import (
    MeaningSchema,
    ResponsePolicySchema,
    SchemaLifecycleStatus,
    UseAuthorization,
    UseDecision,
    UseOperation,
    UseProfile,
)
from cemm.v350.schema.registry import SchemaRegistry
from cemm.v350.storage.codec import encode_record
from cemm.v350.storage.model import GraphPatch, PatchOperation, PatchOperationKind, RecordKind
from cemm.v350.storage.store import SemanticStore


def _patch(store: SemanticStore, kind: RecordKind, record, *, expected_revision=None, expected_fingerprint=None):
    from cemm.v350.storage.codec import record_ref, record_revision
    target = record_ref(kind, record)
    return store.apply_patch(GraphPatch(
        patch_ref=f"patch:test:{kind.value}:{target}:{record_revision(kind, record)}:{store.revision}",
        context_ref="test:phase13",
        scope_ref="test",
        source_ref="source:test",
        permission_ref="internal",
        operations=(PatchOperation(
            operation_ref=f"op:test:{kind.value}:{target}:{record_revision(kind, record)}:{store.revision}",
            operation_kind=PatchOperationKind.UPSERT,
            record_kind=kind,
            target_ref=target,
            record_revision=record_revision(kind, record),
            payload=encode_record(kind, record),
            expected_record_revision=expected_revision,
            expected_record_fingerprint=expected_fingerprint,
            reason="phase13 test fixture",
        ),),
        expected_store_revision=store.revision,
    ))


def _candidate(ref: str = "schema:test:learned") -> ResponsePolicySchema:
    return ResponsePolicySchema(
        schema_ref=ref,
        semantic_key="opaque-test-key",
        lifecycle_status=SchemaLifecycleStatus.CANDIDATE,
        use_profile=UseProfile.from_mapping({UseOperation.RESPONSE_POLICY: UseDecision.ALLOW}),
    )


def _persist_candidate_and_package(store: SemanticStore):
    candidate = _candidate()
    result = _patch(store, RecordKind.SCHEMA, candidate)
    assert result.committed, result.errors
    stored = store.get_record(RecordKind.SCHEMA, candidate.schema_ref, candidate.revision)
    assert stored is not None
    pin = PinnedRecord(RecordKind.SCHEMA, stored.record_ref, stored.revision, stored.record_fingerprint)
    package = LearningPackageRecord(
        package_ref="learning-package:test",
        package_family="semantic_type_and_inheritance",
        candidate_pins=(pin,),
        dependency_pins=(),
        frontier_refs=(),
        evidence_link_refs=(),
        counterexample_link_refs=(),
        competence_case_refs=("competence:test:ground",),
        requested_use_authorizations=(UseAuthorization(UseOperation.RESPONSE_POLICY, UseDecision.ALLOW),),
        promotion_policy_ref="policy:test:promotion",
        review_refs=("review:test",),
        provenance_refs=("provenance:test",),
        source_lineage_refs=("lineage:induction",),
        permission_ref="internal",
    )
    result = LearningPackageCommitCoordinator(store).persist(package)
    assert result.committed, result.errors
    return candidate, pin, package


def _persist_passed_competence(store: SemanticStore, package: LearningPackageRecord) -> CompetenceResultRecord:
    with store.snapshot() as snapshot:
        result = CompetenceResultRecord(
            result_ref="competence-result:test:ground",
            package_ref=package.package_ref,
            package_revision=package.revision,
            use_operation=UseOperation.RESPONSE_POLICY,
            candidate_pins=package.candidate_pins,
            dependency_pins=package.dependency_pins,
            case_refs=package.competence_case_refs,
            outcome=CompetenceOutcome.PASSED,
            passed_case_refs=package.competence_case_refs,
            failed_case_refs=(),
            counterexample_refs=(),
            proof_refs=("proof:test:ground",),
            failure_frontier_refs=(),
            snapshot_revision=snapshot.store_revision,
            boot_fingerprint=snapshot.boot_fingerprint,
            overlay_fingerprint=snapshot.overlay_fingerprint,
            runner_ref="runner:test",
            runner_revision="1",
            independent_lineage_refs=("lineage:independent-competence",),
            environment_refs=("environment:test",),
            permission_ref="internal",
        )
    commit = LearningCompetenceRunner(store, runner_ref="runner:test", runner_revision="1").persist(result)
    assert commit.committed, commit.errors
    return result


def test_candidate_allow_profile_is_not_executable_authority():
    candidate = _candidate()
    registry = SchemaRegistry((candidate,))
    with pytest.raises(KeyError):
        registry.schema_for_use(candidate.schema_ref, UseOperation.RESPONSE_POLICY)
    with pytest.raises(KeyError):
        registry.authoritative_schema(candidate.schema_ref)


def test_competence_verified_allow_is_not_promoted_authority():
    schema = MeaningSchema(
        schema_ref="schema:test:competence-only",
        semantic_key="opaque-competence-only",
        lifecycle_status=SchemaLifecycleStatus.COMPETENCE_VERIFIED,
        use_profile=UseProfile.from_mapping({UseOperation.RESPONSE_POLICY: UseDecision.ALLOW}),
    )
    registry = SchemaRegistry((schema,))
    with pytest.raises(KeyError):
        registry.schema_for_use(schema.schema_ref, UseOperation.GROUND)


def test_response_policy_is_independent_use_axis():
    assert UseOperation.RESPONSE_POLICY.value == "response_policy"
    schema = MeaningSchema(
        schema_ref="schema:test:response-policy",
        semantic_key="opaque-response-policy",
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_profile=UseProfile.from_mapping({UseOperation.RESPONSE_POLICY: UseDecision.ALLOW}),
    )
    registry = SchemaRegistry((schema,))
    assert registry.schema_for_use(schema.schema_ref, UseOperation.RESPONSE_POLICY).schema_ref == schema.schema_ref
    with pytest.raises(KeyError):
        registry.schema_for_use(schema.schema_ref, UseOperation.PLAN)


def test_candidate_supersession_does_not_shadow_active_authority():
    active = MeaningSchema(
        schema_ref="schema:test:shadow",
        semantic_key="opaque-active",
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_profile=UseProfile.from_mapping({UseOperation.GROUND: UseDecision.ALLOW}),
        revision=1,
    )
    candidate = MeaningSchema(
        schema_ref=active.schema_ref,
        semantic_key="opaque-candidate",
        lifecycle_status=SchemaLifecycleStatus.CANDIDATE,
        use_profile=UseProfile.from_mapping({UseOperation.GROUND: UseDecision.ALLOW}),
        revision=2,
        supersedes_revision=1,
    )
    registry = SchemaRegistry((active, candidate))
    assert registry.authoritative_schema(active.schema_ref).revision == 1
    assert registry.schema_for_use(active.schema_ref, UseOperation.GROUND).revision == 1


def test_direct_graph_patch_cannot_activate_tracked_candidate_without_promotion_decision():
    store = SemanticStore()
    _, pin, _ = _persist_candidate_and_package(store)
    active = MeaningSchema(
        schema_ref=pin.record_ref,
        semantic_key="opaque-test-key",
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_profile=UseProfile.from_mapping({UseOperation.GROUND: UseDecision.ALLOW}),
        revision=2,
    )
    commit = _patch(store, RecordKind.SCHEMA, active, expected_revision=1, expected_fingerprint=pin.record_fingerprint)
    assert not commit.committed
    assert any("PromotionDecision" in error or "promotion" in error.lower() for error in commit.errors)
    store.close()


def test_per_use_competence_promotes_atomically_and_survives_restart(tmp_path: Path):
    overlay = tmp_path / "learning.sqlite"
    store = SemanticStore(overlay)
    _, _, package = _persist_candidate_and_package(store)
    competence = _persist_passed_competence(store, package)
    policy = PromotionPolicyEngine(store)
    evaluation = policy.evaluate(
        package,
        (competence,),
        EvidenceSummary((), (), (), (), (), (), 0.0, 0.0),
    )
    decision = policy.decision_record(
        package,
        evaluation,
        policy_ref="policy:test:promotion",
        review_refs=("review:test",),
        authorization_refs=("authorization:test",),
    )
    commit = PromotionCoordinator(store).promote(package, decision)
    assert commit.committed, commit.errors
    promoted = store.repositories.schemas.for_use("schema:test:learned", UseOperation.RESPONSE_POLICY)
    assert promoted.lifecycle_status == SchemaLifecycleStatus.ACTIVE
    with pytest.raises(KeyError):
        store.repositories.schemas.for_use("schema:test:learned", UseOperation.TRANSITION)
    before = LearningRehydrationCoordinator(store).require_clean()
    assert before.active_package_refs == (package.package_ref,)
    store.close()

    restarted = SemanticStore(overlay)
    after = LearningRehydrationCoordinator(restarted).require_clean()
    assert after.active_package_refs == before.active_package_refs
    promoted_after = restarted.repositories.schemas.for_use("schema:test:learned", UseOperation.RESPONSE_POLICY)
    assert promoted_after.record_fingerprint == promoted.record_fingerprint
    restarted.close()


def test_repeated_evidence_never_substitutes_for_competence():
    package = LearningPackageRecord(
        package_ref="learning-package:evidence-only",
        package_family="property_state_value_structure",
        candidate_pins=(PinnedRecord(RecordKind.SCHEMA, "schema:test:evidence", 1, "f" * 64),),
        dependency_pins=(),
        frontier_refs=(), evidence_link_refs=("e:1", "e:2", "e:3"), counterexample_link_refs=(),
        competence_case_refs=("case:1",),
        requested_use_authorizations=(UseAuthorization(UseOperation.INFER, UseDecision.ALLOW),),
        promotion_policy_ref="policy:test",
    )
    result = PromotionPolicyEngine().evaluate(
        package,
        (),
        EvidenceSummary(("e:1", "e:2", "e:3"), (), (), (), ("l:1", "l:2", "l:3"), (), 1000.0, 0.0),
    )
    assert not result.use_grants
    assert any("missing_passed_competence" in item for item in result.blocked_reasons)


def test_counterexample_requires_explicit_competence_coverage():
    pin = PinnedRecord(RecordKind.SCHEMA, "schema:test:counterexample", 1, "a" * 64)
    package = LearningPackageRecord(
        package_ref="learning-package:counterexample",
        package_family="opaque-family",
        candidate_pins=(pin,), dependency_pins=(), frontier_refs=(), evidence_link_refs=(),
        counterexample_link_refs=("evidence-link:counterexample",),
        competence_case_refs=("case:counterexample",),
        requested_use_authorizations=(UseAuthorization(UseOperation.GROUND, UseDecision.ALLOW),),
        promotion_policy_ref="policy:test",
    )
    result = CompetenceResultRecord(
        result_ref="competence-result:counterexample", package_ref=package.package_ref, package_revision=1,
        use_operation=UseOperation.GROUND, candidate_pins=(pin,), dependency_pins=(),
        case_refs=("case:counterexample",), outcome=CompetenceOutcome.PASSED,
        passed_case_refs=("case:counterexample",), failed_case_refs=(), counterexample_refs=(),
        proof_refs=("proof:counterexample",), failure_frontier_refs=(), snapshot_revision=0,
        boot_fingerprint="none", overlay_fingerprint="none", runner_ref="runner:test", runner_revision="1",
        independent_lineage_refs=("lineage:independent",), environment_refs=("environment:test",),
    )
    evaluation = PromotionPolicyEngine().evaluate(
        package, (result,), EvidenceSummary((), ("evidence-link:counterexample",), (), (), (), ("lineage:counter",), 0.0, 1.0)
    )
    assert evaluation.decision.value == "block"
    assert any("uncovered_counterexamples" in item for item in evaluation.blocked_reasons)
