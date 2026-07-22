"""Canonical v3.5.1 Stage-0..22 orchestration.

The orchestrator owns stage order, generation/effect matrix enforcement, bounded
re-entry and contract validation.  It contains no domain semantics and no legacy UOL
stage aliases.
"""
from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence
from uuid import uuid4

from .cycle_control import CompletionEvaluator, CycleWorkspace
from .effects.authorization import EffectAuthorizationReceipt
from .runtime_generations import GenerationDomain, ReadGeneration, ReadGenerationChanged
from .stage_contracts import CoreStage, EffectKind, StageContract, canonical_stage_contracts, stage_contract


class StageExecutionStatus(str, Enum):
    PERFORMED = "performed"
    DEFERRED = "deferred"
    BLOCKED = "blocked"
    NO_AUTHORIZED_WORK = "no_authorized_work"


@dataclass(frozen=True, slots=True)
class StageCapability:
    cycle_ref: str
    pass_ref: str
    stage: CoreStage
    nonce: str
    predecessor_stage: CoreStage | None
    authority_generation: int
    authority_fingerprint: str
    read_generation: ReadGeneration

    def __post_init__(self) -> None:
        if not self.cycle_ref or not self.pass_ref or not self.nonce:
            raise ValueError("stage capability requires cycle/pass/nonce identity")
        if self.authority_generation != self.read_generation.authority_generation:
            raise ValueError("stage capability authority/read generation mismatch")
        if self.authority_fingerprint != self.read_generation.authority_fingerprint:
            raise ValueError("stage capability authority fingerprint mismatch")


@dataclass(slots=True)
class CognitiveCycleState:
    cycle_ref: str
    context_ref: str
    permission_ref: str
    audience_refs: tuple[str, ...]
    input_payload: Any
    target_language: str | None
    channel_ref: str
    workspace: CycleWorkspace = field(default_factory=CycleWorkspace)
    frontiers: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    trace: list[Mapping[str, Any]] = field(default_factory=list)
    current_stage: CoreStage | None = None
    pass_ref: str = field(default_factory=lambda: "semantic-pass:" + uuid4().hex)
    pass_index: int = 0
    parent_pass_ref: str | None = None
    pass_history: list[Mapping[str, Any]] = field(default_factory=list)
    reentry_count: int = 0
    read_restart_count: int = 0
    pass_read_generation: ReadGeneration | None = None

    @property
    def artifacts(self) -> dict[str, Any]:
        return self.workspace.artifacts


@dataclass(frozen=True, slots=True)
class StageOutcome:
    status: StageExecutionStatus
    artifacts: Mapping[str, Any] = field(default_factory=dict)
    frontier_refs: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    reentry_request: Any | None = None
    terminal: bool = False


class StageAdapter(Protocol):
    stage: CoreStage
    adapter_ref: str
    adapter_revision: int

    def execute(self, cycle: CognitiveCycleState, capability: StageCapability) -> StageOutcome: ...


class SnapshotProvider(Protocol):
    def generation(self) -> ReadGeneration: ...
    def semantic_pass(self): ...


class CanonicalOrchestrationError(RuntimeError):
    pass


class StageContractViolation(CanonicalOrchestrationError):
    pass


def _changed_domains(before: ReadGeneration, after: ReadGeneration) -> frozenset[GenerationDomain]:
    changed = set()
    if (before.authority_generation, before.authority_fingerprint) != (after.authority_generation, after.authority_fingerprint):
        changed.add(GenerationDomain.AUTHORITY)
    if before.world_revision != after.world_revision:
        changed.add(GenerationDomain.WORLD)
    if before.discourse_revision != after.discourse_revision:
        changed.add(GenerationDomain.DISCOURSE)
    if before.runtime_observation_revision != after.runtime_observation_revision:
        changed.add(GenerationDomain.RUNTIME_OBSERVATION)
    if before.audit_revision != after.audit_revision:
        changed.add(GenerationDomain.AUDIT)
    if before.effect_journal_revision != after.effect_journal_revision:
        changed.add(GenerationDomain.EFFECT_JOURNAL)
    return frozenset(changed)


