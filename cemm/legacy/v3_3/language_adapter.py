"""Language adapters for mapping surface text into shared CEMM atoms.

The MeaningPerceptor should not own English-specific lexicons. Its job is to
assemble a MeaningPerceptPacket from upstream normalization, learned lexemes,
NER, surface tags, and language-specific mappings. Adapters keep tokenization,
pronouns, cue words, affect markers, and shallow lexical semantics replaceable
per language while producing the same atom shapes.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import re
from pathlib import Path
from typing import Any, Iterable

from ...types.meaning_percept import ActionAtom, NeedAtom, ReferentAtom, StateAtom
from .semantic_schema_kernel import SemanticSchemaKernel, get_kernel


_TOKEN_RE = re.compile(r"[^\W_]+(?:'[^\W_]+)?|\d+", re.UNICODE)


@dataclass(frozen=True)
class PronounBinding:
    """A surface pronoun mapped into a CEMM referent role."""

    entity_type: str
    role: str
    source: str = "pronoun"
    confidence: float = 0.9


@dataclass(frozen=True)
class StateBinding:
    """A surface state mapped into a semantic state dimension."""

    state_key: str
    dimension: str
    polarity: str
    intensity: float = 0.65
    confidence: float = 0.7


@dataclass(frozen=True)
class NeedBinding:
    """A surface cue mapped into a need atom."""

    need_key: str
    intensity: float
    confidence: float = 0.7


class LanguageAdapter:
    """Base adapter interface for language-specific surface semantics.

    Subclasses may be backed by JSON language packs, learned language models,
    or deterministic seed resources. The contract is intentionally small:
    adapters receive surface tokens and return shared CEMM atom dataclasses.
    """

    language_code = "und"

    def tokenize(self, text: str) -> list[str]:
        """Return normalized tokens for semantic matching.

        Apostrophes are stripped so orthographic variants like "what's"
        and "whats" normalize to the same token.  This is the §5.1
        Normalize step — contraction normalization happens here, not
        by duplicating aliases in JSON data.
        """
        return [
            m.group(0).lower().replace("'", "")
            for m in _TOKEN_RE.finditer(text or "")
        ]

    def surface_tokens(self, text: str) -> list[str]:
        """Return token surfaces with original casing preserved."""
        return [m.group(0) for m in _TOKEN_RE.finditer(text or "")]

    def punctuation_features(self, text: str) -> dict[str, Any]:
        stripped = (text or "").rstrip()
        return {
            "has_question_mark": "?" in text,
            "has_exclamation": "!" in text,
            "has_ellipsis": "..." in text,
            "is_all_caps": text.isupper() and len(text.strip()) > 2,
            "trailing_punctuation": stripped[-1] if stripped and stripped[-1] in ".!?,;:" else "",
        }

    def map_pronouns(self, tokens: list[str]) -> list[ReferentAtom]:
        return []

    def map_deictics(self, tokens: list[str]) -> list[ReferentAtom]:
        return []

    def map_actions(self, tokens: list[str]) -> list[ActionAtom]:
        return []

    def map_states(self, tokens: list[str]) -> list[StateAtom]:
        return []

    def map_needs(self, tokens: list[str]) -> list[NeedAtom]:
        return []

    def detect_affect(self, raw_text: str, tokens: list[str]) -> list[dict[str, Any]]:
        return []

    def is_entity_surface_excluded(self, surface: str, known_words: set[str] | None = None) -> bool:
        word = self.normalize_surface(surface)
        return not word or word in (known_words or set())

    def capitalization_confidence(self, surface: str, token_index: int) -> float:
        return 0.4 if token_index == 0 else 0.6

    def normalize_surface(self, surface: str) -> str:
        return (surface or "").strip(".,!?;:\"'()[]{}").lower()

    def ngrams(self, tokens: list[str], max_size: int = 4) -> Iterable[tuple[str, int, int]]:
        limit = min(max_size, len(tokens))
        for size in range(limit, 0, -1):
            for start in range(0, len(tokens) - size + 1):
                end = start + size
                yield " ".join(tokens[start:end]), start, end


class SchemaBackedLanguageAdapter(LanguageAdapter):
    """Unified language adapter backed by JSON language packs + Semantic Schema Kernel.

    Loads pronouns, deictics, states, needs, affect markers, entity exclude,
    negations, and modals from JSON files in the language pack directory.
    Action lookup is delegated to the Semantic Schema Kernel's
    ActionOperatorRegistry, which contains canonical action operator schemas
    with per-language aliases.

    Language files are alias layers only. Canonical action meaning lives in
    cemm/data/semantic_schemas/action_operator_schemas.json.
    """

    def __init__(
        self,
        language_code: str = "en",
        pack_dir: Path | None = None,
        kernel: SemanticSchemaKernel | None = None,
    ) -> None:
        self.language_code = language_code
        if pack_dir is None:
            pack_dir = Path(__file__).parent.parent.parent / "data" / "languages" / language_code
        self._pack_dir = pack_dir
        self._kernel = kernel or get_kernel()
        self._load_pack()

    def _load_pack(self) -> None:
        self._pronouns: dict[str, PronounBinding] = {}
        self._deictics: set[str] = set()
        self._states: dict[str, StateBinding] = {}
        self._needs: dict[str, NeedBinding] = {}
        self._affect_markers: dict[str, set[str]] = {}
        self._entity_exclude: frozenset[str] = frozenset()
        self._negations: set[str] = set()
        self._proposed_modals: set[str] = set()
        self._desired_modals: set[str] = set()
        self._self_pronouns: set[str] = set()
        self._third_person_pronouns: set[str] = set()

        def _load(name: str) -> Any | None:
            path = self._pack_dir / name
            if not path.exists():
                return None
            return json.loads(path.read_text(encoding="utf-8"))

        pron_data = _load("pronouns.json")
        if pron_data:
            for surface, mapping in pron_data.items():
                entity_type = mapping.get("entity_type", "unknown")
                role = mapping.get("role", "topic")
                confidence = mapping.get("confidence", 0.9)
                source = mapping.get("source", "pronoun")
                self._pronouns[surface] = PronounBinding(
                    entity_type, role, source=source, confidence=confidence,
                )
                if entity_type == "self":
                    self._self_pronouns.add(surface)
                elif entity_type == "person":
                    self._third_person_pronouns.add(surface)

        deictic_data = _load("deictic_words.json")
        if deictic_data:
            self._deictics = set(deictic_data)

        state_data = _load("state_keywords.json")
        if state_data:
            for surface, mapping in state_data.items():
                self._states[surface] = StateBinding(
                    state_key=mapping.get("state_key", surface),
                    dimension=mapping.get("dimension", "unknown"),
                    polarity=mapping.get("polarity", "unknown"),
                    intensity=float(mapping.get("intensity", 0.65)),
                )

        need_data = _load("need_keywords.json")
        if need_data:
            for surface, mapping in need_data.items():
                self._needs[surface] = NeedBinding(
                    need_key=mapping.get("need_key", surface),
                    intensity=float(mapping.get("intensity", 0.5)),
                )

        affect_data = _load("affect_markers.json")
        if affect_data:
            for affect_type, markers in affect_data.items():
                self._affect_markers[affect_type] = set(markers)

        exclude_data = _load("entity_exclude.json")
        if exclude_data:
            self._entity_exclude = frozenset(exclude_data)

        neg_data = _load("negations.json")
        if neg_data:
            self._negations = set(neg_data)

        modal_data = _load("modals.json")
        if modal_data:
            for surface, modality in modal_data.items():
                if modality == "proposed":
                    self._proposed_modals.add(surface)
                elif modality == "desired":
                    self._desired_modals.add(surface)

    def map_pronouns(self, tokens: list[str]) -> list[ReferentAtom]:
        atoms: list[ReferentAtom] = []
        seen: set[str] = set()
        for token in tokens:
            binding = self._pronouns.get(token)
            if binding is None or token in seen:
                continue
            seen.add(token)
            atoms.append(ReferentAtom(
                surface=token,
                entity_type=binding.entity_type,
                role=binding.role,
                known=True,
                source=binding.source,
                confidence=binding.confidence,
            ))
        return atoms

    def map_deictics(self, tokens: list[str]) -> list[ReferentAtom]:
        atoms: list[ReferentAtom] = []
        for token in dict.fromkeys(tokens):
            if token not in self._deictics:
                continue
            is_place = token in {"here", "there", "ebee", "ebea"}
            atoms.append(ReferentAtom(
                surface=token,
                entity_type="place" if is_place else "abstract",
                role="place" if is_place else "topic",
                known=True,
                source="deixis",
                confidence=0.7,
            ))
        return atoms

    def map_actions(self, tokens: list[str]) -> list[ActionAtom]:
        token_set = set(tokens)
        modality = self._modality(token_set)
        polarity = "negated" if token_set & self._negations else "affirmed"
        atoms: list[ActionAtom] = []
        consumed: set[int] = set()

        # Pass 1: Multi-word aliases (bigrams, trigrams) — check first for precedence
        for n in (3, 2):
            for i in range(len(tokens) - n + 1):
                if any(i + j in consumed for j in range(n)):
                    continue
                phrase = " ".join(tokens[i:i + n])
                action_key = self._kernel.action_operators.lookup_alias(phrase, self.language_code)
                if action_key is None:
                    continue
                schema_slots = self._kernel.action_operators.slots_for(action_key)
                actor_role, target_role, object_role = self._infer_roles_from_schema(action_key, token_set, phrase)
                atoms.append(ActionAtom(
                    surface=phrase,
                    action_key=action_key,
                    actor_role=actor_role,
                    object_role=object_role,
                    target_role=target_role,
                    modality=modality,
                    polarity=polarity,
                    confidence=0.7,
                    schema_slots=schema_slots,
                ))
                for j in range(n):
                    consumed.add(i + j)

        # Pass 2: Single-token aliases — skip tokens consumed by multi-word matches
        for i, token in enumerate(tokens):
            if i in consumed:
                continue
            action_key = self._kernel.action_operators.lookup_alias(token, self.language_code)
            if action_key is None:
                continue
            schema_slots = self._kernel.action_operators.slots_for(action_key)
            actor_role, target_role, object_role = self._infer_roles_from_schema(action_key, token_set, token)
            atoms.append(ActionAtom(
                surface=token,
                action_key=action_key,
                actor_role=actor_role,
                object_role=object_role,
                target_role=target_role,
                modality=modality,
                polarity=polarity,
                confidence=0.7,
                schema_slots=schema_slots,
            ))
        return atoms

    def map_states(self, tokens: list[str]) -> list[StateAtom]:
        token_set = set(tokens)
        holder = self._holder_role(token_set)
        atoms: list[StateAtom] = []
        for token in tokens:
            binding = self._states.get(token)
            if binding is None:
                continue
            atoms.append(StateAtom(
                surface=token,
                state_key=binding.state_key,
                holder_role=holder,
                dimension=binding.dimension,
                polarity=binding.polarity,
                intensity=binding.intensity,
                confidence=binding.confidence,
            ))
        return atoms

    def map_needs(self, tokens: list[str]) -> list[NeedAtom]:
        token_set = set(tokens)
        holder = "self" if token_set & self._self_pronouns else "user"
        atoms: list[NeedAtom] = []
        for token in tokens:
            binding = self._needs.get(token)
            if binding is None:
                continue
            atoms.append(NeedAtom(
                holder_role=holder,
                need_key=binding.need_key,
                intensity=binding.intensity,
                confidence=binding.confidence,
            ))
        return atoms

    def detect_affect(self, raw_text: str, tokens: list[str]) -> list[dict[str, Any]]:
        text = (raw_text or "").lower()
        token_set = set(tokens)
        markers: list[dict[str, Any]] = []
        for affect_type, surfaces in self._affect_markers.items():
            for surface in surfaces:
                matched = surface in text if " " in surface else surface in token_set
                if not matched:
                    continue
                markers.append({
                    "type": affect_type,
                    "surface": surface,
                    "confidence": 0.6,
                    "source": f"{self.language_code}_adapter",
                })
        return markers

    def is_entity_surface_excluded(self, surface: str, known_words: set[str] | None = None) -> bool:
        word = self.normalize_surface(surface)
        if not word or word.isdigit():
            return True
        if word in self._entity_exclude:
            return True
        if word in (known_words or set()):
            return True
        return False

    @property
    def known_tokens(self) -> set[str]:
        """All known surface tokens for language detection scoring."""
        tokens: set[str] = set()
        tokens.update(self._pronouns.keys())
        tokens.update(self._states.keys())
        tokens.update(self._needs.keys())
        tokens.update(self._entity_exclude)
        tokens.update(self._deictics)
        for action_key in self._kernel.action_operators.all_action_keys():
            schema = self._kernel.action_operators.get(action_key)
            if schema and self.language_code in schema.aliases:
                tokens.update(schema.aliases[self.language_code])
        return tokens

    def _modality(self, token_set: set[str]) -> str:
        desired_without_have = self._desired_modals - {"have"}
        if token_set & desired_without_have:
            return "desired"
        if "have" in token_set and "to" in token_set:
            return "desired"
        if token_set & self._proposed_modals:
            return "proposed"
        return "observed"

    def _holder_role(self, token_set: set[str]) -> str:
        if token_set & self._self_pronouns:
            return "self"
        if token_set & self._third_person_pronouns:
            return "third_party"
        return "user"

    def _actor_role(self, token_set: set[str]) -> str | None:
        user_pronouns = {s for s, b in self._pronouns.items() if b.entity_type == "user" and b.role == "actor"}
        if token_set & user_pronouns:
            return "user"
        if token_set & self._self_pronouns:
            return "self"
        if token_set & self._third_person_pronouns:
            return "third_party"
        return None

    def _target_role(self, action_key: str, token_set: set[str]) -> str | None:
        schema = self._kernel.action_operators.get(action_key)
        if schema is None:
            return None
        slots = schema.slots
        if "target" in slots or "recipient" in slots:
            if token_set & self._self_pronouns:
                return "self"
            if token_set & self._third_person_pronouns:
                return "third_party"
            return "target"
        return None

    def _infer_roles_from_schema(
        self, action_key: str, token_set: set[str],
        action_surface: str = "",
    ) -> tuple[str | None, str | None, str | None]:
        """Infer actor, target, and object roles from schema slots when pronouns are absent.

        For statements like 'eat food' (no pronouns), the speaker is the default actor.
        For schemas with an object slot, assign the object noun surface as the object role.
        For schemas with a target/recipient slot, assign via target role logic.
        """
        schema = self._kernel.action_operators.get(action_key)
        if schema is None:
            return None, None, None
        actor = self._actor_role(token_set)
        if actor is None and "actor" in schema.slots:
            actor = "user"
        target = self._target_role(action_key, token_set)
        obj = None
        if "object" in schema.slots and target is None:
            remaining = token_set - set(self._pronouns) - {action_surface.lower()}
            remaining.discard("")
            obj = next(iter(remaining), "object")
        return actor, target, obj


logger = logging.getLogger(__name__)


def get_adapter(language: str = "en") -> LanguageAdapter:
    """Get a LanguageAdapter for the given language.

    Returns SchemaBackedLanguageAdapter for any language with a JSON pack.
    Falls back to English if the requested language pack is not available.
    """
    pack_dir = Path(__file__).parent.parent.parent / "data" / "languages" / language
    if not pack_dir.exists() or not (pack_dir / "pronouns.json").exists():
        if language != "en":
            logger.warning("Language pack '%s' not found at %s, falling back to 'en'", language, pack_dir)
            return get_adapter("en")
    return SchemaBackedLanguageAdapter(language_code=language, pack_dir=pack_dir)


__all__ = [
    "LanguageAdapter",
    "SchemaBackedLanguageAdapter",
    "PronounBinding",
    "StateBinding",
    "NeedBinding",
    "get_adapter",
]
