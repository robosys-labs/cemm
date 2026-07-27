"""Fail-closed semantic span-coverage receipts.

A candidate is executable only when every observed form unit belongs to exactly
one of two partitions: consumed semantic evidence or a typed residual.  The
receipt binds that partition to the exact construction schema, grounding
hypothesis, and pre-match seed that produced it.  Serialized receipts are
untrusted; all derived fields, provenance hashes, and content references are
recomputed during loading.
"""
from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from cemm.model import canonical, stable

COVERAGE_ABI_VERSION = 5

CRITICAL_CLASSES = frozenset(
    {
        "force_critical",
        "predicate_critical",
        "argument_critical",
        "polarity_critical",
        "scope_critical",
    }
)
NONCRITICAL_CLASSES = frozenset(
    {
        "discourse_noncritical",
        "punctuation_noncritical",
        "emphasis_noncritical",
        "modifier_noncritical",
    }
)


class CoverageIntegrityError(ValueError):
    """A coverage receipt is absent, malformed, forged, or contradictory."""


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
        }

    def __post_init__(self) -> None:
        if not self.span_ref:
            raise CoverageIntegrityError("residual span requires span_ref")
        if not self.unit_refs:
            raise CoverageIntegrityError(f"residual {self.span_ref} has no units")
        if self.residual_class not in CRITICAL_CLASSES | NONCRITICAL_CLASSES:
            raise CoverageIntegrityError(
                f"residual {self.span_ref} has unknown class {self.residual_class!r}"
            )
        if self.token_start < 0 or self.token_end <= self.token_start:
            raise CoverageIntegrityError(f"residual {self.span_ref} has invalid token bounds")
        if self.char_start < 0 or self.char_end < self.char_start:
            raise CoverageIntegrityError(
                f"residual {self.span_ref} has invalid character bounds"
            )
        expected = stable("residual-span", self.identity_body())
        if self.span_ref != expected:
            raise CoverageIntegrityError(
                f"residual span_ref does not match content: {self.span_ref} != {expected}"
            )

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
    invariants: Mapping[str, bool] = field(default_factory=dict)
    silent_unit_refs: tuple[str, ...] = ()
    extraneous_consumed_unit_refs: tuple[str, ...] = ()
    duplicate_input_unit_refs: tuple[str, ...] = ()
    duplicate_consumed_unit_refs: tuple[str, ...] = ()
    duplicate_residual_unit_refs: tuple[str, ...] = ()
    consumed_residual_overlap_refs: tuple[str, ...] = ()
    semantic_role_extraneous_unit_refs: tuple[str, ...] = ()
    semantic_role_duplicate_unit_refs: tuple[str, ...] = ()
    unassigned_consumed_unit_refs: tuple[str, ...] = ()
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
        """Create a verified, deliberately non-executable diagnostic receipt."""
        match_seed = match_seed_ref or stable(
            "coverage-diagnostic-match-seed", schema_ref, hypothesis_ref, seed
        )
        return CoveragePolicy.build(
            (),
            (),
            required_semantic_roles=("coverage_receipt",),
            schema_ref=schema_ref,
            hypothesis_ref=hypothesis_ref,
            match_seed_ref=match_seed,
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

    def assert_provenance(
        self,
        *,
        schema_ref: str,
        hypothesis_ref: str,
        match_seed_ref: str,
    ) -> None:
        expected = (str(schema_ref), str(hypothesis_ref), str(match_seed_ref))
        actual = (self.schema_ref, self.hypothesis_ref, self.match_seed_ref)
        if actual != expected:
            raise CoverageIntegrityError(
                "coverage provenance does not match selected semantic candidate: "
                f"serialized={actual!r} selected={expected!r}"
            )

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
            "semantic_role_unit_refs": {
                key: list(value)
                for key, value in sorted(self.semantic_role_unit_refs.items())
            },
            "unit_weights": {
                key: float(value) for key, value in sorted(self.unit_weights.items())
            },
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
            "semantic_role_extraneous_unit_refs": list(
                self.semantic_role_extraneous_unit_refs
            ),
            "semantic_role_duplicate_unit_refs": list(
                self.semantic_role_duplicate_unit_refs
            ),
            "unassigned_consumed_unit_refs": list(self.unassigned_consumed_unit_refs),
        }


