"""Independent foundation containment, not completed definition/query support.

Registry metadata and type membership do not answer requests for descriptive
content. These regressions deliberately do not use bootstrap output as gold.
The useful definition/projection and response obligations remain open.
"""
from __future__ import annotations

from dataclasses import fields
import json
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.affordances import SemanticAffordanceIndex
from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.cycle import SemanticMode
from cemm_authoritative_hybrid.expression_projection import project_expression
from cemm_authoritative_hybrid.expressions import (
    BoundVariable,
    GroundedReference,
    LiteralValue,
    RoleBinding,
    SemanticApplication,
    SemanticExpression,
    VariableBinder,
)
from cemm_authoritative_hybrid.forms import FormResolver
from cemm_authoritative_hybrid.persistence import Fact, RevisionPin, memory_stores
from cemm_authoritative_hybrid.proposal_context import (
    ContributionSlot, ProposalContext, ProposalContextBuilder, VariableSlot,
    _variable_slots,
)
from cemm_authoritative_hybrid.r3_artifacts import QueryStatus
from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
from cemm_authoritative_hybrid.r3_effects import NoEffectReceipt
from cemm_authoritative_hybrid.r4_contracts import (
    AssertionCompilerError,
    ExpectedCycleContractCompiler,
    ReviewedScenario,
)
from cemm_authoritative_hybrid.r4_pipeline import load_reviewed_scenarios
from cemm_authoritative_hybrid.situation import SituationContext
from cemm_authoritative_hybrid.verifier import ExactProgramVerifier

ROOT = Path(__file__).parents[1]

