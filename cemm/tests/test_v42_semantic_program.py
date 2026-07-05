"""Tests for v4.2 semantic program compiler, obligation scheduler, teaching frames,
and runtime invariant guard extensions.

These tests verify the architectural invariants from the gap-fix plan:
- Social wrapper cannot be entry when a content question exists.
- Obligation scheduler suppresses lower-force instructions.
- Teaching frame opens/continues/closes correctly.
- Runtime invariant guards catch bypasses.
"""

from __future__ import annotations

import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ["CEMM_EXPORT_PATH"] = ""

from cemm.types.semantic_program import SemanticInstruction, SemanticProgram
from cemm.types.obligation_frame import ObligationFrame
from cemm.types.teaching_frame import TeachingFrame
from cemm.types.uol_graph import UOLGraph, UOLMeaningGroup, UOLAtom, UOLEdge, CandidateSet, PortBinding
from cemm.kernel.semantic_program_compiler import SemanticProgramCompiler
from cemm.kernel.semantic_obligation_scheduler import SemanticObligationScheduler
from cemm.kernel.teaching_frame_manager import TeachingFrameManager
from cemm.kernel.invariant_guard import InvariantGuard


# ── SemanticProgramCompiler ──────────────────────────────────────


def test_compiler_empty_graph():
    compiler = SemanticProgramCompiler()
    program = compiler.compile(UOLGraph(id="g1", signal_id="s1"))
    assert len(program.instructions) == 0
    assert program.entry_instruction_id == ""
    assert program.graph_id == "g1"


def test_compiler_classifies_question():
    graph = UOLGraph(id="g1", signal_id="s1")
    g = UOLMeaningGroup(id="grp1", surface="what's your name?")
    intent_atom = graph.add_atom("intent", "question", surface="what is a president", confidence=0.8)
    g.atom_ids.append(intent_atom.id)
    graph.groups.append(g)
    graph.group_atom_ids[g.id] = g.atom_ids

    compiler = SemanticProgramCompiler()
    program = compiler.compile(graph)
    assert len(program.instructions) == 1
    assert program.instructions[0].instruction_kind == "question"
    assert program.entry_instruction_id == program.instructions[0].instruction_id


def test_compiler_classifies_teaching():
    graph = UOLGraph(id="g1", signal_id="s1")
    g = UOLMeaningGroup(id="grp1", surface="I want to teach you about president")
    intent_atom = graph.add_atom("intent", "teaching", surface="teach", confidence=0.8)
    target_atom = graph.add_atom("entity", "entity:president", surface="president", confidence=0.7)
    graph.add_edge("teaches", intent_atom.id, target_atom.id)
    g.atom_ids.extend([intent_atom.id, target_atom.id])
    graph.groups.append(g)
    graph.group_atom_ids[g.id] = g.atom_ids

    compiler = SemanticProgramCompiler()
    program = compiler.compile(graph)
    assert program.instructions[0].instruction_kind == "teaching"


def test_compiler_social_does_not_suppress_question():
    graph = UOLGraph(id="g1", signal_id="s1")
    social_group = UOLMeaningGroup(id="grp_social", surface="lol")
    intent_social = graph.add_atom("intent", "greeting", surface="lol", confidence=0.6)
    social_group.atom_ids.append(intent_social.id)
    graph.groups.append(social_group)
    graph.group_atom_ids[social_group.id] = social_group.atom_ids

    question_group = UOLMeaningGroup(id="grp_q", surface="what's your name?", parent_group_id="grp_social")
    intent_q = graph.add_atom("intent", "question", surface="what is a president", confidence=0.8)
    question_group.atom_ids.append(intent_q.id)
    graph.groups.append(question_group)
    graph.group_atom_ids[question_group.id] = question_group.atom_ids

    compiler = SemanticProgramCompiler()
    program = compiler.compile(graph)
    entry = program.entry_instruction
    assert entry is not None
    assert entry.instruction_kind == "question"
    rejected = program.diagnostics.get("rejected_candidates", [])
    social_ids = [r["id"] for r in rejected if r["kind"] == "social"]
    assert len(social_ids) >= 1


