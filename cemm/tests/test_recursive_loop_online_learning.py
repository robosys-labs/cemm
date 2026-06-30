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


def test_recursive_loop_runs_all_online_learning_updates():
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    loop = RecursiveLoop(pipeline, store, online_learner, inductor)

    from cemm.__main__ import seed_registry, seed_self_state
    seed_registry(registry)
    seed_self_state(store)

    calls = []
    for method_name in ("update_self_state", "update_source_trust", "update_operator_reliability", "update_ranking_weights"):
        if not hasattr(online_learner, method_name):
            continue
        original = getattr(online_learner, method_name)
        def make_capture(orig, name):
            def capture(*args, **kwargs):
                calls.append(name)
                return orig(*args, **kwargs)
            return capture
        setattr(online_learner, method_name, make_capture(original, method_name))

    loop.run_once("hello", context_id="ctx")
    assert "update_self_state" in calls
    assert "update_source_trust" in calls
    assert "update_operator_reliability" in calls
    assert "update_ranking_weights" in calls
