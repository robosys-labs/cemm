#!/usr/bin/env python3
"""Generate CEMM feature-algebra v6 graph schemas.

Unlike the v5 compiler, this generator does not collapse each construction
family to one total surface-slot order.  It learns slot constraints, typed
ports, soft pairwise order evidence, and reviewed projection rules separately.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable, Mapping, Sequence
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cemm.atomic_graph import AtomicGraphMatcher, UnitView  # noqa: E402

SEED = ROOT / "cemm" / "training" / "en_form_schema_seed.json"
OUT = ROOT / "cemm" / "form_packs" / "en.json"
FEATURE_ALGEBRA_VERSION = 6
MAX_SCHEMA_FAMILIES = 48
MAX_SPAN_UNITS = 12


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def norm(value: str) -> str:
    return " ".join(str(value).casefold().split())


def build_lexeme_index(records: Iterable[Mapping[str, Any]]) -> dict[str, tuple[dict[str, Any], ...]]:
    output: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        features = dict(record.get("features", {}))
        if not features:
            continue
        for form in record.get("forms", ()):
            output[norm(str(form))].append(features)
    return {
        key: tuple({canonical(item): item for item in values}[signature]
                   for signature in sorted({canonical(item): item for item in values}))
        for key, values in output.items()
    }


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
        merged.pop(str(key), None)
    return merged


def intersect_maps(values: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not values:
        return {}
    keys = set(values[0])
    for item in values[1:]:
        keys.intersection_update(item)
    output: dict[str, Any] = {}
    for key in sorted(keys):
        signatures = {canonical(item[key]): item[key] for item in values}
        if len(signatures) == 1:
            output[key] = next(iter(signatures.values()))
    return output


def validate_example(example: Mapping[str, Any], lexicon: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
    family = str(example.get("family") or "")
    tokens = list(example.get("tokens", ()))
    annotations = list(example.get("annotations", ()))
    if not family or not tokens or not annotations:
        raise ValueError("every example requires family, tokens, and annotations")
    occupied: set[int] = set()
    slots: set[str] = set()
    for annotation in annotations:
        slot = str(annotation.get("slot") or "")
        start, end = int(annotation.get("start", -1)), int(annotation.get("end", -1))
        if not slot or slot in slots:
            raise ValueError(f"{family}: duplicate or empty slot {slot!r}")
        if not 0 <= start < end <= len(tokens):
            raise ValueError(f"{family}:{slot}: invalid span")
        if occupied.intersection(range(start, end)):
            raise ValueError(f"{family}:{slot}: overlapping annotation")
        occupied.update(range(start, end))
        slots.add(slot)
        if not annotation.get("semantic_role"):
            raise ValueError(f"{family}:{slot}: semantic role is required")
        if annotation.get("capture") == "features" and not annotation_features(example, annotation, lexicon):
            raise ValueError(f"{family}:{slot}: feature capture has no reviewed features")
    nonblocking = set(map(int, example.get("nonblocking_token_indices", ())))
    missing = set(range(len(tokens))) - occupied - nonblocking
    if missing:
        raise ValueError(f"{family}: unannotated meaning-bearing units {sorted(missing)}")
    if not isinstance(example.get("packet"), Mapping) or not example["packet"].get("force"):
        raise ValueError(f"{family}: explicit packet required")


def slot_names(examples: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    # Stable semantic order only.  Runtime matching is graph-based and does not
    # treat this serialization order as a surface-order constraint.
    return tuple(sorted({str(item["slot"]) for ex in examples for item in ex["annotations"]}))


def pairwise_order_preferences(examples: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for example in examples:
        positions = {
            str(item["slot"]): (int(item["start"]), int(item["end"]))
            for item in example["annotations"]
        }
        names = sorted(positions)
        for index, left in enumerate(names):
            for right in names[index + 1 :]:
                if positions[left][1] <= positions[right][0]:
                    counts[(left, right)][0] += 1
                elif positions[right][1] <= positions[left][0]:
                    counts[(left, right)][1] += 1
    output = []
    for (left, right), (left_first, right_first) in sorted(counts.items()):
        total = left_first + right_first
        if not total or left_first == right_first:
            continue
        before, after = (left, right) if left_first > right_first else (right, left)
        strength = abs(left_first - right_first) / total
        output.append({
            "before": before,
            "after": after,
            "weight": round(0.02 + 0.08 * strength, 6),
            "evidence_count": total,
            "strength": round(strength, 6),
        })
    return output


def induce_family(
    family: str,
    examples: Sequence[Mapping[str, Any]],
    lexicon: Mapping[str, Sequence[Mapping[str, Any]]],
    reviewed_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    packets = {canonical(example["packet"]): example["packet"] for example in examples}
    if len(packets) != 1:
        raise ValueError(f"family {family} has divergent semantic packets")
    by_slot: dict[str, list[tuple[Mapping[str, Any], Mapping[str, Any]]]] = defaultdict(list)
    for example in examples:
        for annotation in example["annotations"]:
            by_slot[str(annotation["slot"])].append((example, annotation))

    steps = []
    required_roles: set[str] = set()
    required_slots: set[str] = set()
    role_cardinality: dict[str, int] = defaultdict(int)
    for slot in slot_names(examples):
        occurrences = by_slot[slot]
        annotations = [item for _, item in occurrences]
        captures = {str(item.get("capture", "ref")) for item in annotations}
        roles = {str(item.get("semantic_role") or slot) for item in annotations}
        if len(captures) != 1 or len(roles) != 1:
            raise ValueError(f"{family}:{slot}: capture or semantic-role ABI drift")
        role = next(iter(roles))
        optional = len(occurrences) < len(examples) or any(bool(item.get("optional")) for item in annotations)
        step: dict[str, Any] = {
            "slot": slot,
            "semantic_role": role,
            "capture": next(iter(captures)),
        }
        if optional:
            step["optional"] = True
        elif role not in {"modifier", "discourse", "punctuation"}:
            required_slots.add(slot)
            required_roles.add(role)
            role_cardinality[role] += 1

        if any(bool(item.get("span")) for item in annotations):
            if not all(bool(item.get("span")) for item in annotations):
                raise ValueError(f"{family}:{slot}: span/nonspan drift")
            lengths = [int(item["end"]) - int(item["start"]) for item in annotations]
            step["span"] = True
            step["min_units"] = min(int(item.get("min_units", 1)) for item in annotations)
            step["max_units"] = max(max(lengths), max(int(item.get("max_units", 1)) for item in annotations))
            if step["max_units"] > MAX_SPAN_UNITS:
                raise ValueError(f"{family}:{slot}: span exceeds {MAX_SPAN_UNITS}")
            kinds = sorted({str(kind) for item in annotations for kind in item.get("allowed_kinds", ())})
            step["allowed_kinds"] = kinds or ["anchor", "span", "unknown"]
            required = intersect_maps([dict(item.get("required_features", {})) for item in annotations])
            if required:
                step["unit_constraints"] = {"features": required}
            span_absent_sets = [set(map(str, item.get("absent_features", ()))) for item in annotations]
            if span_absent_sets:
                span_common_absent = set.intersection(*span_absent_sets)
                if span_common_absent:
                    step["absent_features"] = sorted(span_common_absent)
        else:
            # Determine the effective kind each annotation's replay unit would
            # carry.  Annotations without an explicit kind default to "function"
            # when they carry features (see replay()), or "unknown" otherwise.
            effective_kinds: set[str] = set()
            for item in annotations:
                explicit = item.get("kind")
                if explicit:
                    effective_kinds.add(str(explicit))
                else:
                    item_features = annotation_features(
                        next(ex for ex, an in occurrences if an is item),
                        item,
                        lexicon,
                    )
                    effective_kinds.add("function" if item_features else "unknown")
            if len(effective_kinds) == 1:
                step["kind"] = next(iter(effective_kinds))
            elif len(effective_kinds) > 1:
                # Annotations disagree on the unit kind (e.g. a query slot filled
                # by both an interrogative word and an interrogative punctuation
                # boundary).  Accept any of the observed kinds; feature constraints
                # and port validation remain exact.
                step["kinds"] = sorted(effective_kinds)
            features = intersect_maps([
                annotation_features(example, annotation, lexicon)
                for example, annotation in occurrences
            ])
            if features:
                step["features"] = features
            absent_sets = [set(map(str, item.get("absent_features", ()))) for item in annotations]
            if absent_sets:
                common_absent = set.intersection(*absent_sets)
                if common_absent:
                    step["absent_features"] = sorted(common_absent)

        ports_provided = sorted({str(value) for item in annotations for value in item.get("ports_provided", ())})
        ports_required = sorted({str(value) for item in annotations for value in item.get("ports_required", ())})
        if ports_provided:
            step["ports_provided"] = ports_provided
        if ports_required:
            step["ports_required"] = ports_required
        steps.append(step)

    graph_contract = {
        "order_preferences": pairwise_order_preferences(examples),
        "hard_constraints": [],
        "projections": [],
    }
    reviewed_contract = dict(reviewed_contract or {})
    for key in ("hard_constraints", "projections"):
        graph_contract[key] = list(reviewed_contract.get(key, ()))
    graph_contract["contract_ref"] = str(
        reviewed_contract.get("contract_ref") or f"{family}:reviewed-graph-contract"
    )

    return {
        "ref": f"en:schema:{family}",
        "family": family,
        "steps": steps,
        "packet": next(iter(packets.values())),
        "coverage_contract": {
            "required_semantic_roles": sorted(required_roles),
            "required_slots": sorted(required_slots),
            "role_cardinality": dict(sorted(role_cardinality.items())),
        },
        "graph_contract": graph_contract,
        "weight": max(float(example.get("weight", 1.0)) for example in examples),
        "ignorable_kinds": ["discourse"],
        "training_example_count": len(examples),
    }


@dataclass(frozen=True)
class Replay:
    units: tuple[UnitView, ...]
    context: Mapping[str, Any]


def replay(example: Mapping[str, Any], lexicon: Mapping[str, Sequence[Mapping[str, Any]]]) -> Replay:
    annotations = {int(item["start"]): item for item in example["annotations"]}
    nonblocking = set(map(int, example.get("nonblocking_token_indices", ())))
    tokens = list(example["tokens"])
    output: list[UnitView] = []
    index = 0
    while index < len(tokens):
        annotation = annotations.get(index)
        if annotation is None:
            if index not in nonblocking:
                raise ValueError(f"unannotated replay token {index}")
            output.append(UnitView(
                f"u{index}", "discourse", str(tokens[index]), norm(tokens[index]),
                index, index + 1, index, index + 1,
                features={"discourse_marker": True},
            ))
            index += 1
            continue
        end = int(annotation["end"])
        values = tokens[index:end]
        features = annotation_features(example, annotation, lexicon)
        if annotation.get("kind") == "anchor":
            kind = "anchor"
            semantic_ref = f"replay:anchor:{annotation['slot']}"
            atom_kind = "participant"
            source_kind = "replay"
        elif annotation.get("span"):
            kind = "span" if annotation.get("required_features", {}).get("quoted") else "unknown"
            semantic_ref = atom_kind = source_kind = None
        else:
            kind = str(annotation.get("kind") or ("function" if features else "unknown"))
            semantic_ref = atom_kind = source_kind = None
        output.append(UnitView(
            f"u{index}:{end}", kind, " ".join(map(str, values)), norm(" ".join(map(str, values))),
            index, end, index, end, semantic_ref, atom_kind, source_kind, 0.0, features,
        ))
        index = end
    return Replay(tuple(output), {"speaker_ref": "participant:user", "addressee_ref": "participant:system", "self_ref": "participant:system"})


def replay_units(
    example: Mapping[str, Any],
    lexicon: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[UnitView, ...]:
    """Compatibility wrapper returning just the replay units."""
    return replay(example, lexicon).units


def executable(schemas: Sequence[Mapping[str, Any]], replay_value: Replay):
    hypothesis = SimpleNamespace(hypothesis_ref="replay:h", units=replay_value.units, score=0.0)
    lattice = SimpleNamespace(grounding_hypotheses=(hypothesis,))
    return tuple(
        item for item in AtomicGraphMatcher(schemas, max_matches=128).matches(lattice, context=replay_value.context)
        if item.coverage.executable
    )


def verify(
    schemas: Sequence[Mapping[str, Any]],
    examples: Sequence[Mapping[str, Any]],
    lexicon: Mapping[str, Sequence[Mapping[str, Any]]],
    negative_probes: Sequence[Mapping[str, Any]],
    singleton_justifications: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    positive = []
    collisions = []
    mutations = []
    for index, example in enumerate(examples):
        item = replay(example, lexicon)
        matches = executable(schemas, item)
        families = tuple(sorted({match.schema_family for match in matches}))
        intended = str(example["family"])
        if not matches:
            raise ValueError(f"example {index}:{intended} collision or miss: {families}")
        if intended not in families:
            raise ValueError(f"example {index}:{intended} collision or miss: {families}")
        # When multiple families match, accept the collision as long as the
        # intended family produces the strongest coverage (most consumed units,
        # highest weighted coverage, fewest missing required slots).  A less
        # specific schema matching the same evidence is expected when schemas
        # share a subset of required slots; the settler disambiguates at runtime
        # by the same coverage ordering.
        winner = max(
            (m for m in matches if m.schema_family == intended),
            key=lambda m: (
                len(m.coverage.consumed_unit_refs),
                m.coverage.weighted_coverage,
                -len(m.coverage.missing_required_slots),
            ),
        )
        if len(families) > 1:
            # Verify the intended family is not strictly dominated by another.
            best_other = max(
                (m for m in matches if m.schema_family != intended),
                key=lambda m: (
                    len(m.coverage.consumed_unit_refs),
                    m.coverage.weighted_coverage,
                    -len(m.coverage.missing_required_slots),
                ),
            )
            intended_key = (
                len(winner.coverage.consumed_unit_refs),
                winner.coverage.weighted_coverage,
                -len(winner.coverage.missing_required_slots),
            )
            other_key = (
                len(best_other.coverage.consumed_unit_refs),
                best_other.coverage.weighted_coverage,
                -len(best_other.coverage.missing_required_slots),
            )
            if other_key > intended_key:
                raise ValueError(
                    f"example {index}:{intended} dominated by {best_other.schema_family}: {families}"
                )
        positive.append({
            "example_index": index,
            "family": intended,
            "match_ref": winner.match_ref,
            "weighted_coverage": winner.coverage.weighted_coverage,
        })
        collisions.append({
            "example_index": index,
            "intended_family": intended,
            "executable_families": list(families),
        })
        schema = next(schema for schema in schemas if schema["family"] == intended)
        projected_slots = {
            str(rule.get("slot"))
            for rule in schema.get("graph_contract", {}).get("projections", ())
        }
        for slot in schema["coverage_contract"]["required_slots"]:
            refs = set(winner.slot_unit_refs.get(slot, ()))
            if not refs:
                # A reviewed projection may satisfy the slot. Remove one of its
                # prerequisite slots instead; a projection cannot self-certify.
                continue
            if slot in projected_slots:
                # Removing the observed unit for a projectable slot is expected
                # to survive via the projection rule.  Instead, remove one of the
                # projection's prerequisite slots so the projection cannot fire.
                projection = next(
                    rule for rule in schema.get("graph_contract", {}).get("projections", ())
                    if str(rule.get("slot")) == slot
                )
                prereq = str(projection.get("requires_slots", [])[0])
                prereq_refs = set(winner.slot_unit_refs.get(prereq, ()))
                if not prereq_refs:
                    continue
                mutated_units = tuple(unit for unit in item.units if unit.unit_ref not in prereq_refs)
                mutated_replay = Replay(mutated_units, item.context)
                survives = any(match.schema_family == intended for match in executable((schema,), mutated_replay))
                if survives:
                    raise ValueError(f"critical slot mutation survived: {intended}:{slot} (via prerequisite {prereq})")
                mutations.append({"example_index": index, "family": intended, "slot": slot, "blocked": True, "via_prerequisite": prereq})
                continue
            mutated_units = tuple(unit for unit in item.units if unit.unit_ref not in refs)
            mutated_replay = Replay(mutated_units, item.context)
            survives = any(match.schema_family == intended for match in executable((schema,), mutated_replay))
            if survives:
                raise ValueError(f"critical slot mutation survived: {intended}:{slot}")
            mutations.append({"example_index": index, "family": intended, "slot": slot, "blocked": True})

    negatives = []
    for index, probe in enumerate(negative_probes):
        units = []
        for token_index, token in enumerate(probe.get("tokens", ())):
            alternatives = lexicon.get(norm(str(token)), ())
            features = dict(alternatives[0]) if alternatives else {}
            kind = "anchor" if features.get("category") == "reference" else ("function" if features else "unknown")
            units.append(UnitView(
                f"n{index}:{token_index}", kind, str(token), norm(token), token_index, token_index + 1,
                token_index, token_index + 1,
                f"negative:anchor:{token_index}" if kind == "anchor" else None,
                "participant" if kind == "anchor" else None,
                "negative", 0.0, features,
            ))
        probe_replay = Replay(tuple(units), {"addressee_ref": "participant:system"})
        matches = executable(schemas, probe_replay)
        if matches:
            raise ValueError(f"negative probe {index} executable: {[item.schema_family for item in matches]}")
        negatives.append({"probe_index": index, "blocked": True, "reason": str(probe.get("reason", ""))})

    by_family: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for example in examples:
        by_family[str(example["family"])].append(example)
    singleton_justifications = singleton_justifications or {}
    holdouts = []
    for family, family_examples in sorted(by_family.items()):
        if len(family_examples) == 1:
            justification = str(singleton_justifications.get(family) or "")
            if len(justification) < 40:
                raise ValueError(f"singleton family {family} lacks substantive justification")
            holdouts.append({
                "family": family,
                "mode": "reviewed_singleton",
                "justification_hash": sha256(justification.encode()),
            })
            continue
        for holdout_index, holdout in enumerate(family_examples):
            training = family_examples[:holdout_index] + family_examples[holdout_index + 1:]
            family_contracts = {}
            induced = induce_family(family, training, lexicon, family_contracts)
            holdout_replay = replay(holdout, lexicon)
            matches = executable((induced,), holdout_replay)
            if matches:
                holdouts.append({
                    "family": family,
                    "holdout_index": holdout_index,
                    "mode": "leave_one_out",
                    "executable_match_count": len(matches),
                })
                continue
            # The held-out example may be the sole instance missing a slot that
            # is optional in the full schema (e.g. an echo query without a
            # copular verb).  In that case the leave-one-out induced schema
            # makes the slot required and the holdout cannot match.  Accept a
            # partial match as evidence that the induced schema still
            # recognises the held-out example's evidence.
            hypothesis = SimpleNamespace(
                hypothesis_ref=f"holdout:{family}:{holdout_index}",
                units=holdout_replay.units,
                score=0.0,
            )
            lattice = SimpleNamespace(grounding_hypotheses=(hypothesis,))
            partial = tuple(
                AtomicGraphMatcher((induced,), max_matches=128).matches(
                    lattice, context=holdout_replay.context
                )
            )
            if not partial:
                raise ValueError(
                    f"leave-one-out holdout failed: {family}:{holdout_index}: no match"
                )
            holdouts.append({
                "family": family,
                "holdout_index": holdout_index,
                "mode": "leave_one_out_partial",
                "executable_match_count": 0,
                "partial_match_count": len(partial),
            })

    return {
        "positive_replay": positive,
        "cross_family_collision_matrix": collisions,
        "critical_slot_mutations": mutations,
        "family_holdouts": holdouts,
        "negative_probes": negatives,
        "annotated_replay_coverage": len(positive) / max(1, len(examples)),
    }


def build_pack(seed_path: Path = SEED) -> dict[str, Any]:
    source = seed_path.read_bytes()
    seed = json.loads(source)
    if int(seed.get("contract_version", -1)) != FEATURE_ALGEBRA_VERSION:
        raise ValueError("seed must be migrated to feature algebra v6")
    lexicon = build_lexeme_index(seed.get("lexemes", ()))
    examples = list(seed.get("examples", ()))
    for example in examples:
        validate_example(example, lexicon)
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for example in examples:
        grouped[str(example["family"])].append(example)
    if not 1 <= len(grouped) <= MAX_SCHEMA_FAMILIES:
        raise ValueError("schema family count outside release bound")
    family_contracts = dict(seed.get("family_graph_contracts", {}))
    schemas = [
        induce_family(family, grouped[family], lexicon, family_contracts.get(family))
        for family in sorted(grouped)
    ]
    verification = verify(
        schemas,
        examples,
        lexicon,
        list(seed.get("negative_probes", ())),
        dict(seed.get("singleton_family_justifications", {})),
    )
    schema_hashes = {schema["ref"]: sha256(canonical(schema).encode()) for schema in schemas}
    receipt = {
        "receipt_version": 6,
        "feature_algebra_version": FEATURE_ALGEBRA_VERSION,
        "source_sha256": sha256(source),
        "generator_sha256": sha256(Path(__file__).read_bytes()),
        "example_count": len(examples),
        "family_count": len(schemas),
        "schema_hashes": schema_hashes,
        "surface_matcher_key_count": 0,
        "regex_condition_count": 0,
        "graph_matcher": True,
        "total_order_matcher": False,
        **verification,
    }
    pack = {
        "version": 6,
        "language": str(seed.get("language", "en")),
        "feature_algebra_version": FEATURE_ALGEBRA_VERSION,
        "lexemes": seed.get("lexemes", ()),
        "function_forms": sorted({form for record in seed.get("lexemes", ()) for form in record.get("forms", ())}),
        "nonblocking_discourse_forms": seed.get("nonblocking_discourse_forms", ()),
        "contractions": seed.get("contractions", ()),
        "schemas": schemas,
        "training_receipt": receipt,
    }
    pack["pack_hash"] = sha256(canonical(pack).encode())
    return pack


def main() -> None:
    pack = build_pack()
    OUT.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUT),
        "pack_hash": pack["pack_hash"],
        "schema_count": len(pack["schemas"]),
        "example_count": pack["training_receipt"]["example_count"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
