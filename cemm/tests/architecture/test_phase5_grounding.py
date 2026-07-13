"""Phase 5 gate tests: Grounded understanding and schema use.

Gates (from IMPLEMENTATION_PLAN.md Phase 5):
- a known lexeme or schema ref does not imply understanding;
- self-derived cases cannot produce active status;
- typical properties do not close definitions;
- unsupported constructs produce explicit blockers;
- opaque/provisional meanings remain safely preservable.

Additional guardrail tests from AGENTS.md §7.1-7.6, UNDERSTANDING_PIPELINE.md §4-10:
- Field-level provenance tracks kind (asserted/observed/hypothesized/etc.)
- Pattern function and strength are independent
- Typical/default/incidental patterns never satisfy constitutive requirements
- SchemaGroundingAssessment is a derived control record, not an activation authority
- Competence cases from definition test well-formedness only
- Self-certification forbidden — same path cannot generate input, expected, and judge
- Open-world negative cases: 'neither' is not rejection
- SchemaUseProfile: opaque/partial/active/causal levels with correct operations
- EXECUTE never permitted by profile alone
- Recursive component classification: inverse/positive-monotone/stratified/unsupported
- GroundingResolver does not activate schemas
- Scope is not truth precedence
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cemm.kernel.schema.provenance import (
    ProvenanceKind, ContributionRecord, FieldProvenanceMap,
    WEAK_PROVENANCE, INDEPENDENT_PROVENANCE, DERIVED_PROVENANCE,
)
from cemm.kernel.schema.pattern_assessment import (
    PatternFunction, PatternStrength, assess_patterns,
    is_constitutive, can_satisfy_constitutive_requirement,
    has_constitutive_pattern, has_differentiator,
)
from cemm.kernel.schema.grounding_spec import (
    GroundingSpecification, SemanticPattern,
)
from cemm.kernel.schema.closure import (
    SchemaGroundingAssessment, GroundedDefinitionClosure,
    CompetenceProfile, RecursiveComponent, ClosureCheckResult, ClosureCheckStatus,
)
from cemm.kernel.schema.competence import (
    CompetenceHarness, CompetenceCase, CompetenceCheckKind,
    CompetenceAssessment, ContrastResult,
)
from cemm.kernel.schema.use_profile import (
    SchemaUseProfile, derive_use_profile, UseProfileLevel, SemanticOperation,
    OPAQUE_OPERATIONS, PARTIAL_OPERATIONS, ACTIVE_OPERATIONS, CAUSAL_OPERATIONS,
)
from cemm.kernel.schema.store import SemanticSchemaStore
from cemm.kernel.schema.envelope import SchemaEnvelope
from cemm.kernel.schema.resolver import SchemaResolver
from cemm.kernel.model.identity import Scope, ScopeLevel, Provenance
from cemm.kernel.understanding.grounding import (
    GroundingResolver, ReferentGrounding, DefinitionGrounding,
)


# ── Helpers ────────────────────────────────────────────────────────


def make_envelope(record_id: str, semantic_key: str, status: str = "candidate") -> SchemaEnvelope:
    return SchemaEnvelope(
        record_id=record_id,
        semantic_key=semantic_key,
        schema_kind="predicate",
        status=status,
        provenance=Provenance(source_id="boot", source_kind="boot"),
    )


def make_pattern(function: str = "typical", strength: str = "defeasible") -> SemanticPattern:
    return SemanticPattern(function=function, strength=strength)


# ── Gate 1: a known lexeme or schema ref does not imply understanding ──


def test_known_lexeme_does_not_imply_understanding():
    """A known lexeme or schema ref does not imply understanding.

    A schema may be registered and active but still not have a
    SchemaUseProfile at the ACTIVE level if competence is not met.
    """
    store = SemanticSchemaStore()
    env = make_envelope("schema:test:v1", "test", status="active")
    store.register(env)
    store.activate("schema:test:v1", expected_revision=1)
    store.index_lexical_form("test", "en", "test")

    resolver = GroundingResolver(store)
    # Ground the definition — even though the schema is active,
    # without competence assessment, use profile should be PARTIAL
    result = resolver.ground_definition("test")

    assert result.is_grounded is False  # Not understood yet
    assert result.use_profile is not None
    # Without competence, should be PARTIAL or OPAQUE, not ACTIVE
    assert result.use_profile.level != UseProfileLevel.ACTIVE


def test_known_schema_ref_still_needs_closure():
    """A schema ref alone doesn't mean the schema is structurally executable."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:unclosed:v1", "unclosed", status="candidate")
    store.register(env)

    resolver = GroundingResolver(store)
    result = resolver.ground_definition("unclosed")

    # Candidate schema without closure → not grounded
    assert result.is_grounded is False


