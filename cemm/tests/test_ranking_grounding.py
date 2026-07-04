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
from cemm.types.uol_graph import UOLGraph
from cemm.types.uol_atom import UOLAtom, UOLEdge
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



def test_grounding_populates_location_ids_for_location_roles() -> None:
    store = Store(":memory:")
    _put_entity(store, "lagos", "Lagos", "place", ["lagos"])
    graph = UOLGraph(
        id="seg",
        signal_id="s1",
        context_id="ctx",
        atoms={
            "lagos_atom": UOLAtom(id="lagos_atom", kind="entity", key="entity:lagos", surface="Lagos"),
            "src_atom": UOLAtom(id="src_atom", kind="process", key="process:request_weather", surface="request weather"),
        },
        edges=[
            UOLEdge(id="loc_edge", edge_type="has_role", source_id="src_atom", target_id="lagos_atom", features={"role": "location"}),
        ],
    )
    kernel = ContextKernelBuilder.from_signal(_sig("weather in Lagos"), turn_index=1)
    pipeline = GroundingPipeline(EntityResolver(store.entities), FrameEngine(store.claims))
    grounded = pipeline.run(graph, kernel)
    assert "lagos" in grounded.resolved_location_ids
