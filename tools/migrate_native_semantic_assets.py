#!/usr/bin/env python3
"""Deterministically migrate CEMM authority and English form supervision.

This migration changes sources of truth, not generated packs alone.  It is
idempotent and fail-closed: duplicate families, conflicting operator roles or
malformed prior learning qualifiers are rejected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

TARGET_CONTRACT_VERSION = 7
DESIGNATION_CONTRACT = "contract:designation_learning"


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def add_operator_role(base: dict[str, Any], role_ref: str, filler_kind: str = "atom") -> bool:
    rows = list(base.setdefault("operator_roles", []))
    matches = [
        item for item in rows
        if item.get("operator_ref") == "op:event" and item.get("role_ref") == role_ref
    ]
    expected = {
        "operator_ref": "op:event",
        "role_ref": role_ref,
        "required": False,
        "filler_kind": filler_kind,
    }
    if len(matches) > 1:
        raise ValueError(f"duplicate event operator role: {role_ref}")
    if matches:
        if canonical(matches[0]) != canonical(expected):
            raise ValueError(f"conflicting event operator role: {role_ref}")
        return False
    rows.append(expected)
    rows.sort(key=lambda item: (str(item.get("operator_ref")), str(item.get("role_ref"))))
    base["operator_roles"] = rows
    return True


_OPEN_CLASS_LEMMAS = {
    "know": "rel:knows",
    "mean": "event:define",
    "signify": "event:define",
    "say": "event:say",
    "call": "event:name",
    "learn": "event:learn",
    "remember": "event:remember",
    "prefer": "rel:prefers",
    "want": "event:want",
    "intend": "event:intend",
    "teach": "event:teach",
    "forget": "event:forget",
    "define": "event:define",
    "translate": "event:translate",
    "infer": "event:infer",
}


_OPEN_CLASS_FORMS = {
    "want": ["want", "wants", "wanted", "wanting"],
    "intend": ["intend", "intends", "intended", "intending"],
    "teach": ["teach", "teaches", "taught", "teaching"],
    "forget": ["forget", "forgets", "forgot", "forgotten", "forgetting"],
    "define": ["define", "defines", "defined", "defining"],
    "translate": ["translate", "translates", "translated", "translating"],
    "infer": ["infer", "infers", "inferred", "inferring"],
}


def _clean_open_class_lexemes(seed: dict[str, Any]) -> int:
    changed = 0
    lexemes = list(seed.setdefault("lexemes", []))
    present_lemmas: set[str] = set()
    for record in lexemes:
        features = dict(record.get("features", {}))
        lemma = str(features.get("lemma") or "")
        if lemma not in _OPEN_CLASS_LEMMAS:
            if features.get("property_ref") == "label:full_name":
                features["property_ref"] = "label:name_full"
                record["features"] = features
                changed += 1
            continue
        present_lemmas.add(lemma)
        before = canonical(features)
        features = {
            key: value
            for key, value in features.items()
            if key not in {
                "semantic_port", "relation_ref", "predicate",
                "semantic_target_hint", "semantic_ref", "semantic_kind",
                "property_ref", "capability_ref", "state_dimension_ref",
                "contribution_kind", "affordance_ref",
                "ports_provided", "ports_required",
            }
        }
        features.update({
            "category": "verb",
            "lemma": lemma,
            "open_class": True,
        })
        # The reviewed installer-time lemma map selects supervision targets.
        # No semantic target hint is emitted into source or runtime form packs.
        record["features"] = features
        changed += int(canonical(features) != before)
    for lemma, forms in sorted(_OPEN_CLASS_FORMS.items()):
        if lemma in present_lemmas:
            continue
        lexemes.append({
            "forms": forms,
            "features": {
                "category": "verb",
                "lemma": lemma,
                "open_class": True,
            },
        })
        changed += 1
    lexemes.sort(key=lambda item: (str(item.get("features", {}).get("lemma", "")), canonical(item.get("forms", []))))
    seed["lexemes"] = lexemes
    return changed



def _semantic_target_kind(ref: str) -> str:
    if ref.startswith("event:"):
        return "event_type"
    if ref.startswith("rel:"):
        return "relation_type"
    if ref.startswith("label:"):
        return "label_type"
    if ref.startswith("cap:"):
        return "capability"
    if ref.startswith("dim:"):
        return "state_dimension"
    if ref.startswith("value:"):
        return "value"
    return "concept"


def _migrate_open_class_annotations(seed: dict[str, Any]) -> int:
    """Move existing predicate identity from lexical features to semantic anchors.

    The source token and lemma remain language evidence. The predicate slot is
    replayed as the designation target named by semantic_target_hint, and packet
    templates capture that target ref. This preserves existing construction
    families without allowing the language pack to own semantic identity.
    """
    changed = 0
    by_form: dict[str, tuple[str, str]] = {}
    for record in seed.get("lexemes", ()):
        features = dict(record.get("features", {}))
        lemma = str(features.get("lemma") or "")
        target = _OPEN_CLASS_LEMMAS.get(lemma, "")
        if not target:
            continue
        kind = _semantic_target_kind(target)
        for form in record.get("forms", ()):
            by_form[str(form).casefold()] = (target, kind)

    def replace_template(value: Any, slot_targets: Mapping[str, str]) -> int:
        local = 0
        if isinstance(value, dict):
            for key, nested in list(value.items()):
                if isinstance(nested, dict) and "$feature" in nested:
                    path = str(nested["$feature"])
                    slot, _, feature = path.partition(".")
                    if slot in slot_targets and feature in {"semantic_ref", "relation_ref", "semantic_port"}:
                        value[key] = {"$capture": slot}
                        local += 1
                        continue
                if isinstance(nested, str) and nested.startswith("$feature:"):
                    path = nested.split(":", 1)[1]
                    slot, _, feature = path.partition(".")
                    if slot in slot_targets and feature in {"semantic_ref", "relation_ref", "semantic_port"}:
                        value[key] = f"$capture:{slot}"
                        local += 1
                        continue
                local += replace_template(nested, slot_targets)
        elif isinstance(value, list):
            for nested in value:
                local += replace_template(nested, slot_targets)
        return local

    for example in seed.get("examples", ()):
        tokens = [str(item) for item in example.get("tokens", ())]
        slot_targets: dict[str, str] = {}
        for annotation in example.get("annotations", ()):
            start, end = int(annotation.get("start", -1)), int(annotation.get("end", -1))
            if end != start + 1 or not 0 <= start < len(tokens):
                continue
            resolved = by_form.get(tokens[start].casefold())
            if not resolved:
                continue
            target, kind = resolved
            role = str(annotation.get("semantic_role") or "")
            slot = str(annotation.get("slot") or "")
            if role not in {"predicate", "predicate_head"} and slot not in {
                "predicate", "definition_predicate", "desire_predicate",
                "knowledge_predicate", "event_type",
            }:
                continue
            before = canonical(annotation)
            annotation["kind"] = "anchor"
            annotation["capture"] = "ref"
            annotation["semantic_ref"] = target
            annotation["atom_kind"] = kind
            required = dict(annotation.get("required_features", {}))
            for key in ("semantic_port", "relation_ref", "lemma"):
                required.pop(key, None)
            required.update({
                "semantic_contribution_abi": 1,
                "contribution_kind": "predicate",
                "semantic_kind": kind,
            })
            annotation["required_features"] = required
            if "drop_features" in annotation:
                filtered_drop = [
                    item for item in annotation.get("drop_features", ())
                    if item not in {"semantic_port", "relation_ref", "semantic_ref"}
                ]
                if filtered_drop:
                    annotation["drop_features"] = filtered_drop
                else:
                    annotation.pop("drop_features", None)
            if "keep_features" in annotation:
                filtered_keep = [
                    item for item in annotation.get("keep_features", ())
                    if item not in {"semantic_port", "relation_ref"}
                ]
                if filtered_keep:
                    annotation["keep_features"] = filtered_keep
                else:
                    annotation.pop("keep_features", None)
            slot_targets[slot] = target
            changed += int(canonical(annotation) != before)
        changed += replace_template(example.get("packet", {}), slot_targets)

    forbidden = []
    def scan(value: Any, path: str = "root") -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                if key == "semantic_port" or (isinstance(nested, str) and "semantic_port" in nested):
                    forbidden.append(f"{path}.{key}")
                scan(nested, f"{path}.{key}")
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                scan(nested, f"{path}[{index}]")
    scan(seed)
    if forbidden:
        raise ValueError("legacy semantic_port survived source migration: " + ",".join(forbidden[:12]))
    return changed



_ARGUMENT_PORT_BY_ROLE = {
    "subject": "argument:subject",
    "actor": "argument:subject",
    "experiencer": "argument:subject",
    "knower": "argument:subject",
    "speaker": "argument:subject",
    "object": "argument:object",
    "content": "argument:object",
    "definition": "argument:object",
    "target": "argument:target",
    "value": "argument:value",
}


def _ensure_argument_ports(seed: dict[str, Any]) -> int:
    """Give graph arguments canonical kernel-role ports.

    Existing v6 supervision was inconsistent about declaring ports on literal
    and open spans because lexical semantic_port features previously carried
    much of the burden. Semantic-target affordances now provide exact predicate
    requirements, so every meaning-bearing argument slot must expose its role.
    """
    changed = 0
    for example in seed.get("examples", ()):
        for annotation in example.get("annotations", ()):
            role = str(annotation.get("semantic_role") or "")
            port = _ARGUMENT_PORT_BY_ROLE.get(role)
            if not port:
                continue
            ports = list(dict.fromkeys(map(str, annotation.get("ports_provided", ()))))
            if port not in ports:
                ports.append(port)
                annotation["ports_provided"] = sorted(ports)
                changed += 1
    return changed


def _rewrite_legacy_learning(value: Any) -> int:
    changed = 0
    if isinstance(value, dict):
        if value.get("learning_operation") == "resolve_designation":
            value.pop("learning_operation")
            value["learning_contract_ref"] = DESIGNATION_CONTRACT
            changed += 1
        for key, nested in list(value.items()):
            if isinstance(nested, str) and nested == "$feature:predicate.semantic_port":
                value[key] = "$feature:predicate.semantic_ref"
                changed += 1
            else:
                changed += _rewrite_legacy_learning(nested)
    elif isinstance(value, list):
        for nested in value:
            changed += _rewrite_legacy_learning(nested)
    return changed


def _annotation(
    slot: str,
    start: int,
    end: int,
    role: str,
    *,
    kind: str | None = None,
    capture: str = "features",
    semantic_ref: str | None = None,
    atom_kind: str | None = None,
    required_features: Mapping[str, Any] | None = None,
    ports_provided: tuple[str, ...] = (),
    ports_required: tuple[str, ...] = (),
    optional: bool = False,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "slot": slot,
        "start": start,
        "end": end,
        "capture": capture,
        "semantic_role": role,
    }
    if kind:
        item["kind"] = kind
    if semantic_ref:
        item["semantic_ref"] = semantic_ref
    if atom_kind:
        item["atom_kind"] = atom_kind
    if required_features:
        item["required_features"] = dict(required_features)
    if ports_provided:
        item["ports_provided"] = list(ports_provided)
    if ports_required:
        item["ports_required"] = list(ports_required)
    if optional:
        item["optional"] = True
    return item


def _predicate_annotation(slot: str, start: int, semantic_ref: str, atom_kind: str) -> dict[str, Any]:
    return _annotation(
        slot, start, start + 1, "predicate_head",
        kind="anchor", capture="ref", semantic_ref=semantic_ref, atom_kind=atom_kind,
        required_features={
            "semantic_contribution_abi": 1,
            "contribution_kind": "predicate",
            "semantic_kind": atom_kind,
        },
        ports_provided=(f"predicate:{'event' if atom_kind == 'event_type' else 'relation'}",),
    )


def _capability_inventory_example() -> dict[str, Any]:
    return {
        "family": "capability_inventory_query",
        "tokens": ["what", "can", "you", "do", "?"],
        "annotations": [
            _annotation("query", 0, 1, "force", capture="features", ports_provided=("force:query",)),
            _annotation("modal", 1, 2, "scope", capture="features", ports_provided=("scope:capability",)),
            _annotation(
                "target", 2, 3, "subject", kind="anchor", capture="ref",
                semantic_ref="participant:system", atom_kind="participant",
                ports_provided=("argument:subject",),
            ),
            _annotation("action", 3, 4, "binder", capture="features", ports_required=("scope:capability", "argument:subject")),
            _annotation("boundary", 4, 5, "punctuation", kind="punctuation", capture="features", optional=True),
        ],
        "packet": {
            "force": "query",
            "apps": [],
            "query": {
                "restrictions": [
                    {
                        "operator": "op:type",
                        "args": {"role:instance": {"$capture": "target"}, "role:class": "?agent_class"},
                        "stance": "support",
                    },
                    {
                        "operator": "op:relation",
                        "args": {
                            "role:subject": "?agent_class",
                            "role:relation": "rel:entitles_capability",
                            "role:object": "?capability",
                        },
                        "stance": "support",
                    },
                ],
                "variables": [
                    {"ref": "?agent_class", "filler_kind": "concept", "role_ref": "role:class"},
                    {"ref": "?capability", "filler_kind": "atom", "role_ref": "role:object"},
                ],
                "projection": ["?capability"],
                "qualifiers": {
                    "query_kind": "capability_inventory_query",
                    "answer_cardinality": "many",
                    "target_ref": {"$capture": "target"},
                },
            },
            "directive": None,
            "describe": None,
            "qualifiers": {"construction_family": "capability_inventory_query"},
            "modality": "capability",
        },
        "weight": 1.85,
    }


def _learning_answer_examples() -> list[dict[str, Any]]:
    def build(tokens: list[str], *, anaphor_kind: str, with_modifier: bool) -> dict[str, Any]:
        predicate_index = 2 if with_modifier else 1
        target_index = predicate_index + 1
        annotations = [
            _annotation(
                "anaphor", 0, 1, "reference", kind=anaphor_kind, capture="features",
                semantic_ref=("participant:system" if anaphor_kind == "anchor" else None),
                atom_kind=("participant" if anaphor_kind == "anchor" else None),
                required_features={"anaphoric": True},
                ports_provided=("reference:pending_learning",),
            )
        ]
        if with_modifier:
            annotations.append(_annotation("modifier", 1, 2, "modifier", capture="features", optional=True))
        annotations.extend([
            _predicate_annotation("definition_predicate", predicate_index, "event:define", "event_type"),
            _annotation(
                "meaning_target", target_index, target_index + 1, "object", kind="anchor", capture="ref",
                semantic_ref="event:greeting", atom_kind="event_type",
                ports_provided=("argument:definition",),
            ),
        ])
        return {
            "family": "designation_learning_answer",
            "tokens": tokens,
            "annotations": annotations,
            "packet": {
                "force": "claim",
                "apps": [
                    {
                        "operator": "op:designation",
                        "args": {
                            "role:target": {"$capture": "meaning_target"},
                            "role:label_type": "label:lexical",
                            "role:surface": {"$context": "pending_learning_surface_literal"},
                            "role:language": {"$context": "language_literal"},
                            "role:script": {"$context": "script_literal"},
                            "role:prior": {"$context": "one_float_literal"},
                            "role:preferred": {"$context": "true_literal"},
                        },
                        "stance": "support",
                    }
                ],
                "query": None,
                "directive": None,
                "describe": None,
                "qualifiers": {
                    "construction_family": "designation_learning_answer",
                    "consumes_pending_learning": True,
                    "pending_learning_obligation_ref": {"$context": "pending_learning_obligation_ref"},
                    "learning_plan_ref": {"$context": "pending_learning_plan_ref"},
                },
                "modality": "actual",
            },
            "weight": 2.0,
        }
    return [
        build(["it", "just", "means", "hi"], anaphor_kind="function", with_modifier=True),
        build(["it", "means", "hi"], anaphor_kind="function", with_modifier=False),
    ]


def _definition_claim_example() -> dict[str, Any]:
    return {
        "family": "definition_designation_claim",
        "tokens": ["glorp", "means", "hi"],
        "annotations": [
            {
                "slot": "surface",
                "start": 0,
                "end": 1,
                "span": True,
                "capture": "literal:text",
                "semantic_role": "subject_surface",
                "allowed_kinds": ["anchor", "span", "unknown"],
                "max_units": 4,
                "ports_provided": ["argument:surface"],
            },
            _predicate_annotation("definition_predicate", 1, "event:define", "event_type"),
            _annotation(
                "meaning_target", 2, 3, "object", kind="anchor", capture="ref",
                semantic_ref="event:greeting", atom_kind="event_type",
                ports_provided=("argument:definition",),
            ),
        ],
        "packet": {
            "force": "claim",
            "apps": [{
                "operator": "op:designation",
                "args": {
                    "role:target": {"$capture": "meaning_target"},
                    "role:label_type": "label:lexical",
                    "role:surface": {"$capture": "surface"},
                    "role:language": {"$context": "language_literal"},
                    "role:script": {"$context": "script_literal"},
                    "role:prior": {"$context": "one_float_literal"},
                    "role:preferred": {"$context": "true_literal"},
                },
                "stance": "support",
            }],
            "query": None,
            "directive": None,
            "describe": None,
            "qualifiers": {"construction_family": "definition_designation_claim"},
            "modality": "actual",
        },
        "weight": 1.95,
    }


def _generic_type_predication_example() -> dict[str, Any]:
    return {
        "family": "generic_type_predication",
        "tokens": ["CEMM", "is", "agent"],
        "annotations": [
            _annotation(
                "subject", 0, 1, "subject", kind="anchor", capture="ref",
                semantic_ref="participant:system", atom_kind="participant",
                ports_provided=("argument:subject",),
            ),
            _annotation(
                "binder", 1, 2, "binder", capture="features",
                ports_provided=("binder:predication",),
                ports_required=("argument:subject", "predicate:type"),
            ),
            _annotation(
                "predicate", 2, 3, "predicate_head", kind="anchor", capture="ref",
                semantic_ref="concept:agent", atom_kind="concept",
                required_features={
                    "semantic_contribution_abi": 1,
                    "contribution_kind": "predicate",
                    "semantic_kind": "concept",
                },
                ports_provided=("predicate:type",),
                ports_required=("argument:subject",),
            ),
        ],
        "packet": {
            "force": "claim",
            "apps": [{
                "operator": "op:type",
                "args": {
                    "role:instance": {"$capture": "subject"},
                    "role:class": {"$capture": "predicate"},
                },
                "stance": "support",
            }],
            "query": None,
            "directive": None,
            "describe": None,
            "qualifiers": {"construction_family": "generic_type_predication"},
            "modality": "actual",
        },
        "weight": 1.7,
    }


def _generic_state_value_predication_example(
    *,
    subject_surface: str,
    subject_ref: str,
    value_surface: str,
    value_ref: str,
    dimension_ref: str,
) -> dict[str, Any]:
    return {
        "family": "generic_state_value_predication",
        "tokens": [subject_surface, "is", value_surface],
        "annotations": [
            _annotation(
                "subject", 0, 1, "subject", kind="anchor", capture="ref",
                semantic_ref=subject_ref, atom_kind="participant",
                ports_provided=("argument:subject",),
            ),
            _annotation(
                "binder", 1, 2, "binder", capture="features",
                ports_provided=("binder:predication",),
                ports_required=("argument:subject", "predicate:state_value"),
            ),
            _annotation(
                "predicate", 2, 3, "predicate_head", kind="anchor", capture="ref",
                semantic_ref=value_ref, atom_kind="value",
                required_features={
                    "semantic_contribution_abi": 1,
                    "contribution_kind": "predicate",
                    "semantic_kind": "value",
                    "state_dimension_ref": dimension_ref,
                },
                ports_provided=("predicate:state_value", "argument:value"),
                ports_required=("argument:subject",),
            ),
        ],
        "packet": {
            "force": "claim",
            "apps": [{
                "operator": "op:state",
                "args": {
                    "role:subject": {"$capture": "subject"},
                    "role:dimension": {"$feature": "predicate.state_dimension_ref"},
                    "role:value": {"$capture": "predicate"},
                },
                "stance": "support",
            }],
            "query": None,
            "directive": None,
            "describe": None,
            "qualifiers": {"construction_family": "generic_state_value_predication"},
            "modality": "actual",
        },
        "weight": 1.7,
    }


def _reaction_example() -> dict[str, Any]:
    return {
        "family": "semantic_discourse_reaction",
        "tokens": ["wow", "lol"],
        "nonblocking_token_indices": [0],
        "annotations": [
            _annotation(
                "reaction", 1, 2, "discourse", kind="anchor", capture="ref",
                semantic_ref="concept:laughing_out_loud", atom_kind="concept",
                required_features={
                    "semantic_contribution_abi": 1,
                    "contribution_kind": "discourse",
                    "reaction_kind": "amusement",
                },
                ports_provided=("discourse:reaction",),
            ),
        ],
        "packet": {
            "force": "acknowledgment",
            "apps": [],
            "query": None,
            "directive": None,
            "describe": None,
            "qualifiers": {
                "construction_family": "semantic_discourse_reaction",
                "reaction_ref": {"$capture": "reaction"},
                "reaction_kind": {"$feature": "reaction.reaction_kind"},
            },
            "modality": "actual",
        },
        "weight": 1.25,
    }


def migrate_seed(seed: dict[str, Any]) -> dict[str, int]:
    changed = 0
    seed["version"] = TARGET_CONTRACT_VERSION
    seed["contract_version"] = TARGET_CONTRACT_VERSION
    changed += _clean_open_class_lexemes(seed)
    changed += _migrate_open_class_annotations(seed)
    changed += _rewrite_legacy_learning(seed)
    # Remove the sentence-shaped embedded proposition program. Recursive
    # graphlets and reviewed proposition-taking frames are the sole owner.
    examples_before = list(seed.get("examples", ()))
    seed["examples"] = [
        item for item in examples_before
        if item.get("family") != "desire_knowledge_designation_query"
    ]
    changed += len(examples_before) - len(seed["examples"])
    justifications = dict(seed.get("singleton_family_justifications", {}))
    changed += int("desire_knowledge_designation_query" in justifications)
    justifications.pop("desire_knowledge_designation_query", None)
    seed["singleton_family_justifications"] = justifications

    # Normalize the complete pre-existing source before computing signatures.
    changed += _ensure_argument_ports(seed)

    additions = [
        _capability_inventory_example(),
        *_learning_answer_examples(),
        _definition_claim_example(),
        _generic_type_predication_example(),
        _generic_state_value_predication_example(
            subject_surface="CEMM", subject_ref="participant:system",
            value_surface="available", value_ref="value:available",
            dimension_ref="dim:availability",
        ),
        _generic_state_value_predication_example(
            subject_surface="I", subject_ref="participant:user",
            value_surface="remembered", value_ref="value:remembered",
            dimension_ref="dim:memory_status",
        ),
        _reaction_example(),
    ]
    # New reviewed families must enter in the same canonical shape produced for
    # an already-migrated source. Otherwise a second run changes their signature
    # and appends duplicates.
    additions_seed = {"lexemes": list(seed.get("lexemes", ())), "examples": additions}
    _migrate_open_class_annotations(additions_seed)
    _ensure_argument_ports(additions_seed)
    additions = list(additions_seed["examples"])

    examples = list(seed.setdefault("examples", []))
    by_signature = {canonical(item): item for item in examples}
    for item in additions:
        signature = canonical(item)
        if signature not in by_signature:
            examples.append(item)
            by_signature[signature] = item
            changed += 1
    seed["examples"] = examples

    justifications = dict(seed.setdefault("singleton_family_justifications", {}))
    for family, text in {
        "capability_inventory_query": "Reviewed generic capability projection over participant type and entitlement authority; not a phrase-specific response branch.",
        "definition_designation_claim": "Reviewed generic surface-to-target designation assertion used for direct lexical definition teaching.",
        "generic_type_predication": "Reviewed semantic-kind-driven type lowering; the lexical predicate is supplied by designation affordance authority.",
        "semantic_discourse_reaction": "Reviewed discourse-affordance composition that creates acknowledgment force without world-state assertion.",
    }.items():
        justifications.setdefault(family, text)
    # designation_learning_answer has two examples and therefore uses leave-one-out.
    seed["singleton_family_justifications"] = justifications
    return {"changed": changed, "example_count": len(examples)}


def migrate_generator_text(text: str) -> str:
    text = text.replace("feature-algebra v6", "feature-algebra v7")
    text = text.replace("FEATURE_ALGEBRA_VERSION = 6", "FEATURE_ALGEBRA_VERSION = 7")
    text = text.replace('"receipt_version": 6', '"receipt_version": 7')
    old = '''        if annotation.get("kind") == "anchor":\n            kind = "anchor"\n            semantic_ref = f"replay:anchor:{annotation['slot']}"\n            atom_kind = "participant"\n            source_kind = "replay"\n'''
    new = '''        if annotation.get("kind") == "anchor":\n            kind = "anchor"\n            semantic_ref = str(\n                annotation.get("semantic_ref")\n                or features.get("semantic_ref")\n                or f"replay:anchor:{annotation['slot']}"\n            )\n            atom_kind = str(\n                annotation.get("atom_kind")\n                or features.get("semantic_kind")\n                or "participant"\n            )\n            source_kind = "replay"\n'''
    count = text.count(old)
    if count == 1:
        text = text.replace(old, new, 1)
    elif new not in text:
        raise ValueError(f"generator replay anchor expected once, found {count}")
    old = '''        "function_forms": sorted({form for record in seed.get("lexemes", ()) for form in record.get("forms", ())}),\n'''
    new = '''        "function_forms": sorted({\n            form\n            for record in seed.get("lexemes", ())\n            if not bool(dict(record.get("features", {})).get("open_class"))\n            for form in record.get("forms", ())\n        }),\n'''
    count = text.count(old)
    if count == 1:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise ValueError(f"generator function_forms anchor expected once, found {count}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    repo = args.repo.resolve()
    base_path = repo / "cemm" / "data" / "base.json"
    seed_path = repo / "cemm" / "training" / "en_form_schema_seed.json"
    legacy_generator_path = repo / "tools" / "generate_en_form_pack_v6.py"
    generator_path = repo / "tools" / "generate_en_form_pack_v7.py"
    source_generator_path = generator_path if generator_path.exists() else legacy_generator_path

    before = {
        str(path.relative_to(repo)): digest(path)
        for path in (base_path, seed_path, source_generator_path)
    }
    base = json.loads(base_path.read_text(encoding="utf-8"))
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    base_changed = int(add_operator_role(base, "role:object")) + int(add_operator_role(base, "role:target"))
    seed_result = migrate_seed(seed)
    generator_before = source_generator_path.read_text(encoding="utf-8")
    generator_after = migrate_generator_text(generator_before)

    if not args.check:
        write_json(base_path, base)
        write_json(seed_path, seed)
        generator_path.write_text(generator_after, encoding="utf-8")
        if legacy_generator_path.exists() and legacy_generator_path != generator_path:
            legacy_generator_path.unlink()
    result = {
        "base_changes": base_changed,
        **seed_result,
        "generator_changed": generator_after != generator_before,
        "before": before,
    }
    if not args.check:
        result["after"] = {
            str(path.relative_to(repo)): digest(path)
            for path in (base_path, seed_path, generator_path)
        }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