__cemm_test_inventory__ = {
    "tests/test_foundation_semantics.py::test_public_question_never_substitutes_registry_kind[what-cemm]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-public-question-never-substitutes-registry-kind-what-cemm",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "6f2c1e07f92ddd308036e6900d561f1976e906fa1bf4446869e538b2d78acbd1"
    },
    "tests/test_foundation_semantics.py::test_public_question_never_substitutes_registry_kind[who-cemm]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-public-question-never-substitutes-registry-kind-who-cemm",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "6f2c1e07f92ddd308036e6900d561f1976e906fa1bf4446869e538b2d78acbd1"
    },
    "tests/test_foundation_semantics.py::test_public_question_never_substitutes_registry_kind[where-cemm]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-public-question-never-substitutes-registry-kind-where-cemm",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "6f2c1e07f92ddd308036e6900d561f1976e906fa1bf4446869e538b2d78acbd1"
    },
    "tests/test_foundation_semantics.py::test_public_question_never_substitutes_registry_kind[define-mother]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-public-question-never-substitutes-registry-kind-define-mother",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "6f2c1e07f92ddd308036e6900d561f1976e906fa1bf4446869e538b2d78acbd1"
    },
    "tests/test_foundation_semantics.py::test_public_question_never_substitutes_registry_kind[what-mother]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-public-question-never-substitutes-registry-kind-what-mother",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "6f2c1e07f92ddd308036e6900d561f1976e906fa1bf4446869e538b2d78acbd1"
    },
    "tests/test_foundation_semantics.py::test_definition_does_not_substitute_a_known_type_member[define-mother]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-definition-does-not-substitute-a-known-type-member-define-mother",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "0813e012b4caaea8f9a4758a39b20ffdb72464d7e89a8d72ffa112d36347dfd4"
    },
    "tests/test_foundation_semantics.py::test_definition_does_not_substitute_a_known_type_member[what-mother]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-definition-does-not-substitute-a-known-type-member-what-mother",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "0813e012b4caaea8f9a4758a39b20ffdb72464d7e89a8d72ffa112d36347dfd4"
    },
    "tests/test_foundation_semantics.py::test_retired_definition_form_cue_stays_unresolved[bare]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-retired-definition-form-cue-stays-unresolved-bare",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "ea8fa35204d3ab3fd0c50f110c3cedb50ec919030ae8f7a60a5f09fe8b3e9e3a"
    },
    "tests/test_foundation_semantics.py::test_retired_definition_form_cue_stays_unresolved[following-clause]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-retired-definition-form-cue-stays-unresolved-following-clause",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "ea8fa35204d3ab3fd0c50f110c3cedb50ec919030ae8f7a60a5f09fe8b3e9e3a"
    },
    "tests/test_foundation_semantics.py::test_retired_definition_form_cue_stays_unresolved[preceding-clause]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-retired-definition-form-cue-stays-unresolved-preceding-clause",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "ea8fa35204d3ab3fd0c50f110c3cedb50ec919030ae8f7a60a5f09fe8b3e9e3a"
    },
    "tests/test_foundation_semantics.py::test_context_rejects_variable_sources_without_exact_query_ownership[nominal]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-context-rejects-variable-sources-without-exact-query-ownership-nominal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "625d23c57b37ec1fb1db9231945155a745d4363cedd37d91f99901bf142a0348"
    },
    "tests/test_foundation_semantics.py::test_context_rejects_variable_sources_without_exact_query_ownership[binder-only]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-context-rejects-variable-sources-without-exact-query-ownership-binder-only",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "625d23c57b37ec1fb1db9231945155a745d4363cedd37d91f99901bf142a0348"
    },
    "tests/test_foundation_semantics.py::test_context_rejects_variable_sources_without_exact_query_ownership[query-plus-nominal]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-context-rejects-variable-sources-without-exact-query-ownership-query-plus-nominal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "625d23c57b37ec1fb1db9231945155a745d4363cedd37d91f99901bf142a0348"
    },
    "tests/test_foundation_semantics.py::test_verifier_reconstructs_variable_source_ownership_after_context_forgery": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-verifier-reconstructs-variable-source-ownership-after-context-forgery",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "exact-verifier",
        "source_ast_sha256": "2c87c95ee8c2e1a6fcd686eba7ca6db996e188d9a6caca5ae409e5a9cd4f37e5"
    },
    "tests/test_foundation_semantics.py::test_retired_definition_cannot_forge_a_variable_from_unresolved_source": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-retired-definition-cannot-forge-a-variable-from-unresolved-source",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "eb97dc00e6a5fcec60d53a871771a737141c1a38d5fefb3c20e42e867b65488d"
    },
    "tests/test_foundation_semantics.py::test_reviewed_interrogatives_keep_open_variable_sources[english]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-reviewed-interrogatives-keep-open-variable-sources-english",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "9a6e3d177304b3589614e3d5e2a1acfeb545c41471afa0b49df176293fcdc46a"
    },
    "tests/test_foundation_semantics.py::test_reviewed_interrogatives_keep_open_variable_sources[spanish]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-reviewed-interrogatives-keep-open-variable-sources-spanish",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "9a6e3d177304b3589614e3d5e2a1acfeb545c41471afa0b49df176293fcdc46a"
    },
    "tests/test_foundation_semantics.py::test_multiword_nominal_keeps_query_variable_and_roundtrip[determined-multiword]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-multiword-nominal-keeps-query-variable-and-roundtrip-determined-multiword",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "e0a0311b0bfb82d99ff77987b9149e4a7664ea175029b354a765cc1dbf48bd85"
    },
    "tests/test_foundation_semantics.py::test_multiword_nominal_keeps_query_variable_and_roundtrip[bare-multiword]": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-multiword-nominal-keeps-query-variable-and-roundtrip-bare-multiword",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "e0a0311b0bfb82d99ff77987b9149e4a7664ea175029b354a765cc1dbf48bd85"
    },
    "tests/test_foundation_semantics.py::test_designation_surface_variable_preserves_query_and_binder_sources": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-designation-surface-variable-preserves-query-and-binder-sources",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "32da4b32b7d3898281d4e3bf9e80c7286595c8d19b50908a5fa5008597d339ad"
    },
    "tests/test_foundation_semantics.py::test_retiring_definition_cue_preserves_all_other_reviewed_form_fields": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:foundation-retiring-definition-cue-preserves-all-other-reviewed-form-fields",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "form-context",
        "source_ast_sha256": "790d41bfd69ad5fbd47403c18d465017888935eebc6a1934f50870870d6f4884"
    },
    "tests/test_foundation_semantics.py::test_atom_registry_does_not_supply_implicit_query_support": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-atom-registry-does-not-supply-implicit-query-support",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "92a3176559cfc1f00a849c02d5d1279641ef46b42954c78b3628c68e728c9e1c"
    },
    "tests/test_foundation_semantics.py::test_explicit_type_fact_preserves_binding_and_attributed_proof": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-explicit-type-fact-preserves-binding-and-attributed-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "f87254046850cea44432442d425e462bd5e6f84181629f187557883e6fb03747"
    },
    "tests/test_foundation_semantics.py::test_metadata_only_definition_is_not_compilable_gold": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-metadata-only-definition-is-not-compilable-gold",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "833a43ed3526888442fdf7292eea55b6c5cc9329cbc72f1a7dc490a425d3d185"
    },
    "tests/test_foundation_semantics.py::test_explicit_ordinary_type_application_remains_compilable": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-explicit-ordinary-type-application-compiles",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "cd61d9f00df28b8f76175421a9419bacbff286e7697c700a7a9d60a281b229b9"
    },
    "tests/test_foundation_semantics.py::test_known_definition_traversal_is_retired_not_completed": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-closure-known-definition-selected-semantic-path",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "source_ast_sha256": "d1f3b4e2d83b2582594b9505553a9fa7b6ec8e843c7596d12d9ad237cf71db42",
        "supersedes_node_id": "tests/test_r3_r4_predecessor_regressions.py::test_closure_known_definition_traverses_selected_semantic_path"
    },
    "tests/test_foundation_semantics.py::test_historical_definition_gold_requires_real_semantic_content[definition-digital-agent]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-reviewed-nominal-state-relation-definition-digital-agent",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "3100a25eb2b4e54a7834561ef3c1dc414565236a65a68f8b38e1bb286d4cba36",
        "supersedes_node_id": "tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[definition-digital-agent]"
    },
    "tests/test_foundation_semantics.py::test_historical_definition_gold_requires_real_semantic_content[definition-mother]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-reviewed-nominal-state-relation-definition-mother",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-2",
        "owner_ref": "expected-contract",
        "source_ast_sha256": "3100a25eb2b4e54a7834561ef3c1dc414565236a65a68f8b38e1bb286d4cba36",
        "supersedes_node_id": "tests/test_r4_closeout_regressions.py::test_reviewed_nominal_state_relation_families_match_authentic_cycles[definition-mother]"
    }
}


