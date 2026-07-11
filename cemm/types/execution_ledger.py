"""ExecutionLedger — transactional record of one turn's contract execution.

Every contract operation is recorded as a ledger entry with status
transitions: proposed → authorized → executing → succeeded/failed →
committed/rolled_back. No partial failure may leave a durable artifact
or session binding in an untracked state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class LedgerEntryStatus(str, Enum):
    PROPOSED = "proposed"
    AUTHORIZED = "authorized"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"


LEDGER_ENTRY_TYPES = frozenset({
    "query",
    "write",
    "state",
    "reaction",
    "safety",
    "learning",
    "action",
    "response",
})


@dataclass
class ExecutionLedgerEntry:
    """One recorded operation in the execution ledger."""
    operation_id: str
    operation_type: str
    node_id: str = ""
    contract_id: str = ""
    status: str = LedgerEntryStatus.PROPOSED.value

    source_frame_id: str = ""
    source_branch_id: str = ""
    source_episode_id: str = ""
    source_gap_ids: tuple[str, ...] = ()

    error: str = ""
    result: Any = None
    started_at: float = 0.0
    completed_at: float = 0.0

    def transition(self, new_status: str) -> None:
        if new_status not in LedgerEntryStatus.__members__.values():
            raise ValueError(f"invalid status: {new_status}")
        self.status = new_status


@dataclass
class ExecutionLedger:
    """Transactional record of execution for one turn.

    If any entry has status FAILED or ROLLED_BACK after execution,
    is_consistent is False and no durable effects from this turn
    should be considered committed.
    """
    turn_id: str = ""
    session_id: str = ""
    entries: list[ExecutionLedgerEntry] = field(default_factory=list)
    is_consistent: bool = True

    def add_entry(self, entry: ExecutionLedgerEntry) -> None:
        self.entries.append(entry)

    def entry_by_id(self, operation_id: str) -> ExecutionLedgerEntry | None:
        for e in self.entries:
            if e.operation_id == operation_id:
                return e
        return None

    def entries_by_type(self, op_type: str) -> list[ExecutionLedgerEntry]:
        return [e for e in self.entries if e.operation_type == op_type]

    def succeeded(self) -> list[ExecutionLedgerEntry]:
        return [e for e in self.entries if e.status == LedgerEntryStatus.SUCCEEDED.value]

    def failed(self) -> list[ExecutionLedgerEntry]:
        return [
            e for e in self.entries
            if e.status in (LedgerEntryStatus.FAILED.value, LedgerEntryStatus.ROLLED_BACK.value)
        ]

    @property
    def has_failures(self) -> bool:
        return bool(self.failed())

    def mark_inconsistent(self) -> None:
        self.is_consistent = False
