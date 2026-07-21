"""Canonical persisted-identity and idempotency primitives for CEMM v3.5.1."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .storage.codec import record_fingerprints, record_ref
from .storage.model import RecordKind, StoredRecord


class IdempotencyOutcome(str, Enum):
    """Typed result of comparing a deterministic durable identity."""

    ABSENT = "absent"
    EQUIVALENT = "equivalent"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True)
class CanonicalPersistedIdentity:
    record_kind: RecordKind
    record_ref: str
    revision: int
    content_fingerprint: str
    record_fingerprint: str

    @property
    def key(self) -> tuple[str, str, int, str]:
        return (
            self.record_kind.value,
            self.record_ref,
            self.revision,
            self.record_fingerprint,
        )


@dataclass(frozen=True, slots=True)
class IdempotencyAssessment:
    outcome: IdempotencyOutcome
    expected: CanonicalPersistedIdentity
    observed_fingerprint: str | None = None

    @property
    def equivalent(self) -> bool:
        return self.outcome is IdempotencyOutcome.EQUIVALENT


def canonical_persisted_identity(
    record_kind: RecordKind,
    record: Any,
    *,
    revision: int = 1,
) -> CanonicalPersistedIdentity:
    if revision < 1:
        raise ValueError("persisted identity revision must be positive")
    content_fingerprint, complete_fingerprint = record_fingerprints(
        record_kind, record
    )
    return CanonicalPersistedIdentity(
        record_kind=record_kind,
        record_ref=record_ref(record_kind, record),
        revision=revision,
        content_fingerprint=content_fingerprint,
        record_fingerprint=complete_fingerprint,
    )


def classify_persisted_identity(
    existing: StoredRecord[Any] | None,
    record_kind: RecordKind,
    record: Any,
    *,
    revision: int = 1,
) -> IdempotencyAssessment:
    """Compare canonical durable identity without raw Python object equality."""

    expected = canonical_persisted_identity(
        record_kind, record, revision=revision
    )
    if existing is None:
        return IdempotencyAssessment(IdempotencyOutcome.ABSENT, expected)

    equivalent = (
        existing.record_kind == expected.record_kind
        and existing.record_ref == expected.record_ref
        and existing.revision == expected.revision
        and existing.record_fingerprint == expected.record_fingerprint
    )
    return IdempotencyAssessment(
        IdempotencyOutcome.EQUIVALENT
        if equivalent
        else IdempotencyOutcome.CONFLICT,
        expected,
        observed_fingerprint=existing.record_fingerprint,
    )


def require_equivalent_or_absent(
    existing: StoredRecord[Any] | None,
    record_kind: RecordKind,
    record: Any,
    *,
    revision: int = 1,
    label: str = "persisted identity",
) -> IdempotencyAssessment:
    assessment = classify_persisted_identity(
        existing, record_kind, record, revision=revision
    )
    if assessment.outcome is IdempotencyOutcome.CONFLICT:
        raise RuntimeError(
            f"{label} collision:{assessment.expected.record_kind.value}:"
            f"{assessment.expected.record_ref}@{assessment.expected.revision}:"
            f"expected={assessment.expected.record_fingerprint}:"
            f"observed={assessment.observed_fingerprint}"
        )
    return assessment


__all__ = [
    "CanonicalPersistedIdentity",
    "IdempotencyAssessment",
    "IdempotencyOutcome",
    "canonical_persisted_identity",
    "classify_persisted_identity",
    "require_equivalent_or_absent",
]