def _assert_no_atom_kind_answer(result) -> None:
    assert result.verification is not None
    meaning = result.verification.selected_meaning
    if meaning is not None:
        assert not any(
            app.operator == "op:type"
            and binding.role_ref == "role:type"
            and binding.filler == LiteralValue("string", "concept")
            for app in meaning.expression.applications
            for binding in app.roles
        ), meaning.expression.as_dict()
    assert result.effect_receipt is None or isinstance(
        result.effect_receipt, NoEffectReceipt
    )


@pytest.mark.parametrize(
    "surface",
    ("What is CEMM?", "Who is CEMM?", "Where is CEMM?", "Define mother.", "What is a mother?"),
    ids=("what-cemm", "who-cemm", "where-cemm", "define-mother", "what-mother"),
)
def test_public_question_never_substitutes_registry_kind(surface: str, tmp_path: Path) -> None:
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        before = runtime.stores.world.revision, runtime.stores.r3_world_facts()
        result = runtime.process("session:foundation-question", surface)
        assert (runtime.stores.world.revision, runtime.stores.r3_world_facts()) == before
        _assert_no_atom_kind_answer(result)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize(
    "surface", ("Define mother.", "What is a mother?"), ids=("define-mother", "what-mother")
)
def test_definition_does_not_substitute_a_known_type_member(surface: str, tmp_path: Path) -> None:
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        # Both existing role spellings describe Alice's membership, not mother.
        runtime.stores.world.commit(
            (
                Fact(
                    fact_ref="fact:foundation-alice-mother",
                    operator="op:type",
                    args={"predicate_ref": "concept:mother", "role:subject": "entity:alice", "role:type": "concept:mother"},
                    proof={"source": "source:reviewed-membership"},
                ),
                Fact(
                    fact_ref="fact:foundation-alice-mother-nominal",
                    operator="op:type",
                    args={"predicate_ref": "concept:mother", "role:instance": "entity:alice", "role:class": "concept:mother"},
                    proof={"source": "source:reviewed-membership"},
                ),
            ),
            expected_revision=0,
        )
        before = runtime.stores.world.revision, runtime.stores.r3_world_facts()
        result = runtime.process("session:foundation-description", surface)
        assert (runtime.stores.world.revision, runtime.stores.r3_world_facts()) == before
        _assert_no_atom_kind_answer(result)
        meaning = result.verification.selected_meaning
        assert meaning is None or not any(
            app.operator == "op:type" for app in meaning.expression.applications
        ), "A type member is not the requested descriptive content"
    finally:
        runtime.stores.close()


