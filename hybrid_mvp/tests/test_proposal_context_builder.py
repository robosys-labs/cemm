from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from cemm_authoritative_hybrid.affordances import AffordanceProfile
from cemm_authoritative_hybrid.authority import AtomRecord, EventSignature, RoleSpec
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
from cemm_authoritative_hybrid.grounding import (
    DesignationCandidate,
    GroundedItem,
    GroundingResult,
    ReferenceRequirement,
)
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.proposal_context import ProposalContextBuilder


class IndexedAuthority:
    def __init__(self) -> None:
        self.generation = "authority:g1"
        self.atoms = {
            "dimension:availability": AtomRecord(
                "dimension:availability", "state_dimension"
            ),
            "dimension:power": AtomRecord("dimension:power", "state_dimension"),
            "dimension:temperature": AtomRecord(
                "dimension:temperature", "state_dimension"
            ),
            "participant:user": AtomRecord("participant:user", "participant"),
            "participant:system": AtomRecord("participant:system", "participant"),
            "event:greeting": AtomRecord("event:greeting", "event_type"),
        }
        self.operator_roles = {
            "op:state": ["role:subject", "role:dimension", "role:value"],
        }
        self.transition_probes: list[str] = []
        self.signature_probes: list[str] = []
        self.signatures = {
            "event:set_state": EventSignature(
                event_type="event:set_state",
                roles=(
                    RoleSpec("role:actor", ("participant",)),
                    RoleSpec("role:target", ("entity",)),
                    RoleSpec("role:dimension", ("state_dimension",)),
                    RoleSpec("role:value", ("state_value",)),
                ),
                required_capabilities=("cap:set_state",),
                required_permissions=("permission:set_state",),
                adapter_ref="adapter:state",
            ),
            "event:greeting": EventSignature(
                event_type="event:greeting",
                roles=(
                    RoleSpec("role:actor", ("participant",)),
                    RoleSpec(
                        "role:content",
                        ("proposition",),
                        required=False,
                        proposition_valued=True,
                    ),
                ),
            ),
        }

    def by_transition(self, key: str) -> dict[str, Any] | None:
        self.transition_probes.append(key)
        if key == "dimension:availability":
            return {"event_type": "event:set_state"}
        return None

    def by_event_signature(self, event_type: str) -> EventSignature | None:
        self.signature_probes.append(event_type)
        return self.signatures.get(event_type)

    def by_kind(self, kind: str) -> frozenset[str]:
        raise AssertionError(f"target-independent authority scan: {kind}")


class IndexedAffordances:
    def __init__(self, count: int = 1) -> None:
        self.authority_generation = "authority:g1"
        self.probes: list[str] = []
        self.profiles = tuple(
            AffordanceProfile(
                target_ref="dimension:availability",
                contribution_kinds=("predicate", "anchor"),
                input_ports=("role:subject", "role:value"),
                output_ports=("role:dimension",),
                role_candidates=("role:dimension", f"role:variant-{index}"),
                frame_ref=f"frame:availability:{index}",
            )
            for index in range(count)
        )

    def for_target(self, target_ref: str) -> tuple[AffordanceProfile, ...]:
        self.probes.append(target_ref)
        return tuple(row for row in self.profiles if row.target_ref == target_ref)


def pin() -> RevisionPin:
    return RevisionPin("authority:g1", 2, 3, 4, 5, "model:m1")


def orientation(
    mode: SemanticMode = SemanticMode.REQUEST,
    *,
    cache_key: str | None = "legacy-incomplete-cache-key",
    focus_refs: tuple[str, ...] = ("dimension:availability",),
    source_text: str = "availability",
    participants: tuple[str, ...] = ("participant:user",),
    revision_pin: RevisionPin | None = None,
) -> Orientation:
    current = revision_pin or pin()
    return Orientation.create(
        session_ref="session:1",
        turn_ref="turn:1",
        source_text=source_text,
        mode=mode,
        participant_frame="participant_frame:1",
        temporal_frame="temporal_frame:1",
        focus_refs=focus_refs,
        obligation_refs=(),
        capability_summary=("cap:set_state",),
        permission_summary=("permission:set_state",),
        budgets={"proposal": 4},
        participants=participants,
        active_turn_ref="turn:1",
        event_refs=(),
        scanned_atom_count=0,
        index_probes=("focus",),
        visited_refs=("dimension:availability",),
        cache_key=cache_key,
        revision_pin=current,
    )

