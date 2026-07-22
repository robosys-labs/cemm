"""Typed Phase-10 deterministic composition and baseline dynamics artifacts.

These are mechanism contracts, not semantic ontology.  Meaning remains exact CSIR plus
its pinned v3.5.1 authority closure.  The deterministic baseline exists to make semantics
inspectable before learned recurrent parameters are required and later becomes an oracle /
shadow comparator for the recurrent solver.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping

from ..csir.model import CSIRGraph, CSIRRef, ExactAuthorityPin


class CompositionConstraintKind(str, Enum):
    AUTHORITY = "authority"
    GROUNDING = "grounding"
    CONSTRUCTION = "construction"
    PORT = "port"
    TYPE = "type"
    SCOPE = "scope"
    CONTEXT = "context"
    COVERAGE = "coverage"
    DISTINCTNESS = "distinctness"
    BUDGET = "budget"


@dataclass(frozen=True, slots=True)
class DeterministicCompositionBudget:
    maximum_branches: int = 256
    maximum_program_steps: int = 256
    maximum_schema_class_candidates: int = 64
    maximum_fragments: int = 128
    canonicalization_budget: int = 100_000

    def __post_init__(self) -> None:
        values = (
            self.maximum_branches,
            self.maximum_program_steps,
            self.maximum_schema_class_candidates,
            self.maximum_fragments,
            self.canonicalization_budget,
        )
        if any(value < 1 for value in values):
            raise ValueError("deterministic composition budgets must be positive")


@dataclass(frozen=True, slots=True)
class ConstraintAssessment:
    assessment_ref: str
    kind: CompositionConstraintKind
    satisfied: bool
    hard: bool
    subject_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    reason_ref: str = ""

    def __post_init__(self) -> None:
        if not self.assessment_ref.strip():
            raise ValueError("constraint assessment requires stable identity")
        if len(self.subject_refs) != len(set(self.subject_refs)):
            raise ValueError("constraint assessment subject refs must be unique")
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise ValueError("constraint assessment evidence refs must be unique")
        if self.hard and not self.reason_ref.strip():
            raise ValueError("hard constraint assessment requires a reason_ref")


@dataclass(frozen=True, slots=True)
class CompositionFrontier:
    frontier_ref: str
    missing_contract: str
    source_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    effects: tuple[str, ...] = ("learning", "clarification")

    def __post_init__(self) -> None:
        if not self.frontier_ref.strip() or not self.missing_contract.strip():
            raise ValueError("composition frontier requires identity and missing contract")
        for values, label in (
            (self.source_refs, "source refs"),
            (self.evidence_refs, "evidence refs"),
            (self.effects, "effects"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"composition frontier {label} must be unique")


@dataclass(frozen=True, slots=True)
class CandidateActivation:
    candidate_ref: str
    semantic_fingerprint: str
    exact_fingerprint: str
    support: float
    score_components: tuple[tuple[str, float], ...] = ()
    evidence_refs: tuple[str, ...] = ()
    frontier_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.candidate_ref.strip() or not self.semantic_fingerprint.strip() or not self.exact_fingerprint.strip():
            raise ValueError("candidate activation requires exact candidate identity")
        if not isfinite(self.support):
            raise ValueError("candidate activation support must be finite")
        names = tuple(name for name, _ in self.score_components)
        if len(names) != len(set(names)):
            raise ValueError("candidate activation score component names must be unique")
        if any(not isfinite(value) for _, value in self.score_components):
            raise ValueError("candidate activation score components must be finite")


@dataclass(frozen=True, slots=True)
class DeterministicActivationPayload:
    payload_ref: str
    candidate_activations: tuple[CandidateActivation, ...]
    candidate_graphs: tuple[tuple[str, CSIRGraph], ...]
    partial_graph: CSIRGraph | None = None
    open_variables: tuple[CSIRRef, ...] = ()
    frontier_refs: tuple[str, ...] = ()
    authority_pins: tuple[ExactAuthorityPin, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.payload_ref.strip():
            raise ValueError("deterministic activation payload requires identity")
        refs = tuple(item.candidate_ref for item in self.candidate_activations)
        if len(refs) != len(set(refs)):
            raise ValueError("deterministic activation payload candidate refs must be unique")
        graph_refs = tuple(ref for ref, _ in self.candidate_graphs)
        if len(graph_refs) != len(set(graph_refs)) or set(graph_refs) != set(refs):
            raise ValueError("candidate graphs must exactly correspond to candidate activations")
        if len(self.open_variables) != len(set(self.open_variables)):
            raise ValueError("open variables must be unique")
        if len(self.frontier_refs) != len(set(self.frontier_refs)):
            raise ValueError("activation frontier refs must be unique")
        if len({pin.key for pin in self.authority_pins}) != len(self.authority_pins):
            raise ValueError("activation authority pins must be unique")


__all__ = [
    "CandidateActivation",
    "CompositionConstraintKind",
    "CompositionFrontier",
    "ConstraintAssessment",
    "DeterministicActivationPayload",
    "DeterministicCompositionBudget",
]
