from __future__ import annotations
import time
import uuid
from cemm.store.store import Store
from cemm.learning.inductor import Inductor
from cemm.types.action import Action, ActionKind, ActionStatus
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
from cemm.types.model import ModelKind, ModelStatus


def _make_signal(store: Store, kind: SignalKind, source_type: SourceType,
                  context_id: str, observed_at: float) -> str:
    sid = uuid.uuid4().hex[:16]
    sig = Signal(
        id=sid, kind=kind, source_id="test", source_type=source_type,
        content="test", observed_at=observed_at, context_id=context_id,
        salience=0.5, trust=0.5, permission=Permission.public(),
    )
    store.signals.put(sig)
    return sid


def _make_action(store: Store, kind: ActionKind, result_signal_id: str | None,
                  created_at: float) -> str:
    aid = uuid.uuid4().hex[:16]
    action = Action(
        id=aid, kind=kind, operator_model_id="test",
        result_signal_id=result_signal_id,
        status=ActionStatus.EXECUTED, created_at=created_at,
    )
    store.actions.put(action)
    return aid


class TestSequentialPatternInduction:
    def test_detects_repeated_action_signal_pattern(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=3)
        now = time.time()
        for i in range(5):
            sig_id = _make_signal(
                store, SignalKind.ACTION_RESULT, SourceType.ASSISTANT,
                f"ctx{i}", now - (5 - i) * 0.1,
            )
            _make_action(store, ActionKind.ASK, sig_id, now - (5 - i) * 0.1)

        candidates = inductor._find_sequential_patterns()
        assert len(candidates) == 1
        model = candidates[0]
        assert model.kind == ModelKind.CAUSAL_RULE
        assert model.name == "causal:ask->action_result"
        assert "action_kind:ask" in model.preconditions
        assert "signal_kind:action_result" in model.effects
        assert 0.0 < model.confidence <= 1.0

    def test_confidence_formula(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=2)
        now = time.time()
        for i in range(4):
            sig_id = _make_signal(
                store, SignalKind.ACTION_RESULT, SourceType.ASSISTANT,
                f"ctx{i}", now - (4 - i) * 0.1,
            )
            _make_action(store, ActionKind.ASK, sig_id, now - (4 - i) * 0.1)
        failure_sig_id = _make_signal(
            store, SignalKind.INPUT, SourceType.USER,
            "fail", now - 0.05,
        )
        _make_action(store, ActionKind.ASK, failure_sig_id, now - 0.05)

        candidates = inductor._find_sequential_patterns()
        assert len(candidates) == 1
        expected = 4 / (4 + 1)
        assert abs(candidates[0].confidence - expected) < 0.01

    def test_skips_below_threshold(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=5)
        now = time.time()
        for i in range(2):
            sig_id = _make_signal(
                store, SignalKind.ACTION_RESULT, SourceType.ASSISTANT,
                f"ctx{i}", now - (2 - i) * 0.1,
            )
            _make_action(store, ActionKind.ASK, sig_id, now - (2 - i) * 0.1)

        candidates = inductor._find_sequential_patterns()
        assert len(candidates) == 0

    def test_skips_already_active_rule(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=3)
        now = time.time()
        from cemm.types.model import Model
        existing = Model(
            id="existing_seq",
            kind=ModelKind.CAUSAL_RULE,
            name="causal:ask->action_result",
            description="Existing",
            preconditions=["action_kind:ask"],
            effects=["signal_kind:action_result"],
            confidence=0.9,
            status=ModelStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        store.models.put(existing)
        for i in range(5):
            sig_id = _make_signal(
                store, SignalKind.ACTION_RESULT, SourceType.ASSISTANT,
                f"ctx{i}", now - (5 - i) * 0.1,
            )
            _make_action(store, ActionKind.ASK, sig_id, now - (5 - i) * 0.1)

        candidates = inductor._find_sequential_patterns()
        assert len(candidates) == 0

    def test_detects_multiple_patterns(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=2)
        now = time.time()
        for i in range(3):
            sig_id = _make_signal(
                store, SignalKind.ACTION_RESULT, SourceType.ASSISTANT,
                f"ask{i}", now - (3 - i) * 0.1,
            )
            _make_action(store, ActionKind.ASK, sig_id, now - (3 - i) * 0.1)
        for i in range(3):
            sig_id = _make_signal(
                store, SignalKind.INPUT, SourceType.USER,
                f"ans{i}", now - (3 - i) * 0.1,
            )
            _make_action(store, ActionKind.ANSWER, sig_id, now - (3 - i) * 0.1)

        candidates = inductor._find_sequential_patterns()
        names = {c.name for c in candidates}
        assert "causal:ask->action_result" in names
        assert "causal:answer->input" in names

    def test_wired_into_maybe_induct(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=3)
        now = time.time()
        for i in range(5):
            sig_id = _make_signal(
                store, SignalKind.ACTION_RESULT, SourceType.ASSISTANT,
                f"ctx{i}", now - (5 - i) * 0.1,
            )
            _make_action(store, ActionKind.ASK, sig_id, now - (5 - i) * 0.1)

        candidates = inductor.maybe_induct()
        seq_candidates = [
            m for m in candidates
            if m.kind == ModelKind.CAUSAL_RULE
            and m.name.startswith("causal:")
        ]
        assert len(seq_candidates) == 1

    def test_ignores_actions_outside_5s_window(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=2)
        now = time.time()
        for i in range(3):
            sig_id = _make_signal(
                store, SignalKind.ACTION_RESULT, SourceType.ASSISTANT,
                f"ctx{i}", now,
            )
            _make_action(store, ActionKind.ASK, sig_id, now - 10)

        candidates = inductor._find_sequential_patterns()
        assert len(candidates) == 0


class TestSlotCompletionInduction:
    def test_detects_generic_response_pattern(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=3)
        now = time.time()
        for i in range(5):
            _make_signal(
                store, SignalKind.ACTION_RESULT, SourceType.ASSISTANT,
                f"ctx{i}", now - (5 - i) * 0.1,
            )
            _make_signal(
                store, SignalKind.INPUT, SourceType.USER,
                f"ctx{i}", now - (5 - i) * 0.1 + 0.05,
            )

        candidates = inductor._find_slot_completion()
        assert len(candidates) == 1
        model = candidates[0]
        assert model.kind == ModelKind.CONTEXT_RULE
        assert model.name == "completion:generic_response"
        assert 0.0 < model.confidence <= 1.0

    def test_detects_entity_completion_pattern(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=2)
        now = time.time()
        for i in range(3):
            ar_id = _make_signal(
                store, SignalKind.ACTION_RESULT, SourceType.ASSISTANT,
                f"ctx{i}", now - (3 - i) * 0.1,
            )
            user_id = uuid.uuid4().hex[:16]
            from cemm.types.signal import ObservationSemantics
            user_sig = Signal(
                id=user_id, kind=SignalKind.INPUT,
                source_id="test", source_type=SourceType.USER,
                content=f"answer {i}", observed_at=now - (3 - i) * 0.1 + 0.05,
                context_id=f"ctx{i}", salience=0.5, trust=0.5,
                permission=Permission.public(),
                observation_semantics=ObservationSemantics(
                    speech_act="answer", target_entity_id="entity_pg",
                ),
            )
            store.signals.put(user_sig)

        candidates = inductor._find_slot_completion()
        assert len(candidates) == 1
        assert candidates[0].name == "completion:entity_completion"

    def test_skips_internal_signals_between_action_result_and_user(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=3)
        now = time.time()
        for i in range(5):
            _make_signal(
                store, SignalKind.ACTION_RESULT, SourceType.ASSISTANT,
                f"ctx{i}", now - (5 - i) * 0.1,
            )
            _make_signal(
                store, SignalKind.TRACE, SourceType.SYSTEM,
                f"ctx{i}", now - (5 - i) * 0.1 + 0.02,
            )
            _make_signal(
                store, SignalKind.MEMORY_UPDATE, SourceType.SYSTEM,
                f"ctx{i}", now - (5 - i) * 0.1 + 0.04,
            )
            _make_signal(
                store, SignalKind.INPUT, SourceType.USER,
                f"ctx{i}", now - (5 - i) * 0.1 + 0.06,
            )

        candidates = inductor._find_slot_completion()
        assert len(candidates) == 1

    def test_skips_non_user_followup(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=3)
        now = time.time()
        for i in range(5):
            _make_signal(
                store, SignalKind.ACTION_RESULT, SourceType.ASSISTANT,
                f"ctx{i}", now - (5 - i) * 0.1,
            )
            _make_signal(
                store, SignalKind.TRACE, SourceType.SYSTEM,
                f"ctx{i}", now - (5 - i) * 0.1 + 0.05,
            )

        candidates = inductor._find_slot_completion()
        assert len(candidates) == 0

    def test_skips_outside_5s_window(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=3)
        now = time.time()
        for i in range(5):
            _make_signal(
                store, SignalKind.ACTION_RESULT, SourceType.ASSISTANT,
                f"ctx{i}", now - (5 - i) * 0.1,
            )
            _make_signal(
                store, SignalKind.INPUT, SourceType.USER,
                f"ctx{i}", now - (5 - i) * 0.1 + 6.0,
            )

        candidates = inductor._find_slot_completion()
        assert len(candidates) == 0

    def test_skips_below_threshold(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=5)
        now = time.time()
        for i in range(2):
            _make_signal(
                store, SignalKind.ACTION_RESULT, SourceType.ASSISTANT,
                f"ctx{i}", now - (2 - i) * 0.1,
            )
            _make_signal(
                store, SignalKind.INPUT, SourceType.USER,
                f"ctx{i}", now - (2 - i) * 0.1 + 0.05,
            )

        candidates = inductor._find_slot_completion()
        assert len(candidates) == 0

    def test_wired_into_maybe_induct(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=3)
        now = time.time()
        for i in range(5):
            _make_signal(
                store, SignalKind.ACTION_RESULT, SourceType.ASSISTANT,
                f"ctx{i}", now - (5 - i) * 0.1,
            )
            _make_signal(
                store, SignalKind.INPUT, SourceType.USER,
                f"ctx{i}", now - (5 - i) * 0.1 + 0.05,
            )

        candidates = inductor.maybe_induct()
        completion_candidates = [
            m for m in candidates
            if m.kind == ModelKind.CONTEXT_RULE
            and m.name.startswith("completion:generic")
        ]
        assert len(completion_candidates) == 1
