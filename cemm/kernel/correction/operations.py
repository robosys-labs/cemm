"""CorrectionOperations — 6 typed correction/retention operations.

Import boundary: model submodules only. No engine, schema, or epistemics imports.

Architectural guardrails (AGENTS.md §7.8, ACCEPTANCE_TESTS.md §38-40,
IMPLEMENTATION_PLAN.md Phase 11):
- The kernel distinguishes:
  1. schema/proposition supersession
  2. source support retraction
  3. permission revocation
  4. archival
  5. user-requested forgetting
  6. privacy deletion
- Each targets exact evidence, proposition, sense, or schema revisions
  and triggers appropriate dependency reassessment.
- Archival is not privacy deletion.
- Provenance history may be retained only where policy permits.
- Removed support stops contributing.
- Dependent cognition re-evaluates.
- Historical meaning remains where policy permits.
- Archival cannot masquerade as privacy deletion.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CorrectionKind(str, Enum):
    """The 6 distinct correction/retention operations.

    Each targets exact evidence, proposition, sense, or schema revisions
    and triggers appropriate dependency reassessment.
    """
    SUPERSESSION = "supersession"                # schema/proposition supersession
    SUPPORT_RETRACTION = "support_retraction"    # source support retraction
    PERMISSION_REVOCATION = "permission_revocation"  # permission revocation
    ARCHIVAL = "archival"                        # archival (reversible)
    FORGETTING = "forgetting"                    # user-requested forgetting
    PRIVACY_DELETION = "privacy_deletion"        # privacy deletion (irreversible)


class CorrectionReversibility(str, Enum):
    """Reversibility of a correction operation."""
    REVERSIBLE = "reversible"        # archival — can be undone
    IRREVERSIBLE = "irreversible"    # privacy deletion — cannot be undone
    CONDITIONAL = "conditional"      # supersession — reversible if journaled


class RetentionPolicy(str, Enum):
    """Retention policy for provenance history."""
    RETAIN = "retain"          # Provenance history retained
    REMOVE = "remove"          # Provenance history removed
    CRYPTO_ERASE = "crypto_erase"  # Cryptographically erased


@dataclass(frozen=True, slots=True)
class CorrectionOperation:
    """A typed correction/retention operation.

    Each targets exact evidence, proposition, sense, or schema revisions
    and triggers appropriate dependency reassessment.
    """
    operation_id: str
    kind: CorrectionKind
    target_ref: str  # exact evidence/proposition/sense/schema revision ref
    target_kind: str  # "evidence", "proposition", "sense", "schema_revision"
    reason: str = ""
    reversibility: CorrectionReversibility = CorrectionReversibility.CONDITIONAL
    retention_policy: RetentionPolicy = RetentionPolicy.RETAIN
    triggers_reassessment: bool = True  # Always triggers dependency reassessment
    timestamp: str = ""


@dataclass(frozen=True, slots=True)
class CorrectionResult:
    """Result of executing a correction operation."""
    operation_id: str
    success: bool
    affected_refs: tuple[str, ...] = ()  # refs of affected dependent artifacts
    retained_history: bool = True  # Whether provenance history was retained
    detail: str = ""


class CorrectionOperationFactory:
    """Factory for creating typed correction operations.

    Each operation targets exact evidence, proposition, sense, or schema
    revisions. The factory ensures correct reversibility and retention
    policy for each kind.
    """

    @staticmethod
    def supersession(
        target_ref: str,
        target_kind: str = "schema_revision",
        reason: str = "",
    ) -> CorrectionOperation:
        """Schema/proposition supersession.

        Supersession is reversible if journaled. Provenance history
        is retained. Old historical proposition meaning is preserved.
        """
        return CorrectionOperation(
            operation_id=f"supersede:{target_ref}",
            kind=CorrectionKind.SUPERSESSION,
            target_ref=target_ref,
            target_kind=target_kind,
            reason=reason,
            reversibility=CorrectionReversibility.CONDITIONAL,
            retention_policy=RetentionPolicy.RETAIN,
        )

    @staticmethod
    def support_retraction(
        target_ref: str,
        target_kind: str = "evidence",
        reason: str = "",
    ) -> CorrectionOperation:
        """Source support retraction.

        Removed support stops contributing. Provenance history remains
        where permitted. Dependent cognition re-evaluates.
        """
        return CorrectionOperation(
            operation_id=f"retract:{target_ref}",
            kind=CorrectionKind.SUPPORT_RETRACTION,
            target_ref=target_ref,
            target_kind=target_kind,
            reason=reason,
            reversibility=CorrectionReversibility.CONDITIONAL,
            retention_policy=RetentionPolicy.RETAIN,
        )

    @staticmethod
    def permission_revocation(
        target_ref: str,
        target_kind: str = "schema_revision",
        reason: str = "",
    ) -> CorrectionOperation:
        """Permission revocation.

        Revokes permission for a specific revision. Triggers dependency
        reassessment. Provenance history retained where permitted.
        """
        return CorrectionOperation(
            operation_id=f"revoke:{target_ref}",
            kind=CorrectionKind.PERMISSION_REVOCATION,
            target_ref=target_ref,
            target_kind=target_kind,
            reason=reason,
            reversibility=CorrectionReversibility.CONDITIONAL,
            retention_policy=RetentionPolicy.RETAIN,
        )

    @staticmethod
    def archival(
        target_ref: str,
        target_kind: str = "proposition",
        reason: str = "",
    ) -> CorrectionOperation:
        """Archival — reversible and retrievable under policy.

        Archival is not privacy deletion. Archival remains
        reversible/retrievable under policy.
        """
        return CorrectionOperation(
            operation_id=f"archive:{target_ref}",
            kind=CorrectionKind.ARCHIVAL,
            target_ref=target_ref,
            target_kind=target_kind,
            reason=reason,
            reversibility=CorrectionReversibility.REVERSIBLE,
            retention_policy=RetentionPolicy.RETAIN,
        )

    @staticmethod
    def forgetting(
        target_ref: str,
        target_kind: str = "proposition",
        reason: str = "",
    ) -> CorrectionOperation:
        """User-requested forgetting.

        User-requested forgetting removes content but may retain
        provenance history where policy permits.
        """
        return CorrectionOperation(
            operation_id=f"forget:{target_ref}",
            kind=CorrectionKind.FORGETTING,
            target_ref=target_ref,
            target_kind=target_kind,
            reason=reason,
            reversibility=CorrectionReversibility.IRREVERSIBLE,
            retention_policy=RetentionPolicy.RETAIN,
        )

    @staticmethod
    def privacy_deletion(
        target_ref: str,
        target_kind: str = "proposition",
        reason: str = "",
    ) -> CorrectionOperation:
        """Privacy deletion — irreversible, cryptographically erased.

        Privacy deletion removes or cryptographically erases protected
        content. Provenance history is cryptographically erased.
        Archival cannot masquerade as privacy deletion.
        """
        return CorrectionOperation(
            operation_id=f"privacy_delete:{target_ref}",
            kind=CorrectionKind.PRIVACY_DELETION,
            target_ref=target_ref,
            target_kind=target_kind,
            reason=reason,
            reversibility=CorrectionReversibility.IRREVERSIBLE,
            retention_policy=RetentionPolicy.CRYPTO_ERASE,
        )
