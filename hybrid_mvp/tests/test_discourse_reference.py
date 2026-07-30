"""Tests for discourse reference resolution.

Reference resolution applies person/number/kind/recency/scope constraints
and preserves alternatives below margin.  ``"what did you say?"`` resolves
to verified system speech; ``"that"`` resolves to a prior verified
proposition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.dialogue import (
    FocusStore,
    ReferenceConstraints,
    ReferenceResolution,
    ReferenceResolver,
    VerifiedSemanticFocus,
)


# ---------------------------------------------------------------------------
# Test-only orientation (minimal, for resolver.resolve)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _TestOrientation:
    """Minimal orientation for reference resolution tests."""

    session_ref: str = "session:test"
    turn_ref: str = "turn:test"
    source_text: str = ""
    focus_refs: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Test-only dialogue session helper
# ---------------------------------------------------------------------------


@dataclass
class _TurnResult:
    """Result of one dialogue turn."""

    participant: str
    text: str
    turn: str
    semantic_content_ref: str | None = None
    proposition_ref: str | None = None
    resolution: ReferenceResolution | None = None
    reference_bindings: dict[str, str] = field(default_factory=dict)
    bindings: tuple[tuple[str, str], ...] = ()


class _DialogueSession:
    """Test-only dialogue session wrapping FocusStore and ReferenceResolver."""

    def __init__(self, resolver: ReferenceResolver) -> None:
        self.focus = resolver._focus_store
        self._resolver = resolver
        self._turn = 0
        self._system_speech: dict[int, str] = {}
        self._user_props: dict[int, str] = {}

    def process(self, participant: str, text: str) -> _TurnResult:
        self._turn += 1
        turn_ref = f"turn:{self._turn}"

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
            self._system_speech[self._turn] = content_ref

            # Check for "what did you say?" reference query.
            lowered = text.lower()
            if "what did you say" in lowered:
                constraints = ReferenceConstraints(
                    person="second",
                    number="singular",
                    kind="content",
                    recency=10,
                    scope="local",
                )
                orientation = _TestOrientation(
                    session_ref="session:test",
                    turn_ref=turn_ref,
                    source_text=text,
                )
                resolution = self._resolver.resolve(
                    "what", constraints, orientation
                )
                return _TurnResult(
                    participant=participant,
                    text=text,
                    turn=turn_ref,
                    semantic_content_ref=content_ref,
                    resolution=resolution,
                    reference_bindings=resolution.bindings,
                    bindings=(
                        (("content", resolution.resolved_ref),)
                        if resolution.resolved_ref
                        else ()
                    ),
                )

            return _TurnResult(
                participant=participant,
                text=text,
                turn=turn_ref,
                semantic_content_ref=content_ref,
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
            self._user_props[self._turn] = prop_ref

            # Check for "that" demonstrative reference.
            lowered = text.lower()
            if lowered.startswith("that") or " that " in lowered:
                constraints = ReferenceConstraints(
                    person="third",
                    number="singular",
                    kind="proposition",
                    recency=10,
                    scope="local",
                )
                orientation = _TestOrientation(
                    session_ref="session:test",
                    turn_ref=turn_ref,
                    source_text=text,
                )
                resolution = self._resolver.resolve(
                    "that", constraints, orientation
                )
                return _TurnResult(
                    participant=participant,
                    text=text,
                    turn=turn_ref,
                    proposition_ref=prop_ref,
                    resolution=resolution,
                    reference_bindings=resolution.bindings,
                )

            return _TurnResult(
                participant=participant,
                text=text,
                turn=turn_ref,
                proposition_ref=prop_ref,
            )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def focus_store():
    return FocusStore()


@pytest.fixture
def resolver(focus_store, linked_authority):
    return ReferenceResolver(focus_store, linked_authority)


@pytest.fixture
def dialogue_session(resolver):
    return _DialogueSession(resolver)


# ---------------------------------------------------------------------------
# "what did you say?" resolves to verified system speech
# ---------------------------------------------------------------------------


def test_what_did_you_say_resolves_verified_system_speech(dialogue_session):
    first = dialogue_session.process("s", "what is your name?")
    second = dialogue_session.process("s", "what did you say?")
    assert second.resolution is not None
    assert second.resolution.resolved_ref == first.semantic_content_ref
    assert second.bindings == (
        ("content", first.semantic_content_ref),
    )


def test_what_did_you_say_resolves_to_most_recent_system_speech(dialogue_session):
    dialogue_session.process("s", "hello")
    second_speech = dialogue_session.process("s", "my name is CEMM")
    query = dialogue_session.process("s", "what did you say?")
    assert query.resolution is not None
    assert query.resolution.resolved_ref == second_speech.semantic_content_ref


def test_what_did_you_say_does_not_resolve_user_speech(dialogue_session):
    """'what did you say?' with person=second only resolves system speech."""
    dialogue_session.process("u", "I am Ada")
    query = dialogue_session.process("s", "what did you say?")
    assert query.resolution is not None
    # Should not resolve to user proposition because person=second filters
    # to participant:system only.
    user_prop = dialogue_session._user_props.get(1)
    assert query.resolution.resolved_ref != user_prop


# ---------------------------------------------------------------------------
# "that" resolves to prior verified proposition
# ---------------------------------------------------------------------------


def test_that_resolves_prior_verified_proposition(dialogue_session):
    prior = dialogue_session.process("u", "CEMM can learn reviewed aliases")
    result = dialogue_session.process("u", "that's the best thing I ever heard")
    prior_claim_ref = prior.proposition_ref
    assert result.resolution is not None
    assert result.resolution.resolved_ref == prior_claim_ref
    assert result.reference_bindings["that"] == prior_claim_ref


def test_that_resolves_most_recent_proposition(dialogue_session):
    dialogue_session.process("u", "the door is open")
    second_prop = dialogue_session.process("u", "the light is on")
    result = dialogue_session.process("u", "that is interesting")
    assert result.resolution is not None
    assert result.resolution.resolved_ref == second_prop.proposition_ref


# ---------------------------------------------------------------------------
# Reference constraints
# ---------------------------------------------------------------------------


def test_person_constraint_filters_by_participant(focus_store, resolver):
    """person='second' only matches participant:system entries."""
    user_ref = "prop:user-claim"
    system_ref = "prop:system-speech"
    focus_store.add(VerifiedSemanticFocus(
        proposition_refs=(user_ref,),
        entity_refs=(),
        event_refs=(),
        salience_evidence=(),
        participant="participant:user",
        turn="turn:1",
        revision=1,
    ))
    focus_store.add(VerifiedSemanticFocus(
        proposition_refs=(system_ref,),
        entity_refs=(),
        event_refs=(),
        salience_evidence=(),
        participant="participant:system",
        turn="turn:2",
        revision=2,
    ))

    constraints = ReferenceConstraints(
        person="second", number=None, kind=None, recency=10, scope=None
    )
    resolution = resolver.resolve("you", constraints, _TestOrientation())
    assert resolution.resolved_ref == system_ref


def test_person_first_filters_to_user(focus_store, resolver):
    """person='first' only matches participant:user entries."""
    user_ref = "prop:user-claim"
    system_ref = "prop:system-speech"
    focus_store.add(VerifiedSemanticFocus(
        proposition_refs=(user_ref,),
        entity_refs=(),
        event_refs=(),
        salience_evidence=(),
        participant="participant:user",
        turn="turn:1",
        revision=1,
    ))
    focus_store.add(VerifiedSemanticFocus(
        proposition_refs=(system_ref,),
        entity_refs=(),
        event_refs=(),
        salience_evidence=(),
        participant="participant:system",
        turn="turn:2",
        revision=2,
    ))

    constraints = ReferenceConstraints(
        person="first", number=None, kind=None, recency=10, scope=None
    )
    resolution = resolver.resolve("I", constraints, _TestOrientation())
    assert resolution.resolved_ref == user_ref


def test_kind_constraint_filters_by_kind(focus_store, resolver):
    """kind='entity' only matches entity_refs."""
    prop_ref = "prop:1"
    entity_ref = "entity:door"
    focus_store.add(VerifiedSemanticFocus(
        proposition_refs=(prop_ref,),
        entity_refs=(entity_ref,),
        event_refs=(),
        salience_evidence=(),
        participant="participant:user",
        turn="turn:1",
        revision=1,
    ))

    constraints = ReferenceConstraints(
        person=None, number=None, kind="entity", recency=10, scope=None
    )
    resolution = resolver.resolve("it", constraints, _TestOrientation())
    assert resolution.resolved_ref == entity_ref


def test_recency_constraint_limits_candidates(focus_store, resolver):
    """recency=1 only considers the most recent entry."""
    old_ref = "prop:old"
    new_ref = "prop:new"
    focus_store.add(VerifiedSemanticFocus(
        proposition_refs=(old_ref,),
        entity_refs=(),
        event_refs=(),
        salience_evidence=(),
        participant="participant:user",
        turn="turn:1",
        revision=1,
    ))
    focus_store.add(VerifiedSemanticFocus(
        proposition_refs=(new_ref,),
        entity_refs=(),
        event_refs=(),
        salience_evidence=(),
        participant="participant:user",
        turn="turn:2",
        revision=2,
    ))

    constraints = ReferenceConstraints(
        person=None, number=None, kind=None, recency=1, scope=None
    )
    resolution = resolver.resolve("that", constraints, _TestOrientation())
    assert resolution.resolved_ref == new_ref


def test_unresolved_ref_returns_none(focus_store, resolver):
    """No candidates yields resolved_ref=None."""
    constraints = ReferenceConstraints(
        person="second", number=None, kind=None, recency=10, scope=None
    )
    resolution = resolver.resolve("you", constraints, _TestOrientation())
    assert resolution.resolved_ref is None
    assert resolution.bindings == {}


# ---------------------------------------------------------------------------
# Alternatives below margin
# ---------------------------------------------------------------------------


def test_alternatives_below_margin_are_preserved(focus_store, resolver):
    """Alternatives within the margin of the best candidate are preserved."""
    refs = []
    for i in range(5):
        ref = f"prop:{i}"
        refs.append(ref)
        focus_store.add(VerifiedSemanticFocus(
            proposition_refs=(ref,),
            entity_refs=(),
            event_refs=(),
            salience_evidence=(),
            participant="participant:user",
            turn=f"turn:{i}",
            revision=i,
        ))

    constraints = ReferenceConstraints(
        person=None, number=None, kind=None, recency=10, scope=None
    )
    resolution = resolver.resolve("that", constraints, _TestOrientation())
    # Best is the most recent (prop:4).
    assert resolution.resolved_ref == "prop:4"
    # Alternatives should be preserved (within margin).
    assert len(resolution.alternatives) > 0
    assert "prop:4" not in resolution.alternatives


def test_resolution_bindings_contain_ref_to_resolved(focus_store, resolver):
    focus_store.add(VerifiedSemanticFocus(
        proposition_refs=("prop:1",),
        entity_refs=(),
        event_refs=(),
        salience_evidence=(),
        participant="participant:user",
        turn="turn:1",
        revision=1,
    ))
    constraints = ReferenceConstraints(
        person=None, number=None, kind=None, recency=10, scope=None
    )
    resolution = resolver.resolve("that", constraints, _TestOrientation())
    assert resolution.bindings == {"that": "prop:1"}


# ---------------------------------------------------------------------------
# Orientation integration
# ---------------------------------------------------------------------------


def test_orientation_projector_uses_focus_store(linked_authority, memory_stores_fixture):
    """OrientationProjector uses FocusStore refs when provided."""
    from cemm_authoritative_hybrid.cycle import OrientationProjector
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.dialogue import FocusStore, VerifiedSemanticFocus

    store = FocusStore()
    store.add(VerifiedSemanticFocus(
        proposition_refs=("prop:verified",),
        entity_refs=("entity:door",),
        event_refs=(),
        salience_evidence=(),
        participant="participant:user",
        turn="turn:1",
        revision=1,
    ))

    projector = OrientationProjector(
        authority=linked_authority,
        stores=memory_stores_fixture,
        config=RuntimeConfig.release(),
        focus_store=store,
    )
    orientation = projector.project("session:test", "anything")
    assert "entity:door" in orientation.focus_refs
    assert "prop:verified" in orientation.focus_refs
