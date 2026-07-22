"""Typed CEMM v3.5.1 runtime ABI artifacts.

Stage-5+ semantic artifacts use exact CSIR v2.  No UOL-shaped ``Any`` candidate wrapper
is part of the canonical ABI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .csir.authority import CURRENT_KERNEL_ABI
from .csir.canonical_v351 import exact_fingerprint, semantic_fingerprint
from .csir.model import CSIRCandidate, CSIRGraph, CSIRRef, ExactAuthorityPin
from .runtime_generations import AuthoritySnapshot, ReadGeneration
from .schema.model import semantic_fingerprint as runtime_fingerprint


@dataclass(frozen=True, slots=True)
class RuntimeInput:
    content: str
    language_hints: tuple[str, ...] = ()
    emission_idempotency_key: str | None = None
    discourse_anchors: tuple[Any, ...] = ()
    multimodal_tracks: tuple[Any, ...] = ()
    system_output_anchors: tuple[Any, ...] = ()
    grounding_constraints: tuple[Any, ...] = ()
    speaker_ref: str | None = None
    participant_evidence_refs: tuple[str, ...] = ()
    response_requested: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise TypeError("runtime input content must be text")
        if self.speaker_ref is not None and not self.speaker_ref.strip():
            raise ValueError("speaker_ref must be non-empty")
        if len(self.participant_evidence_refs) != len(set(self.participant_evidence_refs)):
            raise ValueError("participant evidence refs must be unique")


@dataclass(frozen=True, slots=True)
class EvidenceEnvelope:
    evidence_ref: str
    source_ref: str
    kind: str
    payload: Any
    context_ref: str
    permission_ref: str
    confidence: float = 1.0
    evidence_refs: tuple[str, ...] = ()
    lineage_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EvidenceLattice:
    lattice_ref: str
    form_lattice: Any | None
    structured_observations: tuple[Any, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    unresolved_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GroundingCandidateSet:
    candidate_set_ref: str
    preparation: Any
    result: Any
    evidence_refs: tuple[str, ...] = ()
    unresolved_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CSIRCandidateSet:
    candidate_set_ref: str
    candidates: tuple[CSIRCandidate, ...]
    authority_generation: int
    authority_fingerprint: str
    kernel_abi_fingerprint: str
    closure_proof_refs: tuple[str, ...]
    hard_constraint_trace_refs: tuple[str, ...]
    unresolved_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.candidate_set_ref:
            raise ValueError("CSIRCandidateSet requires stable identity")
        if self.authority_generation < 1 or not self.authority_fingerprint:
            raise ValueError("CSIRCandidateSet requires exact AuthorityGeneration")
        if self.kernel_abi_fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise ValueError("CSIRCandidateSet kernel ABI mismatch")
        semantic = [item.semantic_fingerprint for item in self.candidates]
        if len(semantic) != len(set(semantic)):
            raise ValueError("CSIRCandidateSet must contain one candidate per semantic equivalence class")
        for item in self.candidates:
            if (
                item.authority_generation != self.authority_generation
                or item.authority_fingerprint != self.authority_fingerprint
                or item.kernel_abi_fingerprint != self.kernel_abi_fingerprint
            ):
                raise ValueError("CSIR candidate authority/kernel ABI differs from candidate set")
            if semantic_fingerprint(item.graph) != item.semantic_fingerprint:
                raise ValueError("CSIR candidate semantic fingerprint is not kernel-derived")
            if exact_fingerprint(item.graph) != item.exact_fingerprint:
                raise ValueError("CSIR candidate exact fingerprint is not kernel-derived")

    @property
    def semantic_fingerprints(self) -> tuple[str, ...]:
        return tuple(item.semantic_fingerprint for item in self.candidates)


@dataclass(frozen=True, slots=True)
class ActivationGraph:
    graph_ref: str
    payload: Any
    authority_generation: int
    authority_fingerprint: str
    semantic_authority_snapshot_fingerprint: str = ""
    dynamics_parameter_pins: tuple[ExactAuthorityPin, ...] = ()
    kernel_abi_fingerprint: str = CURRENT_KERNEL_ABI.fingerprint
    proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kernel_abi_fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise ValueError("activation graph kernel ABI mismatch")
        if len({pin.key for pin in self.dynamics_parameter_pins}) != len(self.dynamics_parameter_pins):
            raise ValueError("activation graph dynamics pins must be unique")


@dataclass(frozen=True, slots=True)
class ActivationTrace:
    trace_ref: str
    iterations: int
    convergence_delta: float
    proof_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ConvergenceAssessment:
    converged: bool
    semantic_normal_form_stable: bool
    activation_delta: float
    epsilon: float
    reason_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SemanticAttractor:
    attractor_ref: str
    graph: CSIRGraph
    semantic_fingerprint: str
    support: float
    energy: float | None = None
    derivation_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if semantic_fingerprint(self.graph) != self.semantic_fingerprint:
            raise ValueError("semantic attractor fingerprint must equal canonical CSIR normal form")


@dataclass(frozen=True, slots=True)
class SemanticAttractorSet:
    attractor_set_ref: str
    attractors: tuple[SemanticAttractor, ...]
    partial_meaning: CSIRGraph | None
    open_variables: tuple[CSIRRef, ...]
    convergence: ConvergenceAssessment
    authority_generation: int
    authority_fingerprint: str
    semantic_authority_snapshot_fingerprint: str = ""
    dynamics_parameter_pins: tuple[ExactAuthorityPin, ...] = ()
    kernel_abi_fingerprint: str = CURRENT_KERNEL_ABI.fingerprint
    proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kernel_abi_fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise ValueError("semantic attractor set kernel ABI mismatch")
        if len({pin.key for pin in self.dynamics_parameter_pins}) != len(self.dynamics_parameter_pins):
            raise ValueError("semantic attractor dynamics pins must be unique")
        fps = tuple(item.semantic_fingerprint for item in self.attractors)
        if len(fps) != len(set(fps)):
            raise ValueError("attractor set contains duplicate semantic equivalence classes")

    @property
    def semantic_fingerprints(self) -> tuple[str, ...]:
        return tuple(item.semantic_fingerprint for item in self.attractors)


@dataclass(frozen=True, slots=True)
class CognitiveCyclePins:
    authority_snapshot: AuthoritySnapshot
    read_generation: ReadGeneration
    kernel_abi_fingerprint: str
    context_ref: str
    permission_ref: str
    channel_ref: str
    target_language: str | None
    cycle_time: str
    semantic_authority_snapshot_fingerprint: str = ""
    dynamics_parameter_pins: tuple[ExactAuthorityPin, ...] = ()
    runtime_attestation_ref: str = ""

    def __post_init__(self) -> None:
        if self.kernel_abi_fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise ValueError("cycle pins do not identify the active Kernel Semantic ABI")


@dataclass(frozen=True, slots=True)
class RealizationPlanArtifact:
    plan_ref: str
    selected_candidate_ref: str
    novelty: bool = False
    risk_refs: tuple[str, ...] = ()
    audit_required: bool = False
    release_competence: bool = False
    unreviewed_transform: bool = False
    channel_metadata: Any | None = None


@dataclass(frozen=True, slots=True)
class SurfaceCandidateArtifact:
    candidate_ref: str
    surface: str
    language_tag: str
    proof_ref: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.candidate_ref or not self.surface or not self.language_tag or not self.proof_ref:
            raise ValueError("surface candidate requires identity, surface, language and proof_ref")


@dataclass(frozen=True, slots=True)
class EmissionObservationArtifact:
    emission_ref: str
    surface_candidate_ref: str
    output_text: str
    evidence_refs: tuple[str, ...]
    channel_ref: str


@dataclass(frozen=True, slots=True)
class RuntimeResult:
    cycle_ref: str
    context_ref: str
    output_text: str | None
    target_language: str | None
    stage_trace: tuple[Mapping[str, Any], ...]
    frontier_refs: tuple[str, ...]
    errors: tuple[str, ...]
    artifacts: Mapping[str, Any]

    @property
    def emitted(self) -> bool:
        return bool(self.output_text)

    @property
    def cycle_id(self) -> str:
        return self.cycle_ref

    @property
    def context_id(self) -> str:
        return self.context_ref

    @property
    def completion_status(self) -> str:
        return str(self.artifacts.get("cycle_completion_status", "PARTIAL"))

    @property
    def trace(self):
        @dataclass(frozen=True, slots=True)
        class _Trace:
            stages: tuple[str, ...]
            details: tuple[Mapping[str, Any], ...]
            errors: tuple[str, ...]
        return _Trace(
            tuple(str(x.get("stage_name", "")) for x in self.stage_trace),
            self.stage_trace,
            self.errors,
        )


def artifact_ref(prefix: str, *parts: Any) -> str:
    return f"{prefix}:" + runtime_fingerprint(prefix, parts, 24)


__all__ = [
    "ActivationGraph", "ActivationTrace", "CSIRCandidateSet", "CognitiveCyclePins",
    "ConvergenceAssessment", "EvidenceEnvelope", "EvidenceLattice",
    "EmissionObservationArtifact", "GroundingCandidateSet", "RealizationPlanArtifact",
    "RuntimeInput", "RuntimeResult", "SemanticAttractor", "SemanticAttractorSet",
    "SurfaceCandidateArtifact", "artifact_ref",
]
