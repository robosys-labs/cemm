from __future__ import annotations
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.kernel.training_export import serialize_turn
from cemm.types.context_kernel import ContextKernel
from cemm.types.permission import Permission
from cemm.types.semantic_event_graph import SemanticEventGraph
from cemm.types.semantic_answer_graph import SemanticAnswerGraph
from cemm.types.packets import GroundedGraph, MemoryPacket, InferencePacket, DecisionPacket, ActionPlan
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.trace import Trace
from cemm.cemm_trainer import validate_training_record


_REQUIRED_TASK_TYPES = {
    "semantic_graph_extraction", "semantic_graph_denoising", "semantic_latent_target",
    "claim_extraction", "entity_resolution", "uol_mapping", "context_inference",
    "pragmatic_interpretation", "semantic_answer_composition", "operator_selection",
    "temporal_relation_derivation", "frame_classification", "semantic_text_realization",
    "text_to_answer", "self_state_update", "memory_retrieval_ranking",
    "next_event_prediction", "causal_effect_prediction", "causal_rule_extraction",
    "contradiction_detection", "verifier_calibration", "claim_canonicalization",
    "structural_induction", "ranking_judgment", "synthesis_verification",
}


def _make_signal() -> Signal:
    return Signal(
        id="s1",
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content="hello",
        observed_at=time.time(),
        context_id="ctx",
        salience=0.5,
        trust=0.8,
        permission=Permission.public(),
    )


def test_training_export_decomposes_all_prompts_task_types():
    kernel = ContextKernel(id="ctx", permission=Permission.public())
    seg = SemanticEventGraph(
        id="seg1", source_signal_ids=["s1"], context_id="ctx", entity_refs=[],
        processes=[], states=[], claim_refs=[], model_refs=[], action_refs=[],
        temporal_edges=[], causal_edges=[], permission_scope="public", confidence=0.7,
    )
    sag = SemanticAnswerGraph(
        id="sag1", intent="answer", source_signal_ids=["s1"], context_id="ctx",
        selected_claim_ids=[], selected_model_ids=[], entity_refs=[], causal_edges=[],
        temporal_edges=[],
    )
    grounded = GroundedGraph(id="gg1", semantic_event_graph_id="seg1", missing_slots=[])
    memory = MemoryPacket(id="mp1", selected_signal_ids=["s1"], selected_claim_ids=[], selected_model_ids=[])
    inference = InferencePacket(
        id="ip1", predictions=[], implications=[], contradictions=[], missing_slots=[],
        state_deltas={}, inference_graph_input_signal_ids=["s1"],
    )
    decision = DecisionPacket(
        action_kind="answer",
        action_plan=ActionPlan(action_kind="answer", execution_allowed=True, confidence=0.7, risk=0.0),
        confidence=0.7, reason="test",
    )
    trace = Trace(context_id="ctx", input_signal_ids=["s1"], semantic_event_graph_id="seg1", semantic_answer_graph_id="sag1")
    input_signal = _make_signal()

    records = serialize_turn(
        input_text="hello", output_text="hi", kernel=kernel, input_signal=input_signal,
        trace=trace, semantic_event_graph=seg, semantic_answer_graph=sag,
        grounded_graph=grounded, memory_packet=memory, inference_packet=inference,
        decision_packet=decision,
    )
    assert isinstance(records, list)
    task_types = {r["task_type"] for r in records}
    missing = _REQUIRED_TASK_TYPES - task_types
    assert not missing, f"Missing task types: {missing}"

    for record in records:
        validate_training_record(record["task_type"], record["payload"])
