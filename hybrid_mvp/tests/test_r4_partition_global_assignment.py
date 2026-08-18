from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.r4_episodes import AuthenticEpisode
from cemm_authoritative_hybrid.r4_mutations import SemanticMutation
from cemm_authoritative_hybrid.r4_partition_config import RATIO_DENOMINATOR, R4PartitionConfig
from cemm_authoritative_hybrid.r4_partition_contracts import (
    PURPOSE_BY_SPLIT,
    SPLITS,
    GlobalPartitionComponent,
    LabelCount,
    PartitionEvidence,
    R4SplitManifest,
    SplitClassRecord,
    canonical_json_bytes,
)
from cemm_authoritative_hybrid.r4_partitions import GlobalLeakagePartitioner, normalized_surface_key
from cemm_authoritative_hybrid.r4_partition_verify import PartitionVerificationError, verify_partition_assignment

ROOT = Path(__file__).parents[1]

__cemm_test_inventory__ = {
    'tests/test_r4_partition_global_assignment.py::test_real_graph_reconstructs_all_axes_without_coarse_language_collapse': {
        'activation_phase': 'R4',
        'assertion_ref': 'assertion:r4-global-graph-reconstructs-seven-exact-axes',
        'diagnostic_role': 'owner',
        'introduced_by_task': 'R4-Partition-Corrective-Task-4',
        'owner_ref': 'mutation-partition',
        'source_ast_sha256': 'dec8eb0a750ead763e86a89900ec0b0d23e1889fbdb6401ae5a23e69f241894f',
    },
    'tests/test_r4_partition_global_assignment.py::test_real_allocator_is_whole_component_deterministic_and_independently_verified': {
        'activation_phase': 'R4',
        'assertion_ref': 'assertion:r4-global-assignment-is-deterministic-and-independently-verified',
        'diagnostic_role': 'owner',
        'introduced_by_task': 'R4-Partition-Corrective-Task-5',
        'owner_ref': 'mutation-partition',
        'source_ast_sha256': '90aa8a47c5a8be9bed2db614d68de3a10a63e3ce133354d6b149b3103601e2fa',
    },
    'tests/test_r4_partition_global_assignment.py::test_independent_verifier_rejects_split_tamper': {
        'activation_phase': 'R4',
        'assertion_ref': 'assertion:r4-independent-verifier-rejects-split-tamper',
        'diagnostic_role': 'owner',
        'introduced_by_task': 'R4-Partition-Corrective-Task-5',
        'owner_ref': 'mutation-partition',
        'source_ast_sha256': 'e1787b22db9957fd373f09c25618eda748eeffa79aacad48f1e1ccc10371e334',
    },
    'tests/test_r4_partition_global_assignment.py::test_synthetic_giant_component_fails_four_class_feasibility': {
        'activation_phase': 'R4',
        'assertion_ref': 'assertion:r4-giant-component-fails-four-class-feasibility',
        'diagnostic_role': 'owner',
        'introduced_by_task': 'R4-Partition-Corrective-Task-5',
        'owner_ref': 'mutation-partition',
        'source_ast_sha256': 'e29dae679d51a1f04ac32419f8cf7a9218bbb085227f0b89158d093789dd4e56',
    },
    **{
        f'tests/test_r4_partition_global_assignment.py::test_no_leakage_hyperedge_crosses_classes[{case_id}]': {
            'activation_phase': 'R4',
            'assertion_ref': 'assertion:partition-leakage-no-lineage-component-crosses-partitions',
            'diagnostic_role': 'owner',
            'introduced_by_task': 'R4-Partition-Corrective-Task-7',
            'owner_ref': 'mutation-partition',
            'source_ast_sha256': '0000000000000000000000000000000000000000000000000000000000000000',
            'supersedes_node_id': f'tests/test_partition_leakage.py::test_no_lineage_component_crosses_partitions[{case_id}]',
        }
        for case_id in (
            'adversarial_mutation',
            'authority_target',
            'dialogue',
            'entity',
            'graph_topology',
            'lexical_value',
            'normalized_text',
            'template',
        )
    },
    'tests/test_r4_partition_global_assignment.py::test_split_manifest_counts_match_assignment': {
        'activation_phase': 'R4',
        'assertion_ref': 'assertion:partition-leakage-partition-manifest-has-correct-counts',
        'diagnostic_role': 'owner',
        'introduced_by_task': 'R4-Partition-Corrective-Task-7',
        'owner_ref': 'mutation-partition',
        'source_ast_sha256': '0000000000000000000000000000000000000000000000000000000000000000',
        'supersedes_node_id': 'tests/test_partition_leakage.py::test_partition_manifest_has_correct_counts',
    },
    'tests/test_r4_partition_global_assignment.py::test_split_payload_counts_match_manifest': {
        'activation_phase': 'R4',
        'assertion_ref': 'assertion:partition-leakage-partition-counts-match-files',
        'diagnostic_role': 'owner',
        'introduced_by_task': 'R4-Partition-Corrective-Task-7',
        'owner_ref': 'mutation-partition',
        'source_ast_sha256': '0000000000000000000000000000000000000000000000000000000000000000',
        'supersedes_node_id': 'tests/test_partition_leakage.py::test_partition_counts_match_files',
    },
    'tests/test_r4_partition_global_assignment.py::test_split_payload_hashes_match_manifest': {
        'activation_phase': 'R4',
        'assertion_ref': 'assertion:partition-leakage-partition-manifest-hashes-match-files',
        'diagnostic_role': 'owner',
        'introduced_by_task': 'R4-Partition-Corrective-Task-7',
        'owner_ref': 'mutation-partition',
        'source_ast_sha256': '0000000000000000000000000000000000000000000000000000000000000000',
        'supersedes_node_id': 'tests/test_partition_leakage.py::test_partition_manifest_hashes_match_files',
    },
    'tests/test_r4_partition_global_assignment.py::test_every_episode_appears_in_exactly_one_class': {
        'activation_phase': 'R4',
        'assertion_ref': 'assertion:partition-leakage-every-episode-apars-in-exactly-one-partition',
        'diagnostic_role': 'owner',
        'introduced_by_task': 'R4-Partition-Corrective-Task-7',
        'owner_ref': 'mutation-partition',
        'source_ast_sha256': '0000000000000000000000000000000000000000000000000000000000000000',
        'supersedes_node_id': 'tests/test_partition_leakage.py::test_every_episode_apars_in_exactly_one_partition',
    },
    'tests/test_r4_partition_global_assignment.py::test_class_sizes_satisfy_reviewed_integer_objective': {
        'activation_phase': 'R4',
        'assertion_ref': 'assertion:partition-leakage-partition-ratios-are-approximately-balanced',
        'diagnostic_role': 'owner',
        'introduced_by_task': 'R4-Partition-Corrective-Task-7',
        'owner_ref': 'mutation-partition',
        'source_ast_sha256': '0000000000000000000000000000000000000000000000000000000000000000',
        'supersedes_node_id': 'tests/test_partition_leakage.py::test_partition_ratios_are_approximately_balanced',
    },
}


