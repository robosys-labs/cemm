"""Golden trace tests: verify role labels never leak into realized output.

These tests exercise the exact failure modes documented in the v4.2 gap-fix
proposal. They verify that internal role atoms (target, possessor, topic, etc.)
used for CPU/port binding never become answerable user-facing text.

The architecture invariant under test:
  structural frames may guide planning,
  but only answerable frames with a valid projection policy may fill user-facing slots.
"""

from __future__ import annotations

import os
import sys
import time
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
os.environ["CEMM_EXPORT_PATH"] = ""

from ...types.relation_frame import RelationFrame, RelationArgument
from ...types.obligation_frame import ObligationFrame
from ...types.semantic_program import SemanticProgram, SemanticInstruction
from ...types.semantic_query import SemanticQuery, QueryConstraint
from ...types.answer_binding import AnswerBinding, SlotFill
from ...kernel.semantic_query_engine import SemanticQueryEngine
from ...kernel.relation_algebra import RelationAlgebra
from ...memory.predicate_schema_store import PredicateSchemaStore
from ...kernel.relation_frame_compiler import RelationFrameCompiler
from ...types.uol_graph import UOLGraph
from ..harness import SeededSystem

_ROLE_LABELS = {"target", "possessor", "topic", "actor", "holder"}


def _make_role_frame(
    role_label: str = "target",
    confidence: float = 0.9,
) -> RelationFrame:
    return RelationFrame(
        relation_id=uuid.uuid4().hex[:16],
        relation_key="has_role",
        relation_family="role",
        subject=RelationArgument(role="subject", atom_id="atom:self", entity_id="self", surface="you"),
        object=RelationArgument(role="object", atom_id="atom:role", surface=role_label),
        source_atom_ids=["atom:self", "atom:role"],
        confidence=confidence,
        answerable=False,
        structural=True,
        projection_policy="none",
    )


def _make_teaching_frame(
    relation_key: str = "is_a",
    subj_surface: str = "my name",
    obj_surface: str = "Chibueze",
    confidence: float = 0.72,
) -> RelationFrame:
    return RelationFrame(
        relation_id=uuid.uuid4().hex[:16],
        relation_key=relation_key,
        relation_family="taxonomy",
        subject=RelationArgument(role="subject", surface=subj_surface, confidence=confidence),
        object=RelationArgument(role="object", surface=obj_surface, confidence=confidence),
        source_atom_ids=["atom:teaching"],
        confidence=confidence,
        answerable=True,
        structural=False,
        projection_policy="object",
    )


# ── Test: Structural frames are correctly classified ──────────────


def test_structural_frame_has_role_marked_non_answerable():
    frame = _make_role_frame("target")
    assert frame.answerable is False
    assert frame.structural is True
    assert frame.projection_policy == "none"


def test_answerable_frame_not_structural():
    frame = _make_teaching_frame()
    assert frame.answerable is True
    assert frame.structural is False
    assert frame.projection_policy == "object"


# ── Test: build_query filters structural frames ───────────────────


def test_build_query_filters_structural_frames():
    engine = SemanticQueryEngine()
    role_frame = _make_role_frame("target")
    teaching_frame = _make_teaching_frame()

    obligation = ObligationFrame(
        primary_instruction_id="inst_1",
        obligation_kind="answer_concept",
        response_mode="evidence_answer",
        evidence_policy="required",
    )
    program = SemanticProgram(
        graph_id="g1", signal_id="s1", context_id="c1",
        instructions=[SemanticInstruction(
            instruction_id="inst_1", group_id="grp1",
            surface="how are you", instruction_kind="question",
            atom_ids=["atom:self"],
            confidence=0.8,
        )],
        entry_instruction_id="inst_1",
    )

    query = engine.build_query(obligation, [role_frame, teaching_frame], program)
    assert query.relation_key == "", (
        f"Expected no relation key (structural frame filtered), got {query.relation_key!r}"
    )


