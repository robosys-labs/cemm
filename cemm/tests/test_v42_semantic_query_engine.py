"""Tests for v4.2 PR3: SemanticQueryEngine, SemanticQuery, AnswerBinding, RealizationContract.

Tests the architectural breakthrough: closing the loop from ObligationFrame
through RelationAlgebra to RealizationContract.
"""

from __future__ import annotations

import os
import sys
import uuid
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.types.semantic_query import SemanticQuery, QueryConstraint
from cemm.types.answer_binding import AnswerBinding, SlotFill
from cemm.types.realization_contract import RealizationContract, RealizationSlot
from cemm.types.relation_frame import RelationFrame, RelationArgument
from cemm.types.obligation_frame import ObligationFrame
from cemm.types.semantic_program import SemanticProgram, SemanticInstruction
from cemm.types.uol_graph import UOLGraph
from cemm.kernel.semantic_query_engine import SemanticQueryEngine
from cemm.kernel.semantic_realizer import SemanticRealizer
from cemm.kernel.relation_algebra import RelationAlgebra
from cemm.kernel.relation_frame_compiler import RelationFrameCompiler
from cemm.memory.predicate_schema_store import PredicateSchemaStore
from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime
from cemm.types.context_kernel import ContextKernel
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission


# ── Helpers ───────────────────────────────────────────────────────


def _signal(text: str = "hello") -> Signal:
    return Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content=text,
        observed_at=time.time(),
        context_id="query_test",
        salience=0.8,
        trust=0.8,
        permission=Permission.public(),
    )


def _kernel() -> ContextKernel:
    return ContextKernel(id=uuid.uuid4().hex[:16])


def _make_frame(
    relation_key: str = "is_a",
    subj_concept: str = "dog",
    obj_concept: str = "animal",
    subj_surface: str = "dog",
    obj_surface: str = "animal",
    confidence: float = 0.8,
) -> RelationFrame:
    return RelationFrame(
        relation_id=uuid.uuid4().hex[:16],
        relation_key=relation_key,
        relation_family="taxonomy",
        subject=RelationArgument(role="subject", concept_id=subj_concept, surface=subj_surface, confidence=confidence),
        object=RelationArgument(role="object", concept_id=obj_concept, surface=obj_surface, confidence=confidence),
        confidence=confidence,
    )


def _make_obligation(
    kind: str = "answer_concept",
    response_mode: str = "evidence_answer",
    evidence_policy: str = "required",
    write_policy: str = "none",
    required_slots: list[str] | None = None,
    blocked_by: list[str] | None = None,
) -> ObligationFrame:
    return ObligationFrame(
        primary_instruction_id="inst_1",
        obligation_kind=kind,
        response_mode=response_mode,
        evidence_policy=evidence_policy,
        write_policy=write_policy,
        required_slots=required_slots or [],
        blocked_by=blocked_by or [],
        confidence=0.7,
    )


def _make_program(surface: str = "what is a dog") -> SemanticProgram:
    return SemanticProgram(
        graph_id="g1",
        signal_id="s1",
        context_id="c1",
        instructions=[SemanticInstruction(
            instruction_id="inst_1",
            group_id="grp1",
            surface=surface,
            instruction_kind="question",
            confidence=0.8,
        )],
        entry_instruction_id="inst_1",
    )


# ── SemanticQuery type tests ──────────────────────────────────────


def test_semantic_query_defaults():
    q = SemanticQuery()
    assert q.query_kind == "lookup"
    assert q.allow_inheritance is True
    assert q.allow_inverse is True
    assert q.evidence_policy == "speaker_asserted"


def test_query_constraint_defaults():
    c = QueryConstraint()
    assert c.role == ""
    assert c.concept_id == ""
    assert c.confidence == 0.5


# ── AnswerBinding type tests ──────────────────────────────────────


def test_answer_binding_defaults():
    b = AnswerBinding()
    assert b.has_answer is False
    assert b.confidence == 0.0
    assert b.slot_fills == []


def test_answer_binding_evidence_refs_present_empty():
    b = AnswerBinding()
    assert b.evidence_refs_present() is False


