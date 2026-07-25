#!/usr/bin/env python3
"""Repair and link the CEMM v1 foundational authority bundle.

This is a semantic migration, not a compatibility shim.  It moves reusable
meta-relations/rules out of the family demo, corrects concept hierarchy, keeps
reified state specifications explicit, derives value→dimension indexes, repairs
reviewed source corpora, and validates the complete authority graph before any
file is replaced.
"""
from __future__ import annotations

import argparse
import sys
import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from cemm.authority import (
    FOUNDATIONAL_META_RELATIONS,
    GENERIC_FOUNDATION_RULES,
    load_documents,
    validate_documents,
    validate_pack_constants,
)




def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

FOUNDATION_RELATION_METADATA = {
    "rel:subtype_of": {"foundational": True, "operational": True, "user_visible": False},
    "rel:facet_of": {"foundational": True, "operational": True, "user_visible": False},
    "rel:subrelation_of": {"foundational": True, "operational": True, "user_visible": False},
    "rel:subject_type": {"foundational": True, "operational": True, "user_visible": False},
    "rel:implies_subject_state": {"foundational": True, "operational": True, "user_visible": False},
    "rel:implies_object_state": {"foundational": True, "operational": True, "user_visible": False},
    "rel:state_dimension": {"foundational": True, "operational": True, "user_visible": False, "state_spec_binding": True},
    "rel:state_value": {"foundational": True, "operational": True, "user_visible": False, "state_spec_binding": True},
    "rel:value_of_dimension": {"foundational": True, "operational": True, "user_visible": False, "derived_index": True},
    "rel:entitles_state_dimension": {"foundational": True, "operational": True, "user_visible": False},
    "rel:dimension_domain": {"foundational": True, "operational": True, "user_visible": False},
    "rel:entitles_capability": {"foundational": True, "operational": True, "user_visible": False},
    "rel:entitles_resource": {"foundational": True, "operational": True, "user_visible": False},
    "rel:mechanism_applies_to": {"foundational": True, "operational": True, "user_visible": False},
    "rel:depends_on": {"foundational": True, "operational": True, "user_visible": False},
}


def generic_rules() -> list[dict[str, Any]]:
    return [
        {
            "rule_ref": "rule:subrelation-inheritance",
            "rule_kind": "definition",
            "if": [
                {"operator": "op:relation", "args": {"role:subject": "?r1", "role:relation": "rel:subrelation_of", "role:object": "?r2"}},
                {"operator": "op:relation", "args": {"role:subject": "?x", "role:relation": "?r1", "role:object": "?y"}},
            ],
            "then": [
                {"operator": "op:relation", "args": {"role:subject": "?x", "role:relation": "?r2", "role:object": "?y"}},
            ],
            "confidence": 1.0,
            "authority_status": "reviewed",
        },
        {
            "rule_ref": "rule:relation-subject-type",
            "rule_kind": "definition",
            "if": [
                {"operator": "op:relation", "args": {"role:subject": "?r", "role:relation": "rel:subject_type", "role:object": "?c"}},
                {"operator": "op:relation", "args": {"role:subject": "?x", "role:relation": "?r", "role:object": "?y"}},
            ],
            "then": [
                {"operator": "op:type", "args": {"role:instance": "?x", "role:class": "?c"}},
            ],
            "confidence": 1.0,
            "authority_status": "reviewed",
        },
        {
            "rule_ref": "rule:type-subtype-inheritance",
            "rule_kind": "definition",
            "if": [
                {"operator": "op:type", "args": {"role:instance": "?x", "role:class": "?a"}},
                {"operator": "op:relation", "args": {"role:subject": "?a", "role:relation": "rel:subtype_of", "role:object": "?b"}},
            ],
            "then": [
                {"operator": "op:type", "args": {"role:instance": "?x", "role:class": "?b"}},
            ],
            "confidence": 1.0,
            "authority_status": "reviewed",
        },
        {
            "rule_ref": "rule:relation-subject-state",
            "rule_kind": "entailment",
            "if": [
                {"operator": "op:relation", "args": {"role:subject": "?r", "role:relation": "rel:implies_subject_state", "role:object": "?spec"}},
                {"operator": "op:relation", "args": {"role:subject": "?spec", "role:relation": "rel:state_dimension", "role:object": "?dim"}},
                {"operator": "op:relation", "args": {"role:subject": "?spec", "role:relation": "rel:state_value", "role:object": "?val"}},
                {"operator": "op:relation", "args": {"role:subject": "?x", "role:relation": "?r", "role:object": "?y"}},
            ],
            "then": [
                {"operator": "op:state", "args": {"role:subject": "?x", "role:dimension": "?dim", "role:value": "?val"}},
            ],
            "confidence": 1.0,
            "authority_status": "reviewed",
        },
        {
            "rule_ref": "rule:relation-object-state",
            "rule_kind": "entailment",
            "if": [
                {"operator": "op:relation", "args": {"role:subject": "?r", "role:relation": "rel:implies_object_state", "role:object": "?spec"}},
                {"operator": "op:relation", "args": {"role:subject": "?spec", "role:relation": "rel:state_dimension", "role:object": "?dim"}},
                {"operator": "op:relation", "args": {"role:subject": "?spec", "role:relation": "rel:state_value", "role:object": "?val"}},
                {"operator": "op:relation", "args": {"role:subject": "?x", "role:relation": "?r", "role:object": "?y"}},
            ],
            "then": [
                {"operator": "op:state", "args": {"role:subject": "?y", "role:dimension": "?dim", "role:value": "?val"}},
            ],
            "confidence": 1.0,
            "authority_status": "reviewed",
        },
    ]


