from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.learning.surface_tagger import SurfaceTagger, SEMANTIC_TAG_TO_ROLE
from cemm.learning.lexeme_memory import LexemeMemory


class TestSurfaceTagger:
    def test_unknown_lexeme_from_normalizer(self) -> None:
        tagger = SurfaceTagger()
        tags = tagger.tag(["the", "book", "mentions", "zibble"], unknown_tokens=["zibble"])
        assert tags[-1] == "B-UNKNOWN_LEXEME"

    def test_known_word_not_unknown(self) -> None:
        tagger = SurfaceTagger(known_words={"zibble"})
        tags = tagger.tag(["what", "is", "a", "zibble"], unknown_tokens=["zibble"])
        # Even though the normalizer listed zibble as unknown, the shared vocabulary says it is known.
        assert "B-UNKNOWN_LEXEME" not in tags

    def test_lexeme_memory_word_not_unknown(self) -> None:
        lexemes = LexemeMemory()
        lexemes.learn("zibble", role="word", maps_to="zibble")
        tagger = SurfaceTagger(lexeme_memory=lexemes)
        tags = tagger.tag(["what", "is", "a", "zibble"], unknown_tokens=["zibble"])
        assert "B-UNKNOWN_LEXEME" not in tags

    def test_process_word_tagged(self) -> None:
        tagger = SurfaceTagger()
        tags = tagger.tag(["remember", "the", "answer"])
        assert tags[0] == "B-PROCESS"

    def test_semantic_spans(self) -> None:
        tagger = SurfaceTagger()
        spans = tagger.extract_semantic_spans(["what", "is", "a", "zibble"], unknown_tokens=["zibble"])
        roles = {span["role"] for span in spans}
        assert "unknown_lexeme" in roles
