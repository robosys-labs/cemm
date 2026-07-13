"""ArchivalPrivacyGuard — enforces archival ≠ privacy deletion.

Import boundary: model submodules only. No engine imports.

Architectural guardrails (AGENTS.md §7.8, ACCEPTANCE_TESTS.md §40,
IMPLEMENTATION_PLAN.md Phase 11):
- Archival is not privacy deletion.
- Archival remains reversible/retrievable under policy.
- Privacy deletion removes or cryptographically erases protected content.
- Neither is mislabeled as the other.
- Provenance history may be retained only where policy permits.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .operations import (
    CorrectionOperation, CorrectionKind, CorrectionReversibility,
    RetentionPolicy,
)


@dataclass(frozen=True, slots=True)
class PolicyCheckResult:
    """Result of a policy check on a correction operation."""
    is_valid: bool
    violation: str = ""


class ArchivalPrivacyGuard:
    """Guards that archival and privacy deletion are never confused.

    Archival is not privacy deletion.
    Archival remains reversible/retrievable under policy.
    Privacy deletion removes or cryptographically erases protected content.
    Neither is mislabeled as the other.
    """

    def check_operation(self, operation: CorrectionOperation) -> PolicyCheckResult:
        """Check that a correction operation has correct reversibility
        and retention policy for its kind.
        """
        if operation.kind == CorrectionKind.ARCHIVAL:
            # Archival must be reversible
            if operation.reversibility != CorrectionReversibility.REVERSIBLE:
                return PolicyCheckResult(
                    is_valid=False,
                    violation="archival must be reversible",
                )
            # Archival must retain provenance history
            if operation.retention_policy == RetentionPolicy.CRYPTO_ERASE:
                return PolicyCheckResult(
                    is_valid=False,
                    violation="archival must not crypto-erase provenance",
                )
            # Archival must not be labeled as privacy deletion
            if "privacy" in operation.operation_id.lower():
                return PolicyCheckResult(
                    is_valid=False,
                    violation="archival mislabeled as privacy deletion",
                )

        if operation.kind == CorrectionKind.PRIVACY_DELETION:
            # Privacy deletion must be irreversible
            if operation.reversibility != CorrectionReversibility.IRREVERSIBLE:
                return PolicyCheckResult(
                    is_valid=False,
                    violation="privacy deletion must be irreversible",
                )
            # Privacy deletion must crypto-erase
            if operation.retention_policy != RetentionPolicy.CRYPTO_ERASE:
                return PolicyCheckResult(
                    is_valid=False,
                    violation="privacy deletion must crypto-erase protected content",
                )
            # Privacy deletion must not be labeled as archival
            if "archive" in operation.operation_id.lower():
                return PolicyCheckResult(
                    is_valid=False,
                    violation="privacy deletion mislabeled as archival",
                )

        if operation.kind == CorrectionKind.FORGETTING:
            # Forgetting must be irreversible
            if operation.reversibility != CorrectionReversibility.IRREVERSIBLE:
                return PolicyCheckResult(
                    is_valid=False,
                    violation="forgetting must be irreversible",
                )

        return PolicyCheckResult(is_valid=True)

    def is_archival(self, operation: CorrectionOperation) -> bool:
        """Check if an operation is archival."""
        return operation.kind == CorrectionKind.ARCHIVAL

    def is_privacy_deletion(self, operation: CorrectionOperation) -> bool:
        """Check if an operation is privacy deletion."""
        return operation.kind == CorrectionKind.PRIVACY_DELETION

    def can_retrieve(self, operation: CorrectionOperation) -> bool:
        """Check if content can be retrieved after this operation.

        Archival remains reversible/retrievable under policy.
        Privacy deletion is not retrievable.
        """
        if operation.kind == CorrectionKind.ARCHIVAL:
            return True
        if operation.kind == CorrectionKind.PRIVACY_DELETION:
            return False
        if operation.kind == CorrectionKind.FORGETTING:
            return False
        # Supersession, support retraction, permission revocation
        # retain history — retrievable
        return True

    def can_reverse(self, operation: CorrectionOperation) -> bool:
        """Check if an operation can be reversed.

        Archival is reversible.
        Privacy deletion is irreversible.
        """
        if operation.kind == CorrectionKind.ARCHIVAL:
            return True
        if operation.kind == CorrectionKind.PRIVACY_DELETION:
            return False
        if operation.kind == CorrectionKind.FORGETTING:
            return False
        # Supersession is reversible if journaled
        if operation.kind == CorrectionKind.SUPERSESSION:
            return True
        # Support retraction and permission revocation are conditionally reversible
        return True


class CorrectionTargetingGuard:
    """Guards that correction targets exact sense/revision.

    Correction targets exact evidence, proposition, sense, or schema
    revisions. Unrelated senses are unaffected. Old historical
    proposition meaning is preserved.
    """

    def check_target_precision(
        self,
        operation: CorrectionOperation,
        known_targets: tuple[str, ...],
    ) -> PolicyCheckResult:
        """Check that a correction operation targets a precise, known target.

        Each targets exact evidence, proposition, sense, or schema
        revisions.
        """
        if not operation.target_ref:
            return PolicyCheckResult(
                is_valid=False,
                violation="correction operation has empty target_ref",
            )

        if operation.target_ref not in known_targets:
            return PolicyCheckResult(
                is_valid=False,
                violation=f"target {operation.target_ref} not in known targets",
            )

        return PolicyCheckResult(is_valid=True)

    def check_unaffected_senses(
        self,
        operation: CorrectionOperation,
        related_senses: tuple[str, ...],
        affected_senses: tuple[str, ...],
    ) -> PolicyCheckResult:
        """Check that unrelated senses are unaffected.

        Correct one sense of a polysemous term — unrelated senses
        unaffected.
        """
        target = operation.target_ref
        unrelated = tuple(s for s in related_senses if s != target)

        for s in unrelated:
            if s in affected_senses:
                return PolicyCheckResult(
                    is_valid=False,
                    violation=f"unrelated sense {s} was affected by correction targeting {target}",
                )

        return PolicyCheckResult(is_valid=True)

    def check_history_preserved(
        self,
        operation: CorrectionOperation,
        history_available: bool,
    ) -> PolicyCheckResult:
        """Check that old historical proposition meaning is preserved
        where policy permits.

        Old historical proposition meaning preserved.
        Provenance history may be retained only where policy permits.
        """
        # Privacy deletion and forgetting do not preserve history
        if operation.kind in (CorrectionKind.PRIVACY_DELETION, CorrectionKind.FORGETTING):
            return PolicyCheckResult(is_valid=True)  # History not required

        # All other operations must preserve history
        if not history_available:
            return PolicyCheckResult(
                is_valid=False,
                violation=f"historical meaning not preserved for {operation.kind.value}",
            )

        return PolicyCheckResult(is_valid=True)
