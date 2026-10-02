"""Development presentation controls: actual public sources, no output gold."""
from pathlib import Path
import json
import shutil
from dataclasses import replace
import pytest

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.development_reference import _EnglishGraph, _CannotPresent
from cemm_authoritative_hybrid.expressions import (
    SemanticExpression, SemanticApplication, RoleBinding, GroundedReference,
    LiteralValue, ScopeOperator, ExpressionLink, VariableBinder, BoundVariable,
)

ROOT = Path(__file__).resolve().parents[1]

__cemm_test_inventory__ = {
    "tests/test_foundation_development_reference.py::test_public_reference_preserves_meaning[type]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-public-reference-preserves-meaning-type",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "f3aaa489ce1cdd3d493848288fc37ce56f14f0ae5348c037c959f251f8254287",
    },
    "tests/test_foundation_development_reference.py::test_public_reference_preserves_meaning[negative]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-public-reference-preserves-meaning-negative",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "f3aaa489ce1cdd3d493848288fc37ce56f14f0ae5348c037c959f251f8254287",
    },
    "tests/test_foundation_development_reference.py::test_public_reference_preserves_meaning[speaker]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-public-reference-preserves-meaning-speaker",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "f3aaa489ce1cdd3d493848288fc37ce56f14f0ae5348c037c959f251f8254287",
    },
    "tests/test_foundation_development_reference.py::test_public_reference_preserves_meaning[addressee]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-public-reference-preserves-meaning-addressee",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "f3aaa489ce1cdd3d493848288fc37ce56f14f0ae5348c037c959f251f8254287",
    },
    "tests/test_foundation_development_reference.py::test_public_reference_preserves_meaning[forward]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-public-reference-preserves-meaning-forward",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "f3aaa489ce1cdd3d493848288fc37ce56f14f0ae5348c037c959f251f8254287",
    },
    "tests/test_foundation_development_reference.py::test_public_reference_preserves_meaning[reverse]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-public-reference-preserves-meaning-reverse",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "f3aaa489ce1cdd3d493848288fc37ce56f14f0ae5348c037c959f251f8254287",
    },
    "tests/test_foundation_development_reference.py::test_public_reference_preserves_meaning[state]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-public-reference-preserves-meaning-state",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "f3aaa489ce1cdd3d493848288fc37ce56f14f0ae5348c037c959f251f8254287",
    },
    "tests/test_foundation_development_reference.py::test_public_reference_preserves_meaning[nested]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-public-reference-preserves-meaning-nested",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "f3aaa489ce1cdd3d493848288fc37ce56f14f0ae5348c037c959f251f8254287",
    },
    "tests/test_foundation_development_reference.py::test_public_reference_preserves_meaning[teaching]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-public-reference-preserves-meaning-teaching",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "f3aaa489ce1cdd3d493848288fc37ce56f14f0ae5348c037c959f251f8254287",
    },
    "tests/test_foundation_development_reference.py::test_reference_conditions_do_not_invent_outcomes[lexical]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-reference-conditions-do-not-invent-outcomes-lexical",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "659cdbe91f8bc62627e4405c5ebf1d35055fd1540bcf7d719852deda759c97dd",
    },
    "tests/test_foundation_development_reference.py::test_reference_conditions_do_not_invent_outcomes[noop]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-reference-conditions-do-not-invent-outcomes-noop",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "659cdbe91f8bc62627e4405c5ebf1d35055fd1540bcf7d719852deda759c97dd",
    },
    "tests/test_foundation_development_reference.py::test_reference_conditions_do_not_invent_outcomes[ambiguous]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-reference-conditions-do-not-invent-outcomes-ambiguous",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "659cdbe91f8bc62627e4405c5ebf1d35055fd1540bcf7d719852deda759c97dd",
    },
    "tests/test_foundation_development_reference.py::test_reference_conditions_do_not_invent_outcomes[proposal-gap]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-reference-conditions-do-not-invent-outcomes-proposal-gap",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "659cdbe91f8bc62627e4405c5ebf1d35055fd1540bcf7d719852deda759c97dd",
    },
    "tests/test_foundation_development_reference.py::test_component_signed_response_maps_actual_claims[support]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-component-signed-response-maps-actual-claims-support",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "3d041bd7be2478b2efd5a046c14cf701a103720075391172754c3b43793ff1b0",
    },
    "tests/test_foundation_development_reference.py::test_component_signed_response_maps_actual_claims[denial]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-component-signed-response-maps-actual-claims-denial",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "3d041bd7be2478b2efd5a046c14cf701a103720075391172754c3b43793ff1b0",
    },
    "tests/test_foundation_development_reference.py::test_component_signed_response_maps_actual_claims[conflict]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-component-signed-response-maps-actual-claims-conflict",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "3d041bd7be2478b2efd5a046c14cf701a103720075391172754c3b43793ff1b0",
    },
    "tests/test_foundation_development_reference.py::test_component_signed_response_maps_actual_claims[missing]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-component-signed-response-maps-actual-claims-missing",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "3d041bd7be2478b2efd5a046c14cf701a103720075391172754c3b43793ff1b0",
    },
    "tests/test_foundation_development_reference.py::test_component_signed_response_maps_actual_claims[definition-missing]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-component-signed-response-maps-actual-claims-definition-missing",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "3d041bd7be2478b2efd5a046c14cf701a103720075391172754c3b43793ff1b0",
    },
    "tests/test_foundation_development_reference.py::test_recursive_reference_preserves_nested_and_object_roles[nested-negative]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-recursive-reference-preserves-nested-and-object-roles-nested-negative",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "a4d6419b148d5eaf31287701b57c03c29bc721a487630ed73637826073822063",
    },
    "tests/test_foundation_development_reference.py::test_recursive_reference_preserves_nested_and_object_roles[nested-relation]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-recursive-reference-preserves-nested-and-object-roles-nested-relation",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "a4d6419b148d5eaf31287701b57c03c29bc721a487630ed73637826073822063",
    },
    "tests/test_foundation_development_reference.py::test_recursive_reference_preserves_nested_and_object_roles[owns]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-recursive-reference-preserves-nested-and-object-roles-owns",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "a4d6419b148d5eaf31287701b57c03c29bc721a487630ed73637826073822063",
    },
    "tests/test_foundation_development_reference.py::test_reference_rejects_substituted_actual_sources[source]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-reference-rejects-substituted-actual-sources-source",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "252340a8091019c3680d57d009301bfa803b4e242990cc035988cf22859d75d9",
    },
    "tests/test_foundation_development_reference.py::test_reference_rejects_substituted_actual_sources[effect]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-reference-rejects-substituted-actual-sources-effect",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "252340a8091019c3680d57d009301bfa803b4e242990cc035988cf22859d75d9",
    },
    "tests/test_foundation_development_reference.py::test_reference_rejects_substituted_actual_sources[response]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-reference-rejects-substituted-actual-sources-response",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "252340a8091019c3680d57d009301bfa803b4e242990cc035988cf22859d75d9",
    },
    "tests/test_foundation_development_reference.py::test_reference_rejects_substituted_actual_sources[profile]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-reference-rejects-substituted-actual-sources-profile",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "252340a8091019c3680d57d009301bfa803b4e242990cc035988cf22859d75d9",
    },
    "tests/test_foundation_development_reference.py::test_reference_uses_single_pinned_batch_and_never_enumerates_atoms": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-reference-uses-single-pinned-batch-and-never-enumerates-atoms",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "cda108f139d0788a9ead027a16498c6cd73f03686f74e0e57b980f60f7c6e332",
    },
    "tests/test_foundation_development_reference.py::test_component_unsupported_structure_never_omits_semantics[label]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-component-unsupported-structure-never-omits-semantics-label",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "05aa090ea85447f37a380f169a0e13ffdee64a08579701de8701c104c39ac025",
    },
    "tests/test_foundation_development_reference.py::test_component_unsupported_structure_never_omits_semantics[qualifier]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-component-unsupported-structure-never-omits-semantics-qualifier",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "05aa090ea85447f37a380f169a0e13ffdee64a08579701de8701c104c39ac025",
    },
    "tests/test_foundation_development_reference.py::test_component_unsupported_structure_never_omits_semantics[scope]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-component-unsupported-structure-never-omits-semantics-scope",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "05aa090ea85447f37a380f169a0e13ffdee64a08579701de8701c104c39ac025",
    },
    "tests/test_foundation_development_reference.py::test_component_unsupported_structure_never_omits_semantics[binder]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-component-unsupported-structure-never-omits-semantics-binder",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "05aa090ea85447f37a380f169a0e13ffdee64a08579701de8701c104c39ac025",
    },
    "tests/test_foundation_development_reference.py::test_component_unsupported_structure_never_omits_semantics[role]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-component-unsupported-structure-never-omits-semantics-role",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "05aa090ea85447f37a380f169a0e13ffdee64a08579701de8701c104c39ac025",
    },
    "tests/test_foundation_development_reference.py::test_cli_development_reference_is_explicit_and_isolated[concise]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-cli-development-reference-is-explicit-and-isolated-concise",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "51c1031b3f2120481a49a0b6f07ee4c581fde0d7eebae4d1c9c94ea89de1bcdb",
    },
    "tests/test_foundation_development_reference.py::test_cli_development_reference_is_explicit_and_isolated[trace]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-cli-development-reference-is-explicit-and-isolated-trace",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "51c1031b3f2120481a49a0b6f07ee4c581fde0d7eebae4d1c9c94ea89de1bcdb",
    },
    "tests/test_foundation_development_reference.py::test_component_output_perspective_uses_original_situation[agreement]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-component-output-perspective-uses-original-situation-agreement",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "f29c1546d3595928be26cdfa0932c3b7092be7d16dcece277fbf572744071e2d",
    },
    "tests/test_foundation_development_reference.py::test_component_output_perspective_uses_original_situation[object]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-component-output-perspective-uses-original-situation-object",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "f29c1546d3595928be26cdfa0932c3b7092be7d16dcece277fbf572744071e2d",
    },
    "tests/test_foundation_development_reference.py::test_component_output_perspective_uses_original_situation[both]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-component-output-perspective-uses-original-situation-both",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "f29c1546d3595928be26cdfa0932c3b7092be7d16dcece277fbf572744071e2d",
    },
    "tests/test_foundation_development_reference.py::test_default_cli_remains_exact_cycle_json": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-default-cli-remains-exact-cycle-json",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "269c95adc46ffa0553529aa026005f0be1043dc5a14a8da20352b13c198a4b93",
    },
    "tests/test_foundation_development_reference.py::test_component_request_wrapper_preserves_same_graph_outcome_distinctions[unknown]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-component-request-wrapper-preserves-same-graph-outcome-distinctions-unknown",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "6b5f5dbec1ea8ada14340fca66a002a0b7c37edd82b29f942a121848af613809",
    },
    "tests/test_foundation_development_reference.py::test_component_request_wrapper_preserves_same_graph_outcome_distinctions[denied]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-component-request-wrapper-preserves-same-graph-outcome-distinctions-denied",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "6b5f5dbec1ea8ada14340fca66a002a0b7c37edd82b29f942a121848af613809",
    },
    "tests/test_foundation_development_reference.py::test_component_request_wrapper_preserves_same_graph_outcome_distinctions[failed]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-component-request-wrapper-preserves-same-graph-outcome-distinctions-failed",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "6b5f5dbec1ea8ada14340fca66a002a0b7c37edd82b29f942a121848af613809",
    },
    "tests/test_foundation_development_reference.py::test_component_request_wrapper_preserves_same_graph_outcome_distinctions[bounded]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-component-request-wrapper-preserves-same-graph-outcome-distinctions-bounded",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "6b5f5dbec1ea8ada14340fca66a002a0b7c37edd82b29f942a121848af613809",
    },
    "tests/test_foundation_development_reference.py::test_component_request_wrapper_preserves_same_graph_outcome_distinctions[effect-denied]": {
        "activation_phase": "R4", "assertion_ref": "assertion:foundation-development-component-request-wrapper-preserves-same-graph-outcome-distinctions-effect-denied",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-7", "owner_ref": "runtime-path",
        "source_ast_sha256": "6b5f5dbec1ea8ada14340fca66a002a0b7c37edd82b29f942a121848af613809",
    },
}

