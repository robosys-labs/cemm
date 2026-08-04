from __future__ import annotations

from dataclasses import replace

import pytest

from cemm_authoritative_hybrid import forms, grounding
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.forms import (
    EvidenceItem,
    EvidencePacket,
    FormHypothesis,
    FormLattice,
    FormResolver,
    FormUnit,
)
from cemm_authoritative_hybrid.grounding import Grounder
from cemm_authoritative_hybrid.persistence import RevisionPin


def _pin() -> RevisionPin:
    return RevisionPin("authority:test", 1, 2, 3, 4, "model:test")


def _unit(*, normalized: str = "hello") -> FormUnit:
    return FormUnit(
        unit_ref="unit:0",
        source_text="Hello",
        normalized_forms=(normalized,),
        source_start=0,
        source_end=5,
        features=(("discourse", "greeting"),),
    )


def _lattice(*, normalized: str = "hello") -> FormLattice:
    return FormLattice.create(
        evidence_packet_ref="evidence_packet:test",
        form_pack_hash="sha256:form-pack",
        source_text="Hello",
        units=(_unit(normalized=normalized),),
        hypotheses=(
            FormHypothesis(
                hypothesis_ref="hypothesis:0",
                unit_refs=("unit:0",),
                construction="discourse_report",
                features=(("discourse", "greeting"),),
            ),
        ),
    )


def test_evidence_packet_abi1_rejects_tamper_and_freezes_nested_content() -> None:
    item = EvidenceItem.create(
        source="text",
        content="Hello",
        source_ref="source:test",
        provenance_refs=("turn:test",),
        adapter_receipt_ref=None,
    )
    packet = EvidencePacket.create(
        items=(item,),
        source_text="Hello",
        form_pack_hash="sha256:form-pack",
    )

    assert forms.EVIDENCE_ABI_VERSION == 1
    assert packet.packet_ref.startswith("evidence_packet:")
    assert EvidencePacket.from_dict(packet.as_dict()) == packet
    with pytest.raises(ValueError, match="ref mismatch"):
        EvidencePacket.from_dict(
            {**packet.as_dict(), "packet_ref": "evidence_packet:forged"}
        )
    with pytest.raises(ValueError, match="source_text"):
        EvidencePacket.create(
            items=(item,),
            source_text="Different",
            form_pack_hash="sha256:form-pack",
        )


def test_resolve_evidence_preserves_exact_packet_lineage(
    form_resolver: FormResolver,
) -> None:
    item = EvidenceItem.create(
        source="text",
        content="Hello",
        source_ref="source:test",
        provenance_refs=("turn:test",),
        adapter_receipt_ref=None,
    )
    packet = EvidencePacket.create(
        items=(item,),
        source_text="Hello",
        form_pack_hash=form_resolver.form_pack_hash,
    )

    lattice = form_resolver.resolve_evidence(packet)

    assert lattice.evidence_packet_ref == packet.packet_ref
    assert lattice.form_pack_hash == packet.form_pack_hash
    with pytest.raises(ValueError, match="form pack hash"):
        form_resolver.resolve_evidence(
            EvidencePacket.create(
                items=(item,),
                source_text="Hello",
                form_pack_hash="sha256:wrong",
            )
        )


class _OversizedUnits(tuple[FormUnit, ...]):
    def __iter__(self):
        raise AssertionError("oversized units were iterated before bound rejection")


def test_form_lattice_create_prebounds_units_before_iteration() -> None:
    oversized = _OversizedUnits((_unit(),) * 65)
    with pytest.raises(ValueError, match="units exceeds"):
        FormLattice.create(
            evidence_packet_ref="evidence_packet:test",
            form_pack_hash="sha256:form-pack",
            source_text="Hello",
            units=oversized,
            hypotheses=(),
        )


def test_form_resolver_enforces_reduced_config_unit_bound(form_pack) -> None:
    resolver = FormResolver(
        form_pack,
        RuntimeConfig(max_input_tokens=2),
    )
    with pytest.raises(ValueError, match="unit bound"):
        resolver.resolve("a b")


class _OversizedProvenance(tuple[str, ...]):
    def __iter__(self):
        raise AssertionError("provenance was iterated before bound rejection")


