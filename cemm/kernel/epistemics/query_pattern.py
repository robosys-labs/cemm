"""Structured semantic retrieval patterns.

v3.4.1 replacement: patterns are built from SelectedInterpretation refs and
schema-generic RoleBinding.filler_ref values; no object/ref shadow API is
required.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class QueryPatternKind(str, Enum):
    PROPOSITION_LOOKUP = "proposition_lookup"
    REFERENT_QUERY = "referent_query"
    SCHEMA_QUERY = "schema_query"
    OPEN_PORT_FILL = "open_port_fill"
    GOAL_QUERY = "goal_query"
    EVIDENCE_GATHER = "evidence_gather"
    CAPABILITY_QUERY = "capability_query"


class EvidencePolicy(str, Enum):
    ALL_EVIDENCE = "all_evidence"
    SUPPORTING_ONLY = "supporting_only"
    COUNTEREVIDENCE_ONLY = "counterevidence_only"
    INDEPENDENT_ONLY = "independent_only"


@dataclass(frozen=True, slots=True)
class ReferentConstraint:
    role_schema_ref: str = ""
    concept_id: str = ""
    entity_id: str = ""
    surface: str = ""
    semantic_key: str = ""
    filler_ref: str = ""


@dataclass(frozen=True, slots=True)
class SemanticQueryPattern:
    pattern_id: str
    pattern_kind: QueryPatternKind
    proposition_ref: str = ""
    semantic_keys: tuple[str, ...] = ()
    referent_constraints: tuple[ReferentConstraint, ...] = ()
    context_ref: str = ""
    evidence_policy: EvidencePolicy = EvidencePolicy.ALL_EVIDENCE
    temporal_scope: str = "any"
    goal_ref: str = ""
    open_port_role_schema_ref: str = ""
    confidence: float = 0.5


class QueryPatternBuilder:
    def __init__(self) -> None:
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"qp:{self._counter}"

    def build_from_interpretations(
        self,
        interpretations: list[Any] | tuple[Any, ...] | None = None,
    ) -> tuple[SemanticQueryPattern, ...]:
        if not interpretations:
            return ()
        patterns: list[SemanticQueryPattern] = []
        for interpretation in interpretations:
            proposition_ref = getattr(interpretation, "proposition_ref", "")
            if not proposition_ref:
                continue
            semantic_keys = tuple(dict.fromkeys(
                key for key in (
                    getattr(interpretation, "predicate_semantic_key", ""),
                    getattr(interpretation, "predicate_schema_ref", ""),
                ) if key
            ))
            constraints = tuple(
                ReferentConstraint(
                    role_schema_ref=getattr(binding, "role_schema_ref", ""),
                    filler_ref=getattr(binding, "filler_ref", ""),
                    concept_id=getattr(binding, "filler_ref", ""),
                )
                for binding in getattr(interpretation, "role_bindings", ())
                if getattr(binding, "role_schema_ref", "")
            )
            patterns.append(SemanticQueryPattern(
                pattern_id=self._next_id(),
                pattern_kind=QueryPatternKind.PROPOSITION_LOOKUP,
                proposition_ref=proposition_ref,
                semantic_keys=semantic_keys,
                referent_constraints=constraints,
                context_ref=getattr(interpretation, "context_ref", ""),
            ))
        return tuple(patterns)

    def build_from_open_ports(
        self,
        open_ports: tuple[Any, ...] = (),
    ) -> tuple[SemanticQueryPattern, ...]:
        return tuple(
            SemanticQueryPattern(
                pattern_id=self._next_id(),
                pattern_kind=QueryPatternKind.OPEN_PORT_FILL,
                open_port_role_schema_ref=getattr(port, "role_schema_ref", ""),
                semantic_keys=(getattr(port, "role_schema_ref", ""),),
            )
            for port in open_ports
            if getattr(port, "role_schema_ref", "")
        )

    def build_from_goals(
        self,
        goal_refs: tuple[str, ...] = (),
    ) -> tuple[SemanticQueryPattern, ...]:
        return tuple(
            SemanticQueryPattern(
                pattern_id=self._next_id(),
                pattern_kind=QueryPatternKind.GOAL_QUERY,
                goal_ref=goal_ref,
            )
            for goal_ref in goal_refs if goal_ref
        )

    def build_evidence_gather(
        self,
        proposition_ref: str,
        context_ref: str = "",
        policy: EvidencePolicy = EvidencePolicy.ALL_EVIDENCE,
    ) -> SemanticQueryPattern:
        return SemanticQueryPattern(
            pattern_id=self._next_id(),
            pattern_kind=QueryPatternKind.EVIDENCE_GATHER,
            proposition_ref=proposition_ref,
            context_ref=context_ref,
            evidence_policy=policy,
        )