def _fact_signature(item: dict[str, Any]) -> str:
    return canonical((item.get("operator"), item.get("stance", "support"), item.get("args", {})))


def _add_atom(data: dict[str, Any], ref: str, kind: str, metadata: dict[str, Any]) -> bool:
    for atom in data.setdefault("atoms", []):
        if atom.get("ref") != ref:
            continue
        if atom.get("kind") != kind:
            raise ValueError(f"foundational atom kind conflict {ref}: {atom.get('kind')} != {kind}")
        merged = dict(atom.get("metadata", {})); merged.update(metadata); atom["metadata"] = merged
        return False
    data["atoms"].append({"ref": ref, "kind": kind, "metadata": dict(metadata)})
    return True


def _add_fact(data: dict[str, Any], fact_ref: str, operator: str, args: dict[str, Any]) -> bool:
    signature = canonical((operator, "support", args))
    if any(_fact_signature(item) == signature for item in data.setdefault("facts", [])):
        return False
    data["facts"].append({
        "fact_ref": fact_ref,
        "operator": operator,
        "args": args,
        "source_ref": "seed",
        "authority_status": "reviewed",
    })
    return True


def _atom_kinds(documents: dict[Path, dict[str, Any]]) -> dict[str, str]:
    output = {}
    for data in documents.values():
        for atom in data.get("atoms", ()):
            ref, kind = str(atom["ref"]), str(atom["kind"])
            if ref in output and output[ref] != kind:
                raise ValueError(f"cross-file atom kind conflict {ref}: {output[ref]} != {kind}")
            output[ref] = kind
    return output


def _convert_concept_hierarchy(data: dict[str, Any], kinds: dict[str, str]) -> int:
    changed = 0
    for fact in data.get("facts", ()):
        if fact.get("operator") != "op:type":
            continue
        args = fact.get("args", {})
        instance = args.get("role:instance")
        class_ref = args.get("role:class")
        if kinds.get(instance) == "concept" and kinds.get(class_ref) == "concept":
            fact["operator"] = "op:relation"
            fact["args"] = {
                "role:subject": instance,
                "role:relation": "rel:subtype_of",
                "role:object": class_ref,
            }
            changed += 1
    return changed


def _state_spec_pairs(documents: dict[Path, dict[str, Any]]) -> dict[str, tuple[str, str]]:
    dimensions: dict[str, set[str]] = {}
    values: dict[str, set[str]] = {}
    for data in documents.values():
        for fact in data.get("facts", ()):
            if fact.get("operator") != "op:relation":
                continue
            args = fact.get("args", {})
            relation = args.get("role:relation")
            subject = args.get("role:subject")
            obj = args.get("role:object")
            if relation == "rel:state_dimension" and isinstance(subject, str) and isinstance(obj, str):
                dimensions.setdefault(subject, set()).add(obj)
            elif relation == "rel:state_value" and isinstance(subject, str) and isinstance(obj, str):
                values.setdefault(subject, set()).add(obj)
    output = {}
    for spec in sorted(set(dimensions) | set(values)):
        if len(dimensions.get(spec, ())) != 1 or len(values.get(spec, ())) != 1:
            raise ValueError(
                f"state specification {spec} is incomplete/ambiguous: "
                f"dimensions={sorted(dimensions.get(spec, ()))}, values={sorted(values.get(spec, ()))}"
            )
        output[spec] = (next(iter(dimensions[spec])), next(iter(values[spec])))
    return output


