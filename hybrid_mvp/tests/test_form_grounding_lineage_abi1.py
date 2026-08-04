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
                forms.EVIDENCE_MAX_AGGREGATE_NODES // forms.EVIDENCE_MAX_CONTAINER_ITEMS
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
                forms.EVIDENCE_MAX_AGGREGATE_CHARS // forms.EVIDENCE_MAX_SCALAR_CHARS
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


class _ExplodingWireUnit(FormUnit):
    def as_dict(self) -> dict[str, object]:
        raise AssertionError("child serialized before lattice scalar validation")


def test_form_unit_and_nested_codec_reject_hostile_scalars() -> None:
    huge_ref = "r" * (forms.EVIDENCE_MAX_REF_CHARS + 1)
    huge_scalar = "s" * (forms.EVIDENCE_MAX_SCALAR_CHARS + 1)
    huge_key = "k" * (forms.EVIDENCE_MAX_KEY_CHARS + 1)

    with pytest.raises(ValueError, match="unit_ref exceeds"):
        replace(_unit(), unit_ref=huge_ref)
    with pytest.raises(ValueError, match="source text exceeds"):
        replace(
            _unit(),
            source_text="s" * (forms.EVIDENCE_MAX_SOURCE_CHARS + 1),
            source_end=forms.EVIDENCE_MAX_SOURCE_CHARS + 1,
        )
    with pytest.raises(ValueError, match="normalized_forms.*exceeds"):
        replace(_unit(), normalized_forms=(huge_scalar,))
    with pytest.raises(ValueError, match="feature key exceeds"):
        replace(_unit(), features=((huge_key, "value"),))
    with pytest.raises(ValueError, match="feature value exceeds"):
        replace(_unit(), features=(("key", huge_scalar),))

    wire = _unit().as_dict()
    with pytest.raises(ValueError, match="normalized_forms.*exceeds"):
        FormUnit.from_dict({**wire, "normalized_forms": [huge_scalar]})


def test_form_hypothesis_and_nested_codec_reject_hostile_scalars() -> None:
    huge_ref = "r" * (forms.EVIDENCE_MAX_REF_CHARS + 1)
    huge_scalar = "s" * (forms.EVIDENCE_MAX_SCALAR_CHARS + 1)
    huge_key = "k" * (forms.EVIDENCE_MAX_KEY_CHARS + 1)
    hypothesis = _lattice().hypotheses[0]

    with pytest.raises(ValueError, match="hypothesis_ref exceeds"):
        replace(hypothesis, hypothesis_ref=huge_ref)
    with pytest.raises(ValueError, match="unit_ref exceeds"):
        replace(hypothesis, unit_refs=(huge_ref,))
    with pytest.raises(ValueError, match="construction exceeds"):
        replace(hypothesis, construction=huge_scalar)
    with pytest.raises(ValueError, match="feature key exceeds"):
        replace(hypothesis, features=((huge_key, "value"),))
    with pytest.raises(ValueError, match="feature value exceeds"):
        replace(hypothesis, features=(("key", huge_scalar),))

    wire = hypothesis.as_dict()
    with pytest.raises(ValueError, match="unit_ref exceeds"):
        FormHypothesis.from_dict({**wire, "unit_refs": [huge_ref]})


def test_form_lattice_prebounds_scalars_before_child_serialization_and_decode() -> None:
    huge_ref = "r" * (forms.EVIDENCE_MAX_REF_CHARS + 1)
    exploding_unit = _ExplodingWireUnit(
        unit_ref="unit:0",
        source_text="Hello",
        normalized_forms=("hello",),
        source_start=0,
        source_end=5,
        features=(),
    )

    with pytest.raises(ValueError, match="evidence_packet_ref exceeds"):
        FormLattice.create(
            evidence_packet_ref=huge_ref,
            form_pack_hash="sha256:form-pack",
            source_text="Hello",
            units=(exploding_unit,),
            hypotheses=(),
        )
    with pytest.raises(ValueError, match="form_pack_hash exceeds"):
        FormLattice.create(
            evidence_packet_ref="evidence_packet:test",
            form_pack_hash=huge_ref,
            source_text="Hello",
            units=(exploding_unit,),
            hypotheses=(),
        )
    with pytest.raises(ValueError, match="source text exceeds"):
        FormLattice.create(
            evidence_packet_ref="evidence_packet:test",
            form_pack_hash="sha256:form-pack",
            source_text="s" * (forms.EVIDENCE_MAX_SOURCE_CHARS + 1),
            units=(exploding_unit,),
            hypotheses=(),
        )
    with pytest.raises(TypeError, match="source_text"):
        FormLattice.create(
            evidence_packet_ref="evidence_packet:test",
            form_pack_hash="sha256:form-pack",
            source_text=None,  # type: ignore[arg-type]
            units=(exploding_unit,),
            hypotheses=(),
        )

    wire = _lattice().as_dict()
    with pytest.raises(ValueError, match="lattice_ref exceeds"):
        FormLattice.from_dict({**wire, "lattice_ref": huge_ref, "units": [object()]})


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


