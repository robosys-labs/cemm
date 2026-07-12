"""RelationExtractor — perception-layer relation atom candidate extractor.

Moved from MeaningGraphBuilder to comply with AGENTS.md §3.1 (surface evidence
is not authority) and §3.4 (one authority per decision).  Relation extraction
belongs in the perception/segmentation layer, not the graph builder.

This component produces *candidate* RelationAtom objects from MeaningGroup
tokens.  It does not create graph edges, structural observations, or durable
mutations.  The graph builder consumes the atoms and creates authoritative
graph structure.

All linguistic data (contractions, pronouns, stop words, discourse markers,
filler words, slot-to-predicate mappings, identity/definition cues) is loaded
from uol_semantics.json via uol_metadata.  No hardcoded English constants.
No regex is used.  Tokenisation is boundary-safe via text_match.
"""

from __future__ import annotations

from typing import Any

from ..types.meaning_percept import MeaningGroup, RelationAtom
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


class RelationExtractor:
    """Extract RelationAtom candidates from meaning groups.

    All linguistic data is data-driven from uol_semantics.json.
    Language-specific seed scaffolding per AGENTS.md §12.
    """

    def __init__(self, schema_kernel: Any | None = None) -> None:
        self._schema_kernel = schema_kernel
        self._contractions = _contractions_map()
        self._pronoun_to_entity = _pronoun_to_entity_map()
        self._possessive_to_entity = _possessive_to_entity_map()
        self._slot_to_predicate = _slot_to_predicate_map()
        self._remember_verbs = _remember_extra_verbs_map()
        self._possessive_pronouns = cue_set("possessive_pronoun")
        self._stop_words = cue_set("stopword") - self._possessive_pronouns - set(self._pronoun_to_entity.keys())
        self._discourse_markers = frame_alias_set("discourse_marker")
        self._filler_words = cue_set("filler_word")
        self._identity_cues = cue_set("definition_cue")
        self._copula_cues = cue_set("identity_cue")

    def extract(self, groups: list[MeaningGroup]) -> list[RelationAtom]:
        """Extract RelationAtom candidates from meaning groups."""
        results: list[RelationAtom] = []
        for group in groups:
            is_teaching = (
                group.group_type == "teaching"
                or any(intent.intent_key == "teaching" for intent in group.intents)
            )
            is_assertion = group.group_type in ("clause", "answer") or any(
                intent.intent_key == "statement" for intent in group.intents
            )
            is_command = group.group_type == "command" or any(
                intent.intent_key == "command" for intent in group.intents
            )
            if is_teaching or is_assertion:
                atom = self._from_teaching_or_assertion(group, is_teaching, is_assertion)
                if atom is not None:
                    results.append(atom)
            if is_command:
                atom = self._from_remember_command(group)
                if atom is not None:
                    results.append(atom)
            is_question = group.group_type == "question" or any(
                intent.intent_key in ("question", "user_profile_query")
                for intent in group.intents
            )
            if is_question:
                atom = self._from_possessive_query(group)
                if atom is not None:
                    results.append(atom)
        return results

    def _from_teaching_or_assertion(
        self, group: MeaningGroup, is_teaching: bool, is_assertion: bool,
    ) -> RelationAtom | None:
        tokens = group.tokens
        if not tokens:
            return None
        expanded = self._expand_contractions(tokens)
        cased_surface = group.surface

        store_as_teaching = is_teaching or is_assertion
        atom = self._parse_possessive(expanded, cased_surface, group, store_as_teaching)
        if atom is not None:
            return atom

        atom = self._parse_identity(expanded, cased_surface, group, is_teaching, is_assertion)
        if atom is not None:
            return atom
        return None

    def _parse_possessive(
        self, tokens: list[str], cased_surface: str, group: MeaningGroup, is_teaching: bool,
    ) -> RelationAtom | None:
        token_set = set(tokens)
        if not token_set & self._possessive_pronouns:
            return None

        all_cues = self._copula_cues | self._identity_cues
        cue = None
        for c in all_cues:
            if c in tokens:
                cue = c
                break
        if cue is None:
            return None
        index = tokens.index(cue)
        left = self._clean_side(tokens[:index])
        right = self._clean_side(tokens[index + 1:])
        if not left or not right:
            return None

        right = self._preserve_case(right, cased_surface)

        left_lower = left.lower().strip()
        left_words = left_lower.split()
        if not left_words:
            return None
        # Skip leading discourse markers to find the possessive pronoun
        start = 0
        while start < len(left_words) and left_words[start] in self._discourse_markers:
            start += 1
        if start >= len(left_words) or left_words[start] not in self._possessive_pronouns:
            return None
        poss_pronoun = left_words[start]
        slot_word = left_words[start + 1] if start + 1 < len(left_words) else ""

        subject = self._possessive_to_entity.get(poss_pronoun, "user")
        if poss_pronoun in ("mine", "yours", "his", "hers", "theirs", "ours"):
            edge_type, prop_dim = "has_property", ""
        else:
            slot_entry = self._slot_to_predicate.get(slot_word)
            if slot_entry:
                edge_type = slot_entry.get("edge_type", "has_property")
                prop_dim = slot_entry.get("property_dimension", "")
            else:
                edge_type, prop_dim = "has_property", slot_word

        object_head, domain_text = self._split_domain(right)
        features: dict[str, Any] = {
            "subject_surface": subject,
            "object_surface": object_head,
            "property_dimension": prop_dim,
            "is_teaching": is_teaching,
        }
        if domain_text:
            features["domain_surface"] = domain_text

        return RelationAtom(
            relation_key=edge_type,
            source_role=subject,
            target_role="topic",
            surface=" ".join(tokens),
            source="relation_extractor",
            confidence=min(0.74, group.confidence + 0.12),
            group_id=group.id,
            features=features,
        )

    def _parse_identity(
        self, tokens: list[str], cased_surface: str, group: MeaningGroup,
        is_teaching: bool, is_assertion: bool,
    ) -> RelationAtom | None:
        # Definition cues first (more specific), then copula cues
        ordered_cues = list(self._identity_cues) + list(self._copula_cues)
        for cue in ordered_cues:
            if cue not in tokens:
                continue
            index = tokens.index(cue)
            left_tokens = tokens[:index]
            entity_refs = [self._pronoun_to_entity.get(t.lower()) for t in left_tokens]
            entity_refs = [e for e in entity_refs if e is not None]
            if entity_refs:
                left = entity_refs[-1]
            else:
                left = self._clean_side(left_tokens)
            right = self._clean_side(tokens[index + 1:])
            if not left or not right:
                continue

            if is_assertion and not is_teaching:
                token_set = set(tokens)
                has_possessive = bool(token_set & self._possessive_pronouns)
                has_explicit_cue = bool(token_set & self._identity_cues)
                if not has_possessive and not has_explicit_cue:
                    subj_lower = left.lower().strip()
                    obj_lower = right.lower().strip()
                    if any(subj_lower == dm or subj_lower.startswith(dm + " ") for dm in self._discourse_markers):
                        continue
                    if obj_lower in self._filler_words:
                        continue

            right = self._preserve_case(right, cased_surface)
            relation_key = "same_as" if cue in self._identity_cues else "is_a"
            object_head, domain_text = self._split_domain(right)
            features: dict[str, Any] = {
                "subject_surface": left,
                "object_surface": object_head,
                "is_teaching": is_teaching or is_assertion,
            }
            if domain_text:
                features["domain_surface"] = domain_text

            return RelationAtom(
                relation_key=relation_key,
                source_role=left if left in ("user", "self") else "",
                target_role="topic",
                surface=" ".join(tokens),
                source="relation_extractor",
                confidence=min(0.74, group.confidence + 0.12),
                group_id=group.id,
                features=features,
            )
        return None

    def _from_remember_command(self, group: MeaningGroup) -> RelationAtom | None:
        tokens = tokenize_surface(group.surface)
        if "remember" not in tokens:
            return None
        rem_index = tokens.index("remember")
        after_rem = tokens[rem_index + 1:]

        relation_key = ""
        verb_index = -1
        for i, tok in enumerate(after_rem):
            rk = self._lookup_relation_verb(tok)
            if rk:
                relation_key = rk
                verb_index = i
                break
        if verb_index < 0 or not relation_key:
            return None

        subject_pronoun = after_rem[verb_index - 1] if verb_index > 0 else ""
        object_tokens = after_rem[verb_index + 1:]
        if not object_tokens or not subject_pronoun:
            return None

        subject = self._pronoun_to_entity.get(subject_pronoun.lower(), subject_pronoun)
        object_surface = " ".join(object_tokens)

        return RelationAtom(
            relation_key=relation_key,
            source_role=subject if subject in ("user", "self") else "",
            target_role="topic",
            surface=group.surface,
            source="relation_extractor",
            confidence=0.7,
            group_id=group.id,
            features={
                "subject_surface": subject,
                "object_surface": object_surface,
                "is_remember_command": True,
                "relation_verb": after_rem[verb_index],
            },
        )

    def _from_possessive_query(self, group: MeaningGroup) -> RelationAtom | None:
        """Extract a has_property relation candidate from a possessive query.

        Detects patterns like 'what is my email?' or 'do you know my name?'
        structurally — any possessive pronoun followed by a content word in a
        question context produces a has_property candidate with that word as
        property_dimension.  Works for known slot words (name, email, age) and
        unknown ones (learned via prior assertions).
        """
        tokens = group.tokens
        if not tokens:
            return None
        expanded = self._expand_contractions(tokens)

        poss_idx = -1
        for i, tok in enumerate(expanded):
            if tok in self._possessive_pronouns:
                poss_idx = i
                break
        if poss_idx < 0:
            return None

        slot_word = ""
        for tok in expanded[poss_idx + 1:]:
            if tok in self._stop_words or tok in self._filler_words:
                continue
            if tok in self._possessive_pronouns:
                break
            slot_word = tok
            break
        if not slot_word:
            return None

        slot_entry = self._slot_to_predicate.get(slot_word)
        if slot_entry:
            edge_type = slot_entry.get("edge_type", "has_property")
            prop_dim = slot_entry.get("property_dimension", slot_word)
        else:
            edge_type, prop_dim = "has_property", slot_word

        poss_pronoun = expanded[poss_idx]
        subject = self._possessive_to_entity.get(poss_pronoun, "user")

        return RelationAtom(
            relation_key=edge_type,
            source_role=subject,
            target_role="topic",
            surface=" ".join(tokens),
            source="relation_extractor",
            confidence=min(0.68, group.confidence + 0.08),
            group_id=group.id,
            features={
                "subject_surface": subject,
                "object_surface": "",
                "property_dimension": prop_dim,
                "is_query": True,
            },
        )

    def extract_possessive_query(self, group: MeaningGroup) -> RelationAtom | None:
        """Extract a has_property relation candidate from a possessive query.

        Public entry point for early possessive query detection (before intent
        atoms are created).  Does not depend on group.intents — only uses
        group.group_type and language-pack-driven token analysis.

        Returns a RelationAtom with property_dimension set to the slot word,
        or None if the group is not a possessive query.
        """
        if group.group_type != "question" and not group.surface.rstrip().endswith("?"):
            return None
        return self._from_possessive_query(group)

    def _lookup_relation_verb(self, token: str) -> str | None:
        if self._schema_kernel is not None:
            action_key = self._schema_kernel.action_operators.lookup_alias(token, "en")
            if action_key:
                deltas = self._schema_kernel.action_operators.relation_deltas_for(action_key)
                if deltas:
                    return deltas[0].get("relation_key")
        return self._remember_verbs.get(token)

    def _expand_contractions(self, tokens: list[str]) -> list[str]:
        expanded: list[str] = []
        for t in tokens:
            contracted = self._contractions.get(t)
            if contracted:
                expanded.extend(contracted.split())
            else:
                expanded.append(t)
        return expanded

    def _clean_side(self, tokens: list[str]) -> str:
        clean = [t for t in tokens if t not in self._stop_words]
        return " ".join(clean).strip()

    @staticmethod
    def _preserve_case(text: str, cased_surface: str) -> str:
        if not cased_surface:
            return text
        cased_lower = cased_surface.lower()
        text_lower = text.lower()
        pos = cased_lower.find(text_lower)
        if pos >= 0:
            return cased_surface[pos:pos + len(text)]
        return text

    @staticmethod
    def _split_domain(surface: str) -> tuple[str, str]:
        if " of " not in surface:
            return surface, ""
        head, domain = surface.split(" of ", 1)
        return head.strip() or surface, domain.strip()
