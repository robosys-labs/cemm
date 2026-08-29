from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.r4_partition_config import (
    BOUND_VIOLATION_FORMULA,
    LABEL_DEVIATION_FORMULA,
    RARE_LABEL_FORMULA,
    SIZE_DEVIATION_FORMULA,
    DimensionMaximum,
    DimensionMinimum,
    PartitionBounds,
    PartitionObjective,
    R4PartitionConfig,
    SplitWeight,
)
from cemm_authoritative_hybrid.r4_partition_contracts import (
    PURPOSE_BY_SPLIT,
    SPLITS,
    ClassCount,
    DimensionSufficiency,
    GlobalPartitionComponent,
    LabelCount,
    LeakageHyperedge,
    PartitionEvidence,
    R4ClassAuthorization,
    R4ClassCapability,
    R4PartitionSufficiencyReceipt,
    R4SplitManifest,
    SplitClassRecord,
    StratificationLabel,
    artifact_graph_ref_for,
    authenticate_class_capability,
)


ROOT = Path(__file__).parents[1]
SCHEMA_PATHS = (
    ROOT / "schemas/r4_partition_evidence.schema.json",
    ROOT / "schemas/r4_split_manifest.schema.json",
    ROOT / "schemas/r4_partition_sufficiency.schema.json",
    ROOT / "schemas/r4_class_capability.schema.json",
    ROOT / "schemas/r4_class_authorization.schema.json",
    ROOT / "schemas/r4_partition_config.schema.json",
)
__cemm_test_inventory__ = {
    "tests/test_r4_partition_contracts.py::test_partition_contracts_are_factory_only_and_canonical": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-partition-contracts-factory-only-and-canonical",
        "diagnostic_role": "phase",
        "introduced_by_task": "R4-Partition-Corrective-Task-3",
        "source_ast_sha256": "8f17ec138e67086741add95e21baccaefb46c21ff5433b0f357e7977d1c277fd",
    },
    "tests/test_r4_partition_contracts.py::test_component_identity_binds_source_and_partition_abi_not_assignment": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-component-identity-binds-source-and-partition-abi",
        "diagnostic_role": "phase",
        "introduced_by_task": "R4-Partition-Corrective-Task-3",
        "source_ast_sha256": "f62b20c68a29369e2daeb8f09e94bffeb54d7e6805dea5b3cc83fd73af64ba82",
    },
    "tests/test_r4_partition_contracts.py::test_leakage_and_label_records_reject_noncanonical_members": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-leakage-and-label-records-reject-noncanonical-members",
        "diagnostic_role": "phase",
        "introduced_by_task": "R4-Partition-Corrective-Task-3",
        "source_ast_sha256": "a02618a938ab890f7f3719a37d13f4042760cb97fee066f3dbf26c023906d176",
    },
    "tests/test_r4_partition_contracts.py::test_partition_evidence_reconstructs_global_coverage_and_rejects_tamper": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-partition-evidence-reconstructs-global-coverage",
        "diagnostic_role": "phase",
        "introduced_by_task": "R4-Partition-Corrective-Task-3",
        "source_ast_sha256": "b4362bcb5fd3c966c6e64412e912ce4a8a351f5079a0f2b91a719e809a86214a",
    },
    "tests/test_r4_partition_contracts.py::test_split_manifest_is_exact_four_class_boundary": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-split-manifest-is-exact-four-class-boundary",
        "diagnostic_role": "phase",
        "introduced_by_task": "R4-Partition-Corrective-Task-3",
        "source_ast_sha256": "1e80a82f5ab26b29dadfc50067726f9308ebaa27ceb40181eb65ba43f36cb2f3",
    },
    "tests/test_r4_partition_contracts.py::test_split_manifest_rejects_unsafe_paths_and_invalid_purpose_pairing": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-split-manifest-rejects-unsafe-paths-and-purpose-pairing",
        "diagnostic_role": "phase",
        "introduced_by_task": "R4-Partition-Corrective-Task-3",
        "source_ast_sha256": "b586a5df5c1c1c6ef86cfa7e373a805066de4ab49427ec191b1f9dd8711c0486",
    },
    "tests/test_r4_partition_contracts.py::test_partition_sufficiency_is_non_vacuous_complete_and_reconstructible": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-partition-sufficiency-is-non-vacuous-and-complete",
        "diagnostic_role": "phase",
        "introduced_by_task": "R4-Partition-Corrective-Task-3",
        "source_ast_sha256": "a2ebd4cfc1f85fceb3ef7b134d28f980485fee277df6f0e41614b9535f52570a",
    },
    "tests/test_r4_partition_contracts.py::test_class_capability_requires_independent_authorization_trust": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-class-capability-requires-independent-authorization-trust",
        "diagnostic_role": "phase",
        "introduced_by_task": "R4-Partition-Corrective-Task-3",
        "source_ast_sha256": "a97cd4f6e872fab8a67410e6f9c138a0808139f9261f47e02f11e4e633c53307",
    },
    "tests/test_r4_partition_contracts.py::test_class_authorization_discloses_no_sibling_or_build_receipt_fields": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-class-authorization-discloses-no-sibling-identities",
        "diagnostic_role": "phase",
        "introduced_by_task": "R4-Partition-Corrective-Task-3",
        "source_ast_sha256": "6a32d4210f6ee8b3035e810dc501c3a7d9d314f6d76b9444e19ebdc7712f2b25",
    },
    "tests/test_r4_partition_contracts.py::test_partition_config_binds_reviewed_integer_formulas_and_acyclic_basis": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-partition-config-binds-reviewed-integer-formulas",
        "diagnostic_role": "phase",
        "introduced_by_task": "R4-Partition-Corrective-Task-3",
        "source_ast_sha256": "da7dea5ae66e7376b9eea44bc25040e3e302fc90fa22e00aaed3b483605fe712",
    },
    "tests/test_r4_partition_contracts.py::test_contract_decoders_reject_unknown_missing_nonfinite_and_noncanonical_json": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-contract-decoders-reject-untrusted-json-bytes",
        "diagnostic_role": "phase",
        "introduced_by_task": "R4-Partition-Corrective-Task-3",
        "source_ast_sha256": "26502a9d10f1993251aa56f54f68b8a5de9023dafa24efaf8273f4df6ad81c06",
    },
    "tests/test_r4_partition_contracts.py::test_r4_partition_schemas_are_strict_draft_2020_12": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-partition-schemas-are-strict-draft-2020-12",
        "diagnostic_role": "phase",
        "introduced_by_task": "R4-Partition-Corrective-Task-3",
        "source_ast_sha256": "9d56f7a983ba53a53d70c12e6f05d8be1777029db13e2cccf84c5f14fab7c471",
    },
    "tests/test_r4_partition_contracts.py::test_partition_abi_registry_declares_hard_cut_without_activation_claim": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-partition-abi-registry-declares-hard-cut-without-activation",
        "diagnostic_role": "phase",
        "introduced_by_task": "R4-Partition-Corrective-Task-3",
        "source_ast_sha256": "e129f9f25948f28eeb049ad5670df68f4e2950db1fa67a4410940b373b45f34a",
    },
}


