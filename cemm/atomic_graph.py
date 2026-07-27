"""Bounded atomic semantic graph assembly.

This module is deliberately surface-agnostic.  It accepts already-normalized,
feature-bearing form units and assembles them into typed slot graphs.  Surface
order is evidence, never semantic authority.  Missing slots may be projected
only by reviewed, typed projection rules with explicit penalties and provenance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence
import hashlib
import json


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _stable(namespace: str, *parts: Any) -> str:
    digest = hashlib.sha256(_canonical((namespace, parts)).encode("utf-8")).hexdigest()[:24]
    return f"{namespace}:{digest}"


def feature_path(features: Mapping[str, Any], path: str, default: Any = None) -> Any:
    value: Any = features
    for part in str(path).split("."):
        if not isinstance(value, Mapping) or part not in value:
            return default
        value = value[part]
    return value


def value_matches(actual: Any, expected: Any) -> bool:
    if isinstance(expected, Mapping):
        if "any_of" in expected:
            return any(value_matches(actual, item) for item in expected["any_of"])
        if "all_of" in expected:
            return all(value_matches(actual, item) for item in expected["all_of"])
        if "not" in expected:
            return not value_matches(actual, expected["not"])
        if "present" in expected:
            present = actual not in (None, False, "", (), [], {})
            return present is bool(expected["present"])
    if isinstance(expected, (list, tuple, set, frozenset)):
        expected_values = {_canonical(item) for item in expected}
        if isinstance(actual, (list, tuple, set, frozenset)):
            return bool({_canonical(item) for item in actual}.intersection(expected_values))
        return _canonical(actual) in expected_values
    if isinstance(actual, (list, tuple, set, frozenset)):
        return _canonical(expected) in {_canonical(item) for item in actual}
    return actual == expected


@dataclass(frozen=True)
class UnitView:
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
    features: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_object(cls, value: Any) -> "UnitView":
        return cls(
            unit_ref=str(getattr(value, "unit_ref")),
            kind=str(getattr(value, "kind")),
            surface=str(getattr(value, "surface", "")),
            normalized=str(getattr(value, "normalized", "")),
            token_start=int(getattr(value, "token_start", -1)),
            token_end=int(getattr(value, "token_end", -1)),
            char_start=int(getattr(value, "char_start", -1)),
            char_end=int(getattr(value, "char_end", -1)),
            semantic_ref=getattr(value, "semantic_ref", None),
            atom_kind=getattr(value, "atom_kind", None),
            source_kind=getattr(value, "source_kind", None),
            score=float(getattr(value, "score", 0.0)),
            features=dict(getattr(value, "features", {}) or {}),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "unit_ref": self.unit_ref,
            "kind": self.kind,
            "surface": self.surface,
            "normalized": self.normalized,
            "token_start": self.token_start,
            "token_end": self.token_end,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "semantic_ref": self.semantic_ref,
            "atom_kind": self.atom_kind,
            "source_kind": self.source_kind,
            "score": self.score,
            "features": dict(self.features),
        }


@dataclass(frozen=True)
class SlotSpec:
    slot: str
    semantic_role: str
    capture: str
    optional: bool
    match: Mapping[str, Any]
    span: bool = False
    min_units: int = 1
    max_units: int = 1
    allowed_kinds: tuple[str, ...] = ()
    ports_provided: tuple[str, ...] = ()
    ports_required: tuple[str, ...] = ()
    weight: float = 0.0


@dataclass(frozen=True)
class ProjectionRule:
    slot: str
    source: str
    value: Any = None
    context_path: str | None = None
    features: Mapping[str, Any] = field(default_factory=dict)
    requires_slots: tuple[str, ...] = ()
    forbids_slots: tuple[str, ...] = ()
    ports_provided: tuple[str, ...] = ()
    penalty: float = 0.25
    reason: str = "reviewed_projection"


@dataclass(frozen=True)
class OrderPreference:
    before: str
    after: str
    weight: float = 0.08


@dataclass(frozen=True)
class HardConstraint:
    kind: str
    slots: tuple[str, ...]
    max_distance: int | None = None


@dataclass(frozen=True)
class SlotCandidate:
    slot: str
    units: tuple[UnitView, ...]
    capture: Any
    features: Mapping[str, Any]
    score: float

    @property
    def unit_refs(self) -> tuple[str, ...]:
        return tuple(item.unit_ref for item in self.units)

    @property
    def start(self) -> int:
        return min((item.token_start for item in self.units), default=-1)

    @property
    def end(self) -> int:
        return max((item.token_end for item in self.units), default=-1)


@dataclass(frozen=True)
class ProjectedSlot:
    slot: str
    capture: Any
    features: Mapping[str, Any]
    source: str
    reason: str
    penalty: float
    ports_provided: tuple[str, ...] = ()


@dataclass(frozen=True)
class GroundingResidual:
    unit_ref: str
    surface: str
    normalized: str
    kind: str
    semantic_ref: str | None
    atom_kind: str | None
    source_kind: str | None
    grounding_status: str
    residual_class: str
    role_hypotheses: tuple[str, ...]
    features: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "unit_ref": self.unit_ref,
            "surface": self.surface,
            "normalized": self.normalized,
            "kind": self.kind,
            "semantic_ref": self.semantic_ref,
            "atom_kind": self.atom_kind,
            "source_kind": self.source_kind,
            "grounding_status": self.grounding_status,
            "residual_class": self.residual_class,
            "role_hypotheses": list(self.role_hypotheses),
            "features": dict(self.features),
        }


@dataclass(frozen=True)
class GraphCoverage:
    expected_unit_refs: tuple[str, ...]
    consumed_unit_refs: tuple[str, ...]
    residuals: tuple[GroundingResidual, ...]
    required_slots: tuple[str, ...]
    missing_required_slots: tuple[str, ...]
    projected_slots: tuple[str, ...]
    slot_unit_refs: Mapping[str, tuple[str, ...]]
    complete: bool
    executable: bool
    weighted_coverage: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "expected_unit_refs": list(self.expected_unit_refs),
            "consumed_unit_refs": list(self.consumed_unit_refs),
            "residuals": [item.as_dict() for item in self.residuals],
            "required_slots": list(self.required_slots),
            "missing_required_slots": list(self.missing_required_slots),
            "projected_slots": list(self.projected_slots),
            "slot_unit_refs": {key: list(value) for key, value in sorted(self.slot_unit_refs.items())},
            "complete": self.complete,
            "executable": self.executable,
            "weighted_coverage": self.weighted_coverage,
        }


@dataclass(frozen=True)
class AtomicGraphMatch:
    match_ref: str
    schema_ref: str
    schema_family: str
    hypothesis_ref: str
    captures: Mapping[str, Any]
    slot_features: Mapping[str, Mapping[str, Any]]
    slot_unit_refs: Mapping[str, tuple[str, ...]]
    semantic_role_by_unit_ref: Mapping[str, str]
    projected: Mapping[str, ProjectedSlot]
    score: float
    coverage: GraphCoverage
    packet_template: Mapping[str, Any]
    diagnostics: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "match_ref": self.match_ref,
            "schema_ref": self.schema_ref,
            "schema_family": self.schema_family,
            "hypothesis_ref": self.hypothesis_ref,
            "captures": dict(self.captures),
            "slot_features": {key: dict(value) for key, value in self.slot_features.items()},
            "slot_unit_refs": {key: list(value) for key, value in self.slot_unit_refs.items()},
            "semantic_role_by_unit_ref": dict(self.semantic_role_by_unit_ref),
            "projected": {
                key: {
                    "capture": value.capture,
                    "features": dict(value.features),
                    "source": value.source,
                    "reason": value.reason,
                    "penalty": value.penalty,
                    "ports_provided": list(value.ports_provided),
                }
                for key, value in self.projected.items()
            },
            "score": self.score,
            "coverage": self.coverage.as_dict(),
            "diagnostics": dict(self.diagnostics),
        }


def _capture(units: Sequence[UnitView], mode: str) -> Any:
    if mode == "ref":
        return units[0].semantic_ref if units else None
    if mode == "refs":
        return [item.semantic_ref for item in units]
    if mode == "features":
        if len(units) == 1:
            return dict(units[0].features)
        return [dict(item.features) for item in units]
    text = " ".join(item.surface for item in units).strip()
    if mode == "literal:text":
        return {"literal": {"type": "text", "value": text}}
    if mode == "text":
        return text
    if mode == "units":
        return [item.as_dict() for item in units]
    return text


def _unit_matches(unit: UnitView, spec: Mapping[str, Any]) -> bool:
    kind = spec.get("kind")
    if kind and unit.kind != kind:
        return False
    kinds = set(spec.get("kinds", ()))
    if kinds and unit.kind not in kinds:
        return False
    anchor_kind = spec.get("anchor_kind")
    if anchor_kind and not (unit.kind == "anchor" and unit.atom_kind == anchor_kind):
        return False
    anchor_kinds = set(spec.get("anchor_kinds", ()))
    if anchor_kinds and not (unit.kind == "anchor" and unit.atom_kind in anchor_kinds):
        return False
    anchor_ref = spec.get("anchor_ref")
    if anchor_ref and unit.semantic_ref != anchor_ref:
        return False
    source_kind = spec.get("source_kind")
    if source_kind and unit.source_kind != source_kind:
        return False
    for path, expected in dict(spec.get("features", {})).items():
        if not value_matches(feature_path(unit.features, path), expected):
            return False
    for path in tuple(spec.get("absent_features", ())):
        if feature_path(unit.features, path) not in (None, False, "", (), [], {}):
            return False
    return True


def _residual_for(unit: UnitView, role_hypotheses: Iterable[str] = ()) -> GroundingResidual:
    features = dict(unit.features)
    grounded = bool(unit.kind == "anchor" and unit.semantic_ref)
    if grounded:
        residual_class = (
            "grounded_predicate_unassigned"
            if features.get("predicate") or features.get("property_ref")
            else "grounded_argument_unassigned"
        )
        grounding_status = "grounded"
    elif unit.kind == "unknown":
        residual_class = "unknown_form"
        grounding_status = "unknown"
    elif features.get("predicate") or features.get("property_ref") or features.get("copular"):
        residual_class = "known_predicate_unassigned"
        grounding_status = "lexically_known"
    else:
        residual_class = "known_form_unassigned"
        grounding_status = "lexically_known"
    return GroundingResidual(
        unit_ref=unit.unit_ref,
        surface=unit.surface,
        normalized=unit.normalized,
        kind=unit.kind,
        semantic_ref=unit.semantic_ref,
        atom_kind=unit.atom_kind,
        source_kind=unit.source_kind,
        grounding_status=grounding_status,
        residual_class=residual_class,
        role_hypotheses=tuple(sorted(set(map(str, role_hypotheses)))),
        features=features,
    )


class AtomicGraphMatcher:
    """Bounded, N-best semantic slot graph matcher.

    It evaluates every schema against every bounded grounding hypothesis.  Units
    are assigned to typed slots globally rather than consumed in surface order.
    Hard graph constraints determine legality; order preferences only influence
    score.  Reviewed projection rules may fill absent semantic slots without
    pretending that an omitted surface token was observed.
    """

    def __init__(
        self,
        schemas: Iterable[Mapping[str, Any]],
        *,
        max_matches: int = 32,
        max_candidates_per_slot: int = 48,
        state_budget: int = 12000,
        max_partial_matches: int = 8,
    ) -> None:
        self.schemas = tuple(dict(item) for item in schemas)
        self.max_matches = int(max_matches)
        self.max_candidates_per_slot = int(max_candidates_per_slot)
        self.state_budget = int(state_budget)
        self.max_partial_matches = int(max_partial_matches)
        for schema in self.schemas:
            self._validate_schema(schema)

    @staticmethod
    def _validate_schema(schema: Mapping[str, Any]) -> None:
        if not schema.get("ref") or not schema.get("family"):
            raise ValueError("graph schema requires ref and family")
        steps = tuple(schema.get("steps", ()))
        if not steps or len(steps) > 16:
            raise ValueError("graph schema requires 1..16 slots")
        slots = [str(item.get("slot") or "") for item in steps]
        if any(not item for item in slots) or len(slots) != len(set(slots)):
            raise ValueError("graph schema slots must be unique and non-empty")
        contract = dict(schema.get("graph_contract", {}))
        for rule in contract.get("projections", ()):
            if str(rule.get("slot")) not in slots:
                raise ValueError(f"projection targets unknown slot: {rule}")
            if rule.get("source") not in {"constant", "context"}:
                raise ValueError(f"unsupported projection source: {rule.get('source')}")
        for pref in contract.get("order_preferences", ()):
            if str(pref.get("before")) not in slots or str(pref.get("after")) not in slots:
                raise ValueError(f"order preference references unknown slot: {pref}")

    @staticmethod
    def _slot_specs(schema: Mapping[str, Any]) -> tuple[SlotSpec, ...]:
        output: list[SlotSpec] = []
        for raw in schema.get("steps", ()):
            step = dict(raw)
            match = {
                key: step[key]
                for key in (
                    "kind", "kinds", "anchor_kind", "anchor_kinds", "anchor_ref",
                    "source_kind", "features", "absent_features",
                )
                if key in step
            }
            output.append(
                SlotSpec(
                    slot=str(step["slot"]),
                    semantic_role=str(step.get("semantic_role") or step["slot"]),
                    capture=str(step.get("capture", "ref")),
                    optional=bool(step.get("optional", False)),
                    match=match,
                    span=bool(step.get("span", False)),
                    min_units=max(1, int(step.get("min_units", 1))),
                    max_units=max(1, int(step.get("max_units", 1))),
                    allowed_kinds=tuple(map(str, step.get("allowed_kinds", ()))),
                    ports_provided=tuple(map(str, step.get("ports_provided", ()))),
                    ports_required=tuple(map(str, step.get("ports_required", ()))),
                    weight=float(step.get("weight", 0.0)),
                )
            )
        return tuple(output)

    @staticmethod
    def _projections(schema: Mapping[str, Any]) -> tuple[ProjectionRule, ...]:
        return tuple(
            ProjectionRule(
                slot=str(item["slot"]),
                source=str(item["source"]),
                value=item.get("value"),
                context_path=item.get("context_path"),
                features=dict(item.get("features", {})),
                requires_slots=tuple(map(str, item.get("requires_slots", ()))),
                forbids_slots=tuple(map(str, item.get("forbids_slots", ()))),
                ports_provided=tuple(map(str, item.get("ports_provided", ()))),
                penalty=float(item.get("penalty", 0.25)),
                reason=str(item.get("reason", "reviewed_projection")),
            )
            for item in dict(schema.get("graph_contract", {})).get("projections", ())
        )

    @staticmethod
    def _order_preferences(schema: Mapping[str, Any]) -> tuple[OrderPreference, ...]:
        return tuple(
            OrderPreference(
                before=str(item["before"]),
                after=str(item["after"]),
                weight=float(item.get("weight", 0.08)),
            )
            for item in dict(schema.get("graph_contract", {})).get("order_preferences", ())
        )

    @staticmethod
    def _hard_constraints(schema: Mapping[str, Any]) -> tuple[HardConstraint, ...]:
        return tuple(
            HardConstraint(
                kind=str(item["kind"]),
                slots=tuple(map(str, item.get("slots", ()))),
                max_distance=(int(item["max_distance"]) if item.get("max_distance") is not None else None),
            )
            for item in dict(schema.get("graph_contract", {})).get("hard_constraints", ())
        )

    def _slot_candidates(self, units: Sequence[UnitView], spec: SlotSpec) -> tuple[SlotCandidate, ...]:
        output: list[SlotCandidate] = []
        if spec.span:
            max_len = min(spec.max_units, len(units))
            for start in range(len(units)):
                for length in range(spec.min_units, max_len + 1):
                    selected = tuple(units[start : start + length])
                    if len(selected) != length:
                        continue
                    if spec.allowed_kinds and any(item.kind not in spec.allowed_kinds for item in selected):
                        continue
                    if spec.match and any(not _unit_matches(item, spec.match) for item in selected):
                        continue
                    features: dict[str, Any] = {}
                    for item in selected:
                        features.update(item.features)
                    output.append(
                        SlotCandidate(
                            slot=spec.slot,
                            units=selected,
                            capture=_capture(selected, spec.capture),
                            features=features,
                            score=sum(item.score for item in selected) + spec.weight - 0.01 * (length - spec.min_units),
                        )
                    )
        else:
            for unit in units:
                if not _unit_matches(unit, spec.match):
                    continue
                output.append(
                    SlotCandidate(
                        slot=spec.slot,
                        units=(unit,),
                        capture=_capture((unit,), spec.capture),
                        features=dict(unit.features),
                        score=unit.score + spec.weight + (0.08 if unit.kind == "anchor" and unit.semantic_ref else 0.0),
                    )
                )
        output.sort(key=lambda item: (-item.score, item.start, item.end, item.unit_refs))
        return tuple(output[: self.max_candidates_per_slot])

    @staticmethod
    def _read_context(context: Mapping[str, Any], path: str | None) -> Any:
        if not path:
            return None
        value: Any = context
        for part in str(path).split("."):
            if not isinstance(value, Mapping) or part not in value:
                return None
            value = value[part]
        return value

    def _apply_projections(
        self,
        specs: Mapping[str, SlotSpec],
        assigned: Mapping[str, SlotCandidate],
        rules: Sequence[ProjectionRule],
        context: Mapping[str, Any],
    ) -> dict[str, ProjectedSlot]:
        projected: dict[str, ProjectedSlot] = {}
        changed = True
        while changed:
            changed = False
            available = set(assigned) | set(projected)
            for rule in rules:
                if rule.slot in available:
                    continue
                if not set(rule.requires_slots).issubset(available):
                    continue
                if set(rule.forbids_slots).intersection(available):
                    continue
                if rule.source == "context":
                    capture = self._read_context(context, rule.context_path)
                else:
                    capture = rule.value
                if capture is None:
                    continue
                projected[rule.slot] = ProjectedSlot(
                    slot=rule.slot,
                    capture=capture,
                    features=dict(rule.features),
                    source=rule.source,
                    reason=rule.reason,
                    penalty=rule.penalty,
                    ports_provided=rule.ports_provided,
                )
                changed = True
        return projected

    @staticmethod
    def _positions(assigned: Mapping[str, SlotCandidate]) -> dict[str, tuple[int, int]]:
        return {slot: (candidate.start, candidate.end) for slot, candidate in assigned.items()}

    def _hard_constraints_ok(
        self,
        assigned: Mapping[str, SlotCandidate],
        constraints: Sequence[HardConstraint],
    ) -> bool:
        positions = self._positions(assigned)
        for constraint in constraints:
            present = [slot for slot in constraint.slots if slot in positions]
            if len(present) < len(constraint.slots):
                continue
            if constraint.kind == "adjacent":
                ordered = sorted((positions[slot][0], positions[slot][1]) for slot in constraint.slots)
                if any(left[1] != right[0] for left, right in zip(ordered, ordered[1:])):
                    return False
            elif constraint.kind == "max_distance":
                starts = [positions[slot][0] for slot in constraint.slots]
                ends = [positions[slot][1] for slot in constraint.slots]
                distance = max(ends) - min(starts)
                if constraint.max_distance is not None and distance > constraint.max_distance:
                    return False
            elif constraint.kind == "same_anchor_ref":
                refs = {
                    unit.semantic_ref
                    for slot in constraint.slots
                    for unit in assigned[slot].units
                    if unit.semantic_ref
                }
                if len(refs) > 1:
                    return False
            else:
                raise ValueError(f"unsupported hard graph constraint: {constraint.kind}")
        return True

    @staticmethod
    def _port_state(
        specs: Mapping[str, SlotSpec],
        assigned: Mapping[str, SlotCandidate],
        projected: Mapping[str, ProjectedSlot],
    ) -> tuple[set[str], set[str]]:
        provided: set[str] = set()
        required: set[str] = set()
        for slot in set(assigned) | set(projected):
            spec = specs[slot]
            provided.update(spec.ports_provided)
            required.update(spec.ports_required)
        for item in projected.values():
            provided.update(item.ports_provided)
        return provided, required

    @staticmethod
    def _order_score(
        assigned: Mapping[str, SlotCandidate],
        preferences: Sequence[OrderPreference],
    ) -> tuple[float, list[dict[str, Any]]]:
        score = 0.0
        evidence: list[dict[str, Any]] = []
        for preference in preferences:
            left = assigned.get(preference.before)
            right = assigned.get(preference.after)
            if left is None or right is None:
                continue
            satisfied = left.end <= right.start
            delta = preference.weight if satisfied else -preference.weight
            score += delta
            evidence.append(
                {
                    "before": preference.before,
                    "after": preference.after,
                    "satisfied": satisfied,
                    "weight": preference.weight,
                    "delta": delta,
                }
            )
        return score, evidence

    @staticmethod
    def _coverage(
        units: Sequence[UnitView],
        specs: Mapping[str, SlotSpec],
        assigned: Mapping[str, SlotCandidate],
        projected: Mapping[str, ProjectedSlot],
    ) -> GraphCoverage:
        consumed = tuple(
            dict.fromkeys(
                ref
                for candidate in assigned.values()
                for ref in candidate.unit_refs
            )
        )
        consumed_set = set(consumed)
        slot_unit_refs = {slot: candidate.unit_refs for slot, candidate in assigned.items()}
        role_hypotheses_by_ref: dict[str, set[str]] = {}
        for slot, candidate in assigned.items():
            role = specs[slot].semantic_role
            for ref in candidate.unit_refs:
                role_hypotheses_by_ref.setdefault(ref, set()).add(role)
        residuals = tuple(
            _residual_for(unit, role_hypotheses_by_ref.get(unit.unit_ref, ()))
            for unit in units
            if unit.unit_ref not in consumed_set
            and unit.kind not in {"discourse"}
            and not (unit.kind == "punctuation" and unit.features.get("boundary_only"))
        )
        required = tuple(sorted(slot for slot, spec in specs.items() if not spec.optional))
        available = set(assigned) | set(projected)
        missing = tuple(slot for slot in required if slot not in available)
        expected = tuple(item.unit_ref for item in units)
        weights = {
            item.unit_ref: (
                2.0
                if item.kind == "anchor"
                or item.features.get("predicate")
                or item.features.get("property_ref")
                or item.features.get("discourse_force")
                else 0.5
            )
            for item in units
        }
        total = sum(weights.values()) or 1.0
        weighted = sum(weights.get(ref, 0.0) for ref in consumed_set) / total
        critical_residuals = tuple(
            item
            for item in residuals
            if item.residual_class not in {"known_form_unassigned"}
        )
        complete = not missing and not critical_residuals
        return GraphCoverage(
            expected_unit_refs=expected,
            consumed_unit_refs=consumed,
            residuals=residuals,
            required_slots=required,
            missing_required_slots=missing,
            projected_slots=tuple(sorted(projected)),
            slot_unit_refs=slot_unit_refs,
            complete=complete,
            executable=complete,
            weighted_coverage=max(0.0, min(1.0, weighted)),
        )

    def _match_schema(
        self,
        hypothesis: Any,
        schema: Mapping[str, Any],
        context: Mapping[str, Any],
    ) -> tuple[AtomicGraphMatch, ...]:
        units = tuple(UnitView.from_object(item) for item in getattr(hypothesis, "units", ()))
        specs_tuple = self._slot_specs(schema)
        specs = {item.slot: item for item in specs_tuple}
        candidates = {item.slot: self._slot_candidates(units, item) for item in specs_tuple}
        projections = self._projections(schema)
        preferences = self._order_preferences(schema)
        hard_constraints = self._hard_constraints(schema)

        ordered_slots = sorted(
            specs,
            key=lambda slot: (
                specs[slot].optional,
                len(candidates[slot]) if candidates[slot] else 10**9,
                slot,
            ),
        )
        states = 0
        raw_results: list[tuple[dict[str, SlotCandidate], float]] = []
        best_partial: list[tuple[int, float, dict[str, SlotCandidate]]] = []

        def remember_partial(assigned: dict[str, SlotCandidate], score: float) -> None:
            required_assigned = sum(1 for slot, spec in specs.items() if not spec.optional and slot in assigned)
            best_partial.append((required_assigned, score, dict(assigned)))
            best_partial.sort(key=lambda item: (-item[0], -item[1], _canonical(sorted(item[2]))))
            del best_partial[self.max_partial_matches :]

        def walk(index: int, assigned: dict[str, SlotCandidate], used: set[str], score: float) -> None:
            nonlocal states
            states += 1
            if states > self.state_budget:
                return
            remember_partial(assigned, score)
            if index >= len(ordered_slots):
                raw_results.append((dict(assigned), score))
                return
            slot = ordered_slots[index]
            spec = specs[slot]
            viable = [
                item
                for item in candidates[slot]
                if not used.intersection(item.unit_refs)
            ]
            if spec.optional:
                walk(index + 1, assigned, used, score - 0.02)
            for item in viable:
                assigned[slot] = item
                if self._hard_constraints_ok(assigned, hard_constraints):
                    walk(index + 1, assigned, used | set(item.unit_refs), score + item.score)
                assigned.pop(slot, None)
            if not viable and not spec.optional:
                # Preserve the partial graph; reviewed projection rules are applied
                # after all real evidence assignments have been explored.
                walk(index + 1, assigned, used, score - 0.12)

        walk(0, {}, set(), 0.0)
        if not raw_results:
            raw_results = [(item[2], item[1]) for item in best_partial]

        matches: list[AtomicGraphMatch] = []
        seen: set[str] = set()
        for assigned, base_score in raw_results:
            projected = self._apply_projections(specs, assigned, projections, context)
            provided, required_ports = self._port_state(specs, assigned, projected)
            missing_ports = tuple(sorted(required_ports - provided))
            if missing_ports:
                continue
            coverage = self._coverage(units, specs, assigned, projected)
            captures: dict[str, Any] = {
                slot: candidate.capture for slot, candidate in assigned.items()
            }
            captures.update({slot: item.capture for slot, item in projected.items()})
            slot_features: dict[str, Mapping[str, Any]] = {
                slot: dict(candidate.features) for slot, candidate in assigned.items()
            }
            slot_features.update({slot: dict(item.features) for slot, item in projected.items()})
            role_by_unit: dict[str, str] = {}
            for slot, candidate in assigned.items():
                for ref in candidate.unit_refs:
                    role_by_unit[ref] = specs[slot].semantic_role
            order_score, order_evidence = self._order_score(assigned, preferences)
            projection_penalty = sum(item.penalty for item in projected.values())
            score = (
                float(getattr(hypothesis, "score", 0.0))
                + float(schema.get("weight", 1.0))
                + base_score
                + order_score
                + 0.5 * coverage.weighted_coverage
                - projection_penalty
                - 0.2 * len(coverage.missing_required_slots)
            )
            signature = _canonical(
                {
                    "schema": schema["ref"],
                    "hypothesis": getattr(hypothesis, "hypothesis_ref", ""),
                    "captures": captures,
                    "slots": {key: list(value.unit_refs) for key, value in assigned.items()},
                    "projected": sorted(projected),
                }
            )
            if signature in seen:
                continue
            seen.add(signature)
            match_ref = _stable("atomic-graph-match", signature)
            matches.append(
                AtomicGraphMatch(
                    match_ref=match_ref,
                    schema_ref=str(schema["ref"]),
                    schema_family=str(schema.get("family") or schema["ref"]),
                    hypothesis_ref=str(getattr(hypothesis, "hypothesis_ref", "")),
                    captures=captures,
                    slot_features=slot_features,
                    slot_unit_refs={slot: candidate.unit_refs for slot, candidate in assigned.items()},
                    semantic_role_by_unit_ref=role_by_unit,
                    projected=projected,
                    score=score,
                    coverage=coverage,
                    packet_template=dict(schema["packet"]),
                    diagnostics={
                        "search_states": states,
                        "state_budget": self.state_budget,
                        "order_evidence": order_evidence,
                        "ports_provided": sorted(provided),
                        "ports_required": sorted(required_ports),
                        "missing_ports": list(missing_ports),
                        "projection_penalty": projection_penalty,
                    },
                )
            )
        matches.sort(
            key=lambda item: (
                not item.coverage.executable,
                len(item.coverage.missing_required_slots),
                -item.coverage.weighted_coverage,
                -item.score,
                item.match_ref,
            )
        )
        return tuple(matches[: self.max_matches])

    def matches(self, lattice: Any, *, context: Mapping[str, Any] | None = None) -> tuple[AtomicGraphMatch, ...]:
        context = dict(context or {})
        output: list[AtomicGraphMatch] = []
        for hypothesis in tuple(getattr(lattice, "grounding_hypotheses", ())):
            for schema in self.schemas:
                output.extend(self._match_schema(hypothesis, schema, context))
        unique: dict[str, AtomicGraphMatch] = {}
        for item in output:
            prior = unique.get(item.match_ref)
            if prior is None or item.score > prior.score:
                unique[item.match_ref] = item
        ordered = sorted(
            unique.values(),
            key=lambda item: (
                not item.coverage.executable,
                len(item.coverage.missing_required_slots),
                -item.coverage.weighted_coverage,
                -item.score,
                item.match_ref,
            ),
        )
        return tuple(ordered[: self.max_matches])


def deterministic_participant_reference(
    *,
    lexical_features: Mapping[str, Any],
    semantic_candidates: Sequence[tuple[str, float, Mapping[str, Any]]],
) -> tuple[str, float, Mapping[str, Any]] | None:
    """Return a unique participant-relative grounding, otherwise ``None``.

    This helper is intended for ``FormProcessor.hypotheses``.  When the active
    participant frame has resolved a first/second-person form to exactly one
    participant, the raw unresolved lexical alternative must not survive as a
    competing hypothesis.
    """
    if not lexical_features.get("participant_role"):
        return None
    by_ref: dict[str, tuple[str, float, Mapping[str, Any]]] = {}
    for ref, weight, features in semantic_candidates:
        by_ref[str(ref)] = (str(ref), float(weight), dict(features))
    if len(by_ref) != 1:
        return None
    return next(iter(by_ref.values()))