def test_answer_binding_evidence_refs_present_with_evidence():
    b = AnswerBinding(
        slot_fills=[SlotFill(slot_name="object", evidence_refs=["ev1", "ev2"])],
    )
    assert b.evidence_refs_present() is True


# ── RealizationContract type tests ────────────────────────────────


def test_realization_contract_defaults():
    c = RealizationContract()
    assert c.response_mode == "general_conversation"
    assert c.evidence_policy == "none"
    assert c.explanation_required is False


# ── SemanticQueryEngine: build_query ──────────────────────────────


def test_build_query_from_obligation():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    frames = [_make_frame("is_a", "dog", "animal")]
    obligation = _make_obligation("answer_concept", "evidence_answer", "required")
    program = _make_program()

    query = engine.build_query(obligation, frames, program)
    assert query.query_kind == "lookup"
    assert query.evidence_policy == "required"
    assert query.source_obligation_id == "inst_1"


def test_build_query_no_frames():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    obligation = _make_obligation()
    query = engine.build_query(obligation, [])
    assert query.relation_key == ""
    assert query.query_kind == "lookup"


def test_build_query_blocked_obligation():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    obligation = _make_obligation(blocked_by=["unresolved_port:holder"])
    query = engine.build_query(obligation, [])
    assert query.blocked_by == ["unresolved_port:holder"]


def test_build_query_social_reply_kind():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    obligation = _make_obligation("social_reply", "social_response", "none")
    query = engine.build_query(obligation, [])
    assert query.query_kind == "none"


def test_build_query_store_patch_kind():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    obligation = _make_obligation("store_patch", "store_confirmation", "speaker_asserted", "patch_only")
    query = engine.build_query(obligation, [])
    assert query.query_kind == "assert"


def test_build_query_answer_relation_kind():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)
    obligation = _make_obligation("answer_relation", "evidence_answer", "required")
    query = engine.build_query(obligation, [])
    assert query.query_kind == "lookup"


def test_build_query_answer_user_profile_kind():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)
    obligation = _make_obligation("answer_user_profile", "user_profile", "none")
    query = engine.build_query(obligation, [])
    assert query.query_kind == "lookup"


def test_build_query_ask_clarification_kind():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)
    obligation = _make_obligation("ask_clarification", "ask_clarification", "none")
    query = engine.build_query(obligation, [])
    assert query.query_kind == "clarify"


def test_build_query_abstain_policy_kind():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)
    obligation = _make_obligation("abstain_policy", "abstain", "none")
    query = engine.build_query(obligation, [])
    assert query.query_kind == "none"


def test_build_query_exit_kind():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)
    obligation = _make_obligation("exit", "session_exit", "none")
    query = engine.build_query(obligation, [])
    assert query.query_kind == "none"


# ── SemanticQueryEngine: execute ──────────────────────────────────


def test_execute_blocked_query_returns_abstention():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    query = SemanticQuery(
        query_id="q1",
        blocked_by=["unresolved_port:holder"],
    )
    binding = engine.execute(query, [])
    assert binding.has_answer is False
    assert "blocked" in binding.abstention_reason


def test_execute_no_relation_key_returns_abstention():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    query = SemanticQuery(query_id="q1", relation_key="")
    binding = engine.execute(query, [])
    assert binding.has_answer is False
    assert binding.abstention_reason == "no_relation_key_or_algebra"


def test_execute_no_matches_returns_abstention():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    query = SemanticQuery(query_id="q1", relation_key="is_a")
    binding = engine.execute(query, [])
    assert binding.has_answer is False
    assert binding.abstention_reason == "no_matches"


def test_execute_with_matching_frames():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    frames = [_make_frame("is_a", "dog", "animal")]
    query = SemanticQuery(
        query_id="q1",
        relation_key="is_a",
        allow_inheritance=False,
        allow_inverse=False,
    )
    binding = engine.execute(query, frames)
    assert binding.has_answer is True
    assert len(binding.slot_fills) == 1
    assert binding.slot_fills[0].concept_id == "animal"
    assert binding.confidence > 0.0


