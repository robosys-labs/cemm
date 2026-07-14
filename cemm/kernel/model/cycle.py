"""KernelSnapshot and CognitiveCycle — immutable cycle artifacts.

Import boundary: standard library only → refs, identity, trace.

Per CORE_LOOP.md §3 and §1:
- KernelSnapshot pins all environment revisions for one cycle.
- CognitiveCycle is the immutable artifact carrying all stage outputs.
- Stages return new cycle revisions or typed artifacts; no hidden mutation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .identity import AssessmentEnvironmentFingerprint
from .refs import FrozenMap
from .trace import CycleTrace


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
) -> KernelSnapshot:
    """Pin a KernelSnapshot from current store revisions.

    Per CORE_LOOP.md §3, all interpretation and planning in a cycle use
    the pinned snapshot unless a learning transaction creates a child
    schema snapshot for bounded replay.
    """
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
    """Pinned environment revisions for one cognitive cycle.

    A child learning snapshot derives from this exact base; it does not
    read moving global schema state during validation.
    """
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
    def pin(
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
    ) -> KernelSnapshot:
        """Pin a snapshot from current store revisions."""
        return pin_snapshot(
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

    @property
    def fingerprint(self) -> AssessmentEnvironmentFingerprint:
        """Derive the assessment environment fingerprint from this snapshot."""
        return AssessmentEnvironmentFingerprint(
            schema_store_revision=self.schema_store_revision,
            dependency_revision_hash=f"{self.schema_store_revision}:{self.kernel_foundation_version}",
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
    """What triggered this cognitive cycle."""
    trigger_kind: str  # user_utterance, sensor, tool_result, timer, etc.
    signal_ids: tuple[str, ...] = ()
    wake_reason: str = ""


@dataclass(frozen=True, slots=True)
class CognitiveCycle:
    """Immutable artifact for one cognitive cycle.

    Stages populate fields in order per CORE_LOOP.md §4-§5.
    Each stage returns a new revision; fields are populated as stages complete.
    """
    cycle_id: str
    trigger: CycleTrigger
    snapshot: KernelSnapshot

    # Stage outputs (populated as stages complete)
    surface_evidence: tuple[Any, ...] = ()
    meaning_candidates: tuple[Any, ...] = ()
    grounded_candidates: tuple[Any, ...] = ()
    selected_interpretations: tuple[Any, ...] = ()

    workspace: Any | None = None
    retrieval_results: tuple[Any, ...] = ()
    epistemic_assessments: tuple[Any, ...] = ()
    capability_assessments: tuple[Any, ...] = ()
    gaps: tuple[Any, ...] = ()

    goals: tuple[Any, ...] = ()
    plans: tuple[Any, ...] = ()
    authorization: Any | None = None
    execution_ledger: Any | None = None

    critical_mutations: Any | None = None
    critical_commit: Any | None = None

    message_plan: Any | None = None
    output_event: Any | None = None
    output_mutations: Any | None = None
    output_commit: Any | None = None

    scheduled_wakes: tuple[Any, ...] = ()
    trace: CycleTrace | None = None
