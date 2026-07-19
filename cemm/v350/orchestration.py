"""Canonical CEMM v3.5 Stage-0..22 orchestration boundary.

This module is intentionally domain-light.  It owns stage order, snapshot refresh
boundaries, capability issuance, trace integrity, and fail-closed control flow.
Semantic decisions remain inside the independently-authorized phase components.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Mapping, Protocol, Sequence
from uuid import uuid4


class CoreStage(IntEnum):
    ORIENT_AND_PIN = 0
    OBSERVE = 1
    ANALYZE_AND_FUSE_FORM = 2
    GENERATE_REFERENT_AND_SCHEMA_CANDIDATES = 3
    PROJECT_REFERENT_KNOWLEDGE_AND_ENTITLEMENTS = 4
    BUILD_UOL_FACTOR_GRAPH = 5
    SOLVE_MEANING_HYPOTHESES = 6
    SELECT_MEANING_BUNDLE = 7
    CLASSIFY_DISCOURSE_CLAIMS_EVENTS_AND_GAPS = 8
    EPISTEMICALLY_ASSESS_AND_PLACE_CONTEXT = 9
    RETRIEVE_AND_ANSWER_BIND = 10
    BUILD_OR_ADVANCE_LEARNING_FRONTIERS = 11
    INFER_AND_PREVIEW_TRANSITIONS = 12
    COMMIT_AUTHORIZED_KNOWLEDGE_AND_STATE = 13
    ASSESS_IMPACT_AND_IMPORTANCE = 14
    DERIVE_OBLIGATIONS_GENERATE_AND_ARBITRATE_GOALS = 15
    PLAN_AUTHORIZE_EXECUTE_AND_RECONCILE = 16
    RECONCILE_OPERATION_OUTCOMES_AND_REFRESH_GOALS = 17
    BUILD_RESPONSE_UOL = 18
    REALIZE_TARGET_LANGUAGE = 19
    VERIFY_AND_AUTHORIZE_EMISSION = 20
    COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND = 21
    INVALIDATE_RECOMPUTE_AND_FINALIZE = 22


@dataclass(frozen=True, slots=True)
class StageCapability:
    """Unforgeable-by-convention orchestration capability for one cycle/stage.

    Semantic components must not accept a plain stage-name string as authority.
    Runtime adapters should validate this exact object against the cycle token.
    """

    cycle_ref: str
    stage: CoreStage
    nonce: str
    predecessor_stage: CoreStage | None
    snapshot_fingerprint: str


@dataclass(slots=True)
class CycleState:
    cycle_ref: str
    context_ref: str
    permission_ref: str
    audience_refs: tuple[str, ...]
    input_payload: Any
    target_language: str | None
    channel_ref: str
    artifacts: dict[str, Any] = field(default_factory=dict)
    frontiers: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    trace: list[Mapping[str, Any]] = field(default_factory=list)
    current_stage: CoreStage | None = None
    refresh_goal_stage15: bool = False


@dataclass(frozen=True, slots=True)
class StageOutcome:
    artifacts: Mapping[str, Any] = field(default_factory=dict)
    frontier_refs: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    request_goal_refresh: bool = False
    terminal: bool = False


class StageAdapter(Protocol):
    stage: CoreStage
    adapter_ref: str
    adapter_revision: int

    def execute(self, cycle: CycleState, capability: StageCapability) -> StageOutcome: ...


class SnapshotProvider(Protocol):
    def fingerprint(self) -> str: ...


class CanonicalOrchestrationError(RuntimeError):
    pass


class CanonicalOrchestrator:
    """Sole stage-order authority for public v3.5 semantic cycles."""

    def __init__(
        self,
        adapters: Sequence[StageAdapter],
        *,
        snapshot_provider: SnapshotProvider,
        authority_guard: Any,
    ) -> None:
        self.snapshot_provider = snapshot_provider
        self.authority_guard = authority_guard
        by_stage: dict[CoreStage, StageAdapter] = {}
        for adapter in adapters:
            if adapter.stage in by_stage:
                raise CanonicalOrchestrationError(f"duplicate stage adapter: {adapter.stage.name}")
            if not adapter.adapter_ref or int(adapter.adapter_revision) < 1:
                raise CanonicalOrchestrationError("stage adapters require stable ref/revision")
            by_stage[adapter.stage] = adapter
        missing = tuple(stage for stage in CoreStage if stage not in by_stage)
        if missing:
            raise CanonicalOrchestrationError(
                "canonical runtime is not fully wired; missing stages: "
                + ",".join(stage.name for stage in missing)
            )
        self.adapters = by_stage

    def run(
        self,
        input_payload: Any,
        *,
        context_ref: str,
        permission_ref: str = "conversation",
        audience_refs: tuple[str, ...] = (),
        target_language: str | None = None,
        channel_ref: str = "text",
    ) -> CycleState:
        self.authority_guard.require_service_authority()
        cycle = CycleState(
            cycle_ref="cycle:" + uuid4().hex,
            context_ref=context_ref,
            permission_ref=permission_ref,
            audience_refs=tuple(audience_refs),
            input_payload=input_payload,
            target_language=target_language,
            channel_ref=channel_ref,
        )
        stage_index = 0
        stage_order = tuple(CoreStage)
        refresh_count = 0
        while stage_index < len(stage_order):
            stage = stage_order[stage_index]
            # Stage 17 may force a semantic re-entry to the sole generic goal
            # authority at Stage 15.  It may not create another goal family.
            if stage == CoreStage.BUILD_RESPONSE_UOL and cycle.refresh_goal_stage15:
                refresh_count += 1
                if refresh_count > 1:
                    raise CanonicalOrchestrationError("bounded Stage-15 goal refresh exceeded")
                cycle.refresh_goal_stage15 = False
                stage_index = stage_order.index(
                    CoreStage.DERIVE_OBLIGATIONS_GENERATE_AND_ARBITRATE_GOALS
                )
                continue
            snapshot_fp = self.snapshot_provider.fingerprint()
            predecessor = cycle.current_stage
            capability = StageCapability(
                cycle_ref=cycle.cycle_ref,
                stage=stage,
                nonce=uuid4().hex,
                predecessor_stage=predecessor,
                snapshot_fingerprint=snapshot_fp,
            )
            adapter = self.adapters[stage]
            self.authority_guard.require_stage_adapter(
                stage=stage,
                adapter_ref=adapter.adapter_ref,
                adapter_revision=adapter.adapter_revision,
            )
            outcome = adapter.execute(cycle, capability)
            if not isinstance(outcome, StageOutcome):
                raise CanonicalOrchestrationError(
                    f"{adapter.adapter_ref} returned non-StageOutcome at {stage.name}"
                )
            cycle.current_stage = stage
            cycle.artifacts.update(dict(outcome.artifacts))
            cycle.frontiers.extend(outcome.frontier_refs)
            cycle.errors.extend(outcome.errors)
            cycle.refresh_goal_stage15 = cycle.refresh_goal_stage15 or outcome.request_goal_refresh
            cycle.trace.append({
                "cycle_ref": cycle.cycle_ref,
                "stage": int(stage),
                "stage_name": stage.name,
                "adapter_ref": adapter.adapter_ref,
                "adapter_revision": adapter.adapter_revision,
                "snapshot_fingerprint": snapshot_fp,
                "frontier_refs": outcome.frontier_refs,
                "errors": outcome.errors,
            })
            if outcome.terminal:
                break
            stage_index += 1
        return cycle
