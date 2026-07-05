from __future__ import annotations

import os
import sys
import time
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
os.environ["CEMM_EXPORT_PATH"] = ""

from ...memory.durable_semantic_store import DurableSemanticStore
from ...learning.memory_patch_compiler import MemoryPatchCompiler
from ...learning.patch_validator import PatchValidator
from ...learning.patch_committer import PatchCommitter
from ...store.store import Store


def _query_by_domain(store: DurableSemanticStore, domain: str) -> list:
    domain = str(domain)
    return [
        r for r in store.all_relations()
        if r.qualifiers.get("domain") == domain
    ]


def test_golden_social_suppression() -> None:
    """Verify domain-scoped suppression: private relation hidden from public scope."""
    store = DurableSemanticStore()

    rec_private = store.add_relation(
        relation_key="rel_b",
        relation_family="social_test",
        subject_concept_id="entity_a",
        object_concept_id="entity_c",
    )
    rec_private.qualifiers["domain"] = "domain_private"

    rec_public = store.add_relation(
        relation_key="rel_b",
        relation_family="social_test",
        subject_concept_id="entity_a",
        object_concept_id="entity_d",
    )
    rec_public.qualifiers["domain"] = "domain_public"

    all_relations = store.all_relations()
    assert len(all_relations) == 2, f"Expected 2 relations, got {len(all_relations)}"

    public_relations = _query_by_domain(store, "domain_public")
    assert len(public_relations) == 1
    assert public_relations[0].object_concept_id == "entity_d"

    private_relations = _query_by_domain(store, "domain_private")
    assert len(private_relations) == 1
    assert private_relations[0].object_concept_id == "entity_c"

    suppressed_ids = {r.record_id for r in all_relations} - {r.record_id for r in public_relations}
    assert len(suppressed_ids) == 1
    assert list(suppressed_ids)[0] == rec_private.record_id
