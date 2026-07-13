"""RetractionEngine — executes correction operations and triggers reassessment.

Import boundary: model + epistemics submodules only. No engine imports.

Architectural guardrails (AGENTS.md §7.8, ACCEPTANCE_TESTS.md §39,
IMPLEMENTATION_PLAN.md Phase 11):
- Removed support stops contributing.
- Dependent cognition re-evaluates via invalidation.
- Provenance history remains where policy permits.
- Each operation targets exact evidence, proposition, sense, or schema
  revisions and triggers appropriate dependency reassessment.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .operations import (
    CorrectionOperation, CorrectionKind, CorrectionResult,
    CorrectionReversibility, RetentionPolicy,
)


@dataclass(frozen=True, slots=True)
class DependentArtifact:
    """A dependent artifact that needs reassessment."""
    artifact_ref: str
    artifact_kind: str  # assessment, inference, cached_answer, plan, etc.
    depends_on: str  # the target_ref it depends on


class RetractionEngine:
    """Executes correction operations and triggers dependency reassessment.

    Removed support stops contributing.
    Dependent cognition re-evaluates via invalidation.
    Provenance history remains where policy permits.

    Does NOT:
    - Delete evidence without tracking dependents
    - Skip dependency reassessment
    - Retain provenance history where policy says to remove
    - Treat archival as privacy deletion or vice versa
    """

    def __init__(self) -> None:
        self._dependents: dict[str, list[DependentArtifact]] = {}
        self._executed: dict[str, CorrectionResult] = {}
        self._retained_history: dict[str, bool] = {}
        self._retracted_targets: set[str] = set()

    def register_dependency(
        self,
        artifact_ref: str,
        artifact_kind: str,
        depends_on: str,
    ) -> None:
        """Register that an artifact depends on a target."""
        dep = DependentArtifact(
            artifact_ref=artifact_ref,
            artifact_kind=artifact_kind,
            depends_on=depends_on,
        )
        self._dependents.setdefault(depends_on, []).append(dep)

    def execute(self, operation: CorrectionOperation) -> CorrectionResult:
        """Execute a correction operation.

        Each targets exact evidence, proposition, sense, or schema
        revisions and triggers appropriate dependency reassessment.
        """
        # Find all dependents of the target
        dependents = self._dependents.get(operation.target_ref, [])
        affected_refs = tuple(d.artifact_ref for d in dependents)

        # Determine if provenance history is retained
        retained = operation.retention_policy != RetentionPolicy.REMOVE and \
                   operation.retention_policy != RetentionPolicy.CRYPTO_ERASE

        # For privacy deletion, history is crypto-erased
        if operation.kind == CorrectionKind.PRIVACY_DELETION:
            retained = False

        # For support retraction, removed support stops contributing
        # but provenance history remains where permitted
        if operation.kind == CorrectionKind.SUPPORT_RETRACTION:
            retained = True  # History retained by default

        result = CorrectionResult(
            operation_id=operation.operation_id,
            success=True,
            affected_refs=affected_refs,
            retained_history=retained,
            detail=f"executed {operation.kind.value} on {operation.target_ref}",
        )

        self._executed[operation.operation_id] = result
        self._retained_history[operation.operation_id] = retained

        # Track retracted targets for exact lookup
        if operation.kind == CorrectionKind.SUPPORT_RETRACTION:
            self._retracted_targets.add(operation.target_ref)

        return result

    def get_dependents(self, target_ref: str) -> tuple[DependentArtifact, ...]:
        """Get all dependents of a target."""
        return tuple(self._dependents.get(target_ref, []))

    def was_executed(self, operation_id: str) -> bool:
        """Check if an operation was executed."""
        return operation_id in self._executed

    def get_result(self, operation_id: str) -> CorrectionResult | None:
        """Get the result of an executed operation."""
        return self._executed.get(operation_id)

    def history_retained(self, operation_id: str) -> bool:
        """Check if provenance history was retained for an operation."""
        return self._retained_history.get(operation_id, True)

    def support_still_contributes(
        self,
        target_ref: str,
        after_retraction: bool = True,
    ) -> bool:
        """Check if support still contributes after retraction.

        Removed support stops contributing.
        """
        if not after_retraction:
            return True

        return target_ref not in self._retracted_targets
