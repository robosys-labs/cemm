"""SemanticQueryPattern — structured query patterns for semantic retrieval.

Builds query patterns from selected propositions, goals, open ports,
and context. A query pattern specifies what to look up and how:
which semantic keys, which referent constraints, which evidence policy,
and which temporal scope.

Import boundary: model + schema submodules only. No engine imports.

Architectural guardrails (CORE_LOOP.md §C1, AUTHORITY_MATRIX):
- Query patterns are derived control records, not semantic objects.
- Query patterns do NOT decide truth, select interpretations, or
  produce response wording.
- Open ports use role_schema_ref, not role_name.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class QueryPatternKind(str, Enum):
    """Kind of semantic query pattern."""
    PROPOSITION_LOOKUP = "proposition_lookup"
    REFERENT_QUERY = "referent_query"
    SCHEMA_QUERY = "schema_query"
    OPEN_PORT_FILL = "open_port_fill"
    GOAL_QUERY = "goal_query"
    EVIDENCE_GATHER = "evidence_gather"
    CAPABILITY_QUERY = "capability_query"


class EvidencePolicy(str, Enum):
    """Policy for evidence retrieval."""
    ALL_EVIDENCE = "all_evidence"
    SUPPORTING_ONLY = "supporting_only"
    COUNTEREVIDENCE_ONLY = "counterevidence_only"
    INDEPENDENT_ONLY = "independent_only"


@dataclass(frozen=True, slots=True)
class ReferentConstraint:
    """A constraint on a referent in a query pattern."""
    role_schema_ref: str = ""
    concept_id: str = ""
    entity_id: str = ""
    surface: str = ""
    semantic_key: str = ""


@dataclass(frozen=True, slots=True)
class SemanticQueryPattern:
    """A structured query pattern for semantic retrieval.

    Derived from propositions, goals, open ports, and context.
    Specifies what to look up and how, without deciding truth or
    selecting interpretations.
    """
    pattern_id: str
    pattern_kind: QueryPatternKind
    proposition_ref: str = ""
    semantic_keys: tuple[str, ...] = ()
    referent_constraints: tuple[ReferentConstraint, ...] = ()
    context_ref: str = ""
    evidence_policy: EvidencePolicy = EvidencePolicy.ALL_EVIDENCE
    temporal_scope: str = "any"  # any, current, historical
    goal_ref: str = ""
    open_port_role_schema_ref: str = ""
    confidence: float = 0.5


class QueryPatternBuilder:
    """Builds SemanticQueryPatterns from cycle inputs.

    Does NOT:
    - Decide truth
    - Select interpretations
    - Produce response wording
    - Mutate stores
    """

    def __init__(self) -> None:
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"qp:{self._counter}"

    def build_from_interpretations(
        self,
        interpretations: list[Any] | None = None,
    ) -> tuple[SemanticQueryPattern, ...]:
        """Build query patterns from selected interpretations.

        For each interpretation, builds a proposition lookup pattern
        that queries for evidence and records related to the
        interpretation's proposition.
        """
        if not interpretations:
            return ()

        patterns: list[SemanticQueryPattern] = []
        for interp in interpretations:
            prop_ref = getattr(interp, "proposition_ref", "")
            if not prop_ref:
                prop = getattr(interp, "proposition", None)
                if prop is not None:
                    prop_ref = getattr(prop, "id", "")

            if not prop_ref:
                continue

            # Extract semantic keys from the interpretation
            semantic_keys: list[str] = []
            prop = getattr(interp, "proposition", None)
            if prop is not None:
                pred_ref = getattr(prop, "predicate_schema_ref", "") or getattr(prop, "predication_ref", "")
                if pred_ref:
                    semantic_keys.append(pred_ref)

            # Extract referent constraints from role bindings
            constraints: list[ReferentConstraint] = []
            role_bindings = getattr(interp, "role_bindings", None) or getattr(prop, "role_bindings", None)
            if role_bindings:
                if isinstance(role_bindings, dict):
                    for role_ref, filler in role_bindings.items():
                        constraints.append(self._constraint_from_filler(role_ref, filler))
                elif isinstance(role_bindings, (list, tuple)):
                    for binding in role_bindings:
                        role_ref = getattr(binding, "role_schema_ref", "")
                        filler = getattr(binding, "filler", None)
                        if role_ref and filler is not None:
                            constraints.append(self._constraint_from_filler(role_ref, filler))

            context_ref = getattr(interp, "context_ref", "")
            if not context_ref:
                ctx = getattr(interp, "context_frame", None)
                if ctx is not None:
                    context_ref = getattr(ctx, "id", "")

            patterns.append(SemanticQueryPattern(
                pattern_id=self._next_id(),
                pattern_kind=QueryPatternKind.PROPOSITION_LOOKUP,
                proposition_ref=prop_ref,
                semantic_keys=tuple(semantic_keys),
                referent_constraints=tuple(constraints),
                context_ref=context_ref,
            ))

        return tuple(patterns)

    def build_from_open_ports(
        self,
        open_ports: tuple[Any, ...] = (),
    ) -> tuple[SemanticQueryPattern, ...]:
        """Build query patterns from open ports.

        Open ports use role_schema_ref, not role_name.
        Each open port generates a fill pattern looking for referents
        that could satisfy the role's schema requirements.
        """
        patterns: list[SemanticQueryPattern] = []
        for port in open_ports:
            role_schema_ref = getattr(port, "role_schema_ref", "")
            if not role_schema_ref:
                continue

            patterns.append(SemanticQueryPattern(
                pattern_id=self._next_id(),
                pattern_kind=QueryPatternKind.OPEN_PORT_FILL,
                open_port_role_schema_ref=role_schema_ref,
                semantic_keys=(role_schema_ref,),
            ))

        return tuple(patterns)

    def build_from_goals(
        self,
        goal_refs: tuple[str, ...] = (),
    ) -> tuple[SemanticQueryPattern, ...]:
        """Build query patterns from active goals."""
        patterns: list[SemanticQueryPattern] = []
        for goal_ref in goal_refs:
            patterns.append(SemanticQueryPattern(
                pattern_id=self._next_id(),
                pattern_kind=QueryPatternKind.GOAL_QUERY,
                goal_ref=goal_ref,
            ))

        return tuple(patterns)

    def build_evidence_gather(
        self,
        proposition_ref: str,
        context_ref: str = "",
        policy: EvidencePolicy = EvidencePolicy.ALL_EVIDENCE,
    ) -> SemanticQueryPattern:
        """Build an evidence gathering pattern for a proposition."""
        return SemanticQueryPattern(
            pattern_id=self._next_id(),
            pattern_kind=QueryPatternKind.EVIDENCE_GATHER,
            proposition_ref=proposition_ref,
            context_ref=context_ref,
            evidence_policy=policy,
        )

    def _constraint_from_filler(
        self, role_ref: str, filler: Any,
    ) -> ReferentConstraint:
        """Build a ReferentConstraint from a role binding filler."""
        concept_id = ""
        entity_id = ""
        surface = ""
        semantic_key = ""

        if isinstance(filler, str):
            concept_id = filler
        else:
            concept_id = getattr(filler, "concept_id", "")
            entity_id = getattr(filler, "entity_id", "")
            surface = getattr(filler, "surface", "")
            semantic_key = getattr(filler, "semantic_key", "")

        return ReferentConstraint(
            role_schema_ref=role_ref,
            concept_id=concept_id,
            entity_id=entity_id,
            surface=surface,
            semantic_key=semantic_key,
        )
