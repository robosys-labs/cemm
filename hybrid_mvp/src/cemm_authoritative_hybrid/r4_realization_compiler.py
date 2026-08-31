"""Independent reconstruction of reviewed R4.1 realization semantics."""
from __future__ import annotations

from dataclasses import dataclass

from .authority import LinkedAuthority
from .canonical import stable_ref
from .r4_expansion import ExpandedCase
from .r4_supervision import (
    DesignationAlignment,
    ExpressionSetResponseSubject,
    LiteralAlignment,
    MorphologyAlignment,
    OmissionAlignment,
    ProposalTarget,
    RealizationRow,
    ReferenceAlignment,
    ResponseSubject,
    TypedGapResponseSubject,
    VerifierRejectionResponseSubject,
)


@dataclass(frozen=True)
class CompiledReviewedRealization:
    response_signature_ref: str
    authorized_surface: str
    covered_slot_refs: tuple[str, ...]
    omitted_slot_refs: tuple[str, ...]
    operation_count: int


class RealizationCompilationError(ValueError):
    """A reviewed surface does not reconstruct its source-owned semantics."""


def response_subject_from_proposal(proposal: ProposalTarget) -> ResponseSubject:
    """Reconstruct the closed response subject without consulting realization."""

    if type(proposal) is not ProposalTarget:
        raise TypeError("proposal must be exact ProposalTarget")
    if proposal.target_kind == "derive":
        return ExpressionSetResponseSubject.create(
            expected_expression_relation=proposal.expected_expression_relation,
            expression_refs=proposal.expected_expression_refs,
        )
    if proposal.target_kind == "abstain" and proposal.abstention is not None:
        return TypedGapResponseSubject.create(typed_gap=proposal.abstention)
    if (
        proposal.target_kind == "verification_rejection"
        and proposal.verification_rejection is not None
    ):
        return VerifierRejectionResponseSubject.create(
            verifier_rejection=proposal.verification_rejection
        )
    raise RealizationCompilationError("proposal has no closed response subject")


def reconstruct_response_signature_material(
    *, case: ExpandedCase, proposal: ProposalTarget, row: RealizationRow
) -> dict[str, object]:
    """Rebuild only the semantic signature material owned by ABI 1."""

    subject = response_subject_from_proposal(proposal)
    if subject != row.response_subject or row.source_case_ref != case.case_ref:
        raise RealizationCompilationError("response subject ownership drift")
    return {
        "response_subject": subject.as_dict(),
        "bindings": [item.as_dict() for item in row.bindings],
        "discourse_action_ref": row.discourse_action_ref,
        "polarity_ref": row.polarity_ref,
        "modality_ref": row.modality_ref,
        "epistemic_status_ref": row.epistemic_status_ref,
        "output_speaker_ref": row.output_speaker_ref,
        "output_addressee_ref": row.output_addressee_ref,
        "semantic_slots": [item.as_dict() for item in row.semantic_slots],
    }


