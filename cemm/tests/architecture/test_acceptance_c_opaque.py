"""Acceptance Suite C — Opaque concepts and definitions (tests 8-13).

From ACCEPTANCE_TESTS.md:
### 8. Opaque relation preservation
### 9. Claim count does not ground meaning
### 10. Complete single definition can be structurally sufficient
### 11. False but compositional definition
### 12. Typical feature is not identity
### 13. Expressiveness blocker
"""
from __future__ import annotations

import pytest

from cemm.kernel.schema.store import SemanticSchemaStore
from cemm.kernel.schema.envelope import SchemaEnvelope
from cemm.kernel.schema.closure import (
    GroundedDefinitionClosure, RecursiveComponent,
    SchemaGroundingAssessment, ClosureCheckResult, ClosureCheckStatus,
)
from cemm.kernel.schema.use_profile import (
    SchemaUseProfile, UseProfileLevel, derive_use_profile,
    SemanticOperation, OPAQUE_OPERATIONS, PARTIAL_OPERATIONS,
    ACTIVE_OPERATIONS,
)
from cemm.kernel.schema.pattern_assessment import (
    PatternFunction, PatternAssessment, assess_patterns,
)
from cemm.kernel.schema.grounding_spec import (
    SemanticPattern, GroundingSpecification,
)
from cemm.kernel.model.identity import Provenance


# ── Helpers ────────────────────────────────────────────────────────


def make_envelope(
    record_id: str, semantic_key: str, status: str = "candidate",
    schema_kind: str = "predicate",
) -> SchemaEnvelope:
    return SchemaEnvelope(
        record_id=record_id,
        semantic_key=semantic_key,
        schema_kind=schema_kind,
        status=status,
        provenance=Provenance(source_id="boot", source_kind="boot"),
    )


def make_assessment(
    record_id: str = "schema:test:v1",
    is_executable: bool = False,
    blockers: tuple[str, ...] = (),
) -> SchemaGroundingAssessment:
    return SchemaGroundingAssessment(
        record_id=record_id,
        semantic_key="test",
        environment_fingerprint="fp1",
        is_structurally_executable=is_executable,
        blocker_reasons=blockers,
    )


# ── Test 8: Opaque relation preservation ──


def test_8a_opaque_schema_not_in_store():
    """Neither dax nor wug schema exists in an empty store."""
    store = SemanticSchemaStore()
    assert store.get("schema:dax:v1") is None
    assert store.get("schema:wug:v1") is None


def test_8b_opaque_use_profile_blocks_classification():
    """Opaque profile blocks classification and definition answers."""
    assessment = make_assessment(is_executable=False, blockers=("No schema",))
    profile = derive_use_profile(assessment, context_ref="ctx:actual")
    assert profile.level == UseProfileLevel.OPAQUE
    assert not profile.permits(SemanticOperation.CLASSIFY)
    assert not profile.permits(SemanticOperation.ANSWER_DEFINING_QUERY)
    assert not profile.permits(SemanticOperation.LICENSED_INFERENCE)


def test_8c_opaque_profile_permits_quote_and_preserve():
    """Opaque profiles permit quote, preserve, search, probe."""
    assessment = make_assessment(is_executable=False)
    profile = derive_use_profile(assessment, context_ref="ctx:actual")
    assert profile.permits(SemanticOperation.QUOTE)
    assert profile.permits(SemanticOperation.PRESERVE)
    assert profile.permits(SemanticOperation.SEARCH)
    assert profile.permits(SemanticOperation.PROBE)


# ── Test 9: Claim count does not ground meaning ──


def test_9a_circular_closure_not_active():
    """Circular definitions (leader→chief→leader) cannot activate jointly."""
    component = RecursiveComponent(
        component_id="rc_circular",
        member_refs=("schema:leader:v1", "schema:chief:v1"),
        classification="unsupported_non_monotone",
        has_external_anchor=False,
    )
    assert not component.can_activate_jointly


def test_9b_support_count_does_not_defeat_ungrounded():
    """Support count cannot defeat ungrounded/circular closure."""
    component = RecursiveComponent(
        component_id="rc1",
        member_refs=("schema:leader:v1", "schema:chief:v1"),
        classification="unsupported_non_monotone",
        has_external_anchor=False,
        has_non_redundant_contribution=True,
        has_type_consistent_mapping=True,
        has_declared_semantics=True,
    )
    assert not component.can_activate_jointly


# ── Test 10: Complete single definition ──


def test_10a_structural_closure_may_pass():
    """Structural closure may pass for a complete definition."""
    closure = GroundedDefinitionClosure()
    env = make_envelope("schema:complete:v1", "complete", status="candidate")
    spec = GroundingSpecification(semantic_family="relation")
    result = closure.assess(env, grounding_spec=spec)
    assert any(
        r.status == ClosureCheckStatus.PASSED
        for r in result.check_results
    )


