import pytest
from cemm.kernel.context_kernel_builder import ContextKernelBuilder
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
from cemm.types.context_kernel import Budget
import time


class TestContextKernelBuilder:
    def test_build_minimal(self):
        builder = ContextKernelBuilder()
        kernel = builder.build()
        assert kernel.id is not None
        assert kernel.time.bucket is not None
        assert kernel.budget.max_claims == 128

    def test_build_from_signal(self):
        now = time.time()
        signal = Signal(
            id="sig_001", kind=SignalKind.INPUT,
            source_id="user", source_type=SourceType.USER,
            content="hello", observed_at=now,
            context_id="ctx_001", salience=0.8, trust=0.8,
            permission=Permission.public(),
        )
        builder = ContextKernelBuilder()
        kernel = builder.from_signal(signal)
        assert kernel.id == "ctx_001"
        assert signal.id in kernel.memory.working_signal_ids

    def test_time_bucket_morning(self):
        import datetime
        ts = datetime.datetime(2026, 6, 27, 10, 30).timestamp()
        bucket = ContextKernelBuilder._compute_bucket(ts)
        assert bucket == "morning"

    def test_time_bucket_night(self):
        import datetime
        ts = datetime.datetime(2026, 6, 27, 23, 30).timestamp()
        bucket = ContextKernelBuilder._compute_bucket(ts)
        assert bucket == "night"
