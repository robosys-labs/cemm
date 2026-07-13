"""Truth maintenance — evidence aggregation, lineage, contradiction, temporal validity.

Import boundary: model + schema submodules only. No engine imports.

Architectural guardrails (AGENTS.md §10, §7.5):
- Four support states: supported, refuted, both, neither
- Absence is not falsity
- Confidence, freshness, accessibility, source trust, and schema
  executability are separate dimensions
- Evidence independence follows derivation lineage, not record count
- A dependency or environment change invalidates all dependent derived
  cognition, including assessments, inferred propositions, cached answers
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from ..model.epistemic import EpistemicAssessment
from ..model.identity import TimeExtent
from .evaluator import (
    EvidenceRecord, SupportState, AdmissibilityLevel,
    EpistemicEvaluator,
)


@dataclass(frozen=True, slots=True)
class LineageNode:
    """A node in the evidence derivation lineage graph."""
    node_id: str
    source_ref: str = ""
    derivation_kind: str = "observed"  # observed, entailed, inferred, translated, paraphrased
    parent_refs: tuple[str, ...] = ()  # parent lineage nodes
    is_independent: bool = False
    independence_key: str = ""  # unique key for independent sources


@dataclass(frozen=True, slots=True)
class LineageGraph:
    """Graph of evidence derivation lineages."""
    nodes: tuple[LineageNode, ...] = ()

    def independent_roots(self) -> frozenset[str]:
        """Get the set of independent root node IDs."""
        roots: set[str] = set()
        for node in self.nodes:
            if node.is_independent and not node.parent_refs:
                roots.add(node.node_id)
        return frozenset(roots)

    def lineage_of(self, node_id: str) -> tuple[str, ...]:
        """Get the full lineage chain for a node (root → node)."""
        node_map = {n.node_id: n for n in self.nodes}
        chain: list[str] = []
        current = node_id
        visited: set[str] = set()
        while current and current not in visited:
            visited.add(current)
            chain.append(current)
            node = node_map.get(current)
            if node is None or not node.parent_refs:
                break
            current = node.parent_refs[0]
        return tuple(reversed(chain))

    def independence_count(self, node_ids: tuple[str, ...]) -> int:
        """Count independent lineage roots among the given nodes.

        Only nodes that are themselves independent roots (is_independent
        and no parents) are counted. Derived nodes (translations, paraphrases)
        inherit their root's lineage and do not add independent evidence.
        """
        roots = self.independent_roots()
        count = 0
        for nid in node_ids:
            if nid in roots:
                count += 1
        return count


@dataclass(frozen=True, slots=True)
class ContradictionRecord:
    """A detected contradiction between propositions."""
    contradiction_id: str
    proposition_a_ref: str
    proposition_b_ref: str
    context_ref: str = ""
    contradiction_kind: str = "direct"  # direct, indirect, contextual
    support_a_score: float = 0.0
    support_b_score: float = 0.0
    resolution: str = "unresolved"  # unresolved, a_wins, b_wins, both_contested


class TruthMaintenance:
    """Truth maintenance system for evidence aggregation and invalidation.

    Tracks:
    - Evidence records per proposition
    - Lineage graphs for independence checking
    - Contradictions between propositions
    - Temporal validity of evidence

    Does NOT:
    - Activate schemas
    - Mutate persistent stores
    - Decide final truth (that's EpistemicEvaluator's job)
    """

    def __init__(self) -> None:
        self._evidence: dict[str, list[EvidenceRecord]] = {}
        self._lineage_graphs: dict[str, LineageGraph] = {}
        self._contradictions: list[ContradictionRecord] = []
        self._invalidated: set[str] = set()

    def add_evidence(self, record: EvidenceRecord) -> None:
        """Add an evidence record for a proposition."""
        self._evidence.setdefault(record.proposition_ref, []).append(record)
        # Adding evidence may invalidate previous assessments
        self._invalidated.add(record.proposition_ref)

    def get_evidence(self, proposition_ref: str) -> tuple[EvidenceRecord, ...]:
        """Get all evidence for a proposition."""
        return tuple(self._evidence.get(proposition_ref, ()))

    def aggregate_support(
        self,
        proposition_ref: str,
    ) -> tuple[float, float, int]:
        """Aggregate support and opposition for a proposition.

        Returns (support_score, opposition_score, independent_count).
        """
        evidence = self.get_evidence(proposition_ref)
        support = 0.0
        opposition = 0.0
        independent = 0

        for ev in evidence:
            if ev.supports:
                support += ev.confidence
                if ev.is_independent:
                    independent += 1
            else:
                opposition += ev.confidence

        return support, opposition, independent

    def detect_contradiction(
        self,
        prop_a_ref: str,
        prop_b_ref: str,
        context_ref: str = "",
    ) -> ContradictionRecord | None:
        """Detect a contradiction between two propositions.

        A contradiction exists when one proposition is supported and
        the other is refuted, or both are supported but mutually exclusive.
        """
        support_a, opposition_a, _ = self.aggregate_support(prop_a_ref)
        support_b, opposition_b, _ = self.aggregate_support(prop_b_ref)

        # Direct contradiction: A supported and B refuted (or vice versa)
        if support_a > 0 and opposition_b > 0:
            return ContradictionRecord(
                contradiction_id=f"contr:{prop_a_ref}:{prop_b_ref}",
                proposition_a_ref=prop_a_ref,
                proposition_b_ref=prop_b_ref,
                context_ref=context_ref,
                contradiction_kind="direct",
                support_a_score=support_a,
                support_b_score=support_b,
            )
        if support_b > 0 and opposition_a > 0:
            return ContradictionRecord(
                contradiction_id=f"contr:{prop_b_ref}:{prop_a_ref}",
                proposition_a_ref=prop_b_ref,
                proposition_b_ref=prop_a_ref,
                context_ref=context_ref,
                contradiction_kind="direct",
                support_a_score=support_b,
                support_b_score=support_a,
            )

        return None

    def check_temporal_validity(
        self,
        evidence: tuple[EvidenceRecord, ...],
        current_time: datetime | None = None,
    ) -> tuple[bool, list[str]]:
        """Check temporal validity of evidence.

        Returns (is_valid, expired_evidence_ids).
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        is_valid = True
        expired: list[str] = []

        for ev in evidence:
            if ev.temporal_validity is not None:
                # Check if evidence is still within valid time
                if ev.temporal_validity.end is not None:
                    if current_time > ev.temporal_validity.end:
                        is_valid = False
                        expired.append(ev.evidence_id)

        return is_valid, expired

    def invalidate(self, proposition_ref: str) -> None:
        """Mark a proposition's assessment as invalidated.

        A dependency or environment change invalidates all dependent
        derived cognition (AGENTS.md §7.5).
        """
        self._invalidated.add(proposition_ref)

    def is_invalidated(self, proposition_ref: str) -> bool:
        """Check if a proposition's assessment is invalidated."""
        return proposition_ref in self._invalidated

    def clear_invalidation(self, proposition_ref: str) -> None:
        """Clear invalidation after reassessment."""
        self._invalidated.discard(proposition_ref)

    def check_lineage_independence(
        self,
        evidence: tuple[EvidenceRecord, ...],
        lineage_graph: LineageGraph | None = None,
    ) -> int:
        """Check how many pieces of evidence have independent lineage.

        Evidence independence follows derivation lineage, not record count
        or source labels. Translations, paraphrases, summaries, generated
        examples, and retrieved copies inherit their root lineage unless
        an independent observation or oracle exists.
        """
        if lineage_graph is None:
            # Without a lineage graph, use the is_independent flag
            return sum(1 for ev in evidence if ev.is_independent)

        # With a lineage graph, count independent roots
        node_ids = tuple(ev.evidence_id for ev in evidence)
        return lineage_graph.independence_count(node_ids)
