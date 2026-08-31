"""Authentic R4 build-environment execution owners."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

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
from cemm_authoritative_hybrid.r4_mutation_compiler import ReviewedMutationCompiler
from cemm_authoritative_hybrid.r4_mutations import (
    MutationBoundaryResult,
    MutationExecutionRequest,
    MutationExecutor,
)
from cemm_authoritative_hybrid.r4_pipeline import load_reviewed_scenarios
from cemm_authoritative_hybrid.r4_supervision import MutationContract

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


def _invalid_role_mutation(case):
    payload = case.as_dict()
    path = (
        "contract",
        "expected_expressions",
        0,
        "applications",
        0,
        "roles",
        0,
        "role_ref",
    )
    before = payload["contract"]["expected_expressions"][0]["applications"][0][
        "roles"
    ][0]["role_ref"]
    contract = MutationContract.create(
        mutation_family_ref="mutation_family:invalid_role",
        source_case_ref=case.case_ref,
        scope="contract",
        changed_dimension_ref="mutation_dimension:invalid_role",
        selector_kind="json_path",
        changed_path=path,
        operation="replace",
        expected_before=before,
        replacement_after="not-a-role",
        applicability_ref="mutation_applicability:semantic_expression",
        expected_earliest_owner="expected-contract-compiler",
        expected_status="rejected",
        expected_error_code="invalid_role_ref",
        disposition="reject",
        effect_kind="no_effect",
        expected_effect_ref=None,
        review_refs=("source_review:0123456789abcdef01234567",),
    )
    return ReviewedMutationCompiler().compile(case=case, contract=contract)


def test_environment_factory_returns_exact_committed_owners(tmp_path: Path) -> None:
    environment = build_environment(ROOT, tmp_path, source_revision="1" * 40)

    assert environment["source_revision"] == "1" * 40
    assert callable(environment["runtime_factory"])
    assert hasattr(environment["restart_executor"], "execute_restart_case")
    assert hasattr(environment["mutation_owner"], "execute_mutation")


def test_build_cli_requires_explicit_source_revision(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/build_r4_artifacts.py",
            "--environment",
            "src/cemm_authoritative_hybrid/r4_environment.py",
            "--output",
            str(tmp_path / "build"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "the following arguments are required: --source-revision" in completed.stderr


def test_build_cli_keeps_execution_state_out_of_artifact_output() -> None:
    source = (ROOT / "scripts" / "build_r4_artifacts.py").read_text(encoding="utf-8")
    assert 'TemporaryDirectory(prefix="cemm-r4-build-state-")' in source
    assert "Path(execution_state.name)" in source
    assert "args.output.resolve(),\n            source_revision" not in source


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
    mutations = (_invalid_role_mutation(case),)
    owner = AuthenticMutationOwner(ROOT, tmp_path)

    observations = MutationExecutor(owner).execute(mutations)
    request = MutationExecutionRequest.create(mutations[0])
    first = owner.execute_mutation(request)

    assert type(first) is MutationBoundaryResult
    assert first.artifact_ref != mutations[0].mutation_ref
    assert first.error_code == "invalid_role_ref"
    assert {row.dimension for row in mutations} == {"invalid_role"}
    assert all(row.matched_expectation for row in observations)


__cemm_test_inventory__ = {'tests/test_r4_environment.py::test_environment_factory_returns_exact_committed_owners': {'activation_phase': 'R4',
                                                                                           'assertion_ref': 'assertion:r4-environment-factory-returns-authentic-owners',
                                                                                           'diagnostic_role': 'owner',
                                                                                           'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                           'owner_ref': 'mutation-partition',
                                                                                           'source_ast_sha256': '50cad1812768fd684a6ccdc805bb84ae85e7919e9bb914b88e0e702a963cfea7'},
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
                                                                                                     'source_ast_sha256': '4c5659ae3781511a11d4e18300fbf8d4fa0dbab5314e940d41bd004b81c957dc'},
 'tests/test_r4_environment.py::test_build_cli_requires_explicit_source_revision': {'activation_phase': 'R4',
                                                                                    'assertion_ref': 'assertion:r4-build-cli-requires-source-revision',
                                                                                    'diagnostic_role': 'owner',
                                                                                    'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                    'owner_ref': 'mutation-partition',
                                                                                    'source_ast_sha256': 'fef5756285cb4bc34fdaf3c1d2869c55b7a0f3ea7b8b3b78929522d56eb00bf6'},
 'tests/test_r4_environment.py::test_build_cli_keeps_execution_state_out_of_artifact_output': {'activation_phase': 'R4',
                                                                                               'assertion_ref': 'assertion:r4-build-cli-isolates-execution-state',
                                                                                               'diagnostic_role': 'owner',
                                                                                               'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                               'owner_ref': 'mutation-partition',
                                                                                               'source_ast_sha256': '0708c5d3d7e8c7a7104b51e76d53c5dc3326f4b6b31a9aef94072a901d0aa431'}}
