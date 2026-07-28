from __future__ import annotations

import json
from pathlib import Path

import pytest

from cemm.activation import assert_native_semantic_activation
from cemm.learning_plans import (
    DESIGNATION_LEARNING_CONTRACT,
    LearningContractRegistry,
)
from cemm.proof import ProofEngine, VerifiedSemanticFocus
from cemm.semantic_contributions import SemanticAffordanceIndex
from cemm.semantic_description import SemanticDescriptionEngine
from cemm.store import Store
from cemm.runtime import Runtime

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "cemm" / "data" / "base.json"
FOUNDATION = ROOT / "cemm" / "data" / "conversation_foundation.json"
FORM = ROOT / "cemm" / "form_packs" / "en.json"
LANGUAGE = ROOT / "cemm" / "language_packs" / "en.json"


def build_runtime(tmp_path: Path) -> Runtime:
    store = Store(tmp_path / "cemm.sqlite")
    store.import_bundle((BASE, FOUNDATION))
    return Runtime(store, LANGUAGE)


def test_generated_assets_are_recursive_spine_clean():
    form = json.loads(FORM.read_text(encoding="utf-8"))
    source = json.loads(
        (ROOT / "cemm" / "training" / "en_form_schema_seed.json").read_text(
            encoding="utf-8"
        )
    )
    payload = json.dumps({"form": form, "source": source}, sort_keys=True)
    assert form["feature_algebra_version"] == 7
    assert source["version"] == 7
    assert source["contract_version"] == 7
    assert "semantic_port" not in payload
    assert "learning_operation" not in payload
    assert "resolve_designation" not in payload
    families = {item["family"] for item in form["schemas"]}
    assert "desire_knowledge_designation_query" not in families
    assert {
        "capability_inventory_query",
        "designation_learning_answer",
        "definition_designation_claim",
        "generic_type_predication",
        "generic_state_value_predication",
        "semantic_discourse_reaction",
    }.issubset(families)
    open_forms = {
        form_value
        for record in form["lexemes"]
        if record.get("features", {}).get("open_class")
        for form_value in record.get("forms", ())
    }
    assert open_forms.isdisjoint(set(form["function_forms"]))
    language = json.loads(LANGUAGE.read_text(encoding="utf-8"))
    assert open_forms.isdisjoint(set(language.get("function_forms", ())))
    interpreter_source = (ROOT / "cemm" / "interpreter.py").read_text(encoding="utf-8")
    assert "RecursiveCompositionChart" in interpreter_source
    assert 'pack.data.get("grammar_tokens")' not in interpreter_source
    assert 'pack.data.get("function_forms")' not in interpreter_source


def test_activation_attests_recursive_contracts_and_abis(tmp_path):
    runtime = build_runtime(tmp_path)
    attestation = assert_native_semantic_activation(runtime.i.form_pack, runtime.s)
    assert attestation["ok"] is True
    assert attestation["semantic_contribution_abi"] == 1
    assert attestation["learning_plan_abi"] == 1
    assert attestation["proposition_graph_abi"] == 2
    assert attestation["atomic_composition_abi"] == 1
    assert attestation["coverage_abi"] == 7
    assert attestation["feature_algebra_version"] == 7
    LearningContractRegistry(runtime.s, runtime.s.generation).get(
        DESIGNATION_LEARNING_CONTRACT
    )


def test_unknown_meaning_query_opens_typed_plan_then_commits_answer(tmp_path):
    runtime = build_runtime(tmp_path)
    first = runtime.process("What does glorp mean?")
    assert first["response_csir"]["action"] == "request_learning_evidence"
    qualifiers = first["response_csir"]["qualifiers"]
    assert qualifiers["learning_plan_ref"]
    assert qualifiers["learning_plan"]["contract_ref"] == DESIGNATION_LEARNING_CONTRACT
    assert qualifiers["learning_plan"]["authority_generation"] == int(
        runtime.runtime_attestation["authority_generation"]
    )
    assert "learning_operation" not in json.dumps(first)

    second = runtime.process("It means hi")
    assert second["status"] in {"learned", "answered", "resolved", "acknowledged"}
    assert runtime.dialogue_state.pending is None
    targets = runtime.s.db.execute(
        "SELECT target_ref FROM designation_index WHERE lower(surface)=lower(?)",
        ("glorp",),
    ).fetchall()
    assert {str(row[0]) for row in targets} == {"event:greeting"}


def test_direct_definition_uses_same_designation_substrate(tmp_path):
    runtime = build_runtime(tmp_path)
    result = runtime.process("glorp means hi")
    assert result["packet"]["apps"][0]["operator"] == "op:designation"
    rows = runtime.s.db.execute(
        "SELECT target_ref FROM designation_index WHERE lower(surface)=lower(?)",
        ("glorp",),
    ).fetchall()
    assert {str(row[0]) for row in rows} == {"event:greeting"}


def test_learned_synonym_inherits_target_affordance_without_pack_regeneration(tmp_path):
    runtime = build_runtime(tmp_path)
    before_hash = runtime.i.form_pack.hash
    runtime.process("glorp means hi")
    runtime.reload_authority()
    assert runtime.i.form_pack.hash == before_hash
    profiles = SemanticAffordanceIndex(runtime.s, runtime.s.generation).profiles_for(
        "event:greeting"
    )
    assert any(item.contribution_kind in {"predicate", "discourse"} for item in profiles)
    lattice = runtime.i.observe(
        "glorp", runtime.session.input_frame(source="user", channel="text")
    )
    units = [
        unit
        for hypothesis in lattice.resolved_form_lattice.grounding_hypotheses
        for unit in hypothesis.units
        if unit.semantic_ref == "event:greeting"
    ]
    assert units
    assert any(unit.features.get("semantic_contribution_abi") == 1 for unit in units)


