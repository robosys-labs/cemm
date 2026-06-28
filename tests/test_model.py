import pytest
from cemm.types.model import Model, ModelKind, ModelStatus


class TestModel:
    def test_create_minimal(self):
        m = Model(id="m1", kind=ModelKind.PREDICATE, name="test", description="")
        assert m.status == ModelStatus.CANDIDATE

    def test_model_kind_values(self):
        assert ModelKind.CAUSAL_RULE.value == "causal_rule"
        assert ModelKind.INDUCTOR.value == "inductor"
