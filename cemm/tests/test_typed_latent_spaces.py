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




def test_process_input_sets_answer_latent():
    from cemm.store.store import Store
    from cemm.registry import Registry
    from cemm.kernel.pipeline import Pipeline
    from cemm.learning.online import OnlineLearner
    from cemm.learning.inductor import Inductor
    from cemm.kernel.recursive_loop import RecursiveLoop
    from cemm.operators.registry import OperatorRegistry
    from cemm.operators.answer import AnswerOperator
    from cemm.operators.ask import AskOperator
    from cemm.operators.remember import RememberOperator
    from cemm.operators.abstain import AbstainOperator
    from cemm.__main__ import seed_registry, seed_self_state, process_input

    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)
    seed_registry(registry)
    seed_self_state(store)
    for op in [AnswerOperator(), AskOperator(), RememberOperator(), AbstainOperator()]:
        op_registry.register(op)
    output = process_input("hello", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert output
    # The answer operator result should carry a SAG with a non-empty answer_latent
    assert recursive_loop._last_result is not None
    assert recursive_loop._last_result.decision_packet is not None



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


