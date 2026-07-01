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
    tagger = NERTagger(dim=256)
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
    result = pipeline.run("Alice visited Paris on Monday", context_id="ctx")
    seg = result.semantic_event_graph
    assert seg is not None
    entity_ids = {ref.get("entity_id", ref.get("entity", "")) for ref in seg.entity_refs}
    assert "alice" in entity_ids, entity_ids
    assert "paris" in entity_ids, entity_ids
    assert "monday" in entity_ids, entity_ids


def test_learned_ner_extracts_multi_word_entities():
    store = Store(":memory:")
    registry = Registry()
    seed_registry(registry)
    seed_self_state(store)
    pipeline = Pipeline(store, registry)
    result = pipeline.run("Jane Doe visited New York and works at Google LLC", context_id="ctx")
    seg = result.semantic_event_graph
    assert seg is not None
    entity_ids = {ref.get("entity_id", ref.get("entity", "")) for ref in seg.entity_refs}
    assert "jane doe" in entity_ids, entity_ids
    assert "new york" in entity_ids, entity_ids
    assert "google llc" in entity_ids, entity_ids
