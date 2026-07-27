"""Fail-closed semantic coverage ABI v6.

V6 preserves grounding provenance and distinguishes observed-unit assignments
from reviewed virtual projections.  A projected slot can satisfy a semantic
role, but it never masquerades as an observed or consumed form unit.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence
import hashlib
import json
import math

try:
    from cemm.model import canonical, stable
except Exception:  # standalone verification
    def canonical(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)

    def stable(namespace: str, *parts: Any) -> str:
        return f"{namespace}:" + hashlib.sha256(canonical(parts).encode()).hexdigest()[:24]


COVERAGE_ABI_VERSION = 6

CRITICAL_CLASSES = frozenset({
    "force_critical",
    "predicate_critical",
    "argument_critical",
    "polarity_critical",
    "scope_critical",
    "grounded_argument_unassigned",
    "grounded_predicate_unassigned",
    "known_predicate_unassigned",
    "unknown_form",
})
NONCRITICAL_CLASSES = frozenset({
    "discourse_noncritical",
    "punctuation_noncritical",
    "emphasis_noncritical",
    "modifier_noncritical",
    "known_form_unassigned",
})


class CoverageIntegrityError(ValueError):
    pass


def _sha256(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _tuple_strings(value: Iterable[Any]) -> tuple[str, ...]:
    return tuple(str(item) for item in value)


@dataclass(frozen=True)
class ResidualSpan:
    span_ref: str
    unit_refs: tuple[str, ...]
    surface: str
    normalized: str
    token_start: int
    token_end: int
    char_start: int
    char_end: int
    residual_class: str
    role_hypotheses: tuple[str, ...] = ()
    features: Mapping[str, Any] = field(default_factory=dict)
    semantic_ref: str | None = None
    atom_kind: str | None = None
    source_kind: str | None = None
    grounding_status: str = "unknown"
    grounding_proof_refs: tuple[str, ...] = ()

    def identity_body(self) -> dict[str, Any]:
        return {
            "unit_refs": list(self.unit_refs),
            "surface": self.surface,
            "normalized": self.normalized,
            "token_start": self.token_start,
            "token_end": self.token_end,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "residual_class": self.residual_class,
            "role_hypotheses": list(self.role_hypotheses),
            "features": dict(self.features),
            "semantic_ref": self.semantic_ref,
            "atom_kind": self.atom_kind,
            "source_kind": self.source_kind,
            "grounding_status": self.grounding_status,
            "grounding_proof_refs": list(self.grounding_proof_refs),
        }

    def __post_init__(self) -> None:
        if not self.unit_refs:
            raise CoverageIntegrityError("residual requires unit refs")
        if self.residual_class not in CRITICAL_CLASSES | NONCRITICAL_CLASSES:
            raise CoverageIntegrityError(f"unknown residual class {self.residual_class!r}")
        if self.token_start < 0 or self.token_end <= self.token_start:
            raise CoverageIntegrityError("invalid residual token bounds")
        if self.char_start < 0 or self.char_end < self.char_start:
            raise CoverageIntegrityError("invalid residual character bounds")
        if self.grounding_status == "grounded" and not self.semantic_ref:
            raise CoverageIntegrityError("grounded residual lacks semantic_ref")
        expected = stable("residual-span-v6", self.identity_body())
        if self.span_ref != expected:
            raise CoverageIntegrityError(f"residual span_ref mismatch: {self.span_ref} != {expected}")

    @property
    def critical(self) -> bool:
        return self.residual_class in CRITICAL_CLASSES

    def as_dict(self) -> dict[str, Any]:
        return {"span_ref": self.span_ref, **self.identity_body(), "critical": self.critical}


@dataclass(frozen=True)
class InterpretationCoverage:
    coverage_ref: str
    seed_hash: str
    body_hash: str
    schema_ref: str
    hypothesis_ref: str
    match_seed_ref: str
    diagnostic_only: bool
    expected_unit_refs: tuple[str, ...]
    consumed_unit_refs: tuple[str, ...]
    residuals: tuple[ResidualSpan, ...]
    required_semantic_roles: tuple[str, ...]
    semantic_role_unit_refs: Mapping[str, tuple[str, ...]]
    unit_weights: Mapping[str, float]
    weighted_coverage: float
    complete: bool
    critical_residual_refs: tuple[str, ...]
    noncritical_residual_refs: tuple[str, ...]
    missing_semantic_roles: tuple[str, ...]
    invariants: Mapping[str, bool]
    silent_unit_refs: tuple[str, ...] = ()
    extraneous_consumed_unit_refs: tuple[str, ...] = ()
    duplicate_input_unit_refs: tuple[str, ...] = ()
    duplicate_consumed_unit_refs: tuple[str, ...] = ()
    duplicate_residual_unit_refs: tuple[str, ...] = ()
    consumed_residual_overlap_refs: tuple[str, ...] = ()
    semantic_role_extraneous_unit_refs: tuple[str, ...] = ()
    semantic_role_duplicate_unit_refs: tuple[str, ...] = ()
    unassigned_consumed_unit_refs: tuple[str, ...] = ()
    required_semantic_slots: tuple[str, ...] = ()
    slot_unit_refs: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    projected_semantic_roles: Mapping[str, tuple[Mapping[str, Any], ...]] = field(default_factory=dict)
    projected_slots: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    missing_semantic_slots: tuple[str, ...] = ()
    abi_version: int = COVERAGE_ABI_VERSION

    @classmethod
    def unresolved(
        cls,
        *,
        seed: Any = "missing",
        schema_ref: str = "diagnostic:unresolved",
        hypothesis_ref: str = "diagnostic:none",
        match_seed_ref: str | None = None,
    ) -> "InterpretationCoverage":
        return CoveragePolicy.build(
            (),
            (),
            required_semantic_roles=("coverage_receipt",),
            required_semantic_slots=("coverage_receipt",),
            schema_ref=schema_ref,
            hypothesis_ref=hypothesis_ref,
            match_seed_ref=match_seed_ref or stable("coverage-diagnostic-match-seed-v6", schema_ref, hypothesis_ref, seed),
            diagnostic_only=True,
            seed=seed,
        )

    @property
    def critical_residuals(self) -> tuple[ResidualSpan, ...]:
        refs = set(self.critical_residual_refs)
        return tuple(item for item in self.residuals if item.span_ref in refs)

    @property
    def noncritical_residuals(self) -> tuple[ResidualSpan, ...]:
        refs = set(self.noncritical_residual_refs)
        return tuple(item for item in self.residuals if item.span_ref in refs)

    @property
    def executable(self) -> bool:
        return (
            not self.diagnostic_only
            and self.complete
            and bool(self.expected_unit_refs)
            and bool(self.invariants)
            and all(self.invariants.values())
        )

    def assert_provenance(self, *, schema_ref: str, hypothesis_ref: str, match_seed_ref: str) -> None:
        expected = (str(schema_ref), str(hypothesis_ref), str(match_seed_ref))
        actual = (self.schema_ref, self.hypothesis_ref, self.match_seed_ref)
        if actual != expected:
            raise CoverageIntegrityError(f"coverage provenance mismatch: {actual!r} != {expected!r}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "coverage_ref": self.coverage_ref,
            "seed_hash": self.seed_hash,
            "body_hash": self.body_hash,
            "schema_ref": self.schema_ref,
            "hypothesis_ref": self.hypothesis_ref,
            "match_seed_ref": self.match_seed_ref,
            "diagnostic_only": self.diagnostic_only,
            "expected_unit_refs": list(self.expected_unit_refs),
            "consumed_unit_refs": list(self.consumed_unit_refs),
            "residuals": [item.as_dict() for item in self.residuals],
            "required_semantic_roles": list(self.required_semantic_roles),
            "semantic_role_unit_refs": {key: list(value) for key, value in sorted(self.semantic_role_unit_refs.items())},
            "required_semantic_slots": list(self.required_semantic_slots),
            "slot_unit_refs": {key: list(value) for key, value in sorted(self.slot_unit_refs.items())},
            "projected_semantic_roles": {
                key: [dict(item) for item in values]
                for key, values in sorted(self.projected_semantic_roles.items())
            },
            "projected_slots": {key: dict(value) for key, value in sorted(self.projected_slots.items())},
            "missing_semantic_slots": list(self.missing_semantic_slots),
            "unit_weights": {key: float(value) for key, value in sorted(self.unit_weights.items())},
            "weighted_coverage": self.weighted_coverage,
            "complete": self.complete,
            "critical_residual_refs": list(self.critical_residual_refs),
            "noncritical_residual_refs": list(self.noncritical_residual_refs),
            "missing_semantic_roles": list(self.missing_semantic_roles),
            "invariants": dict(self.invariants),
            "silent_unit_refs": list(self.silent_unit_refs),
            "extraneous_consumed_unit_refs": list(self.extraneous_consumed_unit_refs),
            "duplicate_input_unit_refs": list(self.duplicate_input_unit_refs),
            "duplicate_consumed_unit_refs": list(self.duplicate_consumed_unit_refs),
            "duplicate_residual_unit_refs": list(self.duplicate_residual_unit_refs),
            "consumed_residual_overlap_refs": list(self.consumed_residual_overlap_refs),
            "semantic_role_extraneous_unit_refs": list(self.semantic_role_extraneous_unit_refs),
            "semantic_role_duplicate_unit_refs": list(self.semantic_role_duplicate_unit_refs),
            "unassigned_consumed_unit_refs": list(self.unassigned_consumed_unit_refs),
        }


class CoveragePolicy:
    _FORCE_FEATURES = {"interrogative", "directive", "question_domain", "discourse_force", "force_evidence"}
    _PREDICATE_FEATURES = {
        "predicate", "lemma", "semantic_port", "relation_port", "event_port",
        "state_port", "property_marker", "property_ref", "property_kind", "copular", "auxiliary",
    }
    _POLARITY_FEATURES = {"negation", "polarity"}
    _SCOPE_FEATURES = {"quantifier", "modal", "scope_operator", "conditional"}

    @staticmethod
    def _feature_truth(features: Mapping[str, Any], names: set[str]) -> bool:
        return any(features.get(name) not in (None, False, "", (), [], {}) for name in names)

    @classmethod
    def classify_unit(
        cls,
        unit: Any,
        *,
        assigned_role: str | None = None,
        schema_hints: Mapping[str, Any] | None = None,
    ) -> tuple[str, tuple[str, ...]]:
        features = dict(getattr(unit, "features", {}) or {})
        role = assigned_role or dict(schema_hints or {}).get("role") or features.get("syntactic_role")
        kind = getattr(unit, "kind", None)
        semantic_ref = getattr(unit, "semantic_ref", None)

        # Punctuation marked as boundary-only by the language pack is
        # non-critical evidence regardless of its force features.  The force
        # evidence is still available to the graph matcher via the slot's
        # feature constraints; it simply does not create a critical residual
        # when the punctuation is not consumed by a slot.
        if kind == "punctuation" and features.get("boundary_only"):
            return "punctuation_noncritical", ("boundary",)
        if cls._feature_truth(features, cls._FORCE_FEATURES):
            return "force_critical", ("force",)
        if cls._feature_truth(features, cls._POLARITY_FEATURES):
            return "polarity_critical", ("polarity",)
        if cls._feature_truth(features, cls._SCOPE_FEATURES):
            return "scope_critical", ("scope",)
        if kind == "punctuation":
            return "punctuation_noncritical", ("boundary",)
        if kind == "discourse" or features.get("discourse_marker"):
            return "discourse_noncritical", ("discourse",)
        if features.get("emphasis") or features.get("focus_only"):
            return "emphasis_noncritical", ("emphasis",)
        if kind == "anchor" and semantic_ref:
            if role in {"predicate", "predicate_head", "relation", "event_type", "state_dimension", "binder"}:
                return "grounded_predicate_unassigned", (str(role),)
            return "grounded_argument_unassigned", (str(role or "referent"),)
        if role in {"subject", "object", "target", "actor", "patient", "theme", "recipient", "referent", "argument", "value"}:
            return "argument_critical", (str(role),)
        if role in {"predicate", "predicate_head", "relation", "event_type", "state_dimension", "binder"}:
            return "predicate_critical", (str(role),)
        if cls._feature_truth(features, cls._PREDICATE_FEATURES):
            return "known_predicate_unassigned", ("predicate_head_or_binder",)
        if kind == "unknown":
            return "unknown_form", ("predicate_or_argument",)
        if features.get("modifier") or role in {"modifier", "adjunct"}:
            return "modifier_noncritical", (str(role or "modifier"),)
        if kind == "function":
            return "known_form_unassigned", ("function",)
        return "known_form_unassigned", ("unassigned",)

    @classmethod
    def build(
        cls,
        units: Sequence[Any],
        consumed_unit_refs: Iterable[str],
        *,
        role_by_unit_ref: Mapping[str, str] | None = None,
        slot_by_unit_ref: Mapping[str, str] | None = None,
        required_semantic_roles: Iterable[str] = (),
        required_semantic_slots: Iterable[str] = (),
        projected_semantic_roles: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
        projected_slots: Mapping[str, Mapping[str, Any]] | None = None,
        schema_hints_by_unit_ref: Mapping[str, Mapping[str, Any]] | None = None,
        schema_ref: str | None = None,
        hypothesis_ref: str | None = None,
        match_seed_ref: str | None = None,
        diagnostic_only: bool = False,
        seed: Any = None,
    ) -> InterpretationCoverage:
        expected = _tuple_strings(getattr(unit, "unit_ref") for unit in units)
        consumed = _tuple_strings(consumed_unit_refs)
        roles = {str(k): str(v) for k, v in dict(role_by_unit_ref or {}).items()}
        slots = {str(k): str(v) for k, v in dict(slot_by_unit_ref or {}).items()}
        required_roles = tuple(sorted(set(map(str, required_semantic_roles))))
        required_slots = tuple(sorted(set(map(str, required_semantic_slots))))
        projected_roles = {
            str(role): tuple(dict(item) for item in values)
            for role, values in dict(projected_semantic_roles or {}).items()
        }
        projected_slot_map = {str(slot): dict(value) for slot, value in dict(projected_slots or {}).items()}
        hints = dict(schema_hints_by_unit_ref or {})
        schema = str(schema_ref or ("diagnostic:coverage" if diagnostic_only else "coverage:standalone"))
        hypothesis = str(hypothesis_ref or stable("coverage-hypothesis-v6", expected, consumed))
        match_seed = str(match_seed_ref or stable("coverage-match-seed-v6", schema, hypothesis, expected, consumed, roles, slots, projected_roles, projected_slot_map))
        if diagnostic_only and expected:
            raise CoverageIntegrityError("diagnostic coverage cannot contain observed units")
        if not diagnostic_only and not expected:
            raise CoverageIntegrityError("non-diagnostic coverage requires observed units")

        consumed_set = set(consumed)
        residuals: list[ResidualSpan] = []
        unit_weights: dict[str, float] = {}
        for unit in units:
            ref = str(getattr(unit, "unit_ref"))
            unit_class, _ = cls.classify_unit(unit, assigned_role=roles.get(ref), schema_hints=hints.get(ref))
            unit_weights[ref] = 2.0 if unit_class in CRITICAL_CLASSES else 0.5
            if ref in consumed_set:
                continue
            residual_class, role_hypotheses = cls.classify_unit(unit, assigned_role=roles.get(ref), schema_hints=hints.get(ref))
            semantic_ref = getattr(unit, "semantic_ref", None)
            source_kind = getattr(unit, "source_kind", None)
            grounding_status = "grounded" if getattr(unit, "kind", None) == "anchor" and semantic_ref else ("unknown" if getattr(unit, "kind", None) == "unknown" else "lexically_known")
            proof_refs = tuple(
                str(item)
                for item in (
                    getattr(unit, "grounding_proof_refs", ())
                    or ([getattr(unit, "unit_ref")] if grounding_status == "grounded" else ())
                )
            )
            body = {
                "unit_refs": [ref],
                "surface": str(getattr(unit, "surface", "")),
                "normalized": str(getattr(unit, "normalized", "")),
                "token_start": int(getattr(unit, "token_start", -1)),
                "token_end": int(getattr(unit, "token_end", -1)),
                "char_start": int(getattr(unit, "char_start", -1)),
                "char_end": int(getattr(unit, "char_end", -1)),
                "residual_class": residual_class,
                "role_hypotheses": list(role_hypotheses),
                "features": dict(getattr(unit, "features", {}) or {}),
                "semantic_ref": semantic_ref,
                "atom_kind": getattr(unit, "atom_kind", None),
                "source_kind": source_kind,
                "grounding_status": grounding_status,
                "grounding_proof_refs": list(proof_refs),
            }
            residuals.append(ResidualSpan(
                span_ref=stable("residual-span-v6", body),
                unit_refs=(ref,),
                surface=body["surface"],
                normalized=body["normalized"],
                token_start=body["token_start"],
                token_end=body["token_end"],
                char_start=body["char_start"],
                char_end=body["char_end"],
                residual_class=residual_class,
                role_hypotheses=tuple(role_hypotheses),
                features=body["features"],
                semantic_ref=semantic_ref,
                atom_kind=body["atom_kind"],
                source_kind=source_kind,
                grounding_status=grounding_status,
                grounding_proof_refs=proof_refs,
            ))

        derived = _derive(
            expected=expected,
            consumed=consumed,
            residuals=tuple(residuals),
            required_roles=required_roles,
            required_slots=required_slots,
            raw_roles=roles,
            raw_slots=slots,
            projected_roles=projected_roles,
            projected_slots=projected_slot_map,
            unit_weights=unit_weights,
            diagnostic_only=diagnostic_only,
        )
        body = _body(
            schema_ref=schema,
            hypothesis_ref=hypothesis,
            match_seed_ref=match_seed,
            diagnostic_only=diagnostic_only,
            expected=expected,
            consumed=consumed,
            residuals=tuple(residuals),
            required_roles=required_roles,
            role_refs=derived["role_refs"],
            required_slots=required_slots,
            slot_refs=derived["slot_refs"],
            projected_roles=projected_roles,
            projected_slots=projected_slot_map,
            unit_weights=unit_weights,
            **derived["body_fields"],
        )
        seed_hash = _sha256(("coverage-seed-v6", schema, hypothesis, match_seed, seed))
        body_hash = _sha256(body)
        return InterpretationCoverage(
            coverage_ref=stable("interpretation-coverage-v6", seed_hash, body_hash),
            seed_hash=seed_hash,
            body_hash=body_hash,
            schema_ref=schema,
            hypothesis_ref=hypothesis,
            match_seed_ref=match_seed,
            diagnostic_only=diagnostic_only,
            expected_unit_refs=expected,
            consumed_unit_refs=consumed,
            residuals=tuple(residuals),
            required_semantic_roles=required_roles,
            semantic_role_unit_refs=derived["role_refs"],
            required_semantic_slots=required_slots,
            slot_unit_refs=derived["slot_refs"],
            projected_semantic_roles=projected_roles,
            projected_slots=projected_slot_map,
            unit_weights=unit_weights,
            **derived["model_fields"],
        )


def _derive(
    *,
    expected: tuple[str, ...],
    consumed: tuple[str, ...],
    residuals: tuple[ResidualSpan, ...],
    required_roles: tuple[str, ...],
    required_slots: tuple[str, ...],
    raw_roles: Mapping[str, str],
    raw_slots: Mapping[str, str],
    projected_roles: Mapping[str, tuple[Mapping[str, Any], ...]],
    projected_slots: Mapping[str, Mapping[str, Any]],
    unit_weights: Mapping[str, float],
    diagnostic_only: bool,
) -> dict[str, Any]:
    expected_counts = Counter(expected)
    consumed_counts = Counter(consumed)
    residual_refs = tuple(ref for item in residuals for ref in item.unit_refs)
    residual_counts = Counter(residual_refs)
    expected_set, consumed_set, residual_set = set(expected), set(consumed), set(residual_refs)
    duplicate_input = tuple(sorted(k for k, v in expected_counts.items() if v > 1))
    duplicate_consumed = tuple(sorted(k for k, v in consumed_counts.items() if v > 1))
    duplicate_residual = tuple(sorted(k for k, v in residual_counts.items() if v > 1))
    overlap = tuple(sorted(consumed_set & residual_set))
    silent = tuple(sorted(expected_set - consumed_set - residual_set))
    extraneous = tuple(sorted((consumed_set | residual_set) - expected_set))

    role_extraneous = tuple(sorted(set(raw_roles) - consumed_set))
    grouped_roles: dict[str, list[str]] = defaultdict(list)
    grouped_slots: dict[str, list[str]] = defaultdict(list)
    for ref in consumed:
        if raw_roles.get(ref):
            grouped_roles[raw_roles[ref]].append(ref)
        if raw_slots.get(ref):
            grouped_slots[raw_slots[ref]].append(ref)
    role_refs = {key: tuple(value) for key, value in sorted(grouped_roles.items())}
    slot_refs = {key: tuple(value) for key, value in sorted(grouped_slots.items())}
    flattened_roles = tuple(ref for refs in role_refs.values() for ref in refs)
    role_duplicate = tuple(sorted(k for k, v in Counter(flattened_roles).items() if v > 1))
    unassigned = tuple(sorted(consumed_set - set(flattened_roles)))
    missing_roles = tuple(role for role in required_roles if not role_refs.get(role) and not projected_roles.get(role))
    missing_slots = tuple(slot for slot in required_slots if not slot_refs.get(slot) and slot not in projected_slots)

    if set(unit_weights) != expected_set:
        raise CoverageIntegrityError("coverage unit weights do not match expected units")
    total = sum(float(value) for value in unit_weights.values())
    weighted = 0.0 if diagnostic_only else (1.0 if total <= 0 else sum(float(unit_weights.get(ref, 0.0)) for ref in consumed_set) / total)
    weighted = max(0.0, min(1.0, weighted))
    critical = tuple(item.span_ref for item in residuals if item.critical)
    noncritical = tuple(item.span_ref for item in residuals if not item.critical)
    invariants = {
        "all_units_accounted_for": not silent and not extraneous,
        "unique_input_unit_refs": not duplicate_input,
        "unique_consumed_unit_refs": not duplicate_consumed,
        "unique_residual_unit_refs": not duplicate_residual,
        "consumed_residual_disjoint": not overlap,
        "semantic_roles_satisfied": not missing_roles,
        "semantic_slots_satisfied": not missing_slots,
        "semantic_role_refs_consumed": not role_extraneous,
        "unique_semantic_role_assignment": not role_duplicate,
        "consumed_units_role_assigned": not unassigned,
        "projected_roles_are_explicit": all(values for values in projected_roles.values()),
        "projected_slots_are_explicit": all(isinstance(value, Mapping) and value for value in projected_slots.values()),
        "critical_residuals_block_execution": True,
        "diagnostic_receipt_non_executable": not diagnostic_only,
    }
    complete = not diagnostic_only and bool(expected) and not critical and all(invariants.values())
    model_fields = {
        "weighted_coverage": weighted,
        "complete": complete,
        "critical_residual_refs": critical,
        "noncritical_residual_refs": noncritical,
        "missing_semantic_roles": missing_roles,
        "missing_semantic_slots": missing_slots,
        "invariants": invariants,
        "silent_unit_refs": silent,
        "extraneous_consumed_unit_refs": extraneous,
        "duplicate_input_unit_refs": duplicate_input,
        "duplicate_consumed_unit_refs": duplicate_consumed,
        "duplicate_residual_unit_refs": duplicate_residual,
        "consumed_residual_overlap_refs": overlap,
        "semantic_role_extraneous_unit_refs": role_extraneous,
        "semantic_role_duplicate_unit_refs": role_duplicate,
        "unassigned_consumed_unit_refs": unassigned,
    }
    body_fields = {
        "weighted": weighted,
        "complete": complete,
        "critical": critical,
        "noncritical": noncritical,
        "missing_roles": missing_roles,
        "missing_slots": missing_slots,
        "invariants": invariants,
        "silent": silent,
        "extraneous": extraneous,
        "duplicate_input": duplicate_input,
        "duplicate_consumed": duplicate_consumed,
        "duplicate_residual": duplicate_residual,
        "overlap": overlap,
        "role_extraneous": role_extraneous,
        "role_duplicate": role_duplicate,
        "unassigned": unassigned,
    }
    return {"role_refs": role_refs, "slot_refs": slot_refs, "model_fields": model_fields, "body_fields": body_fields}


def _body(**kwargs: Any) -> dict[str, Any]:
    residuals = kwargs.pop("residuals")
    return {
        "abi_version": COVERAGE_ABI_VERSION,
        **kwargs,
        "residuals": [item.as_dict() for item in residuals],
    }


def _residual_from_mapping(item: Mapping[str, Any]) -> ResidualSpan:
    body = {
        "unit_refs": list(map(str, item.get("unit_refs", ()))),
        "surface": str(item.get("surface", "")),
        "normalized": str(item.get("normalized", "")),
        "token_start": int(item.get("token_start", -1)),
        "token_end": int(item.get("token_end", -1)),
        "char_start": int(item.get("char_start", -1)),
        "char_end": int(item.get("char_end", -1)),
        "residual_class": str(item.get("residual_class", "known_predicate_unassigned")),
        "role_hypotheses": list(map(str, item.get("role_hypotheses", ()))),
        "features": dict(item.get("features", {})),
        "semantic_ref": item.get("semantic_ref"),
        "atom_kind": item.get("atom_kind"),
        "source_kind": item.get("source_kind"),
        "grounding_status": str(item.get("grounding_status", "unknown")),
        "grounding_proof_refs": list(map(str, item.get("grounding_proof_refs", ()))),
    }
    expected = stable("residual-span-v6", body)
    supplied = str(item.get("span_ref") or "")
    if supplied != expected:
        raise CoverageIntegrityError("residual span_ref mismatch")
    return ResidualSpan(
        span_ref=supplied,
        unit_refs=tuple(body["unit_refs"]),
        surface=body["surface"],
        normalized=body["normalized"],
        token_start=body["token_start"],
        token_end=body["token_end"],
        char_start=body["char_start"],
        char_end=body["char_end"],
        residual_class=body["residual_class"],
        role_hypotheses=tuple(body["role_hypotheses"]),
        features=body["features"],
        semantic_ref=body["semantic_ref"],
        atom_kind=body["atom_kind"],
        source_kind=body["source_kind"],
        grounding_status=body["grounding_status"],
        grounding_proof_refs=tuple(body["grounding_proof_refs"]),
    )


def coverage_from_dict(value: Mapping[str, Any] | None) -> InterpretationCoverage:
    if not isinstance(value, Mapping) or not value:
        raise CoverageIntegrityError("missing coverage receipt")
    if int(value.get("abi_version", -1)) != COVERAGE_ABI_VERSION:
        raise CoverageIntegrityError(f"unsupported coverage ABI {value.get('abi_version')!r}")
    residuals = tuple(_residual_from_mapping(item) for item in value.get("residuals", ()))
    projected_roles = {
        str(role): tuple(dict(item) for item in values)
        for role, values in dict(value.get("projected_semantic_roles", {})).items()
    }
    projected_slots = {str(slot): dict(item) for slot, item in dict(value.get("projected_slots", {})).items()}
    role_refs = {str(role): tuple(map(str, refs)) for role, refs in dict(value.get("semantic_role_unit_refs", {})).items()}
    slot_refs = {str(slot): tuple(map(str, refs)) for slot, refs in dict(value.get("slot_unit_refs", {})).items()}
    expected = tuple(map(str, value.get("expected_unit_refs", ())))
    consumed = tuple(map(str, value.get("consumed_unit_refs", ())))
    roles = {ref: role for role, refs in role_refs.items() for ref in refs}
    slots = {ref: slot for slot, refs in slot_refs.items() for ref in refs}
    weights = {str(ref): float(weight) for ref, weight in dict(value.get("unit_weights", {})).items()}
    derived = _derive(
        expected=expected,
        consumed=consumed,
        residuals=residuals,
        required_roles=tuple(map(str, value.get("required_semantic_roles", ()))),
        required_slots=tuple(map(str, value.get("required_semantic_slots", ()))),
        raw_roles=roles,
        raw_slots=slots,
        projected_roles=projected_roles,
        projected_slots=projected_slots,
        unit_weights=weights,
        diagnostic_only=bool(value.get("diagnostic_only", False)),
    )
    for key, recomputed in derived["model_fields"].items():
        raw = value.get(key)
        if key == "weighted_coverage" and raw is None:
            raise CoverageIntegrityError("weighted coverage missing from receipt (expected units not reconciled)")
        normalized = dict(raw) if key == "invariants" and isinstance(raw, Mapping) else tuple(raw or ()) if isinstance(recomputed, tuple) else float(raw) if key == "weighted_coverage" else bool(raw)
        if key == "weighted_coverage":
            if not math.isclose(normalized, recomputed, rel_tol=0.0, abs_tol=1e-12):
                raise CoverageIntegrityError("weighted coverage mismatch")
        elif normalized != recomputed:
            raise CoverageIntegrityError(f"coverage derived field mismatch: {key}")
    body = _body(
        schema_ref=str(value.get("schema_ref") or ""),
        hypothesis_ref=str(value.get("hypothesis_ref") or ""),
        match_seed_ref=str(value.get("match_seed_ref") or ""),
        diagnostic_only=bool(value.get("diagnostic_only", False)),
        expected=expected,
        consumed=consumed,
        residuals=residuals,
        required_roles=tuple(map(str, value.get("required_semantic_roles", ()))),
        role_refs=role_refs,
        required_slots=tuple(map(str, value.get("required_semantic_slots", ()))),
        slot_refs=slot_refs,
        projected_roles=projected_roles,
        projected_slots=projected_slots,
        unit_weights=weights,
        **derived["body_fields"],
    )
    if str(value.get("body_hash") or "") != _sha256(body):
        raise CoverageIntegrityError("coverage body hash mismatch")
    expected_ref = stable("interpretation-coverage-v6", str(value.get("seed_hash") or ""), str(value.get("body_hash") or ""))
    if str(value.get("coverage_ref") or "") != expected_ref:
        raise CoverageIntegrityError("coverage_ref mismatch")
    return InterpretationCoverage(
        coverage_ref=expected_ref,
        seed_hash=str(value["seed_hash"]),
        body_hash=str(value["body_hash"]),
        schema_ref=str(value["schema_ref"]),
        hypothesis_ref=str(value["hypothesis_ref"]),
        match_seed_ref=str(value["match_seed_ref"]),
        diagnostic_only=bool(value.get("diagnostic_only", False)),
        expected_unit_refs=expected,
        consumed_unit_refs=consumed,
        residuals=residuals,
        required_semantic_roles=tuple(map(str, value.get("required_semantic_roles", ()))),
        semantic_role_unit_refs=role_refs,
        required_semantic_slots=tuple(map(str, value.get("required_semantic_slots", ()))),
        slot_unit_refs=slot_refs,
        projected_semantic_roles=projected_roles,
        projected_slots=projected_slots,
        unit_weights=weights,
        **derived["model_fields"],
    )
