"""Training task definitions for CEMM v3.3 Learning Nervous System.

Each pipeline stage is a separate supervised task with:
- Its own train/eval split
- Its own metrics (accuracy for classifiers, F1 for multi-label, BLEU/ROUGE for realization)
- Its own model size (Pi-friendly: logistic regression, small MLP, distilled models)

Training targets:
    meaning_percept_extraction       — input: signal, output: atom set
    surface_binding_learning         — input: surface + context, output: act type mapping
    conversation_act_classification  — input: atoms + frame + discourse, output: act packet
    act_resolution_planning          — input: act packet + frame, output: obligation list
    retrieval_plan_prediction        — input: obligations + frame, output: retrieval mode
    memory_update_planning           — input: candidates + plan, output: batch tasks
    response_planning                — input: obligations + evidence, output: response plan
    error_attribution                — input: reaction + discourse + output, output: error type
    semantic_text_realization        — input: response plan + evidence, output: text

Promotion rule:
    candidate labels → validation (held-out eval set) → promoted registry update
    → deterministic fallback preserved

Generated labels must never become active truth without validation.
The deterministic code path remains as fallback. Promoted models augment, not replace.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskType(str, Enum):
    CLASSIFICATION = "classification"
    MULTI_LABEL = "multi_label"
    SEQUENCE = "sequence"
    STRUCTURED = "structured"


class MetricType(str, Enum):
    ACCURACY = "accuracy"
    F1 = "f1"
    PRECISION = "precision"
    RECALL = "recall"
    BLEU = "bleu"
    ROUGE = "rouge"
    EXACT_MATCH = "exact_match"


@dataclass
class TrainingTaskSpec:
    """Specification for a single supervised training task."""
    name: str
    task_type: TaskType
    input_fields: list[str]
    output_fields: list[str]
    metrics: list[MetricType]
    model_hint: str = "logistic_regression"  # logistic_regression, small_mlp, distilled
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "task_type": self.task_type.value,
            "input_fields": list(self.input_fields),
            "output_fields": list(self.output_fields),
            "metrics": [m.value for m in self.metrics],
            "model_hint": self.model_hint,
            "description": self.description,
        }


# ── Task Specifications ──────────────────────────────────────────

TASK_SPECS: dict[str, TrainingTaskSpec] = {
    "meaning_percept_extraction": TrainingTaskSpec(
        name="meaning_percept_extraction",
        task_type=TaskType.STRUCTURED,
        input_fields=["signal.content", "signal.normalized_forms", "language"],
        output_fields=["referents", "actions", "states", "needs", "affect_markers", "unknown_lexemes"],
        metrics=[MetricType.EXACT_MATCH, MetricType.F1],
        model_hint="small_mlp",
        description="Extract structured atoms from raw signal text.",
    ),
    "surface_binding_learning": TrainingTaskSpec(
        name="surface_binding_learning",
        task_type=TaskType.CLASSIFICATION,
        input_fields=["surface", "context", "language", "discourse_state"],
        output_fields=["maps_to_act_type", "maps_to_frame_key", "confidence"],
        metrics=[MetricType.ACCURACY, MetricType.F1],
        model_hint="logistic_regression",
        description="Learn surface-to-meaning bindings from user interactions and corrections.",
    ),
    "conversation_act_classification": TrainingTaskSpec(
        name="conversation_act_classification",
        task_type=TaskType.MULTI_LABEL,
        input_fields=["uol_atoms", "frame_keys", "discourse_stack", "meaning_percept"],
        output_fields=["act_type", "confidence", "secondary_acts"],
        metrics=[MetricType.F1, MetricType.ACCURACY],
        model_hint="logistic_regression",
        description="Classify conversation acts from atoms, frames, and discourse state.",
    ),
    "act_resolution_planning": TrainingTaskSpec(
        name="act_resolution_planning",
        task_type=TaskType.STRUCTURED,
        input_fields=["conversation_act", "situation_frame", "safety_frame"],
        output_fields=["obligations", "answer_task", "requires_retrieval"],
        metrics=[MetricType.EXACT_MATCH, MetricType.F1],
        model_hint="small_mlp",
        description="Plan obligations and answer tasks from conversation acts.",
    ),
    "retrieval_plan_prediction": TrainingTaskSpec(
        name="retrieval_plan_prediction",
        task_type=TaskType.CLASSIFICATION,
        input_fields=["obligations", "situation_frame", "has_unknown_lexemes"],
        output_fields=["retrieval_mode"],
        metrics=[MetricType.ACCURACY],
        model_hint="logistic_regression",
        description="Predict retrieval mode from obligations and frame.",
    ),
    "memory_update_planning": TrainingTaskSpec(
        name="memory_update_planning",
        task_type=TaskType.STRUCTURED,
        input_fields=["fact_candidates", "act_resolution_plan", "topic_state"],
        output_fields=["memory_tasks", "confidence"],
        metrics=[MetricType.F1, MetricType.EXACT_MATCH],
        model_hint="small_mlp",
        description="Plan memory write tasks from fact candidates and resolution plan.",
    ),
    "response_planning": TrainingTaskSpec(
        name="response_planning",
        task_type=TaskType.STRUCTURED,
        input_fields=["obligations", "evidence", "user_state", "previous_response"],
        output_fields=["intent", "response_mode", "obligation_kind", "move_types"],
        metrics=[MetricType.EXACT_MATCH, MetricType.F1],
        model_hint="small_mlp",
        description="Plan response from obligations, evidence, and user state.",
    ),
    "error_attribution": TrainingTaskSpec(
        name="error_attribution",
        task_type=TaskType.CLASSIFICATION,
        input_fields=["reaction_signal", "discourse_stack", "decision_packet", "realization_metadata"],
        output_fields=["error_type", "correct_act_type", "confidence"],
        metrics=[MetricType.ACCURACY, MetricType.F1],
        model_hint="logistic_regression",
        description="Attribute errors from reaction signals and discourse state.",
    ),
    "semantic_text_realization": TrainingTaskSpec(
        name="semantic_text_realization",
        task_type=TaskType.SEQUENCE,
        input_fields=["response_plan", "evidence", "template_variables"],
        output_fields=["output_text"],
        metrics=[MetricType.BLEU, MetricType.ROUGE],
        model_hint="distilled",
        description="Realize text from response plan and evidence.",
    ),
}


@dataclass
class TrainingLabel:
    """A single training label for any task.

    For positive supervision: `is_negative` = False, `label` = correct output.
    For negative supervision: `is_negative` = True, `label` = wrong output to avoid.
    """
    task_name: str
    input_data: dict[str, Any]
    label: dict[str, Any]
    is_negative: bool = False
    source: str = "deterministic"  # deterministic, correction, user_teaching
    confidence: float = 1.0
    turn_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_name": self.task_name,
            "input_data": dict(self.input_data),
            "label": dict(self.label),
            "is_negative": self.is_negative,
            "source": self.source,
            "confidence": self.confidence,
            "turn_id": self.turn_id,
        }


@dataclass
class CorrectionLabel:
    """Dual-signal correction label from error attribution.

    Provides both:
    - Positive supervision: input → correct_act_type (what to do)
    - Negative supervision: previous_intent → error_type (what NOT to do)
    """
    input_surface: str
    correct_act_type: str
    previous_intent: str
    error_type: str
    confidence: float = 0.8
    turn_id: str = ""

    def to_positive_label(self) -> TrainingLabel:
        """Generate a positive training label for surface_binding_learning."""
        return TrainingLabel(
            task_name="surface_binding_learning",
            input_data={"surface": self.input_surface, "language": "en"},
            label={"maps_to_act_type": self.correct_act_type, "maps_to_frame_key": self.correct_act_type},
            is_negative=False,
            source="correction",
            confidence=self.confidence,
            turn_id=self.turn_id,
        )

    def to_negative_label(self) -> TrainingLabel:
        """Generate a negative training label for conversation_act_classification."""
        return TrainingLabel(
            task_name="conversation_act_classification",
            input_data={"surface": self.input_surface, "language": "en"},
            label={"act_type": self.previous_intent, "error_type": self.error_type},
            is_negative=True,
            source="correction",
            confidence=self.confidence,
            turn_id=self.turn_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_surface": self.input_surface,
            "correct_act_type": self.correct_act_type,
            "previous_intent": self.previous_intent,
            "error_type": self.error_type,
            "confidence": self.confidence,
            "turn_id": self.turn_id,
        }


def get_task_spec(name: str) -> TrainingTaskSpec | None:
    """Get a training task specification by name."""
    return TASK_SPECS.get(name)


def all_task_specs() -> dict[str, TrainingTaskSpec]:
    """Return all training task specifications."""
    return dict(TASK_SPECS)
