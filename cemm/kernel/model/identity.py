"""Identity, scope, provenance, permission, and temporal types.

Import boundary: standard library only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ── Scope ──────────────────────────────────────────────────────────


class ScopeLevel(str, Enum):
    GLOBAL = "global"
    TENANT = "tenant"
    USER = "user"
    SESSION = "session"


@dataclass(frozen=True, slots=True)
class Scope:
    """Access/ownership scope — not truth context."""
    level: ScopeLevel = ScopeLevel.GLOBAL
    owner_id: str | None = None
    session_id: str | None = None

    def is_wider_than(self, other: "Scope") -> bool:
        order = {
            ScopeLevel.GLOBAL: 0,
            ScopeLevel.TENANT: 1,
            ScopeLevel.USER: 2,
            ScopeLevel.SESSION: 3,
        }
        return order[self.level] < order[other.level]


# ── Provenance ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Provenance:
    """Origin record for a semantic artifact."""
    source_id: str
    source_kind: str = "unknown"
    observed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    language_tag: str = "und"
    turn_index: int = 0
    independence_key: str = ""


# ── Permission ─────────────────────────────────────────────────────


class PermissionScope(str, Enum):
    PUBLIC = "public"
    USER_PRIVATE = "user_private"
    SESSION_PRIVATE = "session_private"
    SYSTEM_PRIVATE = "system_private"


class RetentionPolicy(str, Enum):
    EPHEMERAL = "ephemeral"
    SESSION = "session"
    LONG_TERM = "long_term"


@dataclass(frozen=True, slots=True)
class Permission:
    """Access and retention permissions for a record."""
    scope: PermissionScope = PermissionScope.PUBLIC
    may_store: bool = True
    may_retrieve: bool = True
    may_use: bool = True
    may_share: bool = False
    may_execute: bool = False
    retention: RetentionPolicy = RetentionPolicy.LONG_TERM

    @classmethod
    def public(cls) -> "Permission":
        return cls(
            scope=PermissionScope.PUBLIC,
            may_store=True, may_retrieve=True, may_use=True,
            may_share=False, may_execute=True,
            retention=RetentionPolicy.LONG_TERM,
        )

    @classmethod
    def user_private(cls) -> "Permission":
        return cls(
            scope=PermissionScope.USER_PRIVATE,
            may_store=True, may_retrieve=True, may_use=True,
            may_share=False, may_execute=False,
            retention=RetentionPolicy.SESSION,
        )

    @classmethod
    def session_private(cls) -> "Permission":
        return cls(
            scope=PermissionScope.SESSION_PRIVATE,
            may_store=True, may_retrieve=True, may_use=True,
            may_share=False, may_execute=False,
            retention=RetentionPolicy.EPHEMERAL,
        )


# ── TimeExtent ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TimeExtent:
    """Temporal interval or instant."""
    start: datetime | None = None
    end: datetime | None = None
    granularity: str = "instant"  # instant, interval, point_in_time
    calendar: str = "gregorian"

    def is_instant(self) -> bool:
        return self.start is not None and self.end is None

    def contains(self, moment: datetime) -> bool:
        if self.start is not None and moment < self.start:
            return False
        if self.end is not None and moment > self.end:
            return False
        return True


# ── SemanticIdentity ───────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SemanticIdentity:
    """Stable semantic identity for a record (used in mutations)."""
    identity_kind: str  # proposition, state_slot, schema_revision, etc.
    key: str
    qualifiers: tuple[str, ...] = ()


# ── AssessmentEnvironmentFingerprint ───────────────────────────────


@dataclass(frozen=True, slots=True)
class AssessmentEnvironmentFingerprint:
    """Pinned snapshot of the assessment environment.

    A change in any field invalidates all dependent derived cognition.
    """
    schema_store_revision: int
    dependency_revision_hash: str
    grounding_policy_version: str
    competency_suite_hash: str
    kernel_foundation_version: str
    type_registry_version: str
    inference_policy_version: str
    truth_maintenance_version: str
    adapter_contract_hash: str
    context_scope_policy_version: str

    def to_tuple(self) -> tuple[Any, ...]:
        return (
            self.schema_store_revision,
            self.dependency_revision_hash,
            self.grounding_policy_version,
            self.competency_suite_hash,
            self.kernel_foundation_version,
            self.type_registry_version,
            self.inference_policy_version,
            self.truth_maintenance_version,
            self.adapter_contract_hash,
            self.context_scope_policy_version,
        )

    def __hash__(self) -> int:
        return hash(self.to_tuple())
