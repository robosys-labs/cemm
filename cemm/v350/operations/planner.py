"""Exact-snapshot operation planning and hard authorization for Phase 16."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from ..goals.model import GoalCandidateRecord, GoalDecisionRecord
from ..learning.model import PinnedRecord
from ..schema.model import ActionSchema, UseOperation, schema_authorizes_use, semantic_fingerprint
from ..storage.codec import record_fingerprints
from ..storage.model import RecordKind
from ..uol.model import CapabilityStatus, FillerRef, SemanticApplication
from .model import (
    IdempotencyMode, OperationAdapterContractRecord, OperationAuthorizationDecision,
    OperationAuthorizationRecord, OperationGateAssessmentRecord, OperationPlanRecord,
)


def _pin(stored) -> PinnedRecord:
    return PinnedRecord(stored.record_kind, stored.record_ref, stored.revision, stored.record_fingerprint)


class OperationPlanner:
    """Build a plan only from a currently selected EXECUTE goal.

    Planning is non-mutating and does not imply permission to submit an external
    operation.  All authority inputs are exact revision/fingerprint pins.
    """
    def __init__(self, store) -> None:
        self.store = store

    def plan(self, decision_pin: PinnedRecord, goal_ref: str, adapter_contract_pin: PinnedRecord) -> OperationPlanRecord:
        # Capture the logical store before any planning read. Planning may perform
        # many exact lookups; if any concurrent commit occurs before the plan is
        # sealed, fail instead of mixing multiple snapshots into one authority.
        with self.store.snapshot() as source_snapshot:
            pass
        decision_stored = self._exact(decision_pin, RecordKind.GOAL_DECISION)
        decision = decision_stored.payload
        decision_current = self.store.get_record(RecordKind.GOAL_DECISION, decision_pin.record_ref)
        if decision_current is None or decision_current.revision != decision_pin.revision or decision_current.record_fingerprint != decision_pin.record_fingerprint:
            raise ValueError("operation planning requires the current exact GoalDecisionRecord")
        if not isinstance(decision, GoalDecisionRecord) or goal_ref not in decision.selected_goal_refs:
            raise ValueError("operation planning requires an exact currently selected goal")
        candidate_pin = next((p for p in decision.candidate_pins if p.record_ref == goal_ref), None)
        if candidate_pin is None:
            raise ValueError("selected goal is not pinned by GoalDecisionRecord")
        candidate_stored = self._exact(candidate_pin, RecordKind.GOAL_CANDIDATE)
        candidate = candidate_stored.payload
        if not isinstance(candidate, GoalCandidateRecord) or candidate.operation != UseOperation.EXECUTE:
            raise ValueError("OperationPlanner accepts only selected EXECUTE goals")
        if not candidate.authorized:
            raise ValueError("Phase-15 eligibility denied; operation cannot be planned")
        if len(candidate.target_refs) != 1:
            raise ValueError("EXECUTE goal requires exactly one target action application")
        app_stored = self.store.get_record(RecordKind.SEMANTIC_APPLICATION, candidate.target_refs[0])
        if app_stored is None or not isinstance(app_stored.payload, SemanticApplication):
            raise ValueError("EXECUTE goal target must resolve to one SemanticApplication")
        app = app_stored.payload
        schema_stored = self.store.get_record(RecordKind.SCHEMA, app.schema_ref, app.schema_revision)
        if schema_stored is None or not isinstance(schema_stored.payload, ActionSchema):
            raise ValueError("operation application must pin an ActionSchema")
        action = schema_stored.payload
        if not schema_authorizes_use(action, UseOperation.PLAN) or not schema_authorizes_use(action, UseOperation.EXECUTE):
            raise ValueError("action schema is not independently PLAN and EXECUTE authorized")
        effective_plan = self.store.repositories.schemas.for_use(app.schema_ref, UseOperation.PLAN)
        effective_execute = self.store.repositories.schemas.for_use(app.schema_ref, UseOperation.EXECUTE)
        if effective_plan.revision != app.schema_revision or effective_execute.revision != app.schema_revision:
            raise ValueError("operation application pins a stale/non-effective action schema revision")
        required_ports = tuple(sorted(port.port_ref for port in action.local_ports if port.cardinality.minimum > 0))
        binding_map = {binding.port_ref: binding for binding in app.bindings}
        missing = [port for port in required_ports if port not in binding_map or len(binding_map[port].fillers) == 0]
        if missing:
            raise ValueError(f"operation target has ungrounded required ports: {missing}")
        if action.controlling_port_ref is None:
            raise ValueError("executable action requires an explicit controlling_port_ref")
        control = binding_map.get(action.controlling_port_ref)
        holders = tuple(f.ref for f in (() if control is None else control.fillers) if isinstance(f, FillerRef))
        if len(holders) != 1:
            raise ValueError("operation controlling port must resolve to exactly one holder")
        holder = holders[0]
        capabilities = [
            stored for stored in self.store.records(RecordKind.CAPABILITY_INSTANCE)
            if getattr(stored.payload, "holder_ref", None) == holder
            and getattr(stored.payload, "action_schema_ref", None) == app.schema_ref
            and getattr(stored.payload, "action_schema_revision", None) == app.schema_revision
            and getattr(stored.payload, "status", None) == CapabilityStatus.AVAILABLE
            and getattr(stored.payload, "context_ref", None) in {"global", app.context_ref}
        ]
        if len(capabilities) != 1:
            raise ValueError(f"operation requires one unambiguous live capability; found {len(capabilities)}")
        adapter_stored = self._exact(adapter_contract_pin, RecordKind.OPERATION_ADAPTER_CONTRACT)
        adapter = adapter_stored.payload
        if not isinstance(adapter, OperationAdapterContractRecord) or not adapter.active:
            raise ValueError("operation adapter contract is not active")
        if (app.schema_ref, app.schema_revision) not in adapter.action_schema_pins:
            raise ValueError("adapter contract does not authorize exact action schema revision")
        if not set(binding_map).issubset(set(adapter.supported_port_refs)):
            raise ValueError("adapter cannot bind all action application ports")
        auth_pins = tuple(getattr(candidate, "authorization_pins", ()))
        auth_identities={(p.record_kind,p.record_ref,p.revision,p.record_fingerprint) for p in auth_pins}
        for required_pin in (_pin(app_stored),_pin(schema_stored),_pin(capabilities[0])):
            identity=(required_pin.record_kind,required_pin.record_ref,required_pin.revision,required_pin.record_fingerprint)
            if identity not in auth_identities:
                raise ValueError("Phase-15 EXECUTE eligibility does not pin the exact target/schema/capability used by the operation plan")
        idempotency_key = None
        if adapter.idempotency_mode != IdempotencyMode.NONE:
            idempotency_key = "idem:" + semantic_fingerprint(
                "operation-idempotency", (decision_pin.key, candidate_pin.key, _pin(app_stored).key, adapter_contract_pin.key), 32
            )
        with self.store.snapshot() as snapshot:
            if snapshot.fingerprint != source_snapshot.fingerprint:
                raise ValueError("store changed during operation planning; replan on one exact snapshot")
            return OperationPlanRecord(
                plan_ref="operation-plan:" + semantic_fingerprint(
                    "operation-plan-ref", (source_snapshot.fingerprint, decision_pin.key, candidate_pin.key, app_stored.record_fingerprint,
                                           schema_stored.record_fingerprint, capabilities[0].record_fingerprint, adapter_stored.record_fingerprint), 24
                ),
                goal_decision_pin=decision_pin, goal_candidate_pin=candidate_pin,
                action_application_pin=_pin(app_stored), action_schema_pin=_pin(schema_stored),
                controlling_holder_ref=holder, bound_port_refs=tuple(sorted(binding_map)), capability_pin=_pin(capabilities[0]),
                adapter_contract_pin=adapter_contract_pin, authorization_input_pins=auth_pins,
                idempotency_key=idempotency_key, context_ref=app.context_ref,
                permission_ref=candidate.permission_ref, sensitivity=candidate.sensitivity,
                snapshot_revision=source_snapshot.store_revision, snapshot_fingerprint=source_snapshot.fingerprint,
            )

    def _exact(self, pin: PinnedRecord, expected_kind: RecordKind):
        if pin.record_kind != expected_kind:
            raise ValueError(f"expected {expected_kind.value} pin, got {pin.record_kind.value}")
        stored = self.store.get_record(pin.record_kind, pin.record_ref, pin.revision)
        if stored is None or stored.record_fingerprint != pin.record_fingerprint:
            raise ValueError(f"stale exact operation dependency: {pin.key}")
        return stored


@dataclass(frozen=True, slots=True)
class GateEvaluation:
    gate_ref: str
    passed: bool
    checked_pins: tuple[PinnedRecord, ...]
    evaluator_ref: str
    evaluator_revision: str
    authorization_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()
    reason_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.gate_ref.strip() or not self.evaluator_ref.strip() or not self.evaluator_revision.strip():
            raise ValueError("gate/evaluator identity must be non-empty")
        if self.passed and not self.checked_pins:
            raise ValueError("passing hard-gate evaluation requires exact checked pins")


class OperationGateEvaluator(Protocol):
    def evaluate(self, plan: OperationPlanRecord, store) -> GateEvaluation: ...


class OperationAuthorizationGate:
    """Fresh execution authorization. Phase-15 eligibility never grants execution.

    Every hard gate becomes an immutable OperationGateAssessmentRecord. ALLOW is
    valid only when exactly one current assessment exists for every required gate,
    with exact checked substrate and evaluator/proof lineage.
    """

    REQUIRED_EXTERNAL_GATES = ("permission", "resources", "risk", "preconditions")
    REQUIRED_GATES = (
        "goal_current", "target_complete", "action_execute_authorized", "live_capability",
        *REQUIRED_EXTERNAL_GATES, "adapter_available", "idempotency_recovery",
    )

    def __init__(self, store) -> None:
        self.store = store

    def authorize(
        self,
        plan: OperationPlanRecord,
        *,
        gate_evaluators: Mapping[str, OperationGateEvaluator],
    ) -> tuple[OperationAuthorizationRecord, tuple[OperationGateAssessmentRecord, ...]]:
        with self.store.snapshot() as source_snapshot:
            pass
        if source_snapshot.store_revision != plan.snapshot_revision or source_snapshot.fingerprint != plan.snapshot_fingerprint:
            raise ValueError("operation plan is no longer on the current exact store snapshot; replan before authorization")
        failed: list[str] = []
        checked: list[PinnedRecord] = []
        authorization_refs: list[str] = []
        gate_inputs: dict[str, dict[str, object]] = {
            gate: {"pins": [], "authorization_refs": [], "proof_refs": [], "reason_refs": [],
                   "evaluator_ref": "kernel:phase16-operation-gate", "evaluator_revision": "1"}
            for gate in self.REQUIRED_GATES
        }

        def add_pin(gate: str, pin: PinnedRecord) -> bool:
            stored=self.store.get_record(pin.record_kind,pin.record_ref,pin.revision)
            current=self.store.get_record(pin.record_kind,pin.record_ref)
            if stored is None or stored.record_fingerprint!=pin.record_fingerprint or current is None or current.revision!=pin.revision or current.record_fingerprint!=pin.record_fingerprint:
                failed.append(gate); return False
            checked.append(pin); gate_inputs[gate]["pins"].append(pin); return True

        # Exact built-in substrate gates.
        for gate,pin in (("goal_current",plan.goal_decision_pin),("goal_current",plan.goal_candidate_pin),
                         ("target_complete",plan.action_application_pin),("action_execute_authorized",plan.action_schema_pin),
                         ("live_capability",plan.capability_pin),("adapter_available",plan.adapter_contract_pin),
                         ("idempotency_recovery",plan.adapter_contract_pin)):
            add_pin(gate,pin)

        decision_stored=self.store.get_record(RecordKind.GOAL_DECISION,plan.goal_decision_pin.record_ref)
        if decision_stored is None or decision_stored.revision!=plan.goal_decision_pin.revision or decision_stored.record_fingerprint!=plan.goal_decision_pin.record_fingerprint:
            failed.append("goal_current")

        candidate_stored=self.store.get_record(plan.goal_candidate_pin.record_kind,plan.goal_candidate_pin.record_ref,plan.goal_candidate_pin.revision)
        if candidate_stored is None or not isinstance(candidate_stored.payload,GoalCandidateRecord) or candidate_stored.payload.operation!=UseOperation.EXECUTE or not candidate_stored.payload.authorized:
            failed.append("goal_current")
        else:
            candidate_auth={(p.record_kind,p.record_ref,p.revision,p.record_fingerprint) for p in getattr(candidate_stored.payload,"authorization_pins",())}
            for required_pin in (plan.action_application_pin,plan.action_schema_pin,plan.capability_pin):
                if (required_pin.record_kind,required_pin.record_ref,required_pin.revision,required_pin.record_fingerprint) not in candidate_auth:
                    failed.append("goal_current");gate_inputs["goal_current"]["reason_refs"].append("phase15_execute_eligibility_substrate_mismatch");break

        app_stored=self.store.get_record(plan.action_application_pin.record_kind,plan.action_application_pin.record_ref,plan.action_application_pin.revision)
        if app_stored is None or not isinstance(app_stored.payload,SemanticApplication):
            failed.append("target_complete")
        else:
            app=app_stored.payload
            schema_stored=self.store.get_record(RecordKind.SCHEMA,app.schema_ref,app.schema_revision)
            if schema_stored is None or schema_stored.record_fingerprint!=plan.action_schema_pin.record_fingerprint or not isinstance(schema_stored.payload,ActionSchema) or not schema_authorizes_use(schema_stored.payload,UseOperation.EXECUTE):
                failed.append("action_execute_authorized")
            else:
                action=schema_stored.payload
                required={p.port_ref for p in action.local_ports if p.cardinality.minimum>0}
                bound={b.port_ref for b in app.bindings if b.fillers}
                if not required.issubset(bound):failed.append("target_complete")
                if action.controlling_port_ref is None:failed.append("target_complete")
                else:
                    binding=app.binding(action.controlling_port_ref)
                    holders=tuple(f.ref for f in (() if binding is None else binding.fillers) if isinstance(f,FillerRef))
                    if holders!=(plan.controlling_holder_ref,):failed.append("target_complete")

        live=[stored for stored in self.store.records(RecordKind.CAPABILITY_INSTANCE)
              if getattr(stored.payload,"holder_ref",None)==plan.controlling_holder_ref
              and getattr(stored.payload,"action_schema_ref",None)==plan.action_schema_pin.record_ref
              and getattr(stored.payload,"action_schema_revision",None)==plan.action_schema_pin.revision
              and getattr(stored.payload,"status",None)==CapabilityStatus.AVAILABLE
              and getattr(stored.payload,"context_ref",None) in {"global",plan.context_ref}]
        if len(live)!=1 or live[0].record_ref!=plan.capability_pin.record_ref or live[0].record_fingerprint!=plan.capability_pin.record_fingerprint:failed.append("live_capability")

        adapter_stored=self.store.get_record(plan.adapter_contract_pin.record_kind,plan.adapter_contract_pin.record_ref,plan.adapter_contract_pin.revision)
        adapter=None if adapter_stored is None else adapter_stored.payload
        if not isinstance(adapter,OperationAdapterContractRecord) or not adapter.active:failed.append("adapter_available")
        if isinstance(adapter,OperationAdapterContractRecord) and adapter.retry_safe_on_unknown and adapter.idempotency_mode==IdempotencyMode.NONE:failed.append("idempotency_recovery")

        for gate in self.REQUIRED_EXTERNAL_GATES:
            evaluator=gate_evaluators.get(gate)
            if evaluator is None:
                failed.append(gate);gate_inputs[gate]["reason_refs"].append(f"missing_gate_evaluator:{gate}");continue
            try:evaluation=evaluator.evaluate(plan,self.store)
            except Exception as exc:
                failed.append(gate);gate_inputs[gate]["reason_refs"].append(f"gate_evaluator_error:{gate}:{type(exc).__name__}");continue
            if evaluation.gate_ref!=gate:
                failed.append(gate);gate_inputs[gate]["reason_refs"].append(f"gate_identity_mismatch:{gate}:{evaluation.gate_ref}");continue
            gate_inputs[gate]["evaluator_ref"]=evaluation.evaluator_ref;gate_inputs[gate]["evaluator_revision"]=evaluation.evaluator_revision
            gate_inputs[gate]["authorization_refs"].extend(evaluation.authorization_refs);gate_inputs[gate]["proof_refs"].extend(evaluation.proof_refs);gate_inputs[gate]["reason_refs"].extend(evaluation.reason_refs)
            valid=True
            for pin in evaluation.checked_pins:
                if not add_pin(gate,pin):valid=False
            if not valid:gate_inputs[gate]["reason_refs"].append(f"stale_gate_substrate:{gate}")
            if not evaluation.passed:failed.append(gate)
            authorization_refs.extend(evaluation.authorization_refs)

        failed_tuple=tuple(sorted(set(failed)))
        passed=tuple(g for g in self.REQUIRED_GATES if g not in set(failed_tuple))
        decision=OperationAuthorizationDecision.ALLOW if not failed_tuple else OperationAuthorizationDecision.DENY
        unique_checked={(p.record_kind.value,p.record_ref,p.revision,p.record_fingerprint):p for p in checked}
        with self.store.snapshot() as snapshot:
            if snapshot.fingerprint != source_snapshot.fingerprint:
                raise ValueError("store changed during hard-gate evaluation; discard assessments and re-authorize")
            plan_pin=PinnedRecord(RecordKind.OPERATION_PLAN,plan.plan_ref,plan.revision,record_fingerprints(RecordKind.OPERATION_PLAN,plan)[1])
            assessments=[]
            for gate in self.REQUIRED_GATES:
                data=gate_inputs[gate];pins=tuple(sorted({(p.record_kind.value,p.record_ref,p.revision,p.record_fingerprint):p for p in data["pins"]}.values(),key=lambda p:p.key))
                gate_passed=gate not in set(failed_tuple)
                assessment=OperationGateAssessmentRecord(
                    assessment_ref="operation-gate:"+semantic_fingerprint("operation-gate-assessment",(plan.plan_ref,gate,snapshot.fingerprint,gate_passed,tuple(p.key+(p.record_fingerprint,) for p in pins),data["evaluator_ref"],data["evaluator_revision"],tuple(sorted(set(data["authorization_refs"]))),tuple(sorted(set(data["proof_refs"]))),tuple(sorted(set(data["reason_refs"])))),24),
                    plan_pin=plan_pin,gate_ref=gate,passed=gate_passed,evaluator_ref=str(data["evaluator_ref"]),evaluator_revision=str(data["evaluator_revision"]),
                    checked_pins=pins,authorization_refs=tuple(sorted(set(data["authorization_refs"]))),proof_refs=tuple(sorted(set(data["proof_refs"]))),reason_refs=tuple(sorted(set(data["reason_refs"]))),
                    context_ref=plan.context_ref,permission_ref=plan.permission_ref,snapshot_revision=snapshot.store_revision,snapshot_fingerprint=snapshot.fingerprint,
                );assessments.append(assessment)
            assessment_pins=tuple(PinnedRecord(RecordKind.OPERATION_GATE_ASSESSMENT,a.assessment_ref,1,record_fingerprints(RecordKind.OPERATION_GATE_ASSESSMENT,a)[1]) for a in assessments)
            auth=OperationAuthorizationRecord(
                authorization_ref="operation-authorization:"+semantic_fingerprint("operation-authorization-ref",(plan.plan_ref,snapshot.fingerprint,tuple(p.key+(p.record_fingerprint,) for p in assessment_pins),failed_tuple),24),
                plan_pin=plan_pin,decision=decision,checked_pins=tuple(unique_checked[key] for key in sorted(unique_checked)),gate_assessment_pins=assessment_pins,
                passed_gates=passed,failed_gates=failed_tuple,authorization_refs=tuple(sorted(set(authorization_refs))),context_ref=plan.context_ref,permission_ref=plan.permission_ref,
                snapshot_revision=snapshot.store_revision,snapshot_fingerprint=snapshot.fingerprint,metadata={"fresh_execution_authority":True},
            )
        return auth,tuple(assessments)