def _episode_refs() -> tuple[str, ...]:
    return tuple(f"episode:{index:04d}" for index in range(1, 5))


def _source_set_ref(refs: tuple[str, ...]) -> str:
    return stable_ref("r4_partition_source_v3", sorted(refs))


def _partition_evidence() -> PartitionEvidence:
    refs = _episode_refs()
    source_set_ref = _source_set_ref(refs)
    first_edge = LeakageHyperedge.create(
        axis="general",
        key_namespace="reviewed_scenario",
        key_ref="scenario:shared-a",
        member_refs=refs[:2],
    )
    second_edge = LeakageHyperedge.create(
        axis="semantic_target",
        key_namespace="exact_predicate",
        key_ref="predicate:shared-b",
        member_refs=refs[2:],
    )
    first_label = StratificationLabel.create(
        namespace="language:en",
        member_refs=(refs[0], refs[2]),
    )
    second_label = StratificationLabel.create(
        namespace="outcome:supported",
        member_refs=(refs[1], refs[3]),
    )
    first_component = GlobalPartitionComponent.create(
        source_set_ref=source_set_ref,
        member_refs=refs[:2],
        hyperedge_refs=(first_edge.hyperedge_ref,),
        split="train",
    )
    second_component = GlobalPartitionComponent.create(
        source_set_ref=source_set_ref,
        member_refs=refs[2:],
        hyperedge_refs=(second_edge.hyperedge_ref,),
        split="selection",
    )
    return PartitionEvidence.create(
        source_set_ref=source_set_ref,
        config_ref="r4_partition_config_v1:reviewed",
        hyperedges=tuple(sorted((first_edge, second_edge), key=lambda row: row.hyperedge_ref)),
        labels=tuple(sorted((first_label, second_label), key=lambda row: row.label_ref)),
        components=tuple(
            sorted((first_component, second_component), key=lambda row: row.component_ref)
        ),
    )


