"""Behavioral R4 closeout regressions over the reviewed corpus.

These tests keep the independent expected-contract compiler total over the
reviewed scenario source without allowing runtime/proposer outputs to influence
expectations.
"""
from __future__ import annotations

from pathlib import Path

from cemm_authoritative_hybrid.authority import AuthorityLinker
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.r4_contracts import (
    ExpectedCycleContract,
    ExpectedCycleContractCompiler,
    ExpectedOutcomeKind,
    ExpressionRelation,
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
 'tests/test_r4_closeout_regressions.py::test_singleton_polysemy_is_not_fabricated_as_ambiguity': {'activation_phase': 'R4',
                                                                                                   'assertion_ref': 'assertion:r4-singleton-polysemy-is-not-fabricated-ambiguity',
                                                                                                   'diagnostic_role': 'owner',
                                                                                                   'introduced_by_task': 'R4-Closeout',
                                                                                                   'owner_ref': 'expected-contract',
                                                                                                   'source_ast_sha256': 'e3537192e23a8bac5019da33aff92a490169470396b3cfa0b53a96dee40f7f88'}}

ROOT = Path(__file__).parents[1]
SCENARIOS = ROOT / "data" / "scenarios" / "use_cases.jsonl"


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