def test_compiler_preserves_discourse_hierarchy():
    graph = UOLGraph(id="g1", signal_id="s1")
    parent = UOLMeaningGroup(id="grp_parent", surface="ok great")
    child = UOLMeaningGroup(id="grp_child", surface="who's the leader?", parent_group_id="grp_parent")
    parent_intent = graph.add_atom("intent", "acknowledgment", surface="ok", confidence=0.5)
    child_intent = graph.add_atom("intent", "question", surface="who's the leader", confidence=0.8)
    parent.atom_ids.append(parent_intent.id)
    child.atom_ids.append(child_intent.id)
    graph.groups.extend([parent, child])
    graph.group_atom_ids[parent.id] = parent.atom_ids
    graph.group_atom_ids[child.id] = child.atom_ids

    compiler = SemanticProgramCompiler()
    program = compiler.compile(graph)
    child_inst = next(i for i in program.instructions if i.group_id == "grp_child")
    assert child_inst.discourse_parent_id == "grp_parent"
    assert program.entry_instruction_id == child_inst.instruction_id


def test_compiler_preserves_candidate_sets():
    graph = UOLGraph(id="g1", signal_id="s1")
    g = UOLMeaningGroup(id="grp1", surface="test")
    atom = graph.add_atom("entity", "entity:test", surface="test")
    g.atom_ids.append(atom.id)
    graph.groups.append(g)
    graph.group_atom_ids[g.id] = g.atom_ids
    cs = CandidateSet(id="cs1", target_span_id="span1", group_id="grp1")
    graph.candidate_sets.append(cs)

    compiler = SemanticProgramCompiler()
    program = compiler.compile(graph)
    assert "cs1" in program.candidate_sets
    assert "cs1" in program.instructions[0].candidate_set_ids


def test_compiler_extracts_port_slots():
    graph = UOLGraph(id="g1", signal_id="s1")
    g = UOLMeaningGroup(id="grp1", surface="test")
    atom = graph.add_atom("entity", "entity:test", surface="test")
    g.atom_ids.append(atom.id)
    graph.groups.append(g)
    graph.group_atom_ids[g.id] = g.atom_ids
    graph.port_bindings.append(PortBinding(
        owner_atom_id=atom.id, port_key="holder", status="placeholder",
    ))

    compiler = SemanticProgramCompiler()
    program = compiler.compile(graph)
    assert "holder" in program.instructions[0].output_slots


# ── SemanticObligationScheduler ──────────────────────────────────


def test_scheduler_empty_program():
    scheduler = SemanticObligationScheduler()
    program = SemanticProgram(graph_id="g1", signal_id="s1", context_id="c1")
    frame = scheduler.schedule(program)
    assert frame.obligation_kind == "abstain_policy"
    assert frame.confidence < 0.5


def test_scheduler_question_obligation():
    scheduler = SemanticObligationScheduler()
    program = SemanticProgram(
        graph_id="g1", signal_id="s1", context_id="c1",
        instructions=[SemanticInstruction(
            instruction_id="i1", group_id="g1", surface="what is a president?",
            instruction_kind="question", confidence=0.8,
        )],
        entry_instruction_id="i1",
    )
    frame = scheduler.schedule(program)
    assert frame.obligation_kind == "answer_concept"
    assert frame.response_mode == "evidence_answer"
    assert frame.evidence_policy == "required"


def test_scheduler_social_suppressed_by_question():
    scheduler = SemanticObligationScheduler()
    program = SemanticProgram(
        graph_id="g1", signal_id="s1", context_id="c1",
        instructions=[
            SemanticInstruction(
                instruction_id="i_social", group_id="g_social", surface="lol",
                instruction_kind="social", confidence=0.6,
            ),
            SemanticInstruction(
                instruction_id="i_q", group_id="g_q", surface="what is a president?",
                instruction_kind="question", confidence=0.8,
            ),
        ],
        entry_instruction_id="i_q",
        suppressed_instruction_ids=["i_social"],
    )
    frame = scheduler.schedule(program)
    assert frame.obligation_kind == "answer_concept"
    assert len(frame.suppressed_obligations) == 1
    assert frame.suppressed_obligations[0]["instruction_kind"] == "social"


def test_scheduler_self_model_obligation():
    scheduler = SemanticObligationScheduler()
    graph = UOLGraph(id="g1", signal_id="s1")
    self_atom = graph.add_atom("self", "self:ce-mm", surface="CEMM", confidence=0.9)
    program = SemanticProgram(
        graph_id="g1", signal_id="s1", context_id="c1",
        instructions=[SemanticInstruction(
            instruction_id="i1", group_id="g1", surface="what's your name?",
            instruction_kind="question", confidence=0.8,
            atom_ids=[self_atom.id],
        )],
        entry_instruction_id="i1",
    )
    frame = scheduler.schedule(program, uol_graph=graph)
    assert frame.obligation_kind == "answer_self_model"


