"""R4 mutation contracts and independent-axis manifests."""
from __future__ import annotations

from cemm_authoritative_hybrid.authority import AtomRecord
from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.r4_contracts import (
    ExpectedCycleContractCompiler,
    ReviewedScenario,
)
from cemm_authoritative_hybrid.r4_expansion import CaseExpander
from cemm_authoritative_hybrid.r4_mutations import (
    MutationBoundaryResult,
    MutationExecutor,
    MutationGenerator,
)
from cemm_authoritative_hybrid.r4_partitions import (
    AXES,
    PartitionAxisManifest,
    PartitionComponent,
    TrainingAllowlist,
    GlobalLeakagePartitioner,
)

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
                                                                                                                    'source_ast_sha256': '4340ae030e1b6801d6fa1b1f082bf4d90f795bb2cd8a4bcec497e520b9e4e3ee'}}



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
