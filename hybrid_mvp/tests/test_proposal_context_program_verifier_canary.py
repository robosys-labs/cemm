from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.contributions import SemanticContribution
from cemm_authoritative_hybrid.cycle import Orientation, SemanticMode
from cemm_authoritative_hybrid.forms import (
    EvidenceItem,
    EvidencePacket,
    FormHypothesis,
    FormLattice,
    FormUnit,
)
from cemm_authoritative_hybrid.grounding import DesignationCandidate, GroundingResult
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
    ProposalContext,
    ProposalContextBuilder,
)
from cemm_authoritative_hybrid.verifier import ExactProgramVerifier


def _pin(authority: object) -> RevisionPin:
    return RevisionPin(authority.generation, 1, 2, 3, 4, "model:canary")


def _orientation(
    authority: object,
    source_text: str,
    *,
    turn_ref: str = "turn:1",
    mode: SemanticMode = SemanticMode.OBSERVE,
) -> Orientation:
    pin = _pin(authority)
    return Orientation.create(
        session_ref="session:canary",
        turn_ref=turn_ref,
        source_text=source_text,
        mode=mode,
        participant_frame="participant:user",
        temporal_frame="now",
        focus_refs=(),
        obligation_refs=(),
        capability_summary=(),
        permission_summary=(),
        budgets={"proposal": 16},
        participants=("participant:user", "participant:system"),
        active_turn_ref=turn_ref,
        event_refs=(),
        scanned_atom_count=0,
        index_probes=(),
        visited_refs=(),
        revision_pin=pin,
    )

def _evidence(
    source_text: str, *, source_ref: str = "evidence:canary"
) -> EvidencePacket:
    item = EvidenceItem.create(
        source="text",
        content=source_text,
        source_ref=source_ref,
        provenance_refs=("turn:1",),
        adapter_receipt_ref=None,
    )
    return EvidencePacket.create(
        items=(item,),
        source_text=source_text,
        form_pack_hash="form-pack:canary",
    )


def _relation_lattice(current_evidence: EvidencePacket) -> FormLattice:
    source = "alicelikesbob"
    return FormLattice.create(
        evidence_packet_ref=current_evidence.packet_ref,
        form_pack_hash="form-pack:canary",
        units=(
            FormUnit("unit:alice", "alice", ("alice",), 0, 5, ()),
            FormUnit("unit:likes", "likes", ("likes",), 5, 10, ()),
            FormUnit("unit:bob", "bob", ("bob",), 10, 13, ()),
        ),
        hypotheses=(),
        source_text=source,
    )


def _relation_grounding(
    authority: object,
    lattice: FormLattice,
    revision_pin: RevisionPin,
) -> GroundingResult:
    rows = (
        ("unit:alice", "alice", "entity:alice"),
        ("unit:likes", "likes", "rel:likes"),
        ("unit:bob", "bob", "entity:bob"),
    )
    return GroundingResult.create(
        evidence_packet_ref=lattice.evidence_packet_ref,
        form_lattice_ref=lattice.lattice_ref,
        revision_pin=revision_pin,
        designations=tuple(
            DesignationCandidate(
                unit_refs=(unit_ref,),
                target_ref=target_ref,
                designation_fact_ref=stable_ref(
                    "designation",
                    {"surface": surface, "target": target_ref, "language": "en"},
                ),
                score=1.0,
                provenance_refs=(authority.generation,),
            )
            for unit_ref, surface, target_ref in rows
        ),
        unresolved=(),
        grounded_items=(),
        provenance_refs=(authority.generation,),
    )


def _contribution(
    *,
    unit_ref: str,
    target_ref: str,
    kind: str,
    input_ports: tuple[str, ...],
    output_ports: tuple[str, ...],
) -> SemanticContribution:
    material = {
        "kind": kind,
        "target": target_ref,
        "units": [unit_ref],
        "inputs": list(input_ports),
        "outputs": list(output_ports),
    }
    return SemanticContribution(
        contribution_ref=stable_ref("contribution", material),
        kind=kind,
        source_unit_refs=(unit_ref,),
        target_ref=target_ref,
        input_ports=input_ports,
        output_ports=output_ports,
        constraints=(),
    )