@pytest.mark.parametrize(
    "surface",
    ("Define mother.", "Define mother. Alice is a person.", "Alice is a person. Define mother."),
    ids=("bare", "following-clause", "preceding-clause"),
)
def test_retired_definition_form_cue_stays_unresolved(surface: str, tmp_path: Path) -> None:
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        _, context = runtime.orient("session:foundation-definition-form", surface)
        assert any(frame.operator_ref == "op:type" for frame in context.application_frames)
        assert not any(row.kind == "open_variable" for row in context.contribution_slots)
        assert context.variable_slots == ()
        assert any(row.critical for row in context.residual_evidence)
        assert ProposalContext.from_dict(context.as_dict()) == context
    finally:
        runtime.stores.close()


def _forged_variable_payload(context, source_refs):
    frame = next(frame for frame in context.application_frames if frame.operator_ref == "op:type")
    variable = VariableSlot.create(
        application_frame_ref=frame.slot_ref,
        role_ref="role:instance",
        required_kinds=("entity", "participant", "concept"),
        source_unit_refs=source_refs,
        construction_ref=None,
    )
    payload = {
        row.name: getattr(context, row.name) for row in fields(context)
        if row.init and row.name not in {"context_ref", "abi_version"}
    }
    payload["variable_slots"] = (variable,)
    return payload


@pytest.mark.parametrize(
    "source_kind", ("nominal", "binder", "mixed"), ids=("nominal", "binder-only", "query-plus-nominal"),
)
def test_context_rejects_variable_sources_without_exact_query_ownership(source_kind: str, tmp_path: Path) -> None:
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        _, context = runtime.orient("session:foundation-forged-variable", "Who is a mother?")
        nominal = next(row for row in context.application_frames if row.operator_ref == "op:type")
        query = next(row for row in context.contribution_slots if row.kind == "open_variable")
        binder = next(row for row in context.contribution_slots if row.kind == "binder")
        source_refs = {
            "nominal": nominal.source_unit_refs,
            "binder": binder.source_unit_refs,
            "mixed": (*query.source_unit_refs, *nominal.source_unit_refs),
        }[source_kind]
        with pytest.raises(ValueError, match="variable.*source evidence"):
            ProposalContext.create(**_forged_variable_payload(context, source_refs))
    finally:
        runtime.stores.close()


def test_verifier_reconstructs_variable_source_ownership_after_context_forgery(tmp_path: Path) -> None:
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        _, context = runtime.orient("session:foundation-forged-candidate", "Who mother")
        nominal = next(row for row in context.application_frames if row.operator_ref == "op:type")
        payload = _forged_variable_payload(context, nominal.source_unit_refs)
        payload["variable_slots"] = (*context.variable_slots, *payload["variable_slots"])
        # Bypass constructors to model an adversarial object. VERIFY must
        # independently reconstruct the canonical envelope, not trust its hash.
        forged = object.__new__(ProposalContext)
        for name, value in payload.items():
            object.__setattr__(forged, name, value)
        object.__setattr__(forged, "abi_version", context.abi_version)
        wire = context.as_dict()
        wire["variable_slots"] = [row.as_dict() for row in payload["variable_slots"]]
        del wire["context_ref"]
        object.__setattr__(forged, "context_ref", stable_ref("proposal_context", wire))
        forged._build_indexes()
        proposal = runtime.proposal_model.propose(forged)
        assert proposal.status == "candidates", "The forged proposal must exercise VERIFY"
        with pytest.raises(ValueError, match="variable.*source evidence"):
            ExactProgramVerifier().verify_candidates(proposal, forged)
    finally:
        runtime.stores.close()


