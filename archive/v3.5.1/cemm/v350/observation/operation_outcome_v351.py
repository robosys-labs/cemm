"""Canonical Stage-17 operation-result reconciliation and bounded semantic re-entry."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from ..csir.model import ExactAuthorityPin
from ..runtime_abi import RuntimeInput, artifact_ref
from .model_v351 import ModalityKind, RawObservationV351


@dataclass(frozen=True, slots=True)
class OperationReentryGuardV351:
    authority_generation: int
    authority_fingerprint: str
    hop_count: int = 0
    seen_observation_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.authority_generation < 1 or not self.authority_fingerprint:
            raise ValueError("operation re-entry guard requires exact authority identity")
        if not 0 <= self.hop_count <= 2:
            raise ValueError("operation re-entry guard exceeds bounded two-hop contract")
        if len(self.seen_observation_refs) != len(set(self.seen_observation_refs)):
            raise ValueError("operation re-entry observation refs must be unique")


@dataclass(frozen=True, slots=True)
class SemanticReentryRequestV351:
    observation_batch: RuntimeInput
    authority_generation: int
    authority_fingerprint: str
    guard: OperationReentryGuardV351
    carry_artifact_keys: tuple[str, ...] = ("_operation_reentry_guard",)
    max_reentries: int = 2

    def __post_init__(self) -> None:
        if self.max_reentries != 2:
            raise ValueError("v3.5.1 operation semantic recurrence is bounded to two hops")
        if (self.guard.authority_generation, self.guard.authority_fingerprint) != (
            self.authority_generation, self.authority_fingerprint,
        ):
            raise ValueError("re-entry request/guard authority mismatch")
        if self.guard.hop_count < 1:
            raise ValueError("re-entry request guard must represent an entered hop")
        if set(self.carry_artifact_keys) != {"_operation_reentry_guard"}:
            raise ValueError("operation re-entry may carry only the cumulative guard")


def _value(item, name, default=None):
    return item.get(name, default) if isinstance(item, Mapping) else getattr(item, name, default)


class CanonicalOperationOutcomeAssimilatorV351:
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "operation_outcome_assimilator"

    def assimilate(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        del store, effect_store, semantic_capabilities  # Stage 17 performs no durable world mutation.
        observations = tuple(cycle.artifacts.get("operation_observations", ()) or ())
        reconciliations = []
        prediction_errors = []
        raw_reentry = []
        recurrence_frontiers = []
        existing = cycle.artifacts.get("_operation_reentry_guard")
        if existing is None:
            guard = OperationReentryGuardV351(
                capability.authority_generation, capability.authority_fingerprint,
            )
        elif not isinstance(existing, OperationReentryGuardV351):
            raise TypeError("_operation_reentry_guard must be OperationReentryGuardV351")
        else:
            guard = existing
        if (guard.authority_generation, guard.authority_fingerprint) != (
            capability.authority_generation, capability.authority_fingerprint,
        ):
            raise ValueError("operation outcome recurrence cannot cross AuthorityGeneration")

        seen = set(guard.seen_observation_refs)
        for index, observation in enumerate(observations):
            operation_ref = str(_value(observation, "operation_ref", "") or "")
            observation_ref = str(
                _value(observation, "observation_ref", "")
                or _value(observation, "result_ref", "")
                or artifact_ref("operation-observation", cycle.cycle_ref, operation_ref, index)
            )
            if observation_ref in seen:
                continue
            evidence_refs = tuple(_value(observation, "evidence_refs", ()) or ()) or (observation_ref,)
            expected = _value(observation, "expected_outcome", None)
            actual = _value(observation, "actual_outcome", _value(observation, "result", None))
            reconciliations.append({
                "reconciliation_ref": artifact_ref("operation-reconciliation", observation_ref),
                "operation_ref": operation_ref,
                "observation_ref": observation_ref,
                "matched_prediction": expected == actual if expected is not None else None,
                "evidence_refs": evidence_refs,
            })
            if expected is not None and expected != actual:
                prediction_errors.append({
                    "prediction_error_ref": artifact_ref("operation-prediction-error", observation_ref),
                    "operation_ref": operation_ref, "expected": expected, "actual": actual,
                    "evidence_refs": evidence_refs,
                })

            projection_pin = _value(observation, "semantic_projection_pin", None)
            model_pin = _value(observation, "observation_model_pin", None)
            fragments = tuple(_value(observation, "semantic_fragments", ()) or ())
            if projection_pin is None and not fragments:
                continue
            if fragments and projection_pin is None:
                recurrence_frontiers.append(
                    f"frontier:operation-reentry:semantic-projection-authority-missing:{observation_ref}"
                )
                continue
            if projection_pin is not None and not isinstance(projection_pin, ExactAuthorityPin):
                raise TypeError("operation semantic projection requires ExactAuthorityPin")
            if model_pin is not None and not isinstance(model_pin, ExactAuthorityPin):
                raise TypeError("operation observation model requires ExactAuthorityPin")
            payload = {
                "operation_ref": operation_ref,
                "result": actual,
                "semantic_projection_pins": () if projection_pin is None else (projection_pin,),
                "semantic_fragments": fragments,
            }
            raw_reentry.append(RawObservationV351(
                observation_ref=observation_ref,
                modality=ModalityKind.OPERATION_RESULT,
                source_ref=operation_ref or observation_ref,
                payload=payload,
                context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref,
                confidence=_value(observation, "confidence", 1.0),
                evidence_refs=evidence_refs,
                lineage_refs=tuple(_value(observation, "lineage_refs", ()) or evidence_refs),
                requested_model_pin=model_pin,
            ))
            seen.add(observation_ref)

        artifacts = {
            "outcome_reconciliations": tuple(reconciliations),
            "operation_prediction_errors": tuple(prediction_errors),
        }
        if not raw_reentry:
            from ..orchestration import StageExecutionStatus, StageOutcome
            return StageOutcome(
                StageExecutionStatus.PERFORMED, artifacts=artifacts,
                frontier_refs=tuple(sorted(set(recurrence_frontiers))),
            )
        if guard.hop_count >= 2:
            from ..orchestration import StageExecutionStatus, StageOutcome
            return StageOutcome(
                StageExecutionStatus.PERFORMED, artifacts=artifacts,
                frontier_refs=tuple(sorted(set((*recurrence_frontiers, "frontier:operation-reentry:bounded-hop-limit")))),
            )
        next_guard = replace(
            guard, hop_count=guard.hop_count + 1,
            seen_observation_refs=tuple(sorted(seen)),
        )
        base = cycle.input_payload if isinstance(cycle.input_payload, RuntimeInput) else RuntimeInput(str(cycle.input_payload))
        # Preserve participant/session identity and response intent across recurrence. Only the
        # observation payload changes; re-entry must not silently become an anonymous new user turn.
        batch = RuntimeInput(
            content="", language_hints=base.language_hints,
            emission_idempotency_key=base.emission_idempotency_key,
            discourse_anchors=base.discourse_anchors, multimodal_tracks=(),
            system_output_anchors=base.system_output_anchors,
            grounding_constraints=base.grounding_constraints,
            speaker_ref=base.speaker_ref, participant_evidence_refs=base.participant_evidence_refs,
            response_requested=base.response_requested,
            observations=tuple(raw_reentry),
        )
        request = SemanticReentryRequestV351(
            observation_batch=batch,
            authority_generation=capability.authority_generation,
            authority_fingerprint=capability.authority_fingerprint,
            guard=next_guard,
        )
        artifacts["_operation_reentry_guard"] = next_guard
        from ..orchestration import StageExecutionStatus, StageOutcome
        return StageOutcome(
            StageExecutionStatus.PERFORMED, artifacts=artifacts, reentry_request=request,
            frontier_refs=tuple(sorted(set(recurrence_frontiers))),
        )


__all__ = [
    "CanonicalOperationOutcomeAssimilatorV351", "OperationReentryGuardV351",
    "SemanticReentryRequestV351",
]
