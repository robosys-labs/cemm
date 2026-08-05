from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.cycle import SemanticMode
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.situation import (
    SITUATION_CONTEXT_ABI_VERSION,
    SituationContext,
)

__cemm_test_inventory__ = {
    "tests/test_r3_situation_context.py::test_situation_context_identity_covers_source_lineage": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-situation-context-identity-covers-source-lineage",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "situation-context",
        "source_ast_sha256": "ed18af67031282313d55d0b19587545f92976857bdf0659235731b2b3b0d0109"
    },
    "tests/test_r3_situation_context.py::test_situation_context_round_trip_is_exact": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-situation-context-round-trip-is-exact",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "situation-context",
        "source_ast_sha256": "e402834965e571d3cf069ae299d54e84fd5c1b57686c82f5e62218744d9effa0"
    },
    "tests/test_r3_situation_context.py::test_situation_rejects_mode_scope_disagreement": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-situation-rejects-mode-scope-disagreement",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "situation-context",
        "source_ast_sha256": "34b45c7aff023bd269590b9e6f848e300870bd732431a8f846c64fa98f7091c5"
    },
    "tests/test_r3_situation_context.py::test_situation_requires_distinct_reviewed_participants": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-situation-requires-distinct-reviewed-participants",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Complete",
        "owner_ref": "situation-context",
        "source_ast_sha256": "ec94bb68c6db4216febb335ae88ad0d2e2641db729bc31c7625083dcee599642"
    }
}



def _pin() -> RevisionPin:
    return RevisionPin(
        authority_generation="authority:test",
        world_revision=1,
        session_revision=2,
        episode_revision=3,
        effect_revision=4,
        model_identity="model:test",
    )


def _situation() -> SituationContext:
    return SituationContext.create(
        orientation_ref="orientation:test",
        proposal_context_ref="proposal_context:test",
        mode=SemanticMode.QUERY,
        session_ref="session:test",
        turn_ref="turn:test",
        turn_index=1,
        participant_refs=("participant:system", "participant:user"),
        speaker_ref="participant:user",
        addressee_ref="participant:system",
        actor_ref=None,
        temporal_frame_ref="time:now",
        active_event_refs=("event:turn",),
        focus_snapshot_ref="snapshot:focus:test",
        focus_refs=("entity:bob",),
        obligation_snapshot_ref="snapshot:obligation:test",
        obligation_refs=(),
        capability_refs=("cap:answer",),
        permission_snapshot_ref="snapshot:permission:test",
        permission_refs=(),
        resource_snapshot_ref="snapshot:resource:test",
        resource_refs=(),
        adapter_snapshot_ref="snapshot:adapter:test",
        adapter_refs=(),
        evidence_kinds=("text",),
        evidence_policy_refs=("policy:evidence:test",),
        adapter_receipt_refs=(),
        trusted_observation=False,
        source_refs=(
            "evidence:test",
            "form_lattice:test",
            "grounding:test",
        ),
        epistemic_scope_ref="epistemic_scope:query",
        session_phase_ref="session_phase:active_turn",
        revision_pin=_pin(),
    )


def test_situation_context_round_trip_is_exact() -> None:
    value = _situation()
    assert value.abi_version == SITUATION_CONTEXT_ABI_VERSION
    assert SituationContext.from_dict(value.as_dict()) == value


def test_situation_context_identity_covers_source_lineage() -> None:
    left = _situation()
    data = left.as_dict()
    data["source_refs"] = [
        "evidence:other",
        "form_lattice:test",
        "grounding:test",
    ]
    data["situation_ref"] = left.situation_ref
    with pytest.raises(ValueError, match="non-canonical SituationContext"):
        SituationContext.from_dict(data)


def test_situation_rejects_mode_scope_disagreement() -> None:
    values = _situation().as_dict()
    values["epistemic_scope_ref"] = "epistemic_scope:observed"
    values["situation_ref"] = "situation:forged"
    with pytest.raises(ValueError, match="epistemic scope does not match"):
        SituationContext.from_dict(values)


def test_situation_requires_distinct_reviewed_participants() -> None:
    with pytest.raises(ValueError, match="must differ"):
        SituationContext.create(
            orientation_ref="orientation:test",
            proposal_context_ref="proposal_context:test",
            mode=SemanticMode.OBSERVE,
            session_ref="session:test",
            turn_ref="turn:test",
            turn_index=1,
            participant_refs=("participant:user",),
            speaker_ref="participant:user",
            addressee_ref="participant:user",
            actor_ref=None,
            temporal_frame_ref="time:now",
            active_event_refs=(),
            focus_snapshot_ref="snapshot:focus:test",
            focus_refs=(),
            obligation_snapshot_ref="snapshot:obligation:test",
            obligation_refs=(),
            capability_refs=(),
            permission_snapshot_ref="snapshot:permission:test",
            permission_refs=(),
            resource_snapshot_ref="snapshot:resource:test",
            resource_refs=(),
            adapter_snapshot_ref="snapshot:adapter:test",
            adapter_refs=(),
            evidence_kinds=("text",),
            evidence_policy_refs=("policy:evidence:test",),
            adapter_receipt_refs=(),
            trusted_observation=False,
            source_refs=("evidence:test",),
            epistemic_scope_ref="epistemic_scope:observed",
            session_phase_ref="session_phase:active_turn",
            revision_pin=_pin(),
        )
