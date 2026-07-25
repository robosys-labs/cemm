#!/usr/bin/env python3
"""Compile reviewed language evidence into open structured supervision."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any
from cemm.curriculum import CurriculumManifest, SemanticEpisode

MAX_ANCHORS = 8
MAX_APPS = 3
MAX_RULE_IF = 3
MAX_RULE_THEN = 3
BASE_SOURCE_CLASSES = (
    ["NONE", "FRAME_SPEAKER", "FRAME_ADDRESSEE"]
    + [f"A{i}" for i in range(MAX_ANCHORS)]
    + [f"DIM_OF_A{i}" for i in range(MAX_ANCHORS)]
    + ["Q0", "Q1", "Q2", "NEW_ENTITY_0", "NEW_ENTITY_1", "NEW_EVENT_0", "NEW_EVENT_1"]
)
RULE_SOURCES = ["NONE"] + [f"A{i}" for i in range(MAX_ANCHORS)] + ["V0", "V1", "V2", "E0", "E1"]


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def norm(value):
    return unicodedata.normalize("NFKC", str(value))


def pack_hash(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def load_knowledge(paths):
    kinds = {}
    value_dimensions = {}
    spec_dimensions = {}
    spec_values = {}
    for path in paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for atom in data.get("atoms", []):
            kinds[atom["ref"]] = atom["kind"]
        for fact in data.get("facts", []):
            args = fact.get("args", {})
            if fact.get("operator") != "op:relation":
                continue
            relation = args.get("role:relation")
            subject = args.get("role:subject")
            obj = args.get("role:object")
            if relation == "rel:value_of_dimension":
                value_dimensions.setdefault(subject, set()).add(obj)
            elif relation == "rel:state_dimension":
                spec_dimensions.setdefault(subject, set()).add(obj)
            elif relation == "rel:state_value":
                spec_values.setdefault(subject, set()).add(obj)
    for spec in set(spec_dimensions) & set(spec_values):
        for value in spec_values[spec]:
            value_dimensions.setdefault(value, set()).update(spec_dimensions[spec])
    kinds.setdefault("participant:user", "participant")
    kinds.setdefault("participant:system", "participant")
    return kinds, value_dimensions


def replace_mentions(surface: str, mentions: list[dict[str, Any]], kind_map: dict[str, str]):
    refs = []
    for mention in mentions:
        if mention["ref"] not in refs:
            refs.append(mention["ref"])
    ref_to_placeholder = {ref: f"A{i}" for i, ref in enumerate(refs)}
    spans = []
    for mention in mentions:
        phrase = mention["surface"]
        for hit in re.finditer(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", surface, flags=re.I | re.UNICODE):
            spans.append((hit.start(), hit.end(), len(phrase), mention["ref"]))
    chosen = []
    for span in sorted(spans, key=lambda item: (item[0], -item[2])):
        if not any(span[0] < other[1] and span[1] > other[0] for other in chosen):
            chosen.append(span)
    output = []
    position = 0
    for start, end, _, ref in sorted(chosen):
        output.append(surface[position:start])
        kind = next(
            (item.get("kind") for item in mentions if item["ref"] == ref and item.get("kind")),
            None,
        ) or kind_map.get(ref, "atom")
        output.append(f"@{ref_to_placeholder[ref]}<{kind}>")
        position = end
    output.append(surface[position:])
    return "".join(output), ref_to_placeholder


def source_for(value, ref_to_placeholder, new_map, constant_map=None):
    if isinstance(value, str) and value in ref_to_placeholder:
        return ref_to_placeholder[value]
    if value == "participant:user":
        return "FRAME_SPEAKER"
    if value == "participant:system":
        return "FRAME_ADDRESSEE"
    if isinstance(value, str) and value.startswith("?q") and value[2:].isdigit():
        return f"Q{value[2:]}"
    if isinstance(value, str) and value in new_map:
        return new_map[value]
    if isinstance(value, str) and constant_map and value in constant_map:
        return constant_map[value]
    if isinstance(value, dict) and "literal" in value:
        return "NONE"
    return None


def structured_target(semantic, ref_to_placeholder, value_dimensions, kind_map, constant_map=None):
    new_map = {}
    entity_count = event_count = 0
    for item in semantic.get("new", []):
        if item["kind"] == "entity":
            new_map[item["token"]] = f"NEW_ENTITY_{entity_count}"
            entity_count += 1
        elif item["kind"] == "event":
            new_map[item["token"]] = f"NEW_EVENT_{event_count}"
            event_count += 1
    if "force" not in semantic:
        raise ValueError("interpretation supervision requires explicit discourse force")
    force = str(semantic["force"])
    if semantic.get("describe"):
        source = source_for(semantic["describe"], ref_to_placeholder, new_map, constant_map)
        if not source:
            raise ValueError("describe target must be grounded")
        return {"force": force, "intent": "describe", "describe_source": source, "apps": []}

    raw_query = semantic.get("query")
    if raw_query and raw_query.get("operator"):
        raise ValueError("query supervision requires QueryStructure.restrictions")
    applications = raw_query.get("restrictions", []) if raw_query else semantic.get("apps", [])
    output = []
    for application in applications[:MAX_APPS]:
        bindings = {}
        args = application.get("args", {})
        if application.get("operator") == "op:type":
            instance = args.get("role:instance")
            class_ref = args.get("role:class")
            if kind_map.get(instance) == "concept" and kind_map.get(class_ref) == "concept":
                raise ValueError(
                    "generic concept predication must use op:relation/rel:subtype_of, not op:type(concept, concept)"
                )
        for role, value in args.items():
            source = source_for(value, ref_to_placeholder, new_map, constant_map)
            if source:
                bindings[role] = source
        if application["operator"] == "op:state" and "role:dimension" not in bindings:
            if "role:dimension" not in args:
                raise ValueError("state supervision requires an explicit semantic dimension")
            value_ref = args.get("role:value")
            value_source = source_for(value_ref, ref_to_placeholder, new_map, constant_map)
            dimension_ref = args.get("role:dimension")
            known_dimensions = value_dimensions.get(value_ref, set()) if isinstance(value_ref, str) else set()
            if value_source and value_source.startswith("A") and known_dimensions == {dimension_ref}:
                bindings["role:dimension"] = "DIM_OF_" + value_source
            else:
                raise ValueError(
                    f"unexpressed state dimension requires one reviewed value→dimension relation: {dimension_ref} <- {value_ref}"
                )
        output.append({"operator": application["operator"], "bindings": bindings})
    projection = []
    for value in (raw_query or {}).get("projection", []):
        source = source_for(value, ref_to_placeholder, new_map, constant_map)
        if source:
            projection.append(source)
    legacy_intent = "query" if force == "query" else "describe" if force == "description_request" else "assert"
    return {
        "force": force,
        "intent": legacy_intent,
        "describe_source": "NONE",
        "apps": output,
        "projection": projection,
    }


def rule_value(value, ref_to_placeholder, variable_map, constant_map=None):
    if isinstance(value, str) and value in ref_to_placeholder:
        return ref_to_placeholder[value]
    if isinstance(value, str) and value in variable_map:
        return variable_map[value]
    if isinstance(value, str) and constant_map and value in constant_map:
        return constant_map[value]
    return None


def rule_target(rule, ref_to_placeholder, constant_map=None):
    variables = []
    existentials = []
    for side in (rule.get("if", []), rule.get("then", [])):
        for application in side:
            for value in application.get("args", {}).values():
                if isinstance(value, str) and value.startswith("?") and value not in variables:
                    variables.append(value)
                if isinstance(value, str) and value.startswith("!") and value not in existentials:
                    existentials.append(value)
    variable_map = {value: f"V{i}" for i, value in enumerate(variables[:3])}
    variable_map.update({value: f"E{i}" for i, value in enumerate(existentials[:2])})

    def compile_side(items, maximum):
        output = []
        for application in items[:maximum]:
            bindings = {}
            for role, value in application.get("args", {}).items():
                source = rule_value(value, ref_to_placeholder, variable_map, constant_map)
                if not source:
                    raise ValueError(f"rule constant must be mention-grounded or variable: {value}")
                bindings[role] = source
            output.append({"operator": application["operator"], "bindings": bindings})
        return output

    return {
        "rule_kind": rule.get("rule_kind", "definition"),
        "if": compile_side(rule.get("if", []), MAX_RULE_IF),
        "then": compile_side(rule.get("then", []), MAX_RULE_THEN),
    }


def realization_refs(example):
    refs = []

    def add(value):
        if isinstance(value, str) and ":" in value and value not in refs:
            refs.append(value)

    if "plan" in example:
        plan = example["plan"]
        if plan.get("value"):
            add(plan["value"])
        for fact in plan.get("facts", []):
            for value in fact.get("args", {}).values():
                add(value)
    else:
        for value in example["fact"].get("args", {}).values():
            add(value)
    refs.sort()
    return {ref: f"@A{i}" for i, ref in enumerate(refs)}


def replace_with_map(surface, mentions, refs):
    spans = []
    for mention in mentions:
        if mention["ref"] not in refs:
            continue
        for hit in re.finditer(r"(?<!\w)" + re.escape(mention["surface"]) + r"(?!\w)", surface, flags=re.I | re.UNICODE):
            spans.append((hit.start(), hit.end(), len(mention["surface"]), refs[mention["ref"]]))
    chosen = []
    for span in sorted(spans, key=lambda item: (item[0], -item[2])):
        if not any(span[0] < other[1] and span[1] > other[0] for other in chosen):
            chosen.append(span)
    output = []
    position = 0
    for start, end, _, placeholder in sorted(chosen):
        output += [surface[position:start], placeholder]
        position = end
    output.append(surface[position:])
    return "".join(output)


def _value(value, refs):
    if isinstance(value, str) and value in refs:
        return refs[value]
    if isinstance(value, dict) and "literal" in value:
        return f"lit:{value['literal']['type']}:{value['literal']['value']}"
    return str(value)


def serialize_fact(fact, refs):
    parts = ["FACT", fact.get("stance", "support"), fact["operator"]]
    for role, value in sorted(fact.get("args", {}).items()):
        parts += [role, _value(value, refs)]
    return " ".join(parts)


def serialize_plan(plan, refs):
    parts = ["PLAN", plan["goal"]]
    if plan.get("value"):
        parts += ["VALUE", _value(plan["value"], refs)]
    for fact in plan.get("facts", []):
        parts += ["|", serialize_fact(fact, refs)]
    return " ".join(parts)


def compile_corpus(corpus: Path, knowledge_paths: list[Path]):
    source = json.loads(corpus.read_text(encoding="utf-8"))
    kinds, value_dimensions = load_knowledge(knowledge_paths)
    language = source["language"]
    constant_refs = tuple(sorted(set(str(ref) for ref in source.get("constant_refs", ()))))
    unknown_constants = [ref for ref in constant_refs if ref not in kinds]
    if unknown_constants:
        raise ValueError(f"reviewed constant refs are absent from semantic authority: {unknown_constants}")
    constant_sources = {f"CONST{i}": ref for i, ref in enumerate(constant_refs)}
    constant_map = {ref: source_ref for source_ref, ref in constant_sources.items()}
    output = {
        "version": 6,
        "language": language,
        "forces": sorted(set(source.get("forces", ["claim", "query", "description_request", "directive", "correction", "retraction", "acknowledgment"]))),
        "source_classes": list(BASE_SOURCE_CLASSES) + list(constant_sources),
        "constant_sources": constant_sources,
        "rule_sources": RULE_SOURCES,
        "operators": [],
        "roles": [],
        "structured_examples": [],
        "rule_examples": [],
        "realization_examples": [],
        "response_examples": [],
        "grammar_tokens": [],
        "function_forms": sorted(set(item.casefold() for item in source.get("function_forms", []))),
    }
    for index, example in enumerate(source.get("interpretation_examples", [])):
        input_text, refs = replace_mentions(example["surface"], example.get("mentions", []), kinds)
        output["structured_examples"].append(
            {
                "example_ref": example.get("example_ref", f"{language}:s:{index}"),
                "input": input_text,
                "target": structured_target(example["semantic"], refs, value_dimensions, kinds, constant_map),
                "weight": float(example.get("weight", 1)),
            }
        )
    for index, example in enumerate(source.get("definition_examples", [])):
        input_text, refs = replace_mentions(example["surface"], example.get("mentions", []), kinds)
        output["rule_examples"].append(
            {
                "example_ref": example.get("example_ref", f"{language}:d:{index}"),
                "input": input_text,
                "target": rule_target(example["rule"], refs, constant_map),
                "weight": float(example.get("weight", 1)),
            }
        )
    for index, example in enumerate(source.get("realization_examples", [])):
        refs = realization_refs(example)
        delex = replace_with_map(example["surface"], example.get("mentions", []), refs)
        semantic = serialize_plan(example["plan"], refs) if "plan" in example else serialize_fact(example["fact"], refs)
        output["realization_examples"].append(
            {
                "example_ref": example.get("example_ref", f"{language}:r:{index}"),
                "semantic": semantic,
                "surface_plan": delex,
                "weight": float(example.get("weight", 1)),
            }
        )
        output["grammar_tokens"].extend(
            token
            for token in re.findall(r"@[A-Z]\d+|[\wÀ-ÿ'’-]+|[^\w\s]", delex, re.UNICODE)
            if not token.startswith("@A")
        )
    for index, example in enumerate(source.get("response_examples", [])):
        semantic = str(example["semantic"])
        surface_plan = str(example["surface_plan"])
        output["response_examples"].append({
            "example_ref": example.get("example_ref", f"{language}:response:{index}"),
            "semantic": semantic,
            "surface_plan": surface_plan,
            "weight": float(example.get("weight", 1)),
        })
        output["grammar_tokens"].extend(
            token for token in re.findall(r"@[A-Z]\d+|[\wÀ-ÿ'’-]+|[^\w\s]", surface_plan, re.UNICODE)
            if not token.startswith(("@A", "@E", "@N"))
        )
    if source.get("semantic_episodes"):
        episodes = tuple(SemanticEpisode.from_dict(item) for item in source["semantic_episodes"])
        manifest = CurriculumManifest(
            tuple(source.get("train_families", sorted({x.family for x in episodes}))),
            tuple(source.get("holdout_families", ())),
            episodes,
            tuple(source.get("required_contrasts", (
                "claim_query_directive", "deictic_frame_reversal", "state_dimension_value",
                "transition_no_transition", "partial_meaning", "response_targeting",
            ))),
        )
        manifest.validate()
        output["curriculum_manifest"] = manifest.as_dict()

    operators = set()
    roles = set()
    for example in output["structured_examples"]:
        for application in example["target"].get("apps", []):
            operators.add(application["operator"])
            roles.update(application.get("bindings", {}))
    for example in output["rule_examples"]:
        for side in ("if", "then"):
            for application in example["target"].get(side, []):
                operators.add(application["operator"])
                roles.update(application.get("bindings", {}))
    if "op:state" in operators:
        roles.add("role:dimension")
    output["operators"] = sorted(operators)
    output["roles"] = sorted(roles)
    output["grammar_tokens"] = sorted(set(token.casefold() for token in output["grammar_tokens"]))
    output["pack_hash"] = pack_hash({key: value for key, value in output.items() if key != "pack_hash"})
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus")
    parser.add_argument("output")
    parser.add_argument("--knowledge", action="append", default=[])
    args = parser.parse_args()
    pack = compile_corpus(Path(args.corpus), [Path(item) for item in args.knowledge])
    Path(args.output).write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    print(pack["pack_hash"])


if __name__ == "__main__":
    main()
