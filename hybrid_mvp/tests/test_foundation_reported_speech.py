"""Clause-local ownership for recursively composed reported speech."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.expressions import (
    CompilationSuccess,
    SemanticExpressionCompiler,
)
from cemm_authoritative_hybrid.programs import (
    ProgramAction,
    SemanticSwitchProgram,
    SourceAssignment,
)
from cemm_authoritative_hybrid.proposal_context import ProposalContext, ReferenceSlot
from cemm_authoritative_hybrid.verifier import _replay_program
from cemm_authoritative_hybrid.verifier_reconstruction import (
    reconstruct_expected_expression,
)


ROOT = Path(__file__).resolve().parents[1]

__cemm_test_inventory__ = {
    "tests/test_foundation_reported_speech.py::test_reported_leave_gold_names_the_child_actor_explicitly": {
        "activation_phase": "R4", "assertion_ref": "assertion:reported-leave-gold-names-child-actor-explicitly",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "r4-scenario-source",
        "source_ast_sha256": "aaae658a0d70bdcd63bec211c42cb1fe52e3adcbdd6dc1c6c0d510f1f3a311a7",
    },
    "tests/test_foundation_reported_speech.py::test_reported_speaker_inheritance_requires_explicit_reviewed_authority": {
        "activation_phase": "R3", "assertion_ref": "assertion:reported-speaker-inheritance-requires-reviewed-authority",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "semantic-affordances",
        "source_ast_sha256": "15b93d37f8fabaec929eef5ac7cf3a1f2b30d8c3cb2af9c8761c5c8eafc11666",
    },
    "tests/test_foundation_reported_speech.py::test_verifier_rejects_swapped_reported_role_inheritance_control": {
        "activation_phase": "R3", "assertion_ref": "assertion:verifier-rejects-swapped-reported-role-inheritance-control",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "exact-verifier",
        "source_ast_sha256": "216a13aac9d44c8043147c15d02a0501e4bead2390e5363ab79f40fe15bfdd5e",
    },
    "tests/test_foundation_reported_speech.py::test_reported_speaker_verification_fails_closed_without_linked_authority": {
        "activation_phase": "R3", "assertion_ref": "assertion:reported-speaker-verification-requires-linked-authority",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "exact-verifier",
        "source_ast_sha256": "b279b94582aee32a40c1793bc4a1b688fc7a28716c935c68e4418c72f02e7281",
    },
    "tests/test_foundation_reported_speech.py::test_reported_farewell_inherits_exact_speaker_without_situated_addressee": {
        "activation_phase": "R3", "assertion_ref": "assertion:reported-farewell-inherits-exact-speaker-without-situated-addressee",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "situation-context",
        "source_ast_sha256": "acd66e346366a5f05cf7abde60253ab2cd58a3167488163ee43eef5509a8edd8",
    },
    "tests/test_foundation_reported_speech.py::test_explicit_child_actor_wins_and_reporting_actor_stays_parent_local": {
        "activation_phase": "R3", "assertion_ref": "assertion:reported-explicit-child-actor-wins",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "situation-context",
        "source_ast_sha256": "6c3db7503c6721d4b8a02f7af16615dad38499179d79dae3520ec399ccd9e049",
    },
    "tests/test_foundation_reported_speech.py::test_noncommunicative_child_does_not_inherit_reporting_actor": {
        "activation_phase": "R3", "assertion_ref": "assertion:reported-noncommunicative-child-does-not-inherit-actor",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "situation-context",
        "source_ast_sha256": "acb1db9d065e31e7ad0d81a7c2649b687b4156c61100de40e8de6eb5ba99b688",
    },
    "tests/test_foundation_reported_speech.py::test_standalone_farewell_retains_situated_actor_and_addressee": {
        "activation_phase": "R3", "assertion_ref": "assertion:standalone-farewell-retains-situated-participants",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "situation-context",
        "source_ast_sha256": "221fd71da4a22bc7c587f982b2210b4d2027e4692582d0ffee8ee7016b86be5a",
    },
    "tests/test_foundation_reported_speech.py::test_reported_and_standalone_greeting_share_reviewed_participant_control": {
        "activation_phase": "R3", "assertion_ref": "assertion:reported-and-standalone-greeting-participant-control",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "situation-context",
        "source_ast_sha256": "573d8d070b5ae5e03c99b4540d5075c71dff2ba253698f023b02f92e790d2fb1",
    },
    "tests/test_foundation_reported_speech.py::test_semantic_state_dedup_settles_complete_multi_sentence_report": {
        "activation_phase": "R3", "assertion_ref": "assertion:semantic-state-dedup-settles-complete-multi-sentence-report",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "recursive-composer",
        "source_ast_sha256": "39d9ddcabf28e67b5a110032187019f69b9b34bc69fc9499c28e64dec24b27e0",
    },
    "tests/test_foundation_reported_speech.py::test_content_local_negation_never_scopes_the_reporting_event": {
        "activation_phase": "R3", "assertion_ref": "assertion:reported-content-negation-is-local",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "situation-context",
        "source_ast_sha256": "05984b07a60a516ff36261439b41cb947128e09689ff3a71d78c4e3ae8b96805",
    },
    "tests/test_foundation_reported_speech.py::test_nested_state_and_relation_content_preserve_clause_local_roles[state]": {
        "activation_phase": "R3", "assertion_ref": "assertion:reported-nested-state-preserves-local-roles",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "situation-context",
        "source_ast_sha256": "1746ba9a91a45263d65bbb3b9ef841e27619ce84bcd51d3e331577b877563fe9",
    },
    "tests/test_foundation_reported_speech.py::test_nested_state_and_relation_content_preserve_clause_local_roles[relation]": {
        "activation_phase": "R3", "assertion_ref": "assertion:reported-nested-relation-preserves-local-roles",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "situation-context",
        "source_ast_sha256": "1746ba9a91a45263d65bbb3b9ef841e27619ce84bcd51d3e331577b877563fe9",
    },
    "tests/test_foundation_reported_speech.py::test_verifier_rejects_forged_cross_clause_report_content": {
        "activation_phase": "R3", "assertion_ref": "assertion:verifier-rejects-cross-clause-report-content",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "exact-verifier",
        "source_ast_sha256": "49d227156e00279b01a8f35caada1f7114b0af23c9738b17afb39f1985b1c179",
    },
    "tests/test_foundation_reported_speech.py::test_verifier_rejects_forged_content_scope_on_reporting_parent": {
        "activation_phase": "R3", "assertion_ref": "assertion:verifier-rejects-content-scope-on-report-parent",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "exact-verifier",
        "source_ast_sha256": "6121c0bbe172fb436593192d1ac32ca139ac4954095d419c1b78235f128e4921",
    },
    "tests/test_foundation_reported_speech.py::test_verifier_rejects_parent_source_reference_bound_to_report_child": {
        "activation_phase": "R3", "assertion_ref": "assertion:verifier-rejects-parent-source-reference-on-report-child",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "exact-verifier",
        "source_ast_sha256": "8959b7b00a474c528f7b6813b7e7c16c4f5e629ea89c65a712140b2b46f9b67d",
    },
    "tests/test_foundation_reported_speech.py::test_verifier_rejects_forged_reported_speaker_control_for_leave": {
        "activation_phase": "R3", "assertion_ref": "assertion:verifier-rejects-forged-reported-speaker-control",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "exact-verifier",
        "source_ast_sha256": "9896aa1ade67bb8103ac0ce412e61baff0eec809f88f321b81c0d970d8454299",
    },
    "tests/test_foundation_reported_speech.py::test_verifier_rejects_extra_provenance_on_eligible_reported_speaker": {
        "activation_phase": "R3", "assertion_ref": "assertion:verifier-rejects-extra-provenance-on-eligible-reported-speaker",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "exact-verifier",
        "source_ast_sha256": "5202f6fda0295d9e6021b63e62395f5141ffbe3de643e53d97d3d6070fb271c8",
    },
    "tests/test_foundation_reported_speech.py::test_compiler_materializes_scoped_child_before_proposition_binding": {
        "activation_phase": "R3", "assertion_ref": "assertion:compiler-materializes-scoped-child-before-proposition-binding",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "expression-compiler",
        "source_ast_sha256": "02a65c17d849a2fcec85e88b12a3756d22c07880b24307addfd19ec0fc323dd4",
    },
    "tests/test_foundation_reported_speech.py::test_verifier_reconstructs_ordinary_punctuation_clause_locality": {
        "activation_phase": "R3", "assertion_ref": "assertion:verifier-reconstructs-ordinary-punctuation-clause-locality",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "exact-verifier",
        "source_ast_sha256": "641e63a03eeb6b5f3aa12870de3b48daf45a720dde57bc72fe04e14f0f2487b3",
    },
    "tests/test_foundation_reported_speech.py::test_report_content_introductory_punctuation_is_not_a_sentence_boundary[comma]": {
        "activation_phase": "R3", "assertion_ref": "assertion:reported-content-comma-is-not-sentence-boundary",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "situation-context",
        "source_ast_sha256": "cdab6cb904b15cab624a38c9189dbdd177c0264848692c315c04fa5d357a79a3",
    },
    "tests/test_foundation_reported_speech.py::test_report_content_introductory_punctuation_is_not_a_sentence_boundary[colon]": {
        "activation_phase": "R3", "assertion_ref": "assertion:reported-content-colon-is-not-sentence-boundary",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Speech", "owner_ref": "situation-context",
        "source_ast_sha256": "cdab6cb904b15cab624a38c9189dbdd177c0264848692c315c04fa5d357a79a3",
    },
}


@pytest.fixture
def runtime(tmp_path: Path):
    owner = load_runtime(ROOT, profile="development", store_path=tmp_path / "store.db")
    try:
        yield owner
    finally:
        owner.stores.close()


def _propose(runtime, source: str):
    orientation, context = runtime.orient(f"session:{source}", source)
    proposal = runtime._owners["proposal"].propose(context)
    verification = runtime._owners["verification"].verify_candidates(proposal, context)
    return orientation, context, proposal, verification


def _applications(verification):
    assert verification.status == "selected"
    return {
        row.predicate_ref: row
        for row in verification.selected_meaning.expression.applications
    }


def _roles(application):
    return {row.role_ref: row.filler for row in application.roles}


def _frame_map(candidate, context):
    return {
        action.arguments[0]: context.frame(action.arguments[1])
        for action in candidate.program.actions
        if action.action_type == "instantiate_operator"
    }


def _rebuild_program(program, replacements, *, action_order=None):
    original_actions = (
        program.actions
        if action_order is None
        else tuple(program.actions[index] for index in action_order)
    )
    actions = tuple(
        ProgramAction.create(
            action_index=index,
            action_type=action.action_type,
            arguments=replacements.get(action.action_index, action.arguments),
            source_unit_refs=action.source_unit_refs,
        )
        for index, action in enumerate(original_actions)
    )
    action_refs = {
        old.action_ref: new.action_ref
        for old, new in zip(original_actions, actions, strict=True)
    }
    assignments = tuple(
        SourceAssignment.create(
            source_unit_ref=row.source_unit_ref,
            contribution_slot_ref=row.contribution_slot_ref,
            assignment_kind=row.assignment_kind,
            target_action_ref=(
                action_refs[row.target_action_ref]
                if row.target_action_ref is not None
                else None
            ),
            target_role_ref=row.target_role_ref,
            residual_kind=row.residual_kind,
            critical=row.critical,
        )
        for row in program.source_assignments
    )
    return SemanticSwitchProgram.create(
        orientation_ref=program.orientation_ref,
        proposal_context_ref=program.proposal_context_ref,
        actions=actions,
        root_refs=program.root_refs,
        mode_slot_ref=program.mode_slot_ref,
        goal_refs=program.goal_refs,
        source_unit_refs=program.source_unit_refs,
        source_assignments=assignments,
        revision_pin=program.revision_pin,
    )


def _forged_context_with_reference(context, reference):
    values = {
        name: getattr(context, name)
        for name in (
            "orientation_ref",
            "evidence_packet_ref",
            "form_lattice_ref",
            "grounding_ref",
            "designation_slots",
            "contribution_slots",
            "mode_slots",
            "application_frames",
            "scope_slots",
            "expression_link_slots",
            "variable_slots",
            "transition_slots",
            "residual_evidence",
            "context_refs",
            "source_unit_refs",
            "source_unit_spans",
            "revision_pin",
        )
    }
    values["reference_slots"] = (*context.reference_slots, reference)
    # An adversarial verifier fixture intentionally bypasses context creation:
    # the verifier must not trust a self-described coreference control.
    return ProposalContext._from_checked(context.context_ref, values)


def test_reported_farewell_inherits_exact_speaker_without_situated_addressee(runtime) -> None:
    _, context, proposal, verification = _propose(runtime, "Alice said goodbye.")

    assert proposal.truncated is False
    applications = _applications(verification)
    say_roles = _roles(applications["event:say"])
    farewell_roles = _roles(applications["event:farewell"])
    assert say_roles["role:actor"].target_ref == "entity:alice"
    assert farewell_roles["role:actor"].target_ref == "entity:alice"
    assert "role:addressee" not in farewell_roles
    farewell_frame = next(
        row for row in context.application_frames
        if row.predicate_target_ref == "event:farewell"
    )
    assert "role:addressee" in farewell_frame.optional_roles
    assert not any(
        row.resolution_kind == "situated_participant"
        and farewell_frame.slot_ref in row.provenance_refs
        for row in context.reference_slots
    )


def test_explicit_child_actor_wins_and_reporting_actor_stays_parent_local(runtime) -> None:
    _, context, proposal, verification = _propose(runtime, "Alice said Bob left.")

    assert proposal.truncated is False
    applications = _applications(verification)
    assert _roles(applications["event:say"])["role:actor"].target_ref == "entity:alice"
    assert _roles(applications["event:leave"])["role:actor"].target_ref == "entity:bob"
    leave_frame = next(
        row for row in context.application_frames if row.predicate_target_ref == "event:leave"
    )
    assert not any(
        row.resolution_kind == "reported_speaker_coreference"
        and leave_frame.slot_ref in row.provenance_refs
        for row in context.reference_slots
    )


def test_noncommunicative_child_does_not_inherit_reporting_actor(runtime) -> None:
    _, context, proposal, verification = _propose(runtime, "Alice said leave.")

    leave_frame = next(
        row for row in context.application_frames if row.predicate_target_ref == "event:leave"
    )
    assert not any(
        row.resolution_kind == "reported_speaker_coreference"
        and leave_frame.slot_ref in row.provenance_refs
        for row in context.reference_slots
    )
    assert proposal.status == "abstained"
    assert verification.status == "abstained"


def test_reported_leave_gold_names_the_child_actor_explicitly() -> None:
    rows = {
        row["scenario_ref"]: row
        for row in (
            json.loads(line)
            for line in (ROOT / "data/scenarios/use_cases.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        )
    }
    for scenario_ref, speaker in (
        ("scenario:reported_speech-0081", "entity:alice"),
        ("scenario:reported_speech-0082", "entity:bob"),
    ):
        row = rows[scenario_ref]
        assertion = row["semantic_assertions"][0]
        spoken_name = speaker.split(":", 1)[1]
        assert assertion == {
            "kind": "reported_speech",
            "speaker": speaker,
            "event": "event:say",
            "content": "event:leave",
            "content_actor": speaker,
        }
        assert all(
            surface.casefold().split().count(spoken_name) == 2
            for surface in row["surface_examples"]
        )


def test_standalone_farewell_retains_situated_actor_and_addressee(runtime) -> None:
    _, context, _, verification = _propose(runtime, "goodbye")

    applications = _applications(verification)
    roles = _roles(applications["event:farewell"])
    assert roles["role:actor"].target_ref == "participant:user"
    assert roles["role:addressee"].target_ref == "participant:system"
    frame = next(
        row for row in context.application_frames
        if row.predicate_target_ref == "event:farewell"
    )
    assert "role:addressee" in frame.optional_roles


def test_reported_and_standalone_greeting_share_reviewed_participant_control(
    runtime,
) -> None:
    _, reported_context, _, reported_verification = _propose(
        runtime, "Alice said hello."
    )
    reported = _applications(reported_verification)
    say_roles = _roles(reported["event:say"])
    greeting_roles = _roles(reported["event:greeting"])
    assert say_roles["role:actor"].target_ref == "entity:alice"
    assert greeting_roles["role:actor"].target_ref == "entity:alice"
    assert "role:addressee" not in greeting_roles
    reported_frame = next(
        row for row in reported_context.application_frames
        if row.predicate_target_ref == "event:greeting"
    )
    assert "role:addressee" in reported_frame.optional_roles


def test_reported_speaker_inheritance_requires_explicit_reviewed_authority(
    runtime,
) -> None:
    authority = runtime.authority
    for child_target in ("event:greeting", "event:farewell"):
        control = authority.reported_role_inheritance_control(
            "event:say", "role:content", child_target, "role:actor"
        )
        assert control is not None
        source_control = authority.source_attribution_control(
            "event:say", "role:content"
        )
        assert source_control is not None
        assert source_control.source_role_ref == "role:actor"
        assert control.source_attribution_control_ref == source_control.control_ref
        assert control.child_target_ref == child_target
        assert control.child_role_ref == "role:actor"

    assert authority.reported_role_inheritance_control(
        "event:say", "role:content", "event:leave", "role:actor"
    ) is None

    _, context, _, _ = _propose(runtime, "Alice said goodbye.")
    inherited = next(
        row
        for row in context.reference_slots
        if row.resolution_kind == "reported_speaker_coreference"
    )
    farewell_control = authority.reported_role_inheritance_control(
        "event:say", "role:content", "event:farewell", "role:actor"
    )
    assert farewell_control is not None
    assert inherited.provenance_refs[-1] == farewell_control.control_ref

    _, standalone_context, _, standalone_verification = _propose(runtime, "hello")
    standalone = _roles(_applications(standalone_verification)["event:greeting"])
    assert standalone["role:actor"].target_ref == "participant:user"
    assert standalone["role:addressee"].target_ref == "participant:system"
    standalone_frame = next(
        row for row in standalone_context.application_frames
        if row.predicate_target_ref == "event:greeting"
    )
    assert "role:addressee" in standalone_frame.optional_roles


def test_semantic_state_dedup_settles_complete_multi_sentence_report(
    runtime,
) -> None:
    source = "The server is offline. You said goodbye."
    _, context, proposal, verification = _propose(runtime, source)
    report_end = source.index("said") + len("said")
    frames_by_ref = {row.slot_ref: row for row in context.application_frames}

    for reference in context.reference_slots:
        scoped = tuple(
            frames_by_ref[ref]
            for ref in reference.provenance_refs
            if ref in frames_by_ref
        )
        if reference.target_ref == "entity:server":
            assert scoped and all(
                row.predicate_target_ref not in {"event:say", "event:farewell"}
                for row in scoped
            )
        if reference.target_ref == "participant:system" and reference.source_unit_refs:
            assert scoped and all(
                row.predicate_target_ref not in {"dim:availability", "value:offline"}
                for row in scoped
            )

    # Independent action order does not create a distinct semantic search
    # state or proposal. The complete graph settles below the existing cap.
    assert proposal.status == "candidates"
    assert proposal.truncated is False
    assert proposal.explored_states < 768
    assert len(proposal.candidates) == 1
    assert verification.status == "selected"
    assert verification.selected_candidate_ref == proposal.candidates[0].candidate_ref
    for candidate in proposal.candidates:
        frames = _frame_map(candidate, context)
        for action in candidate.program.actions:
            if action.action_type != "bind_nested_application" or action.arguments[0] != "role":
                continue
            _, parent_ref, role_ref, child_ref = action.arguments
            if role_ref != "role:content" or frames[parent_ref].predicate_target_ref != "event:say":
                continue
            child_frame = frames[child_ref]
            child_span = context.source_span(child_frame.source_unit_refs)
            assert child_span is not None and child_span[0] >= report_end

    compiled = SemanticExpressionCompiler().compile(
        proposal.candidates[0].program, context
    )
    assert isinstance(compiled, CompilationSuccess)
    applications = {
        row.predicate_ref: row for row in compiled.expression.applications
    }
    assert set(applications) == {
        "dim:availability", "event:say", "event:farewell"
    }
    state_roles = _roles(applications["dim:availability"])
    say_roles = _roles(applications["event:say"])
    farewell_roles = _roles(applications["event:farewell"])
    assert state_roles["role:subject"].target_ref == "entity:server"
    assert state_roles["role:value"].target_ref == "value:offline"
    assert say_roles["role:actor"].target_ref == "participant:system"
    assert say_roles["role:content"].node_ref == applications["event:farewell"].application_ref
    assert farewell_roles["role:actor"].target_ref == "participant:system"
    root_predicates = {
        row.predicate_ref for row in compiled.expression.applications
        if row.application_ref in compiled.expression.root_refs
    }
    assert root_predicates == {"dim:availability", "event:say"}


def test_content_local_negation_never_scopes_the_reporting_event(runtime) -> None:
    source = "Alice said the server is not online."
    _, context, proposal, verification = _propose(runtime, source)

    assert proposal.truncated is False
    applications = _applications(verification)
    expression = verification.selected_meaning.expression
    assert len(expression.scope_operators) == 1
    assert expression.scope_operators[0].operand_ref == applications["dim:availability"].application_ref
    for candidate in proposal.candidates:
        frames = _frame_map(candidate, context)
        for action in candidate.program.actions:
            if action.action_type == "attach_scope" and action.arguments[2] in frames:
                assert frames[action.arguments[2]].predicate_target_ref != "event:say"


@pytest.mark.parametrize(
    ("source", "content_predicate", "expected_roles"),
    (
        (
            "Alice said the server is offline.",
            "dim:availability",
            {"role:subject": "entity:server", "role:value": "value:offline"},
        ),
        (
            "Alice said Bob likes Alice.",
            "rel:likes",
            {"role:subject": "entity:bob", "role:object": "entity:alice"},
        ),
    ),
    ids=("state", "relation"),
)
def test_nested_state_and_relation_content_preserve_clause_local_roles(
    runtime, source: str, content_predicate: str, expected_roles: dict[str, str]
) -> None:
    _, _, proposal, verification = _propose(runtime, source)

    assert proposal.truncated is False
    applications = _applications(verification)
    roles = _roles(applications[content_predicate])
    assert {role: roles[role].target_ref for role in expected_roles} == expected_roles
    say_content = _roles(applications["event:say"])["role:content"]
    assert say_content.node_ref == applications[content_predicate].application_ref


def test_verifier_rejects_forged_cross_clause_report_content(runtime) -> None:
    source = "The server is offline. You said goodbye."
    _, context, proposal, _ = _propose(runtime, source)
    candidate = next(
        row
        for row in proposal.candidates
        if (
            (frames := _frame_map(row, context))
            and (
                nested := next(
                    (
                        action
                        for action in row.program.actions
                        if action.action_type == "bind_nested_application"
                        and action.arguments[0] == "role"
                        and frames[action.arguments[1]].predicate_target_ref == "event:say"
                        and frames[action.arguments[3]].predicate_target_ref == "event:farewell"
                    ),
                    None,
                )
            )
            is not None
            and any(
                action.action_type == "instantiate_operator"
                and frames[action.arguments[0]].predicate_target_ref == "dim:availability"
                and action.action_index < nested.action_index
                for action in row.program.actions
            )
        )
    )
    frames = _frame_map(candidate, context)
    prior_ref = next(
        ref for ref, frame in frames.items()
        if frame.predicate_target_ref == "dim:availability"
    )
    nested = next(
        action for action in candidate.program.actions
        if action.action_type == "bind_nested_application"
        and action.arguments[0] == "role"
        and frames[action.arguments[1]].predicate_target_ref == "event:say"
    )
    forged = _rebuild_program(
        candidate.program,
        {
            nested.action_index: (
                "role",
                nested.arguments[1],
                "role:content",
                prior_ref,
            )
        },
    )

    assert "reported_content_locality" in {
        row.code for row in _replay_program(
            forged, context, authority=runtime.authority
        )
    }


def test_verifier_rejects_forged_content_scope_on_reporting_parent(runtime) -> None:
    _, context, proposal, verification = _propose(
        runtime, "Alice said the server is not online."
    )
    assert verification.status == "selected"
    candidate = next(
        row for row in proposal.candidates
        if row.candidate_ref == verification.selected_candidate_ref
    )
    frames = _frame_map(candidate, context)
    scope = next(
        action for action in candidate.program.actions
        if action.action_type == "attach_scope"
    )
    say_action = next(
        action for action in candidate.program.actions
        if action.action_type == "instantiate_operator"
        and frames[action.arguments[0]].predicate_target_ref == "event:say"
    )
    order = list(range(len(candidate.program.actions)))
    order.remove(say_action.action_index)
    order.insert(scope.action_index, say_action.action_index)
    reordered = _rebuild_program(
        candidate.program,
        {},
        action_order=tuple(order),
    )
    frames = {
        action.arguments[0]: context.frame(action.arguments[1])
        for action in reordered.actions
        if action.action_type == "instantiate_operator"
    }
    say_ref = next(
        ref for ref, frame in frames.items()
        if frame.predicate_target_ref == "event:say"
    )
    scope = next(
        action for action in reordered.actions
        if action.action_type == "attach_scope"
    )
    forged = _rebuild_program(
        reordered,
        {scope.action_index: (scope.arguments[0], scope.arguments[1], say_ref)},
    )

    assert "reported_scope_locality" in {
        row.code for row in _replay_program(
            forged, context, authority=runtime.authority
        )
    }


def test_verifier_rejects_parent_source_reference_bound_to_report_child(runtime) -> None:
    _, context, proposal, verification = _propose(runtime, "Alice said goodbye.")
    candidate = next(
        row for row in proposal.candidates
        if row.candidate_ref == verification.selected_candidate_ref
    )
    frames = _frame_map(candidate, context)
    child_ref = next(
        ref for ref, frame in frames.items()
        if frame.predicate_target_ref == "event:farewell"
    )
    say_frame_ref = next(
        frame.slot_ref for frame in frames.values()
        if frame.predicate_target_ref == "event:say"
    )
    parent_reference = next(
        row for row in context.reference_slots
        if row.target_ref == "entity:alice"
        and row.source_unit_refs
        and say_frame_ref in row.provenance_refs
    )
    actor = next(
        action for action in candidate.program.actions
        if action.action_type == "bind_reference"
        and action.arguments[:2] == (child_ref, "role:actor")
    )
    forged = _rebuild_program(
        candidate.program,
        {
            actor.action_index: (
                child_ref,
                "role:actor",
                parent_reference.slot_ref,
            )
        },
    )

    assert "reference_source_locality" in {
        row.code for row in _replay_program(
            forged, context, authority=runtime.authority
        )
    }
    assert reconstruct_expected_expression(
        forged, context, authority=runtime.authority
    ) is None


def test_verifier_rejects_forged_reported_speaker_control_for_leave(runtime) -> None:
    _, context, proposal, verification = _propose(runtime, "Alice said Bob left.")
    candidate = next(
        row for row in proposal.candidates
        if row.candidate_ref == verification.selected_candidate_ref
    )
    frames = _frame_map(candidate, context)
    leave_ref = next(
        ref for ref, frame in frames.items()
        if frame.predicate_target_ref == "event:leave"
    )
    leave_frame_ref = frames[leave_ref].slot_ref
    say_frame_ref = next(
        frame.slot_ref for frame in frames.values()
        if frame.predicate_target_ref == "event:say"
    )
    parent_reference = next(
        row for row in context.reference_slots
        if row.target_ref == "entity:alice"
        and row.source_unit_refs
        and say_frame_ref in row.provenance_refs
    )
    forged_reference = ReferenceSlot.create(
        target_ref=parent_reference.target_ref,
        target_kind=parent_reference.target_kind,
        source_unit_refs=(),
        resolution_kind="reported_speaker_coreference",
        compatible_roles=("role:actor",),
        score_q=parent_reference.score_q,
        provenance_refs=(
            parent_reference.slot_ref,
            say_frame_ref,
            leave_frame_ref,
            "form_hypothesis:forged-report-control",
        ),
    )
    forged_context = _forged_context_with_reference(context, forged_reference)
    actor = next(
        action for action in candidate.program.actions
        if action.action_type == "bind_reference"
        and action.arguments[:2] == (leave_ref, "role:actor")
    )
    forged = _rebuild_program(
        candidate.program,
        {
            actor.action_index: (
                leave_ref,
                "role:actor",
                forged_reference.slot_ref,
            )
        },
    )

    assert "reference_source_locality" in {
        row.code for row in _replay_program(
            forged, forged_context, authority=runtime.authority
        )
    }
    assert reconstruct_expected_expression(
        forged, forged_context, authority=runtime.authority
    ) is None


def test_verifier_rejects_extra_provenance_on_eligible_reported_speaker(runtime) -> None:
    _, context, proposal, verification = _propose(runtime, "Alice said goodbye.")
    candidate = next(
        row for row in proposal.candidates
        if row.candidate_ref == verification.selected_candidate_ref
    )
    canonical = next(
        row for row in context.reference_slots
        if row.resolution_kind == "reported_speaker_coreference"
    )
    forged_reference = ReferenceSlot.create(
        target_ref=canonical.target_ref,
        target_kind=canonical.target_kind,
        source_unit_refs=canonical.source_unit_refs,
        resolution_kind=canonical.resolution_kind,
        compatible_roles=canonical.compatible_roles,
        score_q=canonical.score_q,
        provenance_refs=(*canonical.provenance_refs, "review:forged"),
    )
    forged_context = _forged_context_with_reference(context, forged_reference)
    child_ref = next(
        action.arguments[0]
        for action in candidate.program.actions
        if action.action_type == "instantiate_operator"
        and context.frame(action.arguments[1]).predicate_target_ref == "event:farewell"
    )
    actor = next(
        action for action in candidate.program.actions
        if action.action_type == "bind_reference"
        and action.arguments[:2] == (child_ref, "role:actor")
    )
    forged = _rebuild_program(
        candidate.program,
        {
            actor.action_index: (
                child_ref,
                "role:actor",
                forged_reference.slot_ref,
            )
        },
    )

    assert "reference_source_locality" in {
        row.code for row in _replay_program(
            forged, forged_context, authority=runtime.authority
        )
    }
    assert reconstruct_expected_expression(
        forged, forged_context, authority=runtime.authority
    ) is None


def test_verifier_rejects_swapped_reported_role_inheritance_control(runtime) -> None:
    _, context, proposal, verification = _propose(runtime, "Alice said goodbye.")
    candidate = next(
        row for row in proposal.candidates
        if row.candidate_ref == verification.selected_candidate_ref
    )
    canonical = next(
        row for row in context.reference_slots
        if row.resolution_kind == "reported_speaker_coreference"
    )
    greeting_control = runtime.authority.reported_role_inheritance_control(
        "event:say", "role:content", "event:greeting", "role:actor"
    )
    assert greeting_control is not None
    forged_reference = ReferenceSlot.create(
        target_ref=canonical.target_ref,
        target_kind=canonical.target_kind,
        source_unit_refs=canonical.source_unit_refs,
        resolution_kind=canonical.resolution_kind,
        compatible_roles=canonical.compatible_roles,
        score_q=canonical.score_q,
        provenance_refs=(*canonical.provenance_refs[:-1], greeting_control.control_ref),
    )
    forged_context = _forged_context_with_reference(context, forged_reference)
    child_ref = next(
        action.arguments[0]
        for action in candidate.program.actions
        if action.action_type == "instantiate_operator"
        and context.frame(action.arguments[1]).predicate_target_ref == "event:farewell"
    )
    actor = next(
        action for action in candidate.program.actions
        if action.action_type == "bind_reference"
        and action.arguments[:2] == (child_ref, "role:actor")
    )
    forged = _rebuild_program(
        candidate.program,
        {
            actor.action_index: (
                child_ref,
                "role:actor",
                forged_reference.slot_ref,
            )
        },
    )

    assert "reference_source_locality" in {
        row.code for row in _replay_program(
            forged, forged_context, authority=runtime.authority
        )
    }
    assert reconstruct_expected_expression(
        forged, forged_context, authority=runtime.authority
    ) is None


def test_reported_speaker_verification_fails_closed_without_linked_authority(
    runtime,
) -> None:
    _, context, proposal, verification = _propose(runtime, "Alice said goodbye.")
    candidate = next(
        row for row in proposal.candidates
        if row.candidate_ref == verification.selected_candidate_ref
    )

    assert "reported_speaker_authority_missing" in {
        row.code for row in _replay_program(candidate.program, context)
    }
    assert _replay_program(
        candidate.program, context, authority=runtime.authority
    ) == ()
    assert reconstruct_expected_expression(candidate.program, context) is None
    assert (
        reconstruct_expected_expression(
            candidate.program, context, authority=runtime.authority
        )
        == verification.selected_meaning.expression
    )


def test_verifier_reconstructs_ordinary_punctuation_clause_locality(runtime) -> None:
    source = "The server is offline. Alice likes Bob."
    _, context, proposal, verification = _propose(runtime, source)
    candidate = next(
        row for row in proposal.candidates
        if row.candidate_ref == verification.selected_candidate_ref
    )
    frames = _frame_map(candidate, context)
    relation_ref = next(
        ref for ref, frame in frames.items()
        if frame.predicate_target_ref == "rel:likes"
    )
    server_reference = next(
        row for row in context.reference_slots
        if row.target_ref == "entity:server" and row.source_unit_refs
    )
    masquerading_reference = ReferenceSlot.create(
        target_ref=server_reference.target_ref,
        target_kind=server_reference.target_kind,
        source_unit_refs=server_reference.source_unit_refs,
        resolution_kind=server_reference.resolution_kind,
        compatible_roles=("role:subject",),
        score_q=server_reference.score_q,
        provenance_refs=("application_frame_slot:forged-spelling",),
    )
    forged_context = _forged_context_with_reference(
        context, masquerading_reference
    )
    subject = next(
        action for action in candidate.program.actions
        if action.action_type == "bind_reference"
        and action.arguments[:2] == (relation_ref, "role:subject")
    )
    forged = _rebuild_program(
        candidate.program,
        {
            subject.action_index: (
                relation_ref,
                "role:subject",
                masquerading_reference.slot_ref,
            )
        },
    )

    assert "reference_source_locality" in {
        row.code for row in _replay_program(
            forged, forged_context, authority=runtime.authority
        )
    }
    assert reconstruct_expected_expression(
        forged, forged_context, authority=runtime.authority
    ) is None


def test_compiler_materializes_scoped_child_before_proposition_binding(runtime) -> None:
    _, _, proposal, verification = _propose(
        runtime, "Alice said the server is not online."
    )
    candidate = next(
        row for row in proposal.candidates
        if row.candidate_ref == verification.selected_candidate_ref
    )
    scope = next(
        action for action in candidate.program.actions
        if action.action_type == "attach_scope"
    )
    nested = next(
        action for action in candidate.program.actions
        if action.action_type == "bind_nested_application"
        and action.arguments[0] == "role"
    )

    assert scope.action_index < nested.action_index
    assert nested.arguments[3] == scope.arguments[0]
    receipt = next(
        row for row in verification.candidate_receipts
        if row.candidate_ref == candidate.candidate_ref
    )
    assert receipt.accepted
    assert receipt.expression is not None


@pytest.mark.parametrize(
    "source",
    ("Alice said, Bob left.", "Alice said: Bob left."),
    ids=("comma", "colon"),
)
def test_report_content_introductory_punctuation_is_not_a_sentence_boundary(
    runtime, source: str
) -> None:
    _, context, proposal, verification = _propose(runtime, source)

    assert proposal.truncated is False
    applications = _applications(verification)
    assert _roles(applications["event:say"])["role:actor"].target_ref == "entity:alice"
    assert _roles(applications["event:leave"])["role:actor"].target_ref == "entity:bob"
    assert (
        _roles(applications["event:say"])["role:content"].node_ref
        == applications["event:leave"].application_ref
    )
    introductory = next(
        row
        for row in context.contribution_slots
        if row.source_unit_refs
        and context.source_span(row.source_unit_refs) == (10, 11)
    )
    assert ("orthography", "punctuation") in introductory.constraints
    assert ("orthography", "sentence_boundary") not in introductory.constraints
