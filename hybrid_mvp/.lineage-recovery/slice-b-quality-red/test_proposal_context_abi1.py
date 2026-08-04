from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from types import MappingProxyType
from typing import Any

import pytest

import cemm_authoritative_hybrid.proposal_context as context_module

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.proposal_context import (
    PROPOSAL_CONTEXT_ABI_VERSION,
    ApplicationFrameSlot,
    ContributionSlot,
    DesignationSlot,
    ExpressionLinkSlot,
    ModeSlot,
    ProposalContext,
    ReferenceSlot,
    ResidualEvidence,
    ScopeSlot,
    TransitionSlot,
    VariableSlot,
)


def _pin(*, world_revision: int = 2) -> RevisionPin:
    return RevisionPin("authority:g1", world_revision, 3, 4, 5, "model:m1")


def _slots() -> dict[str, Any]:
    designation = DesignationSlot.create(
        source_unit_refs=("unit:loves",),
        target_ref="dimension:availability",
        target_kind="state_dimension",
        score_q=950_000,
        designation_fact_ref="designation:availability",
        provenance_refs=("authority:g1",),
    )
    contribution = ContributionSlot.create(
        contribution_ref="contribution:alice-anchor",
        kind="anchor",
        source_unit_refs=("unit:alice",),
        target_ref="entity:alice",
        target_kind="entity",
        input_ports=(),
        output_ports=("role:subject",),
        constraints=(("source", "designation"),),
        provenance_refs=("designation:alice",),
        literal_value=None,
    )
    predicate_contribution = ContributionSlot.create(
        contribution_ref="contribution:availability-predicate",
        kind="predicate",
        source_unit_refs=("unit:loves",),
        target_ref="dimension:availability",
        target_kind="state_dimension",
        input_ports=("role:subject", "role:value"),
        output_ports=("role:dimension",),
        constraints=(("source", "designation"),),
        provenance_refs=("designation:availability",),
        literal_value=None,
    )
    mode = ModeSlot.create(
        mode="OBSERVE",
        source_unit_refs=(),
        construction_ref=None,
        requested_effect="admission",
    )
    frame = ApplicationFrameSlot.create(
        designation_slot_ref=designation.slot_ref,
        predicate_target_ref="dimension:availability",
        predicate_kind="state_dimension",
        operator_ref="op:state",
        structural_role_ref="role:dimension",
        required_roles=("role:subject", "role:value"),
        optional_roles=(),
        proposition_roles=(),
        source_unit_refs=("unit:loves",),
        derived_role_targets=(("role:dimension", "dimension:availability"),),
        affordance_frame_ref="frame:availability",
        provenance_refs=(designation.slot_ref, "authority:g1", "frame:availability"),
    )
    reference = ReferenceSlot.create(
        target_ref="entity:alice",
        target_kind="entity",
        source_unit_refs=("unit:alice",),
        resolution_kind="designation",
        compatible_roles=("role:subject",),
        score_q=900_000,
        provenance_refs=(designation.slot_ref,),
    )
    scope = ScopeSlot.create(
        operator_type="scope:polarity",
        value_ref="value:positive",
        source_unit_refs=(),
        construction_ref=None,
    )
    link = ExpressionLinkSlot.create(
        link_type="link:sequence",
        commutative=False,
        min_arity=2,
        max_arity=2,
        source_unit_refs=(),
        construction_ref="construction:sequence",
    )
    variable = VariableSlot.create(
        application_frame_ref=frame.slot_ref,
        role_ref="role:object",
        required_kinds=("entity",),
        source_unit_refs=(),
        construction_ref="construction:query",
    )
    transition = TransitionSlot.create(
        application_frame_ref=frame.slot_ref,
        event_type_ref="event:set_state",
        compatible_modes=("REQUEST", "SIMULATE"),
        required_roles=("role:actor", "role:target", "role:dimension", "role:value"),
        required_capabilities=("cap:set_state",),
        required_permissions=("permission:set_state",),
        adapter_ref="adapter:state",
        source_unit_refs=(),
    )
    residual = ResidualEvidence.create(
        source_unit_ref="unit:period",
        contribution_kind="discourse",
        critical=False,
        reason="punctuation",
    )
    return {
        "designation": designation,
        "contribution": contribution,
        "predicate_contribution": predicate_contribution,
        "mode": mode,
        "frame": frame,
        "reference": reference,
        "scope": scope,
        "link": link,
        "variable": variable,
        "transition": transition,
        "residual": residual,
    }