def _nested_grounding_result() -> grounding.GroundingResult:
    return grounding.GroundingResult.create(
        evidence_packet_ref="evidence_packet:test",
        form_lattice_ref="form_lattice:test",
        revision_pin=_pin(),
        designations=(
            grounding.DesignationCandidate(
                unit_refs=("unit:0",),
                target_ref="event:greeting",
                designation_fact_ref="designation:greeting",
                score=0.1,
                provenance_refs=("authority:test",),
            ),
        ),
        unresolved=(
            grounding.ReferenceRequirement(
                unit_ref="unit:1",
                kind="designation",
                required_kind="concept",
                resolved_ref=None,
            ),
        ),
        grounded_items=(
            grounding.GroundedItem(
                source_ref="evidence_item:test",
                source_kind="text",
                target_ref="event:greeting",
                unit_refs=("unit:0",),
            ),
        ),
        provenance_refs=("authority:test", "turn:test"),
    )


def test_grounding_nested_codecs_are_strict_tamper_evident_and_exact() -> None:
    result = _nested_grounding_result()
    wire = result.as_dict()
    rebuilt = grounding.GroundingResult.from_dict(wire)

    assert rebuilt == result
    assert rebuilt.designations[0].score.hex() == result.designations[0].score.hex()
    assert (
        grounding.DesignationCandidate.from_dict(result.designations[0].as_dict())
        == result.designations[0]
    )
    assert (
        grounding.ReferenceRequirement.from_dict(result.unresolved[0].as_dict())
        == result.unresolved[0]
    )
    assert (
        grounding.GroundedItem.from_dict(result.grounded_items[0].as_dict())
        == result.grounded_items[0]
    )

    tampered_score = result.as_dict()
    tampered_score["designations"][0]["score"] = 0.2
    with pytest.raises(ValueError, match="GroundingResult ref mismatch"):
        grounding.GroundingResult.from_dict(tampered_score)

    nested_unknown = result.designations[0].as_dict()
    nested_unknown["unknown"] = "field"
    with pytest.raises(ValueError, match="DesignationCandidate fields"):
        grounding.DesignationCandidate.from_dict(nested_unknown)

    with pytest.raises(TypeError, match="unit_refs must be a tuple"):
        replace(result.designations[0], unit_refs=["unit:0"])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="score must be finite"):
        replace(result.designations[0], score=float("nan"))


class _OversizedDesignations(tuple[grounding.DesignationCandidate, ...]):
    def __iter__(self):  # type: ignore[no-untyped-def]
        raise AssertionError("oversized designations were iterated")


def test_grounding_result_prebounds_before_iteration_and_child_decode() -> None:
    candidate = _nested_grounding_result().designations[0]
    oversized = _OversizedDesignations(
        (candidate,) * (grounding.GROUNDING_MAX_DESIGNATIONS + 1)
    )
    with pytest.raises(ValueError, match="designations exceeds"):
        grounding.GroundingResult.create(
            evidence_packet_ref="evidence_packet:test",
            form_lattice_ref="form_lattice:test",
            revision_pin=_pin(),
            designations=oversized,
            unresolved=(),
            grounded_items=(),
            provenance_refs=(),
        )

    wire = _nested_grounding_result().as_dict()
    wire["designations"] = [object()] * (grounding.GROUNDING_MAX_DESIGNATIONS + 1)
    with pytest.raises(ValueError, match="designations exceeds"):
        grounding.GroundingResult.from_dict(wire)

    huge_ref = "x" * (forms.EVIDENCE_MAX_REF_CHARS + 1)
    hostile_wire = _nested_grounding_result().as_dict()
    hostile_wire["grounding_ref"] = huge_ref
    hostile_wire["designations"] = [object()]
    with pytest.raises(ValueError, match="grounding_ref exceeds"):
        grounding.GroundingResult.from_dict(hostile_wire)


