from __future__ import annotations

import ast
from pathlib import Path

from cemm.v350.stage_contracts import (
    CoreStage, PersistenceClass, canonical_stage_contracts, stage_contract,
)
from cemm.v350.runtime_generations import GenerationDomain


ROOT = Path(__file__).resolve().parents[2]
EXPECTED = (
    "ORIENT_AND_PIN_SEMANTIC_BRAIN",
    "OBSERVE_MULTIMODAL_EVIDENCE",
    "ENCODE_FORM_AND_SENSOR_EVIDENCE",
    "ACTIVATE_AND_GROUND_REFERENTS",
    "PROJECT_ENTITLED_STATE_SPACES",
    "COMPILE_CANDIDATES_TO_CSIR",
    "RUN_RECURRENT_MEANING_DYNAMICS",
    "STABILIZE_SEMANTIC_ATTRACTORS",
    "BUILD_DISCOURSE_PROPOSITION_EVENT_AND_QUERY_STRUCTURES",
    "PLACE_EPISTEMIC_CONTEXT_AND_ASSIMILATE_WORLD_BELIEF",
    "QUERY_AND_EXPLAIN_FROM_GROUNDED_WORLD_MODEL",
    "CLASSIFY_PREDICTION_ERROR_AND_ADVANCE_LEARNING",
    "SIMULATE_CAUSAL_TRANSITIONS_AND_COUNTERFACTUALS",
    "COMMIT_AUTHORIZED_KNOWLEDGE_STATE_AND_LEARNING_ARTIFACTS",
    "PROPAGATE_CAPABILITY_IMPACT_AFFECT_AND_SIGNIFICANCE",
    "DERIVE_OBLIGATIONS_AND_ARBITRATE_GOALS",
    "PLAN_AUTHORIZE_EXECUTE_AND_OBSERVE",
    "ASSIMILATE_OPERATION_OUTCOMES_AND_RECUR",
    "CONSTRUCT_RESPONSE_CSIR",
    "REALIZE_TARGET_LANGUAGE_OR_MODALITY",
    "VERIFY_SEMANTIC_EQUIVALENCE_AND_AUTHORIZE_EMISSION",
    "COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND",
    "CONSOLIDATE_INVALIDATE_REPLAY_AND_FINALIZE",
)


def test_stage_abi_matches_core_loop_exactly():
    assert tuple(stage.name for stage in CoreStage) == EXPECTED
    assert tuple(c.stage for c in canonical_stage_contracts()) == tuple(CoreStage)


def test_stages_5_6_7_are_real_csir_recurrent_attractor_contracts_not_renames():
    c5 = stage_contract(CoreStage.COMPILE_CANDIDATES_TO_CSIR)
    c6 = stage_contract(CoreStage.RUN_RECURRENT_MEANING_DYNAMICS)
    c7 = stage_contract(CoreStage.STABILIZE_SEMANTIC_ATTRACTORS)
    assert "csir_candidates" in c5.produced_outputs
    assert "activation_graph" in c6.produced_outputs
    assert "semantic_attractors" in c7.produced_outputs
    text = " ".join((*c5.produced_outputs, *c6.produced_outputs, *c7.produced_outputs)).lower()
    assert "uol" not in text and "factor_graph" not in text and "meaning_bundle" not in text


def test_persistence_matrix_matches_runtime_plan_workspace_defaults():
    for stage in (
        CoreStage.PROPAGATE_CAPABILITY_IMPACT_AFFECT_AND_SIGNIFICANCE,
        CoreStage.DERIVE_OBLIGATIONS_AND_ARBITRATE_GOALS,
        CoreStage.CONSTRUCT_RESPONSE_CSIR,
        CoreStage.REALIZE_TARGET_LANGUAGE_OR_MODALITY,
    ):
        assert stage_contract(stage).persistence is PersistenceClass.OPTIONAL_AUDIT
        assert GenerationDomain.WORLD not in stage_contract(stage).allowed_generation_changes
        assert GenerationDomain.AUTHORITY not in stage_contract(stage).allowed_generation_changes


def test_canonical_runtime_has_no_uol_or_composition_imports():
    path = ROOT / "cemm/v350/runtime_v351.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.append("." * node.level + (node.module or ""))
        elif isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
    assert not any("v347" in name or ".uol" in name for name in names)


def test_old_stage_tokens_absent_from_canonical_runtime_graph():
    text = (ROOT / "cemm/v350/runtime_graph.py").read_text(encoding="utf-8")
    for token in (
        "BUILD_UOL_FACTOR_GRAPH", "SOLVE_MEANING_HYPOTHESES",
        "SELECT_MEANING_BUNDLE", "BUILD_RESPONSE_UOL",
    ):
        assert token not in text


def test_stage22_does_not_publish_authority_inside_active_semantic_pass():
    contract = stage_contract(CoreStage.CONSOLIDATE_INVALIDATE_REPLAY_AND_FINALIZE)
    assert GenerationDomain.AUTHORITY not in contract.allowed_generation_changes
    assert GenerationDomain.AUDIT in contract.allowed_generation_changes


def test_every_stage_contract_has_stable_manifest_fingerprint():
    fingerprints = [item.fingerprint for item in canonical_stage_contracts()]
    assert len(fingerprints) == 23
    assert len(set(fingerprints)) == 23
    assert all(value.startswith("stage-contract-v351:") for value in fingerprints)


def test_stage_adapters_are_explicit_classes_not_generated_with_type_factory():
    source = (ROOT / "cemm/v350/stage_adapters.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    adapter_classes = [
        node for node in tree.body
        if isinstance(node, ast.ClassDef)
        and any(
            isinstance(base, ast.Name) and base.id == "_ConcreteStageAdapter"
            for base in node.bases
        )
    ]
    assert len(adapter_classes) == 23
    assert "type(" not in source.replace("{type(result).__name__}", "")