def _context(*, pin: RevisionPin | None = None) -> ProposalContext:
    slots = _slots()
    return ProposalContext.create(
        orientation_ref="orientation:1",
        evidence_packet_ref="evidence:1",
        form_lattice_ref="lattice:1",
        grounding_ref="grounding:1",
        designation_slots=(slots["designation"],),
        contribution_slots=(slots["contribution"], slots["predicate_contribution"]),
        mode_slots=(slots["mode"],),
        application_frames=(slots["frame"],),
        reference_slots=(slots["reference"],),
        scope_slots=(slots["scope"],),
        expression_link_slots=(slots["link"],),
        variable_slots=(slots["variable"],),
        transition_slots=(slots["transition"],),
        residual_evidence=(slots["residual"],),
        context_refs=("turn:1",),
        source_unit_refs=("unit:alice", "unit:loves", "unit:period"),
        source_unit_spans=(
            ("unit:alice", 0, 5),
            ("unit:loves", 5, 10),
            ("unit:period", 10, 11),
        ),
        revision_pin=pin or _pin(),
    )


def _creation_fields(context: ProposalContext) -> dict[str, Any]:
    return {
        "orientation_ref": context.orientation_ref,
        "evidence_packet_ref": context.evidence_packet_ref,
        "form_lattice_ref": context.form_lattice_ref,
        "grounding_ref": context.grounding_ref,
        "designation_slots": context.designation_slots,
        "contribution_slots": context.contribution_slots,
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


def _contains_float(value: Any) -> bool:
    if isinstance(value, float):
        return True
    if isinstance(value, dict):
        return any(_contains_float(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_float(item) for item in value)
    return False


def test_proposal_context_abi1_is_content_addressed_and_round_trips_exactly() -> None:
    context = _context()

    assert PROPOSAL_CONTEXT_ABI_VERSION == 1
    assert context.context_ref.startswith("proposal_context:")
    assert ProposalContext.from_dict(context.as_dict()) == context
    assert not _contains_float(context.as_dict())
    assert "resolved_applications" not in context.as_dict()
    assert "semantic_expression" not in context.as_dict()


def test_proposal_context_identity_includes_required_grounding_ref() -> None:
    context = _context()
    fields = _creation_fields(context)
    changed = ProposalContext.create(**(fields | {"grounding_ref": "grounding:other"}))

    assert context.as_dict()["grounding_ref"] == "grounding:1"
    assert changed.grounding_ref == "grounding:other"
    assert changed.context_ref != context.context_ref


def test_every_slot_is_content_addressed_and_strictly_round_trips() -> None:
    for slot in _slots().values():
        assert type(slot).from_dict(slot.as_dict()) == slot
        ref_field = "residual_ref" if isinstance(slot, ResidualEvidence) else "slot_ref"
        with pytest.raises(ValueError, match="ref mismatch"):
            replace(slot, **{ref_field: "forged:ref"})


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (lambda payload: payload.update({"abi_version": True}), "ABI"),
        (lambda payload: payload.update({"abi_version": 1.0}), "ABI"),
        (lambda payload: payload.update({"unknown": "field"}), "fields"),
        (
            lambda payload: payload["designation_slots"][0].update({"score_q": 0.5}),
            "score_q",
        ),
        (
            lambda payload: payload["revision_pin"].update({"world_revision": True}),
            "world_revision",
        ),
    ),
    ids=(
        "bool-abi-version",
        "float-abi-version",
        "unknown-top-level-field",
        "float-score",
        "bool-revision",
    ),
)
def test_context_deserialization_rejects_non_exact_wire_values(
    mutation: Any, message: str
) -> None:
    payload = _context().as_dict()
    mutation(payload)

    with pytest.raises((TypeError, ValueError), match=message):
        ProposalContext.from_dict(payload)


def test_nested_slot_tampering_cannot_be_hidden_by_container_ref() -> None:
    payload = _context().as_dict()
    payload["designation_slots"][0]["target_ref"] = "entity:bob"

    with pytest.raises(ValueError, match="ref mismatch"):
        ProposalContext.from_dict(payload)


