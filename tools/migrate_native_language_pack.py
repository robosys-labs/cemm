#!/usr/bin/env python3
"""Migrate English realization authority for typed learning and new query families."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def write_pack(path: Path, data: dict[str, Any]) -> None:
    material = {key: value for key, value in data.items() if key != "pack_hash"}
    data["pack_hash"] = hashlib.sha256(canonical(material).encode()).hexdigest()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def migrate_generator(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    before = text
    text = text.replace(
        " ('learn','RESPONSE request_learning_evidence LEARNING resolve_designation EVIDENCE @E0','What does @E0 refer to here?'),\n",
        "",
    )
    text = text.replace(
        " ('learned-binding','RESPONSE answer_bindings QUERY_KIND designation_learning PROPERTY @A0 LEARNING resolve_designation BINDING ?q0 @A1 ?q1 @A0 EVIDENCE @E0','In this context, @E0 refers to @A1.'),\n",
        " ('learned-binding','RESPONSE answer_bindings QUERY_KIND designation_learning PROPERTY @A0 BINDING ?q0 @A1 ?q1 @A0 EVIDENCE @E0','In this context, @E0 refers to @A1.'),\n",
    )
    text = text.replace(
        " ('capability-answer','RESPONSE answer_bindings QUERY_KIND capability_query BINDING ?q1 @A0','I can @A0.'),\n",
        " ('capability-answer','RESPONSE answer_bindings QUERY_KIND capability_inventory_query BINDING ?capability @A0','I can use @A0.'),\n",
    )
    changed = text != before
    if changed:
        path.write_text(text, encoding="utf-8")
    elif "LEARNING resolve_designation" in text or "QUERY_KIND capability_query" in text:
        raise ValueError("English language-pack generator rewrite anchors were absent")
    return changed


def _rule(ref: str, action: str, template: str, required: list[str], semantic: list[str], **when: Any) -> dict[str, Any]:
    return {
        "ref": ref,
        "when": {"action": action, **when},
        "template": template,
        "required_slots": required,
        "semantic_slots": semantic,
    }


def migrate_pack(path: Path, form_pack: dict[str, Any] | str) -> dict[str, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(form_pack, dict):
        form_pack_hash = str(form_pack["pack_hash"])
        form_lexemes = tuple(form_pack.get("lexemes", ()))
    else:
        # Backward-compatible maintenance API for callers that only update the
        # hash. Full installation always passes the generated form pack so
        # legacy input-side function forms can also be sanitized.
        form_pack_hash = str(form_pack)
        form_lexemes = ()
    data["form_pack_hash"] = form_pack_hash
    rules = list(data.get("response_grammar", ()))
    changed = 0
    for rule in rules:
        if rule.get("when", {}).get("action") == "request_learning_evidence":
            desired = ["evidence", "learning_plan_ref", "query_kind", "query_ref"]
            if rule.get("semantic_slots") != desired:
                rule["semantic_slots"] = desired
                changed += 1
    additions = [
        _rule(
            "en:response:generic-clarify",
            "request_generic_clarification",
            "Could you clarify?",
            [],
            ["frontier_ref"],
        ),
        _rule(
            "en:response:learning-evidence",
            "request_learning_evidence",
            "What does {evidence} refer to here?",
            ["evidence"],
            ["evidence", "learning_plan_ref", "query_kind", "query_ref"],
        ),
        _rule(
            "en:response:capability-inventory",
            "answer_bindings",
            "I can use {value}.",
            ["value"],
            ["binding_values", "query_kind", "query_ref", "target_ref"],
            query_kind="capability_inventory_query",
            has_bindings=True,
        ),
        _rule(
            "en:response:capability-inventory-multiple",
            "report_multiple_bindings",
            "I can use {value}.",
            ["value"],
            ["binding_values", "query_kind", "query_ref", "target_ref"],
            query_kind="capability_inventory_query",
            has_bindings=True,
        ),
        _rule(
            "en:response:capability-inventory-unknown",
            "report_target_uncertainty",
            "I cannot verify an available capability.",
            [],
            ["query_kind", "query_ref", "target_ref"],
            query_kind="capability_inventory_query",
        ),
    ]
    existing = {str(item.get("ref")) for item in rules}
    for item in additions:
        if item["ref"] not in existing:
            rules.append(item)
            existing.add(item["ref"])
            changed += 1
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

    # The native semantic spine replaces the legacy LEARNING resolve_designation
    # response signature with a typed LEARNING_PLAN signature.  The old example
    # was removed by migrate_generator; add the replacement here so the realizer
    # can verify request_learning_evidence responses.  QUERY_KIND values are
    # raw strings (not atom placeholders) because they are plain identifiers
    # that do not match the semantic-ref pattern.
    learning_example_ref = "en:response:learning-evidence"
    if not any(str(item.get("example_ref", "")) == learning_example_ref for item in data["response_examples"]):
        data["response_examples"].append({
            "example_ref": learning_example_ref,
            "semantic": "RESPONSE request_learning_evidence QUERY_KIND designation_learning LEARNING_PLAN @E0 EVIDENCE @E1",
            "surface_plan": "What does @E1 refer to here?",
            "weight": 1.0,
        })
        changed += 1

    # Language-pack function forms are legacy input-side data. Keep output
    # grammar completely separate from pre-core form classification. If an old
    # pack carries this field, retain only the closed-class forms independently
    # licensed by the generated form pack. The Interpreter no longer consumes
    # this field, but sanitizing it prevents future accidental recoupling.
    closed_forms = {
        str(form)
        for record in form_lexemes
        if not bool(dict(record.get("features", {})).get("open_class"))
        for form in record.get("forms", ())
    }
    if "function_forms" in data:
        current = set(map(str, data.get("function_forms", ())))
        cleaned = sorted(current & closed_forms)
        if list(data.get("function_forms", ())) != cleaned:
            data["function_forms"] = cleaned
            changed += 1

    grammar = set(data.get("grammar_tokens", ()))
    grammar.update({"use", "available", "capability", "verify", "an"})
    data["grammar_tokens"] = sorted(grammar)
    write_pack(path, data)
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