def _relation_contributions() -> tuple[SemanticContribution, ...]:
    return (
        _contribution(
            unit_ref="unit:alice",
            target_ref="entity:alice",
            kind="anchor",
            input_ports=(),
            output_ports=("role:subject",),
        ),
        _contribution(
            unit_ref="unit:likes",
            target_ref="rel:likes",
            kind="predicate",
            input_ports=("role:subject", "role:object"),
            output_ports=("role:relation",),
        ),
        _contribution(
            unit_ref="unit:bob",
            target_ref="entity:bob",
            kind="anchor",
            input_ports=(),
            output_ports=("role:object",),
        ),
    )


def _build_relation_context(linked_authority, affordance_index, *, turn_ref="turn:1"):
    current_evidence = _evidence(
        "alicelikesbob",
        source_ref=f"evidence:{turn_ref}",
    )
    lattice = _relation_lattice(current_evidence)
    current_orientation = _orientation(
        linked_authority,
        lattice.source_text,
        turn_ref=turn_ref,
    )
    assert current_orientation.revision_pin is not None
    return ProposalContextBuilder(
        linked_authority,
        affordance_index,
        RuntimeConfig.release(),
    ).build(
        orientation=current_orientation,
        evidence=current_evidence,
        form_lattice=lattice,
        grounding_result=_relation_grounding(
            linked_authority,
            lattice,
            current_orientation.revision_pin,
        ),
        contributions=_relation_contributions(),
    )


def _program_from_context(context: ProposalContext) -> SemanticSwitchProgram:
    mode = context.mode_slots[0]
    frame = next(
        row
        for row in context.application_frames
        if row.predicate_target_ref == "rel:likes"
    )
    designations = tuple(
        sorted(context.designation_slots, key=lambda row: row.target_ref)
    )
    contribution_by_target = {
        row.target_ref: row
        for row in context.contribution_slots
        if row.target_ref is not None
    }
    actions = [
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=(mode.slot_ref,),
        ),
    ]
    for designation in designations:
        actions.append(
            ProgramAction.create(
                action_index=len(actions),
                action_type="select_designation",
                arguments=(designation.slot_ref,),
            )
        )
    instantiate = ProgramAction.create(
        action_index=len(actions),
        action_type="instantiate_operator",
        arguments=("application:likes", frame.slot_ref),
        source_unit_refs=("unit:likes",),
    )
    actions.append(instantiate)
    subject = ProgramAction.create(
        action_index=len(actions),
        action_type="bind_role",
        arguments=(
            "application:likes",
            "role:subject",
            contribution_by_target["entity:alice"].slot_ref,
        ),
        source_unit_refs=("unit:alice",),
    )
    actions.append(subject)
    object_action = ProgramAction.create(
        action_index=len(actions),
        action_type="bind_role",
        arguments=(
            "application:likes",
            "role:object",
            contribution_by_target["entity:bob"].slot_ref,
        ),
        source_unit_refs=("unit:bob",),
    )
    actions.append(object_action)
    actions.append(
        ProgramAction.create(
            action_index=len(actions),
            action_type="complete_program",
            arguments=(),
        )
    )
    assignments = (
        SourceAssignment.create(
            source_unit_ref="unit:alice",
            contribution_slot_ref=contribution_by_target["entity:alice"].slot_ref,
            assignment_kind="role",
            target_action_ref=subject.action_ref,
            target_role_ref="role:subject",
            residual_kind=None,
            critical=True,
        ),
        SourceAssignment.create(
            source_unit_ref="unit:likes",
            contribution_slot_ref=contribution_by_target["rel:likes"].slot_ref,
            assignment_kind="predicate",
            target_action_ref=instantiate.action_ref,
            target_role_ref=None,
            residual_kind=None,
            critical=True,
        ),
        SourceAssignment.create(
            source_unit_ref="unit:bob",
            contribution_slot_ref=contribution_by_target["entity:bob"].slot_ref,
            assignment_kind="role",
            target_action_ref=object_action.action_ref,
            target_role_ref="role:object",
            residual_kind=None,
            critical=True,
        ),
    )
    return SemanticSwitchProgram.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        actions=tuple(actions),
        root_refs=("application:likes",),
        mode_slot_ref=mode.slot_ref,
        goal_refs=("goal:understand",),
        source_unit_refs=context.source_unit_refs,
        source_assignments=assignments,
        revision_pin=context.revision_pin,
    )