def test_context_identity_covers_revision_and_all_slot_content() -> None:
    original = _context()
    revised = _context(pin=_pin(world_revision=9))
    changed_scope = ScopeSlot.create(
        operator_type="scope:polarity",
        value_ref="value:negative",
        source_unit_refs=(),
        construction_ref=None,
    )
    changed = ProposalContext.create(
        orientation_ref=original.orientation_ref,
        evidence_packet_ref=original.evidence_packet_ref,
        form_lattice_ref=original.form_lattice_ref,
        grounding_ref=original.grounding_ref,
        designation_slots=original.designation_slots,
        contribution_slots=original.contribution_slots,
        mode_slots=original.mode_slots,
        application_frames=original.application_frames,
        reference_slots=original.reference_slots,
        scope_slots=(changed_scope,),
        expression_link_slots=original.expression_link_slots,
        variable_slots=original.variable_slots,
        transition_slots=original.transition_slots,
        residual_evidence=original.residual_evidence,
        context_refs=original.context_refs,
        source_unit_refs=original.source_unit_refs,
        source_unit_spans=original.source_unit_spans,
        revision_pin=original.revision_pin,
    )

    assert original.context_ref != revised.context_ref
    assert original.context_ref != changed.context_ref


def test_context_rejects_duplicate_slots_unknown_sources_and_invalid_spans() -> None:
    context = _context()
    fields = _creation_fields(context)
    fields["designation_slots"] = context.designation_slots * 2
    with pytest.raises(ValueError, match="duplicate designation"):
        ProposalContext.create(**fields)
    fields = _creation_fields(context)
    fields["source_unit_refs"] = ("unit:alice", "unit:period")
    fields["source_unit_spans"] = (
        ("unit:alice", 0, 5),
        ("unit:period", 5, 6),
    )
    with pytest.raises(ValueError, match="unknown source unit"):
        ProposalContext.create(**fields)
    fields = _creation_fields(context)
    fields["source_unit_spans"] = (
        ("unit:alice", 5, 0),
        ("unit:loves", 6, 11),
        ("unit:period", 11, 12),
    )
    with pytest.raises(ValueError, match="source span"):
        ProposalContext.create(**fields)
    duplicate_residual = ResidualEvidence.create(
        source_unit_ref="unit:period",
        contribution_kind="discourse",
        critical=False,
        reason="terminal punctuation",
    )
    fields = _creation_fields(context)
    fields["residual_evidence"] = (*context.residual_evidence, duplicate_residual)
    with pytest.raises(ValueError, match="duplicate residual source"):
        ProposalContext.create(**fields)


@pytest.mark.parametrize(
    "spans",
    (
        (
            ("unit:alice", 0, 0),
            ("unit:loves", 0, 5),
            ("unit:period", 5, 6),
        ),
        (
            ("unit:alice", 0, 5),
            ("unit:loves", 6, 11),
            ("unit:period", 5, 6),
        ),
        (
            ("unit:alice", 0, 5),
            ("unit:loves", 4, 9),
            ("unit:period", 9, 10),
        ),
    ),
    ids=("zero-width", "gap", "overlap"),
)
def test_direct_context_rejects_zero_width_and_noncontiguous_spans(
    spans: tuple[tuple[str, int, int], ...],
) -> None:
    context = _context()
    fields = _creation_fields(context)
    fields["source_unit_spans"] = spans

    with pytest.raises(ValueError, match="source span"):
        ProposalContext.create(**fields)


def test_context_codec_rejects_noncontiguous_wire_spans() -> None:
    payload = _context().as_dict()
    payload["source_unit_spans"][1][1] += 1
    payload["source_unit_spans"][1][2] += 1

    with pytest.raises(ValueError, match="source span"):
        ProposalContext.from_dict(payload)


def test_context_slot_tuples_are_bounded_by_runtime_config() -> None:
    context = _context()
    second = DesignationSlot.create(
        source_unit_refs=("unit:loves",),
        target_ref="relation:love",
        target_kind="relation_type",
        score_q=800_000,
        designation_fact_ref="designation:love",
        provenance_refs=("authority:g1",),
    )

    fields = _creation_fields(context)
    fields["designation_slots"] = (context.designation_slots[0], second)
    with pytest.raises(ValueError, match="designation slot bound"):
        ProposalContext.create(
            **fields, config=RuntimeConfig(max_orientation_alternatives=1)
        )


def test_mode_slots_use_the_orientation_alternative_bound() -> None:
    context = _context()
    fields = _creation_fields(context)
    fields["mode_slots"] = tuple(
        ModeSlot.create(
            mode="OBSERVE",
            source_unit_refs=(),
            construction_ref=f"construction:{index}",
            requested_effect="admission",
        )
        for index in range(5)
    )

    expanded = ProposalContext.create(**fields)

    assert len(expanded.mode_slots) == 5