# ── Gate 2: self-derived cases cannot produce active status ─────────


def test_self_certified_competence_is_invalid():
    """Self-derived competence cases cannot produce active status.

    The same implementation path cannot generate input meaning,
    expected graph, and pass judgment without an independent invariant.
    """
    harness = CompetenceHarness()

    cases = (
        CompetenceCase(
            case_id="c1",
            check_kind=CompetenceCheckKind.POSITIVE_CASE,
            input_lineage="impl_path_a",
            oracle_lineage="impl_path_a",  # Same path!
            is_independent=False,
            passed=True,
        ),
        CompetenceCase(
            case_id="c2",
            check_kind=CompetenceCheckKind.ROLE_STRUCTURE,
            input_lineage="impl_path_a",
            oracle_lineage="impl_path_a",
            is_independent=False,
            passed=True,
        ),
    )

    assessment = harness.assess(cases, implementation_path="impl_path_a")
    assert assessment.is_self_certified
    assert not assessment.is_competent


def test_self_certified_produces_partial_not_active():
    """Self-certified competence should produce PARTIAL use profile, not ACTIVE."""
    closure = GroundedDefinitionClosure()
    env = make_envelope("schema:selfcert:v1", "selfcert", status="active")

    grounding_spec = GroundingSpecification(
        semantic_family="predicate",
        allowed_cycle_classes=frozenset({"positive_monotone_recursive"}),
    )

    patterns = (make_pattern(function="constitutive"),)

    assessment = closure.assess(
        envelope=env,
        grounding_spec=grounding_spec,
        patterns=patterns,
    )

    # Self-certified competence
    profile = derive_use_profile(
        assessment=assessment,
        competence_is_competent=False,
        competence_is_self_certified=True,
    )

    assert profile.level == UseProfileLevel.PARTIAL
    assert "self-certified" in profile.limitations[0].lower()


def test_independent_competence_can_produce_active():
    """Independent competence can produce ACTIVE use profile."""
    closure = GroundedDefinitionClosure()
    env = make_envelope("schema:indep:v1", "indep", status="active")

    grounding_spec = GroundingSpecification(
        semantic_family="predicate",
        allowed_cycle_classes=frozenset({"positive_monotone_recursive"}),
    )

    patterns = (make_pattern(function="constitutive"),)

    assessment = closure.assess(
        envelope=env,
        grounding_spec=grounding_spec,
        patterns=patterns,
    )

    profile = derive_use_profile(
        assessment=assessment,
        competence_is_competent=True,
        competence_is_self_certified=False,
        epistemic_admissible=True,
        scope_accessible=True,
    )

    assert profile.level == UseProfileLevel.ACTIVE


# ── Gate 3: typical properties do not close definitions ────────────


def test_typical_pattern_cannot_satisfy_constitutive():
    """Typical patterns cannot satisfy constitutive requirements."""
    pattern = make_pattern(function="typical")
    assert not can_satisfy_constitutive_requirement(pattern)
    assert not is_constitutive(pattern)


def test_default_pattern_cannot_satisfy_constitutive():
    """Default patterns cannot satisfy constitutive requirements."""
    pattern = make_pattern(function="default")
    assert not can_satisfy_constitutive_requirement(pattern)


def test_incidental_pattern_cannot_satisfy_constitutive():
    """Incidental patterns cannot satisfy constitutive requirements."""
    pattern = make_pattern(function="incidental")
    assert not can_satisfy_constitutive_requirement(pattern)


def test_constitutive_pattern_satisfies_constitutive():
    """Constitutive patterns CAN satisfy constitutive requirements."""
    pattern = make_pattern(function="constitutive")
    assert can_satisfy_constitutive_requirement(pattern)
    assert is_constitutive(pattern)


