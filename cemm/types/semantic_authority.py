from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class AuthorityState(str, Enum):
    """Canonical authority states for semantic artifacts.

    Progression:
        observed -> candidate -> selected -> scoped -> validated -> authorized -> executed -> committed

    Terminal states (no further progression):
        unresolved, suppressed, quarantined, contradicted, rejected, retired
    """
    OBSERVED = "observed"
    CANDIDATE = "candidate"
    SELECTED = "selected"
    SCOPED = "scoped"
    VALIDATED = "validated"
    AUTHORIZED = "authorized"
    EXECUTED = "executed"
    COMMITTED = "committed"

    # Terminal states
    UNRESOLVED = "unresolved"
    SUPPRESSED = "suppressed"
    QUARANTINED = "quarantined"
    CONTRADICTED = "contradicted"
    REJECTED = "rejected"
    RETIRED = "retired"

    def is_terminal(self) -> bool:
        return self in {
            AuthorityState.UNRESOLVED,
            AuthorityState.SUPPRESSED,
            AuthorityState.QUARANTINED,
            AuthorityState.CONTRADICTED,
            AuthorityState.REJECTED,
            AuthorityState.RETIRED,
            AuthorityState.COMMITTED,
        }

    def can_transition_to(self, target: "AuthorityState") -> bool:
        """Check if transition from self to target is valid."""
        if self.is_terminal():
            return False

        progression = [
            AuthorityState.OBSERVED,
            AuthorityState.CANDIDATE,
            AuthorityState.SELECTED,
            AuthorityState.SCOPED,
            AuthorityState.VALIDATED,
            AuthorityState.AUTHORIZED,
            AuthorityState.EXECUTED,
            AuthorityState.COMMITTED,
        ]

        terminals = [
            AuthorityState.UNRESOLVED,
            AuthorityState.SUPPRESSED,
            AuthorityState.QUARANTINED,
            AuthorityState.CONTRADICTED,
            AuthorityState.REJECTED,
            AuthorityState.RETIRED,
        ]

        if self == target:
            return True

        # Can advance one step in progression
        if self in progression and target in progression:
            self_idx = progression.index(self)
            target_idx = progression.index(target)
            return target_idx == self_idx + 1

        # Can transition to any terminal state at any time
        if target in terminals:
            return True

        # Can skip from observed to UNRESOLVED
        if self == AuthorityState.OBSERVED and target == AuthorityState.UNRESOLVED:
            return True

        return False


@dataclass(frozen=True, slots=True)
class AuthorityTransition:
    """A recorded authority state transition with reason."""
    artifact_ref: str  # semantic ref string
    from_state: AuthorityState
    to_state: AuthorityState
    reason: str = ""
    provenance_ref: str = ""

    def is_valid(self) -> bool:
        return self.from_state.can_transition_to(self.to_state)

    def __post_init__(self) -> None:
        if not self.is_valid():
            raise ValueError(
                f"Invalid authority transition: {self.from_state.value} -> {self.to_state.value}"
            )


@dataclass(frozen=True, slots=True)
class AuthorityRecord:
    """Tracks the authority state of a semantic artifact."""
    artifact_ref: str
    current_state: AuthorityState = AuthorityState.OBSERVED
    transitions: tuple[AuthorityTransition, ...] = ()

    def transition_to(self, target: AuthorityState, reason: str = "", provenance_ref: str = "") -> "AuthorityRecord":
        if not self.current_state.can_transition_to(target):
            raise ValueError(
                f"Cannot transition from {self.current_state.value} to {target.value}"
            )
        transition = AuthorityTransition(
            artifact_ref=self.artifact_ref,
            from_state=self.current_state,
            to_state=target,
            reason=reason,
            provenance_ref=provenance_ref,
        )
        return AuthorityRecord(
            artifact_ref=self.artifact_ref,
            current_state=target,
            transitions=self.transitions + (transition,),
        )
