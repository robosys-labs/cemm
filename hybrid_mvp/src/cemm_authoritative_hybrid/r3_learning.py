"""Learning Plan ABI 3 binds the existing generic dialogue continuation."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
from typing import Any, Mapping

from .authority import DesignationLearningContract, LinkedAuthority
from .canonical import stable_ref
from .config import RuntimeConfig
from .cycle import SemanticMode
from . import dialogue
from .r3_codec import exact_fields, exact_int, wire_refs
from .decision import DecisionAction
from .expressions import (
    GroundedReference, LiteralValue, RoleBinding, SemanticApplication,
    SemanticExpression, UnresolvedValue, VerifiedMeaning,
)
from .persistence import RevisionPin, SemanticStores
from .r3_artifacts import EvaluationBundle
from .situation import SituationContext

LEARNING_PLAN_ABI_VERSION = 3

from .r3_designations import AdmittedDesignationReader, DesignationEvidence


class AliasReviewVerifier:
    """Privileged per-store HMAC configuration, never supplied through dialogue.

    A canonical public grant is evidence only until this separately configured
    key authenticates it. The verifier intentionally has no signing API.
    """

    _GRANT_FIELDS = frozenset({"proposal_key", "proposal_journal_ref", "proposal_receipt_ref",
        "plan_ref", "source_obligation_ref", "source_query_ref", "source_journal_ref",
        "surface", "target_ref", "language", "reviewer_ref", "policy_ref", "key_ref",
        "store_binding", "nonce", "expires_at_turn"})

    def __init__(self, *, key: bytes, key_ref: str, reviewer_ref: str, policy_ref: str, store_binding: str):
        if type(key) is not bytes or len(key) < 32:
            raise ValueError("review key must contain at least 256 bits of separately configured secret material")
        self.__key = key
        self.key_ref = _text(key_ref, "key_ref")
        self.reviewer_ref = _text(reviewer_ref, "reviewer_ref")
        self.policy_ref = _text(policy_ref, "policy_ref")
        self.store_binding = _text(store_binding, "store_binding")

    def verify(self, signed_review, *, store_binding):
        # Serialize once before authentication and retain those exact detached
        # bytes: caller mutation cannot replace a verified grant after the check.
        encoded = json.dumps(signed_review, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False)
        if len(encoded) > 16384:
            raise ValueError("review exceeds bound")
        review = json.loads(encoded)
        exact_fields(review, {"grant", "signature"}, "signed alias review")
        grant = exact_fields(review["grant"], self._GRANT_FIELDS, "alias review grant")
        for name in self._GRANT_FIELDS - {"expires_at_turn"}:
            _text(grant[name], name)
        exact_int(grant["expires_at_turn"], "review expiry", minimum=1)
        signature = _text(review["signature"], "review signature")
        payload = json.dumps(grant, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        if not hmac.compare_digest(hmac.new(self.__key, payload, hashlib.sha256).hexdigest(), signature):
            raise PermissionError("alias review authentication failed")
        if (grant["key_ref"] != self.key_ref or grant["reviewer_ref"] != self.reviewer_ref
                or grant["policy_ref"] != self.policy_ref or grant["store_binding"] != self.store_binding
                or store_binding != self.store_binding):
            raise PermissionError("alias review privileged scope mismatch")
        return review

__all__ = [
    "AdmittedDesignationReader",
    "DesignationEvidence",
    "LEARNING_PLAN_ABI_VERSION",
    "LearningPlan",
    "LearningCoordinator",
    "DesignationLearningLowering",
    "lower_designation_learning",
    "LearningLoweringError",
]


def _text(value: object, name: str) -> str:
    if type(value) is not str or not value:
        raise TypeError(f"{name} must be exact nonempty str")
    if len(value) > 512:
        raise ValueError(f"{name} exceeds bound")
    return value


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


@dataclass(frozen=True)
class DesignationLearningLowering:
    """Pure source-to-content derivation, never reviewer or publication authority."""

    contract: DesignationLearningContract
    source_application_ref: str
    actor_ref: str
    designation: SemanticApplication
    proof_refs: tuple[str, ...]


class LearningLoweringError(ValueError):
    """A bounded source-owner diagnostic; it never licenses a partial lowering."""

    def __init__(self, blocker_ref: str) -> None:
        self.blocker_ref = _text(blocker_ref, "blocker_ref")
        super().__init__(self.blocker_ref)


def lower_designation_learning(
    authority: LinkedAuthority, expression: SemanticExpression, situation: SituationContext,
) -> DesignationLearningLowering:
    """Lower one eligible reviewed event while retaining its original meaning.

    Static contracts/grants are indexed at activation; this bounded derivation
    neither reads stores nor interprets wording nor grants an external adapter.
    """
    if type(authority) is not LinkedAuthority or type(expression) is not SemanticExpression or type(situation) is not SituationContext:
        raise TypeError("learning lowering requires exact linked authority, expression and situation")
    if situation.mode is not SemanticMode.REQUEST or situation.revision_pin.authority_generation != authority.generation:
        raise ValueError("learning lowering requires a current-authority REQUEST")
    if (len(expression.applications) != 1 or len(expression.root_refs) != 1
            or expression.binders or expression.expression_links):
        raise ValueError("learning lowering requires one complete unembedded application")
    app = expression.applications[0]
    node_ref = expression.root_refs[0]
    scopes = {scope.scope_ref: scope for scope in expression.scope_operators}
    visited: set[str] = set()
    while node_ref in scopes:
        scope = scopes[node_ref]
        if (node_ref in visited or scope.operator_type != "scope:polarity"
                or scope.value_ref not in {"polarity:positive", "scope_value:polarity:positive"}):
            raise ValueError("learning lowering requires a positive directive root")
        visited.add(node_ref)
        node_ref = scope.operand_ref
    if node_ref != app.application_ref or len(visited) != len(scopes) or app.qualifiers:
        raise ValueError("learning lowering cannot discard graph or qualifier content")
    contract = authority.learning_contract_for_source(app.operator, app.predicate_ref)
    if contract is None:
        raise ValueError("learning source has no exact linked contract")
    signature = authority.by_event_signature(contract.source_event_ref)
    if signature is None or situation.session_phase_ref not in signature.valid_session_phases:
        raise ValueError("learning source is unavailable in the current session phase")
    roles = {binding.role_ref: binding.filler for binding in app.roles}
    if set(roles) - {contract.actor_role_ref, contract.surface_role_ref, contract.target_role_ref}:
        raise ValueError("learning source has extra roles outside the linked contract")
    for ref, blocker in (
        (contract.surface_role_ref, "learning:surface_missing"),
        (contract.target_role_ref, "learning:target_missing"),
    ):
        if roles.get(ref) is None or type(roles[ref]) is UnresolvedValue:
            raise LearningLoweringError(blocker)
    if expression.unresolved_fillers:
        raise ValueError("learning lowering cannot discard residual evidence")
    if set(roles) != {contract.actor_role_ref, contract.surface_role_ref, contract.target_role_ref}:
        raise ValueError("learning source roles differ from the linked contract")
    actor, surface, target = (roles[ref] for ref in
        (contract.actor_role_ref, contract.surface_role_ref, contract.target_role_ref))
    if (type(actor) is not GroundedReference or type(target) is not GroundedReference
            or type(surface) is not LiteralValue or surface.value_type != "string"
            or type(surface.value) is not str or not surface.value or len(surface.value) > 512):
        raise ValueError("learning requires grounded actor/target and a bounded exact surface")
    actor_atom, target_atom = authority.atoms.get(actor.target_ref), authority.atoms.get(target.target_ref)
    if (actor.target_ref != situation.actor_ref or actor.target_ref != situation.addressee_ref
            or actor.target_ref not in situation.participant_refs or actor_atom is None
            or actor_atom.kind != "participant" or actor_atom.reviewed is not True):
        raise ValueError("learning actor must be the explicit reviewed addressed executor")
    if target_atom is None or target_atom.reviewed is not True or target_atom.kind not in contract.allowed_target_kinds:
        raise ValueError("learning target must be an allowed existing reviewed identity")
    if (not authority.capability_granted(actor.target_ref, contract.capability_ref)
            or contract.capability_ref not in situation.capability_refs):
        raise ValueError("learning requires matching linked and captured actor capability")
    if (not authority.permission_granted(actor.target_ref, contract.permission_ref, contract.source_event_ref)
            or contract.permission_ref not in situation.permission_refs):
        raise PermissionError("learning lacks linked or captured actor permission")
    designation = SemanticApplication("application:designation", contract.commit_operator_ref,
        contract.designation_label_ref, (
            RoleBinding("role:label_type", GroundedReference(contract.designation_label_ref)),
            RoleBinding("role:surface", surface), RoleBinding("role:target", target),
        ))
    canonical = SemanticExpression.create(
        applications=(designation,), root_refs=(designation.application_ref,)
    ).applications[0]
    return DesignationLearningLowering(contract, app.application_ref, actor.target_ref, canonical,
        (app.application_ref, actor.target_ref, contract.contract_ref, authority.content_hash,
         contract.capability_ref, contract.permission_ref, contract.review_policy_ref))


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
    source_obligation_ref: str

    _FIELDS = frozenset({
        "abi_version", "plan_ref", "contract_ref", "verified_meaning_ref",
        "expression_ref", "situation_ref", "decision_ref", "source_query_ref",
        "goal_ref", "capability_ref", "permission_ref", "commit_operator_ref",
        "surface_literal", "target_ref", "expected_target_kinds",
        "answer_contract_ref", "provenance_refs", "revision_pin",
        "expires_at_turn", "source_obligation_ref",
    })

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use LearningPlan.create")

    @classmethod
    def create(cls, *, verified_meaning_ref: str, expression_ref: str,
               situation_ref: str, decision_ref: str, source_query_ref: str,
               surface_literal: str, target_ref: str,
               expected_target_kinds: tuple[str, ...], provenance_refs: tuple[str, ...],
               revision_pin: RevisionPin, expires_at_turn: int,
               capability_ref: str,
               permission_ref: str,
               commit_operator_ref: str,
               contract_ref: str,
               answer_contract_ref: str,
               goal_ref: str,
               source_obligation_ref: str) -> "LearningPlan":
        if type(expires_at_turn) is not int or expires_at_turn < 0:
            raise ValueError("expires_at_turn must be nonnegative int")
        expected = _refs(expected_target_kinds, "expected_target_kinds")
        provenance = _refs(provenance_refs, "provenance_refs")
        source = _text(source_obligation_ref, "source_obligation_ref")
        if source not in provenance:
            raise ValueError("source obligation must be retained in plan provenance")
        base = {
            "source_obligation_ref": source,
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
        goal_ref = _text(goal_ref, "goal_ref")
        provisional = {"abi_version": LEARNING_PLAN_ABI_VERSION, **{
            key: list(value) if type(value) is tuple else value.as_dict() if type(value) is RevisionPin else value
            for key, value in {**base, "goal_ref": goal_ref}.items()
        }}
        plan_ref = stable_ref("learning_plan", provisional)
        obj = object.__new__(cls)
        values = {
            "abi_version": LEARNING_PLAN_ABI_VERSION, "plan_ref": plan_ref,
            **base, "goal_ref": goal_ref,
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
            "source_obligation_ref": self.source_obligation_ref,
        }

    def validate_source(self, obligation: dialogue.DialogueObligation,
                        situation: SituationContext | None = None) -> None:
        """Authenticate the canonical source and, when supplied, its answer window."""
        if type(obligation) is not dialogue.DialogueObligation:
            raise TypeError("learning source must be exact generic DialogueObligation")
        if LearningPlan.from_dict(self.as_dict()) != self or dialogue.DialogueObligation.from_dict(obligation.as_dict()) != obligation:
            raise ValueError("non-canonical learning continuation")
        if (self.source_obligation_ref != obligation.obligation_ref
                or self.source_query_ref != obligation.source_query_ref
                or self.answer_contract_ref != obligation.expected_answer_contract_ref
                or self.expires_at_turn != obligation.expires_turn_index
                or obligation.kind is not dialogue.ObligationKind.LEARNING_ANSWER
                or obligation.completion_receipt_ref is not None):
            raise ValueError("learning plan differs from its pending source obligation")
        if situation is not None:
            if type(situation) is not SituationContext:
                raise TypeError("learning answer requires exact SituationContext")
            if (situation.mode is not SemanticMode.REQUEST
                    or self.situation_ref != situation.situation_ref
                    or self.revision_pin != situation.revision_pin
                    or obligation.session_ref != situation.session_ref
                    or obligation.obligation_ref not in situation.obligation_refs
                    or not obligation.created_turn_index < situation.turn_index < obligation.expires_turn_index):
                raise ValueError("learning source does not bind the current pending answer session/window")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LearningPlan":
        data = exact_fields(data, cls._FIELDS, "LearningPlan")
        if exact_int(data["abi_version"], "abi_version") != LEARNING_PLAN_ABI_VERSION:
            raise ValueError("unsupported Learning Plan ABI")
        rebuilt = cls.create(
            verified_meaning_ref=data["verified_meaning_ref"],
            expression_ref=data["expression_ref"], situation_ref=data["situation_ref"],
            decision_ref=data["decision_ref"], source_query_ref=data["source_query_ref"],
            surface_literal=data["surface_literal"], target_ref=data["target_ref"],
            expected_target_kinds=wire_refs(data["expected_target_kinds"], "expected_target_kinds", maximum=256),
            provenance_refs=wire_refs(data["provenance_refs"], "provenance_refs", maximum=256),
            revision_pin=RevisionPin.from_dict(data["revision_pin"]),
            expires_at_turn=data["expires_at_turn"], capability_ref=data["capability_ref"],
            permission_ref=data["permission_ref"], commit_operator_ref=data["commit_operator_ref"],
            contract_ref=data["contract_ref"], answer_contract_ref=data["answer_contract_ref"],
            goal_ref=data["goal_ref"], source_obligation_ref=data["source_obligation_ref"],
        )
        if rebuilt.as_dict() != dict(data):
            raise ValueError("non-canonical LearningPlan")
        return rebuilt


class LearningCoordinator:
    """Materialize the exact evaluated learning draft; never reinterpret meaning."""

    def __init__(self, authority: Any, stores: SemanticStores, config: RuntimeConfig | None = None) -> None:
        self._authority = authority
        self._stores = stores
        self._config = config or RuntimeConfig.release()

    def materialize(self, evaluation: EvaluationBundle, meaning: VerifiedMeaning,
                    situation: SituationContext) -> tuple[LearningPlan | None, dialogue.DialogueObligation | None]:
        plan, pending, _source_journal = self.materialize_with_source(evaluation, meaning, situation)
        return plan, pending

    def materialize_with_source(self, evaluation: EvaluationBundle, meaning: VerifiedMeaning,
                                situation: SituationContext):
        """Return the exact journal that the shared dialogue binding validated."""
        if type(evaluation) is not EvaluationBundle or type(meaning) is not VerifiedMeaning or type(situation) is not SituationContext:
            raise TypeError("learning materialization requires exact R3 artifacts")
        decision = evaluation.decision
        if decision.verified_meaning_ref != meaning.verified_meaning_ref:
            raise ValueError("learning materialization meaning lineage mismatch")
        if decision.situation.situation_ref != situation.situation_ref:
            raise ValueError("learning materialization situation lineage mismatch")
        if (evaluation.expression != meaning.expression or evaluation.situation != situation
                or decision.expression_ref != meaning.expression.expression_ref
                or meaning.revision_pin != situation.revision_pin or evaluation.revision_pin != situation.revision_pin):
            raise ValueError("learning materialization expression or revision lineage mismatch")
        if decision.action is not DecisionAction.CREATE_LEARNING_OBLIGATION:
            if evaluation.learning_drafts:
                raise ValueError("non-learning Decision carries learning drafts")
            return None, None, None
        if situation.mode is not SemanticMode.REQUEST:
            raise ValueError("learning obligation requires REQUEST mode")
        if len(evaluation.learning_drafts) != 1:
            raise ValueError("learning obligation requires exactly one evaluated draft")
        draft = evaluation.learning_drafts[0]
        if draft.kind != "directive":
            raise ValueError("learning materialization requires a directive draft")
        if decision.learning_draft_refs != (draft.learning_draft_ref,):
            raise ValueError("learning Decision does not bind the evaluated draft")
        if draft.revision_pin != situation.revision_pin:
            raise ValueError("learning draft revision pin is stale")
        if draft.target_ref is None:
            raise ValueError("materializable learning draft requires target_ref")
        if not draft.expected_target_kinds:
            raise ValueError("materializable learning draft requires expected_target_kinds")
        from .dialogue import learning_answer_binding
        lowered = lower_designation_learning(self._authority, meaning.expression, situation)
        contract, app = lowered.contract, lowered.designation
        pending, source_journal = learning_answer_binding(self._stores, situation, app,
            maximum=self._config.max_orientation_alternatives)
        if (draft.source_query_ref != pending.source_query_ref
                or draft.proof_refs != (*lowered.proof_refs, pending.obligation_ref)
                or decision.proof_refs != lowered.proof_refs
                or decision.policy_refs != (contract.review_policy_ref,)):
            raise ValueError("learning draft does not bind the exact pending query")
        roles = {binding.role_ref: binding.filler for binding in app.roles}
        if (draft.surface_literal != roles["role:surface"].value or draft.target_ref != roles["role:target"].target_ref
                or draft.answer_contract_ref != pending.expected_answer_contract_ref
                or draft.answer_contract_ref != contract.answer_contract_ref):
            raise ValueError("learning draft changes the bound answer")
        atom = self._authority.atoms.get(draft.target_ref)
        if atom is None or draft.expected_target_kinds != (atom.kind,):
            raise ValueError("learning draft target kind differs from reviewed identity")
        plan = LearningPlan.create(
            contract_ref=contract.contract_ref,
            goal_ref=contract.goal_ref,
            capability_ref=contract.capability_ref,
            permission_ref=contract.permission_ref,
            commit_operator_ref=contract.commit_operator_ref,
            verified_meaning_ref=meaning.verified_meaning_ref,
            expression_ref=meaning.expression.expression_ref,
            situation_ref=situation.situation_ref,
            decision_ref=decision.decision_ref,
            source_query_ref=pending.source_query_ref,
            source_obligation_ref=pending.obligation_ref,
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
            expires_at_turn=pending.expires_turn_index,
        )
        # Binding is a read: retain the exact canonical source record without renewal.
        return plan, pending, source_journal


def learning_proposal_request(stores: SemanticStores, evaluation: EvaluationBundle,
        source: dialogue.DialogueObligation, source_journal,
        *, maximum: int) -> dict[str, Any]:
    """Retain already-materialized evidence in the existing journal request.

    The coordinator owns exact source-query validation. Its bounded journal read
    is retained here as immutable retry evidence, never a publication grant.
    """
    situation = evaluation.situation
    return {
        "learning_source_journal": source_journal.as_dict(),
        "learning_source_key": source_journal.entry.idempotency_key,
        "learning_session_state": dialogue.continuation_session_reservation(stores, situation),
        "learning_obligation_maximum": maximum,
        "learning_obligation_snapshot": dict(stores.r3_obligation_snapshot(source.session_ref, maximum=maximum)),
    }


def validate_learning_proposal_request(stores: SemanticStores, request: Mapping[str, Any], *, planned: bool):
    """Recheck retained witnesses inside the existing persistence transaction.

    No historical situation is repinned or rebound. Only the proposal's own
    PLANNED journal increment is permitted before its terminal transition.
    """
    from .persistence import StaleRevisionError
    from .r3_codec import thaw_json
    from .r3_effects import _predicted_pin
    from .r3_persistence import effect_journal_get
    request = thaw_json(request)
    meaning = VerifiedMeaning.from_dict(request["learning_meaning"])
    evaluation = EvaluationBundle.from_dict(request["learning_evaluation"])
    plan = LearningPlan.from_dict(request["learning_plan"])
    source = dialogue.DialogueObligation.from_dict(request["learning_source_obligation"])
    situation, decision = evaluation.situation, evaluation.decision
    plan.validate_source(source, situation)
    if (meaning.expression != evaluation.expression or meaning.revision_pin != situation.revision_pin
            or evaluation.revision_pin != situation.revision_pin
            or decision.verified_meaning_ref != meaning.verified_meaning_ref
            or plan.verified_meaning_ref != meaning.verified_meaning_ref
            or plan.decision_ref != decision.decision_ref or plan.expression_ref != meaning.expression.expression_ref
            or decision.action is not DecisionAction.CREATE_LEARNING_OBLIGATION):
        raise ValueError("learning proposal canonical lineage mismatch")
    if stores.revision_pin() != _predicted_pin(situation.revision_pin, effects=int(planned)):
        raise StaleRevisionError("learning proposal reservation revision changed")
    maximum = exact_int(request["learning_obligation_maximum"], "learning obligation maximum",
        minimum=1, maximum=RuntimeConfig.max_orientation_alternatives)
    snapshot = stores.r3_obligation_snapshot(source.session_ref, maximum=maximum)
    if (snapshot != request["learning_obligation_snapshot"]
            or snapshot["snapshot_ref"] != situation.obligation_snapshot_ref
            or tuple(snapshot["obligation_refs"]) != situation.obligation_refs):
        raise StaleRevisionError("learning proposal source snapshot changed")
    pending = stores.pending_dialogue_obligations(source.session_ref, situation.obligation_refs,
        maximum=maximum, turn_index=situation.turn_index)
    if source not in pending:
        raise ValueError("learning proposal source pending row changed")
    if dialogue.continuation_session_reservation(stores, situation) != request["learning_session_state"]:
        raise StaleRevisionError("learning proposal source session changed")
    journal = effect_journal_get(stores, request["learning_source_key"])
    if journal is None or journal.as_dict() != request["learning_source_journal"]:
        raise ValueError("learning proposal source query journal changed")
    return meaning, evaluation, plan, source


def publication_proposal_lineage(stores, authority, proposal, grant):
    """Validate historical proposal proof against today's linked authority.

    This read does not require the original pending row to remain live or its
    publication window to remain open. Publication eligibility is separate.
    """
    from .r3_codec import thaw_json
    from .r3_effects import NoEffectReceipt, NoEffectReason, R3EffectGateway, _predicted_pin
    from .r3_persistence import EffectJournalEntry, EffectJournalState
    if type(authority) is not LinkedAuthority or authority.generation != stores.revision_pin().authority_generation:
        raise ValueError("publication requires current linked authority")
    request = thaw_json(proposal.entry.request_payload)
    meaning = VerifiedMeaning.from_dict(request["learning_meaning"])
    evaluation = EvaluationBundle.from_dict(request["learning_evaluation"])
    plan = LearningPlan.from_dict(request["learning_plan"])
    source = dialogue.DialogueObligation.from_dict(request["learning_source_obligation"])
    situation, decision = evaluation.situation, evaluation.decision
    plan.validate_source(source, situation)
    lowered = lower_designation_learning(authority, meaning.expression, situation)
    contract = lowered.contract
    _, source_journal = dialogue.validate_learning_source(stores, source, situation, lowered.designation)
    if source_journal.as_dict() != request["learning_source_journal"]:
        raise ValueError("publication source query journal changed")
    if len(evaluation.learning_drafts) != 1:
        raise ValueError("publication requires one exact learning draft")
    draft = evaluation.learning_drafts[0]
    roles = {binding.role_ref: binding.filler for binding in lowered.designation.roles}
    expected_plan = LearningPlan.create(contract_ref=contract.contract_ref, goal_ref=contract.goal_ref,
        capability_ref=contract.capability_ref, permission_ref=contract.permission_ref,
        commit_operator_ref=contract.commit_operator_ref, verified_meaning_ref=meaning.verified_meaning_ref,
        expression_ref=meaning.expression.expression_ref, situation_ref=situation.situation_ref,
        decision_ref=decision.decision_ref, source_query_ref=source.source_query_ref,
        source_obligation_ref=source.obligation_ref, surface_literal=roles["role:surface"].value,
        target_ref=roles["role:target"].target_ref,
        expected_target_kinds=(authority.atoms[roles["role:target"].target_ref].kind,),
        answer_contract_ref=contract.answer_contract_ref,
        provenance_refs=tuple(dict.fromkeys((meaning.verification_receipt_ref, meaning.compilation_proof_ref,
            draft.learning_draft_ref, *draft.proof_refs))), revision_pin=situation.revision_pin,
        expires_at_turn=source.expires_turn_index)
    if (plan != expected_plan or meaning.expression != evaluation.expression
            or meaning.revision_pin != situation.revision_pin or evaluation.revision_pin != situation.revision_pin
            or decision.verified_meaning_ref != meaning.verified_meaning_ref
            or decision.action is not DecisionAction.CREATE_LEARNING_OBLIGATION
            or decision.proof_refs != lowered.proof_refs or decision.policy_refs != (contract.review_policy_ref,)
            or draft.proof_refs != (*lowered.proof_refs, source.obligation_ref)
            or draft.source_query_ref != source.source_query_ref
            or draft.surface_literal != plan.surface_literal or draft.target_ref != plan.target_ref
            or draft.expected_target_kinds != plan.expected_target_kinds
            or draft.answer_contract_ref != plan.answer_contract_ref):
        raise ValueError("publication proposal semantic lineage mismatch")
    key = R3EffectGateway._effect_key(decision.decision_ref, None, "no_effect:learning_obligation_only")
    origin = stable_ref("effect_journal_origin", {"decision_ref": decision.decision_ref,
        "kind": "no_effect:learning_obligation_only"})
    planned = EffectJournalEntry.create(idempotency_key=key, state=EffectJournalState.PLANNED,
        attempt_index=0, intent_ref=origin, decision_ref=decision.decision_ref, request_payload=request,
        observation_payload=None, outcome_ref=None, blocker_refs=(), parent_journal_ref=None,
        effect_revision=situation.revision_pin.effect_revision + 1)
    expected_receipt = NoEffectReceipt.create(reason=NoEffectReason.LEARNING_OBLIGATION_ONLY,
        idempotency_key=key, journal_origin_ref=origin, journal_preterminal_ref=planned.journal_ref,
        decision_ref=decision.decision_ref, verified_meaning_ref=meaning.verified_meaning_ref,
        expression_ref=meaning.expression.expression_ref, situation_ref=situation.situation_ref,
        program_ref=meaning.program_ref, learning_plan_ref=plan.plan_ref, source_obligation_ref=source.obligation_ref,
        proof_refs=decision.proof_refs, blocker_refs=decision.blocker_refs, input_revision_pin=situation.revision_pin,
        output_revision_pin=_predicted_pin(situation.revision_pin, effects=2, session=1))
    if (proposal.entry.state is not EffectJournalState.NO_EFFECT or proposal.entry.idempotency_key != key
            or proposal.entry.parent_journal_ref != planned.journal_ref
            or proposal.entry.outcome_ref != expected_receipt.receipt_ref
            or thaw_json(proposal.receipt_payload) != expected_receipt.as_dict()
            or proposal.entry.effect_revision != expected_receipt.output_revision_pin.effect_revision):
        raise ValueError("publication proposal terminal lineage mismatch")
    expected_scope = {"proposal_key": key, "proposal_journal_ref": proposal.entry.journal_ref,
        "proposal_receipt_ref": expected_receipt.receipt_ref, "plan_ref": plan.plan_ref,
        "source_obligation_ref": source.obligation_ref, "source_query_ref": source.source_query_ref,
        "source_journal_ref": source_journal.entry.journal_ref, "surface": plan.surface_literal,
        "target_ref": plan.target_ref, "policy_ref": contract.review_policy_ref}
    if any(grant[name] != value for name, value in expected_scope.items()):
        raise PermissionError("alias review does not authorize this exact proposal")
    if not source.created_turn_index < situation.turn_index < grant["expires_at_turn"] <= source.expires_turn_index:
        raise PermissionError("alias review expiry exceeds the original pending window")
    return meaning, evaluation, plan, source, contract


def publication_lineage(stores, authority, proposal, grant):
    """Historical proof plus live publication-only model/phase/conflict checks."""
    meaning, evaluation, plan, source, contract = publication_proposal_lineage(stores, authority, proposal, grant)
    if plan.revision_pin.model_identity != stores.revision_pin().model_identity:
        raise ValueError("publication cannot reuse a foreign model meaning")
    session = stores.r3_session_snapshot(source.session_ref)
    signature = authority.by_event_signature(contract.source_event_ref)
    if session["session_phase_ref"] not in signature.valid_session_phases:
        raise PermissionError("publication phase is not currently authorized")
    if authority.designations.facts_for_surface(plan.surface_literal, grant["language"]):
        raise ValueError("publication conflicts with an existing linked designation")
    return meaning, evaluation, plan, source, contract


def validate_publication_snapshot(stores, request, *, effect_increments):
    """Recheck bounded exact publication witnesses under the persistence lock."""
    from .r3_codec import thaw_json
    from .r3_effects import _predicted_pin
    from .r3_persistence import effect_journal_get
    from .persistence import StaleRevisionError
    request = thaw_json(request)
    pin = RevisionPin.from_dict(request["publication_pin"])
    if stores.revision_pin() != _predicted_pin(pin, effects=effect_increments):
        raise StaleRevisionError("publication snapshot revision changed")
    if stores.obligations.revision != request["publication_obligation_revision"]:
        raise StaleRevisionError("publication obligation revision changed")
    proposal = request["proposal"]
    original = proposal["entry"]["request_payload"]
    source = dialogue.DialogueObligation.from_dict(original["learning_source_obligation"])
    situation = EvaluationBundle.from_dict(original["learning_evaluation"]).situation
    for key, expected in ((proposal["entry"]["idempotency_key"], proposal),
            (original["learning_source_key"], original["learning_source_journal"])):
        journal = effect_journal_get(stores, key)
        if journal is None or journal.as_dict() != expected:
            raise ValueError("publication original proposal/source journal changed")
    session = stores.r3_session_snapshot(source.session_ref)
    if session != request["publication_session"]:
        raise StaleRevisionError("publication session snapshot changed")
    if not source.created_turn_index < situation.turn_index <= session["turn_index"] < request["review"]["grant"]["expires_at_turn"] <= source.expires_turn_index:
        raise ValueError("publication source/answer/current turn window is invalid")
    snapshot = stores.r3_obligation_snapshot(source.session_ref, maximum=RuntimeConfig.max_orientation_alternatives)
    if snapshot != request["publication_obligation_snapshot"]:
        raise StaleRevisionError("publication pending snapshot changed")
    pending = stores.pending_dialogue_obligations(source.session_ref, (source.obligation_ref,),
        maximum=1, turn_index=session["turn_index"])
    if pending != (source,) or snapshot["obligation_refs"] != [source.obligation_ref]:
        raise ValueError("publication requires its exact original single pending obligation")
    if stores.r3_alias_facts(request["review"]["grant"]["surface"], request["review"]["grant"]["language"],
            maximum=RuntimeConfig.max_designations_per_span):
        raise ValueError("publication alias conflicts with existing world evidence")
    return source