def _split_classes() -> tuple[SplitClassRecord, ...]:
    refs = _episode_refs()
    rows: list[SplitClassRecord] = []
    for split, member in zip(SPLITS, refs, strict=True):
        digest = hashlib.sha256(f"{split}\n{member}\n".encode("utf-8")).hexdigest()
        rows.append(
            SplitClassRecord.create(
                split=split,
                purpose=PURPOSE_BY_SPLIT[split],
                payload_path=f"artifacts/r4/splits/{split}.jsonl",
                payload_sha256=digest,
                payload_count=1,
                member_refs=(member,),
                component_refs=(f"component:{split}",),
                label_counts=(
                    LabelCount.create(label_ref=f"label:{split}", count=1),
                ),
            )
        )
    return tuple(rows)


def _split_manifest() -> R4SplitManifest:
    refs = _episode_refs()
    return R4SplitManifest.create(
        source_set_ref=_source_set_ref(refs),
        generator_source_revision="1" * 40,
        authority_generation="authority_generation:r4-reviewed",
        config_ref="r4_partition_config_v1:reviewed",
        partition_evidence_ref="r4_partition_evidence_v3:reviewed",
        partition_sufficiency_ref="r4_partition_sufficiency_v1:reviewed",
        classes=_split_classes(),
    )


def _class_counts() -> tuple[ClassCount, ...]:
    return tuple(
        ClassCount.create(split=split, source_count=1, component_count=1)
        for split in SPLITS
    )


def _dimension_rows() -> tuple[DimensionSufficiency, ...]:
    rows = [
        DimensionSufficiency.create(
            dimension_ref=dimension_ref,
            split=split,
            source_support=4,
            feasible_component_support=4,
            observed_support=1,
            minimum=1,
            maximum=4,
            passed=True,
            infeasibility_reason="",
        )
        for dimension_ref in ("dimension:language", "dimension:topology")
        for split in SPLITS
    ]
    return tuple(rows)


def _sufficiency() -> R4PartitionSufficiencyReceipt:
    return R4PartitionSufficiencyReceipt.create(
        passed=True,
        class_counts=_class_counts(),
        dimension_rows=_dimension_rows(),
    )


def _capability() -> R4ClassCapability:
    return R4ClassCapability.create(
        purpose="training",
        split="train",
        payload_path="artifacts/r4/splits/train.jsonl",
        payload_sha256="a" * 64,
        payload_count=1,
        source_set_ref=_source_set_ref(_episode_refs()),
        split_manifest_ref=_split_manifest().manifest_ref,
    )


def _authorization(capability: R4ClassCapability) -> R4ClassAuthorization:
    artifact_graph_ref = artifact_graph_ref_for(
        source_set_ref=capability.source_set_ref,
        config_ref="r4_partition_config_v1:reviewed",
        partition_evidence_ref="r4_partition_evidence_v3:reviewed",
        partition_sufficiency_ref="r4_partition_sufficiency_v1:reviewed",
        split_manifest_ref=capability.split_manifest_ref,
        capability_ref=capability.capability_ref,
    )
    return R4ClassAuthorization.create(
        purpose=capability.purpose,
        expected_capability_ref=capability.capability_ref,
        expected_capability_sha256=hashlib.sha256(
            capability.to_json_bytes()
        ).hexdigest(),
        artifact_graph_ref=artifact_graph_ref,
        generator_source_revision="1" * 40,
        authority_generation="authority_generation:r4-reviewed",
    )


def _partition_config() -> R4PartitionConfig:
    minima = tuple(
        DimensionMinimum.create(
            dimension_ref=dimension_ref,
            split=split,
            minimum=1,
        )
        for dimension_ref in ("dimension:language", "dimension:topology")
        for split in SPLITS
    )
    maxima = tuple(
        DimensionMaximum.create(
            dimension_ref=dimension_ref,
            split=split,
            maximum=4,
        )
        for dimension_ref in ("dimension:language", "dimension:topology")
        for split in SPLITS
    )
    return R4PartitionConfig.create(
        seed=1701,
        target_weights=tuple(
            SplitWeight.create(split=split, weight=weight)
            for split, weight in zip(SPLITS, (60, 15, 15, 10), strict=True)
        ),
        bounds=PartitionBounds.reviewed(),
        objective=PartitionObjective.reviewed(),
        minima=minima,
        maxima=maxima,
        feasibility_basis_ref="r4_partition_feasibility_basis_v1:reviewed",
        minima_witness_ref="r4_partition_minima_witness_v1:reviewed",
    )