def test_scheduler_teaching_obligation():
    scheduler = SemanticObligationScheduler()
    program = SemanticProgram(
        graph_id="g1", signal_id="s1", context_id="c1",
        instructions=[SemanticInstruction(
            instruction_id="i1", group_id="g1", surface="teach about president",
            instruction_kind="teaching", confidence=0.7,
        )],
        entry_instruction_id="i1",
    )
    frame = scheduler.schedule(program)
    assert frame.obligation_kind == "continue_teaching"
    assert frame.write_policy == "patch_only"


def test_scheduler_assertion_obligation():
    scheduler = SemanticObligationScheduler()
    program = SemanticProgram(
        graph_id="g1", signal_id="s1", context_id="c1",
        instructions=[SemanticInstruction(
            instruction_id="i1", group_id="g1", surface="a president is a leader",
            instruction_kind="assertion", confidence=0.7,
        )],
        entry_instruction_id="i1",
    )
    frame = scheduler.schedule(program)
    assert frame.obligation_kind == "store_patch"
    assert frame.write_policy == "patch_only"


def test_scheduler_blocked_by_unresolved_ports():
    from cemm.kernel.semantic_working_set import SemanticWorkingSet
    from cemm.types.semantic_focus import SemanticFocus

    scheduler = SemanticObligationScheduler()
    program = SemanticProgram(
        graph_id="g1", signal_id="s1", context_id="c1",
        instructions=[SemanticInstruction(
            instruction_id="i1", group_id="g1", surface="test",
            instruction_kind="question", confidence=0.8,
            output_slots={"holder": ""},
        )],
        entry_instruction_id="i1",
    )
    ws = SemanticWorkingSet(
        focus_items=[SemanticFocus("a1", "unresolved_required_port", 2, 0.5)],
        unresolved_ports=["holder"],
    )
    frame = scheduler.schedule(program, ws)
    assert "unresolved_port:holder" in frame.blocked_by


# ── TeachingFrameManager ─────────────────────────────────────────


def test_teaching_frame_opens_on_teaching_instruction():
    mgr = TeachingFrameManager()
    program = SemanticProgram(
        graph_id="g1", signal_id="s1", context_id="c1",
        instructions=[SemanticInstruction(
            instruction_id="i1", group_id="g1", surface="teach about president",
            instruction_kind="teaching", confidence=0.7,
        )],
        entry_instruction_id="i1",
    )
    graph = UOLGraph(id="g1", signal_id="s1")
    intent_atom = graph.add_atom("intent", "intent:teach", surface="teach")
    target_atom = graph.add_atom("entity", "entity:president", surface="president")
    graph.add_edge("teaches", intent_atom.id, target_atom.id)
    program.instructions[0].atom_ids = [intent_atom.id, target_atom.id]

    frame = mgr.process_turn(program, graph, signal_id="sig1")
    assert frame is not None
    assert frame.target_concept_key == "president"
    assert frame.active is True
    assert frame.started_signal_id == "sig1"


def test_teaching_frame_continues_on_related_input():
    mgr = TeachingFrameManager()

    teach_program = SemanticProgram(
        graph_id="g1", signal_id="s1", context_id="c1",
        instructions=[SemanticInstruction(
            instruction_id="i1", group_id="g1", surface="teach about president",
            instruction_kind="teaching", confidence=0.7,
        )],
        entry_instruction_id="i1",
    )
    graph1 = UOLGraph(id="g1", signal_id="s1")
    intent_atom = graph1.add_atom("intent", "intent:teach", surface="teach")
    target_atom = graph1.add_atom("entity", "entity:president", surface="president")
    graph1.add_edge("teaches", intent_atom.id, target_atom.id)
    teach_program.instructions[0].atom_ids = [intent_atom.id, target_atom.id]

    mgr.process_turn(teach_program, graph1, signal_id="sig1")

    cont_program = SemanticProgram(
        graph_id="g2", signal_id="s2", context_id="c1",
        instructions=[SemanticInstruction(
            instruction_id="i2", group_id="g2", surface="a president is a leader",
            instruction_kind="assertion", confidence=0.6,
            discourse_relation="elaboration",
        )],
        entry_instruction_id="i2",
    )
    graph2 = UOLGraph(id="g2", signal_id="s2")
    frame = mgr.process_turn(cont_program, graph2, signal_id="sig2")
    assert frame is not None
    assert frame.target_concept_key == "president"
    assert frame.last_signal_id == "sig2"
    assert "g2" in frame.accumulated_graph_ids