def test_identity_pattern_satisfies_constitutive():
    """Identity patterns CAN satisfy constitutive requirements."""
    pattern = make_pattern(function="identity")
    assert can_satisfy_constitutive_requirement(pattern)


def test_only_typical_patterns_do_not_close():
    """A schema with only typical patterns should not close definition."""
    grounding_spec = GroundingSpecification(semantic_family="predicate")
    patterns = (
        make_pattern(function="typical"),
        make_pattern(function="default"),
        make_pattern(function="incidental"),
    )

    assessment = assess_patterns(patterns, grounding_spec)
    assert not assessment.has_constitutive
    assert any("constitutive" in b.lower() for b in assessment.blocker_reasons)


def test_constitutive_pattern_closes():
    """A schema with at least one constitutive pattern can close."""
    grounding_spec = GroundingSpecification(semantic_family="predicate")
    patterns = (
        make_pattern(function="typical"),
        make_pattern(function="constitutive"),  # At least one constitutive
    )

    assessment = assess_patterns(patterns, grounding_spec)
    assert assessment.has_constitutive


# ── Gate 4: unsupported constructs produce explicit blockers ───────


def test_unsupported_recursive_component_produces_blocker():
    """Unsupported non-monotone recursive components cannot activate jointly."""
    component = RecursiveComponent(
        component_id="rc1",
        classification="unsupported_non_monotone",
        has_external_anchor=True,
        has_non_redundant_contribution=True,
    )
    assert not component.can_activate_jointly


def test_forbidden_dependency_prevents_joint_activation():
    """Forbidden dependencies prevent joint activation."""
    component = RecursiveComponent(
        component_id="rc2",
        classification="positive_monotone",
        has_external_anchor=True,
        has_non_redundant_contribution=True,
        has_type_consistent_mapping=True,
        has_declared_semantics=True,
        has_forbidden_dependency=True,  # Forbidden!
    )
    assert not component.can_activate_jointly


def test_inverse_relation_can_activate():
    """Inverse relation clusters can activate jointly if all requirements met."""
    component = RecursiveComponent(
        component_id="rc3",
        classification="inverse_relation",
        has_external_anchor=True,
        has_non_redundant_contribution=True,
        has_type_consistent_mapping=True,
        has_declared_semantics=True,
        has_forbidden_dependency=False,
    )
    assert component.can_activate_jointly


def test_closure_failure_produces_blockers():
    """A failed closure check should produce explicit blocker reasons."""
    closure = GroundedDefinitionClosure()
    env = make_envelope("schema:blocked:v1", "blocked")

    # Empty grounding spec with no family
    grounding_spec = GroundingSpecification(semantic_family="")
    patterns = (make_pattern(function="typical"),)  # No constitutive

    assessment = closure.assess(
        envelope=env,
        grounding_spec=grounding_spec,
        patterns=patterns,
    )

    assert not assessment.is_structurally_executable
    assert len(assessment.blocker_reasons) > 0
    # Should have blockers for family and constitutive pattern
    assert any("family" in b.lower() for b in assessment.blocker_reasons)
    assert any("constitutive" in b.lower() for b in assessment.blocker_reasons)


# ── Gate 5: opaque/provisional meanings remain safely preservable ──


def test_opaque_profile_permits_quote_and_preserve():
    """Opaque profiles should permit quote, preserve, search, probe."""
    closure = GroundedDefinitionClosure()
    env = make_envelope("schema:opaque:v1", "opaque")

    grounding_spec = GroundingSpecification(semantic_family="predicate")
    # No constitutive patterns → not structurally executable → opaque
    patterns = (make_pattern(function="typical"),)

    assessment = closure.assess(
        envelope=env,
        grounding_spec=grounding_spec,
        patterns=patterns,
    )

    profile = derive_use_profile(assessment)

    assert profile.level == UseProfileLevel.OPAQUE
    assert profile.permits(SemanticOperation.QUOTE)
    assert profile.permits(SemanticOperation.PRESERVE)
    assert profile.permits(SemanticOperation.SEARCH)
    assert profile.permits(SemanticOperation.PROBE)
    # Should NOT permit active operations
    assert not profile.permits(SemanticOperation.CLASSIFY)
    assert not profile.permits(SemanticOperation.LICENSED_INFERENCE)


