"""Authentic R4 build-environment execution owners."""
from __future__ import annotations

from pathlib import Path

from cemm_authoritative_hybrid.authority import AuthorityLinker
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.proposal import BootstrapProposer
from cemm_authoritative_hybrid.r3_cycle import CycleResult
from cemm_authoritative_hybrid.r4_contracts import ExpectedCycleContractCompiler
from cemm_authoritative_hybrid.r4_environment import (
    AuthenticMutationOwner,
    AuthenticRestartExecutor,
    admitted_source_for_phase,
    build_environment,
)
from cemm_authoritative_hybrid.r4_episodes import EpisodeExecutionResult
from cemm_authoritative_hybrid.r4_expansion import CaseExpander
from cemm_authoritative_hybrid.r4_mutations import (
    MutationBoundaryResult,
    MutationExecutor,
    MutationGenerator,
)
from cemm_authoritative_hybrid.r4_pipeline import load_reviewed_scenarios

ROOT = Path(__file__).parents[1]


def _cases_for(scenario_ref: str):
    authority = AuthorityLinker().link_path(
        ROOT / "data" / "authority" / "manifest.json"
    )
    pin = RevisionPin(
        authority.generation,
        0,
        0,
        0,
        0,
        BootstrapProposer(RuntimeConfig.release()).model_identity,
    )
    compiler = ExpectedCycleContractCompiler(
        authority, abi_registry_ref="abi:r4-environment-test"
    )
    scenario = next(
        row
        for row in load_reviewed_scenarios(
            ROOT / "data" / "scenarios" / "use_cases.jsonl"
        )
        if row.scenario_ref == scenario_ref
    )
    return CaseExpander(compiler).expand(
        scenario,
        revision_pin=pin,
        environments=scenario.metadata.get("environments", ({},)),
    )


def test_environment_factory_returns_exact_committed_owners(tmp_path: Path) -> None:
    environment = build_environment(ROOT, tmp_path)

    assert environment["source_revision"] == admitted_source_for_phase(ROOT, "R3")
    assert callable(environment["runtime_factory"])
    assert hasattr(environment["restart_executor"], "execute_restart_case")
    assert hasattr(environment["mutation_owner"], "execute_mutation")


def test_restart_executor_reopens_persistent_state_and_emits_cycle_result(
    tmp_path: Path,
) -> None:
    case = _cases_for("scenario:restart-0193")[0]
    owner = AuthenticRestartExecutor(ROOT, tmp_path)

    result = owner.execute_restart_case(case, session_ref="session:r4-restart")

    assert type(result) is EpisodeExecutionResult
    assert type(result.cycle) is CycleResult
    assert result.cycle.gap_receipt is not None


def test_mutation_owner_reports_observed_boundary_not_expected_labels(
    tmp_path: Path,
) -> None:
    case = _cases_for("scenario:reordered_constructions-0021")[0]
    mutations = MutationGenerator().generate(case)
    owner = AuthenticMutationOwner(ROOT, tmp_path)

    observations = MutationExecutor(owner).execute(mutations)
    first = owner.execute_mutation(mutations[0])

    assert type(first) is MutationBoundaryResult
    assert first.artifact_ref != mutations[0].mutation_ref
    assert first.error_code == "invalid_role_ref"
    assert {row.dimension for row in mutations} == {
        "invalid_role",
        "missing_predicate",
        "dangling_root",
        "source_untrusted",
        "stale_revision",
        "decision_action_mismatch",
    }
    assert all(row.matched_expectation for row in observations)


__cemm_test_inventory__ = {'tests/test_r4_environment.py::test_environment_factory_returns_exact_committed_owners': {'activation_phase': 'R4',
                                                                                           'assertion_ref': 'assertion:r4-environment-factory-returns-authentic-owners',
                                                                                           'diagnostic_role': 'owner',
                                                                                           'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                           'owner_ref': 'mutation-partition',
                                                                                           'source_ast_sha256': '6dc78e81abb47f3533a8fba2076f80187aebe0be9b0e9fb9c71bed1e613ddc76'},
 'tests/test_r4_environment.py::test_restart_executor_reopens_persistent_state_and_emits_cycle_result': {'activation_phase': 'R4',
                                                                                                         'assertion_ref': 'assertion:r4-restart-executor-reopens-persistent-state',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                         'owner_ref': 'mutation-partition',
                                                                                                         'source_ast_sha256': 'ed6a5b204aa5dba5a575f52396316d7d58b5e17905db383211945731d2790d28'},
 'tests/test_r4_environment.py::test_mutation_owner_reports_observed_boundary_not_expected_labels': {'activation_phase': 'R4',
                                                                                                     'assertion_ref': 'assertion:r4-mutation-owner-reports-observed-boundary',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                     'owner_ref': 'mutation-partition',
                                                                                                     'source_ast_sha256': '1d34ee412ea235df7da8bb1febf44d2e5e19bd413195318ec6ba80250d198b90'}}