def test_teaching_frame_closes_on_unrelated_input():
    mgr = TeachingFrameManager()

    teach_program = SemanticProgram(
        graph_id="g1", signal_id="s1", context_id="c1",
        instructions=[SemanticInstruction(
            instruction_id="i1", group_id="g1", surface="teach about president",
            instruction_kind="teaching", confidence=0.7,
        )],
        entry_instruction_id="i1",
    )
    graph1 = UOLGraph(id="g1", signal_id="s1")
    intent_atom = graph1.add_atom("intent", "intent:teach", surface="teach")
    target_atom = graph1.add_atom("entity", "entity:president", surface="president")
    graph1.add_edge("teaches", intent_atom.id, target_atom.id)
    teach_program.instructions[0].atom_ids = [intent_atom.id, target_atom.id]

    mgr.process_turn(teach_program, graph1, signal_id="sig1")
    assert mgr.active_frame is not None

    unrelated_program = SemanticProgram(
        graph_id="g2", signal_id="s2", context_id="c1",
        instructions=[SemanticInstruction(
            instruction_id="i2", group_id="g2", surface="what's the weather?",
            instruction_kind="question", confidence=0.8,
        )],
        entry_instruction_id="i2",
    )
    mgr.process_turn(unrelated_program, UOLGraph(id="g2", signal_id="s2"), signal_id="sig2")
    assert mgr.active_frame is None or not mgr.active_frame.active


def test_teaching_frame_no_op_without_program():
    mgr = TeachingFrameManager()
    assert mgr.active_frame is None
    assert mgr.process_turn(None) is None


# ── InvariantGuard extensions ────────────────────────────────────


def test_invariant_no_social_over_content_passes():
    InvariantGuard.reset()
    assert InvariantGuard.check_no_social_over_content("question", []) is True
    assert InvariantGuard.errors == []


def test_invariant_no_social_over_content_fails():
    InvariantGuard.reset()
    result = InvariantGuard.check_no_social_over_content("social", ["question"])
    assert result is False
    assert len(InvariantGuard.errors) == 1
    assert "social" in InvariantGuard.errors[0]


def test_invariant_no_decision_without_uol_graph():
    InvariantGuard.reset()
    assert InvariantGuard.check_no_decision_without_uol_graph(True) is True
    assert InvariantGuard.check_no_decision_without_uol_graph(False) is False
    assert len(InvariantGuard.errors) == 1


def test_invariant_no_realization_without_contract():
    InvariantGuard.reset()
    assert InvariantGuard.check_no_realization_without_contract(True, "hello") is True
    assert InvariantGuard.check_no_realization_without_contract(False, "hello") is False
    assert InvariantGuard.check_no_realization_without_contract(False, "") is True


def test_invariant_no_patch_commit_without_validation():
    InvariantGuard.reset()
    assert InvariantGuard.check_no_patch_commit_without_validation(True) is True
    assert InvariantGuard.check_no_patch_commit_without_validation(False) is False


def test_invariant_no_custom_upsert_claim():
    InvariantGuard.reset()
    assert InvariantGuard.check_no_custom_upsert_claim_outside_adapter("upsert_relation_candidate") is True
    assert InvariantGuard.check_no_custom_upsert_claim_outside_adapter("custom:upsert_claim") is False
    assert len(InvariantGuard.errors) == 1


# ── SemanticKernelRuntime integration ────────────────────────────


def test_runtime_produces_semantic_program_diagnostics():
    from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime
    from cemm.types.context_kernel import ContextKernel
    from cemm.types.signal import Signal, SignalKind, SourceType
    from cemm.types.permission import Permission
    import time

    runtime = SemanticKernelRuntime()
    signal = Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content="what's your name?",
        observed_at=time.time(),
        context_id="test",
        salience=0.8,
        trust=0.8,
        permission=Permission.public(),
    )
    kernel = ContextKernel(id="test")
    result = runtime.run_turn(signal, kernel)
    assert result.diagnostics is not None
    assert "semantic_program" in result.diagnostics


def test_runtime_exposes_new_components():
    from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime
    runtime = SemanticKernelRuntime()
    assert runtime.program_compiler is not None
    assert runtime.obligation_scheduler is not None
    assert runtime.teaching_frame_manager is not None
