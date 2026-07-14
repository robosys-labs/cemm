from __future__ import annotations

import uuid
import json
import time
from dataclasses import asdict
from typing import Any

from ...types.context_kernel import ContextKernel
from ...types.context_inference import ContextInference
from ...types.conversation_act import ConversationAct, ConversationActPacket
from typing import Any
from ...types.semantic_answer_graph import SemanticAnswerGraph
from ...types.packets import (
    GroundedGraph, MemoryPacket, InferencePacket, DecisionPacket,
    ActionPlan, packet_to_dict,
)
from ...types.trace import Trace
from ...types.signal import Signal, ObservationSemantics
from ...types.meaning_percept import MeaningPerceptPacket, SituationFrame, SafetyFrame, RetrievalPlan


def _make_record(task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": uuid.uuid4().hex[:16],
        "task_type": task_type,
        "permission_scope": "local_training",
        "payload": payload,
        "created_at": int(time.time()),
    }


def _task_payload(
    base: dict[str, Any],
    task_type: str,
    *,
    semantic_event_graph: Any | None = None,
    semantic_answer_graph: SemanticAnswerGraph | None = None,
    grounded_graph: GroundedGraph | None = None,
    memory_packet: MemoryPacket | None = None,
    inference_packet: InferencePacket | None = None,
    decision_packet: DecisionPacket | None = None,
    observation_semantics: ObservationSemantics | None = None,
    context_inference: ContextInference | None = None,
    kernel: ContextKernel | None = None,
    trace: Trace | None = None,
    meaning_percept: MeaningPerceptPacket | None = None,
    situation_frame: SituationFrame | None = None,
    safety_frame: SafetyFrame | None = None,
    retrieval_plan: RetrievalPlan | None = None,
) -> dict[str, Any]:
    payload = dict(base)
    if semantic_event_graph:
        payload["semantic_event_graph"] = packet_to_dict(semantic_event_graph)
    if semantic_answer_graph:
        payload["semantic_answer_graph"] = packet_to_dict(semantic_answer_graph)
    if grounded_graph:
        payload["grounded_graph"] = packet_to_dict(grounded_graph)
    if memory_packet:
        payload["memory_packet"] = packet_to_dict(memory_packet)
    if inference_packet:
        payload["inference_packet"] = packet_to_dict(inference_packet)
    if decision_packet:
        payload["decision_packet"] = packet_to_dict(decision_packet)
        if decision_packet.action_plan:
            payload["action_plan"] = asdict(decision_packet.action_plan)
    if observation_semantics:
        payload["observation_semantics"] = asdict(observation_semantics)
    if context_inference:
        payload["context_inference"] = asdict(context_inference)
    if meaning_percept:
        payload["meaning_percept"] = asdict(meaning_percept)
    if situation_frame:
        payload["situation_frame"] = asdict(situation_frame)
    if safety_frame:
        payload["safety_frame"] = asdict(safety_frame)
    if retrieval_plan:
        payload["retrieval_plan"] = asdict(retrieval_plan)
    if kernel and kernel.self_view:
        payload["self_state"] = asdict(kernel.self_view)
    if trace:
        payload["trace"] = asdict(trace)
        payload["selected_evidence"] = {
            "selected_claim_ids": trace.selected_claim_ids or [],
            "selected_model_ids": trace.selected_model_ids or [],
        }
        payload["output_text"] = payload.get("output_text", "")
        payload["realization_metadata"] = {
            "strategy": trace.realization_strategy,
            "verified": trace.realization_verified,
            "details": trace.realization_details,
        }
        payload["verification_metadata"] = {
            "synthesis_strategy_model_id": trace.synthesis_strategy_model_id,
            "synthesis_verified": trace.synthesis_verified,
            "synthesis_verification_type": trace.synthesis_verification_type,
            "verifier_model_id": trace.verifier_model_id,
            "details": trace.verification_details,
        }
    return payload


