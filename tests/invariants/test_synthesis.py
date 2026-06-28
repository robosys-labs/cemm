import pytest
from cemm.synthesis.router import SynthesisRouter
from cemm.synthesis.template import TemplateStrategy
from cemm.synthesis.extractive import ExtractiveStrategy
from cemm.synthesis.verifier import SynthesisVerifier
from cemm.store.store import Store
from cemm.registry import Registry
from cemm.types.context_kernel import ContextKernel


class TestSynthesis:
    def test_template_strategy_can_handle(self):
        t = TemplateStrategy()
        assert t.can_handle({"template_key": "greeting"})
        assert not t.can_handle({})

    def test_template_greeting(self):
        t = TemplateStrategy()
        result = t.render(
            ContextKernel(id="test"), Store(":memory:"), Registry(),
            {"template_key": "greeting"},
        )
        assert result.success
        assert "Hello" in result.output

    def test_extractive_strategy_can_handle(self):
        e = ExtractiveStrategy()
        assert e.can_handle({"claim_ids": ["cl_001"]})
        assert not e.can_handle({})

    def test_router_selects_template_first(self):
        router = SynthesisRouter()
        kernel = ContextKernel(id="test")
        store = Store(":memory:")
        reg = Registry()
        strategy = router.select_strategy(kernel, store, reg, {"template_key": "greeting"})
        assert strategy == "template"

    def test_verifier_rejects_empty(self):
        verifier = SynthesisVerifier()
        ok, issues = verifier.verify("", [], [], ContextKernel(id="test"))
        assert not ok

    def test_verifier_accepts_valid(self):
        verifier = SynthesisVerifier()
        ok, issues = verifier.verify("Hello", ["cl_001"], [], ContextKernel(id="test"))
        assert ok
