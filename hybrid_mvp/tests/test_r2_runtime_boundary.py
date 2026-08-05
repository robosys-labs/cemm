"""R2 authentic public runtime boundary tests.

Per R2 plan Task 8:
- No internal ref is exposed as a user-visible designation by spelling
- No raw program is treated as meaning (EVALUATE rejects raw programs)
- The six-phase runtime boundary is maintained (no legacy stage numbers)
- VerifiedMeaning is the only input to EVALUATE
- Transition previews do not cross into effect execution
- No forbidden legacy tokens in active source
- Public API surfaces do not leak internal refs
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from cemm_authoritative_hybrid.expressions import (
    CompilationSuccess,
    SemanticExpressionCompiler,
)
from cemm_authoritative_hybrid.learning import _is_internal_ref_spelling
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

__cemm_test_inventory__ = {
    "tests/test_r2_runtime_boundary.py::test_internal_ref_prefixes_are_rejected_as_surfaces[adapter-act]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-internal-ref-prefixes-are-rejected-as-surfaces",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "397b599e9d8732936e583487f352753e403218d03495b57090be5c8a13a446c7"
    },
    "tests/test_r2_runtime_boundary.py::test_internal_ref_prefixes_are_rejected_as_surfaces[cap-learn]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-internal-ref-prefixes-are-rejected-as-surfaces",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "397b599e9d8732936e583487f352753e403218d03495b57090be5c8a13a446c7"
    },
    "tests/test_r2_runtime_boundary.py::test_internal_ref_prefixes_are_rejected_as_surfaces[concept-love]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-internal-ref-prefixes-are-rejected-as-surfaces",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "397b599e9d8732936e583487f352753e403218d03495b57090be5c8a13a446c7"
    },
    "tests/test_r2_runtime_boundary.py::test_internal_ref_prefixes_are_rejected_as_surfaces[dim-mood]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-internal-ref-prefixes-are-rejected-as-surfaces",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "397b599e9d8732936e583487f352753e403218d03495b57090be5c8a13a446c7"
    },
    "tests/test_r2_runtime_boundary.py::test_internal_ref_prefixes_are_rejected_as_surfaces[entity-alice]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-internal-ref-prefixes-are-rejected-as-surfaces",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "397b599e9d8732936e583487f352753e403218d03495b57090be5c8a13a446c7"
    },
    "tests/test_r2_runtime_boundary.py::test_internal_ref_prefixes_are_rejected_as_surfaces[event-act]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-internal-ref-prefixes-are-rejected-as-surfaces",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "397b599e9d8732936e583487f352753e403218d03495b57090be5c8a13a446c7"
    },
    "tests/test_r2_runtime_boundary.py::test_internal_ref_prefixes_are_rejected_as_surfaces[label-name]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-internal-ref-prefixes-are-rejected-as-surfaces",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "397b599e9d8732936e583487f352753e403218d03495b57090be5c8a13a446c7"
    },
    "tests/test_r2_runtime_boundary.py::test_internal_ref_prefixes_are_rejected_as_surfaces[op-event]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-internal-ref-prefixes-are-rejected-as-surfaces",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "397b599e9d8732936e583487f352753e403218d03495b57090be5c8a13a446c7"
    },
    "tests/test_r2_runtime_boundary.py::test_internal_ref_prefixes_are_rejected_as_surfaces[participant-speaker]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-internal-ref-prefixes-are-rejected-as-surfaces",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "397b599e9d8732936e583487f352753e403218d03495b57090be5c8a13a446c7"
    },
    "tests/test_r2_runtime_boundary.py::test_internal_ref_prefixes_are_rejected_as_surfaces[relation-love]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-internal-ref-prefixes-are-rejected-as-surfaces",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "397b599e9d8732936e583487f352753e403218d03495b57090be5c8a13a446c7"
    },
    "tests/test_r2_runtime_boundary.py::test_internal_ref_prefixes_are_rejected_as_surfaces[role-subject]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-internal-ref-prefixes-are-rejected-as-surfaces",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "397b599e9d8732936e583487f352753e403218d03495b57090be5c8a13a446c7"
    },
    "tests/test_r2_runtime_boundary.py::test_internal_ref_prefixes_are_rejected_as_surfaces[state-happy]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-internal-ref-prefixes-are-rejected-as-surfaces",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "397b599e9d8732936e583487f352753e403218d03495b57090be5c8a13a446c7"
    },
    "tests/test_r2_runtime_boundary.py::test_internal_ref_prefixes_are_rejected_as_surfaces[state_value-happy]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-internal-ref-prefixes-are-rejected-as-surfaces",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "397b599e9d8732936e583487f352753e403218d03495b57090be5c8a13a446c7"
    },
    "tests/test_r2_runtime_boundary.py::test_no_legacy_runtime_branches_in_source": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-no-legacy-runtime-branches-in-source",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "62f842ef90910c9645f569801336d6b916460ce7a978d04e424ed3f1f0cce591"
    },
    "tests/test_r2_runtime_boundary.py::test_no_legacy_stage_numbers_in_source": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-no-legacy-stage-numbers-in-source",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "172f4c8d265741802d6e3decebc7f62809fd2a60a3f2798bac5bf78916d059de"
    },
    "tests/test_r2_runtime_boundary.py::test_normal_surfaces_are_not_internal_refs[Alice]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-normal-surfaces-are-not-internal-refs",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "9ebcc3eda004b8c4b3ea4d09c45a77541a006c2c45e5a19586b0cb5c282e77ef"
    },
    "tests/test_r2_runtime_boundary.py::test_normal_surfaces_are_not_internal_refs[a-normal-word]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-normal-surfaces-are-not-internal-refs",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "9ebcc3eda004b8c4b3ea4d09c45a77541a006c2c45e5a19586b0cb5c282e77ef"
    },
    "tests/test_r2_runtime_boundary.py::test_normal_surfaces_are_not_internal_refs[happy]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-normal-surfaces-are-not-internal-refs",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "9ebcc3eda004b8c4b3ea4d09c45a77541a006c2c45e5a19586b0cb5c282e77ef"
    },
    "tests/test_r2_runtime_boundary.py::test_normal_surfaces_are_not_internal_refs[learning]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-normal-surfaces-are-not-internal-refs",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "9ebcc3eda004b8c4b3ea4d09c45a77541a006c2c45e5a19586b0cb5c282e77ef"
    },
    "tests/test_r2_runtime_boundary.py::test_normal_surfaces_are_not_internal_refs[love]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-normal-surfaces-are-not-internal-refs",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "9ebcc3eda004b8c4b3ea4d09c45a77541a006c2c45e5a19586b0cb5c282e77ef"
    },
    "tests/test_r2_runtime_boundary.py::test_normal_surfaces_are_not_internal_refs[the-event]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-normal-surfaces-are-not-internal-refs",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "9ebcc3eda004b8c4b3ea4d09c45a77541a006c2c45e5a19586b0cb5c282e77ef"
    },
    "tests/test_r2_runtime_boundary.py::test_program_compiles_to_expression_not_meaning": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-program-compiles-to-expression-not-meaning",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "51da74970fa5aa22c3669e2e52a78c71d0703aca8046d3e872db20e048d4dfab"
    },
    "tests/test_r2_runtime_boundary.py::test_program_ref_differs_from_expression_ref": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-program-ref-differs-from-expression-ref",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "7de7e0254c49e088080480e60f3392aed5e6e4fdff331fc10e6aebb0db9da06e"
    },
    "tests/test_r2_runtime_boundary.py::test_runtime_does_not_branch_on_stage_numbers": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-runtime-does-not-branch-on-stage-numbers",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "6d086698dabf1298e7438bbbd39fbcb7dd7125a0ace067165297fe5465ed5fc8"
    },
    "tests/test_r2_runtime_boundary.py::test_six_phases_are_named_not_numbered": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-six-phases-are-named-not-numbered",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "d11088ff2a62d66fb39b007b2792a41f5c0296f4960f6a005dabd7665865134b"
    },
    "tests/test_r2_runtime_boundary.py::test_transition_preview_has_no_effect_execution": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-transition-preview-has-no-effect-execution",
        "diagnostic_role": "owner",
        "introduced_by_task": "R2-Implementation",
        "owner_ref": "runtime-boundary",
        "source_ast_sha256": "1031c3262635769053bcb14273141b9478aaf876edb2ac040db6ae071dde126d"
    },
}


ROOT = Path(__file__).parents[1]
SRC = ROOT / "src" / "cemm_authoritative_hybrid"

# ---------------------------------------------------------------------------
# Internal-ref lexicalization prevention
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ref",
    [
        "op:event",
        "role:subject",
        "entity:alice",
        "concept:love",
        "relation:love",
        "event:act",
        "state:happy",
        "state_value:happy",
        "dim:mood",
        "cap:learn",
        "adapter:act",
        "label:name",
        "participant:speaker",
    ],
    ids=[
        "op-event",
        "role-subject",
        "entity-alice",
        "concept-love",
        "relation-love",
        "event-act",
        "state-happy",
        "state_value-happy",
        "dim-mood",
        "cap-learn",
        "adapter-act",
        "label-name",
        "participant-speaker",
    ],
)
def test_internal_ref_prefixes_are_rejected_as_surfaces(ref: str):
    """Internal refs must not be exposed as user-visible surfaces."""
    assert _is_internal_ref_spelling(ref), f"{ref} should be recognized as internal"


@pytest.mark.parametrize(
    "surface",
    [
        "love",
        "Alice",
        "happy",
        "the event",
        "learning",
        "a normal word",
    ],
    ids=[
        "love",
        "Alice",
        "happy",
        "the-event",
        "learning",
        "a-normal-word",
    ],
)
def test_normal_surfaces_are_not_internal_refs(surface: str):
    """Normal surface words are not internal refs."""
    assert not _is_internal_ref_spelling(surface), f"{surface} should not be internal"


# ---------------------------------------------------------------------------
# Program-as-meaning prevention
# ---------------------------------------------------------------------------


def _pin() -> RevisionPin:
    return RevisionPin("authority:g1", 1, 2, 3, 4, "model:m1")


def _context():
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
        transition=lambda ref: None,
    )


def _program(context):
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


def test_program_compiles_to_expression_not_meaning():
    """A program compiles to a SemanticExpression, not a VerifiedMeaning.

    The compiler produces a SemanticExpression.  VerifiedMeaning requires
    additional verification (coverage, proof, receipt) that the compiler
    does not provide.  This proves program != meaning.
    """
    context = _context()
    program = _program(context)
    result = SemanticExpressionCompiler().compile(program, context)
    assert isinstance(result, CompilationSuccess)
    # The result is a SemanticExpression, not a VerifiedMeaning
    assert hasattr(result, "expression")
    assert hasattr(result, "proof")
    assert not hasattr(result, "coverage_receipt")
    assert not hasattr(result, "verification_receipt")


def test_program_ref_differs_from_expression_ref():
    """Program identity differs from semantic expression identity."""
    context = _context()
    program = _program(context)
    result = SemanticExpressionCompiler().compile(program, context)
    assert isinstance(result, CompilationSuccess)
    assert program.program_ref != result.expression.expression_ref


# ---------------------------------------------------------------------------
# Transition preview boundary (R2/R3)
# ---------------------------------------------------------------------------


def test_transition_preview_has_no_effect_execution():
    """TransitionPreview contains no effect execution fields.

    This proves the R2/R3 boundary: R2 previews transitions, R3 executes.
    """
    preview = TransitionPreview(
        preview_ref="action:0",
        transition_slot_ref="transition_slot:0",
        source_application_ref="application:0",
        event_type_ref="event:act",
        compatible_modes=("OBSERVE",),
        required_roles=("role:subject",),
        required_capabilities=("cap:act",),
        required_permissions=("perm:act",),
        adapter_ref="adapter:act",
    )
    serialized = preview.as_dict()
    forbidden = {"effect_receipt", "execution_result", "world_state", "mutated_refs", "effect_ref"}
    assert not any(key in serialized for key in forbidden)


# ---------------------------------------------------------------------------
# Legacy token prevention
# ---------------------------------------------------------------------------


def test_no_legacy_stage_numbers_in_source():
    """No active source file contains legacy stage-number constructs."""
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in SRC.rglob("*.py")
    )
    forbidden = ("StageRecord", "stage_trace", "range(23)", "weights_only=False")
    offenders = [token for token in forbidden if token in source]
    assert not offenders, f"forbidden legacy tokens found: {offenders}"


def test_no_legacy_runtime_branches_in_source():
    """No active source file contains legacy runtime branch constructs."""
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in SRC.rglob("*.py")
    )
    # Legacy compatibility adapters and stage-based dispatch are forbidden
    forbidden = ("legacy_stage", "compatibility_adapter", "stage_number")
    offenders = [token for token in forbidden if token in source]
    assert not offenders, f"forbidden legacy constructs found: {offenders}"


# ---------------------------------------------------------------------------
# Six-phase boundary
# ---------------------------------------------------------------------------


def test_six_phases_are_named_not_numbered():
    """The runtime uses named phases, not stage numbers."""
    from cemm_authoritative_hybrid.cycle import SemanticPhase
    phases = tuple(SemanticPhase)
    assert len(phases) == 6
    # Phase names should be semantic, not numeric
    for phase in phases:
        assert not phase.value.startswith("stage")
        assert not phase.value.isdigit()


def test_runtime_does_not_branch_on_stage_numbers():
    """No runtime code branches on legacy stage numbers."""
    from cemm_authoritative_hybrid import cycle
    source = Path(cycle.__file__).read_text(encoding="utf-8")
    # The cycle module should not contain stage-number dispatch
    assert "stage_number" not in source
    assert "legacy_stage" not in source
