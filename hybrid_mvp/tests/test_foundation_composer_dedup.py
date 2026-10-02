"""Semantic-state de-duplication for the bounded recursive composer."""

from __future__ import annotations

from dataclasses import replace

from cemm_authoritative_hybrid.programs import ProgramAction
from cemm_authoritative_hybrid.recursive_composer._core import _SourceUse, _State
from cemm_authoritative_hybrid.recursive_composer._search import _semantic_state_key


__cemm_test_inventory__ = {
    "tests/test_foundation_composer_dedup.py::test_independent_action_order_is_one_semantic_search_state": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:composer-independent-action-order-is-one-semantic-state",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Reported-Speech",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "9096a5bfcaeb293ba0a7c9604aec302efdbdc3ec9fc01756b6157dcd45c01213",
    },
    "tests/test_foundation_composer_dedup.py::test_semantic_state_key_preserves_evidence_provenance_and_score": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:composer-state-key-preserves-evidence-provenance-and-score",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Reported-Speech",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "13e794e1d68aeb605e5e45fc1eb37ca448f17e57b75994bd5f02f1a1635091c2",
    },
}


def _state(*, reversed_designations: bool = False) -> _State:
    context = ProgramAction.create(
        action_index=0,
        action_type="select_context",
        arguments=("proposal_context:test",),
    )
    mode = ProgramAction.create(
        action_index=1,
        action_type="select_mode",
        arguments=("mode_slot:test",),
        source_unit_refs=("unit:mode",),
    )
    designation_refs = (
        "designation_slot:second",
        "designation_slot:first",
    ) if reversed_designations else (
        "designation_slot:first",
        "designation_slot:second",
    )
    designations = tuple(
        ProgramAction.create(
            action_index=index + 2,
            action_type="select_designation",
            arguments=(designation_ref,),
        )
        for index, designation_ref in enumerate(designation_refs)
    )
    return _State(
        prefix=(context, mode, *designations),
        application_frames=(),
        bound_roles=(),
        node_order=(),
        parents=(),
        source_uses=(
            _SourceUse(
                source_unit_ref="unit:mode",
                contribution_slot_ref="contribution:mode",
                assignment_kind="discourse",
                target_action_ref=mode.action_ref,
                target_role_ref=None,
                critical=False,
            ),
        ),
        selected_designations=designation_refs,
        used_frame_slots=(),
        used_structure_slots=(),
        used_transition_pairs=(),
        score_q=100,
        provenance=("evidence:first", "evidence:second"),
    )


def test_independent_action_order_is_one_semantic_search_state() -> None:
    forward = _state()
    reverse = replace(
        _state(reversed_designations=True),
        provenance=tuple(reversed(forward.provenance)),
    )

    assert tuple(action.action_ref for action in forward.prefix) != tuple(
        action.action_ref for action in reverse.prefix
    )
    assert _semantic_state_key(forward) == _semantic_state_key(reverse)


def test_semantic_state_key_preserves_evidence_provenance_and_score() -> None:
    state = _state()
    different_use = replace(
        state,
        source_uses=(
            replace(
                state.source_uses[0],
                contribution_slot_ref="contribution:other-mode",
            ),
        ),
    )

    assert _semantic_state_key(state) != _semantic_state_key(different_use)
    assert _semantic_state_key(state) != _semantic_state_key(
        replace(state, provenance=("evidence:first", "evidence:third"))
    )
    assert _semantic_state_key(state) != _semantic_state_key(
        replace(state, score_q=state.score_q + 1)
    )