class CoveragePolicy:
    """Classify unconsumed form units without inspecting language strings."""

    _FORCE_FEATURES = {
        "interrogative",
        "directive",
        "question_domain",
        "discourse_force",
    }
    _PREDICATE_FEATURES = {
        "predicate",
        "lemma",
        "semantic_port",
        "relation_port",
        "event_port",
        "state_port",
        "property_marker",
        "property_ref",
        "property_kind",
        "copular",
        "auxiliary",
    }
    _POLARITY_FEATURES = {"negation", "polarity"}
    _SCOPE_FEATURES = {"quantifier", "modal", "scope_operator", "conditional"}

    @staticmethod
    def _feature_truth(features: Mapping[str, Any], names: set[str]) -> bool:
        return any(
            features.get(name) not in (None, False, "", (), [], {}) for name in names
        )

    @classmethod
    def classify_unit(
        cls,
        unit: Any,
        *,
        assigned_role: str | None = None,
        schema_hints: Mapping[str, Any] | None = None,
    ) -> tuple[str, tuple[str, ...]]:
        features = dict(getattr(unit, "features", {}) or {})
        hints = dict(schema_hints or {})
        role = assigned_role or hints.get("role") or features.get("syntactic_role")
        kind = getattr(unit, "kind", None)
        if kind == "punctuation":
            return "punctuation_noncritical", ("boundary",)
        if kind == "discourse" or features.get("discourse_marker"):
            return "discourse_noncritical", ("discourse",)
        if features.get("emphasis") or features.get("focus_only"):
            return "emphasis_noncritical", ("emphasis",)
        if cls._feature_truth(features, cls._POLARITY_FEATURES):
            return "polarity_critical", ("polarity",)
        if cls._feature_truth(features, cls._FORCE_FEATURES):
            return "force_critical", ("force",)
        if cls._feature_truth(features, cls._SCOPE_FEATURES):
            return "scope_critical", ("scope",)
        if role in {
            "subject",
            "object",
            "target",
            "actor",
            "patient",
            "theme",
            "recipient",
            "referent",
            "argument",
            "value",
        }:
            return "argument_critical", (str(role),)
        if role in {"predicate", "relation", "event_type", "state_dimension"}:
            return "predicate_critical", (str(role),)
        if kind == "anchor":
            return "argument_critical", ("referent",)
        if cls._feature_truth(features, cls._PREDICATE_FEATURES):
            return "predicate_critical", ("predicate",)
        if features.get("modifier") or role in {"modifier", "adjunct"}:
            return "modifier_noncritical", (str(role or "modifier"),)
        if kind == "function":
            return "modifier_noncritical", ("function",)
        return "predicate_critical", ("predicate_or_argument",)

    @classmethod
    def build(
        cls,
        units: Sequence[Any],
        consumed_unit_refs: Iterable[str],
        *,
        role_by_unit_ref: Mapping[str, str] | None = None,
        required_semantic_roles: Iterable[str] = (),
        schema_hints_by_unit_ref: Mapping[str, Mapping[str, Any]] | None = None,
        schema_ref: str | None = None,
        hypothesis_ref: str | None = None,
        match_seed_ref: str | None = None,
        diagnostic_only: bool = False,
        seed: Any = None,
    ) -> InterpretationCoverage:
        expected = _tuple_strings(getattr(unit, "unit_ref") for unit in units)
        raw_consumed = _tuple_strings(consumed_unit_refs)
        raw_roles = {
            str(key): str(value) for key, value in dict(role_by_unit_ref or {}).items()
        }
        hints = dict(schema_hints_by_unit_ref or {})
        required_roles = tuple(sorted(set(map(str, required_semantic_roles))))

        schema = str(schema_ref or ("diagnostic:coverage" if diagnostic_only else "coverage:standalone"))
        hypothesis = str(
            hypothesis_ref
            or stable("coverage-standalone-hypothesis", expected, raw_consumed)
        )
        match_seed = str(
            match_seed_ref
            or stable(
                "coverage-standalone-match-seed",
                schema,
                hypothesis,
                expected,
                raw_consumed,
                raw_roles,
            )
        )
        if not schema or not hypothesis or not match_seed:
            raise CoverageIntegrityError("coverage provenance is incomplete")
        if diagnostic_only and expected:
            raise CoverageIntegrityError("diagnostic coverage must not claim observed units")
        if not diagnostic_only and not expected:
            raise CoverageIntegrityError("executable coverage requires observed units")

        expected_counts = Counter(expected)
        consumed_counts = Counter(raw_consumed)
        duplicate_input = tuple(sorted(k for k, v in expected_counts.items() if v > 1))
        duplicate_consumed = tuple(sorted(k for k, v in consumed_counts.items() if v > 1))
        consumed = raw_consumed
        consumed_set = set(consumed)
        expected_set = set(expected)

        residuals: list[ResidualSpan] = []
        unit_weights: dict[str, float] = {}
        for unit in units:
            unit_ref = str(getattr(unit, "unit_ref"))
            unit_class, _ = cls.classify_unit(
                unit,
                assigned_role=raw_roles.get(unit_ref),
                schema_hints=hints.get(unit_ref),
            )
            unit_weights[unit_ref] = 2.0 if unit_class in CRITICAL_CLASSES else 0.5
            if unit_ref in consumed_set:
                continue
            residual_class, role_hypotheses = cls.classify_unit(
                unit,
                assigned_role=raw_roles.get(unit_ref),
                schema_hints=hints.get(unit_ref),
            )
            body = {
                "unit_refs": [unit_ref],
                "surface": str(getattr(unit, "surface", "")),
                "normalized": str(getattr(unit, "normalized", "")),
                "token_start": int(getattr(unit, "token_start", -1)),
                "token_end": int(getattr(unit, "token_end", -1)),
                "char_start": int(getattr(unit, "char_start", -1)),
                "char_end": int(getattr(unit, "char_end", -1)),
                "residual_class": residual_class,
                "role_hypotheses": list(role_hypotheses),
                "features": dict(getattr(unit, "features", {}) or {}),
            }
            residuals.append(
                ResidualSpan(
                    span_ref=stable("residual-span", body),
                    unit_refs=(unit_ref,),
                    surface=body["surface"],
                    normalized=body["normalized"],
                    token_start=body["token_start"],
                    token_end=body["token_end"],
                    char_start=body["char_start"],
                    char_end=body["char_end"],
                    residual_class=residual_class,
                    role_hypotheses=tuple(role_hypotheses),
                    features=body["features"],
                )
            )

        derived = _derive(
            expected=expected,
            consumed=consumed,
            residuals=tuple(residuals),
            required_roles=required_roles,
            raw_roles=raw_roles,
            unit_weights=unit_weights,
            diagnostic_only=diagnostic_only,
        )
        body = _coverage_body(
            schema_ref=schema,
            hypothesis_ref=hypothesis,
            match_seed_ref=match_seed,
            diagnostic_only=diagnostic_only,
            expected=expected,
            consumed=consumed,
            residuals=tuple(residuals),
            required_roles=required_roles,
            role_refs=derived["role_refs"],
            unit_weights=unit_weights,
            **derived["body_fields"],
        )
        seed_hash = _sha256(
            (
                "coverage-seed-v5",
                schema,
                hypothesis,
                match_seed,
                seed,
            )
        )
        body_hash = _sha256(body)
        return InterpretationCoverage(
            coverage_ref=stable("interpretation-coverage", seed_hash, body_hash),
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
            unit_weights=unit_weights,
            **derived["model_fields"],
        )


