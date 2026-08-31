from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.r4_derivation_compiler import (
    DerivationCompilationError,
    ReviewedDerivationCompiler,
)
from cemm_authoritative_hybrid.r4_realization_compiler import (
    RealizationCompilationError,
    ReviewedRealizationCompiler,
)
import cemm_authoritative_hybrid.r4_mutation_compiler as mutation_compiler_module
from cemm_authoritative_hybrid.r4_expansion import ExpandedCase
from cemm_authoritative_hybrid.r4_supervision import (
    BlueprintAction,
    DerivationBlueprint,
    DesignationAlignment,
    ExpressionSetResponseSubject,
    GroundedSelectorBinding,
    LiteralAlignment,
    ProposalTarget,
    RealizationBinding,
    RealizationRow,
    RealizationSlot,
    SourceAssignmentBlueprint,
    SourceAssignmentEntry,
    SourceSpan,
    StructuralSelectorBinding,
    TypedAbstention,
    TypedGapResponseSubject,
    VerificationRejection,
    VerifierRejectionResponseSubject,
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
        "language": "en",
        "contract": SimpleNamespace(
            revision_pin=context.revision_pin,
            expected_expressions=(expression,),
            expected_response=SimpleNamespace(
                discourse_action="answer_state",
                polarity_ref="polarity:positive",
                modality_ref="modality:actual",
                epistemic_status_ref="epistemic_status:supported",
                permitted_omissions=(),
            ),
        ),
    }.items():
        object.__setattr__(case, name, value)
    return case


def _realization_fixture(case, expression, blueprint, linked_authority):
    proposal = ProposalTarget.create(
        source_case_ref=case.case_ref,
        target_kind="derive",
        expected_expression_refs=(expression.expression_ref,),
        match_policy="exact",
        expected_expression_relation="single",
        derivations=(blueprint,),
        abstention=None,
        verification_rejection=None,
        review_refs=("source_review:0123456789abcdef01234567",),
    )
    subject = ExpressionSetResponseSubject.create(
        expected_expression_relation="single",
        expression_refs=(expression.expression_ref,),
    )
    fact = linked_authority.designations.facts_for_surface("lamp", "en")[0]
    slot = RealizationSlot.create(
        slot_ref="response_slot:subject",
        semantic_ref=fact.target_ref,
        required=True,
        qualifier_refs=("qualifier:definite",),
    )
    row = RealizationRow.create(
        source_case_ref=case.case_ref,
        response_subject=subject,
        bindings=(
            RealizationBinding.create(
                binding_key_ref="binding_key:subject",
                semantic_ref=fact.target_ref,
            ),
        ),
        discourse_action_ref="response_action:answer_state",
        polarity_ref="polarity:positive",
        modality_ref="modality:actual",
        epistemic_status_ref="epistemic_status:supported",
        output_speaker_ref="participant:system",
        output_addressee_ref="participant:user",
        authorized_surface="lamp",
        language="en",
        semantic_slots=(slot,),
        alignments=(
            DesignationAlignment.create(
                slot_ref=slot.slot_ref,
                designation_fact_ref=fact.designation_fact_ref,
                surface_start=0,
                surface_end=4,
            ),
        ),
        review_refs=("source_review:0123456789abcdef01234567",),
    )
    return proposal, row


def _forge(value, **changes):
    forged = object.__new__(type(value))
    for name, current in value.__dict__.items():
        object.__setattr__(forged, name, current)
    for name, current in changes.items():
        object.__setattr__(forged, name, current)
    return forged


def _safe_case(case_ref, surface, expected_response):
    case = object.__new__(ExpandedCase)
    for name, value in {
        "case_ref": case_ref,
        "surface_ref": stable_ref("reviewed_surface", {"surface": surface}),
        "surface": surface,
        "language": "en",
        "contract": SimpleNamespace(expected_response=expected_response),
    }.items():
        object.__setattr__(case, name, value)
    return case