def _real():
    episodes = tuple(AuthenticEpisode.from_dict(json.loads(line)) for line in (ROOT / "artifacts/r4/episodes.jsonl").read_text("utf-8").splitlines())
    mutations = tuple(SemanticMutation.from_dict(json.loads(line)) for line in (ROOT / "artifacts/r4/mutations.jsonl").read_text("utf-8").splitlines())
    config = R4PartitionConfig.from_json_bytes((ROOT / "configs/r4_partitions.json").read_bytes())
    return episodes, mutations, config


@pytest.fixture(scope="module")
def assigned():
    episodes, mutations, config = _real()
    result = GlobalLeakagePartitioner().assign(episodes, config=config, mutations=mutations)
    return episodes, mutations, config, result


@pytest.fixture(scope="module")
def in_memory_manifest(assigned):
    episodes, _, config, result = assigned
    episode_by_ref = {row.episode_ref: row for row in episodes}
    payloads: dict[str, bytes] = {}
    classes: list[SplitClassRecord] = []
    for split in SPLITS:
        components = tuple(row for row in result.evidence.components if row.split == split)
        member_refs = tuple(sorted(member for row in components for member in row.member_refs))
        raw = b"".join(canonical_json_bytes(episode_by_ref[ref].as_dict()) for ref in member_refs)
        payloads[split] = raw
        labels = tuple(
            LabelCount.create(
                label_ref=label.label_ref,
                count=len(set(label.member_refs).intersection(member_refs)),
            )
            for label in result.evidence.labels
            if set(label.member_refs).intersection(member_refs)
        )
        classes.append(
            SplitClassRecord.create(
                split=split,
                purpose=PURPOSE_BY_SPLIT[split],
                payload_path=f"artifacts/r4/splits/{split}.jsonl",
                payload_sha256=hashlib.sha256(raw).hexdigest(),
                payload_count=len(member_refs),
                member_refs=member_refs,
                component_refs=tuple(sorted(row.component_ref for row in components)),
                label_counts=labels,
            )
        )
    manifest = R4SplitManifest.create(
        source_set_ref=result.evidence.source_set_ref,
        generator_source_revision="a" * 40,
        authority_generation="authority:test",
        config_ref=config.config_ref,
        partition_evidence_ref=result.evidence.evidence_ref,
        partition_sufficiency_ref="r4_partition_sufficiency_v1:test",
        classes=tuple(classes),
    )
    return manifest, payloads