def evidence() -> EvidencePacket:
    item = EvidenceItem.create(
        source="text",
        content="availability",
        source_ref="evidence_item:1",
        provenance_refs=("turn:1",),
        adapter_receipt_ref=None,
    )
    return EvidencePacket.create(
        items=(item,),
        source_text="availability",
        form_pack_hash="form-pack:1",
    )


def lattice(current_evidence: EvidencePacket | None = None) -> FormLattice:
    current_evidence = current_evidence or evidence()
    return FormLattice.create(
        evidence_packet_ref=current_evidence.packet_ref,
        form_pack_hash=current_evidence.form_pack_hash,
        units=(
            FormUnit(
                "unit:availability",
                "availability",
                ("availability",),
                0,
                12,
                (),
            ),
        ),
        hypotheses=(),
        source_text="availability",
    )


def grounding(
    *rows: tuple[str, str, float],
    current_lattice: FormLattice | None = None,
    current_pin: RevisionPin | None = None,
) -> GroundingResult:
    selected_lattice = current_lattice or lattice()
    selected_pin = current_pin or pin()
    values = rows or (("dimension:availability", "designation:availability", 0.875),)
    return GroundingResult.create(
        evidence_packet_ref=selected_lattice.evidence_packet_ref,
        form_lattice_ref=selected_lattice.lattice_ref,
        revision_pin=selected_pin,
        designations=tuple(
            DesignationCandidate(
                ("unit:availability",), target, fact, score, ("authority:g1",)
            )
            for target, fact, score in values
        ),
        unresolved=(),
        grounded_items=(),
        provenance_refs=("authority:g1",),
    )


def contribution(index: int = 0) -> SemanticContribution:
    return SemanticContribution(
        contribution_ref=f"contribution:availability:{index}",
        kind="predicate",
        source_unit_refs=("unit:availability",),
        target_ref="dimension:availability",
        input_ports=("role:subject", "role:value"),
        output_ports=("role:dimension",),
        constraints=(("profile", str(index)),),
    )


def build(
    *,
    config: RuntimeConfig | None = None,
    authority: IndexedAuthority | None = None,
    affordances: IndexedAffordances | None = None,
    current_orientation: Orientation | None = None,
    current_evidence: EvidencePacket | None = None,
    current_lattice: FormLattice | None = None,
    current_grounding: GroundingResult | None = None,
    contributions: tuple[SemanticContribution, ...] | None = None,
):
    authority = authority or IndexedAuthority()
    affordances = affordances or IndexedAffordances()
    builder = ProposalContextBuilder(
        authority, affordances, config or RuntimeConfig.release()
    )
    selected_orientation = current_orientation or orientation()
    selected_evidence = current_evidence or evidence()
    selected_lattice = current_lattice or lattice(selected_evidence)
    selected_grounding = current_grounding or grounding(
        current_lattice=selected_lattice,
        current_pin=selected_orientation.revision_pin,
    )
    context = builder.build(
        orientation=selected_orientation,
        evidence=selected_evidence,
        form_lattice=selected_lattice,
        grounding_result=selected_grounding,
        contributions=contributions if contributions is not None else (contribution(),),
    )
    return context, authority, affordances


def test_builder_binds_exact_canonical_orientation_ref() -> None:
    current = orientation()
    context, _, _ = build(current_orientation=current)
    assert context.orientation_ref == current.orientation_ref


def test_builder_orientation_lineage_is_independent_of_transient_cache_key() -> None:
    first = orientation(cache_key="cache:first")
    second = orientation(cache_key="cache:second")
    first_context, _, _ = build(current_orientation=first)
    second_context, _, _ = build(current_orientation=second)
    assert first.orientation_ref == second.orientation_ref
    assert first_context.orientation_ref == second_context.orientation_ref
    assert first_context.context_ref == second_context.context_ref


def test_builder_orientation_lineage_changes_with_identity_content() -> None:
    first = orientation()
    second = orientation(focus_refs=("dimension:power",))
    first_context, _, _ = build(current_orientation=first)
    second_context, _, _ = build(current_orientation=second)
    assert first.orientation_ref != second.orientation_ref
    assert first_context.orientation_ref != second_context.orientation_ref
    assert first_context.context_ref != second_context.context_ref

