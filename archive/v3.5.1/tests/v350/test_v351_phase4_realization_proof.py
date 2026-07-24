from __future__ import annotations

from dataclasses import dataclass, field

from cemm.v350.realization.policy import SelectiveRoundTripPolicy, VerificationMode
from cemm.v350.realization.proof import (
    PreservationDecision, RealizationProofBuilder, RealizationTransformStep,
    SemanticPreservationAssessment, required_qualification_refs,
)


@dataclass(frozen=True)
class _Root:
    ref: str


@dataclass(frozen=True)
class _App:
    context_ref: str = "actual"
    polarity: str = "positive"
    use_operation: str = "compose"


@dataclass(frozen=True)
class _Graph:
    record_fingerprint: str = "graph:exact"
    root_refs: tuple = (_Root("app:root"),)
    applications: dict = field(default_factory=lambda: {"app:root": _App()})
    scope_relations: tuple = ()


@dataclass(frozen=True)
class _Response:
    graph: _Graph = field(default_factory=_Graph)
    context_ref: str = "actual"
    permission_ref: str = "conversation"
    sensitivity: str = "normal"
    audience_refs: tuple[str, ...] = ("referent:user",)


class _Store:
    pass


def test_proof_builder_requires_explicit_transform_steps_and_coverage():
    response = _Response()
    builder = RealizationProofBuilder(_Store())
    qualifications = required_qualification_refs(response)
    proof = builder.build(
        semantic_input_ref="response:test",
        semantic_input=response,
        surface_candidate_ref="surface:test",
        surface="hello",
        authority_generation=3,
        authority_fingerprint="authority:exact",
        permission_ref="conversation",
        audience_refs=("referent:user",),
        steps=(RealizationTransformStep(
            step_ref="step:1", transform_kind="reviewed_linearization",
            input_refs=("app:root",), output_refs=("surface:test",),
            # Exact pins are verified by RealizationProofVerifier in integration tests.
            rule_pins=(), coverage_refs=("app:root",),
            preserved_qualification_refs=qualifications,
        ),),
        coverage_refs=("app:root",),
    )
    assert proof.required_coverage_refs == ("app:root",)
    assert proof.covered_semantic_refs == ("app:root",)


def test_selective_roundtrip_policy_keeps_full_roundtrip_for_release_competence():
    assessment = SemanticPreservationAssessment(
        assessment_ref="assessment:1", proof_ref="proof:1",
        decision=PreservationDecision.PASS, checked_pin_refs=(),
        missing_coverage_refs=(), stale_pin_refs=(), reason_refs=(),
        semantic_input_fingerprint="semantic:1", qualification_fingerprint="q:1",
    )
    policy = SelectiveRoundTripPolicy()
    ordinary = policy.decide(preservation=assessment)
    release = policy.decide(preservation=assessment, release_competence=True)
    assert ordinary.mode is VerificationMode.PROOF_ONLY
    assert release.mode is VerificationMode.PROOF_PLUS_INDEPENDENT_ROUNDTRIP


def test_failed_cheap_proof_cannot_be_bypassed_by_full_roundtrip():
    assessment = SemanticPreservationAssessment(
        assessment_ref="assessment:2", proof_ref="proof:2",
        decision=PreservationDecision.FAIL, checked_pin_refs=(),
        missing_coverage_refs=("app:missing",), stale_pin_refs=(),
        reason_refs=("semantic_coverage_incomplete",),
        semantic_input_fingerprint="semantic:2", qualification_fingerprint="q:2",
    )
    decision = SelectiveRoundTripPolicy().decide(
        preservation=assessment, release_competence=True
    )
    assert decision.mode is VerificationMode.BLOCK


@dataclass(frozen=True)
class _CsirTerm:
    term_ref: str


@dataclass(frozen=True)
class _CsirQualifier:
    qualifier_ref: str
    context_ref: str = "actual"


@dataclass(frozen=True)
class _CsirGraph:
    fingerprint: str = "csir:exact"
    terms: tuple = (_CsirTerm("term:self"),)
    variables: tuple = ()
    applications: dict = field(default_factory=dict)
    bindings: tuple = ()
    qualifiers: tuple = (_CsirQualifier("qualifier:context"),)
    relations: tuple = ()
    proof_annotations: tuple = ()


def test_realization_coverage_is_csir_representation_neutral():
    from cemm.v350.realization.proof import required_semantic_coverage
    assert required_semantic_coverage(_CsirGraph()) == ("qualifier:context", "term:self")


def test_proof_builder_rejects_coverage_not_backed_by_transform_steps():
    import pytest

    response = _Response()
    builder = RealizationProofBuilder(_Store())
    qualifications = required_qualification_refs(response)
    with pytest.raises(ValueError, match="coverage must equal"):
        builder.build(
            semantic_input_ref="response:test",
            semantic_input=response,
            surface_candidate_ref="surface:test",
            surface="hello",
            authority_generation=3,
            authority_fingerprint="authority:exact",
            permission_ref="conversation",
            audience_refs=("referent:user",),
            steps=(RealizationTransformStep(
                step_ref="step:1",
                transform_kind="reviewed_linearization",
                input_refs=("app:root",),
                output_refs=("surface:test",),
                coverage_refs=("app:root",),
                preserved_qualification_refs=qualifications,
            ),),
            coverage_refs=("app:root", "semantic:invented"),
        )


def test_qualification_requirements_are_explicit_in_realization_proof():
    from cemm.v350.realization.proof import required_qualification_refs

    required = required_qualification_refs(_Response())
    assert "qualification:context_ref:actual" in required
    assert "qualification:permission_ref:conversation" in required
    assert "qualification:audience:referent:user" in required


def test_stage19_and_stage20_cannot_be_bypassed_with_prebuilt_service_stageoutcome():
    from pathlib import Path
    source = (
        Path(__file__).resolve().parents[2] / "cemm/v350/runtime_v351.py"
    ).read_text(encoding="utf-8")
    stage19 = source[source.index("def stage_19_realize_target_language_or_modality"):source.index("def _authorization_value")]
    stage20 = source[source.index("def stage_20_verify_semantic_equivalence_and_authorize_emission"):source.index("def stage_21_commit_output_discourse")]
    assert "isinstance(result, StageOutcome)" not in stage19
    assert "verify_and_emit" not in stage20
    assert "authorize(" in stage20 and "emit(" in stage20
    assert stage20.index("authorize(") < stage20.index("emit(")