class CanonicalOrchestrator:
    MAX_PRECOMMIT_READ_RESTARTS = 2

    def __init__(self, adapters: Sequence[StageAdapter], *, snapshot_provider: SnapshotProvider, authority_guard: Any) -> None:
        self.snapshot_provider = snapshot_provider
        self.authority_guard = authority_guard
        self.contracts = {c.stage: c for c in canonical_stage_contracts()}
        by_stage = {}
        for adapter in adapters:
            if adapter.stage in by_stage:
                raise CanonicalOrchestrationError(f"duplicate stage adapter:{adapter.stage.name}")
            by_stage[adapter.stage] = adapter
        if tuple(sorted(by_stage, key=int)) != tuple(CoreStage):
            raise CanonicalOrchestrationError("canonical adapters must cover exact v3.5.1 Stage 0..22")
        self.adapters = by_stage

    def _make_capability(self, cycle: CognitiveCycleState, stage: CoreStage) -> StageCapability:
        current = self.snapshot_provider.generation()
        if cycle.pass_read_generation is None:
            cycle.pass_read_generation = current
        pinned = cycle.pass_read_generation
        if (current.authority_generation, current.authority_fingerprint) != (
            pinned.authority_generation, pinned.authority_fingerprint
        ):
            raise ReadGenerationChanged("authority generation changed inside semantic pass")
        # Before the first durable commit, a pass may not silently float to a newer
        # world/discourse/runtime-observation generation. Audit/effect-only movement
        # is intentionally irrelevant to cognitive consistency.
        if current.cognitive_fingerprint != pinned.cognitive_fingerprint:
            if int(stage) <= int(CoreStage.COMMIT_AUTHORIZED_KNOWLEDGE_STATE_AND_LEARNING_ARTIFACTS):
                raise ReadGenerationChanged("cognitive read generation changed before first commit")
            raise CanonicalOrchestrationError(
                "post-commit cognitive generation changed outside the prior stage boundary; replay required"
            )
        return StageCapability(
            cycle_ref=cycle.cycle_ref,
            pass_ref=cycle.pass_ref,
            stage=stage,
            nonce=uuid4().hex,
            predecessor_stage=cycle.current_stage,
            authority_generation=pinned.authority_generation,
            authority_fingerprint=pinned.authority_fingerprint,
            read_generation=pinned,
        )

    @staticmethod
    def _validate_outcome(contract: StageContract, outcome: StageOutcome) -> None:
        undeclared = set(outcome.artifacts).difference(contract.produced_outputs)
        # Internal tracing keys use a private prefix and are not cross-stage ABI.
        undeclared = {key for key in undeclared if not key.startswith("_")}
        if undeclared:
            raise StageContractViolation(
                f"{contract.stage.name} emitted undeclared artifacts:{sorted(undeclared)}"
            )
        if outcome.status == StageExecutionStatus.PERFORMED:
            missing = set(contract.required_outputs_on_performed).difference(outcome.artifacts)
            if missing:
                raise StageContractViolation(
                    f"{contract.stage.name} performed without required outputs:{sorted(missing)}"
                )

    @staticmethod
    def _pass_snapshot(cycle: CognitiveCycleState) -> Mapping[str, Any]:
        return {
            "pass_ref": cycle.pass_ref,
            "pass_index": cycle.pass_index,
            "parent_pass_ref": cycle.parent_pass_ref,
            "frontier_refs": tuple(cycle.frontiers),
            "trace": tuple(x for x in cycle.trace if x.get("pass_ref") == cycle.pass_ref),
        }

    def _restart_precommit(self, cycle: CognitiveCycleState, reason: str) -> None:
        cycle.read_restart_count += 1
        if cycle.read_restart_count > self.MAX_PRECOMMIT_READ_RESTARTS:
            raise CanonicalOrchestrationError("bounded read-generation restart budget exceeded")
        cycle.pass_history.append(self._pass_snapshot(cycle))
        cycle.trace.append({
            "cycle_ref": cycle.cycle_ref, "pass_ref": cycle.pass_ref,
            "pass_index": cycle.pass_index, "event": "read_generation_restart", "reason": reason,
        })
        cycle.parent_pass_ref = cycle.pass_ref
        cycle.pass_index += 1
        cycle.pass_ref = "semantic-pass:" + uuid4().hex
        cycle.workspace = CycleWorkspace()
        cycle.frontiers = []
        cycle.current_stage = None
        cycle.pass_read_generation = None

    def _enforce_generation_matrix(self, contract: StageContract, before: ReadGeneration, after: ReadGeneration) -> None:
        changed = _changed_domains(before, after)
        forbidden = changed.difference(contract.allowed_generation_changes)
        if forbidden:
            raise StageContractViolation(
                f"{contract.stage.name} changed forbidden generations:{sorted(x.value for x in forbidden)}"
            )

    @staticmethod
    def _enforce_effect_receipts(
        contract: StageContract,
        outcome: StageOutcome,
        changed: frozenset[GenerationDomain],
        capability: StageCapability,
        permission_ref: str,
        before: ReadGeneration,
        after: ReadGeneration,
    ) -> None:
        durable_changed = bool(
            changed.intersection({
                GenerationDomain.WORLD, GenerationDomain.DISCOURSE,
                GenerationDomain.AUDIT, GenerationDomain.EFFECT_JOURNAL,
            })
        )
        operation_observed = bool(outcome.artifacts.get("operation_observations"))
        emission_observed = outcome.artifacts.get("emission_observation") is not None
        if not (durable_changed or operation_observed or emission_observed):
            return

        receipts = tuple(outcome.artifacts.get("_effect_authorization_receipts", ()) or ())
        if not receipts:
            raise StageContractViolation(
                f"{contract.stage.name} performed effectful work without EffectAuthorizationBoundary receipt"
            )
        receipt_kinds = set()
        for receipt in receipts:
            if not isinstance(receipt, EffectAuthorizationReceipt) or not receipt.allowed:
                raise StageContractViolation(f"{contract.stage.name} contains invalid/denied effect receipt")
            if (
                receipt.cycle_ref != capability.cycle_ref
                or receipt.pass_ref != capability.pass_ref
                or receipt.capability_nonce != capability.nonce
            ):
                raise StageContractViolation(
                    f"{contract.stage.name} effect receipt belongs to another cycle/pass/capability"
                )
            if receipt.stage != contract.stage:
                raise StageContractViolation(f"{contract.stage.name} received receipt for another stage")
            if (
                receipt.authority_generation != capability.authority_generation
                or receipt.authority_fingerprint != capability.authority_fingerprint
            ):
                raise StageContractViolation(
                    f"{contract.stage.name} effect receipt belongs to another authority generation"
                )
            if receipt.permission_ref not in {"public", permission_ref}:
                raise StageContractViolation(
                    f"{contract.stage.name} effect receipt widens permission scope"
                )
            if receipt.effect_kind not in contract.allowed_effects:
                raise StageContractViolation(
                    f"{contract.stage.name} effect receipt kind not allowed:{receipt.effect_kind.value}"
                )
            receipt_kinds.add(receipt.effect_kind)

        if durable_changed:
            persistence_receipts = tuple(
                receipt for receipt in receipts
                if receipt.effect_kind is EffectKind.DURABLE_PERSISTENCE
            )
            if not persistence_receipts:
                raise StageContractViolation(
                    f"{contract.stage.name} durable generation change requires persistence authorization receipt"
                )
            if any(
                not receipt.patch_ref or not receipt.patch_fingerprint
                or receipt.store_revision_before is None
                for receipt in persistence_receipts
            ):
                raise StageContractViolation(
                    f"{contract.stage.name} persistence receipt lacks exact patch/CAS identity"
                )
            expected_revisions = set(range(before.store_revision, after.store_revision))
            observed_revisions = {int(receipt.store_revision_before) for receipt in persistence_receipts}
            if observed_revisions != expected_revisions:
                raise StageContractViolation(
                    f"{contract.stage.name} persistence receipts do not cover every committed store revision"
                )
            patch_refs = tuple(receipt.patch_ref for receipt in persistence_receipts)
            if len(patch_refs) != len(set(patch_refs)):
                raise StageContractViolation(
                    f"{contract.stage.name} duplicate persistence receipt patch identity"
                )
            receipt_domains = {
                GenerationDomain(value)
                for receipt in persistence_receipts
                for value in receipt.patch_generation_domains
            }
            if not changed.issubset(receipt_domains):
                missing = sorted(domain.value for domain in changed.difference(receipt_domains))
                raise StageContractViolation(
                    f"{contract.stage.name} generation changes lack pre-effect receipt coverage:{missing}"
                )
        if operation_observed and EffectKind.EXTERNAL_OPERATION not in receipt_kinds:
            raise StageContractViolation(
                f"{contract.stage.name} operation observation requires external-operation authorization receipt"
            )
        if emission_observed:
            required = {EffectKind.PROTECTED_DISCLOSURE, EffectKind.EXTERNAL_EMISSION}
            if not required.issubset(receipt_kinds):
                raise StageContractViolation(
                    f"{contract.stage.name} emission requires disclosure and emission authorization receipts"
                )

    def run(self, input_payload: Any, *, context_ref: str, permission_ref: str = "conversation",
            audience_refs: tuple[str, ...] = (), target_language: str | None = None,
            channel_ref: str = "text") -> CognitiveCycleState:
        self.authority_guard.require_service_authority()
        semantic_pass = getattr(self.snapshot_provider, "semantic_pass", None)
        cm = semantic_pass() if callable(semantic_pass) else nullcontext()
        with cm:
            return self._run_cycle(
                input_payload, context_ref=context_ref, permission_ref=permission_ref,
                audience_refs=audience_refs, target_language=target_language, channel_ref=channel_ref,
            )

    def _run_cycle(self, input_payload: Any, *, context_ref: str, permission_ref: str,
                   audience_refs: tuple[str, ...], target_language: str | None,
                   channel_ref: str) -> CognitiveCycleState:
        cycle = CognitiveCycleState(
            cycle_ref="cycle:" + uuid4().hex,
            context_ref=context_ref, permission_ref=permission_ref,
            audience_refs=tuple(audience_refs), input_payload=input_payload,
            target_language=target_language, channel_ref=channel_ref,
        )
        order = tuple(CoreStage)
        index = 0
        while index < len(order):
            stage = order[index]
            contract = self.contracts[stage]
            try:
                capability = self._make_capability(cycle, stage)
            except ReadGenerationChanged as exc:
                if int(stage) > int(CoreStage.COMMIT_AUTHORIZED_KNOWLEDGE_STATE_AND_LEARNING_ARTIFACTS):
                    raise
                self._restart_precommit(cycle, str(exc))
                index = 0
                continue
            missing_inputs = tuple(key for key in contract.required_inputs if key not in cycle.artifacts)
            adapter = self.adapters[stage]
            self.authority_guard.require_stage_adapter(
                stage=stage, adapter_ref=adapter.adapter_ref, adapter_revision=adapter.adapter_revision
            )
            before = self.snapshot_provider.generation()
            try:
                if missing_inputs:
                    outcome = StageOutcome(
                        StageExecutionStatus.DEFERRED,
                        frontier_refs=tuple(f"frontier:stage:{int(stage)}:missing:{key}" for key in missing_inputs),
                    )
                else:
                    outcome = adapter.execute(cycle, capability)
            except ReadGenerationChanged as exc:
                if int(stage) > int(CoreStage.COMMIT_AUTHORIZED_KNOWLEDGE_STATE_AND_LEARNING_ARTIFACTS):
                    raise
                self._restart_precommit(cycle, str(exc))
                index = 0
                continue
            if not isinstance(outcome, StageOutcome):
                raise CanonicalOrchestrationError(f"{adapter.adapter_ref} returned non-StageOutcome")
            after = self.snapshot_provider.generation()
            self._enforce_generation_matrix(contract, before, after)
            self._validate_outcome(contract, outcome)
            self._enforce_effect_receipts(
                contract, outcome, _changed_domains(before, after), capability,
                cycle.permission_ref, before, after,
            )
            # Explicit stage-authorized commits advance the pass read generation. This
            # is the only way the pass moves to a new mutable generation without a
            # restart/replay boundary.
            if _changed_domains(before, after):
                cycle.pass_read_generation = after

            cycle.current_stage = stage
            cycle.workspace.update(outcome.artifacts)
            cycle.frontiers.extend(outcome.frontier_refs)
            for ref in outcome.frontier_refs:
                cycle.workspace.register_frontier(ref)
            cycle.workspace.register_runtime_frontiers(outcome.artifacts.get("_runtime_frontiers", ()))
            cycle.errors.extend(outcome.errors)
            cycle.trace.append({
                "cycle_ref": cycle.cycle_ref, "pass_ref": cycle.pass_ref, "pass_index": cycle.pass_index,
                "stage": int(stage), "stage_name": stage.name, "adapter_ref": adapter.adapter_ref,
                "adapter_revision": adapter.adapter_revision, "status": outcome.status.value,
                "authority_generation": capability.authority_generation,
                "authority_fingerprint": capability.authority_fingerprint,
                "read_generation": capability.read_generation.fingerprint,
                "generation_changes": tuple(sorted(x.value for x in _changed_domains(before, after))),
                "frontier_refs": outcome.frontier_refs, "errors": outcome.errors,
            })

            if outcome.reentry_request is not None:
                if stage != CoreStage.ASSIMILATE_OPERATION_OUTCOMES_AND_RECUR:
                    raise CanonicalOrchestrationError("only Stage 17 may request semantic re-entry")
                request = outcome.reentry_request
                cycle.reentry_count += 1
                if cycle.reentry_count > int(request.max_reentries):
                    raise CanonicalOrchestrationError("bounded semantic re-entry budget exceeded")
                cycle.pass_history.append(self._pass_snapshot(cycle))
                carry = cycle.workspace.carry(request.carry_artifact_keys)
                cycle.parent_pass_ref = cycle.pass_ref
                cycle.pass_index += 1
                cycle.pass_ref = "semantic-pass:" + uuid4().hex
                cycle.input_payload = request.observation_batch
                cycle.workspace = carry
                cycle.frontiers = []
                cycle.current_stage = None
                cycle.pass_read_generation = None
                index = 0
                continue

            if outcome.terminal:
                break
            index += 1

        cycle.pass_history.append(self._pass_snapshot(cycle))
        cycle.artifacts["semantic_pass_history"] = tuple(cycle.pass_history)
        # Stage 22 owns the canonical final status when implemented.  The evaluator is
        # a defensive fallback, never a synonym for errors==[].
        cycle.artifacts.setdefault("cycle_completion_status", CompletionEvaluator().evaluate(cycle).value)
        return cycle


# Deliberately no CycleState alias: stale v3.5 callers must migrate rather than
# silently receiving a different semantic contract.
__all__ = [
    "CanonicalOrchestrationError", "CanonicalOrchestrator", "CognitiveCycleState",
    "CoreStage", "StageAdapter", "StageCapability", "StageContractViolation",
    "StageExecutionStatus", "StageOutcome",
]