def repair_authority_documents(repo: Path) -> dict[str, Any]:
    data_dir = repo / "cemm/data"
    paths = sorted(data_dir.glob("*.json"))
    if not paths:
        raise FileNotFoundError("no cemm/data/*.json authority documents")
    base_path = data_dir / "base.json"
    if base_path not in paths:
        raise FileNotFoundError("missing cemm/data/base.json")
    documents = {path: json.loads(path.read_text(encoding="utf-8")) for path in paths}
    base = documents[base_path]

    added_atoms = 0
    for ref in sorted(FOUNDATIONAL_META_RELATIONS):
        added_atoms += int(_add_atom(base, ref, "relation_type", FOUNDATION_RELATION_METADATA[ref]))
    added_atoms += int(_add_atom(base, "label:name", "label_type", {"foundational": True, "designation_family": "name"}))

    # Generic foundations belong to base, never to a domain/demo document.
    generic_atom_refs = set(FOUNDATIONAL_META_RELATIONS)
    for path, data in documents.items():
        if path == base_path:
            continue
        data["atoms"] = [atom for atom in data.get("atoms", ()) if atom.get("ref") not in generic_atom_refs]
        data["rules"] = [
            rule for rule in data.get("rules", ())
            if rule.get("rule_ref") not in GENERIC_FOUNDATION_RULES | {"rule:type-transitive"}
        ]
    base["rules"] = [
        rule for rule in base.get("rules", ())
        if rule.get("rule_ref") not in GENERIC_FOUNDATION_RULES | {"rule:type-transitive"}
    ] + generic_rules()

    kinds = _atom_kinds(documents)
    concept_hierarchy_changes = sum(_convert_concept_hierarchy(data, kinds) for data in documents.values())

    # Name is a designation family, not an ordinary state or ad-hoc relation.
    _add_fact(base, "foundation:name-full-family", "op:relation", {
        "role:subject": "label:name_full",
        "role:relation": "rel:subtype_of",
        "role:object": "label:name",
    })
    _add_fact(base, "foundation:name-alias-family", "op:relation", {
        "role:subject": "label:name_alias",
        "role:relation": "rel:subtype_of",
        "role:object": "label:name",
    })
    for language, surface in (("en", "name"), ("es", "nombre")):
        _add_fact(base, f"foundation:name-label:{language}", "op:designation", {
            "role:target": "label:name",
            "role:label_type": "label:lexical",
            "role:surface": {"literal": {"type": "text", "value": surface}},
            "role:language": {"literal": {"type": "text", "value": language}},
            "role:script": {"literal": {"type": "text", "value": "Latn"}},
            "role:prior": {"literal": {"type": "float", "value": 1.0}},
            "role:preferred": {"literal": {"type": "bool", "value": True}},
        })

    spec_pairs = _state_spec_pairs(documents)
    value_dimension_pairs = set()
    for dimension, value in spec_pairs.values():
        value_dimension_pairs.add((value, dimension))
    # Domain mappings stay with the domain document that owns the value, rather
    # than contaminating base with family-specific atoms.
    atom_owner = {
        atom["ref"]: path
        for path, data in documents.items()
        for atom in data.get("atoms", ())
    }
    derived_value_dimension = 0
    for value, dimension in sorted(value_dimension_pairs):
        owner = atom_owner.get(value, base_path)
        derived_value_dimension += int(_add_fact(documents[owner], f"derived:value-dimension:{hashlib.sha256((value+'|'+dimension).encode()).hexdigest()[:16]}", "op:relation", {
            "role:subject": value,
            "role:relation": "rel:value_of_dimension",
            "role:object": dimension,
        }))

    for data in documents.values():
        data["atoms"] = sorted(data.get("atoms", ()), key=lambda item: item["ref"])
        data["facts"] = sorted(data.get("facts", ()), key=_fact_signature)
        data["rules"] = sorted(data.get("rules", ()), key=lambda item: item["rule_ref"])

    # Validate temporary files before replacing any repository authority file.
    with tempfile.TemporaryDirectory(prefix="cemm-foundation-link-") as tmp:
        tmpdir = Path(tmp)
        temp_paths = []
        for index, (path, data) in enumerate(sorted(documents.items(), key=lambda item: str(item[0]))):
            target = tmpdir / f"{index:03d}-{path.name}"
            target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temp_paths.append(target)
        linked = validate_documents(load_documents(temp_paths), require_foundations=True)

    for path, data in documents.items():
        target = path.with_suffix(path.suffix + ".tmp")
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(target, path)
    return {
        "documents": [str(path.relative_to(repo)) for path in paths],
        "added_foundational_atoms": added_atoms,
        "concept_hierarchy_facts_rewritten": concept_hierarchy_changes,
        "state_specs": len(spec_pairs),
        "value_dimension_indexes_added": derived_value_dimension,
        "linked_bundle": linked.as_dict(),
    }