def test_retired_definition_cannot_forge_a_variable_from_unresolved_source(tmp_path: Path) -> None:
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        _, context = runtime.orient("session:foundation-forged-definition", "Define mother.")
        source = next(ref for ref, start, _ in context.source_unit_spans if start == 0)
        with pytest.raises(ValueError, match="variable.*source evidence"):
            ProposalContext.create(**_forged_variable_payload(context, (source,)))
    finally:
        runtime.stores.close()


@pytest.mark.parametrize(
    ("language", "surface"),
    (("en", "Who is a mother?"), ("es", "Quién es una madre?")),
    ids=("english", "spanish"),
)
def test_reviewed_interrogatives_keep_open_variable_sources(language: str, surface: str, tmp_path: Path) -> None:
    """Form-owner control only; this does not claim Spanish designation lookup."""
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        orientation, context = runtime.orient("session:foundation-form-control", "Who is a mother?")
        pack = json.loads((ROOT / "data" / "languages" / language / "forms.json").read_text(encoding="utf-8"))
        config = RuntimeConfig.release()
        lattice = FormResolver(pack, config).resolve(surface)
        builder = ProposalContextBuilder(runtime.authority, SemanticAffordanceIndex(runtime.authority, config), config, form_pack=pack)
        contributions, _ = builder._form_evidence_slots(orientation, lattice, {})
        query_sources = {ref for row in contributions if row.kind == "open_variable" for ref in row.source_unit_refs}
        assert query_sources
        variables = _variable_slots(lattice, contributions, context.application_frames, config)
        assert len(variables) == 1
        assert variables[0].role_ref == "role:instance"
        assert set(variables[0].source_unit_refs) <= query_sources
    finally:
        runtime.stores.close()


@pytest.mark.parametrize(
    "surface", ("Who is a job role?", "Who is job role?"),
    ids=("determined-multiword", "bare-multiword"),
)
def test_multiword_nominal_keeps_query_variable_and_roundtrip(surface: str, tmp_path: Path) -> None:
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        _, context = runtime.orient("session:foundation-multiword-variable", surface)
        frame = next(
            row for row in context.application_frames
            if row.predicate_target_ref == "concept:job_role"
            and row.operator_ref == "op:type" and len(row.source_unit_refs) >= 2
        )
        assert any(row.application_frame_ref == frame.slot_ref for row in context.variable_slots)
        assert ProposalContext.from_dict(context.as_dict()) == context
    finally:
        runtime.stores.close()


def test_designation_surface_variable_preserves_query_and_binder_sources(tmp_path: Path) -> None:
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        _, context = runtime.orient("session:foundation-designation-variable", "What is your name?")
        variable = next(
            row for row in context.variable_slots
            if row.role_ref == "role:surface"
            and context.frame(row.application_frame_ref).predicate_kind == "label_type"
        )
        query_sources = {ref for row in context.contribution_slots if row.kind == "open_variable" for ref in row.source_unit_refs}
        binder_sources = {ref for row in context.contribution_slots if row.kind == "binder" for ref in row.source_unit_refs}
        assert set(variable.source_unit_refs) & query_sources
        assert set(variable.source_unit_refs) & binder_sources
        assert set(variable.source_unit_refs) <= query_sources | binder_sources
        assert ProposalContext.from_dict(context.as_dict()) == context
    finally:
        runtime.stores.close()


