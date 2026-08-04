"""Initial RED canaries for Verification Batch ABI 2."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import fields
import inspect
from types import MappingProxyType

import pytest

from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.coverage import CoverageVerifier
from cemm_authoritative_hybrid.expressions import (
    CompilationProof,
    CompilationSuccess,
    GroundedReference,
    RoleBinding,
    SemanticApplication,
    SemanticExpression,
    SemanticExpressionCompiler,
    TranslationRow,
    VerifiedMeaning,
)
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.programs import (
    ProgramAction,
    SemanticSwitchProgram,
    SourceAssignment,
)
from cemm_authoritative_hybrid.proposal import (
    ProposalResult,
    RankedProgramCandidate,
)
from cemm_authoritative_hybrid.proposal_context import (
    ApplicationFrameSlot,
    ContributionSlot,
    DesignationSlot,
    ModeSlot,
    ProposalContext,
)
from cemm_authoritative_hybrid.verifier import (
    VERIFICATION_BATCH_ABI_VERSION,
    ActionMasker,
    CandidateVerificationReceipt,
    ExactProgramVerifier,
    LegalActionIndex,
    VerificationBatch,
)


def _pin(**changes: object) -> RevisionPin:
    values = {
        "authority_generation": "authority:test",
        "world_revision": 1,
        "session_revision": 2,
        "episode_revision": 3,
        "effect_revision": 4,
        "model_identity": "model:test",
    }
    values.update(changes)
    return RevisionPin(**values)  # type: ignore[arg-type]


def _context(
    *,
    predicate_target_ref: str = "event:test",
    predicate_kind: str = "event_type",
    operator_ref: str = "op:event",
    structural_role_ref: str = "role:event",
    derived_role_targets: tuple[tuple[str, str], ...] = (),
    affordance_frame_ref: str = "frame:event-test",
) -> ProposalContext:
    designation = DesignationSlot.create(
        source_unit_refs=("unit:predicate",),
        target_ref=predicate_target_ref,
        target_kind=predicate_kind,
        score_q=900_000,
        designation_fact_ref="designation:test",
        provenance_refs=("authority:test",),
    )
    predicate = ContributionSlot.create(
        contribution_ref="contribution:predicate",
        kind="predicate",
        source_unit_refs=("unit:predicate",),
        target_ref=predicate_target_ref,
        target_kind=predicate_kind,
        input_ports=("role:subject",),
        output_ports=(structural_role_ref,),
        constraints=(),
    )
    first_subject = ContributionSlot.create(
        contribution_ref="contribution:subject-one",
        kind="anchor",
        source_unit_refs=("unit:subject",),
        target_ref="entity:one",
        target_kind="entity",
        input_ports=(),
        output_ports=("role:subject",),
        constraints=(),
        provenance_refs=("designation:one",),
    )
    second_subject = ContributionSlot.create(
        contribution_ref="contribution:subject-two",
        kind="anchor",
        source_unit_refs=("unit:subject",),
        target_ref="entity:two",
        target_kind="entity",
        input_ports=(),
        output_ports=("role:subject",),
        constraints=(),
        provenance_refs=("designation:two",),
    )
    mode = ModeSlot.create(
        mode="OBSERVE",
        source_unit_refs=(),
        construction_ref=None,
        requested_effect="admission",
    )
    frame = ApplicationFrameSlot.create(
        designation_slot_ref=designation.slot_ref,
        predicate_target_ref=predicate_target_ref,
        predicate_kind=predicate_kind,
        operator_ref=operator_ref,
        structural_role_ref=structural_role_ref,
        required_roles=("role:subject",),
        optional_roles=(),
        proposition_roles=(),
        source_unit_refs=("unit:predicate",),
        derived_role_targets=derived_role_targets,
        affordance_frame_ref=affordance_frame_ref,
        provenance_refs=(designation.slot_ref, "authority:test", affordance_frame_ref),
    )
    return ProposalContext.create(
        orientation_ref="orientation:test",
        evidence_packet_ref="evidence:test",
        form_lattice_ref="lattice:test",
        grounding_ref="grounding:test",
        designation_slots=(designation,),
        contribution_slots=(predicate, first_subject, second_subject),
        mode_slots=(mode,),
        application_frames=(frame,),
        reference_slots=(),
        scope_slots=(),
        expression_link_slots=(),
        variable_slots=(),
        transition_slots=(),
        residual_evidence=(),
        context_refs=("turn:test",),
        source_unit_refs=("unit:predicate", "unit:subject"),
        source_unit_spans=(
            ("unit:predicate", 0, 4),
            ("unit:subject", 4, 8),
        ),
        revision_pin=_pin(),
    )


def _program(context: ProposalContext, subject_index: int) -> SemanticSwitchProgram:
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
            arguments=("application:main", context.application_frames[0].slot_ref),
            source_unit_refs=("unit:predicate",),
        ),
        ProgramAction.create(
            action_index=4,
            action_type="bind_role",
            arguments=(
                "application:main",
                "role:subject",
                context.contribution_slots[subject_index].slot_ref,
            ),
            source_unit_refs=("unit:subject",),
        ),
        ProgramAction.create(
            action_index=5,
            action_type="complete_program",
            arguments=(),
        ),
    )
    assignments = (
        SourceAssignment.create(
            source_unit_ref="unit:predicate",
            contribution_slot_ref=context.contribution_slots[0].slot_ref,
            assignment_kind="predicate",
            target_action_ref=actions[3].action_ref,
            target_role_ref=None,
            residual_kind=None,
            critical=False,
        ),
        SourceAssignment.create(
            source_unit_ref="unit:subject",
            contribution_slot_ref=context.contribution_slots[subject_index].slot_ref,
            assignment_kind="role",
            target_action_ref=actions[4].action_ref,
            target_role_ref="role:subject",
            residual_kind=None,
            critical=False,
        ),
    )
    return SemanticSwitchProgram.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        actions=actions,
        root_refs=("application:main",),
        mode_slot_ref=context.mode_slots[0].slot_ref,
        goal_refs=("goal:understand",),
        source_unit_refs=context.source_unit_refs,
        source_assignments=assignments,
        revision_pin=context.revision_pin,
    )


def _proposal(
    context: ProposalContext,
    programs: tuple[SemanticSwitchProgram, ...],
    scores: tuple[int, ...],
    *,
    truncated: bool = False,
) -> ProposalResult:
    candidates = tuple(
        RankedProgramCandidate.create(
            rank=index,
            score_q=scores[index],
            program=program,
            provenance_refs=(f"derivation:{index}",),
        )
        for index, program in enumerate(programs)
    )
    return ProposalResult.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        candidates=candidates,
        status="candidates",
        abstention_code=None,
        explored_states=len(candidates),
        truncated=truncated,
        model_identity=context.revision_pin.model_identity,
        revision_pin=context.revision_pin,
    )


def _verifier(margin: int = 0) -> ExactProgramVerifier:
    return ExactProgramVerifier(
        coverage_verifier=CoverageVerifier(),
        compiler=SemanticExpressionCompiler(),
        ambiguity_margin_q=margin,
    )


def test_selected_batch_round_trips_with_complete_lineage() -> None:
    context = _context()
    proposal = _proposal(context, (_program(context, 1),), (100,))

    batch = _verifier().verify_candidates(proposal, context)

    assert batch.status == "selected"
    assert len(batch.candidate_receipts) == 1
    receipt = batch.candidate_receipts[0]
    assert receipt.accepted
    assert batch.selected_candidate_ref == receipt.candidate_ref
    assert batch.selected_meaning is not None
    assert batch.selected_meaning.verification_receipt_ref == receipt.receipt_ref
    assert VerificationBatch.from_dict(batch.as_dict()) == batch


def test_close_distinct_expressions_are_ambiguous() -> None:
    context = _context()
    proposal = _proposal(
        context,
        (_program(context, 1), _program(context, 2)),
        (100, 95),
    )

    batch = _verifier(5).verify_candidates(proposal, context)

    assert batch.status == "ambiguous"
    assert batch.selected_candidate_ref is None
    assert batch.selected_meaning is None
    assert len(batch.ambiguity_expression_refs) == 2
    assert len(set(batch.ambiguity_expression_refs)) == 2


def test_truncated_proposal_is_rejected_with_one_receipt_per_candidate() -> None:
    context = _context()
    proposal = _proposal(
        context,
        (_program(context, 1), _program(context, 2)),
        (100, 90),
        truncated=True,
    )

    batch = _verifier().verify_candidates(proposal, context)

    assert batch.status == "rejected"
    assert len(batch.candidate_receipts) == len(proposal.candidates)
    assert all(
        "proposal_truncated" in {error.code for error in row.verification_errors}
        for row in batch.candidate_receipts
    )


def test_verification_batch_abi2_has_only_canonical_owner_fields() -> None:
    assert VERIFICATION_BATCH_ABI_VERSION == 2
    assert tuple(field.name for field in fields(CandidateVerificationReceipt)) == (
        "receipt_ref",
        "candidate_ref",
        "candidate_index",
        "candidate_rank",
        "score_q",
        "candidate_provenance_refs",
        "program_ref",
        "expression",
        "compilation_proof",
        "coverage_receipt",
        "verification_errors",
    )
    assert tuple(field.name for field in fields(VerificationBatch)) == (
        "batch_ref",
        "proposal_ref",
        "proposal_context_ref",
        "candidate_receipts",
        "ambiguity_margin_q",
        "status",
        "selected_candidate_ref",
        "selected_meaning",
        "ambiguity_expression_refs",
    )
    with pytest.raises(TypeError):
        CandidateVerificationReceipt()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        VerificationBatch()  # type: ignore[call-arg]


def test_duplicate_derivations_do_not_sum_scores_across_expression_group() -> None:
    context = _context()
    same_program = _program(context, 1)
    distinct_program = _program(context, 2)
    proposal = _proposal(
        context,
        (same_program, same_program, distinct_program),
        (60, 60, 100),
    )

    batch = _verifier().verify_candidates(proposal, context)

    assert batch.status == "selected"
    assert tuple(row.candidate_ref for row in batch.candidate_receipts) == tuple(
        row.candidate_ref for row in proposal.candidates
    )
    assert batch.selected_candidate_ref == proposal.candidates[2].candidate_ref
    assert batch.selected_meaning is not None
    assert batch.selected_meaning.program_ref == distinct_program.program_ref


def test_same_expression_group_uses_highest_score_derivation_lineage() -> None:
    context = _context()
    program = _program(context, 1)
    proposal = _proposal(context, (program, program), (90, 100))

    batch = _verifier().verify_candidates(proposal, context)

    assert batch.status == "selected"
    assert batch.selected_candidate_ref == proposal.candidates[1].candidate_ref
    assert (
        batch.candidate_receipts[0].expression.expression_ref
        == batch.candidate_receipts[1].expression.expression_ref
    )


def test_abstained_proposal_produces_empty_abstained_batch() -> None:
    context = _context()
    proposal = ProposalResult.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        candidates=(),
        status="abstained",
        abstention_code="frontier_exhausted",
        explored_states=1,
        truncated=False,
        model_identity=context.revision_pin.model_identity,
        revision_pin=context.revision_pin,
    )

    batch = _verifier().verify_candidates(proposal, context)

    assert batch.status == "abstained"
    assert batch.candidate_receipts == ()
    assert batch.selected_candidate_ref is None
    assert batch.selected_meaning is None
    assert VerificationBatch.from_dict(batch.as_dict()) == batch


@pytest.mark.parametrize(
    "margin",
    (True, 1.0, -1),
    ids=("bool", "float", "negative"),
)
def test_ambiguity_margin_requires_nonnegative_exact_integer(margin: object) -> None:
    with pytest.raises(ValueError, match="ambiguity_margin_q"):
        ExactProgramVerifier(ambiguity_margin_q=margin)  # type: ignore[arg-type]


def test_forged_context_index_cannot_smuggle_dynamic_frame_pointer() -> None:
    context = _context()
    proposal = _proposal(context, (_program(context, 1),), (100,))
    object.__setattr__(context, "_frame_by_ref", MappingProxyType({}))

    batch = _verifier().verify_candidates(proposal, context)

    assert batch.status == "rejected"
    assert "unknown_application_frame" in {
        error.code for error in batch.candidate_receipts[0].verification_errors
    }


@pytest.mark.parametrize(
    "phase",
    ("coverage", "compiler"),
    ids=("coverage-exception", "compiler-exception"),
)
def test_verifier_programming_exceptions_propagate(phase: str) -> None:
    context = _context()
    proposal = _proposal(context, (_program(context, 1),), (100,))

    class ExplodingCoverage:
        def verify(self, supplied_context, program):
            raise RuntimeError("coverage exploded")

    class ExplodingCompiler:
        def compile(self, program, supplied_context):
            raise RuntimeError("compiler exploded")

    verifier = ExactProgramVerifier(
        coverage_verifier=(
            ExplodingCoverage() if phase == "coverage" else CoverageVerifier()
        ),
        compiler=(
            ExplodingCompiler() if phase == "compiler" else SemanticExpressionCompiler()
        ),
    )
    with pytest.raises(RuntimeError, match=f"{phase} exploded"):
        verifier.verify_candidates(proposal, context)


def test_context_bound_action_mask_rejects_forged_dynamic_pointer() -> None:
    context = _context()
    index = LegalActionIndex(context)
    masker = ActionMasker(index)
    valid = ProgramAction.create(
        action_index=0,
        action_type="select_context",
        arguments=(context.context_ref,),
    )
    forged = ProgramAction.create(
        action_index=0,
        action_type="select_context",
        arguments=("proposal_context:forged",),
    )

    assert index.is_legal(valid, ())
    assert masker.is_allowed(valid, ())
    assert not index.is_legal(forged, ())
    assert not masker.is_allowed(forged, ())


def test_legacy_single_program_verification_surface_is_removed() -> None:
    verifier = _verifier()
    assert not hasattr(verifier, "verify")
    assert not hasattr(verifier, "action_encoding_hash")


def test_candidate_selection_has_no_sorting_pass() -> None:
    source = inspect.getsource(ExactProgramVerifier.verify_candidates)
    assert "sorted(" not in source


def test_unique_error_overflow_retains_explicit_fail_closed_marker() -> None:
    from cemm_authoritative_hybrid.verifier import (
        VerificationError,
        _dedupe_errors,
    )

    errors = tuple(VerificationError(f"error:{index}") for index in range(10_000))
    retained = _dedupe_errors(errors)

    assert retained[-1].code == "verification_error_budget_exhausted"
    assert len(retained) < len(errors)


def _forge(value, **updates):
    """Deliberately bypass strict constructors to exercise verifier checks."""
    result = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(
            result,
            field.name,
            updates.get(field.name, getattr(value, field.name)),
        )
    return result


def test_coverage_runs_before_compiler_for_each_eligible_candidate() -> None:
    context = _context()
    proposal = _proposal(context, (_program(context, 1),), (100,))
    events: list[str] = []

    class CoverageSpy:
        def verify(self, supplied_context, program):
            events.append("coverage")
            return CoverageVerifier().verify(supplied_context, program)

    class CompilerSpy:
        def compile(self, program, supplied_context):
            events.append("compiler")
            return SemanticExpressionCompiler().compile(program, supplied_context)

    batch = ExactProgramVerifier(
        coverage_verifier=CoverageSpy(),
        compiler=CompilerSpy(),
    ).verify_candidates(proposal, context)

    assert batch.status == "selected"
    assert events == ["coverage", "compiler"]


def test_truncation_still_checks_coverage_but_never_compiles() -> None:
    context = _context()
    proposal = _proposal(
        context,
        (_program(context, 1), _program(context, 2)),
        (100, 90),
        truncated=True,
    )
    events: list[str] = []

    class CoverageSpy:
        def verify(self, supplied_context, program):
            events.append("coverage")
            return CoverageVerifier().verify(supplied_context, program)

    class CompilerSpy:
        def compile(self, program, supplied_context):
            events.append("compiler")
            return SemanticExpressionCompiler().compile(program, supplied_context)

    batch = ExactProgramVerifier(
        coverage_verifier=CoverageSpy(),
        compiler=CompilerSpy(),
    ).verify_candidates(proposal, context)

    assert batch.status == "rejected"
    assert events == ["coverage", "coverage"]


def test_program_orientation_forgery_is_rejected_at_canonical_envelope() -> None:
    context = _context()
    proposal = _proposal(context, (_program(context, 1),), (100,))
    original_candidate = proposal.candidates[0]
    forged_program = _forge(
        original_candidate.program,
        orientation_ref="orientation:forged",
    )
    forged_candidate = _forge(original_candidate, program=forged_program)
    forged_proposal = _forge(proposal, candidates=(forged_candidate,))

    with pytest.raises(ValueError, match="ref mismatch|canonical"):
        _verifier().verify_candidates(forged_proposal, context)


def test_independent_proof_domain_check_rejects_reordered_canonical_rows() -> None:
    context = _context()
    program = _program(context, 1)
    proposal = _proposal(context, (program,), (100,))

    class ReorderedProofCompiler:
        def compile(self, supplied_program, supplied_context):
            result = SemanticExpressionCompiler().compile(
                supplied_program, supplied_context
            )
            assert isinstance(result, CompilationSuccess)
            proof = result.proof
            rebuilt = CompilationProof.create(
                program_ref=proof.program_ref,
                proposal_context_ref=proof.proposal_context_ref,
                expression_ref=proof.expression_ref,
                action_translations=tuple(reversed(proof.action_translations)),
                assignment_translations=proof.assignment_translations,
                root_translations=proof.root_translations,
                grounding_refs=proof.grounding_refs,
                revision_pin=proof.revision_pin,
            )
            return CompilationSuccess(result.expression, rebuilt)

    batch = ExactProgramVerifier(compiler=ReorderedProofCompiler()).verify_candidates(
        proposal, context
    )

    assert batch.status == "rejected"
    receipt = batch.candidate_receipts[0]
    assert receipt.expression is not None
    assert receipt.compilation_proof is not None
    assert "action_translation_domain_mismatch" in {
        error.code for error in receipt.verification_errors
    }


def test_independent_expression_round_trip_rejects_forged_compiler_output() -> None:
    context = _context()
    program = _program(context, 1)
    proposal = _proposal(context, (program,), (100,))

    class ForgedExpressionCompiler:
        def compile(self, supplied_program, supplied_context):
            result = SemanticExpressionCompiler().compile(
                supplied_program, supplied_context
            )
            assert isinstance(result, CompilationSuccess)
            forged = _forge(result.expression, applications=())
            return CompilationSuccess(forged, result.proof)

    batch = ExactProgramVerifier(compiler=ForgedExpressionCompiler()).verify_candidates(
        proposal, context
    )

    assert batch.status == "rejected"
    assert "expression_identity_mismatch" in {
        error.code for error in batch.candidate_receipts[0].verification_errors
    }


@pytest.mark.parametrize(
    "field",
    (
        "receipt_ref",
        "candidate_index",
        "expression",
        "compilation_proof",
        "coverage_receipt",
    ),
    ids=("receipt-ref", "candidate-index", "expression", "proof", "coverage"),
)
def test_candidate_receipt_codec_rejects_outer_and_nested_tampering(
    field: str,
) -> None:
    context = _context()
    batch = _verifier().verify_candidates(
        _proposal(context, (_program(context, 1),), (100,)),
        context,
    )
    payload = deepcopy(batch.candidate_receipts[0].as_dict())
    if field == "candidate_index":
        payload[field] = True
    elif field == "expression":
        payload[field]["expression_ref"] = "expression:forged"
    elif field == "compilation_proof":
        payload[field]["proof_ref"] = "compilation_proof:forged"
    elif field == "coverage_receipt":
        payload[field]["coverage_receipt_ref"] = "coverage_receipt:forged"
    else:
        payload[field] = "candidate_verification_receipt:forged"

    with pytest.raises((TypeError, ValueError)):
        CandidateVerificationReceipt.from_dict(payload)


@pytest.mark.parametrize(
    "field",
    ("batch_ref", "candidate_receipts", "selected_meaning"),
    ids=("batch-ref", "nested-receipt", "selected-meaning"),
)
def test_verification_batch_codec_rejects_outer_and_nested_tampering(
    field: str,
) -> None:
    context = _context()
    batch = _verifier().verify_candidates(
        _proposal(context, (_program(context, 1),), (100,)),
        context,
    )
    payload = deepcopy(batch.as_dict())
    if field == "candidate_receipts":
        payload[field][0]["receipt_ref"] = "candidate_verification_receipt:forged"
    elif field == "selected_meaning":
        payload[field]["verified_meaning_ref"] = "verified_meaning:forged"
    else:
        payload[field] = "verification_batch:forged"

    with pytest.raises((TypeError, ValueError)):
        VerificationBatch.from_dict(payload)


@pytest.mark.parametrize(
    "field",
    ("proposal_context_ref", "orientation_ref", "revision_pin"),
    ids=("context", "orientation", "revision"),
)
def test_proposal_context_orientation_and_revision_bindings_are_exact(
    field: str,
) -> None:
    context = _context()
    proposal = _proposal(context, (_program(context, 1),), (100,))
    if field == "revision_pin":
        forged = _forge(
            proposal,
            revision_pin=_pin(world_revision=99),
        )
    else:
        forged = _forge(proposal, **{field: f"{field}:forged"})

    with pytest.raises(ValueError):
        _verifier().verify_candidates(forged, context)


def test_rejected_batch_cannot_conceal_an_accepted_receipt() -> None:
    context = _context()
    selected = _verifier().verify_candidates(
        _proposal(context, (_program(context, 1),), (100,)),
        context,
    )
    receipt = selected.candidate_receipts[0]
    assert receipt.accepted

    with pytest.raises(ValueError, match="rejected"):
        VerificationBatch.create(
            proposal_ref=selected.proposal_ref,
            proposal_context_ref=selected.proposal_context_ref,
            candidate_receipts=(receipt,),
            ambiguity_margin_q=selected.ambiguity_margin_q,
            status="rejected",
            selected_candidate_ref=None,
            selected_meaning=None,
            ambiguity_expression_refs=(),
        )

    payload = selected.as_dict()
    payload["status"] = "rejected"
    payload["selected_candidate_ref"] = None
    payload["selected_meaning"] = None
    with pytest.raises(ValueError, match="rejected"):
        VerificationBatch.from_dict(payload)


def test_receipt_constructor_rejects_forged_nested_expression() -> None:
    context = _context()
    batch = _verifier().verify_candidates(
        _proposal(context, (_program(context, 1),), (100,)),
        context,
    )
    receipt = batch.candidate_receipts[0]
    forged_expression = _forge(receipt.expression, applications=())

    with pytest.raises(ValueError, match="expression"):
        CandidateVerificationReceipt.create(
            candidate_ref=receipt.candidate_ref,
            candidate_index=receipt.candidate_index,
            candidate_rank=receipt.candidate_rank,
            score_q=receipt.score_q,
            candidate_provenance_refs=receipt.candidate_provenance_refs,
            program_ref=receipt.program_ref,
            expression=forged_expression,
            compilation_proof=receipt.compilation_proof,
            coverage_receipt=receipt.coverage_receipt,
            verification_errors=(),
        )


def test_action_translation_targets_are_independently_reconstructed() -> None:
    context = _context()
    program = _program(context, 1)
    proposal = _proposal(context, (program,), (100,))

    class ForgedActionTargetCompiler:
        def compile(self, supplied_program, supplied_context):
            result = SemanticExpressionCompiler().compile(
                supplied_program, supplied_context
            )
            assert isinstance(result, CompilationSuccess)
            proof = result.proof
            rows = list(proof.action_translations)
            first = rows[0]
            rows[0] = TranslationRow(
                first.source_ref,
                first.disposition,
                ("proposal_context:forged",),
            )
            rebuilt = CompilationProof.create(
                program_ref=proof.program_ref,
                proposal_context_ref=proof.proposal_context_ref,
                expression_ref=proof.expression_ref,
                action_translations=rows,
                assignment_translations=proof.assignment_translations,
                root_translations=proof.root_translations,
                grounding_refs=proof.grounding_refs,
                revision_pin=proof.revision_pin,
            )
            return CompilationSuccess(result.expression, rebuilt)

    batch = ExactProgramVerifier(
        compiler=ForgedActionTargetCompiler()
    ).verify_candidates(proposal, context)

    assert batch.status == "rejected"
    assert "action_translation_target_mismatch" in {
        error.code for error in batch.candidate_receipts[0].verification_errors
    }


def test_compilation_grounding_is_independently_reconstructed() -> None:
    context = _context()
    program = _program(context, 1)
    proposal = _proposal(context, (program,), (100,))

    class ForgedGroundingCompiler:
        def compile(self, supplied_program, supplied_context):
            result = SemanticExpressionCompiler().compile(
                supplied_program, supplied_context
            )
            assert isinstance(result, CompilationSuccess)
            proof = result.proof
            rebuilt = CompilationProof.create(
                program_ref=proof.program_ref,
                proposal_context_ref=proof.proposal_context_ref,
                expression_ref=proof.expression_ref,
                action_translations=proof.action_translations,
                assignment_translations=proof.assignment_translations,
                root_translations=proof.root_translations,
                grounding_refs=(*proof.grounding_refs, "grounding:forged"),
                revision_pin=proof.revision_pin,
            )
            return CompilationSuccess(result.expression, rebuilt)

    batch = ExactProgramVerifier(compiler=ForgedGroundingCompiler()).verify_candidates(
        proposal, context
    )

    assert batch.status == "rejected"
    assert "compilation_grounding_mismatch" in {
        error.code for error in batch.candidate_receipts[0].verification_errors
    }


@pytest.mark.parametrize(
    ("domain", "expected_code"),
    (
        ("assignment", "assignment_translation_target_mismatch"),
        ("root", "root_translation_target_mismatch"),
    ),
    ids=("assignment-disposition", "root-disposition"),
)
def test_translation_dispositions_are_independently_reconstructed(
    domain: str,
    expected_code: str,
) -> None:
    context = _context()
    program = _program(context, 1)
    proposal = _proposal(context, (program,), (100,))

    class ForgedDispositionCompiler:
        def compile(self, supplied_program, supplied_context):
            result = SemanticExpressionCompiler().compile(
                supplied_program, supplied_context
            )
            assert isinstance(result, CompilationSuccess)
            proof = result.proof
            assignments = list(proof.assignment_translations)
            roots = list(proof.root_translations)
            if domain == "assignment":
                row = assignments[0]
                assignments[0] = TranslationRow(
                    row.source_ref,
                    "retained",
                    row.target_refs,
                )
            else:
                row = roots[0]
                roots[0] = TranslationRow(
                    row.source_ref,
                    "validated",
                    row.target_refs,
                )
            rebuilt = CompilationProof.create(
                program_ref=proof.program_ref,
                proposal_context_ref=proof.proposal_context_ref,
                expression_ref=proof.expression_ref,
                action_translations=proof.action_translations,
                assignment_translations=assignments,
                root_translations=roots,
                grounding_refs=proof.grounding_refs,
                revision_pin=proof.revision_pin,
            )
            return CompilationSuccess(result.expression, rebuilt)

    batch = ExactProgramVerifier(
        compiler=ForgedDispositionCompiler()
    ).verify_candidates(proposal, context)

    assert batch.status == "rejected"
    assert expected_code in {
        error.code for error in batch.candidate_receipts[0].verification_errors
    }


def test_forged_frame_cache_is_rejected_as_incoherent_context_index() -> None:
    context = _context()
    proposal = _proposal(context, (_program(context, 1),), (100,))
    original = context.application_frames[0]
    forged = _forge(original, predicate_target_ref="event:forged")
    object.__setattr__(
        context,
        "_frame_by_ref",
        MappingProxyType({original.slot_ref: forged}),
    )

    with pytest.raises(ValueError, match="index is incoherent"):
        _verifier().verify_candidates(proposal, context)


def test_batch_constructor_rejects_forged_selected_meaning_ref() -> None:
    context = _context()
    batch = _verifier().verify_candidates(
        _proposal(context, (_program(context, 1),), (100,)),
        context,
    )
    forged_meaning = _forge(
        batch.selected_meaning,
        verified_meaning_ref="verified_meaning:forged",
    )

    with pytest.raises(ValueError, match="meaning"):
        VerificationBatch.create(
            proposal_ref=batch.proposal_ref,
            proposal_context_ref=batch.proposal_context_ref,
            candidate_receipts=batch.candidate_receipts,
            ambiguity_margin_q=batch.ambiguity_margin_q,
            status="selected",
            selected_candidate_ref=batch.selected_candidate_ref,
            selected_meaning=forged_meaning,
            ambiguity_expression_refs=(),
        )


def test_batch_constructor_rejects_forged_ambiguous_receipt_ref() -> None:
    context = _context()
    batch = _verifier(5).verify_candidates(
        _proposal(
            context,
            (_program(context, 1), _program(context, 2)),
            (100, 95),
        ),
        context,
    )
    assert batch.status == "ambiguous"
    forged_receipt = _forge(
        batch.candidate_receipts[0],
        receipt_ref="candidate_verification_receipt:forged",
    )

    with pytest.raises(ValueError, match="receipt"):
        VerificationBatch.create(
            proposal_ref=batch.proposal_ref,
            proposal_context_ref=batch.proposal_context_ref,
            candidate_receipts=(forged_receipt, batch.candidate_receipts[1]),
            ambiguity_margin_q=batch.ambiguity_margin_q,
            status="ambiguous",
            selected_candidate_ref=None,
            selected_meaning=None,
            ambiguity_expression_refs=batch.ambiguity_expression_refs,
        )


@pytest.mark.parametrize(
    ("scores", "margin", "expected_status"),
    (
        ((100, 100), 0, "ambiguous"),
        ((100, 95), 4, "selected"),
    ),
    ids=("equal-score-tie", "outside-margin"),
)
def test_selection_margin_ties_and_exclusions_are_exact(
    scores: tuple[int, int],
    margin: int,
    expected_status: str,
) -> None:
    context = _context()
    proposal = _proposal(
        context,
        (_program(context, 1), _program(context, 2)),
        scores,
    )

    batch = _verifier(margin).verify_candidates(proposal, context)

    assert batch.status == expected_status


def _meaning_for_receipt(receipt) -> VerifiedMeaning:
    assert receipt.expression is not None
    assert receipt.compilation_proof is not None
    return VerifiedMeaning.create(
        program_ref=receipt.program_ref,
        expression=receipt.expression,
        grounding_refs=receipt.compilation_proof.grounding_refs,
        coverage_receipt_ref=receipt.coverage_receipt.coverage_receipt_ref,
        compilation_proof_ref=receipt.compilation_proof.proof_ref,
        verification_receipt_ref=receipt.receipt_ref,
        revision_pin=receipt.coverage_receipt.revision_pin,
    )


def test_state_dimension_derived_role_compiles_to_verified_meaning() -> None:
    context = _context(
        predicate_target_ref="dimension:test",
        predicate_kind="state_dimension",
        operator_ref="op:state",
        structural_role_ref="role:dimension",
        derived_role_targets=(("role:dimension", "dimension:test"),),
        affordance_frame_ref="frame:state-test",
    )
    batch = _verifier().verify_candidates(
        _proposal(context, (_program(context, 1),), (100,)),
        context,
    )

    assert batch.status == "selected"
    assert batch.selected_meaning is not None
    application = batch.selected_meaning.expression.applications[0]
    assert application.operator == "op:state"
    assert application.predicate_ref == "dimension:test"
    assert {
        binding.role_ref: binding.filler.target_ref
        for binding in application.roles
        if isinstance(binding.filler, GroundedReference)
    } == {
        "role:dimension": "dimension:test",
        "role:subject": "entity:one",
    }
    receipt = batch.candidate_receipts[0]
    assert receipt.compilation_proof is not None
    assert "dimension:test" in receipt.compilation_proof.grounding_refs
    assert VerificationBatch.from_dict(batch.as_dict()) == batch


def _rebind_forged_receipt(receipt, **updates):
    forged = _forge(receipt, **updates)
    material = {
        "abi_version": VERIFICATION_BATCH_ABI_VERSION,
        "candidate_ref": forged.candidate_ref,
        "candidate_index": forged.candidate_index,
        "candidate_rank": forged.candidate_rank,
        "score_q": forged.score_q,
        "candidate_provenance_refs": list(forged.candidate_provenance_refs),
        "program_ref": forged.program_ref,
        "expression_ref": (
            forged.expression.expression_ref if forged.expression else None
        ),
        "compilation_proof_ref": (
            forged.compilation_proof.proof_ref if forged.compilation_proof else None
        ),
        "coverage_receipt_ref": forged.coverage_receipt.coverage_receipt_ref,
        "verification_errors": [row.as_dict() for row in forged.verification_errors],
    }
    return _forge(
        forged,
        receipt_ref=stable_ref("candidate_verification_receipt", material),
    )


def test_batch_rejects_recomputed_receipt_score_not_bound_to_candidate_ref() -> None:
    context = _context()
    batch = _verifier().verify_candidates(
        _proposal(context, (_program(context, 1), _program(context, 2)), (100, 50)),
        context,
    )
    assert batch.status == "selected"
    forged_lower = _rebind_forged_receipt(batch.candidate_receipts[1], score_q=101)

    with pytest.raises(ValueError, match="candidate_ref"):
        CandidateVerificationReceipt.from_dict(forged_lower.as_dict())

    with pytest.raises(ValueError, match="candidate_ref"):
        VerificationBatch.create(
            proposal_ref=batch.proposal_ref,
            proposal_context_ref=batch.proposal_context_ref,
            candidate_receipts=(batch.candidate_receipts[0], forged_lower),
            ambiguity_margin_q=batch.ambiguity_margin_q,
            status="selected",
            selected_candidate_ref=forged_lower.candidate_ref,
            selected_meaning=_meaning_for_receipt(forged_lower),
            ambiguity_expression_refs=(),
        )


@pytest.mark.parametrize("forgery", ("operator-predicate", "role-filler"))
def test_independent_r1_reconstruction_rejects_canonical_semantic_forgery(
    forgery: str,
) -> None:
    context = _context()
    program = _program(context, 1)
    proposal = _proposal(context, (program,), (100,))

    class CanonicalSemanticForgeryCompiler:
        def compile(self, supplied_program, supplied_context):
            result = SemanticExpressionCompiler().compile(
                supplied_program, supplied_context
            )
            assert isinstance(result, CompilationSuccess)
            original = result.expression.applications[0]
            application = (
                SemanticApplication(
                    original.application_ref,
                    "op:relation",
                    "relation:forged",
                    original.roles,
                    original.qualifiers,
                )
                if forgery == "operator-predicate"
                else SemanticApplication(
                    original.application_ref,
                    original.operator,
                    original.predicate_ref,
                    (
                        RoleBinding(
                            "role:subject",
                            GroundedReference("entity:forged"),
                        ),
                    ),
                    original.qualifiers,
                )
            )
            forged_expression = SemanticExpression.create(
                applications=(application,),
                root_refs=result.expression.root_refs,
            )
            action_rows = list(result.proof.action_translations)
            terminal = action_rows[-1]
            action_rows[-1] = TranslationRow(
                terminal.source_ref,
                terminal.disposition,
                (forged_expression.expression_ref,),
            )
            forged_proof = CompilationProof.create(
                program_ref=result.proof.program_ref,
                proposal_context_ref=result.proof.proposal_context_ref,
                expression_ref=forged_expression.expression_ref,
                action_translations=action_rows,
                assignment_translations=result.proof.assignment_translations,
                root_translations=result.proof.root_translations,
                grounding_refs=result.proof.grounding_refs,
                revision_pin=result.proof.revision_pin,
            )
            return CompilationSuccess(forged_expression, forged_proof)

    batch = ExactProgramVerifier(
        compiler=CanonicalSemanticForgeryCompiler()
    ).verify_candidates(proposal, context)

    assert batch.status == "rejected"
    receipt = batch.candidate_receipts[0]
    assert receipt.expression is None
    assert receipt.compilation_proof is None
    assert "expression_semantics_mismatch" in {
        error.code for error in receipt.verification_errors
    }


def test_ambiguous_batch_cannot_decode_as_selected_lower_score() -> None:
    context = _context()
    proposal = _proposal(
        context,
        (_program(context, 1), _program(context, 2)),
        (100, 95),
    )
    batch = _verifier(5).verify_candidates(proposal, context)
    assert batch.status == "ambiguous"
    lower = batch.candidate_receipts[1]
    with pytest.raises(ValueError):
        VerificationBatch.create(
            proposal_ref=batch.proposal_ref,
            proposal_context_ref=batch.proposal_context_ref,
            candidate_receipts=batch.candidate_receipts,
            ambiguity_margin_q=batch.ambiguity_margin_q,
            status="selected",
            selected_candidate_ref=lower.candidate_ref,
            selected_meaning=_meaning_for_receipt(lower),
            ambiguity_expression_refs=(),
        )


def test_selected_batch_cannot_decode_with_lower_score_lineage() -> None:
    context = _context()
    proposal = _proposal(
        context,
        (_program(context, 1), _program(context, 2)),
        (100, 50),
    )
    batch = _verifier().verify_candidates(proposal, context)
    assert batch.status == "selected"
    lower = batch.candidate_receipts[1]
    with pytest.raises(ValueError):
        VerificationBatch.create(
            proposal_ref=batch.proposal_ref,
            proposal_context_ref=batch.proposal_context_ref,
            candidate_receipts=batch.candidate_receipts,
            ambiguity_margin_q=batch.ambiguity_margin_q,
            status="selected",
            selected_candidate_ref=lower.candidate_ref,
            selected_meaning=_meaning_for_receipt(lower),
            ambiguity_expression_refs=(),
        )


def test_verification_batch_retains_selection_inputs_and_identity() -> None:
    context = _context()
    batch = _verifier(5).verify_candidates(
        _proposal(
            context,
            (_program(context, 1), _program(context, 2)),
            (100, 95),
        ),
        context,
    )
    assert tuple(row.candidate_rank for row in batch.candidate_receipts) == (0, 1)
    assert tuple(row.score_q for row in batch.candidate_receipts) == (100, 95)
    assert batch.ambiguity_margin_q == 5
    winner = batch.candidate_receipts[0]
    changed = VerificationBatch.create(
        proposal_ref=batch.proposal_ref,
        proposal_context_ref=batch.proposal_context_ref,
        candidate_receipts=batch.candidate_receipts,
        ambiguity_margin_q=4,
        status="selected",
        selected_candidate_ref=winner.candidate_ref,
        selected_meaning=_meaning_for_receipt(winner),
        ambiguity_expression_refs=(),
    )
    assert changed.batch_ref != batch.batch_ref
    assert changed.status == "selected"


def _rebind_forged_proposal(proposal, **updates):
    forged = _forge(proposal, **updates)
    material = {
        "abi_version": 2,
        "orientation_ref": forged.orientation_ref,
        "proposal_context_ref": forged.proposal_context_ref,
        "candidate_refs": [row.candidate_ref for row in forged.candidates],
        "status": forged.status,
        "abstention_code": forged.abstention_code,
        "explored_states": forged.explored_states,
        "truncated": forged.truncated,
        "model_identity": forged.model_identity,
        "revision_pin": forged.revision_pin.as_dict(),
    }
    return _forge(forged, proposal_ref=stable_ref("proposal", material))


def test_envelope_rejects_forged_oversize_candidate_provenance() -> None:
    context = _context()
    proposal = _proposal(context, (_program(context, 1),), (100,))
    original = proposal.candidates[0]
    provenance = tuple(f"derivation:{index}" for index in range(65))
    candidate_ref = stable_ref(
        "proposal_candidate",
        {
            "proposal_result_abi_version": 2,
            "rank": original.rank,
            "score_q": original.score_q,
            "program_ref": original.program.program_ref,
            "provenance_refs": list(provenance),
        },
    )
    forged_candidate = _forge(
        original,
        candidate_ref=candidate_ref,
        provenance_refs=provenance,
    )
    forged = _rebind_forged_proposal(
        proposal,
        candidates=(forged_candidate,),
    )
    with pytest.raises(ValueError):
        _verifier().verify_candidates(forged, context)


def test_envelope_rejects_forged_explored_state_overflow() -> None:
    context = _context()
    proposal = _proposal(context, (_program(context, 1),), (100,))
    forged = _rebind_forged_proposal(proposal, explored_states=2**63)
    with pytest.raises(ValueError):
        _verifier().verify_candidates(forged, context)