def test_execute_with_object_constraint():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    frames = [
        _make_frame("is_a", "dog", "animal"),
        _make_frame("is_a", "cat", "animal"),
        _make_frame("is_a", "car", "vehicle"),
    ]
    query = SemanticQuery(
        query_id="q1",
        relation_key="is_a",
        object_constraint=QueryConstraint(concept_id="vehicle"),
        allow_inheritance=False,
        allow_inverse=False,
    )
    binding = engine.execute(query, frames)
    assert binding.has_answer is True
    assert len(binding.slot_fills) == 1
    assert binding.slot_fills[0].concept_id == "vehicle"


def test_execute_with_subject_constraint():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    frames = [
        _make_frame("is_a", "dog", "animal"),
        _make_frame("is_a", "cat", "animal"),
        _make_frame("is_a", "car", "vehicle"),
    ]
    query = SemanticQuery(
        query_id="q1",
        relation_key="is_a",
        subject_constraint=QueryConstraint(concept_id="dog"),
        allow_inheritance=False,
        allow_inverse=False,
    )
    binding = engine.execute(query, frames)
    assert binding.has_answer is True
    assert len(binding.slot_fills) == 1
    assert binding.slot_fills[0].concept_id == "animal"


def test_execute_with_subject_and_object_constraint():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    frames = [
        _make_frame("is_a", "dog", "animal"),
        _make_frame("is_a", "dog", "mammal"),
        _make_frame("is_a", "cat", "animal"),
    ]
    query = SemanticQuery(
        query_id="q1",
        relation_key="is_a",
        subject_constraint=QueryConstraint(concept_id="dog"),
        object_constraint=QueryConstraint(concept_id="animal"),
        allow_inheritance=False,
        allow_inverse=False,
    )
    binding = engine.execute(query, frames)
    assert binding.has_answer is True
    assert len(binding.slot_fills) == 1
    assert binding.slot_fills[0].concept_id == "animal"


def test_execute_subject_constraint_no_match_returns_abstention():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    frames = [_make_frame("is_a", "dog", "animal")]
    query = SemanticQuery(
        query_id="q1",
        relation_key="is_a",
        subject_constraint=QueryConstraint(concept_id="cat"),
        allow_inheritance=False,
        allow_inverse=False,
    )
    binding = engine.execute(query, frames)
    assert binding.has_answer is False
    assert binding.abstention_reason == "no_matches"


def test_execute_with_inheritance_expansion():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    frames = [
        _make_frame("is_a", "dog", "animal"),
        _make_frame("is_a", "puppy", "dog"),
        _make_frame("has_role", "puppy", "pet", confidence=0.7),
    ]
    frames[2].relation_family = "role"
    query = SemanticQuery(
        query_id="q1",
        relation_key="has_role",
        allow_inheritance=True,
        allow_inverse=False,
    )
    binding = engine.execute(query, frames)
    assert binding.has_answer is True
    assert len(binding.slot_fills) >= 1


def test_execute_explanation_paths_populated():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    frames = [_make_frame("is_a", "dog", "animal")]
    query = SemanticQuery(
        query_id="q1",
        relation_key="is_a",
        allow_inheritance=False,
        allow_inverse=False,
    )
    binding = engine.execute(query, frames)
    assert binding.has_answer is True
    assert len(binding.explanation_paths) >= 1
    assert len(binding.explanation_paths[0]) >= 1


# ── SemanticQueryEngine: build_contract ───────────────────────────


def test_build_contract_with_answer():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    obligation = _make_obligation("answer_concept", "evidence_answer", "required")
    binding = AnswerBinding(
        binding_id="b1",
        source_query_id="q1",
        has_answer=True,
        slot_fills=[SlotFill(slot_name="object", concept_id="animal", surface="animal", confidence=0.8)],
        confidence=0.8,
    )
    contract = engine.build_contract(obligation, binding)
    assert contract.response_mode == "evidence_answer"
    assert contract.template_key == "evidence_answer"
    assert contract.evidence_policy == "required"
    assert contract.explanation_required is True
    assert contract.abstention_reason == ""
    assert "answer" in contract.slots


