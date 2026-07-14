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
class AuthorizationBatch:
    """Per-operation authorization results.

    BF-001: Authorization must be per operation, not one result reused
    for the whole plan.
    """
    by_operation_ref: dict[str, AuthorizationResult] = field(default_factory=dict)

    def get(self, operation_ref: str) -> AuthorizationResult | None:
        return self.by_operation_ref.get(operation_ref)

    @property
    def all_authorized(self) -> bool:
        if not self.by_operation_ref:
            return False
        return all(
            r.status is AuthorizationStatus.AUTHORIZED
            for r in self.by_operation_ref.values()
        )


@dataclass(frozen=True, slots=True)
class AuthorizationConditions:
    """Live conditions for authorization.

    Every operation instance is authorized from live capability, permission,
    risk, context, resources, and current schema-use evidence.
    """
    permission_allowed: bool | None = None
    safety_passed: bool | None = None
    privacy_passed: bool | None = None
    capability_available: bool | None = None
    resources_available: bool | None = None
    context_valid: bool | None = None
    schema_use_valid: bool | None = None
    risk_level: str = "unknown"  # low, medium, high, unknown
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

        BF-003: Unknown (None) conditions produce DEFERRED, never AUTHORIZED.
        """
        checked: list[str] = []
        fingerprint = conditions.environment_fingerprint

        def _check_gate(
            gate_name: str,
            value: bool | None,
            failure_kind: str,
            detail: str,
        ) -> AuthorizationResult | None:
            checked.append(gate_name)
            if value is False:
                return AuthorizationResult(
                    operation_ref=operation.id,
                    status=AuthorizationStatus.DENIED,
                    authorization_fingerprint=fingerprint,
                    conditions_checked=tuple(checked),
                    failure=TypedFailure(
                        failure_kind=failure_kind,
                        detail=detail,
                    ),
                )
            if value is None:
                return AuthorizationResult(
                    operation_ref=operation.id,
                    status=AuthorizationStatus.DEFERRED,
                    authorization_fingerprint=fingerprint,
                    conditions_checked=tuple(checked),
                    failure=TypedFailure(
                        failure_kind=f"{failure_kind}_unknown",
                        detail=f"{gate_name} condition unknown",
                    ),
                )
            return None

        # 1. Permission check
        result = _check_gate("permission", conditions.permission_allowed, "permission_blocked", "permission not allowed for this operation")
        if result:
            return result

        # 2. Safety check
        result = _check_gate("safety", conditions.safety_passed, "safety_violation", "safety check failed")
        if result:
            return result

        # 3. Privacy check
        result = _check_gate("privacy", conditions.privacy_passed, "privacy_violation", "privacy check failed")
        if result:
            return result

        # 4. Capability check
        result = _check_gate("capability", conditions.capability_available, "capability_unavailable", "capability not available for this operation")
        if result:
            return result

        # 5. Resources check
        result = _check_gate("resources", conditions.resources_available, "resource_insufficient", "resources not available")
        if result:
            return result

        # 6. Context check
        result = _check_gate("context", conditions.context_valid, "context_invalid", "context not valid for this operation")
        if result:
            return result

        # 7. Schema-use check
        result = _check_gate("schema_use", conditions.schema_use_valid, "schema_use_invalid", "schema use profile does not permit this operation")
        if result:
            return result

        # 8. Risk check
        checked.append("risk")
        risk_order = {"low": 0, "medium": 1, "high": 2}
        if risk_order.get(conditions.risk_level, -1) > risk_order.get(conditions.risk_threshold, 1):
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
        if conditions.risk_level == "unknown":
            return AuthorizationResult(
                operation_ref=operation.id,
                status=AuthorizationStatus.DEFERRED,
                authorization_fingerprint=fingerprint,
                conditions_checked=tuple(checked),
                failure=TypedFailure(
                    failure_kind="risk_unknown",
                    detail="risk level unknown",
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
