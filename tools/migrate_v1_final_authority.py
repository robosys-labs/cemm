#!/usr/bin/env python3
"""Deterministically migrate canonical JSON authority artifacts to final CEMM v1."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any
from repair_v1_foundations import (
    repair_authority_documents,
    repair_training_corpora,
)
from cemm.authority import load_documents, validate_documents, validate_pack_constants


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def literal(value, typ="text"):
    return {"literal": {"type": typ, "value": value}}


STALE_CONTROL_ROLES = {
    "policy.response_goal_relation",
    "policy.response_value_relation",
    "policy.response_state_subject_relation",
    "policy.response_state_spec_relation",
    "policy.state_value_relation",
    "policy.state_dimension_relation",
    "self.response_state_dimension",
    "self.interpretation_state_dimension",
    "self.epistemic_state_dimension",
    "self.ready",
    "self.processing",
    "self.confused",
    "self.resolved",
    "self.unresolved",
    "self.sufficient",
    "self.insufficient",
    "self.uncertain",
}
STALE_STATE_REFS = {
    "dim:response_state",
    "dim:interpretation_state",
    "dim:epistemic_state",
    "value:ready",
    "value:processing",
    "value:confused",
    "value:resolved",
    "value:unresolved",
    "value:sufficient",
    "value:insufficient",
}


def fact_signature(item):
    return canonical((item.get("operator"), item.get("stance", "support"), item.get("args", {})))


def migrate_base(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    controls = dict(data.get("control_symbols", {}))
    response_roles = (
        "policy.response_goal_relation",
        "policy.response_value_relation",
        "policy.response_state_subject_relation",
        "policy.response_state_spec_relation",
    )
    response_relation_refs = {controls[role] for role in response_roles if role in controls}
    old_state_value_relation = controls.get("policy.state_value_relation")
    old_state_dimension_relation = controls.get("policy.state_dimension_relation")
    old_state_relation_refs = {
        ref for ref in (old_state_value_relation, old_state_dimension_relation) if ref
    }
    obsolete_relation_refs = response_relation_refs | old_state_relation_refs

    # Compress the old state-spec indirection into one direct semantic relation.
    # This preserves real value→dimension meaning while deleting response-policy
    # goals/specs and the compiler-era completion relations.
    spec_values: dict[str, set[str]] = {}
    spec_dimensions: dict[str, set[str]] = {}
    response_goals: set[str] = set()
    response_specs: set[str] = set()
    for item in data.get("facts", []):
        args = item.get("args", {})
        if item.get("operator") != "op:relation":
            continue
        relation = args.get("role:relation")
        subject = args.get("role:subject")
        obj = args.get("role:object")
        if not isinstance(subject, str) or not isinstance(obj, str):
            continue
        if relation == old_state_value_relation:
            spec_values.setdefault(subject, set()).add(obj)
        elif relation == old_state_dimension_relation:
            spec_dimensions.setdefault(subject, set()).add(obj)
        elif relation == controls.get("policy.response_goal_relation"):
            response_goals.add(obj)
        elif relation == controls.get("policy.response_value_relation"):
            response_goals.add(subject)
        elif relation == controls.get("policy.response_state_subject_relation"):
            response_goals.add(subject)
        elif relation == controls.get("policy.response_state_spec_relation"):
            response_goals.add(subject)
            response_specs.add(obj)

    value_dimension_pairs = {
        (value, dimension)
        for spec in set(spec_values) & set(spec_dimensions)
        for value in spec_values[spec]
        for dimension in spec_dimensions[spec]
        if value not in STALE_STATE_REFS and dimension not in STALE_STATE_REFS
    }
    stale_refs = set(STALE_STATE_REFS) | obsolete_relation_refs | response_goals | response_specs

    controls = {
        role: ref
        for role, ref in controls.items()
        if role not in STALE_CONTROL_ROLES and not (role.startswith("self.") and role != "self.ref")
    }
    data["control_symbols"] = controls

    facts = []
    for item in data.get("facts", []):
        args = item.get("args", {})
        values = {value for value in args.values() if isinstance(value, str)}
        if item.get("operator") == "op:relation" and args.get("role:relation") in obsolete_relation_refs:
            continue
        if (
            item.get("operator") == "op:state"
            and args.get("role:subject") == controls.get("self.ref", "participant:system")
            and args.get("role:dimension") in STALE_STATE_REFS
        ):
            continue
        if item.get("operator") == "op:designation" and args.get("role:target") in stale_refs:
            continue
        if values & (response_goals | response_specs | STALE_STATE_REFS | obsolete_relation_refs):
            continue
        facts.append(item)
    data["facts"] = facts
    data["atoms"] = [item for item in data.get("atoms", []) if item.get("ref") not in stale_refs]

    atoms = {item["ref"]: item for item in data.get("atoms", [])}
    def add_atom(ref, kind, **metadata):
        if ref in atoms:
            current = atoms[ref]
            if current["kind"] != kind:
                raise ValueError(f"authority kind conflict for {ref}")
            merged = dict(current.get("metadata", {})); merged.update(metadata); current["metadata"] = merged
        else:
            atoms[ref] = {"ref": ref, "kind": kind, "metadata": metadata}

    add_atom("concept:digital_agent", "concept", foundational=True, operational_profile=True)
    add_atom("domain:continuous", "concept", foundational=True, domain_type="continuous")
    dimensions = {
        "dim:runtime_process_support": {"literal_type":"float", "min":0.0, "max":1.0},
        "dim:semantic_runtime_support": {"literal_type":"float", "min":0.0, "max":1.0},
        "dim:language_realizer_support": {"literal_type":"float", "min":0.0, "max":1.0},
        "dim:critical_blocker_count": {"literal_type":"int", "min":0, "max":1000000},
    }
    for ref, metadata in dimensions.items():
        add_atom(ref, "state_dimension", foundational=True, cardinality="one", domain_type="continuous", positive_direction="higher" if ref != "dim:critical_blocker_count" else "lower", **metadata)
    for ref in ("cap:interpret", "cap:realize", "cap:respond"):
        add_atom(ref, "capability", foundational=True)
    for ref in ("resource:runtime_process", "resource:semantic_runtime", "resource:language_realizer", "resource:output_channel"):
        add_atom(ref, "resource", foundational=True)
    add_atom("label:operational", "label_type", foundational=True)
    add_atom("rel:handled_by_adapter", "relation_type", foundational=True, operational=True, user_visible=False)
    add_atom("rel:requires_capability", "relation_type", foundational=True, operational=True, user_visible=False)
    add_atom("rel:value_of_dimension", "relation_type", foundational=True, operational=True, user_visible=False)
    data["atoms"] = sorted(atoms.values(), key=lambda item: item["ref"])

    required_controls = {
        "self.ref": controls.get("self.ref", "participant:system"),
        "profile.subtype_relation": "rel:subtype_of",
        "profile.facet_relation": "rel:facet_of",
        "profile.entitles_dimension_relation": "rel:entitles_state_dimension",
        "profile.dimension_domain_relation": "rel:dimension_domain",
        "profile.entitles_capability_relation": "rel:entitles_capability",
        "profile.entitles_resource_relation": "rel:entitles_resource",
        "profile.mechanism_applies_relation": "rel:mechanism_applies_to",
        "profile.depends_on_relation": "rel:depends_on",
        "policy.adapter_relation": "rel:handled_by_adapter",
        "policy.required_capability_relation": "rel:requires_capability",
        "profile.value_dimension_relation": "rel:value_of_dimension",
    }
    for role, ref in required_controls.items():
        existing = data["control_symbols"].get(role)
        if existing and existing != ref:
            raise ValueError(f"control symbol conflict {role}: {existing} != {ref}")
        data["control_symbols"][role] = ref

    existing = {fact_signature(item) for item in data["facts"]}
    def add_fact(operator, args, **metadata):
        item = {"operator": operator, "args": args, **metadata}
        signature = fact_signature(item)
        if signature not in existing:
            data["facts"].append(item); existing.add(signature)

    self_ref = data["control_symbols"]["self.ref"]
    add_fact("op:type", {"role:instance": self_ref, "role:class": "concept:digital_agent"}, source_ref="seed", authority_status="reviewed")
    for dimension in dimensions:
        add_fact("op:relation", {"role:subject":"concept:digital_agent","role:relation":"rel:entitles_state_dimension","role:object":dimension}, source_ref="seed", authority_status="reviewed")
        add_fact("op:relation", {"role:subject":dimension,"role:relation":"rel:dimension_domain","role:object":"domain:continuous"}, source_ref="seed", authority_status="reviewed")
    for capability in ("cap:interpret", "cap:realize", "cap:respond"):
        add_fact("op:relation", {"role:subject":"concept:digital_agent","role:relation":"rel:entitles_capability","role:object":capability}, source_ref="seed", authority_status="reviewed")
    for resource in ("resource:runtime_process", "resource:semantic_runtime", "resource:language_realizer", "resource:output_channel"):
        add_fact("op:relation", {"role:subject":"concept:digital_agent","role:relation":"rel:entitles_resource","role:object":resource}, source_ref="seed", authority_status="reviewed")
    dependencies = (
        ("cap:respond", "cap:interpret"),
        ("cap:respond", "cap:realize"),
        ("cap:respond", "resource:output_channel"),
        ("cap:interpret", "resource:runtime_process"),
        ("cap:interpret", "resource:semantic_runtime"),
        ("cap:realize", "resource:language_realizer"),
    )
    for subject, target in dependencies:
        add_fact("op:relation", {"role:subject":subject,"role:relation":"rel:depends_on","role:object":target}, source_ref="seed", authority_status="reviewed")
    for value, dimension in sorted(value_dimension_pairs):
        add_fact(
            "op:relation",
            {"role:subject":value,"role:relation":"rel:value_of_dimension","role:object":dimension},
            source_ref="seed",
            authority_status="reviewed",
        )

    labels = {
        "en": {
            "concept:digital_agent":"digital agent",
            "cap:interpret":"interpretation capability",
            "cap:realize":"language realization capability",
            "cap:respond":"response capability",
            "resource:runtime_process":"runtime process",
            "resource:semantic_runtime":"semantic runtime",
            "resource:language_realizer":"language realizer",
            "resource:output_channel":"output channel",
        },
        "es": {
            "concept:digital_agent":"agente digital",
            "cap:interpret":"capacidad de interpretación",
            "cap:realize":"capacidad de realización lingüística",
            "cap:respond":"capacidad de respuesta",
            "resource:runtime_process":"proceso de ejecución",
            "resource:semantic_runtime":"sistema semántico",
            "resource:language_realizer":"realizador lingüístico",
            "resource:output_channel":"canal de salida",
        },
    }
    for language, mapping in labels.items():
        for target, surface in mapping.items():
            add_fact("op:designation", {
                "role:target":target,
                "role:label_type":"label:operational",
                "role:surface":literal(surface),
                "role:language":literal(language),
                "role:script":literal("Latn"),
                "role:prior":literal(1.0, "float"),
                "role:preferred":literal(True, "bool"),
            }, source_ref="seed", authority_status="reviewed")
    data["facts"] = sorted(data["facts"], key=fact_signature)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "removed_refs": sorted(stale_refs),
        "preserved_value_dimension_pairs": len(value_dimension_pairs),
        "self_ref": self_ref,
        "atom_count": len(data["atoms"]),
        "fact_count": len(data["facts"]),
    }


RESPONSE_EXAMPLES = {
    "en": [
        ("confirm", "RESPONSE confirm", "Yes."),
        ("deny", "RESPONSE deny", "No."),
        ("conflict", "RESPONSE report_conflict", "The evidence conflicts."),
        ("uncertain", "RESPONSE report_target_uncertainty", "I do not have enough evidence."),
        ("clarify", "RESPONSE request_targeted_clarification EVIDENCE @E0", "What does @E0 mean here?"),
        ("capability", "RESPONSE report_capability TARGET @A0 SCORE @N0", "My @A0 is at @N0 percent."),
        ("acknowledge", "RESPONSE acknowledge_claim", "I recorded that claim."),
        ("decline", "RESPONSE decline_directive", "I cannot perform that action."),
        ("operation", "RESPONSE report_operation_result", "The operation is complete."),
        ("greet", "RESPONSE greet", "Hello."),
    ],
    "es": [
        ("confirm", "RESPONSE confirm", "Sí."),
        ("deny", "RESPONSE deny", "No."),
        ("conflict", "RESPONSE report_conflict", "La evidencia es contradictoria."),
        ("uncertain", "RESPONSE report_target_uncertainty", "No tengo suficiente evidencia."),
        ("clarify", "RESPONSE request_targeted_clarification EVIDENCE @E0", "¿Qué significa @E0 aquí?"),
        ("capability", "RESPONSE report_capability TARGET @A0 SCORE @N0", "Mi @A0 está al @N0 por ciento."),
        ("acknowledge", "RESPONSE acknowledge_claim", "He registrado esa afirmación."),
        ("decline", "RESPONSE decline_directive", "No puedo realizar esa acción."),
        ("operation", "RESPONSE report_operation_result", "La operación está completa."),
        ("greet", "RESPONSE greet", "Hola."),
    ],
}


def grammar_tokens(surface: str):
    return [
        token.casefold()
        for token in re.findall(r"@[A-Z]\d+|[\wÀ-ÿ'’-]+|[^\w\s]", surface, re.UNICODE)
        if not token.startswith(("@A", "@E", "@N"))
    ]


def migrate_pack(path: Path, authority_refs: set[str]):
    data = json.loads(path.read_text(encoding="utf-8"))
    language = data["language"]
    if language not in RESPONSE_EXAMPLES:
        raise ValueError(f"no final response supervision for language {language}")
    data["version"] = 6
    data["source_classes"] = [
        value for value in data.get("source_classes", []) if value not in {"USER", "SYSTEM"}
    ]
    constant_sources = {
        str(source): str(ref)
        for source, ref in data.get("constant_sources", {}).items()
    }
    if len(set(constant_sources.values())) != len(constant_sources):
        raise ValueError(f"duplicate reviewed constant refs in {path}")

    def ensure_constant(ref: str) -> str:
        if ref not in authority_refs:
            raise ValueError(f"reviewed language constant is absent from authority: {ref}")
        for source, current in constant_sources.items():
            if current == ref:
                if source not in data["source_classes"]:
                    data["source_classes"].append(source)
                return source
        used = {
            int(match.group(1))
            for source in constant_sources
            if (match := re.fullmatch(r"CONST([0-9]+)", source))
        }
        index = 0
        while index in used:
            index += 1
        source = f"CONST{index}"
        constant_sources[source] = ref
        data["source_classes"].append(source)
        return source

    for value in (
        "FRAME_SPEAKER", "FRAME_ADDRESSEE",
        *(f"DIM_OF_A{i}" for i in range(8)),
        "Q0", "Q1", "Q2",
    ):
        if value not in data["source_classes"]:
            data["source_classes"].append(value)
    required_forces = (
        "claim", "query", "description_request", "directive",
        "correction", "retraction", "acknowledgment",
    )
    data["forces"] = sorted(set(data.get("forces", ())) | set(required_forces))
    patched_state_dimensions = 0
    patched_generic_subtypes = 0
    subtype_source = None
    for example in data.get("structured_examples", []):
        target = example.get("target", {})
        if "force" not in target:
            raise ValueError(f"compiled pack has implicit force: {example.get('example_ref')}")
        anchor_kinds = {
            f"A{index}": kind
            for index, kind in re.findall(r"@A([0-7])<([^>]+)>", str(example.get("input", "")))
        }
        for application in target.get("apps", []):
            bindings = application.setdefault("bindings", {})
            if application.get("operator") == "op:type":
                instance_source = bindings.get("role:instance")
                class_source = bindings.get("role:class")
                # Generic concept predication is a type/facet relation between
                # concepts, not an instance-membership assertion about a concept.
                if (
                    anchor_kinds.get(str(instance_source)) == "concept"
                    and anchor_kinds.get(str(class_source)) == "concept"
                ):
                    subtype_source = subtype_source or ensure_constant("rel:subtype_of")
                    application.clear()
                    application.update({
                        "operator": "op:relation",
                        "bindings": {
                            "role:subject": instance_source,
                            "role:relation": subtype_source,
                            "role:object": class_source,
                        },
                    })
                    patched_generic_subtypes += 1
                    bindings = application["bindings"]
            if application.get("operator") != "op:state":
                continue
            if "role:dimension" in bindings:
                continue
            value_source = bindings.get("role:value")
            if isinstance(value_source, str) and re.fullmatch(r"A[0-7]", value_source):
                bindings["role:dimension"] = "DIM_OF_" + value_source
                patched_state_dimensions += 1
            else:
                raise ValueError(
                    f"state example lacks an explicit/resolvable dimension: {example.get('example_ref')}"
                )
    data["constant_sources"] = dict(sorted(constant_sources.items()))
    for source in data["constant_sources"]:
        if source not in data["source_classes"]:
            data["source_classes"].append(source)
    if patched_generic_subtypes and "op:relation" not in data.get("operators", []):
        data.setdefault("operators", []).append("op:relation")
        data["operators"] = sorted(set(data["operators"]))
    data["realization_examples"] = [
        item for item in data.get("realization_examples", [])
        if not str(item.get("semantic", "")).startswith("PLAN ")
    ]
    response_examples = [
        {
            "example_ref": f"{language}:response:{name}",
            "semantic": semantic,
            "surface_plan": surface,
            "weight": 1.0,
        }
        for name, semantic, surface in RESPONSE_EXAMPLES[language]
    ]
    data["response_examples"] = response_examples
    forms = set(value.casefold() for value in data.get("function_forms", ()))
    if language == "es":
        forms.add("estoy")
    data["function_forms"] = sorted(forms)
    grammar = set(value.casefold() for value in data.get("grammar_tokens", ()))
    for item in response_examples:
        grammar.update(grammar_tokens(item["surface_plan"]))
    data["grammar_tokens"] = sorted(grammar)
    data.pop("pack_hash", None)
    data["pack_hash"] = hashlib.sha256(canonical(data).encode()).hexdigest()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "language": language,
        "pack_hash": data["pack_hash"],
        "response_examples": len(response_examples),
        "patched_state_dimensions": patched_state_dimensions,
        "patched_generic_subtypes": patched_generic_subtypes,
        "constant_sources": len(data["constant_sources"]),
    }

def main(repo: Path):
    # Step 1 retires the old outcome/global-self authority in base.
    base_path = repo / "cemm/data/base.json"
    base_report = migrate_base(base_path)

    # Step 2 links the complete repository authority, not base.json alone.
    # Generic relations/rules are moved to base; all domain files and source
    # corpora are repaired before packs are accepted.
    foundation_report = repair_authority_documents(repo)
    training_report = repair_training_corpora(repo)
    data_paths = sorted((repo / "cemm/data").glob("*.json"))
    linked = validate_documents(load_documents(data_paths), require_foundations=True)
    authority_refs = {
        str(atom["ref"])
        for path in data_paths
        for atom in json.loads(path.read_text(encoding="utf-8")).get("atoms", ())
    }

    report = {
        "base": base_report,
        "foundations": foundation_report,
        "training": training_report,
        "linked_bundle": linked.as_dict(),
        "packs": [],
    }
    pack_paths = []
    for path in sorted((repo / "cemm/language_packs").glob("*.json")):
        if path.name.endswith(".v1.json"):
            path.unlink()
            continue
        report["packs"].append(migrate_pack(path, authority_refs))
        pack_paths.append(path)
    validate_pack_constants(pack_paths, authority_refs)
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(main(args.repo.resolve()), ensure_ascii=False, indent=2))