@pytest.mark.parametrize("source,content", (
    ("Alice is a mother", "Alice is a mother"),
    ("Alice is not a mother", "not (Alice is a mother)"),
    ("I am a mother", "you are a mother"),
    ("You are a mother", "I am a mother"),
    ("Alice likes Bob", "Alice likes Bob"),
    ("Bob likes Alice", "Bob likes Alice"),
    ("server is offline", "the server's availability is offline"),
    ("Mary said Bob left", "saying by Mary with content (departure by Bob)"),
    ("yoz means hello", "\"yoz\" means greetings"),
), ids=("type", "negative", "speaker", "addressee", "forward", "reverse", "state", "nested", "teaching"))
def test_public_reference_preserves_meaning(tmp_path, source, content):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "reference.db")
    try:
        cycle = runtime.process("session:reference", source)
        before = runtime.stores.revision_pin()
        assert callable(getattr(runtime, "development_reference", None)), "development presentation owner missing"
        output = runtime.development_reference(cycle)
        assert output.surface == "Unverified claim: " + content + "."
        assert output.cycle_ref == cycle.cycle_ref
        assert output.response_meaning_ref == cycle.response_meaning.response_meaning_ref
        assert output.gap_ref == cycle.gap_receipt.gap_ref
        assert output.limitations == ()
        assert output.designation_provenance
        assert output.output_rule_refs
        assert output.slot_coverage
        assert runtime.stores.revision_pin() == before
        assert cycle.realization_receipt is None
        assert cycle.gap_receipt.status == "later_owner_not_admitted"
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("source,expected", (
    ("what does yoz mean", 'Meaning unknown. What does "yoz" mean?'),
    ("turn lamp on", 'Unknown; no action completed; requested: setting by me with dimension power with target the lamp with value on.'),
    ("what is Alice", 'Meaning is ambiguous. Clarify the reference.'),
    ("describe Alice", 'Meaning is unresolved. Review the interpretation.'),
), ids=("lexical", "noop", "ambiguous", "proposal-gap"))
def test_reference_conditions_do_not_invent_outcomes(tmp_path, source, expected):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "conditions.db")
    try:
        cycle = runtime.process("session:conditions", source)
        output = runtime.development_reference(cycle)
        assert output.surface == expected
        if cycle.response_meaning is None:
            assert output.response_meaning_ref is None
            assert output.limitations[0].kind == "early_gap_without_response_meaning"
            assert "yoz" not in output.surface
        assert cycle.realization_receipt is None
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("stances,content", (
    (("support",), "description"), (("deny",), "description"),
    (("support", "deny"), "description"), ((), "description"),
    (("support",), "definition"),
), ids=("support", "denial", "conflict", "missing", "definition-missing"))
def test_component_signed_response_maps_actual_claims(tmp_path, stances, content):
    # Isolated component fixture: one explicit configured content-reading;
    # no live authority publication, grants or bare-question default.
    from tests.test_foundation_description_builder import _description_expression, _seed_reviewed_generic_claim
    shutil.copytree(ROOT / "data", tmp_path / "data")
    path = tmp_path / "data/languages/en/forms.json"
    pack = json.loads(path.read_text(encoding="utf-8"))
    pack["application_role_orders"]["content_target_projection"]["result"]["requested_contents"] = [content]
    path.write_text(json.dumps(pack), encoding="utf-8")
    runtime = load_runtime(tmp_path, profile="development", store_path=tmp_path / "signed.db")
    try:
        for index, stance in enumerate(stances):
            _seed_reviewed_generic_claim(runtime.stores, _description_expression(), stance=stance,
                fact_ref=f"fact:component-{index}", source_ref=f"source:opaque-{index}",
                decision_ref=f"decision:component-{index}", occurrence_ref=f"occurrence:component-{index}")
        cycle = runtime.process("session:signed", "what is Alice")
        assert cycle.response_meaning is not None
        before = runtime.stores.revision_pin()
        output = runtime.development_reference(cycle)
        bundle = cycle.response_meaning.description_proof
        assert output.surface and not output.limitations
        if len(stances) == 1 and content == "description":
            verb = "supports" if stances == ("support",) else "denies"
            assert output.surface == f"Evidence [1] {verb}: Alice is a mother."
            assert output.evidence_sources == ((1, "source:opaque-0"),)
            assert bundle.application_refs[0] == bundle.claims[0].application_ref
        else:
            assert "description of Alice" in output.surface or "definition of Alice" in output.surface
            assert "Alice is a mother" not in output.surface
        assert bundle.revision_pin == cycle.evaluation.revision_pin
        assert runtime.stores.revision_pin() == before
        assert cycle.realization_receipt is None
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("source,fragment", (
    ("Mary said Bob is not a mother", "saying by Mary with content (not (Bob is a mother))"),
    ("Mary said Alice likes Bob", "saying by Mary with content (Alice likes Bob)"),
    ("Alice owns book", "Alice owns the book"),
), ids=("nested-negative", "nested-relation", "owns"))
def test_recursive_reference_preserves_nested_and_object_roles(tmp_path, source, fragment):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "roles.db")
    try:
        cycle = runtime.process("session:roles", source)
        output = runtime.development_reference(cycle)
        assert output.surface == "Unverified claim: " + fragment + "."
        expression = cycle.response_meaning.response_expression
        for app in expression.applications:
            assert (app.application_ref, "predicate") in output.slot_coverage
            for role in app.roles:
                assert (app.application_ref, role.role_ref) in output.slot_coverage
        assert "said" not in output.surface and "left" not in output.surface
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("corruption", ("source", "effect", "response", "foreign-profile"),
    ids=("source", "effect", "response", "profile"))