def test_builder_constructs_exact_indexed_current_cycle_context() -> None:
    context, authority, affordances = build()

    designation = context.designation_slots[0]
    frame = context.application_frames[0]
    transition = context.transition_slots[0]
    assert designation.score_q == 875_000
    assert (frame.predicate_target_ref, frame.predicate_kind) == (
        designation.target_ref,
        designation.target_kind,
    )
    assert frame.operator_ref == "op:state"
    assert frame.affordance_frame_ref == "frame:availability:0"
    assert frame.provenance_refs == (
        designation.slot_ref,
        "authority:g1",
        "frame:availability:0",
    )
    assert frame.required_roles == ("role:subject", "role:value")
    assert "role:dimension" not in frame.required_roles
    assert transition.event_type_ref == "event:set_state"
    assert transition.required_roles == (
        "role:actor",
        "role:target",
        "role:dimension",
        "role:value",
    )
    assert transition.required_capabilities == ("cap:set_state",)
    assert transition.required_permissions == ("permission:set_state",)
    assert transition.adapter_ref == "adapter:state"
    assert context.source_span(("unit:availability",)) == (0, 12)
    assert context.revision_pin == pin()
    assert authority.transition_probes == ["dimension:availability"]
    assert authority.signature_probes == ["event:set_state"]
    assert affordances.probes == ["dimension:availability"]
    assert "resolved_applications" not in context.as_dict()


def test_builder_binds_exact_packet_lattice_grounding_context_identity() -> None:
    current_orientation = orientation()
    current_evidence = evidence()
    current_lattice = lattice(current_evidence)
    current_grounding = grounding(
        current_lattice=current_lattice,
        current_pin=current_orientation.revision_pin,
    )

    context, _, _ = build(
        current_orientation=current_orientation,
        current_evidence=current_evidence,
        current_lattice=current_lattice,
        current_grounding=current_grounding,
    )

    assert context.evidence_packet_ref == current_evidence.packet_ref
    assert context.form_lattice_ref == current_lattice.lattice_ref
    assert context.grounding_ref == current_grounding.grounding_ref
    assert (
        context.revision_pin
        == current_grounding.revision_pin
        == current_orientation.revision_pin
    )


def test_builder_enforces_per_span_and_per_target_bounds() -> None:
    config = replace(
        RuntimeConfig.release(),
        max_designations_per_span=2,
        max_affordances_per_target=2,
        max_orientation_alternatives=8,
    )
    candidates = grounding(
        ("dimension:availability", "designation:availability", 0.9),
        ("dimension:power", "designation:power", 0.7),
        ("dimension:temperature", "designation:temperature", 0.4),
    )
    context, _, affordances = build(
        config=config,
        affordances=IndexedAffordances(4),
        current_grounding=candidates,
        contributions=tuple(contribution(index) for index in range(7)),
    )

    assert tuple(row.target_ref for row in context.designation_slots) == (
        "dimension:availability",
        "dimension:power",
    )
    assert len(context.application_frames) == 2
    assert tuple(row.affordance_frame_ref for row in context.application_frames) == (
        "frame:availability:0",
        "frame:availability:1",
    )
    assert len({row.slot_ref for row in context.application_frames}) == 2
    assert len(context.contribution_slots) == 4
    assert affordances.probes == ["dimension:availability", "dimension:power"]


def test_builder_identity_covers_complete_evidence_lattice_and_orientation() -> None:
    original, _, _ = build()
    original_evidence = evidence()
    changed_evidence = EvidencePacket.create(
        items=original_evidence.items,
        source_text=original_evidence.source_text,
        form_pack_hash="form-pack:2",
    )
    original_lattice = lattice()
    changed_lattice = FormLattice.create(
        evidence_packet_ref=original_lattice.evidence_packet_ref,
        form_pack_hash=original_lattice.form_pack_hash,
        source_text=original_lattice.source_text,
        units=(
            replace(
                original_lattice.units[0],
                normalized_forms=("available",),
            ),
        ),
        hypotheses=original_lattice.hypotheses,
    )
    changed_orientation = orientation(focus_refs=("dimension:power",))

    evidence_context, _, _ = build(current_evidence=changed_evidence)
    lattice_context, _, _ = build(current_lattice=changed_lattice)
    orientation_context, _, _ = build(current_orientation=changed_orientation)

    assert evidence_context.evidence_packet_ref != original.evidence_packet_ref
    assert lattice_context.form_lattice_ref != original.form_lattice_ref
    assert orientation_context.orientation_ref != original.orientation_ref
    assert (
        len(
            {
                original.context_ref,
                evidence_context.context_ref,
                lattice_context.context_ref,
                orientation_context.context_ref,
            }
        )
        == 4
    )


