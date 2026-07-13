"""OperationAuthorizer — sole permission/safety/capability gate.

Import boundary: model + schema + epistemics + self_model submodules only.
No engine imports.

Architectural guardrails (AGENTS.md §7.7, CORE_LOOP.md D4, AUTHORITY_MATRIX):
- OperationAuthorizer is the sole authority for operation authorization.
- Every operation instance is authorized from live capability, permission,
  risk, context, resources, and current schema-use evidence.
- Authorization is revalidated before irreversible execution and critical
  commit.
- Schema usability tier never authorizes an operation.
- Score preference never authorizes an operation.
- Authorization gates: permission, safety, privacy, capability, resources,
  context.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..model.plan import OperationInstance
from ..model.execution import TypedFailure
from ..model.identity import AssessmentEnvironmentFingerprint


class AuthorizationStatus(str, Enum):
    """Status of an authorization decision."""
    AUTHORIZED = "authorized"
    DENIED = "denied"
    DEFERRED = "deferred"  # Needs more information or revalidation


@dataclass(frozen=True, slots=True)
class AuthorizationResult:
    """Result of authorizing an operation instance.

    OperationAuthorizer is the sole authority for operation authorization.
    """
    operation_ref: str
    status: AuthorizationStatus
    authorization_fingerprint: str = ""
    conditions_checked: tuple[str, ...] = ()
    failure: TypedFailure | None = None
    revalidation_required: bool = False  # Must revalidate before commit


@dataclass(frozen=True, slots=True)
class AuthorizationConditions:
    """Live conditions for authorization.

    Every operation instance is authorized from live capability, permission,
    risk, context, resources, and current schema-use evidence.
    """
    permission_allowed: bool = True
    safety_passed: bool = True
    privacy_passed: bool = True
    capability_available: bool = True
    resources_available: bool = True
    context_valid: bool = True
    schema_use_valid: bool = True
    risk_level: str = "low"  # low, medium, high
    risk_threshold: str = "medium"  # operations above threshold are blocked
    environment_fingerprint: str = ""


class OperationAuthorizer:
    """Sole permission/safety/capability gate for operation authorization.

    Every operation instance is authorized from live capability, permission,
    risk, context, resources, and current schema-use evidence.

    Authorization is revalidated before irreversible execution and
    critical commit.

    Does NOT:
    - Execute operations
    - Commit mutations
    - Decide response content
    - Use schema usability tier as authorization
    """

    def authorize(
        self,
        operation: OperationInstance,
        conditions: AuthorizationConditions,
    ) -> AuthorizationResult:
        """Authorize an operation instance.

        Gates: permission, safety, privacy, capability, resources, context,
        schema-use, risk.
        """
        checked: list[str] = []
        fingerprint = conditions.environment_fingerprint

        # 1. Permission check
        checked.append("permission")
        if not conditions.permission_allowed:
            return AuthorizationResult(
                operation_ref=operation.id,
                status=AuthorizationStatus.DENIED,
                authorization_fingerprint=fingerprint,
                conditions_checked=tuple(checked),
                failure=TypedFailure(
                    failure_kind="permission_blocked",
                    detail="permission not allowed for this operation",
                ),
            )

        # 2. Safety check
        checked.append("safety")
        if not conditions.safety_passed:
            return AuthorizationResult(
                operation_ref=operation.id,
                status=AuthorizationStatus.DENIED,
                authorization_fingerprint=fingerprint,
                conditions_checked=tuple(checked),
                failure=TypedFailure(
                    failure_kind="safety_violation",
                    detail="safety check failed",
                ),
            )

        # 3. Privacy check
        checked.append("privacy")
        if not conditions.privacy_passed:
            return AuthorizationResult(
                operation_ref=operation.id,
                status=AuthorizationStatus.DENIED,
                authorization_fingerprint=fingerprint,
                conditions_checked=tuple(checked),
                failure=TypedFailure(
                    failure_kind="privacy_violation",
                    detail="privacy check failed",
                ),
            )

        # 4. Capability check
        checked.append("capability")
        if not conditions.capability_available:
            return AuthorizationResult(
                operation_ref=operation.id,
                status=AuthorizationStatus.DENIED,
                authorization_fingerprint=fingerprint,
                conditions_checked=tuple(checked),
                failure=TypedFailure(
                    failure_kind="capability_unavailable",
                    detail="capability not available for this operation",
                ),
            )

        # 5. Resources check
        checked.append("resources")
        if not conditions.resources_available:
            return AuthorizationResult(
                operation_ref=operation.id,
                status=AuthorizationStatus.DENIED,
                authorization_fingerprint=fingerprint,
                conditions_checked=tuple(checked),
                failure=TypedFailure(
                    failure_kind="resource_insufficient",
                    detail="resources not available",
                ),
            )

        # 6. Context check
        checked.append("context")
        if not conditions.context_valid:
            return AuthorizationResult(
                operation_ref=operation.id,
                status=AuthorizationStatus.DENIED,
                authorization_fingerprint=fingerprint,
                conditions_checked=tuple(checked),
                failure=TypedFailure(
                    failure_kind="context_invalid",
                    detail="context not valid for this operation",
                ),
            )

        # 7. Schema-use check
        checked.append("schema_use")
        if not conditions.schema_use_valid:
            return AuthorizationResult(
                operation_ref=operation.id,
                status=AuthorizationStatus.DENIED,
                authorization_fingerprint=fingerprint,
                conditions_checked=tuple(checked),
                failure=TypedFailure(
                    failure_kind="schema_use_invalid",
                    detail="schema use profile does not permit this operation",
                ),
            )

        # 8. Risk check
        checked.append("risk")
        risk_order = {"low": 0, "medium": 1, "high": 2}
        if risk_order.get(conditions.risk_level, 0) > risk_order.get(conditions.risk_threshold, 1):
            return AuthorizationResult(
                operation_ref=operation.id,
                status=AuthorizationStatus.DENIED,
                authorization_fingerprint=fingerprint,
                conditions_checked=tuple(checked),
                failure=TypedFailure(
                    failure_kind="risk_exceeded",
                    detail=f"risk level {conditions.risk_level} exceeds threshold {conditions.risk_threshold}",
                ),
            )

        # All checks passed
        return AuthorizationResult(
            operation_ref=operation.id,
            status=AuthorizationStatus.AUTHORIZED,
            authorization_fingerprint=fingerprint,
            conditions_checked=tuple(checked),
            revalidation_required=True,  # Always require revalidation before commit
        )

    def revalidate(
        self,
        previous: AuthorizationResult,
        current_conditions: AuthorizationConditions,
    ) -> AuthorizationResult:
        """Revalidate an authorization before irreversible execution or
        critical commit.

        Authorization is revalidated before irreversible execution and
        critical commit.
        """
        # If fingerprint changed, must re-check all conditions
        if previous.authorization_fingerprint != current_conditions.environment_fingerprint:
            # Fingerprint changed — full revalidation
            return AuthorizationResult(
                operation_ref=previous.operation_ref,
                status=AuthorizationStatus.DENIED,
                authorization_fingerprint=current_conditions.environment_fingerprint,
                conditions_checked=previous.conditions_checked,
                failure=TypedFailure(
                    failure_kind="commit_conflict",
                    detail=(
                        f"environment changed: was {previous.authorization_fingerprint}, "
                        f"now {current_conditions.environment_fingerprint}"
                    ),
                ),
                revalidation_required=True,
            )

        # Re-check all conditions
        # Create a dummy operation for re-check
        op = OperationInstance(
            id=previous.operation_ref,
            schema_ref="",
        )
        return self.authorize(op, current_conditions)
