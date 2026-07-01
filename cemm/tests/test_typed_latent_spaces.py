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


def test_encoder_produces_fixed_dim_vectors():
    encoder = LatentEncoder(dim=64)
    vec = encoder.encode("entity", ["user", "self_main"])
    assert len(vec) == 64
    assert any(v != 0 for v in vec)


def test_encoder_namespaces_are_independent():
    encoder = LatentEncoder(dim=64)
    entity_vec = encoder.encode("entity", ["greeting"])
    process_vec = encoder.encode("process", ["greeting"])
    assert entity_vec != process_vec


def test_encode_typed_returns_all_spaces():
    encoder = LatentEncoder(dim=64)
    latents = encoder.encode_typed(
        entity_ids=["user"],
        process_keys=["greeting"],
        state_keys=["happy"],
        claim_tuples=[("likes", "coffee")],
        model_keys=["uol_0"],
        context_id="ctx",
        self_mode="assistant",
        memory_claim_ids=["c1"],
        action_kind="answer",
        answer_intent="answer",
        answer_claim_ids=["c1"],
    )
    assert isinstance(latents, TypedLatents)
    assert len(latents.entity) == 64
    assert len(latents.answer) == 64


def test_answer_encoder_populates_answer_latent():
    encoder = LatentEncoder(dim=64)
    vec = encoder.encode_answer(
        intent="answer",
        selected_claim_ids=["c1"],
        selected_model_ids=["m1"],
    )
    assert len(vec) == 64
    assert any(v != 0 for v in vec)


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


def test_trace_contains_full_typed_latents(tmp_path, monkeypatch):
    import os
    import json
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

    export_file = tmp_path / "export.jsonl"
    monkeypatch.setenv("CEMM_EXPORT_PATH", str(export_file))

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
    assert export_file.exists()
    records = [json.loads(line) for line in export_file.read_text().splitlines()]
    full_turn = next((r for r in records if r.get("task_type") == "full_turn_export"), None)
    assert full_turn is not None
    trace = full_turn["payload"]["trace"]
    typed_latents = trace["typed_latents"]
    assert typed_latents is not None
    assert len(typed_latents["answer"]) == 64
    assert len(typed_latents["entity"]) == 64
    assert len(typed_latents["process"]) == 64
    assert len(typed_latents["self"]) == 64