def test_evidence_create_prebounds_scalars_provenance_and_aggregates(
    form_resolver: FormResolver,
) -> None:
    with pytest.raises(ValueError, match="source_ref exceeds"):
        EvidenceItem.create(
            source="text",
            content="hello",
            source_ref="r" * (forms.EVIDENCE_MAX_REF_CHARS + 1),
            provenance_refs=(),
            adapter_receipt_ref=None,
        )

    with pytest.raises(ValueError, match="content string exceeds"):
        EvidenceItem.create(
            source="sensor",
            content={"value": "x" * (forms.EVIDENCE_MAX_SCALAR_CHARS + 1)},
            source_ref="source:sensor",
            provenance_refs=(),
            adapter_receipt_ref="receipt:test",
        )

    provenance = _OversizedProvenance(
        ("turn:test",) * (forms.EVIDENCE_MAX_PROVENANCE_REFS + 1)
    )
    with pytest.raises(ValueError, match="provenance_refs exceeds"):
        EvidenceItem.create(
            source="text",
            content="hello",
            source_ref="source:test",
            provenance_refs=provenance,
            adapter_receipt_ref=None,
        )

    with pytest.raises(ValueError, match="integer"):
        EvidenceItem.create(
            source="sensor",
            content={"count": forms.EVIDENCE_MAX_INTEGER + 1},
            source_ref="source:sensor",
            provenance_refs=(),
            adapter_receipt_ref="receipt:test",
        )

    aggregate = {
        "rows": [
            [None] * forms.EVIDENCE_MAX_CONTAINER_ITEMS
            for _ in range(
                forms.EVIDENCE_MAX_AGGREGATE_NODES
                // forms.EVIDENCE_MAX_CONTAINER_ITEMS
                + 1
            )
        ]
    }
    with pytest.raises(ValueError, match="aggregate nodes"):
        EvidenceItem.create(
            source="sensor",
            content=aggregate,
            source_ref="source:sensor",
            provenance_refs=(),
            adapter_receipt_ref="receipt:test",
        )

    aggregate_chars = {
        "rows": [
            "x" * forms.EVIDENCE_MAX_SCALAR_CHARS
            for _ in range(
                forms.EVIDENCE_MAX_AGGREGATE_CHARS
                // forms.EVIDENCE_MAX_SCALAR_CHARS
                + 1
            )
        ]
    }
    with pytest.raises(ValueError, match="aggregate chars"):
        EvidenceItem.create(
            source="sensor",
            content=aggregate_chars,
            source_ref="source:sensor",
            provenance_refs=(),
            adapter_receipt_ref="receipt:test",
        )

    with pytest.raises(ValueError, match="mapping key"):
        EvidenceItem.create(
            source="sensor",
            content={"k" * (forms.EVIDENCE_MAX_KEY_CHARS + 1): None},
            source_ref="source:sensor",
            provenance_refs=(),
            adapter_receipt_ref="receipt:test",
        )

    class ExplodingTokenizer:
        def __call__(self, _text: str):
            raise AssertionError("huge source reached tokenization")

    form_resolver._tokenize = ExplodingTokenizer()  # type: ignore[method-assign]
    with pytest.raises(ValueError, match="source text exceeds"):
        form_resolver.resolve("x" * (forms.EVIDENCE_MAX_SOURCE_CHARS + 1))


def test_evidence_nested_mapping_is_deeply_immutable() -> None:
    item = EvidenceItem.create(
        source="sensor",
        content={"nested": {"values": [1, 2]}},
        source_ref="source:sensor",
        provenance_refs=("turn:test",),
        adapter_receipt_ref="receipt:test",
    )

    nested = item.content["nested"]
    with pytest.raises(TypeError):
        nested["forged"] = True  # type: ignore[index]
    assert nested["values"] == (1, 2)  # type: ignore[index]


def test_duplicate_modality_evidence_preserves_rows_and_unique_source_units(
    form_resolver: FormResolver,
) -> None:
    lattice = form_resolver.resolve("can can")
    hypothesis = next(
        row for row in lattice.hypotheses if row.construction == "modality"
    )
    assert hypothesis.unit_refs == ("unit:0", "unit:2")
    assert hypothesis.features == (
        ("modality", "capability"),
        ("modality", "capability"),
    )

    repeated_feature_unit = FormUnit(
        unit_ref="unit:0",
        source_text="can",
        normalized_forms=("can",),
        source_start=0,
        source_end=3,
        features=(
            ("modality", "capability"),
            ("modality", "capability"),
        ),
    )
    repeated = form_resolver._build_hypotheses((repeated_feature_unit,))
    modality = next(row for row in repeated if row.construction == "modality")
    assert modality.unit_refs == ("unit:0",)
    assert modality.features == repeated_feature_unit.features