def test_builder_rejects_geometry_unknown_units_and_revision_drift() -> None:
    original_lattice = lattice()
    with pytest.raises(ValueError, match="geometry"):
        FormLattice.create(
            evidence_packet_ref=original_lattice.evidence_packet_ref,
            form_pack_hash=original_lattice.form_pack_hash,
            source_text=original_lattice.source_text,
            units=(replace(original_lattice.units[0], source_end=11),),
            hypotheses=original_lattice.hypotheses,
        )

    current = grounding()
    unknown = GroundingResult.create(
        evidence_packet_ref=current.evidence_packet_ref,
        form_lattice_ref=current.form_lattice_ref,
        revision_pin=current.revision_pin,
        designations=(replace(current.designations[0], unit_refs=("unit:unknown",)),),
        unresolved=current.unresolved,
        grounded_items=current.grounded_items,
        provenance_refs=current.provenance_refs,
    )
    with pytest.raises(ValueError, match="unknown source unit"):
        build(current_grounding=unknown)

    drifted = orientation(revision_pin=replace(pin(), world_revision=99))
    with pytest.raises(ValueError, match="revision pin"):
        build(
            current_orientation=drifted,
            current_grounding=grounding(current_pin=pin()),
        )


@pytest.mark.parametrize(
    "case",
    ("zero-width", "gap", "overlap"),
    ids=("zero-width", "gap", "overlap"),
)
def test_builder_rejects_zero_width_and_noncontiguous_unit_geometry(
    case: str,
) -> None:
    with pytest.raises(ValueError, match="geometry"):
        if case == "zero-width":
            source = "x"
            units = (
                FormUnit("unit:empty", "", (), 0, 0, ()),
                FormUnit("unit:text", "x", ("x",), 0, 1, ()),
            )
        elif case == "gap":
            source = "a b"
            units = (
                FormUnit("unit:left", "a", ("a",), 0, 1, ()),
                FormUnit("unit:right", "b", ("b",), 2, 3, ()),
            )
        else:
            source = "ab"
            units = (
                FormUnit("unit:left", "ab", ("ab",), 0, 2, ()),
                FormUnit("unit:right", "b", ("b",), 1, 2, ()),
            )
        FormLattice.create(
            evidence_packet_ref=f"evidence_packet:invalid-{case}",
            form_pack_hash="form-pack:1",
            units=units,
            hypotheses=(),
            source_text=source,
        )


class _ExplodingTuple(tuple):
    def __iter__(self):
        raise AssertionError("oversized raw input was iterated before its bound check")


def _forged_grounding_collection(
    current: GroundingResult,
    field: str,
    value: tuple[Any, ...],
) -> GroundingResult:
    forged = object.__new__(GroundingResult)
    for name in current.__dataclass_fields__:
        object.__setattr__(forged, name, getattr(current, name))
    object.__setattr__(forged, field, value)
    return forged


@pytest.mark.parametrize(
    "field",
    ("designations", "unresolved", "grounded_items", "contributions"),
    ids=("designations", "unresolved", "grounded-items", "contributions"),
)
def test_builder_prebounds_every_raw_grounding_and_contribution_collection(
    field: str,
) -> None:
    config = replace(
        RuntimeConfig.release(),
        max_input_tokens=2,
        max_designations_per_span=1,
        max_affordances_per_target=1,
    )
    current = grounding()
    limits = {
        "designations": config.max_input_tokens * config.max_designations_per_span,
        "unresolved": config.max_input_tokens,
        "grounded_items": config.max_input_tokens,
        "contributions": config.max_input_tokens
        * (config.max_affordances_per_target * 2 + 1),
    }
    if field == "designations":
        item: Any = current.designations[0]
    elif field == "unresolved":
        item = ReferenceRequirement("unit:availability", "designation", None)
    elif field == "grounded_items":
        item = GroundedItem(
            "evidence_item:1",
            "text",
            "dimension:availability",
            ("unit:availability",),
        )
    else:
        item = contribution()
    oversized = _ExplodingTuple((item,) * (limits[field] + 1))

    with pytest.raises(ValueError, match=field.replace("_", " ") + ".*bound"):
        if field == "contributions":
            build(config=config, contributions=oversized)
        else:
            build(
                config=config,
                current_grounding=_forged_grounding_collection(
                    current,
                    field,
                    oversized,
                ),
            )


def test_builder_rejects_authority_and_affordance_generation_drift() -> None:
    authority = IndexedAuthority()
    authority.generation = "authority:stale"
    with pytest.raises(ValueError, match="authority generation"):
        build(authority=authority)

    affordances = IndexedAffordances()
    affordances.authority_generation = "authority:stale"
    with pytest.raises(ValueError, match="affordance.*generation"):
        build(affordances=affordances)