def test_reference_rejects_substituted_actual_sources(tmp_path, corruption):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "tamper.db")
    try:
        first = runtime.process("session:tamper", "Alice likes Bob")
        second = runtime.process("session:tamper", "Bob likes Alice")
        if corruption == "foreign-profile":
            runtime._profile = "release"
        else:
            field, value = {"source": ("evaluation", second.evaluation),
                "effect": ("effect_receipt", second.effect_receipt),
                "response": ("response_meaning", second.response_meaning)}[corruption]
            object.__setattr__(first, field, value)
        with pytest.raises((ValueError, TypeError)):
            runtime.development_reference(first)
    finally:
        runtime.stores.close()


def test_reference_uses_single_pinned_batch_and_never_enumerates_atoms(tmp_path, monkeypatch):
    from contextlib import contextmanager
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "bounded.db")
    try:
        cycle = runtime.process("session:bounded", "Mary said Alice likes Bob")
        reader = runtime._owners["orientation"]._designation_reader
        original = reader.batch
        pins = []
        @contextmanager
        def batch(pin):
            pins.append(pin)
            with original(pin) as result:
                yield result
        monkeypatch.setattr(reader, "batch", batch)
        def forbidden(*args, **kwargs):
            raise AssertionError("whole-store or atom enumeration is forbidden")
        monkeypatch.setattr(runtime.stores.world, "verify", forbidden)
        before = runtime.stores.revision_pin()
        focus = runtime.stores.focus.revision
        assert runtime.development_reference(cycle).surface
        assert pins == [cycle.final_revision_pin]
        monkeypatch.setattr(type(runtime.authority.designations), "bounded_facts", forbidden)
        assert runtime.development_reference(cycle).surface
        assert pins == [cycle.final_revision_pin, cycle.final_revision_pin]
        assert runtime.stores.revision_pin() == before
        assert runtime.stores.focus.revision == focus
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("mutation", ("missing-label", "qualifier", "scope", "binder", "extra-role"),
    ids=("label", "qualifier", "scope", "binder", "role"))