class ReviewedRealizationCompiler:
    """Verify one reviewed response without invoking the runtime realizer."""

    def __init__(self, authority: LinkedAuthority) -> None:
        if type(authority) is not LinkedAuthority:
            raise TypeError("authority must be exact LinkedAuthority")
        self._authority = authority
        self._participant_refs = authority.by_kind("participant")

    def compile(
        self,
        *,
        case: ExpandedCase,
        proposal: ProposalTarget,
        row: RealizationRow,
    ) -> CompiledReviewedRealization:
        if (
            type(case) is not ExpandedCase
            or type(proposal) is not ProposalTarget
            or type(row) is not RealizationRow
        ):
            raise TypeError(
                "reviewed realization requires exact case, proposal and row"
            )
        try:
            return self._compile_checked(case=case, proposal=proposal, row=row)
        except RealizationCompilationError:
            raise
        except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
            raise RealizationCompilationError(
                "reviewed realization violates exact signature reconstruction"
            ) from exc

    def _compile_checked(
        self,
        *,
        case: ExpandedCase,
        proposal: ProposalTarget,
        row: RealizationRow,
    ) -> CompiledReviewedRealization:
        if proposal.source_case_ref != case.case_ref:
            raise RealizationCompilationError(
                "proposal belongs to another source case"
            )
        if row.source_case_ref != case.case_ref or row.language != case.language:
            raise RealizationCompilationError(
                "realization belongs to another source case or language"
            )
        if proposal.review_refs != row.review_refs:
            raise RealizationCompilationError(
                "proposal and realization review authority differ"
            )
        if not row.authorized_surface.strip() or row.authorized_surface.strip().casefold() in {
            "[no authorized surface]",
            "[no surface]",
        }:
            raise RealizationCompilationError(
                "realization has no authorized non-placeholder surface"
            )

        expected_subject = response_subject_from_proposal(proposal)
        if row.response_subject != expected_subject:
            raise RealizationCompilationError(
                "response subject differs from proposal truth"
            )
        response = case.contract.expected_response
        expected_contract = (
            f"response_action:{response.discourse_action}",
            response.polarity_ref,
            response.modality_ref,
            response.epistemic_status_ref,
        )
        actual_contract = (
            row.discourse_action_ref,
            row.polarity_ref,
            row.modality_ref,
            row.epistemic_status_ref,
        )
        if actual_contract != expected_contract:
            raise RealizationCompilationError("response contract drift")
        for participant_ref in (row.output_speaker_ref, row.output_addressee_ref):
            if participant_ref not in self._participant_refs:
                raise RealizationCompilationError(
                    "response participant is absent from linked authority"
                )

        binding_keys = tuple(item.binding_key_ref for item in row.bindings)
        if len(binding_keys) != len(set(binding_keys)):
            raise RealizationCompilationError("realization bindings are not unique")
        slot_refs = tuple(slot.slot_ref for slot in row.semantic_slots)
        if not slot_refs or len(slot_refs) != len(set(slot_refs)):
            raise RealizationCompilationError(
                "realization slots are empty or not unique"
            )
        slots = {slot.slot_ref: slot for slot in row.semantic_slots}
        covered: dict[str, int] = {slot_ref: 0 for slot_ref in slot_refs}
        omitted: list[str] = []
        alignment_refs: set[str] = set()
        operation_count = len(slots)
        alignment_order = tuple(
            (alignment.slot_ref, alignment.alignment_kind, alignment.alignment_ref)
            for alignment in row.alignments
        )
        if any(
            left >= right for left, right in zip(alignment_order, alignment_order[1:])
        ):
            raise RealizationCompilationError(
                "realization alignments are not in canonical order"
            )

        for alignment in row.alignments:
            operation_count += 1
            if type(alignment) not in {
                DesignationAlignment,
                ReferenceAlignment,
                LiteralAlignment,
                MorphologyAlignment,
                OmissionAlignment,
            }:
                raise RealizationCompilationError(
                    "realization alignment is outside the closed union"
                )
            if alignment.alignment_ref in alignment_refs:
                raise RealizationCompilationError(
                    "realization alignment identity is duplicated"
                )
            alignment_refs.add(alignment.alignment_ref)
            slot = slots.get(alignment.slot_ref)
            if slot is None:
                raise RealizationCompilationError(
                    "alignment targets an unknown semantic slot"
                )
            covered[alignment.slot_ref] += 1

            if type(alignment) is OmissionAlignment:
                if (
                    alignment.omission_authority_ref not in row.review_refs
                    or alignment.slot_ref not in response.permitted_omissions
                ):
                    raise RealizationCompilationError(
                        "semantic slot has an unreviewed omission"
                    )
                omitted.append(alignment.slot_ref)
                continue

            if (
                type(alignment.surface_start) is not int
                or type(alignment.surface_end) is not int
                or alignment.surface_start < 0
                or alignment.surface_end <= alignment.surface_start
                or alignment.surface_end > len(row.authorized_surface)
            ):
                raise RealizationCompilationError(
                    "alignment is outside the authorized output surface"
                )
            surface = row.authorized_surface[
                alignment.surface_start : alignment.surface_end
            ]

            if type(alignment) is DesignationAlignment:
                fact = self._authority.designations.resolve_fact(
                    alignment.designation_fact_ref
                )
                if (
                    fact is None
                    or fact.surface != surface
                    or fact.language != row.language
                    or fact.target_ref != slot.semantic_ref
                ):
                    raise RealizationCompilationError(
                        "designation fact alignment differs from linked authority"
                    )
            elif type(alignment) is ReferenceAlignment:
                if (
                    alignment.reference_authority_ref not in row.review_refs
                    or alignment.participant_ref != slot.semantic_ref
                    or alignment.participant_ref not in self._participant_refs
                ):
                    raise RealizationCompilationError(
                        "reference alignment lacks exact participant authority"
                    )
            elif type(alignment) is LiteralAlignment:
                expected_literal_ref = stable_ref(
                    "reviewed_literal",
                    {
                        "literal": surface,
                        "language": row.language,
                        "review_refs": list(row.review_refs),
                    },
                )
                if alignment.literal_source_ref != expected_literal_ref:
                    raise RealizationCompilationError(
                        "literal alignment lacks independently reviewed source authority"
                    )
            elif (
                alignment.morphology_authority_ref not in row.review_refs
            ):
                raise RealizationCompilationError(
                    "morphology alignment lacks row-local review authority"
                )

        for slot in row.semantic_slots:
            count = covered[slot.slot_ref]
            if (slot.required and count != 1) or (not slot.required and count > 1):
                raise RealizationCompilationError("semantic slot coverage drift")

        if type(expected_subject) in {
            TypedGapResponseSubject,
            VerifierRejectionResponseSubject,
        }:
            if row.authorized_surface.strip().casefold() == case.surface.strip().casefold():
                raise RealizationCompilationError(
                    "safe realization cannot echo the input surface"
                )
            if (
                len(row.alignments) != 1
                or type(row.alignments[0]) is not LiteralAlignment
                or row.alignments[0].surface_start != 0
                or row.alignments[0].surface_end != len(row.authorized_surface)
            ):
                raise RealizationCompilationError(
                    "safe realization requires one full-surface reviewed literal"
                )

        material = reconstruct_response_signature_material(
            case=case, proposal=proposal, row=row
        )
        signature_ref = stable_ref("response_signature", material)
        if signature_ref != row.response_signature_ref:
            raise RealizationCompilationError(
                "response signature does not reconstruct"
            )
        omitted_refs = set(omitted)
        return CompiledReviewedRealization(
            response_signature_ref=signature_ref,
            authorized_surface=row.authorized_surface,
            covered_slot_refs=tuple(
                slot_ref for slot_ref in slot_refs if covered[slot_ref]
            ),
            omitted_slot_refs=tuple(
                slot_ref for slot_ref in slot_refs if slot_ref in omitted_refs
            ),
            operation_count=operation_count,
        )


__all__ = [
    "CompiledReviewedRealization",
    "RealizationCompilationError",
    "ReviewedRealizationCompiler",
    "reconstruct_response_signature_material",
    "response_subject_from_proposal",
]
