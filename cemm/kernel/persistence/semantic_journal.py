"""Revisioned semantic-state journal with atomic append transactions."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from threading import RLock
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class JournalEntry:
    entry_id: str
    entry_kind: str
    semantic_identity: str
    payload: dict[str, Any]
    evidence_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    context_ref: str
    valid_time_ref: str = ""
    idempotency_key: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass(frozen=True, slots=True)
class JournalCommit:
    commit_id: str
    base_revision: int
    committed_revision: int
    entry_refs: tuple[str, ...]
    required_entry_refs: tuple[str, ...]
    required_satisfied: bool
    fingerprint: str


class SemanticJournal:
    def __init__(self) -> None:
        self._entries: dict[str, JournalEntry] = {}
        self._identity_index: dict[str, tuple[str, ...]] = {}
        self._idempotency_index: dict[str, str] = {}
        self._revision = 0
        self._lock = RLock()
        self._transaction_snapshot = None

    @property
    def revision(self) -> int:
        return self._revision

    def append(
        self,
        entries: Iterable[JournalEntry],
        *,
        expected_revision: int,
        required_entry_refs: tuple[str, ...] = (),
    ) -> JournalCommit:
        with self._lock:
            if expected_revision != self._revision:
                raise RuntimeError(
                    f"optimistic_lock_failed:{expected_revision}!={self._revision}"
                )
            entry_refs: list[str] = []
            with self.transaction():
                for entry in entries:
                    if not entry.evidence_refs:
                        raise ValueError(f"entry_without_evidence:{entry.entry_id}")
                    if not entry.provenance_refs:
                        raise ValueError(f"entry_without_provenance:{entry.entry_id}")
                    if entry.idempotency_key:
                        existing = self._idempotency_index.get(entry.idempotency_key)
                        if existing:
                            entry_refs.append(existing)
                            continue
                    if entry.entry_id in self._entries:
                        raise ValueError(f"duplicate_entry_id:{entry.entry_id}")
                    self._entries[entry.entry_id] = entry
                    current = self._identity_index.get(entry.semantic_identity, ())
                    self._identity_index[entry.semantic_identity] = (*current, entry.entry_id)
                    if entry.idempotency_key:
                        self._idempotency_index[entry.idempotency_key] = entry.entry_id
                    entry_refs.append(entry.entry_id)
                self._revision += 1

            required = set(required_entry_refs)
            committed = set(entry_refs)
            digest = hashlib.sha256(
                (
                    f"{expected_revision}|{self._revision}|"
                    f"{sorted(entry_refs)}|{sorted(required_entry_refs)}"
                ).encode("utf-8")
            ).hexdigest()
            return JournalCommit(
                commit_id=f"journal_commit:{digest[:16]}",
                base_revision=expected_revision,
                committed_revision=self._revision,
                entry_refs=tuple(entry_refs),
                required_entry_refs=required_entry_refs,
                required_satisfied=required <= committed,
                fingerprint=digest,
            )

    def by_identity(self, semantic_identity: str) -> tuple[JournalEntry, ...]:
        return tuple(
            self._entries[ref]
            for ref in self._identity_index.get(semantic_identity, ())
        )

    def get(self, entry_ref: str) -> JournalEntry | None:
        return self._entries.get(entry_ref)

    def entries(self, entry_kind: str = "") -> tuple[JournalEntry, ...]:
        return tuple(
            entry
            for entry in self._entries.values()
            if not entry_kind or entry.entry_kind == entry_kind
        )

    @contextmanager
    def transaction(self):
        if self._transaction_snapshot is not None:
            yield self
            return
        self._transaction_snapshot = (
            dict(self._entries),
            dict(self._identity_index),
            dict(self._idempotency_index),
            self._revision,
        )
        try:
            yield self
            self._transaction_snapshot = None
        except Exception:
            (
                self._entries,
                self._identity_index,
                self._idempotency_index,
                self._revision,
            ) = self._transaction_snapshot
            self._transaction_snapshot = None
            raise

    def dump(self, path: Path) -> None:
        path.write_text(
            json.dumps(
                [
                    {
                        "entry_id": entry.entry_id,
                        "entry_kind": entry.entry_kind,
                        "semantic_identity": entry.semantic_identity,
                        "payload": entry.payload,
                        "evidence_refs": entry.evidence_refs,
                        "provenance_refs": entry.provenance_refs,
                        "context_ref": entry.context_ref,
                        "valid_time_ref": entry.valid_time_ref,
                        "idempotency_key": entry.idempotency_key,
                        "created_at": entry.created_at,
                    }
                    for entry in self._entries.values()
                ],
                indent=2,
            ),
            encoding="utf-8",
        )
