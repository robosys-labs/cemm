"""Atomic, feature-driven construction assembly for CEMM.

The active runtime never matches semantic constructions against language strings.
Surface forms are converted to atomic feature evidence by the form pack; schemas
are trained/compiled over those features.  The resulting matcher is bounded,
N-best, language-pack data driven, and emits explicit span-coverage receipts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from cemm.model import canonical, lit, norm_text, stable
from cemm.semantic_coverage import (
    CoverageIntegrityError,
    CoveragePolicy,
    InterpretationCoverage,
)


class SchemaValidationError(ValueError):
    pass


class TemplateResolutionError(SchemaValidationError):
    def __init__(self, unresolved_paths: Sequence[str]):
        self.unresolved_paths = tuple(map(str, unresolved_paths))
        super().__init__(
            "atomic schema packet contains unresolved template values: "
            + ", ".join(self.unresolved_paths)
        )


_FORBIDDEN_MATCH_KEYS = frozenset({"literal", "surface", "regex", "pattern_text", "tokens", "phrase"})
_ALLOWED_IGNORABLE_KINDS = frozenset({"discourse", "punctuation"})


def _walk_mappings(value: Any, path: str = "root"):
    if isinstance(value, Mapping):
        yield path, value
        for key, item in value.items():
            yield from _walk_mappings(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _walk_mappings(item, f"{path}[{index}]")


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


def feature_path(features: Mapping[str, Any], path: str, default=None):
    value: Any = features
    for part in str(path).split("."):
        if not isinstance(value, Mapping) or part not in value:
            return default
        value = value[part]
    return value


def unit_matches(unit: Any, spec: Mapping[str, Any]) -> bool:
    """Match a unit using kind/ref/feature constraints only.

    ``literal`` and ``surface`` constraints are forbidden by contract.  The
    lexical layer may map a surface to features, but semantic schemas cannot see
    the original word identity.
    """
    forbidden = _FORBIDDEN_MATCH_KEYS.intersection(spec)
    if forbidden:
        raise SchemaValidationError(
            f"surface constraint(s) forbidden in atomic schema: {sorted(forbidden)}"
        )
    kind = spec.get("kind")
    if kind and getattr(unit, "kind", None) != kind:
        return False
    kinds = spec.get("kinds")
    if kinds and getattr(unit, "kind", None) not in set(kinds):
        return False
    anchor_kind = spec.get("anchor_kind")
    if anchor_kind and not (
        getattr(unit, "kind", None) == "anchor"
        and getattr(unit, "atom_kind", None) == anchor_kind
    ):
        return False
    anchor_kinds = spec.get("anchor_kinds")
    if anchor_kinds and not (
        getattr(unit, "kind", None) == "anchor"
        and getattr(unit, "atom_kind", None) in set(anchor_kinds)
    ):
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
    absent = tuple(spec.get("absent_features", ()))
    if any(feature_path(features, path) not in (None, False, "", (), [], {}) for path in absent):
        return False
    return True


def capture_value(units: Sequence[Any], mode: str):
    if mode == "ref":
        return getattr(units[0], "semantic_ref", None) if units else None
    if mode == "refs":
        return [getattr(item, "semantic_ref", None) for item in units]
    text = " ".join(str(getattr(item, "surface", "")) for item in units).strip()
    if mode == "literal:text":
        return lit(text)
    if mode == "text":
        return text
    if mode == "units":
        return [item.as_dict() if hasattr(item, "as_dict") else vars(item) for item in units]
    if mode == "features":
        return [dict(getattr(item, "features", {}) or {}) for item in units]
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

    def as_dict(self) -> dict[str, Any]:
        return {
            "match_ref": self.match_ref,
            "match_seed_ref": self.match_seed_ref,
            "schema_ref": self.schema_ref,
            "schema_family": self.schema_family,
            "hypothesis_ref": self.hypothesis_ref,
            "captures": dict(self.captures),
            "slot_features": {
                key: dict(value) for key, value in self.slot_features.items()
            },
            "consumed_unit_refs": list(self.consumed_unit_refs),
            "role_by_unit_ref": dict(self.role_by_unit_ref),
            "required_semantic_roles": list(self.required_semantic_roles),
            "score": self.score,
            "coverage": self.coverage.as_dict(),
        }


class AtomicSchemaMatcher:
    """Bounded matcher for trained atomic schemas.

    Schema steps are feature constraints, not phrases.  Each step may consume a
    single unit or a bounded span.  Optional steps are explicit and all skipped
    observed units remain represented in the coverage receipt.
    """

    def __init__(self, schemas: Iterable[Mapping[str, Any]], *, max_matches: int = 32):
        self.schemas = tuple(dict(item) for item in schemas)
        self.max_matches = int(max_matches)
        refs = [str(item.get("ref") or "") for item in self.schemas]
        if len(refs) != len(set(refs)):
            raise SchemaValidationError("atomic schema refs must be unique")
        for schema in self.schemas:
            self.validate_schema(schema)

    @staticmethod
    def validate_schema(schema: Mapping[str, Any]) -> None:
        ref = str(schema.get("ref") or "")
        family = str(schema.get("family") or "")
        steps = tuple(schema.get("steps", ()))
        packet = schema.get("packet")
        if not ref or not family:
            raise SchemaValidationError("schema requires ref and family")
        if not steps:
            raise SchemaValidationError(f"schema {ref} requires steps")
        if len(steps) > 16:
            raise SchemaValidationError(
                f"schema {ref} exceeds the bounded 16-step matcher contract"
            )
        if not isinstance(packet, Mapping):
            raise SchemaValidationError(f"schema {ref} requires packet")
        if packet.get("force") not in {
            "acknowledgment", "claim", "correction", "description_request",
            "directive", "query", "retraction"
        }:
            raise SchemaValidationError(f"schema {ref} has invalid force")

        slots: list[str] = []
        semantic_roles: set[str] = set()
        for index, raw_step in enumerate(steps):
            if not isinstance(raw_step, Mapping):
                raise SchemaValidationError(f"schema {ref} step {index} is not a mapping")
            step = dict(raw_step)
            forbidden = _FORBIDDEN_MATCH_KEYS.intersection(step)
            if forbidden:
                raise SchemaValidationError(
                    f"schema {ref} step {index} contains surface matcher keys {sorted(forbidden)}"
                )
            for nested_path, nested in _walk_mappings(step.get("features", {}), f"{ref}.steps[{index}].features"):
                forbidden_nested = _FORBIDDEN_MATCH_KEYS.intersection(nested)
                if forbidden_nested:
                    raise SchemaValidationError(
                        f"schema {ref} has forbidden nested matcher keys at {nested_path}: {sorted(forbidden_nested)}"
                    )
            slot = str(step.get("slot") or "")
            role = str(step.get("semantic_role") or "")
            if not slot or slot in slots:
                raise SchemaValidationError(f"schema {ref} has duplicate/empty slot {slot!r}")
            if not role:
                raise SchemaValidationError(f"schema {ref}:{slot} lacks semantic_role")
            slots.append(slot)
            if not step.get("optional") and role not in {"modifier", "discourse", "punctuation"}:
                semantic_roles.add(role)
            constrained = any(
                key in step for key in ("kind", "kinds", "anchor_kind", "anchor_kinds", "features", "span")
            )
            if not constrained:
                raise SchemaValidationError(f"schema {ref}:{slot} is unconstrained")
            if step.get("span"):
                minimum = int(step.get("min_units", 1))
                maximum = int(step.get("max_units", 0))
                if not 1 <= minimum <= maximum <= 12:
                    raise SchemaValidationError(f"schema {ref}:{slot} has invalid span bounds")

        ignorable = set(schema.get("ignorable_kinds", ()))
        if not ignorable.issubset(_ALLOWED_IGNORABLE_KINDS):
            raise SchemaValidationError(
                f"schema {ref} declares semantically unsafe ignorable kinds {sorted(ignorable - _ALLOWED_IGNORABLE_KINDS)}"
            )
        contract = dict(schema.get("coverage_contract", {}))
        required_roles = tuple(sorted(set(map(str, contract.get("required_semantic_roles", ())))))
        if not required_roles:
            raise SchemaValidationError(f"schema {ref} lacks coverage_contract.required_semantic_roles")
        absent_roles = set(required_roles) - semantic_roles
        if absent_roles:
            raise SchemaValidationError(
                f"schema {ref} coverage contract references absent required roles {sorted(absent_roles)}"
            )
        if set(semantic_roles) - set(required_roles):
            raise SchemaValidationError(
                f"schema {ref} coverage contract omits nonoptional semantic roles {sorted(set(semantic_roles)-set(required_roles))}"
            )
        dependencies = _template_dependencies(packet)
        for kind, key in dependencies:
            if kind in {"capture", "feature"} and key not in slots:
                raise SchemaValidationError(
                    f"schema {ref} packet depends on unknown {kind} slot {key!r}"
                )

    @staticmethod
    def _span_valid(selected: Sequence[Any], step: Mapping[str, Any]) -> bool:
        if not selected:
            return False
        allowed_kinds = set(step.get("allowed_kinds", ()))
        if allowed_kinds and any(getattr(item, "kind", None) not in allowed_kinds for item in selected):
            return False
        # An explicitly listed kind is itself permission.  The legacy
        # ``allow_*`` flags remain additive for packs that use broad kind sets,
        # but must not contradict ``allowed_kinds`` (a prior bug listed anchors
        # as allowed and then rejected every grounded anchor anyway).
        allow_anchors = bool(step.get("allow_anchors", "anchor" in allowed_kinds))
        allow_punctuation = bool(
            step.get("allow_punctuation", "punctuation" in allowed_kinds)
        )
        allow_function = bool(step.get("allow_function", "function" in allowed_kinds))
        if not allow_anchors and any(getattr(item, "kind", None) == "anchor" for item in selected):
            return False
        if not allow_punctuation and any(getattr(item, "kind", None) == "punctuation" for item in selected):
            return False
        if not allow_function and any(getattr(item, "kind", None) == "function" for item in selected):
            return False
        unit_spec = dict(step.get("unit_constraints", {}))
        if unit_spec and any(not unit_matches(item, unit_spec) for item in selected):
            return False
        return True

    def _match_schema(self, hypothesis: Any, schema: Mapping[str, Any]) -> tuple[SchemaMatch, ...]:
        units = tuple(getattr(hypothesis, "units", ()))
        steps = tuple(schema.get("steps", ()))
        results: list[tuple[dict[str, Any], dict[str, Mapping[str, Any]], tuple[str, ...], dict[str, str], float]] = []
        ignorable = set(schema.get("ignorable_kinds", ()))
        visited_states = 0
        state_budget = max(1024, self.max_matches * 256)

        def walk(
            si: int,
            ui: int,
            captures: dict[str, Any],
            slot_features: dict[str, Mapping[str, Any]],
            consumed: tuple[str, ...],
            roles: dict[str, str],
            score: float,
        ) -> None:
            nonlocal visited_states
            visited_states += 1
            if visited_states > state_budget:
                raise SchemaValidationError(
                    f"schema {schema.get('ref')} exceeded bounded matcher search budget"
                )
            # Only schema-declared ignorable kinds may be traversed. They are not
            # marked consumed and therefore remain visible in the coverage receipt.
            while ui < len(units) and getattr(units[ui], "kind", None) in ignorable:
                ui += 1
            if si >= len(steps):
                # Do not require end-of-input. Remaining material is classified by
                # CoveragePolicy and may make this a partial, non-executable match.
                results.append((dict(captures), dict(slot_features), consumed, dict(roles), score))
                return
            step = dict(steps[si])
            if step.get("optional"):
                skipped = dict(step)
                skipped.pop("optional", None)
                walk(si + 1, ui, captures, slot_features, consumed, roles, score - float(step.get("skip_penalty", 0.02)))
                step = skipped
            slot = str(step.get("slot") or f"slot_{si}")
            semantic_role = str(step.get("semantic_role") or slot)
            mode = str(step.get("capture", "ref"))
            if step.get("span"):
                minimum = max(1, int(step.get("min_units", 1)))
                maximum = min(int(step.get("max_units", 12)), len(units) - ui)
                for length in range(maximum, minimum - 1, -1):
                    selected = units[ui : ui + length]
                    if not self._span_valid(selected, step):
                        continue
                    next_captures = dict(captures)
                    next_captures[slot] = capture_value(selected, mode)
                    merged_features: dict[str, Any] = {}
                    for item in selected:
                        merged_features.update(dict(getattr(item, "features", {}) or {}))
                    next_features = dict(slot_features)
                    next_features[slot] = merged_features
                    next_roles = dict(roles)
                    for item in selected:
                        next_roles[str(getattr(item, "unit_ref"))] = semantic_role
                    walk(
                        si + 1,
                        ui + length,
                        next_captures,
                        next_features,
                        consumed + tuple(str(getattr(item, "unit_ref")) for item in selected),
                        next_roles,
                        score - 0.01 * max(0, length - minimum),
                    )
                return
            if ui >= len(units) or not unit_matches(units[ui], step):
                return
            unit = units[ui]
            next_captures = dict(captures)
            next_captures[slot] = capture_value((unit,), mode)
            next_features = dict(slot_features)
            next_features[slot] = dict(getattr(unit, "features", {}) or {})
            next_roles = dict(roles)
            next_roles[str(getattr(unit, "unit_ref"))] = semantic_role
            walk(
                si + 1,
                ui + 1,
                next_captures,
                next_features,
                consumed + (str(getattr(unit, "unit_ref")),),
                next_roles,
                score + float(step.get("weight", 0.0)),
            )

        walk(0, 0, {}, {}, (), {}, 0.0)
        output: list[SchemaMatch] = []
        for captures, slot_features, consumed, roles, score in results:
            required_roles = tuple(
                schema.get("coverage_contract", {}).get("required_semantic_roles", ())
            )
            hypothesis_ref = str(getattr(hypothesis, "hypothesis_ref", ""))
            match_seed_ref = stable(
                "atomic-schema-match-seed",
                str(schema["ref"]),
                hypothesis_ref,
                captures,
                consumed,
            )
            coverage = CoveragePolicy.build(
                units,
                consumed,
                role_by_unit_ref=roles,
                required_semantic_roles=required_roles,
                schema_ref=str(schema["ref"]),
                hypothesis_ref=hypothesis_ref,
                match_seed_ref=match_seed_ref,
                seed=(captures, consumed),
            )
            payload = (match_seed_ref, coverage.coverage_ref)
            output.append(
                SchemaMatch(
                    stable("atomic-schema-match", payload),
                    match_seed_ref,
                    str(schema["ref"]),
                    str(schema.get("family") or schema["ref"]),
                    str(getattr(hypothesis, "hypothesis_ref", "")),
                    captures,
                    slot_features,
                    consumed,
                    roles,
                    required_roles,
                    float(getattr(hypothesis, "score", 0.0))
                    + float(schema.get("weight", 1.0))
                    + score
                    + 0.5 * coverage.weighted_coverage,
                    coverage,
                    dict(schema["packet"]),
                )
            )
        output.sort(
            key=lambda item: (
                not item.coverage.complete,
                -item.coverage.weighted_coverage,
                -item.score,
                item.match_ref,
            )
        )
        return tuple(output[: self.max_matches])

    def matches(self, lattice: Any) -> tuple[SchemaMatch, ...]:
        output: list[SchemaMatch] = []
        # Scan the complete bounded hypothesis × schema product before ranking.
        # An early raw-match cutoff can allow high-ranked partial hypotheses to
        # starve a later executable hypothesis (notably contraction expansions
        # and participant-grounded alternatives).  The product is already hard
        # bounded by FormProcessor.max_grounding_hypotheses, schema count, and
        # this matcher's per-schema max_matches; ranking/truncation happens only
        # after all candidates have comparable coverage receipts.
        for hypothesis in tuple(getattr(lattice, "grounding_hypotheses", ())):
            for schema in self.schemas:
                output.extend(self._match_schema(hypothesis, schema))
        unique: dict[str, SchemaMatch] = {}
        for item in output:
            previous = unique.get(item.match_ref)
            if previous is None or item.score > previous.score:
                unique[item.match_ref] = item
        ordered = sorted(
            unique.values(),
            key=lambda item: (
                not item.coverage.complete,
                -item.coverage.weighted_coverage,
                -item.score,
                item.match_ref,
            ),
        )
        return tuple(ordered[: self.max_matches])


class _UnresolvedTemplateValue:
    def __init__(self, source: str):
        self.source = source

    def __repr__(self) -> str:
        return f"<unresolved:{self.source}>"


class PacketTemplateResolver:
    @staticmethod
    def _required(value: Any, source: str) -> Any:
        return _UnresolvedTemplateValue(source) if value is None else value

    @staticmethod
    def resolve(
        value: Any,
        captures: Mapping[str, Any],
        slot_features: Mapping[str, Mapping[str, Any]],
        context: Mapping[str, Any],
    ) -> Any:
        if isinstance(value, list):
            return [
                PacketTemplateResolver.resolve(item, captures, slot_features, context)
                for item in value
            ]
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
                result = feature_path(slot_features.get(slot, {}), path)
                return PacketTemplateResolver._required(result, f"feature:{raw}")
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
            return {
                key: PacketTemplateResolver.resolve(item, captures, slot_features, context)
                for key, item in value.items()
            }
        if isinstance(value, str) and value.startswith("$capture:"):
            key = value.split(":", 1)[1]
            return PacketTemplateResolver._required(captures.get(key), f"capture:{key}")
        if isinstance(value, str) and value.startswith("$context:"):
            key = value.split(":", 1)[1]
            return PacketTemplateResolver._required(context.get(key), f"context:{key}")
        if isinstance(value, str) and value.startswith("$feature:"):
            raw = value.split(":", 1)[1]
            slot, _, path = raw.partition(".")
            result = feature_path(slot_features.get(slot, {}), path)
            return PacketTemplateResolver._required(result, f"feature:{raw}")
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
    """Facade used by :mod:`cemm.forms` after the legacy matcher is removed."""

    def __init__(self, form_pack: Any, *, max_matches: int = 32):
        schemas = tuple(getattr(form_pack, "schemas", ()))
        if not schemas:
            raise SchemaValidationError("form pack contains no atomic schemas")
        self.matcher = AtomicSchemaMatcher(schemas, max_matches=max_matches)
        self.max_matches = int(max_matches)

    def evidence_records(self, lattice: Any) -> tuple[SchemaMatch, ...]:
        return self.matcher.matches(lattice)

    @staticmethod
    def instantiate(match: SchemaMatch, participant_frame: Any, language: str) -> dict[str, Any]:
        if not match.coverage.executable:
            raise SchemaValidationError(
                "cannot instantiate an atomic schema without verified complete coverage"
            )
        context = {
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
        packet = PacketTemplateResolver.resolve(
            match.packet_template,
            match.captures,
            match.slot_features,
            context,
        )
        if not isinstance(packet, dict):
            raise SchemaValidationError("atomic schema packet did not resolve to mapping")
        unresolved = PacketTemplateResolver.unresolved(packet)
        if unresolved:
            raise TemplateResolutionError(unresolved)
        qualifiers = dict(packet.get("qualifiers", {}))
        qualifiers.update(
            {
                "construction_schema_ref": match.schema_ref,
                "coverage_ref": match.coverage.coverage_ref,
            }
        )
        packet["qualifiers"] = qualifiers
        return packet

    @staticmethod
    def partial_structure(match: SchemaMatch, participant_frame: Any, language: str) -> dict[str, Any]:
        """Preserve the matched semantic skeleton without authorizing execution."""
        context = {
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
        resolved = PacketTemplateResolver.resolve(
            match.packet_template, match.captures, match.slot_features, context
        )
        unresolved = PacketTemplateResolver.unresolved(resolved)
        return {
            "partial_structure_ref": stable(
                "partial-semantic-structure", match.match_ref, match.coverage.coverage_ref
            ),
            "schema_ref": match.schema_ref,
            "schema_family": match.schema_family,
            "force": resolved.get("force") if isinstance(resolved, Mapping) else None,
            "semantic_skeleton": resolved if not unresolved else None,
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
            if not key:
                continue
            output.setdefault(key, []).append(features)
    return {
        key: tuple(sorted(values, key=canonical))
        for key, values in output.items()
    }


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
