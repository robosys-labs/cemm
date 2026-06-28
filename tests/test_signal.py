import pytest
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
import time


class TestSignal:
    def test_create_basic(self):
        s = Signal(
            id="s1", kind=SignalKind.INPUT,
            source_id="u1", source_type=SourceType.USER,
            content="test", observed_at=time.time(),
            context_id="c1", salience=0.5, trust=0.8,
            permission=Permission.public(),
        )
        assert s.id == "s1"
        assert s.version == "erca.signal.v1"

    def test_kind_values(self):
        assert SignalKind.INPUT.value == "input"
        assert SignalKind.SIMULATION_RESULT.value == "simulation_result"
        assert SignalKind.REFLECTION.value == "reflection"
