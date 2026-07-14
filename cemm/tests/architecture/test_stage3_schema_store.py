"""Stage 3 exit gate tests — make the schema store real.

Tests verify:
1. No direct activation bypass — activate() requires assessment refs
2. Unresolved dependency blocks closure
3. Self-derived competence tests cannot activate
4. Boot store is non-empty and validated
5. All active records have assessment/admissibility refs
6. Historical revisions remain resolvable
7. Transaction rollback works
8. Persistence save/load works
9. Closure checker enforces structural executability
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import replace
from typing import Any

import pytest

from cemm.kernel.schema.store import SemanticSchemaStore
from cemm.kernel.schema.envelope import SchemaEnvelope, SchemaDependency
from cemm.kernel.schema.activation import ActivationStatus
from cemm.kernel.schema.closure import (
    GroundedDefinitionClosure,
    SchemaGroundingAssessment,
    ClosureCheckStatus,
    CompetenceProfile,
)
from cemm.kernel.schema.competence import (
    CompetenceHarness,
    CompetenceCase,
    CompetenceCheckKind,
    ContrastResult,
)
from cemm.kernel.schema.grounding_spec import GroundingSpecification, SemanticPattern
from cemm.kernel.schema.provenance import FieldProvenanceMap, ProvenanceKind
from cemm.kernel.schema.use_profile import (
    derive_use_profile,
    UseProfileLevel,
    SemanticOperation,
)
from cemm.kernel.schema.dependency import CycleClass
from cemm.kernel.model.identity import Scope, ScopeLevel, Provenance, Permission
from cemm.kernel.boot.manifest import build_boot_manifest
from cemm.kernel.boot.validation import BootValidator, BootStatus


# ── Helpers ────────────────────────────────────────────────────────


def make_envelope(
    record_id: str = "schema:test:v1",
    semantic_key: str = "test",
    status: str = "candidate",
    version: int = 1,
    scope: Scope | None = None,
    confidence: float = 0.0,
) -> SchemaEnvelope:
    return SchemaEnvelope(
        record_id=record_id,
        semantic_key=semantic_key,
        schema_kind="test_kind",
        status=status,
        scope=scope or Scope(level=ScopeLevel.GLOBAL),
        version=version,
        confidence=confidence,
        provenance=Provenance(source_id="test"),
        permission=Permission.public(),
    )


def make_grounding_spec(semantic_family: str = "test_family") -> GroundingSpecification:
    return GroundingSpecification(
        semantic_family=semantic_family,
        required_definition_fields=("field1",),
        allowed_cycle_classes=frozenset({"positive_monotone_recursive"}),
        minimum_independent_oracle_classes=frozenset({"invariant"}),
    )


# ── Gate 1: No direct activation bypass ────────────────────────────


def test_activate_without_assessment_ref_blocked():
    """activate() must block when no grounding_assessment_ref is present."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:no_ref:v1", "no_ref")
    store.register(env)
    result = store.activate("schema:no_ref:v1", expected_revision=1)
    assert result.status == ActivationStatus.BLOCKED
    assert "grounding_assessment_ref" in result.detail


def test_activate_with_assessment_ref_succeeds():
    """activate_with_assessment() stamps refs and succeeds."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:with_ref:v1", "with_ref")
    store.register(env)
    result = store.activate_with_assessment(
        "schema:with_ref:v1", expected_revision=1,
        grounding_assessment_ref="assessment:1",
        competence_assessment_ref="competence:1",
        epistemic_admissibility_ref="epistemic:1",
    )
    assert result.status == ActivationStatus.SUCCESS
    activated = store.get("schema:with_ref:v1")
    assert activated.grounding_assessment_ref == "assessment:1"
    assert activated.competence_assessment_ref == "competence:1"
    assert activated.epistemic_admissibility_ref == "epistemic:1"


def test_activate_with_failed_closure_blocked():
    """activate_with_assessment() must block when grounding assessment
    indicates not structurally executable."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:failed_closure:v1", "failed_closure")
    store.register(env)

    # Create a mock assessment that is NOT structurally executable
    failed_assessment = SchemaGroundingAssessment(
        record_id="schema:failed_closure:v1",
        semantic_key="failed_closure",
        environment_fingerprint="test",
        is_structurally_executable=False,
        blocker_reasons=("Semantic family not resolved",),
    )
    result = store.activate_with_assessment(
        "schema:failed_closure:v1", expected_revision=1,
        grounding_assessment_ref="assessment:failed",
        grounding_assessment=failed_assessment,
    )
    assert result.status == ActivationStatus.BLOCKED
    assert "structural executability" in result.detail


