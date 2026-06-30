from cemm.kernel.invariant_guard import InvariantGuard
from cemm.types.context_kernel import ContextKernel


def test_recursive_budget_check():
    from cemm.store.store import Store
    from cemm.registry import Registry
    from cemm.kernel.pipeline import Pipeline
    from cemm.learning.online import OnlineLearner
    from cemm.learning.inductor import Inductor
    from cemm.kernel.recursive_loop import RecursiveLoop
    store = Store(":memory:")
    reg = Registry()
    pipeline = Pipeline(store, reg)
    learner = OnlineLearner(store.source_trust, store.self_store, store.claims)
    inductor = Inductor(store)
    loop = RecursiveLoop(pipeline, store, learner, inductor)
    kernel, signals, actionable = loop.run_once("test", "inv_rec")
    assert kernel is not None
    guard = InvariantGuard()
    guard.reset()
    guard.check_recursive_budget(kernel, 0)
    errors = guard.assert_no_errors()
    assert len(errors) == 0


def test_invariant_guard_resets():
    guard = InvariantGuard()
    guard.reset()
    assert len(guard.errors) == 0
