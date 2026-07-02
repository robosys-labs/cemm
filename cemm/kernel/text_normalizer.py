from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from ..types.normalized_signal import NormalizedSignal
from ..learning.ner_tagger import NERTagger
from ..learning.lexeme_memory import LexemeMemory


def _load_default_ner_tagger() -> NERTagger | None:
    """Load the bundled learned NER tagger if available."""
    try:
        weights_path = Path(__file__).parent / "data" / "models" / "ner_tagger_weights.json"
        if weights_path.exists():
            return NERTagger.load(weights_path)
        alt_path = Path(__file__).parents[1] / "data" / "models" / "ner_tagger_weights.json"
        if alt_path.exists():
            return NERTagger.load(alt_path)
    except Exception:
        pass
    return None


class WordSimilarityMatcher:
    """Lightweight character n-gram + Levenshtein similarity matcher.

    Used by the data-driven normalizer to map noisy or misspelled words back
    to canonical vocabulary entries without relying on hard-coded regexes.
    """

    def __init__(self, max_distance: int = 2) -> None:
        self._max_distance = max_distance

    @staticmethod
    def _char_ngrams(word: str, n: int = 2) -> set[str]:
        if len(word) < n:
            return set()
        return {word[i : i + n] for i in range(len(word) - n + 1)}

    def jaccard(self, a: str, b: str) -> float:
        a_bigrams = self._char_ngrams(a, 2)
        b_bigrams = self._char_ngrams(b, 2)
        if not a_bigrams or not b_bigrams:
            return 0.0
        intersection = len(a_bigrams & b_bigrams)
        union = len(a_bigrams | b_bigrams)
        return intersection / union if union else 0.0

    @staticmethod
    def _levenshtein(a: str, b: str) -> int:
        if len(a) < len(b):
            a, b = b, a
        if not b:
            return len(a)
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a):
            curr = [i + 1]
            for j, cb in enumerate(b):
                cost = 0 if ca == cb else 1
                curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + cost))
            prev = curr
        return prev[-1]

    def similarity(self, a: str, b: str) -> float:
        """Return a similarity score in [0, 1]."""
        if a == b:
            return 1.0
        jac = self.jaccard(a, b)
        max_len = max(len(a), len(b))
        if max_len == 0:
            return 0.0
        dist = self._levenshtein(a, b)
        # Adaptive allowed distance: short words are stricter.
        max_allowed = 1 if max_len <= 5 else self._max_distance
        lev_sim = max(0.0, 1.0 - dist / max_allowed) if max_allowed else 0.0
        return 0.6 * jac + 0.4 * lev_sim

    def is_likely_repair(self, word: str, known: str) -> bool:
        """Return True if `known` is a plausible correction for `word`."""
        if word == known:
            return True
        max_len = max(len(word), len(known))
        if max_len <= 3:
            return False  # Too ambiguous for similarity alone.
        dist = self._levenshtein(word, known)
        if max_len <= 5:
            return dist <= 1
        # For longer words combine edit distance with a minimum shape overlap.
        if dist > 2:
            return False
        return self.jaccard(word, known) >= 0.25


