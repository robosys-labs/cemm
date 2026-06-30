from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.cemm_trainer import validate_training_record
import pytest


def test_validate_requires_context_kernel() -> None:
    """All training records must have a context_kernel."""
    with pytest.raises(ValueError, match="missing ContextKernel"):
        validate_training_record("any_type", {})


def test_validate_rejects_text_to_answer_without_sag() -> None:
    with pytest.raises(ValueError, match="missing SemanticAnswerGraph"):
        validate_training_record("text_to_answer", {
            "context_kernel": {"id": "test"},
        })


def test_validate_passes_complete_record() -> None:
    validate_training_record("operator_selection", {
        "context_kernel": {"id": "test"},
        "semantic_event_graph": {"id": "seg1"},
        "semantic_answer_graph": {"id": "sag1"},
    })


def test_validate_requires_seg_for_claim_extraction() -> None:
    with pytest.raises(ValueError, match="missing SemanticEventGraph"):
        validate_training_record("claim_extraction", {
            "context_kernel": {"id": "test"},
        })


def test_validate_requires_seg_for_frame_classification() -> None:
    with pytest.raises(ValueError, match="missing SemanticEventGraph"):
        validate_training_record("frame_classification", {
            "context_kernel": {"id": "test"},
        })


def test_validate_requires_seg_for_temporal_relation_derivation() -> None:
    with pytest.raises(ValueError, match="missing SemanticEventGraph"):
        validate_training_record("temporal_relation_derivation", {
            "context_kernel": {"id": "test"},
        })


def test_validate_requires_seg_for_uol_mapping() -> None:
    with pytest.raises(ValueError, match="missing SemanticEventGraph"):
        validate_training_record("uol_mapping", {
            "context_kernel": {"id": "test"},
        })


def test_validate_requires_output_text_for_synthesis_verification() -> None:
    with pytest.raises(ValueError, match="missing output_text"):
        validate_training_record("synthesis_verification", {
            "context_kernel": {"id": "test"},
        })


def test_validate_requires_selected_evidence_for_synthesis_verification() -> None:
    with pytest.raises(ValueError, match="missing selected_evidence"):
        validate_training_record("synthesis_verification", {
            "context_kernel": {"id": "test"},
            "output_text": "some output",
        })


def test_validate_synthesis_verification_passes_complete() -> None:
    validate_training_record("synthesis_verification", {
        "context_kernel": {"id": "test"},
        "output_text": "some output",
        "selected_evidence": {"claim_ids": ["c1"]},
    })
