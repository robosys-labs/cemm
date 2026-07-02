from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.kernel.text_normalizer import TextNormalizer, WordSimilarityMatcher
from cemm.learning.lexeme_memory import LexemeMemory


class TestWordSimilarityMatcher:
    def test_exact_match(self) -> None:
        matcher = WordSimilarityMatcher()
        assert matcher.similarity("hello", "hello") == 1.0

    def test_typo_repair(self) -> None:
        matcher = WordSimilarityMatcher()
        # 4+ char words can be repaired by similarity.
        assert matcher.is_likely_repair("beautful", "beautiful")
        assert not matcher.is_likely_repair("xyz", "the")


class TestTextNormalizer:
    def test_loads_vocab_from_json(self) -> None:
        normalizer = TextNormalizer()
        assert "the" in normalizer._known_words
        assert normalizer._noisy_map.get("u") == "you"
        assert normalizer._typo_map.get("teh") == "the"

    def test_noisy_word_repair(self) -> None:
        normalizer = TextNormalizer()
        signal = normalizer.normalize("u going 2day")
        assert "you going today" in signal.normalized_forms
        assert signal.surface_features["likely_slang"] is True

    def test_typo_repair(self) -> None:
        normalizer = TextNormalizer()
        signal = normalizer.normalize("teh quick brown fox")
        assert "the" in signal.canonical_form
        assert signal.surface_features["casual_spelling"] is True

    def test_unknown_token_detection(self) -> None:
        normalizer = TextNormalizer()
        signal = normalizer.normalize("what is a zibble")
        assert "zibble" in signal.unknown_tokens

    def test_runtime_lexeme_memory_expands_vocabulary(self) -> None:
        lexemes = LexemeMemory()
        lexemes.learn("zibble", role="word", maps_to="zibble")
        normalizer = TextNormalizer(lexeme_memory=lexemes)
        signal = normalizer.normalize("what is a zibble")
        assert "zibble" not in signal.unknown_tokens

    def test_proper_noun_not_unknown(self) -> None:
        normalizer = TextNormalizer()
        signal = normalizer.normalize("My name is Alice")
        assert "alice" not in signal.unknown_tokens

    def test_repair_candidates(self) -> None:
        normalizer = TextNormalizer()
        signal = normalizer.normalize("teh cat")
        assert signal.repair_candidates.get("teh") == "the"