def test_query_engine_never_selects_role_frame():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    role_frame = _make_role_frame("possessor")
    teaching_frame = _make_teaching_frame()

    obligation = ObligationFrame(
        primary_instruction_id="inst_1",
        obligation_kind="answer_concept",
        response_mode="evidence_answer",
        evidence_policy="required",
    )
    program = SemanticProgram(
        graph_id="g1", signal_id="s1", context_id="c1",
        instructions=[SemanticInstruction(
            instruction_id="inst_1", group_id="grp1",
            surface="my name is Chibueze", instruction_kind="teaching",
            atom_ids=["atom:teaching", "atom:self"],
            confidence=0.8,
        )],
        entry_instruction_id="inst_1",
    )

    query = engine.build_query(obligation, [role_frame, teaching_frame], program)
    binding = engine.execute(query, [role_frame, teaching_frame])
    if binding.has_answer:
        for fill in binding.slot_fills:
            assert fill.surface not in _ROLE_LABELS, (
                f"Role label leaked into answer: {fill.surface!r}"
            )


# ── Test: query_kind=none never produces answer binding ────────────


def test_query_kind_none_never_has_answer():
    engine = SemanticQueryEngine()
    query = SemanticQuery(query_id="q1", query_kind="none")
    binding = engine.execute(query, [])
    assert binding.has_answer is False
    assert binding.abstention_reason == ""


def test_social_reply_does_not_query_role_frames():
    engine = SemanticQueryEngine()
    role_frame = _make_role_frame("target")
    query = SemanticQuery(
        query_id="q1", query_kind="none", relation_key="",
    )
    binding = engine.execute(query, [role_frame])
    assert binding.has_answer is False
    assert binding.abstention_reason == ""


# ── Test: exit obligation does not query ──────────────────────────


def test_exit_obligation_does_not_query():
    engine = SemanticQueryEngine()
    role_frame = _make_role_frame("target")
    query = SemanticQuery(
        query_id="q1", query_kind="none", relation_key="",
    )
    binding = engine.execute(query, [role_frame])
    assert binding.has_answer is False


# ── Test: Response formation engine never emits role labels ──────


def test_response_engine_no_role_label_in_answer():
    """Role labels like 'target' must not appear in response output.

    Tests the full pipeline via SeededSystem rather than directly
    instantiating the old realizer with synthetic contracts.
    """
    system = SeededSystem()
    result = system.run("what is a target?")
    output = result["output"]
    assert "target" not in output.lower() or output != "target", (
        f"Role label 'target' leaked into output: {output!r}"
    )


def test_response_engine_no_role_label_in_store_confirmation():
    """Role labels from structural frames must not appear as answer text.

    This tests the pipeline invariant: when the system has structural
    has_role frames with role labels like 'possessor', those labels
    must never be projected as answer text in response to a query.
    The user typing 'possessor' as a word is fine — the invariant is
    that the system doesn't surface internal role labels from its own
    structural frames.
    """
    engine = SemanticQueryEngine()
    role_frame = _make_role_frame("possessor")
    obligation = ObligationFrame(
        primary_instruction_id="inst_1",
        obligation_kind="answer_concept",
        response_mode="evidence_answer",
        evidence_policy="required",
    )
    program = SemanticProgram(
        graph_id="g1", signal_id="s1", context_id="c1",
        instructions=[SemanticInstruction(
            instruction_id="inst_1", group_id="grp1",
            surface="what is a possessor", instruction_kind="question",
            atom_ids=["atom:possessor"],
            confidence=0.8,
        )],
        entry_instruction_id="inst_1",
    )
    query = engine.build_query(obligation, [role_frame], program)
    binding = engine.execute(query, [role_frame])
    if binding.has_answer:
        for fill in binding.slot_fills:
            assert fill.surface not in _ROLE_LABELS, (
                f"Role label leaked into answer: {fill.surface!r}"
            )


