from cemm.kernel.recursive_loop import RecursiveLoop
from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline
from cemm.learning.online import OnlineLearner
from cemm.learning.inductor import Inductor

def test_recursive_loop_creates_kernel():
    store = Store(":memory:")
    reg = Registry()
    pipeline = Pipeline(store, reg)
    learner = OnlineLearner(store.source_trust, store.self_store, store.claims)
    inductor = Inductor(store)
    loop = RecursiveLoop(pipeline, store, learner, inductor)
    kernel, signals, actionable = loop.run_once("hello", "test_rec")
    assert kernel is not None
