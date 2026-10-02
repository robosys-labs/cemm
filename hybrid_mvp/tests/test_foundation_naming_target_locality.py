"""Reviewed naming frames cannot borrow another clause's grounded target."""
import pytest

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.coverage import CoverageVerifier
from cemm_authoritative_hybrid.expressions import CompilationFailure, CompilationSuccess
from cemm_authoritative_hybrid.programs import ProgramAction, SemanticSwitchProgram, SourceAssignment
from cemm_authoritative_hybrid.recursive_compiler import compile_recursive
from cemm_authoritative_hybrid.recursive_composer import RecursiveComposer
from cemm_authoritative_hybrid.recursive_composer._expand import iter_choices
from cemm_authoritative_hybrid.verifier_reconstruction import reconstruct_expected_expression
from tests.test_foundation_learning_proposal import ROOT


SURFACE = "learn velnora means mother and learn senvora means likes"


@pytest.fixture
def naming_context(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "naming.db")
    try:
        _, context = runtime.orient("session:naming-locality", SURFACE)
        assert {"concept:mother", "rel:likes"} <= {row.target_ref for row in context.designation_slots}
        yield context
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def _frames(context):
    frames = tuple(sorted((frame for frame in context.application_frames
        if frame.predicate_kind == "event_type"
        and {"role:surface", "role:target"} <= set(frame.required_roles)),
        key=lambda frame: context.source_span(frame.source_unit_refs)))
    assert len(frames) == 2
    return frames


def _advance(owner, state, action_type, predicate):
    choice = next(choice for choice in iter_choices(owner, state)
        if choice.action.action_type == action_type and predicate(choice.action))
    updated = owner._apply(state, choice)
    assert updated is not None
    return updated


def _instantiate(owner, state, frame):
    state = _advance(owner, state, "select_designation",
        lambda action: action.arguments == (frame.designation_slot_ref,))
    return _advance(owner, state, "instantiate_operator",
        lambda action: action.arguments[1] == frame.slot_ref)


@pytest.mark.parametrize("index,local,foreign", (
    (0, "concept:mother", "rel:likes"),
    (1, "rel:likes", "concept:mother"),
), ids=("first-cannot-borrow-later", "second-cannot-borrow-earlier"))
def test_naming_target_choices_are_clause_local(naming_context, index, local, foreign):
    context = naming_context
    owner = RecursiveComposer(context)
    frame = _frames(context)[index]
    state = _instantiate(owner, next(iter(owner._initial_states())), frame)
    choices = tuple(choice.action for choice in iter_choices(owner, state)
        if choice.action.action_type in {"bind_role", "bind_reference"}
        and choice.action.arguments[1] == "role:target")
    targets = {((context.contribution(action.arguments[2])
        if action.action_type == "bind_role" else context.reference(action.arguments[2])).target_ref)
        for action in choices}
    assert local in targets, "own-clause grounded target must remain legal"
    assert foreign not in targets, "naming frame exposes a different clause's grounded target"


def _local_program(context):
    """Follow real composer choices; no fabricated context or coverage rows."""
    owner = RecursiveComposer(context)
    state = next(iter(owner._initial_states()))
    for frame, target, label in zip(_frames(context),
            ("concept:mother", "rel:likes"), ("velnora", "senvora"), strict=True):
        state = _instantiate(owner, state, frame)
        app_ref = next(app for app, ref in state.application_frames if ref == frame.slot_ref)
        state = _advance(owner, state, "bind_reference", lambda action:
            action.arguments[:2] == (app_ref, "role:actor")
            and context.reference(action.arguments[2]).target_ref == "participant:system")
        state = _advance(owner, state, "bind_role", lambda action:
            action.arguments[:2] == (app_ref, "role:surface")
            and context.contribution(action.arguments[2]).literal_value == label
            and ("naming_frame_ref", frame.slot_ref) in context.contribution(action.arguments[2]).constraints)
        state = _advance(owner, state, "bind_reference", lambda action:
            action.arguments[:2] == (app_ref, "role:target")
            and context.reference(action.arguments[2]).target_ref == target)
    state = _advance(owner, state, "bind_nested_application",
        lambda action: action.arguments[0] == "link")
    completed = owner._complete(state)
    assert completed is not None, "positive local program must complete with exact coverage"
    return completed.program


def _swap_target_owners(program):
    target_actions = tuple(action for action in program.actions
        if action.action_type == "bind_reference" and action.arguments[1] == "role:target")
    assert len(target_actions) == 2
    other = {target_actions[0].action_ref: target_actions[1],
        target_actions[1].action_ref: target_actions[0]}
    actions = tuple(ProgramAction.create(action_index=action.action_index,
        action_type=action.action_type,
        arguments=(*action.arguments[:2], other[action.action_ref].arguments[2])
            if action.action_ref in other else action.arguments,
        source_unit_refs=other[action.action_ref].source_unit_refs
            if action.action_ref in other else action.source_unit_refs) for action in program.actions)
    refs = {old.action_ref: new.action_ref for old, new in zip(program.actions, actions, strict=True)}
    for original, replacement in other.items():
        refs[original] = actions[replacement.action_index].action_ref
    assignments = tuple(SourceAssignment.create(source_unit_ref=row.source_unit_ref,
        contribution_slot_ref=row.contribution_slot_ref, assignment_kind=row.assignment_kind,
        target_action_ref=refs.get(row.target_action_ref, row.target_action_ref),
        target_role_ref=row.target_role_ref, residual_kind=row.residual_kind, critical=row.critical)
        for row in program.source_assignments)
    return SemanticSwitchProgram.create(orientation_ref=program.orientation_ref,
        proposal_context_ref=program.proposal_context_ref, actions=actions,
        root_refs=program.root_refs, mode_slot_ref=program.mode_slot_ref,
        goal_refs=program.goal_refs, source_unit_refs=program.source_unit_refs,
        source_assignments=assignments, revision_pin=program.revision_pin)


