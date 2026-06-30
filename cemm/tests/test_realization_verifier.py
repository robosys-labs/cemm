"""Tests for realization verifier."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cemm.kernel.realization_verifier import verify, VerificationResult
from cemm.types.semantic_answer_graph import SemanticAnswerGraph, AnswerVerification


def _sag(intent: str = "answer", confidence: float = 0.9,
         claim_ids: list[str] | None = None,
         uncertainty: list[str] | None = None,
         scope: str = "public",
         verified: bool = True) -> SemanticAnswerGraph:
    return SemanticAnswerGraph(
        id="sag_test",
        intent=intent,
        source_signal_ids=["sig_1"],
        context_id="ctx_1",
        selected_claim_ids=claim_ids or [],
        confidence=confidence,
        uncertainty_reasons=uncertainty or [],
        permission_scope=scope,
        verification=AnswerVerification(supported=verified, verification_type="hard" if verified else "none"),
    )


def test_claim_reflected_in_text() -> None:
    sag = _sag(claim_ids=["clm_jupiter_mass"])
    text = "Jupiter is the most massive planet in the solar system."
    result = verify(sag, text, claim_text_map={"clm_jupiter_mass": "most massive planet"})
    assert result.verified, f"Expected verified, got {result.details}"
    assert result.claim_coverage >= 0.5


def test_claim_not_reflected() -> None:
    sag = _sag(claim_ids=["clm_io_volcanoes"])
    text = "Jupiter has a Great Red Spot."
    result = verify(sag, text, claim_text_map={"clm_io_volcanoes": "Io has active volcanoes"})
    assert not result.verified
    assert result.claim_coverage < 0.5


def test_uncertainty_preserved_when_needed() -> None:
    sag = _sag(confidence=0.4, uncertainty=["insufficient data"])
    text = "The data might suggest a correlation, but it's unclear."
    result = verify(sag, text)
    assert result.uncertainty_preserved, f"Expected uncertainty preserved, got {result.details}"


def test_uncertainty_missing_when_needed() -> None:
    sag = _sag(confidence=0.3, uncertainty=["insufficient data"])
    text = "The answer is definitely yes."
    result = verify(sag, text)
    assert not result.uncertainty_preserved
    assert any("low confidence" in d.lower() for d in result.details)


def test_high_confidence_no_uncertainty_needed() -> None:
    sag = _sag(confidence=0.95)
    text = "Jupiter has a mass of 1.898e27 kg."
    result = verify(sag, text)
    assert result.uncertainty_preserved


def test_private_evidence_protected() -> None:
    sag = _sag(scope="user_private")
    text = "The answer is 42."
    result = verify(sag, text)
    assert result.private_evidence_protected


def test_private_entity_leakage() -> None:
    sag = _sag(scope="user_private")
    text = "Based on Alice's medical records, the result is positive."
    result = verify(sag, text, private_entity_names=["Alice"])
    assert not result.private_evidence_protected


def test_mixed_verification() -> None:
    """Partially correct text gets partial verification."""
    sag = _sag(confidence=0.95, claim_ids=["clm_orbit", "clm_volcanoes"])
    text = "Io orbits Jupiter."
    result = verify(sag, text, claim_text_map={
        "clm_orbit": "Io orbits Jupiter",
        "clm_volcanoes": "Io has volcanoes",
    })
    # One of two claims covered -> coverage 0.5
    assert result.claim_coverage == 0.5
    # High confidence -> no uncertainty markers needed
    assert result.uncertainty_preserved


def test_missing_uncertainty_with_reasons() -> None:
    sag = _sag(confidence=0.6, uncertainty=["multiple conflicting sources",
                                             "outdated measurements"])
    text = "The distance is 384,400 km."
    result = verify(sag, text)
    assert not result.uncertainty_preserved
