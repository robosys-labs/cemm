from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

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
from cemm.__main__ import seed_registry, seed_self_state, seed_causal_models, process_input


def _setup():
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)
    seed_registry(registry)
    seed_self_state(store)
    seed_causal_models(store)
    for op in [AnswerOperator(), AskOperator(), RememberOperator(), AbstainOperator()]:
        op_registry.register(op)
    return store, registry, op_registry, pipeline, online_learner, recursive_loop


def test_causal_inference_seeds_active_model():
    store = Store(":memory:")
    from cemm.types.model import ModelKind, ModelStatus
    seed_causal_models(store)
    models = store.models.find_by_kind(ModelKind.CAUSAL_RULE.value, ModelStatus.ACTIVE.value)
    assert models
    assert any(m.id == "causal_rain_flooding" for m in models)


def test_causal_inference_populates_predictions():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    # A causal input should trigger CausalInference and populate predictions
    output = process_input("rain causes flooding", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert output is not None
    result = recursive_loop._last_result
    assert result is not None
    assert result.inference_packet is not None
    assert any("flood" in p.get("predicate", "").lower() for p in result.inference_packet.predictions), result.inference_packet.predictions


def test_simulation_runs_for_causal_input():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    output = process_input("rain causes flooding", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    result = recursive_loop._last_result
    assert result is not None
    assert result.semantic_event_graph is not None
    assert result.semantic_event_graph.causal_edges
    assert result.inference_packet is not None
    assert result.inference_packet.predictions


def test_multiple_seed_causal_models_exist():
    store = Store(":memory:")
    from cemm.types.model import ModelKind, ModelStatus
    seed_causal_models(store)
    models = store.models.find_by_kind(ModelKind.CAUSAL_RULE.value, ModelStatus.ACTIVE.value)
    assert len(models) >= 4
    ids = {m.id for m in models}
    assert "causal_rain_flooding" in ids
    assert "causal_heat_melt" in ids
    assert "causal_study_pass" in ids
    assert "causal_exercise_energy" in ids


def test_study_causal_model_produces_predictions():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    output = process_input("studying causes passing the exam", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert output is not None
    result = recursive_loop._last_result
    assert result is not None
    assert result.inference_packet is not None
    assert any("pass" in p.get("predicate", "").lower() for p in result.inference_packet.predictions), result.inference_packet.predictions


def test_causal_model_ref_matches_input_semantics():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    output = process_input("heat causes melting", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert output is not None
    result = recursive_loop._last_result
    assert result is not None
    assert result.semantic_event_graph is not None
    assert "causal_heat_melt" in result.semantic_event_graph.model_refs, result.semantic_event_graph.model_refs
    assert result.inference_packet is not None
    assert any("melt" in p.get("predicate", "").lower() for p in result.inference_packet.predictions), result.inference_packet.predictions


def test_learned_causal_model_is_auto_promoted():
    store = Store(":memory:")
    registry = Registry()
    seed_registry(registry)
    seed_self_state(store)
    import time
    from cemm.types.claim import Claim, ClaimStatus
    from cemm.types.entity import Entity, EntityType
    from cemm.types.permission import Permission
    from cemm.learning.inductor import Inductor
    from cemm.learning.online import OnlineLearner
    from cemm.kernel.recursive_loop import RecursiveLoop
    from cemm.types.model import ModelKind, ModelStatus

    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    inductor.set_threshold(3)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)

    store.entities.put(Entity(id="user", type=EntityType.PERSON, name="user", aliases=[], confidence=1.0, created_from_signal_id="test", created_at=time.time(), updated_at=time.time()))
    for i in range(3):
        claim = Claim(
            id=f"c{i}",
            subject_entity_id="user",
            predicate="ate_sugar",
            object_value="hyper",
            object_entity_id="hyper",
            source_id="test",
            qualifiers={"outcome": "success"},
            confidence=0.9,
            trust=0.9,
            status=ClaimStatus.ACTIVE,
            observed_at=time.time(),
            permission=Permission.public(),
        )
        store.claims.put(claim)

    recursive_loop._run_induction(None)

    active = store.models.find_by_kind(ModelKind.CAUSAL_RULE.value, ModelStatus.ACTIVE.value)
    inducted = [m for m in active if m.name == "ate_sugar"]
    assert inducted, f"No active inducted causal model found among {active!r}"


def test_narrative_causal_pattern_is_discovered_and_promoted():
    store = Store(":memory:")
    registry = Registry()
    seed_registry(registry)
    seed_self_state(store)
    import time
    from cemm.types.permission import Permission
    from cemm.types.signal import Signal, SignalKind, SourceType
    from cemm.learning.inductor import Inductor
    from cemm.learning.online import OnlineLearner
    from cemm.kernel.recursive_loop import RecursiveLoop
    from cemm.types.model import ModelKind, ModelStatus

    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    inductor.set_threshold(3)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)

    for i in range(3):
        signal = Signal(
            id=f"s{i}",
            kind=SignalKind.INPUT,
            source_id="test",
            source_type=SourceType.USER,
            content="exercise leads to energy",
            observed_at=time.time(),
            context_id="ctx",
            salience=0.8,
            trust=0.9,
            permission=Permission.public(),
        )
        store.signals.put(signal)

    recursive_loop._run_induction(None)

    active = store.models.find_by_kind(ModelKind.CAUSAL_RULE.value, ModelStatus.ACTIVE.value)
    inducted = [m for m in active if "exercise" in m.name and "energy" in m.name]
    assert inducted, f"No active narrative causal model found among {active!r}"
