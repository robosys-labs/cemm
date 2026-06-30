from __future__ import annotations

import uuid
import json
import time
from dataclasses import asdict
from typing import Any

from ..types.context_kernel import ContextKernel
from ..types.semantic_event_graph import SemanticEventGraph
from ..types.semantic_answer_graph import SemanticAnswerGraph
from ..types.packets import (
    GroundedGraph, MemoryPacket, InferencePacket, DecisionPacket,
    ActionPlan, packet_to_dict,
)
from ..types.trace import Trace
from ..types.signal import Signal


def serialize_turn(
    input_text: str,
    output_text: str,
    kernel: ContextKernel,
    input_signal: Signal,
    trace: Trace | None = None,
    semantic_event_graph: SemanticEventGraph | None = None,
    semantic_answer_graph: SemanticAnswerGraph | None = None,
    grounded_graph: GroundedGraph | None = None,
    memory_packet: MemoryPacket | None = None,
    inference_packet: InferencePacket | None = None,
    decision_packet: DecisionPacket | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "context_kernel": asdict(kernel),
        "input_text": input_text,
        "output_text": output_text,
        "input_signal_id": input_signal.id,
    }
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
    if trace:
        payload["trace"] = asdict(trace)

    return {
        "id": uuid.uuid4().hex[:16],
        "task_type": "full_turn_export",
        "permission_scope": "local_training",
        "payload": payload,
        "created_at": int(time.time()),
    }


def write_turn_to_jsonl(
    path: str,
    turn_data: dict[str, Any],
) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(turn_data, default=str) + "\n")
