from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.r4_episodes import AuthenticEpisode
from cemm_authoritative_hybrid.r4_mutations import SemanticMutation
from cemm_authoritative_hybrid.r4_partition_config import R4PartitionConfig
from cemm_authoritative_hybrid.r4_partition_contracts import GlobalPartitionComponent, PartitionEvidence, SPLITS
from cemm_authoritative_hybrid.r4_partitions import GlobalLeakagePartitioner, normalized_surface_key
from cemm_authoritative_hybrid.r4_partition_verify import PartitionVerificationError, verify_partition_assignment

ROOT = Path(__file__).parents[1]

__cemm_test_inventory__ = {'tests/test_r4_partition_global_assignment.py::test_real_graph_reconstructs_all_axes_without_coarse_language_collapse': {'activation_phase': 'R4',
                                                                                                                          'assertion_ref': 'assertion:r4-global-graph-reconstructs-seven-exact-axes',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'R4-Partition-Corrective-Task-4',
                                                                                                                          'owner_ref': 'mutation-partition',
                                                                                                                          'source_ast_sha256': 'dec8eb0a750ead763e86a89900ec0b0d23e1889fbdb6401ae5a23e69f241894f'},
 'tests/test_r4_partition_global_assignment.py::test_real_allocator_is_whole_component_deterministic_and_independently_verified': {'activation_phase': 'R4',
                                                                                                                                   'assertion_ref': 'assertion:r4-global-assignment-is-deterministic-and-independently-verified',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'R4-Partition-Corrective-Task-5',
                                                                                                                                   'owner_ref': 'mutation-partition',
                                                                                                                                   'source_ast_sha256': '90aa8a47c5a8be9bed2db614d68de3a10a63e3ce133354d6b149b3103601e2fa'},
 'tests/test_r4_partition_global_assignment.py::test_independent_verifier_rejects_split_tamper': {'activation_phase': 'R4',
                                                                                                  'assertion_ref': 'assertion:r4-independent-verifier-rejects-split-tamper',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'R4-Partition-Corrective-Task-5',
                                                                                                  'owner_ref': 'mutation-partition',
                                                                                                  'source_ast_sha256': 'e1787b22db9957fd373f09c25618eda748eeffa79aacad48f1e1ccc10371e334'},
 'tests/test_r4_partition_global_assignment.py::test_synthetic_giant_component_fails_four_class_feasibility': {'activation_phase': 'R4',
                                                                                                               'assertion_ref': 'assertion:r4-giant-component-fails-four-class-feasibility',
                                                                                                               'diagnostic_role': 'owner',
                                                                                                               'introduced_by_task': 'R4-Partition-Corrective-Task-5',
                                                                                                               'owner_ref': 'mutation-partition',
                                                                                                               'source_ast_sha256': 'e29dae679d51a1f04ac32419f8cf7a9218bbb085227f0b89158d093789dd4e56'}}


def _real():
    episodes = tuple(AuthenticEpisode.from_dict(json.loads(line)) for line in (ROOT / "artifacts/r4/episodes.jsonl").read_text("utf-8").splitlines())
    mutations = tuple(SemanticMutation.from_dict(json.loads(line)) for line in (ROOT / "artifacts/r4/mutations.jsonl").read_text("utf-8").splitlines())
    config = R4PartitionConfig.from_json_bytes((ROOT / "configs/r4_partitions.json").read_bytes())
    return episodes, mutations, config


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