def repair_training_corpora(repo: Path) -> dict[str, Any]:
    authority_paths = sorted((repo / "cemm/data").glob("*.json"))
    documents = {path: json.loads(path.read_text(encoding="utf-8")) for path in authority_paths}
    kinds = _atom_kinds(documents)
    spec_pairs = _state_spec_pairs(documents)
    value_dimensions: dict[str, set[str]] = {}
    for dimension, value in spec_pairs.values():
        value_dimensions.setdefault(value, set()).add(dimension)
    for data in documents.values():
        for fact in data.get("facts", ()):
            args = fact.get("args", {})
            if fact.get("operator") == "op:relation" and args.get("role:relation") == "rel:value_of_dimension":
                value_dimensions.setdefault(args.get("role:subject"), set()).add(args.get("role:object"))

    candidates = sorted(set((repo / "cemm/training").glob("*.json")))
    candidates += sorted(set((repo / "reference").glob("**/training/*.json")))
    changed_files = []
    subtype_rewrites = 0
    dimension_repairs = 0
    for path in candidates:
        data = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        constants = set(str(ref) for ref in data.get("constant_refs", ()))
        for example in data.get("interpretation_examples", ()):
            semantic = example.get("semantic", {})
            applications = list(semantic.get("apps", ()))
            query = semantic.get("query")
            if query:
                applications += list(query.get("restrictions", ()))
            directive = semantic.get("directive")
            if directive:
                applications += list(directive.get("content", ()))
            for app in applications:
                args = app.get("args", {})
                if app.get("operator") == "op:type":
                    instance = args.get("role:instance")
                    class_ref = args.get("role:class")
                    if kinds.get(instance) == "concept" and kinds.get(class_ref) == "concept":
                        app["operator"] = "op:relation"
                        app["args"] = {
                            "role:subject": instance,
                            "role:relation": "rel:subtype_of",
                            "role:object": class_ref,
                        }
                        constants.add("rel:subtype_of")
                        subtype_rewrites += 1
                        changed = True
                        args = app["args"]
                if app.get("operator") == "op:state" and "role:dimension" not in args:
                    value = args.get("role:value")
                    dimensions = value_dimensions.get(value, set()) if isinstance(value, str) else set()
                    if len(dimensions) != 1:
                        raise ValueError(
                            f"{path}:{example.get('example_ref')}: state supervision lacks an explicit, uniquely licensed dimension"
                        )
                    args["role:dimension"] = next(iter(dimensions))
                    dimension_repairs += 1
                    changed = True
        if constants:
            ordered = sorted(constants)
            if ordered != list(data.get("constant_refs", ())):
                data["constant_refs"] = ordered
                changed = True
        if changed:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            changed_files.append(str(path.relative_to(repo)))
    return {
        "changed_files": changed_files,
        "generic_subtype_rewrites": subtype_rewrites,
        "explicit_dimension_repairs": dimension_repairs,
    }


def main(repo: Path) -> dict[str, Any]:
    authority = repair_authority_documents(repo)
    training = repair_training_corpora(repo)
    data_paths = sorted((repo / "cemm/data").glob("*.json"))
    atom_refs = {
        str(atom["ref"])
        for path in data_paths
        for atom in json.loads(path.read_text(encoding="utf-8")).get("atoms", ())
    }
    pack_paths = sorted((repo / "cemm/language_packs").glob("*.json"))
    validate_pack_constants(pack_paths, atom_refs)
    return {"authority": authority, "training": training, "packs_validated": [str(path.relative_to(repo)) for path in pack_paths]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(main(args.repo.resolve()), ensure_ascii=False, indent=2))