def serialize_turn(
    input_text: str,
    output_text: str,
    kernel: ContextKernel,
    input_signal: Signal,
    trace: Trace | None = None,
    semantic_event_graph: Any | None = None,
    semantic_answer_graph: SemanticAnswerGraph | None = None,
    grounded_graph: GroundedGraph | None = None,
    memory_packet: MemoryPacket | None = None,
    inference_packet: InferencePacket | None = None,
    decision_packet: DecisionPacket | None = None,
    observation_semantics: ObservationSemantics | None = None,
    context_inference: ContextInference | None = None,
    conversation_act: ConversationActPacket | ConversationAct | None = None,
    meaning_percept: MeaningPerceptPacket | None = None,
    situation_frame: SituationFrame | None = None,
    safety_frame: SafetyFrame | None = None,
    retrieval_plan: RetrievalPlan | None = None,
    act_resolution_plan: Any = None,
    error_attribution: Any = None,
    correction_label: dict[str, Any] | None = None,
    discourse_stack: Any = None,
    semantic_model_store_deltas: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    base_payload: dict[str, Any] = {
        "context_kernel": asdict(kernel),
        "input_text": input_text,
        "output_text": output_text,
        "input_signal_id": input_signal.id,
    }
    if trace:
        base_payload["trace"] = asdict(trace)
        if trace.selected_claim_ids or trace.selected_model_ids:
            base_payload["selected_evidence"] = {
                "selected_claim_ids": trace.selected_claim_ids,
                "selected_model_ids": trace.selected_model_ids,
            }
        base_payload["realization_metadata"] = {
            "strategy": trace.realization_strategy,
            "verified": trace.realization_verified,
            "details": trace.realization_details,
        }
        base_payload["verification_metadata"] = {
            "synthesis_strategy_model_id": trace.synthesis_strategy_model_id,
            "synthesis_verified": trace.synthesis_verified,
            "synthesis_verification_type": trace.synthesis_verification_type,
            "verifier_model_id": trace.verifier_model_id,
            "details": trace.verification_details,
        }
    if semantic_event_graph:
        base_payload["semantic_event_graph"] = packet_to_dict(semantic_event_graph)
    if semantic_answer_graph:
        base_payload["semantic_answer_graph"] = packet_to_dict(semantic_answer_graph)
    if grounded_graph:
        base_payload["grounded_graph"] = packet_to_dict(grounded_graph)
    if memory_packet:
        base_payload["memory_packet"] = packet_to_dict(memory_packet)
    if inference_packet:
        base_payload["inference_packet"] = packet_to_dict(inference_packet)
    if decision_packet:
        base_payload["decision_packet"] = packet_to_dict(decision_packet)
        if decision_packet.action_plan:
            base_payload["action_plan"] = asdict(decision_packet.action_plan)
    if observation_semantics:
        base_payload["observation_semantics"] = asdict(observation_semantics)
    if context_inference:
        base_payload["context_inference"] = asdict(context_inference)
    if conversation_act:
        base_payload["conversation_act"] = asdict(conversation_act)
    if meaning_percept:
        base_payload["meaning_percept"] = asdict(meaning_percept)
    if situation_frame:
        base_payload["situation_frame"] = asdict(situation_frame)
    if safety_frame:
        base_payload["safety_frame"] = asdict(safety_frame)
    if retrieval_plan:
        base_payload["retrieval_plan"] = asdict(retrieval_plan)
    if act_resolution_plan:
        base_payload["act_resolution_plan"] = asdict(act_resolution_plan)
    if error_attribution:
        base_payload["error_attribution"] = asdict(error_attribution)
    if correction_label:
        base_payload["correction_label"] = correction_label
    if discourse_stack:
        entries = discourse_stack.entries[-3:] if hasattr(discourse_stack, "entries") else []
        base_payload["discourse_stack"] = [asdict(e) for e in entries]
    if semantic_model_store_deltas:
        base_payload["semantic_model_store_deltas"] = semantic_model_store_deltas

    records: list[dict[str, Any]] = []
    records.append(_make_record("full_turn_export", dict(base_payload)))

    # v3.3 Phase 10: Surface binding learning record
    if semantic_model_store_deltas:
        records.append(_make_record(
            "surface_binding_learning",
            _task_payload(base_payload, "surface_binding_learning", semantic_model_store_deltas=semantic_model_store_deltas, kernel=kernel, trace=trace),
        ))

    # v3.3 Phase 9: Error attribution and correction label records
    if error_attribution:
        records.append(_make_record(
            "error_attribution",
            _task_payload(base_payload, "error_attribution", error_attribution=error_attribution, kernel=kernel, trace=trace),
        ))
    if correction_label:
        records.append(_make_record(
            "correction_label",
            _task_payload(base_payload, "correction_label", correction_label=correction_label, kernel=kernel, trace=trace),
        ))
    if act_resolution_plan:
        records.append(_make_record(
            "act_resolution_planning",
            _task_payload(base_payload, "act_resolution_planning", act_resolution_plan=act_resolution_plan, decision_packet=decision_packet, kernel=kernel, trace=trace),
        ))

    # v3.1 operational meaning-spine tasks. These make the new foundational
    # packets trainable instead of invisible runtime features.
    if meaning_percept:
        records.append(_make_record(
            "meaning_percept_extraction",
            _task_payload(base_payload, "meaning_percept_extraction", meaning_percept=meaning_percept, kernel=kernel, trace=trace),
        ))
    if situation_frame:
        records.append(_make_record(
            "situation_frame_construction",
            _task_payload(base_payload, "situation_frame_construction", situation_frame=situation_frame, meaning_percept=meaning_percept, kernel=kernel, trace=trace),
        ))
        records.append(_make_record(
            "role_binding",
            _task_payload(base_payload, "role_binding", situation_frame=situation_frame, meaning_percept=meaning_percept, kernel=kernel, trace=trace),
        ))
        records.append(_make_record(
            "outcome_valence_prediction",
            _task_payload(base_payload, "outcome_valence_prediction", situation_frame=situation_frame, kernel=kernel, trace=trace),
        ))
    if safety_frame:
        records.append(_make_record(
            "safety_frame_detection",
            _task_payload(base_payload, "safety_frame_detection", safety_frame=safety_frame, situation_frame=situation_frame, kernel=kernel, trace=trace),
        ))
    if retrieval_plan:
        records.append(_make_record(
            "retrieval_plan_prediction",
            _task_payload(base_payload, "retrieval_plan_prediction", retrieval_plan=retrieval_plan, situation_frame=situation_frame, kernel=kernel, trace=trace),
        ))
    if conversation_act:
        records.append(_make_record(
            "reply_obligation_prediction",
            _task_payload(base_payload, "reply_obligation_prediction", situation_frame=situation_frame, kernel=kernel, trace=trace),
        ))
        records.append(_make_record(
            "act_resolution_planning",
            _task_payload(base_payload, "act_resolution_planning", situation_frame=situation_frame, decision_packet=decision_packet, kernel=kernel, trace=trace),
        ))

    if not semantic_event_graph:
        return records

    seg_dict = packet_to_dict(semantic_event_graph)

    # SEG-based task types
    records.append(_make_record(
        "semantic_graph_extraction",
        _task_payload(base_payload, "semantic_graph_extraction", semantic_event_graph=semantic_event_graph, kernel=kernel, trace=trace),
    ))
    records.append(_make_record(
        "semantic_graph_denoising",
        _task_payload(base_payload, "semantic_graph_denoising", semantic_event_graph=semantic_event_graph, kernel=kernel, trace=trace),
    ))
    records.append(_make_record(
        "semantic_latent_target",
        _task_payload(base_payload, "semantic_latent_target", semantic_event_graph=semantic_event_graph, kernel=kernel, trace=trace),
    ))
    records.append(_make_record(
        "claim_extraction",
        _task_payload(base_payload, "claim_extraction", semantic_event_graph=semantic_event_graph, kernel=kernel, trace=trace),
    ))
    records.append(_make_record(
        "entity_resolution",
        _task_payload(base_payload, "entity_resolution", semantic_event_graph=semantic_event_graph, kernel=kernel, trace=trace),
    ))
    records.append(_make_record(
        "uol_mapping",
        _task_payload(base_payload, "uol_mapping", semantic_event_graph=semantic_event_graph, kernel=kernel, trace=trace),
    ))
    records.append(_make_record(
        "context_inference",
        _task_payload(base_payload, "context_inference", context_inference=context_inference, semantic_event_graph=semantic_event_graph, kernel=kernel, trace=trace),
    ))
    records.append(_make_record(
        "pragmatic_interpretation",
        _task_payload(base_payload, "pragmatic_interpretation", observation_semantics=observation_semantics, semantic_event_graph=semantic_event_graph, kernel=kernel, trace=trace),
    ))
    records.append(_make_record(
        "semantic_answer_composition",
        _task_payload(base_payload, "semantic_answer_composition", semantic_event_graph=semantic_event_graph, semantic_answer_graph=semantic_answer_graph, kernel=kernel, trace=trace),
    ))
    records.append(_make_record(
        "operator_selection",
        _task_payload(base_payload, "operator_selection", semantic_event_graph=semantic_event_graph, semantic_answer_graph=semantic_answer_graph, decision_packet=decision_packet, kernel=kernel, trace=trace),
    ))
    records.append(_make_record(
        "temporal_relation_derivation",
        _task_payload(base_payload, "temporal_relation_derivation", semantic_event_graph=semantic_event_graph, kernel=kernel, trace=trace),
    ))
    records.append(_make_record(
        "frame_classification",
        _task_payload(base_payload, "frame_classification", semantic_event_graph=semantic_event_graph, kernel=kernel, trace=trace),
    ))
    records.append(_make_record(
        "claim_canonicalization",
        _task_payload(base_payload, "claim_canonicalization", semantic_event_graph=semantic_event_graph, kernel=kernel, trace=trace),
    ))
    records.append(_make_record(
        "structural_induction",
        _task_payload(base_payload, "structural_induction", semantic_event_graph=semantic_event_graph, kernel=kernel, trace=trace),
    ))

    # SAG-based task types
    if semantic_answer_graph:
        sag_dict = packet_to_dict(semantic_answer_graph)
        records.append(_make_record(
            "semantic_text_realization",
            _task_payload(base_payload, "semantic_text_realization", semantic_answer_graph=semantic_answer_graph, kernel=kernel, trace=trace),
        ))
        records.append(_make_record(
            "text_to_answer",
            _task_payload(base_payload, "text_to_answer", semantic_answer_graph=semantic_answer_graph, kernel=kernel, trace=trace),
        ))
        records.append(_make_record(
            "contradiction_detection",
            _task_payload(base_payload, "contradiction_detection", semantic_answer_graph=semantic_answer_graph, kernel=kernel, trace=trace),
        ))

    # Memory-based task types
    if memory_packet:
        records.append(_make_record(
            "memory_retrieval_ranking",
            _task_payload(base_payload, "memory_retrieval_ranking", memory_packet=memory_packet, kernel=kernel, trace=trace),
        ))
        records.append(_make_record(
            "ranking_judgment",
            _task_payload(base_payload, "ranking_judgment", memory_packet=memory_packet, kernel=kernel, trace=trace),
        ))

    # Inference-based task types
    if inference_packet:
        records.append(_make_record(
            "next_event_prediction",
            _task_payload(base_payload, "next_event_prediction", inference_packet=inference_packet, semantic_event_graph=semantic_event_graph, kernel=kernel, trace=trace),
        ))
        records.append(_make_record(
            "causal_effect_prediction",
            _task_payload(base_payload, "causal_effect_prediction", inference_packet=inference_packet, semantic_event_graph=semantic_event_graph, kernel=kernel, trace=trace),
        ))
        records.append(_make_record(
            "causal_rule_extraction",
            _task_payload(base_payload, "causal_rule_extraction", inference_packet=inference_packet, semantic_event_graph=semantic_event_graph, kernel=kernel, trace=trace),
        ))

    # Verifier / synthesis task types
    if trace:
        records.append(_make_record(
            "verifier_calibration",
            _task_payload(base_payload, "verifier_calibration", kernel=kernel, trace=trace),
        ))
        records.append(_make_record(
            "synthesis_verification",
            _task_payload(base_payload, "synthesis_verification", kernel=kernel, trace=trace),
        ))

    # Self task type
    if kernel and kernel.self_view:
        records.append(_make_record(
            "self_state_update",
            _task_payload(base_payload, "self_state_update", kernel=kernel, trace=trace),
        ))

    return records


def write_turn_to_jsonl(
    path: str,
    turn_data: dict[str, Any],
) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(turn_data, default=str) + "\n")
