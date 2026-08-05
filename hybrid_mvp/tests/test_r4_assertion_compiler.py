"""R4 total assertion compiler tests."""
from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.authority import (
    AtomRecord,
    DesignationIndex,
    EventSignature,
    RoleSpec,
)
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.r4_contracts import (
    AssertionCompilerError,
    ExpectedCycleContract,
    ExpectedCycleContractCompiler,
    ReviewedAssertion,
    ReviewedScenario,
)

__cemm_test_inventory__ = {
    "tests/test_r4_assertion_compiler.py::test_compiler_resets_situated_state_between_cases": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-compiler-resets-situated-state-between-cases",
        "diagnostic_role": "owner",
        "introduced_by_task": "R4-Complete",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "e8c0c525b5fcb8bd409764402774eefc4ff3c7087b9556d1dc5f550cad76992d"
    },
    "tests/test_r4_assertion_compiler.py::test_core_reviewed_assertion_families_compile_without_propose": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-core-reviewed-assertion-families-compile-without-propose",
        "diagnostic_role": "owner",
        "introduced_by_task": "R4-Complete",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "92dc4bd6f5b0c93e8e05cf61acf47e135898e73cec8b82e7ba5996721ce875b9"
    },
    "tests/test_r4_assertion_compiler.py::test_unknown_assertion_kind_fails_closed": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-unknown-assertion-kind-fails-closed",
        "diagnostic_role": "owner",
        "introduced_by_task": "R4-Complete",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "bfb2f2d5bfaa4a240f1c0339001bc8f7979c5b9f698d67d7a21ab38970027ef7"
    }
}



class _Authority:
    generation = "authority:test"
    atoms = {
        ref: AtomRecord(ref=ref, kind=kind)
        for ref, kind in {
            "event:greeting": "event_type",
            "concept:agent": "concept",
            "entity:lamp": "entity",
            "dim:power": "state_dimension",
            "entity:alice": "entity",
            "rel:likes": "relation_type",
            "entity:book": "entity",
            "concept:job_role": "concept",
            "concept:task": "concept",
            "event:act": "event_type",
            "event:say": "event_type",
            "event:set_state": "event_type",
            "value:on": "state_value",
            "value:off": "state_value",
            "participant:system": "participant",
            "entity:a": "entity",
            "entity:b": "entity",
        }.items()
    }
    event_signatures = {
        "event:greeting": EventSignature(
            event_type="event:greeting",
            roles=(
                RoleSpec(role="role:actor", filler_kinds=(), required=False),
                RoleSpec(role="role:target", filler_kinds=(), required=False),
            ),
        ),
        "event:say": EventSignature(
            event_type="event:say",
            roles=(
                RoleSpec(role="role:actor", filler_kinds=(), required=False),
                RoleSpec(role="role:content", filler_kinds=(), required=False),
            ),
        ),
        "event:set_state": EventSignature(
            event_type="event:set_state",
            roles=(
                RoleSpec(role="role:actor", filler_kinds=(), required=False),
                RoleSpec(role="role:target", filler_kinds=(), required=False),
                RoleSpec(role="role:dimension", filler_kinds=(), required=False),
                RoleSpec(role="role:value", filler_kinds=(), required=False),
            ),
        ),
    }
    value_dimensions = {"value:on": "dim:power", "value:off": "dim:power"}
    designations = DesignationIndex(
        by_surface={
            ("hello", "en"): ("event:greeting",),
            ("job", "en"): ("concept:job_role", "concept:task"),
            ("yoz", "en"): ("event:greeting",),
        },
        by_target={
            ("event:greeting", "en"): ("hello", "yoz"),
            ("concept:job_role", "en"): ("job",),
            ("concept:task", "en"): ("job",),
        },
    )
    capabilities = {}
    permissions = ()
    adapters = ()
    operator_roles = {}
    rules = {}


def _pin() -> RevisionPin:
    return RevisionPin("authority:test", 0, 0, 0, 0, "model:test")