def test_retiring_definition_cue_preserves_all_other_reviewed_form_fields() -> None:
    pack = json.loads((ROOT / "data/languages/en/forms.json").read_text(encoding="utf-8"))
    assert "define" not in pack["query_projection"]
    # The exact predecessor pack, reconstructed by only restoring the retired
    # cue, must retain its known canonical hash. No other input/output field is
    # implicitly removed or regenerated.
    pack["query_projection"]["define"] = {"kind": "query"}
    assert FormResolver(pack, RuntimeConfig.release()).form_pack_hash == (
        "sha256:32f5133c901afc05cc5345bc5766d00c97518b54025cad4ca0fb3707ad40b5ad"
    )


def _situation(pin: RevisionPin) -> SituationContext:
    return SituationContext.create(
        orientation_ref="orientation:foundation",
        proposal_context_ref="proposal_context:foundation",
        mode=SemanticMode.QUERY,
        session_ref="session:foundation",
        turn_ref="turn:foundation",
        turn_index=1,
        participant_refs=("participant:system", "participant:user"),
        speaker_ref="participant:user",
        addressee_ref="participant:system",
        actor_ref=None,
        temporal_frame_ref="time:now",
        active_event_refs=(),
        focus_snapshot_ref="snapshot:focus:foundation",
        focus_refs=(),
        obligation_snapshot_ref="snapshot:obligation:foundation",
        obligation_refs=(),
        capability_refs=(),
        permission_snapshot_ref="snapshot:permission:foundation",
        permission_refs=(),
        resource_snapshot_ref="snapshot:resource:foundation",
        resource_refs=(),
        adapter_snapshot_ref="snapshot:adapter:foundation",
        adapter_refs=(),
        evidence_kinds=("text",),
        evidence_policy_refs=("policy:evidence:foundation",),
        adapter_receipt_refs=(),
        trusted_observation=False,
        source_refs=("source:foundation",),
        epistemic_scope_ref="epistemic_scope:query",
        session_phase_ref="session_phase:active",
        revision_pin=pin,
    )


def test_atom_registry_does_not_supply_implicit_query_support(linked_authority) -> None:
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        app = SemanticApplication(
            "application:metadata-question", "op:type", "concept:mother",
            (RoleBinding("role:subject", GroundedReference("concept:mother")),
             RoleBinding("role:type", LiteralValue("string", "concept"))),
        )
        expression = SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))
        pin = RevisionPin(linked_authority.generation, 0, 0, 0, 0, "model:foundation")
        before = stores.revisions(), stores.r3_world_facts()
        result = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority).evaluate_full(
            expression, project_expression(expression), _situation(pin)
        )
        query = result.query_results[0]
        assert query.status is QueryStatus.UNKNOWN
        assert query.proof is None
        assert query.bindings == ()
        assert set(query.retrieval_refs) <= set(linked_authority.rules)
        assert (stores.revisions(), stores.r3_world_facts()) == before
    finally:
        stores.close()


def test_explicit_type_fact_preserves_binding_and_attributed_proof(linked_authority) -> None:
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        fact = Fact(
            fact_ref="fact:foundation-type",
            operator="op:type",
            args={"predicate_ref": "concept:mother", "role:subject": "entity:alice", "role:type": "concept:mother"},
            proof={"source": "source:reviewed-membership"},
        )
        stores.world.commit((fact,), expected_revision=0)
        app = SemanticApplication(
            "application:type-membership", "op:type", "concept:mother",
            (RoleBinding("role:subject", BoundVariable("?member")),
             RoleBinding("role:type", GroundedReference("concept:mother"))),
        )
        binder = VariableBinder("binder:member", "?member", app.application_ref)
        expression = SemanticExpression.create(
            applications=(app,), binders=(binder,), root_refs=(binder.binder_ref,)
        )
        pin = RevisionPin(linked_authority.generation, 1, 0, 0, 0, "model:foundation")
        before = stores.revisions(), stores.r3_world_facts()
        result = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority).evaluate_full(
            expression, project_expression(expression), _situation(pin)
        )
        query = result.query_results[0]
        variable_ref = expression.binders[0].variable_ref
        assert query.status is QueryStatus.SUPPORTED
        assert query.bindings == ((variable_ref, "entity:alice"),)
        assert query.proof is not None
        assert query.proof.source_refs == ("source:reviewed-membership",)
        assert query.proof.rule_refs == ()
        assert len(query.proof.nodes) == 1
        assert query.proof.nodes[0].source_fact_refs == (fact.fact_ref,)
        assert query.proof.nodes[0].substitutions == query.bindings
        assert query.proof.revision_pin == pin
        assert (stores.revisions(), stores.r3_world_facts()) == before
    finally:
        stores.close()


