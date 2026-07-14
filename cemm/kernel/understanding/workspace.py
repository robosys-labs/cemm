"""WorkspaceController — bounded global semantic workspace (v3.4).

Selects a bounded active set using relevance, novelty, uncertainty,
urgency, goal impact, causal consequence, and discourse obligation.

Import boundary: model + understanding submodules only. No engine imports.

Architectural guardrails (CORE_LOOP.md §C5, AUTHORITY_MATRIX):
- Selects a bounded active set from workspace entries.
- Integration is non-persistent.
- May NOT change truth, select response wording, or produce effects.

Authority: (workspace focus — no sole-authority key, but CORE_LOOP assigns
WorkspaceController as the authority for workspace snapshot)
Must not decide it: truth change, response selection
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..model.workspace import WorkspaceEntry


@dataclass(frozen=True, slots=True)
class WorkspaceSnapshot:
    """A snapshot of the bounded active workspace."""
    entries: tuple[WorkspaceEntry, ...] = ()
    bounded_size: int = 0
    focus_weights: dict[str, float] = field(default_factory=dict)

    @property
    def active_refs(self) -> tuple[str, ...]:
        return tuple(e.item_ref for e in self.entries)

    @property
    def is_empty(self) -> bool:
        return len(self.entries) == 0


class WorkspaceController:
    """Sole authority for workspace focus selection (v3.4).

    Selects a bounded active set using relevance, novelty, uncertainty,
    urgency, goal impact, causal consequence, and discourse obligation.

    Does NOT:
    - Change truth values
    - Select response wording
    - Produce effects or mutations
    - Persist state
    """

    def __init__(self, max_entries: int = 32) -> None:
        self._max_entries = max_entries

    def focus(
        self,
        selected_interpretations: list[Any] | None = None,
        epistemic_assessments: list[Any] | None = None,
        gaps: list[Any] | None = None,
        goal_refs: tuple[str, ...] = (),
        budget: int | None = None,
    ) -> WorkspaceSnapshot:
        """Select a bounded active set from the cycle's semantic artifacts.

        Uses relevance, novelty, uncertainty, urgency, goal impact,
        causal consequence, and discourse obligation to rank entries.
        """
        entries: list[WorkspaceEntry] = []
        max_size = budget or self._max_entries

        # Add selected interpretations to workspace
        if selected_interpretations:
            for interp in selected_interpretations:
                confidence = getattr(interp, "confidence", 0.5)
                is_opaque = getattr(interp, "is_opaque", False)
                is_provisional = getattr(interp, "is_provisional", False)

                # Uncertainty is higher for opaque/provisional
                uncertainty = 0.8 if is_opaque else (0.5 if is_provisional else 0.2)

                # Relevance is based on confidence
                relevance = min(1.0, confidence)

                # Novelty is higher for new propositions
                novelty = 0.5

                # Goal impact
                goal_impact = 0.5
                if goal_refs:
                    goal_impact = 0.7

                entries.append(WorkspaceEntry(
                    item_ref=getattr(interp, "proposition_ref", "") or getattr(interp, "id", ""),
                    item_kind="interpretation",
                    relevance=relevance,
                    novelty=novelty,
                    uncertainty=uncertainty,
                    urgency=0.3,
                    goal_impact=goal_impact,
                    protected_by_goal_refs=goal_refs,
                ))

        # Add epistemic assessments
        if epistemic_assessments:
            for ea in epistemic_assessments:
                prop_ref = getattr(ea, "proposition_ref", "")
                if not prop_ref:
                    continue
                admissibility = getattr(ea, "admissibility", "blocked")
                if admissibility == "blocked":
                    continue
                confidence = getattr(ea, "confidence", 0.0)
                entries.append(WorkspaceEntry(
                    item_ref=prop_ref,
                    item_kind="epistemic_assessment",
                    relevance=min(1.0, confidence),
                    novelty=0.3,
                    uncertainty=1.0 - confidence,
                    urgency=0.2,
                ))

        # Add gaps (high urgency)
        if gaps:
            for gap in gaps:
                gap_id = getattr(gap, "id", "")
                if not gap_id:
                    continue
                learnable = getattr(gap, "learnable", False)
                entries.append(WorkspaceEntry(
                    item_ref=gap_id,
                    item_kind="gap",
                    relevance=0.8,
                    novelty=0.9,
                    uncertainty=1.0,
                    urgency=0.9 if learnable else 0.5,
                    goal_impact=0.7,
                ))

        # Sort by composite score and bound
        def composite_score(e: WorkspaceEntry) -> float:
            return (
                e.relevance * 0.25
                + e.novelty * 0.15
                + e.uncertainty * 0.15
                + e.urgency * 0.20
                + e.goal_impact * 0.20
                + e.causal_consequence * 0.05
            )

        entries.sort(key=composite_score, reverse=True)
        bounded = entries[:max_size]

        # Compute focus weights
        weights: dict[str, float] = {}
        total = sum(composite_score(e) for e in bounded)
        if total > 0:
            for e in bounded:
                weights[e.item_ref] = composite_score(e) / total

        return WorkspaceSnapshot(
            entries=tuple(bounded),
            bounded_size=len(bounded),
            focus_weights=weights,
        )
