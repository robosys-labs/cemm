"""R4 structural sufficiency matrix tests."""
from __future__ import annotations

from cemm_authoritative_hybrid.authority import (
    AtomRecord,
    DesignationIndex,
    EventSignature,
    RoleSpec,
)
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.r4_contracts import (
    ExpectedCycleContractCompiler,
    ReviewedScenario,
)
from cemm_authoritative_hybrid.r4_sufficiency import (
    StructuralSufficiencyEvaluator,
    StructuralSufficiencyReceipt,
)

__cemm_test_inventory__ = {'tests/test_r4_sufficiency.py::test_sufficiency_enforces_explicit_minimums': {'activation_phase': 'R4',
                                                                               'assertion_ref': 'assertion:r4-sufficiency-enforces-explicit-minimums',
                                                                               'diagnostic_role': 'owner',
                                                                               'introduced_by_task': 'R4-Complete',
                                                                               'owner_ref': 'structural-sufficiency',
                                                                               'source_ast_sha256': 'f2a034e06d6090a4cfcf7160db50122d247a99d8171ef121f695be8b6f91c739'},
 'tests/test_r4_sufficiency.py::test_sufficiency_reports_missing_dimension_without_vacuous_denominator': {'activation_phase': 'R4',
                                                                                                          'assertion_ref': 'assertion:r4-sufficiency-reports-missing-dimension-without-vacuous-denominator',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R4-Complete',
                                                                                                          'owner_ref': 'structural-sufficiency',
                                                                                                          'source_ast_sha256': '82e8e4f67ce51bad5b7efd9fd977daa0fc30ae1ce73c3ea4880ee258e1e92294'}}



class _Authority:
    generation = "authority:test"
    atoms = {
        ref: AtomRecord(ref=ref, kind=kind)
        for ref, kind in {
            "entity:a": "entity",
            "dim:x": "state_dimension",
            "value:y": "state_value",
            "event:a": "event_type",
            "rel:r": "relation_type",
            "rel:s": "relation_type",
            "entity:b": "entity",
            "entity:c": "entity",
        }.items()
    }
    event_signatures = {
        "event:a": EventSignature(
            event_type="event:a",
            roles=(
                RoleSpec(role="role:actor", filler_kinds=(), required=False),
            ),
        ),
    }
    value_dimensions = {"value:y": "dim:x"}
    designations = DesignationIndex(
        by_surface={("a", "en"): ("entity:a",)},
        by_target={("entity:a", "en"): ("a",)},
    )
    capabilities = {}
    permissions = ()
    adapters = ()
    operator_roles = {}
    rules = {}


def _contract(kind: str, fields: dict, index: int):
    scenario = ReviewedScenario.from_dict(
        {
            "scenario_ref": f"scenario:{index}",
            "review_status": "reviewed",
            "competency_category": kind,
            "semantic_assertions": [{"kind": kind, **fields}],
            "surface_examples": [f"surface {index}"],
            "expected_gap_kind": None,
            "metadata": {},
        }
    )
    return ExpectedCycleContractCompiler(
        _Authority(), abi_registry_ref="abi:test"
    ).compile(
        scenario_ref=scenario.scenario_ref,
        case_ref=f"case:{index}",
        surface_ref=f"surface:{index}",
        context_ref=f"context:{index}",
        assertions=scenario.assertions,
        situation_constraints={},
        revision_pin=RevisionPin("authority:test", 0, 0, 0, 0, "model:test"),
    )


def test_sufficiency_enforces_explicit_minimums() -> None:
    scenario = ReviewedScenario.from_dict(
        {
            "scenario_ref": "scenario:combined",
            "review_status": "reviewed",
            "competency_category": "coordination",
            "semantic_assertions": [
                {"kind": "relation", "subject": "entity:a", "relation": "rel:r", "object": "entity:b"},
                {"kind": "relation", "subject": "entity:a", "relation": "rel:s", "object": "entity:c"},
            ],
            "surface_examples": ["combined"],
            "expected_gap_kind": None,
            "metadata": {},
        }
    )
    combined = ExpectedCycleContractCompiler(_Authority(), abi_registry_ref="abi:test").compile(
        scenario_ref=scenario.scenario_ref,
        case_ref="case:combined",
        surface_ref="surface:combined",
        context_ref="context:combined",
        assertions=scenario.assertions,
        situation_constraints={},
        revision_pin=RevisionPin("authority:test", 0, 0, 0, 0, "model:test"),
    )
    contracts = (
        _contract("entity", {"target": "entity:a"}, 1),
        _contract("state", {"subject": "entity:a", "dimension": "dim:x", "value": "value:y"}, 2),
        _contract("event", {"target": "event:a", "actor": "entity:a"}, 3),
        _contract("relation", {"subject": "entity:a", "relation": "rel:r", "object": "entity:b"}, 4),
        _contract("designates", {"surface": "a", "target": "entity:a"}, 5),
        combined,
    )
    evaluator = StructuralSufficiencyEvaluator(
        minimums={
            "operator:op:type": 1,
            "operator:op:state": 1,
            "operator:op:event": 1,
            "operator:op:relation": 1,
            "operator:op:designation": 1,
            "roots:multiple": 1,
        }
    )
    receipt = evaluator.evaluate(contracts)
    assert receipt.passed
    assert StructuralSufficiencyReceipt.from_dict(receipt.as_dict()) == receipt


def test_sufficiency_reports_missing_dimension_without_vacuous_denominator() -> None:
    contract = _contract("entity", {"target": "entity:a"}, 1)
    receipt = StructuralSufficiencyEvaluator(
        minimums={"operator:op:event": 1}
    ).evaluate((contract,))
    assert receipt.violations == ("minimum:operator:op:event:0<1",)
