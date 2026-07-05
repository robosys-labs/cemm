"""Tests for v4.2 pipeline bridge: PipelineResult carries semantic stack outputs."""

from __future__ import annotations

import os
import sys
import uuid
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.kernel.pipeline import PipelineResult
from cemm.types.semantic_program import SemanticProgram
from cemm.types.obligation_frame import ObligationFrame
from cemm.types.answer_binding import AnswerBinding, SlotFill
from cemm.types.realization_contract import RealizationContract
from cemm.types.semantic_query import SemanticQuery


def test_pipeline_result_has_v42_fields():
    result = PipelineResult()
    assert hasattr(result, "semantic_program")
    assert hasattr(result, "obligation_frame")
    assert hasattr(result, "relation_frames")
    assert hasattr(result, "semantic_query")
    assert hasattr(result, "answer_binding")
    assert hasattr(result, "realization_contract")
    assert hasattr(result, "semantic_realized_output")


def test_pipeline_result_v42_defaults():
    result = PipelineResult()
    assert result.semantic_program is None
    assert result.obligation_frame is None
    assert result.relation_frames == []
    assert result.semantic_query is None
    assert result.answer_binding is None
    assert result.realization_contract is None
    assert result.semantic_realized_output == ""


def test_pipeline_result_populates_v42_fields():
    result = PipelineResult()
    result.semantic_program = SemanticProgram(
        graph_id="g1", signal_id="s1", context_id="c1",
    )
    result.obligation_frame = ObligationFrame(
        primary_instruction_id="i1",
        obligation_kind="answer_concept",
        response_mode="evidence_answer",
    )
    result.relation_frames = []
    result.semantic_query = SemanticQuery(query_id="q1")
    result.answer_binding = AnswerBinding(binding_id="b1", has_answer=True)
    result.realization_contract = RealizationContract(contract_id="rc1")
    result.semantic_realized_output = "A dog is an animal."

    assert result.semantic_program is not None
    assert result.obligation_frame is not None
    assert result.answer_binding is not None
    assert result.realization_contract is not None
    assert result.semantic_realized_output == "A dog is an animal."


def test_pipeline_result_serialization_safe():
    """Ensure v4.2 fields don't break dataclass defaults."""
    result = PipelineResult()
    import dataclasses
    fields = {f.name for f in dataclasses.fields(result)}
    assert "semantic_program" in fields
    assert "obligation_frame" in fields
    assert "relation_frames" in fields
    assert "semantic_query" in fields
    assert "answer_binding" in fields
    assert "realization_contract" in fields
    assert "semantic_realized_output" in fields
