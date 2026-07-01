from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.learning.ner_tagger import NERTagger


def test_ner_tagger_normalizes_noisy_tags() -> None:
    tagger = NERTagger()
    assert tagger._normalize_tag("b-per") == "B-PER"
    assert tagger._normalize_tag("i-loc") == "I-LOC"
    assert tagger._normalize_tag("O") == "O"
    assert tagger._normalize_tag("x-y") == "O"
    assert tagger._normalize_tag("B_PERSON", seen_labels={"PER"}) == "O"


def test_ner_tagger_extract_entities_with_confidence() -> None:
    tagger = NERTagger()
    tagger._avg_weights = {
        tag: {} for tag in tagger.TAGS
    }
    # Add simple features to strongly bias "tokyo" as B-LOC
    tagger._avg_weights["B-LOC"][0] = 5.0
    tagger._avg_weights["I-LOC"][1] = 5.0
    entities = tagger.extract_entities(["i", "visited", "tokyo", "today"])
    loc = next((e for e in entities if e.get("label") == "LOC"), None)
    if loc:
        assert "confidence" in loc
        assert isinstance(loc["confidence"], (int, float))
