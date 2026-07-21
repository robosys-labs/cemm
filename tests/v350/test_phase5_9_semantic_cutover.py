from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from cemm.v350.language.model import (
    ConstructionKind,
    ConstructionRecord,
    ConstructionSlot,
    LexicalSenseRecord,
    SenseTargetKind,
)
from cemm.v350.schema.model import (
    OpenBindingPurpose,
    PortFillerClass,
    SchemaClass,
    SchemaLifecycleStatus,
    UseOperation,
)
from cemm.v350.uol.codec import variable_from_document
from cemm.v350.uol.model import SemanticVariable, canonical_data


def test_explicit_lexical_use_authority_is_not_primary_operation_fallback() -> None:
    sense = LexicalSenseRecord(
        sense_ref="sense:qaa:test",
        pack_ref="language-pack:qaa",
        pack_revision=1,
        target_kind=SenseTargetKind.SCHEMA,
        target_ref="property:test",
        target_revision=1,
        target_schema_class=SchemaClass.PROPERTY,
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_operation=UseOperation.GROUND,
        authorized_use_operations=(UseOperation.GROUND,),
        use_authority_explicit=True,
        lexical_category="predicate",
        source_refs=("source:test",),
        evidence_refs=("evidence:test",),
        competence_case_refs=("competence:test",),
    )
    assert sense.supports_use(UseOperation.GROUND)
    assert not sense.supports_use(UseOperation.REALIZE)


def test_explicit_construction_use_authority_can_deny_compose() -> None:
    construction = ConstructionRecord(
        construction_ref="construction:qaa:test",
        pack_ref="language-pack:qaa",
        pack_revision=1,
        construction_kind=ConstructionKind.ARGUMENT_STRUCTURE,
        slots=(ConstructionSlot("value"),),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        authorized_use_operations=(),
        use_authority_explicit=True,
        source_refs=("source:test",),
        evidence_refs=("evidence:test",),
        competence_case_refs=("competence:test",),
    )
    assert not construction.supports_use(UseOperation.COMPOSE)


def test_semantic_variable_preserves_exact_nbest_projection_pins() -> None:
    variable = SemanticVariable(
        variable_ref="semantic-variable:test",
        expected_schema_classes=frozenset({SchemaClass.PROPERTY, SchemaClass.STATE_DIMENSION}),
        expected_filler_classes=frozenset({PortFillerClass.REFERENT, PortFillerClass.QUOTED_LITERAL}),
        expected_type_refs=("type:referent",),
        restriction_refs=("referent:self",),
        projection_candidates=(("property:name", 1), ("state:operational_status", 1)),
        open_binding_purpose=OpenBindingPurpose.QUERY,
        evidence_refs=("evidence:test",),
    )
    decoded = variable_from_document(canonical_data(variable))
    assert decoded == variable


