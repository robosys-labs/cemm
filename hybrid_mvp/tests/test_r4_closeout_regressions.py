"""Behavioral R4 closeout regressions over the reviewed corpus.

These tests keep the independent expected-contract compiler total over the
reviewed scenario source without allowing runtime/proposer outputs to influence
expectations.
"""
from __future__ import annotations

import json
from pathlib import Path
import runpy

import pytest

from cemm_authoritative_hybrid.authority import AuthorityLinker
from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.expressions import GroundedReference, LiteralValue
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.proposal import BootstrapProposer
from cemm_authoritative_hybrid.r4_contracts import (
    ExpectedCycleContract,
    ExpectedCycleContractCompiler,
    ExpectedOutcomeKind,
    ExpressionRelation,
)
from cemm_authoritative_hybrid.r4_episodes import (
    AuthenticEpisodeBuilder,
    PublicRuntimeEpisodeOwner,
)
from cemm_authoritative_hybrid.r4_expansion import CaseExpander, ExpandedCase
from cemm_authoritative_hybrid.r4_pipeline import load_reviewed_scenarios

__cemm_test_inventory__ = {'tests/test_r4_closeout_regressions.py::test_every_reviewed_surface_compiles_and_round_trips_canonically': {'activation_phase': 'R4',
                                                                                                             'assertion_ref': 'assertion:r4-reviewed-corpus-compiles-canonically',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'R4-Closeout',
                                                                                                             'owner_ref': 'expected-contract',
                                                                                                             'source_ast_sha256': '41711e3c829cc11ddcbdab0180bf583217b1e75c75f023e9a569e40c3ddef351'},
 'tests/test_r4_closeout_regressions.py::test_external_sensor_provenance_is_not_mistaken_for_active_adapter_authority': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:r4-sensor-provenance-distinct-from-active-adapter-authority',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'R4-Closeout',
                                                                                                                         'owner_ref': 'expected-contract',
                                                                                                                         'source_ast_sha256': 'b7b3742e540d6bcb3bd10eb8a8630a68e59a1b1e0a79cf57569a57109aea798a'},
 'tests/test_r4_closeout_regressions.py::test_learning_reported_speech_and_effect_contracts_have_connected_compatible_topology': {'activation_phase': 'R4',
                                                                                                                                  'assertion_ref': 'assertion:r4-reviewed-contract-topology-is-connected-and-compatible',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'R4-Closeout',
                                                                                                                                  'owner_ref': 'expected-contract',
                                                                                                                                  'source_ast_sha256': '898793eb96c28d0012ba8494bf1d590b4a71e38c071ba006f6d5b6841b972936'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_designation_aliases_match_authentic_r3_cycles': {'activation_phase': 'R4',
                                                                                                        'assertion_ref': 'assertion:r4-designation-aliases-match-authentic-r3-cycles',
                                                                                                        'diagnostic_role': 'owner',
                                                                                                        'introduced_by_task': 'R4-Authentic-Designation-Tranche',
                                                                                                        'owner_ref': 'expected-contract',
                                                                                                        'source_ast_sha256': '4bb776ea398a9bfbe65bc2104c0d8073c644561156695d9df6d44b0a72f00c8d'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_greeting_and_farewell_surfaces_match_authentic_r3_cycles': {'activation_phase': 'R4',
                                                                                                                   'assertion_ref': 'assertion:r4-designation-events-match-authentic-r3-cycles',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'R4-Designation-Event-Tranche',
                                                                                                                   'owner_ref': 'expected-contract',
                                                                                                                   'source_ast_sha256': 'b57ad5da997eea7893fbf073e2a792009287c65c944b2dca09482da882264d8f'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_scenario_source_matches_deterministic_generator': {'activation_phase': 'R4',
                                                                                                          'assertion_ref': 'assertion:r4-reviewed-scenario-source-matches-generator',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R4-Designation-Event-Tranche',
                                                                                                          'owner_ref': 'expected-contract',
                                                                                                          'source_ast_sha256': 'ae45385ae4668fca755ff60a9ab2d4cc915eb8c5b87b84b21c525cab2bac7e54'},
 'tests/test_r4_closeout_regressions.py::test_singleton_polysemy_is_not_fabricated_as_ambiguity': {'activation_phase': 'R4',
                                                                                                   'assertion_ref': 'assertion:r4-singleton-polysemy-is-not-fabricated-ambiguity',
                                                                                                   'diagnostic_role': 'owner',
                                                                                                   'introduced_by_task': 'R4-Closeout',
                                                                                                   'owner_ref': 'expected-contract',
                                                                                                   'source_ast_sha256': 'e3537192e23a8bac5019da33aff92a490169470396b3cfa0b53a96dee40f7f88'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[designation-book]': {'activation_phase': 'R4',
                                                                                                                                   'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-designation-book',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                   'owner_ref': 'expected-contract',
                                                                                                                                   'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[designation-server]': {'activation_phase': 'R4',
                                                                                                                                     'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-designation-server',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                     'owner_ref': 'expected-contract',
                                                                                                                                     'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[definition-digital-agent]': {'activation_phase': 'R4',
                                                                                                                                           'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-definition-digital-agent',
                                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                                           'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                           'owner_ref': 'expected-contract',
                                                                                                                                           'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[definition-mother]': {'activation_phase': 'R4',
                                                                                                                                    'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-definition-mother',
                                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                                    'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                    'owner_ref': 'expected-contract',
                                                                                                                                    'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[designation-partner]': {'activation_phase': 'R4',
                                                                                                                                      'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-designation-partner',
                                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                                      'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                      'owner_ref': 'expected-contract',
                                                                                                                                      'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[designation-progenitor]': {'activation_phase': 'R4',
                                                                                                                                         'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-designation-progenitor',
                                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                                         'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                         'owner_ref': 'expected-contract',
                                                                                                                                         'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[designation-lamp]': {'activation_phase': 'R4',
                                                                                                                                   'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-designation-lamp',
                                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                                   'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                   'owner_ref': 'expected-contract',
                                                                                                                                   'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[relation-likes]': {'activation_phase': 'R4',
                                                                                                                                 'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-likes',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                 'owner_ref': 'expected-contract',
                                                                                                                                 'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[relation-owns]': {'activation_phase': 'R4',
                                                                                                                                'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-owns',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                'owner_ref': 'expected-contract',
                                                                                                                                'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[state-availability]': {'activation_phase': 'R4',
                                                                                                                                     'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-state-availability',
                                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                                     'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                     'owner_ref': 'expected-contract',
                                                                                                                                     'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[state-power]': {'activation_phase': 'R4',
                                                                                                                              'assertion_ref': 'assertion:r4-reviewed-nominal-state-relation-state-power',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                              'owner_ref': 'expected-contract',
                                                                                                                              'source_ast_sha256': 'b269543190623382e2e18ebe0a535f311aec409ad749053255bdc8e00ddaddeb'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_recursive_scope_families_match_authentic_cycles[negation]': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:r4-reviewed-recursive-scope-negation',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                    'owner_ref': 'expected-contract',
                                                                                                                    'source_ast_sha256': '747e09680af34cde50fdb5c8069b51429cd4807cd9b4b809a0c5e104566229cc'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_recursive_scope_families_match_authentic_cycles[modality]': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:r4-reviewed-recursive-scope-modality',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                    'owner_ref': 'expected-contract',
                                                                                                                    'source_ast_sha256': '747e09680af34cde50fdb5c8069b51429cd4807cd9b4b809a0c5e104566229cc'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_recursive_scope_families_match_authentic_cycles[reported-speech]': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:r4-reviewed-recursive-scope-reported-speech',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                           'owner_ref': 'expected-contract',
                                                                                                                           'source_ast_sha256': '747e09680af34cde50fdb5c8069b51429cd4807cd9b4b809a0c5e104566229cc'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_recursive_scope_families_match_authentic_cycles[learning-security]': {'activation_phase': 'R4',
                                                                                                                             'assertion_ref': 'assertion:r4-reviewed-recursive-scope-learning-security',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                             'owner_ref': 'expected-contract',
                                                                                                                             'source_ast_sha256': '747e09680af34cde50fdb5c8069b51429cd4807cd9b4b809a0c5e104566229cc'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_recursive_scope_families_match_authentic_cycles[recursive-family-proof]': {'activation_phase': 'R4',
                                                                                                                                  'assertion_ref': 'assertion:r4-reviewed-recursive-scope-recursive-family-proof',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                  'owner_ref': 'expected-contract',
                                                                                                                                  'source_ast_sha256': '747e09680af34cde50fdb5c8069b51429cd4807cd9b4b809a0c5e104566229cc'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_recursive_scope_families_match_authentic_cycles[participant-reference]': {'activation_phase': 'R4',
                                                                                                                                 'assertion_ref': 'assertion:r4-reviewed-recursive-scope-participant-reference',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                                 'owner_ref': 'expected-contract',
                                                                                                                                 'source_ast_sha256': '747e09680af34cde50fdb5c8069b51429cd4807cd9b4b809a0c5e104566229cc'},
 'tests/test_r4_closeout_regressions.py::test_reviewed_recursive_scope_families_match_authentic_cycles[contradiction]': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:r4-reviewed-recursive-scope-contradiction',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                                                         'owner_ref': 'expected-contract',
                                                                                                                         'source_ast_sha256': '747e09680af34cde50fdb5c8069b51429cd4807cd9b4b809a0c5e104566229cc'}}

ROOT = Path(__file__).parents[1]
SCENARIOS = ROOT / "data" / "scenarios" / "use_cases.jsonl"


def test_reviewed_scenario_source_matches_deterministic_generator() -> None:
    generate_all = runpy.run_path(
        str(ROOT / "scripts" / "generate_scenarios.py")
    )["generate_all"]
    generated = generate_all()
    expected = (
        "\n".join(
            json.dumps(
                row,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            for row in generated
        )
        + "\n"
    ).encode("utf-8")
    assert SCENARIOS.read_bytes() == expected


def _expanded_cases() -> tuple[ExpandedCase, ...]:
    authority = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")
    compiler = ExpectedCycleContractCompiler(authority, abi_registry_ref="abi:r4-closeout")
    pin = RevisionPin(authority.generation, 0, 0, 0, 0, "model:r4-closeout")
    expander = CaseExpander(compiler)
    rows: list[ExpandedCase] = []
    for scenario in load_reviewed_scenarios(SCENARIOS):
        environments = scenario.metadata.get("environments", ({},))
        rows.extend(expander.expand(scenario, revision_pin=pin, environments=environments))
    return tuple(rows)


def _authentic_episodes_for_scenario(
    scenario_ref: str,
    store_root: Path,
):
    authority = AuthorityLinker().link_path(
        ROOT / "data" / "authority" / "manifest.json"
    )
    model_identity = BootstrapProposer(RuntimeConfig.release()).model_identity
    pin = RevisionPin(authority.generation, 0, 0, 0, 0, model_identity)
    compiler = ExpectedCycleContractCompiler(
        authority,
        abi_registry_ref="abi:r4-nominal-state-relation-canary",
    )
    scenario = next(
        row
        for row in load_reviewed_scenarios(SCENARIOS)
        if row.scenario_ref == scenario_ref
    )
    cases = CaseExpander(compiler).expand(
        scenario,
        revision_pin=pin,
        environments=scenario.metadata.get("environments", ({},)),
    )
    runtimes = []

    def runtime_factory(_case: ExpandedCase):
        runtime = load_runtime(
            ROOT,
            profile="development",
            store_path=store_root / f"runtime-{len(runtimes):02d}",
        )
        runtimes.append(runtime)
        return runtime

    try:
        return AuthenticEpisodeBuilder(
            PublicRuntimeEpisodeOwner(runtime_factory)
        ).build_many(cases)
    finally:
        for runtime in reversed(runtimes):
            runtime.stores.close()


@pytest.mark.parametrize(
    "scenario_ref",
    (
        "scenario:designation_definition-0003",
        "scenario:designation_definition-0004",
        "scenario:designation_definition-0006",
        "scenario:designation_definition-0010",
        "scenario:designation_definition-0012",
        "scenario:designation_definition-0013",
        "scenario:designation_definition-0014",
        "scenario:reordered_constructions-0021",
        "scenario:reordered_constructions-0022",
        "scenario:temporal_state-0089",
        "scenario:temporal_state-0091",
    ),
    ids=(
        "designation-book",
        "designation-server",
        "definition-digital-agent",
        "definition-mother",
        "designation-partner",
        "designation-progenitor",
        "designation-lamp",
        "relation-likes",
        "relation-owns",
        "state-availability",
        "state-power",
    ),
)
def test_reviewed_nominal_state_relation_families_match_authentic_cycles(
    scenario_ref: str,
    tmp_path: Path,
) -> None:
    episodes = _authentic_episodes_for_scenario(scenario_ref, tmp_path)

    assert episodes
    assert all(row.comparison.passed for row in episodes)


@pytest.mark.parametrize(
    "scenario_ref",
    (
        "scenario:negation_scope-0047",
        "scenario:modality-0037",
        "scenario:reported_speech-0085",
        "scenario:learning_security-0119",
        "scenario:recursive_family_proof-0059",
        "scenario:participant_reference-0078",
        "scenario:contradiction-0143",
    ),
    ids=(
        "negation",
        "modality",
        "reported-speech",
        "learning-security",
        "recursive-family-proof",
        "participant-reference",
        "contradiction",
    ),
)
def test_reviewed_recursive_scope_families_match_authentic_cycles(
    scenario_ref: str,
    tmp_path: Path,
) -> None:
    episodes = _authentic_episodes_for_scenario(scenario_ref, tmp_path)

    assert episodes
    assert all(row.comparison.passed for row in episodes)
    if scenario_ref == "scenario:recursive_family_proof-0059":
        assert all(
            row.observed_cycle.evaluation is not None
            and row.observed_cycle.evaluation.query_results
            and "rule:mother-in-law-implies-partner-exists"
            in row.observed_cycle.evaluation.query_results[0].retrieval_refs
            for row in episodes
        )


def test_every_reviewed_surface_compiles_and_round_trips_canonically() -> None:
    scenarios = load_reviewed_scenarios(SCENARIOS)
    cases = _expanded_cases()
    assert len(scenarios) == 210
    assert len(cases) == sum(len(row.surface_examples) for row in scenarios)
    assert len(cases) == 400
    assert all(ExpandedCase.from_dict(row.as_dict()) == row for row in cases)
    assert all(
        ExpectedCycleContract.from_dict(row.contract.as_dict()) == row.contract
        for row in cases
    )


def test_reviewed_greeting_and_farewell_surfaces_match_authentic_r3_cycles(
    tmp_path: Path,
) -> None:
    authority = AuthorityLinker().link_path(
        ROOT / "data" / "authority" / "manifest.json"
    )
    model_identity = BootstrapProposer(RuntimeConfig.release()).model_identity
    pin = RevisionPin(authority.generation, 0, 0, 0, 0, model_identity)
    compiler = ExpectedCycleContractCompiler(
        authority, abi_registry_ref="abi:r4-designation-event"
    )
    expander = CaseExpander(compiler)
    selected = {
        row.scenario_ref: row
        for row in load_reviewed_scenarios(SCENARIOS)
        if row.scenario_ref
        in {
            "scenario:designation_definition-0001",
            "scenario:designation_definition-0002",
        }
    }
    assert set(selected) == {
        "scenario:designation_definition-0001",
        "scenario:designation_definition-0002",
    }
    expected_targets = {
        "scenario:designation_definition-0001": "event:greeting",
        "scenario:designation_definition-0002": "event:farewell",
    }
    for scenario_ref, scenario in selected.items():
        assert tuple(row.kind for row in scenario.assertions) == (
            "event",
            "mode",
            "decision",
            "no_effect",
            "response",
        )
        assert scenario.assertions[0].fields["event_type"] == expected_targets[scenario_ref]

    def runtime_factory(case: ExpandedCase):
        store_name = stable_ref("r4_designation_event_store", case.case_ref).split(
            ":", 1
        )[1]
        return load_runtime(
            ROOT,
            profile="development",
            store_path=tmp_path / f"{store_name}.db",
        )

    builder = AuthenticEpisodeBuilder(PublicRuntimeEpisodeOwner(runtime_factory))
    episodes = tuple(
        builder.build(case)
        for scenario in selected.values()
        for case in expander.expand(scenario, revision_pin=pin)
    )
    assert len(episodes) == 5
    assert all(row.comparison.passed for row in episodes)
    for episode in episodes:
        expected = episode.expected_contract.expected_expressions
        meaning = episode.observed_cycle.verification.selected_meaning
        candidate_ref = episode.observed_cycle.verification.selected_candidate_ref
        assert len(expected) == 1
        assert meaning is not None
        assert candidate_ref is not None
        candidate = episode.observed_cycle.proposal.candidate_by_ref(candidate_ref)
        assert tuple(
            action.action_type
            for action in candidate.program.actions
            if action.action_type == "select_designation"
        ) == ("select_designation",)
        expected_target = expected_targets[episode.expanded_case.scenario_ref]
        assert expected_target in candidate.provenance_refs
        assert expected[0].applications[0].operator == "op:event"
        assert meaning.expression.applications[0].operator == "op:event"
        assert (
            expected[0].applications[0].predicate_ref
            == meaning.expression.applications[0].predicate_ref
            == expected_target
        )


def test_reviewed_designation_aliases_match_authentic_r3_cycles(
    tmp_path: Path,
) -> None:
    authority = AuthorityLinker().link_path(
        ROOT / "data" / "authority" / "manifest.json"
    )
    model_identity = BootstrapProposer(RuntimeConfig.release()).model_identity
    pin = RevisionPin(authority.generation, 0, 0, 0, 0, model_identity)
    compiler = ExpectedCycleContractCompiler(
        authority, abi_registry_ref="abi:r4-authentic-designations"
    )
    expander = CaseExpander(compiler)
    scenarios = {
        row.scenario_ref: row
        for row in load_reviewed_scenarios(SCENARIOS)
        if len(row.assertions) == 1 and row.assertions[0].kind == "designates"
    }
    cases = tuple(
        case
        for scenario in scenarios.values()
        for case in expander.expand(scenario, revision_pin=pin)
    )
    linked: list[tuple[ExpandedCase, str, str]] = []
    unlinked: set[tuple[str, str]] = set()
    for case in cases:
        target = scenarios[case.scenario_ref].assertions[0].fields["target"]
        canonical_surface = authority.designations.canonical_surface_for_target(
            case.surface,
            target,
            case.language,
        )
        if canonical_surface is None:
            unlinked.add((case.surface, target))
        else:
            linked.append((case, target, canonical_surface))

    assert len(scenarios) == 10
    assert len(cases) == 22
    assert len(linked) == 19
    assert unlinked == {
        ("the book", "entity:book"),
        ("the server", "entity:server"),
        ("the lamp", "entity:lamp"),
    }
    assert authority.designations.for_surface("entity:book", "en") == ()
    assert authority.designations.for_surface(
        "CEMM", "en"
    ) == authority.designations.for_surface("cemm", "en")
    assert (
        authority.designations.canonical_surface_for_target(
            "cemm", "participant:system", "en"
        )
        == "CEMM"
    )

    episodes = []
    for index, (case, target, canonical_surface) in enumerate(linked):
        runtime = load_runtime(
            ROOT,
            profile="development",
            store_path=tmp_path / f"designation-{index:02d}.db",
        )
        try:
            episode = AuthenticEpisodeBuilder(
                PublicRuntimeEpisodeOwner(lambda _case, runtime=runtime: runtime)
            ).build(case)
        finally:
            runtime.stores.close()
        episodes.append((episode, target, canonical_surface))

    assert all(episode.comparison.passed for episode, _, _ in episodes)
    for episode, target, canonical_surface in episodes:
        expected = episode.expected_contract.expected_expressions
        meaning = episode.observed_cycle.verification.selected_meaning
        candidate_ref = episode.observed_cycle.verification.selected_candidate_ref
        assert len(expected) == 1
        assert meaning is not None
        assert candidate_ref is not None
        candidate = episode.observed_cycle.proposal.candidate_by_ref(candidate_ref)
        assert tuple(
            action.action_type
            for action in candidate.program.actions
            if action.action_type == "select_designation"
        ) == ("select_designation",)
        expected_application = expected[0].applications[0]
        observed_application = meaning.expression.applications[0]
        assert (
            expected_application.operator
            == observed_application.operator
            == "op:designation"
        )
        assert (
            expected_application.predicate_ref
            == observed_application.predicate_ref
            == target
        )
        expected_roles = {
            binding.role_ref: binding.filler
            for binding in expected_application.roles
        }
        observed_roles = {
            binding.role_ref: binding.filler
            for binding in observed_application.roles
        }
        assert expected_roles == observed_roles == {
            "role:surface": LiteralValue("string", canonical_surface),
            "role:target": GroundedReference(target),
        }


def test_singleton_polysemy_is_not_fabricated_as_ambiguity() -> None:
    scenarios = {row.scenario_ref: row for row in load_reviewed_scenarios(SCENARIOS)}
    polysemy = tuple(
        row
        for row in _expanded_cases()
        if any(assertion.kind == "polysemy" for assertion in scenarios[row.scenario_ref].assertions)
    )
    assert polysemy
    for row in polysemy:
        if len(row.contract.expected_expressions) == 1:
            assert row.contract.outcome_kind is not ExpectedOutcomeKind.AMBIGUITY
            assert row.contract.expression_relation is not ExpressionRelation.ANY


def test_external_sensor_provenance_is_not_mistaken_for_active_adapter_authority() -> None:
    cases = _expanded_cases()
    sensor_cases = tuple(
        row for row in cases
        if row.scenario_ref in {
            "scenario:reviewed_sensor_operation_evidence-0099",
            "scenario:reviewed_sensor_operation_evidence-0100",
            "scenario:reviewed_sensor_operation_evidence-0105",
        }
    )
    assert sensor_cases
    assert all(row.contract.outcome_kind is not ExpectedOutcomeKind.GAP for row in sensor_cases)

    explicit_adapter = tuple(row for row in cases if row.scenario_ref == "scenario:capability_policy_adapter_effect-0139")
    assert explicit_adapter
    for row in explicit_adapter:
        assert row.contract.outcome_kind is ExpectedOutcomeKind.GAP
        assert row.contract.expected_gap is not None
        assert row.contract.expected_gap.error_code == "authority_ref_missing"
        assert row.contract.expected_gap.recommended_owner == "authority-link"


def test_learning_reported_speech_and_effect_contracts_have_connected_compatible_topology() -> None:
    cases = _expanded_cases()
    reviewed = {
        row.scenario_ref: row
        for row in cases
        if row.scenario_ref in {
            "scenario:reported_speech-0081",
            "scenario:learning_security-0119",
            "scenario:learning_security-0120",
            "scenario:learning_security-0121",
            "scenario:learning_security-0122",
            "scenario:learning_security-0125",
            "scenario:learning_security-0126",
            "scenario:learning_security-0129",
            "scenario:capability_policy_adapter_effect-0140",
            "scenario:capability_policy_adapter_effect-0142",
        }
    }
    assert len(reviewed) == 10
    for case in reviewed.values():
        for expression in case.contract.expected_expressions:
            application_refs = {app.application_ref for app in expression.applications}
            node_refs = {
                *application_refs,
                *(row.scope_ref for row in expression.scope_operators),
                *(row.link_ref for row in expression.expression_links),
                *(row.binder_ref for row in expression.binders),
            }
            assert set(expression.root_refs) <= node_refs
            child_refs = {
                binding.filler.application_ref
                for app in expression.applications
                for binding in (*app.roles, *app.qualifiers)
                if hasattr(binding.filler, "application_ref")
            }
            assert child_refs <= application_refs
            assert len(expression.root_refs) == 1
