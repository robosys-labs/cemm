"""Atomic semantic graph assembly for CEMM feature algebra v6.

This is the sole Stage-5 construction authority.  It delegates bounded role
assignment to :mod:`cemm.atomic_graph`, then creates fail-closed v6 coverage
receipts.  No surface text, regex, or total slot order participates in semantic
legality.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from cemm.atomic_graph import AtomicGraphMatcher as _GraphEngine
from cemm.model import canonical, lit, norm_text, stable
from cemm.semantic_coverage import CoveragePolicy, InterpretationCoverage


class SchemaValidationError(ValueError):
    pass


class TemplateResolutionError(SchemaValidationError):
    def __init__(self, unresolved_paths: Sequence[str]):
        self.unresolved_paths = tuple(map(str, unresolved_paths))
        super().__init__("atomic graph packet has unresolved template values: " + ", ".join(self.unresolved_paths))


_FORBIDDEN_MATCH_KEYS = frozenset({"literal", "surface", "regex", "pattern_text", "tokens", "phrase"})
_ALLOWED_IGNORABLE_KINDS = frozenset({"discourse"})


def _walk(value: Any, path: str = "root"):
    if isinstance(value, Mapping):
        yield path, value
        for key, item in value.items():
            yield from _walk(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _walk(item, f"{path}[{index}]")


def _template_dependencies(value: Any) -> tuple[tuple[str, str], ...]:
    output: list[tuple[str, str]] = []
    if isinstance(value, Mapping):
        for key in ("$capture", "$literal_capture"):
            if key in value:
                output.append(("capture", str(value[key])))
        for key in ("$feature", "$literal_feature"):
            if key in value:
                output.append(("feature", str(value[key]).partition(".")[0]))
        if "$context" in value:
            output.append(("context", str(value["$context"])))
        for item in value.values():
            output.extend(_template_dependencies(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            output.extend(_template_dependencies(item))
    elif isinstance(value, str):
        if value.startswith("$capture:"):
            output.append(("capture", value.split(":", 1)[1]))
        elif value.startswith("$feature:"):
            output.append(("feature", value.split(":", 1)[1].partition(".")[0]))
        elif value.startswith("$context:"):
            output.append(("context", value.split(":", 1)[1]))
    return tuple(output)


def feature_path(features: Mapping[str, Any], path: str, default=None):
    value: Any = features
    for part in str(path).split("."):
        if not isinstance(value, Mapping) or part not in value:
            return default
        value = value[part]
    return value


def _value_matches(actual: Any, expected: Any) -> bool:
    if isinstance(expected, Mapping):
        if "any_of" in expected:
            return any(_value_matches(actual, item) for item in expected["any_of"])
        if "all_of" in expected:
            return all(_value_matches(actual, item) for item in expected["all_of"])
        if "not" in expected:
            return not _value_matches(actual, expected["not"])
        if "present" in expected:
            present = actual not in (None, False, "", (), [], {})
            return present is bool(expected["present"])
    if isinstance(expected, (list, tuple, set, frozenset)):
        expected_values = {canonical(item) for item in expected}
        if isinstance(actual, (list, tuple, set, frozenset)):
            return bool({canonical(item) for item in actual}.intersection(expected_values))
        return canonical(actual) in expected_values
    if isinstance(actual, (list, tuple, set, frozenset)):
        return canonical(expected) in {canonical(item) for item in actual}
    return actual == expected


def unit_matches(unit: Any, spec: Mapping[str, Any]) -> bool:
    forbidden = _FORBIDDEN_MATCH_KEYS.intersection(spec)
    if forbidden:
        raise SchemaValidationError(f"surface constraint(s) forbidden: {sorted(forbidden)}")
    kind = spec.get("kind")
    if kind and getattr(unit, "kind", None) != kind:
        return False
    kinds = set(spec.get("kinds", ()))
    if kinds and getattr(unit, "kind", None) not in kinds:
        return False
    anchor_kind = spec.get("anchor_kind")
    if anchor_kind and not (getattr(unit, "kind", None) == "anchor" and getattr(unit, "atom_kind", None) == anchor_kind):
        return False
    anchor_kinds = set(spec.get("anchor_kinds", ()))
    if anchor_kinds and not (getattr(unit, "kind", None) == "anchor" and getattr(unit, "atom_kind", None) in anchor_kinds):
        return False
    anchor_ref = spec.get("anchor_ref")
    if anchor_ref and getattr(unit, "semantic_ref", None) != anchor_ref:
        return False
    source_kind = spec.get("source_kind")
    if source_kind and getattr(unit, "source_kind", None) != source_kind:
        return False
    features = dict(getattr(unit, "features", {}) or {})
    for path, expected in dict(spec.get("features", {})).items():
        if not _value_matches(feature_path(features, path), expected):
            return False
    if any(feature_path(features, path) not in (None, False, "", (), [], {}) for path in spec.get("absent_features", ())):
        return False
    return True


def capture_value(units: Sequence[Any], mode: str):
    if mode == "ref":
        return getattr(units[0], "semantic_ref", None) if units else None
    if mode == "refs":
        return [getattr(item, "semantic_ref", None) for item in units]
    if mode == "features":
        return dict(getattr(units[0], "features", {}) or {}) if len(units) == 1 else [dict(getattr(item, "features", {}) or {}) for item in units]
    text = " ".join(str(getattr(item, "surface", "")) for item in units).strip()
    if mode == "literal:text":
        return lit(text)
    if mode == "text":
        return text
    if mode == "units":
        return [item.as_dict() if hasattr(item, "as_dict") else vars(item) for item in units]
    return text


@dataclass(frozen=True)
class SchemaMatch:
    match_ref: str
    match_seed_ref: str
    schema_ref: str
    schema_family: str
    hypothesis_ref: str
    captures: Mapping[str, Any]
    slot_features: Mapping[str, Mapping[str, Any]]
    consumed_unit_refs: tuple[str, ...]
    role_by_unit_ref: Mapping[str, str]
    required_semantic_roles: tuple[str, ...]
    score: float
    coverage: InterpretationCoverage
    packet_template: Mapping[str, Any]
    slot_unit_refs: Mapping[str, tuple[str, ...]]
    projected_slots: Mapping[str, Mapping[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "match_ref": self.match_ref,
            "match_seed_ref": self.match_seed_ref,
            "schema_ref": self.schema_ref,
            "schema_family": self.schema_family,
            "hypothesis_ref": self.hypothesis_ref,
            "captures": dict(self.captures),
            "slot_features": {key: dict(value) for key, value in self.slot_features.items()},
            "consumed_unit_refs": list(self.consumed_unit_refs),
            "role_by_unit_ref": dict(self.role_by_unit_ref),
            "required_semantic_roles": list(self.required_semantic_roles),
            "slot_unit_refs": {key: list(value) for key, value in self.slot_unit_refs.items()},
            "projected_slots": {key: dict(value) for key, value in self.projected_slots.items()},
            "score": self.score,
            "coverage": self.coverage.as_dict(),
        }


class AtomicSchemaMatcher:
    """Compatibility facade over the exclusive v6 graph engine."""

    def __init__(self, schemas: Iterable[Mapping[str, Any]], *, max_matches: int = 32):
        self.schemas = tuple(dict(item) for item in schemas)
        self.max_matches = int(max_matches)
        self._schemas_by_ref = {str(item["ref"]): item for item in self.schemas}
        for schema in self.schemas:
            self.validate_schema(schema)
        self._engine = _GraphEngine(self.schemas, max_matches=max_matches)

    @staticmethod
    def validate_schema(schema: Mapping[str, Any]) -> None:
        ref = str(schema.get("ref") or "")
        family = str(schema.get("family") or "")
        steps = tuple(schema.get("steps", ()))
        packet = schema.get("packet")
        if not ref or not family or not steps or not isinstance(packet, Mapping):
            raise SchemaValidationError("schema requires ref, family, steps, and packet")
        if len(steps) > 16:
            raise SchemaValidationError("schema exceeds 16-slot bound")
        slots: set[str] = set()
        required_roles: set[str] = set()
        required_slots: set[str] = set()
        for index, raw in enumerate(steps):
            step = dict(raw)
            forbidden = _FORBIDDEN_MATCH_KEYS.intersection(step)
            if forbidden:
                raise SchemaValidationError(f"{ref}:{index} contains surface matcher keys {sorted(forbidden)}")
            for path, nested in _walk(step.get("features", {}), f"{ref}.steps[{index}].features"):
                nested_forbidden = _FORBIDDEN_MATCH_KEYS.intersection(nested)
                if nested_forbidden:
                    raise SchemaValidationError(f"{ref} forbidden nested matcher at {path}")
            slot = str(step.get("slot") or "")
            role = str(step.get("semantic_role") or "")
            if not slot or slot in slots or not role:
                raise SchemaValidationError(f"{ref} has invalid slot/role")
            slots.add(slot)
            if not step.get("optional") and role not in {"modifier", "discourse", "punctuation"}:
                required_roles.add(role)
                required_slots.add(slot)
            if not any(key in step for key in ("kind", "kinds", "anchor_kind", "anchor_kinds", "features", "span")):
                raise SchemaValidationError(f"{ref}:{slot} is unconstrained")
        contract = dict(schema.get("coverage_contract", {}))
        contract_roles = set(map(str, contract.get("required_semantic_roles", ())))
        contract_slots = set(map(str, contract.get("required_slots", ())))
        if contract_roles != required_roles:
            raise SchemaValidationError(f"{ref} role coverage contract mismatch: {contract_roles} != {required_roles}")
        if contract_slots != required_slots:
            raise SchemaValidationError(f"{ref} slot coverage contract mismatch: {contract_slots} != {required_slots}")
        role_cardinality = {str(key): int(value) for key, value in dict(contract.get("role_cardinality", {})).items()}
        observed_cardinality: dict[str, int] = {}
        for step in steps:
            if not step.get("optional") and step.get("semantic_role") not in {"modifier", "discourse", "punctuation"}:
                role = str(step["semantic_role"])
                observed_cardinality[role] = observed_cardinality.get(role, 0) + 1
        if role_cardinality != observed_cardinality:
            raise SchemaValidationError(f"{ref} role cardinality contract mismatch")
        ignorable = set(schema.get("ignorable_kinds", ()))
        if not ignorable.issubset(_ALLOWED_IGNORABLE_KINDS):
            raise SchemaValidationError(f"{ref} unsafe ignorable kinds: {sorted(ignorable)}")
        for kind, key in _template_dependencies(packet):
            if kind in {"capture", "feature"} and key not in slots:
                raise SchemaValidationError(f"{ref} packet references unknown slot {key!r}")
        try:
            _GraphEngine((schema,), max_matches=1)
        except ValueError as exc:
            raise SchemaValidationError(str(exc)) from exc

    @staticmethod
    def _context(participant_frame: Any | None) -> dict[str, Any]:
        if participant_frame is None:
            return {}
        return {
            "speaker_ref": participant_frame.speaker_ref,
            "addressee_ref": participant_frame.addressee_ref,
            "self_ref": participant_frame.self_ref,
            "conversation_ref": participant_frame.conversation_ref,
            **dict(getattr(participant_frame, "dialogue_context", {}) or {}),
        }

    def matches(self, lattice: Any, participant_frame: Any | None = None) -> tuple[SchemaMatch, ...]:
        graph_matches = self._engine.matches(lattice, context=self._context(participant_frame))
        hypotheses = {
            str(item.hypothesis_ref): item
            for item in tuple(getattr(lattice, "grounding_hypotheses", ()))
        }
        output: list[SchemaMatch] = []
        for graph in graph_matches:
            schema = self._schemas_by_ref[graph.schema_ref]
            hypothesis = hypotheses.get(graph.hypothesis_ref)
            if hypothesis is None:
                continue
            step_by_slot = {str(item["slot"]): dict(item) for item in schema["steps"]}
            slot_by_unit: dict[str, str] = {}
            for slot, refs in graph.slot_unit_refs.items():
                for ref in refs:
                    slot_by_unit[str(ref)] = str(slot)
            projected_slots = {
                slot: {
                    "capture": item.capture,
                    "features": dict(item.features),
                    "source": item.source,
                    "reason": item.reason,
                    "penalty": item.penalty,
                    "ports_provided": list(item.ports_provided),
                }
                for slot, item in graph.projected.items()
            }
            projected_roles: dict[str, list[dict[str, Any]]] = {}
            for slot, evidence in projected_slots.items():
                role = str(step_by_slot[slot]["semantic_role"])
                projected_roles.setdefault(role, []).append({"slot": slot, **evidence})
            contract = dict(schema.get("coverage_contract", {}))
            match_seed_ref = stable(
                "atomic-graph-schema-match-seed-v6",
                graph.schema_ref,
                graph.hypothesis_ref,
                graph.captures,
                graph.slot_unit_refs,
                projected_slots,
            )
            coverage = CoveragePolicy.build(
                tuple(getattr(hypothesis, "units", ())),
                graph.coverage.consumed_unit_refs,
                role_by_unit_ref=graph.semantic_role_by_unit_ref,
                slot_by_unit_ref=slot_by_unit,
                required_semantic_roles=contract.get("required_semantic_roles", ()),
                required_semantic_slots=contract.get("required_slots", ()),
                projected_semantic_roles=projected_roles,
                projected_slots=projected_slots,
                schema_ref=graph.schema_ref,
                hypothesis_ref=graph.hypothesis_ref,
                match_seed_ref=match_seed_ref,
                seed=(graph.captures, graph.slot_unit_refs, projected_slots),
            )
            output.append(SchemaMatch(
                match_ref=stable("atomic-graph-schema-match-v6", match_seed_ref, coverage.coverage_ref),
                match_seed_ref=match_seed_ref,
                schema_ref=graph.schema_ref,
                schema_family=graph.schema_family,
                hypothesis_ref=graph.hypothesis_ref,
                captures=dict(graph.captures),
                slot_features={key: dict(value) for key, value in graph.slot_features.items()},
                consumed_unit_refs=tuple(graph.coverage.consumed_unit_refs),
                role_by_unit_ref=dict(graph.semantic_role_by_unit_ref),
                required_semantic_roles=tuple(map(str, contract.get("required_semantic_roles", ()))),
                score=float(graph.score),
                coverage=coverage,
                packet_template=dict(graph.packet_template),
                slot_unit_refs={key: tuple(value) for key, value in graph.slot_unit_refs.items()},
                projected_slots=projected_slots,
            ))
        output.sort(key=lambda item: (
            not item.coverage.executable,
            len(item.coverage.missing_semantic_slots),
            -item.coverage.weighted_coverage,
            -item.score,
            item.match_ref,
        ))
        return tuple(output[: self.max_matches])


class _UnresolvedTemplateValue:
    def __init__(self, source: str):
        self.source = source


class PacketTemplateResolver:
    @staticmethod
    def _required(value: Any, source: str) -> Any:
        return _UnresolvedTemplateValue(source) if value is None else value

    @staticmethod
    def resolve(value: Any, captures: Mapping[str, Any], slot_features: Mapping[str, Mapping[str, Any]], context: Mapping[str, Any]) -> Any:
        if isinstance(value, list):
            return [PacketTemplateResolver.resolve(item, captures, slot_features, context) for item in value]
        if isinstance(value, dict):
            if "$capture" in value:
                key = str(value["$capture"])
                return PacketTemplateResolver._required(captures.get(key), f"capture:{key}")
            if "$context" in value:
                key = str(value["$context"])
                return PacketTemplateResolver._required(context.get(key), f"context:{key}")
            if "$feature" in value:
                raw = str(value["$feature"])
                slot, _, path = raw.partition(".")
                return PacketTemplateResolver._required(feature_path(slot_features.get(slot, {}), path), f"feature:{raw}")
            if "$literal_capture" in value:
                key = str(value["$literal_capture"])
                raw = captures.get(key)
                if raw is None:
                    return _UnresolvedTemplateValue(f"literal_capture:{key}")
                if isinstance(raw, Mapping) and "literal" in raw:
                    return raw
                return lit(raw, str(value.get("type", "text")))
            if "$literal_feature" in value:
                raw_path = str(value["$literal_feature"])
                slot, _, path = raw_path.partition(".")
                raw = feature_path(slot_features.get(slot, {}), path)
                if raw is None:
                    return _UnresolvedTemplateValue(f"literal_feature:{raw_path}")
                return lit(raw, str(value.get("type", "text")))
            return {key: PacketTemplateResolver.resolve(item, captures, slot_features, context) for key, item in value.items()}
        if isinstance(value, str) and value.startswith("$capture:"):
            key = value.split(":", 1)[1]
            return PacketTemplateResolver._required(captures.get(key), f"capture:{key}")
        if isinstance(value, str) and value.startswith("$context:"):
            key = value.split(":", 1)[1]
            return PacketTemplateResolver._required(context.get(key), f"context:{key}")
        if isinstance(value, str) and value.startswith("$feature:"):
            raw = value.split(":", 1)[1]
            slot, _, path = raw.partition(".")
            return PacketTemplateResolver._required(feature_path(slot_features.get(slot, {}), path), f"feature:{raw}")
        return value

    @staticmethod
    def unresolved(value: Any, path: str = "packet") -> tuple[str, ...]:
        output: list[str] = []
        if isinstance(value, _UnresolvedTemplateValue):
            output.append(f"{path}:{value.source}")
        elif isinstance(value, dict):
            for key, item in value.items():
                output.extend(PacketTemplateResolver.unresolved(item, f"{path}.{key}"))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                output.extend(PacketTemplateResolver.unresolved(item, f"{path}[{index}]"))
        return tuple(output)


class AtomicConstructionAssembler:
    def __init__(self, form_pack: Any, *, max_matches: int = 32):
        schemas = tuple(getattr(form_pack, "schemas", ()))
        if not schemas:
            raise SchemaValidationError("form pack contains no graph schemas")
        self.matcher = AtomicSchemaMatcher(schemas, max_matches=max_matches)
        self.max_matches = int(max_matches)

    def evidence_records(self, lattice: Any, participant_frame: Any | None = None) -> tuple[SchemaMatch, ...]:
        return self.matcher.matches(lattice, participant_frame)

    @staticmethod
    def _context(participant_frame: Any, language: str) -> dict[str, Any]:
        return {
            "language_literal": lit(language),
            "script_literal": lit("Latn"),
            "true_literal": lit(True, "bool"),
            "one_float_literal": lit(1.0, "float"),
            "speaker_ref": participant_frame.speaker_ref,
            "addressee_ref": participant_frame.addressee_ref,
            "self_ref": participant_frame.self_ref,
            "conversation_ref": participant_frame.conversation_ref,
            **dict(getattr(participant_frame, "dialogue_context", {}) or {}),
        }

    @staticmethod
    def instantiate(match: SchemaMatch, participant_frame: Any, language: str) -> dict[str, Any]:
        if not match.coverage.executable:
            raise SchemaValidationError("cannot instantiate graph without complete v6 coverage")
        packet = PacketTemplateResolver.resolve(
            match.packet_template,
            match.captures,
            match.slot_features,
            AtomicConstructionAssembler._context(participant_frame, language),
        )
        if not isinstance(packet, dict):
            raise SchemaValidationError("graph packet did not resolve to mapping")
        unresolved = PacketTemplateResolver.unresolved(packet)
        if unresolved:
            raise TemplateResolutionError(unresolved)
        qualifiers = dict(packet.get("qualifiers", {}))
        qualifiers.update({
            "construction_schema_ref": match.schema_ref,
            "coverage_ref": match.coverage.coverage_ref,
            "projected_slots": sorted(match.projected_slots),
        })
        packet["qualifiers"] = qualifiers
        return packet

    @staticmethod
    def partial_structure(match: SchemaMatch, participant_frame: Any, language: str) -> dict[str, Any]:
        resolved = PacketTemplateResolver.resolve(
            match.packet_template,
            match.captures,
            match.slot_features,
            AtomicConstructionAssembler._context(participant_frame, language),
        )
        unresolved = PacketTemplateResolver.unresolved(resolved)
        return {
            "partial_structure_ref": stable("partial-semantic-graph-v6", match.match_ref, match.coverage.coverage_ref),
            "schema_ref": match.schema_ref,
            "schema_family": match.schema_family,
            "force": resolved.get("force") if isinstance(resolved, Mapping) else None,
            "semantic_skeleton": resolved if not unresolved else None,
            "captures": dict(match.captures),
            "slot_features": {key: dict(value) for key, value in match.slot_features.items()},
            "slot_unit_refs": {key: list(value) for key, value in match.slot_unit_refs.items()},
            "projected_slots": {key: dict(value) for key, value in match.projected_slots.items()},
            "missing_semantic_slots": list(match.coverage.missing_semantic_slots),
            "unresolved_template_paths": list(unresolved),
            "coverage": match.coverage.as_dict(),
            "open_residuals": [item.as_dict() for item in match.coverage.critical_residuals],
            "executable": False,
        }


def lexeme_index(records: Iterable[Mapping[str, Any]]) -> dict[str, tuple[dict[str, Any], ...]]:
    output: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        features = dict(record.get("features", {}))
        if not features:
            continue
        for form in record.get("forms", ()):
            key = norm_text(str(form))
            if key:
                output.setdefault(key, []).append(features)
    return {key: tuple(sorted(values, key=canonical)) for key, values in output.items()}


def merge_lexeme_features(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    alternatives: dict[str, list[Any]] = {}
    for record in records:
        for key, value in record.items():
            if key not in merged:
                merged[key] = value
            elif canonical(merged[key]) != canonical(value):
                alternatives.setdefault(key, [merged[key]])
                if all(canonical(existing) != canonical(value) for existing in alternatives[key]):
                    alternatives[key].append(value)
    for key, values in alternatives.items():
        merged[key] = tuple(values)
    return merged