def _safe_row(case, proposal, subject, surface, slot_ref, semantic_ref):
    review_refs = proposal.review_refs
    slot = RealizationSlot.create(
        slot_ref=slot_ref,
        semantic_ref=semantic_ref,
        required=True,
        qualifier_refs=(),
    )
    return RealizationRow.create(
        source_case_ref=case.case_ref,
        response_subject=subject,
        bindings=(),
        discourse_action_ref=(
            f"response_action:{case.contract.expected_response.discourse_action}"
        ),
        polarity_ref=case.contract.expected_response.polarity_ref,
        modality_ref=case.contract.expected_response.modality_ref,
        epistemic_status_ref=case.contract.expected_response.epistemic_status_ref,
        output_speaker_ref="participant:system",
        output_addressee_ref="participant:user",
        authorized_surface=surface,
        language=case.language,
        semantic_slots=(slot,),
        alignments=(
            LiteralAlignment.create(
                slot_ref=slot.slot_ref,
                literal_source_ref=stable_ref(
                    "reviewed_literal",
                    {
                        "literal": surface,
                        "language": case.language,
                        "review_refs": list(review_refs),
                    },
                ),
                surface_start=0,
                surface_end=len(surface),
            ),
        ),
        review_refs=review_refs,
    )


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


def test_realization_compiler_reconstructs_complete_signature(
    derivation_fixture, linked_authority
):
    case, _context, blueprint = derivation_fixture
    expression = case.contract.expected_expressions[0]
    proposal, row = _realization_fixture(
        case, expression, blueprint, linked_authority
    )

    result = ReviewedRealizationCompiler(linked_authority).compile(
        case=case,
        proposal=proposal,
        row=row,
    )

    assert result.response_signature_ref == row.response_signature_ref
    assert result.covered_slot_refs == tuple(slot.slot_ref for slot in row.semantic_slots)
    assert result.omitted_slot_refs == ()
    assert result.authorized_surface == row.authorized_surface


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("polarity_ref", "polarity:negative"),
        ("modality_ref", "modality:possible"),
        ("epistemic_status_ref", "epistemic_status:unknown"),
        ("output_speaker_ref", "participant:user"),
        ("output_addressee_ref", "participant:system"),
        ("authorized_surface", "shade"),
        ("language", "fr"),
    ],
    ids=(
        "polarity",
        "modality",
        "epistemic",
        "speaker",
        "addressee",
        "designation-surface",
        "language",
    ),
)
def test_realization_compiler_rejects_semantic_drift(
    derivation_fixture, linked_authority, field, replacement
):
    case, _context, blueprint = derivation_fixture
    expression = case.contract.expected_expressions[0]
    proposal, row = _realization_fixture(
        case, expression, blueprint, linked_authority
    )
    forged = _forge(row, **{field: replacement})

    with pytest.raises(RealizationCompilationError):
        ReviewedRealizationCompiler(linked_authority).compile(
            case=case, proposal=proposal, row=forged
        )


def test_realization_compiler_rejects_unowned_literal(
    derivation_fixture, linked_authority
):
    case, _context, blueprint = derivation_fixture
    expression = case.contract.expected_expressions[0]
    proposal, row = _realization_fixture(
        case, expression, blueprint, linked_authority
    )
    literal = LiteralAlignment.create(
        slot_ref=row.semantic_slots[0].slot_ref,
        literal_source_ref=stable_ref("reviewed_literal", {"unowned": True}),
        surface_start=0,
        surface_end=4,
    )
    forged = _forge(row, alignments=(literal,))

    with pytest.raises(RealizationCompilationError, match="literal"):
        ReviewedRealizationCompiler(linked_authority).compile(
            case=case, proposal=proposal, row=forged
        )


