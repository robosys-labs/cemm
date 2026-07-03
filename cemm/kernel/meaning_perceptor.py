"""MeaningPerceptor - assemble foundational meaning atoms from a Signal.

The perceptor is the first semantic boundary after normalization. It should
not classify the final conversation act, route the response, or mutate memory.
Its job is narrower and more important:

* preserve normalized surface evidence,
* bind named entities, pronouns, deixis, learned lexemes, and surface tags,
* emit shared CEMM atoms that are language-neutral,
* keep uncertainty explicit for later frame binding and learning.

Language-specific cue tables live behind LanguageAdapter implementations. The
default English adapter preserves the current deterministic seed behavior, but
the perceptor itself is prepared for multilingual adapters and learned surface
models.
"""

from __future__ import annotations

from typing import Any, Iterable
import uuid

from ..learning.lexeme_memory import LexemeMemory, LexemeRole
from ..learning.ner_tagger import NERTagger
from ..learning.surface_tagger import SurfaceTagger
from ..types.context_kernel import ContextKernel
from ..types.meaning_percept import (
    ActionAtom,
    MeaningPerceptPacket,
    NeedAtom,
    ReferentAtom,
    RelationAtom,
    StateAtom,
)
from ..types.signal import Signal
from .language_adapter import EnglishLanguageAdapter, LanguageAdapter


_ENTITY_ROLES = {"person", "place", "organization", "entity", "object", "time"}
_SURFACE_ACTION_ROLES = {"process", "command_alias"}


