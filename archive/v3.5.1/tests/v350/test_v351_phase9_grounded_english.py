from __future__ import annotations

import pytest

from cemm.v350.csir import CSIRGraph, CSIRNodeKind, CSIRRef, ExactAuthorityPin, SemanticVariable
from cemm.v350.csir.authority_v351 import AuthoritySnapshotV351
from cemm.v350.grounded import (
    AnswerProjection,
    Claim,
    GapKind,
    IdentityCandidate,
    IdentityCandidateStatus,
    InformationGap,
    Query,
)
from cemm.v350.language.minimum_english_v351 import (
    MINIMUM_REVIEWED_ENGLISH,
    REQUIRED_COMPOSITION_FAMILIES,
    SemanticAuthorityBindings,
)
from cemm.v350.language.reversible_normalization import normalize_with_provenance


def test_claim_attribution_is_structural_not_automatic_world_admission():
    claim = Claim(
        "claim:1", "prop:1", "speaker:1", (), "actual", "actual", ("e:1",), 1.0
    )
    assert claim.source_context_ref == "actual"
    assert claim.reported_context_ref == "actual"
    assert not hasattr(claim, "admission_decision")


def test_query_gap_and_answer_projection_remain_distinct():
    variable = SemanticVariable("who", open_purpose="query")
    graph = CSIRGraph(variables=(variable,), root_refs=(variable.node_ref,))
    gap = InformationGap("gap:1", GapKind.REFERENT, variable.node_ref, graph, ("e:1",))
    projection = AnswerProjection("projection:1", variable.node_ref)
    query = Query(
        "query:1", graph, (gap.gap_ref,), projection, "speaker:1", ("self",), "actual", ("e:1",)
    )
    assert query.gap_refs == ("gap:1",)
    assert query.answer_projection.projection_ref == "projection:1"


def test_identity_support_does_not_itself_resolve_identity():
    candidate = IdentityCandidate(
        "identity:1", "mention:1", "referent:alice",
        IdentityCandidateStatus.CANDIDATE, 0.999, ("e:1",)
    )
    assert candidate.status is IdentityCandidateStatus.CANDIDATE


def test_minimum_english_package_covers_all_required_families():
    assert {x.family for x in MINIMUM_REVIEWED_ENGLISH.constructions} == set(REQUIRED_COMPOSITION_FAMILIES)




def test_minimum_english_package_is_content_addressed_exact_authority():
    assert MINIMUM_REVIEWED_ENGLISH.package_pin.ref == "language-pack:en"
    assert MINIMUM_REVIEWED_ENGLISH.package_pin.revision == MINIMUM_REVIEWED_ENGLISH.revision
    assert MINIMUM_REVIEWED_ENGLISH.package_pin.content_hash == MINIMUM_REVIEWED_ENGLISH.content_hash



def test_minimum_english_activation_requires_exact_authority_generation_bindings():
    slots = {sense.semantic_slot for sense in MINIMUM_REVIEWED_ENGLISH.senses}
    slots.update(
        step.semantic_slot
        for construction in MINIMUM_REVIEWED_ENGLISH.constructions
        for step in construction.program
        if step.semantic_slot
    )
    pins = {
        slot: ExactAuthorityPin(
            "language_projection_binding", "test", slot, 1, f"sha:{slot}", "global"
        )
        for slot in sorted(slots)
    }
    snapshot = AuthoritySnapshotV351(
        1, "authority:1",
        auxiliary_exact_pins=(MINIMUM_REVIEWED_ENGLISH.package_pin, *pins.values()),
    )
    MINIMUM_REVIEWED_ENGLISH.validate(
        SemanticAuthorityBindings(pins), authority_snapshot=snapshot
    )

    missing_snapshot = AuthoritySnapshotV351(1, "authority:missing")
    with pytest.raises(ValueError, match="package pin"):
        MINIMUM_REVIEWED_ENGLISH.validate(
            SemanticAuthorityBindings(pins), authority_snapshot=missing_snapshot
        )


def test_unicode_normalization_is_reversible_by_preserved_source_evidence():
    text = "Ａlice İS Here"
    result = normalize_with_provenance(text)
    assert result.normalized_text != text
    assert result.reverse() == text
    assert result.segments


def test_normalization_composes_across_codepoint_boundaries():
    text = "A\u030A"  # decomposed Å
    result = normalize_with_provenance(text)
    assert result.normalized_text == "å"
    assert result.reverse() == text
    assert result.original_span_for(0, 1) == (0, 2)


def test_normalization_handles_hangul_composition_without_characterwise_drift():
    text = "\u1100\u1161"  # choseong kiyeok + jungseong a -> 가 under NFKC
    result = normalize_with_provenance(text)
    assert result.normalized_text == "가"
    assert result.original_span_for(0, 1) == (0, 2)
    assert result.reverse() == text