@pytest.mark.parametrize("owner", ("compiler", "reconstruction", "coverage"), ids=("compiler", "reconstruction", "coverage"))
def test_naming_target_swap_is_rejected_independently(naming_context, owner):
    context = naming_context
    positive = _local_program(context)
    coverage = CoverageVerifier().verify(context, positive)
    assert coverage.executable and coverage.errors == ()
    assert isinstance(compile_recursive(positive, context), CompilationSuccess)
    expected = reconstruct_expected_expression(positive, context)
    assert expected is not None
    pairs = set()
    for application in expected.applications:
        roles = {row.role_ref: row.filler for row in application.roles}
        assert application.predicate_ref == "event:learn_alias"
        assert roles["role:actor"].target_ref == "participant:system"
        pairs.add((roles["role:surface"].value, roles["role:target"].target_ref))
    assert pairs == {("velnora", "concept:mother"), ("senvora", "rel:likes")}
    swapped = _swap_target_owners(positive)
    assert SemanticSwitchProgram.from_dict(swapped.as_dict()) == swapped
    assert swapped.source_unit_refs == positive.source_unit_refs
    assert tuple(action for action in swapped.actions if action.action_type == "bind_role"
        and action.arguments[1] == "role:surface") == tuple(action for action in positive.actions
        if action.action_type == "bind_role" and action.arguments[1] == "role:surface")
    if owner == "compiler":
        assert isinstance(compile_recursive(swapped, context), CompilationFailure), (
            "compiler accepted foreign targets with correct own-frame literals")
    elif owner == "reconstruction":
        assert reconstruct_expected_expression(swapped, context) is None, (
            "independent reconstruction accepted foreign targets with correct own-frame literals")
    else:
        coverage = CoverageVerifier().verify(context, swapped)
        assert not coverage.executable
        assert any(error.code == "naming_role_owner_mismatch" for error in coverage.errors)


@pytest.mark.parametrize("owner", ("compiler", "reconstruction", "coverage"), ids=("compiler", "reconstruction", "coverage"))
def test_naming_target_missing_marker_is_denied_not_unrestricted(naming_context, owner):
    from tests.test_foundation_semantics import _membership_unchecked
    context = naming_context
    swapped = _swap_target_owners(_local_program(context))
    slots = tuple(_membership_unchecked(row, constraints=())
        if ("discourse", "definition_marker") in row.constraints else row
        for row in context.contribution_slots)
    forged = _membership_unchecked(context, contribution_slots=slots)
    if owner == "compiler":
        assert isinstance(compile_recursive(swapped, forged), CompilationFailure)
    elif owner == "reconstruction":
        assert reconstruct_expected_expression(swapped, forged) is None
    else:
        assert not CoverageVerifier().verify(forged, swapped).executable


__cemm_test_inventory__ = {
    "tests/test_foundation_naming_target_locality.py::test_naming_target_choices_are_clause_local[first-cannot-borrow-later]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-target-choices-are-clause-local-first-cannot-borrow-later",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "653f43d707a53be944aac25364d7f428d7b9850bb0e78cf249c673341d7a46af"
    },
    "tests/test_foundation_naming_target_locality.py::test_naming_target_choices_are_clause_local[second-cannot-borrow-earlier]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-target-choices-are-clause-local-second-cannot-borrow-earlier",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "653f43d707a53be944aac25364d7f428d7b9850bb0e78cf249c673341d7a46af"
    },
    "tests/test_foundation_naming_target_locality.py::test_naming_target_missing_marker_is_denied_not_unrestricted[compiler]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-target-missing-marker-is-denied-not-unrestricted-compiler",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "922dfe3fa7775234b5939212f483fb78a874f0bebd164aeaa242bb5f77387056"
    },
    "tests/test_foundation_naming_target_locality.py::test_naming_target_missing_marker_is_denied_not_unrestricted[coverage]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-target-missing-marker-is-denied-not-unrestricted-coverage",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "922dfe3fa7775234b5939212f483fb78a874f0bebd164aeaa242bb5f77387056"
    },
    "tests/test_foundation_naming_target_locality.py::test_naming_target_missing_marker_is_denied_not_unrestricted[reconstruction]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-target-missing-marker-is-denied-not-unrestricted-reconstruction",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "922dfe3fa7775234b5939212f483fb78a874f0bebd164aeaa242bb5f77387056"
    },
    "tests/test_foundation_naming_target_locality.py::test_naming_target_swap_is_rejected_independently[compiler]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-target-swap-is-rejected-independently-compiler",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "b8527cba36a06a9b23f5b2f080b6179be4d98254209dc7024f531938d910c942"
    },
    "tests/test_foundation_naming_target_locality.py::test_naming_target_swap_is_rejected_independently[coverage]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-target-swap-is-rejected-independently-coverage",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "b8527cba36a06a9b23f5b2f080b6179be4d98254209dc7024f531938d910c942"
    },
    "tests/test_foundation_naming_target_locality.py::test_naming_target_swap_is_rejected_independently[reconstruction]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-target-swap-is-rejected-independently-reconstruction",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "b8527cba36a06a9b23f5b2f080b6179be4d98254209dc7024f531938d910c942"
    }
}