def test_partition_contracts_are_factory_only_and_canonical() -> None:
    factory_only = (
        LeakageHyperedge,
        StratificationLabel,
        GlobalPartitionComponent,
        PartitionEvidence,
        LabelCount,
        SplitClassRecord,
        R4SplitManifest,
        ClassCount,
        DimensionSufficiency,
        R4PartitionSufficiencyReceipt,
        R4ClassCapability,
        R4ClassAuthorization,
        SplitWeight,
        PartitionBounds,
        PartitionObjective,
        DimensionMinimum,
        DimensionMaximum,
        R4PartitionConfig,
    )
    for contract in factory_only:
        with pytest.raises(TypeError, match="use "):
            contract()

    evidence = _partition_evidence()
    manifest = _split_manifest()
    sufficiency = _sufficiency()
    capability = _capability()
    authorization = _authorization(capability)
    config = _partition_config()

    round_trips = (
        (PartitionEvidence, evidence),
        (R4SplitManifest, manifest),
        (R4PartitionSufficiencyReceipt, sufficiency),
        (R4ClassCapability, capability),
        (R4ClassAuthorization, authorization),
        (R4PartitionConfig, config),
    )
    for contract, value in round_trips:
        raw = value.to_json_bytes()
        assert raw.endswith(b"\n")
        assert contract.from_json_bytes(raw) == value
        assert value.to_json_bytes() == raw


def test_component_identity_binds_source_and_partition_abi_not_assignment() -> None:
    refs = ("episode:0001", "episode:0002")
    source = _source_set_ref(refs)
    hyperedges = ("r4_leakage_hyperedge_v3:shared",)
    train = GlobalPartitionComponent.create(
        source_set_ref=source,
        member_refs=refs,
        hyperedge_refs=hyperedges,
        split="train",
    )
    selection = GlobalPartitionComponent.create(
        source_set_ref=source,
        member_refs=refs,
        hyperedge_refs=hyperedges,
        split="selection",
    )
    changed_source = GlobalPartitionComponent.create(
        source_set_ref="r4_partition_source_v3:other",
        member_refs=refs,
        hyperedge_refs=hyperedges,
        split="train",
    )

    assert train.component_ref == selection.component_ref
    assert train.component_ref != changed_source.component_ref
    assert train.partition_abi_version == 3


def test_leakage_and_label_records_reject_noncanonical_members() -> None:
    with pytest.raises(ValueError, match="strictly sorted"):
        LeakageHyperedge.create(
            axis="general",
            key_namespace="scenario",
            key_ref="scenario:shared",
            member_refs=("episode:0002", "episode:0001"),
        )
    with pytest.raises(ValueError, match="unique"):
        StratificationLabel.create(
            namespace="language:en",
            member_refs=("episode:0001", "episode:0001"),
        )
    with pytest.raises(ValueError, match="at least two"):
        LeakageHyperedge.create(
            axis="general",
            key_namespace="scenario",
            key_ref="scenario:shared",
            member_refs=("episode:0001",),
        )
    with pytest.raises(ValueError, match="unsupported leakage axis"):
        LeakageHyperedge.create(
            axis="language",
            key_namespace="coarse_language",
            key_ref="language:en",
            member_refs=("episode:0001", "episode:0002"),
        )
    with pytest.raises(ValueError, match="content/reference"):
        StratificationLabel.create(
            namespace="language:en",
            member_refs=("not-a-ref",),
        )