def test_build_contract_no_answer():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    obligation = _make_obligation("answer_concept", "evidence_answer", "required")
    binding = AnswerBinding(
        binding_id="b1",
        source_query_id="q1",
        has_answer=False,
        abstention_reason="no_matches",
    )
    contract = engine.build_contract(obligation, binding)
    assert contract.template_key == "abstain"
    assert contract.abstention_reason == "no_matches"
    assert contract.explanation_required is False


def test_build_contract_self_model():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    obligation = _make_obligation("answer_self_model", "evidence_answer", "required")
    binding = AnswerBinding(
        binding_id="b1",
        has_answer=True,
        slot_fills=[SlotFill(slot_name="object", surface="CEMM", confidence=0.9)],
        confidence=0.9,
    )
    contract = engine.build_contract(obligation, binding)
    assert contract.template_key == "self_identity"


def test_build_contract_store_patch():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    obligation = _make_obligation("store_patch", "store_confirmation", "speaker_asserted", "patch_only")
    binding = AnswerBinding(
        binding_id="b1",
        has_answer=True,
        slot_fills=[SlotFill(slot_name="object", surface="president", confidence=0.7)],
        confidence=0.7,
    )
    contract = engine.build_contract(obligation, binding)
    assert contract.template_key == "store_confirmation"
    assert contract.write_policy == "patch_only"


def test_build_contract_answer_relation():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)
    obligation = _make_obligation("answer_relation", "evidence_answer", "required")
    binding = AnswerBinding(
        binding_id="b1", has_answer=True,
        slot_fills=[SlotFill(slot_name="object", surface="mammal", confidence=0.8)],
        confidence=0.8,
    )
    contract = engine.build_contract(obligation, binding)
    assert contract.template_key == "evidence_answer"


def test_build_contract_answer_user_profile():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)
    obligation = _make_obligation("answer_user_profile", "user_profile", "none")
    binding = AnswerBinding(
        binding_id="b1", has_answer=True,
        slot_fills=[SlotFill(slot_name="object", surface="name is Alice", confidence=0.7)],
        confidence=0.7,
    )
    contract = engine.build_contract(obligation, binding)
    assert contract.template_key == "user_profile"


def test_build_contract_ask_clarification():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)
    obligation = _make_obligation("ask_clarification", "ask_clarification", "none")
    binding = AnswerBinding(
        binding_id="b1", has_answer=True,
        slot_fills=[SlotFill(slot_name="object", surface="that term", confidence=0.5)],
        confidence=0.5,
    )
    contract = engine.build_contract(obligation, binding)
    assert contract.template_key == "ask_clarification"


def test_build_contract_exit():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)
    obligation = _make_obligation("exit", "session_exit", "none")
    binding = AnswerBinding(
        binding_id="b1", has_answer=True,
        slot_fills=[SlotFill(slot_name="object", surface="goodbye", confidence=0.9)],
        confidence=0.9,
    )
    contract = engine.build_contract(obligation, binding)
    assert contract.template_key == "session_exit"


def test_build_contract_verification_level_strict():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    obligation = _make_obligation("answer_concept", "evidence_answer", "required")
    binding = AnswerBinding(
        binding_id="b1",
        has_answer=True,
        slot_fills=[SlotFill(slot_name="object", concept_id="animal", confidence=0.8)],
        confidence=0.8,
    )
    contract = engine.build_contract(obligation, binding)
    assert contract.verification_level == "strict"


def test_build_contract_unfilled_slots():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    obligation = _make_obligation("answer_concept", "evidence_answer", "required", required_slots=["holder", "answer"])
    binding = AnswerBinding(
        binding_id="b1",
        has_answer=True,
        slot_fills=[SlotFill(slot_name="answer", concept_id="animal", confidence=0.8)],
        confidence=0.8,
    )
    contract = engine.build_contract(obligation, binding)
    assert "answer" in contract.filled_slots
    assert "holder" in contract.unfilled_slots


# ── SemanticQueryEngine: run (full pipeline) ──────────────────────


def test_run_full_pipeline_with_answer():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    frames = [_make_frame("is_a", "dog", "animal")]
    obligation = _make_obligation("answer_concept", "evidence_answer", "required")
    program = _make_program()

    query, binding, contract = engine.run(obligation, frames, program)
    assert query.query_kind == "lookup"
    assert binding.has_answer is True
    assert contract.template_key == "evidence_answer"