def _load_migrator(repo_root: Path):
    path = repo_root / "tools" / "migrate_v350_phase9_semantic_seed.py"
    spec = importlib.util.spec_from_file_location("phase9_migrator_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in records),
        encoding="utf-8",
    )


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_phase9_seed_migration_is_idempotent_and_does_not_fabricate_matrix_force(
    tmp_path: Path,
) -> None:
    root = tmp_path / "v350"
    modules = [
        {"allow_empty": False, "authority_scope": "language_evidence", "module_ref": "languages:packs", "path": "languages/packs.jsonl", "phase": 7, "record_kind": "language_pack"},
        {"allow_empty": False, "authority_scope": "language_evidence", "module_ref": "languages:forms", "path": "languages/forms.jsonl", "phase": 7, "record_kind": "language_form"},
        {"allow_empty": False, "authority_scope": "language_evidence", "module_ref": "languages:senses", "path": "languages/senses.jsonl", "phase": 7, "record_kind": "lexical_sense"},
        {"allow_empty": False, "authority_scope": "language_evidence", "module_ref": "languages:form_sense_links", "path": "languages/form_sense_links.jsonl", "phase": 7, "record_kind": "form_sense_link"},
        {"allow_empty": False, "authority_scope": "language_evidence", "module_ref": "languages:constructions", "path": "languages/constructions.jsonl", "phase": 7, "record_kind": "construction"},
        {"allow_empty": True, "authority_scope": "response", "module_ref": "response:policies", "path": "response/policies.jsonl", "phase": 20, "record_kind": "response_policy_rule"},
        {"allow_empty": True, "authority_scope": "response", "module_ref": "response:transforms", "path": "response/transforms.jsonl", "phase": 20, "record_kind": "response_transform_rule"},
    ]
    root.mkdir(parents=True)
    (root / "manifest.json").write_text(json.dumps({"modules": modules, "metadata": {}}, indent=2) + "\n", encoding="utf-8")
    source = ["source:reviewed"]
    evidence = ["evidence:reviewed"]
    competence = ["competence:reviewed"]
    _write_jsonl(root / "languages/packs.jsonl", [{
        "pack_ref": "language-pack:qaa", "language_tag": "qaa", "revision": 1,
        "lifecycle_status": "active", "scripts": ["Latn"],
        "source_refs": source, "evidence_refs": evidence,
        "competence_case_refs": competence, "permission_ref": "public", "metadata": {},
    }])
    _write_jsonl(root / "languages/forms.jsonl", [{
        "form_ref": "form:qaa:zo", "pack_ref": "language-pack:qaa", "pack_revision": 1,
        "written_form": "zo", "normalized_form": "zo", "form_kind": "token", "revision": 1,
        "lifecycle_status": "active", "script": "Latn", "token_count": 1,
        "feature_values": [], "source_refs": source, "evidence_refs": evidence,
        "permission_ref": "public", "metadata": {},
    }])
    _write_jsonl(root / "languages/senses.jsonl", [{
        "sense_ref": "sense:qaa:query", "pack_ref": "language-pack:qaa", "pack_revision": 1,
        "target_kind": "discourse", "target_ref": "discourse-act:ask", "target_revision": 1,
        "target_schema_class": "discourse_act", "revision": 1, "lifecycle_status": "active",
        "use_operation": "ground", "lexical_category": "query_marker", "argument_map": [],
        "expected_type_refs": [], "scope_behavior": "none", "context_constraints": [],
        "feature_constraints": [], "source_refs": source, "evidence_refs": evidence,
        "competence_case_refs": competence, "permission_ref": "public",
        "metadata": {"query_variable": True, "query_expected_schema_classes": ["property"]},
    }])
    _write_jsonl(root / "languages/form_sense_links.jsonl", [{
        "link_ref": "form-sense-link:qaa:zo", "form_ref": "form:qaa:zo", "form_revision": 1,
        "sense_ref": "sense:qaa:query", "sense_revision": 1, "revision": 1,
        "lifecycle_status": "active", "prior_weight": 1.0, "register_refs": [],
        "condition_refs": [], "source_refs": source, "evidence_refs": evidence,
        "permission_ref": "public", "metadata": {},
    }])
    _write_jsonl(root / "languages/constructions.jsonl", [{
        "construction_ref": "construction:qaa:test", "pack_ref": "language-pack:qaa", "pack_revision": 1,
        "construction_kind": "argument_structure", "revision": 1, "lifecycle_status": "active",
        "slots": [{"slot_ref": "value", "minimum": 1, "maximum": 1, "accepted_categories": ["query_marker"], "accepted_target_classes": [], "dependency_relations": [], "dependency_position": "either", "anchor_to_trigger": True, "constituency_labels": [], "optional_when_licensed": False, "semantic_port_ref": "value"}],
        "trigger_sense_refs": ["sense:qaa:query"], "source_refs": source, "evidence_refs": evidence,
        "competence_case_refs": competence, "permission_ref": "public",
        "metadata": {"interpretation_enabled": False},
    }])
    _write_jsonl(root / "response/policies.jsonl", [{
        "rule_ref": "response-policy-rule:answer:property-x", "trigger_record_kinds": ["semantic_application"],
        "trigger_schema_pins": [["property:x", 1]], "goal_schema_ref": "response-policy:answer-query", "goal_schema_revision": 1,
        "goal_operation": "plan", "target_selectors": [{"mode": "source"}], "priority": 1,
        "lifecycle_status": "active", "use_operation": "response_policy", "use_decision": "allow", "permission_ref": "public", "revision": 1,
        "metadata": {"purpose": "answer_retrieved_semantic_application"},
    }])
    _write_jsonl(root / "response/transforms.jsonl", [{
        "rule_ref": "response-transform-rule:answer:property-x", "goal_schema_pins": [["response-policy:answer-query", 1]],
        "source_record_kinds": ["semantic_application"], "output_schema_ref": "property:x", "output_schema_revision": 1,
        "selectors": [{"output_port_ref": "value", "mode": "source"}], "priority": 1,
        "lifecycle_status": "active", "use_operation": "plan", "use_decision": "allow", "permission_ref": "public", "revision": 1,
        "metadata": {"purpose": "reconstruct_exact_source_semantics"},
    }])

    migrator = _load_migrator(Path(__file__).resolve().parents[2])
    migrator.migrate(root)
    assert migrator.verify_invariants(root) == ()
    first = _tree_bytes(root)
    migrator.migrate(root)
    assert _tree_bytes(root) == first

    senses = []
    manifest = json.loads((root / "manifest.json").read_text())
    for module in manifest["modules"]:
        if module["record_kind"] == "lexical_sense":
            senses.extend(json.loads(line) for line in (root / module["path"]).read_text().splitlines() if line)
    query = next(item for item in senses if item["sense_ref"] == "sense:qaa:query")
    assert query["target_ref"] is None
    assert query["use_authority_explicit"] is True
    assert "ground" in query["authorized_use_operations"]
    assert not any(str(ref).startswith("competence:phase9:") for item in senses for ref in item.get("competence_case_refs", ()))
    assert not any(item.get("metadata", {}).get("phase9_matrix_question_force") for item in senses)

    direct_links = []
    for module in manifest["modules"]:
        if module["record_kind"] == "form_sense_link":
            direct_links.extend(json.loads(line) for line in (root / module["path"]).read_text().splitlines() if line)
    original = next(item for item in direct_links if item["link_ref"] == "form-sense-link:qaa:zo")
    assert original["lifecycle_status"] == "superseded"

    constructions = []
    for module in manifest["modules"]:
        if module["record_kind"] == "construction":
            constructions.extend(json.loads(line) for line in (root / module["path"]).read_text().splitlines() if line)
    construction = next(item for item in constructions if item["construction_ref"] == "construction:qaa:test")
    assert "interpretation_enabled" not in construction["metadata"]
    assert construction["use_authority_explicit"] is True
    assert "compose" not in construction["authorized_use_operations"]
