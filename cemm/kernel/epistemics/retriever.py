"""Evidence-aware retrieval from schema and semantic fact stores."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .query_pattern import QueryPatternBuilder
from ..memory.semantic import FactQuery

@dataclass(frozen=True, slots=True)
class RetrievalResult:
    query_pattern_ref: str
    record_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    relation_refs: tuple[str, ...] = ()
    records: tuple[Any, ...] = ()
    confidence: float = 0.0
    is_empty: bool = True

@dataclass(frozen=True, slots=True)
class RetrievalBatch:
    results: tuple[RetrievalResult, ...] = ()
    total_records: int = 0

    @property
    def is_empty(self):
        return all(item.is_empty for item in self.results)

class SemanticRetriever:
    def __init__(
        self, store=None, schema_store=None,
        truth_maintenance=None,
    ):
        self._store = store
        self._schemas = schema_store
        self._truth = truth_maintenance
        self._builder = QueryPatternBuilder()

    def retrieve(
        self, selected_interpretations=None,
        goal_refs=(), open_ports=(),
        context_ref="", durable_store=None,
        schema_store=None,
    ):
        memory = durable_store or self._store
        schemas = schema_store or self._schemas
        patterns = (
            self._builder.build_from_interpretations(
                selected_interpretations
            )
            + self._builder.build_from_open_ports(
                open_ports
            )
            + self._builder.build_from_goals(
                goal_refs
            )
        )
        results = tuple(
            self._execute(
                pattern, memory, schemas
            )
            for pattern in patterns
        )
        return RetrievalBatch(
            results=results,
            total_records=sum(
                len(result.records)
                + len(result.record_refs)
                for result in results
            ),
        )

    def _execute(self, pattern, memory, schemas):
        schema_refs = []
        for key in pattern.semantic_keys:
            if schemas is not None:
                schema_refs.extend(
                    item.record_id
                    for item in schemas.find_candidates(key)
                )
        facts = ()
        if memory is not None and hasattr(memory, "query"):
            predicate = (
                pattern.semantic_keys[0]
                if pattern.semantic_keys else ""
            )
            role_constraints = {
                constraint.role_schema_ref.removeprefix(
                    "role:"
                ): constraint.filler_ref
                for constraint in pattern.referent_constraints
                if (
                    constraint.role_schema_ref
                    and constraint.filler_ref
                    and not constraint.filler_ref.startswith(
                        ("grammar:", "open:")
                    )
                )
            }
            facts = memory.query(FactQuery(
                predicate_key=predicate,
                role_constraints=role_constraints,
                context_refs=(
                    (pattern.context_ref,)
                    if pattern.context_ref else ()
                ),
            ))
        evidence = [
            ref
            for fact in facts
            for ref in fact.evidence_refs
        ]
        if self._truth is not None and pattern.proposition_ref:
            evidence.extend(
                item.evidence_id
                for item in self._truth.get_evidence(
                    pattern.proposition_ref
                )
            )
        empty = not schema_refs and not facts and not evidence
        return RetrievalResult(
            query_pattern_ref=pattern.pattern_id,
            record_refs=tuple(
                dict.fromkeys(schema_refs)
            ),
            evidence_refs=tuple(
                dict.fromkeys(evidence)
            ),
            relation_refs=tuple(
                fact.fact_id for fact in facts
            ),
            records=tuple(facts),
            confidence=(
                0.0 if empty
                else min(
                    1.0,
                    0.4 + 0.1 * (
                        len(facts) + len(schema_refs)
                    ),
                )
            ),
            is_empty=empty,
        )
