"""SemanticRetriever — sole authority for semantic retrieval (v3.4).

Builds semantic query patterns from selected propositions, goals, open
ports, and context. Retrieves canonical records and evidence.

Import boundary: model + schema + epistemics submodules only. No engine imports.

Architectural guardrails (CORE_LOOP.md §C1, AUTHORITY_MATRIX):
- Retrieve canonical records and evidence.
- Does NOT decide truth, select interpretations, or produce response wording.

Authority: semantic_retrieval
Must not decide it: runtime-local helper
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .query_pattern import (
    SemanticQueryPattern,
    QueryPatternKind,
    EvidencePolicy,
    QueryPatternBuilder,
)


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """A retrieval result for a single query pattern."""
    query_pattern_ref: str
    record_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    relation_refs: tuple[str, ...] = ()
    confidence: float = 0.0
    is_empty: bool = True


@dataclass(frozen=True, slots=True)
class RetrievalBatch:
    """A batch of retrieval results."""
    results: tuple[RetrievalResult, ...] = ()
    total_records: int = 0

    @property
    def is_empty(self) -> bool:
        return all(r.is_empty for r in self.results)


class SemanticRetriever:
    """Sole authority for semantic retrieval (v3.4).

    Builds semantic query patterns from selected propositions, goals,
    open ports, and context. Retrieves canonical records and evidence
    from the schema store and durable semantic store.

    Does NOT:
    - Decide truth
    - Select interpretations
    - Produce response wording
    - Mutate stores
    """

    def __init__(
        self,
        store: Any | None = None,
        schema_store: Any | None = None,
        truth_maintenance: Any | None = None,
    ) -> None:
        self._store = store  # DurableSemanticStore
        self._schema_store = schema_store  # SemanticSchemaStore
        self._truth_maintenance = truth_maintenance
        self._pattern_builder = QueryPatternBuilder()

    def retrieve(
        self,
        selected_interpretations: list[Any] | None = None,
        goal_refs: tuple[str, ...] = (),
        open_ports: tuple[Any, ...] = (),
        context_ref: str = "",
        durable_store: Any | None = None,
        schema_store: Any | None = None,
    ) -> RetrievalBatch:
        """Retrieve canonical records and evidence for the cycle.

        Builds query patterns from selected propositions, goals, open
        ports, and context. Returns evidence-aware results.
        """
        store = durable_store or self._store
        schemas = schema_store or self._schema_store

        # Build query patterns
        prop_patterns = self._pattern_builder.build_from_interpretations(
            selected_interpretations,
        )
        port_patterns = self._pattern_builder.build_from_open_ports(open_ports)
        goal_patterns = self._pattern_builder.build_from_goals(goal_refs)

        all_patterns = prop_patterns + port_patterns + goal_patterns

        if not all_patterns:
            return RetrievalBatch()

        results: list[RetrievalResult] = []
        for pattern in all_patterns:
            result = self._execute_pattern(pattern, store, schemas)
            results.append(result)

        total = sum(len(r.record_refs) + len(r.relation_refs) for r in results)
        return RetrievalBatch(
            results=tuple(results),
            total_records=total,
        )

    def _execute_pattern(
        self,
        pattern: SemanticQueryPattern,
        durable_store: Any | None,
        schema_store: Any | None,
    ) -> RetrievalResult:
        """Execute a single query pattern against available stores."""
        record_refs: list[str] = []
        evidence_refs: list[str] = []
        relation_refs: list[str] = []

        # Query schema store for matching schema records
        if schema_store is not None:
            for sem_key in pattern.semantic_keys:
                candidates = self._query_schema_store(schema_store, sem_key)
                record_refs.extend(candidates)

        # Query durable store for relation records matching referent constraints
        if durable_store is not None:
            relations = self._query_durable_store(durable_store, pattern)
            relation_refs.extend(relations)

        # Gather evidence from truth maintenance if available
        if self._truth_maintenance is not None and pattern.proposition_ref:
            evidence = self._gather_evidence(pattern)
            evidence_refs.extend(evidence)

        is_empty = (
            len(record_refs) == 0
            and len(relation_refs) == 0
            and len(evidence_refs) == 0
        )
        confidence = (
            0.0 if is_empty
            else min(1.0, (len(record_refs) + len(relation_refs)) * 0.3 + 0.2)
        )

        return RetrievalResult(
            query_pattern_ref=pattern.pattern_id,
            record_refs=tuple(record_refs),
            evidence_refs=tuple(evidence_refs),
            relation_refs=tuple(relation_refs),
            confidence=confidence,
            is_empty=is_empty,
        )

    def _query_schema_store(
        self, schema_store: Any, semantic_key: str,
    ) -> list[str]:
        """Query schema store for records matching a semantic key."""
        try:
            if hasattr(schema_store, "find_candidates"):
                candidates = schema_store.find_candidates(semantic_key)
                return [
                    getattr(c, "record_id", str(c)) for c in candidates
                ]
            if hasattr(schema_store, "active_record_ids"):
                active_ids = schema_store.active_record_ids()
                return [
                    rid for rid in active_ids
                    if semantic_key in rid
                ]
        except Exception:
            pass
        return []

    def _query_durable_store(
        self, durable_store: Any, pattern: SemanticQueryPattern,
    ) -> list[str]:
        """Query durable store for relation records matching the pattern."""
        try:
            if not hasattr(durable_store, "query_relations"):
                return []

            subject_concept = ""
            subject_entity = ""
            subject_surface = ""
            relation_key = ""

            # Use the first constraint as subject, second as relation
            # Role resolution is schema-generic — no hard-coded role names
            for i, constraint in enumerate(pattern.referent_constraints):
                if i == 0:
                    subject_concept = constraint.concept_id
                    subject_entity = constraint.entity_id
                    subject_surface = constraint.surface
                elif i == 1:
                    relation_key = constraint.concept_id or constraint.semantic_key

            if not relation_key and pattern.semantic_keys:
                relation_key = pattern.semantic_keys[0]

            frames = durable_store.query_relations(
                relation_key=relation_key,
                subject_concept_id=subject_concept,
                subject_entity_id=subject_entity,
                subject_surface=subject_surface,
                active_only=True,
            )
            return [getattr(f, "relation_id", "") for f in frames]
        except Exception:
            pass
        return []

    def _gather_evidence(self, pattern: SemanticQueryPattern) -> list[str]:
        """Gather evidence refs from truth maintenance for a proposition."""
        try:
            evidence = self._truth_maintenance.get_evidence(pattern.proposition_ref)
            return [getattr(ev, "evidence_id", str(ev)) for ev in evidence]
        except Exception:
            pass
        return []
