from __future__ import annotations

import os
import sys
import time
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
os.environ["CEMM_EXPORT_PATH"] = ""

from ...memory.durable_semantic_store import DurableSemanticStore


def test_golden_self_identity() -> None:
    """Store and retrieve a self-identity relation: "self attr_z val_q"."""
    store = DurableSemanticStore()
    store.add_relation(
        relation_key="attr_z",
        relation_family="self_identity",
        subject_entity_id="self",
        subject_surface="self",
        object_entity_id="val_q",
        object_surface="val_q",
        confidence=0.95,
    )

    frames = store.query_relations(subject_entity_id="self")
    assert len(frames) == 1, f"Expected 1 frame, got {len(frames)}"
    assert frames[0].relation_key == "attr_z"
    assert frames[0].object.entity_id == "val_q"