def test_lookup_maps_are_prebuilt_immutable_and_not_serialized() -> None:
    context = _context()
    designation = context.designation_slots[0]
    frame = context.application_frames[0]

    assert context.designation(designation.slot_ref) is designation
    assert (
        context.contribution(context.contribution_slots[0].slot_ref)
        is context.contribution_slots[0]
    )
    assert context.contributions_for_source("unit:alice") == (
        context.contribution_slots[0],
    )
    assert context.contributions_for_source("unit:unknown") == ()
    assert isinstance(context._contributions_by_source, MappingProxyType)
    with pytest.raises(TypeError):
        context._contributions_by_source["forged"] = context.contribution_slots  # type: ignore[index]
    assert context.mode_slot(context.mode_slots[0].slot_ref) is context.mode_slots[0]
    assert context.frame(frame.slot_ref) is frame
    assert context.frame_for_designation(designation.slot_ref) == (frame,)
    assert (
        context.reference(context.reference_slots[0].slot_ref)
        is context.reference_slots[0]
    )
    assert context.scope(context.scope_slots[0].slot_ref) is context.scope_slots[0]
    assert (
        context.expression_link(context.expression_link_slots[0].slot_ref)
        is context.expression_link_slots[0]
    )
    assert (
        context.variable(context.variable_slots[0].slot_ref)
        is context.variable_slots[0]
    )
    assert (
        context.transition(context.transition_slots[0].slot_ref)
        is context.transition_slots[0]
    )
    assert (
        context.residual(context.residual_evidence[0].residual_ref)
        is context.residual_evidence[0]
    )
    assert context.residual_for_source("unit:period") is context.residual_evidence[0]
    assert context.has_context_ref("turn:1") is True
    assert context.source_span(("unit:alice", "unit:loves")) == (0, 10)
    assert context.source_span(("unit:alice", "unit:unknown")) is None
    assert isinstance(context._designation_by_ref, MappingProxyType)
    with pytest.raises(TypeError):
        context._designation_by_ref["forged"] = designation  # type: ignore[index]
    assert all(not key.startswith("_") for key in context.as_dict())


def test_frame_accessor_rejects_a_derived_cache_row_not_owned_by_serialized_slots() -> (
    None
):
    context = _context()
    canonical = context.application_frames[0]
    forged = object.__new__(ApplicationFrameSlot)
    for item in canonical.__dataclass_fields__:
        object.__setattr__(forged, item, getattr(canonical, item))
    object.__setattr__(forged, "operator_ref", "op:event")
    object.__setattr__(
        context,
        "_frame_by_ref",
        MappingProxyType({canonical.slot_ref: forged}),
    )
    with pytest.raises(ValueError, match="derived index"):
        context.frame(canonical.slot_ref)


def test_content_addressed_constructors_reject_container_coercion() -> None:
    with pytest.raises(TypeError, match="source_unit_refs"):
        DesignationSlot.create(
            source_unit_refs=["unit:alice"],  # type: ignore[arg-type]
            target_ref="entity:alice",
            target_kind="entity",
            score_q=1,
            designation_fact_ref="designation:alice",
            provenance_refs=("authority:g1",),
        )
    context = _context()
    fields = _creation_fields(context)
    fields["designation_slots"] = list(fields["designation_slots"])
    with pytest.raises(TypeError, match="designation slots"):
        ProposalContext.create(**fields)
    fields = _creation_fields(context)
    fields["contribution_slots"] = context.designation_slots
    with pytest.raises(TypeError, match="contribution slots"):
        ProposalContext.create(**fields)


def test_context_rejects_residual_for_contributed_source() -> None:
    context = _context()
    fields = _creation_fields(context)
    fields["residual_evidence"] = (
        ResidualEvidence.create(
            source_unit_ref="unit:alice",
            contribution_kind="anchor",
            critical=True,
            reason="must not overlap a contribution",
        ),
    )

    with pytest.raises(ValueError, match="residual.*contribution"):
        ProposalContext.create(**fields)


def test_context_and_nested_slots_are_immutable() -> None:
    context = _context()
    with pytest.raises(FrozenInstanceError):
        context.context_ref = "forged"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        context.designation_slots[0].score_q = 1  # type: ignore[misc]


