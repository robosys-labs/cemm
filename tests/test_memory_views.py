from cemm.retrieval.memory_views import MemoryViews
from cemm.store.store import Store
from cemm.types.context_kernel import ContextKernel


def test_working_memory_returns_dict():
    store = Store(":memory:")
    views = MemoryViews(store)
    kernel = ContextKernel(id="test")
    result = views.working_memory(kernel)
    assert "signals" in result
    assert "entities" in result
    assert "claims" in result


def test_uol_memory_returns_models():
    store = Store(":memory:")
    views = MemoryViews(store)
    result = views.uol_memory()
    assert isinstance(result, list)


def test_trust_memory_empty():
    store = Store(":memory:")
    views = MemoryViews(store)
    result = views.trust_memory()
    assert isinstance(result, list)
