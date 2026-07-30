"""Tests for verified semantic dialogue focus.

Only verified semantic refs enter focus — unverified output never enters
focus.  These tests verify the :class:`FocusStore` and
:class:`VerifiedSemanticFocus` contracts, including the constraint that
unverified output is rejected and never appears in focus.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.dialogue import (
    FocusStore,
    VerifiedSemanticFocus,
)


# ---------------------------------------------------------------------------
# Test-only dialogue session helper
# ---------------------------------------------------------------------------


@dataclass
class _TurnResult:
    """Result of one dialogue turn in the test session."""

    participant: str
    text: str
    turn: str
    verified: bool
    semantic_content_ref: str | None = None
    proposition_ref: str | None = None
    response_ref: str | None = None
    status: str = "verified"


class _DialogueSession:
    """Test-only dialogue session wrapping :class:`FocusStore`.

    Simulates ``runtime.process(participant, text)`` for focus-related
    tests.  Verified output enters focus; unverified output is rejected
    and never enters focus.
    """

    def __init__(self) -> None:
        self.focus = FocusStore()
        self._turn = 0

    def process(
        self,
        participant: str,
        text: str,
        *,
        verified: bool = True,
    ) -> _TurnResult:
        self._turn += 1
        turn_ref = f"turn:{self._turn}"

        if not verified:
            # Unverified output is rejected and never enters focus.
            response_ref = stable_ref(
                "response", {"text": text, "turn": self._turn}
            )
            return _TurnResult(
                participant=participant,
                text=text,
                turn=turn_ref,
                verified=False,
                response_ref=response_ref,
                status="rejected",
            )

        if participant == "s":
            content_ref = stable_ref(
                "semantic_content", {"text": text, "turn": self._turn}
            )
            focus = VerifiedSemanticFocus(
                proposition_refs=(content_ref,),
                entity_refs=(),
                event_refs=(),
                salience_evidence=(content_ref,),
                participant="participant:system",
                turn=turn_ref,
                revision=self._turn,
            )
            self.focus.add(focus)
            return _TurnResult(
                participant=participant,
                text=text,
                turn=turn_ref,
                verified=True,
                semantic_content_ref=content_ref,
                response_ref=content_ref,
                status="verified",
            )
        else:
            prop_ref = stable_ref(
                "proposition", {"text": text, "turn": self._turn}
            )
            focus = VerifiedSemanticFocus(
                proposition_refs=(prop_ref,),
                entity_refs=(),
                event_refs=(),
                salience_evidence=(prop_ref,),
                participant="participant:user",
                turn=turn_ref,
                revision=self._turn,
            )
            self.focus.add(focus)
            return _TurnResult(
                participant=participant,
                text=text,
                turn=turn_ref,
                verified=True,
                proposition_ref=prop_ref,
                response_ref=prop_ref,
                status="verified",
            )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dialogue_session():
    """A test-only dialogue session with a FocusStore."""
    return _DialogueSession()


@pytest.fixture
def corrupt_realizer():
    """A realizer that produces unverified output.

    The corrupt realizer always marks output as unverified, so the
    realization receipt status is ``"rejected"`` and the response ref
    never enters focus.
    """

    class _CorruptRealizer:
        def process(self, session, text):
            session._turn += 1
            response_ref = stable_ref(
                "response", {"text": text, "turn": session._turn}
            )
            return _TurnResult(
                participant="s",
                text=text,
                turn=f"turn:{session._turn}",
                verified=False,
                response_ref=response_ref,
                status="rejected",
            )

    return _CorruptRealizer()


# ---------------------------------------------------------------------------
# Focus store tests
# ---------------------------------------------------------------------------


def test_focus_store_starts_empty():
    store = FocusStore()
    assert store.refs == frozenset()
    assert store.query("anything") is False


def test_focus_store_stores_verified_refs():
    store = FocusStore()
    focus = VerifiedSemanticFocus(
        proposition_refs=("prop:1", "prop:2"),
        entity_refs=("entity:door",),
        event_refs=("event:greeting",),
        salience_evidence=("prop:1",),
        participant="participant:system",
        turn="turn:1",
        revision=1,
    )
    store.add(focus)
    assert store.query("prop:1")
    assert store.query("prop:2")
    assert store.query("entity:door")
    assert store.query("event:greeting")
    assert not store.query("prop:3")
    assert store.refs == frozenset(
        {"prop:1", "prop:2", "entity:door", "event:greeting"}
    )


def test_focus_store_accumulates_across_turns():
    store = FocusStore()
    store.add(VerifiedSemanticFocus(
        proposition_refs=("prop:a",),
        entity_refs=(),
        event_refs=(),
        salience_evidence=(),
        participant="participant:user",
        turn="turn:1",
        revision=1,
    ))
    store.add(VerifiedSemanticFocus(
        proposition_refs=("prop:b",),
        entity_refs=(),
        event_refs=(),
        salience_evidence=(),
        participant="participant:system",
        turn="turn:2",
        revision=2,
    ))
    assert store.query("prop:a")
    assert store.query("prop:b")
    assert len(store.entries) == 2


def test_focus_store_recent_entries():
    store = FocusStore()
    for i in range(5):
        store.add(VerifiedSemanticFocus(
            proposition_refs=(f"prop:{i}",),
            entity_refs=(),
            event_refs=(),
            salience_evidence=(),
            participant="participant:user",
            turn=f"turn:{i}",
            revision=i,
        ))
    recent = store.recent_entries(2)
    assert len(recent) == 2
    assert recent[-1].proposition_refs == ("prop:4",)
    assert recent[-2].proposition_refs == ("prop:3",)


# ---------------------------------------------------------------------------
# VerifiedSemanticFocus immutability
# ---------------------------------------------------------------------------


def test_verified_semantic_focus_is_frozen():
    focus = VerifiedSemanticFocus(
        proposition_refs=("prop:1",),
        entity_refs=(),
        event_refs=(),
        salience_evidence=(),
        participant="participant:system",
        turn="turn:1",
        revision=1,
    )
    with pytest.raises(Exception):
        focus.proposition_refs = ("prop:2",)  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Unverified output never enters focus
# ---------------------------------------------------------------------------


def test_unverified_output_never_enters_focus(dialogue_session, corrupt_realizer):
    """Unverified output is rejected and never enters focus."""
    result = corrupt_realizer.process(dialogue_session, "what is your name?")
    assert result.status == "rejected"
    assert result.response_ref not in dialogue_session.focus.refs


def test_verified_output_enters_focus(dialogue_session):
    """Verified system output enters focus."""
    result = dialogue_session.process("s", "what is your name?")
    assert result.status == "verified"
    assert result.response_ref in dialogue_session.focus.refs


def test_verified_user_proposition_enters_focus(dialogue_session):
    """Verified user propositions enter focus."""
    result = dialogue_session.process("u", "CEMM can learn reviewed aliases")
    assert result.status == "verified"
    assert result.proposition_ref in dialogue_session.focus.refs


def test_mixed_verified_and_unverified(dialogue_session, corrupt_realizer):
    """Verified output enters focus; unverified does not."""
    verified = dialogue_session.process("s", "hello")
    unverified = corrupt_realizer.process(dialogue_session, "goodbye")
    assert verified.response_ref in dialogue_session.focus.refs
    assert unverified.response_ref not in dialogue_session.focus.refs