def test_recursive_query_uses_app_valued_content_not_sentence_family(tmp_path):
    runtime = build_runtime(tmp_path)
    result = runtime.process("Do you want to know my name?", mode="read_only")
    assert result["interpretation"]["status"] == "resolved"
    query = result["packet"]["query"]
    assert query["qualifiers"]["query_kind"] == "embedded_proposition_query"
    restrictions = query["restrictions"]
    assert len(restrictions) >= 2
    assert all(item["operator"] in {"op:designation", "op:type", "op:relation", "op:state", "op:event"} for item in restrictions)
    app_values = [
        value
        for item in restrictions
        for value in item.get("args", {}).values()
        if isinstance(value, dict) and set(value) == {"app"}
    ]
    assert app_values
    assert all(item.get("application_ref") for item in restrictions)


def test_compiler_rejects_unlicensed_app_role(tmp_path):
    runtime = build_runtime(tmp_path)
    child_ref = "candidate:child"
    parent_ref = "candidate:parent"
    packet = {
        "force": "query",
        "query": {
            "restrictions": [
                {
                    "application_ref": child_ref,
                    "operator": "op:event",
                    "args": {
                        "role:event": "?child_event",
                        "role:type": "event:greeting",
                    },
                },
                {
                    "application_ref": parent_ref,
                    "operator": "op:event",
                    "args": {
                        "role:event": "?parent_event",
                        "role:type": "event:greeting",
                        "role:object": {"app": child_ref},
                    },
                },
            ],
            "variables": [
                {"ref": "?child_event", "filler_kind": "event"},
                {"ref": "?parent_event", "filler_kind": "event"},
            ],
            "projection": ["?parent_event"],
            "qualifiers": {"query_kind": "test"},
        },
    }
    with pytest.raises(ValueError, match="invalid filler"):
        runtime.i.compiler.compile(packet)


def test_semantic_description_is_bounded_and_proof_bearing(tmp_path):
    runtime = build_runtime(tmp_path)
    engine = SemanticDescriptionEngine(
        runtime.s, runtime.config, int(runtime.runtime_attestation["authority_generation"])
    )
    request = engine.request("event:learn")
    result = engine.describe(request)
    assert result.target_kind == "event_type"
    assert len(result.facts) <= request.max_facts
    assert result.preferred_surface
    assert result.claim_refs
    assert result.source_refs


def test_meaning_query_describes_a_grounded_designation(tmp_path):
    runtime = build_runtime(tmp_path)
    result = runtime.process("What does hi mean?", mode="read_only")

    assert result["interpretation"]["status"] == "resolved"
    assert result["description_result"]["target_ref"] == "event:greeting"
    assert result["query_result"]["qualifiers"]["query_kind"] == "semantic_description"
    assert result["response_csir"]["action"] == "describe_semantic_target"


def test_meaning_query_describes_a_learned_designation(tmp_path):
    runtime = build_runtime(tmp_path)
    runtime.process("glorp means hi")

    result = runtime.process("What does glorp mean?", mode="read_only")

    assert result["description_result"]["target_ref"] == "event:greeting"
    assert result["query_result"]["qualifiers"]["query_kind"] == "semantic_description"


def test_proof_focus_is_stale_after_world_revision_change(tmp_path):
    runtime = build_runtime(tmp_path)
    engine = ProofEngine(
        runtime.s, runtime.config, int(runtime.runtime_attestation["authority_generation"])
    )
    current = runtime.s.revisions()["world_revision"]
    focus = VerifiedSemanticFocus.create(
        focus_kind="query_result",
        response_ref="response:test",
        query_ref="query:test",
        world_revision=current + 1,
        authority_generation=int(runtime.runtime_attestation["authority_generation"]),
    )
    proof = engine.explain_focus(focus)
    assert proof.completeness == "stale"


def test_ambiguous_value_does_not_gain_bare_state_predicate(tmp_path):
    runtime = build_runtime(tmp_path)
    index = SemanticAffordanceIndex(runtime.s, runtime.s.generation)
    for value_ref in ("value:unknown",):
        dimensions = runtime.s.dimensions_for_value(value_ref)
        if len(dimensions) != 1:
            assert all(
                item.metadata.get("kernel_operator_ref") != "op:state"
                or item.contribution_kind != "predicate"
                for item in index.profiles_for(value_ref)
            )


def test_authority_reload_invalidates_generation_bound_learning_and_focus(tmp_path):
    runtime = build_runtime(tmp_path)
    first = runtime.process("What does glorp mean?")
    plan_ref = first["response_csir"]["qualifiers"]["learning_plan_ref"]
    assert runtime.dialogue_state.pending is not None
    receipt = runtime.reload_authority()
    assert receipt["invalidated_pending_learning_plan_ref"] == plan_ref
    assert runtime.dialogue_state.pending is None
    assert runtime.dialogue_state.verified_focus == ()


def test_cli_entrypoint_requires_native_activation():
    source = (ROOT / "cemm" / "cli.py").read_text(encoding="utf-8")
    assert "assert_native_semantic_activation" in source
    assert "instance.i.form_pack" in source
