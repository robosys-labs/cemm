"""R2 transition preview boundary tests.

Per R2 plan Task 7:
- propose_transition actions produce TransitionPreview objects in receipts
- Previews record transition metadata without triggering effect execution
- Previews are empty for programs without propose_transition actions
- Previews round-trip through serialization
- The R2/R3 boundary is maintained: previews contain no executed effects
"""

from __future__ import annotations

from types import SimpleNamespace

from cemm_authoritative_hybrid.expressions import SemanticExpressionCompiler
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.programs import (
    ProgramAction,
    SemanticSwitchProgram,
    SourceAssignment,
)
from cemm_authoritative_hybrid.transition_preview import (
    TransitionPreview,
    extract_transition_previews,
)


def _pin() -> RevisionPin:
    return RevisionPin("authority:g1", 1, 2, 3, 4, "model:m1")


def _context(*, with_transition=True):
    designations = {
        "designation_slot:event": SimpleNamespace(
            slot_ref="designation_slot:event",
            target_ref="event:act",
            designation_fact_ref="designation:event",
            provenance_refs=("authority:g1",),
        ),
    }
    contributions = {
        "contribution_slot:actor": SimpleNamespace(
            slot_ref="contribution_slot:actor",
            kind="anchor",
            target_ref="entity:actor",
            literal_value=None,
            output_ports=("role:subject",),
            provenance_refs=("designation:actor",),
        ),
    }
    frames = {
        "application_frame_slot:event": SimpleNamespace(
            slot_ref="application_frame_slot:event",
            operator_ref="op:event",
            predicate_target_ref="event:act",
            required_roles=("role:subject",),
            optional_roles=(),
            proposition_roles=(),
            derived_role_targets=(),
        ),
    }
    transitions = {}
    if with_transition:
        transitions["transition_slot:act"] = SimpleNamespace(
            slot_ref="transition_slot:act",
            application_frame_ref="application_frame_slot:event",
            event_type_ref="event:act",
            compatible_modes=("OBSERVE",),
            required_roles=("role:subject",),
            required_capabilities=("cap:act",),
            required_permissions=("perm:act",),
            adapter_ref="adapter:act",
        )
    modes = {"mode_slot:observe": SimpleNamespace(slot_ref="mode_slot:observe", mode="OBSERVE")}
    return SimpleNamespace(
        context_ref="proposal_context:one",
        orientation_ref="orientation:one",
        revision_pin=_pin(),
        designation=lambda ref: designations.get(ref),
        contribution=lambda ref: contributions.get(ref),
        frame=lambda ref: frames.get(ref),
        mode_slot=lambda ref: modes.get(ref),
        reference=lambda ref: None,
        scope=lambda ref: None,
        expression_link=lambda ref: None,
        variable=lambda ref: None,
        transition=lambda ref: transitions.get(ref),
    )


def _program_with_transition(context):
    actions = [
        ProgramAction.create(action_index=0, action_type="select_context", arguments=(context.context_ref,)),
        ProgramAction.create(action_index=1, action_type="select_mode", arguments=("mode_slot:observe",)),
        ProgramAction.create(action_index=2, action_type="select_designation", arguments=("designation_slot:event",)),
        ProgramAction.create(action_index=3, action_type="instantiate_operator", arguments=("application:0", "application_frame_slot:event"), source_unit_refs=("unit:act",)),
        ProgramAction.create(action_index=4, action_type="bind_role", arguments=("application:0", "role:subject", "contribution_slot:actor"), source_unit_refs=("unit:actor",)),
        ProgramAction.create(action_index=5, action_type="propose_transition", arguments=("transition_slot:act", "application:0")),
        ProgramAction.create(action_index=6, action_type="complete_program", arguments=()),
    ]
    assignments = (
        SourceAssignment.create(source_unit_ref="unit:act", contribution_slot_ref="contribution_slot:predicate", assignment_kind="predicate", target_action_ref=actions[3].action_ref, target_role_ref=None, residual_kind=None, critical=True),
        SourceAssignment.create(source_unit_ref="unit:actor", contribution_slot_ref="contribution_slot:actor", assignment_kind="role", target_action_ref=actions[4].action_ref, target_role_ref="role:subject", residual_kind=None, critical=True),
    )
    return SemanticSwitchProgram.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        actions=tuple(actions),
        root_refs=("application:0",),
        mode_slot_ref="mode_slot:observe",
        goal_refs=("goal:act",),
        source_unit_refs=("unit:act", "unit:actor"),
        source_assignments=assignments,
        revision_pin=context.revision_pin,
    )


