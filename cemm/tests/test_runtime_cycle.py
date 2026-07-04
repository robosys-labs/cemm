"""Tests for Phase 3 runtime cycle infrastructure."""

from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ["CEMM_EXPORT_PATH"] = ""

from cemm.types.runtime_cycle import RuntimeCycleResult
from cemm.types.semantic_focus import SemanticFocus
from cemm.kernel.semantic_working_set import SemanticWorkingSet
from cemm.kernel.semantic_attention_controller import SemanticAttentionController
from cemm.types.uol_graph import UOLGraph, UOLAtom, PortBinding, CandidateSet, ConceptResolution, AffordancePrediction
from cemm.types.context_kernel import ContextKernel, Budget, WorldState, UserState, TimeState, ConversationState, GoalState, MemoryState


def test_runtime_cycle_result_defaults():
    result = RuntimeCycleResult(signal="s1", context_kernel="k1")
    assert result.signal == "s1"
    assert result.context_kernel == "k1"
    assert result.percept is None
    assert result.patch_candidates == []
    assert result.realized_output == ""
    assert result.cost_ms == 0.0


def test_runtime_cycle_result_full():
    result = RuntimeCycleResult(
        signal="s1",
        context_kernel="k1",
        percept="p1",
        uol_graph="g1",
        working_set="ws1",
        retrieval="r1",
        resolution="res1",
        act_plan="plan1",
        patch_candidates=["pc1"],
        validation=["v1"],
        consolidation=["c1"],
        realized_output="hello",
        diagnostics={"key": "val"},
        cost_ms=42.5,
    )
    assert result.signal == "s1"
    assert result.context_kernel == "k1"
    assert result.percept == "p1"
    assert result.uol_graph == "g1"
    assert result.working_set == "ws1"
    assert result.retrieval == "r1"
    assert result.resolution == "res1"
    assert result.act_plan == "plan1"
    assert result.patch_candidates == ["pc1"]
    assert result.validation == ["v1"]
    assert result.consolidation == ["c1"]
    assert result.realized_output == "hello"
    assert result.diagnostics == {"key": "val"}
    assert result.cost_ms == 42.5


def test_semantic_focus_fields():
    focus = SemanticFocus(atom_id="a1", reason="safety", priority=1, confidence=0.95)
    assert focus.atom_id == "a1"
    assert focus.reason == "safety"
    assert focus.priority == 1
    assert focus.confidence == 0.95


def test_semantic_working_set_defaults():
    ws = SemanticWorkingSet()
    assert ws.focus_items == []
    assert ws.selected_paths == []
    assert ws.rejected_paths == []
    assert ws.unresolved_ports == []
    assert ws.evidence_requirements == []
    assert ws.risk_flags == []


def test_semantic_working_set_with_focus():
    items = [
        SemanticFocus("a1", "test", 1, 0.9),
        SemanticFocus("a2", "test", 2, 0.5),
    ]
    ws = SemanticWorkingSet(focus_items=items)
    assert len(ws.focus_items) == 2
    assert ws.focus_items[0].atom_id == "a1"
    assert ws.focus_items[1].atom_id == "a2"
    assert ws.focus_items[1].priority == 2


def test_attention_controller_empty_graph():
    controller = SemanticAttentionController()
    result = controller.attend(UOLGraph(), ContextKernel(id="test"))
    assert isinstance(result, SemanticWorkingSet)
    assert result.focus_items == []
    assert result.selected_paths == []
    assert result.rejected_paths == []
    assert result.unresolved_ports == []
    assert result.evidence_requirements == []
    assert result.risk_flags == []


def test_attention_controller_unresolved_ports():
    controller = SemanticAttentionController()
    graph = UOLGraph()
    graph.atoms["a1"] = UOLAtom(id="a1", kind="entity", key="test")
    graph.port_bindings.append(PortBinding(owner_atom_id="a1", port_key="holder", required=True, status="placeholder", score=0.2))
    result = controller.attend(graph, ContextKernel(id="test"))
    assert len(result.focus_items) >= 1
    assert any("unresolved_required_port" in item.reason for item in result.focus_items)
    assert len(result.unresolved_ports) >= 1


def test_attention_controller_ambiguous_candidates():
    controller = SemanticAttentionController()
    graph = UOLGraph()
    graph.candidate_sets.append(CandidateSet(id="cs1", target_span_id="span1", resolved=False, confidence=0.4))
    result = controller.attend(graph, ContextKernel(id="test"))
    assert any("ambiguous_candidates" in item.reason and item.priority == 4 for item in result.focus_items)


def test_attention_controller_safety_risk():
    controller = SemanticAttentionController()
    graph = UOLGraph()
    graph.atoms["a1"] = UOLAtom(id="a1", kind="permission", key="deny", confidence=0.9)
    result = controller.attend(graph, ContextKernel(id="test"))
    assert any("safety_risk" in item.reason and item.priority == 1 for item in result.focus_items)
    assert "permission:deny" in result.risk_flags


def test_attention_controller_intent_atoms():
    controller = SemanticAttentionController()
    graph = UOLGraph()
    graph.atoms["a1"] = UOLAtom(id="a1", kind="intent", key="ask", confidence=0.8)
    result = controller.attend(graph, ContextKernel(id="test"))
    assert any(item.reason == "active_intent" and item.priority == 7 for item in result.focus_items)


def test_attention_controller_priority_ordering():
    controller = SemanticAttentionController()
    graph = UOLGraph()
    graph.atoms["a1"] = UOLAtom(id="a1", kind="permission", key="deny", confidence=0.9)
    graph.atoms["a2"] = UOLAtom(id="a2", kind="entity", key="test")
    graph.atoms["a3"] = UOLAtom(id="a3", kind="intent", key="ask", confidence=0.8)
    graph.port_bindings.append(PortBinding(owner_atom_id="a2", port_key="holder", required=True, status="placeholder", score=0.2))
    result = controller.attend(graph, ContextKernel(id="test"))
    priorities = [item.priority for item in result.focus_items]
    assert priorities == sorted(priorities)
    assert 1 in priorities
    assert 2 in priorities
    assert 7 in priorities


def test_attention_controller_no_focus_items():
    controller = SemanticAttentionController()
    graph = UOLGraph()
    graph.atoms["a1"] = UOLAtom(id="a1", kind="entity", key="test")
    result = controller.attend(graph, ContextKernel(id="test"))
    assert result.focus_items == []


def test_attention_controller_selected_paths():
    controller = SemanticAttentionController()
    graph = UOLGraph()
    graph.atoms["a1"] = UOLAtom(id="a1", kind="entity", key="test")
    graph.candidate_sets.append(CandidateSet(id="cs1", target_span_id="span1", resolved=True, selected_atom_id="a1"))
    result = controller.attend(graph, ContextKernel(id="test"))
    assert "a1" in result.selected_paths