def test_realization_compiler_does_not_call_runtime_realization(
    derivation_fixture, linked_authority, monkeypatch: pytest.MonkeyPatch
):
    import cemm_authoritative_hybrid.realization as runtime_realization

    monkeypatch.setattr(
        runtime_realization.NeuralConstrainedRealizer,
        "realize",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("runtime realizer reached")
        ),
    )
    monkeypatch.setattr(
        runtime_realization.RealizationVerifier,
        "verify",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("runtime realization verifier reached")
        ),
    )
    case, _context, blueprint = derivation_fixture
    expression = case.contract.expected_expressions[0]
    proposal, row = _realization_fixture(
        case, expression, blueprint, linked_authority
    )

    result = ReviewedRealizationCompiler(linked_authority).compile(
        case=case, proposal=proposal, row=row
    )
    assert result.authorized_surface == "lamp"


@pytest.mark.parametrize(
    "target_kind",
    ["abstain", "verification_rejection"],
    ids=("gap", "rejection"),
)
def test_realization_compiler_requires_independently_reviewed_safe_surface(
    linked_authority, target_kind
):
    review_refs = ("source_review:0123456789abcdef01234567",)
    if target_kind == "abstain":
        case_ref = "expanded_case_v2:1123456789abcdef01234567"
        abstention = TypedAbstention.create(
            gap_kind_ref="gap_kind:unresolved_designation",
            critical=True,
            earliest_owner="orient",
            safe_disposition="frontier",
        )
        proposal = ProposalTarget.create(
            source_case_ref=case_ref,
            target_kind="abstain",
            expected_expression_refs=(),
            match_policy="exact",
            expected_expression_relation="none",
            derivations=(),
            abstention=abstention,
            verification_rejection=None,
            review_refs=review_refs,
        )
        subject = TypedGapResponseSubject.create(typed_gap=abstention)
        action = "report_gap"
        slot_ref = "response_slot:gap"
        semantic_ref = abstention.abstention_ref
    else:
        case_ref = "expanded_case_v2:2123456789abcdef01234567"
        rejection = VerificationRejection.create(
            input_kind="mutation_payload",
            adversarial_blueprint_ref=None,
            mutation_payload_ref="mutation_payload:0123456789abcdef01234567",
            expected_owner="verify",
            verification_error_code="verification_error:invalid_role",
            rejection_disposition="reject",
            critical=True,
        )
        proposal = ProposalTarget.create(
            source_case_ref=case_ref,
            target_kind="verification_rejection",
            expected_expression_refs=(),
            match_policy="exact",
            expected_expression_relation="none",
            derivations=(),
            abstention=None,
            verification_rejection=rejection,
            review_refs=review_refs,
        )
        subject = VerifierRejectionResponseSubject.create(
            verifier_rejection=rejection
        )
        action = "reject_candidate"
        slot_ref = "response_slot:verifier_rejection"
        semantic_ref = rejection.verification_rejection_ref

    case = _safe_case(
        case_ref,
        "unsafe input",
        SimpleNamespace(
            discourse_action=action,
            polarity_ref="polarity:positive",
            modality_ref="modality:actual",
            epistemic_status_ref="epistemic_status:unknown",
            permitted_omissions=(),
        ),
    )
    row = _safe_row(
        case,
        proposal,
        subject,
        "I cannot safely answer that.",
        slot_ref,
        semantic_ref,
    )
    result = ReviewedRealizationCompiler(linked_authority).compile(
        case=case, proposal=proposal, row=row
    )
    assert result.authorized_surface
    assert result.authorized_surface != case.surface

    echo = _forge(row, authorized_surface=case.surface)
    with pytest.raises(RealizationCompilationError):
        ReviewedRealizationCompiler(linked_authority).compile(
            case=case, proposal=proposal, row=echo
        )


def test_mutation_compiler_has_no_generator_environment_or_observation_oracle() -> None:
    source = inspect.getsource(mutation_compiler_module)
    assert "MutationGenerator" not in source
    assert "_SPECS" not in source
    assert "r4_environment" not in source
    assert "MutationObservation" not in source