def test_activate_with_self_certified_competence_blocked():
    """activate_with_assessment() must block when competence is self-certified."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:self_cert:v1", "self_cert")
    store.register(env)

    class MockCompetence:
        is_self_certified = True

    result = store.activate_with_assessment(
        "schema:self_cert:v1", expected_revision=1,
        grounding_assessment_ref="assessment:1",
        competence_assessment=MockCompetence(),
    )
    assert result.status == ActivationStatus.BLOCKED
    assert "self-certified" in result.detail


# ── Gate 2: Unresolved dependency blocks closure ───────────────────


def test_unresolved_dependency_blocks_closure():
    """Closure check #5 must FAIL when dependencies don't resolve in store."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:dep_test:v1", "dep_test")
    store.register(env)

    closure = GroundedDefinitionClosure()
    spec = make_grounding_spec()
    assessment = closure.assess(
        envelope=env,
        grounding_spec=spec,
        dependencies=("schema:nonexistent:v1",),
        store=store,
    )
    check5 = [r for r in assessment.check_results if r.check_number == 5][0]
    assert check5.status == ClosureCheckStatus.FAILED
    assert not assessment.is_structurally_executable


def test_resolved_dependency_passes_closure():
    """Closure check #5 must PASS when dependencies resolve in store."""
    store = SemanticSchemaStore()
    dep_env = make_envelope("schema:dep_target:v1", "dep_target")
    store.register(dep_env)
    env = make_envelope("schema:dep_user:v1", "dep_user")
    store.register(env)

    closure = GroundedDefinitionClosure()
    spec = make_grounding_spec()
    assessment = closure.assess(
        envelope=env,
        grounding_spec=spec,
        dependencies=("schema:dep_target:v1",),
        store=store,
    )
    check5 = [r for r in assessment.check_results if r.check_number == 5][0]
    assert check5.status == ClosureCheckStatus.PASSED


# ── Gate 3: Self-derived competence tests cannot activate ──────────


def test_self_certified_competence_cannot_activate():
    """Competence harness must detect self-certification and block activation."""
    harness = CompetenceHarness()
    cases = (
        CompetenceCase(
            case_id="case1",
            check_kind=CompetenceCheckKind.POSITIVE_CASE,
            input_lineage="same_path",
            oracle_lineage="same_path",
            is_independent=False,
            passed=True,
        ),
    )
    assessment = harness.assess(cases, implementation_path="same_path")
    assert assessment.is_self_certified
    assert not assessment.is_competent


def test_independent_competence_can_activate():
    """Competence with independent oracle passes and can activate."""
    harness = CompetenceHarness()
    cases = (
        CompetenceCase(
            case_id="case1",
            check_kind=CompetenceCheckKind.POSITIVE_CASE,
            input_lineage="input_path",
            oracle_lineage="independent_oracle",
            is_independent=True,
            passed=True,
        ),
        CompetenceCase(
            case_id="case2",
            check_kind=CompetenceCheckKind.ROLE_STRUCTURE,
            input_lineage="input_path",
            oracle_lineage="independent_oracle",
            is_independent=True,
            passed=True,
        ),
        CompetenceCase(
            case_id="case3",
            check_kind=CompetenceCheckKind.DEFINING_QUERY,
            input_lineage="input_path",
            oracle_lineage="independent_oracle",
            is_independent=True,
            passed=True,
        ),
        CompetenceCase(
            case_id="case4",
            check_kind=CompetenceCheckKind.CONTRAST,
            input_lineage="input_path",
            oracle_lineage="independent_oracle",
            is_independent=True,
            passed=True,
            contrast_result=ContrastResult.SUPPORTED,
        ),
        CompetenceCase(
            case_id="case5",
            check_kind=CompetenceCheckKind.LICENSED_INFERENCE,
            input_lineage="input_path",
            oracle_lineage="independent_oracle",
            is_independent=True,
            passed=True,
        ),
    )
    assessment = harness.assess(cases, implementation_path="input_path")
    assert not assessment.is_self_certified
    assert assessment.is_competent
    assert assessment.independent_oracle_count >= 1