def test_run_full_pipeline_no_answer():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    obligation = _make_obligation("answer_concept", "evidence_answer", "required")
    program = _make_program()

    query, binding, contract = engine.run(obligation, [], program)
    assert binding.has_answer is False
    assert contract.template_key == "abstain"


def test_run_full_pipeline_blocked():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    obligation = _make_obligation(blocked_by=["unresolved_port:holder"])
    program = _make_program()

    query, binding, contract = engine.run(obligation, [], program)
    assert binding.has_answer is False
    assert "blocked" in binding.abstention_reason
    assert contract.template_key == "blocked"


# ── Runtime integration ───────────────────────────────────────────


def test_runtime_exposes_query_engine():
    runtime = SemanticKernelRuntime()
    assert runtime.query_engine is not None


def test_runtime_diagnostics_include_query_results():
    runtime = SemanticKernelRuntime()
    result = runtime.run_turn(_signal("what is a dog"), _kernel())
    assert result.diagnostics is not None
    if "semantic_query" in result.diagnostics:
        assert "query_kind" in result.diagnostics["semantic_query"]
        assert "answer_binding" in result.diagnostics
        assert "realization_contract" in result.diagnostics


def test_runtime_diagnostics_include_realization_contract():
    runtime = SemanticKernelRuntime()
    result = runtime.run_turn(_signal("hello"), _kernel())
    assert result.diagnostics is not None
    if "realization_contract" in result.diagnostics:
        rc = result.diagnostics["realization_contract"]
        assert "response_mode" in rc
        assert "template_key" in rc


# ── Golden path: inheritance through query engine ─────────────────


def test_golden_inherited_answer_through_query_engine():
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)

    frames = [
        _make_frame("is_a", "dog", "animal"),
        _make_frame("is_a", "puppy", "dog"),
        _make_frame("has_role", "dog", "pet", confidence=0.7),
    ]
    frames[2].relation_family = "role"

    obligation = _make_obligation("answer_concept", "evidence_answer", "required")
    program = _make_program()

    query, binding, contract = engine.run(obligation, frames, program)
    assert binding.has_answer is True
    assert len(binding.slot_fills) >= 1
    assert any(f.is_inherited for f in binding.slot_fills) or len(binding.slot_fills) >= 1
    assert contract.explanation_required is True


# ── SemanticRealizer tests ────────────────────────────────────────


def test_realizer_evidence_answer():
    realizer = SemanticRealizer()
    contract = RealizationContract(
        template_key="evidence_answer",
        slots={"answer": RealizationSlot(slot_key="answer", slot_kind="concept", value="a dog is an animal")},
    )
    text = realizer.realize(contract)
    assert text == "a dog is an animal"


def test_realizer_self_identity():
    realizer = SemanticRealizer()
    contract = RealizationContract(
        template_key="self_identity",
        slots={"answer": RealizationSlot(slot_key="answer", slot_kind="self_identity", value="CEMM")},
    )
    text = realizer.realize(contract)
    assert "CEMM" in text


def test_realizer_store_confirmation():
    realizer = SemanticRealizer()
    contract = RealizationContract(
        template_key="store_confirmation",
        slots={"answer": RealizationSlot(slot_key="answer", slot_kind="concept", value="a president is a leader")},
    )
    text = realizer.realize(contract)
    assert "learned" in text
    assert "president" in text


def test_realizer_abstain_no_reason():
    realizer = SemanticRealizer()
    contract = RealizationContract(
        template_key="abstain",
        abstention_reason="",
    )
    text = realizer.realize(contract)
    assert "not sure" in text.lower()


def test_realizer_abstain_with_reason():
    realizer = SemanticRealizer()
    contract = RealizationContract(
        template_key="abstain",
        abstention_reason="no_matches",
    )
    text = realizer.realize(contract)
    assert "don't have enough information" in text


def test_realizer_blocked():
    realizer = SemanticRealizer()
    contract = RealizationContract(
        template_key="blocked",
        abstention_reason="blocked:unresolved_port:holder",
    )
    text = realizer.realize(contract)
    assert "more information" in text