def test_component_unsupported_structure_never_omits_semantics(tmp_path, mutation):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "unsupported.db")
    try:
        cycle = runtime.process("session:unsupported", "Alice is a mother")
        app = cycle.evaluation.expression.applications[0]
        kwargs = dict(applications=(app,), root_refs=(app.application_ref,))
        if mutation == "missing-label":
            app = replace(app, predicate_ref="concept:person", roles=(RoleBinding("role:instance", GroundedReference("entity:alice")), RoleBinding("role:class", GroundedReference("concept:person"))))
            kwargs["applications"] = (app,)
        elif mutation == "qualifier":
            kwargs["applications"] = (replace(app, qualifiers=(RoleBinding("role:owner", LiteralValue("string", "do not omit")),)),)
        elif mutation == "scope":
            scope = ScopeOperator("scope:unsupported", "scope:aspect", "scope_value:aspect:ongoing", app.application_ref)
            kwargs.update(scope_operators=(scope,), root_refs=(scope.scope_ref,))
        elif mutation == "binder":
            app = replace(app, roles=(RoleBinding("role:instance", BoundVariable("?who")), RoleBinding("role:class", GroundedReference("concept:mother"))))
            # Simple type-instance questions are now licensed. Keep this negative
            # assertion about unsupported binder semantics with a scoped body;
            # removing its polarity would change the question's meaning.
            scope = ScopeOperator("scope:bound-negative", "scope:polarity", "scope_value:polarity:negative", app.application_ref)
            binder = VariableBinder("binder:who", "?who", scope.scope_ref)
            kwargs.update(applications=(app,), scope_operators=(scope,), binders=(binder,), root_refs=(binder.binder_ref,))
        else:
            kwargs["applications"] = (replace(app, roles=(*app.roles, RoleBinding("role:owner", GroundedReference("entity:bob")))),)
        expression = SemanticExpression.create(**kwargs)
        reader = runtime._owners["orientation"]._designation_reader
        with reader.batch(cycle.final_revision_pin) as batch:
            renderer = _EnglishGraph(batch, cycle.evaluation.situation, [], [], [])
            with pytest.raises(_CannotPresent):
                renderer.graph(expression)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("trace", (False, True), ids=("concise", "trace"))