def test_partition_evidence_reconstructs_global_coverage_and_rejects_tamper() -> None:
    evidence = _partition_evidence()
    assert evidence.source_set_ref == _source_set_ref(_episode_refs())
    assert set().union(*(set(row.member_refs) for row in evidence.components)) == set(
        _episode_refs()
    )

    changed_split = deepcopy(evidence.as_dict())
    changed_split["components"][0]["split"] = "frozen_test"
    with pytest.raises(ValueError, match="non-canonical PartitionEvidence"):
        PartitionEvidence.from_dict(changed_split)

    crossing_edge = deepcopy(evidence.as_dict())
    first_component_members = crossing_edge["components"][0]["member_refs"]
    second_component_members = crossing_edge["components"][1]["member_refs"]
    crossing_edge["hyperedges"][0]["member_refs"] = sorted(
        (first_component_members[0], second_component_members[0])
    )
    with pytest.raises(ValueError):
        PartitionEvidence.from_dict(crossing_edge)

    unknown = deepcopy(evidence.as_dict())
    unknown["legacy_axis_manifests"] = []
    with pytest.raises(ValueError, match="fields mismatch"):
        PartitionEvidence.from_dict(unknown)


def test_split_manifest_is_exact_four_class_boundary() -> None:
    manifest = _split_manifest()
    assert tuple(row.split for row in manifest.classes) == SPLITS
    assert sum(row.payload_count for row in manifest.classes) == 4
    assert R4SplitManifest.from_json_bytes(manifest.to_json_bytes()) == manifest

    for field, replacement in (
        ("generator_source_revision", "2" * 40),
        ("authority_generation", "authority_generation:changed"),
        ("config_ref", "r4_partition_config_v1:changed"),
    ):
        corrupted = deepcopy(manifest.as_dict())
        corrupted[field] = replacement
        with pytest.raises(ValueError, match="non-canonical R4SplitManifest"):
            R4SplitManifest.from_dict(corrupted)

    reordered = deepcopy(manifest.as_dict())
    reordered["classes"][0], reordered["classes"][1] = (
        reordered["classes"][1],
        reordered["classes"][0],
    )
    with pytest.raises(ValueError, match="canonical order"):
        R4SplitManifest.from_dict(reordered)

    missing = deepcopy(manifest.as_dict())
    missing["classes"].pop()
    with pytest.raises(ValueError, match="exactly four"):
        R4SplitManifest.from_dict(missing)


def test_split_manifest_rejects_unsafe_paths_and_invalid_purpose_pairing() -> None:
    common = {
        "split": "train",
        "purpose": "training",
        "payload_sha256": "a" * 64,
        "payload_count": 1,
        "member_refs": ("episode:0001",),
        "component_refs": ("component:train",),
        "label_counts": (),
    }
    for path in (
        "../train.jsonl",
        "C:/artifacts/r4/splits/train.jsonl",
        "artifacts\\r4\\splits\\train.jsonl",
        "artifacts/r4/splits/CON",
        "/artifacts/r4/splits/train.jsonl",
    ):
        with pytest.raises(ValueError, match="payload_path"):
            SplitClassRecord.create(payload_path=path, **common)

    with pytest.raises(ValueError, match="purpose/split"):
        SplitClassRecord.create(
            payload_path="artifacts/r4/splits/train.jsonl",
            **{**common, "purpose": "evaluation"},
        )
    with pytest.raises(ValueError, match="payload_count"):
        SplitClassRecord.create(
            payload_path="artifacts/r4/splits/train.jsonl",
            **{**common, "payload_count": 2},
        )


def test_partition_sufficiency_is_non_vacuous_complete_and_reconstructible() -> None:
    receipt = _sufficiency()
    assert receipt.passed is True
    assert tuple(row.split for row in receipt.class_counts) == SPLITS
    assert R4PartitionSufficiencyReceipt.from_json_bytes(receipt.to_json_bytes()) == receipt

    with pytest.raises(ValueError, match="outside the admitted bound"):
        ClassCount.create(split="train", source_count=0, component_count=1)
    with pytest.raises(ValueError, match="outside the admitted bound"):
        DimensionSufficiency.create(
            dimension_ref="dimension:language",
            split="train",
            source_support=0,
            feasible_component_support=1,
            observed_support=0,
            minimum=1,
            maximum=1,
            passed=False,
            infeasibility_reason="zero source support",
        )
    with pytest.raises(ValueError, match="passed flag"):
        DimensionSufficiency.create(
            dimension_ref="dimension:language",
            split="train",
            source_support=4,
            feasible_component_support=4,
            observed_support=0,
            minimum=1,
            maximum=4,
            passed=True,
            infeasibility_reason="",
        )
    with pytest.raises(ValueError, match="every canonical split"):
        R4PartitionSufficiencyReceipt.create(
            passed=True,
            class_counts=_class_counts(),
            dimension_rows=_dimension_rows()[:-1],
        )
    oversized_counts = tuple(
        ClassCount.create(split=split, source_count=4096, component_count=4096)
        for split in SPLITS
    )
    with pytest.raises(ValueError, match="aggregate class counts"):
        R4PartitionSufficiencyReceipt.create(
            passed=True,
            class_counts=oversized_counts,
            dimension_rows=_dimension_rows(),
        )


