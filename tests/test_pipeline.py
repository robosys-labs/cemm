import pytest
from cemm.kernel.pipeline import Pipeline
from cemm.store.store import Store
from cemm.registry import Registry


class TestPipeline:
    def test_run_returns_result(self):
        store = Store(":memory:")
        reg = Registry()
        pipeline = Pipeline(store, reg)
        result = pipeline.run("Hello, world!")
        assert result.kernel is not None
        assert len(result.signals) >= 1

    def test_run_with_context_id(self):
        store = Store(":memory:")
        reg = Registry()
        pipeline = Pipeline(store, reg)
        result = pipeline.run("Test", context_id="fixed_ctx")
        assert result.kernel.id == "fixed_ctx"

    def test_run_stores_signal(self):
        store = Store(":memory:")
        reg = Registry()
        pipeline = Pipeline(store, reg)
        pipeline.run("Save me")
        assert store.signals.count() >= 1