def _derive(
    *,
    expected: tuple[str, ...],
    consumed: tuple[str, ...],
    residuals: tuple[ResidualSpan, ...],
    required_roles: tuple[str, ...],
    raw_roles: Mapping[str, str],
    unit_weights: Mapping[str, float],
    diagnostic_only: bool,
) -> dict[str, Any]:
    expected_counts = Counter(expected)
    consumed_counts = Counter(consumed)
    residual_refs = tuple(ref for item in residuals for ref in item.unit_refs)
    residual_counts = Counter(residual_refs)
    expected_set = set(expected)
    consumed_set = set(consumed)
    residual_set = set(residual_refs)

    duplicate_input = tuple(sorted(k for k, v in expected_counts.items() if v > 1))
    duplicate_consumed = tuple(sorted(k for k, v in consumed_counts.items() if v > 1))
    duplicate_residual = tuple(sorted(k for k, v in residual_counts.items() if v > 1))
    overlap = tuple(sorted(consumed_set & residual_set))
    silent = tuple(sorted(expected_set - consumed_set - residual_set))
    extraneous = tuple(sorted((consumed_set | residual_set) - expected_set))

    role_extraneous = tuple(sorted(set(raw_roles) - consumed_set))
    grouped: dict[str, list[str]] = defaultdict(list)
    for unit_ref in consumed:
        role = raw_roles.get(unit_ref)
        if role:
            grouped[role].append(unit_ref)
    role_refs = {key: tuple(value) for key, value in sorted(grouped.items())}
    flattened = tuple(ref for refs in role_refs.values() for ref in refs)
    flattened_counts = Counter(flattened)
    role_duplicate = tuple(sorted(k for k, v in flattened_counts.items() if v > 1))
    unassigned = tuple(sorted(consumed_set - set(flattened)))
    missing_roles = tuple(role for role in required_roles if not role_refs.get(role))

    if set(unit_weights) != expected_set:
        raise CoverageIntegrityError(
            "coverage unit-weight basis differs from expected units: "
            f"missing={sorted(expected_set-set(unit_weights))}, "
            f"extra={sorted(set(unit_weights)-expected_set)}"
        )
    total_weight = sum(float(value) for value in unit_weights.values())
    weighted = (
        0.0
        if diagnostic_only
        else 1.0
        if total_weight <= 0.0
        else sum(float(unit_weights.get(ref, 0.0)) for ref in consumed_set) / total_weight
    )
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
        "semantic_role_refs_consumed": not role_extraneous,
        "unique_semantic_role_assignment": not role_duplicate,
        "consumed_units_role_assigned": not unassigned,
        "critical_residuals_block_execution": True,
        "diagnostic_receipt_non_executable": not diagnostic_only,
    }
    complete = (
        not diagnostic_only
        and bool(expected)
        and not critical
        and all(invariants.values())
    )
    model_fields = {
        "weighted_coverage": weighted,
        "complete": complete,
        "critical_residual_refs": critical,
        "noncritical_residual_refs": noncritical,
        "missing_semantic_roles": missing_roles,
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
    return {"role_refs": role_refs, "model_fields": model_fields, "body_fields": body_fields}


def _coverage_body(
    *,
    schema_ref: str,
    hypothesis_ref: str,
    match_seed_ref: str,
    diagnostic_only: bool,
    expected: Sequence[str],
    consumed: Sequence[str],
    residuals: Sequence[ResidualSpan],
    required_roles: Sequence[str],
    role_refs: Mapping[str, Sequence[str]],
    unit_weights: Mapping[str, float],
    weighted: float,
    complete: bool,
    critical: Sequence[str],
    noncritical: Sequence[str],
    missing_roles: Sequence[str],
    invariants: Mapping[str, bool],
    silent: Sequence[str],
    extraneous: Sequence[str],
    duplicate_input: Sequence[str],
    duplicate_consumed: Sequence[str],
    duplicate_residual: Sequence[str],
    overlap: Sequence[str],
    role_extraneous: Sequence[str],
    role_duplicate: Sequence[str],
    unassigned: Sequence[str],
) -> dict[str, Any]:
    return {
        "abi_version": COVERAGE_ABI_VERSION,
        "schema_ref": schema_ref,
        "hypothesis_ref": hypothesis_ref,
        "match_seed_ref": match_seed_ref,
        "diagnostic_only": bool(diagnostic_only),
        "expected_unit_refs": list(expected),
        "consumed_unit_refs": list(consumed),
        "residuals": [item.as_dict() for item in residuals],
        "required_semantic_roles": list(required_roles),
        "semantic_role_unit_refs": {
            key: list(value) for key, value in sorted(role_refs.items())
        },
        "unit_weights": {
            key: float(value) for key, value in sorted(unit_weights.items())
        },
        "weighted_coverage": float(weighted),
        "complete": bool(complete),
        "critical_residual_refs": list(critical),
        "noncritical_residual_refs": list(noncritical),
        "missing_semantic_roles": list(missing_roles),
        "invariants": dict(invariants),
        "silent_unit_refs": list(silent),
        "extraneous_consumed_unit_refs": list(extraneous),
        "duplicate_input_unit_refs": list(duplicate_input),
        "duplicate_consumed_unit_refs": list(duplicate_consumed),
        "duplicate_residual_unit_refs": list(duplicate_residual),
        "consumed_residual_overlap_refs": list(overlap),
        "semantic_role_extraneous_unit_refs": list(role_extraneous),
        "semantic_role_duplicate_unit_refs": list(role_duplicate),
        "unassigned_consumed_unit_refs": list(unassigned),
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
        "residual_class": str(item.get("residual_class", "predicate_critical")),
        "role_hypotheses": list(map(str, item.get("role_hypotheses", ()))),
        "features": dict(item.get("features", {})),
    }
    expected_ref = stable("residual-span", body)
    supplied_ref = str(item.get("span_ref") or "")
    if supplied_ref != expected_ref:
        raise CoverageIntegrityError(
            f"residual span_ref mismatch: {supplied_ref!r} != {expected_ref!r}"
        )
    expected_critical = body["residual_class"] in CRITICAL_CLASSES
    if "critical" in item and bool(item["critical"]) is not expected_critical:
        raise CoverageIntegrityError("residual critical flag does not match class")
    return ResidualSpan(
        span_ref=supplied_ref,
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
    )


def coverage_from_dict(value: Mapping[str, Any] | None) -> InterpretationCoverage:
    """Load and fully verify an untrusted serialized coverage receipt."""
    if not isinstance(value, Mapping) or not value:
        raise CoverageIntegrityError("missing interpretation coverage receipt")
    if int(value.get("abi_version", -1)) != COVERAGE_ABI_VERSION:
        raise CoverageIntegrityError(
            f"unsupported coverage ABI {value.get('abi_version')!r}"
        )

    diagnostic_only = bool(value.get("diagnostic_only", False))
    expected = tuple(map(str, value.get("expected_unit_refs", ())))
    if not expected and not diagnostic_only:
        raise CoverageIntegrityError("coverage receipt has no expected units")
    if expected and diagnostic_only:
        raise CoverageIntegrityError("diagnostic coverage cannot contain expected units")

    schema_ref = str(value.get("schema_ref") or "")
    hypothesis_ref = str(value.get("hypothesis_ref") or "")
    match_seed_ref = str(value.get("match_seed_ref") or "")
    if not schema_ref or not hypothesis_ref or not match_seed_ref:
        raise CoverageIntegrityError("coverage provenance is incomplete")
    consumed = tuple(map(str, value.get("consumed_unit_refs", ())))
    residuals = tuple(
        _residual_from_mapping(item) for item in value.get("residuals", ())
    )
    required_roles = tuple(
        sorted(set(map(str, value.get("required_semantic_roles", ()))))
    )
    role_refs = {
        str(role): tuple(map(str, refs))
        for role, refs in dict(value.get("semantic_role_unit_refs", {})).items()
    }
    raw_roles: dict[str, str] = {}
    for role, refs in role_refs.items():
        for ref in refs:
            if ref in raw_roles:
                # Preserve the duplicate in the derived flattened receipt by using
                # a synthetic second key. The verifier will reject it below.
                raw_roles[f"{ref}\x00duplicate\x00{role}"] = role
            else:
                raw_roles[ref] = role

    unit_weights: dict[str, float] = {}
    for ref, raw_weight in dict(value.get("unit_weights", {}) or {}).items():
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError) as exc:
            raise CoverageIntegrityError(f"unit weight is not numeric: {ref}") from exc
        if not math.isfinite(weight) or weight <= 0.0:
            raise CoverageIntegrityError(
                f"unit weight must be positive and finite: {ref}"
            )
        unit_weights[str(ref)] = weight

    # Recompute from the serialized role map directly so duplicate assignments
    # remain visible rather than being collapsed by a dictionary inversion.
    expected_counts = Counter(expected)
    consumed_counts = Counter(consumed)
    residual_unit_refs = tuple(ref for item in residuals for ref in item.unit_refs)
    residual_counts = Counter(residual_unit_refs)
    expected_set = set(expected)
    consumed_set = set(consumed)
    residual_set = set(residual_unit_refs)
    duplicate_input = tuple(sorted(k for k, v in expected_counts.items() if v > 1))
    duplicate_consumed = tuple(sorted(k for k, v in consumed_counts.items() if v > 1))
    duplicate_residual = tuple(sorted(k for k, v in residual_counts.items() if v > 1))
    overlap = tuple(sorted(consumed_set & residual_set))
    silent = tuple(sorted(expected_set - consumed_set - residual_set))
    extraneous = tuple(sorted((consumed_set | residual_set) - expected_set))
    flattened = tuple(ref for refs in role_refs.values() for ref in refs)
    role_counts = Counter(flattened)
    role_extraneous = tuple(sorted(set(flattened) - consumed_set))
    role_duplicate = tuple(sorted(k for k, v in role_counts.items() if v > 1))
    unassigned = tuple(sorted(consumed_set - set(flattened)))
    missing_roles = tuple(role for role in required_roles if not role_refs.get(role))
    critical = tuple(item.span_ref for item in residuals if item.critical)
    noncritical = tuple(item.span_ref for item in residuals if not item.critical)

    if set(unit_weights) != expected_set:
        raise CoverageIntegrityError(
            "coverage unit-weight basis differs from expected units: "
            f"missing={sorted(expected_set-set(unit_weights))}, "
            f"extra={sorted(set(unit_weights)-expected_set)}"
        )
    total_weight = sum(unit_weights.values())
    weighted = (
        0.0
        if diagnostic_only
        else 1.0
        if total_weight <= 0.0
        else sum(unit_weights.get(ref, 0.0) for ref in consumed_set) / total_weight
    )
    weighted = max(0.0, min(1.0, weighted))
    invariants = {
        "all_units_accounted_for": not silent and not extraneous,
        "unique_input_unit_refs": not duplicate_input,
        "unique_consumed_unit_refs": not duplicate_consumed,
        "unique_residual_unit_refs": not duplicate_residual,
        "consumed_residual_disjoint": not overlap,
        "semantic_roles_satisfied": not missing_roles,
        "semantic_role_refs_consumed": not role_extraneous,
        "unique_semantic_role_assignment": not role_duplicate,
        "consumed_units_role_assigned": not unassigned,
        "critical_residuals_block_execution": True,
        "diagnostic_receipt_non_executable": not diagnostic_only,
    }
    complete = (
        not diagnostic_only
        and bool(expected)
        and not critical
        and all(invariants.values())
    )

    expected_derived: dict[str, Any] = {
        "weighted_coverage": weighted,
        "complete": complete,
        "critical_residual_refs": critical,
        "noncritical_residual_refs": noncritical,
        "missing_semantic_roles": missing_roles,
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
    for key, recomputed in expected_derived.items():
        raw = value.get(key)
        if key == "weighted_coverage":
            try:
                normalized: Any = float(raw)
            except (TypeError, ValueError) as exc:
                raise CoverageIntegrityError("weighted coverage is not numeric") from exc
            if not math.isclose(normalized, recomputed, rel_tol=0.0, abs_tol=1e-12):
                raise CoverageIntegrityError(
                    f"coverage derived field mismatch for {key}: "
                    f"serialized={normalized!r} recomputed={recomputed!r}"
                )
            continue
        if key == "invariants":
            normalized = dict(raw) if isinstance(raw, Mapping) else {}
        elif isinstance(recomputed, tuple):
            normalized = tuple(raw or ())
        else:
            normalized = bool(raw)
        if normalized != recomputed:
            raise CoverageIntegrityError(
                f"coverage derived field mismatch for {key}: "
                f"serialized={normalized!r} recomputed={recomputed!r}"
            )

    body = _coverage_body(
        schema_ref=schema_ref,
        hypothesis_ref=hypothesis_ref,
        match_seed_ref=match_seed_ref,
        diagnostic_only=diagnostic_only,
        expected=expected,
        consumed=consumed,
        residuals=residuals,
        required_roles=required_roles,
        role_refs=role_refs,
        unit_weights=unit_weights,
        weighted=weighted,
        complete=complete,
        critical=critical,
        noncritical=noncritical,
        missing_roles=missing_roles,
        invariants=invariants,
        silent=silent,
        extraneous=extraneous,
        duplicate_input=duplicate_input,
        duplicate_consumed=duplicate_consumed,
        duplicate_residual=duplicate_residual,
        overlap=overlap,
        role_extraneous=role_extraneous,
        role_duplicate=role_duplicate,
        unassigned=unassigned,
    )
    seed_hash = str(value.get("seed_hash") or "")
    body_hash = str(value.get("body_hash") or "")
    coverage_ref = str(value.get("coverage_ref") or "")
    if not seed_hash:
        raise CoverageIntegrityError("coverage seed hash is absent")
    if body_hash != _sha256(body):
        raise CoverageIntegrityError("coverage body hash does not match serialized content")
    expected_ref = stable("interpretation-coverage", seed_hash, body_hash)
    if coverage_ref != expected_ref:
        raise CoverageIntegrityError("coverage_ref does not match seed/body hashes")

    return InterpretationCoverage(
        coverage_ref=coverage_ref,
        seed_hash=seed_hash,
        body_hash=body_hash,
        schema_ref=schema_ref,
        hypothesis_ref=hypothesis_ref,
        match_seed_ref=match_seed_ref,
        diagnostic_only=diagnostic_only,
        expected_unit_refs=expected,
        consumed_unit_refs=consumed,
        residuals=residuals,
        required_semantic_roles=required_roles,
        semantic_role_unit_refs=role_refs,
        unit_weights=unit_weights,
        weighted_coverage=weighted,
        complete=complete,
        critical_residual_refs=critical,
        noncritical_residual_refs=noncritical,
        missing_semantic_roles=missing_roles,
        invariants=invariants,
        silent_unit_refs=silent,
        extraneous_consumed_unit_refs=extraneous,
        duplicate_input_unit_refs=duplicate_input,
        duplicate_consumed_unit_refs=duplicate_consumed,
        duplicate_residual_unit_refs=duplicate_residual,
        consumed_residual_overlap_refs=overlap,
        semantic_role_extraneous_unit_refs=role_extraneous,
        semantic_role_duplicate_unit_refs=role_duplicate,
        unassigned_consumed_unit_refs=unassigned,
    )
