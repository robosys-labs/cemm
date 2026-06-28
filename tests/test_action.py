import pytest
from cemm.types.action import Action, ActionKind, ActionStatus
from cemm.types.trace import Trace


class TestAction:
    def test_create_minimal(self):
        a = Action(id="a1", kind=ActionKind.ANSWER, operator_model_id="op1")
        assert a.status == ActionStatus.PLANNED

    def test_action_kind_values(self):
        assert ActionKind.ABSTAIN.value == "abstain"
        assert ActionKind.REFLECT.value == "reflect"
