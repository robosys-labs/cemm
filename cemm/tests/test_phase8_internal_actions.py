from __future__ import annotations

from types import SimpleNamespace

from cemm.actions import InternalActionAuthorizer, InternalActionProposer
from cemm.response import ResponseFormationEngine
from cemm.response.types import InternalActionProposal, ResponseCandidatePlan, ResponseMove, ResponseSituation, WriteOutcome


def test_phase8_authorizes_output_state_but_does_not_execute_side_effects():
    situation = ResponseSituation(
        obligation_frame=SimpleNamespace(obligation_kind="social_reply", response_mode="social_response", context={}, evidence_policy="none"),
        uol_graph=SimpleNamespace(atoms={"i1": SimpleNamespace(id="i1", kind="intent", key="greeting", features={}, confidence=0.9)}),
        semantic_program=SimpleNamespace(entry_instruction=SimpleNamespace(atom_ids=["i1"], instruction_kind="social")),
    )

    result = ResponseFormationEngine().form(situation)

    action_types = {a.action_type for a in result.internal_actions}
    assert "update_output_state" in action_types
    assert all(a.authorized for a in result.internal_actions)
    assert result.action_authorization is not None
    assert result.diagnostics["actions"]["authorized_count"] >= 1


def test_phase8_safety_event_requires_safety_frame_and_is_authorized():
    situation = ResponseSituation(
        obligation_frame=SimpleNamespace(obligation_kind="abstain_policy", response_mode="safety_refusal", context={}, evidence_policy="none"),
        safety_frame=SimpleNamespace(id="sf1", category="violence", severity="high", confidence=0.92),
    )

    result = ResponseFormationEngine().form(situation)

    safety_actions = [a for a in result.internal_actions if a.action_type == "flag_safety_event"]
    assert safety_actions
    assert safety_actions[0].payload["category"] == "violence"
    assert "sf1" in safety_actions[0].source_refs


def test_phase8_language_preference_requires_explicit_semantic_authority():
    graph = SimpleNamespace(atoms={
        "lang1": SimpleNamespace(
            id="lang1",
            kind="preference",
            key="language_preference",
            features={"language": "fr", "authority": "explicit_preference"},
            confidence=0.91,
        )
    })
    situation = ResponseSituation(
        obligation_frame=SimpleNamespace(obligation_kind="social_reply", response_mode="social_response", context={}, evidence_policy="none"),
        uol_graph=graph,
        semantic_program=SimpleNamespace(entry_instruction=SimpleNamespace(atom_ids=[], instruction_kind="social")),
    )

    result = ResponseFormationEngine().form(situation)

    actions = [a for a in result.internal_actions if a.action_type == "set_language_preference"]
    assert actions
    assert actions[0].payload["language"] == "fr"
    assert "lang1" in actions[0].source_refs


def test_phase8_inferred_language_hint_is_not_promoted_to_preference():
    graph = SimpleNamespace(atoms={
        "lang1": SimpleNamespace(
            id="lang1",
            kind="entity",
            key="place",
            features={"language": "fr", "authority": "inferred_hint"},
            confidence=0.7,
        )
    })
    situation = ResponseSituation(
        obligation_frame=SimpleNamespace(obligation_kind="social_reply", response_mode="social_response", context={}, evidence_policy="none"),
        uol_graph=graph,
        semantic_program=SimpleNamespace(entry_instruction=SimpleNamespace(atom_ids=[], instruction_kind="social")),
    )

    result = ResponseFormationEngine().form(situation)

    authorized_types = {a.action_type for a in result.internal_actions}
    assert "set_language_hint" in authorized_types
    assert "set_language_preference" not in authorized_types


def test_phase8_denies_side_effect_action_from_response_layer():
    proposal = InternalActionProposal(action_type="send_email", confidence=1.0, reversible=False, source_refs=["x"])
    result = InternalActionAuthorizer().authorize([proposal], ResponseSituation(), ResponseCandidatePlan())

    assert not result.authorized_actions
    assert result.rejected_actions[0].action_type == "send_email"
    assert result.decisions[0].reason == "side_effect_action_not_authorized_by_response_layer"


def test_phase8_locale_hint_must_have_semantic_source_refs():
    proposal = InternalActionProposal(
        action_type="set_locale_hint",
        payload={"locale": "fr-FR", "authority": "inferred_hint"},
        confidence=0.9,
        reversible=True,
        source_refs=[],
    )
    result = InternalActionAuthorizer().authorize([proposal], ResponseSituation(), ResponseCandidatePlan())

    assert not result.authorized_actions
    assert result.decisions[0].reason == "missing_semantic_source_refs"


def test_phase8_write_outcome_records_status_without_content_echo():
    situation = ResponseSituation(
        obligation_frame=SimpleNamespace(obligation_kind="store_patch", response_mode="store_confirmation", context={}, evidence_policy="speaker_asserted"),
        write_outcome=WriteOutcome(commit_status="committed", patch_count=1, committed_count=1, committed_patch_ids=["p1"]),
    )

    result = ResponseFormationEngine().form(situation)

    write_actions = [a for a in result.internal_actions if a.action_type == "record_write_outcome"]
    assert write_actions
    assert write_actions[0].payload["commit_status"] == "committed"
    assert "content" not in write_actions[0].payload
