"""Canonical post-VERIFY R3 kernel composition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, runtime_checkable

from .canonical import stable_ref
from .config import RuntimeConfig
from .cycle import Orientation
from .expressions import VerifiedMeaning
from .persistence import RevisionPin, SemanticStores
from .proposal_context import ProposalContext
from .r3_artifacts import EvaluationBundle
from .r3_cognition import R3EvaluationOwner
from .r3_effects import AdapterRegistry, EffectReceipt, NoEffectReceipt, R3EffectGateway
from .r3_learning import DialogueObligation, LearningCoordinator, LearningPlan
from .r3_response import ResponseBuilder, ResponseMeaning
from .situation import (
    SituationContext, SituationContextBuilder, SituationContextVerifier,
    SituationInputBundle,
)

R3_ARTIFACT_BUNDLE_ABI_VERSION = 1

__all__ = ["R3Artifacts", "R3Owner", "R3Kernel"]


@dataclass(frozen=True, init=False)
class R3Artifacts:
    abi_version: int
    artifacts_ref: str
    situation: SituationContext
    evaluation: EvaluationBundle
    effect: EffectReceipt | NoEffectReceipt
    learning_plan: LearningPlan | None
    obligation: DialogueObligation | None
    response_meaning: ResponseMeaning
    input_revision_pin: RevisionPin
    output_revision_pin: RevisionPin

    _FIELDS = frozenset({
        "abi_version", "artifacts_ref", "situation", "evaluation", "effect",
        "learning_plan", "obligation", "response_meaning",
        "input_revision_pin", "output_revision_pin",
    })

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use R3Artifacts.create")

    @classmethod
    def create(cls, *, situation: SituationContext, evaluation: EvaluationBundle,
               effect: EffectReceipt | NoEffectReceipt,
               learning_plan: LearningPlan | None,
               obligation: DialogueObligation | None,
               response_meaning: ResponseMeaning,
               input_revision_pin: RevisionPin,
               output_revision_pin: RevisionPin) -> "R3Artifacts":
        if type(situation) is not SituationContext or type(evaluation) is not EvaluationBundle:
            raise TypeError("invalid R3 situation/evaluation")
        if type(effect) not in {EffectReceipt, NoEffectReceipt}:
            raise TypeError("effect must be exact EffectReceipt or NoEffectReceipt")
        if learning_plan is not None and type(learning_plan) is not LearningPlan:
            raise TypeError("learning_plan must be exact LearningPlan or None")
        if obligation is not None and type(obligation) is not DialogueObligation:
            raise TypeError("obligation must be exact DialogueObligation or None")
        if type(response_meaning) is not ResponseMeaning:
            raise TypeError("response_meaning must be exact ResponseMeaning")
        if evaluation.decision.situation.situation_ref != situation.situation_ref:
            raise ValueError("R3 evaluation/situation mismatch")
        if response_meaning.decision_ref != evaluation.decision.decision_ref:
            raise ValueError("R3 response/decision mismatch")
        if response_meaning.effect_outcome_ref != effect.receipt_ref:
            raise ValueError("R3 response/effect mismatch")
        if learning_plan is None and obligation is not None:
            raise ValueError("obligation requires learning plan")
        if learning_plan is not None:
            if obligation is None or obligation.plan_ref != learning_plan.plan_ref:
                raise ValueError("learning obligation does not bind plan")
        material = {
            "abi_version": R3_ARTIFACT_BUNDLE_ABI_VERSION,
            "situation": situation.as_dict(),
            "evaluation": evaluation.as_dict(),
            "effect": effect.as_dict(),
            "learning_plan": learning_plan.as_dict() if learning_plan else None,
            "obligation": obligation.as_dict() if obligation else None,
            "response_meaning": response_meaning.as_dict(),
            "input_revision_pin": input_revision_pin.as_dict(),
            "output_revision_pin": output_revision_pin.as_dict(),
        }
        obj = object.__new__(cls)
        values = {
            "abi_version": R3_ARTIFACT_BUNDLE_ABI_VERSION,
            "artifacts_ref": stable_ref("r3_artifacts", material),
            "situation": situation, "evaluation": evaluation, "effect": effect,
            "learning_plan": learning_plan, "obligation": obligation,
            "response_meaning": response_meaning,
            "input_revision_pin": input_revision_pin,
            "output_revision_pin": output_revision_pin,
        }
        for name, item in values.items(): object.__setattr__(obj, name, item)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version, "artifacts_ref": self.artifacts_ref,
            "situation": self.situation.as_dict(),
            "evaluation": self.evaluation.as_dict(),
            "effect": self.effect.as_dict(),
            "learning_plan": self.learning_plan.as_dict() if self.learning_plan else None,
            "obligation": self.obligation.as_dict() if self.obligation else None,
            "response_meaning": self.response_meaning.as_dict(),
            "input_revision_pin": self.input_revision_pin.as_dict(),
            "output_revision_pin": self.output_revision_pin.as_dict(),
        }


@runtime_checkable
class R3Owner(Protocol):
    def run(self, *, meaning: VerifiedMeaning, orientation: Orientation,
            context: ProposalContext,
            situation_inputs: SituationInputBundle) -> R3Artifacts: ...


class R3Kernel:
    """Run EVALUATE, EFFECT and response-semantic construction exactly once."""

    def __init__(self, *, authority: Any, stores: SemanticStores,
                 config: RuntimeConfig, adapters: AdapterRegistry | None = None,
                 resource_refs: tuple[str, ...] = ()) -> None:
        self._stores = stores
        self._adapters = adapters or AdapterRegistry()
        if type(resource_refs) is not tuple or any(type(ref) is not str or not ref for ref in resource_refs):
            raise TypeError("resource_refs must be an exact ref tuple")
        self._resource_refs = tuple(dict.fromkeys(resource_refs))
        self._situation_builder = SituationContextBuilder(authority)
        self._situation_verifier = SituationContextVerifier(authority)
        self._evaluator = R3EvaluationOwner(authority, stores, config)
        self._learning = LearningCoordinator(authority, stores)
        self._effects = R3EffectGateway(stores, self._adapters)
        self._response = ResponseBuilder()

    def run(self, *, meaning: VerifiedMeaning, orientation: Orientation,
            context: ProposalContext,
            situation_inputs: SituationInputBundle) -> R3Artifacts:
        if type(meaning) is not VerifiedMeaning:
            raise TypeError("R3Kernel requires exact VerifiedMeaning")
        input_pin = self._stores.revision_pin()
        if meaning.revision_pin != input_pin or context.revision_pin != input_pin:
            raise ValueError("R3 input revision pin is stale")
        if type(situation_inputs) is not SituationInputBundle:
            raise TypeError("R3Kernel requires exact SituationInputBundle")
        situation = self._situation_builder.build(
            orientation, context, **situation_inputs.as_kwargs()
        )
        situation = self._situation_verifier.verify(
            situation, orientation, context, **situation_inputs.as_kwargs()
        )
        evaluation = self._evaluator.evaluate(meaning, situation)
        learning_plan, obligation = self._learning.materialize(
            evaluation, meaning, situation
        )
        effect = self._effects.execute(
            evaluation, meaning, situation, learning_plan=learning_plan,
            obligation=obligation,
        )
        output_pin = self._stores.revision_pin()
        response = self._response.build(
            evaluation=evaluation,
            meaning=meaning,
            situation=situation,
            effect=effect,
            learning_plan=learning_plan,
            obligation=obligation,
        )
        return R3Artifacts.create(
            situation=situation,
            evaluation=evaluation,
            effect=effect,
            learning_plan=learning_plan,
            obligation=obligation,
            response_meaning=response,
            input_revision_pin=input_pin,
            output_revision_pin=output_pin,
        )
