"""Primitive goal composition from semantic runtime state.

This module is deliberately language-agnostic. It does not classify English
surface strings. Social, safety, memory, and answer behavior must arrive as
semantic structure: obligation kind, response act hints, UOL intent atoms,
safety frames, write outcomes, and answer bindings.
"""

from __future__ import annotations

from typing import Any

from .types import PrimitiveResponseGoal, ResponseSituation


ANSWER_OBLIGATIONS = frozenset({
    "answer_concept",
    "answer_relation",
    "answer_self_model",
    "answer_user_profile",
    "answer_self_identity",
    "answer_self_capability",
    "answer_self_knowledge",
})

GREETING_ACTS = frozenset({"greeting", "social_greet"})
CHECKIN_ACTS = frozenset({"phatic_checkin", "reciprocal_phatic", "status_checkin"})
FRUSTRATION_ACTS = frozenset({"frustration_signal", "user_complaint"})
REPAIR_ACTS = frozenset({"repair", "confusion_repair", "correction"})
FAREWELL_ACTS = frozenset({"session_exit", "farewell"})
ACK_ACTS = frozenset({"acknowledgment", "playful_acknowledgment"})


class PrimitiveGoalComposer:
    """Compose language-agnostic primitive goals for one response turn."""

    def compose(self, situation: ResponseSituation) -> list[PrimitiveResponseGoal]:
        obligation = situation.obligation_frame
        if obligation is None:
            return [self._goal("negate", confidence=0.35, reason="missing_obligation")]

        safety_goals = self._compose_safety(situation)
        if safety_goals:
            return safety_goals

        reaction_goals = self._compose_reaction(situation)
        kind = getattr(obligation, "obligation_kind", "") or ""

        if kind == "exit":
            return [*reaction_goals, self._goal("farewell", confidence=0.95, reason="exit_obligation")]

        if kind == "social_reply":
            return [*reaction_goals, *self._compose_social(situation)]

        if kind == "store_patch":
            return [*reaction_goals, *self._compose_store_patch(situation)]

        if kind == "acknowledge_emotional_context":
            return [*reaction_goals, *self._compose_emotional(situation)]

        if kind == "ask_clarification":
            return [*reaction_goals, self._goal("clarify", confidence=0.85, reason="clarification_obligation")]

        if kind == "repair":
            return [*reaction_goals, self._goal("repair_self", confidence=0.85, reason="repair_obligation")]

        if kind in ANSWER_OBLIGATIONS:
            return [*reaction_goals, *self._compose_answer(situation)]

        if kind == "continue_teaching":
            return [*reaction_goals, self._goal("acknowledge", confidence=0.8, reason="continue_teaching")]

        if kind == "abstain_policy":
            return [
                *reaction_goals,
                self._goal("negate", confidence=0.65, reason="abstain_policy"),
                self._goal("hedge", confidence=0.65, reason="abstain_policy"),
            ]

        return [*reaction_goals, self._goal("acknowledge", confidence=0.45, reason="unknown_obligation")]

    def _compose_safety(self, situation: ResponseSituation) -> list[PrimitiveResponseGoal]:
        safety = situation.safety_frame
        if safety is None:
            return []
        category = (getattr(safety, "category", "") or getattr(safety, "risk_type", "") or "").lower()
        severity = (getattr(safety, "severity", "") or getattr(safety, "risk_level", "") or "").lower()
        if not category or category in {"none", "safe", "low"}:
            return []
        constraints = {"no_instruction", "no_endorsement"}
        if severity in {"high", "critical", "imminent"}:
            constraints.add("immediate_harm_prevention")
        return [
            self._goal(
                "refuse",
                confidence=0.97,
                required=True,
                priority=0,
                constraints=constraints | {"explicit_negative"},
                reason=f"safety:{category}",
            ),
            self._goal(
                "deescalate",
                confidence=0.9,
                required=True,
                priority=1,
                constraints=constraints,
                reason=f"safety:{category}",
            ),
        ]

    def _compose_reaction(self, situation: ResponseSituation) -> list[PrimitiveResponseGoal]:
        reaction = situation.reaction_signal
        if reaction is None:
            if situation.temperature.conversation_repair_debt <= 0:
                return []
            return [self._goal("repair_self", confidence=0.65, priority=2, reason="repair_debt")]

        failed = bool(
            getattr(reaction, "is_negative", False)
            or getattr(reaction, "marks_previous_failed", False)
            or getattr(reaction, "requires_repair", False)
        )
        confidence = float(getattr(reaction, "confidence", 0.7) or 0.7)
        if not failed or confidence < 0.45:
            return []
        return [self._goal("repair_self", confidence=confidence, priority=1, reason="reaction_signal")]

    def _compose_social(self, situation: ResponseSituation) -> list[PrimitiveResponseGoal]:
        acts = self._act_keys(situation)
        goals: list[PrimitiveResponseGoal] = []

        if acts & FAREWELL_ACTS:
            goals.append(self._goal("farewell", confidence=0.92, reason="farewell_act"))
        if acts & GREETING_ACTS:
            goals.append(self._goal("greet", confidence=0.9, reason="greeting_act"))
        if acts & CHECKIN_ACTS:
            goals.append(self._goal("assert", confidence=0.65, slots={"self_state_key": "operational"}, reason="checkin_act"))
            goals.append(self._goal("reciprocate", confidence=0.8, reason="checkin_act"))
        if acts & FRUSTRATION_ACTS:
            goals.append(self._goal("repair_self", confidence=0.72, priority=2, reason="frustration_act"))
            goals.append(self._goal("acknowledge", confidence=0.65, reason="frustration_act"))
        if acts & ACK_ACTS:
            goals.append(self._goal("acknowledge", confidence=0.7, reason="acknowledgment_act"))

        if not goals:
            instruction_kind = self._entry_instruction_kind(situation)
            if instruction_kind == "repair":
                goals.append(self._goal("repair_self", confidence=0.75, reason="instruction_kind:repair"))
            else:
                goals.append(self._goal("acknowledge", confidence=0.55, reason="social_reply_without_specific_act"))
        return goals

    def _compose_store_patch(self, situation: ResponseSituation) -> list[PrimitiveResponseGoal]:
        write = situation.write_outcome
        if write is not None and write.committed:
            refs = [*write.committed_patch_ids, *write.committed_record_ids]
            return [
                self._goal("acknowledge", confidence=0.85, evidence_refs=refs, reason="write_committed"),
                self._goal("confirm_write", confidence=0.9, evidence_refs=refs, reason="write_committed"),
            ]
        if write is not None and write.commit_status in {"rejected", "conflict", "quarantined"}:
            return [
                self._goal("acknowledge", confidence=0.7, reason=f"write_{write.commit_status}"),
                self._goal("clarify", confidence=0.65, reason=f"write_{write.commit_status}"),
            ]
        return [self._goal("acknowledge", confidence=0.75, reason="write_not_committed")]

    def _compose_emotional(self, situation: ResponseSituation) -> list[PrimitiveResponseGoal]:
        goals = [self._goal("acknowledge", confidence=0.8, reason="emotional_context")]
        obligation = situation.obligation_frame
        for pred in getattr(obligation, "context", {}).get("affordance_predictions", []) if obligation is not None else []:
            if getattr(pred, "effect_type", "") != "evaluation_shift":
                continue
            patch_template = getattr(pred, "predicted_patch_template", {}) or {}
            shift = patch_template.get("affect_shift", "")
            if shift:
                goals.append(self._goal(
                    "assert",
                    confidence=float(getattr(pred, "confidence", 0.6) or 0.6),
                    slots={"evaluation_shift": shift},
                    source_refs=[getattr(pred, "id", "") or getattr(pred, "affordance_key", "")],
                    reason="affordance_evaluation_shift",
                ))
            break
        return goals

    def _compose_answer(self, situation: ResponseSituation) -> list[PrimitiveResponseGoal]:
        binding = situation.answer_binding or getattr(situation.evidence, "answer_binding", None)
        has_answer = bool(getattr(binding, "has_answer", False))
        evidence_refs = list(getattr(situation.evidence, "evidence_refs", []) or [])
        if not evidence_refs and binding is not None:
            for fill in getattr(binding, "slot_fills", []) or []:
                evidence_refs.extend(getattr(fill, "source_frame_ids", []) or [])
                evidence_refs.extend(getattr(fill, "evidence_refs", []) or [])
        if has_answer:
            answer_confidence = float(getattr(binding, "confidence", 0.8) or 0.8)
            goals = [self._goal("assert", confidence=answer_confidence, evidence_refs=evidence_refs, reason="answer_bound")]
            obligation = situation.obligation_frame
            if getattr(obligation, "evidence_policy", "") == "required":
                if self._should_explain_evidence(situation, answer_confidence):
                    goals.append(self._goal("explain_evidence", confidence=0.65, evidence_refs=evidence_refs, reason="evidence_required"))
            return goals
        abstention_reason = getattr(binding, "abstention_reason", "") or getattr(situation.evidence, "abstention_reason", "")
        if abstention_reason in {"missing_required_slots", "clarify"}:
            return [self._goal("clarify", confidence=0.75, reason=abstention_reason)]
        return [
            self._goal("negate", confidence=0.65, reason=abstention_reason or "no_answer"),
            self._goal("hedge", confidence=0.6, reason=abstention_reason or "no_answer"),
        ]

    @staticmethod
    def _should_explain_evidence(situation: ResponseSituation, answer_confidence: float) -> bool:
        """Gate evidence explanation rendering.

        Evidence is internally required for all questions, but the explanation
        should only be rendered externally when at least one of:
        - user explicitly requested source/reason
        - confidence is borderline (below 0.75)
        - style.detail is high (above 0.7)
        - user_detail_appetite is high (above 0.7)
        - debug/diagnostics mode is active
        """
        style_detail = float(getattr(situation.style, "detail", 0.5) or 0.5)
        if style_detail > 0.7:
            return True
        user_detail_appetite = float(getattr(situation.temperature, "user_detail_appetite", 0.5) or 0.5)
        if user_detail_appetite > 0.7:
            return True
        obligation = situation.obligation_frame
        source_requested = False
        if obligation is not None:
            context = getattr(obligation, "context", {}) or {}
            act_hints = context.get("response_act_hints", []) or []
            for hint in act_hints:
                hint_str = str(hint).lower() if isinstance(hint, str) else str(hint.get("act", "") or hint.get("intent", "")).lower()
                if any(marker in hint_str for marker in ("source", "reason", "evidence", "why", "how_do_you_know", "citation")):
                    source_requested = True
                    break
        if source_requested:
            return True
        obligation_contract = getattr(obligation, "context", {}).get("obligation_contract") if obligation is not None else None
        query_contract = getattr(obligation_contract, "query_contract", None)
        if (
            getattr(obligation, "obligation_kind", "") == "answer_user_profile"
            and getattr(query_contract, "query_kind", "") == "profile_dimension"
        ):
            return False
        if answer_confidence < 0.75:
            return True
        budget = getattr(situation, "budget_decision", None)
        if budget is not None and getattr(budget, "risk_level", "") in {"high", "critical"}:
            return True
        return False

    def _act_keys(self, situation: ResponseSituation) -> set[str]:
        acts: set[str] = set()
        obligation = situation.obligation_frame
        context = getattr(obligation, "context", {}) or {}
        for hint in context.get("response_act_hints", []) or []:
            if isinstance(hint, str):
                acts.add(hint)
            elif isinstance(hint, dict):
                act = str(hint.get("act", "") or hint.get("intent", "")).strip()
                if act:
                    acts.add(act)

        for atom in self._entry_atoms(situation):
            if getattr(atom, "kind", "") == "intent":
                key = getattr(atom, "key", "") or getattr(atom, "intent_key", "")
                if key:
                    acts.add(str(key))
            for key in ("intent_key", "act_type", "response_act"):
                value = getattr(atom, "features", {}).get(key, "") if hasattr(atom, "features") else ""
                if value:
                    acts.add(str(value))

        entry = self._entry_instruction(situation)
        for act_type in getattr(entry, "candidate_act_types", []) or []:
            if act_type:
                acts.add(str(act_type))

        graph = situation.uol_graph
        if graph is not None and entry is not None:
            group_id = getattr(entry, "group_id", "")
            for group in getattr(graph, "groups", []) or []:
                if getattr(group, "id", "") != group_id:
                    continue
                for act_type in getattr(group, "features", {}).get("candidate_act_types", []) or []:
                    if act_type:
                        acts.add(str(act_type))
            wanted = set(getattr(entry, "construction_match_ids", []) or [])
            for match in getattr(graph, "construction_matches", []) or []:
                if wanted and getattr(match, "id", "") not in wanted:
                    continue
                if not wanted and getattr(match, "group_id", "") != group_id:
                    continue
                for hint in getattr(match, "pragmatic_hints", []) or []:
                    if hint:
                        acts.add(str(hint))
        return {a.strip() for a in acts if a and a.strip()}

    def _entry_instruction_kind(self, situation: ResponseSituation) -> str:
        entry = self._entry_instruction(situation)
        return getattr(entry, "instruction_kind", "") if entry is not None else ""

    def _entry_instruction(self, situation: ResponseSituation) -> Any | None:
        program = situation.semantic_program
        if program is None:
            return None
        return getattr(program, "entry_instruction", None)

    def _entry_atoms(self, situation: ResponseSituation) -> list[Any]:
        graph = situation.uol_graph
        entry = self._entry_instruction(situation)
        if graph is None or entry is None:
            return []
        atoms = getattr(graph, "atoms", {}) or {}
        return [atoms[atom_id] for atom_id in getattr(entry, "atom_ids", []) or [] if atom_id in atoms]

    @staticmethod
    def _goal(
        goal_type: str,
        *,
        confidence: float,
        required: bool = False,
        priority: int = 5,
        target_refs: list[str] | None = None,
        source_refs: list[str] | None = None,
        evidence_refs: list[str] | None = None,
        constraints: set[str] | None = None,
        slots: dict[str, Any] | None = None,
        reason: str = "",
    ) -> PrimitiveResponseGoal:
        return PrimitiveResponseGoal(
            goal_type=goal_type,
            confidence=confidence,
            required=required,
            priority=priority,
            target_refs=list(target_refs or []),
            source_refs=[ref for ref in list(source_refs or []) if ref],
            evidence_refs=[ref for ref in list(evidence_refs or []) if ref],
            constraints=set(constraints or set()),
            slots=dict(slots or {}),
            reason=reason,
        )