def _proposal(
    context: ProposalContext, program: SemanticSwitchProgram
) -> ProposalResult:
    candidate = RankedProgramCandidate.create(
        rank=0,
        score_q=900_000,
        program=program,
        provenance_refs=(context.evidence_packet_ref, context.form_lattice_ref),
    )
    return ProposalResult.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        candidates=(candidate,),
        status="candidates",
        abstention_code=None,
        explored_states=1,
        truncated=False,
        model_identity=context.revision_pin.model_identity or "",
        revision_pin=context.revision_pin,
    )


def test_builder_program_proposal_verifier_preserve_exact_lineage(
    linked_authority,
    affordance_index,
) -> None:
    context = _build_relation_context(linked_authority, affordance_index)
    expected_orientation = _orientation(linked_authority, "alicelikesbob")
    assert context.orientation_ref == expected_orientation.orientation_ref
    program = _program_from_context(context)
    proposal = _proposal(context, program)

    batch = ExactProgramVerifier().verify_candidates(proposal, context)

    assert batch.status == "selected"
    assert batch.proposal_context_ref == context.context_ref
    assert batch.selected_candidate_ref == proposal.candidates[0].candidate_ref
    assert batch.selected_meaning is not None
    meaning = batch.selected_meaning
    receipt = batch.candidate_receipts[0]
    assert meaning.program_ref == program.program_ref
    assert meaning.expression.expression_ref != program.program_ref
    assert receipt.program_ref == program.program_ref
    assert receipt.coverage_receipt.program_ref == program.program_ref
    assert receipt.coverage_receipt.proposal_context_ref == context.context_ref
    assert receipt.compilation_proof is not None
    assert receipt.compilation_proof.program_ref == program.program_ref
    assert receipt.compilation_proof.proposal_context_ref == context.context_ref
    assert receipt.compilation_proof.expression_ref == meaning.expression.expression_ref
    assert meaning.coverage_receipt_ref == receipt.coverage_receipt.coverage_receipt_ref
    assert meaning.compilation_proof_ref == receipt.compilation_proof.proof_ref
    assert meaning.verification_receipt_ref == receipt.receipt_ref
    assert meaning.revision_pin == context.revision_pin == program.revision_pin
    assert set(meaning.grounding_refs) == set(receipt.compilation_proof.grounding_refs)


def test_cross_cycle_context_program_mismatch_fails_closed(
    linked_authority,
    affordance_index,
) -> None:
    first = _build_relation_context(
        linked_authority,
        affordance_index,
        turn_ref="turn:1",
    )
    second = _build_relation_context(
        linked_authority,
        affordance_index,
        turn_ref="turn:2",
    )
    program = _program_from_context(first)
    proposal = _proposal(first, program)

    assert first.context_ref != second.context_ref
    with pytest.raises(ValueError, match="identities differ"):
        ExactProgramVerifier().verify_candidates(proposal, second)


def test_builder_does_not_hide_source_behind_structural_slot_without_contribution(
    linked_authority,
    affordance_index,
) -> None:
    source = "mode"
    current_evidence = _evidence(source)
    lattice = FormLattice.create(
        evidence_packet_ref=current_evidence.packet_ref,
        form_pack_hash="form-pack:canary",
        units=(FormUnit("unit:mode", source, (source,), 0, 4, ()),),
        hypotheses=(
            FormHypothesis(
                "hypothesis:observe",
                ("unit:mode",),
                "OBSERVE",
                (),
            ),
        ),
        source_text=source,
    )
    current_orientation = _orientation(linked_authority, source)
    assert current_orientation.revision_pin is not None
    empty_grounding = GroundingResult.create(
        evidence_packet_ref=lattice.evidence_packet_ref,
        form_lattice_ref=lattice.lattice_ref,
        revision_pin=current_orientation.revision_pin,
        designations=(),
        unresolved=(),
        grounded_items=(),
        provenance_refs=(),
    )
    context = ProposalContextBuilder(
        linked_authority,
        affordance_index,
        RuntimeConfig.release(),
    ).build(
        orientation=current_orientation,
        evidence=current_evidence,
        form_lattice=lattice,
        grounding_result=empty_grounding,
        contributions=(),
    )

    residual = context.residual_for_source("unit:mode")
    assert residual is not None
    assert residual.critical is True
    assert context.contributions_for_source("unit:mode") == ()