def test_10b_same_lineage_yields_provisional():
    """Same-lineage (self-certified) tests yield provisional, not active."""
    assessment = make_assessment(is_executable=True)
    profile = derive_use_profile(
        assessment,
        context_ref="ctx:actual",
        competence_is_competent=False,
        competence_is_self_certified=True,
        epistemic_admissible=True,
    )
    assert profile.level == UseProfileLevel.PARTIAL
    assert not profile.permits(SemanticOperation.CLASSIFY)


def test_10c_admission_and_competence_separate():
    """Actual-context admission and independent competence remain separate."""
    assessment = make_assessment(is_executable=True)

    # Epistemic admissible but not competent → partial
    profile1 = derive_use_profile(
        assessment, context_ref="ctx:actual",
        competence_is_competent=False, epistemic_admissible=True,
    )
    assert profile1.level == UseProfileLevel.PARTIAL

    # Competent but not epistemic admissible → opaque
    profile2 = derive_use_profile(
        assessment, context_ref="ctx:actual",
        competence_is_competent=True, epistemic_admissible=False,
    )
    assert profile2.level == UseProfileLevel.OPAQUE

    # Both → active
    profile3 = derive_use_profile(
        assessment, context_ref="ctx:actual",
        competence_is_competent=True, epistemic_admissible=True,
    )
    assert profile3.level == UseProfileLevel.ACTIVE


# ── Test 11: False but compositional definition ──


def test_11a_user_theory_structurally_executable_but_not_admitted():
    """User-attributed theory may be structurally executable but not admitted
    as actual-world meaning."""
    assessment = make_assessment(is_executable=True)
    profile = derive_use_profile(
        assessment, context_ref="ctx:actual",
        competence_is_competent=False, epistemic_admissible=False,
    )
    assert profile.level == UseProfileLevel.OPAQUE
    assert not profile.permits(SemanticOperation.CLASSIFY)


def test_11b_global_schema_not_overwritten():
    """Global/audited schema is not overwritten by user theory."""
    store = SemanticSchemaStore()
    global_schema = make_envelope("schema:doctor:v1", "doctor", status="active")
    store.register(global_schema)

    user_schema = make_envelope("schema:doctor_user:v1", "doctor", status="candidate")
    store.register(user_schema)

    env = store.get("schema:doctor:v1")
    assert env is not None
    assert env.status == "active"


# ── Test 12: Typical feature is not identity ──


def test_12a_typical_is_not_constitutive():
    """Pattern function 'typical' is not constitutive identity."""
    assert PatternFunction.TYPICAL != PatternFunction.CONSTITUTIVE
    assert PatternFunction.TYPICAL != PatternFunction.IDENTITY


def test_12b_typical_does_not_close_definition():
    """Typical patterns cannot close definitions — no constitutive pattern."""
    typical_pattern = SemanticPattern(
        pattern_kind="p1",
        function=PatternFunction.TYPICAL.value,
        expression="flies",
    )
    spec = GroundingSpecification(semantic_family="kind")
    assessment = assess_patterns((typical_pattern,), spec)
    assert not assessment.has_constitutive
    assert len(assessment.blocker_reasons) > 0


def test_12c_absence_not_refutation():
    """Absence of flight evidence is not refutation — typical is non-constitutive."""
    typical_pattern = SemanticPattern(
        pattern_kind="p1",
        function=PatternFunction.TYPICAL.value,
        expression="flies",
    )
    spec = GroundingSpecification(semantic_family="kind")
    assessment = assess_patterns((typical_pattern,), spec)
    assert assessment.non_constitutive_count >= 1


# ── Test 13: Expressiveness blocker ──


def test_13a_unsupported_non_monotone_produces_blocker():
    """Unsupported non-monotone recursive components cannot activate jointly."""
    component = RecursiveComponent(
        component_id="rc_neg",
        member_refs=("schema:a:v1", "schema:b:v1"),
        classification="unsupported_non_monotone",
        has_external_anchor=False,
        has_forbidden_dependency=True,
    )
    assert not component.can_activate_jointly


def test_13b_closure_failure_produces_blockers():
    """A failed closure check produces explicit blocker reasons."""
    closure = GroundedDefinitionClosure()
    env = make_envelope("schema:blocked:v1", "blocked", status="candidate")
    spec = GroundingSpecification(semantic_family="")
    result = closure.assess(env, grounding_spec=spec)
    assert not result.is_structurally_executable
    assert len(result.blocker_reasons) > 0


def test_13c_no_silent_approximation():
    """Unsupported constructs produce exact blockers, not silent approximation."""
    closure = GroundedDefinitionClosure()
    env = make_envelope("schema:unsupported:v1", "unsupported", status="candidate")
    spec = GroundingSpecification(semantic_family="")
    result = closure.assess(env, grounding_spec=spec)
    assert not result.is_structurally_executable
    assert len(result.blocker_reasons) > 0
    for blocker in result.blocker_reasons:
        assert isinstance(blocker, str)
        assert len(blocker) > 0
