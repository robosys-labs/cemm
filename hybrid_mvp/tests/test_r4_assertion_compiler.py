"""R4 total assertion compiler tests."""
from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.authority import (
    AtomRecord,
    DesignationFact,
    DesignationIndex,
    EventSignature,
    RoleSpec,
)
from cemm_authoritative_hybrid.cycle import CycleStatus, SemanticMode
from cemm_authoritative_hybrid.decision import DecisionAction, DecisionStatus
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.r4_contracts import (
    AssertionCompilerError,
    ExpectedCycleContract,
    ExpectedCycleContractCompiler,
    ExpectedEffectKind,
    ExpectedGapContract,
    ExpectedResponseContract,
    ReviewedAssertion,
    ReviewedScenario,
)

__cemm_test_inventory__ = {'tests/test_r4_assertion_compiler.py::test_unknown_assertion_kind_fails_closed': {'activation_phase': 'R4',
                                                                                   'assertion_ref': 'assertion:r4-unknown-assertion-kind-fails-closed',
                                                                                   'diagnostic_role': 'owner',
                                                                                   'introduced_by_task': 'R4-Complete',
                                                                                   'owner_ref': 'expected-contract',
                                                                                   'source_ast_sha256': 'bfb2f2d5bfaa4a240f1c0339001bc8f7979c5b9f698d67d7a21ab38970027ef7'},
 'tests/test_r4_assertion_compiler.py::test_sr1_structured_gap_kinds_preserve_exact_owners': {'activation_phase': 'R4',
                                                                                              'assertion_ref': 'assertion:r4-sr1-structured-gap-kinds-preserve-exact-owners',
                                                                                              'diagnostic_role': 'owner',
                                                                                              'introduced_by_task': 'R4.1-SR1',
                                                                                              'owner_ref': 'expected-contract',
                                                                                              'source_ast_sha256': 'ee926791b7c190eda0eb9939583034df550423e2b8898b56e6e5f4f93efc9011'},
 'tests/test_r4_assertion_compiler.py::test_sr1_adversarial_is_exact_verification_rejection': {'activation_phase': 'R4',
                                                                                               'assertion_ref': 'assertion:r4-sr1-adversarial-is-exact-verification-rejection',
                                                                                               'diagnostic_role': 'owner',
                                                                                               'introduced_by_task': 'R4.1-SR1',
                                                                                               'owner_ref': 'expected-contract',
                                                                                               'source_ast_sha256': '4f2809ff94230bc83875c503a398ae7a964e174e5325f39466bf9d7177c89879'},
 'tests/test_r4_assertion_compiler.py::test_sr1_adversarial_and_gap_cannot_mix': {'activation_phase': 'R4',
                                                                                  'assertion_ref': 'assertion:r4-sr1-adversarial-and-gap-cannot-mix',
                                                                                  'diagnostic_role': 'owner',
                                                                                  'introduced_by_task': 'R4.1-SR1',
                                                                                  'owner_ref': 'expected-contract',
                                                                                  'source_ast_sha256': '2bcf5149765444c3c022684b79fbac8fa80acccd6977f6481a8b6ea05b7eb689'},
 'tests/test_r4_assertion_compiler.py::test_sr1_old_abi2_generic_gap_rows_fail_closed': {'activation_phase': 'R4',
                                                                                         'assertion_ref': 'assertion:r4-sr1-old-abi2-generic-gap-rows-fail-closed',
                                                                                         'diagnostic_role': 'owner',
                                                                                         'introduced_by_task': 'R4.1-SR1',
                                                                                         'owner_ref': 'expected-contract',
                                                                                         'source_ast_sha256': '07211bf87892b397a761aebc7b56cd4f051cc5315328a6affd53b8d46661cdcc'},
 'tests/test_r4_assertion_compiler.py::test_core_reviewed_assertion_families_compile_without_propose': {'activation_phase': 'R4',
                                                                                                        'assertion_ref': 'assertion:r4-core-reviewed-assertion-families-compile-without-propose',
                                                                                                        'diagnostic_role': 'owner',
                                                                                                        'introduced_by_task': 'R4-Complete',
                                                                                                        'owner_ref': 'expected-contract',
                                                                                                        'source_ast_sha256': '92dc4bd6f5b0c93e8e05cf61acf47e135898e73cec8b82e7ba5996721ce875b9'},
 'tests/test_r4_assertion_compiler.py::test_explicit_cycle_contract_rows_are_complete_and_override_defaults': {'activation_phase': 'R4',
                                                                                                               'assertion_ref': 'assertion:r4-explicit-cycle-contract-rows-are-complete',
                                                                                                               'diagnostic_role': 'owner',
                                                                                                               'introduced_by_task': 'R4-Designation-Event-Tranche',
                                                                                                               'owner_ref': 'expected-contract',
                                                                                                               'source_ast_sha256': 'a02a80bcfa01b7ab55354f92dcb3389e87670e608869703274b08ce0e5e112ba'},
 'tests/test_r4_assertion_compiler.py::test_compiler_resets_situated_state_between_cases': {'activation_phase': 'R4',
                                                                                            'assertion_ref': 'assertion:r4-compiler-resets-situated-state-between-cases',
                                                                                            'diagnostic_role': 'owner',
                                                                                            'introduced_by_task': 'R4-Complete',
                                                                                            'owner_ref': 'expected-contract',
                                                                                            'source_ast_sha256': '18044cd2bafe34c53b9f8f12b2cbe162fc35ad3502fb8077df57f58ecbd98ef6'},
 'tests/test_r4_assertion_compiler.py::test_sr4_5_linked_composed_expression_is_one_canonical_meaning': {'activation_phase': 'R4',
                                                                                                         'assertion_ref': 'assertion:r4-sr4-5-linked-composed-expression-is-one-canonical-meaning',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R4.1-SR4.5',
                                                                                                         'owner_ref': 'expected-contract',
                                                                                                         'source_ast_sha256': 'bb6810ca70840b81a57a0d1fa41403e55f35d2cf7ac3751153d014e7c15cbc38'},
 'tests/test_r4_assertion_compiler.py::test_sr4_5_true_multi_root_and_type_role_remain_one_meaning': {'activation_phase': 'R4',
                                                                                                      'assertion_ref': 'assertion:r4-sr4-5-true-multi-root-and-type-role-remain-one-meaning',
                                                                                                      'diagnostic_role': 'owner',
                                                                                                      'introduced_by_task': 'R4.1-SR4.5',
                                                                                                      'owner_ref': 'expected-contract',
                                                                                                      'source_ast_sha256': '5db2ca8db9295dd67b5f122a2bee4ab0af8922ebf50f9254658e44af12276ad4'},
 'tests/test_r4_assertion_compiler.py::test_sr4_5_proposition_filler_requires_reviewed_proposition_role': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:r4-sr4-5-proposition-filler-requires-reviewed-proposition-role',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R4.1-SR4.5',
                                                                                                           'owner_ref': 'expected-contract',
                                                                                                           'source_ast_sha256': 'e75431218e15fbdd03f93a56bc017aa5671752008586436ade6daff86376dd17'},
 'tests/test_r4_assertion_compiler.py::test_sr4_5_reviewed_proposition_role_builds_one_reachable_graph': {'activation_phase': 'R4',
                                                                                                          'assertion_ref': 'assertion:r4-sr4-5-reviewed-proposition-role-builds-one-reachable-graph',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R4.1-SR4.5',
                                                                                                          'owner_ref': 'expected-contract',
                                                                                                          'source_ast_sha256': '6d4c644ae982c9c16dea9c6035cc11c65f0a10af3fb82c0df24090086347c94d'},
 'tests/test_r4_assertion_compiler.py::test_sr4_5_composed_expression_rejects_noncanonical_graphs': {'activation_phase': 'R4',
                                                                                                     'assertion_ref': 'assertion:r4-sr4-5-composed-expression-rejects-noncanonical-graphs',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'R4.1-SR4.5',
                                                                                                     'owner_ref': 'expected-contract',
                                                                                                     'source_ast_sha256': 'a1edf610cdf2e991aafef82954a4d29c58a58f15af00f2ea93111739846cf053'},
 'tests/test_r4_assertion_compiler.py::test_sr4_5_separate_assertions_and_conflicts_are_not_multi_root': {'activation_phase': 'R4',
                                                                                                          'assertion_ref': 'assertion:r4-sr4-5-separate-assertions-and-conflicts-are-not-multi-root',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R4.1-SR4.5',
                                                                                                          'owner_ref': 'expected-contract',
                                                                                                          'source_ast_sha256': '1151e2392282653134c4f213f629efdca65e9f9048def634ca07fd8306a7d6b1'}}



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
            "event:literal": "event_type",
            "value:on": "state_value",
            "value:off": "state_value",
            "participant:system": "participant",
            "participant:user": "participant",
            "entity:a": "entity",
            "entity:b": "entity",
            "adapter:state": "adapter",
            "permission:set_state": "permission",
        }.items()
    }
    event_signatures = {
        "event:greeting": EventSignature(
            event_type="event:greeting",
            roles=(
                RoleSpec(
                    role="role:actor",
                    filler_kinds=("participant", "entity"),
                    required=False,
                ),
                RoleSpec(
                    role="role:addressee",
                    filler_kinds=("participant", "entity"),
                    required=False,
                ),
            ),
        ),
        "event:say": EventSignature(
            event_type="event:say",
            roles=(
                RoleSpec(role="role:actor", filler_kinds=(), required=False),
                RoleSpec(
                    role="role:content",
                    filler_kinds=(),
                    required=False,
                    proposition_valued=True,
                ),
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
        "event:literal": EventSignature(
            event_type="event:literal",
            roles=(
                RoleSpec(
                    role="role:surface",
                    filler_kinds=("literal",),
                    required=True,
                ),
            ),
        ),
    }
    value_dimensions = {"value:on": "dim:power", "value:off": "dim:power"}
    designations = DesignationIndex(
        tuple(
            DesignationFact.create(surface=surface, target_ref=target, language="en")
            for surface, target in (
                ("hello", "event:greeting"),
                ("job", "concept:job_role"),
                ("job", "concept:task"),
                ("yoz", "event:greeting"),
            )
        )
    )
    capabilities = {}
    permissions = ()
    adapters = ("adapter:state",)
    operator_roles = {
        "op:designation": ["role:surface", "role:target", "role:label_type"],
        "op:type": ["role:subject", "role:type", "role:instance", "role:class"],
        "op:relation": ["role:subject", "role:relation", "role:object"],
        "op:state": ["role:subject", "role:dimension", "role:value"],
        "op:event": ["role:event", "role:type"],
    }
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


def test_operation_prerequisites_are_authority_linked_and_preserved() -> None:
    scenario = ReviewedScenario.from_dict(
        {
            "scenario_ref": "scenario:operation-prerequisites",
            "review_status": "reviewed",
            "competency_category": "transition",
            "semantic_assertions": [
                {
                    "kind": "transition",
                    "event": "event:set_state",
                    "subject": "entity:lamp",
                    "dimension": "dim:power",
                    "from_value": "value:off",
                    "to_value": "value:on",
                }
            ],
            "surface_examples": ["turn the lamp on"],
            "metadata": {},
        }
    )
    compiler = ExpectedCycleContractCompiler(_Authority(), abi_registry_ref="abi:test")

    def compile_with(constraints):
        return compiler.compile(
            scenario_ref=scenario.scenario_ref,
            case_ref="case:operation-prerequisites",
            surface_ref="surface:operation-prerequisites",
            context_ref="context:operation-prerequisites",
            assertions=scenario.assertions,
            situation_constraints=constraints,
            revision_pin=_pin(),
        )

    contract = compile_with(
        {
            "adapter_refs": ["adapter:state"],
            "permission_refs": ["permission:set_state"],
            "world_facts": [],
        }
    )
    assert contract.situation_constraints["adapter_refs"] == ("adapter:state",)
    assert contract.situation_constraints["permission_refs"] == (
        "permission:set_state",
    )
    with pytest.raises(ValueError, match="adapter"):
        compile_with({"adapter_refs": ["adapter:missing"]})
    with pytest.raises(ValueError, match="permission"):
        compile_with({"permission_refs": ["permission:missing"]})


def test_explicit_cycle_contract_rows_are_complete_and_override_defaults() -> None:
    scenario = ReviewedScenario.from_dict(
        {
            "scenario_ref": "scenario:explicit-cycle-contract",
            "review_status": "reviewed",
            "competency_category": "designation_definition",
            "semantic_assertions": [
                {
                    "kind": "event",
                    "event_type": "event:greeting",
                    "roles": {
                        "role:actor": "participant:user",
                        "role:addressee": "participant:system",
                    },
                },
                {"kind": "mode", "mode": "OBSERVE"},
                {
                    "kind": "decision",
                    "status": "contested",
                    "action": "retain_attribution",
                },
                {"kind": "no_effect", "reason": "attributed_only"},
                {
                    "kind": "response",
                    "discourse_action": "acknowledge",
                    "cycle_status": "partial",
                    "polarity": "polarity:positive",
                    "modality": "modality:actual",
                    "epistemic_status": "epistemic_status:contested",
                },
            ],
            "surface_examples": ["hello"],
            "metadata": {},
        }
    )
    compiler = ExpectedCycleContractCompiler(_Authority(), abi_registry_ref="abi:test")
    contract = compiler.compile(
        scenario_ref=scenario.scenario_ref,
        case_ref="case:explicit-cycle-contract",
        surface_ref="surface:explicit-cycle-contract",
        context_ref="context:explicit-cycle-contract",
        assertions=scenario.assertions,
        situation_constraints={},
        revision_pin=_pin(),
    )
    assert contract.expected_mode is SemanticMode.OBSERVE
    assert len(contract.expected_expressions) == 1
    assert contract.expected_expressions[0].applications[0].operator == "op:event"
    assert contract.expected_decision.status is DecisionStatus.CONTESTED
    assert contract.expected_decision.action is DecisionAction.RETAIN_ATTRIBUTION
    assert contract.expected_effect.kind is ExpectedEffectKind.NO_EFFECT
    assert contract.expected_effect.status_or_reason == "attributed_only"
    assert contract.expected_response.discourse_action == "acknowledge"
    assert contract.expected_response.cycle_status is CycleStatus.PARTIAL
    assert contract.expected_response.epistemic_status_ref == "epistemic_status:contested"

    with pytest.raises(ValueError, match="epistemic_status"):
        ExpectedResponseContract(
            "acknowledge",
            CycleStatus.PARTIAL,
            "polarity:positive",
            "modality:actual",
            "contested",
        )

    invalid_epistemic = ReviewedScenario.from_dict(
        {
            "scenario_ref": "scenario:invalid-epistemic-cycle-contract",
            "review_status": "reviewed",
            "competency_category": "designation_definition",
            "semantic_assertions": [
                {
                    "kind": "event",
                    "event_type": "event:greeting",
                    "roles": {"role:actor": "participant:user"},
                },
                {"kind": "mode", "mode": "OBSERVE"},
                {
                    "kind": "decision",
                    "status": "contested",
                    "action": "retain_attribution",
                },
                {"kind": "no_effect", "reason": "attributed_only"},
                {
                    "kind": "response",
                    "discourse_action": "acknowledge",
                    "cycle_status": "partial",
                    "polarity": "polarity:positive",
                    "modality": "modality:actual",
                    "epistemic_status": "epistemic:contested",
                },
            ],
            "surface_examples": ["hello"],
            "metadata": {},
        }
    )
    with pytest.raises(ValueError, match="epistemic_status"):
        compiler.compile(
            scenario_ref=invalid_epistemic.scenario_ref,
            case_ref="case:invalid-epistemic-cycle-contract",
            surface_ref="surface:invalid-epistemic-cycle-contract",
            context_ref="context:invalid-epistemic-cycle-contract",
            assertions=invalid_epistemic.assertions,
            situation_constraints={},
            revision_pin=_pin(),
        )

    incomplete = ReviewedScenario.from_dict(
        {
            "scenario_ref": "scenario:incomplete-cycle-contract",
            "review_status": "reviewed",
            "competency_category": "designation_definition",
            "semantic_assertions": [
                {
                    "kind": "event",
                    "event_type": "event:greeting",
                    "roles": {
                        "role:actor": "participant:user",
                        "role:addressee": "participant:system",
                    },
                },
                {
                    "kind": "decision",
                    "status": "contested",
                    "action": "retain_attribution",
                },
            ],
            "surface_examples": ["hello"],
            "metadata": {},
        }
    )
    with pytest.raises(
        ValueError,
        match="exactly one decision, no_effect and response",
    ):
        compiler.compile(
            scenario_ref=incomplete.scenario_ref,
            case_ref="case:incomplete-cycle-contract",
            surface_ref="surface:incomplete-cycle-contract",
            context_ref="context:incomplete-cycle-contract",
            assertions=incomplete.assertions,
            situation_constraints={},
            revision_pin=_pin(),
        )


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


def test_sr1_structured_gap_kinds_preserve_exact_owners() -> None:
    rows = [
        ("evidence", "form-context"),
        ("designation", "form-context"),
        ("reference", "form-context"),
        ("authority", "authority-link"),
        ("proposal", "recursive-composer"),
        ("verification", "exact-verifier"),
        ("inference", "decision-query-proof"),
        ("state", "epistemic-state"),
        ("transition", "capability-effect"),
        ("learning", "learning-dialogue"),
        ("resource", "capability-effect"),
        ("permission", "capability-effect"),
        ("adapter", "capability-effect"),
        ("operation", "capability-effect"),
        ("storage", "persistence-recovery"),
        ("realization", "response-contract"),
        ("performance", "runtime-activation"),
        ("implementation", "runtime-activation"),
    ]
    for gap_kind, owner in rows:
        contract = _compile(
            "gap", {"gap_kind": gap_kind, "description": f"{gap_kind} gap"}
        )
        assert contract.outcome_kind.value == "gap"
        assert contract.expected_gap is not None
        assert contract.expected_gap.kind == gap_kind
        assert contract.expected_gap.recommended_owner == owner


def test_sr1_adversarial_is_exact_verification_rejection() -> None:
    contract = _compile(
        "adversarial",
        {
            "attack": "unknown_operator",
            "operator": "op:invented",
            "expected_owner": "exact-verifier",
            "expected_error_code": "verification:unknown_operator",
        },
    )
    assert contract.outcome_kind.value == "verification_rejection"
    assert contract.expression_relation.value == "none"
    assert contract.expected_gap is not None
    assert contract.expected_gap.kind == "verification"
    assert contract.expected_gap.recommended_owner == "exact-verifier"
    assert contract.expected_gap.safe_response_action == "reject_candidate"
    assert contract.expected_gap.error_code == "verification:unknown_operator"
    assert contract.expected_response.discourse_action == "reject_candidate"
    assert contract.expected_response.epistemic_status_ref == "epistemic_status:unknown"
    for invalid in (None, 7, True):
        with pytest.raises((TypeError, ValueError), match="expected_error_code"):
            _compile(
                "adversarial",
                {
                    "attack": "unknown_operator",
                    "expected_error_code": invalid,
                },
            )


def test_sr1_adversarial_and_gap_cannot_mix() -> None:
    with pytest.raises(ValueError, match="gap.*adversarial|mixed"):
        ReviewedScenario.from_dict(
            {
                "scenario_ref": "scenario:mixed-rejection",
                "review_status": "reviewed",
                "competency_category": "adversarial_programs",
                "semantic_assertions": [
                    {
                        "kind": "gap",
                        "gap_kind": "verification",
                        "description": "gap",
                    },
                    {"kind": "adversarial", "attack": "unknown_operator"},
                ],
                "surface_examples": ["attack"],
                "metadata": {},
            }
        )


def _composed_application(
    local_ref: str,
    operator: str,
    predicate: str,
    roles: dict,
) -> dict:
    return {
        "local_ref": local_ref,
        "operator": operator,
        "predicate": predicate,
        "roles": roles,
    }


def _grounded(target: str) -> dict:
    return {"kind": "grounded", "target": target}


def _literal(value: object, value_type: str = "string") -> dict:
    return {"kind": "literal", "value_type": value_type, "value": value}


def _linked_fields(link_type: str = "link:condition") -> dict:
    return {
        "shape": "linked",
        "mode": "SIMULATE",
        "applications": [
            _composed_application(
                "power",
                "op:state",
                "dim:power",
                {
                    "role:subject": _grounded("entity:lamp"),
                    "role:dimension": _grounded("dim:power"),
                    "role:value": _grounded("value:on"),
                },
            ),
            _composed_application(
                "greeting",
                "op:event",
                "event:greeting",
                {
                    "role:actor": _grounded("participant:user"),
                    "role:addressee": _grounded("participant:system"),
                },
            ),
        ],
        "expression_links": [
            {
                "local_ref": "joined",
                "link_type": link_type,
                "operand_local_refs": ["power", "greeting"],
            }
        ],
        "root_local_refs": ["joined"],
    }


def _assert_linked_composed_expression_is_one_canonical_meaning(
    link_type: str,
) -> None:
    contract = _compile("composed_expression", _linked_fields(link_type))

    assert contract.expression_relation.value == "single"
    assert contract.expected_mode is SemanticMode.SIMULATE
    assert len(contract.expected_expressions) == 1
    expression = contract.expected_expressions[0]
    assert len(expression.root_refs) == 1
    assert len(expression.expression_links) == 1
    assert expression.expression_links[0].link_type == link_type
    assert expression.root_refs == (expression.expression_links[0].link_ref,)
    assert ExpectedCycleContract.from_dict(contract.as_dict()) == contract


def test_sr4_5_linked_composed_expression_is_one_canonical_meaning() -> None:
    for link_type in (
        "link:coordination",
        "link:conjunction",
        "link:disjunction",
        "link:condition",
        "link:cause",
        "link:purpose",
        "link:contrast",
        "link:sequence",
    ):
        _assert_linked_composed_expression_is_one_canonical_meaning(link_type)

    licensed_literal = _linked_fields()
    licensed_literal["applications"][1] = _composed_application(
        "greeting",
        "op:event",
        "event:literal",
        {"role:surface": _literal("reviewed literal")},
    )
    assert _compile(
        "composed_expression", licensed_literal
    ).expression_relation.value == "single"

    designation = _linked_fields()
    designation["applications"][1] = _composed_application(
        "greeting",
        "op:designation",
        "event:greeting",
        {
            "role:surface": _literal("hello"),
            "role:target": _grounded("event:greeting"),
        },
    )
    assert _compile(
        "composed_expression", designation
    ).expression_relation.value == "single"

    commutative = _linked_fields("link:coordination")
    commutative_reversed = _linked_fields("link:coordination")
    commutative_reversed["applications"].reverse()
    commutative_reversed["expression_links"][0]["operand_local_refs"].reverse()
    assert (
        _compile("composed_expression", commutative).expected_expressions[0].expression_ref
        == _compile(
            "composed_expression", commutative_reversed
        ).expected_expressions[0].expression_ref
    )

    ordered = _linked_fields("link:condition")
    ordered_reversed = _linked_fields("link:condition")
    ordered_reversed["expression_links"][0]["operand_local_refs"].reverse()
    assert (
        _compile("composed_expression", ordered).expected_expressions[0].expression_ref
        != _compile(
            "composed_expression", ordered_reversed
        ).expected_expressions[0].expression_ref
    )

    renamed = _linked_fields("link:condition")
    renamed["applications"][0]["local_ref"] = "first_application"
    renamed["applications"][1]["local_ref"] = "second_application"
    renamed["expression_links"][0]["local_ref"] = "conditional_link"
    renamed["expression_links"][0]["operand_local_refs"] = [
        "first_application",
        "second_application",
    ]
    renamed["root_local_refs"] = ["conditional_link"]
    assert (
        _compile("composed_expression", ordered).expected_expressions[0].expression_ref
        == _compile("composed_expression", renamed).expected_expressions[0].expression_ref
    )


def test_sr4_5_true_multi_root_and_type_role_remain_one_meaning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fields = {
        "shape": "multi_root",
        "applications": [
            _composed_application(
                "typing",
                "op:type",
                "concept:agent",
                {
                    "role:subject": _grounded("concept:agent"),
                    "role:type": _literal("concept"),
                },
            ),
            _composed_application(
                "liking",
                "op:relation",
                "rel:likes",
                {
                    "role:subject": _grounded("entity:alice"),
                    "role:object": _grounded("entity:book"),
                },
            ),
        ],
        "expression_links": [],
        "root_local_refs": ["typing", "liking"],
    }

    first = _compile("composed_expression", fields)
    renamed = {
        "shape": "multi_root",
        "applications": [
            _composed_application(
                "second",
                "op:relation",
                "rel:likes",
                {
                    "role:object": _grounded("entity:book"),
                    "role:subject": _grounded("entity:alice"),
                },
            ),
            _composed_application(
                "first",
                "op:type",
                "concept:agent",
                {
                    "role:type": _literal("concept"),
                    "role:subject": _grounded("concept:agent"),
                },
            ),
        ],
        "expression_links": [],
        "root_local_refs": ["second", "first"],
    }
    second = _compile("composed_expression", renamed)

    assert first.expression_relation.value == "single"
    assert len(first.expected_expressions) == 1
    expression = first.expected_expressions[0]
    assert len(expression.root_refs) == 2
    assert not expression.expression_links
    assert any(
        application.operator == "op:type"
        and any(role.role_ref == "role:type" for role in application.roles)
        for application in expression.applications
    )
    assert second.expected_expressions[0].expression_ref == expression.expression_ref

    work: list[str] = []

    def counted_work(
        _compiler: ExpectedCycleContractCompiler, operation: str
    ) -> None:
        work.append(operation)

    monkeypatch.setattr(
        ExpectedCycleContractCompiler,
        "_record_composed_work",
        counted_work,
    )

    def compile_roots(count: int) -> int:
        work.clear()
        root_fields = {
            "shape": "multi_root",
            "applications": [
                _composed_application(
                    f"root_{index}",
                    "op:type",
                    "concept:agent",
                    {
                        "role:subject": _grounded("concept:agent"),
                        "role:type": _literal("concept"),
                    },
                )
                for index in range(count)
            ],
            "expression_links": [],
            "root_local_refs": [f"root_{index}" for index in range(count)],
        }
        _compile("composed_expression", root_fields)
        assert work.count("local_ref_duplicate_probe") == count
        assert work.count("local_ref_insert") == count
        assert work.count("root_resolution") == count
        assert work.count("proposition_resolution") == 0
        assert work.count("link_operand_resolution") == 0
        return len(work)

    assert compile_roots(2) == 6
    assert compile_roots(8) == 24

    work.clear()
    _compile("composed_expression", _linked_fields())
    assert work == [
        "local_ref_duplicate_probe",
        "local_ref_insert",
        "local_ref_duplicate_probe",
        "local_ref_insert",
        "local_ref_duplicate_probe",
        "local_ref_insert",
        "root_resolution",
        "link_operand_resolution",
        "link_operand_resolution",
    ]


def test_sr4_5_proposition_filler_requires_reviewed_proposition_role() -> None:
    fields = _linked_fields("link:condition")
    fields["applications"][1] = _composed_application(
        "greeting",
        "op:event",
        "event:greeting",
        {
            "role:actor": {"kind": "proposition", "node_local_ref": "power"},
            "role:addressee": _grounded("participant:system"),
        },
    )
    with pytest.raises(ValueError, match="proposition"):
        _compile("composed_expression", fields)


def test_sr4_5_reviewed_proposition_role_builds_one_reachable_graph() -> None:
    fields = {
        "shape": "linked",
        "applications": [
            _composed_application(
                "content",
                "op:event",
                "event:greeting",
                {"role:actor": _grounded("participant:user")},
            ),
            _composed_application(
                "speech",
                "op:event",
                "event:say",
                {
                    "role:actor": _grounded("entity:alice"),
                    "role:content": {
                        "kind": "proposition",
                        "node_local_ref": "content",
                    },
                },
            ),
            _composed_application(
                "power",
                "op:state",
                "dim:power",
                {
                    "role:subject": _grounded("entity:lamp"),
                    "role:dimension": _grounded("dim:power"),
                    "role:value": _grounded("value:on"),
                },
            ),
        ],
        "expression_links": [
            {
                "local_ref": "joined",
                "link_type": "link:coordination",
                "operand_local_refs": ["speech", "power"],
            }
        ],
        "root_local_refs": ["joined"],
    }

    expression = _compile(
        "composed_expression", fields
    ).expected_expressions[0]

    assert len(expression.applications) == 3
    assert len(expression.expression_links) == 1
    assert len(expression.root_refs) == 1


def _assert_composed_expression_rejects_noncanonical_graph(
    mutation: str,
    error: str,
) -> None:
    fields = _linked_fields()
    if mutation == "duplicate_local":
        fields["applications"][1]["local_ref"] = "power"
    elif mutation == "duplicate_root":
        fields["root_local_refs"] = ["joined", "joined"]
    elif mutation == "unknown_root":
        fields["root_local_refs"] = ["missing"]
    elif mutation == "unknown_shape":
        fields["shape"] = "conflict"
    elif mutation == "bad_link_arity":
        fields["expression_links"][0]["operand_local_refs"] = ["power"]
    elif mutation == "unknown_link":
        fields["expression_links"][0]["link_type"] = "link:invented"
    elif mutation == "dangling_operand":
        fields["expression_links"][0]["operand_local_refs"] = [
            "power",
            "missing",
        ]
    elif mutation == "multi_root_with_link":
        fields["shape"] = "multi_root"
        fields["root_local_refs"] = ["power", "greeting"]
    elif mutation == "linked_without_link":
        fields["expression_links"] = []
        fields["root_local_refs"] = ["power"]
    elif mutation == "unknown_operator":
        fields["applications"][0]["operator"] = "op:invented"
    elif mutation == "unknown_predicate":
        fields["applications"][0]["predicate"] = "dim:missing"
    elif mutation == "wrong_predicate_kind":
        fields["applications"][0]["predicate"] = "concept:agent"
    elif mutation == "unknown_role":
        fields["applications"][0]["roles"] = {
            "role:invented": _grounded("entity:lamp")
        }
    elif mutation == "unknown_filler":
        fields["applications"][0]["roles"]["role:subject"] = {
            "kind": "invented",
            "target": "entity:lamp",
        }
    elif mutation == "literal_event_actor":
        fields["applications"][1]["roles"]["role:actor"] = _literal("alice")
    elif mutation in {"designation_non_string", "designation_empty"}:
        fields["applications"][1] = _composed_application(
            "designation",
            "op:designation",
            "event:greeting",
            {
                "role:surface": (
                    _literal(7, "integer")
                    if mutation == "designation_non_string"
                    else _literal("")
                ),
                "role:target": _grounded("event:greeting"),
            },
        )
    elif mutation == "dangling_proposition":
        fields["applications"][1] = _composed_application(
            "greeting",
            "op:event",
            "event:greeting",
            {
                "role:actor": {
                    "kind": "proposition",
                    "node_local_ref": "missing",
                }
            },
        )
    elif mutation == "orphan":
        fields["expression_links"][0]["operand_local_refs"] = ["power", "power"]
    elif mutation == "cycle":
        fields["expression_links"] = [
            {
                "local_ref": "left",
                "link_type": "link:condition",
                "operand_local_refs": ["power", "right"],
            },
            {
                "local_ref": "right",
                "link_type": "link:condition",
                "operand_local_refs": ["greeting", "left"],
            },
        ]
        fields["root_local_refs"] = ["left"]
    elif mutation == "integer_bool":
        fields["applications"][0] = _composed_application(
            "power",
            "op:type",
            "concept:agent",
            {
                "role:subject": _grounded("concept:agent"),
                "role:type": _literal(True, "integer"),
            },
        )
    elif mutation == "boolean_int":
        fields["applications"][0] = _composed_application(
            "power",
            "op:type",
            "concept:agent",
            {
                "role:subject": _grounded("concept:agent"),
                "role:type": _literal(1, "boolean"),
            },
        )
    elif mutation == "wrong_type_literal":
        fields["applications"][0] = _composed_application(
            "power",
            "op:type",
            "concept:agent",
            {
                "role:subject": _grounded("concept:agent"),
                "role:type": _literal("adapter"),
            },
        )
    elif mutation == "extra_application_field":
        fields["applications"][0]["surface"] = "not structural"
    elif mutation == "missing_link_field":
        del fields["expression_links"][0]["operand_local_refs"]
    elif mutation == "extra_filler_field":
        fields["applications"][0]["roles"]["role:subject"]["extra"] = True
    elif mutation == "over_role_bound":
        fields["applications"][0]["roles"] = {
            f"role:extra_{index}": _grounded("entity:lamp")
            for index in range(17)
        }
    elif mutation == "over_depth":
        fields["applications"] = [
            _composed_application(
                f"app_{index}",
                "op:type",
                "concept:agent",
                {
                    "role:subject": _grounded("concept:agent"),
                    "role:type": _literal("concept"),
                },
            )
            for index in range(8)
        ]
        fields["expression_links"] = [
            {
                "local_ref": f"link_{index}",
                "link_type": "link:condition",
                "operand_local_refs": [
                    "app_0" if index == 0 else f"link_{index - 1}",
                    f"app_{index + 1}",
                ],
            }
            for index in range(7)
        ]
        fields["root_local_refs"] = ["link_6"]
    elif mutation == "over_application_bound":
        fields["applications"] = [fields["applications"][0]] * 25
    elif mutation == "over_link_bound":
        fields["expression_links"] = [fields["expression_links"][0]] * 25
    else:
        fields = {
            "shape": "multi_root",
            "applications": [
                _composed_application(
                    f"root_{index}",
                    "op:type",
                    "concept:agent",
                    {
                        "role:subject": _grounded("concept:agent"),
                        "role:type": _literal(str(index)),
                    },
                )
                for index in range(9)
            ],
            "expression_links": [],
            "root_local_refs": [f"root_{index}" for index in range(9)],
        }
    with pytest.raises((AssertionCompilerError, TypeError, ValueError), match=error):
        _compile("composed_expression", fields)


def test_sr4_5_composed_expression_rejects_noncanonical_graphs() -> None:
    for mutation, error in (
        ("duplicate_local", "duplicate"),
        ("duplicate_root", "duplicate"),
        ("unknown_root", "unknown|dangling"),
        ("unknown_shape", "shape"),
        ("bad_link_arity", "arity"),
        ("unknown_link", "unsupported expression link"),
        ("dangling_operand", "unknown expression link operand"),
        ("multi_root_with_link", "multi_root"),
        ("linked_without_link", "linked"),
        ("unknown_operator", "operator"),
        ("unknown_predicate", "authority ref"),
        ("wrong_predicate_kind", "incompatible kind"),
        ("unknown_role", "role"),
        ("unknown_filler", "filler kind"),
        ("literal_event_actor", "literal filler"),
        ("designation_non_string", "designation surface"),
        ("designation_empty", "designation surface"),
        ("dangling_proposition", "unknown proposition"),
        ("orphan", "non-root"),
        ("cycle", "cycle|parent"),
        ("integer_bool", "integer"),
        ("boolean_int", "boolean"),
        ("wrong_type_literal", "type role"),
        ("extra_application_field", "fields must match"),
        ("missing_link_field", "fields must match"),
        ("extra_filler_field", "fields must match"),
        ("over_role_bound", "role bound"),
        ("over_depth", "depth"),
        ("over_application_bound", "application"),
        ("over_link_bound", "link"),
        ("over_root_bound", "root"),
    ):
        _assert_composed_expression_rejects_noncanonical_graph(mutation, error)


def test_sr4_5_separate_assertions_and_conflicts_are_not_multi_root() -> None:
    ordinary = ReviewedScenario.from_dict(
        {
            "scenario_ref": "scenario:ordinary-all",
            "review_status": "reviewed",
            "competency_category": "relation",
            "semantic_assertions": [
                {
                    "kind": "relation",
                    "subject": "entity:alice",
                    "relation": "rel:likes",
                    "object": "entity:book",
                },
                {
                    "kind": "state",
                    "subject": "entity:lamp",
                    "dimension": "dim:power",
                    "value": "value:on",
                },
            ],
            "surface_examples": ["two claims"],
            "metadata": {},
        }
    )
    compiler = ExpectedCycleContractCompiler(_Authority(), abi_registry_ref="abi:test")
    contract = compiler.compile(
        scenario_ref=ordinary.scenario_ref,
        case_ref="case:ordinary-all",
        surface_ref="surface:ordinary-all",
        context_ref="context:test",
        assertions=ordinary.assertions,
        situation_constraints={},
        revision_pin=_pin(),
    )
    conflict = _compile(
        "conflict",
        {
            "subject": "entity:lamp",
            "dimension": "dim:power",
            "values": ["value:on", "value:off"],
        },
    )

    assert contract.expression_relation.value == "all"
    assert len(contract.expected_expressions) == 2
    assert all(len(row.root_refs) == 1 for row in contract.expected_expressions)
    assert conflict.expression_relation.value == "conflict"
    assert len(conflict.expected_expressions) == 2


def test_sr1_old_abi2_generic_gap_rows_fail_closed() -> None:
    with pytest.raises(ValueError, match="recommended owner mismatch"):
        ExpectedGapContract.from_dict(
            {
                "kind": "proposal",
                "status": "proposal_abstained",
                "recommended_owner": "training",
                "safe_response_action": "request_proposal_review",
                "error_code": "proposal:critical_residual",
            }
        )
    with pytest.raises(ValueError, match="unsupported expected gap kind"):
        ExpectedGapContract.from_dict(
            {
                "kind": "semantic",
                "status": "gap",
                "recommended_owner": "runtime",
                "safe_response_action": "stop_without_surface",
                "error_code": None,
            }
        )