def test_builder_emits_reference_and_query_variable_contributions() -> None:
    source = "you availability what"
    current_evidence = EvidencePacket.create(
        items=(
            EvidenceItem.create(
                source="text",
                content=source,
                source_ref="evidence_item:query",
                provenance_refs=("turn:1",),
                adapter_receipt_ref=None,
            ),
        ),
        source_text=source,
        form_pack_hash="form-pack:1",
    )
    current_lattice = FormLattice.create(
        evidence_packet_ref=current_evidence.packet_ref,
        form_pack_hash="form-pack:1",
        units=(
            FormUnit(
                "unit:you",
                "you",
                ("you",),
                0,
                3,
                (("participant", "reference_system"),),
            ),
            FormUnit("unit:space-1", " ", (), 3, 4, ()),
            FormUnit("unit:availability", "availability", ("availability",), 4, 16, ()),
            FormUnit("unit:space-2", " ", (), 16, 17, ()),
            FormUnit("unit:what", "what", ("what",), 17, 21, (("query", "query"),)),
        ),
        hypotheses=(
            FormHypothesis(
                "hypothesis:query", ("unit:what",), "query", (("query", "query"),)
            ),
        ),
        source_text=source,
    )

    current_orientation = orientation(
        SemanticMode.QUERY,
        source_text=source,
        participants=("participant:user", "participant:system"),
    )

    context, _, _ = build(
        current_orientation=current_orientation,
        current_evidence=current_evidence,
        current_lattice=current_lattice,
    )

    assert tuple(row.target_ref for row in context.reference_slots) == (
        "participant:system",
    )
    assert tuple(row.kind for row in context.contributions_for_source("unit:you")) == (
        "reference",
    )
    assert tuple(row.kind for row in context.contributions_for_source("unit:what")) == (
        "open_variable",
    )
    assert len(context.variable_slots) == 2
    assert all(
        row.application_frame_ref == context.application_frames[0].slot_ref
        for row in context.variable_slots
    )
    assert tuple(row.role_ref for row in context.variable_slots) == (
        "role:subject",
        "role:value",
    )
    assert context.variable_slots[1].required_kinds == ("state_value",)
    assert context.residual_for_source("unit:you") is None
    assert context.residual_for_source("unit:what") is None


def test_builder_emits_closed_class_contributions_for_structural_evidence() -> None:
    source = "is not and"
    current_evidence = EvidencePacket.create(
        items=(
            EvidenceItem.create(
                source="text",
                content=source,
                source_ref="evidence_item:closed",
                provenance_refs=("turn:1",),
                adapter_receipt_ref=None,
            ),
        ),
        source_text=source,
        form_pack_hash="form-pack:1",
    )
    current_lattice = FormLattice.create(
        evidence_packet_ref=current_evidence.packet_ref,
        form_pack_hash="form-pack:1",
        units=(
            FormUnit("unit:is", "is", ("is",), 0, 2, (("binder", "copula"),)),
            FormUnit("unit:space-1", " ", (), 2, 3, ()),
            FormUnit("unit:not", "not", ("not",), 3, 6, (("polarity", "negation"),)),
            FormUnit("unit:space-2", " ", (), 6, 7, ()),
            FormUnit(
                "unit:and", "and", ("and",), 7, 10, (("connector", "conjunction"),)
            ),
        ),
        hypotheses=(
            FormHypothesis(
                "hypothesis:negation",
                ("unit:not",),
                "negation",
                (("polarity", "negation"),),
            ),
            FormHypothesis(
                "hypothesis:conjunction",
                ("unit:and",),
                "conjunction",
                (("connector", "conjunction"),),
            ),
        ),
        source_text=source,
    )

    current_orientation = orientation(SemanticMode.OBSERVE, source_text=source)

    context, _, _ = build(
        current_orientation=current_orientation,
        current_evidence=current_evidence,
        current_lattice=current_lattice,
        current_grounding=grounding_result_empty(
            current_lattice=current_lattice,
            current_pin=current_orientation.revision_pin,
        ),
        contributions=(),
    )

    assert tuple(row.kind for row in context.contributions_for_source("unit:is")) == (
        "binder",
    )
    assert tuple(row.kind for row in context.contributions_for_source("unit:not")) == (
        "scope",
    )
    assert tuple(row.kind for row in context.contributions_for_source("unit:and")) == (
        "connector",
    )
    assert len(context.scope_slots) == 1
    assert len(context.expression_link_slots) == 1
    assert all(not row.critical for row in context.residual_evidence)


