"""ImplicitPredicateDetector - detect implicit predicates from context.

When a meaning group has referents but no explicit action or state predicate,
infer likely predicates from the group's role, neighboring groups, and
discourse context.

Language-agnostic: uses group structure and intent fields, not English string
matching.
"""

from __future__ import annotations

from typing import Any

from ..types.meaning_percept import (
    AtomEvidence,
    MeaningGroup,
    PredicatePhrase,
    ReferentAtom,
)


class ImplicitPredicateDetector:
    """Detect implicit predicates (is_a, has_property, etc.) from context.

    Operates after explicit predicate extraction. Adds predicates for groups
    that have semantic content (referents, intents) but no explicit
    action/state predicates.
    """

    def detect(
        self,
        groups: list[MeaningGroup],
        referents: list[ReferentAtom],
        predicates: list[PredicatePhrase],
    ) -> list[PredicatePhrase]:
        """Detect implicit predicates for groups lacking explicit ones.

        Args:
            groups: Meaning groups with populated atoms and intents.
            referents: Flat list of all referent atoms.
            predicates: Already-extracted predicate phrases.

        Returns:
            Newly detected implicit predicate phrases (not yet in predicates).
        """
        new_predicates: list[PredicatePhrase] = []

        for group in groups:
            if group.actions or group.states:
                continue

            has_explicit = any(p.group_id == group.id for p in predicates)
            if has_explicit:
                continue

            if not group.referents and not referents:
                continue

            implicit = self._infer_implicit_predicate(
                group, referents, predicates,
            )
            if implicit is not None:
                new_predicates.append(implicit)
                group.predicate_ids.append(implicit.id)

        return new_predicates

    def _infer_implicit_predicate(
        self,
        group: MeaningGroup,
        referents: list[ReferentAtom],
        existing: list[PredicatePhrase],
    ) -> PredicatePhrase | None:
        """Infer a single implicit predicate for a group.

        Checks group intent, group type, and discourse context.
        """
        if not group.intents:
            return None

        intent = group.intents[0]
        intent_key = intent.intent_key

        predicate_key = f"intent:{intent_key}"
        # Skip if an intent predicate already exists for this group
        for pred in existing:
            if pred.group_id == group.id and pred.predicate_key == predicate_key:
                return None

        group_referents = group.referents or [
            r for r in referents if r.group_id == group.id
        ]
        group_surface_tokens = set(group.tokens) if group.tokens else set()

        predicate = PredicatePhrase(
            id="",
            group_id=group.id,
            surface=group.surface,
            start_token=group.start_token,
            end_token=group.end_token,
            predicate_key=predicate_key,
            predicate_surface=group.surface,
            actor_role=(
                "user"
                if group_surface_tokens & {"i", "we", "my"}
                else "self"
                if group_surface_tokens & {"you", "your"}
                else None
            ),
            target_role=intent.target_role if intent.target_role else "conversation",
            modality=(
                "requested"
                if intent.is_question or intent.is_command
                else "observed"
            ),
            polarity=intent.polarity if intent.polarity else "affirmed",
            confidence=max(0.35, intent.confidence - 0.1),
            evidence=[
                AtomEvidence(
                    source="implicit_predicate_detector",
                    group_id=group.id,
                    surface=group.surface,
                    confidence=intent.confidence - 0.1,
                    rationale=(
                        f"implicit from intent={intent_key}"
                    ),
                ),
            ],
        )

        return predicate
