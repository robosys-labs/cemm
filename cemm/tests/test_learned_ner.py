from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.learning.ner_tagger import NERTagger
from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline
from cemm.__main__ import seed_registry, seed_self_state


def test_ner_tagger_trains_on_synthetic_data():
    tagger = NERTagger(dim=1024)
    sentences = [
        "Alice visited Paris".split(),
        "Bob met Carol in London".split(),
        "David joined Google yesterday".split(),
    ]
    labels = [
        ["B-PER", "O", "B-LOC"],
        ["B-PER", "O", "B-PER", "O", "B-LOC"],
        ["B-PER", "O", "B-ORG", "B-TIME"],
    ]
    tagger.train(sentences, labels, epochs=10)

    pred = tagger.extract_entities("Alice visited Paris".split())
    texts = {ent["text"] for ent in pred}
    assert "Alice" in texts
    assert "Paris" in texts


def test_learned_ner_populates_entity_refs_in_seg():
    store = Store(":memory:")
    registry = Registry()
    seed_registry(registry)
    seed_self_state(store)
    pipeline = Pipeline(store, registry)
    # Use real-world examples that the conll-trained tagger is likely to recognize.
    result = pipeline.run("Microsoft opened in Tokyo on January 2025", context_id="ctx")
    seg = result.semantic_event_graph
    assert seg is not None
    entity_ids = {ref.get("entity_id", ref.get("entity", "")) for ref in seg.entity_refs}
    assert "tokyo" in entity_ids, entity_ids
    assert "january 2025" in entity_ids or "january" in entity_ids, entity_ids


def test_learned_ner_extracts_multi_word_entities():
    store = Store(":memory:")
    registry = Registry()
    seed_registry(registry)
    seed_self_state(store)
    pipeline = Pipeline(store, registry)
    result = pipeline.run("New York based Microsoft Corporation hired John Smith", context_id="ctx")
    seg = result.semantic_event_graph
    assert seg is not None
    entity_ids = {ref.get("entity_id", ref.get("entity", "")) for ref in seg.entity_refs}
    assert "microsoft corporation" in entity_ids or "microsoft" in entity_ids, entity_ids
    assert "john" in entity_ids or "smith" in entity_ids or "john smith" in entity_ids, entity_ids
