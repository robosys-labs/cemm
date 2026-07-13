"""CommonGroundManager — tracks actual dispatched communication.

Import boundary: model submodules only. No engine imports.

Architectural guardrails (AGENTS.md §13, §20, CORE_LOOP.md H,
AUTHORITY_MATRIX):
- CommonGroundManager tracks who asserted, asked, accepted, rejected,
  corrected, promised, answered, or left unresolved which proposition.
- It records actual dispatched communication, not intended text.
- Output common-ground mutation occurs only after dispatch success.
- CommonGroundManager operates through output commit.
- Intended text is not added to common ground.
- Pending question/commitment is not created as if emitted.
- CommonGroundManager via commit — discourse mutations only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DiscourseStatus(str, Enum):
    """Status of a proposition in common ground."""
    ASSERTED = "asserted"
    ASKED = "asked"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CORRECTED = "corrected"
    PROMISED = "promised"
    ANSWERED = "answered"
    UNRESOLVED = "unresolved"


class DispatchStatus(str, Enum):
    """Status of a dispatch attempt."""
    PENDING = "pending"
    DISPATCHED = "dispatched"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class CommonGroundEntry:
    """An entry in common ground.

    CommonGroundManager tracks who asserted, asked, accepted, rejected,
    corrected, promised, answered, or left unresolved which proposition.
    It records actual dispatched communication, not intended text.
    """
    entry_id: str
    proposition_ref: str
    participant_ref: str
    discourse_status: DiscourseStatus
    dispatch_status: DispatchStatus
    dispatched_at: str = ""  # ISO timestamp, empty if not dispatched
    message_plan_ref: str = ""
    corrects_entry_id: str = ""  # If this entry corrects a prior entry


@dataclass(frozen=True, slots=True)
class DispatchResult:
    """Result of a dispatch attempt."""
    message_plan_ref: str
    status: DispatchStatus
    transport_outcome: str = ""
    dispatched_at: str = ""


class CommonGroundManager:
    """Tracks actual dispatched communication.

    CommonGroundManager tracks who asserted, asked, accepted, rejected,
    corrected, promised, answered, or left unresolved which proposition.
    It records actual dispatched communication, not intended text.

    Output common-ground mutation occurs only after dispatch success.

    Does NOT:
    - Record intended (non-dispatched) text
    - Create pending obligations for non-emitted content
    - Decide response content
    - Mutate without commit
    """

    def __init__(self) -> None:
        self._entries: dict[str, CommonGroundEntry] = {}
        self._by_proposition: dict[str, list[str]] = {}
        self._by_participant: dict[str, list[str]] = {}

    def record_dispatch(
        self,
        proposition_ref: str,
        participant_ref: str,
        discourse_status: DiscourseStatus,
        dispatch_result: DispatchResult,
        corrects_entry_id: str = "",
    ) -> CommonGroundEntry:
        """Record a dispatched communication in common ground.

        Output common-ground mutation occurs only after dispatch success.
        This method should only be called after successful dispatch.
        """
        if dispatch_result.status != DispatchStatus.DISPATCHED:
            # Do not record non-dispatched communication
            raise ValueError(
                "CommonGroundManager records only dispatched communication, "
                f"not {dispatch_result.status.value}"
            )

        entry_id = f"cg:{proposition_ref}:{participant_ref}:{dispatch_result.dispatched_at}"

        entry = CommonGroundEntry(
            entry_id=entry_id,
            proposition_ref=proposition_ref,
            participant_ref=participant_ref,
            discourse_status=discourse_status,
            dispatch_status=DispatchStatus.DISPATCHED,
            dispatched_at=dispatch_result.dispatched_at,
            message_plan_ref=dispatch_result.message_plan_ref,
            corrects_entry_id=corrects_entry_id,
        )

        self._entries[entry_id] = entry
        self._by_proposition.setdefault(proposition_ref, []).append(entry_id)
        self._by_participant.setdefault(participant_ref, []).append(entry_id)

        # If correcting a prior entry, mark it as corrected
        if corrects_entry_id and corrects_entry_id in self._entries:
            from dataclasses import replace
            old = self._entries[corrects_entry_id]
            self._entries[corrects_entry_id] = replace(
                old, discourse_status=DiscourseStatus.CORRECTED
            )

        return entry

    def get_entries_for_proposition(
        self,
        proposition_ref: str,
    ) -> tuple[CommonGroundEntry, ...]:
        """Get all common ground entries for a proposition."""
        ids = self._by_proposition.get(proposition_ref, [])
        return tuple(self._entries[eid] for eid in ids if eid in self._entries)

    def get_entries_for_participant(
        self,
        participant_ref: str,
    ) -> tuple[CommonGroundEntry, ...]:
        """Get all common ground entries for a participant."""
        ids = self._by_participant.get(participant_ref, [])
        return tuple(self._entries[eid] for eid in ids if eid in self._entries)

    def get_unresolved(self) -> tuple[CommonGroundEntry, ...]:
        """Get all unresolved propositions in common ground."""
        return tuple(
            e for e in self._entries.values()
            if e.discourse_status == DiscourseStatus.UNRESOLVED
        )

    def get_open_questions(self) -> tuple[CommonGroundEntry, ...]:
        """Get all open questions (asked but not answered)."""
        asked = {
            e.proposition_ref for e in self._entries.values()
            if e.discourse_status == DiscourseStatus.ASKED
        }
        answered = {
            e.proposition_ref for e in self._entries.values()
            if e.discourse_status == DiscourseStatus.ANSWERED
        }
        open_props = asked - answered
        return tuple(
            e for e in self._entries.values()
            if e.proposition_ref in open_props
        )

    def is_dispatched(self, proposition_ref: str) -> bool:
        """Check if a proposition has been dispatched."""
        entries = self.get_entries_for_proposition(proposition_ref)
        return any(
            e.dispatch_status == DispatchStatus.DISPATCHED for e in entries
        )

    def try_record_intended(
        self,
        proposition_ref: str,
        participant_ref: str,
        discourse_status: DiscourseStatus,
    ) -> bool:
        """Try to record intended (non-dispatched) communication.

        This should ALWAYS fail — CommonGroundManager records only
        actual dispatched communication, not intended text.
        """
        # Intended text is not added to common ground
        return False


class RepairObligationGenerator:
    """Generates repair obligations from invalidated prior output.

    Invalidated prior output can generate a repair obligation.
    Historical dispatched output remains an event and may generate a
    repair obligation.

    Qualified language for stale/repaired prior claims.
    """

    def __init__(self) -> None:
        self._repair_obligations: list[RepairObligation] = []

    def generate_from_invalidation(
        self,
        invalidated_message_ref: str,
        reason: str = "",
        original_proposition_ref: str = "",
    ) -> RepairObligation:
        """Generate a repair obligation from invalidated prior output.

        Invalidated prior output can generate a repair obligation.
        """
        obligation = RepairObligation(
            obligation_id=f"repair:{invalidated_message_ref}",
            invalidated_message_ref=invalidated_message_ref,
            original_proposition_ref=original_proposition_ref,
            reason=reason,
        )
        self._repair_obligations.append(obligation)
        return obligation

    def get_pending_repairs(self) -> tuple[RepairObligation, ...]:
        """Get all pending repair obligations."""
        return tuple(o for o in self._repair_obligations if not o.is_fulfilled)

    def fulfill(self, obligation_id: str) -> bool:
        """Mark a repair obligation as fulfilled."""
        for o in self._repair_obligations:
            if o.obligation_id == obligation_id:
                from dataclasses import replace
                self._repair_obligations.remove(o)
                self._repair_obligations.append(
                    replace(o, is_fulfilled=True)
                )
                return True
        return False


@dataclass(frozen=True, slots=True)
class RepairObligation:
    """A repair obligation from invalidated prior output.

    Invalidated prior output can generate a repair obligation.
    """
    obligation_id: str
    invalidated_message_ref: str
    original_proposition_ref: str = ""
    reason: str = ""
    is_fulfilled: bool = False