# ── Gate 4: Boot store is non-empty and validated ──────────────────


def test_boot_store_non_empty():
    """Runtime with boot loading must have a non-empty store."""
    from cemm.app.runtime import Runtime
    rt = Runtime()
    assert len(rt.schema_store) > 0
    assert rt.boot_report is not None
    assert rt.boot_report.status == BootStatus.READY


def test_boot_store_validated():
    """Boot validation report must have passed foundation tests."""
    from cemm.app.runtime import Runtime
    rt = Runtime()
    assert rt.boot_report.foundation_tests_passed
    assert len(rt.boot_report.halted_reasons) == 0


def test_boot_loads_all_schema_kinds():
    """Boot must load entity_kinds, contexts, operations, policies, metalanguage."""
    from cemm.app.runtime import Runtime
    rt = Runtime()
    store = rt.schema_store
    kinds = {"entity_kind", "state_dimension", "context", "operation", "policy", "metalanguage"}
    for kind in kinds:
        records = store.records_by_kind(kind)
        assert len(records) > 0, f"No records of kind {kind}"


def test_boot_no_load_skips_boot():
    """Runtime with load_boot=False should have empty store."""
    from cemm.app.runtime import Runtime
    rt = Runtime(load_boot=False)
    assert len(rt.schema_store) == 0
    assert rt.boot_report is None


# ── Gate 5: All active records have assessment/admissibility refs ──


def test_active_records_have_assessment_refs():
    """All active records must have grounding_assessment_ref."""
    store = SemanticSchemaStore()
    env1 = make_envelope("schema:active1:v1", "active1")
    env2 = make_envelope("schema:active2:v1", "active2")
    store.register(env1)
    store.register(env2)

    store.activate_with_assessment(
        "schema:active1:v1", expected_revision=1,
        grounding_assessment_ref="assessment:1",
    )
    store.activate_with_assessment(
        "schema:active2:v1", expected_revision=1,
        grounding_assessment_ref="assessment:2",
    )

    for env in store.records_by_status("active"):
        assert env.grounding_assessment_ref, (
            f"Active record {env.record_id} has no grounding_assessment_ref"
        )


# ── Gate 6: Historical revisions remain resolvable ─────────────────


