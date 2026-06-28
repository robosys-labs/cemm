import pytest
from cemm.causal.inference import CausalInference
from cemm.causal.simulation import SimulationEngine
from cemm.store.store import Store
from cemm.types.model import Model, ModelKind, ModelStatus
from cemm.types.claim import Claim
from cemm.types.context_kernel import ContextKernel


class TestCausalInference:
    def test_predict_returns_list(self):
        store = Store(":memory:")
        inference = CausalInference(store)
        kernel = ContextKernel(id="test")
        results = inference.predict("delete_file", [], kernel)
        assert isinstance(results, list)

    def test_transitive_closure_bounded(self):
        store = Store(":memory:")
        inference = CausalInference(store)
        kernel = ContextKernel(id="test")
        results = inference.transitive_closure(["cl_001"], kernel, max_depth=3)
        assert isinstance(results, list)


class TestSimulationEngine:
    def test_simulate_returns_result(self):
        store = Store(":memory:")
        engine = SimulationEngine(store)
        kernel = ContextKernel(id="test")
        result = engine.simulate("save_file", kernel)
        assert result.signal_id is not None
        assert isinstance(result.predicted_claims, list)
