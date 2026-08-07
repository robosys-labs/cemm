"""Learning Plan ABI 2 and persistent dialogue obligations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .canonical import stable_ref
from .cycle import SemanticMode
from .decision import DecisionAction
from .expressions import VerifiedMeaning
from .persistence import RevisionPin, SemanticStores
from .r3_artifacts import EvaluationBundle
from .situation import SituationContext

LEARNING_PLAN_ABI_VERSION = 2
DIALOGUE_OBLIGATION_ABI_VERSION = 1

__all__ = [
    "LEARNING_PLAN_ABI_VERSION",
    "LearningPlan",
    "DialogueObligation",
    "LearningCoordinator",
]


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
    if type(value) is not tuple or len(value) > 256:
        raise TypeError(f"{name} must be bounded exact tuple")
    for item in value:
        _text(item, f"{name} item")
    if len(value) != len(set(value)):
        raise ValueError(f"{name} must contain unique refs")
    return value


def _pin(value: object) -> RevisionPin:
    if type(value) is not RevisionPin:
        raise TypeError("revision_pin must be exact RevisionPin")
    if RevisionPin.from_dict(value.as_dict()) != value:
        raise ValueError("revision_pin is non-canonical")
    return value


@dataclass(frozen=True, init=False)
class LearningPlan:
    abi_version: int
    plan_ref: str
    contract_ref: str
    verified_meaning_ref: str
    expression_ref: str
    situation_ref: str
    decision_ref: str
    source_query_ref: str
    goal_ref: str
    capability_ref: str
    permission_ref: str
    commit_operator_ref: str
    surface_literal: str
    target_ref: str
    expected_target_kinds: tuple[str, ...]
    answer_contract_ref: str
    provenance_refs: tuple[str, ...]
    revision_pin: RevisionPin
    expires_at_turn: int
    obligation_ref: str

    _FIELDS = frozenset({
        "abi_version", "plan_ref", "contract_ref", "verified_meaning_ref",
        "expression_ref", "situation_ref", "decision_ref", "source_query_ref",
        "goal_ref", "capability_ref", "permission_ref", "commit_operator_ref",
        "surface_literal", "target_ref", "expected_target_kinds",
        "answer_contract_ref", "provenance_refs", "revision_pin",
        "expires_at_turn", "obligation_ref",
    })

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use LearningPlan.create")

    @classmethod
    def create(cls, *, verified_meaning_ref: str, expression_ref: str,
               situation_ref: str, decision_ref: str, source_query_ref: str,
               surface_literal: str, target_ref: str,
               expected_target_kinds: tuple[str, ...], provenance_refs: tuple[str, ...],
               revision_pin: RevisionPin, expires_at_turn: int,
               capability_ref: str = "cap:learn",
               permission_ref: str = "permission:learn_designation",
               commit_operator_ref: str = "op:designation",
               contract_ref: str = "contract:designation_learning:v2",
               answer_contract_ref: str = "contract:designation_answer:v2",
               goal_ref: str | None = None,
               obligation_ref: str | None = None) -> "LearningPlan":
        if type(expires_at_turn) is not int or expires_at_turn < 0:
            raise ValueError("expires_at_turn must be nonnegative int")
        expected = _refs(expected_target_kinds, "expected_target_kinds")
        provenance = _refs(provenance_refs, "provenance_refs")
        base = {
            "contract_ref": _text(contract_ref, "contract_ref"),
            "verified_meaning_ref": _text(verified_meaning_ref, "verified_meaning_ref"),
            "expression_ref": _text(expression_ref, "expression_ref"),
            "situation_ref": _text(situation_ref, "situation_ref"),
            "decision_ref": _text(decision_ref, "decision_ref"),
            "source_query_ref": _text(source_query_ref, "source_query_ref"),
            "capability_ref": _text(capability_ref, "capability_ref"),
            "permission_ref": _text(permission_ref, "permission_ref"),
            "commit_operator_ref": _text(commit_operator_ref, "commit_operator_ref"),
            "surface_literal": _text(surface_literal, "surface_literal"),
            "target_ref": _text(target_ref, "target_ref"),
            "expected_target_kinds": expected,
            "answer_contract_ref": _text(answer_contract_ref, "answer_contract_ref"),
            "provenance_refs": provenance,
            "revision_pin": _pin(revision_pin),
            "expires_at_turn": expires_at_turn,
        }
        goal_ref = (
            stable_ref("learning_goal", {"surface": base["surface_literal"], "target": base["target_ref"]})
            if goal_ref is None else _text(goal_ref, "goal_ref")
        )
        provisional = {"abi_version": LEARNING_PLAN_ABI_VERSION, **{
            key: list(value) if type(value) is tuple else value.as_dict() if type(value) is RevisionPin else value
            for key, value in {**base, "goal_ref": goal_ref}.items()
        }}
        plan_ref = stable_ref("learning_plan", provisional)
        obligation_ref = (
            stable_ref("learning_obligation", {"plan_ref": plan_ref, "answer_contract_ref": base["answer_contract_ref"]})
            if obligation_ref is None else _text(obligation_ref, "obligation_ref")
        )
        # plan_ref includes all semantic plan content except the derived obligation;
        # the obligation is itself deterministically derived from the plan.
        obj = object.__new__(cls)
        values = {
            "abi_version": LEARNING_PLAN_ABI_VERSION, "plan_ref": plan_ref,
            **base, "goal_ref": goal_ref, "obligation_ref": obligation_ref,
        }
        for name, item in values.items(): object.__setattr__(obj, name, item)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version, "plan_ref": self.plan_ref,
            "contract_ref": self.contract_ref,
            "verified_meaning_ref": self.verified_meaning_ref,
            "expression_ref": self.expression_ref, "situation_ref": self.situation_ref,
            "decision_ref": self.decision_ref, "source_query_ref": self.source_query_ref,
            "goal_ref": self.goal_ref, "capability_ref": self.capability_ref,
            "permission_ref": self.permission_ref,
            "commit_operator_ref": self.commit_operator_ref,
            "surface_literal": self.surface_literal, "target_ref": self.target_ref,
            "expected_target_kinds": list(self.expected_target_kinds),
            "answer_contract_ref": self.answer_contract_ref,
            "provenance_refs": list(self.provenance_refs),
            "revision_pin": self.revision_pin.as_dict(),
            "expires_at_turn": self.expires_at_turn,
            "obligation_ref": self.obligation_ref,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LearningPlan":
        if type(data) is not dict or frozenset(data) != cls._FIELDS:
            raise ValueError("LearningPlan fields mismatch")
        rebuilt = cls.create(
            verified_meaning_ref=data["verified_meaning_ref"],
            expression_ref=data["expression_ref"], situation_ref=data["situation_ref"],
            decision_ref=data["decision_ref"], source_query_ref=data["source_query_ref"],
            surface_literal=data["surface_literal"], target_ref=data["target_ref"],
            expected_target_kinds=tuple(data["expected_target_kinds"]),
            provenance_refs=tuple(data["provenance_refs"]),
            revision_pin=RevisionPin.from_dict(data["revision_pin"]),
            expires_at_turn=data["expires_at_turn"], capability_ref=data["capability_ref"],
            permission_ref=data["permission_ref"], commit_operator_ref=data["commit_operator_ref"],
            contract_ref=data["contract_ref"], answer_contract_ref=data["answer_contract_ref"],
            goal_ref=data["goal_ref"], obligation_ref=data["obligation_ref"],
        )
        if rebuilt.as_dict() != dict(data):
            raise ValueError("non-canonical LearningPlan")
        return rebuilt


@dataclass(frozen=True, init=False)
class DialogueObligation:
    abi_version: int
    obligation_ref: str
    kind: str
    session_ref: str
    plan_ref: str
    source_query_ref: str
    expected_answer_contract_ref: str
    expires_at_turn: int
    completion_receipt_ref: str | None
    revision_pin: RevisionPin

    _FIELDS = frozenset({"abi_version", "obligation_ref", "kind", "session_ref", "plan_ref", "source_query_ref", "expected_answer_contract_ref", "expires_at_turn", "completion_receipt_ref", "revision_pin"})

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use DialogueObligation.create")

    @classmethod
    def create(cls, *, plan: LearningPlan, session_ref: str,
               completion_receipt_ref: str | None = None) -> "DialogueObligation":
        if type(plan) is not LearningPlan:
            raise TypeError("plan must be exact LearningPlan")
        values = {
            "kind": "learning_answer", "session_ref": _text(session_ref, "session_ref"),
            "plan_ref": plan.plan_ref, "source_query_ref": plan.source_query_ref,
            "expected_answer_contract_ref": plan.answer_contract_ref,
            "expires_at_turn": plan.expires_at_turn,
            "completion_receipt_ref": _optional(completion_receipt_ref, "completion_receipt_ref"),
            "revision_pin": plan.revision_pin,
        }
        material = {"abi_version": DIALOGUE_OBLIGATION_ABI_VERSION, **{
            key: value.as_dict() if type(value) is RevisionPin else value
            for key, value in values.items()
        }}
        obligation_ref = stable_ref("dialogue_obligation", material)
        if completion_receipt_ref is None and obligation_ref != plan.obligation_ref:
            # LearningPlan obligation identity is intentionally derived from the
            # plan and answer contract. Keep the exact plan-owned identity.
            obligation_ref = plan.obligation_ref
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", DIALOGUE_OBLIGATION_ABI_VERSION)
        object.__setattr__(obj, "obligation_ref", obligation_ref)
        for name, item in values.items(): object.__setattr__(obj, name, item)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "obligation_ref": self.obligation_ref,
                "kind": self.kind, "session_ref": self.session_ref, "plan_ref": self.plan_ref,
                "source_query_ref": self.source_query_ref,
                "expected_answer_contract_ref": self.expected_answer_contract_ref,
                "expires_at_turn": self.expires_at_turn,
                "completion_receipt_ref": self.completion_receipt_ref,
                "revision_pin": self.revision_pin.as_dict()}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DialogueObligation":
        if type(data) is not dict or frozenset(data) != cls._FIELDS:
            raise ValueError("DialogueObligation fields mismatch")
        # Reconstruct the plan-owned fields without pretending the obligation can
        # exist independently of its exact LearningPlan.  The wire value is
        # authenticated directly by its canonical material.
        values = {
            "kind": _text(data["kind"], "kind"),
            "session_ref": _text(data["session_ref"], "session_ref"),
            "plan_ref": _text(data["plan_ref"], "plan_ref"),
            "source_query_ref": _text(data["source_query_ref"], "source_query_ref"),
            "expected_answer_contract_ref": _text(
                data["expected_answer_contract_ref"],
                "expected_answer_contract_ref",
            ),
            "expires_at_turn": data["expires_at_turn"],
            "completion_receipt_ref": _optional(
                data["completion_receipt_ref"], "completion_receipt_ref"
            ),
            "revision_pin": RevisionPin.from_dict(data["revision_pin"]),
        }
        if values["kind"] != "learning_answer":
            raise ValueError("unsupported dialogue obligation kind")
        if type(values["expires_at_turn"]) is not int or values["expires_at_turn"] < 0:
            raise ValueError("expires_at_turn must be nonnegative int")
        material = {
            "abi_version": DIALOGUE_OBLIGATION_ABI_VERSION,
            **{
                key: value.as_dict() if type(value) is RevisionPin else value
                for key, value in values.items()
            },
        }
        expected_ref = stable_ref("dialogue_obligation", material)
        stored_ref = _text(data["obligation_ref"], "obligation_ref")
        # Pending obligations may use the plan-owned deterministic identity.
        plan_owned = stable_ref(
            "learning_obligation",
            {
                "plan_ref": values["plan_ref"],
                "answer_contract_ref": values["expected_answer_contract_ref"],
            },
        )
        if stored_ref not in {expected_ref, plan_owned}:
            raise ValueError("DialogueObligation obligation_ref mismatch")
        result = object.__new__(cls)
        object.__setattr__(result, "abi_version", DIALOGUE_OBLIGATION_ABI_VERSION)
        object.__setattr__(result, "obligation_ref", stored_ref)
        for name, value in values.items():
            object.__setattr__(result, name, value)
        if result.as_dict() != dict(data):
            raise ValueError("non-canonical DialogueObligation")
        return result


class LearningCoordinator:
    """Materialize the exact evaluated learning draft; never reinterpret meaning."""

    def __init__(self, authority: Any, stores: SemanticStores) -> None:
        self._authority = authority
        self._stores = stores

    def materialize(self, evaluation: EvaluationBundle, meaning: VerifiedMeaning,
                    situation: SituationContext) -> tuple[LearningPlan | None, DialogueObligation | None]:
        if type(evaluation) is not EvaluationBundle or type(meaning) is not VerifiedMeaning or type(situation) is not SituationContext:
            raise TypeError("learning materialization requires exact R3 artifacts")
        decision = evaluation.decision
        if decision.verified_meaning_ref != meaning.verified_meaning_ref:
            raise ValueError("learning materialization meaning lineage mismatch")
        if decision.situation.situation_ref != situation.situation_ref:
            raise ValueError("learning materialization situation lineage mismatch")
        if decision.action is not DecisionAction.CREATE_LEARNING_OBLIGATION:
            if evaluation.learning_drafts:
                raise ValueError("non-learning Decision carries learning drafts")
            return None, None
        if situation.mode is not SemanticMode.REQUEST:
            raise ValueError("learning obligation requires REQUEST mode")
        if len(evaluation.learning_drafts) != 1:
            raise ValueError("learning obligation requires exactly one evaluated draft")
        draft = evaluation.learning_drafts[0]
        if decision.learning_draft_refs != (draft.learning_draft_ref,):
            raise ValueError("learning Decision does not bind the evaluated draft")
        if draft.revision_pin != situation.revision_pin:
            raise ValueError("learning draft revision pin is stale")
        if draft.target_ref is None:
            raise ValueError("materializable learning draft requires target_ref")
        if not draft.expected_target_kinds:
            raise ValueError("materializable learning draft requires expected_target_kinds")
        query_ref = draft.source_query_ref or stable_ref(
            "learning_source_query",
            {"expression_ref": meaning.expression.expression_ref},
        )
        plan = LearningPlan.create(
            verified_meaning_ref=meaning.verified_meaning_ref,
            expression_ref=meaning.expression.expression_ref,
            situation_ref=situation.situation_ref,
            decision_ref=decision.decision_ref,
            source_query_ref=query_ref,
            surface_literal=draft.surface_literal,
            target_ref=draft.target_ref,
            expected_target_kinds=draft.expected_target_kinds,
            answer_contract_ref=draft.answer_contract_ref,
            provenance_refs=tuple(dict.fromkeys((
                meaning.verification_receipt_ref,
                meaning.compilation_proof_ref,
                draft.learning_draft_ref,
                *draft.proof_refs,
            ))),
            revision_pin=situation.revision_pin,
            expires_at_turn=1,
        )
        obligation = DialogueObligation.create(plan=plan, session_ref=situation.session_ref)
        # Persistence is owned by EFFECT so obligation creation and its effect
        # journal receipt are committed atomically.
        return plan, obligation