def test_cli_development_reference_is_explicit_and_isolated(tmp_path, monkeypatch, capsys, trace):
    import sys
    from cemm_authoritative_hybrid import cli
    monkeypatch.setattr(cli, "DEMO_TURNS", ("Alice likes Bob",))
    args = ("cemm", "--root", str(ROOT), "--demo",
        "--store", str(tmp_path / "cli.db"), "--development-reference")
    monkeypatch.setattr(sys, "argv", (*args, "--trace") if trace else args)
    cli.main()
    text = capsys.readouterr().out
    assert "CEMM (development reference): Unverified claim: Alice likes Bob." in text
    assert ('"development_only": true' in text) is trace
    assert ('"realization_receipt": null' in text) is trace
    assert ('"cycle_ref"' in text) is trace


@pytest.mark.parametrize("subject,object_ref,expected", (
    ("participant:user", "entity:bob", "you like Bob"),
    ("entity:bob", "participant:system", "Bob likes me"),
    ("participant:system", "participant:user", "I like you"),
), ids=("agreement", "object", "both"))
def test_component_output_perspective_uses_original_situation(tmp_path, subject, object_ref, expected):
    # Independently specified canonical graph, not a claim that the public
    # participant-object input construction is implemented.
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "perspective.db")
    try:
        cycle = runtime.process("session:perspective", "Alice likes Bob")
        app = SemanticApplication("app:test", "op:relation", "rel:likes", (
            RoleBinding("role:subject", GroundedReference(subject)),
            RoleBinding("role:object", GroundedReference(object_ref))))
        expression = SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))
        with runtime._owners["orientation"]._designation_reader.batch(cycle.final_revision_pin) as batch:
            renderer = _EnglishGraph(batch, cycle.evaluation.situation, [], [], [])
            assert renderer.graph(expression) == expected
    finally:
        runtime.stores.close()


