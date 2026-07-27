#!/usr/bin/env python3
"""Fail-closed migration of en_form_schema_seed.json from v5 to v6."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "cemm" / "training" / "en_form_schema_seed.json"


def find_family_packet(examples, family):
    values = [item["packet"] for item in examples if item.get("family") == family]
    signatures = {json.dumps(item, sort_keys=True, separators=(",", ":")): item for item in values}
    if len(signatures) != 1:
        raise ValueError(f"{family} must have one packet signature before migration")
    return deepcopy(next(iter(signatures.values())))


def ensure_punctuation_lexeme(seed):
    for record in seed.get("lexemes", ()):
        if "?" in record.get("forms", ()):
            features = dict(record.get("features", {}))
            required = {
                "category": "boundary",
                "boundary_type": "interrogative",
                "discourse_force": "query",
                "force_evidence": "query",
            }
            if any(features.get(key) != value for key, value in required.items()):
                raise ValueError("existing ? lexeme conflicts with v6 force evidence")
            # Mark the boundary punctuation as boundary-only so the graph
            # matcher treats it as ignorable evidence, not a competing slot
            # candidate.
            features["boundary_only"] = True
            record["features"] = features
            return
    seed.setdefault("lexemes", []).append({
        "forms": ["?"],
        "features": {
            "category": "boundary",
            "boundary_type": "interrogative",
            "discourse_force": "query",
            "force_evidence": "query",
            "boundary_only": True,
        },
    })


def migrate_roles(seed):
    examples = seed.get("examples", ())
    # First pass: assign roles and default ports.
    for example in examples:
        for annotation in example.get("annotations", ()):
            slot = str(annotation.get("slot") or "")
            if slot == "property":
                annotation["semantic_role"] = "predicate_head"
                annotation.setdefault("ports_provided", ["predicate:designation"])
                annotation.setdefault("ports_required", ["argument:subject"])
            elif slot == "copula":
                annotation["semantic_role"] = "binder"
                annotation.setdefault("ports_provided", ["binder:predication"])
                annotation.setdefault("ports_required", ["argument:subject", "predicate:designation"])
            elif slot in {"target", "subject"}:
                annotation.setdefault("ports_provided", ["argument:subject"])
            elif slot in {"query", "force"}:
                annotation.setdefault("ports_provided", ["force:query"])

    # Second pass: for families without a property/predicate_head slot, the
    # binder cannot require predicate:designation (no slot provides it).  This
    # applies to operational_condition_query, type_query, etc. where the copula
    # binds a state/operational predicate, not a designation property.
    families_with_property: set[str] = set()
    for example in examples:
        if any(str(a.get("slot")) == "property" for a in example.get("annotations", ())):
            families_with_property.add(str(example.get("family")))
    for example in examples:
        family = str(example.get("family"))
        if family in families_with_property:
            continue
        for annotation in example.get("annotations", ()):
            if str(annotation.get("slot")) == "copula":
                required = list(annotation.get("ports_required", []))
                annotation["ports_required"] = [p for p in required if p != "predicate:designation"]

    # Third pass: the meaning_query family's surface slot is intentionally
    # unconstrained (it captures an unknown surface for lexical learning).  But
    # without any constraint it also matches anaphoric/demonstrative units that
    # belong to contextual_meaning_query, causing a schema collision under the
    # v6 graph matcher.  Add absent_features to distinguish the two families:
    # meaning_query's surface must not be anaphoric or demonstrative.
    for example in examples:
        if str(example.get("family")) != "meaning_query":
            continue
        for annotation in example.get("annotations", ()):
            if str(annotation.get("slot")) == "surface":
                absent = list(annotation.get("absent_features", []))
                for feat in ("anaphoric", "demonstrative"):
                    if feat not in absent:
                        absent.append(feat)
                annotation["absent_features"] = absent


def ensure_echo_examples(seed):
    examples = seed.setdefault("examples", [])
    packet = find_family_packet(examples, "designation_query")
    signatures = {
        tuple(str(token).casefold() for token in item.get("tokens", ()))
        for item in examples
        if item.get("family") == "designation_query"
    }
    additions = [
        {
            "family": "designation_query",
            "tokens": ["your", "name", "is", "?"],
            "annotations": [
                {
                    "slot": "target", "start": 0, "end": 1, "kind": "anchor",
                    "capture": "ref", "semantic_role": "subject",
                    "drop_features": ["participant_role", "person"],
                    "ports_provided": ["argument:subject"],
                },
                {
                    "slot": "property", "start": 1, "end": 2,
                    "capture": "features", "semantic_role": "predicate_head",
                    "ports_provided": ["predicate:designation"],
                    "ports_required": ["argument:subject"],
                },
                {
                    "slot": "copula", "start": 2, "end": 3,
                    "capture": "features", "semantic_role": "binder",
                    "ports_provided": ["binder:predication"],
                    "ports_required": ["argument:subject", "predicate:designation"],
                },
                {
                    "slot": "query", "start": 3, "end": 4,
                    "kind": "punctuation", "capture": "features",
                    "semantic_role": "force", "ports_provided": ["force:query"],
                },
            ],
            "packet": deepcopy(packet),
            "weight": 1.75,
        },
        {
            "family": "designation_query",
            "tokens": ["your", "name", "?"],
            "annotations": [
                {
                    "slot": "target", "start": 0, "end": 1, "kind": "anchor",
                    "capture": "ref", "semantic_role": "subject",
                    "drop_features": ["participant_role", "person"],
                    "ports_provided": ["argument:subject"],
                },
                {
                    "slot": "property", "start": 1, "end": 2,
                    "capture": "features", "semantic_role": "predicate_head",
                    "ports_provided": ["predicate:designation"],
                    "ports_required": ["argument:subject"],
                },
                {
                    "slot": "query", "start": 2, "end": 3,
                    "kind": "punctuation", "capture": "features",
                    "semantic_role": "force", "ports_provided": ["force:query"],
                },
            ],
            "packet": deepcopy(packet),
            "weight": 1.65,
        },
    ]
    for item in additions:
        signature = tuple(str(token).casefold() for token in item["tokens"])
        if signature not in signatures:
            examples.append(item)
            signatures.add(signature)


def ensure_graph_contracts(seed):
    contracts = seed.setdefault("family_graph_contracts", {})
    contracts["designation_query"] = {
        "contract_ref": "en:graph-contract:designation-query:v1",
        "hard_constraints": [
            {"kind": "max_distance", "slots": ["target", "property"], "max_distance": 4}
        ],
        "projections": [
            {
                "slot": "copula",
                "source": "constant",
                "value": {"implicit": True, "copular": True, "semantic_port": "predication"},
                "features": {"implicit": True, "copular": True, "semantic_port": "predication"},
                "requires_slots": ["query", "target", "property"],
                "ports_provided": ["binder:predication"],
                "penalty": 0.16,
                "reason": "implicit_copular_binding",
            },
            {
                "slot": "target",
                "source": "context",
                "context_path": "addressee_ref",
                "features": {"projected": True, "participant_role": "addressee", "possessive": True},
                "requires_slots": ["query", "property"],
                "ports_provided": ["argument:subject"],
                "penalty": 0.24,
                "reason": "direct_dialogue_addressee_projection",
            },
        ],
    }


def ensure_negative_probes(seed):
    probes = seed.setdefault("negative_probes", [])
    known = {tuple(str(token).casefold() for token in item.get("tokens", ())) for item in probes}
    additions = [
        {"tokens": ["your", "name", "is"], "reason": "incomplete claim lacks force or value"},
        {"tokens": ["you", "name", "is", "?"], "reason": "nonpossessive target cannot fill designation possessor"},
        {"tokens": ["your", "type", "is", "?"], "reason": "type property must not collide with designation query"},
    ]
    for item in additions:
        signature = tuple(str(token).casefold() for token in item["tokens"])
        if signature not in known:
            probes.append(item)
            known.add(signature)


def migrate(path: Path = SEED) -> None:
    seed = json.loads(path.read_text(encoding="utf-8"))
    if int(seed.get("contract_version", -1)) not in {5, 6}:
        raise ValueError("expected v5 or v6 seed")
    seed["contract_version"] = 6
    ensure_punctuation_lexeme(seed)
    migrate_roles(seed)
    ensure_echo_examples(seed)
    ensure_graph_contracts(seed)
    ensure_negative_probes(seed)
    path.write_text(json.dumps(seed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    migrate()
