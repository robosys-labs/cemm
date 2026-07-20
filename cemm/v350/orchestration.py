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
    # Compatibility field only. Direct Stage-17 -> Stage-15 jumps are no longer
    # semantic authority; operation feedback must use reentry_request.
    refresh_goal_stage15: bool = False
    pass_ref: str = field(default_factory=lambda: "semantic-pass:" + uuid4().hex)
    pass_index: int = 0
    parent_pass_ref: str | None = None
    pass_history: list[SemanticPassSnapshot] = field(default_factory=list)
    frontier_history: list[tuple[str, ...]] = field(default_factory=list)
    reentry_count: int = 0


@dataclass(frozen=True, slots=True)
class SemanticPassSnapshot:
    pass_ref: str
    pass_index: int
    parent_pass_ref: str | None
    input_payload: Any
    artifacts: Mapping[str, Any]
    frontier_refs: tuple[str, ...]
    trace: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True, slots=True)
class StageOutcome:
    artifacts: Mapping[str, Any] = field(default_factory=dict)
    frontier_refs: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    request_goal_refresh: bool = False
    reentry_request: Any | None = None
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
        while stage_index < len(stage_order):
            stage = stage_order[stage_index]
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
            cycle.trace.append({
                "cycle_ref": cycle.cycle_ref,
                "pass_ref": cycle.pass_ref,
                "pass_index": cycle.pass_index,
                "stage": int(stage),
                "stage_name": stage.name,
                "adapter_ref": adapter.adapter_ref,
                "adapter_revision": adapter.adapter_revision,
                "snapshot_fingerprint": snapshot_fp,
                "frontier_refs": outcome.frontier_refs,
                "errors": outcome.errors,
            })

            if outcome.request_goal_refresh and outcome.reentry_request is None:
                raise CanonicalOrchestrationError(
                    "direct Stage-17 -> Stage-15 refresh is forbidden; "
                    "operation outcomes must request semantic re-entry"
                )

            if outcome.reentry_request is not None:
                if stage != CoreStage.RECONCILE_OPERATION_OUTCOMES_AND_REFRESH_GOALS:
                    raise CanonicalOrchestrationError(
                        "semantic re-entry may be requested only by Stage 17"
                    )
                request = outcome.reentry_request
                cycle.reentry_count += 1
                if cycle.reentry_count > int(request.max_reentries):
                    raise CanonicalOrchestrationError(
                        "bounded semantic re-entry budget exceeded"
                    )
                cycle.pass_history.append(
                    SemanticPassSnapshot(
                        pass_ref=cycle.pass_ref,
                        pass_index=cycle.pass_index,
                        parent_pass_ref=cycle.parent_pass_ref,
                        input_payload=cycle.input_payload,
                        artifacts=dict(cycle.artifacts),
                        frontier_refs=tuple(cycle.frontiers),
                        trace=tuple(
                            item for item in cycle.trace
                            if item.get("pass_ref") == cycle.pass_ref
                        ),
                    )
                )
                carried = {
                    key: cycle.artifacts[key]
                    for key in request.carry_artifact_keys
                    if key in cycle.artifacts
                }
                cycle.frontier_history.append(tuple(cycle.frontiers))
                cycle.parent_pass_ref = cycle.pass_ref
                cycle.pass_index += 1
                cycle.pass_ref = "semantic-pass:" + uuid4().hex
                cycle.input_payload = request.observation_batch
                cycle.artifacts = carried
                cycle.frontiers = []
                cycle.current_stage = None
                stage_index = 0
                continue

            if outcome.terminal:
                break
            stage_index += 1

        cycle.pass_history.append(
            SemanticPassSnapshot(
                pass_ref=cycle.pass_ref,
                pass_index=cycle.pass_index,
                parent_pass_ref=cycle.parent_pass_ref,
                input_payload=cycle.input_payload,
                artifacts=dict(cycle.artifacts),
                frontier_refs=tuple(cycle.frontiers),
                trace=tuple(
                    item for item in cycle.trace if item.get("pass_ref") == cycle.pass_ref
                ),
            )
        )
        cycle.artifacts["semantic_pass_history"] = tuple(cycle.pass_history)
        return cycle
