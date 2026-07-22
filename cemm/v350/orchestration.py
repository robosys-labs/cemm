"""Canonical CEMM v3.5 Stage-0..22 orchestration boundary.

Stage names remain the v3.5 compatibility ABI until Phase 5. This module owns
generation-separated capability issuance, cycle-local workspace, bounded read
generation restarts, trace integrity, and honest final completion state.
"""
from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Mapping, Protocol, Sequence
from uuid import uuid4

from .cycle_control import CompletionEvaluator, CycleWorkspace
from .runtime_generations import ReadGeneration, ReadGenerationChanged


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
    cycle_ref: str
    stage: CoreStage
    nonce: str
    predecessor_stage: CoreStage | None
    snapshot_fingerprint: str
    authority_generation: int = 0
    authority_fingerprint: str = ""
    read_generation_fingerprint: str = ""
    cognitive_generation_fingerprint: str = ""
    store_revision: int = 0


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
    pass_ref: str = field(
        default_factory=lambda: "semantic-pass:" + uuid4().hex
    )
    pass_index: int = 0
    parent_pass_ref: str | None = None
    pass_history: list["SemanticPassSnapshot"] = field(
        default_factory=list
    )
    frontier_history: list[tuple[str, ...]] = field(
        default_factory=list
    )
    reentry_count: int = 0
    read_restart_count: int = 0
    workspace: CycleWorkspace = field(
        default_factory=CycleWorkspace
    )

    def __post_init__(self) -> None:
        self.workspace.bind(self.artifacts)


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

    def execute(
        self,
        cycle: CycleState,
        capability: StageCapability,
    ) -> StageOutcome:
        ...


class SnapshotProvider(Protocol):
    def fingerprint(self) -> str:
        ...

    def generation(self) -> ReadGeneration:
        ...


class CanonicalOrchestrationError(RuntimeError):
    pass


