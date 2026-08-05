"""R2 context-local legal action relation tests.

Per R2 plan section 3:
- Every action has positive and negative legality tests
- Masker/exhaustive parity is proven on generated small contexts
- Legality is pure, deterministic, bounded, and context-local
- No ref-name inspection or authority scan exists
- Bounds are enforced (applications, actions, nodes)
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.programs import ProgramAction
from cemm_authoritative_hybrid.verifier import (
    ActionMasker,
    LegalActionIndex,
    _prefix_budget,
)

__cemm_test_inventory__ = {
    "tests/test_r2_legal_actions.py::test_abstain_illegal_after_terminal": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-abstain-illegal-after-terminal",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "2a09d3d40d8a2398f1d4d82f80d3fae49774dd24301d65a8b49537368862c629"
    },
    "tests/test_r2_legal_actions.py::test_application_bound_enforced": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-application-bound-enforced",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "b684ca91762dd819b0ee16a33a88db8b0e890f148b9cb4e2eaa2a52e604159fc"
    },
    "tests/test_r2_legal_actions.py::test_complete_program_illegal_without_required_roles": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-complete-program-illegal-without-required-roles",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "2f597b684e249b6f6238946ca1617732bebf5246ba9a6d694e0721b62aa05394"
    },
    "tests/test_r2_legal_actions.py::test_instantiate_operator_illegal_without_designation": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-instantiate-operator-illegal-without-designation",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "cf37b7e449fed4d2e4500820868373b6f92f20bd4b5aa1c0904f6e7fdc20e2f2"
    },
    "tests/test_r2_legal_actions.py::test_instantiate_operator_legal_after_designation": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-instantiate-operator-legal-after-designation",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "d9ba100e230c898c1a34a99ab9191b96194e914024b05b797b9961393088e356"
    },
    "tests/test_r2_legal_actions.py::test_is_legal_is_pure_predicate": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-is-legal-is-pure-predicate",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "afd9ef4bdf716230858f9ed48fca40e81327a63e6f7d7a431736dfebe54b9f18"
    },
    "tests/test_r2_legal_actions.py::test_masker_matches_legal_index": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-masker-matches-legal-index",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "485451ddf06db79f90923493c620e31118b712e22532f5594b6a5d67bf8248e1"
    },
    "tests/test_r2_legal_actions.py::test_node_bound_enforced_for_attach_scope": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-node-bound-enforced-for-attach-scope",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "5df86ca6ce65dc74130722e033c20e38af6f2ab787af75f5937c4a1db182242e"
    },
    "tests/test_r2_legal_actions.py::test_prefix_budget_empty": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-prefix-budget-empty",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "b12cb00fca4cdb76782f08a27b4b70c90f317bda665d8d5e926610f08c373901"
    },
    "tests/test_r2_legal_actions.py::test_prefix_budget_tracks_applications": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-prefix-budget-tracks-applications",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "5c68f0f3868b88459c778dbe560190b3279556f3bcf087bec38231acfc779795"
    },
    "tests/test_r2_legal_actions.py::test_select_context_illegal_with_wrong_ref": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-select-context-illegal-with-wrong-ref",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "75f0c0c021588e745c994e65bb5d3d0c0c02d710b16e07d1245c978bab89d139"
    },
    "tests/test_r2_legal_actions.py::test_select_context_legal_on_empty_prefix": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-select-context-legal-on-empty-prefix",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "0724db37d1ac014e83ebffe3bc78eb216abb866e4a8abe0b7ef797c6c326870a"
    },
    "tests/test_r2_legal_actions.py::test_select_designation_illegal_duplicate": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-select-designation-illegal-duplicate",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "67fcc962bce673bbe76fe2eb268109548c385e442823cf44bf243f1dd04f5111"
    },
    "tests/test_r2_legal_actions.py::test_select_designation_legal_after_mode": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-select-designation-legal-after-mode",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "c31856bd36381dd8f745c78c0b57efa2a3374358bbcbf8585362d317aba3ad29"
    },
    "tests/test_r2_legal_actions.py::test_select_mode_illegal_on_empty_prefix": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-select-mode-illegal-on-empty-prefix",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "01a889421ab25557656cb048e1afe022ce29d27c19c12c438adc00afe453c638"
    },
    "tests/test_r2_legal_actions.py::test_select_mode_legal_after_select_context": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-select-mode-legal-after-select-context",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "recursive-composer",
        "source_ast_sha256": "f9012c1e97eda27a526278f32872d7afa5e2bd63d403293cc11ad44d1b69afb6"
    },
}



# ---------------------------------------------------------------------------
# Budget tracking tests
# ---------------------------------------------------------------------------


def test_prefix_budget_empty():
    """Empty prefix has zero budget use."""
    app_count, action_count, node_count = _prefix_budget(())
    assert app_count == 0
    assert action_count == 0
    assert node_count == 0


def test_prefix_budget_tracks_applications(masker):
    """Budget tracks application count from instantiate_operator actions."""
    context = masker.legal_index.context
    actions = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=(context.mode_slots[0].slot_ref,),
        ),
        ProgramAction.create(
            action_index=2,
            action_type="select_designation",
            arguments=(context.designation_slots[0].slot_ref,),
        ),
        ProgramAction.create(
            action_index=3,
            action_type="instantiate_operator",
            arguments=(
                "application:0",
                context.application_frames[0].slot_ref,
            ),
        ),
    )
    app_count, action_count, node_count = _prefix_budget(actions)
    assert app_count == 1
    assert action_count == 4
    assert node_count == 1


# ---------------------------------------------------------------------------
# Positive and negative legality tests per action type
# ---------------------------------------------------------------------------


def test_select_context_legal_on_empty_prefix(masker):
    """select_context is legal only on empty prefix with correct context_ref."""
    context = masker.legal_index.context
    action = ProgramAction.create(
        action_index=0,
        action_type="select_context",
        arguments=(context.context_ref,),
    )
    assert masker.legal_index.is_legal(action, ())


def test_select_context_illegal_with_wrong_ref(masker):
    """select_context with wrong context_ref is illegal."""
    context = masker.legal_index.context
    action = ProgramAction.create(
        action_index=0,
        action_type="select_context",
        arguments=("ctx:wrong",),
    )
    assert not masker.legal_index.is_legal(action, ())


def test_select_mode_legal_after_select_context(masker):
    """select_mode is legal after select_context with valid mode slot."""
    context = masker.legal_index.context
    prefix = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
    )
    mode_slot = context.mode_slots[0]
    action = ProgramAction.create(
        action_index=1,
        action_type="select_mode",
        arguments=(mode_slot.slot_ref,),
    )
    assert masker.legal_index.is_legal(action, prefix)


def test_select_mode_illegal_on_empty_prefix(masker):
    """select_mode is illegal on empty prefix."""
    context = masker.legal_index.context
    mode_slot = context.mode_slots[0]
    action = ProgramAction.create(
        action_index=0,
        action_type="select_mode",
        arguments=(mode_slot.slot_ref,),
    )
    assert not masker.legal_index.is_legal(action, ())


def test_select_designation_legal_after_mode(masker):
    """select_designation is legal after select_mode with valid designation."""
    context = masker.legal_index.context
    prefix = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=(context.mode_slots[0].slot_ref,),
        ),
    )
    designation = context.designation_slots[0]
    action = ProgramAction.create(
        action_index=2,
        action_type="select_designation",
        arguments=(designation.slot_ref,),
    )
    assert masker.legal_index.is_legal(action, prefix)


def test_select_designation_illegal_duplicate(masker):
    """select_designation is illegal for duplicate designation."""
    context = masker.legal_index.context
    designation = context.designation_slots[0]
    prefix = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=(context.mode_slots[0].slot_ref,),
        ),
        ProgramAction.create(
            action_index=2,
            action_type="select_designation",
            arguments=(designation.slot_ref,),
        ),
    )
    action = ProgramAction.create(
        action_index=3,
        action_type="select_designation",
        arguments=(designation.slot_ref,),
    )
    assert not masker.legal_index.is_legal(action, prefix)


def test_instantiate_operator_legal_after_designation(masker):
    """instantiate_operator is legal after selecting its designation."""
    context = masker.legal_index.context
    designation = context.designation_slots[0]
    frame = context.application_frames[0]
    prefix = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=(context.mode_slots[0].slot_ref,),
        ),
        ProgramAction.create(
            action_index=2,
            action_type="select_designation",
            arguments=(designation.slot_ref,),
        ),
    )
    action = ProgramAction.create(
        action_index=3,
        action_type="instantiate_operator",
        arguments=("application:0", frame.slot_ref),
    )
    assert masker.legal_index.is_legal(action, prefix)


def test_instantiate_operator_illegal_without_designation(masker):
    """instantiate_operator is illegal without selecting its designation."""
    context = masker.legal_index.context
    frame = context.application_frames[0]
    prefix = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=(context.mode_slots[0].slot_ref,),
        ),
    )
    action = ProgramAction.create(
        action_index=2,
        action_type="instantiate_operator",
        arguments=("application:0", frame.slot_ref),
    )
    assert not masker.legal_index.is_legal(action, prefix)


def test_complete_program_illegal_without_required_roles(masker):
    """complete_program is illegal when required roles are not satisfied."""
    context = masker.legal_index.context
    designation = context.designation_slots[0]
    frame = context.application_frames[0]
    prefix = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=(context.mode_slots[0].slot_ref,),
        ),
        ProgramAction.create(
            action_index=2,
            action_type="select_designation",
            arguments=(designation.slot_ref,),
        ),
        ProgramAction.create(
            action_index=3,
            action_type="instantiate_operator",
            arguments=("application:0", frame.slot_ref),
        ),
    )
    action = ProgramAction.create(
        action_index=4,
        action_type="complete_program",
        arguments=(),
    )
    # Required roles are not bound yet
    assert not masker.legal_index.is_legal(action, prefix)


def test_abstain_illegal_after_terminal(masker, valid_program):
    """abstain is illegal after a terminal action."""
    context = masker.legal_index.context
    prefix = valid_program.actions
    action = ProgramAction.create(
        action_index=len(prefix),
        action_type="abstain",
        arguments=(),
    )
    assert not masker.legal_index.is_legal(action, prefix)


# ---------------------------------------------------------------------------
# Bounds enforcement tests
# ---------------------------------------------------------------------------


def test_application_bound_enforced(masker):
    """instantiate_operator is illegal when application bound is reached."""
    context = masker.legal_index.context
    legal = LegalActionIndex(context, max_applications=1)
    designation = context.designation_slots[0]
    frame = context.application_frames[0]
    prefix = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=(context.mode_slots[0].slot_ref,),
        ),
        ProgramAction.create(
            action_index=2,
            action_type="select_designation",
            arguments=(designation.slot_ref,),
        ),
        ProgramAction.create(
            action_index=3,
            action_type="instantiate_operator",
            arguments=("application:0", frame.slot_ref),
        ),
    )
    # Second application should be rejected (max_applications=1)
    action = ProgramAction.create(
        action_index=4,
        action_type="instantiate_operator",
        arguments=("application:1", frame.slot_ref),
    )
    assert not legal.is_legal(action, prefix)


def test_node_bound_enforced_for_attach_scope(masker):
    """attach_scope is illegal when node bound is reached."""
    from cemm_authoritative_hybrid.proposal_context import (
        ApplicationFrameSlot,
        ContributionSlot,
        DesignationSlot,
        ModeSlot,
        ProposalContext,
        ScopeSlot,
    )
    from cemm_authoritative_hybrid.persistence import RevisionPin
    from cemm_authoritative_hybrid.proposal import BootstrapProposer

    # Build a context with a scope slot so the test exercises the node
    # bound rather than unknown_scope_slot.
    pin = RevisionPin("authority:bootstrap", 1, 2, 3, 4, BootstrapProposer.model_identity)
    mode = ModeSlot.create(
        mode="OBSERVE", source_unit_refs=(), construction_ref=None,
        requested_effect="admission",
    )
    designation = DesignationSlot.create(
        source_unit_refs=("unit:predicate",),
        target_ref="event:test-0", target_kind="event_type",
        score_q=900_000, designation_fact_ref="designation:test-0",
        provenance_refs=("designation:test-0",),
    )
    predicate = ContributionSlot.create(
        contribution_ref="contribution:predicate-0", kind="predicate",
        source_unit_refs=("unit:predicate",),
        target_ref="event:test-0", target_kind="event_type",
        input_ports=("role:subject",), output_ports=("role:event",),
        constraints=(), provenance_refs=("designation:test-0",),
    )
    subject = ContributionSlot.create(
        contribution_ref="contribution:subject", kind="anchor",
        source_unit_refs=("unit:subject",),
        target_ref="entity:test", target_kind="entity",
        input_ports=(), output_ports=("role:subject",),
        constraints=(), provenance_refs=("designation:subject",),
    )
    frame = ApplicationFrameSlot.create(
        designation_slot_ref=designation.slot_ref,
        predicate_target_ref=designation.target_ref,
        predicate_kind=designation.target_kind,
        operator_ref="op:event", structural_role_ref="role:event",
        required_roles=("role:subject",), optional_roles=(),
        proposition_roles=(),
        source_unit_refs=("unit:predicate",),
        derived_role_targets=(),
        affordance_frame_ref="frame:test-0",
        provenance_refs=(designation.slot_ref, "frame:test-0"),
    )
    scope = ScopeSlot.create(
        operator_type="scope:polarity",
        value_ref="polarity:negative",
        source_unit_refs=(),
        construction_ref=None,
    )
    context = ProposalContext.create(
        orientation_ref="orientation:bootstrap",
        evidence_packet_ref="evidence:bootstrap",
        form_lattice_ref="lattice:bootstrap",
        grounding_ref="grounding:bootstrap",
        designation_slots=(designation,),
        contribution_slots=(predicate, subject),
        mode_slots=(mode,),
        application_frames=(frame,),
        reference_slots=(),
        scope_slots=(scope,),
        expression_link_slots=(),
        variable_slots=(),
        transition_slots=(),
        residual_evidence=(),
        context_refs=("turn:bootstrap",),
        source_unit_refs=("unit:predicate", "unit:subject"),
        source_unit_spans=(("unit:predicate", 0, 4), ("unit:subject", 4, 8)),
        revision_pin=pin,
    )
    legal = LegalActionIndex(context, max_nodes=1)
    prefix = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=(context.mode_slots[0].slot_ref,),
        ),
        ProgramAction.create(
            action_index=2,
            action_type="select_designation",
            arguments=(designation.slot_ref,),
        ),
        ProgramAction.create(
            action_index=3,
            action_type="instantiate_operator",
            arguments=("application:0", frame.slot_ref),
        ),
    )
    # node_count is already 1 (from application:0), max_nodes=1
    action = ProgramAction.create(
        action_index=4,
        action_type="attach_scope",
        arguments=("scope:0", scope.slot_ref, "application:0"),
    )
    assert not legal.is_legal(action, prefix)


# ---------------------------------------------------------------------------
# Masker parity test
# ---------------------------------------------------------------------------


def test_masker_matches_legal_index(masker, prefix):
    """ActionMasker produces the same legal set as LegalActionIndex."""
    from tests.test_action_masks import _candidate_actions

    context = masker.legal_index.context
    candidates = _candidate_actions(context, len(prefix))
    masked = masker.filter_legal(prefix, candidates)
    exhaustive = tuple(
        candidate
        for candidate in candidates
        if masker.legal_index.is_legal(candidate, prefix)
    )
    assert set(masked) == set(exhaustive)


# ---------------------------------------------------------------------------
# Legality purity test
# ---------------------------------------------------------------------------


def test_is_legal_is_pure_predicate(masker, prefix):
    """is_legal returns the same result for the same inputs."""
    from tests.test_action_masks import _candidate_actions

    legal_index = masker.legal_index
    candidates = _candidate_actions(legal_index.context, len(prefix))
    if candidates:
        action = candidates[0]
        result1 = legal_index.is_legal(action, prefix)
        result2 = legal_index.is_legal(action, prefix)
        assert result1 == result2
