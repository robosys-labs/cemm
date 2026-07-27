#!/usr/bin/env python3
"""Deterministically induce and verify the English atomic form pack.

This is a release compiler, not a fixture writer.  Every receipt is computed by
replaying the induced schemas through the same matcher used at runtime.  Positive
replay, cross-family collision, leave-one-out holdout, critical-slot mutation,
and negative probes must all pass before the pack is written.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cemm.form_algebra import AtomicSchemaMatcher, SchemaValidationError  # noqa: E402
from cemm.model import canonical, stable  # noqa: E402

SEED = ROOT / "cemm" / "training" / "en_form_schema_seed.json"
OUT = ROOT / "cemm" / "form_packs" / "en.json"
FEATURE_ALGEBRA_VERSION = 5
MAX_SCHEMA_FAMILIES = 32
MAX_SPAN_UNITS = 12


def norm(value: str) -> str:
    return " ".join(str(value).casefold().split())


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def build_lexeme_index(records: Iterable[Mapping[str, Any]]) -> dict[str, tuple[dict[str, Any], ...]]:
    output: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        features = dict(record.get("features", {}))
        if not features:
            continue
        for form in record.get("forms", ()):
            output[norm(str(form))].append(features)
    return {
        key: tuple({canonical(item): item for item in values}[item]
                   for item in sorted({canonical(item): item for item in values}))
        for key, values in output.items()
    }


def intersect_feature_maps(maps: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not maps:
        return {}
    common_keys = set(maps[0])
    for item in maps[1:]:
        common_keys.intersection_update(item)
    output: dict[str, Any] = {}
    for key in sorted(common_keys):
        alternatives = []
        for item in maps:
            raw = item[key]
            values = raw if isinstance(raw, list) else [raw]
            alternatives.append({canonical(value): value for value in values})
        shared = set(alternatives[0])
        for item in alternatives[1:]:
            shared.intersection_update(item)
        if shared:
            values = [alternatives[0][signature] for signature in sorted(shared)]
            output[key] = values[0] if len(values) == 1 else {"any_of": values}
    return output


def annotation_features(
    example: Mapping[str, Any],
    annotation: Mapping[str, Any],
    lexicon: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    maps: list[Mapping[str, Any]] = []
    for token in list(example["tokens"])[int(annotation["start"]): int(annotation["end"])]:
        maps.extend(lexicon.get(norm(str(token)), ()))
    merged: dict[str, Any] = {}
    for key in sorted({key for item in maps for key in item}):
        values = {canonical(item[key]): item[key] for item in maps if key in item}
        if len(values) == 1:
            merged[key] = next(iter(values.values()))
    keep = annotation.get("keep_features")
    if keep:
        merged = {key: merged[key] for key in keep if key in merged}
    merged.update(dict(annotation.get("required_features", {})))
    for key in annotation.get("drop_features", ()):
        merged.pop(key, None)
    return merged


def validate_example(example: Mapping[str, Any], lexicon: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
    family = str(example.get("family") or "")
    tokens = list(example.get("tokens", ()))
    annotations = list(example.get("annotations", ()))
    if not family or not tokens or not annotations:
        raise ValueError("every training example requires family, tokens, and annotations")
    occupied: set[int] = set()
    slots: set[str] = set()
    for annotation in annotations:
        slot = str(annotation.get("slot") or "")
        start, end = int(annotation.get("start", -1)), int(annotation.get("end", -1))
        if not slot or slot in slots:
            raise ValueError(f"{family}: duplicate/empty slot {slot!r}")
        if not (0 <= start < end <= len(tokens)):
            raise ValueError(f"{family}:{slot}: invalid span {start}:{end}")
        overlap = occupied.intersection(range(start, end))
        if overlap:
            raise ValueError(f"{family}:{slot}: overlapping indices {sorted(overlap)}")
        occupied.update(range(start, end))
        slots.add(slot)
        if not annotation.get("semantic_role"):
            raise ValueError(f"{family}:{slot}: semantic_role is required")
        if annotation.get("span"):
            maximum = int(annotation.get("max_units", MAX_SPAN_UNITS))
            if not 1 <= end - start <= maximum <= MAX_SPAN_UNITS:
                raise ValueError(f"{family}:{slot}: invalid bounded span")
        elif annotation.get("capture") == "features" and not annotation_features(example, annotation, lexicon):
            raise ValueError(f"{family}:{slot}: feature capture lacks reviewed features")
    nonblocking = set(map(int, example.get("nonblocking_token_indices", ())))
    missing = set(range(len(tokens))) - occupied - nonblocking
    if missing:
        raise ValueError(f"{family}: unannotated meaning-bearing token indices {sorted(missing)}")
    packet = example.get("packet")
    if not isinstance(packet, Mapping) or not packet.get("force"):
        raise ValueError(f"{family}: explicit semantic packet is required")


def slot_order(examples: Sequence[Mapping[str, Any]]) -> list[str]:
    nodes: set[str] = set()
    edges: dict[str, set[str]] = defaultdict(set)
    indegree: dict[str, int] = defaultdict(int)
    average: dict[str, list[float]] = defaultdict(list)
    for example in examples:
        ordered = sorted(example["annotations"], key=lambda x: (int(x["start"]), int(x["end"]), str(x["slot"])))
        slots = [str(item["slot"]) for item in ordered]
        nodes.update(slots)
        for item in ordered:
            average[str(item["slot"])].append(float(item["start"]))
        for left, right in zip(slots, slots[1:]):
            if right not in edges[left]:
                edges[left].add(right)
                indegree[right] += 1
                indegree.setdefault(left, indegree.get(left, 0))
    ready = sorted(
        (node for node in nodes if indegree.get(node, 0) == 0),
        key=lambda node: (sum(average[node]) / len(average[node]), node),
    )
    result: list[str] = []
    while ready:
        node = ready.pop(0)
        result.append(node)
        for target in sorted(edges.get(node, ())):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
                ready.sort(key=lambda item: (sum(average[item]) / len(average[item]), item))
    if len(result) != len(nodes):
        raise ValueError(f"cyclic slot order: {sorted(nodes)}")
    return result


def induce_family(
    family: str,
    examples: Sequence[Mapping[str, Any]],
    lexicon: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    packet_signatures = {canonical(example["packet"]) for example in examples}
    if len(packet_signatures) != 1:
        raise ValueError(f"family {family} has divergent semantic packets")
    by_slot: dict[str, list[tuple[Mapping[str, Any], Mapping[str, Any]]]] = defaultdict(list)
    for example in examples:
        for annotation in example["annotations"]:
            by_slot[str(annotation["slot"])].append((example, annotation))
    steps: list[dict[str, Any]] = []
    required_roles: set[str] = set()
    for slot in slot_order(examples):
        occurrences = by_slot[slot]
        annotations = [annotation for _, annotation in occurrences]
        capture_values = {str(item.get("capture", "ref")) for item in annotations}
        role_values = {str(item.get("semantic_role") or slot) for item in annotations}
        if len(capture_values) != 1 or len(role_values) != 1:
            raise ValueError(f"{family}:{slot}: capture/role ABI drift")
        role = next(iter(role_values))
        step: dict[str, Any] = {
            "slot": slot,
            "semantic_role": role,
            "capture": next(iter(capture_values)),
        }
        optional = len(occurrences) < len(examples) or any(bool(item.get("optional")) for item in annotations)
        if optional:
            step["optional"] = True
        elif role not in {"modifier", "discourse", "punctuation"}:
            required_roles.add(role)
        if any(bool(item.get("span")) for item in annotations):
            if not all(bool(item.get("span")) for item in annotations):
                raise ValueError(f"{family}:{slot}: span/nonspan drift")
            step["span"] = True
            lengths = [int(item["end"]) - int(item["start"]) for _, item in occurrences]
            step["min_units"] = min(int(item.get("min_units", 1)) for item in annotations)
            step["max_units"] = max(max(lengths), max(int(item.get("max_units", 1)) for item in annotations))
            if step["max_units"] > MAX_SPAN_UNITS:
                raise ValueError(f"{family}:{slot}: span exceeds bound")
            allowed = sorted({kind for item in annotations for kind in item.get("allowed_kinds", ())})
            if not allowed:
                allowed = ["anchor", "span", "unknown"]
            step["allowed_kinds"] = allowed
            for flag in ("allow_anchors", "allow_function", "allow_punctuation"):
                if any(bool(item.get(flag)) for item in annotations):
                    step[flag] = True
            required_feature_maps = [dict(item.get("required_features", {})) for item in annotations]
            common_required = intersect_feature_maps(required_feature_maps)
            if common_required:
                step["unit_constraints"] = {"features": common_required}
        else:
            kinds = {str(item.get("kind")) for item in annotations if item.get("kind")}
            if len(kinds) == 1:
                step["kind"] = next(iter(kinds))
            feature_maps = [annotation_features(example, annotation, lexicon) for example, annotation in occurrences]
            common = intersect_feature_maps(feature_maps)
            if common:
                step["features"] = common
            absent_sets = [set(map(str, item.get("absent_features", ()))) for item in annotations]
            if absent_sets:
                common_absent = set.intersection(*absent_sets)
                if common_absent:
                    step["absent_features"] = sorted(common_absent)
        steps.append(step)
    schema = {
        "ref": f"en:schema:{family}",
        "family": family,
        "steps": steps,
        "packet": json.loads(next(iter(packet_signatures))),
        "coverage_contract": {"required_semantic_roles": sorted(required_roles)},
        "weight": max(float(example.get("weight", 1.0)) for example in examples),
        "ignorable_kinds": ["discourse", "punctuation"],
        "training_example_count": len(examples),
    }
    AtomicSchemaMatcher.validate_schema(schema)
    return schema


@dataclass(frozen=True)
class ReplayUnit:
    unit_ref: str
    kind: str
    surface: str
    normalized: str
    token_start: int
    token_end: int
    char_start: int
    char_end: int
    semantic_ref: str | None = None
    atom_kind: str | None = None
    source_kind: str | None = None
    score: float = 0.0
    features: Mapping[str, Any] = None

    def as_dict(self):
        return {
            **self.__dict__,
            "features": dict(self.features or {}),
        }


def replay_units(
    example: Mapping[str, Any],
    lexicon: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[ReplayUnit, ...]:
    tokens = list(example["tokens"])
    annotations_by_start = {int(item["start"]): item for item in example["annotations"]}
    nonblocking = set(map(int, example.get("nonblocking_token_indices", ())))
    output: list[ReplayUnit] = []
    index = 0
    while index < len(tokens):
        annotation = annotations_by_start.get(index)
        if annotation is None:
            if index not in nonblocking:
                raise ValueError(f"replay encountered unannotated token {index}")
            features = {"discourse_marker": True}
            output.append(ReplayUnit(f"u{index}", "discourse", str(tokens[index]), norm(tokens[index]), index, index + 1, index, index + 1, features=features))
            index += 1
            continue
        end = int(annotation["end"])
        values = tokens[index:end]
        required = dict(annotation.get("required_features", {}))
        if annotation.get("span") and required.get("quoted"):
            output.append(ReplayUnit(
                f"u{index}:{end}", "span", " ".join(map(str, values)), norm(" ".join(map(str, values))),
                index, end, index, end, source_kind="quoted_span", features=required,
            ))
        elif annotation.get("kind") == "anchor":
            features = annotation_features(example, annotation, lexicon)
            output.append(ReplayUnit(
                f"u{index}:{end}", "anchor", " ".join(map(str, values)), norm(" ".join(map(str, values))),
                index, end, index, end, semantic_ref=f"replay:anchor:{annotation['slot']}", atom_kind="participant", source_kind="replay", features=features,
            ))
        elif annotation.get("span"):
            for offset, token in enumerate(values, start=index):
                alternatives = lexicon.get(norm(str(token)), ())
                features = dict(alternatives[0]) if alternatives else {}
                features.update(required)
                kind = "function" if alternatives else "unknown"
                output.append(ReplayUnit(f"u{offset}", kind, str(token), norm(token), offset, offset + 1, offset, offset + 1, features=features))
        else:
            raw_maps = [
                item
                for token in values
                for item in lexicon.get(norm(str(token)), ())
            ]
            features = {}
            for item in raw_maps:
                features.update(dict(item))
            features.update(required)
            kind = str(annotation.get("kind") or "function")
            output.append(ReplayUnit(f"u{index}:{end}", kind, " ".join(map(str, values)), norm(" ".join(map(str, values))), index, end, index, end, features=features))
        index = end
    return tuple(output)


def executable_matches(schemas: Sequence[Mapping[str, Any]], units: Sequence[ReplayUnit]):
    hypothesis = SimpleNamespace(hypothesis_ref=stable("replay-hypothesis", [unit.as_dict() for unit in units]), units=tuple(units), score=0.0)
    lattice = SimpleNamespace(grounding_hypotheses=(hypothesis,))
    return tuple(item for item in AtomicSchemaMatcher(schemas, max_matches=128).matches(lattice) if item.coverage.executable)


def verify_schemas(
    schemas: Sequence[Mapping[str, Any]],
    examples: Sequence[Mapping[str, Any]],
    lexicon: Mapping[str, Sequence[Mapping[str, Any]]],
    singleton_justifications: Mapping[str, str],
    negative_probes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    replay_receipts = []
    collision_rows = []
    mutation_receipts = []
    for index, example in enumerate(examples):
        units = replay_units(example, lexicon)
        matches = executable_matches(schemas, units)
        families = tuple(sorted({item.schema_family for item in matches}))
        intended = str(example["family"])
        if families != (intended,) or len(matches) != 1:
            raise ValueError(
                f"example {index}:{intended} collision/miss/nonunique: "
                f"families={families}, matches={len(matches)}"
            )
        match = matches[0]
        replay_receipts.append({
            "example_index": index,
            "family": intended,
            "unit_signature": sha256_bytes(canonical([unit.as_dict() for unit in units]).encode()),
            "match_ref": match.match_ref,
            "coverage_ref": match.coverage.coverage_ref,
            "weighted_coverage": match.coverage.weighted_coverage,
        })
        collision_rows.append({
            "example_index": index,
            "intended_family": intended,
            "executable_families": list(families),
            "executable_match_count": len(matches),
        })
        # Each nonoptional nonmodifier slot is mutation tested by removing all of
        # its replay units; the intended schema must no longer be executable.
        schema = next(item for item in schemas if item["family"] == intended)
        for step in schema["steps"]:
            if step.get("optional") or step.get("semantic_role") in {"modifier", "discourse", "punctuation"}:
                continue
            role = str(step["semantic_role"])
            role_units = set(match.coverage.semantic_role_unit_refs.get(role, ()))
            mutated = tuple(unit for unit in units if unit.unit_ref not in role_units)
            survives = any(item.schema_family == intended for item in executable_matches((schema,), mutated))
            if survives:
                raise ValueError(f"mutation failed to block {intended}:{role}")
            mutation_receipts.append({"example_index": index, "family": intended, "semantic_role": role, "blocked": True})

    by_family: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for example in examples:
        by_family[str(example["family"])].append(example)
    holdout_receipts = []
    for family, family_examples in sorted(by_family.items()):
        if len(family_examples) == 1:
            justification = str(singleton_justifications.get(family) or "")
            if len(justification) < 40:
                raise ValueError(f"singleton family {family} lacks substantive justification")
            holdout_receipts.append({"family": family, "mode": "reviewed_singleton", "justification_hash": sha256_bytes(justification.encode())})
            continue
        for holdout_index, holdout in enumerate(family_examples):
            training = family_examples[:holdout_index] + family_examples[holdout_index + 1 :]
            induced = induce_family(family, training, lexicon)
            matches = executable_matches((induced,), replay_units(holdout, lexicon))
            if len(matches) != 1:
                raise ValueError(
                    f"leave-one-out holdout failed/nonunique: "
                    f"{family}:{holdout_index}:matches={len(matches)}"
                )
            holdout_receipts.append({
                "family": family,
                "holdout_index": holdout_index,
                "mode": "leave_one_out",
                "coverage_ref": matches[0].coverage.coverage_ref,
                "executable_match_count": len(matches),
            })

    negative_receipts = []
    for index, probe in enumerate(negative_probes):
        tokens = list(probe.get("tokens", ()))
        units = []
        for token_index, token in enumerate(tokens):
            alternatives = lexicon.get(norm(str(token)), ())
            features = dict(alternatives[0]) if alternatives else {}
            if features.get("category") == "reference":
                kind = "anchor"
                semantic_ref = f"negative:anchor:{token_index}"
                atom_kind = "participant"
            else:
                kind = "function" if alternatives else "unknown"
                semantic_ref = atom_kind = None
            units.append(ReplayUnit(f"n{index}:{token_index}", kind, str(token), norm(token), token_index, token_index + 1, token_index, token_index + 1, semantic_ref, atom_kind, "negative", features=features))
        matches = executable_matches(schemas, units)
        if matches:
            raise ValueError(f"negative probe {index} unexpectedly executable: {[item.schema_family for item in matches]}")
        negative_receipts.append({"probe_index": index, "reason": str(probe.get("reason", "")), "blocked": True})

    return {
        "positive_replay": replay_receipts,
        "cross_family_collision_matrix": collision_rows,
        "critical_slot_mutations": mutation_receipts,
        "family_holdouts": holdout_receipts,
        "negative_probes": negative_receipts,
        "annotated_replay_coverage": len(replay_receipts) / max(1, len(examples)),
    }


def count_forbidden_match_keys(value: Any) -> int:
    forbidden = {"literal", "surface", "regex", "pattern_text", "tokens", "phrase"}
    if isinstance(value, Mapping):
        return len(forbidden.intersection(value)) + sum(count_forbidden_match_keys(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(count_forbidden_match_keys(item) for item in value)
    return 0


def build_pack(seed_path: Path = SEED) -> dict[str, Any]:
    source_bytes = seed_path.read_bytes()
    seed = json.loads(source_bytes)
    if int(seed.get("contract_version", -1)) != FEATURE_ALGEBRA_VERSION:
        raise ValueError("seed contract version does not match feature algebra")
    lexicon = build_lexeme_index(seed.get("lexemes", ()))
    examples = list(seed.get("examples", ()))
    for example in examples:
        validate_example(example, lexicon)
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for example in examples:
        grouped[str(example["family"])].append(example)
    if not 1 <= len(grouped) <= MAX_SCHEMA_FAMILIES:
        raise ValueError("schema family count outside release bound")
    schemas = [induce_family(family, grouped[family], lexicon) for family in sorted(grouped)]
    verification = verify_schemas(
        schemas,
        examples,
        lexicon,
        dict(seed.get("singleton_family_justifications", {})),
        list(seed.get("negative_probes", ())),
    )
    forbidden_count = sum(count_forbidden_match_keys(schema.get("steps", ())) for schema in schemas)
    if forbidden_count:
        raise ValueError("surface matcher keys survived induction")
    schema_hashes = {
        schema["ref"]: sha256_bytes(canonical(schema).encode()) for schema in schemas
    }
    receipt = {
        "receipt_version": 5,
        "feature_algebra_version": FEATURE_ALGEBRA_VERSION,
        "source_sha256": sha256_bytes(source_bytes),
        "generator_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "example_count": len(examples),
        "family_count": len(schemas),
        "schema_hashes": schema_hashes,
        "surface_matcher_key_count": forbidden_count,
        "regex_condition_count": 0,
        "anti_unified_family_count": sum(1 for values in grouped.values() if len(values) > 1),
        "required_span_providers": sorted(set(map(str, seed.get("required_span_providers", ())))),
        **verification,
    }
    pack = {
        "version": 5,
        "language": str(seed.get("language", "en")),
        "feature_algebra_version": FEATURE_ALGEBRA_VERSION,
        "lexemes": seed.get("lexemes", ()),
        "function_forms": sorted({form for record in seed.get("lexemes", ()) for form in record.get("forms", ())}),
        "nonblocking_discourse_forms": seed.get("nonblocking_discourse_forms", ()),
        "contractions": seed.get("contractions", ()),
        "schemas": schemas,
        "training_receipt": receipt,
    }
    pack["pack_hash"] = sha256_bytes(canonical(pack).encode())
    return pack


def main() -> None:
    pack = build_pack()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUT),
        "pack_hash": pack["pack_hash"],
        "schema_count": len(pack["schemas"]),
        "example_count": pack["training_receipt"]["example_count"],
        "replay_coverage": pack["training_receipt"]["annotated_replay_coverage"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
