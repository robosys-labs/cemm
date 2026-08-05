"""Regression canaries for the 8ae17cd R2 deep-review correction."""

from __future__ import annotations

from types import SimpleNamespace

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.forms import FormResolver
from cemm_authoritative_hybrid.grounding import Grounder
from cemm_authoritative_hybrid.literal_codec import (
    decode_literal_slot,
    decode_literal_value,
)
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.proposal import BootstrapProposer
from cemm_authoritative_hybrid.proposal_context import (
    ApplicationFrameSlot,
    ContributionSlot,
    DesignationSlot,
    ModeSlot,
    ProposalContext,
    VariableSlot,
)


def test_literal_decoder_returns_exact_scalar_types():
    assert decode_literal_value("string", "42") == "42"
    assert decode_literal_value("integer", "42") == 42
    assert type(decode_literal_value("integer", "42")) is int
    assert decode_literal_value("boolean", "true") is True
    assert decode_literal_value("boolean", "false") is False


def test_literal_slot_requires_one_exact_kind():
    slot = SimpleNamespace(
        literal_value="-7",
        constraints=(("literal", "-7"), ("literal_kind", "integer")),
    )
    kind, value = decode_literal_slot(slot)
    assert kind == "integer"
    assert value == -7
    assert type(value) is int


def test_multi_unit_designation_is_grounded_as_one_span():
    class _DesignationIndex:
        @staticmethod
        def for_surface(surface, language):
            if (surface, language) == ("mother in law", "en"):
                return ("rel:mother_in_law",)
            return ()

    authority = SimpleNamespace(designations=_DesignationIndex())
    config = RuntimeConfig.release()
    form_pack = {
        "language": "en",
        "tokenization": {"lowercase": True, "punctuation": []},
    }
    resolver = FormResolver(form_pack, config)
    lattice = resolver.resolve("mother in law")
    grounder = Grounder(
        authority=authority,
        config=config,
        form_pack=form_pack,
        form_pack_hash=resolver.form_pack_hash,
    )
    pin = RevisionPin("authority:test", 1, 2, 3, 4, "bootstrap-proposer")
    result = grounder.ground_lattice(lattice, pin)
    matches = [
        row for row in result.designations
        if row.target_ref == "rel:mother_in_law"
    ]
    assert len(matches) == 1
    assert len(matches[0].unit_refs) == 3


def _query_context() -> ProposalContext:
    pin = RevisionPin(
        "authority:bootstrap", 1, 2, 3, 4, BootstrapProposer.model_identity
    )
    mode = ModeSlot.create(
        mode="QUERY",
        source_unit_refs=("unit:who",),
        construction_ref="hyp:query",
        requested_effect="query",
    )
    designation = DesignationSlot.create(
        source_unit_refs=("unit:predicate",),
        target_ref="event:test-query",
        target_kind="event_type",
        score_q=900_000,
        designation_fact_ref="designation:test-query",
        provenance_refs=("designation:test-query",),
    )
    predicate = ContributionSlot.create(
        contribution_ref="contribution:predicate",
        kind="predicate",
        source_unit_refs=("unit:predicate",),
        target_ref="event:test-query",
        target_kind="event_type",
        input_ports=("role:subject",),
        output_ports=("role:event",),
        constraints=(),
        provenance_refs=(designation.slot_ref,),
    )
    variable_contribution = ContributionSlot.create(
        contribution_ref="contribution:who",
        kind="open_variable",
        source_unit_refs=("unit:who",),
        target_ref=None,
        target_kind=None,
        input_ports=(),
        output_ports=("role:variable",),
        constraints=(("query", "query"),),
        provenance_refs=("hyp:query",),
    )
    frame = ApplicationFrameSlot.create(
        designation_slot_ref=designation.slot_ref,
        predicate_target_ref=designation.target_ref,
        predicate_kind=designation.target_kind,
        operator_ref="op:event",
        structural_role_ref="role:event",
        required_roles=("role:subject",),
        optional_roles=(),
        proposition_roles=(),
        source_unit_refs=("unit:predicate",),
        derived_role_targets=(),
        affordance_frame_ref="frame:test-query",
        provenance_refs=(designation.slot_ref, "frame:test-query"),
    )
    variable = VariableSlot.create(
        application_frame_ref=frame.slot_ref,
        role_ref="role:subject",
        required_kinds=("entity", "participant", "concept"),
        source_unit_refs=("unit:who",),
        construction_ref="hyp:query",
    )
    return ProposalContext.create(
        orientation_ref="orientation:bootstrap",
        evidence_packet_ref="evidence:bootstrap",
        form_lattice_ref="lattice:bootstrap",
        grounding_ref="grounding:bootstrap",
        designation_slots=(designation,),
        contribution_slots=(predicate, variable_contribution),
        mode_slots=(mode,),
        application_frames=(frame,),
        reference_slots=(),
        scope_slots=(),
        expression_link_slots=(),
        variable_slots=(variable,),
        transition_slots=(),
        residual_evidence=(),
        context_refs=("turn:bootstrap",),
        source_unit_refs=("unit:predicate", "unit:who"),
        source_unit_spans=(
            ("unit:predicate", 0, 4),
            ("unit:who", 4, 7),
        ),
        revision_pin=pin,
    )


def test_query_mode_preserves_variable_source_for_projection():
    proposal = BootstrapProposer(RuntimeConfig.release()).propose(_query_context())
    assert proposal.status == "candidates"
    assert proposal.candidates
    assert any(
        action.action_type == "project_variable"
        for action in proposal.candidates[0].program.actions
    )
    variable_assignments = [
        row
        for row in proposal.candidates[0].program.source_assignments
        if row.source_unit_ref == "unit:who"
    ]
    assert len(variable_assignments) == 1
    assert variable_assignments[0].target_role_ref == "role:subject"