def test_class_capability_requires_independent_authorization_trust() -> None:
    capability = _capability()
    authorization = _authorization(capability)
    authorization_sha = hashlib.sha256(authorization.to_json_bytes()).hexdigest()

    assert (
        authenticate_class_capability(
            capability,
            authorization,
            expected_authorization_ref=authorization.authorization_ref,
            expected_authorization_sha256=authorization_sha,
        )
        is capability
    )

    with pytest.raises(ValueError, match="authorization ref"):
        authenticate_class_capability(
            capability,
            authorization,
            expected_authorization_ref="r4_class_authorization_v1:replaced",
            expected_authorization_sha256=authorization_sha,
        )
    with pytest.raises(ValueError, match="authorization SHA"):
        authenticate_class_capability(
            capability,
            authorization,
            expected_authorization_ref=authorization.authorization_ref,
            expected_authorization_sha256="0" * 64,
        )

    replacement = R4ClassCapability.create(
        purpose="training",
        split="train",
        payload_path="artifacts/r4/splits/train.jsonl",
        payload_sha256="b" * 64,
        payload_count=1,
        source_set_ref=capability.source_set_ref,
        split_manifest_ref=capability.split_manifest_ref,
    )
    replacement_authorization = _authorization(replacement)
    with pytest.raises(ValueError, match="authorization ref"):
        authenticate_class_capability(
            replacement,
            replacement_authorization,
            expected_authorization_ref=authorization.authorization_ref,
            expected_authorization_sha256=authorization_sha,
        )


def test_class_authorization_discloses_no_sibling_or_build_receipt_fields() -> None:
    capability = _capability()
    authorization = _authorization(capability)
    assert set(authorization.as_dict()) == {
        "abi_version",
        "authorization_ref",
        "purpose",
        "expected_capability_ref",
        "expected_capability_sha256",
        "artifact_graph_ref",
        "generator_source_revision",
        "authority_generation",
    }
    assert set(capability.as_dict()) == {
        "abi_version",
        "capability_ref",
        "purpose",
        "split",
        "payload_path",
        "payload_ref",
        "payload_sha256",
        "payload_count",
        "source_set_ref",
        "split_manifest_ref",
    }
    forbidden = (
        "sibling",
        "selection_path",
        "calibration_path",
        "frozen_test_path",
        "build_receipt",
        "authorization_sha256",
    )
    wire_text = json.dumps(
        {"capability": capability.as_dict(), "authorization": authorization.as_dict()},
        sort_keys=True,
    )
    assert all(term not in wire_text for term in forbidden)

    for field in ("sibling_paths", "build_receipt_ref"):
        corrupted = deepcopy(authorization.as_dict())
        corrupted[field] = [] if field == "sibling_paths" else "r4_build_v4:forged"
        with pytest.raises(ValueError, match="fields mismatch"):
            R4ClassAuthorization.from_dict(corrupted)


def test_partition_config_binds_reviewed_integer_formulas_and_acyclic_basis() -> None:
    config = _partition_config()
    assert tuple((row.split, row.weight) for row in config.target_weights) == (
        ("train", 60),
        ("selection", 15),
        ("calibration", 15),
        ("frozen_test", 10),
    )
    assert config.objective.rare_label_formula == RARE_LABEL_FORMULA
    assert config.objective.size_deviation_formula == SIZE_DEVIATION_FORMULA
    assert config.objective.label_deviation_formula == LABEL_DEVIATION_FORMULA
    assert config.objective.bound_violation_formula == BOUND_VIOLATION_FORMULA
    assert "feasibility_receipt" not in config.as_dict()
    assert "split_manifest" not in config.as_dict()
    assert "build_receipt" not in config.as_dict()

    mutation_cases = (
        ("seed", config.seed + 1),
        ("feasibility_basis_ref", "r4_partition_feasibility_basis_v1:changed"),
        ("minima_witness_ref", "r4_partition_minima_witness_v1:changed"),
    )
    for field, replacement in mutation_cases:
        corrupted = deepcopy(config.as_dict())
        corrupted[field] = replacement
        with pytest.raises(ValueError, match="non-canonical R4PartitionConfig"):
            R4PartitionConfig.from_dict(corrupted)

    changed_weight = deepcopy(config.as_dict())
    changed_weight["target_weights"][0]["weight"] = 59
    with pytest.raises(ValueError, match="60/15/15/10"):
        R4PartitionConfig.from_dict(changed_weight)

    changed_formula = deepcopy(config.as_dict())
    changed_formula["objective"]["size_deviation_formula"] += " + 1"
    with pytest.raises(ValueError, match="reviewed integer formulas"):
        R4PartitionConfig.from_dict(changed_formula)

    changed_bound = deepcopy(config.as_dict())
    changed_bound["bounds"]["max_solver_states"] += 1
    with pytest.raises(ValueError, match="reviewed hard bounds"):
        R4PartitionConfig.from_dict(changed_bound)

    incomplete = deepcopy(config.as_dict())
    incomplete["minima"].pop()
    incomplete["maxima"].pop()
    incomplete.pop("config_ref")
    incomplete["config_ref"] = "r4_partition_config_v1:forged"
    with pytest.raises(ValueError, match="every canonical split"):
        R4PartitionConfig.from_dict(incomplete)


