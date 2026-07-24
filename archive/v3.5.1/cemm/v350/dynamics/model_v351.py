"""Phase-13 typed recurrent semantic activation contracts for CEMM v3.5.1.

The exact CSIR graph remains semantic identity.  These structures are cycle-local dynamic
state: sparse activations, typed messages, hard masks, competition groups, and convergence
trace.  They never create semantic identity from scores or embeddings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Mapping

from ..csir.model import CSIRGraph, ExactAuthorityPin
from ..schema.model import semantic_fingerprint


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class MessageFamily(StrEnum):
    LEXICAL = "lexical"
    CONSTRUCTION = "construction"
    PORT_ROLE = "port_role"
    TYPE = "type"
    IDENTITY = "identity"
    SCOPE = "scope"
    TIME_ASPECT = "time_aspect"
    CONTEXT = "context"
    STATE = "state"
    CAUSAL_EXPECTATION = "causal_expectation"
    DISCOURSE = "discourse"
    MULTIMODAL = "multimodal"


REQUIRED_MESSAGE_FAMILIES = tuple(MessageFamily)


class ActivationNodeKind(StrEnum):
    SEMANTIC_CLASS = "semantic_class"
    TERM = "term"
    VARIABLE = "variable"
    APPLICATION = "application"
    BINDING = "binding"
    QUALIFIER = "qualifier"
    SCOPE = "scope"
    COORDINATION = "coordination"
    EVIDENCE = "evidence"
    REFERENT = "referent"
    STATE_PROJECTION = "state_projection"
    DISCOURSE_ANCHOR = "discourse_anchor"
    MULTIMODAL_TRACK = "multimodal_track"


class EdgePolarity(StrEnum):
    EXCITATORY = "excitatory"
    INHIBITORY = "inhibitory"


class HardMaskReason(StrEnum):
    AUTHORITY_MISMATCH = "authority_mismatch"
    KERNEL_ABI_MISMATCH = "kernel_abi_mismatch"
    HARD_CONSTRAINT = "hard_constraint"
    TYPE_INCOMPATIBLE = "type_incompatible"
    CONTEXT_INCOMPATIBLE = "context_incompatible"
    PERMISSION_INCOMPATIBLE = "permission_incompatible"
    DANGLING_STRUCTURE = "dangling_structure"
    NUMERIC_INVALID = "numeric_invalid"


class ConvergenceKind(StrEnum):
    CONVERGED = "converged"
    BUDGET_EXHAUSTED_PARTIAL = "budget_exhausted_partial"
    NO_ADMISSIBLE_CANDIDATE = "no_admissible_candidate"
    OSCILLATION_DETECTED = "oscillation_detected"
    NUMERIC_INVALID = "numeric_invalid"
    AUTHORITY_INVALIDATED = "authority_invalidated"


@dataclass(frozen=True, slots=True)
class SemanticActivationNode:
    node_ref: str
    node_kind: ActivationNodeKind
    semantic_class_ref: str
    source_ref: str
    initial_activation: float
    current_activation: float
    evidence_refs: tuple[str, ...] = ()
    lineage_refs: tuple[str, ...] = ()
    exact_authority_pins: tuple[ExactAuthorityPin, ...] = ()
    feature_refs: tuple[str, ...] = ()
    unresolved_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.node_ref, "node_ref"),
            (self.semantic_class_ref, "semantic_class_ref"),
            (self.source_ref, "source_ref"),
        ):
            if not value.strip():
                raise ValueError(f"activation {label} must be non-empty")
        for value in (self.initial_activation, self.current_activation):
            if not isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError("activation values must be finite in [0,1]")
        _unique(self.evidence_refs, "activation evidence refs")
        _unique(self.lineage_refs, "activation lineage refs")
        _unique(tuple(pin.key for pin in self.exact_authority_pins), "activation authority pins")
        _unique(self.feature_refs, "activation feature refs")
        _unique(self.unresolved_refs, "activation unresolved refs")


@dataclass(frozen=True, slots=True)
class TypedMessageEdge:
    edge_ref: str
    family: MessageFamily
    source_node_ref: str
    target_node_ref: str
    polarity: EdgePolarity
    strength: float
    evidence_refs: tuple[str, ...] = ()
    authority_pins: tuple[ExactAuthorityPin, ...] = ()
    feature_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.edge_ref.strip() or not self.source_node_ref.strip() or not self.target_node_ref.strip():
            raise ValueError("typed message edge requires stable identity and endpoints")
        if self.source_node_ref == self.target_node_ref:
            raise ValueError("typed message edge cannot self-loop; recurrent memory is node-local")
        if not isfinite(self.strength) or self.strength < 0.0:
            raise ValueError("typed message strength must be finite and non-negative")
        _unique(self.evidence_refs, "typed edge evidence refs")
        _unique(tuple(pin.key for pin in self.authority_pins), "typed edge authority pins")
        _unique(self.feature_refs, "typed edge feature refs")


@dataclass(frozen=True, slots=True)
class HardConstraintMask:
    mask_ref: str
    target_node_ref: str
    allowed: bool
    reason: HardMaskReason
    proof_refs: tuple[str, ...]
    authority_pins: tuple[ExactAuthorityPin, ...] = ()

    def __post_init__(self) -> None:
        if not self.mask_ref.strip() or not self.target_node_ref.strip():
            raise ValueError("hard mask requires stable identity/target")
        if not self.proof_refs:
            raise ValueError("hard mask requires proof lineage")
        _unique(self.proof_refs, "hard mask proof refs")
        _unique(tuple(pin.key for pin in self.authority_pins), "hard mask authority pins")


@dataclass(frozen=True, slots=True)
class CompetitionGroup:
    group_ref: str
    member_node_refs: tuple[str, ...]
    basis_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.group_ref.strip() or len(self.member_node_refs) < 2:
            raise ValueError("competition group requires identity and at least two members")
        _unique(self.member_node_refs, "competition group members")
        _unique(self.basis_refs, "competition group basis refs")


@dataclass(frozen=True, slots=True)
class DynamicsParameterSet:
    parameter_set_ref: str
    parameter_pins: tuple[ExactAuthorityPin, ...]
    values: tuple[tuple[str, float], ...]
    family_gains: tuple[tuple[MessageFamily, float], ...]
    calibration_evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.parameter_set_ref.strip():
            raise ValueError("dynamics parameter set requires stable identity")
        if not self.parameter_pins:
            raise ValueError("recurrent dynamics requires exact parameter authority")
        _unique(tuple(pin.key for pin in self.parameter_pins), "dynamics parameter pins")
        _unique(tuple(name for name, _ in self.values), "dynamics parameter names")
        _unique(tuple(family for family, _ in self.family_gains), "dynamics family gains")
        for name, value in self.values:
            if not name.strip() or not isfinite(value):
                raise ValueError("dynamics parameters require finite named values")
        family_map = dict(self.family_gains)
        missing = set(REQUIRED_MESSAGE_FAMILIES).difference(family_map)
        if missing:
            raise ValueError(f"dynamics parameter set misses message families:{sorted(x.value for x in missing)}")
        if any(not isfinite(value) or value < 0.0 for value in family_map.values()):
            raise ValueError("message family gains must be finite and non-negative")
        _unique(self.calibration_evidence_refs, "dynamics calibration evidence")

    def value(self, name: str) -> float:
        values = dict(self.values)
        if name not in values:
            raise KeyError(f"missing exact recurrent parameter:{name}")
        return float(values[name])

    def gain(self, family: MessageFamily) -> float:
        values = dict(self.family_gains)
        return float(values[family])


@dataclass(frozen=True, slots=True)
class IterationActivationSummary:
    iteration: int
    maximum_delta: float
    active_nodes: int
    masked_nodes: int
    total_energy: float
    semantic_normal_form_refs: tuple[str, ...]
    competition_winner_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.iteration < 0 or self.active_nodes < 0 or self.masked_nodes < 0:
            raise ValueError("iteration summary counts cannot be negative")
        if not isfinite(self.maximum_delta) or self.maximum_delta < 0.0:
            raise ValueError("iteration maximum delta must be finite/non-negative")
        if not isfinite(self.total_energy):
            raise ValueError("iteration energy must be finite")
        _unique(self.semantic_normal_form_refs, "iteration semantic normal forms")
        _unique(self.competition_winner_refs, "iteration competition winners")


@dataclass(frozen=True, slots=True)
class TypedActivationPayload:
    payload_ref: str
    nodes: tuple[SemanticActivationNode, ...]
    edges: tuple[TypedMessageEdge, ...]
    masks: tuple[HardConstraintMask, ...]
    competition_groups: tuple[CompetitionGroup, ...]
    parameter_set: DynamicsParameterSet
    candidate_node_refs: tuple[tuple[str, str], ...]
    candidate_graphs: tuple[tuple[str, CSIRGraph], ...]
    candidate_prior_scores: tuple[tuple[str, float], ...]
    candidate_evidence_refs: tuple[tuple[str, tuple[str, ...]], ...]
    candidate_derivation_refs: tuple[tuple[str, tuple[str, ...]], ...]
    open_variable_refs: tuple[str, ...]
    unresolved_refs: tuple[str, ...]
    iteration_summaries: tuple[IterationActivationSummary, ...] = ()
    family_edge_counts: tuple[tuple[MessageFamily, int], ...] = ()
    proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.payload_ref.strip():
            raise ValueError("activation payload requires stable identity")
        node_refs = tuple(item.node_ref for item in self.nodes)
        _unique(node_refs, "activation node refs")
        edge_refs = tuple(item.edge_ref for item in self.edges)
        _unique(edge_refs, "activation edge refs")
        mask_refs = tuple(item.mask_ref for item in self.masks)
        _unique(mask_refs, "activation mask refs")
        known = set(node_refs)
        if any(item.source_node_ref not in known or item.target_node_ref not in known for item in self.edges):
            raise ValueError("activation edge references unknown node")
        if any(item.target_node_ref not in known for item in self.masks):
            raise ValueError("activation mask references unknown node")
        _unique(tuple(ref for ref, _ in self.candidate_node_refs), "candidate refs in activation payload")
        _unique(tuple(node_ref for _, node_ref in self.candidate_node_refs), "candidate node mappings")
        _unique(tuple(ref for ref, _ in self.candidate_graphs), "candidate graph refs")
        _unique(tuple(ref for ref, _ in self.candidate_prior_scores), "candidate prior refs")
        _unique(tuple(ref for ref, _ in self.candidate_evidence_refs), "candidate evidence refs")
        _unique(tuple(ref for ref, _ in self.candidate_derivation_refs), "candidate derivation refs")
        candidate_refs = {ref for ref, _ in self.candidate_node_refs}
        for label, refs in (
            ("candidate graph", {ref for ref, _ in self.candidate_graphs}),
            ("candidate prior", {ref for ref, _ in self.candidate_prior_scores}),
            ("candidate evidence", {ref for ref, _ in self.candidate_evidence_refs}),
            ("candidate derivation", {ref for ref, _ in self.candidate_derivation_refs}),
        ):
            if refs != candidate_refs:
                raise ValueError(f"{label} refs must exactly match activation candidate refs")
        if any(node_ref not in known for _, node_ref in self.candidate_node_refs):
            raise ValueError("candidate node mapping references unknown activation node")
        self._validate_competition_members(known)
        _unique(self.open_variable_refs, "activation open variables")
        _unique(self.unresolved_refs, "activation unresolved refs")
        _unique(tuple(family for family, _ in self.family_edge_counts), "activation family edge counts")
        _unique(self.proof_refs, "activation proof refs")

    def _validate_competition_members(self, known) -> None:
        mapped_nodes = {node_ref for _, node_ref in self.candidate_node_refs}
        seen = set()
        for group in self.competition_groups:
            if any(ref not in known for ref in group.member_node_refs):
                raise ValueError("competition group references unknown activation node")
            overlap = seen.intersection(group.member_node_refs)
            if overlap:
                raise ValueError("candidate competition node appears in more than one group")
            seen.update(group.member_node_refs)
        if self.competition_groups and not mapped_nodes.issubset(seen):
            raise ValueError("competition groups must cover every candidate node when competition exists")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint("typed-activation-payload-v351", self, 64)

    def node_map(self) -> Mapping[str, SemanticActivationNode]:
        return {item.node_ref: item for item in self.nodes}


def _unique(values, label: str) -> None:
    values = tuple(values)
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


__all__ = [
    "ActivationNodeKind", "CompetitionGroup", "ConvergenceKind", "DynamicsParameterSet",
    "EdgePolarity", "HardConstraintMask", "HardMaskReason", "IterationActivationSummary",
    "MessageFamily", "REQUIRED_MESSAGE_FAMILIES", "SemanticActivationNode",
    "TypedActivationPayload", "TypedMessageEdge",
]