class TextNormalizer:
    """Data-driven text normalization.

    Loads canonical vocabulary, noisy-word and typo mappings from a JSON file
    (default: ``cemm/data/vocab.json``) and uses character n-gram / Levenshtein
    similarity to repair unknown or noisy tokens.  Runtime-learned words from
    ``LexemeMemory`` and entities from an optional ``NERTagger`` are treated as
    known, so the vocabulary grows through use rather than hard-coding.
    """

    DEFAULT_VOCAB_PATH = Path(__file__).parent.parent / "data" / "vocab.json"

    def __init__(
        self,
        vocab_path: str | Path | None = None,
        ner_tagger: NERTagger | None = None,
        lexeme_memory: LexemeMemory | None = None,
    ) -> None:
        self._ner_tagger = ner_tagger or _load_default_ner_tagger()
        self._lexeme_memory = lexeme_memory
        self._matcher = WordSimilarityMatcher()
        self._vocab_path = Path(vocab_path) if vocab_path else self.DEFAULT_VOCAB_PATH
        self._load_vocab()

    def _load_vocab(self) -> None:
        if self._vocab_path.exists():
            data = json.loads(self._vocab_path.read_text(encoding="utf-8"))
            self._known_words = set(data.get("known_words", []))
            self._noisy_map = dict(data.get("noisy_map", {}))
            self._typo_map = dict(data.get("typo_map", {}))
        else:
            self._known_words = set()
            self._noisy_map = {}
            self._typo_map = {}

    def normalize(self, text: str) -> NormalizedSignal:
        raw = text
        nfkc = unicodedata.normalize("NFKC", raw)
        folded = "".join(
            c for c in unicodedata.normalize("NFKD", nfkc) if not unicodedata.combining(c)
        )
        lowered = folded.lower()
        emoji_count = sum(1 for c in lowered if unicodedata.category(c).startswith("So"))
        punctuation_stripped = re.sub(r"[^\w\s]", " ", lowered, flags=re.UNICODE)
        collapsed = re.sub(r"\s+", " ", punctuation_stripped).strip()
        # Preserve original casing for proper-noun detection.
        cased_stripped = re.sub(r"[^\w\s]", " ", folded, flags=re.UNICODE)
        cased_collapsed = re.sub(r"\s+", " ", cased_stripped).strip()

        repeated_runs = re.findall(r"([a-z])\1{2,}", collapsed)
        repeated_collapsed = re.sub(r"([a-z])\1{2,}", r"\1\1", collapsed)
        repeated_single_collapsed = re.sub(r"([a-z])\1{2,}", r"\1", collapsed)

        raw_tokens = cased_collapsed.split()
        tokens, lexical, slang_used = self._repair_tokens(raw_tokens)
        forms = []
        for form in [collapsed, repeated_collapsed, repeated_single_collapsed, lexical]:
            if form and form not in forms:
                forms.append(form)

        scripts = sorted(
            {unicodedata.name(c, "UNKNOWN").split()[0] for c in raw if c.isalpha()}
        )

        unknown_tokens = self._detect_unknown_tokens(raw_tokens)
        repair_candidates = self._detect_repair_candidates(raw_tokens)

        repeated_chars = len(repeated_runs) > 0
        casual_spelling = bool(repair_candidates)

        return NormalizedSignal(
            raw_text=raw,
            normalized_forms=forms,
            canonical_form=forms[-1] if forms else "",
            detected_scripts=scripts,
            noise_features={
                "emoji_count": emoji_count,
                "repeated_char_runs": len(repeated_runs),
                "leading_or_trailing_space": raw != raw.strip(),
                "repeated_chars": repeated_chars,
                "casual_spelling": casual_spelling,
                "likely_slang": slang_used,
                "unknown_tokens": len(unknown_tokens),
            },
            transform_trace=[
                {"name": "nfkc", "value": nfkc},
                {"name": "diacritic_fold", "value": folded},
                {"name": "punctuation_strip", "value": collapsed},
                {"name": "lexical_noise_map", "value": lexical},
            ],
            surface_features={
                "repeated_chars": repeated_chars,
                "casual_spelling": casual_spelling,
                "likely_slang": slang_used,
                "unknown_tokens": unknown_tokens,
                "repair_candidates": repair_candidates,
            },
            unknown_tokens=unknown_tokens,
            repair_candidates=repair_candidates,
            confidence=0.7 if forms else 0.0,
        )

    def _repair_tokens(self, words: list[str]) -> tuple[list[str], str, bool]:
        """Map noisy / misspelled tokens to canonical forms."""
        repaired: list[str] = []
        slang_used = False
        for w in words:
            bare = w.strip(".,!?;:\"'()[]{}").lower()
            if not bare:
                continue
            # Exact noisy / typo map first.
            canonical = self._noisy_map.get(bare) or self._typo_map.get(bare)
            if canonical:
                repaired.append(canonical)
                slang_used = True
                continue
            # Runtime lexeme memory next.
            if self._lexeme_memory is not None:
                lex = self._lexeme_memory.lookup_active(bare)
                if lex is not None:
                    repaired.append(lex.canonical)
                    continue
            # Similarity-based repair for short tokens.
            if len(bare) <= 6:
                match = self._best_match(bare)
                if match is not None and self._matcher.is_likely_repair(bare, match):
                    repaired.append(match)
                    slang_used = True
                    continue
            repaired.append(bare)
        return repaired, " ".join(repaired), slang_used

    def _best_match(self, word: str) -> str | None:
        best_score = 0.0
        best_word: str | None = None
        for known in self._known_words:
            score = self._matcher.similarity(word, known)
            if score > best_score:
                best_score = score
                best_word = known
        return best_word

    def _entity_names(self, words: list[str]) -> set[str]:
        """Return lowercase entity names detected by the optional NER tagger."""
        names: set[str] = set()
        if self._ner_tagger is None:
            return names
        try:
            for ent in self._ner_tagger.extract_entities(words):
                name = ent.get("text", "").lower().strip()
                if name:
                    names.add(name)
        except Exception:
            pass
        return names

    def _detect_unknown_tokens(self, words: list[str]) -> list[str]:
        unknowns: list[str] = []
        entity_names = self._entity_names(words)
        for w in words:
            bare = w.strip(".,!?;:\"'()[]{}").lower()
            if not bare:
                continue
            if bare.isdigit():
                continue
            if bare in self._known_words:
                continue
            if bare in self._noisy_map.values() or bare in self._typo_map.values():
                continue
            if self._lexeme_memory is not None and self._lexeme_memory.lookup_active(bare) is not None:
                continue
            if bare in entity_names:
                continue
            # Allow capitalized proper nouns (teachable as entity).
            if w and w[0].isupper() and len(bare) > 2:
                continue
            unknowns.append(bare)
        return unknowns

    def _detect_repair_candidates(self, words: list[str]) -> dict[str, str]:
        """Surface a map of noisy/misspelled token -> canonical candidate."""
        candidates: dict[str, str] = {}
        for w in words:
            bare = w.strip(".,!?;:\"'()[]{}").lower()
            if not bare:
                continue
            if bare in self._known_words:
                continue
            # Exact maps.
            if bare in self._noisy_map:
                candidates[bare] = self._noisy_map[bare]
                continue
            if bare in self._typo_map:
                candidates[bare] = self._typo_map[bare]
                continue
            # Similarity repair.
            if len(bare) <= 6:
                match = self._best_match(bare)
                if match is not None and self._matcher.is_likely_repair(bare, match):
                    candidates[bare] = match
        return candidates

    def learn_word(self, surface: str, canonical: str) -> None:
        """Add a new known word to the in-memory vocabulary at runtime."""
        self._known_words.add(canonical.lower())
        if self._lexeme_memory is not None:
            self._lexeme_memory.learn(surface, role="word", canonical=canonical)