def test_default_cli_remains_exact_cycle_json(tmp_path, monkeypatch, capsys):
    from cemm_authoritative_hybrid import cli
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "default.db")
    try:
        monkeypatch.setattr(cli, "DEMO_TURNS", ("Alice is a mother",))
        cycles = cli.demo(runtime)
        text = capsys.readouterr().out.split("\n", 1)[1]
        assert json.loads(text) == cycles[0].as_dict()
        assert "development_only" not in text
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("epistemic,status,discourse,expected", (
    ("epistemic_status:unknown", "unknown", "unknown", "Unknown; no action completed; requested: "),
    ("epistemic_status:denied", "denied", "deny", "Denied; no action completed; requested: "),
    ("epistemic_status:pending", "denied", "acknowledge_operation", "Denied; Pending; no action completed; requested: "),
    ("epistemic_status:unknown", "operation_failed", "acknowledge_operation", "Failed; Unknown; no action completed; requested: "),
    ("epistemic_status:unknown", "budget_exhausted", "report_gap", "Evidence bound exceeded; Unknown; no action completed; requested: "),
), ids=("unknown", "denied", "effect-denied", "failed", "bounded"))
def test_component_request_wrapper_preserves_same_graph_outcome_distinctions(tmp_path, epistemic, status, discourse, expected):
    from dataclasses import fields
    from cemm_authoritative_hybrid.cycle import CycleStatus
    from cemm_authoritative_hybrid.r3_response import ResponseMeaning
    from cemm_authoritative_hybrid import development_reference
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "wrapper.db")
    try:
        actual = runtime.process("session:wrapper", "turn lamp on").response_meaning
        # Output-grammar component records, not altered public decisions,
        # effects or evidence. Same canonical request graph/count in each.
        values = {f.name: getattr(actual, f.name) for f in fields(actual)
            if f.name not in {"abi_version", "response_meaning_ref"}}
        values.update(epistemic_status_ref=epistemic, cycle_status=CycleStatus(status), discourse_action=discourse)
        response = ResponseMeaning.create(**values)
        assert response.response_expression == actual.response_expression
        assert callable(getattr(development_reference, "_request_prefix", None)), "situated request wrapper missing"
        assert development_reference._request_prefix(response) == expected
    finally:
        runtime.stores.close()
