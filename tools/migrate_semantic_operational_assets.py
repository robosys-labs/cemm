#!/usr/bin/env python3
"""Deterministically migrate CEMM assets without changing authority ownership.

Semantic authority migration is removal-only. It may delete artifacts introduced
by the rejected first bundle and timeless system-state seed claims, but it never
adds, redefines, or silently replaces an atom. Language-pack changes are merged
by stable record identity so unrelated reviewed supervision is preserved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

try:
    from tools.authority_ownership import validate_repository_authority
except ImportError:  # direct script execution from tools/
    from authority_ownership import validate_repository_authority


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def write_hashed(path: Path, value: dict[str, Any]) -> None:
    material = {key: item for key, item in value.items() if key != "pack_hash"}
    value["pack_hash"] = hashlib.sha256(canonical(material).encode()).hexdigest()
    atomic_write_json(path, value)


def fact_signature(value: Mapping[str, Any]) -> str:
    return canonical(
        {
            "operator": value.get("operator"),
            "args": value.get("args", {}),
            "stance": value.get("stance", "support"),
        }
    )


# These refs were introduced by the rejected first bundle. They are not part of
# the current architecture and are removed only if a partially applied attempt
# left them in conversation_foundation.json.
REJECTED_BUNDLE_ATOMS = frozenset(
    {
        "dim:operational_condition",
        "dim:runtime_support",
        "value:operating_normally",
        "value:degraded",
        "rel:attributed_property",
        "concept:surface_pattern_matching",
    }
)

# These refs are owned by base.json and may be referenced by conversation data,
# but conversation_foundation.json must never define or replace them.
BASE_OWNED_REFS = frozenset(
    {
        "value:unknown",
        "dim:runtime_process_support",
        "dim:semantic_runtime_support",
        "dim:language_realizer_support",
        "dim:critical_blocker_count",
        "rel:subtype_of",
        "rel:value_of_dimension",
    }
)

TRANSIENT_SELF_DIMENSIONS = frozenset(
    {
        "dim:availability",
        "dim:communication_status",
        "dim:emotional_state",
        "dim:runtime_process_support",
        "dim:semantic_runtime_support",
        "dim:language_realizer_support",
        "dim:critical_blocker_count",
        "dim:operational_condition",
        "dim:runtime_support",
    }
)


def _contains_ref(value: Any, refs: frozenset[str]) -> bool:
    if isinstance(value, str):
        return value in refs
    if isinstance(value, Mapping):
        return any(_contains_ref(item, refs) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_ref(item, refs) for item in value)
    return False


def _atom_map(atoms: Iterable[Mapping[str, Any]], *, source: str) -> dict[str, str]:
    output: dict[str, str] = {}
    for index, atom in enumerate(atoms):
        ref = str(atom.get("ref") or "")
        if not ref:
            raise ValueError(f"{source}: atom {index} has no ref")
        if ref in output:
            raise ValueError(f"{source}: duplicate local atom definition: {ref}")
        output[ref] = canonical(atom)
    return output


def migrate_seed(path: Path) -> dict[str, Any]:
    data = read(path)
    previous_report = dict(data.get("semantic_operational_migration", {}) or {})
    original_atoms = list(data.get("atoms", ()))
    original_by_ref = _atom_map(original_atoms, source=str(path))

    illegal_base_definitions = sorted(BASE_OWNED_REFS.intersection(original_by_ref))
    if illegal_base_definitions:
        raise ValueError(
            "conversation authority redefines base-owned atoms before migration: "
            + ", ".join(illegal_base_definitions)
        )

    removed_atoms = [
        str(item["ref"])
        for item in original_atoms
        if str(item.get("ref")) in REJECTED_BUNDLE_ATOMS
    ]
    data["atoms"] = [
        item
        for item in original_atoms
        if str(item.get("ref")) not in REJECTED_BUNDLE_ATOMS
    ]

    kept_facts: list[dict[str, Any]] = []
    removed_facts: list[str] = []
    for fact in data.get("facts", ()):
        args = dict(fact.get("args", {}) or {})
        # Seed documents have no occurrence time/context semantics. A reviewed
        # self operational state here would therefore be timeless and invalid.
        timeless_transient_self = (
            fact.get("operator") == "op:state"
            and args.get("role:subject") == "participant:system"
            and args.get("role:dimension") in TRANSIENT_SELF_DIMENSIONS
            and fact.get("authority_status", "reviewed") == "reviewed"
        )
        rejected_reference = _contains_ref(fact, REJECTED_BUNDLE_ATOMS)
        rejected_source = fact.get("source_ref") == "semantic-operational-contract"
        if timeless_transient_self or rejected_reference or rejected_source:
            removed_facts.append(str(fact.get("fact_ref") or fact_signature(fact)))
            continue
        kept_facts.append(dict(fact))
    data["facts"] = kept_facts

    migrated_by_ref = _atom_map(data["atoms"], source=f"{path}:migrated")
    modified = sorted(
        ref
        for ref, definition in migrated_by_ref.items()
        if ref in original_by_ref and original_by_ref[ref] != definition
    )
    added = sorted(set(migrated_by_ref) - set(original_by_ref))
    surviving_removed = sorted(REJECTED_BUNDLE_ATOMS.intersection(migrated_by_ref))
    base_redefinitions = sorted(BASE_OWNED_REFS.intersection(migrated_by_ref))
    if modified or added or surviving_removed or base_redefinitions:
        raise ValueError(
            "semantic migration violated authority ownership: "
            f"added={added}, modified={modified}, "
            f"surviving_rejected={surviving_removed}, "
            f"base_redefinitions={base_redefinitions}"
        )

    cumulative_removed_atoms = sorted(
        set(previous_report.get("removed_rejected_bundle_atoms", ()))
        | set(removed_atoms)
    )
    cumulative_removed_facts = sorted(
        set(previous_report.get("removed_fact_refs", ())) | set(removed_facts)
    )
    report = {
        "contract": "CEMM_RUNTIME_IMPLEMENTATION_CONTRACT.md",
        "authority_change": "removal_only",
        "added_atom_count": 0,
        "modified_atom_count": 0,
        "removed_rejected_bundle_atoms": cumulative_removed_atoms,
        "removed_durable_transient_state_count": len(cumulative_removed_facts),
        "removed_fact_refs": cumulative_removed_facts,
        "base_owned_refs_not_defined_here": sorted(BASE_OWNED_REFS),
        "operational_status_storage": "cycle_local_assessment_not_authority_atom",
        "epistemic_modes": [
            "observed",
            "derived",
            "predicted",
            "simulated",
            "desired",
            "committed",
        ],
    }
    data["semantic_operational_migration"] = report
    atomic_write_json(path, data)
    return report


def _merge_by_key(
    existing: Iterable[Mapping[str, Any]],
    additions: Iterable[Mapping[str, Any]],
    key: Callable[[Mapping[str, Any]], str],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for item in existing:
        identity = key(item)
        if identity not in merged:
            order.append(identity)
        merged[identity] = dict(item)
    for item in additions:
        identity = key(item)
        if identity not in merged:
            order.append(identity)
        merged[identity] = dict(item)
    return [merged[identity] for identity in order]


def _closed_exact_response_example(example: Mapping[str, Any]) -> bool:
    semantic = str(example.get("semantic", ""))
    plan = str(example.get("surface_plan", ""))
    if not semantic.startswith("RESPONSE ") or not plan.strip():
        return False
    dynamic_markers = (
        "@A",
        "@E",
        "@N",
        "BINDING",
        "FACT",
        "QUERY_KIND",
        "PROPERTY",
        "TARGET",
        "EVIDENCE",
        "QUALIFIER",
    )
    return not any(marker in semantic for marker in dynamic_markers)


def migrate_language_pack(path: Path, form_pack_path: Path) -> dict[str, Any]:
    data = read(path)
    form_pack = read(form_pack_path)
    before_hash = data.get("pack_hash")
    prior_contract = dict(data.get("semantic_operational_contract", {}) or {})
    migration_source_hash = prior_contract.get("migration_source_pack_hash") or before_hash
    data["form_pack"] = "../form_packs/en.json"
    data["form_pack_hash"] = form_pack["pack_hash"]

    reference_additions = [
        {"surface": "I", "features": {"person": "first", "number": "singular", "possessive": False}, "weight": 2.0},
        {"surface": "my", "features": {"person": "first", "number": "singular", "possessive": True}, "weight": 2.0},
        {"surface": "myself", "features": {"person": "first", "number": "singular", "possessive": False, "reflexive": True}, "weight": 2.0},
        {"surface": "you", "features": {"person": "second", "number": "singular", "possessive": False}, "weight": 2.0},
        {"surface": "your", "features": {"person": "second", "number": "singular", "possessive": True}, "weight": 2.0},
        {"surface": "they", "features": {"person": "third", "number": "singular", "possessive": False}, "weight": 1.0},
        {"surface": "their", "features": {"person": "third", "number": "singular", "possessive": True}, "weight": 1.0},
    ]
    data["reference_realization"] = _merge_by_key(
        data.get("reference_realization", ()),
        reference_additions,
        lambda item: canonical((item.get("surface"), item.get("features", {}))),
    )
    data["orthography"] = {
        **dict(data.get("orthography", {}) or {}),
        "sentence_initial_capitalization": True,
    }
    predicate_additions = [
        {"surface": "am", "features": {"lemma": "be", "tense": "present", "person": "first", "number": "singular"}, "weight": 2.0},
        {"surface": "are", "features": {"lemma": "be", "tense": "present", "person": "second", "number": "singular"}, "weight": 2.0},
        {"surface": "is", "features": {"lemma": "be", "tense": "present", "person": "third", "number": "singular"}, "weight": 2.0},
        {"surface": "are", "features": {"lemma": "be", "tense": "present", "number": "plural"}, "weight": 2.0},
    ]
    data["predicate_realization"] = _merge_by_key(
        data.get("predicate_realization", ()),
        predicate_additions,
        lambda item: canonical((item.get("surface"), item.get("features", {}))),
    )

    exact_additions = [
        {"semantic": "RESPONSE greet", "surface_plan": "Hello."},
        {"semantic": "RESPONSE acknowledge_claim", "surface_plan": "Understood."},
        {"semantic": "RESPONSE confirm", "surface_plan": "Yes."},
        {"semantic": "RESPONSE deny", "surface_plan": "No."},
        {"semantic": "RESPONSE report_target_uncertainty", "surface_plan": "I do not have enough evidence."},
        {"semantic": "RESPONSE report_conflict", "surface_plan": "I found conflicting evidence."},
    ]
    preserved_exact = [
        dict(item)
        for item in data.get("response_examples", ())
        if _closed_exact_response_example(item)
    ]
    data["response_examples"] = _merge_by_key(
        preserved_exact,
        exact_additions,
        lambda item: canonical(item.get("semantic")),
    )

    grammar_additions = [
        {"ref": "en:response:greet", "when": {"action": "greet"}, "template": "Hello.", "required_slots": [], "semantic_slots": []},
        {"ref": "en:response:acknowledge", "when": {"action": "acknowledge_claim"}, "template": "Understood.", "required_slots": [], "semantic_slots": []},
        {"ref": "en:response:designation", "when": {"action": "answer_bindings", "query_kind": "designation_property", "has_bindings": True}, "template": "{subject_possessive} {property} is {value}.", "required_slots": ["subject_possessive", "property", "value"], "semantic_slots": ["subject_ref", "property_ref", "binding_values"]},
        {"ref": "en:response:designation-multiple", "when": {"action": "report_multiple_bindings", "query_kind": "designation_property", "has_bindings": True}, "template": "{subject_possessive} {property} has multiple matching values: {value}.", "required_slots": ["subject_possessive", "property", "value"], "semantic_slots": ["subject_ref", "property_ref", "binding_values"]},
        {"ref": "en:response:state", "when": {"action": "answer_bindings", "query_kind": "state_query", "has_bindings": True}, "template": "{subject_possessive} {property} is {value}.", "required_slots": ["subject_possessive", "property", "value"], "semantic_slots": ["subject_ref", "property_ref", "binding_values"]},
        {"ref": "en:response:state-multiple", "when": {"action": "report_multiple_bindings", "query_kind": "state_query", "has_bindings": True}, "template": "{subject_possessive} {property} has multiple matching values: {value}.", "required_slots": ["subject_possessive", "property", "value"], "semantic_slots": ["subject_ref", "property_ref", "binding_values"]},
        {"ref": "en:response:type", "when": {"action": "answer_bindings", "query_kind": "type_query", "has_bindings": True}, "template": "{subject} {copula} a {value}.", "required_slots": ["subject", "copula", "value"], "semantic_slots": ["subject_ref", "binding_values"]},
        {"ref": "en:response:type-multiple", "when": {"action": "report_multiple_bindings", "query_kind": "type_query", "has_bindings": True}, "template": "{subject} may match multiple types: {value}.", "required_slots": ["subject", "value"], "semantic_slots": ["subject_ref", "binding_values"]},
        {"ref": "en:response:operational-normal", "when": {"action": "report_operational_condition", "qualifiers": {"assessment_status": "operating_normally"}}, "template": "I am operating normally and able to respond.", "required_slots": [], "semantic_slots": ["target_ref", "assessment_status", "snapshot_ref"]},
        {"ref": "en:response:operational-degraded", "when": {"action": "report_operational_condition", "qualifiers": {"assessment_status": "degraded"}}, "template": "I am operating, but some runtime resources are degraded.", "required_slots": [], "semantic_slots": ["target_ref", "assessment_status", "snapshot_ref"]},
        {"ref": "en:response:operational-unavailable", "when": {"action": "report_operational_condition", "qualifiers": {"assessment_status": "unavailable"}}, "template": "I have runtime blockers that limit what I can do right now.", "required_slots": [], "semantic_slots": ["target_ref", "assessment_status", "snapshot_ref"]},
        {"ref": "en:response:operational-unknown", "when": {"action": "report_operational_condition", "qualifiers": {"assessment_status": "unknown"}}, "template": "I cannot verify my full runtime condition right now.", "required_slots": [], "semantic_slots": ["target_ref", "assessment_status", "snapshot_ref"]},
        {"ref": "en:response:relation-supported", "when": {"action": "confirm", "query_kind": "relation_query"}, "template": "Yes.", "required_slots": [], "semantic_slots": ["query_ref", "subject_ref", "relation_ref", "object_surface"]},
        {"ref": "en:response:relation-denied", "when": {"action": "deny", "query_kind": "relation_query"}, "template": "No.", "required_slots": [], "semantic_slots": ["query_ref", "subject_ref", "relation_ref", "object_surface"]},
        {"ref": "en:response:relation-unknown", "when": {"action": "report_target_uncertainty", "query_kind": "relation_query"}, "template": "I do not have evidence that {subject} {relation} {object_surface}.", "required_slots": ["subject", "relation", "object_surface"], "semantic_slots": ["query_ref", "subject_ref", "object_surface", "relation_ref"]},
        {"ref": "en:response:type-unknown", "when": {"action": "report_target_uncertainty", "query_kind": "type_query"}, "template": "I do not have enough evidence about {subject}.", "required_slots": ["subject"], "semantic_slots": ["query_ref", "subject_ref"]},
        {"ref": "en:response:designation-unknown", "when": {"action": "report_target_uncertainty", "query_kind": "designation_property"}, "template": "I do not have enough evidence about {subject_possessive} {property}.", "required_slots": ["subject_possessive", "property"], "semantic_slots": ["query_ref", "subject_ref", "property_ref"]},
        {"ref": "en:response:state-unknown", "when": {"action": "report_target_uncertainty", "query_kind": "state_query"}, "template": "I do not have enough evidence about {subject_possessive} {property}.", "required_slots": ["subject_possessive", "property"], "semantic_slots": ["query_ref", "subject_ref", "property_ref"]},
        {"ref": "en:response:learning", "when": {"action": "request_learning_evidence"}, "template": "What does {evidence} refer to here?", "required_slots": ["evidence"], "semantic_slots": ["evidence", "learning_operation", "frontier_ref"]},
        {"ref": "en:response:clarify", "when": {"action": "request_targeted_clarification"}, "template": "Could you clarify {evidence}?", "required_slots": ["evidence"], "semantic_slots": ["evidence", "frontier_ref"]},
        {"ref": "en:response:surface-choice", "when": {"action": "explain_surface_choice"}, "template": "{surface_choice_b} would have been more natural than {surface_choice_a} because I was referring to myself.", "required_slots": ["surface_choice_a", "surface_choice_b"], "semantic_slots": ["surface_decision_ref", "surface_choice_a", "surface_choice_b", "prior_response_ref", "prior_surface"]},
        {"ref": "en:response:attributed-claim", "when": {"action": "acknowledge_attributed_claim"}, "template": "I understand that you think {subject} {copula} {predicate_surface}.", "required_slots": ["subject", "copula", "predicate_surface"], "semantic_slots": ["subject_ref", "predicate_surface", "claim_kind"]},
        {"ref": "en:response:capability-available", "when": {"action": "report_capability", "qualifiers": {"status": "available"}}, "template": "This capability is available.", "required_slots": [], "semantic_slots": ["target_ref", "status"]},
        {"ref": "en:response:capability-degraded", "when": {"action": "report_capability", "qualifiers": {"status": "degraded"}}, "template": "This capability is degraded.", "required_slots": [], "semantic_slots": ["target_ref", "status"]},
        {"ref": "en:response:capability-unavailable", "when": {"action": "report_capability", "qualifiers": {"status": "unavailable"}}, "template": "This capability is unavailable.", "required_slots": [], "semantic_slots": ["target_ref", "status"]},
        {"ref": "en:response:capability-unknown", "when": {"action": "report_capability", "qualifiers": {"status": "unknown"}}, "template": "I cannot verify this capability right now.", "required_slots": [], "semantic_slots": ["target_ref", "status"]},
        {"ref": "en:response:confirm", "when": {"action": "confirm"}, "template": "Yes.", "required_slots": [], "semantic_slots": ["query_ref", "query_kind"]},
        {"ref": "en:response:deny", "when": {"action": "deny"}, "template": "No.", "required_slots": [], "semantic_slots": ["query_ref", "query_kind"]},
        {"ref": "en:response:conflict", "when": {"action": "report_conflict"}, "template": "I found conflicting evidence.", "required_slots": [], "semantic_slots": ["query_ref", "query_kind"]},
        {"ref": "en:response:operation-succeeded", "when": {"action": "report_operation_result"}, "template": "The operation completed.", "required_slots": [], "semantic_slots": ["target_ref"]},
        {"ref": "en:response:directive-declined", "when": {"action": "decline_directive"}, "template": "I could not perform that operation.", "required_slots": [], "semantic_slots": ["target_ref"]},
    ]
    query_response_actions = {
        "answer_bindings",
        "report_multiple_bindings",
        "confirm",
        "deny",
        "report_conflict",
        "report_target_uncertainty",
        "report_operational_condition",
    }
    for rule in grammar_additions:
        if rule.get("when", {}).get("action") in query_response_actions:
            rule["semantic_slots"] = sorted(
                set(rule.get("semantic_slots", ())) | {"query_ref", "query_kind"}
            )
    refs = [str(item.get("ref") or "") for item in grammar_additions]
    if len(refs) != len(set(refs)) or any(not ref for ref in refs):
        raise ValueError("canonical response grammar contains missing or duplicate refs")
    for rule in grammar_additions:
        if not isinstance(rule.get("when"), Mapping):
            raise ValueError(f"response rule has invalid matcher: {rule.get('ref')}")
        if not isinstance(rule.get("required_slots"), list) or not isinstance(rule.get("semantic_slots"), list):
            raise ValueError(f"response rule lacks explicit slot ABI: {rule.get('ref')}")
    data["response_grammar"] = sorted(
        (dict(item) for item in grammar_additions), key=lambda item: str(item["ref"])
    )

    # Learned-pointer verification uses this lexical allow-list. Derive it from
    # the actual closed plans and grammar templates so the list cannot drift from
    # executable surface supervision.
    import re
    grammar = set(data.get("grammar_tokens", ()))
    surface_material = [
        str(item.get("surface_plan", "")) for item in data.get("response_examples", ())
    ] + [str(item.get("template", "")) for item in data["response_grammar"]]
    for material in surface_material:
        without_fields = re.sub(r"\{[^{}]+\}", " ", material)
        grammar.update(
            token.casefold()
            for token in re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?|[^\w\s]", without_fields)
            if token.strip()
        )
    data["grammar_tokens"] = sorted(grammar)
    data["semantic_operational_contract"] = {
        "contract": "CEMM_RUNTIME_IMPLEMENTATION_CONTRACT.md",
        "response_fallback": "same_response_csir_only",
        "perspective": "output_participant_frame",
        "form_schema_algebra": "atomic-feature-v5",
        "operational_status": "cycle_local_structured_assessment",
        "authority_atom_additions": 0,
        "migration_source_pack_hash": migration_source_hash,
    }
    write_hashed(path, data)
    return {
        "migration_source_pack_hash": migration_source_hash,
        "new_pack_hash": data["pack_hash"],
        "preserved_exact_response_examples": len(preserved_exact),
        "response_grammar_rule_count": len(data["response_grammar"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    # Clean reviewed branches must already have one owner per atom. Exact source
    # hashes in the installer prevent this from becoming a drift bypass.
    validate_repository_authority(repo)
    report = migrate_seed(repo / "cemm/data/conversation_foundation.json")
    language_report = migrate_language_pack(
        repo / "cemm/language_packs/en.json",
        repo / "cemm/form_packs/en.json",
    )
    validate_repository_authority(repo)
    print(json.dumps({"status": "migrated", **report, "language": language_report}, indent=2))


if __name__ == "__main__":
    main()
