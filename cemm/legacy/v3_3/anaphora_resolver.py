"""AnaphoraResolver - resolve pronouns, reflexives, and deictic references.

Language-agnostic: resolves via entity_type compatibility and salience,
not English pronoun lists. Works with the entity_type and role fields
already set by the language adapter's map_pronouns/map_deictics.
"""

from __future__ import annotations

from typing import Any

from ...types.meaning_percept import AtomEvidence, MeaningGroup, ReferentAtom

_ENTITY_TYPE_MAP: dict[str, str] = {
    "user": "user",
    "self": "self",
    "person": "person",
    "object": "object",
    "place": "place",
}


class AnaphoraResolver:
    """Resolve pronouns, reflexives, and other anaphoric references.

    For referents with source='pronoun' or source='deixis', resolves
    entity_id by matching entity_type against salient entities across groups.
    """

    # Entity types that can be resolved to inherent identities.
    _INHERENT_IDS: dict[str, str] = {
        "user": "user",
        "self": "self",
    }

    def resolve(
        self,
        referents: list[ReferentAtom],
        groups: list[MeaningGroup],
        entities: list[dict[str, Any]] | None = None,
        language: Any = None,
        prior_salience: dict[str, float] | None = None,
    ) -> list[ReferentAtom]:
        """Resolve anaphoric references in referent atoms.

        Resolves inherent identity pronouns (user, self) by setting
        entity_id. Third-person pronouns (person, object, place) are
        resolved against known entities and prior-turn salience when
        available, setting entity_id for cross-turn coreference.

        Returns the same mutated referent list for chaining.

        Args:
            referents: Flat list of all referent atoms.
            groups: Meaning groups with group.referents populated.
            entities: Optional list of known entity dicts with 'text', 'role',
                      'entity_type' keys.
            language: Optional language adapter for surface normalization.
            prior_salience: Salience map from previous turn(s), enabling
                            cross-turn pronoun resolution.
        """
        known_entities: list[dict[str, Any]] = []
        for ref in referents:
            if ref.source in ("pronoun", "deixis"):
                continue
            if ref.entity_id or ref.source == "ner" or ref.source == "capitalization":
                known_entities.append({
                    "text": ref.surface,
                    "entity_id": ref.entity_id or ref.surface.lower(),
                    "entity_type": ref.entity_type,
                    "role": ref.role,
                    "confidence": ref.confidence,
                })

        for group in groups:
            for ref in group.referents:
                if ref.source in ("pronoun", "deixis"):
                    continue
                internal_id = ref.entity_id or ref.surface.lower()
                entry = {
                    "text": ref.surface,
                    "entity_id": internal_id,
                    "entity_type": ref.entity_type,
                    "role": ref.role,
                    "confidence": ref.confidence,
                }
                if entry not in known_entities:
                    known_entities.append(entry)

        if entities:
            for ent in entities:
                internal_id = str(ent.get("text", "")).lower()
                entry = {
                    "text": str(ent.get("text", "")),
                    "entity_id": str(ent.get("entity_id", internal_id)),
                    "entity_type": str(ent.get("entity_type", ent.get("role", "unknown"))),
                    "role": str(ent.get("role", "topic")),
                    "confidence": float(ent.get("confidence", 0.5)),
                }
                if entry not in known_entities:
                    known_entities.append(entry)

        for ref in referents:
            if ref.source not in ("pronoun", "deixis") or ref.entity_id:
                continue

            if ref.entity_type in self._INHERENT_IDS:
                ref.entity_id = self._INHERENT_IDS[ref.entity_type]
                continue

            # Third-person pronouns: resolve against known entities.
            # When prior_salience is available, boost confidence for
            # entities that were salient in previous turns.
            target_type = self._match_type(ref.entity_type)
            if target_type is None:
                continue

            match = self._find_best_match(
                ref.surface, target_type, known_entities,
            )
            if match is not None:
                entity_id = match["entity_id"]
                confidence = match.get("confidence", 0.5) * 0.85
                if prior_salience and entity_id in prior_salience:
                    confidence = min(1.0, confidence + prior_salience[entity_id] * 0.3)
                    ref.entity_id = entity_id
                elif len(known_entities) == 1 and target_type == "person":
                    ref.entity_id = entity_id
                ref.evidence.append(AtomEvidence(
                    source="anaphora_candidate",
                    surface=ref.surface,
                    confidence=confidence,
                    rationale=f"candidate_entity={entity_id}",
                ))

        return referents

    @staticmethod
    def _match_type(entity_type: str) -> str | None:
        """Map referent entity_type to a known entity type for matching."""
        return _ENTITY_TYPE_MAP.get(entity_type)

    @staticmethod
    def _find_best_match(
        surface: str,
        target_type: str,
        known_entities: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Find the best matching entity for a given target type."""
        candidates = [
            e
            for e in known_entities
            if e.get("entity_type", "") == target_type
        ]
        if not candidates:
            candidates = [
                e
                for e in known_entities
                if e.get("entity_type", "") in (target_type, "unknown")
            ]
        if not candidates:
            return None
        return max(candidates, key=lambda e: e.get("confidence", 0.5))
