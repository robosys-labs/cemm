"""Response move composition.

Primitive goals are semantic forces. Response moves are communicative acts
that can be realized in one or more languages. This stage remains
language-agnostic and preserves required components for later gates/ranking.
"""

from __future__ import annotations

from typing import Any

from .types import PrimitiveResponseGoal, ResponseMove, ResponseSituation


class ResponseMoveComposer:
    def compose(
        self,
        goals: list[PrimitiveResponseGoal],
        situation: ResponseSituation,
    ) -> list[ResponseMove]:
        if not goals:
            return [self._move("honest_abstain", [], confidence=0.3, tags={"missing_goals"})]

        goal_types = {goal.goal_type for goal in goals}
        moves: list[ResponseMove] = []

        if "refuse" in goal_types:
            safety_goals = [g for g in goals if g.goal_type in {"refuse", "deescalate"}]
            moves.append(self._move(
                "safety_refusal",
                safety_goals,
                confidence=max((g.confidence for g in safety_goals), default=0.95),
                priority=0,
                safety_required=True,
                required_components={"explicit_negative", "no_instruction", "no_endorsement"},
                satisfied_components={"explicit_negative", "no_instruction", "no_endorsement"},
                tags={"safety"},
            ))
            return moves

        if "repair_self" in goal_types:
            repair_goals = [g for g in goals if g.goal_type == "repair_self"]
            moves.append(self._move(
                "repair_prior_response",
                repair_goals,
                confidence=max(g.confidence for g in repair_goals),
                priority=1,
                required_components={"acknowledge_prior_failure"},
                satisfied_components={"acknowledge_prior_failure"},
                tags={"repair"},
            ))

        if "farewell" in goal_types:
            farewell_goals = [g for g in goals if g.goal_type == "farewell"]
            moves.append(self._move("social_farewell", farewell_goals, confidence=max(g.confidence for g in farewell_goals), tags={"social"}))

        if "greet" in goal_types:
            greet_goals = [g for g in goals if g.goal_type == "greet"]
            moves.append(self._move("social_greet", greet_goals, confidence=max(g.confidence for g in greet_goals), tags={"social"}))

        if "confirm_write" in goal_types:
            write_goals = [g for g in goals if g.goal_type in {"acknowledge", "confirm_write"}]
            moves.append(self._move(
                "confirm_memory_write",
                write_goals,
                confidence=max(g.confidence for g in write_goals),
                required_components={"write_committed"},
                satisfied_components={"write_committed"},
                tags={"memory"},
            ))
        elif "acknowledge" in goal_types:
            if not any(move.move_type in {"social_greet", "phatic_response"} for move in moves):
                ack_goals = [g for g in goals if g.goal_type == "acknowledge"]
                moves.append(self._move("acknowledge_heard", ack_goals, confidence=max(g.confidence for g in ack_goals), tags={"acknowledgment"}))

        if "reciprocate" in goal_types:
            phatic_goals = [g for g in goals if g.goal_type in {"reciprocate", "assert"}]
            moves.append(self._move("phatic_response", phatic_goals, confidence=max(g.confidence for g in phatic_goals), tags={"social"}))

        if "assert" in goal_types and self._has_answer(situation):
            assert_goals = [g for g in goals if g.goal_type == "assert"]
            evidence_refs = self._collect_refs(assert_goals)
            if not evidence_refs:
                evidence_refs = self._extract_evidence_refs(situation.answer_binding or getattr(situation.evidence, "answer_binding", None))
            moves.append(self._move(
                "answer",
                assert_goals,
                confidence=max(g.confidence for g in assert_goals),
                required_components={"grounded_answer"},
                satisfied_components={"grounded_answer"} if evidence_refs or not self._evidence_required(situation) else set(),
                evidence_refs=evidence_refs,
                tags={"answer"},
            ))

        if "explain_evidence" in goal_types:
            explain_goals = [g for g in goals if g.goal_type == "explain_evidence"]
            moves.append(self._move("evidence_explanation", explain_goals, confidence=max(g.confidence for g in explain_goals), evidence_refs=self._collect_refs(explain_goals), tags={"evidence"}))

        if "clarify" in goal_types or "query" in goal_types:
            clarify_goals = [g for g in goals if g.goal_type in {"clarify", "query"}]
            moves.append(self._move("clarify", clarify_goals, confidence=max(g.confidence for g in clarify_goals), tags={"clarification"}))

        if ("negate" in goal_types or "hedge" in goal_types) and not self._has_answer(situation):
            abstain_goals = [g for g in goals if g.goal_type in {"negate", "hedge"}]
            moves.append(self._move(
                "honest_abstain",
                abstain_goals,
                confidence=max((g.confidence for g in abstain_goals), default=0.55),
                required_components={"truthful_uncertainty"},
                satisfied_components={"truthful_uncertainty"},
                tags={"abstention"},
            ))

        if "deescalate" in goal_types and not any(m.move_type in {"safety_refusal", "deescalate"} for m in moves):
            deescalate_goals = [g for g in goals if g.goal_type == "deescalate"]
            moves.append(self._move("deescalate", deescalate_goals, confidence=max(g.confidence for g in deescalate_goals), tags={"deescalation"}))

        if not moves:
            moves.append(self._move("honest_abstain", goals, confidence=0.35, tags={"fallback"}))
        return sorted(moves, key=lambda move: move.priority)

    @staticmethod
    def _move(
        move_type: str,
        primitive_goals: list[PrimitiveResponseGoal],
        *,
        confidence: float,
        priority: int = 5,
        required_components: set[str] | None = None,
        satisfied_components: set[str] | None = None,
        safety_required: bool = False,
        evidence_refs: list[str] | None = None,
        tags: set[str] | None = None,
    ) -> ResponseMove:
        refs = list(evidence_refs or [])
        source_refs: list[str] = []
        for goal in primitive_goals:
            refs.extend(goal.evidence_refs)
            source_refs.extend(goal.source_refs)
        return ResponseMove(
            move_type=move_type,
            primitive_goals=list(primitive_goals),
            confidence=confidence,
            priority=priority,
            required_components=set(required_components or set()),
            satisfied_components=set(satisfied_components or set()),
            safety_required=safety_required,
            evidence_refs=_dedupe(refs),
            source_refs=_dedupe(source_refs),
            tags=set(tags or set()),
        )

    @staticmethod
    def _has_answer(situation: ResponseSituation) -> bool:
        binding = situation.answer_binding or getattr(situation.evidence, "answer_binding", None)
        return bool(getattr(binding, "has_answer", False))

    @staticmethod
    def _evidence_required(situation: ResponseSituation) -> bool:
        obligation = situation.obligation_frame
        return getattr(obligation, "evidence_policy", "") == "required"

    @staticmethod
    def _collect_refs(goals: list[PrimitiveResponseGoal]) -> list[str]:
        refs: list[str] = []
        for goal in goals:
            refs.extend(goal.evidence_refs)
            refs.extend(goal.source_refs)
        return _dedupe(refs)

    @staticmethod
    def _extract_evidence_refs(binding: Any) -> list[str]:
        refs: list[str] = []
        for fill in getattr(binding, "slot_fills", []) or []:
            refs.extend(getattr(fill, "source_frame_ids", []) or [])
            refs.extend(getattr(fill, "evidence_refs", []) or [])
        return _dedupe(refs)


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out