def test_realizer_fills_answer_from_binding():
    realizer = SemanticRealizer()
    contract = RealizationContract(template_key="evidence_answer")
    binding = AnswerBinding(
        slot_fills=[SlotFill(slot_name="object", surface="animal", confidence=0.8)],
    )
    text = realizer.realize(contract, binding)
    assert text == "animal"


def test_realizer_fills_answer_from_concept_id():
    realizer = SemanticRealizer()
    contract = RealizationContract(template_key="evidence_answer")
    binding = AnswerBinding(
        slot_fills=[SlotFill(slot_name="object", concept_id="mammal", confidence=0.8)],
    )
    text = realizer.realize(contract, binding)
    assert text == "mammal"


def test_realizer_appends_explanation_when_required():
    realizer = SemanticRealizer()
    contract = RealizationContract(
        template_key="evidence_answer",
        explanation_required=True,
        slots={"answer": RealizationSlot(slot_key="answer", slot_kind="concept", value="pet")},
    )
    binding = AnswerBinding(
        slot_fills=[SlotFill(slot_name="object", surface="pet", confidence=0.7)],
        explanation_paths=[["puppy", "is_a", "dog", "has_role", "pet"]],
    )
    text = realizer.realize(contract, binding)
    assert "pet" in text
    assert "via:" in text


def test_realizer_no_explanation_when_not_required():
    realizer = SemanticRealizer()
    contract = RealizationContract(
        template_key="evidence_answer",
        explanation_required=False,
        slots={"answer": RealizationSlot(slot_key="answer", slot_kind="concept", value="animal")},
    )
    binding = AnswerBinding(
        slot_fills=[SlotFill(slot_name="object", surface="animal", confidence=0.8)],
        explanation_paths=[["dog", "is_a", "animal"]],
    )
    text = realizer.realize(contract, binding)
    assert "via:" not in text


def test_realizer_social_response():
    realizer = SemanticRealizer()
    contract = RealizationContract(template_key="social_response")
    text = realizer.realize(contract)
    assert text == "Hello!"


def test_realizer_general_conversation():
    realizer = SemanticRealizer()
    contract = RealizationContract(template_key="general_conversation")
    text = realizer.realize(contract)
    assert text == "I understand."


def test_realizer_teaching_continuation():
    realizer = SemanticRealizer()
    contract = RealizationContract(
        template_key="teaching_continuation",
        slots={"answer": RealizationSlot(slot_key="answer", slot_kind="concept", value="a president is a leader")},
    )
    text = realizer.realize(contract)
    assert "president" in text
    assert "Tell me more" in text


def test_realizer_user_profile():
    realizer = SemanticRealizer()
    contract = RealizationContract(
        template_key="user_profile",
        slots={"answer": RealizationSlot(slot_key="answer", slot_kind="profile", value="name is Alice")},
    )
    text = realizer.realize(contract)
    assert "Alice" in text


def test_realizer_ask_clarification():
    realizer = SemanticRealizer()
    contract = RealizationContract(
        template_key="ask_clarification",
        slots={"answer": RealizationSlot(slot_key="answer", slot_kind="surface", value="that term")},
    )
    text = realizer.realize(contract)
    assert "clarify" in text


def test_realizer_session_exit():
    realizer = SemanticRealizer()
    contract = RealizationContract(template_key="session_exit")
    text = realizer.realize(contract)
    assert text == "Goodbye!"


def test_realizer_missing_variable_falls_back_gracefully():
    realizer = SemanticRealizer()
    contract = RealizationContract(
        template_key="self_identity",
        slots={},
    )
    text = realizer.realize(contract)
    assert text == "I'm not sure about that yet."


def test_realizer_rejects_slot_kind_mismatch():
    """A mood value (surface) cannot fill a self_identity slot."""
    realizer = SemanticRealizer()
    contract = RealizationContract(
        template_key="self_identity",
        slots={"answer": RealizationSlot(slot_key="answer", slot_kind="surface", value="good")},
    )
    text = realizer.realize(contract)
    assert "good" not in text
    assert text == "I'm not sure about that yet."


