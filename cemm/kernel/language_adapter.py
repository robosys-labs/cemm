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
import re
from pathlib import Path
from typing import Any, Iterable

from ..types.meaning_percept import ActionAtom, NeedAtom, ReferentAtom, StateAtom


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
        """Return normalized tokens for semantic matching."""
        return [m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")]

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


class EnglishLanguageAdapter(LanguageAdapter):
    """Default deterministic English adapter.

    This preserves the current seed behavior while moving it behind an adapter
    boundary so Igbo, Yoruba, Spanish, or learned language packs can emit the
    same CEMM atoms without changing the kernel.
    """

    language_code = "en"

    PRONOUNS: dict[str, PronounBinding] = {
        "i": PronounBinding("user", "actor"),
        "me": PronounBinding("user", "target"),
        "my": PronounBinding("user", "possessor"),
        "mine": PronounBinding("user", "possessor"),
        "myself": PronounBinding("user", "target"),
        "we": PronounBinding("user", "actor"),
        "us": PronounBinding("user", "target"),
        "our": PronounBinding("user", "possessor"),
        "you": PronounBinding("self", "target"),
        "your": PronounBinding("self", "possessor"),
        "yourself": PronounBinding("self", "target"),
        "yours": PronounBinding("self", "possessor"),
        "he": PronounBinding("person", "actor"),
        "him": PronounBinding("person", "target"),
        "his": PronounBinding("person", "possessor"),
        "she": PronounBinding("person", "actor"),
        "her": PronounBinding("person", "target"),
        "hers": PronounBinding("person", "possessor"),
        "they": PronounBinding("person", "actor"),
        "them": PronounBinding("person", "target"),
        "their": PronounBinding("person", "possessor"),
        "it": PronounBinding("object", "target", confidence=0.75),
        "its": PronounBinding("object", "possessor", confidence=0.75),
    }

    DEICTICS = {"here", "there", "this", "that", "those", "these", "now", "then"}

    ACTIONS: dict[str, str] = {
        "come": "move_toward_source",
        "go": "move_to_place",
        "give": "transfer_object",
        "take": "acquire_object",
        "beat": "physically_harm_target",
        "hit": "physically_harm_target",
        "hurt": "physically_harm_target",
        "attack": "physically_harm_target",
        "help": "improve_state",
        "learn": "increase_capability",
        "remember": "memory_write",
        "forget": "memory_loss",
        "eat": "consume_food",
        "drink": "consume_liquid",
        "move": "change_location",
        "run": "move_fast",
        "walk": "move_slow",
        "bring": "transfer_to_speaker",
        "send": "transfer_to_target",
        "find": "search_locate",
        "look": "search_locate",
        "ask": "request_information",
        "tell": "provide_information",
        "show": "display_information",
        "teach": "transfer_knowledge",
    }

    STATES: dict[str, StateBinding] = {
        "hungry": StateBinding("hungry", "hunger", "negative", intensity=0.75),
        "thirsty": StateBinding("thirsty", "hunger", "negative", intensity=0.75),
        "fine": StateBinding("fine", "happiness", "positive", intensity=0.55),
        "good": StateBinding("good", "happiness", "positive", intensity=0.6),
        "okay": StateBinding("okay", "happiness", "positive", intensity=0.55),
        "ok": StateBinding("ok", "happiness", "positive", intensity=0.55),
        "sick": StateBinding("sick", "health", "negative", intensity=0.75),
        "ill": StateBinding("ill", "health", "negative", intensity=0.75),
        "tired": StateBinding("tired", "health", "negative", intensity=0.65),
        "angry": StateBinding("angry", "happiness", "negative", intensity=0.75),
        "happy": StateBinding("happy", "happiness", "positive", intensity=0.7),
        "sad": StateBinding("sad", "happiness", "negative", intensity=0.7),
        "confused": StateBinding("confused", "knowledge", "negative", intensity=0.7),
        "lost": StateBinding("lost", "knowledge", "negative", intensity=0.65),
    }

    NEEDS: dict[str, NeedBinding] = {
        "hungry": NeedBinding("food", 0.8),
        "thirsty": NeedBinding("water", 0.8),
        "tired": NeedBinding("rest", 0.7),
        "confused": NeedBinding("clarity", 0.7),
        "lost": NeedBinding("clarity", 0.6),
        "help": NeedBinding("help", 0.6),
    }

    AFFECT_MARKERS: dict[str, set[str]] = {
        "frustration": {
            "ugh", "argh", "seriously", "come on", "really", "urgh", "urghh", "ughh",
            "canned responses", "same response", "generic response", "template response",
            "scripted", "copy paste", "robotic", "pattern matcher",
        },
        "playful": {"lol", "haha", "heh", "lmao", "rofl"},
        "sadness": {"sigh", "alas", "unfortunately"},
        "anger": {"damn", "crap", "hell"},
        "surprise": {"wow", "whoa", "omg", "oh my"},
        "repair": {
            "what", "wait what", "lol what", "huh", "what are you talking about",
            "what do you mean", "i don't get it", "come again",
        },
    }

    ENTITY_EXCLUDE: frozenset[str] = frozenset({
        "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
        "my", "your", "his", "its", "our", "their", "mine", "yours", "ours", "theirs",
        "myself", "yourself", "himself", "herself", "itself", "ourselves", "yourselves",
        "themselves", "the", "a", "an", "and", "or", "but", "if", "then", "than", "to",
        "of", "in", "on", "at", "for", "with", "by", "from", "as", "is", "are", "was",
        "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "can", "this", "that", "these", "those",
        "what", "which", "who", "when", "where", "why", "how", "all", "each", "every",
        "some", "any", "no", "not", "only", "just", "so", "very", "too", "also", "am",
        "about", "actually", "wait", "hi", "hey", "hello", "bye", "goodbye", "oh", "well",
        "hmm", "uh", "um", "yeah", "yup", "ok", "okay", "sure", "right", "yes", "nah",
        "lol", "haha", "heh", "lmao", "rofl", "wow", "yay", "aww", "boo", "meh", "huh",
        "please", "thanks", "thank", "urgh", "urghh", "ugh", "ughh", "argh", "seriously",
        "really",
    })

    NEGATIONS = {"not", "never", "dont", "don't", "no", "cannot", "can't", "wont", "won't"}
    PROPOSED_MODALS = {"should", "can", "could", "would", "shall", "may", "might"}
    DESIRED_MODALS = {"must", "need", "needs", "want", "wants", "have"}
    SELF_PRONOUNS = {"you", "your", "yourself", "yours"}
    THIRD_PERSON_PRONOUNS = {"he", "she", "him", "her", "they", "them", "their"}

    def map_pronouns(self, tokens: list[str]) -> list[ReferentAtom]:
        atoms: list[ReferentAtom] = []
        seen: set[str] = set()
        for token in tokens:
            binding = self.PRONOUNS.get(token)
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
            if token not in self.DEICTICS:
                continue
            is_place = token in {"here", "there"}
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
        polarity = "negated" if token_set & self.NEGATIONS else "affirmed"
        atoms: list[ActionAtom] = []
        for token in tokens:
            action_key = self.ACTIONS.get(token)
            if action_key is None:
                continue
            atoms.append(ActionAtom(
                surface=token,
                action_key=action_key,
                actor_role=self._actor_role(token_set),
                target_role=self._target_role(action_key, token_set),
                modality=modality,
                polarity=polarity,
                confidence=0.7,
            ))
        return atoms

    def map_states(self, tokens: list[str]) -> list[StateAtom]:
        token_set = set(tokens)
        holder = self._holder_role(token_set)
        atoms: list[StateAtom] = []
        for token in tokens:
            binding = self.STATES.get(token)
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
        holder = "self" if token_set & self.SELF_PRONOUNS else "user"
        atoms: list[NeedAtom] = []
        for token in tokens:
            binding = self.NEEDS.get(token)
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
        for affect_type, surfaces in self.AFFECT_MARKERS.items():
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
        if word in self.ENTITY_EXCLUDE:
            return True
        if word in (known_words or set()):
            return True
        return False

    def _modality(self, token_set: set[str]) -> str:
        desired_without_have = self.DESIRED_MODALS - {"have"}
        if token_set & desired_without_have:
            return "desired"
        if "have" in token_set and "to" in token_set:
            return "desired"
        if token_set & self.PROPOSED_MODALS:
            return "proposed"
        return "observed"

    def _holder_role(self, token_set: set[str]) -> str:
        if token_set & self.SELF_PRONOUNS:
            return "self"
        if token_set & self.THIRD_PERSON_PRONOUNS:
            return "third_party"
        return "user"

    def _actor_role(self, token_set: set[str]) -> str | None:
        if token_set & {"i", "we"}:
            return "user"
        if token_set & self.SELF_PRONOUNS:
            return "self"
        if token_set & self.THIRD_PERSON_PRONOUNS:
            return "third_party"
        return None

    def _target_role(self, action_key: str, token_set: set[str]) -> str | None:
        if action_key in {"physically_harm_target", "transfer_object", "transfer_to_target"}:
            if token_set & self.SELF_PRONOUNS:
                return "self"
            if token_set & self.THIRD_PERSON_PRONOUNS:
                return "third_party"
            return "target"
        return None


# ── JSON-backed adapter for non-English languages ──────────────────


class JSONLanguageAdapter(LanguageAdapter):
    """Adapter that loads language-specific mappings from JSON files.

    Used for non-English languages (Igbo, Yoruba, etc.) where we have
    language pack data files but don't need the full deterministic seed.
    """

    def __init__(self, language_code: str = "und", pack_dir: Path | None = None) -> None:
        self.language_code = language_code
        if pack_dir is None:
            pack_dir = Path(__file__).parent.parent / "data" / "languages" / language_code
        self._pack_dir = pack_dir
        self._load_pack()

    def _load_pack(self) -> None:
        """Load all available JSON files from the language pack directory."""
        self._pronouns: dict[str, PronounBinding] = {}
        self._deictics: set[str] = set()
        self._actions: dict[str, str] = {}
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
                self._pronouns[surface] = PronounBinding(entity_type, role, confidence=confidence)
                if entity_type == "self":
                    self._self_pronouns.add(surface)
                elif entity_type == "person":
                    self._third_person_pronouns.add(surface)

        deictic_data = _load("deictic_words.json")
        if deictic_data:
            self._deictics = set(deictic_data)

        action_data = _load("action_keywords.json")
        if action_data:
            self._actions = dict(action_data)

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
        for token in tokens:
            action_key = self._actions.get(token)
            if action_key is None:
                continue
            atoms.append(ActionAtom(
                surface=token,
                action_key=action_key,
                actor_role=self._actor_role(token_set),
                target_role=self._target_role(action_key, token_set),
                modality=modality,
                polarity=polarity,
                confidence=0.7,
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
        if action_key in {"physically_harm_target", "transfer_object", "transfer_to_target"}:
            if token_set & self._self_pronouns:
                return "self"
            if token_set & self._third_person_pronouns:
                return "third_party"
            return "target"
        return None


def get_adapter(language: str = "en") -> LanguageAdapter:
    """Get a LanguageAdapter for the given language.

    Returns EnglishLanguageAdapter for 'en', JSONLanguageAdapter for others.
    Falls back to English if the requested language pack is not available.
    """
    if language == "en":
        return EnglishLanguageAdapter()
    pack_dir = Path(__file__).parent.parent / "data" / "languages" / language
    if not pack_dir.exists() or not (pack_dir / "pronouns.json").exists():
        return EnglishLanguageAdapter()
    return JSONLanguageAdapter(language_code=language, pack_dir=pack_dir)
