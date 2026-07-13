"""Schema versioning and revision retention policy.

Import boundary: standard library only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SchemaStatus(str, Enum):
    CANDIDATE = "candidate"
    PROVISIONAL = "provisional"
    ACTIVE = "active"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class RevisionEntry:
    """An entry in the schema revision history.

    A proposition bound to a schema revision keeps that revision
    reachable. Garbage collection may compact indexes but may not
    remove revision content needed to interpret historical propositions
    or replay results.
    """
    record_id: str
    semantic_key: str
    version: int
    status: SchemaStatus = SchemaStatus.CANDIDATE
    supersedes_refs: tuple[str, ...] = ()
    retained_for_proposition_refs: tuple[str, ...] = ()
    retained_for_replay_refs: tuple[str, ...] = ()
    compacted: bool = False


def is_retention_required(
    entry: RevisionEntry,
    bound_proposition_refs: frozenset[str],
    bound_replay_refs: frozenset[str],
) -> bool:
    """Check if a revision must be retained.

    Revisions bound to historical propositions or replay results
    must remain reachable.
    """
    if entry.status == SchemaStatus.ACTIVE:
        return True
    if any(ref in bound_proposition_refs for ref in entry.retained_for_proposition_refs):
        return True
    if any(ref in bound_replay_refs for ref in entry.retained_for_replay_refs):
        return True
    return False