def test_contract_decoders_reject_unknown_missing_nonfinite_and_noncanonical_json() -> None:
    capability = _capability()
    value = capability.as_dict()

    unknown = deepcopy(value)
    unknown["test_payload_path"] = "artifacts/r4/splits/frozen_test.jsonl"
    with pytest.raises(ValueError, match="fields mismatch"):
        R4ClassCapability.from_dict(unknown)

    missing = deepcopy(value)
    missing.pop("source_set_ref")
    with pytest.raises(ValueError, match="fields mismatch"):
        R4ClassCapability.from_dict(missing)

    raw = capability.to_json_bytes()
    duplicate = raw.replace(
        b'{"abi_version":1,',
        b'{"abi_version":1,"abi_version":1,',
        1,
    )
    with pytest.raises(ValueError, match="duplicate JSON key"):
        R4ClassCapability.from_json_bytes(duplicate)

    nonfinite = raw.replace(b'"payload_count":1', b'"payload_count":NaN', 1)
    with pytest.raises(ValueError, match="non-finite JSON"):
        R4ClassCapability.from_json_bytes(nonfinite)

    pretty = json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    with pytest.raises(ValueError, match="not canonical"):
        R4ClassCapability.from_json_bytes(pretty)

    with pytest.raises(ValueError, match="strict UTF-8"):
        R4ClassCapability.from_json_bytes(raw[:-1] + b"\xff")


def test_r4_partition_schemas_are_strict_draft_2020_12() -> None:
    instances = {
        "r4_partition_evidence.schema.json": _partition_evidence().as_dict(),
        "r4_split_manifest.schema.json": _split_manifest().as_dict(),
        "r4_partition_sufficiency.schema.json": _sufficiency().as_dict(),
        "r4_class_capability.schema.json": _capability().as_dict(),
        "r4_class_authorization.schema.json": _authorization(_capability()).as_dict(),
        "r4_partition_config.schema.json": _partition_config().as_dict(),
    }

    def assert_strict_objects(value: object) -> None:
        if type(value) is dict:
            if value.get("type") == "object":
                assert value.get("additionalProperties") is False
            for child in value.values():
                assert_strict_objects(child)
        elif type(value) is list:
            for child in value:
                assert_strict_objects(child)

    for path in SCHEMA_PATHS:
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert_strict_objects(schema)
        Draft202012Validator(schema).validate(instances[path.name])


def test_partition_abi_registry_declares_hard_cut_without_activation_claim() -> None:
    text = (ROOT / "docs/ABI_REGISTRY.md").read_text(encoding="utf-8")
    required_rows = (
        "| Partition Evidence ABI | **3** |",
        "| R4 Split Manifest ABI | **1** |",
        "| R4 Partition Sufficiency ABI | **1** |",
        "| R4 Class Capability ABI | **1** |",
        "| R4 Class Authorization ABI | **1** |",
        "| Partition Config ABI | **1** |",
        "| R4 Build Receipt ABI | **4** |",
    )
    assert all(row in text for row in required_rows)
    assert "Partition Axis Manifest ABI 2 and Training Allowlist ABI 2 are retired" in text
    assert "registered target; generation and activation remain pending" in text
    assert "R4 Build Receipt ABI | **3**" not in text