def grounding_result_empty(
    *,
    current_lattice: FormLattice | None = None,
    current_pin: RevisionPin | None = None,
) -> GroundingResult:
    selected_lattice = current_lattice or lattice()
    return GroundingResult.create(
        evidence_packet_ref=selected_lattice.evidence_packet_ref,
        form_lattice_ref=selected_lattice.lattice_ref,
        revision_pin=current_pin or pin(),
        designations=(),
        unresolved=(),
        grounded_items=(),
        provenance_refs=(),
    )


def test_designation_without_usable_contribution_remains_critical() -> None:
    context, _, _ = build(contributions=())

    residual = context.residual_for_source("unit:availability")
    assert residual is not None
    assert residual.critical is True
    assert residual.contribution_kind == "anchor"


def test_unresolved_participant_evidence_is_critical_reference_residual() -> None:
    source = "you"
    current_evidence = EvidencePacket.create(
        items=(
            EvidenceItem.create(
                source="text",
                content=source,
                source_ref="evidence_item:you",
                provenance_refs=("turn:1",),
                adapter_receipt_ref=None,
            ),
        ),
        source_text=source,
        form_pack_hash="form-pack:1",
    )
    current_lattice = FormLattice.create(
        evidence_packet_ref=current_evidence.packet_ref,
        form_pack_hash="form-pack:1",
        units=(
            FormUnit(
                "unit:you",
                "you",
                ("you",),
                0,
                3,
                (("participant", "reference_system"),),
            ),
        ),
        hypotheses=(
            FormHypothesis(
                "hypothesis:deixis",
                ("unit:you",),
                "deixis",
                (("participant", "reference_system"),),
            ),
        ),
        source_text=source,
    )

    current_orientation = orientation(
        SemanticMode.OBSERVE, source_text=source, participants=("participant:user",)
    )

    context, _, _ = build(
        current_orientation=current_orientation,
        current_evidence=current_evidence,
        current_lattice=current_lattice,
        current_grounding=grounding_result_empty(
            current_lattice=current_lattice,
            current_pin=current_orientation.revision_pin,
        ),
        contributions=(),
    )

    residual = context.residual_for_source("unit:you")
    assert residual is not None
    assert residual.critical is True
    assert residual.contribution_kind == "reference"


def test_event_frame_uses_exact_reviewed_signature_once() -> None:
    authority = IndexedAuthority()

    class EventAffordances:
        def __init__(self) -> None:
            self.authority_generation = "authority:g1"
            self.probes: list[str] = []

        def for_target(self, target_ref: str) -> tuple[AffordanceProfile, ...]:
            self.probes.append(target_ref)
            return (
                AffordanceProfile(
                    target_ref="event:greeting",
                    contribution_kinds=("predicate",),
                    input_ports=("role:actor", "role:content"),
                    output_ports=("role:event",),
                    role_candidates=("role:actor", "role:content"),
                    frame_ref="frame:greeting",
                ),
            )

    affordances = EventAffordances()
    builder = ProposalContextBuilder(authority, affordances, RuntimeConfig.release())
    event_grounding = grounding(
        ("event:greeting", "designation:greeting", 0.9),
    )
    event_contribution = SemanticContribution(
        contribution_ref="contribution:greeting",
        kind="predicate",
        source_unit_refs=("unit:availability",),
        target_ref="event:greeting",
        input_ports=("role:actor", "role:content"),
        output_ports=("role:event",),
        constraints=(),
    )

    context = builder.build(
        orientation=orientation(SemanticMode.OBSERVE),
        evidence=evidence(),
        form_lattice=lattice(),
        grounding_result=event_grounding,
        contributions=(event_contribution,),
    )

    frame = context.application_frames[0]
    assert frame.required_roles == ("role:actor",)
    assert frame.optional_roles == ("role:content",)
    assert frame.proposition_roles == ("role:content",)
    assert authority.signature_probes == ["event:greeting"]
    assert affordances.probes == ["event:greeting"]