def _program_without_transition(context):
    actions = [
        ProgramAction.create(action_index=0, action_type="select_context", arguments=(context.context_ref,)),
        ProgramAction.create(action_index=1, action_type="select_mode", arguments=("mode_slot:observe",)),
        ProgramAction.create(action_index=2, action_type="select_designation", arguments=("designation_slot:event",)),
        ProgramAction.create(action_index=3, action_type="instantiate_operator", arguments=("application:0", "application_frame_slot:event"), source_unit_refs=("unit:act",)),
        ProgramAction.create(action_index=4, action_type="bind_role", arguments=("application:0", "role:subject", "contribution_slot:actor"), source_unit_refs=("unit:actor",)),
        ProgramAction.create(action_index=5, action_type="complete_program", arguments=()),
    ]
    assignments = (
        SourceAssignment.create(source_unit_ref="unit:act", contribution_slot_ref="contribution_slot:predicate", assignment_kind="predicate", target_action_ref=actions[3].action_ref, target_role_ref=None, residual_kind=None, critical=True),
        SourceAssignment.create(source_unit_ref="unit:actor", contribution_slot_ref="contribution_slot:actor", assignment_kind="role", target_action_ref=actions[4].action_ref, target_role_ref="role:subject", residual_kind=None, critical=True),
    )
    return SemanticSwitchProgram.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        actions=tuple(actions),
        root_refs=("application:0",),
        mode_slot_ref="mode_slot:observe",
        goal_refs=("goal:act",),
        source_unit_refs=("unit:act", "unit:actor"),
        source_assignments=assignments,
        revision_pin=context.revision_pin,
    )


def test_propose_transition_produces_preview():
    """A program with propose_transition produces a TransitionPreview."""
    context = _context()
    program = _program_with_transition(context)
    previews = extract_transition_previews(program, context)
    assert len(previews) == 1
    preview = previews[0]
    assert preview.transition_slot_ref == "transition_slot:act"
    assert preview.source_application_ref == "application:0"
    assert preview.event_type_ref == "event:act"
    assert preview.compatible_modes == ("OBSERVE",)
    assert preview.required_roles == ("role:subject",)
    assert preview.required_capabilities == ("cap:act",)
    assert preview.required_permissions == ("perm:act",)
    assert preview.adapter_ref == "adapter:act"


def test_no_transition_produces_empty_previews():
    """A program without propose_transition produces no previews."""
    context = _context()
    program = _program_without_transition(context)
    previews = extract_transition_previews(program, context)
    assert len(previews) == 0


def test_transition_preview_round_trips():
    """TransitionPreview survives serialization round-trip."""
    context = _context()
    program = _program_with_transition(context)
    previews = extract_transition_previews(program, context)
    assert len(previews) == 1
    preview = previews[0]
    serialized = preview.as_dict()
    restored = TransitionPreview.from_dict(serialized)
    assert restored == preview


def test_transition_preview_has_no_executed_effects():
    """TransitionPreview contains only metadata, no executed effects.

    This is the R2/R3 boundary: R2 previews transitions, R3 executes them.
    The preview must not contain any effect receipts, execution results,
    or world-state mutations.
    """
    context = _context()
    program = _program_with_transition(context)
    previews = extract_transition_previews(program, context)
    assert len(previews) == 1
    preview = previews[0]
    # The preview only contains metadata fields, not execution results
    serialized = preview.as_dict()
    forbidden_keys = {"effect_receipt", "execution_result", "world_state", "mutated_refs"}
    assert not any(key in serialized for key in forbidden_keys)


def test_invalid_transition_slot_produces_no_preview():
    """An invalid transition slot produces no preview (silently skipped)."""
    context = _context(with_transition=False)
    program = _program_with_transition(context)
    previews = extract_transition_previews(program, context)
    assert len(previews) == 0


def test_compiler_admits_propose_transition():
    """The recursive compiler admits propose_transition actions."""
    context = _context()
    program = _program_with_transition(context)
    result = SemanticExpressionCompiler().compile(program, context)
    from cemm_authoritative_hybrid.expressions import CompilationFailure, CompilationSuccess
    assert isinstance(result, CompilationSuccess), f"expected success, got {result.code if isinstance(result, CompilationFailure) else type(result)}"
