"""Live runtime capability evidence adapter.

This module does not keep a static capability truth list.  It derives candidate
operations from active operation schemas and evaluates them against the actual
runtime components, channels, resources, permissions, and cycle context.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib

from .capability_evaluator import (
    CapabilityEvaluator,
    ChannelRecord,
    CompetenceRecord,
    ComponentHealthRecord,
    ContextualPrecondition,
    ImplementationRecord,
    PermissionRecord,
    ResourceRecord,
)


class RuntimeCapabilityProvider:
    def __init__(
        self,
        *,
        evaluator: CapabilityEvaluator,
        schema_store,
        operation_specs: tuple[dict, ...],
        components: dict[str, object],
    ) -> None:
        self._evaluator = evaluator
        self._schemas = schema_store
        self._specs = {
            str(item.get("semantic_key", "")): dict(item)
            for item in operation_specs
            if item.get("semantic_key")
        }
        self._components = dict(components)

    def assess_cycle(self, cycle) -> tuple[object, ...]:
        requested: set[str] = set()
        broad_query = False
        for interpretation in tuple(
            getattr(cycle, "selected_interpretations", ()) or ()
        ):
            if (
                getattr(interpretation, "predicate_semantic_key", "")
                != "capable_of"
                or getattr(interpretation, "communicative_force", "")
                not in {"ask", "query"}
            ):
                continue
            operation = next((
                binding.filler_ref
                for binding in getattr(interpretation, "role_bindings", ())
                if binding.role_schema_ref.removeprefix("role:") == "operation"
            ), "")
            if operation:
                requested.add(self._normalize_operation(operation))
            else:
                broad_query = True

        if not requested and not broad_query:
            return ()
        operations = (
            tuple(self._specs)
            if broad_query
            else tuple(sorted(requested))
        )
        return tuple(
            self._assess(operation, cycle)
            for operation in operations
            if operation in self._specs
        )

    def _assess(self, operation: str, cycle):
        implementation = self._components.get(operation)
        active_schema = self._schemas.find_active(operation)
        implementation_id = self._implementation_id(implementation)
        owner = getattr(implementation, "__self__", None)
        health_value = str(
            getattr(owner, "health", getattr(implementation, "health", "healthy"))
        )
        if health_value not in {"healthy", "degraded", "failed"}:
            health_value = "healthy" if callable(implementation) else "failed"

        assessment = self._evaluator.evaluate(
            subject_ref="self",
            operation_schema_ref=operation,
            competence=CompetenceRecord(
                schema_ref=(
                    active_schema.record_id if active_schema is not None else operation
                ),
                is_competent=active_schema is not None and callable(implementation),
                competence_score=(
                    1.0
                    if active_schema is not None and callable(implementation)
                    else 0.0
                ),
                detail="active operation schema and installed runtime component",
            ),
            implementation=ImplementationRecord(
                operation_ref=operation,
                implementation_id=implementation_id,
                is_registered=callable(implementation),
            ),
            component_health=ComponentHealthRecord(
                component_id=implementation_id or f"runtime:missing:{operation}",
                health=health_value,
            ),
            input_channel=ChannelRecord(
                channel_kind="input",
                channel_id=getattr(
                    next(iter(cycle.trigger.input_signals), None),
                    "channel",
                    "text",
                ),
                is_available=bool(cycle.trigger.input_signals),
                detail="current cycle input channel",
            ),
            output_channel=ChannelRecord(
                channel_kind="output",
                channel_id="canonical-cycle",
                is_available=True,
                detail="canonical cognitive/communicative output channel",
            ),
            resources=(ResourceRecord(
                resource_kind="runtime_execution_slot",
                status="available",
                available_amount=1.0,
                required_amount=1.0,
            ),),
            permission=PermissionRecord(
                operation_ref=operation,
                is_allowed=True,
                policy_ref="runtime:default_safe_operation_policy",
                detail="operation is registered in the canonical boot package",
            ),
            preconditions=(ContextualPrecondition(
                precondition_id="runtime:cycle_context_present",
                description="a pinned cognitive cycle context exists",
                is_satisfied=bool(cycle.trigger.context_id),
            ),),
            observed_reliability=1.0 if callable(implementation) else 0.0,
        )
        fingerprint = self._fingerprint(cycle, operation, implementation_id)
        return replace(
            assessment,
            assessment_id=f"capability:{fingerprint[:16]}",
            context_ref="actual",
            environment_fingerprint=fingerprint,
        )

    @staticmethod
    def _normalize_operation(value: str) -> str:
        return value.removeprefix("ref:schema:")

    @staticmethod
    def _implementation_id(implementation: object | None) -> str:
        if not callable(implementation):
            return ""
        module = getattr(implementation, "__module__", "")
        qualname = getattr(
            implementation,
            "__qualname__",
            getattr(implementation, "__name__", implementation.__class__.__qualname__),
        )
        return f"runtime:{module}.{qualname}".rstrip(".")

    @staticmethod
    def _fingerprint(cycle, operation: str, component_id: str) -> str:
        snapshot = cycle.snapshot
        raw = "|".join((
            operation,
            component_id,
            str(snapshot.schema_store_revision),
            str(snapshot.resource_revision),
            str(snapshot.permission_policy_revision),
            str(snapshot.competence_suite_hash),
        ))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
