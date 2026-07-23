"""Cycle-local workspace, typed frontier effects and v3.5.1 completion semantics."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping


class FrontierEffect(str, Enum):
    INFORMATIONAL = "informational"
    LEARNING = "learning"
    CLARIFICATION = "clarification"
    BLOCKS_QUERY_ANSWER = "blocks_query_answer"
    BLOCKS_COMMIT = "blocks_commit"
    BLOCKS_EFFECT = "blocks_effect"
    BLOCKS_REALIZATION = "blocks_realization"
    BLOCKS_EMISSION = "blocks_emission"


class CycleCompletionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    NO_RESPONSE_REQUIRED = "NO_RESPONSE_REQUIRED"
    RESPONSE_DEFERRED = "RESPONSE_DEFERRED"
    RESPONSE_BLOCKED = "RESPONSE_BLOCKED"
    ACTION_UNCERTAIN = "ACTION_UNCERTAIN"
    RUNTIME_ERROR = "RUNTIME_ERROR"


def infer_frontier_effects(
    frontier_ref: str,
    *,
    frontier_class: str | None = None,
    requested_use: str | None = None,
) -> frozenset[FrontierEffect]:
    ref = str(frontier_ref)
    klass = str(frontier_class or "")
    use = str(requested_use or "")
    effects: set[FrontierEffect] = set()

    if (
        "learning" in klass
        or ref.startswith(("learning-frontier:", "frontier:form-", "frontier:construction:", "frontier:composition:"))
    ):
        effects.add(FrontierEffect.LEARNING)
    if "grounding" in klass or "reference_ambiguity" in klass:
        effects.add(FrontierEffect.LEARNING)
        if use in {"query", "answer"} or "query" in ref:
            effects.add(FrontierEffect.BLOCKS_QUERY_ANSWER)
    if "policy_block" in klass or "permission_block" in klass:
        if use in {"execute", "transition"}:
            effects.add(FrontierEffect.BLOCKS_EFFECT)
        elif use == "realize":
            effects.add(FrontierEffect.BLOCKS_REALIZATION)
        else:
            effects.add(FrontierEffect.BLOCKS_EMISSION)
    if "operation_outcome_unknown" in klass or ref.startswith(("frontier:operation-", "frontier:operation:")):
        effects.add(FrontierEffect.BLOCKS_EFFECT)
    if "realization_gap" in klass or ref.startswith(("frontier:realization:", "frontier:response:")):
        effects.add(FrontierEffect.BLOCKS_REALIZATION)
    if ref.startswith(("frontier:emission:", "frontier:emission-", "frontier:output-discourse:")):
        effects.add(FrontierEffect.BLOCKS_EMISSION)
    if ref.startswith(("frontier:query", "frontier:stage:10", "runtime-frontier:query")):
        effects.add(FrontierEffect.BLOCKS_QUERY_ANSWER)
    if ref.startswith("frontier:runtime-capability:"):
        try:
            stage = int(ref.split(":", 3)[3].split(":", 1)[0])
        except (ValueError, IndexError):
            stage = -1
        if 5 <= stage <= 10:
            effects.add(FrontierEffect.BLOCKS_QUERY_ANSWER)
        elif stage in {16, 17}:
            effects.add(FrontierEffect.BLOCKS_EFFECT)
        elif stage in {18, 19}:
            effects.add(FrontierEffect.BLOCKS_REALIZATION)
        elif stage in {20, 21}:
            effects.add(FrontierEffect.BLOCKS_EMISSION)
    if "budget" in klass or "budget" in ref or "timeout" in ref:
        effects.add(FrontierEffect.INFORMATIONAL)
    if not effects:
        effects.add(FrontierEffect.INFORMATIONAL)
    return frozenset(effects)


@dataclass(slots=True)
class CycleWorkspace:
    artifacts: dict[str, Any] = field(default_factory=dict)
    frontier_effects: dict[str, frozenset[FrontierEffect]] = field(default_factory=dict)
    durable_proposal_refs: list[str] = field(default_factory=list)

    def bind(self, artifacts: dict[str, Any]) -> None:
        self.artifacts = artifacts

    def update(self, values: Mapping[str, Any]) -> None:
        self.artifacts.update(dict(values))

    def register_frontier(self, frontier_ref: str, effects: Iterable[FrontierEffect] | None = None) -> None:
        resolved = frozenset(effects) if effects is not None else infer_frontier_effects(frontier_ref)
        current = self.frontier_effects.get(frontier_ref, frozenset())
        self.frontier_effects[frontier_ref] = frozenset((*current, *resolved))

    def register_runtime_frontiers(self, frontiers: Iterable[Any]) -> None:
        for frontier in frontiers:
            ref = str(getattr(frontier, "frontier_ref", "") or "")
            if not ref:
                continue
            explicit = tuple(getattr(frontier, "effects", ()) or ())
            effects = (
                tuple(item if isinstance(item, FrontierEffect) else FrontierEffect(str(item)) for item in explicit)
                if explicit
                else infer_frontier_effects(
                    ref,
                    frontier_class=str(getattr(getattr(frontier, "frontier_class", None), "value", getattr(frontier, "frontier_class", ""))),
                    requested_use=getattr(frontier, "requested_use", None),
                )
            )
            self.register_frontier(ref, effects)

    def carry(self, keys: Iterable[str]) -> "CycleWorkspace":
        return CycleWorkspace(artifacts={key: self.artifacts[key] for key in keys if key in self.artifacts})


class CompletionEvaluator:
    """Evaluate only the v3.5.1 ABI; no UOL-era artifact aliases."""

    def evaluate(self, cycle: Any) -> CycleCompletionStatus:
        if tuple(getattr(cycle, "errors", ())):
            return CycleCompletionStatus.RUNTIME_ERROR
        artifacts = getattr(cycle, "artifacts", {})
        effects: set[FrontierEffect] = set()
        workspace = getattr(cycle, "workspace", None)
        if workspace is not None:
            for values in workspace.frontier_effects.values():
                effects.update(values)
        for frontier in artifacts.get("_runtime_frontiers", ()):
            effects.update(infer_frontier_effects(
                getattr(frontier, "frontier_ref", ""),
                frontier_class=str(getattr(getattr(frontier, "frontier_class", None), "value", getattr(frontier, "frontier_class", ""))),
                requested_use=getattr(frontier, "requested_use", None),
            ))

        observations = tuple(artifacts.get("operation_observations", ()) or ())
        if any(
            str(getattr(getattr(item, "status", None), "value", getattr(item, "status", ""))).lower() in {"unknown", "uncertain"}
            for item in observations
        ):
            return CycleCompletionStatus.ACTION_UNCERTAIN

        response_requested = bool(getattr(getattr(cycle, "input_payload", None), "response_requested", True))
        emission = artifacts.get("emission_observation")
        if emission is not None:
            if FrontierEffect.BLOCKS_EMISSION in effects:
                return CycleCompletionStatus.RUNTIME_ERROR
            if response_requested and FrontierEffect.BLOCKS_QUERY_ANSWER in effects:
                return CycleCompletionStatus.PARTIAL
            return CycleCompletionStatus.SUCCESS

        if artifacts.get("silence_outcome") is not None:
            return CycleCompletionStatus.NO_RESPONSE_REQUIRED

        response_exists = bool(artifacts.get("response_decision") or artifacts.get("response_csir_candidates"))
        surface_exists = bool(artifacts.get("surface_candidates"))
        if FrontierEffect.BLOCKS_EMISSION in effects and surface_exists:
            return CycleCompletionStatus.RESPONSE_BLOCKED
        if FrontierEffect.BLOCKS_REALIZATION in effects and response_exists:
            return CycleCompletionStatus.RESPONSE_DEFERRED
        if response_requested and FrontierEffect.BLOCKS_QUERY_ANSWER in effects:
            return CycleCompletionStatus.RESPONSE_DEFERRED if not response_exists else CycleCompletionStatus.PARTIAL
        if response_requested and response_exists and not surface_exists:
            return CycleCompletionStatus.RESPONSE_DEFERRED
        if response_requested and not response_exists:
            return CycleCompletionStatus.RESPONSE_DEFERRED
        if not response_requested and not response_exists:
            return CycleCompletionStatus.NO_RESPONSE_REQUIRED
        return CycleCompletionStatus.PARTIAL


__all__ = [
    "CompletionEvaluator", "CycleCompletionStatus", "CycleWorkspace", "FrontierEffect",
    "infer_frontier_effects",
]