def test_form_lattice_abi1_is_content_addressed_strict_and_indexed_once() -> None:
    lattice = _lattice()

    assert forms.FORM_LATTICE_ABI_VERSION == 1
    assert lattice.abi_version == 1
    assert lattice.source_length == 5
    assert lattice.lattice_ref.startswith("form_lattice:")
    assert lattice.unit("unit:0") is lattice.units[0]
    assert lattice.unit_index is lattice.unit_index
    with pytest.raises(TypeError):
        lattice.unit_index["unit:forged"] = lattice.units[0]  # type: ignore[index]

    wire = lattice.as_dict()
    assert FormLattice.from_dict(wire) == lattice
    with pytest.raises(ValueError, match="ref mismatch"):
        FormLattice.from_dict({**wire, "lattice_ref": "form_lattice:forged"})
    with pytest.raises(TypeError, match="abi_version"):
        FormLattice.from_dict({**wire, "abi_version": True})
    with pytest.raises(TypeError, match="source_length"):
        FormLattice.from_dict({**wire, "source_length": True})
    with pytest.raises(ValueError, match="fields mismatch"):
        FormLattice.from_dict({**wire, "unexpected": "field"})
    with pytest.raises(ValueError, match="units exceeds"):
        FormLattice.from_dict({**wire, "units": wire["units"] * 65})
    with pytest.raises(ValueError, match="hypotheses exceeds"):
        FormLattice.from_dict({**wire, "hypotheses": wire["hypotheses"] * 17})
    unit_wire = lattice.units[0].as_dict()
    with pytest.raises(ValueError, match="normalized_forms exceeds"):
        FormUnit.from_dict({**unit_wire, "normalized_forms": ["x"] * 9})
    with pytest.raises(ValueError, match="features exceeds"):
        FormUnit.from_dict({**unit_wire, "features": [["kind", "value"]] * 17})
    hypothesis_wire = lattice.hypotheses[0].as_dict()
    with pytest.raises(ValueError, match="unit_refs exceeds"):
        FormHypothesis.from_dict(
            {
                **hypothesis_wire,
                "unit_refs": [f"unit:{index}" for index in range(65)],
            }
        )
    with pytest.raises(ValueError, match="features exceeds"):
        FormHypothesis.from_dict(
            {
                **hypothesis_wire,
                "features": [["kind", "value"]] * 65,
            }
        )
    with pytest.raises(ValueError, match="geometry"):
        FormLattice.create(
            evidence_packet_ref="evidence_packet:test",
            form_pack_hash="sha256:form-pack",
            source_text="Hello",
            units=(replace(_unit(), source_end=4),),
            hypotheses=(),
        )


def test_grounding_result_abi1_is_content_addressed_and_lineage_pinned() -> None:
    lattice = _lattice()
    result = grounding.GroundingResult.create(
        evidence_packet_ref=lattice.evidence_packet_ref,
        form_lattice_ref=lattice.lattice_ref,
        revision_pin=_pin(),
        designations=(),
        unresolved=(),
        grounded_items=(),
        provenance_refs=("authority:test",),
    )

    assert grounding.GROUNDING_RESULT_ABI_VERSION == 1
    assert result.abi_version == 1
    assert result.created_refs == ()
    assert result.grounding_ref.startswith("grounding_result:")
    wire = result.as_dict()
    assert grounding.GroundingResult.from_dict(wire) == result
    with pytest.raises(ValueError, match="created_refs.*empty"):
        grounding.GroundingResult.from_dict(
            {**wire, "created_refs": ["concept:manufactured"]}
        )


def test_ground_lattice_consumes_existing_lattice_without_resolver_reentry(
    grounder: Grounder,
) -> None:
    lattice = _lattice()

    class ExplodingResolver:
        def resolve(self, *_args: object, **_kwargs: object) -> FormLattice:
            raise AssertionError("ground_lattice retokenized source text")

    grounder._resolver = ExplodingResolver()  # type: ignore[assignment]
    result = grounder.ground_lattice(lattice, revision_pin=_pin())

    assert result.form_lattice_ref == lattice.lattice_ref
    assert result.evidence_packet_ref == lattice.evidence_packet_ref