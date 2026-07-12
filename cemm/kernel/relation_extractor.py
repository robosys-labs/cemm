"""Perception-layer relation candidate extraction.

The extractor emits candidates only. It preserves public surface evidence,
explicit proposition mode, open semantic roles, dimension, and cardinality. It
never creates graph edges, placeholders, patches, or durable mutations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ..types.meaning_percept import MeaningGroup, RelationAtom
from .proposition_semantics import ASSERTED, QUERIED
from .text_match import tokenize_surface
from .uol_metadata import (
    cue_set,
    frame_alias_set,
    contractions as _contractions_map,
    pronoun_to_entity as _pronoun_to_entity_map,
    possessive_to_entity as _possessive_to_entity_map,
    possessive_slot_to_predicate as _slot_to_predicate_map,
    remember_extra_verbs as _remember_extra_verbs_map,
)


@dataclass(frozen=True, slots=True)
class _PhraseMatch:
    start: int
    length: int
    phrase: str


class RelationExtractor:
    """Extract relation candidates without granting operational authority."""

    def __init__(
        self,
        schema_kernel: Any | None = None,
        *,
        language_code: str = "en",
    ) -> None:
        self._schema_kernel = schema_kernel
        self._language_code = language_code or "en"
        self._contractions = _contractions_map()
        self._pronoun_to_entity = _pronoun_to_entity_map()
        self._possessive_to_entity = _possessive_to_entity_map()
        self._slot_to_predicate = _slot_to_predicate_map()
        self._remember_verbs = _remember_extra_verbs_map()
        self._possessive_pronouns = cue_set("possessive_pronoun")
        self._stop_words = (
            cue_set("stopword")
            - self._possessive_pronouns
            - set(self._pronoun_to_entity.keys())
        )
        self._discourse_markers = frame_alias_set("discourse_marker")
        self._filler_words = cue_set("filler_word")
        self._definition_cues = cue_set("definition_cue")
        self._copula_cues = cue_set("identity_cue")
        remember_aliases = (
            frame_alias_set("command_remember")
            | frame_alias_set("teaching_remember")
        )
        self._remember_markers = frozenset(
            alias for alias in remember_aliases if alias and " " not in alias
        )

    def extract(self, groups: list[MeaningGroup]) -> list[RelationAtom]:
        results: list[RelationAtom] = []
        for group in groups:
            intent_keys = {intent.intent_key for intent in group.intents}
            is_teaching = group.group_type == "teaching" or "teaching" in intent_keys
            is_assertion = group.group_type in {"clause", "answer"} or "statement" in intent_keys
            is_command = group.group_type == "command" or "command" in intent_keys
            is_question = group.group_type == "question" or bool(
                intent_keys & {"question", "user_profile_query"}
            )

            if is_teaching or is_assertion:
                atom = self._from_teaching_or_assertion(group, is_teaching, is_assertion)
                if atom is not None:
                    results.append(atom)
            if is_command:
                atom = self._from_remember_command(group)
                if atom is not None:
                    results.append(atom)
            if is_question:
                atom = self._from_possessive_query(group)
                if atom is not None:
                    results.append(atom)
        return self._dedupe(results)

    def _from_teaching_or_assertion(
        self,
        group: MeaningGroup,
        is_teaching: bool,
        is_assertion: bool,
    ) -> RelationAtom | None:
        tokens = self._expand_contractions(group.tokens)
        if not tokens:
            return None
        atom = self._parse_possessive(tokens, group.surface, group, is_teaching or is_assertion)
        if atom is not None:
            return atom
        return self._parse_identity(tokens, group.surface, group, is_teaching, is_assertion)

    def _parse_possessive(
        self,
        tokens: list[str],
        cased_surface: str,
        group: MeaningGroup,
        is_teaching: bool,
    ) -> RelationAtom | None:
        cue = self._best_cue(tokens, self._definition_cues | self._copula_cues)
        if cue is None:
            return None
        left_tokens = tokens[:cue.start]
        right_tokens = tokens[cue.start + cue.length:]
        poss_index = self._first_index(left_tokens, self._possessive_pronouns)
        if poss_index < 0:
            return None

        slot_phrase, slot_entry = self._slot_after_possessive(left_tokens, poss_index)
        right = self._clean_side(right_tokens)
        if not slot_phrase or not right:
            return None

        poss_pronoun = left_tokens[poss_index]
        subject = self._possessive_to_entity.get(poss_pronoun, "user")
        right = self._preserve_case(right, cased_surface)
        edge_type = str(slot_entry.get("edge_type", "has_property") or "has_property")
        dimension = str(slot_entry.get("property_dimension", slot_phrase) or slot_phrase)
        cardinality = str(slot_entry.get("cardinality", "unknown") or "unknown")
        update_policy = str(slot_entry.get("update_policy", "append") or "append")

        return RelationAtom(
            relation_key=edge_type,
            source_role=subject,
            target_role="object",
            proposition_mode=ASSERTED,
            open_roles=[],
            surface=" ".join(tokens),
            source="relation_extractor",
            confidence=min(0.78, group.confidence + 0.12),
            group_id=group.id,
            features={
                "subject_surface": subject,
                "object_surface": right,
                "property_dimension": dimension,
                "dimension": dimension,
                "slot_surface": slot_phrase,
                "cardinality": cardinality,
                "update_policy": update_policy,
                "is_teaching": is_teaching,
                "proposition_mode": ASSERTED,
                "open_roles": [],
            },
        )

    def _parse_identity(
        self,
        tokens: list[str],
        cased_surface: str,
        group: MeaningGroup,
        is_teaching: bool,
        is_assertion: bool,
    ) -> RelationAtom | None:
        # Definition cues are semantically more specific than generic copulas.
        cue_groups = ((self._definition_cues, "same_as"), (self._copula_cues, "is_a"))
        for cues, relation_key in cue_groups:
            for match in self._ordered_matches(tokens, cues):
                left_tokens = tokens[:match.start]
                right_tokens = tokens[match.start + match.length:]
                left = self._resolve_subject(left_tokens)
                right = self._clean_side(right_tokens)
                if not left or not right:
                    continue
                if is_assertion and not is_teaching and not self._assertion_is_semantically_supported(
                    left, right, tokens
                ):
                    continue
                right = self._preserve_case(right, cased_surface)
                return RelationAtom(
                    relation_key=relation_key,
                    source_role=left if left in {"user", "self"} else "subject",
                    target_role="object",
                    proposition_mode=ASSERTED,
                    open_roles=[],
                    surface=" ".join(tokens),
                    source="relation_extractor",
                    confidence=min(0.78, group.confidence + 0.12),
                    group_id=group.id,
                    features={
                        "subject_surface": left,
                        "object_surface": right,
                        "cardinality": "set" if relation_key == "is_a" else "many",
                        "update_policy": "merge",
                        "is_teaching": is_teaching or is_assertion,
                        "proposition_mode": ASSERTED,
                        "open_roles": [],
                    },
                )
        return None

    def _from_remember_command(self, group: MeaningGroup) -> RelationAtom | None:
        tokens = self._expand_contractions(tokenize_surface(group.surface))
        marker_index = self._first_index(tokens, self._remember_markers)
        if marker_index < 0:
            return None
        after_marker = tokens[marker_index + 1:]

        relation_key = ""
        verb_index = -1
        for index, token in enumerate(after_marker):
            relation_key = self._lookup_relation_verb(token) or ""
            if relation_key:
                verb_index = index
                break
        if verb_index <= 0:
            return None

        subject_surface = self._pronoun_to_entity.get(
            after_marker[verb_index - 1].lower(), after_marker[verb_index - 1]
        )
        object_tokens = after_marker[verb_index + 1:]
        object_surface = self._clean_side(object_tokens)
        if not subject_surface or not object_surface:
            return None

        return RelationAtom(
            relation_key=relation_key,
            source_role=subject_surface if subject_surface in {"user", "self"} else "subject",
            target_role="object",
            proposition_mode=ASSERTED,
            open_roles=[],
            surface=group.surface,
            source="relation_extractor",
            confidence=max(0.45, min(0.76, group.confidence + 0.08)),
            group_id=group.id,
            features={
                "subject_surface": subject_surface,
                "object_surface": self._preserve_case(object_surface, group.surface),
                "is_remember_command": True,
                "relation_verb": after_marker[verb_index],
                "cardinality": "unknown",
                "update_policy": "append",
                "proposition_mode": ASSERTED,
                "open_roles": [],
            },
        )

    def _from_possessive_query(self, group: MeaningGroup) -> RelationAtom | None:
        tokens = self._expand_contractions(group.tokens)
        if not tokens:
            return None
        poss_index = self._first_index(tokens, self._possessive_pronouns)
        if poss_index < 0:
            return None

        slot_phrase, slot_entry = self._slot_after_possessive(tokens, poss_index)
        if not slot_phrase:
            return None
        subject = self._possessive_to_entity.get(tokens[poss_index], "user")
        edge_type = str(slot_entry.get("edge_type", "has_property") or "has_property")
        dimension = str(slot_entry.get("property_dimension", slot_phrase) or slot_phrase)
        cardinality = str(slot_entry.get("cardinality", "optional_one") or "optional_one")

        return RelationAtom(
            relation_key=edge_type,
            source_role=subject,
            target_role="",
            proposition_mode=QUERIED,
            open_roles=["object"],
            surface=" ".join(tokens),
            source="relation_extractor",
            confidence=min(0.74, group.confidence + 0.08),
            group_id=group.id,
            features={
                "subject_surface": subject,
                "object_surface": "",
                "property_dimension": dimension,
                "dimension": dimension,
                "slot_surface": slot_phrase,
                "cardinality": cardinality,
                "is_query": True,
                "proposition_mode": QUERIED,
                "open_roles": ["object"],
            },
        )

    def extract_possessive_query(self, group: MeaningGroup) -> RelationAtom | None:
        if group.group_type != "question" and not group.surface.rstrip().endswith("?"):
            return None
        return self._from_possessive_query(group)

    def _slot_after_possessive(
        self,
        tokens: list[str],
        possessive_index: int,
    ) -> tuple[str, dict[str, Any]]:
        region: list[str] = []
        for token in tokens[possessive_index + 1:]:
            if token in self._possessive_pronouns:
                break
            if token in self._definition_cues or token in self._copula_cues:
                break
            if token in self._stop_words or token in self._filler_words:
                continue
            region.append(token)
        if not region:
            return "", {}

        normalized_keys = sorted(
            self._slot_to_predicate,
            key=lambda key: (-len(key.split()), -len(key), key),
        )
        for key in normalized_keys:
            key_tokens = key.split()
            if region[:len(key_tokens)] == key_tokens:
                return key, dict(self._slot_to_predicate[key])

        # Unknown dimensions remain candidates. Do not destructively infer
        # cardinality or replacement semantics for them.
        return " ".join(region), {
            "edge_type": "has_property",
            "property_dimension": "_".join(region),
            "cardinality": "unknown",
            "update_policy": "append",
        }

    def _lookup_relation_verb(self, token: str) -> str | None:
        if self._schema_kernel is not None:
            action_key = self._schema_kernel.action_operators.lookup_alias(
                token, self._language_code
            )
            if action_key:
                deltas = self._schema_kernel.action_operators.relation_deltas_for(action_key)
                if deltas:
                    return str(deltas[0].get("relation_key", "") or "") or None
        return self._remember_verbs.get(token)

    def _resolve_subject(self, tokens: list[str]) -> str:
        for token in reversed(tokens):
            mapped = self._pronoun_to_entity.get(token.lower())
            if mapped:
                return mapped
        return self._clean_side(tokens)

    def _assertion_is_semantically_supported(
        self,
        left: str,
        right: str,
        tokens: list[str],
    ) -> bool:
        has_possessive = bool(set(tokens) & self._possessive_pronouns)
        has_definition = bool(self._best_cue(tokens, self._definition_cues))
        if has_possessive or has_definition:
            return True
        left_lower = left.lower().strip()
        right_lower = right.lower().strip()
        if any(left_lower == marker or left_lower.startswith(marker + " ") for marker in self._discourse_markers):
            return False
        return right_lower not in self._filler_words

    def _ordered_matches(self, tokens: list[str], phrases: Iterable[str]) -> list[_PhraseMatch]:
        matches: list[_PhraseMatch] = []
        for phrase in phrases:
            parts = phrase.split()
            if not parts:
                continue
            for start in range(0, len(tokens) - len(parts) + 1):
                if tokens[start:start + len(parts)] == parts:
                    matches.append(_PhraseMatch(start, len(parts), phrase))
        matches.sort(key=lambda item: (-item.length, item.start, item.phrase))
        return matches

    def _best_cue(self, tokens: list[str], phrases: Iterable[str]) -> _PhraseMatch | None:
        matches = self._ordered_matches(tokens, phrases)
        return matches[0] if matches else None

    @staticmethod
    def _first_index(tokens: list[str], choices: Iterable[str]) -> int:
        choice_set = set(choices)
        for index, token in enumerate(tokens):
            if token in choice_set:
                return index
        return -1

    def _expand_contractions(self, tokens: list[str]) -> list[str]:
        expanded: list[str] = []
        for token in tokens:
            replacement = self._contractions.get(token)
            expanded.extend(replacement.split() if replacement else [token])
        return expanded

    def _clean_side(self, tokens: list[str]) -> str:
        return " ".join(token for token in tokens if token not in self._stop_words).strip()

    @staticmethod
    def _preserve_case(text: str, cased_surface: str) -> str:
        if not text or not cased_surface:
            return text
        position = cased_surface.lower().find(text.lower())
        return cased_surface[position:position + len(text)] if position >= 0 else text

    @staticmethod
    def _dedupe(atoms: list[RelationAtom]) -> list[RelationAtom]:
        result: list[RelationAtom] = []
        seen: set[tuple[Any, ...]] = set()
        for atom in atoms:
            key = (
                atom.group_id,
                atom.relation_key,
                atom.proposition_mode,
                tuple(atom.open_roles),
                atom.features.get("subject_surface", ""),
                atom.features.get("object_surface", ""),
                atom.features.get("dimension", ""),
            )
            if key not in seen:
                seen.add(key)
                result.append(atom)
        return result