def test_superseded_revisions_remain_resolvable():
    """Superseded revisions must remain resolvable via get()."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:hist:v1", "hist")
    store.register(env)
    store.activate_with_assessment(
        "schema:hist:v1", expected_revision=1,
        grounding_assessment_ref="assessment:hist",
    )
    store.supersede("schema:hist:v1", "schema:hist:v2", reason="new version")

    # Original revision must still be resolvable
    old = store.get("schema:hist:v1")
    assert old is not None
    assert old.status == "superseded"


# ── Gate 7: Transaction rollback ───────────────────────────────────


def test_transaction_commit():
    """Transaction commits on clean exit."""
    store = SemanticSchemaStore()
    with store.transaction():
        env = make_envelope("schema:txn:v1", "txn")
        store.register(env)
    assert store.get("schema:txn:v1") is not None


def test_transaction_rollback():
    """Transaction rolls back on exception."""
    store = SemanticSchemaStore()
    try:
        with store.transaction():
            env = make_envelope("schema:rollback:v1", "rollback")
            store.register(env)
            raise ValueError("test error")
    except ValueError:
        pass

    assert store.get("schema:rollback:v1") is None
    assert len(store) == 0


def test_transaction_nested_rollback():
    """Transaction rollback restores all state including revisions."""
    store = SemanticSchemaStore()
    env1 = make_envelope("schema:keep:v1", "keep")
    store.register(env1)
    rev_before = store.store_revision

    try:
        with store.transaction():
            env2 = make_envelope("schema:discard:v1", "discard")
            store.register(env2)
            raise RuntimeError("rollback test")
    except RuntimeError:
        pass

    assert store.get("schema:keep:v1") is not None
    assert store.get("schema:discard:v1") is None
    assert store.store_revision == rev_before


# ── Gate 8: Persistence ────────────────────────────────────────────


def test_persistence_save_load():
    """Store state must survive save/load cycle."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:persist:v1", "persist")
    store.register(env)
    store.activate_with_assessment(
        "schema:persist:v1", expected_revision=1,
        grounding_assessment_ref="assessment:persist",
    )
    store.index_lexical_form("persist", "en", "persist")

    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        path = f.name

    try:
        store.save_to_file(path)
        store2 = SemanticSchemaStore()
        store2.load_from_file(path)

        assert len(store2) == len(store)
        env2 = store2.get("schema:persist:v1")
        assert env2 is not None
        assert env2.status == "active"
        assert env2.grounding_assessment_ref == "assessment:persist"
        assert store2.lookup_lexical_form("persist", "en") == ("persist",)
        assert store2.store_revision == store.store_revision
    finally:
        os.unlink(path)


# ── Gate 9: Use profile derivation ─────────────────────────────────


def test_use_profile_opaque_for_non_executable():
    """Use profile must be OPAQUE for non-structurally-executable schemas."""
    assessment = SchemaGroundingAssessment(
        record_id="schema:opaque:v1",
        semantic_key="opaque",
        environment_fingerprint="test",
        is_structurally_executable=False,
        blocker_reasons=("Missing fields",),
    )
    profile = derive_use_profile(assessment, context_ref="ctx:1")
    assert profile.level == UseProfileLevel.OPAQUE
    assert profile.permits(SemanticOperation.QUOTE)
    assert not profile.permits(SemanticOperation.CLASSIFY)


def test_use_profile_active_for_executable_competent():
    """Use profile must be ACTIVE for structurally executable + competent schemas."""
    assessment = SchemaGroundingAssessment(
        record_id="schema:active:v1",
        semantic_key="active",
        environment_fingerprint="test",
        is_structurally_executable=True,
    )
    profile = derive_use_profile(
        assessment,
        context_ref="ctx:1",
        competence_is_competent=True,
        epistemic_admissible=True,
        scope_accessible=True,
    )
    assert profile.level == UseProfileLevel.ACTIVE
    assert profile.permits(SemanticOperation.CLASSIFY)
    assert profile.permits(SemanticOperation.LICENSED_INFERENCE)
    assert not profile.permits(SemanticOperation.EXECUTE)


def test_use_profile_partial_for_incompetent():
    """Use profile must be PARTIAL when competence not met."""
    assessment = SchemaGroundingAssessment(
        record_id="schema:partial:v1",
        semantic_key="partial",
        environment_fingerprint="test",
        is_structurally_executable=True,
    )
    profile = derive_use_profile(
        assessment,
        context_ref="ctx:1",
        competence_is_competent=False,
    )
    assert profile.level == UseProfileLevel.PARTIAL
    assert profile.permits(SemanticOperation.TYPED_REFERENCE)
    assert not profile.permits(SemanticOperation.CLASSIFY)


def test_use_profile_execute_never_permitted():
    """EXECUTE must never be permitted by profile alone."""
    assessment = SchemaGroundingAssessment(
        record_id="schema:exec:v1",
        semantic_key="exec",
        environment_fingerprint="test",
        is_structurally_executable=True,
    )
    profile = derive_use_profile(
        assessment,
        competence_is_competent=True,
        epistemic_admissible=True,
        scope_accessible=True,
    )
    assert not profile.permits_execute()
    assert not profile.permits(SemanticOperation.EXECUTE)


