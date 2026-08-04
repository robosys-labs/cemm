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
    orientation_ref: str = "orientation:test",
    revision_pin: RevisionPin | None = None,
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
        orientation_ref=orientation_ref,
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
        revision_pin=revision_pin or _pin(),
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


@pytest.mark.parametrize(
    "forgery",
    ("operator-predicate", "role-filler"),
    ids=("operator-predicate", "role-filler"),
)
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

__cemm_test_inventory__ = {'tests/test_r1_verification_batch.py::test_abstained_proposal_produces_empty_abstained_batch': {'activation_phase': 'R1',
                                                                                                 'assertion_ref': 'assertion:r1-r1-verification-batch-test-abstained-proposal-produces-empty-abstained-batch',
                                                                                                 'diagnostic_role': 'owner',
                                                                                                 'introduced_by_task': 'R1-Task-7',
                                                                                                 'owner_ref': 'program-verifier',
                                                                                                 'source_ast_sha256': 'abf1f9df4347d76b84484e9909cd62e8cc6b519eb7f29e25bf37e66b891144f3'},
 'tests/test_r1_verification_batch.py::test_action_translation_targets_are_independently_reconstructed': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-r1-verification-batch-test-action-translation-targets-are-independently-reconstructed',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                                          'owner_ref': 'program-verifier',
                                                                                                          'source_ast_sha256': 'f1634468b24a8ed23465bf61c9e54b0f76318ec3e1f8154d47e95a17bf1462e2'},
 'tests/test_r1_verification_batch.py::test_ambiguity_margin_requires_nonnegative_exact_integer[bool]': {'activation_phase': 'R1',
                                                                                                         'assertion_ref': 'assertion:r1-r1-verification-batch-test-ambiguity-margin-requires-nonnegative-exact-integer-bool',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R1-Task-7',
                                                                                                         'owner_ref': 'program-verifier',
                                                                                                         'source_ast_sha256': 'ed3b6af4aed7c831d545b6e1481865a16fb1bf776b8ee81fafb5ba1ce3d00e3f'},
 'tests/test_r1_verification_batch.py::test_ambiguity_margin_requires_nonnegative_exact_integer[float]': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-r1-verification-batch-test-ambiguity-margin-requires-nonnegative-exact-integer-float',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                                          'owner_ref': 'program-verifier',
                                                                                                          'source_ast_sha256': 'ed3b6af4aed7c831d545b6e1481865a16fb1bf776b8ee81fafb5ba1ce3d00e3f'},
 'tests/test_r1_verification_batch.py::test_ambiguity_margin_requires_nonnegative_exact_integer[negative]': {'activation_phase': 'R1',
                                                                                                             'assertion_ref': 'assertion:r1-r1-verification-batch-test-ambiguity-margin-requires-nonnegative-exact-integer-negative',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'R1-Task-7',
                                                                                                             'owner_ref': 'program-verifier',
                                                                                                             'source_ast_sha256': 'ed3b6af4aed7c831d545b6e1481865a16fb1bf776b8ee81fafb5ba1ce3d00e3f'},
 'tests/test_r1_verification_batch.py::test_ambiguous_batch_cannot_decode_as_selected_lower_score': {'activation_phase': 'R1',
                                                                                                     'assertion_ref': 'assertion:r1-r1-verification-batch-test-ambiguous-batch-cannot-decode-as-selected-lower-score',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'R1-Task-7',
                                                                                                     'owner_ref': 'program-verifier',
                                                                                                     'source_ast_sha256': '9780da44e3701ed7375ac5e3bc8b2553003b86eae55d92ecc9794e5b72a09929'},
 'tests/test_r1_verification_batch.py::test_batch_constructor_rejects_forged_ambiguous_receipt_ref': {'activation_phase': 'R1',
                                                                                                      'assertion_ref': 'assertion:r1-r1-verification-batch-test-batch-constructor-rejects-forged-ambiguous-receipt-ref',
                                                                                                      'diagnostic_role': 'owner',
                                                                                                      'introduced_by_task': 'R1-Task-7',
                                                                                                      'owner_ref': 'program-verifier',
                                                                                                      'source_ast_sha256': '85d25dfc402207366321e549696f9623b62199feac71f095ffbc2483212f4416'},
 'tests/test_r1_verification_batch.py::test_batch_constructor_rejects_forged_selected_meaning_ref': {'activation_phase': 'R1',
                                                                                                     'assertion_ref': 'assertion:r1-r1-verification-batch-test-batch-constructor-rejects-forged-selected-meaning-ref',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'R1-Task-7',
                                                                                                     'owner_ref': 'program-verifier',
                                                                                                     'source_ast_sha256': 'c5b3e571b9b43e5c62b265f378f7fb2bd17c72db3c219481a857868f4e23760e'},
 'tests/test_r1_verification_batch.py::test_batch_rejects_recomputed_receipt_score_not_bound_to_candidate_ref': {'activation_phase': 'R1',
                                                                                                                 'assertion_ref': 'assertion:r1-r1-verification-batch-test-batch-rejects-recomputed-receipt-score-not-bound-to-candidate-ref',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'R1-Task-7',
                                                                                                                 'owner_ref': 'program-verifier',
                                                                                                                 'source_ast_sha256': '23a808909fcbcaca79e6d30f0a11f134ec544cbe9a0c5602c4cd4496d3c636a0'},
 'tests/test_r1_verification_batch.py::test_candidate_receipt_codec_rejects_outer_and_nested_tampering[candidate-index]': {'activation_phase': 'R1',
                                                                                                                           'assertion_ref': 'assertion:r1-r1-verification-batch-test-candidate-receipt-codec-rejects-outer-and-nested-tampering-candidate-index',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'R1-Task-7',
                                                                                                                           'owner_ref': 'program-verifier',
                                                                                                                           'source_ast_sha256': '4b502084041750f7d7d21b8239754989d412ff973a9da725ca944f35636efef6'},
 'tests/test_r1_verification_batch.py::test_candidate_receipt_codec_rejects_outer_and_nested_tampering[coverage]': {'activation_phase': 'R1',
                                                                                                                    'assertion_ref': 'assertion:r1-r1-verification-batch-test-candidate-receipt-codec-rejects-outer-and-nested-tampering-coverage',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'R1-Task-7',
                                                                                                                    'owner_ref': 'program-verifier',
                                                                                                                    'source_ast_sha256': '4b502084041750f7d7d21b8239754989d412ff973a9da725ca944f35636efef6'},
 'tests/test_r1_verification_batch.py::test_candidate_receipt_codec_rejects_outer_and_nested_tampering[expression]': {'activation_phase': 'R1',
                                                                                                                      'assertion_ref': 'assertion:r1-r1-verification-batch-test-candidate-receipt-codec-rejects-outer-and-nested-tampering-expression',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'R1-Task-7',
                                                                                                                      'owner_ref': 'program-verifier',
                                                                                                                      'source_ast_sha256': '4b502084041750f7d7d21b8239754989d412ff973a9da725ca944f35636efef6'},
 'tests/test_r1_verification_batch.py::test_candidate_receipt_codec_rejects_outer_and_nested_tampering[proof]': {'activation_phase': 'R1',
                                                                                                                 'assertion_ref': 'assertion:r1-r1-verification-batch-test-candidate-receipt-codec-rejects-outer-and-nested-tampering-proof',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'R1-Task-7',
                                                                                                                 'owner_ref': 'program-verifier',
                                                                                                                 'source_ast_sha256': '4b502084041750f7d7d21b8239754989d412ff973a9da725ca944f35636efef6'},
 'tests/test_r1_verification_batch.py::test_candidate_receipt_codec_rejects_outer_and_nested_tampering[receipt-ref]': {'activation_phase': 'R1',
                                                                                                                       'assertion_ref': 'assertion:r1-r1-verification-batch-test-candidate-receipt-codec-rejects-outer-and-nested-tampering-receipt-ref',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'R1-Task-7',
                                                                                                                       'owner_ref': 'program-verifier',
                                                                                                                       'source_ast_sha256': '4b502084041750f7d7d21b8239754989d412ff973a9da725ca944f35636efef6'},
 'tests/test_r1_verification_batch.py::test_candidate_selection_has_no_sorting_pass': {'activation_phase': 'R1',
                                                                                       'assertion_ref': 'assertion:r1-r1-verification-batch-test-candidate-selection-has-no-sorting-pass',
                                                                                       'diagnostic_role': 'owner',
                                                                                       'introduced_by_task': 'R1-Task-7',
                                                                                       'owner_ref': 'program-verifier',
                                                                                       'source_ast_sha256': '87dc1b7bf161c5072eef035169ad91c7ff344fabd3aa011667f9b31b45a7cefc'},
 'tests/test_r1_verification_batch.py::test_close_distinct_expressions_are_ambiguous': {'activation_phase': 'R1',
                                                                                        'assertion_ref': 'assertion:r1-r1-verification-batch-test-close-distinct-expressions-are-ambiguous',
                                                                                        'diagnostic_role': 'owner',
                                                                                        'introduced_by_task': 'R1-Task-7',
                                                                                        'owner_ref': 'program-verifier',
                                                                                        'source_ast_sha256': '54c5c590ac9bee15b8fd836c5cb6f7fccb4016345dc30dfaa5d3c85092286571'},
 'tests/test_r1_verification_batch.py::test_compilation_grounding_is_independently_reconstructed': {'activation_phase': 'R1',
                                                                                                    'assertion_ref': 'assertion:r1-r1-verification-batch-test-compilation-grounding-is-independently-reconstructed',
                                                                                                    'diagnostic_role': 'owner',
                                                                                                    'introduced_by_task': 'R1-Task-7',
                                                                                                    'owner_ref': 'program-verifier',
                                                                                                    'source_ast_sha256': '24c1baf5a63e4d7e68721c02757856fee7c761c4e571604b01d0274a9bd00a83'},
 'tests/test_r1_verification_batch.py::test_context_bound_action_mask_rejects_forged_dynamic_pointer': {'activation_phase': 'R1',
                                                                                                        'assertion_ref': 'assertion:r1-r1-verification-batch-test-context-bound-action-mask-rejects-forged-dynamic-pointer',
                                                                                                        'diagnostic_role': 'owner',
                                                                                                        'introduced_by_task': 'R1-Task-7',
                                                                                                        'owner_ref': 'program-verifier',
                                                                                                        'source_ast_sha256': '91ce3758c90551f2d0b34ea0195426be1f2d7c5f6e57187bb50ac9e6e3bd15cd'},
 'tests/test_r1_verification_batch.py::test_coverage_runs_before_compiler_for_each_eligible_candidate': {'activation_phase': 'R1',
                                                                                                         'assertion_ref': 'assertion:r1-r1-verification-batch-test-coverage-runs-before-compiler-for-each-eligible-candidate',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R1-Task-7',
                                                                                                         'owner_ref': 'program-verifier',
                                                                                                         'source_ast_sha256': '368b91b6c3ca452e9c868c096336923f6097b753042407e04abfb1a0a89a73d9'},
 'tests/test_r1_verification_batch.py::test_duplicate_derivations_do_not_sum_scores_across_expression_group': {'activation_phase': 'R1',
                                                                                                               'assertion_ref': 'assertion:r1-r1-verification-batch-test-duplicate-derivations-do-not-sum-scores-across-expression-group',
                                                                                                               'diagnostic_role': 'owner',
                                                                                                               'introduced_by_task': 'R1-Task-7',
                                                                                                               'owner_ref': 'program-verifier',
                                                                                                               'source_ast_sha256': '61440a26653ea65d32e3a1808cef2bcbf577cda8ab46c5222fdc042d20a9c7b0'},
 'tests/test_r1_verification_batch.py::test_envelope_rejects_forged_explored_state_overflow': {'activation_phase': 'R1',
                                                                                               'assertion_ref': 'assertion:r1-r1-verification-batch-test-envelope-rejects-forged-explored-state-overflow',
                                                                                               'diagnostic_role': 'owner',
                                                                                               'introduced_by_task': 'R1-Task-7',
                                                                                               'owner_ref': 'program-verifier',
                                                                                               'source_ast_sha256': 'def1d3c3a4eef95dc39f63e87612aa41b2774690afb2393e2cc598cde14e659f'},
 'tests/test_r1_verification_batch.py::test_envelope_rejects_forged_oversize_candidate_provenance': {'activation_phase': 'R1',
                                                                                                     'assertion_ref': 'assertion:r1-r1-verification-batch-test-envelope-rejects-forged-oversize-candidate-provenance',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'R1-Task-7',
                                                                                                     'owner_ref': 'program-verifier',
                                                                                                     'source_ast_sha256': '122c789eb2aa10e24bdb3b75c4758bcdfc33374b828ff1b2a487f81a61c48152'},
 'tests/test_r1_verification_batch.py::test_forged_context_index_cannot_smuggle_dynamic_frame_pointer': {'activation_phase': 'R1',
                                                                                                         'assertion_ref': 'assertion:r1-r1-verification-batch-test-forged-context-index-cannot-smuggle-dynamic-frame-pointer',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R1-Task-7',
                                                                                                         'owner_ref': 'program-verifier',
                                                                                                         'source_ast_sha256': '69893569762af22d49dcac7130a584a3668fe103d30e7587ca7ed2575e974733'},
 'tests/test_r1_verification_batch.py::test_forged_frame_cache_is_rejected_as_incoherent_context_index': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-r1-verification-batch-test-forged-frame-cache-is-rejected-as-incoherent-context-index',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                                          'owner_ref': 'program-verifier',
                                                                                                          'source_ast_sha256': '1e33630a3dd9c246fbbd0b855bac8d9a042b19b93581cf3c89db0debf00c19c8'},
 'tests/test_r1_verification_batch.py::test_independent_expression_round_trip_rejects_forged_compiler_output': {'activation_phase': 'R1',
                                                                                                                'assertion_ref': 'assertion:r1-r1-verification-batch-test-independent-expression-round-trip-rejects-forged-compiler-output',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'R1-Task-7',
                                                                                                                'owner_ref': 'program-verifier',
                                                                                                                'source_ast_sha256': '5850bbbb0e3b69f5b051151d9e2014f271a44995c21140554641605a9ee29a70'},
 'tests/test_r1_verification_batch.py::test_independent_proof_domain_check_rejects_reordered_canonical_rows': {'activation_phase': 'R1',
                                                                                                               'assertion_ref': 'assertion:r1-r1-verification-batch-test-independent-proof-domain-check-rejects-reordered-canonical-rows',
                                                                                                               'diagnostic_role': 'owner',
                                                                                                               'introduced_by_task': 'R1-Task-7',
                                                                                                               'owner_ref': 'program-verifier',
                                                                                                               'source_ast_sha256': 'f31d0f0d5a86c5969f1c3a019b7cf7a416045eaa92063c07f2845191fa89ee67'},
 'tests/test_r1_verification_batch.py::test_independent_r1_reconstruction_rejects_canonical_semantic_forgery[operator-predicate]': {'activation_phase': 'R1',
                                                                                                                                    'assertion_ref': 'assertion:r1-r1-verification-batch-test-independent-r1-reconstruction-rejects-canonical-semantic-forgery-operator-predicate',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'R1-Task-7',
                                                                                                                                    'owner_ref': 'program-verifier',
                                                                                                                                    'source_ast_sha256': '5bea0d1386006ae629ff130b772e10cf4e33e2425197fb3dc9a0eced57128141'},
 'tests/test_r1_verification_batch.py::test_independent_r1_reconstruction_rejects_canonical_semantic_forgery[role-filler]': {'activation_phase': 'R1',
                                                                                                                             'assertion_ref': 'assertion:r1-r1-verification-batch-test-independent-r1-reconstruction-rejects-canonical-semantic-forgery-role-filler',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'R1-Task-7',
                                                                                                                             'owner_ref': 'program-verifier',
                                                                                                                             'source_ast_sha256': '5bea0d1386006ae629ff130b772e10cf4e33e2425197fb3dc9a0eced57128141'},
 'tests/test_r1_verification_batch.py::test_legacy_single_program_verification_surface_is_removed': {'activation_phase': 'R1',
                                                                                                     'assertion_ref': 'assertion:r1-r1-verification-batch-test-legacy-single-program-verification-surface-is-removed',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'R1-Task-7',
                                                                                                     'owner_ref': 'program-verifier',
                                                                                                     'source_ast_sha256': '43b244d16b9665dc4197da099f5e8ebec67edb91d4433696d681b6a1afc090d8'},
 'tests/test_r1_verification_batch.py::test_program_orientation_forgery_is_rejected_at_canonical_envelope': {'activation_phase': 'R1',
                                                                                                             'assertion_ref': 'assertion:r1-r1-verification-batch-test-program-orientation-forgery-is-rejected-at-canonical-envelope',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'R1-Task-7',
                                                                                                             'owner_ref': 'program-verifier',
                                                                                                             'source_ast_sha256': 'b7ee931c5c50992ac6d69201192d3c8850d41d9d3f6245bc7ecaf7ef6f2cebda'},
 'tests/test_r1_verification_batch.py::test_proposal_context_orientation_and_revision_bindings_are_exact[context]': {'activation_phase': 'R1',
                                                                                                                     'assertion_ref': 'assertion:r1-r1-verification-batch-test-proposal-context-orientation-and-revision-bindings-are-exact-context',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'R1-Task-7',
                                                                                                                     'owner_ref': 'program-verifier',
                                                                                                                     'source_ast_sha256': '93604eb69f513844661e332c5bad14641e6bd72d68c7882bc678e189cd5810dc'},
 'tests/test_r1_verification_batch.py::test_proposal_context_orientation_and_revision_bindings_are_exact[orientation]': {'activation_phase': 'R1',
                                                                                                                         'assertion_ref': 'assertion:r1-r1-verification-batch-test-proposal-context-orientation-and-revision-bindings-are-exact-orientation',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'R1-Task-7',
                                                                                                                         'owner_ref': 'program-verifier',
                                                                                                                         'source_ast_sha256': '93604eb69f513844661e332c5bad14641e6bd72d68c7882bc678e189cd5810dc'},
 'tests/test_r1_verification_batch.py::test_proposal_context_orientation_and_revision_bindings_are_exact[revision]': {'activation_phase': 'R1',
                                                                                                                      'assertion_ref': 'assertion:r1-r1-verification-batch-test-proposal-context-orientation-and-revision-bindings-are-exact-revision',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'R1-Task-7',
                                                                                                                      'owner_ref': 'program-verifier',
                                                                                                                      'source_ast_sha256': '93604eb69f513844661e332c5bad14641e6bd72d68c7882bc678e189cd5810dc'},
 'tests/test_r1_verification_batch.py::test_receipt_constructor_rejects_forged_nested_expression': {'activation_phase': 'R1',
                                                                                                    'assertion_ref': 'assertion:r1-r1-verification-batch-test-receipt-constructor-rejects-forged-nested-expression',
                                                                                                    'diagnostic_role': 'owner',
                                                                                                    'introduced_by_task': 'R1-Task-7',
                                                                                                    'owner_ref': 'program-verifier',
                                                                                                    'source_ast_sha256': '881ee8909f633bb8337518ae7679e39d30af356aaa59aa6b9648ca047db12efe'},
 'tests/test_r1_verification_batch.py::test_rejected_batch_cannot_conceal_an_accepted_receipt': {'activation_phase': 'R1',
                                                                                                 'assertion_ref': 'assertion:r1-r1-verification-batch-test-rejected-batch-cannot-conceal-an-accepted-receipt',
                                                                                                 'diagnostic_role': 'owner',
                                                                                                 'introduced_by_task': 'R1-Task-7',
                                                                                                 'owner_ref': 'program-verifier',
                                                                                                 'source_ast_sha256': '910bdca455d5c012a28283d258288016ad0a01ac49f286bf3538e2801bf88786'},
 'tests/test_r1_verification_batch.py::test_same_expression_group_uses_highest_score_derivation_lineage': {'activation_phase': 'R1',
                                                                                                           'assertion_ref': 'assertion:r1-r1-verification-batch-test-same-expression-group-uses-highest-score-derivation-lineage',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R1-Task-7',
                                                                                                           'owner_ref': 'program-verifier',
                                                                                                           'source_ast_sha256': '385df5809653c1c893b9141a608992ae5a861d6961b3668b819b0f900c8eac05'},
 'tests/test_r1_verification_batch.py::test_selected_batch_cannot_decode_with_lower_score_lineage': {'activation_phase': 'R1',
                                                                                                     'assertion_ref': 'assertion:r1-r1-verification-batch-test-selected-batch-cannot-decode-with-lower-score-lineage',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'R1-Task-7',
                                                                                                     'owner_ref': 'program-verifier',
                                                                                                     'source_ast_sha256': '5ed443f9e40127232d9947a9f0c72f5ca994b5d1fff4797121d12a93ce7fd4fe'},
 'tests/test_r1_verification_batch.py::test_selected_batch_round_trips_with_complete_lineage': {'activation_phase': 'R1',
                                                                                                'assertion_ref': 'assertion:r1-r1-verification-batch-test-selected-batch-round-trips-with-complete-lineage',
                                                                                                'diagnostic_role': 'owner',
                                                                                                'introduced_by_task': 'R1-Task-7',
                                                                                                'owner_ref': 'program-verifier',
                                                                                                'source_ast_sha256': 'ec42ddf831ef691e30a9417519683a3dc62272a9a12797ff638b6e22c24c8b1a'},
 'tests/test_r1_verification_batch.py::test_selection_margin_ties_and_exclusions_are_exact[equal-score-tie]': {'activation_phase': 'R1',
                                                                                                               'assertion_ref': 'assertion:r1-r1-verification-batch-test-selection-margin-ties-and-exclusions-are-exact-equal-score-tie',
                                                                                                               'diagnostic_role': 'owner',
                                                                                                               'introduced_by_task': 'R1-Task-7',
                                                                                                               'owner_ref': 'program-verifier',
                                                                                                               'source_ast_sha256': '88ddd9e02c097ee12eff324a622874d191082c088e29e51573740a77ea7ecc65'},
 'tests/test_r1_verification_batch.py::test_selection_margin_ties_and_exclusions_are_exact[outside-margin]': {'activation_phase': 'R1',
                                                                                                              'assertion_ref': 'assertion:r1-r1-verification-batch-test-selection-margin-ties-and-exclusions-are-exact-outside-margin',
                                                                                                              'diagnostic_role': 'owner',
                                                                                                              'introduced_by_task': 'R1-Task-7',
                                                                                                              'owner_ref': 'program-verifier',
                                                                                                              'source_ast_sha256': '88ddd9e02c097ee12eff324a622874d191082c088e29e51573740a77ea7ecc65'},
 'tests/test_r1_verification_batch.py::test_state_dimension_derived_role_compiles_to_verified_meaning': {'activation_phase': 'R1',
                                                                                                         'assertion_ref': 'assertion:r1-r1-verification-batch-test-state-dimension-derived-role-compiles-to-verified-meaning',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R1-Task-7',
                                                                                                         'owner_ref': 'program-verifier',
                                                                                                         'source_ast_sha256': '92d912a1f181966175bb5d16819bafb4b4977319513dcce0d382e40839f2d946'},
 'tests/test_r1_verification_batch.py::test_translation_dispositions_are_independently_reconstructed[assignment-disposition]': {'activation_phase': 'R1',
                                                                                                                                'assertion_ref': 'assertion:r1-r1-verification-batch-test-translation-dispositions-are-independently-reconstructed-assignment-disposition',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'R1-Task-7',
                                                                                                                                'owner_ref': 'program-verifier',
                                                                                                                                'source_ast_sha256': '51a35741e2c7996673c992e43be3909db1b3b22b47ac84b1308e2cdea2671d9e'},
 'tests/test_r1_verification_batch.py::test_translation_dispositions_are_independently_reconstructed[root-disposition]': {'activation_phase': 'R1',
                                                                                                                          'assertion_ref': 'assertion:r1-r1-verification-batch-test-translation-dispositions-are-independently-reconstructed-root-disposition',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'R1-Task-7',
                                                                                                                          'owner_ref': 'program-verifier',
                                                                                                                          'source_ast_sha256': '51a35741e2c7996673c992e43be3909db1b3b22b47ac84b1308e2cdea2671d9e'},
 'tests/test_r1_verification_batch.py::test_truncated_proposal_is_rejected_with_one_receipt_per_candidate': {'activation_phase': 'R1',
                                                                                                             'assertion_ref': 'assertion:r1-r1-verification-batch-test-truncated-proposal-is-rejected-with-one-receipt-per-candidate',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'R1-Task-7',
                                                                                                             'owner_ref': 'program-verifier',
                                                                                                             'source_ast_sha256': 'db5b16d5cce70de1bea89800fafc1a7d149b63637e724aa21c6c9db52be7a069'},
 'tests/test_r1_verification_batch.py::test_truncation_still_checks_coverage_but_never_compiles': {'activation_phase': 'R1',
                                                                                                   'assertion_ref': 'assertion:r1-r1-verification-batch-test-truncation-still-checks-coverage-but-never-compiles',
                                                                                                   'diagnostic_role': 'owner',
                                                                                                   'introduced_by_task': 'R1-Task-7',
                                                                                                   'owner_ref': 'program-verifier',
                                                                                                   'source_ast_sha256': '5d73a46659a3fa2d5b92dcf198e71fa19048400d57956bf82419eef6a15e9d63'},
 'tests/test_r1_verification_batch.py::test_unique_error_overflow_retains_explicit_fail_closed_marker': {'activation_phase': 'R1',
                                                                                                         'assertion_ref': 'assertion:r1-r1-verification-batch-test-unique-error-overflow-retains-explicit-fail-closed-marker',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R1-Task-7',
                                                                                                         'owner_ref': 'program-verifier',
                                                                                                         'source_ast_sha256': '29ddcd8b09ee9b3771180ee4ad71b6e9eaa543edf4e2138c93ede87aa505e230'},
 'tests/test_r1_verification_batch.py::test_verification_batch_abi2_has_only_canonical_owner_fields': {'activation_phase': 'R1',
                                                                                                       'assertion_ref': 'assertion:r1-r1-verification-batch-test-verification-batch-abi2-has-only-canonical-owner-fields',
                                                                                                       'diagnostic_role': 'owner',
                                                                                                       'introduced_by_task': 'R1-Task-7',
                                                                                                       'owner_ref': 'program-verifier',
                                                                                                       'source_ast_sha256': '4104693deaaf74430bbfaff0d64da00f2605e55c50bfce5bdc71df8ad2c5820a'},
 'tests/test_r1_verification_batch.py::test_verification_batch_codec_rejects_outer_and_nested_tampering[batch-ref]': {'activation_phase': 'R1',
                                                                                                                      'assertion_ref': 'assertion:r1-r1-verification-batch-test-verification-batch-codec-rejects-outer-and-nested-tampering-batch-ref',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'R1-Task-7',
                                                                                                                      'owner_ref': 'program-verifier',
                                                                                                                      'source_ast_sha256': 'e8ca0b3735fbd2904f512231eb64d4ea65c408a31808f4bc054a4524773339ca'},
 'tests/test_r1_verification_batch.py::test_verification_batch_codec_rejects_outer_and_nested_tampering[nested-receipt]': {'activation_phase': 'R1',
                                                                                                                           'assertion_ref': 'assertion:r1-r1-verification-batch-test-verification-batch-codec-rejects-outer-and-nested-tampering-nested-receipt',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'R1-Task-7',
                                                                                                                           'owner_ref': 'program-verifier',
                                                                                                                           'source_ast_sha256': 'e8ca0b3735fbd2904f512231eb64d4ea65c408a31808f4bc054a4524773339ca'},
 'tests/test_r1_verification_batch.py::test_verification_batch_codec_rejects_outer_and_nested_tampering[selected-meaning]': {'activation_phase': 'R1',
                                                                                                                             'assertion_ref': 'assertion:r1-r1-verification-batch-test-verification-batch-codec-rejects-outer-and-nested-tampering-selected-meaning',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'R1-Task-7',
                                                                                                                             'owner_ref': 'program-verifier',
                                                                                                                             'source_ast_sha256': 'e8ca0b3735fbd2904f512231eb64d4ea65c408a31808f4bc054a4524773339ca'},
 'tests/test_r1_verification_batch.py::test_verification_batch_retains_selection_inputs_and_identity': {'activation_phase': 'R1',
                                                                                                        'assertion_ref': 'assertion:r1-r1-verification-batch-test-verification-batch-retains-selection-inputs-and-identity',
                                                                                                        'diagnostic_role': 'owner',
                                                                                                        'introduced_by_task': 'R1-Task-7',
                                                                                                        'owner_ref': 'program-verifier',
                                                                                                        'source_ast_sha256': '05290762a623931c2c851fecfa80dca22fb220cb8458483e9aecc689bee7e07b'},
 'tests/test_r1_verification_batch.py::test_verifier_programming_exceptions_propagate[compiler-exception]': {'activation_phase': 'R1',
                                                                                                             'assertion_ref': 'assertion:r1-r1-verification-batch-test-verifier-programming-exceptions-propagate-compiler-exception',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'R1-Task-7',
                                                                                                             'owner_ref': 'program-verifier',
                                                                                                             'source_ast_sha256': '3e59d96696928f767a3685e60dfdffcc912de63d22c1791ea303a9e6811fe29e'},
 'tests/test_r1_verification_batch.py::test_verifier_programming_exceptions_propagate[coverage-exception]': {'activation_phase': 'R1',
                                                                                                             'assertion_ref': 'assertion:r1-r1-verification-batch-test-verifier-programming-exceptions-propagate-coverage-exception',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'R1-Task-7',
                                                                                                             'owner_ref': 'program-verifier',
                                                                                                             'source_ast_sha256': '3e59d96696928f767a3685e60dfdffcc912de63d22c1791ea303a9e6811fe29e'}}
