"""Response Meaning ABI 2: exact semantic contract before surface language."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .canonical import stable_ref
from .cycle import CycleStatus, SemanticMode
from .decision import DecisionAction, DecisionStatus
from .expressions import SemanticExpression, VerifiedMeaning
from .expression_transform import instantiate_bindings, negate_expression
from .persistence import RevisionPin
from .r3_artifacts import EvaluationBundle
from .r3_effects import EffectReceipt, NoEffectReceipt
from .r3_learning import DialogueObligation, LearningPlan
from .situation import SituationContext

RESPONSE_MEANING_ABI_VERSION = 2

__all__ = ["RESPONSE_MEANING_ABI_VERSION", "ResponseMeaning", "ResponseBuilder"]


def _text(value: object, name: str) -> str:
    if type(value) is not str or not value:
        raise TypeError(f"{name} must be exact nonempty str")
    if len(value) > 512:
        raise ValueError(f"{name} exceeds bound")
    return value


def _optional(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _text(value, name)


def _refs(value: object, name: str) -> tuple[str, ...]:
    if type(value) is not tuple or len(value) > 512:
        raise TypeError(f"{name} must be bounded exact tuple")
    for item in value:
        _text(item, f"{name} item")
    if len(value) != len(set(value)):
        raise ValueError(f"{name} must contain unique refs")
    return value


def _pairs(value: object, name: str) -> tuple[tuple[str, str], ...]:
    if type(value) is not tuple or len(value) > 512:
        raise TypeError(f"{name} must be bounded exact tuple")
    rows: list[tuple[str, str]] = []
    for row in value:
        if type(row) is not tuple or len(row) != 2:
            raise TypeError(f"{name} rows must be pairs")
        rows.append((_text(row[0], f"{name} key"), _text(row[1], f"{name} value")))
    return tuple(rows)


def _pin(value: object) -> RevisionPin:
    if type(value) is not RevisionPin:
        raise TypeError("revision_pin must be exact RevisionPin")
    if RevisionPin.from_dict(value.as_dict()) != value:
        raise ValueError("revision_pin is non-canonical")
    return value


@dataclass(frozen=True, init=False)
class ResponseMeaning:
    abi_version: int
    response_meaning_ref: str
    decision_ref: str
    verified_meaning_ref: str
    source_expression_ref: str
    response_expression: SemanticExpression
    situation_ref: str
    effect_outcome_ref: str
    learning_plan_ref: str | None
    obligation_ref: str | None
    learning_plan: LearningPlan | None
    obligation: DialogueObligation | None
    mode: SemanticMode
    cycle_status: CycleStatus
    discourse_action: str
    bindings: tuple[tuple[str, str], ...]
    polarity_ref: str
    modality_ref: str
    epistemic_status_ref: str
    source_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    blocker_refs: tuple[str, ...]
    policy_refs: tuple[str, ...]
    permitted_omissions: tuple[str, ...]
    revision_pin: RevisionPin

    _FIELDS = frozenset({
        "abi_version", "response_meaning_ref", "decision_ref",
        "verified_meaning_ref", "source_expression_ref", "response_expression",
        "situation_ref", "effect_outcome_ref", "learning_plan_ref",
        "obligation_ref", "learning_plan", "obligation", "mode",
        "cycle_status", "discourse_action",
        "bindings", "polarity_ref", "modality_ref", "epistemic_status_ref",
        "source_refs", "proof_refs", "blocker_refs", "policy_refs",
        "permitted_omissions", "revision_pin",
    })

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use ResponseMeaning.create")

    @classmethod
    def create(cls, *, decision_ref: str, verified_meaning_ref: str,
               source_expression_ref: str, response_expression: SemanticExpression,
               situation_ref: str, effect_outcome_ref: str,
               learning_plan_ref: str | None, obligation_ref: str | None,
               mode: SemanticMode, cycle_status: CycleStatus,
               discourse_action: str, bindings: tuple[tuple[str, str], ...],
               polarity_ref: str, modality_ref: str, epistemic_status_ref: str,
               source_refs: tuple[str, ...], proof_refs: tuple[str, ...],
               blocker_refs: tuple[str, ...], policy_refs: tuple[str, ...],
               permitted_omissions: tuple[str, ...], revision_pin: RevisionPin,
               learning_plan: LearningPlan | None = None,
               obligation: DialogueObligation | None = None) -> "ResponseMeaning":
        if type(response_expression) is not SemanticExpression:
            raise TypeError("response_expression must be exact SemanticExpression")
        if SemanticExpression.from_dict(response_expression.as_dict()) != response_expression:
            raise ValueError("response_expression is non-canonical")
        if type(mode) is not SemanticMode or type(cycle_status) is not CycleStatus:
            raise TypeError("mode/cycle_status must be closed enums")
        if learning_plan is not None:
            if type(learning_plan) is not LearningPlan:
                raise TypeError("learning_plan must be exact LearningPlan or None")
            if LearningPlan.from_dict(learning_plan.as_dict()) != learning_plan:
                raise ValueError("learning_plan is non-canonical")
            if learning_plan_ref != learning_plan.plan_ref:
                raise ValueError("learning_plan_ref does not bind learning_plan")
        elif learning_plan_ref is not None:
            raise ValueError("learning_plan_ref requires exact learning_plan content")
        if obligation is not None:
            if type(obligation) is not DialogueObligation:
                raise TypeError("obligation must be exact DialogueObligation or None")
            if obligation_ref != obligation.obligation_ref:
                raise ValueError("obligation_ref does not bind obligation")
            if learning_plan is None or obligation.plan_ref != learning_plan.plan_ref:
                raise ValueError("obligation does not bind learning_plan")
        elif obligation_ref is not None:
            raise ValueError("obligation_ref requires exact obligation content")
        values = {
            "decision_ref": _text(decision_ref, "decision_ref"),
            "verified_meaning_ref": _text(verified_meaning_ref, "verified_meaning_ref"),
            "source_expression_ref": _text(source_expression_ref, "source_expression_ref"),
            "response_expression": response_expression,
            "situation_ref": _text(situation_ref, "situation_ref"),
            "effect_outcome_ref": _text(effect_outcome_ref, "effect_outcome_ref"),
            "learning_plan_ref": _optional(learning_plan_ref, "learning_plan_ref"),
            "obligation_ref": _optional(obligation_ref, "obligation_ref"),
            "learning_plan": learning_plan,
            "obligation": obligation,
            "mode": mode, "cycle_status": cycle_status,
            "discourse_action": _text(discourse_action, "discourse_action"),
            "bindings": _pairs(bindings, "bindings"),
            "polarity_ref": _text(polarity_ref, "polarity_ref"),
            "modality_ref": _text(modality_ref, "modality_ref"),
            "epistemic_status_ref": _text(epistemic_status_ref, "epistemic_status_ref"),
            "source_refs": _refs(source_refs, "source_refs"),
            "proof_refs": _refs(proof_refs, "proof_refs"),
            "blocker_refs": _refs(blocker_refs, "blocker_refs"),
            "policy_refs": _refs(policy_refs, "policy_refs"),
            "permitted_omissions": _refs(permitted_omissions, "permitted_omissions"),
            "revision_pin": _pin(revision_pin),
        }
        material = {
            "abi_version": RESPONSE_MEANING_ABI_VERSION,
            **{
                key: value.value if isinstance(value, (SemanticMode, CycleStatus))
                else [list(row) for row in value] if key == "bindings"
                else list(value) if type(value) is tuple
                else value.as_dict()
                if type(value) in {
                    SemanticExpression,
                    RevisionPin,
                    LearningPlan,
                    DialogueObligation,
                }
                else value
                for key, value in values.items()
            },
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", RESPONSE_MEANING_ABI_VERSION)
        object.__setattr__(obj, "response_meaning_ref", stable_ref("response_meaning", material))
        for name, item in values.items(): object.__setattr__(obj, name, item)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "response_meaning_ref": self.response_meaning_ref,
            "decision_ref": self.decision_ref,
            "verified_meaning_ref": self.verified_meaning_ref,
            "source_expression_ref": self.source_expression_ref,
            "response_expression": self.response_expression.as_dict(),
            "situation_ref": self.situation_ref,
            "effect_outcome_ref": self.effect_outcome_ref,
            "learning_plan_ref": self.learning_plan_ref,
            "obligation_ref": self.obligation_ref,
            "learning_plan": self.learning_plan.as_dict() if self.learning_plan else None,
            "obligation": self.obligation.as_dict() if self.obligation else None,
            "mode": self.mode.value,
            "cycle_status": self.cycle_status.value,
            "discourse_action": self.discourse_action,
            "bindings": [list(row) for row in self.bindings],
            "polarity_ref": self.polarity_ref,
            "modality_ref": self.modality_ref,
            "epistemic_status_ref": self.epistemic_status_ref,
            "source_refs": list(self.source_refs),
            "proof_refs": list(self.proof_refs),
            "blocker_refs": list(self.blocker_refs),
            "policy_refs": list(self.policy_refs),
            "permitted_omissions": list(self.permitted_omissions),
            "revision_pin": self.revision_pin.as_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ResponseMeaning":
        if type(data) is not dict or frozenset(data) != cls._FIELDS:
            raise ValueError("ResponseMeaning fields mismatch")
        rebuilt = cls.create(
            decision_ref=data["decision_ref"], verified_meaning_ref=data["verified_meaning_ref"],
            source_expression_ref=data["source_expression_ref"],
            response_expression=SemanticExpression.from_dict(data["response_expression"]),
            situation_ref=data["situation_ref"], effect_outcome_ref=data["effect_outcome_ref"],
            learning_plan_ref=data["learning_plan_ref"], obligation_ref=data["obligation_ref"],
            learning_plan=(
                None
                if data["learning_plan"] is None
                else LearningPlan.from_dict(data["learning_plan"])
            ),
            obligation=(
                None
                if data["obligation"] is None
                else DialogueObligation.from_dict(data["obligation"])
            ),
            mode=SemanticMode(data["mode"]), cycle_status=CycleStatus(data["cycle_status"]),
            discourse_action=data["discourse_action"],
            bindings=tuple((row[0], row[1]) for row in data["bindings"]),
            polarity_ref=data["polarity_ref"], modality_ref=data["modality_ref"],
            epistemic_status_ref=data["epistemic_status_ref"],
            source_refs=tuple(data["source_refs"]), proof_refs=tuple(data["proof_refs"]),
            blocker_refs=tuple(data["blocker_refs"]), policy_refs=tuple(data["policy_refs"]),
            permitted_omissions=tuple(data["permitted_omissions"]),
            revision_pin=RevisionPin.from_dict(data["revision_pin"]),
        )
        if data["response_meaning_ref"] != rebuilt.response_meaning_ref or rebuilt.as_dict() != dict(data):
            raise ValueError("non-canonical ResponseMeaning")
        return rebuilt


class ResponseBuilder:
    """Build response semantics from typed R3 receipts only."""

    @staticmethod
    def _status(decision_status: DecisionStatus, effect: EffectReceipt | NoEffectReceipt) -> CycleStatus:
        if type(effect) is EffectReceipt:
            if effect.status.value in {"failed", "stale_revision"}:
                return CycleStatus.OPERATION_FAILED
            if effect.status.value in {"resource_unavailable", "adapter_missing"}:
                return CycleStatus.RESOURCE_UNAVAILABLE
            if effect.status.value == "denied":
                return CycleStatus.DENIED
            if effect.status.value == "pending":
                return CycleStatus.PARTIAL
        if decision_status is DecisionStatus.DENIED:
            return CycleStatus.DENIED
        if decision_status is DecisionStatus.RESOURCE_UNAVAILABLE:
            return CycleStatus.RESOURCE_UNAVAILABLE
        if decision_status is DecisionStatus.CONFLICT:
            return CycleStatus.CONFLICT
        if decision_status is DecisionStatus.UNKNOWN:
            return CycleStatus.UNKNOWN
        if decision_status is DecisionStatus.FAILED:
            return CycleStatus.OPERATION_FAILED
        return CycleStatus.PARTIAL

    @staticmethod
    def _discourse(decision_status: DecisionStatus, action: DecisionAction) -> str:
        if decision_status in {DecisionStatus.SUPPORTED, DecisionStatus.CONTRADICTED}:
            return "answer"
        if decision_status is DecisionStatus.DENIED:
            return "deny"
        if decision_status is DecisionStatus.CONFLICT:
            return "clarify"
        if decision_status is DecisionStatus.UNKNOWN:
            return "unknown"
        if action is DecisionAction.REQUEST_EFFECT:
            return "acknowledge_operation"
        if action is DecisionAction.CREATE_LEARNING_OBLIGATION:
            return "request_learning_answer"
        if action is DecisionAction.PREVIEW_TRANSITION:
            return "answer_simulation"
        return "acknowledge"

    def build(self, *, evaluation: EvaluationBundle, meaning: VerifiedMeaning,
              situation: SituationContext, effect: EffectReceipt | NoEffectReceipt,
              learning_plan: LearningPlan | None,
              obligation: DialogueObligation | None) -> ResponseMeaning:
        if evaluation.decision.verified_meaning_ref != meaning.verified_meaning_ref:
            raise ValueError("response decision/meaning mismatch")
        effect_ref = effect.receipt_ref
        status = self._status(evaluation.decision.status, effect)
        polarity = "polarity:negative" if evaluation.decision.status in {
            DecisionStatus.CONTRADICTED, DecisionStatus.DENIED, DecisionStatus.FAILED
        } else "polarity:positive"
        epistemic = f"epistemic_status:{evaluation.decision.status.value}"
        response_expression = meaning.expression
        if evaluation.decision.action is DecisionAction.ANSWER:
            response_expression = instantiate_bindings(
                meaning.expression, evaluation.decision.bindings
            )
            if evaluation.decision.status is DecisionStatus.CONTRADICTED:
                response_expression = negate_expression(response_expression)
            if (
                evaluation.decision.answer_expression_ref is None
                or response_expression.expression_ref
                != evaluation.decision.answer_expression_ref
            ):
                raise ValueError(
                    "Decision answer_expression_ref does not bind the exact answer semantics"
                )
        elif evaluation.decision.answer_expression_ref is not None:
            raise ValueError("non-answer Decision cannot carry answer_expression_ref")

        return ResponseMeaning.create(
            decision_ref=evaluation.decision.decision_ref,
            verified_meaning_ref=meaning.verified_meaning_ref,
            source_expression_ref=meaning.expression.expression_ref,
            response_expression=response_expression,
            situation_ref=situation.situation_ref,
            effect_outcome_ref=effect_ref,
            learning_plan_ref=learning_plan.plan_ref if learning_plan else None,
            obligation_ref=obligation.obligation_ref if obligation else None,
            mode=situation.mode,
            cycle_status=status,
            discourse_action=self._discourse(evaluation.decision.status, evaluation.decision.action),
            bindings=evaluation.decision.bindings,
            polarity_ref=polarity,
            modality_ref="modality:actual" if situation.mode is not SemanticMode.SIMULATE else "modality:possible",
            epistemic_status_ref=epistemic,
            source_refs=tuple(dict.fromkeys((*evaluation.decision.source_refs, *situation.source_refs))),
            proof_refs=evaluation.decision.proof_refs,
            blocker_refs=evaluation.decision.blocker_refs,
            policy_refs=evaluation.decision.policy_refs,
            permitted_omissions=(),
            revision_pin=(
                effect.output_revision_pin
                if type(effect) is EffectReceipt
                else effect.revision_pin
            ),
            learning_plan=learning_plan,
            obligation=obligation,
        )
