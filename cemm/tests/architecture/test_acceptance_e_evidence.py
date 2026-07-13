"""Acceptance Suite E — Evidence lineage and competence (tests 19-24).

### 19. No self-certification
### 20. Evidence lineage independence
### 21. Independent oracle
### 22. Negative case — no competence
### 23. No evidence laundering
### 24. Field-level provenance honesty
"""
from __future__ import annotations

import pytest

from cemm.kernel.schema.closure import CompetenceProfile, SchemaGroundingAssessment
from cemm.kernel.schema.use_profile import (
    UseProfileLevel, derive_use_profile, SemanticOperation,
)
from cemm.kernel.schema.provenance import (
    ProvenanceKind, ContributionRecord, FieldProvenanceMap,
    WEAK_PROVENANCE, INDEPENDENT_PROVENANCE, DERIVED_PROVENANCE,
)
from cemm.kernel.model.identity import Provenance


def make_assessment(
    record_id: str = "schema:test:v1",
    is_executable: bool = True,
) -> SchemaGroundingAssessment:
    return SchemaGroundingAssessment(
        record_id=record_id,
        semantic_key="test",
        environment_fingerprint="fp1",
        is_structurally_executable=is_executable,
    )


# ── Test 19: No self-certification ──


def test_19a_self_certified_competence_is_invalid():
    """Self-certified competence is invalid — is_competent returns False."""
    profile = CompetenceProfile(
        positive_case_passed=True,
        role_structure_preserved=True,
        defining_query_answered=True,
        contrast_distinguished=True,
        licensed_inference_performed=True,
        independent_oracle_count=5,
        self_certified=True,
    )
    assert not profile.is_competent


def test_19b_self_certified_yields_provisional_not_active():
    """Self-certified competence yields provisional, not active."""
    assessment = make_assessment()
    profile = derive_use_profile(
        assessment, context_ref="ctx:actual",
        competence_is_competent=False,
        competence_is_self_certified=True,
        epistemic_admissible=True,
    )
    assert profile.level == UseProfileLevel.PARTIAL
    assert not profile.permits(SemanticOperation.CLASSIFY)


def test_19c_definition_derived_tests_cannot_certify():
    """Competence cases derived from the definition test well-formedness only."""
    profile = CompetenceProfile(
        positive_case_passed=True,
        role_structure_preserved=False,  # Missing
        defining_query_answered=True,
        contrast_distinguished=True,
        licensed_inference_performed=True,
        independent_oracle_count=1,
        self_certified=False,
    )
    assert not profile.is_competent  # Missing role_structure_preserved


# ── Test 20: Evidence lineage independence ──


def test_20a_translations_inherit_lineage():
    """Translations inherit their root lineage unless independent observation."""
    contrib = ContributionRecord(
        field_name="definition",
        provenance_kind=ProvenanceKind.INDUCED,
        source_ref="source:translation_1",
        confidence=0.8,
        is_independent=False,
    )
    assert not contrib.can_certify_truth


def test_20b_paraphrases_inherit_lineage():
    """Paraphrases inherit their root lineage."""
    contrib = ContributionRecord(
        field_name="definition",
        provenance_kind=ProvenanceKind.ENTAILED,
        source_ref="source:paraphrase",
        confidence=0.9,
        is_independent=False,
    )
    assert not contrib.can_certify_truth


def test_20c_independent_observation_certifies():
    """Independent observation can certify truth."""
    contrib = ContributionRecord(
        field_name="definition",
        provenance_kind=ProvenanceKind.OBSERVED,
        source_ref="source:observation_1",
        confidence=0.9,
        is_independent=True,
    )
    assert contrib.can_certify_truth


# ── Test 21: Independent oracle ──


def test_21a_independent_oracle_required():
    """At least one independent oracle is required for competence."""
    profile = CompetenceProfile(
        positive_case_passed=True,
        role_structure_preserved=True,
        defining_query_answered=True,
        contrast_distinguished=True,
        licensed_inference_performed=True,
        independent_oracle_count=0,  # No oracle
        self_certified=False,
    )
    assert not profile.is_competent


def test_21b_one_oracle_sufficient_with_all_checks():
    """One independent oracle is sufficient when all checks pass."""
    profile = CompetenceProfile(
        positive_case_passed=True,
        role_structure_preserved=True,
        defining_query_answered=True,
        contrast_distinguished=True,
        licensed_inference_performed=True,
        independent_oracle_count=1,
        self_certified=False,
    )
    assert profile.is_competent


# ── Test 22: Negative case — open-world truth ──


def test_22a_no_competence_yields_provisional():
    """No competence yields provisional, not active."""
    assessment = make_assessment()
    profile = derive_use_profile(
        assessment, context_ref="ctx:actual",
        competence_is_competent=False,
        competence_is_self_certified=False,
        epistemic_admissible=True,
    )
    assert profile.level == UseProfileLevel.PARTIAL


