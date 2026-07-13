"""GroundingFrontier — smallest blocking frontier over typed dependencies.

Import boundary: model + schema submodules only. No engine imports.

Architectural guardrails (LEARNING_PIPELINE.md §5):
- The transaction computes the smallest blocking frontier over typed
  dependencies.
- Priority:
    active goal blocker
    required semantic family/role/value
    constitutive structure
    independent discrimination
    differentiator
    context/time applicability
    enrichment
- Budgets include: max dependency depth, max open gaps, max probes,
  max hypothesis branches, max schema size, max competence cost,
  max replay work, user-burden/repeated-question limit
- Asked probe keys are persisted. Budget exhaustion leaves exact typed
  gaps and a resumable transaction. It does not mark failure, repeat
  the same question, or fabricate closure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..model.gap import LearningBudget, GapRecord


class FrontierPriority(int, Enum):
    """Priority ordering for grounding frontier items."""
    ACTIVE_GOAL_BLOCKER = 0
    REQUIRED_FAMILY_ROLE_VALUE = 1
    CONSTITUTIVE_STRUCTURE = 2
    INDEPENDENT_DISCRIMINATION = 3
    DIFFERENTIATOR = 4
    CONTEXT_TIME_APPLICABILITY = 5
    ENRICHMENT = 6


@dataclass(frozen=True, slots=True)
class FrontierItem:
    """A single item in the grounding frontier.

    Represents a typed dependency that blocks schema grounding.
    """
    item_id: str
    dependency_ref: str  # Ref to typed dependency
    blocker_kind: str  # missing_semantic_family, missing_required_role, etc.
    priority: FrontierPriority = FrontierPriority.ENRICHMENT
    is_blocking: bool = True
    probe_key: str = ""  # Idempotency key for probing this item
    estimated_probe_cost: int = 1
    target_schema_ref: str = ""
    target_field: str = ""


@dataclass(frozen=True, slots=True)
class GroundingFrontier:
    """The smallest blocking frontier over typed dependencies.

    The frontier is the minimal set of blockers that must be resolved
    for the schema to achieve structural executability.
    """
    items: tuple[FrontierItem, ...] = ()
    budget: LearningBudget = field(default_factory=LearningBudget)
    asked_probe_keys: frozenset[str] = field(default_factory=frozenset)

    def blocking_items(self) -> tuple[FrontierItem, ...]:
        """Get only blocking items, sorted by priority."""
        blockers = [item for item in self.items if item.is_blocking]
        blockers.sort(key=lambda x: x.priority)
        return tuple(blockers)

    def unasked_blocking_items(self) -> tuple[FrontierItem, ...]:
        """Get blocking items that haven't been probed yet."""
        return tuple(
            item for item in self.blocking_items()
            if item.probe_key not in self.asked_probe_keys
        )

    def is_exhausted(self) -> bool:
        """Check if probe budget is exhausted or all items have been asked."""
        if self.budget.probes_remaining <= 0:
            return True
        # Also exhausted if no unasked blocking items remain
        return len(self.unasked_blocking_items()) == 0

    def is_resumable(self) -> bool:
        """Check if the frontier is resumable (has unasked items and budget can be replenished)."""
        return len(self.unasked_blocking_items()) > 0

    def next_probe_targets(self) -> tuple[FrontierItem, ...]:
        """Get the next items to probe, respecting budget.

        Budget exhaustion leaves exact typed gaps and a resumable
        transaction. It does not mark failure.
        """
        unasked = self.unasked_blocking_items()
        if not unasked or self.is_exhausted():
            return ()

        # Take as many as budget allows
        affordable: list[FrontierItem] = []
        remaining = self.budget.probes_remaining
        for item in unasked:
            if remaining <= 0:
                break
            affordable.append(item)
            remaining -= item.estimated_probe_cost

        return tuple(affordable)

    def remaining_gaps(self) -> tuple[str, ...]:
        """Get the gap kinds for unasked blocking items.

        These are the exact typed gaps that remain.
        """
        return tuple(item.blocker_kind for item in self.unasked_blocking_items())


class GroundingFrontierBuilder:
    """Builds the grounding frontier from blockers.

    Computes the smallest blocking frontier over typed dependencies.
    """

    def build(
        self,
        blockers: tuple[FrontierItem, ...] = (),
        budget: LearningBudget | None = None,
        asked_probe_keys: frozenset[str] | None = None,
    ) -> GroundingFrontier:
        """Build a grounding frontier from blocker items.

        The frontier is the minimal set of blockers — only items that
        are actually blocking and haven't been resolved.
        """
        if budget is None:
            budget = LearningBudget()
        if asked_probe_keys is None:
            asked_probe_keys = frozenset()

        # Filter to only blocking items
        blocking = tuple(item for item in blockers if item.is_blocking)

        # Sort by priority (smallest blocking frontier = highest priority first)
        sorted_blockers = sorted(blocking, key=lambda x: x.priority)

        return GroundingFrontier(
            items=tuple(sorted_blockers),
            budget=budget,
            asked_probe_keys=asked_probe_keys,
        )

    def classify_blocker(
        self,
        blocker_kind: str,
    ) -> FrontierPriority:
        """Classify a blocker kind into priority.

        Maps blocker vocabulary from UNDERSTANDING_PIPELINE.md §13
        to frontier priority.
        """
        priority_map = {
            "missing_semantic_family": FrontierPriority.REQUIRED_FAMILY_ROLE_VALUE,
            "missing_definition_field": FrontierPriority.REQUIRED_FAMILY_ROLE_VALUE,
            "missing_required_role": FrontierPriority.REQUIRED_FAMILY_ROLE_VALUE,
            "missing_value_type": FrontierPriority.REQUIRED_FAMILY_ROLE_VALUE,
            "missing_constitutive_pattern": FrontierPriority.CONSTITUTIVE_STRUCTURE,
            "missing_differentiator": FrontierPriority.DIFFERENTIATOR,
            "ungrounded_dependency": FrontierPriority.CONSTITUTIVE_STRUCTURE,
            "unsupported_recursive_cycle": FrontierPriority.CONSTITUTIVE_STRUCTURE,
            "missing_independent_competence": FrontierPriority.INDEPENDENT_DISCRIMINATION,
            "actual_context_not_admitted": FrontierPriority.CONTEXT_TIME_APPLICABILITY,
            "expressiveness_blocker": FrontierPriority.ENRICHMENT,
            "sense_individuation_pending": FrontierPriority.INDEPENDENT_DISCRIMINATION,
            "stale_assessment": FrontierPriority.CONTEXT_TIME_APPLICABILITY,
        }
        return priority_map.get(blocker_kind, FrontierPriority.ENRICHMENT)