class MeaningPerceptor:
    """Build MeaningPerceptPacket from normalized signal and semantic hints."""

    def __init__(
        self,
        ner_tagger: NERTagger | None = None,
        surface_tagger: SurfaceTagger | None = None,
        lexeme_memory: LexemeMemory | None = None,
        language_adapter: LanguageAdapter | None = None,
    ) -> None:
        self._ner_tagger = ner_tagger
        self._surface_tagger = surface_tagger
        self._lexeme_memory = lexeme_memory
        self._language = language_adapter or EnglishLanguageAdapter()

    def perceive(
        self,
        signal: Signal,
        kernel: ContextKernel,
    ) -> MeaningPerceptPacket:
        """Build a MeaningPerceptPacket without side effects."""
        raw_text = signal.content or ""
        tokens = self._language.tokenize(raw_text)
        normalized_tokens, repaired_tokens, normalized_forms, unknown_tokens = self._normalization(signal, tokens)
        semantic_tokens = repaired_tokens or normalized_tokens or tokens

        packet = MeaningPerceptPacket(
            id=uuid.uuid4().hex[:16],
            signal_id=signal.id,
            context_id=signal.context_id,
            raw_text=raw_text,
            tokens=tokens,
            normalized_tokens=normalized_tokens,
            repaired_tokens=repaired_tokens,
            normalized_forms=normalized_forms,
            punctuation_features=self._language.punctuation_features(raw_text),
            speaker_entity_id="user",
            listener_entity_id="self",
        )

        known_words = self._known_words()
        ner_entities = self._extract_ner(semantic_tokens)
        semantic_spans = self._extract_surface_spans(semantic_tokens, unknown_tokens)

        self._add_ner_referents(packet, ner_entities)
        self._extend_referents(packet, self._language.map_pronouns(semantic_tokens))
        self._extend_referents(packet, self._language.map_deictics(semantic_tokens))
        self._add_capitalized_referents(packet, raw_text, known_words)

        self._apply_surface_spans(packet, semantic_spans)
        self._apply_lexeme_memory(packet, semantic_tokens)

        self._extend_actions(packet, self._language.map_actions(semantic_tokens))
        self._extend_states(packet, self._language.map_states(semantic_tokens))
        self._extend_needs(packet, self._language.map_needs(semantic_tokens))

        self._add_unknown_lexemes(packet, unknown_tokens, semantic_tokens, known_words, semantic_spans)
        self._add_idiom_candidates(packet, semantic_tokens, unknown_tokens)
        packet.affect_markers = self._dedupe_dicts(
            [*packet.affect_markers, *self._language.detect_affect(raw_text, semantic_tokens)],
            key_fields=("type", "surface"),
        )

        packet.attention_target = self._attention_target(packet, kernel)
        packet.confidence = self._confidence(packet)
        return packet

    def _normalization(
        self,
        signal: Signal,
        fallback_tokens: list[str],
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        normalized = getattr(signal, "normalized", None)
        if normalized is None:
            return fallback_tokens, fallback_tokens, [], []

        canonical = getattr(normalized, "canonical_form", "") or ""
        normalized_tokens = self._language.tokenize(canonical) if canonical else fallback_tokens
        surface_features = getattr(normalized, "surface_features", {}) or {}
        unknown_tokens = [str(t) for t in surface_features.get("unknown_tokens", []) if str(t).strip()]
        normalized_forms = [str(f) for f in getattr(normalized, "normalized_forms", [])]
        return normalized_tokens, normalized_tokens, normalized_forms, unknown_tokens

    def _extract_ner(self, tokens: list[str]) -> list[dict[str, Any]]:
        if self._ner_tagger is None or not tokens:
            return []
        return self._ner_tagger.extract_entities(tokens)

    def _extract_surface_spans(
        self,
        tokens: list[str],
        unknown_tokens: list[str],
    ) -> list[dict[str, Any]]:
        if self._surface_tagger is None or not tokens:
            return []
        return self._surface_tagger.extract_all(tokens, unknown_tokens=unknown_tokens)

    def _known_words(self) -> set[str]:
        if self._surface_tagger is None:
            return set()
        return set(getattr(self._surface_tagger, "_known_words", set()))

    def _add_ner_referents(
        self,
        packet: MeaningPerceptPacket,
        entities: Iterable[dict[str, Any]],
    ) -> None:
        for entity in entities:
            role = str(entity.get("role", "entity") or "entity").lower()
            if role not in _ENTITY_ROLES:
                continue
            entity_type = {
                "time": "abstract",
                "entity": "unknown",
            }.get(role, role)
            self._extend_referents(packet, [ReferentAtom(
                surface=str(entity.get("text", "")),
                entity_type=entity_type,
                role="topic",
                known=float(entity.get("confidence", 0.0) or 0.0) > 0.5,
                source="ner",
                confidence=float(entity.get("confidence", 0.5) or 0.5),
            )])

    def _add_capitalized_referents(
        self,
        packet: MeaningPerceptPacket,
        raw_text: str,
        known_words: set[str],
    ) -> None:
        existing = {r.surface.lower() for r in packet.referents if r.surface}
        for index, surface in enumerate(self._language.surface_tokens(raw_text)):
            clean = surface.strip(".,!?;:\"'()[]{}")
            if not clean or not clean[0].isupper():
                continue
            lower = self._language.normalize_surface(clean)
            if lower in existing:
                continue
            if self._language.is_entity_surface_excluded(clean, known_words):
                continue
            if self._active_lexeme(lower) is not None:
                continue
            existing.add(lower)
            self._extend_referents(packet, [ReferentAtom(
                surface=clean,
                entity_type="person",
                role="topic",
                known=False,
                source="capitalization",
                confidence=self._language.capitalization_confidence(clean, index),
            )])

    def _apply_surface_spans(
        self,
        packet: MeaningPerceptPacket,
        spans: Iterable[dict[str, Any]],
    ) -> None:
        for span in spans:
            surface = str(span.get("text", "") or "").strip()
            role = str(span.get("role", "") or "").lower()
            confidence = float(span.get("confidence", 0.6) or 0.6)
            if not surface:
                continue
            if role in _SURFACE_ACTION_ROLES:
                self._extend_actions(packet, [ActionAtom(
                    surface=surface,
                    action_key=self._canonical_key(surface),
                    confidence=confidence,
                )])
            elif role == "state":
                self._extend_states(packet, [StateAtom(
                    surface=surface,
                    state_key=self._canonical_key(surface),
                    holder_role="user",
                    confidence=confidence,
                )])
            elif role == "relation":
                self._extend_relations(packet, [RelationAtom(
                    relation_key=self._canonical_key(surface),
                    confidence=confidence,
                )])

    def _apply_lexeme_memory(
        self,
        packet: MeaningPerceptPacket,
        tokens: list[str],
    ) -> None:
        if self._lexeme_memory is None or not tokens:
            return

        covered: set[tuple[int, int]] = set()
        for surface, start, end in self._language.ngrams(tokens, max_size=4):
            if any(start < covered_end and end > covered_start for covered_start, covered_end in covered):
                continue
            lexeme = self._active_lexeme(surface)
            if lexeme is None:
                continue

            role = self._lexeme_role(lexeme)
            mapped = lexeme.maps_to or lexeme.canonical or surface
            confidence = max(0.45, min(0.95, float(lexeme.confidence or 0.5)))
            if role == LexemeRole.ENTITY.value:
                self._extend_referents(packet, [ReferentAtom(
                    surface=surface,
                    entity_id=mapped if mapped else None,
                    entity_type="unknown",
                    role="topic",
                    known=True,
                    source="lexeme_memory",
                    confidence=confidence,
                )])
            elif role in {LexemeRole.PROCESS.value, LexemeRole.COMMAND_ALIAS.value}:
                self._extend_actions(packet, [ActionAtom(
                    surface=surface,
                    action_key=mapped,
                    confidence=confidence,
                )])
            elif role == LexemeRole.STATE.value:
                self._extend_states(packet, [StateAtom(
                    surface=surface,
                    state_key=mapped,
                    holder_role="user",
                    confidence=confidence,
                )])
            elif role == LexemeRole.RELATION.value:
                self._extend_relations(packet, [RelationAtom(
                    relation_key=mapped,
                    confidence=confidence,
                )])
            covered.add((start, end))

    def _add_unknown_lexemes(
        self,
        packet: MeaningPerceptPacket,
        unknown_tokens: list[str],
        tokens: list[str],
        known_words: set[str],
        semantic_spans: Iterable[dict[str, Any]],
    ) -> None:
        candidates = [str(t) for t in unknown_tokens]
        candidates.extend(
            str(span.get("text", ""))
            for span in semantic_spans
            if str(span.get("role", "")).lower() == "unknown_lexeme"
        )
        unknowns: list[dict[str, Any]] = []
        for surface in candidates:
            normalized = self._language.normalize_surface(surface)
            if not normalized or normalized in known_words:
                continue
            if self._active_lexeme(normalized) is not None:
                continue
            position = tokens.index(normalized) if normalized in tokens else -1
            unknowns.append({
                "surface": surface,
                "role": self._unknown_role(surface, normalized, tokens, position),
                "position": position,
                "confidence": 0.5,
            })
        packet.unknown_lexemes = self._dedupe_dicts(
            [*packet.unknown_lexemes, *unknowns],
            key_fields=("surface", "position"),
        )

    def _add_idiom_candidates(
        self,
        packet: MeaningPerceptPacket,
        tokens: list[str],
        unknown_tokens: list[str],
    ) -> None:
        unknown_set = {self._language.normalize_surface(t) for t in unknown_tokens}
        candidates: list[dict[str, Any]] = []
        if len(tokens) >= 3 and unknown_set:
            for start in range(0, len(tokens) - 2):
                phrase_tokens = tokens[start:start + 3]
                unknown_count = sum(1 for token in phrase_tokens if token in unknown_set)
                if unknown_count >= 2:
                    candidates.append({
                        "surface": " ".join(phrase_tokens),
                        "start": start,
                        "end": start + 3,
                        "confidence": 0.4,
                        "source": "unknown_sequence",
                    })

        if self._lexeme_memory is not None:
            for surface, start, end in self._language.ngrams(tokens, max_size=5):
                lexeme = self._active_lexeme(surface)
                if lexeme and self._lexeme_role(lexeme) == LexemeRole.COMMAND_ALIAS.value and " " in surface:
                    candidates.append({
                        "surface": surface,
                        "start": start,
                        "end": end,
                        "confidence": max(0.5, float(lexeme.confidence or 0.5)),
                        "source": "lexeme_memory",
                    })

        packet.idiom_candidates = self._dedupe_dicts(
            [*packet.idiom_candidates, *candidates],
            key_fields=("surface", "start", "end"),
        )

    def _unknown_role(
        self,
        surface: str,
        normalized: str,
        tokens: list[str],
        position: int,
    ) -> str:
        if position > 0 and tokens[position - 1] in {"you", "your", "you're"}:
            return "self_evaluation"
        if surface[:1].isupper():
            return "person_candidate"
        if position >= 0 and tokens[max(0, position - 2):position] and "teach" in tokens:
            return "teachable_surface"
        return "unknown"

    def _attention_target(
        self,
        packet: MeaningPerceptPacket,
        kernel: ContextKernel,
    ) -> str | None:
        for role in ("target", "object", "topic", "place"):
            for ref in packet.referents:
                if ref.role == role and ref.source not in {"pronoun", "deixis"} and ref.surface:
                    return ref.surface
        topic = getattr(getattr(kernel, "topic", None), "active_topic_surface", "")
        if topic:
            return topic
        for ref in packet.referents:
            if ref.surface:
                return ref.surface
        return None

    def _confidence(self, packet: MeaningPerceptPacket) -> float:
        evidence_atoms = (
            len(packet.referents)
            + len(packet.actions)
            + len(packet.states)
            + len(packet.relations)
            + len(packet.needs)
            + len(packet.affect_markers)
        )
        uncertainty_penalty = min(0.25, len(packet.unknown_lexemes) * 0.04)
        lexical_bonus = min(0.35, evidence_atoms * 0.05)
        if packet.actions and packet.referents:
            lexical_bonus += 0.08
        return max(0.2, min(0.95, 0.35 + lexical_bonus - uncertainty_penalty))

    def _active_lexeme(self, surface: str) -> Any | None:
        if self._lexeme_memory is None:
            return None
        return self._lexeme_memory.lookup_active(surface)

    @staticmethod
    def _lexeme_role(lexeme: Any) -> str:
        role = getattr(lexeme, "role", "")
        return str(getattr(role, "value", role))

    def _canonical_key(self, surface: str) -> str:
        return "_".join(self._language.tokenize(surface))

    def _extend_referents(self, packet: MeaningPerceptPacket, atoms: Iterable[ReferentAtom]) -> None:
        seen = {
            (r.surface.lower(), r.entity_id or "", r.entity_type, r.role, r.source)
            for r in packet.referents
        }
        for atom in atoms:
            if not atom.surface:
                continue
            key = (atom.surface.lower(), atom.entity_id or "", atom.entity_type, atom.role, atom.source)
            if key in seen:
                continue
            packet.referents.append(atom)
            seen.add(key)

    def _extend_actions(self, packet: MeaningPerceptPacket, atoms: Iterable[ActionAtom]) -> None:
        seen = {(a.surface.lower(), a.action_key, a.modality, a.polarity) for a in packet.actions}
        for atom in atoms:
            key = (atom.surface.lower(), atom.action_key, atom.modality, atom.polarity)
            if not atom.surface or key in seen:
                continue
            packet.actions.append(atom)
            seen.add(key)

    def _extend_states(self, packet: MeaningPerceptPacket, atoms: Iterable[StateAtom]) -> None:
        seen = {(s.surface.lower(), s.state_key, s.holder_role, s.dimension) for s in packet.states}
        for atom in atoms:
            key = (atom.surface.lower(), atom.state_key, atom.holder_role, atom.dimension)
            if not atom.surface or key in seen:
                continue
            packet.states.append(atom)
            seen.add(key)

    def _extend_relations(self, packet: MeaningPerceptPacket, atoms: Iterable[RelationAtom]) -> None:
        seen = {(r.relation_key, r.source_role, r.target_role) for r in packet.relations}
        for atom in atoms:
            key = (atom.relation_key, atom.source_role, atom.target_role)
            if not atom.relation_key or key in seen:
                continue
            packet.relations.append(atom)
            seen.add(key)

    def _extend_needs(self, packet: MeaningPerceptPacket, atoms: Iterable[NeedAtom]) -> None:
        seen = {(n.holder_role, n.need_key) for n in packet.needs}
        for atom in atoms:
            key = (atom.holder_role, atom.need_key)
            if not atom.need_key or key in seen:
                continue
            packet.needs.append(atom)
            seen.add(key)

    @staticmethod
    def _dedupe_dicts(
        values: Iterable[dict[str, Any]],
        key_fields: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        for value in values:
            key = tuple(value.get(field) for field in key_fields)
            if key in seen:
                continue
            result.append(value)
            seen.add(key)
        return result