def test_builder_rejects_cross_lattice_grounding_with_same_unit_refs() -> None:
    original_lattice = lattice()
    forged_lattice = FormLattice.create(
        evidence_packet_ref=original_lattice.evidence_packet_ref,
        form_pack_hash=original_lattice.form_pack_hash,
        source_text=original_lattice.source_text,
        units=(
            replace(
                original_lattice.units[0],
                normalized_forms=("different-normalization",),
            ),
        ),
        hypotheses=original_lattice.hypotheses,
    )
    original_grounding = grounding()

    assert forged_lattice.lattice_ref != original_lattice.lattice_ref
    with pytest.raises(ValueError, match="form lattice lineage"):
        build(
            current_lattice=forged_lattice,
            current_grounding=original_grounding,
        )


def test_builder_requires_authority_generation_attribute() -> None:
    malformed = IndexedAuthority()
    del malformed.generation

    with pytest.raises(AttributeError, match="generation"):
        build(authority=malformed)


def test_builder_requires_affordance_generation_attribute() -> None:
    malformed = IndexedAffordances()
    del malformed.authority_generation

    with pytest.raises(AttributeError, match="authority_generation"):
        build(affordances=malformed)


class _NonCanonicalOrientation(Orientation):
    def __getattribute__(self, name: str):
        raise AssertionError(f"noncanonical orientation was used: {name}")


def test_builder_rejects_orientation_subclass_before_use() -> None:
    forged = object.__new__(_NonCanonicalOrientation)
    current_evidence = evidence()
    current_lattice = lattice(current_evidence)
    current_grounding = grounding(
        current_lattice=current_lattice,
        current_pin=pin(),
    )

    with pytest.raises(TypeError, match="orientation must be Orientation"):
        build(
            current_orientation=forged,
            current_evidence=current_evidence,
            current_lattice=current_lattice,
            current_grounding=current_grounding,
        )