def test_partial_profile_permits_typed_reference():
    """Partial profiles should permit typed reference and qualified composition."""
    closure = GroundedDefinitionClosure()
    env = make_envelope("schema:partial:v1", "partial")

    grounding_spec = GroundingSpecification(
        semantic_family="predicate",
        allowed_cycle_classes=frozenset({"positive_monotone_recursive"}),
    )
    patterns = (make_pattern(function="constitutive"),)

    assessment = closure.assess(
        envelope=env,
        grounding_spec=grounding_spec,
        patterns=patterns,
    )

    # Structurally executable but no competence → partial
    profile = derive_use_profile(
        assessment,
        competence_is_competent=False,
    )

    assert profile.level == UseProfileLevel.PARTIAL
    assert profile.permits(SemanticOperation.TYPED_REFERENCE)
    assert profile.permits(SemanticOperation.COMPOSE_QUALIFIED)
    assert profile.permits(SemanticOperation.QUERY_THEORY)
    # Should NOT permit active operations
    assert not profile.permits(SemanticOperation.CLASSIFY)


def test_execute_never_permitted_by_profile():
    """EXECUTE is never permitted by profile alone — requires live authorization."""
    closure = GroundedDefinitionClosure()
    env = make_envelope("schema:exec:v1", "exec")

    grounding_spec = GroundingSpecification(
        semantic_family="predicate",
        allowed_cycle_classes=frozenset({"positive_monotone_recursive"}),
    )
    patterns = (make_pattern(function="constitutive"),)

    assessment = closure.assess(
        envelope=env,
        grounding_spec=grounding_spec,
        patterns=patterns,
    )

    # Even with full competence and admissibility
    profile = derive_use_profile(
        assessment,
        competence_is_competent=True,
        epistemic_admissible=True,
        scope_accessible=True,
    )

    assert profile.level == UseProfileLevel.ACTIVE
    assert not profile.permits(SemanticOperation.EXECUTE)
    assert not profile.permits_execute()


def test_causal_profile_permits_predict_but_not_execute():
    """Causal profiles permit predict/simulate/propose but NOT execute."""
    closure = GroundedDefinitionClosure()
    env = make_envelope("schema:causal:v1", "causal")

    grounding_spec = GroundingSpecification(
        semantic_family="predicate",
        allowed_cycle_classes=frozenset({"positive_monotone_recursive"}),
    )
    # Need a constitutive pattern for closure + a causal pattern for causal level
    patterns = (
        make_pattern(function="constitutive"),
        make_pattern(function="causal"),
    )

    assessment = closure.assess(
        envelope=env,
        grounding_spec=grounding_spec,
        patterns=patterns,
    )

    profile = derive_use_profile(
        assessment,
        competence_is_competent=True,
    )

    assert profile.level == UseProfileLevel.CAUSAL
    assert profile.permits(SemanticOperation.PREDICT)
    assert profile.permits(SemanticOperation.SIMULATE)
    assert profile.permits(SemanticOperation.PROPOSE)
    assert not profile.permits(SemanticOperation.EXECUTE)


# ── Field-level provenance tests ───────────────────────────────────


def test_provenance_kinds_exist():
    """All 9 provenance kinds must exist."""
    expected = {
        "asserted", "observed", "entailed", "inherited",
        "induced", "adapter-supplied", "boot-supplied",
        "hypothesized", "defaulted",
    }
    actual = {k.value for k in ProvenanceKind}
    assert actual == expected


def test_weak_provenance_cannot_certify_truth():
    """Hypothesized/defaulted contributions cannot certify truth."""
    weak = ContributionRecord(
        field_name="test_field",
        provenance_kind=ProvenanceKind.HYPOTHESIZED,
        is_independent=True,
    )
    assert weak.is_weak
    assert not weak.can_certify_truth

    defaulted = ContributionRecord(
        field_name="test_field",
        provenance_kind=ProvenanceKind.DEFAULTED,
        is_independent=True,
    )
    assert defaulted.is_weak
    assert not defaulted.can_certify_truth


def test_observed_provenance_can_certify_truth():
    """Observed contributions with independence can certify truth."""
    observed = ContributionRecord(
        field_name="test_field",
        provenance_kind=ProvenanceKind.OBSERVED,
        is_independent=True,
    )
    assert not observed.is_weak
    assert observed.can_certify_truth


