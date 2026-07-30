"""Tests for typed dialogue obligations and goal arbitration.

Clarification, learning answers, requested evidence, and pending operation
resolution use frozen ``DialogueObligation`` records with source query,
expected semantic answer contract, expiry, and completion receipt.  Only one
learning obligation may exist; unrelated dialogue cannot accidentally consume
it.  ``GoalArbiter`` selects among verified goals/obligations by policy; a UI
intent label is derived afterward and has no control authority.
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.dialogue import (
    DialogueObligation,
    DialogueObligationManager,
    GoalArbiter,
    GoalSelection,
)
from cemm_authoritative_hybrid.persistence import Obligation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def obligation_manager():
    return DialogueObligationManager()


@pytest.fixture
def goal_arbiter(linked_authority):
    return GoalArbiter(linked_authority, RuntimeConfig.release())


def _obligation(
    *,
    kind: str = "clarification",
    ref: str = "obligation:1",
    source_query_ref: str = "query:1",
    expected_answer_contract_ref: str = "contract:answer:1",
    expiry: int = 10,
    completion_receipt_ref: str | None = None,
) -> DialogueObligation:
    return DialogueObligation(
        obligation_ref=ref,
        kind=kind,  # type: ignore[arg-type]
        source_query_ref=source_query_ref,
        expected_answer_contract_ref=expected_answer_contract_ref,
        expiry=expiry,
        completion_receipt_ref=completion_receipt_ref,
    )


# ---------------------------------------------------------------------------
# Frozen obligation records
# ---------------------------------------------------------------------------


def test_dialogue_obligation_is_frozen():
    ob = _obligation()
    with pytest.raises(Exception):
        ob.kind = "evidence_request"  # type: ignore[misc]


def test_dialogue_obligation_carries_source_query_and_contract():
    ob = _obligation(
        source_query_ref="query:who",
        expected_answer_contract_ref="contract:name",
        expiry=5,
    )
    assert ob.source_query_ref == "query:who"
    assert ob.expected_answer_contract_ref == "contract:name"
    assert ob.expiry == 5
    assert ob.completion_receipt_ref is None


@pytest.mark.parametrize(
    "kind",
    ["clarification", "learning_answer", "evidence_request", "operation_resolution"],
)
def test_dialogue_obligation_accepts_typed_kinds(kind):
    ob = _obligation(kind=kind)
    assert ob.kind == kind


# ---------------------------------------------------------------------------
# Obligation manager: add / pending / fulfill
# ---------------------------------------------------------------------------


def test_pending_returns_unfulfilled_obligations(obligation_manager):
    obligation_manager.add(_obligation(ref="ob:a"))
    obligation_manager.add(_obligation(ref="ob:b"))
    pending = obligation_manager.pending()
    assert len(pending) == 2
    refs = {ob.obligation_ref for ob in pending}
    assert refs == {"ob:a", "ob:b"}


def test_fulfill_marks_obligation_with_completion_receipt(obligation_manager):
    obligation_manager.add(_obligation(ref="ob:a"))
    obligation_manager.fulfill("ob:a", "receipt:done")
    pending = obligation_manager.pending()
    assert pending == ()
    fulfilled = obligation_manager.get("ob:a")
    assert fulfilled is not None
    assert fulfilled.completion_receipt_ref == "receipt:done"


def test_fulfill_unknown_obligation_raises(obligation_manager):
    with pytest.raises(KeyError):
        obligation_manager.fulfill("ob:missing", "receipt:done")


def test_get_returns_none_for_unknown(obligation_manager):
    assert obligation_manager.get("ob:missing") is None


# ---------------------------------------------------------------------------
# Only one learning obligation may exist
# ---------------------------------------------------------------------------


def test_only_one_learning_obligation_may_exist(obligation_manager):
    obligation_manager.add(_obligation(ref="ob:learn-1", kind="learning_answer"))
    with pytest.raises(ValueError):
        obligation_manager.add(
            _obligation(ref="ob:learn-2", kind="learning_answer")
        )


def test_non_learning_obligations_coexist(obligation_manager):
    obligation_manager.add(_obligation(ref="ob:clar", kind="clarification"))
    obligation_manager.add(
        _obligation(ref="ob:evid", kind="evidence_request")
    )
    obligation_manager.add(
        _obligation(ref="ob:op", kind="operation_resolution")
    )
    assert len(obligation_manager.pending()) == 3


def test_learning_obligation_alongside_non_learning(obligation_manager):
    obligation_manager.add(_obligation(ref="ob:clar", kind="clarification"))
    obligation_manager.add(
        _obligation(ref="ob:learn", kind="learning_answer")
    )
    assert obligation_manager.has_learning_obligation()
    assert len(obligation_manager.pending()) == 2


# ---------------------------------------------------------------------------
# Unrelated dialogue cannot accidentally consume a learning obligation
# ---------------------------------------------------------------------------


def test_fulfilling_non_learning_does_not_consume_learning(obligation_manager):
    obligation_manager.add(_obligation(ref="ob:learn", kind="learning_answer"))
    obligation_manager.add(_obligation(ref="ob:clar", kind="clarification"))
    # Fulfilling the clarification must not affect the learning obligation.
    obligation_manager.fulfill("ob:clar", "receipt:clar-done")
    assert obligation_manager.has_learning_obligation()
    learn = obligation_manager.get("ob:learn")
    assert learn is not None
    assert learn.completion_receipt_ref is None


def test_fulfilled_learning_allows_new_learning(obligation_manager):
    obligation_manager.add(_obligation(ref="ob:learn-1", kind="learning_answer"))
    obligation_manager.fulfill("ob:learn-1", "receipt:done")
    # A new learning obligation may be added once the prior is fulfilled.
    obligation_manager.add(_obligation(ref="ob:learn-2", kind="learning_answer"))
    assert obligation_manager.has_learning_obligation()


# ---------------------------------------------------------------------------
# Goal arbitration
# ---------------------------------------------------------------------------


def _persistence_obligation(
    *, ref: str = "ob:1", priority: float = 1.0, satisfied: bool = False
) -> Obligation:
    return Obligation(
        obligation_ref=ref,
        kind="clarification",
        source_ref="query:1",
        target_ref="contract:1",
        priority=priority,
        satisfied=satisfied,
        blockers=(),
    )


def test_goal_arbiter_prefers_obligation_over_goal(goal_arbiter):
    selection = goal_arbiter.select(
        goals=("goal:explore",),
        obligations=(_persistence_obligation(ref="ob:1"),),
    )
    assert selection.selected_obligation_ref == "ob:1"
    assert selection.selected_goal_ref is None
    assert selection.ui_intent_label == "obligation:fulfill"


def test_goal_arbiter_selects_higher_priority_obligation(goal_arbiter):
    selection = goal_arbiter.select(
        goals=(),
        obligations=(
            _persistence_obligation(ref="ob:low", priority=1.0),
            _persistence_obligation(ref="ob:high", priority=5.0),
        ),
    )
    assert selection.selected_obligation_ref == "ob:high"


def test_goal_arbiter_ignores_satisfied_obligations(goal_arbiter):
    selection = goal_arbiter.select(
        goals=("goal:explore",),
        obligations=(_persistence_obligation(ref="ob:done", satisfied=True),),
    )
    assert selection.selected_obligation_ref is None
    assert selection.selected_goal_ref == "goal:explore"
    assert selection.ui_intent_label == "goal:pursue"


def test_goal_arbiter_idle_when_nothing_pending(goal_arbiter):
    selection = goal_arbiter.select(goals=(), obligations=())
    assert selection.selected_obligation_ref is None
    assert selection.selected_goal_ref is None
    assert selection.ui_intent_label == "idle"


def test_goal_selection_is_frozen():
    selection = GoalSelection(
        selected_goal_ref="goal:1",
        selected_obligation_ref=None,
        ui_intent_label="goal:pursue",
        policy_ref="policy:goal_arbitration",
    )
    with pytest.raises(Exception):
        selection.ui_intent_label = "idle"  # type: ignore[misc]


def test_ui_intent_label_has_no_control_authority(goal_arbiter):
    """The UI intent label is a derived display label, not a control ref."""
    selection = goal_arbiter.select(
        goals=("goal:1",), obligations=()
    )
    # The label is a string label only; it is not a goal/obligation ref that
    # could be dispatched against.
    assert selection.ui_intent_label == "goal:pursue"
    assert selection.ui_intent_label != selection.selected_goal_ref
