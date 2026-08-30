from __future__ import annotations

from types import SimpleNamespace

import pytest

from cemm_authoritative_hybrid.r4_derivation_compiler import (
    DerivationCompilationError,
    ReviewedDerivationCompiler,
)
from cemm_authoritative_hybrid.r4_expansion import ExpandedCase
from cemm_authoritative_hybrid.r4_supervision import (
    BlueprintAction,
    DerivationBlueprint,
    GroundedSelectorBinding,
    SourceAssignmentBlueprint,
    SourceAssignmentEntry,
    SourceSpan,
    StructuralSelectorBinding,
)
from cemm_authoritative_hybrid.verifier_reconstruction import (
    reconstruct_expected_expression,
)


def _semantic_case(context, expression) -> ExpandedCase:
    case = object.__new__(ExpandedCase)
    for name, value in {
        "case_ref": "expanded_case_v2:0123456789abcdef01234567",
        "surface_ref": "reviewed_surface:0123456789abcdef01234567",
        "surface": "test one",
        "contract": SimpleNamespace(
            revision_pin=context.revision_pin,
            expected_expressions=(expression,),
        ),
    }.items():
        object.__setattr__(case, name, value)
    return case


def _blueprint(case, context, expression) -> DerivationBlueprint:
    predicate = context.contribution_slots[0]
    subject = context.contribution_slots[1]
    designation = context.designation_slots[0]
    frame = context.application_frames[0]
    mode = context.mode_slots[0]
    selectors = (
        StructuralSelectorBinding.create(
            selector_handle=0,
            selector_kind="context_slot",
            value_ref=context.context_ref,
        ),
        StructuralSelectorBinding.create(
            selector_handle=1,
            selector_kind="mode_slot",
            value_ref=mode.slot_ref,
        ),
        GroundedSelectorBinding.create(
            selector_handle=2,
            selector_kind="designation_slot",
            source_case_ref=case.case_ref,
            surface_ref=case.surface_ref,
            graph_component_ref=designation.slot_ref,
            semantic_kind_ref="semantic_kind:event_type",
            spans=(SourceSpan.create(surface_ref=case.surface_ref, start=0, end=4),),
            source_selector_kind="source_unit",
            source_selector_ref="unit:predicate",
        ),
        StructuralSelectorBinding.create(
            selector_handle=3,
            selector_kind="local_node",
            value_ref="application:main",
        ),
        GroundedSelectorBinding.create(
            selector_handle=4,
            selector_kind="frame_slot",
            source_case_ref=case.case_ref,
            surface_ref=case.surface_ref,
            graph_component_ref=frame.slot_ref,
            semantic_kind_ref="semantic_kind:event_type",
            spans=(SourceSpan.create(surface_ref=case.surface_ref, start=0, end=4),),
            source_selector_kind="contribution",
            source_selector_ref=predicate.slot_ref,
        ),
        StructuralSelectorBinding.create(
            selector_handle=5,
            selector_kind="role_ref",
            value_ref="role:subject",
        ),
        GroundedSelectorBinding.create(
            selector_handle=6,
            selector_kind="contribution_slot",
            source_case_ref=case.case_ref,
            surface_ref=case.surface_ref,
            graph_component_ref=subject.slot_ref,
            semantic_kind_ref="semantic_kind:entity",
            spans=(SourceSpan.create(surface_ref=case.surface_ref, start=4, end=8),),
            source_selector_kind="contribution",
            source_selector_ref=subject.slot_ref,
        ),
    )
    actions = (
        BlueprintAction.create(action_index=0, action_type="select_context", selector_handles=(0,)),
        BlueprintAction.create(action_index=1, action_type="select_mode", selector_handles=(1,)),
        BlueprintAction.create(action_index=2, action_type="select_designation", selector_handles=(2,)),
        BlueprintAction.create(action_index=3, action_type="instantiate_operator", selector_handles=(3, 4)),
        BlueprintAction.create(action_index=4, action_type="bind_role", selector_handles=(3, 5, 6)),
        BlueprintAction.create(action_index=5, action_type="complete_program", selector_handles=()),
    )
    assignments = SourceAssignmentBlueprint.create(
        observed_source_unit_refs=context.source_unit_refs,
        assignments=(
            SourceAssignmentEntry.create(
                source_unit_ref="unit:predicate",
                contribution_slot_ref=predicate.slot_ref,
                contribution_kind="predicate",
                assignment_kind="predicate",
                target_action_index=3,
                target_role_ref=None,
                residual_kind=None,
                critical=False,
            ),
            SourceAssignmentEntry.create(
                source_unit_ref="unit:subject",
                contribution_slot_ref=subject.slot_ref,
                contribution_kind="anchor",
                assignment_kind="role",
                target_action_index=4,
                target_role_ref="role:subject",
                residual_kind=None,
                critical=False,
            ),
        ),
    )
    return DerivationBlueprint.create(
        selector_bindings=selectors,
        actions=actions,
        root_local_refs=("application:main",),
        expected_expression_ref=expression.expression_ref,
        source_assignment_blueprint=assignments,
    )


@pytest.fixture
def derivation_fixture(proposal_context, valid_program):
    expression = reconstruct_expected_expression(valid_program, proposal_context)
    assert expression is not None
    case = _semantic_case(proposal_context, expression)
    return case, proposal_context, _blueprint(case, proposal_context, expression)


def test_derivation_compiler_reconstructs_source_expression(derivation_fixture):
    case, context, blueprint = derivation_fixture
    result = ReviewedDerivationCompiler().compile(
        case=case,
        context=context,
        blueprint=blueprint,
    )
    assert result.expression == case.contract.expected_expressions[0]
    assert result.expression.expression_ref == blueprint.expected_expression_ref
    assert result.program.program_ref != result.expression.expression_ref
    assert result.assigned_source_unit_refs == context.source_unit_refs
    assert result.residual_source_unit_refs == ()


def test_derivation_compiler_rejects_wrong_expression_ref(derivation_fixture):
    case, context, blueprint = derivation_fixture
    forged = object.__new__(DerivationBlueprint)
    for name, value in blueprint.__dict__.items():
        object.__setattr__(forged, name, value)
    object.__setattr__(
        forged,
        "expected_expression_ref",
        "expression:ffffffffffffffffffffffff",
    )
    with pytest.raises(DerivationCompilationError, match="expected expression"):
        ReviewedDerivationCompiler().compile(
            case=case,
            context=context,
            blueprint=forged,
        )


def test_derivation_compiler_does_not_import_runtime_compilers(
    derivation_fixture, monkeypatch: pytest.MonkeyPatch
):
    import cemm_authoritative_hybrid.recursive_compiler as recursive_compiler

    monkeypatch.setattr(
        recursive_compiler,
        "compile_recursive",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("runtime compiler reached")
        ),
    )
    case, context, blueprint = derivation_fixture
    result = ReviewedDerivationCompiler().compile(
        case=case, context=context, blueprint=blueprint
    )
    assert result.expression == case.contract.expected_expressions[0]