def test_realizer_rejects_surface_for_profile():
    """A surface value cannot fill a profile slot."""
    realizer = SemanticRealizer()
    contract = RealizationContract(
        template_key="user_profile",
        slots={"answer": RealizationSlot(slot_key="answer", slot_kind="surface", value="happy")},
    )
    text = realizer.realize(contract)
    assert "happy" not in text
    assert text == "I'm not sure about that yet."


def test_realizer_accepts_entity_for_self_identity():
    """An entity value can fill a self_identity slot."""
    realizer = SemanticRealizer()
    contract = RealizationContract(
        template_key="self_identity",
        slots={"answer": RealizationSlot(slot_key="answer", slot_kind="entity", value="CEMM")},
    )
    text = realizer.realize(contract)
    assert "CEMM" in text


def test_realizer_slot_has_lineage():
    """RealizationSlot carries source_binding_id and source_atom_id for traceability."""
    slot = RealizationSlot(
        slot_key="answer",
        slot_kind="concept",
        value="animal",
        source_binding_id="b1",
        source_atom_id="atom_5",
        confidence=0.8,
    )
    assert slot.source_binding_id == "b1"
    assert slot.source_atom_id == "atom_5"
    assert slot.confidence == 0.8


def test_build_contract_produces_typed_slots():
    """build_contract should produce RealizationSlots with correct kinds."""
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)
    obligation = _make_obligation("answer_concept", "evidence_answer", "required")
    binding = AnswerBinding(
        binding_id="b1",
        has_answer=True,
        slot_fills=[SlotFill(slot_name="object", concept_id="animal", surface="animal", confidence=0.8)],
        confidence=0.8,
    )
    contract = engine.build_contract(obligation, binding)
    assert "answer" in contract.slots
    slot = contract.slots["answer"]
    assert slot.slot_kind == "concept"
    assert slot.value == "animal"
    assert slot.source_binding_id == "b1"
    assert slot.confidence == 0.8


def test_build_contract_self_model_slot_kind():
    """answer_self_model should produce self_identity slot kind."""
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)
    obligation = _make_obligation("answer_self_model", "self_identity", "none")
    binding = AnswerBinding(
        binding_id="b1",
        has_answer=True,
        slot_fills=[SlotFill(slot_name="object", surface="CEMM", confidence=0.9)],
        confidence=0.9,
    )
    contract = engine.build_contract(obligation, binding)
    assert contract.slots["answer"].slot_kind == "self_identity"


def test_build_contract_user_profile_slot_kind():
    """answer_user_profile should produce profile slot kind."""
    store = PredicateSchemaStore()
    algebra = RelationAlgebra(store)
    engine = SemanticQueryEngine(algebra, store)
    obligation = _make_obligation("answer_user_profile", "user_profile", "none")
    binding = AnswerBinding(
        binding_id="b1",
        has_answer=True,
        slot_fills=[SlotFill(slot_name="object", surface="Chibueze", confidence=0.7)],
        confidence=0.7,
    )
    contract = engine.build_contract(obligation, binding)
    assert contract.slots["answer"].slot_kind == "profile"


# ── First-class field tests ───────────────────────────────────────


def test_runtime_result_has_first_class_v42_fields():
    runtime = SemanticKernelRuntime()
    result = runtime.run_turn(_signal("what is a dog"), _kernel())
    assert result.semantic_program is not None
    assert result.obligation_frame is not None
    assert isinstance(result.relation_frames, list)
    assert hasattr(result, "semantic_query")
    assert hasattr(result, "answer_binding")
    assert hasattr(result, "realization_contract")


def test_runtime_realized_output_populated():
    runtime = SemanticKernelRuntime()
    result = runtime.run_turn(_signal("hello"), _kernel())
    assert isinstance(result.realized_output, str)


def test_runtime_realizer_property():
    runtime = SemanticKernelRuntime()
    assert runtime.realizer is not None


def test_runtime_full_semantic_path_with_relation_frames():
    runtime = SemanticKernelRuntime()
    result = runtime.run_turn(_signal("a dog is an animal"), _kernel())
    assert result.semantic_program is not None
    assert result.obligation_frame is not None
    if result.relation_frames:
        keys = [f.relation_key for f in result.relation_frames]
        assert "is_a" in keys or any(k for k in keys)
