"""GoalArbiter — sole authority for active goals (v3.4).

Compiles requests, questions, promises, corrections, gaps, policies, and
state constraints into desired propositions/information states. Scores
urgency, controllability, expected value, conflict, progress, cost, and
policy priority. Selects active goals without converting them into
response labels.

Import boundary: model + understanding submodules only. No engine imports.

Architectural guardrails (CORE_LOOP.md §D1-D2, AUTHORITY_MATRIX):
- Goals are desired propositions/information states, not response labels.
- Selects active goals without converting them into response labels.

Authority: active_goals
Must not decide it: instruction-kind composer
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from ..model.goal import GoalRecord


@dataclass(frozen=True, slots=True)
class GoalArbitrationResult:
    """Result of goal arbitration."""
    active_goals: tuple[GoalRecord, ...] = ()
    satisfied_goals: tuple[GoalRecord, ...] = ()
    abandoned_goals: tuple[GoalRecord, ...] = ()
    primary_goal: GoalRecord | None = None
    conflict_pairs: tuple[tuple[str, str], ...] = ()

    @property
    def active_count(self) -> int:
        return len(self.active_goals)


class GoalArbiter:
    """Sole authority for active goals (v3.4).

    Derives needs and obligations from requests, questions, promises,
    corrections, gaps, policies, and state constraints. Appraises and
    arbitrates goals.

    Does NOT:
    - Convert goals into response labels
    - Select response wording
    - Produce effects or mutations
    """

    def derive_and_arbitrate(
        self,
        selected_interpretations: list[Any] | None = None,
        communicative_forces: tuple[Any, ...] = (),
        gaps: list[Any] | None = None,
        capability_assessment: Any | None = None,
        owner_ref: str = "self",
    ) -> GoalArbitrationResult:
        """Derive goals from interpretations and arbitrate among them.

        Compiles requests, questions, promises, corrections, gaps into
        desired propositions. Scores and selects active goals.
        """
        goals: list[GoalRecord] = []

        # Derive goals from communicative forces
        for force in communicative_forces:
            force_kind = getattr(force, "force", "") if not isinstance(force, str) else force
            target = getattr(force, "target_proposition_ref", "") if not isinstance(force, str) else ""

            if force_kind == "ask":
                goals.append(GoalRecord(
                    id=f"goal:{uuid4().hex[:12]}",
                    owner_ref=owner_ref,
                    goal_kind="information_state",
                    priority=0.8,
                    urgency=0.7,
                    success_condition_refs=(target,) if target else (),
                ))
            elif force_kind == "request":
                goals.append(GoalRecord(
                    id=f"goal:{uuid4().hex[:12]}",
                    owner_ref=owner_ref,
                    goal_kind="world_state",
                    priority=0.7,
                    urgency=0.6,
                    success_condition_refs=(target,) if target else (),
                ))
            elif force_kind == "assert":
                goals.append(GoalRecord(
                    id=f"goal:{uuid4().hex[:12]}",
                    owner_ref=owner_ref,
                    goal_kind="discourse",
                    priority=0.5,
                    urgency=0.3,
                    success_condition_refs=(target,) if target else (),
                ))
            elif force_kind == "correct":
                goals.append(GoalRecord(
                    id=f"goal:{uuid4().hex[:12]}",
                    owner_ref=owner_ref,
                    goal_kind="world_state",
                    priority=0.9,
                    urgency=0.8,
                    success_condition_refs=(target,) if target else (),
                ))

        # Derive goals from gaps (learning goals)
        if gaps:
            for gap in gaps:
                learnable = getattr(gap, "learnable", False)
                if not learnable:
                    continue
                gap_id = getattr(gap, "id", "")
                goals.append(GoalRecord(
                    id=f"goal:{uuid4().hex[:12]}",
                    owner_ref=owner_ref,
                    goal_kind="information_state",
                    priority=0.6,
                    urgency=0.5,
                    success_condition_refs=(gap_id,),
                ))

        # Derive goals from selected interpretations
        if selected_interpretations:
            for interp in selected_interpretations:
                is_opaque = getattr(interp, "is_opaque", False)
                if is_opaque:
                    prop_ref = getattr(interp, "proposition_ref", "")
                    goals.append(GoalRecord(
                        id=f"goal:{uuid4().hex[:12]}",
                        owner_ref=owner_ref,
                        goal_kind="information_state",
                        priority=0.4,
                        urgency=0.3,
                        success_condition_refs=(prop_ref,) if prop_ref else (),
                    ))

        # Detect conflicts
        conflicts: list[tuple[str, str]] = []
        for i, g1 in enumerate(goals):
            for g2 in goals[i + 1:]:
                if g1.goal_kind == g2.goal_kind and g1.priority > 0.7 and g2.priority > 0.7:
                    if g1.success_condition_refs and g2.success_condition_refs:
                        if set(g1.success_condition_refs) & set(g2.success_condition_refs):
                            conflicts.append((g1.id, g2.id))

        # Sort by composite priority
        def composite(g: GoalRecord) -> float:
            return g.priority * 0.5 + g.urgency * 0.3 + float(g.policy_priority) * 0.2

        goals.sort(key=composite, reverse=True)

        primary = goals[0] if goals else None

        return GoalArbitrationResult(
            active_goals=tuple(goals),
            primary_goal=primary,
            conflict_pairs=tuple(conflicts),
        )