# ── Gate 10: Closure checker with store ─────────────────────────────


def test_closure_with_store_resolves_dependencies():
    """Closure checker with store parameter resolves dependencies correctly."""
    store = SemanticSchemaStore()
    # Register a foundation schema
    foundation = make_envelope("schema:foundation:v1", "foundation")
    store.register(foundation)
    # Register a dependent schema
    dependent = make_envelope("schema:dependent:v1", "dependent")
    store.register(dependent)

    closure = GroundedDefinitionClosure()
    spec = make_grounding_spec()
    assessment = closure.assess(
        envelope=dependent,
        grounding_spec=spec,
        dependencies=("schema:foundation:v1",),
        store=store,
    )
    check5 = [r for r in assessment.check_results if r.check_number == 5][0]
    assert check5.status == ClosureCheckStatus.PASSED


def test_closure_without_store_blocks_on_deps():
    """Closure checker without store returns BLOCKED for dependencies."""
    env = make_envelope("schema:blocked:v1", "blocked")
    closure = GroundedDefinitionClosure()
    spec = make_grounding_spec()
    assessment = closure.assess(
        envelope=env,
        grounding_spec=spec,
        dependencies=("schema:unknown:v1",),
    )
    check5 = [r for r in assessment.check_results if r.check_number == 5][0]
    assert check5.status == ClosureCheckStatus.BLOCKED


# ── Gate 11: Boot validator dependency verification ────────────────


def test_boot_dependency_verification():
    """After boot registration, all dependencies should resolve."""
    store = SemanticSchemaStore()
    validator = BootValidator()
    manifest = build_boot_manifest()
    report = validator.validate_boot(store, manifest)
    validator.register_boot_schemas(store, manifest, report)

    unresolved, resolved = validator.verify_dependencies(store, manifest)
    # All dependencies should resolve after registration
    assert len(unresolved) == 0, f"Unresolved dependencies: {unresolved}"
    assert len(resolved) > 0  # At least some dependencies exist


# ── Regression: CAS failure must not stamp assessment refs ─────────


def test_cas_failure_does_not_stamp_refs():
    """Regression: if CAS fails in activate_with_assessment, the envelope
    must NOT retain assessment refs — otherwise activate() could bypass."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:cas_stamp:v1", "cas_stamp")
    store.register(env)

    # Simulate revision mismatch by setting a wrong expected revision
    result = store.activate_with_assessment(
        "schema:cas_stamp:v1", expected_revision=999,
        grounding_assessment_ref="assessment:should_not_stamp",
    )
    assert result.status == ActivationStatus.CAS_FAILED

    # Envelope must NOT have assessment refs stamped
    env_after = store.get("schema:cas_stamp:v1")
    assert env_after.grounding_assessment_ref == ""
    assert env_after.status == "candidate"


def test_cluster_activation_without_refs_blocked():
    """Regression: cluster activation must enforce assessment refs."""
    store = SemanticSchemaStore()
    env_a = make_envelope("schema:no_ref_a:v1", "no_ref_a")
    env_b = make_envelope("schema:no_ref_b:v1", "no_ref_b")
    store.register(env_a)
    store.register(env_b)

    result = store.activate_cluster(
        ("schema:no_ref_a:v1", "schema:no_ref_b:v1"),
        {"schema:no_ref_a:v1": 1, "schema:no_ref_b:v1": 1},
    )
    assert result.status == ActivationStatus.BLOCKED
    assert "grounding_assessment_ref" in result.detail


def test_stamp_assessment_refs_does_not_activate():
    """stamp_assessment_refs must not change status or increment revision."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:stamp:v1", "stamp")
    store.register(env)
    rev_before = store.get_revision("schema:stamp:v1")

    assert store.stamp_assessment_refs("schema:stamp:v1", "assessment:stamp")
    env_after = store.get("schema:stamp:v1")
    assert env_after.status == "candidate"  # Status unchanged
    assert env_after.grounding_assessment_ref == "assessment:stamp"
    assert store.get_revision("schema:stamp:v1") == rev_before  # Revision unchanged
