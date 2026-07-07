"""ResponseMoveComposer — map primitive goals to response moves.

Deterministic mapping: primitive goals → response moves.
Moves are communicative acts that bundle semantic forces.
"""

from __future__ import annotations

from typing import Any

from .types import (
    PrimitiveResponseGoal,
    ResponseMove,
    RESPONSE_MOVES,
    ResponseSituation,
)


class ResponseMoveComposer:
    """Compose response moves from primitive goals.

    Maps the semantic force (goals) to communicative acts (moves).
    Multiple goals may collapse into one move, or expand into several.
    """

    def compose(
        self,
        goals: list[PrimitiveResponseGoal],
        situation: ResponseSituation,
    ) -> list[ResponseMove]:
        if not goals:
            return [ResponseMove(move_type="honest_abstain", confidence=0.3)]

        goal_types = {g.goal_type for g in goals}
        moves: list[ResponseMove] = []

        # Safety refusal: refuse + deescalate → safety_refusal
        if "refuse" in goal_types and "deescalate" in goal_types:
            moves.append(ResponseMove(
                move_type="safety_refusal",
                primitive_goals=[g for g in goals if g.goal_type in ("refuse", "deescalate")],
                confidence=0.95,
                safety_required=True,
            ))
            return moves

        # Farewell
        if "farewell" in goal_types:
            moves.append(ResponseMove(
                move_type="social_farewell",
                primitive_goals=[g for g in goals if g.goal_type == "farewell"],
                confidence=0.9,
            ))

        # Greet
        if "greet" in goal_types:
            moves.append(ResponseMove(
                move_type="social_greet",
                primitive_goals=[g for g in goals if g.goal_type == "greet"],
                confidence=0.9,
            ))

        # Repair self
        if "repair_self" in goal_types:
            moves.append(ResponseMove(
                move_type="repair_prior_response",
                primitive_goals=[g for g in goals if g.goal_type == "repair_self"],
                confidence=0.8,
            ))

        # Confirm memory write
        if "confirm_write" in goal_types:
            moves.append(ResponseMove(
                move_type="confirm_memory_write",
                primitive_goals=[g for g in goals if g.goal_type in ("acknowledge", "confirm_write")],
                confidence=0.85,
            ))

        # Reciprocate (check-in)
        if "reciprocate" in goal_types:
            moves.append(ResponseMove(
                move_type="phatic_response",
                primitive_goals=[g for g in goals if g.goal_type in ("reciprocate", "assert")],
                confidence=0.8,
            ))

        # Pure acknowledge (heard but not stored)
        if "acknowledge" in goal_types and "confirm_write" not in goal_types:
            # Don't duplicate if we already have a greet or reciprocate
            existing = {m.move_type for m in moves}
            if not (existing & {"social_greet", "phatic_response"}):
                moves.append(ResponseMove(
                    move_type="acknowledge_heard",
                    primitive_goals=[g for g in goals if g.goal_type == "acknowledge"],
                    confidence=0.75,
                ))

        # Answer (assert with evidence)
        if "assert" in goal_types:
            binding = situation.answer_binding
            has_answer = binding is not None and binding.has_answer
            obligation = situation.obligation_frame
            is_answer_kind = False
            if obligation is not None:
                is_answer_kind = obligation.obligation_kind.startswith("answer_")

            if is_answer_kind and has_answer:
                moves.append(ResponseMove(
                    move_type="answer",
                    primitive_goals=[g for g in goals if g.goal_type == "assert"],
                    confidence=0.85,
                    evidence_refs=self._extract_evidence_refs(binding),
                ))
            elif "hedge" in goal_types or "negate" in goal_types:
                # No answer + hedge/negate = honest abstain
                if not any(m.move_type == "honest_abstain" for m in moves):
                    moves.append(ResponseMove(
                        move_type="honest_abstain",
                        primitive_goals=[g for g in goals if g.goal_type in ("negate", "hedge")],
                        confidence=0.6,
                    ))

        # Clarify
        if "query" in goal_types:
            moves.append(ResponseMove(
                move_type="clarify",
                primitive_goals=[g for g in goals if g.goal_type == "query"],
                confidence=0.7,
            ))

        # Deescalate (non-safety, standalone)
        if "deescalate" in goal_types and "refuse" not in goal_types:
            moves.append(ResponseMove(
                move_type="deescalate",
                primitive_goals=[g for g in goals if g.goal_type == "deescalate"],
                confidence=0.7,
            ))

        # Fallback: if no moves were composed, produce honest abstain
        if not moves:
            moves.append(ResponseMove(
                move_type="honest_abstain",
                primitive_goals=goals,
                confidence=0.3,
            ))

        return moves

    def _extract_evidence_refs(self, binding: Any) -> list[str]:
        if binding is None:
            return []
        refs: list[str] = []
        for fill in getattr(binding, "slot_fills", []):
            refs.extend(fill.source_frame_ids)
            refs.extend(fill.evidence_refs)
        return refs
