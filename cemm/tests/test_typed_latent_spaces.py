from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.latent.encoder import LatentEncoder
from cemm.types.latent_space import LatentSpaceSpec, TypedLatents


def test_latent_space_specs_exist():
    encoder = LatentEncoder()
    for name in ("entity", "process", "state", "claim", "model", "context", "self", "memory", "action", "answer"):
        assert name in encoder.spaces
        assert isinstance(encoder.spaces[name], LatentSpaceSpec)



def test_encoder_namespaces_are_independent():
    encoder = LatentEncoder(dim=64)
    entity_vec = encoder.encode("entity", ["greeting"])
    process_vec = encoder.encode("process", ["greeting"])
    assert entity_vec != process_vec





def test_trace_typed_latents_round_trip_via_action_store():
    from cemm.store.store import Store
    from cemm.types.trace import Trace
    from cemm.types.latent_space import TypedLatents
    from cemm.types.action import Action, ActionKind, ActionStatus
    import time

    store = Store(":memory:")
    latents = TypedLatents(
        entity=[0.1] * 64,
        process=[0.2] * 64,
        state=[0.3] * 64,
        claim=[0.4] * 64,
        model=[0.5] * 64,
        context=[0.6] * 64,
        self=[0.7] * 64,
        memory=[0.8] * 64,
        action=[0.9] * 64,
        answer=[1.0] * 64,
    )
    trace = Trace(context_id="ctx", typed_latents=latents)
    action = Action(
        id="a1",
        kind=ActionKind.ANSWER,
        operator_model_id="op",
        status=ActionStatus.EXECUTED,
        trace=trace,
        created_at=time.time(),
    )
    store.actions.put(action)
    loaded = store.actions.get("a1")
    assert loaded is not None
    assert loaded.trace is not None
    assert loaded.trace.typed_latents is not None
    assert loaded.trace.typed_latents.entity == [0.1] * 64
    assert loaded.trace.typed_latents.answer == [1.0] * 64