def _compile(kind: str, fields: dict):
    scenario = ReviewedScenario.from_dict(
        {
            "scenario_ref": f"scenario:{kind}",
            "review_status": "reviewed",
            "competency_category": kind,
            "semantic_assertions": [{"kind": kind, **fields}],
            "surface_examples": ["surface one", "surface two"],
            "expected_gap_kind": None,
            "metadata": {},
        }
    )
    return ExpectedCycleContractCompiler(
        _Authority(), abi_registry_ref="abi:test"
    ).compile(
        scenario_ref=scenario.scenario_ref,
        case_ref=f"case:{kind}",
        surface_ref=f"surface:{kind}",
        context_ref="context:test",
        assertions=scenario.assertions,
        situation_constraints={},
        revision_pin=_pin(),
    )


def test_core_reviewed_assertion_families_compile_without_propose() -> None:
    cases = {
        "designates": {"surface": "hello", "target": "event:greeting"},
        "defines": {"semantic_kind": "concept", "target": "concept:agent"},
        "query": {"dimension": "dim:power", "target": "entity:lamp"},
        "relation": {
            "subject": "entity:alice",
            "relation": "rel:likes",
            "object": "entity:book",
        },
        "polysemy": {"surface": "job", "targets": ["concept:job_role", "concept:task"]},
        "modality": {"modality_kind": "possible", "target": "event:act"},
        "negation": {"scope": "dim:power", "target": "entity:lamp"},
        "reported_speech": {
            "speaker": "entity:alice",
            "event": "event:say",
        },
        "transition": {
            "event": "event:set_state",
            "subject": "entity:lamp",
            "dimension": "dim:power",
            "from_value": "value:off",
            "to_value": "value:on",
        },
        "lookup": {
            "target": "event:greeting",
            "surface": "yoz",
        },
        "contradiction": {
            "subject": "entity:lamp",
            "dimension": "dim:power",
            "values": ["value:on", "value:off"],
        },
        "realization_equivalence": {
            "discourse_action": "respond",
            "status": "resolved",
        },
    }
    for kind, fields in cases.items():
        contract = _compile(kind, fields)
        assert ExpectedCycleContract.from_dict(contract.as_dict()) == contract
        if contract.expected_expressions:
            assert any(expr.applications for expr in contract.expected_expressions)


def test_compiler_resets_situated_state_between_cases() -> None:
    compiler = ExpectedCycleContractCompiler(_Authority(), abi_registry_ref="abi:test")
    first = ReviewedScenario.from_dict(
        {
            "scenario_ref": "scenario:first",
            "review_status": "reviewed",
            "competency_category": "query",
            "semantic_assertions": [
                {"kind": "query", "dimension": "dim:power", "target": "entity:lamp"}
            ],
            "surface_examples": ["is the lamp on?"],
            "expected_gap_kind": None,
            "metadata": {},
        }
    )
    second = ReviewedScenario.from_dict(
        {
            "scenario_ref": "scenario:second",
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
    one = compiler.compile(
        scenario_ref=first.scenario_ref,
        case_ref="case:first",
        surface_ref="surface:first",
        context_ref="context:first",
        assertions=first.assertions,
        situation_constraints={},
        revision_pin=_pin(),
    )
    two = compiler.compile(
        scenario_ref=second.scenario_ref,
        case_ref="case:second",
        surface_ref="surface:second",
        context_ref="context:second",
        assertions=second.assertions,
        situation_constraints={},
        revision_pin=_pin(),
    )
    assert one.expected_mode.value == "QUERY"
    assert two.expected_mode.value == "OBSERVE"


def test_unknown_assertion_kind_fails_closed() -> None:
    assertion = ReviewedAssertion.create(
        kind="invented_kind",
        fields={"target": "entity:test"},
        review_refs=("review:test",),
    )
    with pytest.raises(AssertionCompilerError, match="unsupported_assertion_kind"):
        ExpectedCycleContractCompiler(
            _Authority(), abi_registry_ref="abi:test"
        ).compile(
            scenario_ref="scenario:test",
            case_ref="case:test",
            surface_ref="surface:test",
            context_ref="context:test",
            assertions=(assertion,),
            situation_constraints={},
            revision_pin=_pin(),
        )
