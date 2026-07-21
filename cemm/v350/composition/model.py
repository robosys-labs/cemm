"""Phase-9 cycle-local factor-graph meaning contracts.

These classes describe structural search state, not semantic ontology. Semantic
schema refs appear only as data carried by domain values produced from reviewed
language/schema authorities.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping

from ..schema.model import semantic_fingerprint
from ..uol.model import UOLGraph


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class MeaningVariableKind(StrEnum):
    FORM_PATH = "form_path"
    SENSE = "sense"
    SCHEMA = "schema"
    REFERENT = "referent"
    PORT_FILLER = "port_filler"
    SCOPE = "scope"
    TIME = "time"
    CONTEXT = "context"
    CONSTRUCTION = "construction"
    COORDINATION = "coordination"
    DISCOURSE_ACT = "discourse_act"


class MeaningFactorKind(StrEnum):
    LINK = "link"
    PORT_COMPATIBILITY = "port_compatibility"
    TYPE_ENTITLEMENT = "type_entitlement"
    CONTEXT_ISOLATION = "context_isolation"
    SCOPE_COMPATIBILITY = "scope_compatibility"
    EVIDENCE_EXCLUSIVITY = "evidence_exclusivity"
    CONSTRUCTION_COMPATIBILITY = "construction_compatibility"
    GROUNDING_COHERENCE = "grounding_coherence"
    DISCOURSE_COHERENCE = "discourse_coherence"
    WORLD_PLAUSIBILITY = "world_plausibility"
    DEFAULT_EXPECTATION = "default_expectation"
    COMPLEXITY = "complexity"


@dataclass(frozen=True, slots=True)
class MeaningValue:
    value_ref: str
    score: float
    evidence_refs: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.value_ref, "value_ref")
        if not isfinite(self.score):
            raise ValueError("meaning value score must be finite")
        if not self.evidence_refs:
            raise ValueError("meaning value requires evidence")


@dataclass(frozen=True, slots=True)
class MeaningVariable:
    variable_ref: str
    variable_kind: MeaningVariableKind
    values: tuple[MeaningValue, ...]
    required: bool = True
    evidence_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.variable_ref, "variable_ref")
        refs = tuple(item.value_ref for item in self.values)
        if len(refs) != len(set(refs)):
            raise ValueError(f"duplicate values for {self.variable_ref}")
        if self.required and not self.values:
            raise ValueError("required meaning variable requires a domain")
        if not self.evidence_refs:
            raise ValueError("meaning variable requires evidence")


@dataclass(frozen=True, slots=True)
class MeaningFactor:
    factor_ref: str
    factor_kind: MeaningFactorKind
    variable_refs: tuple[str, ...]
    hard: bool
    allowed_value_tuples: tuple[tuple[str, ...], ...] = ()
    tuple_scores: tuple[tuple[tuple[str, ...], float], ...] = ()
    evidence_refs: tuple[str, ...] = ()
    reason: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.factor_ref, "factor_ref")
        if not self.variable_refs:
            raise ValueError("meaning factor requires variables")
        if len(self.variable_refs) != len(set(self.variable_refs)):
            raise ValueError("meaning factor variables must be unique")
        for values in self.allowed_value_tuples:
            if len(values) != len(self.variable_refs):
                raise ValueError("allowed tuple arity mismatch")
        for values, score in self.tuple_scores:
            if len(values) != len(self.variable_refs) or not isfinite(score):
                raise ValueError("factor tuple score is invalid")
        if self.hard and not self.allowed_value_tuples:
            raise ValueError("hard factor requires at least one allowed tuple")
        if not self.evidence_refs or not self.reason.strip():
            raise ValueError("meaning factor requires evidence and reason")


@dataclass(frozen=True, slots=True)
class MeaningFactorGraph:
    graph_ref: str
    source_lattice_ref: str
    grounding_ref: str
    snapshot_fingerprint: str
    variables: tuple[MeaningVariable, ...]
    factors: tuple[MeaningFactor, ...]
    unresolved_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in ((self.graph_ref, "graph_ref"), (self.source_lattice_ref, "source_lattice_ref"),
                             (self.grounding_ref, "grounding_ref"), (self.snapshot_fingerprint, "snapshot_fingerprint")):
            _ref(value, label)
        refs = tuple(item.variable_ref for item in self.variables)
        if len(refs) != len(set(refs)):
            raise ValueError("meaning factor graph variables must be unique")
        known = set(refs)
        for factor in self.factors:
            if not set(factor.variable_refs).issubset(known):
                raise ValueError("meaning factor references unknown variable")
        if not self.evidence_refs:
            raise ValueError("meaning factor graph requires evidence")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint("meaning-factor-graph", self, 64)


@dataclass(frozen=True, slots=True)
class PruningTrace:
    trace_ref: str
    variable_ref: str
    value_ref: str
    reason: str
    factor_refs: tuple[str, ...]
    depth: int


@dataclass(frozen=True, slots=True)
class MeaningHypothesis:
    hypothesis_ref: str
    assignments: tuple[tuple[str, str], ...]
    score: float
    satisfied_factor_refs: tuple[str, ...]
    unresolved_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _ref(self.hypothesis_ref, "hypothesis_ref")
        if len(self.assignments) != len({key for key, _ in self.assignments}):
            raise ValueError("meaning hypothesis assigns a variable twice")
        if not isfinite(self.score) or not self.evidence_refs:
            raise ValueError("meaning hypothesis requires finite score and evidence")

    @property
    def assignment_map(self) -> dict[str, str]:
        return dict(self.assignments)


@dataclass(frozen=True, slots=True)
class MeaningSolveResult:
    solve_ref: str
    factor_graph_ref: str
    hypotheses: tuple[MeaningHypothesis, ...]
    pruning_trace: tuple[PruningTrace, ...]
    exhausted: bool
    expansions: int
    evidence_refs: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PartialUnderstandingMap:
    understood_refs: tuple[str, ...]
    unresolved_refs: tuple[str, ...]
    frontier_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SelectionAssessment:
    selected_hypothesis_ref: str | None
    decisive: bool
    margin: float
    close_alternative_refs: tuple[str, ...]
    uncertainty_reasons: tuple[str, ...]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MeaningBundle:
    bundle_ref: str
    factor_graph_ref: str
    selected_hypothesis_ref: str | None
    uol_graph: UOLGraph | None
    alternatives: tuple[MeaningHypothesis, ...]
    selection: SelectionAssessment
    partial_understanding: PartialUnderstandingMap
    evidence_refs: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MeaningCompositionResult:
    factor_graph: MeaningFactorGraph
    solve_result: MeaningSolveResult
    bundle: MeaningBundle
    materialization_issue_codes: tuple[tuple[str, tuple[str, ...]], ...] = ()

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(
            "meaning-composition-result",
            (self.factor_graph.fingerprint, self.solve_result.solve_ref, self.bundle.bundle_ref, self.materialization_issue_codes),
            64,
        )


def _ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
