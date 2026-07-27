"""Cycle-local semantic cognition artifacts for CEMM v1.

The objects in this module are compressed CSIR-facing runtime structures.  They
carry interpretation, discourse, query, epistemic and frontier state without
creating a second semantic ontology or persisting transient cognition.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from cemm.model import canonical, isvar, stable


FORCE_CLAIM = "claim"
FORCE_QUERY = "query"
FORCE_DESCRIPTION = "description_request"
FORCE_DIRECTIVE = "directive"
FORCE_CORRECTION = "correction"
FORCE_RETRACTION = "retraction"
FORCE_ACKNOWLEDGMENT = "acknowledgment"


@dataclass(frozen=True)
class SemanticVariable:
    ref: str
    filler_kind: str = "atom"
    role_ref: str | None = None

    def __post_init__(self) -> None:
        if not isvar(self.ref):
            raise ValueError(f"semantic variable must start with ?: {self.ref}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "ref": self.ref,
            "filler_kind": self.filler_kind,
            "role_ref": self.role_ref,
        }


@dataclass(frozen=True)
class QueryStructure:
    query_ref: str
    restrictions: tuple[dict[str, Any], ...]
    variables: tuple[SemanticVariable, ...]
    projection: tuple[str, ...]
    qualifiers: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "QueryStructure":
        if value.get("operator"):
            raise ValueError("bare application queries are unsupported")
        restrictions = tuple(dict(x) for x in value.get("restrictions", ()))
        if not restrictions:
            raise ValueError("query requires restrictions")
        raw_variables = list(value.get("variables", ()))
        raw_projection = value.get("projection")
        projection = tuple(raw_projection) if raw_projection is not None else ()
        inferred: dict[str, SemanticVariable] = {}
        for item in raw_variables:
            variable = SemanticVariable(
                ref=str(item["ref"]),
                filler_kind=str(item.get("filler_kind", "atom")),
                role_ref=item.get("role_ref"),
            )
            inferred[variable.ref] = variable
        for restriction in restrictions:
            for role, filler in restriction.get("args", {}).items():
                if isinstance(filler, str) and isvar(filler):
                    inferred.setdefault(filler, SemanticVariable(filler, "atom", role))
        if raw_projection is None:
            projection = tuple(sorted(inferred))
        unknown_projection = set(projection) - set(inferred)
        if unknown_projection:
            raise ValueError(f"query projects undeclared variables: {sorted(unknown_projection)}")
        ref = str(value.get("query_ref") or stable("query", restrictions, projection, value.get("qualifiers", {})))
        return cls(ref, restrictions, tuple(inferred[key] for key in sorted(inferred)), projection, dict(value.get("qualifiers", {})))

    def as_dict(self) -> dict[str, Any]:
        return {
            "query_ref": self.query_ref,
            "restrictions": [dict(x) for x in self.restrictions],
            "variables": [x.as_dict() for x in self.variables],
            "projection": list(self.projection),
            "qualifiers": dict(self.qualifiers),
        }


@dataclass(frozen=True)
class QueryBinding:
    values: Mapping[str, Any]
    proof_refs: tuple[str, ...] = ()

    def signature(self) -> str:
        return canonical(dict(self.values))

    def as_dict(self) -> dict[str, Any]:
        return {"values": dict(self.values), "proof_refs": list(self.proof_refs)}


@dataclass(frozen=True)
class QueryResult:
    query_ref: str
    status: str
    bindings: tuple[QueryBinding, ...]
    coverage: float
    support_count: int
    opposition_count: int
    unresolved_variables: tuple[str, ...] = ()
    proofs: tuple[dict[str, Any], ...] = ()
    blocking_frontiers: tuple[str, ...] = ()
    qualifiers: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "query_ref": self.query_ref,
            "status": self.status,
            "bindings": [x.as_dict() for x in self.bindings],
            "coverage": self.coverage,
            "support_count": self.support_count,
            "opposition_count": self.opposition_count,
            "unresolved_variables": list(self.unresolved_variables),
            "proofs": list(self.proofs),
            "blocking_frontiers": list(self.blocking_frontiers),
            "qualifiers": dict(self.qualifiers),
        }


@dataclass(frozen=True)
class InterpretationAssessment:
    status: str
    stable_packet: Mapping[str, Any] | None = None
    grounded_refs: tuple[str, ...] = ()
    open_variables: tuple[str, ...] = ()
    unresolved_evidence: tuple[dict[str, Any], ...] = ()
    blockers: tuple[str, ...] = ()
    coverage: Mapping[str, Any] = field(default_factory=dict)
    partial_structure: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "stable_packet": dict(self.stable_packet) if self.stable_packet else None,
            "grounded_refs": list(self.grounded_refs),
            "open_variables": list(self.open_variables),
            "unresolved_evidence": list(self.unresolved_evidence),
            "blockers": list(self.blockers),
            "coverage": dict(self.coverage),
            "partial_structure": dict(self.partial_structure),
        }


@dataclass(frozen=True)
class LearningFrontier:
    frontier_ref: str
    kind: str
    target_ref: str | None
    evidence: tuple[dict[str, Any], ...]
    blocks: tuple[str, ...] = ()

    @classmethod
    def create(
        cls,
        kind: str,
        evidence: Iterable[Mapping[str, Any]],
        *,
        target_ref: str | None = None,
        blocks: Iterable[str] = (),
        cycle_ref: str = "cycle:unknown",
    ) -> "LearningFrontier":
        ev = tuple(dict(x) for x in evidence)
        blocked = tuple(sorted(set(blocks)))
        return cls(stable("frontier", cycle_ref, kind, target_ref, ev, blocked), kind, target_ref, ev, blocked)

    def as_dict(self) -> dict[str, Any]:
        return {
            "frontier_ref": self.frontier_ref,
            "kind": self.kind,
            "target_ref": self.target_ref,
            "evidence": list(self.evidence),
            "blocks": list(self.blocks),
        }


@dataclass(frozen=True)
class FrontierGraph:
    frontiers: tuple[LearningFrontier, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"frontiers": [x.as_dict() for x in self.frontiers]}


@dataclass(frozen=True)
class ScopedEpistemicAssessment:
    target_ref: str
    status: str
    support_refs: tuple[str, ...] = ()
    opposition_refs: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    coverage: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_ref": self.target_ref,
            "status": self.status,
            "support_refs": list(self.support_refs),
            "opposition_refs": list(self.opposition_refs),
            "missing": list(self.missing),
            "coverage": self.coverage,
        }


@dataclass(frozen=True)
class DiscourseAct:
    act_ref: str
    force: str
    speaker_ref: str
    addressee_ref: str
    content: tuple[dict[str, Any], ...] = ()
    query: QueryStructure | None = None
    describe_target: str | None = None
    context_ref: str | None = None
    modality: str = "actual"
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "act_ref": self.act_ref,
            "force": self.force,
            "speaker_ref": self.speaker_ref,
            "addressee_ref": self.addressee_ref,
            "content": [dict(x) for x in self.content],
            "query": self.query.as_dict() if self.query else None,
            "describe_target": self.describe_target,
            "context_ref": self.context_ref,
            "modality": self.modality,
            "evidence": dict(self.evidence),
        }


def build_discourse_act(packet: Mapping[str, Any], participant_frame, trace: Mapping[str, Any] | None = None) -> DiscourseAct:
    if not packet.get("force"):
        raise ValueError("compiled packet requires explicit discourse force")
    force = str(packet["force"])
    query = QueryStructure.from_dict(packet["query"]) if packet.get("query") else None
    if force == FORCE_DIRECTIVE:
        content = tuple(dict(x) for x in packet.get("directive", {}).get("content", ()))
    else:
        content = tuple(dict(x) for x in packet.get("apps", ()))
    context_ref = packet.get("context_ref") or packet.get("qualifiers", {}).get("context")
    modality = str(packet.get("modality") or packet.get("qualifiers", {}).get("modality") or "actual")
    payload = {
        "force": force,
        "speaker": participant_frame.speaker_ref,
        "addressee": participant_frame.addressee_ref,
        "content": content,
        "query": query.as_dict() if query else None,
        "describe": packet.get("describe"),
        "context": context_ref,
        "modality": modality,
    }
    return DiscourseAct(
        act_ref=stable("discourse-act", payload),
        force=str(force),
        speaker_ref=participant_frame.speaker_ref,
        addressee_ref=participant_frame.addressee_ref,
        content=content,
        query=query,
        describe_target=packet.get("describe"),
        context_ref=context_ref,
        modality=modality,
        evidence={**dict(trace or {}), "packet_qualifiers": dict(packet.get("qualifiers", {}))},
    )

# CEMM_SOURCE_REWRITE:cognition:v3.1.3
