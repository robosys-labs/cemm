from __future__ import annotations
from cemm.types.signal import Signal, SignalKind, SourceType, FeedbackSignal
from cemm.types.permission import Permission
import time


class TestFeedbackSignal:
    def test_create_feedback_signal(self):
        signal = Signal(
            id="fb1", kind=SignalKind.FEEDBACK, source_id="user",
            source_type=SourceType.USER, content="Wrong answer",
            observed_at=time.time(), context_id="ctx1",
            salience=0.8, trust=0.5, permission=Permission.public(),
        )
        fb = FeedbackSignal.create(signal, "claim", "c1", rating=-1.0)
        assert fb.id == "fb1"
        assert fb.target_kind == "claim"
        assert fb.target_id == "c1"
        assert fb.rating == -1.0

    def test_signal_kind_set_to_feedback(self):
        signal = Signal(
            id="fb2", kind=SignalKind.INPUT, source_id="user",
            source_type=SourceType.USER, content="Fix this",
            observed_at=time.time(), context_id="ctx1",
            salience=0.8, trust=0.5, permission=Permission.public(),
        )
        fb = FeedbackSignal.create(signal, "action", "a1", rating=0.5)
        assert fb.signal.kind == SignalKind.FEEDBACK

    def test_correction_text(self):
        signal = Signal(
            id="fb3", kind=SignalKind.FEEDBACK, source_id="user",
            source_type=SourceType.USER, content="Actually it's PostgreSQL",
            observed_at=time.time(), context_id="ctx1",
            salience=0.8, trust=0.5, permission=Permission.public(),
        )
        fb = FeedbackSignal.create(signal, "entity", "e1",
                                   correction_text="PostgreSQL")
        assert fb.correction_text == "PostgreSQL"

    def test_target_kind_validation(self):
        signal = Signal(
            id="fb4", kind=SignalKind.FEEDBACK, source_id="user",
            source_type=SourceType.USER, content="ok",
            observed_at=time.time(), context_id="ctx1",
            salience=0.8, trust=0.5, permission=Permission.public(),
        )
        fb = FeedbackSignal.create(signal, "synthesis", "s1", rating=1.0)
        assert fb.target_kind == "synthesis"
