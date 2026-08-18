"""R4 mutation contracts and current mutation-evidence successors."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from cemm_authoritative_hybrid.authority import AtomRecord
from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.gaps import GapKind
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.r4_contracts import (
    ExpectedCycleContractCompiler,
    ReviewedScenario,
)
from cemm_authoritative_hybrid.r4_expansion import CaseExpander
from cemm_authoritative_hybrid.r4_mutations import (
    MUTATION_OBSERVATION_ABI_VERSION,
    SEMANTIC_MUTATION_ABI_VERSION,
    MutationBoundaryResult,
    MutationExecutor,
    MutationGenerator,
    MutationObservation,
    SemanticMutation,
)
from cemm_authoritative_hybrid.r4_partitions import (
    AXES,
    PartitionAxisManifest,
    PartitionComponent,
    TrainingAllowlist,
    GlobalLeakagePartitioner,
)

ROOT = Path(__file__).parents[1]

__cemm_test_inventory__ = {'tests/test_r4_mutations_and_partitions.py::test_mutations_change_one_declared_dimension_and_use_owner_labels': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:r4-mutations-change-one-declared-dimension-and-use-owner-labels',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'R4-Complete',
                                                                                                                  'owner_ref': 'mutation-partition',
                                                                                                                  'source_ast_sha256': '360785939d775f46bab66809510bb38ca2f5d0204e5ac7ff39ce23bf6fc2c3f0'},
 'tests/test_r4_mutations_and_partitions.py::test_partition_axis_manifest_is_exact_and_training_allowlist_has_no_test_refs': {'activation_phase': 'R4',
                                                                                                                              'assertion_ref': 'assertion:r4-partition-axis-manifest-is-exact-and-training-allowlist-has-no-test-refs',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'R4-Complete',
                                                                                                                              'owner_ref': 'mutation-partition',
                                                                                                                              'source_ast_sha256': 'ab80a84f1033f5b98d45c985921f5c6be4f4e71d04c1039d342b854c2f731343'},
 'tests/test_r4_mutations_and_partitions.py::test_global_partition_successor_exposes_four_class_assignment_owner': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:r4-global-partition-successor-exposes-four-class-assignment-owner',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'R4-Partition-Corrective-Task-5',
                                                                                                                    'owner_ref': 'mutation-partition',
                                                                                                                    'source_ast_sha256': '4340ae030e1b6801d6fa1b1f082bf4d90f795bb2cd8a4bcec497e520b9e4e3ee'},
 'tests/test_r4_mutations_and_partitions.py::test_r4_gap_episodes_cover_all_18_kinds': {'activation_phase': 'R4',
                                                                                        'assertion_ref': 'assertion:gap-episode-coverage-all-18-gap-kinds-are-covered',
                                                                                        'diagnostic_role': 'owner',
                                                                                        'introduced_by_task': 'R4-Partition-Corrective-Task-7',
                                                                                        'owner_ref': 'mutation-partition',
                                                                                        'source_ast_sha256': '307a37e7ffb946124baba1bb1cca9ac737f7b98b97f2bb05b84a0b49ccd39509',
                                                                                        'supersedes_node_id': 'tests/test_gap_episode_coverage.py::test_all_18_gap_kinds_are_covered'},
 'tests/test_r4_mutations_and_partitions.py::test_r4_gap_kinds_have_positive_and_near_miss': {'activation_phase': 'R4',
                                                                                              'assertion_ref': 'assertion:gap-episode-coverage-every-gap-kind-has-positive-and-near-miss',
                                                                                              'diagnostic_role': 'owner',
                                                                                              'introduced_by_task': 'R4-Partition-Corrective-Task-7',
                                                                                              'owner_ref': 'mutation-partition',
                                                                                              'source_ast_sha256': 'e40241872d451795e469febaf8765b77cabe637044ec47ce62d912831c64d144',
                                                                                              'supersedes_node_id': 'tests/test_gap_episode_coverage.py::test_every_gap_kind_has_positive_and_near_miss'},
 'tests/test_r4_mutations_and_partitions.py::test_r4_hard_negatives_exist': {'activation_phase': 'R4',
                                                                             'assertion_ref': 'assertion:hard-negatives-hard-negatives-exist',
                                                                             'diagnostic_role': 'owner',
                                                                             'introduced_by_task': 'R4-Partition-Corrective-Task-7',
                                                                             'owner_ref': 'mutation-partition',
                                                                             'source_ast_sha256': '831949b5c220299f8d140e56e55c36fbe71673f6b29e60658c30a8e8454e3f88',
                                                                             'supersedes_node_id': 'tests/test_hard_negatives.py::test_hard_negatives_exist'},
 'tests/test_r4_mutations_and_partitions.py::test_r4_hard_negatives_mutate_one_dimension': {'activation_phase': 'R4',
                                                                                            'assertion_ref': 'assertion:hard-negatives-hard-negatives-mutate-one-dimension',
                                                                                            'diagnostic_role': 'owner',
                                                                                            'introduced_by_task': 'R4-Partition-Corrective-Task-7',
                                                                                            'owner_ref': 'mutation-partition',
                                                                                            'source_ast_sha256': '104883238d8c1999898bfd6ea8394e512083e482c86bd5ec3cad533ad139f31a',
                                                                                            'supersedes_node_id': 'tests/test_hard_negatives.py::test_hard_negatives_mutate_one_dimension'},
 'tests/test_r4_mutations_and_partitions.py::test_r4_hard_negatives_retain_parent_lineage': {'activation_phase': 'R4',
                                                                                             'assertion_ref': 'assertion:hard-negatives-hard-negatives-retain-parent-lineage',
                                                                                             'diagnostic_role': 'owner',
                                                                                             'introduced_by_task': 'R4-Partition-Corrective-Task-7',
                                                                                             'owner_ref': 'mutation-partition',
                                                                                             'source_ast_sha256': 'ab8616a0731f3dc986b408454fe31cdf18ef41057dbbbaf7b052db2e19d86ce6',
                                                                                             'supersedes_node_id': 'tests/test_hard_negatives.py::test_hard_negatives_retain_parent_lineage'},
 'tests/test_r4_mutations_and_partitions.py::test_r4_hard_negatives_have_verifier_error_labels': {'activation_phase': 'R4',
                                                                                                  'assertion_ref': 'assertion:hard-negatives-hard-negatives-have-verifier-error-labels',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'R4-Partition-Corrective-Task-7',
                                                                                                  'owner_ref': 'mutation-partition',
                                                                                                  'source_ast_sha256': 'fc31523aed66c69cef633eb92bbdf4d60ef678c43522eaeff558c592eeb919df',
                                                                                                  'supersedes_node_id': 'tests/test_hard_negatives.py::test_hard_negatives_have_verifier_error_labels'},
 'tests/test_r4_mutations_and_partitions.py::test_r4_hard_negatives_have_valid_labels': {'activation_phase': 'R4',
                                                                                         'assertion_ref': 'assertion:hard-negatives-hard-negatives-have-valid-labels',
                                                                                         'diagnostic_role': 'owner',
                                                                                         'introduced_by_task': 'R4-Partition-Corrective-Task-7',
                                                                                         'owner_ref': 'mutation-partition',
                                                                                         'source_ast_sha256': '6d9f97c9d4cc9d58b2a30f569d2951123109470d96989725efdcc59e49c45de2',
                                                                                         'supersedes_node_id': 'tests/test_hard_negatives.py::test_hard_negatives_have_valid_labels'},
 'tests/test_r4_mutations_and_partitions.py::test_r4_hard_negatives_have_gap_kind': {'activation_phase': 'R4',
                                                                                     'assertion_ref': 'assertion:hard-negatives-hard-negatives-have-gap-kind',
                                                                                     'diagnostic_role': 'owner',
                                                                                     'introduced_by_task': 'R4-Partition-Corrective-Task-7',
                                                                                     'owner_ref': 'mutation-partition',
                                                                                     'source_ast_sha256': 'ef1d018773f6170c892626132a86ee8d2db5c94d8bb28ff2cfcfd7ea1ead1eeb',
                                                                                     'supersedes_node_id': 'tests/test_hard_negatives.py::test_hard_negatives_have_gap_kind'},
 'tests/test_r4_mutations_and_partitions.py::test_r4_proposer_miss_and_authority_gap_cases_exist': {'activation_phase': 'R4',
                                                                                                    'assertion_ref': 'assertion:hard-negatives-proposer-miss-and-authority-gap-cases-exist',
                                                                                                    'diagnostic_role': 'owner',
                                                                                                    'introduced_by_task': 'R4-Partition-Corrective-Task-7',
                                                                                                    'owner_ref': 'mutation-partition',
                                                                                                    'source_ast_sha256': 'b942b555d3b44c65b1051feb9129963502245515d2b71eac1a50c099b5853abb',
                                                                                                    'supersedes_node_id': 'tests/test_hard_negatives.py::test_proposer_miss_and_authority_gap_cases_exist'},
 'tests/test_r4_mutations_and_partitions.py::test_r4_hard_negatives_have_unique_refs': {'activation_phase': 'R4',
                                                                                        'assertion_ref': 'assertion:hard-negatives-hard-negatives-have-unique-refs',
                                                                                        'diagnostic_role': 'owner',
                                                                                        'introduced_by_task': 'R4-Partition-Corrective-Task-7',
                                                                                        'owner_ref': 'mutation-partition',
                                                                                        'source_ast_sha256': 'b0e8988ee90471dabc676c114b3ec8cb8d7ebbcb9e7446afd6c61f2e69704229',
                                                                                        'supersedes_node_id': 'tests/test_hard_negatives.py::test_hard_negatives_have_unique_refs'},
 'tests/test_r4_mutations_and_partitions.py::test_r4_hard_negatives_use_active_abi': {'activation_phase': 'R4',
                                                                                      'assertion_ref': 'assertion:hard-negatives-hard-negatives-have-valid-abi-version',
                                                                                      'diagnostic_role': 'owner',
                                                                                      'introduced_by_task': 'R4-Partition-Corrective-Task-7',
                                                                                      'owner_ref': 'mutation-partition',
                                                                                      'source_ast_sha256': 'd5c2f1c2e7d9238e12298d1cbabb5faba09825c18f379fc4e0c5b9e0cecd06b4',
                                                                                      'supersedes_node_id': 'tests/test_hard_negatives.py::test_hard_negatives_have_valid_abi_version'}}


class _Authority:
    generation = "authority:test"
    atoms = {
        ref: AtomRecord(ref=ref, kind=kind)
        for ref, kind in {
            "entity:a": "entity",
            "rel:likes": "relation_type",
            "entity:b": "entity",
        }.items()
    }
    event_signatures = {}
    value_dimensions = {}
    designations = None
    capabilities = {}
    permissions = ()
    adapters = ()
    operator_roles = {}
    rules = {}


def _case_contract():
    scenario = ReviewedScenario.from_dict(
        {
            "scenario_ref": "scenario:mutation",
            "review_status": "reviewed",
            "competency_category": "relation",
            "semantic_assertions": [
                {
                    "kind": "relation",
                    "subject": "entity:a",
                    "relation": "rel:likes",
                    "object": "entity:b",
                }
            ],
            "surface_examples": ["a likes b"],
            "expected_gap_kind": None,
            "metadata": {},
        }
    )
    compiler = ExpectedCycleContractCompiler(
        _Authority(), abi_registry_ref="abi:test"
    )
    expanded = CaseExpander(compiler).expand(
        scenario,
        revision_pin=RevisionPin("authority:test", 0, 0, 0, 0, "model:test"),
        environments=(
            {
                "situation_constraints": {
                    "permission_refs": ["perm:test"],
                    "adapter_refs": ["adapter:test"],
                    "evidence_policy_refs": ["policy:test"],
                }
            },
        ),
    )
    return expanded[0]


class _MatchingOwner:
    def execute_mutation(self, mutation):
        return MutationBoundaryResult(
            earliest_owner=mutation.expected_earliest_owner,
            status=mutation.expected_status,
            error_code=mutation.expected_error_code,
            artifact_ref=f"observed:{mutation.mutation_ref}",
        )


def _jsonl(path: Path) -> tuple[dict, ...]:
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)


def _mutation_evidence() -> tuple[tuple[SemanticMutation, ...], tuple[MutationObservation, ...]]:
    mutations = tuple(
        SemanticMutation.from_dict(row) for row in _jsonl(ROOT / "artifacts/r4/mutations.jsonl")
    )
    observations = tuple(
        MutationObservation.from_dict(row)
        for row in _jsonl(ROOT / "artifacts/r4/mutation_observations.jsonl")
    )
    return mutations, observations


def _gap_evidence_counts() -> tuple[Counter[str], Counter[str], set[str]]:
    scenarios = _jsonl(ROOT / "data/scenarios/use_cases.jsonl")
    scenario_kind = {
        row["scenario_ref"]: row["expected_gap_kind"]
        for row in scenarios
        if row.get("expected_gap_kind") is not None
    }
    cases = _jsonl(ROOT / "artifacts/r4/expanded_cases.jsonl")
    case_kind = {
        row["case_ref"]: scenario_kind[row["scenario_ref"]]
        for row in cases
        if row["scenario_ref"] in scenario_kind
    }
    mutations, _ = _mutation_evidence()
    positive = Counter(case_kind.values())
    near_miss = Counter(
        case_kind[mutation.parent_case_ref]
        for mutation in mutations
        if mutation.parent_case_ref in case_kind
    )
    return positive, near_miss, set(scenario_kind.values())


def test_mutations_change_one_declared_dimension_and_use_owner_labels() -> None:
    case = _case_contract()
    mutations = MutationGenerator().generate(case)
    assert len(mutations) == 8
    assert len({row.dimension for row in mutations}) == 8
    observations = MutationExecutor(_MatchingOwner()).execute(mutations)
    assert all(row.matched_expectation for row in observations)


def test_partition_axis_manifest_is_exact_and_training_allowlist_has_no_test_refs() -> None:
    source_refs = ("episode:a", "episode:b")
    source_set_ref = stable_ref("r4_partition_source_v2", list(source_refs))
    components = (
        PartitionComponent.create(
            protected_value_refs=("surface_family",),
            member_refs=("episode:a",),
            split="train",
        ),
        PartitionComponent.create(
            protected_value_refs=("surface_family",),
            member_refs=("episode:b",),
            split="test",
        ),
    )
    manifest = PartitionAxisManifest.create(
        axis="lexical",
        source_set_ref=source_set_ref,
        seed=1701,
        protected_keys=("surface_family",),
        source_refs=source_refs,
        components=components,
    )
    large_component = PartitionComponent.create(
        protected_value_refs=tuple(f"protected:{index}" for index in range(513)),
        member_refs=("episode:large",),
        split="train",
    )
    assert len(large_component.protected_value_refs) == 513
    assert PartitionAxisManifest.from_dict(manifest.as_dict()) == manifest
    all_manifests = tuple(
        PartitionAxisManifest.create(
            axis=axis,
            source_set_ref=source_set_ref,
            seed=1701,
            protected_keys=("surface_family",),
            source_refs=source_refs,
            components=components,
        )
        for axis in AXES
    )
    allowlist = TrainingAllowlist.from_manifests(all_manifests)
    assert "episode:b" not in allowlist.train_refs
    assert set(AXES) == {
        "general", "lexical", "semantic_target", "topology",
        "dialogue", "mutation", "realization",
    }


def test_global_partition_successor_exposes_four_class_assignment_owner() -> None:
    owner = GlobalLeakagePartitioner()
    assert callable(owner.build_graph)
    assert callable(owner.analyze_feasibility)
    assert callable(owner.assign)


def test_r4_gap_episodes_cover_all_18_kinds() -> None:
    positive, near_miss, reviewed = _gap_evidence_counts()
    expected = {kind.value for kind in GapKind}
    assert reviewed == expected
    assert set(positive) == expected
    assert set(near_miss) == expected


def test_r4_gap_kinds_have_positive_and_near_miss() -> None:
    positive, near_miss, _ = _gap_evidence_counts()
    for kind in GapKind:
        assert positive[kind.value] > 0
        assert near_miss[kind.value] > 0
        assert near_miss[kind.value] >= positive[kind.value]


def test_r4_hard_negatives_exist() -> None:
    mutations, observations = _mutation_evidence()
    assert mutations
    assert len(observations) == len(mutations)


def test_r4_hard_negatives_mutate_one_dimension() -> None:
    mutations, _ = _mutation_evidence()
    for mutation in mutations:
        assert mutation.dimension
        assert mutation.changed_path
        assert mutation.before != mutation.after


def test_r4_hard_negatives_retain_parent_lineage() -> None:
    mutations, _ = _mutation_evidence()
    for mutation in mutations:
        assert mutation.lineage_refs[0] == mutation.parent_case_ref
        assert mutation.lineage_refs[1] == mutation.parent_contract_ref
        assert any(ref.startswith("mutation_family:") for ref in mutation.lineage_refs)
        assert mutation.review_refs


def test_r4_hard_negatives_have_verifier_error_labels() -> None:
    mutations, observations = _mutation_evidence()
    observed = {row.mutation_ref: row for row in observations}
    assert set(observed) == {row.mutation_ref for row in mutations}
    for mutation in mutations:
        row = observed[mutation.mutation_ref]
        assert row.actual_error_code == mutation.expected_error_code
        assert row.matched_expectation
        assert "neural_score" not in json.dumps(mutation.as_dict(), sort_keys=True)


def test_r4_hard_negatives_have_valid_labels() -> None:
    mutations, observations = _mutation_evidence()
    expected = {row.mutation_ref: row for row in mutations}
    for observation in observations:
        mutation = expected[observation.mutation_ref]
        assert observation.actual_earliest_owner == mutation.expected_earliest_owner
        assert observation.actual_status == mutation.expected_status
        assert observation.actual_error_code == mutation.expected_error_code
        assert observation.matched_expectation is True


def test_r4_hard_negatives_have_gap_kind() -> None:
    _, near_miss, reviewed = _gap_evidence_counts()
    expected = {kind.value for kind in GapKind}
    assert reviewed == expected
    assert {kind for kind, count in near_miss.items() if count > 0} == expected


def test_r4_proposer_miss_and_authority_gap_cases_exist() -> None:
    positive, near_miss, _ = _gap_evidence_counts()
    for kind in ("proposal", "authority"):
        assert positive[kind] > 0
        assert near_miss[kind] > 0


def test_r4_hard_negatives_have_unique_refs() -> None:
    mutations, observations = _mutation_evidence()
    mutation_refs = [row.mutation_ref for row in mutations]
    observation_refs = [row.observation_ref for row in observations]
    assert len(mutation_refs) == len(set(mutation_refs))
    assert len(observation_refs) == len(set(observation_refs))


def test_r4_hard_negatives_use_active_abi() -> None:
    mutations, observations = _mutation_evidence()
    assert SEMANTIC_MUTATION_ABI_VERSION == 2
    assert MUTATION_OBSERVATION_ABI_VERSION == 2
    assert all(row.abi_version == SEMANTIC_MUTATION_ABI_VERSION for row in mutations)
    assert all(row.abi_version == MUTATION_OBSERVATION_ABI_VERSION for row in observations)
