from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.kernel.context_kernel_builder import ContextKernelBuilder
from cemm.kernel.grounding import GroundingPipeline
from cemm.kernel.entity_resolver import EntityResolver
from cemm.kernel.frame_engine import FrameEngine
from cemm.retrieval.ranker import Ranker
from cemm.store.store import Store
from cemm.types.claim import Claim
from cemm.types.entity import Entity, EntityType
from cemm.types.permission import Permission
from cemm.types.semantic_event_graph import SemanticEventGraph
from cemm.types.signal import Signal, SignalKind, SourceType


def _sig(text: str) -> Signal:
    return Signal(
        id="s1", kind=SignalKind.INPUT, source_id="user", source_type=SourceType.USER,
        content=text, observed_at=time.time(), context_id="ctx", salience=0.5, trust=0.8,
        permission=Permission.public(),
    )


def _put_entity(store: Store, entity_id: str, name: str, type_name: str, aliases: list[str] | None = None) -> None:
    now = time.time()
    store.entities.put(Entity(
        id=entity_id,
        type=EntityType(type_name),
        name=name,
        aliases=aliases or [],
        confidence=0.9,
        created_from_signal_id="",
        created_at=now,
        updated_at=now,
    ))


def test_ranking_prefers_claims_overlapping_graph_entities() -> None:
    store = Store(":memory:")
    _put_entity(store, "user", "user", "person", ["user"])
    _put_entity(store, "self_main", "CEMM", "system", ["cemm"])
    store.claims.put(Claim(
        id="claim_user_likes", subject_entity_id="user", predicate="likes", object_value="coffee",
        source_id="user", permission=Permission.public(), confidence=0.8, trust=0.8, salience=0.5,
    ))
    store.claims.put(Claim(
        id="claim_self_name", subject_entity_id="self_main", predicate="name", object_value="CEMM",
        source_id="seed", permission=Permission.public(), confidence=0.9, trust=0.9, salience=0.6,
    ))
    kernel = ContextKernelBuilder.from_signal(_sig("who are you"), turn_index=1)
    # Add self_main entity ref to graph so it overlaps with self claim
    graph = SemanticEventGraph(
        id="seg", source_signal_ids=["s1"], context_id="ctx", confidence=0.6,
        entity_refs=[{"entity_id": "self_main", "name": "CEMM", "role": "target"}],
        processes=[{"frame_key": "self_identity_query"}],
    )
    claims = list(store.claims.find_active(limit=100))
    ranked = Ranker().rank_claims(claims, kernel, graph=graph)
    top = ranked[0][0]
    assert top.subject_entity_id == "self_main"


def test_grounding_populates_location_ids_for_location_roles() -> None:
    store = Store(":memory:")
    _put_entity(store, "lagos", "Lagos", "place", ["lagos"])
    graph = SemanticEventGraph(
        id="seg", source_signal_ids=["s1"], context_id="ctx", confidence=0.5,
        entity_refs=[{"entity_id": "lagos", "name": "Lagos", "role": "location"}],
        processes=[{"frame_key": "request_weather"}],
    )
    kernel = ContextKernelBuilder.from_signal(_sig("weather in Lagos"), turn_index=1)
    pipeline = GroundingPipeline(EntityResolver(store.entities), FrameEngine(store.claims))
    grounded = pipeline.run(graph, kernel)
    assert "lagos" in grounded.resolved_location_ids
