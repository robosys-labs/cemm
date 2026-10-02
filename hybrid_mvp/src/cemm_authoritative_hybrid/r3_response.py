"""Response Meaning ABI 5: exact semantic contract before surface language."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .canonical import stable_ref
from .communicative import ResponseSelection, authenticate_consequence
from .cycle import CycleStatus, SemanticMode
from .decision import DecisionAction, DecisionStatus
from .epistemic import exact_epistemic_status_ref
from .expressions import QueryProjection, SemanticExpression, VerifiedMeaning
from .descriptions import DescriptionCompleteness
from .proof_bundle import ProofBundle
from .expression_transform import instantiate_bindings, negate_expression
from .persistence import RevisionPin
from .r3_artifacts import EvaluationBundle
from .r3_effects import EffectReceipt, NoEffectReceipt
from .dialogue import DialogueObligation
from .r3_learning import LearningPlan
from .r3_codec import exact_fields, exact_int, wire_refs, wire_pairs
from .situation import SituationContext

RESPONSE_MEANING_ABI_VERSION = 5

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
    description_proof: ProofBundle | None
    response_selection: ResponseSelection | None

    _FIELDS = frozenset({
        "abi_version", "response_meaning_ref", "decision_ref",
        "verified_meaning_ref", "source_expression_ref", "response_expression",
        "situation_ref", "effect_outcome_ref", "learning_plan_ref",
        "obligation_ref", "learning_plan", "obligation", "mode",
        "cycle_status", "discourse_action",
        "bindings", "polarity_ref", "modality_ref", "epistemic_status_ref",
        "source_refs", "proof_refs", "blocker_refs", "policy_refs",
        "permitted_omissions", "revision_pin", "description_proof", "response_selection",
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
               obligation: DialogueObligation | None = None,
               description_proof: ProofBundle | None = None,
               response_selection: ResponseSelection | None = None) -> "ResponseMeaning":
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
            if (learning_plan.decision_ref != decision_ref
                    or learning_plan.verified_meaning_ref != verified_meaning_ref
                    or learning_plan.expression_ref != source_expression_ref
                    or learning_plan.situation_ref != situation_ref):
                raise ValueError("response learning plan lineage mismatch")
            if obligation is None:
                raise ValueError("learning plan requires its exact source obligation")
        elif learning_plan_ref is not None:
            raise ValueError("learning_plan_ref requires exact learning_plan content")
        if obligation is not None:
            if type(obligation) is not DialogueObligation:
                raise TypeError("obligation must be exact DialogueObligation or None")
            if obligation_ref != obligation.obligation_ref:
                raise ValueError("obligation_ref does not bind obligation")
            if learning_plan is None:
                raise ValueError("obligation does not bind learning_plan")
            learning_plan.validate_source(obligation)
        elif obligation_ref is not None:
            raise ValueError("obligation_ref requires exact obligation content")
        if description_proof is not None:
            if type(description_proof) is not ProofBundle:
                raise TypeError("description_proof must be exact ProofBundle or None")
            if ProofBundle.from_dict(description_proof.as_dict()) != description_proof:
                raise ValueError("description_proof must be canonical")
            request = description_proof.description.request
            request_expression = _request_expression(description_proof)
            sufficient = description_proof.description.completeness is DescriptionCompleteness.SUFFICIENT
            expected = description_proof.description.answer_expression if sufficient else request_expression
            completeness = description_proof.description.completeness
            epistemic = {
                DescriptionCompleteness.SUFFICIENT: "epistemic_status:attributed",
                DescriptionCompleteness.PARTIAL: "epistemic_status:partial",
                DescriptionCompleteness.CONFLICT: "epistemic_status:conflict",
                DescriptionCompleteness.MISSING: "epistemic_status:unknown",
                DescriptionCompleteness.BUDGET_EXHAUSTED: "epistemic_status:unknown",
            }[completeness]
            discourse = {
                DescriptionCompleteness.SUFFICIENT: "answer",
                DescriptionCompleteness.PARTIAL: "clarify",
                DescriptionCompleteness.CONFLICT: "clarify",
                DescriptionCompleteness.MISSING: "unknown",
                DescriptionCompleteness.BUDGET_EXHAUSTED: "report_gap",
            }[completeness]
            status = {
                DescriptionCompleteness.SUFFICIENT: CycleStatus.PARTIAL,
                DescriptionCompleteness.PARTIAL: CycleStatus.PARTIAL,
                DescriptionCompleteness.CONFLICT: CycleStatus.CONFLICT,
                DescriptionCompleteness.MISSING: CycleStatus.UNKNOWN,
                DescriptionCompleteness.BUDGET_EXHAUSTED: CycleStatus.BUDGET_EXHAUSTED,
            }[completeness]
            if (source_expression_ref != request.source_expression_ref
                    or request_expression.expression_ref != request.source_expression_ref
                    or situation_ref != request.source_situation_ref
                    or response_expression != expected or mode is not SemanticMode.QUERY
                    or bindings != () or proof_refs != (description_proof.proof_bundle_ref,)
                    or not set(description_proof.description.source_refs).issubset(source_refs)
                    or polarity_ref != "polarity:positive" or modality_ref != "modality:actual"
                    or epistemic_status_ref != epistemic or discourse_action != discourse
                    or cycle_status is not status or permitted_omissions != ()
                    or learning_plan is not None or obligation is not None):
                raise ValueError("response description proof/request/answer lineage mismatch")
        elif response_expression.query_projections:
            raise ValueError("projection response requires exact signed description proof")
        if response_selection is not None:
            if (type(response_selection) is not ResponseSelection
                    or ResponseSelection.from_dict(response_selection.as_dict()) != response_selection
                    or response_selection.outgoing_expression != response_expression
                    or response_selection.situation_ref != situation_ref
                    or discourse_action != "respond" or description_proof is not None
                    or learning_plan is not None or obligation is not None or bindings):
                raise ValueError("response selection graph/situation mismatch")
        elif discourse_action == "respond":
            raise ValueError("respond discourse requires exact response selection")
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
            "epistemic_status_ref": exact_epistemic_status_ref(epistemic_status_ref),
            "source_refs": _refs(source_refs, "source_refs"),
            "proof_refs": _refs(proof_refs, "proof_refs"),
            "blocker_refs": _refs(blocker_refs, "blocker_refs"),
            "policy_refs": _refs(policy_refs, "policy_refs"),
            "permitted_omissions": _refs(permitted_omissions, "permitted_omissions"),
            "revision_pin": _pin(revision_pin),
            "description_proof": description_proof,
            "response_selection": response_selection,
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
                    ProofBundle,
                    ResponseSelection,
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
            "description_proof": self.description_proof.as_dict() if self.description_proof else None,
            "response_selection": self.response_selection.as_dict() if self.response_selection else None,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ResponseMeaning":
        data = exact_fields(data, cls._FIELDS, "ResponseMeaning")
        _strict_response_wire(data)
        if exact_int(data["abi_version"], "abi_version") != RESPONSE_MEANING_ABI_VERSION:
            raise ValueError("unsupported Response Meaning ABI")
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
            bindings=wire_pairs(data["bindings"], "bindings"),
            polarity_ref=data["polarity_ref"], modality_ref=data["modality_ref"],
            epistemic_status_ref=data["epistemic_status_ref"],
            source_refs=wire_refs(data["source_refs"], "source_refs"), proof_refs=wire_refs(data["proof_refs"], "proof_refs"),
            blocker_refs=wire_refs(data["blocker_refs"], "blocker_refs"), policy_refs=wire_refs(data["policy_refs"], "policy_refs"),
            permitted_omissions=wire_refs(data["permitted_omissions"], "permitted_omissions"),
            revision_pin=RevisionPin.from_dict(data["revision_pin"]),
            description_proof=None if data["description_proof"] is None else ProofBundle.from_dict(data["description_proof"]),
            response_selection=None if data["response_selection"] is None else ResponseSelection.from_dict(data["response_selection"]),
        )
        if data["response_meaning_ref"] != rebuilt.response_meaning_ref or rebuilt.as_dict() != dict(data):
            raise ValueError("non-canonical ResponseMeaning")
        return rebuilt


def _strict_response_wire(value: object) -> None:
    """Reject non-JSON values, cycles and mutable aliases before child codecs.

    Child codecs retain their own depth budgets. This preflight checks exact
    JSON types and existing per-container bounds. Serialized JSON has no shared
    mutable-container identity; canonical owner serialization is fully detached.
    """
    active: set[int] = set()
    completed: set[int] = set()
    def visit(item: object) -> None:
        if item is None or type(item) in {str, bool, int, float}:
            if type(item) is float and (item != item or item in {float("inf"), float("-inf")}):
                raise ValueError("response JSON float must be finite")
            if type(item) is str and len(item) > 16_384:
                raise ValueError("response JSON string exceeds bound")
            return
        if type(item) not in {dict, list}:
            raise TypeError("response wire requires exact JSON types")
        if len(item) > 512:
            raise ValueError("response JSON container exceeds bound")
        if id(item) in active or len(active) > 64:
            raise ValueError("response JSON cyclic or excessively nested")
        if id(item) in completed:
            raise ValueError("response JSON contains shared mutable aliases")
        active.add(id(item))
        try:
            if type(item) is dict:
                for key, child in item.items():
                    if type(key) is not str:
                        raise TypeError("response JSON keys must be exact str")
                    visit(child)
            else:
                for child in item: visit(child)
        finally:
            active.remove(id(item))
        completed.add(id(item))
    visit(value)


def _request_expression(bundle: ProofBundle) -> SemanticExpression:
    request = bundle.description.request
    return SemanticExpression.create(applications=(), root_refs=(request.source_projection_ref,),
        query_projections=(QueryProjection(request.source_projection_ref,
            request.requested_content, request.target_ref),))


def _exact_response_inputs(evaluation: EvaluationBundle, situation: SituationContext,
                           effect: EffectReceipt | NoEffectReceipt,
                           meaning: VerifiedMeaning | None = None) -> None:
    for value, kind in ((evaluation, EvaluationBundle), (situation, SituationContext)):
        if type(value) is not kind or kind.from_dict(value.as_dict()) != value:
            raise ValueError("response requires canonical evaluation/situation")
    if type(effect) not in {EffectReceipt, NoEffectReceipt} or type(effect).from_dict(effect.as_dict()) != effect:
        raise ValueError("response requires canonical effect receipt")
    decision = evaluation.decision
    if (evaluation.situation != situation or decision.situation != situation
            or effect.decision_ref != decision.decision_ref
            or effect.verified_meaning_ref != decision.verified_meaning_ref
            or effect.expression_ref != evaluation.expression.expression_ref
            or effect.program_ref != decision.program_ref
            or effect.situation_ref != situation.situation_ref
            or effect.input_revision_pin != evaluation.revision_pin
            or effect.input_revision_pin != situation.revision_pin):
        raise ValueError("response evaluation/effect lineage mismatch")
    if meaning is not None:
        if (type(meaning) is not VerifiedMeaning
                or VerifiedMeaning.from_dict(meaning.as_dict()) != meaning
                or meaning.expression != evaluation.expression
                or meaning.verified_meaning_ref != decision.verified_meaning_ref
                or meaning.program_ref != decision.program_ref
                or meaning.revision_pin != evaluation.revision_pin):
            raise ValueError("response decision/meaning lineage mismatch")
    if evaluation.expression.query_projections:
        if (type(effect) is not NoEffectReceipt or effect.proof_refs != decision.proof_refs
                or effect.blocker_refs != decision.blocker_refs):
            raise ValueError("projection response requires exact read-only effect evidence")


def _answer_expression(evaluation: EvaluationBundle) -> tuple[SemanticExpression, ProofBundle | None]:
    decision, source = evaluation.decision, evaluation.expression
    bundle = evaluation.query_results[0].description_proof if source.query_projections else None
    expression = source
    if decision.action is DecisionAction.RESPOND:
        if evaluation.response_selection is None or decision.selection_ref != evaluation.response_selection.selection_ref:
            raise ValueError("RESPOND requires exact included selection")
        return evaluation.response_selection.outgoing_expression, None
    if decision.action is DecisionAction.ANSWER:
        if bundle is not None:
            expression = bundle.description.answer_expression
        else:
            expression = instantiate_bindings(source, decision.bindings)
            if decision.status is DecisionStatus.CONTRADICTED:
                expression = negate_expression(expression)
        if expression is None or expression.expression_ref != decision.answer_expression_ref:
            raise ValueError("Decision answer_expression_ref does not bind the exact answer semantics")
    elif decision.answer_expression_ref is not None:
        raise ValueError("non-answer Decision cannot carry answer_expression_ref")
    return expression, bundle


def validate_response_linkage(*, response: ResponseMeaning, evaluation: EvaluationBundle,
                              situation: SituationContext, effect: EffectReceipt | NoEffectReceipt,
                              meaning: VerifiedMeaning | None = None,
                              communicative_owner=None, orientation=None, program=None, receipt=None) -> None:
    """Live source/evidence/journal authentication; structural decoding is separate."""
    authenticate_consequence(communicative_owner, situation=situation, meaning=meaning,
        orientation=orientation, program=program, receipt=receipt,
        selection=evaluation.response_selection, evaluation=evaluation, effect=effect)
    validate_response_structure(response=response, evaluation=evaluation, situation=situation, effect=effect, meaning=meaning)


def validate_response_structure(*, response, evaluation, situation, effect, meaning=None):
    """Pure structural correspondence for decoding; never publication authority."""
    _exact_response_inputs(evaluation, situation, effect, meaning)
    if type(response) is not ResponseMeaning or ResponseMeaning.from_dict(response.as_dict()) != response:
        raise ValueError("response must be exact canonical ResponseMeaning")
    _validate_response_fields(response, evaluation, situation, effect)


def _validate_response_fields(response: ResponseMeaning, evaluation: EvaluationBundle,
                              situation: SituationContext, effect: EffectReceipt | NoEffectReceipt) -> None:
    expression, bundle = _answer_expression(evaluation)
    decision = evaluation.decision
    if (response.response_selection != evaluation.response_selection
            or response.description_proof != bundle or response.response_expression != expression
            or response.decision_ref != decision.decision_ref
            or response.verified_meaning_ref != decision.verified_meaning_ref
            or response.source_expression_ref != evaluation.expression.expression_ref
            or response.situation_ref != situation.situation_ref
            or response.effect_outcome_ref != effect.receipt_ref
            or response.revision_pin != effect.output_revision_pin
            or response.mode is not situation.mode or response.bindings != decision.bindings
            or response.source_refs != tuple(dict.fromkeys((*decision.source_refs, *situation.source_refs)))
            or response.proof_refs != decision.proof_refs or response.blocker_refs != decision.blocker_refs
            or response.policy_refs != decision.policy_refs):
        raise ValueError("response source/description/effect lineage mismatch")
    if bundle is not None:
        bundle.description.request.validate_source(evaluation.expression, situation)


class ResponseBuilder:
    """Build response semantics from typed R3 receipts only."""

    @staticmethod
    def _status(decision_status: DecisionStatus, effect: EffectReceipt | NoEffectReceipt) -> CycleStatus:
        if type(effect) is EffectReceipt:
            if effect.status.value == "committed":
                return CycleStatus.RESOLVED
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
        if decision_status is DecisionStatus.BUDGET_EXHAUSTED:
            return CycleStatus.BUDGET_EXHAUSTED
        return CycleStatus.PARTIAL

    @staticmethod
    def _discourse(
        decision_status: DecisionStatus,
        action: DecisionAction,
        effect: EffectReceipt | NoEffectReceipt,
    ) -> str:
        if action is DecisionAction.RESPOND:
            return "respond"
        if decision_status is DecisionStatus.BUDGET_EXHAUSTED:
            return "report_gap"
        if decision_status in {DecisionStatus.SUPPORTED, DecisionStatus.CONTRADICTED}:
            return "answer"
        if decision_status is DecisionStatus.DENIED:
            return "deny"
        if decision_status is DecisionStatus.CONFLICT:
            return "clarify"
        if decision_status is DecisionStatus.UNKNOWN:
            return "unknown"
        if action is DecisionAction.REQUEST_CLARIFICATION:
            return "clarify"
        if action is DecisionAction.REQUEST_EFFECT:
            return (
                "report_effect"
                if type(effect) is EffectReceipt and effect.status.value == "committed"
                else "acknowledge_operation"
            )
        if action is DecisionAction.CREATE_LEARNING_OBLIGATION:
            return "request_learning_answer"
        if action is DecisionAction.PREVIEW_TRANSITION:
            return "answer_simulation"
        if action is DecisionAction.ADMIT_CLAIM:
            return "acknowledge_observation"
        return "acknowledge"

    def build(self, *, evaluation: EvaluationBundle, meaning: VerifiedMeaning,
              situation: SituationContext, effect: EffectReceipt | NoEffectReceipt,
              learning_plan: LearningPlan | None,
              obligation: DialogueObligation | None,
              communicative_owner=None, orientation=None, program=None, receipt=None) -> ResponseMeaning:
        authenticate_consequence(communicative_owner, situation=situation, meaning=meaning,
            orientation=orientation, program=program, receipt=receipt,
            selection=evaluation.response_selection, evaluation=evaluation, effect=effect)
        _exact_response_inputs(evaluation, situation, effect, meaning)
        if learning_plan is not None:
            learning_plan.validate_source(obligation, situation)
            if (type(effect) is not NoEffectReceipt or effect.learning_plan_ref != learning_plan.plan_ref
                    or effect.source_obligation_ref != obligation.obligation_ref):
                raise ValueError("response effect does not bind the learning source")
        elif (type(effect) is NoEffectReceipt
              and (effect.learning_plan_ref is not None or effect.source_obligation_ref is not None)):
            raise ValueError("learning receipt requires its exact plan and source obligation")
        effect_ref = effect.receipt_ref
        status = self._status(evaluation.decision.status, effect)
        polarity = "polarity:negative" if evaluation.decision.status in {
            DecisionStatus.CONTRADICTED, DecisionStatus.DENIED, DecisionStatus.FAILED
        } else "polarity:positive"
        epistemic_by_status = {
            DecisionStatus.SUPPORTED: "epistemic_status:supported",
            DecisionStatus.CONTRADICTED: "epistemic_status:contradicted",
            DecisionStatus.CONFLICT: "epistemic_status:conflict",
            DecisionStatus.UNKNOWN: "epistemic_status:unknown",
            DecisionStatus.PARTIAL: "epistemic_status:partial",
            DecisionStatus.BUDGET_EXHAUSTED: "epistemic_status:unknown",
            DecisionStatus.ADMITTED: "epistemic_status:observed",
            DecisionStatus.ATTRIBUTED: "epistemic_status:attributed",
            DecisionStatus.CONTESTED: "epistemic_status:contested",
            DecisionStatus.DENIED: "epistemic_status:denied",
            DecisionStatus.RESOURCE_UNAVAILABLE: "epistemic_status:unknown",
            DecisionStatus.ADAPTER_MISSING: "epistemic_status:unknown",
            DecisionStatus.SIMULATION: "epistemic_status:simulated",
            DecisionStatus.PENDING: "epistemic_status:pending",
            DecisionStatus.FAILED: "epistemic_status:unknown",
        }
        epistemic = (
            "epistemic_status:observed"
            if type(effect) is EffectReceipt and effect.status.value == "committed"
            else epistemic_by_status[evaluation.decision.status]
        )
        response_expression, description_proof = _answer_expression(evaluation)
        if description_proof is not None and evaluation.decision.action is DecisionAction.ANSWER:
            epistemic = "epistemic_status:attributed"

        response = ResponseMeaning.create(
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
            discourse_action=self._discourse(
                evaluation.decision.status, evaluation.decision.action, effect
            ),
            bindings=evaluation.decision.bindings,
            polarity_ref=polarity,
            modality_ref="modality:actual" if situation.mode is not SemanticMode.SIMULATE else "modality:possible",
            epistemic_status_ref=epistemic,
            source_refs=tuple(dict.fromkeys((*evaluation.decision.source_refs, *situation.source_refs))),
            proof_refs=evaluation.decision.proof_refs,
            blocker_refs=evaluation.decision.blocker_refs,
            policy_refs=evaluation.decision.policy_refs,
            permitted_omissions=(),
            revision_pin=effect.output_revision_pin,
            learning_plan=learning_plan,
            obligation=obligation,
            description_proof=description_proof,
            response_selection=evaluation.response_selection,
        )
        _validate_response_fields(response, evaluation, situation, effect)
        return response