def test_context_rejects_frame_predicate_that_disagrees_with_designation() -> None:
    context = _context()
    mismatched = ApplicationFrameSlot.create(
        designation_slot_ref=context.designation_slots[0].slot_ref,
        predicate_target_ref="relation:love",
        predicate_kind="relation_type",
        operator_ref="op:relation",
        structural_role_ref="role:relation",
        required_roles=("role:subject", "role:object"),
        optional_roles=(),
        proposition_roles=(),
        source_unit_refs=("unit:loves",),
        derived_role_targets=(),
        affordance_frame_ref="frame:relation",
        provenance_refs=(context.designation_slots[0].slot_ref, "frame:relation"),
    )
    fields = _creation_fields(context)
    fields["application_frames"] = (mismatched,)
    fields["variable_slots"] = ()
    fields["transition_slots"] = ()

    with pytest.raises(ValueError, match="predicate.*designation"):
        ProposalContext.create(**fields)


def test_context_rejects_frame_operator_that_disagrees_with_semantic_kind() -> None:
    context = _context()
    original = context.application_frames[0]
    forged = ApplicationFrameSlot.create(
        designation_slot_ref=original.designation_slot_ref,
        predicate_target_ref=original.predicate_target_ref,
        predicate_kind=original.predicate_kind,
        operator_ref="op:event",
        structural_role_ref=original.structural_role_ref,
        required_roles=original.required_roles,
        optional_roles=original.optional_roles,
        proposition_roles=original.proposition_roles,
        source_unit_refs=original.source_unit_refs,
        derived_role_targets=original.derived_role_targets,
        affordance_frame_ref=original.affordance_frame_ref,
        provenance_refs=original.provenance_refs,
    )
    fields = _creation_fields(context)
    fields["application_frames"] = (forged,)
    fields["variable_slots"] = ()
    fields["transition_slots"] = ()
    with pytest.raises(ValueError, match="operator lowering"):
        ProposalContext.create(**fields)


@pytest.mark.parametrize(
    ("updates", "message"),
    (
        ({"structural_role_ref": "role:event"}, "structural role"),
        ({"derived_role_targets": ()}, "derived role"),
        ({"required_roles": ("role:subject",)}, "input roles"),
        (
            {
                "required_roles": ("role:subject",),
                "optional_roles": ("role:value",),
                "proposition_roles": ("role:value",),
            },
            "proposition roles",
        ),
    ),
    ids=(
        "structural-role",
        "derived-role",
        "required-optional-partition",
        "non-event-proposition-role",
    ),
)
def test_context_rejects_frame_roles_not_proven_by_context(
    updates: dict[str, Any], message: str
) -> None:
    context = _context()
    original = context.application_frames[0]
    values = {
        "designation_slot_ref": original.designation_slot_ref,
        "predicate_target_ref": original.predicate_target_ref,
        "predicate_kind": original.predicate_kind,
        "operator_ref": original.operator_ref,
        "structural_role_ref": original.structural_role_ref,
        "required_roles": original.required_roles,
        "optional_roles": original.optional_roles,
        "proposition_roles": original.proposition_roles,
        "source_unit_refs": original.source_unit_refs,
        "derived_role_targets": original.derived_role_targets,
        "affordance_frame_ref": original.affordance_frame_ref,
        "provenance_refs": original.provenance_refs,
    }
    forged = ApplicationFrameSlot.create(**(values | updates))
    fields = _creation_fields(context)
    fields["application_frames"] = (forged,)
    fields["variable_slots"] = ()
    fields["transition_slots"] = ()
    with pytest.raises(ValueError, match=message):
        ProposalContext.create(**fields)


def test_context_rejects_transition_on_non_state_frame() -> None:
    context = _context()
    designation = DesignationSlot.create(
        source_unit_refs=("unit:loves",),
        target_ref="relation:love",
        target_kind="relation_type",
        score_q=950_000,
        designation_fact_ref="designation:love",
        provenance_refs=("authority:g1",),
    )
    frame = ApplicationFrameSlot.create(
        designation_slot_ref=designation.slot_ref,
        predicate_target_ref=designation.target_ref,
        predicate_kind=designation.target_kind,
        operator_ref="op:relation",
        structural_role_ref="role:relation",
        required_roles=("role:subject", "role:object"),
        optional_roles=(),
        proposition_roles=(),
        source_unit_refs=("unit:loves",),
        derived_role_targets=(),
        affordance_frame_ref="frame:love",
        provenance_refs=(designation.slot_ref, "frame:love"),
    )
    transition = TransitionSlot.create(
        application_frame_ref=frame.slot_ref,
        event_type_ref="event:set_state",
        compatible_modes=("REQUEST",),
        required_roles=("role:actor",),
        required_capabilities=("cap:set_state",),
        required_permissions=("permission:set_state",),
        adapter_ref="adapter:state",
        source_unit_refs=("unit:loves",),
    )
    fields = _creation_fields(context)
    relation_predicate = ContributionSlot.create(
        contribution_ref="contribution:love-predicate",
        kind="predicate",
        source_unit_refs=("unit:loves",),
        target_ref=designation.target_ref,
        target_kind=designation.target_kind,
        input_ports=("role:subject", "role:object"),
        output_ports=("role:relation",),
        constraints=(),
        provenance_refs=("frame:love",),
    )
    fields["designation_slots"] = (designation,)
    fields["contribution_slots"] = (
        context.contribution_slots[0],
        relation_predicate,
    )
    fields["application_frames"] = (frame,)
    fields["variable_slots"] = ()
    fields["transition_slots"] = (transition,)

    with pytest.raises(ValueError, match="op:state"):
        ProposalContext.create(**fields)

