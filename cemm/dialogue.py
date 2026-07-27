"""Bounded dialogue obligations and realization provenance.

Dialogue state is cycle/session context, not semantic authority.  One pending
learning obligation may be resumed, and it may be consumed only after the
corresponding semantic commit succeeds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from cemm.model import lit, stable


@dataclass(frozen=True)
class PendingLearningObligation:
    obligation_ref: str
    source_response_ref: str
    source_goal_ref: str
    surface: str
    learning_operation: str
    query: Mapping[str, Any] | None
    expected_answer_shape: Mapping[str, Any]
    expected_semantic_kinds: tuple[str, ...] = ()
    known_bindings: Mapping[str, Any] = field(default_factory=dict)
    original_cycle_ref: str | None = None
    original_candidate_ref: str | None = None
    unresolved_span_ref: str | None = None
    created_turn: int = 0
    expires_after_turn: int = 4
    resumable: bool = True

    def __post_init__(self) -> None:
        if not self.obligation_ref or not self.source_response_ref or not self.source_goal_ref:
            raise ValueError("pending learning obligation requires response and goal provenance")
        if not self.surface.strip():
            raise ValueError("pending learning obligation requires non-empty surface")
        if not self.learning_operation:
            raise ValueError("pending learning obligation requires an operation")
        if not self.expected_answer_shape:
            raise ValueError("pending learning obligation requires expected answer shape")
        if self.created_turn < 0 or self.expires_after_turn < 1:
            raise ValueError("pending learning obligation carries invalid turn bounds")
        if not self.resumable:
            raise ValueError("non-resumable items must not enter pending dialogue state")

    def expired(self, current_turn: int) -> bool:
        return int(current_turn) > self.created_turn + self.expires_after_turn

    def as_dict(self) -> dict[str, Any]:
        return {
            "obligation_ref": self.obligation_ref,
            "source_response_ref": self.source_response_ref,
            "source_goal_ref": self.source_goal_ref,
            "surface": self.surface,
            "learning_operation": self.learning_operation,
            "query": dict(self.query) if self.query else None,
            "expected_answer_shape": dict(self.expected_answer_shape),
            "expected_semantic_kinds": list(self.expected_semantic_kinds),
            "known_bindings": dict(self.known_bindings),
            "original_cycle_ref": self.original_cycle_ref,
            "original_candidate_ref": self.original_candidate_ref,
            "unresolved_span_ref": self.unresolved_span_ref,
            "created_turn": self.created_turn,
            "expires_after_turn": self.expires_after_turn,
            "resumable": self.resumable,
        }


class DialogueState:
    """Session-local state with one exact pending learning continuation."""

    def __init__(self, max_pending: int = 1, expiry_turns: int = 4):
        if int(max_pending) != 1:
            raise ValueError("canonical dialogue ABI permits exactly one pending obligation")
        if expiry_turns < 1:
            raise ValueError("dialogue expiry bound must be positive")
        self._pending: PendingLearningObligation | None = None
        self._last_surface_decision: Mapping[str, Any] | None = None
        self.expiry_turns = int(expiry_turns)

    def expire(self, current_turn: int) -> None:
        if self._pending and self._pending.expired(int(current_turn)):
            self._pending = None

    @property
    def pending(self) -> PendingLearningObligation | None:
        return self._pending

    @property
    def pending_all(self) -> tuple[PendingLearningObligation, ...]:
        return (self._pending,) if self._pending else ()

    @property
    def last_surface_decision(self) -> Mapping[str, Any] | None:
        return dict(self._last_surface_decision) if self._last_surface_decision else None

    def context(self, current_turn: int | None = None) -> dict[str, Any]:
        if current_turn is not None:
            self.expire(int(current_turn))
        pending = self._pending
        decision = dict(self._last_surface_decision or {})
        return {
            "pending_learning_obligation_ref": pending.obligation_ref if pending else None,
            "pending_learning_surface_literal": lit(pending.surface) if pending else None,
            "pending_learning_surface": pending.surface if pending else None,
            "pending_learning_operation": pending.learning_operation if pending else None,
            "pending_learning_original_candidate_ref": pending.original_candidate_ref if pending else None,
            "pending_learning_unresolved_span_ref": pending.unresolved_span_ref if pending else None,
            "pending_learning_obligations": [pending.as_dict()] if pending else [],
            "last_surface_decision": decision,
            "last_surface_decision_ref": decision.get("decision_ref"),
            "last_surface_response_ref": decision.get("response_ref"),
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
        operation = str(qualifiers.get("learning_operation") or "")
        if not operation:
            raise ValueError("learning request lacks structured learning operation")
        expected_shape = dict(
            qualifiers.get("expected_answer_shape")
            or {
                "operation": operation,
                "surface_cardinality": "one",
                "semantic_kind_candidates": list(qualifiers.get("expected_semantic_kinds", ())),
            }
        )
        surface = str(literals[0])
        existing = self._pending
        if existing is not None:
            same_request = (
                existing.source_response_ref == response.response_ref
                and existing.source_goal_ref == source_goal_ref
                and existing.surface == surface
                and existing.learning_operation == operation
            )
            if same_request:
                return
            raise ValueError(
                "a live pending learning obligation cannot be silently replaced"
            )
        payload = (
            response.response_ref,
            source_goal_ref,
            surface,
            operation,
            qualifiers.get("learning_query"),
            expected_shape,
            qualifiers.get("original_candidate_ref"),
            qualifiers.get("unresolved_span_ref"),
            int(turn_index),
        )
        self._pending = PendingLearningObligation(
            stable("pending-learning-obligation", payload),
            response.response_ref,
            source_goal_ref,
            surface,
            operation,
            qualifiers.get("learning_query"),
            expected_shape,
            tuple(qualifiers.get("expected_semantic_kinds", ())),
            dict(qualifiers.get("known_bindings", {})),
            cycle_ref,
            qualifiers.get("original_candidate_ref"),
            qualifiers.get("unresolved_span_ref"),
            int(turn_index),
            self.expiry_turns,
            True,
        )

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
        """Compatibility-free guard: direct consumption is intentionally forbidden."""
        raise ValueError(
            "pending learning obligations must be consumed with consume_after_commit"
        )