def test_proposal_context_rejects_incomplete_source_partition(
    linked_authority,
    affordance_index,
) -> None:
    context = _build_relation_context(linked_authority, affordance_index)
    fields = {
        "orientation_ref": context.orientation_ref,
        "evidence_packet_ref": context.evidence_packet_ref,
        "form_lattice_ref": context.form_lattice_ref,
        "grounding_ref": context.grounding_ref,
        "designation_slots": context.designation_slots,
        "contribution_slots": tuple(
            row
            for row in context.contribution_slots
            if "unit:alice" not in row.source_unit_refs
        ),
        "mode_slots": context.mode_slots,
        "application_frames": context.application_frames,
        "reference_slots": context.reference_slots,
        "scope_slots": context.scope_slots,
        "expression_link_slots": context.expression_link_slots,
        "variable_slots": context.variable_slots,
        "transition_slots": context.transition_slots,
        "residual_evidence": context.residual_evidence,
        "context_refs": context.context_refs,
        "source_unit_refs": context.source_unit_refs,
        "source_unit_spans": context.source_unit_spans,
        "revision_pin": context.revision_pin,
    }

    with pytest.raises(ValueError, match="source partition"):
        ProposalContext.create(**fields)


__cemm_test_inventory__ = {'tests/test_proposal_context_program_verifier_canary.py::test_builder_does_not_hide_source_behind_structural_slot_without_contribution': {'activation_phase': 'R1',
                                                                                                                                           'assertion_ref': 'assertion:r1-proposal-context-program-verifier-canary-test-builder-does-not-hide-source-behind-structural-slot-without-contribution',
                                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                                           'introduced_by_task': 'R1-Task-7',
                                                                                                                                           'owner_ref': 'program-verifier',
                                                                                                                                           'source_ast_sha256': '3a16b0888b4b731dd3220511c333904bde9ac8994d0fb2ea0d3e8f4ff772a904'},
 'tests/test_proposal_context_program_verifier_canary.py::test_builder_program_proposal_verifier_preserve_exact_lineage': {'activation_phase': 'R1',
                                                                                                                           'assertion_ref': 'assertion:r1-slice-b-lineage-canary-exact-orientation',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'R1-Slice-B',
                                                                                                                           'owner_ref': 'runtime-path',
                                                                                                                           'source_ast_sha256': 'c9f4fdfa8648a4aec11923695949e80a8a3c6c6308edf9f61a657d0422c92756'},
 'tests/test_proposal_context_program_verifier_canary.py::test_cross_cycle_context_program_mismatch_fails_closed': {'activation_phase': 'R1',
                                                                                                                    'assertion_ref': 'assertion:r1-proposal-context-program-verifier-canary-test-cross-cycle-context-program-mismatch-fails-closed',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'R1-Task-7',
                                                                                                                    'owner_ref': 'program-verifier',
                                                                                                                    'source_ast_sha256': 'f87933327f748e697ac99091b074c3f868b188418aa5b6e39feae2e85a73746b'},
 'tests/test_proposal_context_program_verifier_canary.py::test_proposal_context_rejects_incomplete_source_partition': {'activation_phase': 'R1',
                                                                                                                       'assertion_ref': 'assertion:r1-proposal-context-program-verifier-canary-test-proposal-context-rejects-incomplete-source-partition',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'R1-Task-7',
                                                                                                                       'owner_ref': 'program-verifier',
                                                                                                                       'source_ast_sha256': 'fbb6b67289cc5dd26a1e1707b9c4c6fe0006b703367c0573f59270e9233008d1'}}