class _ProposalContextSubclass(ProposalContext):
    pass


class _ExplodingDict(dict):
    def __iter__(self):
        raise AssertionError("non-exact mapping keys were iterated")


def test_proposal_context_factories_reject_subclasses() -> None:
    context = _context()
    fields = _creation_fields(context)
    with pytest.raises(TypeError, match="exact ProposalContext"):
        _ProposalContextSubclass.create(**fields)
    with pytest.raises(TypeError, match="exact ProposalContext"):
        _ProposalContextSubclass.from_dict(context.as_dict())


def test_proposal_context_from_dict_rejects_nonexact_or_oversized_before_decode(
    monkeypatch,
) -> None:
    payload = _context().as_dict()
    with pytest.raises(TypeError, match="exact dict"):
        ProposalContext.from_dict(_ExplodingDict(payload))

    def forbidden_child(*_args, **_kwargs):
        raise AssertionError("oversized child list reached child decoder")

    def forbidden_hash(*_args, **_kwargs):
        raise AssertionError("oversized wire payload reached stable_ref")

    monkeypatch.setattr(DesignationSlot, "from_dict", forbidden_child)
    monkeypatch.setattr(context_module, "stable_ref", forbidden_hash)
    payload["designation_slots"] = [
        payload["designation_slots"][0]
        for _ in range(RuntimeConfig.release().max_orientation_alternatives + 1)
    ]
    with pytest.raises(ValueError, match="designation_slots.*bound"):
        ProposalContext.from_dict(payload)


def test_proposal_context_from_dict_prebounds_topology_and_exact_wire_shapes(
    monkeypatch,
) -> None:
    payload = _context().as_dict()

    def forbidden_hash(*_args, **_kwargs):
        raise AssertionError("hostile topology reached stable_ref")

    monkeypatch.setattr(context_module, "stable_ref", forbidden_hash)
    payload["context_refs"] = [
        f"context:{index}"
        for index in range(RuntimeConfig.release().max_orientation_alternatives + 1)
    ]
    with pytest.raises(ValueError, match="context_refs.*bound"):
        ProposalContext.from_dict(payload)

    payload = _context().as_dict()
    payload["source_unit_spans"][0] = tuple(payload["source_unit_spans"][0])
    with pytest.raises(TypeError, match="triples"):
        ProposalContext.from_dict(payload)


def test_proposal_context_create_and_decode_hash_validate_and_index_once(monkeypatch) -> None:
    original = _context()
    real_hash = context_module.stable_ref
    real_validate = context_module._validate_context
    real_build = ProposalContext._build_indexes
    counts = {"hash": 0, "validate": 0, "index": 0}

    def recording_hash(namespace, material):
        if namespace == "proposal_context":
            counts["hash"] += 1
        return real_hash(namespace, material)

    def recording_validate(context, config):
        counts["validate"] += 1
        return real_validate(context, config)

    def recording_build(context):
        counts["index"] += 1
        return real_build(context)

    monkeypatch.setattr(context_module, "stable_ref", recording_hash)
    monkeypatch.setattr(context_module, "_validate_context", recording_validate)
    monkeypatch.setattr(ProposalContext, "_build_indexes", recording_build)

    created = ProposalContext.create(**_creation_fields(original))
    assert created == original
    assert counts == {"hash": 1, "validate": 1, "index": 1}

    counts.update(hash=0, validate=0, index=0)
    decoded = ProposalContext.from_dict(original.as_dict())
    assert decoded == original
    assert counts == {"hash": 1, "validate": 1, "index": 1}
