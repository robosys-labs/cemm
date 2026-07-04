"""PredicatePhraseExtractor - extract predicate phrases from meaning groups.

Language-agnostic: uses group structure and atom fields, not English string
matching. Heuristic logic extracted from MeaningPerceptor._build_predicate_phrases
and related methods.
"""

from __future__ import annotations

from typing import Any

from ..types.meaning_percept import (
    AtomEvidence,
    MeaningAtomOutcome,
    MeaningGroup,
    PredicatePhrase,
)


class PredicatePhraseExtractor:
    """Extract predicate phrases from meaning groups and tokens.

    A predicate phrase is a (subject, predicate, object) triple derived
    from the group's action, state, or intent atoms.
    """

    def extract(
        self,
        groups: list[MeaningGroup],
        language: Any = None,
    ) -> list[PredicatePhrase]:
        """Extract predicate phrases from meaning groups.

        Builds predicates from:
        1. Action atoms in each group
        2. State atoms in each group
        3. Group intent (when no action/state predicate exists)
        """
        predicates: list[PredicatePhrase] = []

        for group in groups:
            for action in group.actions:
                start_token, end_token = self._predicate_span(
                    group, action.surface, language,
                )
                predicate = PredicatePhrase(
                    id=f"pred_{len(predicates)}",
                    group_id=group.id,
                    surface=group.surface,
                    start_token=start_token,
                    end_token=end_token,
                    predicate_key=action.action_key or action.surface,
                    predicate_surface=action.surface,
                    actor_role=action.actor_role,
                    object_role=action.object_role,
                    target_role=action.target_role,
                    place_role=action.place_role,
                    modality=action.modality,
                    polarity=action.polarity,
                    confidence=action.confidence,
                    evidence=list(action.evidence),
                )
                predicates.append(predicate)
                group.predicate_ids.append(predicate.id)

            for state in group.states:
                start_token, end_token = self._predicate_span(
                    group, state.surface, language,
                )
                predicate = PredicatePhrase(
                    id=f"pred_{len(predicates)}",
                    group_id=group.id,
                    surface=group.surface,
                    start_token=start_token,
                    end_token=end_token,
                    predicate_key=f"state:{state.state_key}",
                    predicate_surface=state.surface,
                    actor_role=state.holder_role,
                    modality="observed",
                    polarity=state.polarity,
                    confidence=state.confidence,
                    evidence=list(state.evidence),
                )
                predicates.append(predicate)
                group.predicate_ids.append(predicate.id)

            if group.intents and self._should_emit_intent_predicate(group):
                intent = group.intents[0]
                predicate = PredicatePhrase(
                    id=f"pred_{len(predicates)}",
                    group_id=group.id,
                    surface=group.surface,
                    start_token=group.start_token,
                    end_token=group.end_token,
                    predicate_key=f"intent:{intent.intent_key}",
                    predicate_surface=group.surface,
                    actor_role="user",
                    target_role=intent.target_role,
                    modality=(
                        "requested"
                        if intent.is_question or intent.is_command
                        else "observed"
                    ),
                    polarity=intent.polarity,
                    confidence=intent.confidence,
                    evidence=list(intent.evidence),
                )
                predicates.append(predicate)
                group.predicate_ids.append(predicate.id)

        return predicates

    def build_outcomes(
        self,
        predicates: list[PredicatePhrase],
        groups: list[MeaningGroup],
    ) -> list[MeaningAtomOutcome]:
        """Build MeaningAtomOutcomes from predicate phrases."""
        outcomes: list[MeaningAtomOutcome] = []

        for predicate in predicates:
            atom_kind, atom_key, affected_role, expected_change, valence = (
                self._outcome_for_predicate(predicate)
            )
            outcome = MeaningAtomOutcome(
                id=f"outcome_{len(outcomes)}",
                group_id=predicate.group_id,
                predicate_id=predicate.id,
                atom_kind=atom_kind,
                atom_key=atom_key,
                affected_role=affected_role,
                expected_change=expected_change,
                valence=valence,
                confidence=max(0.35, min(0.9, predicate.confidence)),
                evidence=list(predicate.evidence),
            )
            outcomes.append(outcome)
            group = self._group_by_id(groups, predicate.group_id)
            if group is not None:
                group.outcome_ids.append(outcome.id)

        return outcomes

    @staticmethod
    def _predicate_span(
        group: MeaningGroup,
        surface: str,
        language: Any = None,
    ) -> tuple[int, int]:
        """Calculate token span for a predicate surface within a group."""
        tokenize = (
            getattr(language, "tokenize", None)
            if language is not None
            else None
        )
        if tokenize is not None:
            surface_tokens = tokenize(surface)
        else:
            surface_tokens = surface.lower().split() if surface else []

        if not surface_tokens:
            return group.start_token, group.end_token

        for offset in range(
            0, max(1, len(group.tokens) - len(surface_tokens) + 1),
        ):
            if group.tokens[offset:offset + len(surface_tokens)] == surface_tokens:
                start = group.start_token + offset
                return start, start + len(surface_tokens)

        return group.start_token, group.end_token

    @staticmethod
    def _should_emit_intent_predicate(group: MeaningGroup) -> bool:
        """Determine if an intent-only group should emit a predicate phrase."""
        if not group.intents:
            return False
        intent_key = group.intents[0].intent_key
        if not group.predicate_ids:
            return True
        return intent_key in {
            "fresh_world_query",
            "repair",
            "teaching",
            "session_exit",
            "capability_query",
            "command",
        }

    @staticmethod
    def _outcome_for_predicate(
        predicate: PredicatePhrase,
    ) -> tuple[str, str, str, str, str]:
        """Map a predicate key to an atom outcome tuple."""
        key = predicate.predicate_key
        if key == "physically_harm_target":
            return (
                "safety", key, predicate.target_role or "target",
                "harm_or_health_decrease", "negative",
            )
        if key == "improve_state":
            return (
                "state", key, predicate.target_role or "target",
                "state_improvement", "positive",
            )
        if key in {"memory_write", "intent:teaching"}:
            return (
                "memory", key, "memory",
                "candidate_memory_update", "neutral",
            )
        if key in {"increase_capability", "transfer_knowledge"}:
            return (
                "learning", key, predicate.actor_role or "learner",
                "knowledge_increase", "positive",
            )
        if key == "intent:fresh_world_query":
            return (
                "answer", key, "world",
                "fresh_evidence_required", "neutral",
            )
        if key == "intent:repair":
            return (
                "repair", key, "conversation",
                "clarity_required", "neutral",
            )
        if key.startswith("state:"):
            return (
                "state", key, predicate.actor_role or "holder",
                key.replace("state:", "state_observed:"), "unknown",
            )
        if key.startswith("intent:"):
            return (
                "intent", key, predicate.target_role or "conversation",
                "reply_obligation", "neutral",
            )
        return (
            "action", key, predicate.target_role or predicate.object_role or "event",
            "event_candidate", "unknown",
        )

    @staticmethod
    def _group_by_id(
        groups: list[MeaningGroup],
        group_id: str,
    ) -> MeaningGroup | None:
        for group in groups:
            if group.id == group_id:
                return group
        return None
