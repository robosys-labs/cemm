"""Decision ABI 1 and expression-only EVALUATE dispatch.

``Decision`` is the immutable authorization boundary after exact verification.
A construction ``Program`` is retained only as lineage.  Every action/status
combination is checked before identity is assigned, so an incomplete answer,
effect, learning request, transition preview, or admission cannot masquerade
as a valid decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Protocol, runtime_checkable

from .canonical import stable_ref
from .cycle import SemanticMode
from .expression_projection import ExpressionProjection, project_expression
from .expressions import SemanticExpression, VerifiedMeaning
from .persistence import RevisionPin
from .situation import SituationContext

DECISION_ABI_VERSION = 1
_MAX_TEXT = 512
_MAX_ROWS = 512

__all__ = [
    "DECISION_ABI_VERSION",
    "DecisionStatus",
    "DecisionAction",
    "DecisionContribution",
    "Decision",
    "ModeDecisionOwner",
    "ExactDecisionEvaluator",
]


class DecisionStatus(Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"
    PARTIAL = "partial"
    BUDGET_EXHAUSTED = "budget_exhausted"
    ADMITTED = "admitted"
    ATTRIBUTED = "attributed"
    CONTESTED = "contested"
    DENIED = "denied"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    ADAPTER_MISSING = "adapter_missing"
    SIMULATION = "simulation"
    PENDING = "pending"
    FAILED = "failed"


class DecisionAction(Enum):
    ANSWER = "answer"
    ACKNOWLEDGE = "acknowledge"
    ADMIT_CLAIM = "admit_claim"
    RETAIN_ATTRIBUTION = "retain_attribution"
    PREVIEW_TRANSITION = "preview_transition"
    REQUEST_EFFECT = "request_effect"
    CREATE_LEARNING_OBLIGATION = "create_learning_obligation"
    REQUEST_CLARIFICATION = "request_clarification"
    NO_OP = "no_op"


def _text(value: object, name: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be exact str")
    if not value:
        raise ValueError(f"{name} must be nonempty")
    if len(value) > _MAX_TEXT:
        raise ValueError(f"{name} exceeds {_MAX_TEXT} characters")
    return value


def _optional_text(value: object, name: str) -> str | None:
    return None if value is None else _text(value, name)


def _refs(value: object, name: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be an exact tuple")
    if len(value) > _MAX_ROWS:
        raise ValueError(f"{name} exceeds the Decision row bound")
    checked = tuple(_text(item, f"{name} item") for item in value)
    if len(checked) != len(set(checked)):
        raise ValueError(f"{name} must contain unique refs")
    return checked


def _bindings(value: object) -> tuple[tuple[str, str], ...]:
    if type(value) is not tuple:
        raise TypeError("bindings must be an exact tuple")
    if len(value) > _MAX_ROWS:
        raise ValueError("bindings exceeds the Decision row bound")
    rows: list[tuple[str, str]] = []
    for row in value:
        if type(row) is not tuple or len(row) != 2:
            raise TypeError("bindings rows must be exact pairs")
        variable_ref = _text(row[0], "binding variable_ref")
        target_ref = _text(row[1], "binding target_ref")
        if not variable_ref.startswith("?"):
            raise ValueError("binding variable refs must start with '?'")
        rows.append((variable_ref, target_ref))
    if len(rows) != len({row[0] for row in rows}):
        raise ValueError("bindings must contain unique variables")
    return tuple(rows)


def _wire_refs(value: object, name: str) -> tuple[str, ...]:
    if type(value) is not list:
        raise TypeError(f"{name} wire value must be an exact list")
    return _refs(tuple(value), name)


def _wire_bindings(value: object) -> tuple[tuple[str, str], ...]:
    if type(value) is not list:
        raise TypeError("bindings wire value must be an exact list")
    rows: list[tuple[str, str]] = []
    for row in value:
        if type(row) is not list or len(row) != 2:
            raise TypeError("bindings wire rows must be exact two-item lists")
        rows.append((row[0], row[1]))
    return _bindings(tuple(rows))


def _pin(value: object) -> RevisionPin:
    if type(value) is not RevisionPin:
        raise TypeError("revision_pin must be exact RevisionPin")
    if RevisionPin.from_dict(value.as_dict()) != value:
        raise ValueError("revision_pin is non-canonical")
    return value


_REF_FIELDS = (
    "claim_occurrence_refs",
    "admission_decision_refs",
    "query_result_refs",
    "transition_preview_refs",
    "learning_draft_refs",
    "proof_refs",
    "source_refs",
    "blocker_refs",
    "policy_refs",
)


@dataclass(frozen=True)
class DecisionContribution:
    status: DecisionStatus
    action: DecisionAction
    answer_expression_ref: str | None = None
    bindings: tuple[tuple[str, str], ...] = ()
    claim_occurrence_refs: tuple[str, ...] = ()
    admission_decision_refs: tuple[str, ...] = ()
    query_result_refs: tuple[str, ...] = ()
    transition_preview_refs: tuple[str, ...] = ()
    effect_intent_ref: str | None = None
    learning_draft_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    blocker_refs: tuple[str, ...] = ()
    policy_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.status) is not DecisionStatus:
            raise TypeError("status must be exact DecisionStatus")
        if type(self.action) is not DecisionAction:
            raise TypeError("action must be exact DecisionAction")
        _optional_text(self.answer_expression_ref, "answer_expression_ref")
        _optional_text(self.effect_intent_ref, "effect_intent_ref")
        object.__setattr__(self, "bindings", _bindings(self.bindings))
        for name in _REF_FIELDS:
            object.__setattr__(self, name, _refs(getattr(self, name), name))
        self._validate_matrix()

    def _require(self, condition: bool, detail: str) -> None:
        if not condition:
            raise ValueError(f"invalid DecisionContribution: {detail}")

    def _forbid(self, condition: bool, detail: str) -> None:
        if condition:
            raise ValueError(f"invalid DecisionContribution: {detail}")

    def _validate_matrix(self) -> None:
        action = self.action
        status = self.status
        has_claim = bool(self.claim_occurrence_refs)
        has_admission = bool(self.admission_decision_refs)
        has_query = bool(self.query_result_refs)
        has_transition = bool(self.transition_preview_refs)
        has_learning = bool(self.learning_draft_refs)
        has_effect = self.effect_intent_ref is not None

        if action is DecisionAction.ANSWER:
            self._require(
                status in {DecisionStatus.SUPPORTED, DecisionStatus.CONTRADICTED},
                "ANSWER requires supported or contradicted status",
            )
            self._require(has_query, "ANSWER requires query_result_refs")
            self._require(
                self.answer_expression_ref is not None,
                "ANSWER requires answer_expression_ref",
            )
            self._forbid(
                has_claim or has_admission or has_transition or has_effect or has_learning,
                "ANSWER carries unrelated mutable fields",
            )
            return

        if action is DecisionAction.ACKNOWLEDGE:
            self._require(
                status in {DecisionStatus.ATTRIBUTED, DecisionStatus.CONTESTED},
                "ACKNOWLEDGE requires attributed or contested status",
            )
            self._require(has_claim and has_admission, "ACKNOWLEDGE requires claim and admission refs")
            self._forbid(has_query or has_transition or has_effect or has_learning,
                         "ACKNOWLEDGE carries unrelated fields")
            return

        if action is DecisionAction.ADMIT_CLAIM:
            self._require(status is DecisionStatus.ADMITTED, "ADMIT_CLAIM requires admitted status")
            self._require(has_claim and has_admission, "ADMIT_CLAIM requires claim and admission refs")
            self._require(bool(self.proof_refs), "ADMIT_CLAIM requires proof_refs")
            self._forbid(has_query or has_transition or has_effect or has_learning,
                         "ADMIT_CLAIM carries unrelated fields")
            return

        if action is DecisionAction.RETAIN_ATTRIBUTION:
            self._require(
                status in {DecisionStatus.ATTRIBUTED, DecisionStatus.CONTESTED},
                "RETAIN_ATTRIBUTION requires attributed or contested status",
            )
            self._require(has_claim and has_admission,
                          "RETAIN_ATTRIBUTION requires claim and admission refs")
            self._forbid(has_query or has_transition or has_effect or has_learning,
                         "RETAIN_ATTRIBUTION carries unrelated fields")
            return

        if action is DecisionAction.PREVIEW_TRANSITION:
            self._require(status is DecisionStatus.SIMULATION,
                          "PREVIEW_TRANSITION requires simulation status")
            self._require(has_transition, "PREVIEW_TRANSITION requires transition refs")
            self._forbid(has_effect or has_learning or has_query or has_claim or has_admission,
                         "PREVIEW_TRANSITION carries unrelated fields")
            return

        if action is DecisionAction.REQUEST_EFFECT:
            self._require(status is DecisionStatus.PENDING,
                          "REQUEST_EFFECT requires pending status")
            self._require(has_transition, "REQUEST_EFFECT requires transition refs")
            self._require(has_effect, "REQUEST_EFFECT requires effect_intent_ref")
            self._forbid(has_learning or has_query or has_claim or has_admission,
                         "REQUEST_EFFECT carries unrelated fields")
            return

        if action is DecisionAction.CREATE_LEARNING_OBLIGATION:
            self._require(status is DecisionStatus.PENDING,
                          "CREATE_LEARNING_OBLIGATION requires pending status")
            self._require(has_learning,
                          "CREATE_LEARNING_OBLIGATION requires learning_draft_refs")
            self._forbid(has_effect or has_transition or has_query or has_claim or has_admission,
                         "CREATE_LEARNING_OBLIGATION carries unrelated fields")
            return

        if action is DecisionAction.REQUEST_CLARIFICATION:
            self._require(
                status in {DecisionStatus.CONFLICT, DecisionStatus.UNKNOWN, DecisionStatus.PARTIAL},
                "REQUEST_CLARIFICATION requires conflict, unknown, or partial status",
            )
            self._require(bool(self.blocker_refs),
                          "REQUEST_CLARIFICATION requires blocker_refs")
            self._forbid(has_effect or has_learning or has_claim or has_admission,
                         "REQUEST_CLARIFICATION carries mutable consequence fields")
            return

        if action is DecisionAction.NO_OP:
            self._require(
                status in {
                    DecisionStatus.UNKNOWN,
                    DecisionStatus.BUDGET_EXHAUSTED,
                    DecisionStatus.DENIED,
                    DecisionStatus.RESOURCE_UNAVAILABLE,
                    DecisionStatus.ADAPTER_MISSING,
                    DecisionStatus.FAILED,
                },
                "NO_OP requires a terminal non-success status",
            )
            self._require(bool(self.blocker_refs), "NO_OP requires blocker_refs")
            self._forbid(has_effect or has_learning or has_claim or has_admission,
                         "NO_OP carries mutable consequence fields")
            return

        raise AssertionError("unhandled DecisionAction")


@dataclass(frozen=True, init=False)
class Decision:
    abi_version: int
    decision_ref: str
    verified_meaning_ref: str
    expression_ref: str
    program_ref: str
    situation: SituationContext
    mode: SemanticMode
    status: DecisionStatus
    action: DecisionAction
    answer_expression_ref: str | None
    bindings: tuple[tuple[str, str], ...]
    claim_occurrence_refs: tuple[str, ...]
    admission_decision_refs: tuple[str, ...]
    query_result_refs: tuple[str, ...]
    transition_preview_refs: tuple[str, ...]
    effect_intent_ref: str | None
    learning_draft_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    blocker_refs: tuple[str, ...]
    policy_refs: tuple[str, ...]
    revision_pin: RevisionPin

    _FIELDS = frozenset({
        "abi_version", "decision_ref", "verified_meaning_ref", "expression_ref",
        "program_ref", "situation", "mode", "status", "action",
        "answer_expression_ref", "bindings", "claim_occurrence_refs",
        "admission_decision_refs", "query_result_refs", "transition_preview_refs",
        "effect_intent_ref", "learning_draft_refs", "proof_refs", "source_refs",
        "blocker_refs", "policy_refs", "revision_pin",
    })

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use Decision.create")

    @staticmethod
    def _material(
        *,
        verified_meaning_ref: str,
        expression_ref: str,
        program_ref: str,
        situation: SituationContext,
        contribution: DecisionContribution,
        revision_pin: RevisionPin,
    ) -> dict[str, Any]:
        return {
            "abi_version": DECISION_ABI_VERSION,
            "verified_meaning_ref": verified_meaning_ref,
            "expression_ref": expression_ref,
            "program_ref": program_ref,
            "situation": situation.as_dict(),
            "mode": situation.mode.value,
            "status": contribution.status.value,
            "action": contribution.action.value,
            "answer_expression_ref": contribution.answer_expression_ref,
            "bindings": [list(row) for row in contribution.bindings],
            "claim_occurrence_refs": list(contribution.claim_occurrence_refs),
            "admission_decision_refs": list(contribution.admission_decision_refs),
            "query_result_refs": list(contribution.query_result_refs),
            "transition_preview_refs": list(contribution.transition_preview_refs),
            "effect_intent_ref": contribution.effect_intent_ref,
            "learning_draft_refs": list(contribution.learning_draft_refs),
            "proof_refs": list(contribution.proof_refs),
            "source_refs": list(contribution.source_refs),
            "blocker_refs": list(contribution.blocker_refs),
            "policy_refs": list(contribution.policy_refs),
            "revision_pin": revision_pin.as_dict(),
        }

    @classmethod
    def _from_canonical(cls, decision_ref: str, values: Mapping[str, Any]) -> "Decision":
        result = object.__new__(cls)
        object.__setattr__(result, "abi_version", DECISION_ABI_VERSION)
        object.__setattr__(result, "decision_ref", decision_ref)
        for name, item in values.items():
            object.__setattr__(result, name, item)
        return result

    @classmethod
    def create(
        cls,
        *,
        meaning: VerifiedMeaning,
        situation: SituationContext,
        contribution: DecisionContribution,
    ) -> "Decision":
        if cls is not Decision:
            raise TypeError("Decision factories require exact Decision")
        if type(meaning) is not VerifiedMeaning:
            raise TypeError("meaning must be exact VerifiedMeaning")
        if VerifiedMeaning.from_dict(meaning.as_dict()) != meaning:
            raise ValueError("meaning is non-canonical")
        if type(situation) is not SituationContext:
            raise TypeError("situation must be exact SituationContext")
        if SituationContext.from_dict(situation.as_dict()) != situation:
            raise ValueError("situation is non-canonical")
        if type(contribution) is not DecisionContribution:
            raise TypeError("contribution must be exact DecisionContribution")
        if meaning.revision_pin != situation.revision_pin:
            raise ValueError("meaning and situation revision pins differ")
        values = {
            "verified_meaning_ref": meaning.verified_meaning_ref,
            "expression_ref": meaning.expression.expression_ref,
            "program_ref": meaning.program_ref,
            "situation": situation,
            "mode": situation.mode,
            "status": contribution.status,
            "action": contribution.action,
            "answer_expression_ref": contribution.answer_expression_ref,
            "bindings": contribution.bindings,
            "claim_occurrence_refs": contribution.claim_occurrence_refs,
            "admission_decision_refs": contribution.admission_decision_refs,
            "query_result_refs": contribution.query_result_refs,
            "transition_preview_refs": contribution.transition_preview_refs,
            "effect_intent_ref": contribution.effect_intent_ref,
            "learning_draft_refs": contribution.learning_draft_refs,
            "proof_refs": contribution.proof_refs,
            "source_refs": contribution.source_refs,
            "blocker_refs": contribution.blocker_refs,
            "policy_refs": contribution.policy_refs,
            "revision_pin": _pin(meaning.revision_pin),
        }
        material = cls._material(
            verified_meaning_ref=meaning.verified_meaning_ref,
            expression_ref=meaning.expression.expression_ref,
            program_ref=meaning.program_ref,
            situation=situation,
            contribution=contribution,
            revision_pin=meaning.revision_pin,
        )
        return cls._from_canonical(stable_ref("decision", material), values)

    def _contribution(self) -> DecisionContribution:
        return DecisionContribution(
            status=self.status,
            action=self.action,
            answer_expression_ref=self.answer_expression_ref,
            bindings=self.bindings,
            claim_occurrence_refs=self.claim_occurrence_refs,
            admission_decision_refs=self.admission_decision_refs,
            query_result_refs=self.query_result_refs,
            transition_preview_refs=self.transition_preview_refs,
            effect_intent_ref=self.effect_intent_ref,
            learning_draft_refs=self.learning_draft_refs,
            proof_refs=self.proof_refs,
            source_refs=self.source_refs,
            blocker_refs=self.blocker_refs,
            policy_refs=self.policy_refs,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision_ref": self.decision_ref,
            **self._material(
                verified_meaning_ref=self.verified_meaning_ref,
                expression_ref=self.expression_ref,
                program_ref=self.program_ref,
                situation=self.situation,
                contribution=self._contribution(),
                revision_pin=self.revision_pin,
            ),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Decision":
        if cls is not Decision:
            raise TypeError("Decision codecs require exact Decision")
        if type(value) is not dict or frozenset(value) != cls._FIELDS:
            raise ValueError("Decision fields mismatch")
        if type(value["abi_version"]) is not int or value["abi_version"] != DECISION_ABI_VERSION:
            raise ValueError("unsupported Decision ABI")
        if type(value["situation"]) is not dict or type(value["revision_pin"]) is not dict:
            raise TypeError("Decision nested values must be exact dicts")
        situation = SituationContext.from_dict(value["situation"])
        pin = RevisionPin.from_dict(value["revision_pin"])
        if situation.revision_pin != pin:
            raise ValueError("Decision situation and revision pin differ")
        contribution = DecisionContribution(
            status=DecisionStatus(value["status"]),
            action=DecisionAction(value["action"]),
            answer_expression_ref=value["answer_expression_ref"],
            bindings=_wire_bindings(value["bindings"]),
            claim_occurrence_refs=_wire_refs(value["claim_occurrence_refs"], "claim_occurrence_refs"),
            admission_decision_refs=_wire_refs(value["admission_decision_refs"], "admission_decision_refs"),
            query_result_refs=_wire_refs(value["query_result_refs"], "query_result_refs"),
            transition_preview_refs=_wire_refs(value["transition_preview_refs"], "transition_preview_refs"),
            effect_intent_ref=value["effect_intent_ref"],
            learning_draft_refs=_wire_refs(value["learning_draft_refs"], "learning_draft_refs"),
            proof_refs=_wire_refs(value["proof_refs"], "proof_refs"),
            source_refs=_wire_refs(value["source_refs"], "source_refs"),
            blocker_refs=_wire_refs(value["blocker_refs"], "blocker_refs"),
            policy_refs=_wire_refs(value["policy_refs"], "policy_refs"),
        )
        verified_meaning_ref = _text(value["verified_meaning_ref"], "verified_meaning_ref")
        expression_ref = _text(value["expression_ref"], "expression_ref")
        program_ref = _text(value["program_ref"], "program_ref")
        material = cls._material(
            verified_meaning_ref=verified_meaning_ref,
            expression_ref=expression_ref,
            program_ref=program_ref,
            situation=situation,
            contribution=contribution,
            revision_pin=pin,
        )
        decision_ref = _text(value["decision_ref"], "decision_ref")
        if decision_ref != stable_ref("decision", material):
            raise ValueError("Decision decision_ref mismatch")
        rebuilt = cls._from_canonical(
            decision_ref,
            {
                "verified_meaning_ref": verified_meaning_ref,
                "expression_ref": expression_ref,
                "program_ref": program_ref,
                "situation": situation,
                "mode": situation.mode,
                "status": contribution.status,
                "action": contribution.action,
                "answer_expression_ref": contribution.answer_expression_ref,
                "bindings": contribution.bindings,
                "claim_occurrence_refs": contribution.claim_occurrence_refs,
                "admission_decision_refs": contribution.admission_decision_refs,
                "query_result_refs": contribution.query_result_refs,
                "transition_preview_refs": contribution.transition_preview_refs,
                "effect_intent_ref": contribution.effect_intent_ref,
                "learning_draft_refs": contribution.learning_draft_refs,
                "proof_refs": contribution.proof_refs,
                "source_refs": contribution.source_refs,
                "blocker_refs": contribution.blocker_refs,
                "policy_refs": contribution.policy_refs,
                "revision_pin": pin,
            },
        )
        if rebuilt.as_dict() != dict(value):
            raise ValueError("non-canonical Decision encoding")
        return rebuilt


@runtime_checkable
class ModeDecisionOwner(Protocol):
    def evaluate(
        self,
        expression: SemanticExpression,
        projection: ExpressionProjection,
        situation: SituationContext,
    ) -> DecisionContribution:
        raise NotImplementedError


class ExactDecisionEvaluator:
    """Dispatch EVALUATE by the closed semantic mode, never by text or Program."""

    def __init__(self, owners: Mapping[SemanticMode, ModeDecisionOwner]) -> None:
        if not isinstance(owners, Mapping):
            raise TypeError("owners must be a mapping")
        if set(owners) != set(SemanticMode):
            missing = sorted(mode.value for mode in set(SemanticMode) - set(owners))
            extra = sorted(str(mode) for mode in set(owners) - set(SemanticMode))
            raise ValueError(
                "decision owners must cover the exact SemanticMode set: "
                f"missing={missing}, extra={extra}"
            )
        copied: dict[SemanticMode, ModeDecisionOwner] = {}
        for mode, owner in owners.items():
            if type(mode) is not SemanticMode:
                raise TypeError("decision owner keys must be exact SemanticMode")
            if not isinstance(owner, ModeDecisionOwner):
                raise TypeError(f"{mode.value} owner violates ModeDecisionOwner")
            copied[mode] = owner
        self._owners = copied

    def evaluate(self, meaning: VerifiedMeaning, situation: SituationContext) -> Decision:
        if type(meaning) is not VerifiedMeaning:
            raise TypeError("EVALUATE accepts exact VerifiedMeaning only")
        if type(situation) is not SituationContext:
            raise TypeError("EVALUATE accepts exact SituationContext only")
        if meaning.revision_pin != situation.revision_pin:
            raise ValueError("meaning and situation revision pins differ")
        projection = project_expression(meaning.expression)
        contribution = self._owners[situation.mode].evaluate(
            meaning.expression, projection, situation
        )
        if type(contribution) is not DecisionContribution:
            raise TypeError("mode owner returned a non-canonical contribution")
        return Decision.create(
            meaning=meaning,
            situation=situation,
            contribution=contribution,
        )
