"""Language-neutral semantic response-candidate ranking."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class RankedResponseCandidate:
    intent: Any
    score: float
    score_breakdown: tuple[tuple[str, float], ...]
    candidate_kind: str = "semantic_intent"


class ResponseCandidateRanker:
    """Ranks semantic intents without inspecting words or rendering templates."""

    def rank(self, intents: Iterable[Any], cycle) -> tuple[RankedResponseCandidate, ...]:
        snapshot = getattr(cycle, "context_snapshot", None)
        selected = tuple(getattr(cycle, "selected_interpretations", ()) or ())
        selected_predicates = {
            str(getattr(item, "predicate_semantic_key", "")) for item in selected
        }
        has_answerable_query = any(
            getattr(item, "communicative_force", "") in {"ask", "query"}
            for item in selected
        )
        correction_present = any(
            relation.relation_kind == "correction"
            for graph in tuple(getattr(cycle, "meaning_candidates", ()) or ())
            for relation in tuple(getattr(graph, "discourse_relations", ()) or ())
        )
        ranked = []
        for intent in intents:
            breakdown = []
            provenance = tuple(getattr(intent, "provenance_refs", ()) or ())
            breakdown.append(("provenance", 0.20 if provenance else -0.50))
            predicate = str(getattr(intent, "predicate_key", ""))
            force = str(getattr(intent, "communicative_force", ""))

            if has_answerable_query and force == "assert":
                breakdown.append(("query_answer_fit", 0.35))
            if predicate in selected_predicates:
                breakdown.append(("predicate_continuity", 0.12))
            if correction_present and predicate in {"named", "acknowledges", "corrects"}:
                breakdown.append(("correction_fit", 0.25))
            if predicate == "requests" and selected:
                # Generic clarification must not outrank a grounded partial meaning.
                breakdown.append(("unnecessary_clarification", -0.70))
            if predicate == "requests" and not selected:
                breakdown.append(("necessary_clarification", 0.18))

            role_count = len(tuple(getattr(intent, "roles", ()) or ()))
            breakdown.append(("semantic_specificity", min(0.18, role_count * 0.04)))

            if snapshot is not None:
                repetition = self._repetition_penalty(intent, snapshot)
                if repetition:
                    breakdown.append(("repetition", repetition))
                activation = float(snapshot.predicate_weight(predicate))
                if activation:
                    breakdown.append(("topic_activation", min(0.12, activation * 0.12)))

            score = sum(value for _, value in breakdown)
            ranked.append(RankedResponseCandidate(
                intent=intent,
                score=score,
                score_breakdown=tuple(breakdown),
            ))
        return tuple(sorted(
            ranked,
            key=lambda item: (
                item.score,
                len(tuple(getattr(item.intent, "provenance_refs", ()) or ())),
                str(getattr(item.intent, "intent_id", "")),
            ),
            reverse=True,
        ))

    def select(self, ranked: tuple[RankedResponseCandidate, ...]) -> tuple[Any, ...]:
        if not ranked:
            return ()
        top = ranked[0]
        # Preserve multiple factual answers when they are semantically equivalent
        # and nearly tied; otherwise select one coherent response act.
        selected = [top.intent]
        top_predicate = str(getattr(top.intent, "predicate_key", ""))
        if top_predicate not in {"requests", "acknowledges", "corrects"}:
            for candidate in ranked[1:]:
                if top.score - candidate.score > 0.04:
                    break
                if str(getattr(candidate.intent, "predicate_key", "")) == top_predicate:
                    selected.append(candidate.intent)
        return tuple(selected)

    @staticmethod
    def _repetition_penalty(intent, snapshot) -> float:
        predicate = str(getattr(intent, "predicate_key", ""))
        recent = tuple(getattr(snapshot, "recent_clauses", ()) or ())[-4:]
        repeats = sum(
            1 for clause in recent
            if clause.speaker_ref == "self" and clause.predicate_key == predicate
        )
        return -min(0.36, repeats * 0.12)