def test_adapter_supplied_is_candidate_only():
    """Adapter-supplied contributions are candidate evidence only."""
    adapter = ContributionRecord(
        field_name="test_field",
        provenance_kind=ProvenanceKind.ADAPTER_SUPPLIED,
    )
    assert adapter.is_adapter_supplied
    assert not adapter.can_certify_truth


def test_self_certification_detection():
    """FieldProvenanceMap detects self-certification."""
    contribs = (
        ContributionRecord(
            field_name="field_a",
            provenance_kind=ProvenanceKind.OBSERVED,
            source_ref="impl_path",
            is_independent=True,
        ),
    )
    provenance_map = FieldProvenanceMap(contributions=contribs)

    # Same implementation path as source → self-certified
    assert provenance_map.can_self_certify("field_a", "impl_path")
    # Different implementation path → not self-certified
    assert not provenance_map.can_self_certify("field_a", "other_path")


def test_lineage_inheritance():
    """Translations/paraphrases inherit root lineage."""
    original = ContributionRecord(
        field_name="field_a",
        provenance_kind=ProvenanceKind.OBSERVED,
        source_ref="source_1",
        is_independent=True,
        derivation_lineage=("source_1",),
    )
    # A translation inherits the same root lineage
    translation = ContributionRecord(
        field_name="field_a",
        provenance_kind=ProvenanceKind.ENTAILED,
        source_ref="translation_1",
        is_independent=False,
        derivation_lineage=("source_1", "translation_1"),
    )

    assert original.lineage_root == "source_1"
    assert translation.lineage_root == "source_1"  # Same root


# ── Competence harness tests ───────────────────────────────────────


def test_competence_minimum_checks():
    """Competence requires all minimum checks to pass."""
    harness = CompetenceHarness()

    # All checks pass with independent oracle
    cases = (
        CompetenceCase(case_id="c1", check_kind=CompetenceCheckKind.POSITIVE_CASE,
                       input_lineage="src", oracle_lineage="oracle",
                       is_independent=True, passed=True),
        CompetenceCase(case_id="c2", check_kind=CompetenceCheckKind.ROLE_STRUCTURE,
                       input_lineage="src", oracle_lineage="oracle",
                       is_independent=True, passed=True),
        CompetenceCase(case_id="c3", check_kind=CompetenceCheckKind.DEFINING_QUERY,
                       input_lineage="src", oracle_lineage="oracle",
                       is_independent=True, passed=True),
        CompetenceCase(case_id="c4", check_kind=CompetenceCheckKind.CONTRAST,
                       input_lineage="src", oracle_lineage="oracle",
                       is_independent=True, passed=True,
                       contrast_result=ContrastResult.SUPPORTED),
        CompetenceCase(case_id="c5", check_kind=CompetenceCheckKind.LICENSED_INFERENCE,
                       input_lineage="src", oracle_lineage="oracle",
                       is_independent=True, passed=True),
    )

    assessment = harness.assess(cases, implementation_path="impl")
    assert assessment.is_competent
    assert not assessment.is_self_certified


def test_competence_missing_check_fails():
    """Missing any minimum check should fail competence."""
    harness = CompetenceHarness()

    cases = (
        CompetenceCase(case_id="c1", check_kind=CompetenceCheckKind.POSITIVE_CASE,
                       input_lineage="src", oracle_lineage="oracle",
                       is_independent=True, passed=True),
        # Missing: role_structure, defining_query, contrast, licensed_inference
    )

    assessment = harness.assess(cases, implementation_path="impl")
    assert not assessment.is_competent


def test_open_world_neither_is_not_rejection():
    """Open-world negative cases: 'neither' is not rejection.

    A negative case passes only when the candidate schema derives
    an incompatibility or a better alternative.
    """
    harness = CompetenceHarness()

    # Contrast case with 'neither' result — should NOT pass
    cases = (
        CompetenceCase(case_id="c1", check_kind=CompetenceCheckKind.CONTRAST,
                       input_lineage="src", oracle_lineage="oracle",
                       is_independent=True, passed=False,
                       contrast_result=ContrastResult.NEITHER),
    )

    assessment = harness.assess(cases, implementation_path="impl")
    # 'neither' should not count as passing contrast
    assert not assessment.is_competent


