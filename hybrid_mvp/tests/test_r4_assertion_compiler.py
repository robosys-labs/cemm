"""R4 total assertion compiler tests."""
from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.authority import (
    AtomRecord,
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
                                                                                               'source_ast_sha256': 'ff58b764484269ed144a2771e1f3683f5cebc18c8470583c256dc6b554027320'},
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
                                                                                                               'source_ast_sha256': 'bd67178ca9b3635a3521e7117169aa17f59548e0a472ca2fe84c86da7e1090f0'},
 'tests/test_r4_assertion_compiler.py::test_compiler_resets_situated_state_between_cases': {'activation_phase': 'R4',
                                                                                            'assertion_ref': 'assertion:r4-compiler-resets-situated-state-between-cases',
                                                                                            'diagnostic_role': 'owner',
                                                                                            'introduced_by_task': 'R4-Complete',
                                                                                            'owner_ref': 'expected-contract',
                                                                                            'source_ast_sha256': '18044cd2bafe34c53b9f8f12b2cbe162fc35ad3502fb8077df57f58ecbd98ef6'}}



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
            "participant:user": "participant",
            "entity:a": "entity",
            "entity:b": "entity",
        }.items()
    }
    event_signatures = {
        "event:greeting": EventSignature(
            event_type="event:greeting",
            roles=(
                RoleSpec(role="role:actor", filler_kinds=(), required=False),
                RoleSpec(role="role:addressee", filler_kinds=(), required=False),
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