def test_grounding_result_rejects_forged_refs_revision_and_created_authority() -> None:
    result = _nested_grounding_result()

    with pytest.raises(ValueError, match="GroundingResult ref mismatch"):
        replace(result, grounding_ref="grounding_result:forged")
    with pytest.raises(ValueError, match="created_refs.*empty"):
        replace(result, created_refs=("concept:manufactured",))

    forged_evidence = result.as_dict()
    forged_evidence["evidence_packet_ref"] = "evidence_packet:other"
    with pytest.raises(ValueError, match="GroundingResult ref mismatch"):
        grounding.GroundingResult.from_dict(forged_evidence)

    forged_pin = result.as_dict()
    forged_pin["revision_pin"]["world_revision"] = True
    with pytest.raises(TypeError, match="world_revision must be int"):
        grounding.GroundingResult.from_dict(forged_pin)


@pytest.mark.parametrize(
    "helper_name",
    ("_ground_surface", "_ground_sensor", "_ground_operation"),
    ids=("surface", "sensor", "operation"),
)
def test_grounder_has_no_unlineaged_private_grounding_helpers(
    helper_name: str,
) -> None:
    assert helper_name not in Grounder.__dict__

def test_r1_grounding_result_rejects_forgery_and_exact_revision_types() -> None:
    result = _nested_grounding_result()

    with pytest.raises(ValueError, match="GroundingResult ref mismatch"):
        replace(result, grounding_ref="grounding_result:forged")
    with pytest.raises(ValueError, match="created_refs.*empty"):
        replace(result, created_refs=("concept:manufactured",))

    forged_evidence = result.as_dict()
    forged_evidence["evidence_packet_ref"] = "evidence_packet:other"
    with pytest.raises(ValueError, match="GroundingResult ref mismatch"):
        grounding.GroundingResult.from_dict(forged_evidence)

    forged_pin = result.as_dict()
    forged_pin["revision_pin"]["world_revision"] = True
    with pytest.raises(TypeError, match="world_revision must be exact int"):
        grounding.GroundingResult.from_dict(forged_pin)

