"""KernelSnapshot and CognitiveCycle — immutable cycle artifacts.

The cycle carries response intents as an explicit DECIDE-stage artifact.  The
response planner consumes only this field; selected input interpretations are
not implicitly echoed as output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .identity import AssessmentEnvironmentFingerprint
from .trace import CycleTrace
from .signal import InputSignal


def pin_snapshot(
    *,
    schema_store_revision: int = 0,
    semantic_memory_revision: int = 0,
    episodic_event_revision: int = 0,
    common_ground_revision: int = 0,
    self_health_revision: int = 0,
    resource_revision: int = 0,
    permission_policy_revision: int = 0,
    active_goal_revision: int = 0,
    learning_transaction_revision: int = 0,
    competence_suite_hash: str = "",
    grounding_policy_version: str = "",
    kernel_foundation_version: str = "",
    type_registry_version: str = "",
    inference_policy_version: str = "",
    truth_maintenance_version: str = "",
    adapter_contract_hash: str = "",
    context_scope_policy_version: str = "",
) -> "KernelSnapshot":
    return KernelSnapshot(
        schema_store_revision=schema_store_revision,
        semantic_memory_revision=semantic_memory_revision,
        episodic_event_revision=episodic_event_revision,
        common_ground_revision=common_ground_revision,
        self_health_revision=self_health_revision,
        resource_revision=resource_revision,
        permission_policy_revision=permission_policy_revision,
        active_goal_revision=active_goal_revision,
        learning_transaction_revision=learning_transaction_revision,
        competence_suite_hash=competence_suite_hash,
        grounding_policy_version=grounding_policy_version,
        kernel_foundation_version=kernel_foundation_version,
        type_registry_version=type_registry_version,
        inference_policy_version=inference_policy_version,
        truth_maintenance_version=truth_maintenance_version,
        adapter_contract_hash=adapter_contract_hash,
        context_scope_policy_version=context_scope_policy_version,
    )


@dataclass(frozen=True, slots=True)
class KernelSnapshot:
    schema_store_revision: int = 0
    semantic_memory_revision: int = 0
    episodic_event_revision: int = 0
    common_ground_revision: int = 0
    self_health_revision: int = 0
    resource_revision: int = 0
    permission_policy_revision: int = 0
    active_goal_revision: int = 0
    learning_transaction_revision: int = 0
    competence_suite_hash: str = ""
    grounding_policy_version: str = ""
    kernel_foundation_version: str = ""
    type_registry_version: str = ""
    inference_policy_version: str = ""
    truth_maintenance_version: str = ""
    adapter_contract_hash: str = ""
    context_scope_policy_version: str = ""
    clock_observation: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @staticmethod
    def pin(**kwargs: Any) -> "KernelSnapshot":
        return pin_snapshot(**kwargs)

    @property
    def fingerprint(self) -> AssessmentEnvironmentFingerprint:
        return AssessmentEnvironmentFingerprint(
            schema_store_revision=self.schema_store_revision,
            dependency_revision_hash=(
                f"{self.schema_store_revision}:"
                f"{self.kernel_foundation_version}"
            ),
            grounding_policy_version=self.grounding_policy_version,
            competency_suite_hash=self.competence_suite_hash,
            kernel_foundation_version=self.kernel_foundation_version,
            type_registry_version=self.type_registry_version,
            inference_policy_version=self.inference_policy_version,
            truth_maintenance_version=self.truth_maintenance_version,
            adapter_contract_hash=self.adapter_contract_hash,
            context_scope_policy_version=self.context_scope_policy_version,
        )


@dataclass(frozen=True, slots=True)
class CycleTrigger:
    trigger_kind: str
    signal_ids: tuple[str, ...] = ()
    input_signals: tuple[InputSignal, ...] = ()
    context_id: str = "default"
    wake_reason: str = ""


@dataclass(frozen=True, slots=True)
class CognitiveCycle:
    cycle_id: str
    trigger: CycleTrigger
    snapshot: KernelSnapshot

    surface_evidence: tuple[Any, ...] = ()
    meaning_candidates: tuple[Any, ...] = ()
    grounded_candidates: tuple[Any, ...] = ()
    selected_interpretations: tuple[Any, ...] = ()
    dialogue_resolution: Any | None = None
    dialogue_obligations: tuple[Any, ...] = ()

    workspace: Any | None = None
    retrieval_results: tuple[Any, ...] = ()
    epistemic_assessments: tuple[Any, ...] = ()
    capability_assessments: tuple[Any, ...] = ()
    knowledge_assessments: tuple[Any, ...] = ()
    inference_outcomes: tuple[Any, ...] = ()
    inference_proofs: tuple[Any, ...] = ()
    existential_constraints: tuple[Any, ...] = ()
    inference_commit: Any | None = None
    rule_learning_results: tuple[Any, ...] = ()
    self_reports: tuple[Any, ...] = ()
    gaps: tuple[Any, ...] = ()

    goals: tuple[Any, ...] = ()
    plans: tuple[Any, ...] = ()
    authorization: Any | None = None
    execution_ledger: Any | None = None
    reconciliation_result: Any | None = None

    critical_mutations: Any | None = None
    critical_commit: Any | None = None

    response_intents: tuple[Any, ...] = ()
    message_plan: Any | None = None
    realization_authorization: Any | None = None
    surface_payload: Any | None = None
    output_event: Any | None = None
    output_mutations: Any | None = None
    output_commit: Any | None = None

    learning_transactions: tuple[Any, ...] = ()
    invalidation_result: Any | None = None
    repair_obligations: tuple[Any, ...] = ()
    scheduled_wakes: tuple[Any, ...] = ()
    trace: CycleTrace | None = None
