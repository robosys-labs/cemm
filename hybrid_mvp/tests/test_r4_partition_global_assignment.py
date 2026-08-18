from __future__ import annotations

import json
from pathlib import Path

from cemm_authoritative_hybrid.r4_episodes import AuthenticEpisode
from cemm_authoritative_hybrid.r4_mutations import SemanticMutation
from cemm_authoritative_hybrid.r4_partitions import GlobalLeakagePartitioner, normalized_surface_key

ROOT = Path(__file__).parents[1]
__cemm_test_inventory__ = {'tests/test_r4_partition_global_assignment.py::test_real_graph_reconstructs_all_axes_without_coarse_language_collapse': {'activation_phase': 'R4',
                                                                                                                          'assertion_ref': 'assertion:r4-global-graph-reconstructs-seven-exact-axes',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'R4-Partition-Corrective-Task-4',
                                                                                                                          'owner_ref': 'mutation-partition',
                                                                                                                          'source_ast_sha256': 'a32db19c2a5fa91afc277bfe42baef6bd7e2f2018a96588e69bc3f40847fe509'},
 'tests/test_r4_partition_global_assignment.py::test_synthetic_giant_component_fails_four_class_feasibility': {'activation_phase': 'R4',
                                                                                                               'assertion_ref': 'assertion:r4-giant-component-fails-four-class-feasibility',
                                                                                                               'diagnostic_role': 'owner',
                                                                                                               'introduced_by_task': 'R4-Partition-Corrective-Task-4',
                                                                                                               'owner_ref': 'mutation-partition',
                                                                                                               'source_ast_sha256': 'f3a2d7496ee394918043f3059ab0ab145da59e071881be1ee919516b719a1ac9'}}

def _real():
    episodes = tuple(AuthenticEpisode.from_dict(json.loads(line)) for line in (ROOT / "artifacts/r4/episodes.jsonl").read_text("utf-8").splitlines())
    mutations = tuple(SemanticMutation.from_dict(json.loads(line)) for line in (ROOT / "artifacts/r4/mutations.jsonl").read_text("utf-8").splitlines())
    return episodes, mutations

def test_real_graph_reconstructs_all_axes_without_coarse_language_collapse() -> None:
    episodes, mutations = _real()
    graph = GlobalLeakagePartitioner().build_graph(episodes, mutations=mutations)
    assert len(episodes) == 400
    assert len(graph.components) == 84
    assert max(map(lambda row: len(row.member_refs), graph.components)) == 248
    assert tuple(sorted({row.axis for row in graph.hyperedges})) == ("dialogue", "general", "lexical", "mutation", "realization", "semantic_target", "topology")
    assert not any(row.key_namespace == "language" and row.key_ref == "en" for row in graph.hyperedges)
    assert normalized_surface_key("Hello", "en") == normalized_surface_key(" hello ", "en")
    assert normalized_surface_key("hello", "en") != normalized_surface_key("hello", "fr")

def _synthetic(index: int) -> dict:
    return {"episode_ref": f"episode:synthetic-{index}", "generator_lineage_refs": [], "expanded_case": {"scenario_ref": "scenario:one-giant-component", "case_ref": f"case:synthetic-{index}", "trajectory_ref": f"trajectory:synthetic-{index}", "lineage_refs": [], "surface": f"synthetic {index}", "language": "en"}, "expected_contract": {"expected_expressions": [], "expected_response": {}}, "observed_cycle": {}}

def test_synthetic_giant_component_fails_four_class_feasibility() -> None:
    episodes = tuple(_synthetic(i) for i in range(8))
    graph = GlobalLeakagePartitioner().build_graph(episodes)
    assert len(graph.components) == 1
    _, result = GlobalLeakagePartitioner().analyze_feasibility(episodes)
    assert not result.four_nonempty_possible
    assert result.assignment_witness == ()
