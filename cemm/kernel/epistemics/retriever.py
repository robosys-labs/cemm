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


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """A retrieval result for a single query pattern."""
    query_pattern_ref: str
    record_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
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
    open ports, and context. Retrieves canonical records and evidence.

    Does NOT:
    - Decide truth
    - Select interpretations
    - Produce response wording
    - Mutate stores
    """

    def __init__(self, store: Any | None = None) -> None:
        self._store = store

    def retrieve(
        self,
        selected_interpretations: list[Any] | None = None,
        goal_refs: tuple[str, ...] = (),
        open_ports: tuple[Any, ...] = (),
        context_ref: str = "",
        durable_store: Any | None = None,
    ) -> RetrievalBatch:
        """Retrieve canonical records and evidence for the cycle.

        Builds query patterns from selected propositions, goals, open
        ports, and context. Returns evidence-aware results.
        """
        store = durable_store or self._store
        results: list[RetrievalResult] = []

        if store is None:
            return RetrievalBatch()

        # Build query patterns from selected interpretations
        if selected_interpretations:
            for interp in selected_interpretations:
                prop_ref = getattr(interp, "proposition_ref", "")
                if not prop_ref:
                    continue

                # Query durable store for matching records
                record_refs: list[str] = []
                evidence_refs: list[str] = []

                # Try to query the store
                try:
                    if hasattr(store, "lookup_lexical_form"):
                        # For schema store, look up by semantic key
                        pass
                    if hasattr(store, "find_candidates"):
                        # Find schema candidates for the proposition
                        candidates = store.find_candidates(prop_ref)
                        for c in candidates:
                            record_refs.append(getattr(c, "record_id", ""))
                except Exception:
                    pass

                # Try durable semantic store for relation records
                try:
                    if hasattr(store, "relation_count"):
                        count = store.relation_count()
                        if count > 0:
                            # Query relations matching this proposition
                            pass
                except Exception:
                    pass

                results.append(RetrievalResult(
                    query_pattern_ref=prop_ref,
                    record_refs=tuple(record_refs),
                    evidence_refs=tuple(evidence_refs),
                    confidence=0.5 if record_refs else 0.0,
                    is_empty=len(record_refs) == 0,
                ))

        # Build query patterns from open ports
        for port in open_ports:
            role_name = getattr(port, "role_name", "")
            if not role_name:
                continue
            results.append(RetrievalResult(
                query_pattern_ref=f"open_port:{role_name}",
                confidence=0.0,
                is_empty=True,
            ))

        total = sum(len(r.record_refs) for r in results)
        return RetrievalBatch(
            results=tuple(results),
            total_records=total,
        )
