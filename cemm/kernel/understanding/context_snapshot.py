"""Bounded semantic dialogue context used before interpretation selection.

This is a non-truth projection over prior inbound/outbound semantic events.  It
never replaces semantic memory or CommonGroundManager.  Its sole purpose is to
supply recency, salience, topic, anaphora and repetition evidence to grounding,
interpretation ranking and response ranking.
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class SemanticClauseSummary:
    proposition_ref: str
    predication_ref: str = ""
    predicate_key: str = ""
    role_values: tuple[tuple[str, str], ...] = ()
    role_surfaces: tuple[tuple[str, str, str], ...] = ()
    communicative_force: str = ""
    polarity: str = "positive"
    context_ref: str = "actual"
    speaker_ref: str = ""
    addressee_ref: str = ""
    surface_text: str = ""
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def referent_refs(self) -> tuple[str, ...]:
        return tuple(
            value for _, value in self.role_values
            if value and not value.startswith(("value:", "opaque:"))
        )


@dataclass(frozen=True, slots=True)
class DialogueTurnRecord:
    event_ref: str
    context_id: str
    direction: str  # inbound | outbound
    speaker_ref: str
    addressee_ref: str
    clauses: tuple[SemanticClauseSummary, ...] = ()
    surface_text: str = ""
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass(frozen=True, slots=True)
class ContextSnapshot:
    context_id: str
    clock_observation: datetime
    recent_turns: tuple[DialogueTurnRecord, ...] = ()
    recent_clauses: tuple[SemanticClauseSummary, ...] = ()
    predicate_activation: tuple[tuple[str, float], ...] = ()
    referent_activation: tuple[tuple[str, float], ...] = ()
    surface_activation: tuple[tuple[str, float], ...] = ()
    semantic_activation: tuple[tuple[str, float], ...] = ()
    open_question_refs: tuple[str, ...] = ()

    def predicate_weight(self, key: str) -> float:
        return dict(self.predicate_activation).get(key, 0.0)

    def referent_weight(self, ref: str) -> float:
        return dict(self.referent_activation).get(ref, 0.0)

    def semantic_weight(self, key: str) -> float:
        return dict(self.semantic_activation).get(key, 0.0)

    @property
    def recent_system_clause(self) -> SemanticClauseSummary | None:
        return next(
            (
                clause for clause in reversed(self.recent_clauses)
                if clause.speaker_ref == "self"
            ),
            None,
        )

    @property
    def recent_user_clause(self) -> SemanticClauseSummary | None:
        return next(
            (
                clause for clause in reversed(self.recent_clauses)
                if clause.speaker_ref == "user"
            ),
            None,
        )

    @property
    def recent_system_proposition_ref(self) -> str:
        clause = self.recent_system_clause
        return clause.proposition_ref if clause else ""


class DialogueSemanticLedger:
    """Bounded semantic event ledger; not a truth or schema authority."""

    def __init__(self, *, max_turns_per_context: int = 64) -> None:
        self._max_turns = max(4, int(max_turns_per_context))
        self._by_context: dict[str, deque[DialogueTurnRecord]] = {}
        self._lock = RLock()
        self._revision = 0

    @property
    def revision(self) -> int:
        return self._revision

    def append(self, record: DialogueTurnRecord) -> None:
        with self._lock:
            turns = self._by_context.setdefault(
                record.context_id,
                deque(maxlen=self._max_turns),
            )
            if any(item.event_ref == record.event_ref for item in turns):
                return
            turns.append(record)
            self._revision += 1

    def snapshot(
        self,
        context_id: str,
        *,
        clock_observation: datetime | None = None,
        max_turns: int = 16,
    ) -> ContextSnapshot:
        with self._lock:
            turns = tuple(self._by_context.get(context_id, ()))
        turns = turns[-max(1, int(max_turns)):]
        clauses = tuple(clause for turn in turns for clause in turn.clauses)

        predicate_counts: Counter[str] = Counter()
        referent_counts: Counter[str] = Counter()
        surface_counts: Counter[str] = Counter()
        semantic_counts: Counter[str] = Counter()
        open_questions: list[str] = []
        total = max(1, len(clauses))
        for index, clause in enumerate(clauses):
            # Exponential-ish recency without importing numerical packages.
            recency = 1.0 / (1.0 + (len(clauses) - index - 1) * 0.35)
            if clause.predicate_key:
                predicate_counts[clause.predicate_key] += recency
                semantic_counts[clause.predicate_key] += recency
            for ref in clause.referent_refs:
                referent_counts[ref] += recency
            for _, _, semantic_key in clause.role_surfaces:
                if semantic_key:
                    semantic_counts[semantic_key] += recency
            normalized = " ".join(clause.surface_text.casefold().split())
            if normalized:
                surface_counts[normalized] += recency
            if clause.communicative_force in {"ask", "query", "request"}:
                open_questions.append(clause.proposition_ref)

        def normalized(counter: Counter[str]) -> tuple[tuple[str, float], ...]:
            if not counter:
                return ()
            maximum = max(counter.values()) or 1.0
            return tuple(
                sorted(
                    ((key, min(1.0, value / maximum)) for key, value in counter.items()),
                    key=lambda item: (-item[1], item[0]),
                )
            )

        return ContextSnapshot(
            context_id=context_id,
            clock_observation=clock_observation or datetime.now(timezone.utc),
            recent_turns=turns,
            recent_clauses=clauses,
            predicate_activation=normalized(predicate_counts),
            referent_activation=normalized(referent_counts),
            surface_activation=normalized(surface_counts),
            semantic_activation=normalized(semantic_counts),
            open_question_refs=tuple(dict.fromkeys(open_questions)),
        )

    @staticmethod
    def clauses_from_interpretations(
        interpretations: Iterable[Any],
        *,
        speaker_ref: str,
        addressee_ref: str,
        surface_text: str,
    ) -> tuple[SemanticClauseSummary, ...]:
        result = []
        for item in interpretations:
            roles = tuple(
                sorted(
                    (
                        binding.role_schema_ref.removeprefix("role:"),
                        binding.filler_ref,
                    )
                    for binding in tuple(getattr(item, "role_bindings", ()) or ())
                )
            )
            grounding_by_role = {
                grounding.role_schema_ref.removeprefix("role:"): (
                    grounding.surface,
                    grounding.semantic_keys[0] if grounding.semantic_keys else "",
                )
                for grounding in tuple(getattr(item, "role_groundings", ()) or ())
            }
            role_surfaces = tuple(sorted(
                (role, *grounding_by_role.get(role, ("", "")))
                for role, _ in roles
            ))
            result.append(SemanticClauseSummary(
                proposition_ref=str(getattr(item, "proposition_ref", "")),
                predication_ref=str(getattr(item, "predication_ref", "")),
                predicate_key=str(getattr(item, "predicate_semantic_key", "")),
                role_values=roles,
                role_surfaces=role_surfaces,
                communicative_force=str(getattr(item, "communicative_force", "")),
                context_ref=str(getattr(item, "context_ref", "actual")),
                speaker_ref=speaker_ref,
                addressee_ref=addressee_ref,
                surface_text=surface_text,
            ))
        return tuple(result)

    @staticmethod
    def clauses_from_message_plan(
        plan: Any,
        *,
        realized_clause_refs: Iterable[str],
        surface_text: str,
    ) -> tuple[SemanticClauseSummary, ...]:
        realized = set(realized_clause_refs)
        result = []
        for clause in tuple(getattr(plan, "clauses", ()) or ()):
            if clause.clause_id not in realized:
                continue
            roles = tuple(
                sorted(
                    (role.role_key, role.value_ref)
                    for role in tuple(getattr(clause, "roles", ()) or ())
                )
            )
            result.append(SemanticClauseSummary(
                proposition_ref=clause.clause_id,
                predication_ref=clause.clause_id,
                predicate_key=clause.predicate_key,
                role_values=roles,
                communicative_force=clause.communicative_force,
                polarity=clause.polarity,
                context_ref=clause.context_ref,
                speaker_ref="self",
                addressee_ref="user",
                surface_text=surface_text,
            ))
        return tuple(result)
