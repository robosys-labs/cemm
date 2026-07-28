"""Bounded dialogue obligations and realization provenance.

Dialogue state is session context, not semantic authority. One typed learning plan
may be pending. It may be consumed only after its exact Stage-13 semantic commit.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Mapping

from cemm.learning_plans import LearningPlan, PendingLearningObligationV2
from cemm.model import canonical, lit, stable
from cemm.proof import VerifiedSemanticFocus


PendingLearningObligation = PendingLearningObligationV2


class DialogueState:
    """Session-local state with one exact typed learning continuation."""

    def __init__(self, max_pending: int = 1, expiry_turns: int = 4, max_verified_focus: int = 8):
        if int(max_pending) != 1:
            raise ValueError("canonical dialogue ABI permits exactly one pending obligation")
        if expiry_turns < 1:
            raise ValueError("dialogue expiry bound must be positive")
        self._pending: PendingLearningObligation | None = None
        self._last_surface_decision: Mapping[str, Any] | None = None
        if not 1 <= int(max_verified_focus) <= 32:
            raise ValueError("verified semantic focus bound must be in 1..32")
        self._verified_focus: deque[VerifiedSemanticFocus] = deque(maxlen=int(max_verified_focus))
        self._proof_bundles: dict[str, Any] = {}
        self.expiry_turns = int(expiry_turns)

    def expire(self, current_turn: int) -> None:
        if self._pending and self._pending.expired(int(current_turn)):
            self._pending = None

    def invalidate_pending_on_authority_reload(self) -> PendingLearningObligation | None:
        """Clear plans bound to the previous authority generation.

        A pending plan licenses one exact query/contract against one pinned
        authority generation. Reusing it after authority reload would bypass
        the new generation's contract and target-kind validation.
        """
        item = self._pending
        self._pending = None
        self._verified_focus.clear()
        self._proof_bundles.clear()
        return item

    @property
    def pending(self) -> PendingLearningObligation | None:
        return self._pending

    @property
    def pending_all(self) -> tuple[PendingLearningObligation, ...]:
        return (self._pending,) if self._pending else ()

    @property
    def last_surface_decision(self) -> Mapping[str, Any] | None:
        return dict(self._last_surface_decision) if self._last_surface_decision else None

    @property
    def verified_focus(self) -> tuple[VerifiedSemanticFocus, ...]:
        return tuple(self._verified_focus)

    def latest_focus(self, expected_kinds=()) -> VerifiedSemanticFocus | None:
        kinds = set(map(str, expected_kinds))
        for item in reversed(self._verified_focus):
            if not kinds or item.focus_kind in kinds:
                return item
        return None

    def proof_bundle(self, proof_ref: str | None):
        return self._proof_bundles.get(str(proof_ref)) if proof_ref else None

    def record_verified_focus(self, focus: VerifiedSemanticFocus, proof_bundle=None) -> None:
        if not isinstance(focus, VerifiedSemanticFocus):
            raise TypeError("dialogue focus must be VerifiedSemanticFocus")
        duplicate = bool(
            self._verified_focus and self._verified_focus[-1].focus_ref == focus.focus_ref
        )
        if not duplicate:
            self._verified_focus.append(focus)
        if proof_bundle is not None:
            proof_ref = getattr(proof_bundle, "proof_ref", None)
            if proof_ref != focus.proof_ref:
                raise ValueError("semantic focus proof ref mismatch")
            self._proof_bundles[str(proof_ref)] = proof_bundle
        live = {item.proof_ref for item in self._verified_focus if item.proof_ref}
        self._proof_bundles = {key: value for key, value in self._proof_bundles.items() if key in live}

    def context(self, current_turn: int | None = None) -> dict[str, Any]:
        if current_turn is not None:
            self.expire(int(current_turn))
        pending = self._pending
        decision = dict(self._last_surface_decision or {})
        plan = pending.plan if pending else None
        return {
            "pending_learning_obligation_ref": pending.obligation_ref if pending else None,
            "pending_learning_plan": plan.as_dict() if plan else None,
            "pending_learning_plan_ref": plan.plan_ref if plan else None,
            "pending_learning_label_type_ref": plan.label_type_ref if plan else None,
            "pending_learning_surface_literal": lit(plan.surface_literal) if plan else None,
            "pending_learning_surface": plan.surface_literal if plan else None,
            "pending_learning_contract_ref": plan.contract_ref if plan else None,
            "pending_learning_authority_generation": (
                plan.authority_generation if plan else None
            ),
            "pending_learning_original_candidate_ref": plan.original_candidate_ref if plan else None,
            "pending_learning_unresolved_span_ref": plan.unresolved_span_ref if plan else None,
            "pending_learning_obligations": [pending.as_dict()] if pending else [],
            "last_surface_decision": decision,
            "last_surface_decision_ref": decision.get("decision_ref"),
            "last_surface_response_ref": decision.get("response_ref"),
            "verified_semantic_focus": (
                self._verified_focus[-1].as_dict() if self._verified_focus else None
            ),
            "verified_semantic_focuses": [item.as_dict() for item in self._verified_focus],
        }

    @staticmethod
    def _validated_surface_decision(proof: Mapping[str, Any]) -> Mapping[str, Any] | None:
        decision = proof.get("surface_decision")
        equivalence = proof.get("response_equivalence")
        if not isinstance(decision, Mapping) or not isinstance(equivalence, Mapping):
            return None
        required = {
            "decision_ref",
            "response_ref",
            "response_action",
            "chosen_surface",
            "grammar_rule_ref",
            "reference_plan",
            "semantic_signature",
        }
        if required - set(decision):
            raise ValueError("surface decision trace is structurally incomplete")
        if not equivalence.get("equivalent"):
            raise ValueError("verified surface decision lacks equivalent Response CSIR receipt")
        return {**dict(decision), "response_equivalence": dict(equivalence)}

    def observe_response(
        self,
        response: Any,
        realization_proof: Mapping[str, Any] | None = None,
        *,
        cycle_ref: str | None = None,
        turn_index: int = 0,
    ) -> None:
        self.expire(int(turn_index))
        proof = dict(realization_proof or {})
        if not proof.get("verified"):
            return
        decision = self._validated_surface_decision(proof)
        if decision is not None:
            if decision.get("response_ref") != getattr(response, "response_ref", None):
                raise ValueError("surface decision response_ref does not match Response CSIR")
            self._last_surface_decision = decision
        if getattr(response, "action", None) != "request_learning_evidence":
            return
        literals = tuple(getattr(response, "evidence_literals", ()))
        if len(literals) != 1 or not str(literals[0]).strip():
            raise ValueError("learning request must expose exactly one unresolved surface")
        source_goal_ref = getattr(response, "obligation_ref", None)
        if not source_goal_ref:
            raise ValueError("learning request requires exact source goal obligation")
        qualifiers = dict(getattr(response, "qualifiers", {}) or {})
        raw_plan = qualifiers.get("learning_plan")
        if not isinstance(raw_plan, Mapping):
            raise ValueError("learning request lacks typed learning plan")
        plan = LearningPlan.from_dict(raw_plan)
        if plan.surface_literal != str(literals[0]):
            raise ValueError("learning plan surface differs from realized evidence literal")
        if plan.source_query_ref != qualifiers.get("query_ref"):
            raise ValueError("learning plan lost exact source query")
        if plan.source_query_kind != qualifiers.get("query_kind"):
            raise ValueError("learning plan lost exact query kind")
        learning_query = qualifiers.get("learning_query")
        if not isinstance(learning_query, Mapping):
            raise ValueError("learning request lacks exact source query structure")
        if canonical(plan.source_query) != canonical(dict(learning_query)):
            raise ValueError("learning plan source query differs from realized response query")
        plan = plan.bind_response(
            response_ref=getattr(response, "response_ref"),
            goal_ref=source_goal_ref,
        )
        existing = self._pending
        if existing is not None:
            if existing.plan.semantic_signature() == plan.semantic_signature():
                return
            raise ValueError("a live pending learning obligation cannot be silently replaced")
        obligation_ref = stable(
            "pending-learning-obligation",
            cycle_ref,
            plan.as_dict(),
            int(turn_index),
        )
        self._pending = PendingLearningObligation(obligation_ref, plan)

    def require(self, obligation_ref: str | None) -> PendingLearningObligation:
        if not obligation_ref:
            raise ValueError("pending learning operation requires an exact obligation ref")
        item = self._pending
        if item is None or item.obligation_ref != obligation_ref:
            raise ValueError(f"pending learning obligation is absent or expired: {obligation_ref}")
        return item

    def consume_after_commit(
        self,
        obligation_ref: str | None,
        *,
        commit_receipt_ref: str | None,
    ) -> PendingLearningObligation:
        item = self.require(obligation_ref)
        if not commit_receipt_ref:
            raise ValueError("pending learning obligation cannot be consumed before commit receipt")
        self._pending = None
        return item

    def consume(self, obligation_ref: str | None) -> PendingLearningObligation:
        raise ValueError(
            "pending learning obligations must be consumed with consume_after_commit"
        )