def _compile_scenario(authority, scenario):
    return ExpectedCycleContractCompiler(authority, abi_registry_ref="abi:foundation").compile(
        scenario_ref=scenario.scenario_ref,
        case_ref="case:foundation",
        surface_ref="surface:foundation",
        context_ref="context:foundation",
        assertions=scenario.assertions,
        situation_constraints={},
        revision_pin=RevisionPin(authority.generation, 0, 0, 0, 0, "model:foundation"),
    )


def test_metadata_only_definition_is_not_compilable_gold(linked_authority) -> None:
    scenario = ReviewedScenario.from_dict({
        "scenario_ref": "scenario:foundation-independent-definition",
        "review_status": "reviewed",
        "competency_category": "definition",
        "semantic_assertions": [{"kind": "defines", "target": "concept:mother", "semantic_kind": "concept"}],
        "surface_examples": ["Define mother."],
        "metadata": {},
    })
    with pytest.raises(AssertionCompilerError) as error:
        _compile_scenario(linked_authority, scenario)
    assert error.value.code == "definition_requires_semantic_content"
    assert error.value.assertion_ref == scenario.assertions[0].assertion_ref


def test_explicit_ordinary_type_application_remains_compilable(linked_authority) -> None:
    scenario = ReviewedScenario.from_dict({
        "scenario_ref": "scenario:foundation-independent-type-claim",
        "review_status": "reviewed",
        "competency_category": "type",
        "semantic_assertions": [{
            "kind": "application", "operator": "op:type", "predicate": "concept:mother",
            "roles": {"role:subject": "entity:alice", "role:type": "concept:mother"},
        }],
        "surface_examples": ["Alice is a mother."],
        "metadata": {},
    })
    contract = _compile_scenario(linked_authority, scenario)
    assert len(contract.expected_expressions) == 1
    app = contract.expected_expressions[0].applications[0]
    assert app.operator == "op:type"
    assert app.predicate_ref == "concept:mother"
    assert {role.role_ref: role.filler for role in app.roles} == {
        "role:subject": GroundedReference("entity:alice"),
        "role:type": GroundedReference("concept:mother"),
    }


def test_known_definition_traversal_is_retired_not_completed(tmp_path: Path) -> None:
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")
    try:
        before = runtime.stores.world.revision, runtime.stores.r3_world_facts()
        result = runtime.process("session:foundation-retired-traversal", "What is CEMM?")
        assert result.orientation.mode is SemanticMode.QUERY
        assert (runtime.stores.world.revision, runtime.stores.r3_world_facts()) == before
        _assert_no_atom_kind_answer(result)
        # There is no descriptive content in this fresh context. Traversal alone
        # must not claim a supported definition; usable projection stays open.
        assert result.evaluation is None or all(
            query.status is not QueryStatus.SUPPORTED
            for query in result.evaluation.query_results
        )
    finally:
        runtime.stores.close()


@pytest.mark.parametrize(
    "scenario_ref",
    ("scenario:designation_definition-0006", "scenario:designation_definition-0010"),
    ids=("definition-digital-agent", "definition-mother"),
)
def test_historical_definition_gold_requires_real_semantic_content(scenario_ref: str, linked_authority) -> None:
    scenario = next(
        row for row in load_reviewed_scenarios(ROOT / "data" / "scenarios" / "use_cases.jsonl")
        if row.scenario_ref == scenario_ref
    )
    definition = next(row for row in scenario.assertions if row.kind == "defines")
    assert set(definition.fields) == {"target", "semantic_kind"}
    with pytest.raises(AssertionCompilerError) as error:
        _compile_scenario(linked_authority, scenario)
    assert error.value.code == "definition_requires_semantic_content"
    assert error.value.assertion_ref == definition.assertion_ref
