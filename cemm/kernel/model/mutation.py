"""MutationSet and CommitOutcome — the only persistent-mutation authority records.

Import boundary: standard library only → refs, identity, execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .identity import SemanticIdentity, Permission
from .execution import TypedFailure


@dataclass(frozen=True, slots=True)
class MutationOperation:
    """A single mutation operation in a mutation set.

    action: create, update, supersede, append, reject
    """
    id: str
    operation_kind: str = "write"
    semantic_identity: SemanticIdentity | None = None
    action: str = "create"  # create, update, supersede, append, reject
    payload_ref: str = ""
    required: bool = True
    expected_revision: int | None = None
    evidence_refs: tuple[str, ...] = ()
    permission: Permission = field(default_factory=Permission.public)
    reason: str = ""


@dataclass(frozen=True, slots=True)
class MutationSet:
    """A set of mutation operations to be committed atomically.

    phase: critical, output, consolidation
    """
    id: str
    phase: str = "critical"  # critical | output | consolidation
    operations: tuple[MutationOperation, ...] = ()


@dataclass(frozen=True, slots=True)
class CommitOperationResult:
    """Result of committing a single mutation operation."""
    mutation_ref: str  # Ref[MutationOperation]
    status: str = "committed"  # committed, failed, skipped
    record_refs: tuple[str, ...] = ()
    failure: TypedFailure | None = None


@dataclass(frozen=True, slots=True)
class CommitOutcome:
    """Outcome of committing a mutation set.

    Completion claims require exact required commits — if any required
    operation fails, the response must not claim success.
    """
    mutation_set_ref: str  # Ref[MutationSet]
    results: tuple[CommitOperationResult, ...] = ()
    required_satisfied: bool = False
    committed_revision: int | None = None