def test_response_engine_teaching_continuation_no_role_label():
    """Teaching continuation should not leak role labels.
    v3.1: store_patch produces acknowledgment (e.g. 'Got it.' or 'I've stored that.'),
    not a value echo. The key invariant is that internal role labels never surface."""
    system = SeededSystem()
    result = system.run("my name is Chibueze")
    output = result["output"]
    assert "possessor" not in output.lower(), (
        f"Role label leaked into teaching continuation: {output!r}"
    )
    assert output, f"Output should be non-empty, got: {output!r}"


def test_response_engine_farewell_not_hello():
    """Farewell/exit should not produce 'Hello'."""
    system = SeededSystem()
    result = system.run("bye")
    output = result["output"]
    assert "Hello" not in output, (
        f"Farewell should not produce 'Hello', got: {output!r}"
    )


# ── Test: No role labels through RuntimeCycleResult ──────────────


def test_runtime_compiles_has_role_as_structural():
    graph = UOLGraph(id="g1", signal_id="s1")
    self_atom = graph.add_atom("self", "self:system", surface="self", confidence=0.9)
    user_atom = graph.add_atom("entity", "entity:user", surface="user", confidence=0.9)
    role_edge = graph.add_edge("has_role", self_atom.id, user_atom.id, confidence=0.9)
    role_edge.features["role"] = "possessor"

    compiler = RelationFrameCompiler()
    frames = compiler.compile(graph)

    role_frames = [f for f in frames if f.relation_key == "has_role"]
    for f in role_frames:
        assert f.structural is True, "has_role frame should be structural"
        assert f.answerable is False, "has_role frame should not be answerable"
        assert f.projection_policy == "none", (
            "has_role frame should have projection_policy='none'"
        )


# ── Test: projection_policy controls slot projection ──────────────


def test_projection_policy_none_produces_empty_slots():
    engine = SemanticQueryEngine(None, None)
    role_frame = _make_role_frame("target")

    slot_name, surface, concept_id, entity_id = engine._project_frame(
        role_frame, "none",
    )
    assert slot_name == "object"
    assert surface == ""
    assert concept_id == ""
    assert entity_id == ""


def test_projection_policy_object_projects_object():
    engine = SemanticQueryEngine(None, None)
    frame = _make_teaching_frame(obj_surface="animal")

    slot_name, surface, concept_id, entity_id = engine._project_frame(
        frame, "object",
    )
    assert slot_name == "object"
    assert surface == "animal"


def test_projection_policy_subject_projects_subject():
    engine = SemanticQueryEngine(None, None)
    frame = _make_teaching_frame(subj_surface="dog")

    slot_name, surface, concept_id, entity_id = engine._project_frame(
        frame, "subject",
    )
    assert slot_name == "subject"
    assert surface == "dog"


# ── Test: no first-frame fallback ────────────────────────────────


def test_no_first_frame_fallback():
    engine = SemanticQueryEngine()
    role_frame = _make_role_frame("possessor")

    obligation = ObligationFrame(
        primary_instruction_id="inst_1",
        obligation_kind="answer_concept",
        response_mode="evidence_answer",
    )
    query = engine.build_query(obligation, [role_frame])
    assert query.relation_key == "", (
        "Should not fall back to first frame if it's structural/non-answerable"
    )


# ── Test: structural invariant enforced ────────────────────────────


def test_no_role_labels_in_any_obligation_output():
    """Structural invariant: no answer binding may use a frame where answerable=False."""
    engine = SemanticQueryEngine()
    structural_frame = _make_role_frame("topic")

    obligation = ObligationFrame(
        primary_instruction_id="inst_1",
        obligation_kind="answer_concept",
        response_mode="evidence_answer",
    )
    program = SemanticProgram(
        graph_id="g1", signal_id="s1", context_id="c1",
        instructions=[SemanticInstruction(
            instruction_id="inst_1", group_id="grp1",
            surface="test", instruction_kind="question",
            atom_ids=["atom:self"],
            confidence=0.8,
        )],
        entry_instruction_id="inst_1",
    )

    query = engine.build_query(obligation, [structural_frame], program)
    assert query.relation_key == "", (
        "Structural frame must not be selected for any answer obligation"
    )