# ── GroundingResolver tests ────────────────────────────────────────


def test_grounding_resolver_does_not_activate():
    """GroundingResolver must not activate schemas."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:noact:v1", "noact", status="candidate")
    store.register(env)
    store.index_lexical_form("noact", "en", "noact")

    resolver = GroundingResolver(store)
    result = resolver.ground_definition("noact")

    # Schema should still be candidate — not activated
    assert store.get("schema:noact:v1").status == "candidate"


def test_unknown_referent_stays_unknown():
    """Unknown referents should not be converted to generic entities."""
    store = SemanticSchemaStore()
    resolver = GroundingResolver(store)

    result = resolver.ground_referent("unknown_word", "en")

    assert result.is_unknown
    assert "unknown" in result.referent_kind


def test_known_referent_gets_schema_sense():
    """Known referents should resolve to schema sense."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:known:v1", "known", status="active")
    store.register(env)
    store.activate("schema:known:v1", expected_revision=1)
    store.index_lexical_form("known", "en", "known")

    resolver = GroundingResolver(store)
    result = resolver.ground_referent("known", "en")

    assert result.referent_kind == "schema_sense"
    assert not result.is_unknown


# ── SchemaGroundingAssessment is derived, not an authority ─────────


def test_assessment_is_not_activation_authority():
    """SchemaGroundingAssessment must not have activation methods."""
    closure = GroundedDefinitionClosure()
    env = make_envelope("schema:auth:v1", "auth")
    grounding_spec = GroundingSpecification(semantic_family="predicate")
    patterns = (make_pattern(function="constitutive"),)

    assessment = closure.assess(
        envelope=env,
        grounding_spec=grounding_spec,
        patterns=patterns,
    )

    # Must not have activation methods
    assert not hasattr(assessment, "activate")
    assert not hasattr(assessment, "set_status")
    assert not hasattr(assessment, "commit")
    assert not hasattr(assessment, "register")


def test_use_profile_is_not_activation_authority():
    """SchemaUseProfile must not have activation methods."""
    closure = GroundedDefinitionClosure()
    env = make_envelope("schema:up:v1", "up")
    grounding_spec = GroundingSpecification(semantic_family="predicate")
    patterns = (make_pattern(function="constitutive"),)

    assessment = closure.assess(
        envelope=env,
        grounding_spec=grounding_spec,
        patterns=patterns,
    )

    profile = derive_use_profile(assessment, competence_is_competent=True)

    assert not hasattr(profile, "activate")
    assert not hasattr(profile, "set_status")
    assert not hasattr(profile, "commit")


# ── Import boundary tests ──────────────────────────────────────────


def test_provenance_imports_no_engine():
    """Provenance module must not import any engine module."""
    import cemm.kernel.schema.provenance as prov_mod

    forbidden = [
        "cemm.kernel.semantic_kernel_runtime",
        "cemm.kernel.meaning_perceptor",
        "cemm.kernel.meaning_graph_builder",
        "cemm.memory.durable_semantic_store",
    ]
    source = open(prov_mod.__file__, encoding="utf-8").read()
    for f in forbidden:
        assert f not in source, f"provenance.py imports forbidden module {f}"


def test_closure_imports_no_engine():
    """Closure module must not import any engine module."""
    import cemm.kernel.schema.closure as closure_mod

    forbidden = [
        "cemm.kernel.semantic_kernel_runtime",
        "cemm.kernel.meaning_perceptor",
        "cemm.kernel.meaning_graph_builder",
        "cemm.memory.durable_semantic_store",
    ]
    source = open(closure_mod.__file__, encoding="utf-8").read()
    for f in forbidden:
        assert f not in source, f"closure.py imports forbidden module {f}"


def test_grounding_imports_no_engine():
    """Grounding module must not import any engine module."""
    import cemm.kernel.understanding.grounding as grounding_mod

    forbidden = [
        "cemm.kernel.semantic_kernel_runtime",
        "cemm.kernel.meaning_perceptor",
        "cemm.kernel.meaning_graph_builder",
        "cemm.memory.durable_semantic_store",
    ]
    source = open(grounding_mod.__file__, encoding="utf-8").read()
    for f in forbidden:
        assert f not in source, f"grounding.py imports forbidden module {f}"