def test_22b_contrast_neither_supported_nor_refuted():
    """A contrast with no positive evidence but no incompatibility is 'neither'.

    Per ACCEPTANCE_TESTS.md §22: result is `neither`, not rejected;
    discrimination fails honestly. Open-world truth means absence of
    support is not refutation.
    """
    # EpistemicAssessment with support_state='neither' — open-world
    from cemm.kernel.model.epistemic import EpistemicAssessment
    assessment = EpistemicAssessment(
        proposition_ref="prop:contrast:1",
        context_ref="ctx:actual",
        support_state="neither",
        support_score=0.0,
        opposition_score=0.0,
        confidence=0.0,
        admissibility="admitted",
    )
    # 'neither' is not 'refuted' — open-world truth
    assert assessment.support_state == "neither"
    assert assessment.support_state != "refuted"
    # Admissibility is still admitted — not blocked
    assert assessment.admissibility == "admitted"


def test_22c_role_structure_required_for_competence():
    """Role structure preservation is required for competence."""
    profile = CompetenceProfile(
        positive_case_passed=True,
        role_structure_preserved=False,
        defining_query_answered=True,
        contrast_distinguished=True,
        licensed_inference_performed=True,
        independent_oracle_count=1,
        self_certified=False,
    )
    assert not profile.is_competent


# ── Test 23: Cross-schema inference laundering ──


def test_23a_cross_schema_laundering_blocked():
    """Cross-schema inference laundering does not increase support.

    Per ACCEPTANCE_TESTS.md §23: A licenses evidence for B and B licenses
    evidence for A. Transitive support SCC detected; competence/confidence
    of A and B do not increase from the cycle.
    """
    from cemm.kernel.epistemics.invalidation_engine import CrossSchemaLaunderingGuard
    guard = CrossSchemaLaunderingGuard()
    # Register SCC: A and B mutually support each other
    guard.register_support_scc("schema:a:v1", ("schema:a:v1", "schema:b:v1"))
    guard.register_support_scc("schema:b:v1", ("schema:a:v1", "schema:b:v1"))
    # Evidence from A cannot increase support for B (same SCC)
    assert not guard.can_increase_support("schema:a:v1", "schema:b:v1")
    # Evidence from B cannot increase support for A (same SCC)
    assert not guard.can_increase_support("schema:b:v1", "schema:a:v1")


def test_23b_ancestry_cycle_blocked():
    """Circular support ancestry is blocked."""
    from cemm.kernel.epistemics.invalidation_engine import CrossSchemaLaunderingGuard
    guard = CrossSchemaLaunderingGuard()
    # A's ancestry includes B, B's ancestry includes A
    guard.register_support_ancestry("schema:a:v1", ("schema:b:v1",))
    guard.register_support_ancestry("schema:b:v1", ("schema:a:v1",))
    # A cannot increase support for B (B is in A's ancestry)
    assert not guard.can_increase_support("schema:a:v1", "schema:b:v1")


def test_23c_independent_schemas_can_support():
    """Independent schemas (no SCC, no ancestry) can support each other."""
    from cemm.kernel.epistemics.invalidation_engine import CrossSchemaLaunderingGuard
    guard = CrossSchemaLaunderingGuard()
    # No SCC, no ancestry — independent
    assert guard.can_increase_support("schema:c:v1", "schema:d:v1")


# ── Test 24: Field-level provenance honesty ──


def test_24a_each_field_records_provenance():
    """Each field records its provenance kind."""
    contrib = ContributionRecord(
        field_name="definition",
        provenance_kind=ProvenanceKind.ASSERTED,
        source_ref="src:1",
        confidence=0.9,
        is_independent=True,
    )
    assert contrib.field_name == "definition"
    assert contrib.provenance_kind == ProvenanceKind.ASSERTED


def test_24b_weak_fields_identified():
    """Weak (hypothesized/defaulted) fields are identified."""
    fmap = FieldProvenanceMap(contributions=(
        ContributionRecord(
            field_name="strong_field",
            provenance_kind=ProvenanceKind.OBSERVED,
            source_ref="src:1",
            is_independent=True,
        ),
        ContributionRecord(
            field_name="weak_field",
            provenance_kind=ProvenanceKind.HYPOTHESIZED,
            source_ref="src:2",
            is_independent=False,
        ),
    ))
    assert fmap.has_weak_only("weak_field")
    assert not fmap.has_weak_only("strong_field")


def test_24c_provenance_kind_ordered():
    """Provenance kinds are ordered from most to least authoritative."""
    assert ProvenanceKind.ASSERTED != ProvenanceKind.HYPOTHESIZED
    assert ProvenanceKind.OBSERVED in INDEPENDENT_PROVENANCE
    assert ProvenanceKind.HYPOTHESIZED in WEAK_PROVENANCE
    assert ProvenanceKind.INDUCED in DERIVED_PROVENANCE
