#!/usr/bin/env python3
"""Migrate realization authority for typed learning, description and proof CSIR."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def write_pack(path: Path, data: dict[str, Any]) -> None:
    material = {key: value for key, value in data.items() if key != "pack_hash"}
    data["pack_hash"] = hashlib.sha256(canonical(material).encode("utf-8")).hexdigest()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def migrate_generator(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    before = text
    replacements = {
        "  ('learn','RESPONSE request_learning_evidence LEARNING resolve_designation EVIDENCE @E0','What does @E0 refer to here?'),\n": "",
        "  ('learned-binding','RESPONSE answer_bindings QUERY_KIND designation_learning PROPERTY @A0 LEARNING resolve_designation BINDING ?q0 @A1 ?q1 @A0 EVIDENCE @E0','In this context, @E0 refers to @A1.'),\n": "  ('learned-binding','RESPONSE answer_bindings QUERY_KIND designation_learning PROPERTY @A0 BINDING ?q0 @A1 ?q1 @A0 EVIDENCE @E0','In this context, @E0 refers to @A1.'),\n",
        "  ('capability-answer','RESPONSE answer_bindings QUERY_KIND capability_query BINDING ?q1 @A0','I can @A0.'),\n": "  ('capability-answer','RESPONSE answer_bindings QUERY_KIND capability_inventory_query BINDING ?capability @A0','I can use @A0.'),\n",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    if text != before:
        path.write_text(text, encoding="utf-8")
        return True
    if "LEARNING resolve_designation" in text or "QUERY_KIND capability_query" in text:
        raise ValueError("language generator still contains retired semantic protocol")
    return False


def _rule(
    ref: str,
    action: str,
    template: str,
    required: list[str],
    semantic: list[str],
    **when: Any,
) -> dict[str, Any]:
    return {
        "ref": ref,
        "when": {"action": action, **when},
        "template": template,
        "required_slots": required,
        "semantic_slots": semantic,
    }


def _upsert_rules(rules: list[dict[str, Any]], additions: list[dict[str, Any]]) -> int:
    by_ref = {str(item.get("ref")): index for index, item in enumerate(rules)}
    changed = 0
    for item in additions:
        ref = str(item["ref"])
        if ref not in by_ref:
            rules.append(item)
            by_ref[ref] = len(rules) - 1
            changed += 1
        elif canonical(rules[by_ref[ref]]) != canonical(item):
            rules[by_ref[ref]] = item
            changed += 1
    return changed


def migrate_pack(path: Path, form_pack: Mapping[str, Any]) -> dict[str, int]:
    if not isinstance(form_pack, Mapping) or not form_pack.get("pack_hash"):
        raise TypeError("native language migration requires the generated form-pack mapping")
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    form_hash = str(form_pack["pack_hash"])
    if data.get("form_pack_hash") != form_hash:
        data["form_pack_hash"] = form_hash
        changed += 1

    rules = [dict(item) for item in data.get("response_grammar", ())]
    for rule in rules:
        if rule.get("when", {}).get("action") == "request_learning_evidence":
            desired = ["evidence", "learning_plan_ref", "query_kind", "query_ref"]
            if rule.get("semantic_slots") != desired:
                rule["semantic_slots"] = desired
                changed += 1

    description_semantics = [
        "query_ref", "query_kind", "target_ref", "description_result_ref",
        "description_completeness", "target_kind", "description_summary",
    ]
    proof_semantics = [
        "query_ref", "query_kind", "proof_ref", "proof_basis",
        "proof_completeness",
    ]
    additions = [
        _rule(
            "en:response:generic-clarify", "request_generic_clarification",
            "Could you clarify?", [], ["frontier_ref"],
        ),
        _rule(
            "en:response:structural-gap", "report_structural_composition_gap",
            "I understood the known pieces, but their semantic connection is still unresolved.",
            [], ["frontier_ref", "gap_kind"],
        ),
        _rule(
            "en:response:capability-inventory", "answer_bindings",
            "I can use {value}.", ["value"],
            ["binding_values", "query_kind", "query_ref", "target_ref"],
            query_kind="capability_inventory_query", has_bindings=True,
        ),
        _rule(
            "en:response:capability-inventory-multiple", "report_multiple_bindings",
            "I can use {value}.", ["value"],
            ["binding_values", "query_kind", "query_ref", "target_ref"],
            query_kind="capability_inventory_query", has_bindings=True,
        ),
        _rule(
            "en:response:capability-inventory-unknown", "report_target_uncertainty",
            "I cannot verify an available capability.", [],
            ["query_kind", "query_ref", "target_ref"],
            query_kind="capability_inventory_query",
        ),
        _rule(
            "en:response:description-identity", "describe_semantic_target",
            "I know {target} as a {target_kind}, but I do not have enough stored defining structure to explain it further.",
            ["target", "target_kind"], description_semantics,
            query_kind="semantic_description", description_completeness="identity_only",
        ),
        _rule(
            "en:response:description-partial", "describe_semantic_target",
            "{target} is a {target_kind}. Its stored semantic links include {description_summary}, but the description is incomplete.",
            ["target", "target_kind", "description_summary"], description_semantics,
            query_kind="semantic_description", description_completeness="partial_structure",
        ),
        _rule(
            "en:response:description-sufficient", "describe_semantic_target",
            "{target} is a {target_kind}. Its stored semantic links include {description_summary}.",
            ["target", "target_kind", "description_summary"], description_semantics,
            query_kind="semantic_description", description_completeness="sufficient_structure",
        ),
        _rule(
            "en:response:description-conflict", "describe_semantic_target",
            "I have conflicting stored semantic structure for {target}, so I cannot give one settled explanation.",
            ["target"], description_semantics,
            query_kind="semantic_description", description_completeness="conflicting_structure",
        ),
        _rule(
            "en:response:proof-user", "explain_evidence_provenance",
            "I know that from information you provided earlier and the exact record created from it.",
            [], proof_semantics, query_kind="epistemic_provenance", proof_basis="user_report",
        ),
        _rule(
            "en:response:proof-authority", "explain_evidence_provenance",
            "I know that from reviewed foundational authority in my semantic store.",
            [], proof_semantics, query_kind="epistemic_provenance", proof_basis="reviewed_authority",
        ),
        _rule(
            "en:response:proof-inference", "explain_evidence_provenance",
            "I inferred that from stored supporting facts through an exact inference proof.",
            [], proof_semantics, query_kind="epistemic_provenance", proof_basis="inference",
        ),
        _rule(
            "en:response:proof-operation", "explain_evidence_provenance",
            "I know that from the verified current runtime observation used for the answer.",
            [], proof_semantics, query_kind="epistemic_provenance", proof_basis="operational_observation",
        ),
        _rule(
            "en:response:proof-stored", "explain_evidence_provenance",
            "I know that from stored evidence linked to the previous answer.",
            [], proof_semantics, query_kind="epistemic_provenance", proof_basis="stored_evidence",
        ),
        _rule(
            "en:response:proof-unsupported", "explain_evidence_provenance",
            "I do not have a complete supporting proof for that previous answer.",
            [], proof_semantics, query_kind="epistemic_provenance", proof_basis="unsupported",
        ),
    ]
    changed += _upsert_rules(rules, additions)
    data["response_grammar"] = sorted(rules, key=lambda item: str(item.get("ref", "")))

    examples = []
    for item in data.get("response_examples", ()):
        semantic = str(item.get("semantic", ""))
        if "LEARNING resolve_designation" in semantic:
            changed += 1
            if "answer_bindings" in semantic:
                revised = dict(item)
                revised["semantic"] = semantic.replace(" LEARNING resolve_designation", "")
                examples.append(revised)
            continue
        if "QUERY_KIND capability_query" in semantic:
            revised = dict(item)
            revised["semantic"] = semantic.replace(
                "QUERY_KIND capability_query", "QUERY_KIND capability_inventory_query"
            )
            examples.append(revised)
            changed += 1
        else:
            examples.append(item)
    data["response_examples"] = examples

    closed_forms = {
        str(form)
        for record in form_pack.get("lexemes", ())
        if not bool(dict(record.get("features", {})).get("open_class"))
        for form in record.get("forms", ())
    }
    if "function_forms" in data:
        cleaned = sorted(set(map(str, data.get("function_forms", ()))) & closed_forms)
        if list(data.get("function_forms", ())) != cleaned:
            data["function_forms"] = cleaned
            changed += 1

    grammar = set(map(str, data.get("grammar_tokens", ())))
    grammar.update({
        "available", "capability", "verify", "semantic", "stored", "structure",
        "evidence", "reviewed", "foundational", "inferred", "supporting",
        "previous", "incomplete", "conflicting", "runtime", "observation",
    })
    revised_grammar = sorted(grammar)
    if data.get("grammar_tokens") != revised_grammar:
        data["grammar_tokens"] = revised_grammar
        changed += 1

    serialized = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    before_bytes = path.read_bytes()
    write_pack(path, data)
    if path.read_bytes() != before_bytes and changed == 0:
        # A hash-only change is still a real deterministic migration change.
        changed = 1
    return {"changed": changed, "response_rules": len(rules)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    form = json.loads((repo / "cemm/form_packs/en.json").read_text(encoding="utf-8"))
    generator = repo / "tools/generate_en_language_pack.py"
    language_pack = repo / "cemm/language_packs/en.json"
    generator_changed = migrate_generator(generator)
    result = migrate_pack(language_pack, form)
    print(json.dumps({"generator_changed": generator_changed, **result}, indent=2))


if __name__ == "__main__":
    main()
