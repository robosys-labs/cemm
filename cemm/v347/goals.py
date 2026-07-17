"""Semantic goals, operation planning, authorization and reconciliation."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Iterable, Mapping

from .model import (
    CommunicativeForce,
    GoalRecord,
    GraphPatch,
    MeaningBundle,
    OperationOutcome,
    OperationPlan,
    OperationSchema,
    PatchOperation,
    PatchOperationKind,
    PortBinding,
    ReferentKind,
    RulePattern,
    semantic_hash,
)
from .schema import SemanticSchemaStore
from .storage import SemanticStore


@dataclass(frozen=True, slots=True)
class CapabilityState:
    available_capabilities: frozenset[str]
    permissions: frozenset[str]
    resource_state: Mapping[str, float]
    max_risk: float = 0.5
    capability_evidence_refs: Mapping[str, tuple[str, ...]] = None  # type: ignore[assignment]
    store_revision: int = 0

    def __post_init__(self) -> None:
        if self.capability_evidence_refs is None:
            object.__setattr__(self, "capability_evidence_refs", {})


class CapabilityCoordinator:
    """Derive live capability state from durable observations and adapters."""

    def __init__(self, store: SemanticStore, schemas: SemanticSchemaStore):
        self._store = store
        self._schemas = schemas

    def compile_adapter_observation_patch(
        self,
        adapter_operation_refs: Iterable[str],
        *,
        expected_store_revision: int,
    ) -> GraphPatch | None:
        operations: list[PatchOperation] = []
        for operation_ref in sorted(set(adapter_operation_refs)):
            try:
                schema = self._schemas.operation(operation_ref)
            except KeyError:
                continue
            if not schema.capability_ref:
                continue
            observation_ref = semantic_hash("capability_observation", (
                operation_ref, schema.capability_ref, "registered_adapter"
            ))
            operations.append(PatchOperation(
                operation_id=f"op:{observation_ref}",
                kind=PatchOperationKind.UPSERT_CAPABILITY_OBSERVATION,
                target_ref=observation_ref,
                payload={
                    "capability_ref": schema.capability_ref,
                    "available": True,
                    "confidence": 1.0,
                    "source_ref": f"runtime:adapter:{operation_ref}",
                    "context_ref": "actual",
                    "resource_state": dict(schema.metadata.get("resource_state", {"compute": 1.0})),
                    "valid_until": None,
                    "evidence_refs": (f"adapter_registered:{operation_ref}",),
                },
            ))
        # Semantic response is an observed internal capability of the running
        # composition root, not a claim inferred from its own output.
        self_ref = "capability_observation:semantic_response"
        operations.append(PatchOperation(
            operation_id=f"op:{self_ref}",
            kind=PatchOperationKind.UPSERT_CAPABILITY_OBSERVATION,
            target_ref=self_ref,
            payload={
                "capability_ref": "capability:semantic_response",
                "available": True,
                "confidence": 1.0,
                "source_ref": "runtime:composition_root",
                "context_ref": "actual",
                "resource_state": {"compute": 1.0},
                "valid_until": None,
                "evidence_refs": ("runtime_component:realizer",),
            },
        ))
        return GraphPatch(
            patch_id=semantic_hash("patch:capability_observations", tuple(
                operation.target_ref for operation in operations
            )),
            context_ref="actual",
            scope_ref="actual",
            source_ref="runtime:capability_observer",
            evidence_refs=tuple(
                ref for operation in operations for ref in operation.payload.get("evidence_refs", ())
            ),
            operations=tuple(operations),
            expected_store_revision=expected_store_revision,
            permission_ref="internal",
        )

    def state(
        self,
        context_ref: str,
        *,
        permissions: Iterable[str] = ("conversation", "internal"),
        max_risk: float = 0.25,
    ) -> CapabilityState:
        capabilities: set[str] = set()
        resources: dict[str, float] = {}
        evidence: dict[str, list[str]] = {}
        observations: dict[str, list[Mapping[str, Any]]] = {}
        now = datetime.now(timezone.utc)
        for item in self._store.capability_observations(context_ref):
            valid_until = item.get("valid_until")
            if valid_until:
                try:
                    expiry = datetime.fromisoformat(str(valid_until).replace("Z", "+00:00"))
                    if expiry.tzinfo is None:
                        expiry = expiry.replace(tzinfo=timezone.utc)
                    if expiry <= now:
                        continue
                except ValueError:
                    continue
            observations.setdefault(str(item["capability_ref"]), []).append(item)
        for capability_ref, items in observations.items():
            positive = max(
                (float(item["confidence"]) for item in items if bool(item["available"])),
                default=0.0,
            )
            negative = max(
                (float(item["confidence"]) for item in items if not bool(item["available"])),
                default=0.0,
            )
            if positive < 0.5 or negative >= positive:
                continue
            capabilities.add(capability_ref)
            for item in items:
                if not bool(item["available"]):
                    continue
                evidence.setdefault(capability_ref, []).extend(item.get("evidence_refs", ()))
                for key, value in item.get("resource_state", {}).items():
                    resources[str(key)] = max(resources.get(str(key), 0.0), float(value))
        return CapabilityState(
            available_capabilities=frozenset(capabilities),
            permissions=frozenset(permissions),
            resource_state=resources,
            max_risk=max_risk,
            capability_evidence_refs={key: tuple(dict.fromkeys(value)) for key, value in evidence.items()},
            store_revision=self._store.revision,
        )


class OperationLedgerCompiler:
    def compile(
        self,
        plans: Iterable[OperationPlan],
        outcomes: Iterable[OperationOutcome],
        *,
        context_ref: str,
        expected_store_revision: int,
    ) -> GraphPatch | None:
        pairs = tuple(zip(plans, outcomes))
        if not pairs:
            return None
        operations = tuple(PatchOperation(
            operation_id=semantic_hash("op:operation_ledger", (plan.plan_id, outcome.outcome_id)),
            kind=PatchOperationKind.UPSERT_OPERATION_LEDGER,
            target_ref=semantic_hash("operation_ledger", (plan.plan_id, outcome.outcome_id)),
            payload={
                "plan_ref": plan.plan_id,
                "operation_ref": plan.operation_ref,
                "status": outcome.status,
                "authorization_fingerprint": plan.authorization_fingerprint,
                "capability_evidence_refs": plan.live_capability_evidence_refs,
                "observed_proposition_refs": outcome.observed_proposition_refs,
                "errors": outcome.errors,
                "metadata": {
                    "authorized": plan.authorized,
                    "authorization_reason": plan.authorization_reason,
                    "schema_revision": plan.schema_revision,
                },
            },
        ) for plan, outcome in pairs)
        return GraphPatch(
            patch_id=semantic_hash("patch:operation_ledger", tuple(op.target_ref for op in operations)),
            context_ref=context_ref,
            scope_ref=context_ref,
            source_ref="runtime:operation_reconciler",
            evidence_refs=tuple(dict.fromkeys(
                ref for plan, _ in pairs for ref in plan.live_capability_evidence_refs
            )),
            operations=operations,
            expected_store_revision=expected_store_revision,
            permission_ref="internal",
        )


class GoalGenerator:
    def generate(self, bundle: MeaningBundle | None) -> tuple[GoalRecord, ...]:
        if bundle is None:
            return ()
        result = []
        for proposition_ref in bundle.proposition_refs:
            proposition = bundle.graph.referents.get(proposition_ref)
            payload = proposition.payload or {} if proposition else {}
            force = CommunicativeForce(str(payload.get("communicative_force", "assert")))
            if force == CommunicativeForce.ASK:
                kind = "resolve_information_state"
                priority = 0.95
            elif force in {CommunicativeForce.DIRECT, CommunicativeForce.REQUEST}:
                kind = "achieve_requested_operation"
                priority = 1.0
            elif force == CommunicativeForce.CORRECT:
                kind = "reconcile_and_admit_correction"
                priority = 0.9
            else:
                kind = "admit_and_acknowledge_assertion"
                priority = 0.7
            result.append(GoalRecord(
                goal_id=semantic_hash("goal", (proposition_ref, kind)),
                goal_kind=kind,
                content_proposition_refs=(proposition_ref,),
                desired_state_ref=None,
                priority=priority,
                success_conditions=(),
                source_ref=proposition_ref,
            ))
        return tuple(result)


class GoalArbiter:
    def select(self, goals: Iterable[GoalRecord]) -> tuple[GoalRecord, ...]:
        goals = sorted(goals, key=lambda item: item.priority, reverse=True)
        selected = []
        seen_content = set()
        for goal in goals:
            key = (goal.goal_kind, goal.content_proposition_refs)
            if key in seen_content:
                continue
            selected.append(goal)
            seen_content.add(key)
        return tuple(selected)


class OperationPlanner:
    def __init__(self, schemas: SemanticSchemaStore):
        self._schemas = schemas

    def plan(
        self,
        goals: Iterable[GoalRecord],
        bundle: MeaningBundle | None,
    ) -> tuple[OperationPlan, ...]:
        if bundle is None:
            return ()
        plans = []
        for goal in goals:
            if goal.goal_kind != "achieve_requested_operation":
                continue
            for proposition_ref in goal.content_proposition_refs:
                proposition = bundle.graph.referents.get(proposition_ref)
                payload = proposition.payload or {} if proposition else {}
                for predication_ref in payload.get("predication_refs", ()):
                    predication = bundle.graph.predications.get(str(predication_ref))
                    if predication is None:
                        continue
                    for operation in self._schemas.operations_for_predicate(predication.predicate_schema_ref):
                        bindings = self._bind_operation(operation, predication.bindings)
                        if bindings is None:
                            continue
                        plans.append(OperationPlan(
                            plan_id=semantic_hash("operation:plan", (
                                goal.goal_id, operation.operation_ref, bindings
                            )),
                            operation_ref=operation.operation_ref,
                            goal_ref=goal.goal_id,
                            bindings=bindings,
                            precondition_refs=tuple(map(str, operation.metadata.get("precondition_refs", ()))),
                            expected_effect_patch=None,
                            risk=operation.risk,
                            schema_revision=int(operation.metadata.get("revision", 1)),
                            resource_requirements={
                                str(key): float(value)
                                for key, value in operation.metadata.get("resource_requirements", {}).items()
                            },
                        ))
        return tuple(plans)

    @staticmethod
    def _bind_operation(
        operation: OperationSchema,
        source_bindings: tuple[PortBinding, ...],
    ) -> tuple[PortBinding, ...] | None:
        source_by_port = {item.port_id: item for item in source_bindings}
        result = []
        mapping = {
            str(key): str(value)
            for key, value in operation.metadata.get("source_port_map", {}).items()
        }
        for port in operation.input_ports:
            source_port = mapping.get(port.port_id, port.port_id)
            binding = source_by_port.get(source_port)
            if binding is None:
                if port.required:
                    return None
                continue
            result.append(PortBinding(
                port_id=port.port_id,
                referent_refs=binding.referent_refs,
                open_variable_ref=binding.open_variable_ref,
                confidence=binding.confidence,
                evidence_refs=binding.evidence_refs,
                assumptions=binding.assumptions,
            ))
        return tuple(result)


class OperationAuthorizer:
    def __init__(self, schemas: SemanticSchemaStore):
        self._schemas = schemas

    def authorize(
        self,
        plan: OperationPlan,
        capability: CapabilityState,
    ) -> OperationPlan:
        schema = self._schemas.operation(plan.operation_ref)
        reasons = []
        if schema.capability_ref and schema.capability_ref not in capability.available_capabilities:
            reasons.append("capability_unavailable")
        if schema.permission_ref and schema.permission_ref not in capability.permissions:
            reasons.append("permission_missing")
        if plan.risk > capability.max_risk:
            reasons.append("risk_exceeds_limit")
        if any(binding.open_variable_ref for binding in plan.bindings):
            reasons.append("operation_has_open_port")
        for resource, required in plan.resource_requirements.items():
            if float(capability.resource_state.get(resource, 0.0)) < float(required):
                reasons.append(f"resource_insufficient:{resource}")
        capability_evidence = tuple(
            capability.capability_evidence_refs.get(schema.capability_ref, ())
        )
        fingerprint = semantic_hash("operation_authorization", (
            plan.plan_id, schema.operation_ref, plan.schema_revision,
            tuple(sorted(capability.available_capabilities)),
            tuple(sorted(capability.permissions)),
            dict(capability.resource_state), capability.store_revision,
        ), 64)
        return OperationPlan(
            plan_id=plan.plan_id,
            operation_ref=plan.operation_ref,
            goal_ref=plan.goal_ref,
            bindings=plan.bindings,
            precondition_refs=plan.precondition_refs,
            expected_effect_patch=plan.expected_effect_patch,
            risk=plan.risk,
            authorized=not reasons,
            authorization_reason="authorized" if not reasons else ",".join(reasons),
            schema_revision=plan.schema_revision,
            authorization_fingerprint=fingerprint,
            resource_requirements=plan.resource_requirements,
            live_capability_evidence_refs=capability_evidence,
        )


class OperationExecutor:
    """Execute only registered adapter functions after authorization."""

    def __init__(self, adapters: Mapping[str, object] | None = None):
        self._adapters = dict(adapters or {})

    def execute(self, plan: OperationPlan) -> OperationOutcome:
        if not plan.authorized:
            return OperationOutcome(
                outcome_id=semantic_hash("operation:outcome", (plan.plan_id, "blocked")),
                plan_ref=plan.plan_id,
                status="blocked",
                errors=(plan.authorization_reason or "not_authorized",),
            )
        adapter = self._adapters.get(plan.operation_ref)
        if adapter is None:
            return OperationOutcome(
                outcome_id=semantic_hash("operation:outcome", (plan.plan_id, "unavailable")),
                plan_ref=plan.plan_id,
                status="unavailable",
                errors=("operation_adapter_unavailable",),
            )
        try:
            result = adapter(plan)
        except Exception as exc:  # pragma: no cover - adapter boundary
            return OperationOutcome(
                outcome_id=semantic_hash("operation:outcome", (plan.plan_id, "failed", type(exc).__name__)),
                plan_ref=plan.plan_id,
                status="failed",
                errors=(f"{type(exc).__name__}:{exc}",),
            )
        if isinstance(result, OperationOutcome):
            return result
        if isinstance(result, Mapping):
            status = str(result.get("status", "completed"))
            effect_patch = result.get("effect_patch")
            if effect_patch is not None and not isinstance(effect_patch, GraphPatch):
                return OperationOutcome(
                    outcome_id=semantic_hash("operation:outcome", (plan.plan_id, "invalid_effect")),
                    plan_ref=plan.plan_id,
                    status="failed",
                    errors=("adapter_effect_patch_not_graphpatch",),
                )
            return OperationOutcome(
                outcome_id=str(result.get("outcome_id") or semantic_hash(
                    "operation:outcome", (plan.plan_id, status, result)
                )),
                plan_ref=plan.plan_id,
                status=status,
                observed_proposition_refs=tuple(map(str, result.get("observed_proposition_refs", ()))),
                effect_patch=effect_patch,
                errors=tuple(map(str, result.get("errors", ()))),
            )
        return OperationOutcome(
            outcome_id=semantic_hash("operation:outcome", (plan.plan_id, "completed")),
            plan_ref=plan.plan_id,
            status="completed",
        )


class OutcomeReconciler:
    _ADMISSIBLE_EFFECT_KINDS = frozenset({
        PatchOperationKind.UPSERT_REFERENT,
        PatchOperationKind.ADD_ALIAS,
        PatchOperationKind.UPSERT_PREDICATION,
        PatchOperationKind.UPSERT_PROPOSITION,
        PatchOperationKind.UPSERT_KNOWLEDGE,
        PatchOperationKind.SUPERSEDE_KNOWLEDGE,
        PatchOperationKind.RETRACT_SUPPORT,
        PatchOperationKind.UPSERT_WORLD_TRACK,
        PatchOperationKind.UPSERT_EVIDENCE,
    })

    def reconcile(
        self,
        plan: OperationPlan,
        outcome: OperationOutcome,
    ) -> tuple[str, ...]:
        if outcome.status == "completed":
            return ("observed_completion",)
        if outcome.status == "blocked":
            return ("authorization_blocked",)
        if outcome.status == "unavailable":
            return ("capability_unavailable",)
        return ("operation_failed",)

    def admissible_effect_patch(
        self,
        plan: OperationPlan,
        outcome: OperationOutcome,
        *,
        expected_store_revision: int,
    ) -> GraphPatch | None:
        """Re-authorize adapter-proposed effects at the semantic commit boundary."""
        patch = outcome.effect_patch
        if (
            patch is None
            or not plan.authorized
            or outcome.status != "completed"
            or not plan.authorization_fingerprint
        ):
            return None
        if any(operation.kind not in self._ADMISSIBLE_EFFECT_KINDS for operation in patch.operations):
            return None
        return replace(
            patch,
            expected_store_revision=expected_store_revision,
            metadata={
                **dict(patch.metadata),
                "operation_plan_ref": plan.plan_id,
                "authorization_fingerprint": plan.authorization_fingerprint,
                "reconciled": True,
            },
        )