__cemm_test_inventory__ = {'tests/test_form_grounding_lineage_abi1.py::test_duplicate_modality_evidence_preserves_rows_and_unique_source_units': {'activation_phase': 'R1',
                                                                                                                        'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-duplicate-modality-evidence-preserves-rows-and-unique-source-units',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'R1-Task-9',
                                                                                                                        'owner_ref': 'runtime-path',
                                                                                                                        'source_ast_sha256': '8c59a06cf0d0b7d58bfaacc7715c5c1d4eb01a52b7f4eb0c876bfc3c2b528a5b'},
 'tests/test_form_grounding_lineage_abi1.py::test_evidence_create_prebounds_scalars_provenance_and_aggregates': {'activation_phase': 'R1',
                                                                                                                 'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-evidence-create-prebounds-scalars-provenance-and-aggregates',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'R1-Task-9',
                                                                                                                 'owner_ref': 'runtime-path',
                                                                                                                 'source_ast_sha256': 'c9d463e78b0c1fd712b6e42ed5876b97267da0ee05bb201c631afa9804667159'},
 'tests/test_form_grounding_lineage_abi1.py::test_evidence_nested_mapping_is_deeply_immutable': {'activation_phase': 'R1',
                                                                                                 'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-evidence-nested-mapping-is-deeply-immutable',
                                                                                                 'diagnostic_role': 'owner',
                                                                                                 'introduced_by_task': 'R1-Task-9',
                                                                                                 'owner_ref': 'runtime-path',
                                                                                                 'source_ast_sha256': 'e617aa4a4dd7425cfe0bc224fc7dec162420219b86fcb5fdc30f13b07a654bb2'},
 'tests/test_form_grounding_lineage_abi1.py::test_evidence_packet_abi1_rejects_tamper_and_freezes_nested_content': {'activation_phase': 'R1',
                                                                                                                    'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-evidence-packet-abi1-rejects-tamper-and-freezes-nested-content',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'R1-Task-9',
                                                                                                                    'owner_ref': 'runtime-path',
                                                                                                                    'source_ast_sha256': '5160c7723c52e0edd3bdbb59d1538c30e10de76bd548cd3c1f8d080d65c54a48'},
 'tests/test_form_grounding_lineage_abi1.py::test_form_hypothesis_and_nested_codec_reject_hostile_scalars': {'activation_phase': 'R1',
                                                                                                             'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-form-hypothesis-and-nested-codec-reject-hostile-scalars',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'R1-Task-9',
                                                                                                             'owner_ref': 'runtime-path',
                                                                                                             'source_ast_sha256': 'ef6653efe418d2128a61217fe316742ddc1a831f4936bd40071153f684edabf9'},
 'tests/test_form_grounding_lineage_abi1.py::test_form_lattice_abi1_is_content_addressed_strict_and_indexed_once': {'activation_phase': 'R1',
                                                                                                                    'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-form-lattice-abi1-is-content-addressed-strict-and-indexed-once',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'R1-Task-9',
                                                                                                                    'owner_ref': 'runtime-path',
                                                                                                                    'source_ast_sha256': 'e5ba67a6836699a72b6fc41e065fce18208d505b1e4f83f2f55e70fa24d817c8'},
 'tests/test_form_grounding_lineage_abi1.py::test_form_lattice_create_prebounds_units_before_iteration': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-form-lattice-create-prebounds-units-before-iteration',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Task-9',
                                                                                                          'owner_ref': 'runtime-path',
                                                                                                          'source_ast_sha256': '92355faf6b30a0880c533b3fddad21ca3910ce4677df7862cf2c7f8e8b65bf6f'},
 'tests/test_form_grounding_lineage_abi1.py::test_form_lattice_prebounds_scalars_before_child_serialization_and_decode': {'activation_phase': 'R1',
                                                                                                                          'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-form-lattice-prebounds-scalars-before-child-serialization-and-decode',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'R1-Task-9',
                                                                                                                          'owner_ref': 'runtime-path',
                                                                                                                          'source_ast_sha256': '1e84c02ee9daaa1b92fcd6bd0c1ec8dbdb9ddd9ba405d2970f0e8b85537f804e'},
 'tests/test_form_grounding_lineage_abi1.py::test_form_resolver_enforces_reduced_config_unit_bound': {'activation_phase': 'R1',
                                                                                                      'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-form-resolver-enforces-reduced-config-unit-bound',
                                                                                                      'diagnostic_role': 'owner',
                                                                                                      'introduced_by_task': 'R1-Task-9',
                                                                                                      'owner_ref': 'runtime-path',
                                                                                                      'source_ast_sha256': '57e00b672f1052ffda849497e63ba7909c06465f039867fcef5bdf487c2a709e'},
 'tests/test_form_grounding_lineage_abi1.py::test_form_unit_and_nested_codec_reject_hostile_scalars': {'activation_phase': 'R1',
                                                                                                       'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-form-unit-and-nested-codec-reject-hostile-scalars',
                                                                                                       'diagnostic_role': 'owner',
                                                                                                       'introduced_by_task': 'R1-Task-9',
                                                                                                       'owner_ref': 'runtime-path',
                                                                                                       'source_ast_sha256': '46a6d2fe8db57be726c542d644113bad55272c89661e145eb514f1ed237c7b51'},
 'tests/test_form_grounding_lineage_abi1.py::test_ground_lattice_consumes_existing_lattice_without_resolver_reentry': {'activation_phase': 'R1',
                                                                                                                       'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-ground-lattice-consumes-existing-lattice-without-resolver-reentry',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'R1-Task-9',
                                                                                                                       'owner_ref': 'runtime-path',
                                                                                                                       'source_ast_sha256': 'a7bcb797549e2fcc8289b5e1f2afd36b4154248e25259c160a1cbb28d17b4687'},
 'tests/test_form_grounding_lineage_abi1.py::test_grounder_has_no_unlineaged_private_grounding_helpers[operation]': {'activation_phase': 'R1',
                                                                                                                     'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-grounder-has-no-unlineaged-private-grounding-helpers-operation',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'R1-Task-9',
                                                                                                                     'owner_ref': 'runtime-path',
                                                                                                                     'source_ast_sha256': 'cae0529c5f8ed08383e6bffeae866c18ca0e2aa62cc8651ffecfc17925662824'},
 'tests/test_form_grounding_lineage_abi1.py::test_grounder_has_no_unlineaged_private_grounding_helpers[sensor]': {'activation_phase': 'R1',
                                                                                                                  'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-grounder-has-no-unlineaged-private-grounding-helpers-sensor',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'R1-Task-9',
                                                                                                                  'owner_ref': 'runtime-path',
                                                                                                                  'source_ast_sha256': 'cae0529c5f8ed08383e6bffeae866c18ca0e2aa62cc8651ffecfc17925662824'},
 'tests/test_form_grounding_lineage_abi1.py::test_grounder_has_no_unlineaged_private_grounding_helpers[surface]': {'activation_phase': 'R1',
                                                                                                                   'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-grounder-has-no-unlineaged-private-grounding-helpers-surface',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'R1-Task-9',
                                                                                                                   'owner_ref': 'runtime-path',
                                                                                                                   'source_ast_sha256': 'cae0529c5f8ed08383e6bffeae866c18ca0e2aa62cc8651ffecfc17925662824'},
 'tests/test_form_grounding_lineage_abi1.py::test_grounding_nested_codecs_are_strict_tamper_evident_and_exact': {'activation_phase': 'R1',
                                                                                                                 'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-grounding-nested-codecs-are-strict-tamper-evident-and-exact',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'R1-Task-9',
                                                                                                                 'owner_ref': 'runtime-path',
                                                                                                                 'source_ast_sha256': 'a235b0f90f9290622b13c16ce8878223ec60cb54e395458d7bdd60fa807a5f14'},
 'tests/test_form_grounding_lineage_abi1.py::test_grounding_result_abi1_is_content_addressed_and_lineage_pinned': {'activation_phase': 'R1',
                                                                                                                   'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-grounding-result-abi1-is-content-addressed-and-lineage-pinned',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'R1-Task-9',
                                                                                                                   'owner_ref': 'runtime-path',
                                                                                                                   'source_ast_sha256': '48e6583dd24cc7d4c39fd8c0ab25ec6045745117955912c5d38cb4d8f2e47359'},
 'tests/test_form_grounding_lineage_abi1.py::test_grounding_result_prebounds_before_iteration_and_child_decode': {'activation_phase': 'R1',
                                                                                                                  'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-grounding-result-prebounds-before-iteration-and-child-decode',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'R1-Task-9',
                                                                                                                  'owner_ref': 'runtime-path',
                                                                                                                  'source_ast_sha256': 'edc3718d58593d24549739c645211d443761978f4a7d6fdfb6b6cc2903600fc9'},
 'tests/test_form_grounding_lineage_abi1.py::test_grounding_result_rejects_forged_refs_revision_and_created_authority': {'activation_phase': 'R1',
                                                                                                                         'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-grounding-result-rejects-forged-refs-revision-and-created-authority',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'R1-Task-9',
                                                                                                                         'owner_ref': 'runtime-path',
                                                                                                                         'source_ast_sha256': '25d79c86934a2aa8bda14beb1aff30f80924f6845a2ea30c0eb27eb640cbc3b4'},
 'tests/test_form_grounding_lineage_abi1.py::test_resolve_evidence_preserves_exact_packet_lineage': {'activation_phase': 'R1',
                                                                                                     'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-resolve-evidence-preserves-exact-packet-lineage',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'R1-Task-9',
                                                                                                     'owner_ref': 'runtime-path',
                                                                                                     'source_ast_sha256': 'c4e8c5d329a5d6a34ea07e67c524f4266da70d37d0900812ae62aec50a90e474'},
 'tests/test_form_grounding_lineage_abi1.py::test_r1_grounding_result_rejects_forgery_and_exact_revision_types': {'activation_phase': 'R1',
                                                                                                                 'assertion_ref': 'assertion:r1-form-grounding-lineage-abi1-test-grounding-result-rejects-forged-refs-revision-and-created-authority',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'R1-Task-9',
                                                                                                                 'owner_ref': 'runtime-path',
                                                                                                                 'source_ast_sha256': '5ce4f50784ff1fcbb0c399e9a5fd98d4c6ce5eda45baabd7f70f961566a17a51',
                                                                                                                 'supersedes_node_id': 'tests/test_form_grounding_lineage_abi1.py::test_grounding_result_rejects_forged_refs_revision_and_created_authority'},}
