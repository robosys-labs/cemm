"""MeaningPerceptor — builds MeaningPerceptPacket from signal + NER + lexeme memory.

Implements §8.2 from cemm_foundational_fixes.md and §5 from architecture.md.

The MeaningPerceptPacket is the first place where NER, POS-lite role cues,
unknown token detection, slang repair, and referent binding meet. It must be
built immediately after normalization and before UOL mapping.

No component after this should rediscover basic token/entity/action meaning
independently from raw strings.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from ..types.meaning_percept import (
    MeaningPerceptPacket,
    ReferentAtom,
    ActionAtom,
    StateAtom,
    RelationAtom,
    NeedAtom,
    AffordanceAtom,
)
from ..types.signal import Signal
from ..types.context_kernel import ContextKernel
from ..learning.surface_tagger import SurfaceTagger
from ..learning.ner_tagger import NERTagger
from ..learning.lexeme_memory import LexemeMemory


# Pronoun to entity type mapping
_PRONOUN_MAP: dict[str, tuple[str, str, str]] = {
    # surface -> (entity_type, role, source)
    "i": ("user", "actor", "pronoun"),
    "me": ("user", "target", "pronoun"),
    "my": ("user", "possessor", "pronoun"),
    "mine": ("user", "possessor", "pronoun"),
    "myself": ("user", "target", "pronoun"),
    "we": ("user", "actor", "pronoun"),
    "us": ("user", "target", "pronoun"),
    "our": ("user", "possessor", "pronoun"),
    "you": ("self", "target", "pronoun"),
    "your": ("self", "possessor", "pronoun"),
    "yourself": ("self", "target", "pronoun"),
    "yours": ("self", "possessor", "pronoun"),
    "he": ("person", "actor", "pronoun"),
    "him": ("person", "target", "pronoun"),
    "his": ("person", "possessor", "pronoun"),
    "she": ("person", "actor", "pronoun"),
    "her": ("person", "target", "pronoun"),
    "hers": ("person", "possessor", "pronoun"),
    "they": ("person", "actor", "pronoun"),
    "them": ("person", "target", "pronoun"),
    "their": ("person", "possessor", "pronoun"),
    "it": ("object", "target", "pronoun"),
    "its": ("object", "possessor", "pronoun"),
}

# Deictic words
_DEICTIC_WORDS = {"here", "there", "this", "that", "those", "these", "now", "then"}

# Words that should never be treated as entity candidates even when capitalized.
# This includes pronouns, stopwords, common sentence starters, greetings/fillers,
# and affect markers. Phone keyboards auto-capitalize the first word of every
# sentence, so we cannot rely on capitalization alone for proper-noun detection.
_ENTITY_EXCLUDE: frozenset[str] = frozenset({
    # pronouns
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
    "my", "your", "his", "its", "our", "their", "mine", "yours", "ours", "theirs",
    "myself", "yourself", "himself", "herself", "itself", "ourselves", "yourselves", "themselves",
    # articles / determiners / prepositions / conjunctions
    "the", "a", "an", "and", "or", "but", "if", "then", "than", "to", "of", "in", "on", "at", "for",
    "with", "by", "from", "as", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might", "can", "this", "that", "these",
    "those", "what", "which", "who", "when", "where", "why", "how", "all", "each", "every", "some", "any",
    "no", "not", "only", "just", "so", "very", "too", "also", "am", "about", "actually", "wait",
    # greetings / fillers / acknowledgements (common sentence starters)
    "hi", "hey", "hello", "bye", "goodbye", "oh", "well", "hmm", "uh", "um",
    "yeah", "yup", "ok", "okay", "sure", "right", "yes", "nah",
    "lol", "haha", "heh", "lmao", "rofl", "wow", "yay", "aww", "boo", "meh", "huh",
    "please", "thanks", "thank", "urgh", "urghh", "ugh", "ughh", "argh", "seriously", "really",
})

# State keywords mapped to state keys and dimensions
_STATE_KEYWORDS: dict[str, tuple[str, str, str]] = {
    # surface -> (state_key, dimension, polarity)
    "hungry": ("hungry", "hunger", "negative"),
    "thirsty": ("thirsty", "hunger", "negative"),
    "fine": ("fine", "happiness", "positive"),
    "good": ("good", "happiness", "positive"),
    "okay": ("okay", "happiness", "positive"),
    "ok": ("ok", "happiness", "positive"),
    "sick": ("sick", "health", "negative"),
    "ill": ("ill", "health", "negative"),
    "tired": ("tired", "health", "negative"),
    "angry": ("angry", "happiness", "negative"),
    "happy": ("happy", "happiness", "positive"),
    "sad": ("sad", "happiness", "negative"),
    "confused": ("confused", "knowledge", "negative"),
    "lost": ("lost", "knowledge", "negative"),
    "fine_about": ("fine", "happiness", "positive"),
}

# Need keywords mapped to need keys
_NEED_KEYWORDS: dict[str, tuple[str, float]] = {
    "hungry": ("food", 0.8),
    "thirsty": ("water", 0.8),
    "tired": ("rest", 0.7),
    "confused": ("clarity", 0.7),
    "lost": ("clarity", 0.6),
    "help": ("help", 0.6),
}

# Action keywords mapped to action keys
_ACTION_KEYWORDS: dict[str, str] = {
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

# Affect markers
_AFFECT_MARKERS = {
    "frustration": {"ugh", "argh", "seriously", "come on", "really", "urgh", "urghh", "ughh",
                    "canned responses", "same response", "generic response", "template response",
                    "scripted", "copy paste", "robotic", "pattern matcher"},
    "playful": {"lol", "haha", "heh", "lmao", "rofl"},
    "sadness": {"sigh", "alas", "unfortunately"},
    "anger": {"damn", "crap", "hell"},
    "surprise": {"wow", "whoa", "omg", "oh my"},
    "repair": {"what", "wait what", "lol what", "huh", "what are you talking about",
               "what do you mean", "i don't get it", "come again"},
}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


class MeaningPerceptor:
    """Builds MeaningPerceptPacket from signal + normalizer + NER + lexeme memory."""

    def __init__(
        self,
        ner_tagger: NERTagger | None = None,
        surface_tagger: SurfaceTagger | None = None,
        lexeme_memory: LexemeMemory | None = None,
    ) -> None:
        self._ner_tagger = ner_tagger
        self._surface_tagger = surface_tagger
        self._lexeme_memory = lexeme_memory

    def perceive(
        self,
        signal: Signal,
        kernel: ContextKernel,
    ) -> MeaningPerceptPacket:
        """Build a MeaningPerceptPacket from the signal and kernel."""
        raw_text = signal.content
        tokens = _tokenize(raw_text)
        normalized_tokens = tokens
        repaired_tokens = tokens

        # Get normalized forms if available
        normalized_forms: list[str] = []
        if signal.normalized:
            normalized_tokens = _tokenize(signal.normalized.canonical_form)
            repaired_tokens = normalized_tokens
            unknown_tokens = signal.normalized.surface_features.get("unknown_tokens", [])
            normalized_forms = list(getattr(signal.normalized, "normalized_forms", []))
        else:
            unknown_tokens = []

        packet = MeaningPerceptPacket(
            id=uuid.uuid4().hex[:16],
            signal_id=signal.id,
            context_id=signal.context_id,
            raw_text=raw_text,
            tokens=tokens,
            normalized_tokens=normalized_tokens,
            repaired_tokens=repaired_tokens,
            normalized_forms=normalized_forms,
            punctuation_features={
                "has_question_mark": "?" in raw_text,
                "has_exclamation": "!" in raw_text,
                "has_ellipsis": "..." in raw_text,
                "is_all_caps": raw_text.isupper() and len(raw_text) > 2,
                "trailing_punctuation": raw_text.rstrip()[-1] if raw_text.rstrip() and raw_text.rstrip()[-1] in ".!?,;:" else "",
            },
            speaker_entity_id="user",
            listener_entity_id="self",
        )

        # Run NER if available
        ner_entities: list[dict[str, Any]] = []
        if self._ner_tagger:
            ner_entities = self._ner_tagger.extract_entities(tokens)

        # Run surface tagger for semantic roles if available
        semantic_spans: list[dict[str, Any]] = []
        if self._surface_tagger:
            semantic_spans = self._surface_tagger.extract_all(tokens, unknown_tokens=unknown_tokens)

        # Build referents from NER entities
        for ent in ner_entities:
            entity_type = ent.get("role", "unknown")
            if entity_type == "person":
                entity_type = "person"
            elif entity_type == "place":
                entity_type = "place"
            elif entity_type == "organization":
                entity_type = "organization"
            elif entity_type == "time":
                entity_type = "abstract"
            else:
                entity_type = "unknown"
            packet.referents.append(ReferentAtom(
                surface=ent.get("text", ""),
                entity_type=entity_type,
                role="topic",
                known=ent.get("confidence", 0) > 0.5,
                source="ner",
                confidence=ent.get("confidence", 0.5),
            ))

        # Build referents from pronouns
        token_set = set(tokens)
        for pronoun, (etype, role, source) in _PRONOUN_MAP.items():
            if pronoun in token_set:
                packet.referents.append(ReferentAtom(
                    surface=pronoun,
                    entity_type=etype,
                    role=role,
                    known=True,
                    source=source,
                    confidence=0.9,
                ))

        # Detect capitalized tokens as person/place candidates.
        # Phone keyboards auto-capitalize the first word of every sentence, so
        # we cannot rely on capitalization alone. Instead, we exclude pronouns,
        # stopwords, greetings/fillers, and known words. Position 0 gets lower
        # confidence since it may be auto-capitalized rather than a proper noun.
        known_words = set()
        if self._surface_tagger:
            known_words = getattr(self._surface_tagger, "_known_words", set())
        raw_tokens = raw_text.split()
        seen_surfaces: set[str] = set()
        for idx, token in enumerate(raw_tokens):
            clean = token.strip(".,!?;:\"'()[]{}")
            if not clean or not clean[0].isupper():
                continue
            lower = clean.lower()
            if lower in _ENTITY_EXCLUDE:
                continue
            if lower in known_words:
                continue
            if self._lexeme_memory and self._lexeme_memory.lookup_active(lower):
                continue
            if lower in seen_surfaces:
                continue
            seen_surfaces.add(lower)
            # Position 0 may be auto-capitalized by phone keyboard
            confidence = 0.4 if idx == 0 else 0.6
            packet.referents.append(ReferentAtom(
                surface=clean,
                entity_type="person",
                role="topic",
                known=False,
                source="capitalization",
                confidence=confidence,
            ))

        # Detect deictic words
        for deictic in _DEICTIC_WORDS:
            if deictic in token_set:
                packet.referents.append(ReferentAtom(
                    surface=deictic,
                    entity_type="place" if deictic in ("here", "there", "this", "that") else "abstract",
                    role="place" if deictic in ("here", "there") else "topic",
                    known=True,
                    source="deixis",
                    confidence=0.7,
                ))

        # Build actions from action keywords
        for token in tokens:
            if token in _ACTION_KEYWORDS:
                # Determine modality from context
                modality = "observed"
                if any(m in token_set for m in ("should", "can", "could", "would", "shall")):
                    modality = "proposed"
                elif any(m in token_set for m in ("must", "need", "have to")):
                    modality = "desired"
                # Determine polarity
                polarity = "affirmed"
                if any(n in token_set for n in ("not", "never", "dont", "don't", "no")):
                    polarity = "negated"
                packet.actions.append(ActionAtom(
                    surface=token,
                    action_key=_ACTION_KEYWORDS[token],
                    modality=modality,
                    polarity=polarity,
                    confidence=0.7,
                ))

        # Build states from state keywords
        for token in tokens:
            if token in _STATE_KEYWORDS:
                state_key, dimension, polarity = _STATE_KEYWORDS[token]
                # Determine holder based on pronoun context
                holder = "user"
                if "you" in token_set or "your" in token_set:
                    holder = "self"
                elif "he" in token_set or "she" in token_set or "him" in token_set or "her" in token_set:
                    holder = "third_party"
                packet.states.append(StateAtom(
                    surface=token,
                    state_key=state_key,
                    holder_role=holder,
                    dimension=dimension,
                    polarity=polarity,
                    intensity=0.6 if polarity == "positive" else 0.7,
                    confidence=0.7,
                ))

        # Build needs from need keywords
        for token in tokens:
            if token in _NEED_KEYWORDS:
                need_key, intensity = _NEED_KEYWORDS[token]
                holder = "user"
                if "you" in token_set:
                    holder = "self"
                packet.needs.append(NeedAtom(
                    holder_role=holder,
                    need_key=need_key,
                    intensity=intensity,
                    confidence=0.7,
                ))

        # Detect unknown lexemes
        for token in unknown_tokens:
            token_lower = token.lower()
            if token_lower in known_words:
                continue
            if self._lexeme_memory and self._lexeme_memory.lookup_active(token_lower):
                continue
            # Determine candidate role
            role = "unknown"
            # Check if it's near "you" -> likely self evaluation
            token_idx = tokens.index(token_lower) if token_lower in tokens else -1
            if token_idx > 0 and tokens[token_idx - 1] in ("you", "your", "you're"):
                role = "self_evaluation"
            elif token_idx >= 0 and token[0].isupper():
                role = "person_candidate"
            packet.unknown_lexemes.append({
                "surface": token,
                "role": role,
                "position": token_idx,
                "confidence": 0.5,
            })

        # Detect idiom candidates (multi-word unknown phrases)
        # Simple heuristic: sequences of words not in known vocabulary
        if len(tokens) >= 3:
            for i in range(len(tokens) - 2):
                phrase = " ".join(tokens[i:i + 3])
                # Check if this phrase contains unknown words
                phrase_words = tokens[i:i + 3]
                unknown_count = sum(1 for w in phrase_words if w in {t.lower() for t in unknown_tokens})
                if unknown_count >= 2:
                    packet.idiom_candidates.append({
                        "surface": phrase,
                        "start": i,
                        "end": i + 3,
                        "confidence": 0.4,
                    })

        # Detect affect markers
        for affect_type, markers in _AFFECT_MARKERS.items():
            for marker in markers:
                if marker in raw_text.lower():
                    packet.affect_markers.append({
                        "type": affect_type,
                        "surface": marker,
                        "confidence": 0.6,
                    })

        # Set attention target
        if packet.referents:
            # First non-pronoun referent is likely the attention target
            for ref in packet.referents:
                if ref.source not in ("pronoun", "deixis"):
                    packet.attention_target = ref.surface
                    break
            if not packet.attention_target:
                packet.attention_target = packet.referents[0].surface

        # Compute overall confidence
        atom_count = (
            len(packet.referents) + len(packet.actions) + len(packet.states)
            + len(packet.needs) + len(packet.unknown_lexemes)
        )
        packet.confidence = min(0.9, 0.3 + atom_count * 0.1)

        return packet