class CanonicalOrchestrator:
    """Sole stage-order authority for public v3.5 compatibility cycles."""

    MAX_PRECOMMIT_READ_RESTARTS = 2

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
                raise CanonicalOrchestrationError(
                    f"duplicate stage adapter: {adapter.stage.name}"
                )
            if (
                not adapter.adapter_ref
                or int(adapter.adapter_revision) < 1
            ):
                raise CanonicalOrchestrationError(
                    "stage adapters require stable ref/revision"
                )
            by_stage[adapter.stage] = adapter
        missing = tuple(
            stage
            for stage in CoreStage
            if stage not in by_stage
        )
        if missing:
            raise CanonicalOrchestrationError(
                "canonical runtime is not fully wired; missing stages: "
                + ",".join(
                    stage.name for stage in missing
                )
            )
        self.adapters = by_stage

    def _generation(
        self,
    ) -> ReadGeneration | None:
        getter = getattr(
            self.snapshot_provider,
            "generation",
            None,
        )
        return getter() if callable(getter) else None

    @staticmethod
    def _pass_snapshot(
        cycle: CycleState,
    ) -> SemanticPassSnapshot:
        return SemanticPassSnapshot(
            pass_ref=cycle.pass_ref,
            pass_index=cycle.pass_index,
            parent_pass_ref=cycle.parent_pass_ref,
            input_payload=cycle.input_payload,
            artifacts=dict(cycle.artifacts),
            frontier_refs=tuple(cycle.frontiers),
            trace=tuple(
                item
                for item in cycle.trace
                if item.get("pass_ref")
                == cycle.pass_ref
            ),
        )

    def _restart_precommit_read(
        self,
        cycle: CycleState,
        reason: str,
    ) -> None:
        cycle.read_restart_count += 1
        if (
            cycle.read_restart_count
            > self.MAX_PRECOMMIT_READ_RESTARTS
        ):
            raise CanonicalOrchestrationError(
                "bounded pre-commit read-generation "
                "restart budget exceeded"
            )
        cycle.pass_history.append(
            self._pass_snapshot(cycle)
        )
        cycle.frontier_history.append(
            tuple(cycle.frontiers)
        )
        cycle.trace.append(
            {
                "cycle_ref": cycle.cycle_ref,
                "pass_ref": cycle.pass_ref,
                "pass_index": cycle.pass_index,
                "event": "read_generation_restart",
                "reason": reason,
            }
        )
        cycle.parent_pass_ref = cycle.pass_ref
        cycle.pass_index += 1
        cycle.pass_ref = (
            "semantic-pass:" + uuid4().hex
        )
        cycle.artifacts = {}
        cycle.workspace = CycleWorkspace(
            cycle.artifacts
        )
        cycle.frontiers = []
        cycle.current_stage = None

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
        semantic_pass = getattr(self.snapshot_provider, "semantic_pass", None)
        context = semantic_pass() if callable(semantic_pass) else nullcontext()
        with context:
            return self._run_cycle(
                input_payload,
                context_ref=context_ref,
                permission_ref=permission_ref,
                audience_refs=audience_refs,
                target_language=target_language,
                channel_ref=channel_ref,
            )

    def _run_cycle(
        self,
        input_payload: Any,
        *,
        context_ref: str,
        permission_ref: str,
        audience_refs: tuple[str, ...],
        target_language: str | None,
        channel_ref: str,
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
            generation = self._generation()
            snapshot_fp = (
                generation.fingerprint
                if generation is not None
                else self.snapshot_provider.fingerprint()
            )
            capability = StageCapability(
                cycle_ref=cycle.cycle_ref,
                stage=stage,
                nonce=uuid4().hex,
                predecessor_stage=cycle.current_stage,
                snapshot_fingerprint=snapshot_fp,
                authority_generation=(
                    0
                    if generation is None
                    else generation.authority_generation
                ),
                authority_fingerprint=(
                    ""
                    if generation is None
                    else generation.authority_fingerprint
                ),
                read_generation_fingerprint=snapshot_fp,
                cognitive_generation_fingerprint=(
                    ""
                    if generation is None
                    else generation.cognitive_fingerprint
                ),
                store_revision=(
                    0
                    if generation is None
                    else generation.store_revision
                ),
            )
            adapter = self.adapters[stage]
            self.authority_guard.require_stage_adapter(
                stage=stage,
                adapter_ref=adapter.adapter_ref,
                adapter_revision=adapter.adapter_revision,
            )
            try:
                outcome = adapter.execute(
                    cycle,
                    capability,
                )
            except ReadGenerationChanged as exc:
                if int(stage) > int(
                    CoreStage.COMMIT_AUTHORIZED_KNOWLEDGE_AND_STATE
                ):
                    raise
                self._restart_precommit_read(
                    cycle,
                    str(exc),
                )
                stage_index = 0
                continue

            if not isinstance(
                outcome,
                StageOutcome,
            ):
                raise CanonicalOrchestrationError(
                    f"{adapter.adapter_ref} returned "
                    f"non-StageOutcome at {stage.name}"
                )

            cycle.current_stage = stage
            cycle.workspace.update(
                outcome.artifacts
            )
            cycle.frontiers.extend(
                outcome.frontier_refs
            )
            for ref in outcome.frontier_refs:
                cycle.workspace.register_frontier(
                    ref
                )
            cycle.workspace.register_runtime_frontiers(
                outcome.artifacts.get(
                    "runtime_frontiers",
                    (),
                )
            )
            cycle.errors.extend(
                outcome.errors
            )
            cycle.trace.append(
                {
                    "cycle_ref": cycle.cycle_ref,
                    "pass_ref": cycle.pass_ref,
                    "pass_index": cycle.pass_index,
                    "stage": int(stage),
                    "stage_name": stage.name,
                    "adapter_ref": adapter.adapter_ref,
                    "adapter_revision": (
                        adapter.adapter_revision
                    ),
                    "snapshot_fingerprint": snapshot_fp,
                    "authority_generation": (
                        capability.authority_generation
                    ),
                    "authority_fingerprint": (
                        capability.authority_fingerprint
                    ),
                    "cognitive_generation_fingerprint": (
                        capability.cognitive_generation_fingerprint
                    ),
                    "frontier_refs": (
                        outcome.frontier_refs
                    ),
                    "errors": outcome.errors,
                }
            )

            if (
                outcome.request_goal_refresh
                and outcome.reentry_request is None
            ):
                raise CanonicalOrchestrationError(
                    "direct Stage-17 -> Stage-15 refresh "
                    "is forbidden; operation outcomes "
                    "must request semantic re-entry"
                )

            if outcome.reentry_request is not None:
                if (
                    stage
                    != CoreStage.RECONCILE_OPERATION_OUTCOMES_AND_REFRESH_GOALS
                ):
                    raise CanonicalOrchestrationError(
                        "semantic re-entry may be "
                        "requested only by Stage 17"
                    )
                request = outcome.reentry_request
                cycle.reentry_count += 1
                if (
                    cycle.reentry_count
                    > int(request.max_reentries)
                ):
                    raise CanonicalOrchestrationError(
                        "bounded semantic re-entry "
                        "budget exceeded"
                    )
                cycle.pass_history.append(
                    self._pass_snapshot(cycle)
                )
                carried = cycle.workspace.carry(
                    request.carry_artifact_keys
                )
                cycle.frontier_history.append(
                    tuple(cycle.frontiers)
                )
                cycle.parent_pass_ref = (
                    cycle.pass_ref
                )
                cycle.pass_index += 1
                cycle.pass_ref = (
                    "semantic-pass:"
                    + uuid4().hex
                )
                cycle.input_payload = (
                    request.observation_batch
                )
                cycle.workspace = carried
                cycle.artifacts = (
                    carried.artifacts
                )
                cycle.frontiers = []
                cycle.current_stage = None
                stage_index = 0
                continue

            if outcome.terminal:
                break
            stage_index += 1

        cycle.pass_history.append(
            self._pass_snapshot(cycle)
        )
        cycle.artifacts[
            "semantic_pass_history"
        ] = tuple(cycle.pass_history)
        status = CompletionEvaluator().evaluate(
            cycle
        )
        cycle.artifacts[
            "cycle_completion_status"
        ] = status.value
        cycle.artifacts[
            "frontier_effects"
        ] = {
            ref: tuple(
                sorted(
                    effect.value
                    for effect in effects
                )
            )
            for ref, effects in sorted(
                cycle.workspace.frontier_effects.items()
            )
        }
        return cycle