def test_real_graph_reconstructs_all_axes_without_coarse_language_collapse() -> None:
    episodes, mutations, _ = _real()
    graph = GlobalLeakagePartitioner().build_graph(episodes, mutations=mutations)
    assert len(episodes) == 400
    assert len(graph.components) == 84
    assert max(map(lambda row: len(row.member_refs), graph.components)) == 248
    assert tuple(sorted({row.axis for row in graph.hyperedges})) == (
        "dialogue", "general", "lexical", "mutation", "realization", "semantic_target", "topology"
    )
    assert not any(row.key_namespace == "language" and row.key_ref == "en" for row in graph.hyperedges)
    assert normalized_surface_key("Hello", "en") == normalized_surface_key(" hello ", "en")
    assert normalized_surface_key("hello", "en") != normalized_surface_key("hello", "fr")


def test_real_allocator_is_whole_component_deterministic_and_independently_verified() -> None:
    episodes, mutations, config = _real()
    owner = GlobalLeakagePartitioner()
    first = owner.assign(episodes, config=config, mutations=mutations)
    second = owner.assign(reversed(episodes), config=config, mutations=reversed(mutations))
    assert first.evidence.as_dict() == second.evidence.as_dict()
    assert first.assignments == second.assignments
    counts = {split: 0 for split in SPLITS}
    for component in first.evidence.components:
        counts[component.split] += len(component.member_refs)
    assert sum(counts.values()) == 400
    assert all(counts.values())
    assert len({member for row in first.evidence.components for member in row.member_refs}) == 400
    assert first.sparse_counter_updates < 4 * (131_072 + 131_072)
    assert verify_partition_assignment(episodes, mutations=mutations, config=config, evidence=first.evidence) == first.objective


def test_independent_verifier_rejects_split_tamper() -> None:
    episodes, mutations, config = _real()
    result = GlobalLeakagePartitioner().assign(episodes, config=config, mutations=mutations)
    original = result.evidence.components[0]
    other = next(split for split in SPLITS if split != original.split)
    replacement = GlobalPartitionComponent.create(
        source_set_ref=result.evidence.source_set_ref,
        member_refs=original.member_refs,
        hyperedge_refs=original.hyperedge_refs,
        split=other,
    )
    components = tuple(sorted((replacement, *result.evidence.components[1:]), key=lambda row: row.component_ref))
    tampered = PartitionEvidence.create(
        source_set_ref=result.evidence.source_set_ref,
        config_ref=result.evidence.config_ref,
        hyperedges=result.evidence.hyperedges,
        labels=result.evidence.labels,
        components=components,
    )
    with pytest.raises(PartitionVerificationError):
        verify_partition_assignment(episodes, mutations=mutations, config=config, evidence=tampered)


