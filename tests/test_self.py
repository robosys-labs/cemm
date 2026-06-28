import pytest
from cemm.types.self_state import SelfState, InternalMode


class TestSelfState:
    def test_create_defaults(self):
        s = SelfState(id="self_1")
        assert s.name == "cemm"
        assert s.mode == InternalMode.ASSISTANT
        assert s.coherence == 1.0

    def test_mode_values(self):
        assert InternalMode.RESEARCHER.value == "researcher"
        assert InternalMode.REFLECTOR.value == "reflector"
