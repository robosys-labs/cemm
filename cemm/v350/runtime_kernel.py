"""Cross-stage runtime contracts for the hardened CEMM v3.5 core loop.

These classes are mechanism-level control artifacts, not semantic ontology.
They exist to preserve immutable pass lineage, typed observations/frontiers,
participant identity, and bounded semantic re-entry without smuggling domain
meaning into the orchestrator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ObservationKind(StrEnum):
    TEXT = "text"
    AUDIO = "audio"
    VISION = "vision"
    SENSOR = "sensor"
    TOOL_RESULT = "tool_result"
    OPERATION_RESULT = "operation_result"
    TIMER = "timer"
    SYSTEM_EVENT = "system_event"
    TEACHING = "teaching"


class FrontierClass(StrEnum):
    SEMANTIC_LEARNING = "semantic_learning"
    GROUNDING_AMBIGUITY = "grounding_ambiguity"
    REFERENCE_AMBIGUITY = "reference_ambiguity"
    RUNTIME_CAPABILITY = "runtime_capability"
    POLICY_BLOCK = "policy_block"
    PERMISSION_BLOCK = "permission_block"
    BUDGET_INCOMPLETE = "budget_incomplete"
    TEMPORAL_REPLAY = "temporal_replay"
    OPERATION_OUTCOME_UNKNOWN = "operation_outcome_unknown"
    REALIZATION_GAP = "realization_gap"


@dataclass(frozen=True, slots=True)
class ObservationEnvelope:
    observation_ref: str
    kind: ObservationKind
    source_ref: str
    payload_ref: str
    context_ref: str
    permission_ref: str
    observed_at: str | None = None
    confidence: float = 1.0
    evidence_refs: tuple[str, ...] = ()
    lineage_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.observation_ref, "observation_ref"),
            (self.source_ref, "observation source_ref"),
            (self.payload_ref, "observation payload_ref"),
            (self.context_ref, "observation context_ref"),
            (self.permission_ref, "observation permission_ref"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label} must be non-empty")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("observation confidence must be finite in [0,1]")
        for values, label in (
            (self.evidence_refs, "observation evidence"),
            (self.lineage_refs, "observation lineage"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{label} refs must be unique")


@dataclass(frozen=True, slots=True)
class ObservationBatch:
    batch_ref: str
    observations: tuple[ObservationEnvelope, ...]
    context_ref: str
    permission_ref: str
    parent_pass_ref: str | None = None
    reason_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.batch_ref.strip() or not self.context_ref.strip() or not self.permission_ref.strip():
            raise ValueError("observation batch identity/context/permission must be non-empty")
        if not self.observations:
            raise ValueError("observation batch requires at least one observation")
        refs = tuple(item.observation_ref for item in self.observations)
        if len(refs) != len(set(refs)):
            raise ValueError("observation refs must be unique inside one batch")
        if any(item.context_ref != self.context_ref for item in self.observations):
            raise ValueError("one observation batch cannot silently mix semantic contexts")
        if any(item.permission_ref != self.permission_ref for item in self.observations):
            raise ValueError("one observation batch cannot silently widen/mix permission scopes")
        if len(self.reason_refs) != len(set(self.reason_refs)):
            raise ValueError("observation batch reason refs must be unique")




@dataclass(frozen=True, slots=True)
class StructuredObservationAnalysis:
    analyzer_ref: str
    analyzer_revision: str
    observation_refs: tuple[str, ...]
    graph: Any
    proof_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.analyzer_ref.strip() or not self.analyzer_revision.strip():
            raise ValueError("structured observation analyzer identity is required")
        if not self.observation_refs:
            raise ValueError("structured observation analysis requires observations")
        if not self.proof_refs:
            raise ValueError("structured observation analysis requires proof lineage")
        if len(self.observation_refs) != len(set(self.observation_refs)):
            raise ValueError("structured observation refs must be unique")
        if len(self.proof_refs) != len(set(self.proof_refs)):
            raise ValueError("structured observation proof refs must be unique")
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise ValueError("structured observation evidence refs must be unique")

@dataclass(frozen=True, slots=True)
class RuntimeFrontier:
    frontier_ref: str
    frontier_class: FrontierClass
    missing_contract: str
    target_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    context_ref: str
    permission_ref: str
    candidate_refs: tuple[str, ...] = ()
    requested_use: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.frontier_ref, "runtime frontier_ref"),
            (self.missing_contract, "runtime missing_contract"),
            (self.context_ref, "runtime frontier context"),
            (self.permission_ref, "runtime frontier permission"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label} must be non-empty")
        for values, label in (
            (self.target_refs, "runtime frontier targets"),
            (self.evidence_refs, "runtime frontier evidence"),
            (self.candidate_refs, "runtime frontier candidates"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{label} must be unique")


@dataclass(frozen=True, slots=True)
class ParticipantFrame:
    frame_ref: str
    system_ref: str
    input_speaker_ref: str
    input_addressee_refs: tuple[str, ...]
    response_audience_refs: tuple[str, ...]
    context_ref: str
    permission_ref: str
    identity_evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.frame_ref, "participant frame_ref"),
            (self.system_ref, "participant system_ref"),
            (self.input_speaker_ref, "participant input_speaker_ref"),
            (self.context_ref, "participant context_ref"),
            (self.permission_ref, "participant permission_ref"),
        ):
            if not value.strip():
                raise ValueError(f"{label} must be non-empty")
        if not self.input_addressee_refs:
            raise ValueError("participant frame requires input addressee")
        if not self.response_audience_refs:
            raise ValueError("participant frame requires response audience")
        for values, label in (
            (self.input_addressee_refs, "participant input addressees"),
            (self.response_audience_refs, "participant response audiences"),
            (self.identity_evidence_refs, "participant identity evidence"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{label} refs must be unique")


@dataclass(frozen=True, slots=True)
class RuntimeBudgetSet:
    inference_steps: int = 256
    transition_plans: int = 128
    learning_frontiers: int = 128
    realization_candidates: int = 16
    semantic_reentries: int = 2
    external_operations: int = 8

    def __post_init__(self) -> None:
        values = (
            self.inference_steps,
            self.transition_plans,
            self.learning_frontiers,
            self.realization_candidates,
            self.semantic_reentries,
            self.external_operations,
        )
        if any(value < 0 for value in values):
            raise ValueError("runtime budgets cannot be negative")


@dataclass(frozen=True, slots=True)
class SemanticReentryRequest:
    request_ref: str
    observation_batch: ObservationBatch
    reason_refs: tuple[str, ...]
    carry_artifact_keys: tuple[str, ...]
    max_reentries: int

    def __post_init__(self) -> None:
        if not self.request_ref.strip():
            raise ValueError("semantic re-entry request_ref must be non-empty")
        if self.max_reentries < 1:
            raise ValueError("semantic re-entry max_reentries must be positive")
        if not self.reason_refs:
            raise ValueError("semantic re-entry requires explicit reasons")
        if len(self.reason_refs) != len(set(self.reason_refs)):
            raise ValueError("semantic re-entry reasons must be unique")
        if len(self.carry_artifact_keys) != len(set(self.carry_artifact_keys)):
            raise ValueError("semantic re-entry carry keys must be unique")
