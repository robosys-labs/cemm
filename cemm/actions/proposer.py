"""Semantic internal action proposal for CEMM Phase 8.

The proposer reads already-structured runtime state. It must not inspect raw
natural-language text or use language-specific cue tables.
"""

from __future__ import annotations

from typing import Any, Iterable

from cemm.response.types import InternalActionProposal, RealizedCandidate, ResponseCandidatePlan, ResponseSituation


_NONE_KEYS = {"", "none", "safe", "low"}


class InternalActionProposer:
    def propose(
        self,
        situation: ResponseSituation,
        selected_plan: ResponseCandidatePlan,
        realized: RealizedCandidate | None = None,
    ) -> list[InternalActionProposal]:
        proposals: list[InternalActionProposal] = []
        proposals.append(self._output_state_action(situation, selected_plan, realized))
        proposals.extend(self._dialogue_expectation_actions(situation, selected_plan))
        proposals.extend(self._safety_actions(situation))
        proposals.extend(self._repair_actions(situation, selected_plan))
        proposals.extend(self._write_actions(situation))
        proposals.extend(self._distillation_actions(situation))
        proposals.extend(self._locale_language_actions(situation))
        return _dedupe_actions([p for p in proposals if p is not None])

    def _output_state_action(
        self,
        situation: ResponseSituation,
        selected_plan: ResponseCandidatePlan,
        realized: RealizedCandidate | None,
    ) -> InternalActionProposal:
        obligation = situation.obligation_frame
        return InternalActionProposal(
            action_type="update_output_state",
            payload={
                "source": "response_formation",
                "plan_id": selected_plan.plan_id,
                "framing_variant": selected_plan.framing_variant,
                "move_types": [m.move_type for m in selected_plan.moves],
                "assistant_intent": getattr(obligation, "obligation_kind", "") if obligation is not None else "",
                "response_mode": getattr(obligation, "response_mode", "") if obligation is not None else "",
                "language": getattr(realized, "language", situation.language),
                "has_text": bool(getattr(realized, "text", "")),
            },
            confidence=1.0 if selected_plan.moves else 0.5,
            reversible=True,
            source_refs=_source_refs_from_plan(selected_plan),
            reason="selected_response_plan",
        )

    def _dialogue_expectation_actions(
        self,
        situation: ResponseSituation,
        selected_plan: ResponseCandidatePlan,
    ) -> list[InternalActionProposal]:
        actions: list[InternalActionProposal] = []
        move_types = {m.move_type for m in selected_plan.moves}
        if "clarify" in move_types:
            actions.append(InternalActionProposal(
                action_type="set_dialogue_expectation",
                payload={"expected_user_answer_type": "clarification", "plan_id": selected_plan.plan_id},
                confidence=0.85,
                reversible=True,
                source_refs=_source_refs_from_plan(selected_plan),
                reason="clarification_move_selected",
            ))
        if "phatic_response" in move_types:
            actions.append(InternalActionProposal(
                action_type="set_dialogue_expectation",
                payload={"expected_user_answer_type": "social_status", "plan_id": selected_plan.plan_id},
                confidence=0.75,
                reversible=True,
                source_refs=_source_refs_from_plan(selected_plan),
                reason="phatic_response_selected",
            ))
        return actions

    def _safety_actions(self, situation: ResponseSituation) -> list[InternalActionProposal]:
        safety = situation.safety_frame
        if safety is None:
            return []
        category = str(getattr(safety, "category", "") or getattr(safety, "risk_type", "") or "").lower()
        if category in _NONE_KEYS:
            return []
        source_refs = _object_refs(safety)
        return [InternalActionProposal(
            action_type="flag_safety_event",
            payload={
                "category": category,
                "severity": getattr(safety, "severity", "") or getattr(safety, "risk_level", ""),
                "requires_followup": bool(getattr(safety, "requires_followup", False)),
            },
            confidence=float(getattr(safety, "confidence", 0.9) or 0.9),
            reversible=False,
            source_refs=source_refs,
            reason="safety_frame_present",
        )]

    def _repair_actions(self, situation: ResponseSituation, selected_plan: ResponseCandidatePlan) -> list[InternalActionProposal]:
        move_types = {m.move_type for m in selected_plan.moves}
        reaction = situation.reaction_signal
        source_refs = _source_refs_from_plan(selected_plan)
        source_refs.extend(_object_refs(reaction))
        if "repair_prior_response" not in move_types and situation.temperature.conversation_repair_debt <= 0:
            return []
        return [InternalActionProposal(
            action_type="mark_previous_response_failed",
            payload={"repair_target_turn_id": getattr(reaction, "repair_target_turn_id", "") if reaction is not None else ""},
            confidence=float(getattr(reaction, "confidence", 0.7) or 0.7) if reaction is not None else 0.65,
            reversible=True,
            source_refs=_dedupe(source_refs),
            reason="repair_move_selected",
        )]

    def _write_actions(self, situation: ResponseSituation) -> list[InternalActionProposal]:
        write = situation.write_outcome
        if write is None or write.commit_status == "none":
            return []
        refs = [*write.committed_patch_ids, *write.committed_record_ids, *write.rejected_patch_ids, *write.conflict_ids]
        return [InternalActionProposal(
            action_type="record_write_outcome",
            payload={
                "commit_status": write.commit_status,
                "patch_count": write.patch_count,
                "committed_count": write.committed_count,
                "rejected_count": write.rejected_count,
                "quarantined_count": write.quarantined_count,
            },
            confidence=0.95,
            reversible=False,
            source_refs=_dedupe(refs),
            reason="write_outcome_available",
        )]

    def _distillation_actions(self, situation: ResponseSituation) -> list[InternalActionProposal]:
        result = getattr(situation, "distillation_result", None)
        if result is None:
            return []
        return [InternalActionProposal(
            action_type="record_distillation_coverage",
            payload={
                "strategy": getattr(result, "strategy", ""),
                "coverage_estimate": getattr(result, "coverage_estimate", 0.0),
                "partial": bool(getattr(result, "partial", False)),
                "blind_spot_count": len(getattr(result, "blind_spots", []) or []),
            },
            confidence=float(getattr(result, "confidence", 0.7) or 0.7),
            reversible=False,
            source_refs=list(getattr(result, "evidence_refs", []) or []),
            reason="distillation_result_available",
        )]

    def _locale_language_actions(self, situation: ResponseSituation) -> list[InternalActionProposal]:
        actions: list[InternalActionProposal] = []
        for carrier in self._semantic_carriers(situation):
            features = dict(getattr(carrier, "features", {}) or {})
            refs = _object_refs(carrier)
            confidence = float(getattr(carrier, "confidence", features.get("confidence", 0.5)) or 0.5)
            locale_hint = features.get("locale_hint") or features.get("locale")
            language_hint = features.get("language_hint") or features.get("language") or features.get("language_tag")
            if locale_hint:
                actions.append(InternalActionProposal(
                    action_type="set_locale_hint",
                    payload={"locale": locale_hint, "authority": features.get("authority", "inferred_hint")},
                    confidence=confidence,
                    reversible=True,
                    source_refs=refs,
                    reason="semantic_locale_hint",
                ))
            if language_hint:
                authority = features.get("authority") or features.get("preference_authority") or "inferred_hint"
                action_type = "set_language_preference" if authority == "explicit_preference" else "set_language_hint"
                actions.append(InternalActionProposal(
                    action_type=action_type,
                    payload={"language": language_hint, "authority": authority},
                    confidence=confidence,
                    reversible=(action_type != "set_language_preference"),
                    source_refs=refs,
                    reason="semantic_language_hint",
                ))
        return actions

    def _semantic_carriers(self, situation: ResponseSituation) -> Iterable[Any]:
        graph = situation.uol_graph
        if graph is not None:
            for atom in getattr(graph, "atoms", {}).values():
                yield atom
        for frame in situation.relation_frames or []:
            yield frame
            yield getattr(frame, "subject", None)
            yield getattr(frame, "object", None)
        evidence = situation.evidence
        for fill in getattr(getattr(evidence, "answer_binding", None), "slot_fills", []) or []:
            yield fill


def _source_refs_from_plan(plan: ResponseCandidatePlan) -> list[str]:
    refs: list[str] = list(plan.evidence_refs or [])
    for move in plan.moves:
        refs.extend(move.evidence_refs)
        refs.extend(move.source_refs)
    return _dedupe(refs)


def _object_refs(obj: Any) -> list[str]:
    if obj is None:
        return []
    refs: list[str] = []
    for attr in ("id", "atom_id", "relation_id", "signal_id", "source_id"):
        value = getattr(obj, attr, "")
        if value:
            refs.append(str(value))
    for attr in ("source_refs", "evidence_refs", "source_frame_ids"):
        refs.extend(str(v) for v in (getattr(obj, attr, []) or []) if v)
    return _dedupe(refs)


def _dedupe(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out


def _dedupe_actions(actions: Iterable[InternalActionProposal]) -> list[InternalActionProposal]:
    out: list[InternalActionProposal] = []
    seen: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
    for action in actions:
        material = tuple(sorted((str(k), str(v)) for k, v in action.payload.items()))
        key = (action.action_type, material)
        if key not in seen:
            out.append(action)
            seen.add(key)
    return out