_LINEAGE_AXIS_CASES = (
    ("adversarial_mutation", "mutation"),
    ("authority_target", "semantic_target"),
    ("dialogue", "dialogue"),
    ("entity", "semantic_target"),
    ("graph_topology", "topology"),
    ("lexical_value", "lexical"),
    ("normalized_text", "lexical"),
    ("template", "lexical"),
)


@pytest.mark.parametrize(
    ("lineage_case", "axis"),
    _LINEAGE_AXIS_CASES,
    ids=tuple(row[0] for row in _LINEAGE_AXIS_CASES),
)
def test_no_leakage_hyperedge_crosses_classes(assigned, lineage_case: str, axis: str) -> None:
    _, _, _, result = assigned
    owner = {
        member: component.split
        for component in result.evidence.components
        for member in component.member_refs
    }
    edges = tuple(row for row in result.evidence.hyperedges if row.axis == axis)
    assert lineage_case
    assert edges
    for edge in edges:
        assert len({owner[member] for member in edge.member_refs}) == 1


def test_split_manifest_counts_match_assignment(assigned, in_memory_manifest) -> None:
    episodes, _, _, result = assigned
    manifest, _ = in_memory_manifest
    expected = {split: 0 for split in SPLITS}
    for component in result.evidence.components:
        expected[component.split] += len(component.member_refs)
    observed = {row.split: row.payload_count for row in manifest.classes}
    assert observed == expected
    assert sum(observed.values()) == len(episodes) == 400


def test_split_payload_counts_match_manifest(in_memory_manifest) -> None:
    manifest, payloads = in_memory_manifest
    classes = {row.split: row for row in manifest.classes}
    for split in SPLITS:
        row_count = len([line for line in payloads[split].splitlines() if line])
        assert row_count == classes[split].payload_count


def test_split_payload_hashes_match_manifest(in_memory_manifest) -> None:
    manifest, payloads = in_memory_manifest
    classes = {row.split: row for row in manifest.classes}
    for split in SPLITS:
        assert hashlib.sha256(payloads[split]).hexdigest() == classes[split].payload_sha256


def test_every_episode_appears_in_exactly_one_class(assigned, in_memory_manifest) -> None:
    episodes, _, _, _ = assigned
    manifest, _ = in_memory_manifest
    refs = [member for row in manifest.classes for member in row.member_refs]
    expected = sorted(row.episode_ref for row in episodes)
    assert len(refs) == len(set(refs)) == len(expected)
    assert sorted(refs) == expected


def test_class_sizes_satisfy_reviewed_integer_objective(assigned, in_memory_manifest) -> None:
    episodes, _, config, result = assigned
    manifest, _ = in_memory_manifest
    counts = {row.split: row.payload_count for row in manifest.classes}
    weights = {row.split: row.weight for row in config.target_weights}
    size_deviation = sum(
        abs(RATIO_DENOMINATOR * counts[split] - len(episodes) * weights[split])
        for split in SPLITS
    )
    assert tuple((row.split, row.weight) for row in config.target_weights) == (
        ("train", 60),
        ("selection", 15),
        ("calibration", 15),
        ("frozen_test", 10),
    )
    assert size_deviation == result.objective[0]
    assert result.objective[2] == 0


def _synthetic(index: int) -> dict:
    return {
        "episode_ref": f"episode:synthetic-{index}",
        "generator_lineage_refs": [],
        "expanded_case": {
            "scenario_ref": "scenario:one-giant-component",
            "case_ref": f"case:synthetic-{index}",
            "trajectory_ref": f"trajectory:synthetic-{index}",
            "lineage_refs": [],
            "surface": f"synthetic {index}",
            "language": "en",
        },
        "expected_contract": {"expected_expressions": [], "expected_response": {}},
        "observed_cycle": {},
    }


def test_synthetic_giant_component_fails_four_class_feasibility() -> None:
    graph = GlobalLeakagePartitioner().build_graph(tuple(_synthetic(i) for i in range(8)))
    assert len(graph.components) == 1
    _, result = GlobalLeakagePartitioner().analyze_feasibility(tuple(_synthetic(i) for i in range(8)))
    assert not result.four_nonempty_possible
    assert result.assignment_witness == ()