__cemm_test_inventory__ = {
    "tests/test_proposal_context_builder.py::test_builder_binds_exact_canonical_orientation_ref": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-slice-b-context-exact-orientation-ref",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Slice-B",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "37be03d9656b4153d3f90ad88547a158f5e541d8ddd2d4bc7b948129d8e1542c"
    },
    "tests/test_proposal_context_builder.py::test_builder_binds_exact_packet_lattice_grounding_context_identity": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-builder-binds-exact-packet-lattice-grounding-context-identity",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "990e15222eedcdc0156e72db20509ecef132460dcefa7d4c66c95cafab617274"
    },
    "tests/test_proposal_context_builder.py::test_builder_constructs_exact_indexed_current_cycle_context": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-builder-constructs-exact-indexed-current-cycle-context",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "aec2578ce29f99744c41232e1684e31dff43e62f607bd0fd7dc1394be4ef4952"
    },
    "tests/test_proposal_context_builder.py::test_builder_emits_closed_class_contributions_for_structural_evidence": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-builder-emits-closed-class-contributions-for-structural-evidence",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "b360b05b1ed99dc68048077b1dd83485c4f6a0c180ed6b357d8d3142376591c7"
    },
    "tests/test_proposal_context_builder.py::test_builder_emits_reference_and_query_variable_contributions": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-builder-emits-reference-and-query-variable-contributions",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "6b750bae40b3514341ee31daff53c644c6d778a0ed4f99ec1bb01bf4ef12c10f"
    },
    "tests/test_proposal_context_builder.py::test_builder_enforces_per_span_and_per_target_bounds": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-builder-enforces-per-span-and-per-target-bounds",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "8301049248fd80d2068d70a43e040d162ce47bf7c3f7c5e680223b80256ac344"
    },
    "tests/test_proposal_context_builder.py::test_builder_identity_covers_complete_evidence_lattice_and_orientation": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-builder-identity-covers-complete-evidence-lattice-and-orientation",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "9f265990bb0900b63195175b4aa870669d63f05cff29bb35aa31c7be4f0d2939"
    },
    "tests/test_proposal_context_builder.py::test_builder_orientation_lineage_changes_with_identity_content": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-slice-b-context-identity-sensitive",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Slice-B",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "8a6587a633043392b61dd72af8f511f60063db6fc204b52335806f83f297f76b"
    },
    "tests/test_proposal_context_builder.py::test_builder_orientation_lineage_is_independent_of_transient_cache_key": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-slice-b-context-cache-independent",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Slice-B",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "d86835695162e626c4d695ff6b8fc20ff11dacce098a407c66de7b49761a4941"
    },
    "tests/test_proposal_context_builder.py::test_builder_prebounds_every_raw_grounding_and_contribution_collection[contributions]": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-builder-prebounds-every-raw-grounding-and-contribution-collection-contributions",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "2a328602dfee9893760df73c9009b80da80c0613afee4fce222aabd654267c93"
    },
    "tests/test_proposal_context_builder.py::test_builder_prebounds_every_raw_grounding_and_contribution_collection[designations]": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-builder-prebounds-every-raw-grounding-and-contribution-collection-designations",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "2a328602dfee9893760df73c9009b80da80c0613afee4fce222aabd654267c93"
    },
    "tests/test_proposal_context_builder.py::test_builder_prebounds_every_raw_grounding_and_contribution_collection[grounded-items]": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-builder-prebounds-every-raw-grounding-and-contribution-collection-grounded-items",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "2a328602dfee9893760df73c9009b80da80c0613afee4fce222aabd654267c93"
    },
    "tests/test_proposal_context_builder.py::test_builder_prebounds_every_raw_grounding_and_contribution_collection[unresolved]": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-builder-prebounds-every-raw-grounding-and-contribution-collection-unresolved",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "2a328602dfee9893760df73c9009b80da80c0613afee4fce222aabd654267c93"
    },
    "tests/test_proposal_context_builder.py::test_builder_rejects_authority_and_affordance_generation_drift": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-builder-rejects-authority-and-affordance-generation-drift",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "8ea254fe6372246278b9a61486e8a7ce8bbc4fc542aa8d05600da70f2f31631c"
    },
    "tests/test_proposal_context_builder.py::test_builder_rejects_cross_lattice_grounding_with_same_unit_refs": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-builder-rejects-cross-lattice-grounding-with-same-unit-refs",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "e46a98a827747487bdc9bddb7cf9817137a55d8db1bd9e107834a49e903f19aa"
    },
    "tests/test_proposal_context_builder.py::test_builder_rejects_geometry_unknown_units_and_revision_drift": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-builder-rejects-geometry-unknown-units-and-revision-drift",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "b9ed020b110902ac9a82fec327f7a3959a292c13254008eaf6fdc5eab1e8b479"
    },
    "tests/test_proposal_context_builder.py::test_builder_rejects_orientation_subclass_before_use": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-slice-b-context-rejects-orientation-subclass",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Slice-B",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "63e60381234aa8780f6759c18a4154abb6f725c5a8da6404da1b403e15282b47"
    },
    "tests/test_proposal_context_builder.py::test_builder_rejects_zero_width_and_noncontiguous_unit_geometry[gap]": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-builder-rejects-zero-width-and-noncontiguous-unit-geometry-gap",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "247b4a73e3178adacdc8340a7d638da1cda8ada354fb7f5311400c0eafdfe351"
    },
    "tests/test_proposal_context_builder.py::test_builder_rejects_zero_width_and_noncontiguous_unit_geometry[overlap]": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-builder-rejects-zero-width-and-noncontiguous-unit-geometry-overlap",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "247b4a73e3178adacdc8340a7d638da1cda8ada354fb7f5311400c0eafdfe351"
    },
    "tests/test_proposal_context_builder.py::test_builder_rejects_zero_width_and_noncontiguous_unit_geometry[zero-width]": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-builder-rejects-zero-width-and-noncontiguous-unit-geometry-zero-width",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "247b4a73e3178adacdc8340a7d638da1cda8ada354fb7f5311400c0eafdfe351"
    },
    "tests/test_proposal_context_builder.py::test_builder_requires_affordance_generation_attribute": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-builder-requires-affordance-generation-attribute",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "f72d535db8f9612be7c20ee90b44987e6930607f38cebaaf44d1ff4eb43950e5"
    },
    "tests/test_proposal_context_builder.py::test_builder_requires_authority_generation_attribute": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-builder-requires-authority-generation-attribute",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "787bd473b880e8a80cc239b3353d6e071c098064772ccda2a007bb790d0fdb04"
    },
    "tests/test_proposal_context_builder.py::test_designation_without_usable_contribution_remains_critical": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-designation-without-usable-contribution-remains-critical",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "551218e9d77e1899b1e1ca970d6bf0cc8351a6d554fdd8c314ae214fc3e2da6b"
    },
    "tests/test_proposal_context_builder.py::test_event_frame_uses_exact_reviewed_signature_once": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-event-frame-uses-exact-reviewed-signature-once",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "99abd7845ce30181d769f1e1f7af7cbe1583447dd8e72e550774604904356661"
    },
    "tests/test_proposal_context_builder.py::test_unresolved_participant_evidence_is_critical_reference_residual": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-proposal-context-builder-test-unresolved-participant-evidence-is-critical-reference-residual",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "3428d191d2a758680d7bed2239455aa05e79c046f400d2ad887dd5381ac372d7"
    },
}
