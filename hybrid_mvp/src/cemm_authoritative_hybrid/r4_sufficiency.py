"""Review-governed structural sufficiency for R4 contracts and episodes."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .canonical import stable_ref
from .expressions import (
    ApplicationFiller,
    BoundVariable,
    GroundedReference,
    LiteralValue,
    SemanticExpression,
    UnresolvedValue,
)
from .r3_codec import exact_fields, exact_refs, exact_text, wire_refs
from .r4_contracts import ExpectedCycleContract

STRUCTURAL_SUFFICIENCY_ABI_VERSION = 2

__all__ = [
    "STRUCTURAL_SUFFICIENCY_ABI_VERSION",
    "StructuralSufficiencyReceipt",
    "StructuralSufficiencyEvaluator",
]


def _counts(value: Mapping[str, int], name: str) -> Mapping[str, int]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    rows: dict[str, int] = {}
    for key, amount in value.items():
        exact_text(key, f"{name} key")
        if type(amount) is not int or amount < 0:
            raise TypeError(f"{name} values must be nonnegative exact int")
        rows[key] = amount
    return MappingProxyType(dict(sorted(rows.items())))


@dataclass(frozen=True, init=False)
class StructuralSufficiencyReceipt:
    abi_version: int
    receipt_ref: str
    contract_set_ref: str
    episode_set_ref: str | None
    denominator_ref: str
    counts: Mapping[str, int]
    minimums: Mapping[str, int]
    maximums: Mapping[str, int]
    violations: tuple[str, ...]

    _FIELDS = frozenset(
        {
            "abi_version",
            "receipt_ref",
            "contract_set_ref",
            "episode_set_ref",
            "denominator_ref",
            "counts",
            "minimums",
            "maximums",
            "violations",
        }
    )

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use StructuralSufficiencyReceipt.create")

    @classmethod
    def create(
        cls,
        *,
        contract_set_ref: str,
        episode_set_ref: str | None,
        denominator_ref: str,
        counts: Mapping[str, int],
        minimums: Mapping[str, int],
        maximums: Mapping[str, int],
        violations: tuple[str, ...],
    ) -> "StructuralSufficiencyReceipt":
        normalized_counts = _counts(counts, "counts")
        normalized_minimums = _counts(minimums, "minimums")
        normalized_maximums = _counts(maximums, "maximums")
        codes = exact_refs(violations, "violations")
        values = {
            "contract_set_ref": exact_text(contract_set_ref, "contract_set_ref"),
            "episode_set_ref": None
            if episode_set_ref is None
            else exact_text(episode_set_ref, "episode_set_ref"),
            "denominator_ref": exact_text(denominator_ref, "denominator_ref"),
            "counts": normalized_counts,
            "minimums": normalized_minimums,
            "maximums": normalized_maximums,
            "violations": codes,
        }
        material = {
            "abi_version": STRUCTURAL_SUFFICIENCY_ABI_VERSION,
            "contract_set_ref": values["contract_set_ref"],
            "episode_set_ref": values["episode_set_ref"],
            "denominator_ref": values["denominator_ref"],
            "counts": dict(normalized_counts),
            "minimums": dict(normalized_minimums),
            "maximums": dict(normalized_maximums),
            "violations": list(codes),
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", STRUCTURAL_SUFFICIENCY_ABI_VERSION)
        object.__setattr__(obj, "receipt_ref", stable_ref("structural_sufficiency_v2", material))
        for name, value in values.items():
            object.__setattr__(obj, name, value)
        return obj

    @property
    def passed(self) -> bool:
        return not self.violations

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "receipt_ref": self.receipt_ref,
            "contract_set_ref": self.contract_set_ref,
            "episode_set_ref": self.episode_set_ref,
            "denominator_ref": self.denominator_ref,
            "counts": dict(self.counts),
            "minimums": dict(self.minimums),
            "maximums": dict(self.maximums),
            "violations": list(self.violations),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StructuralSufficiencyReceipt":
        row = exact_fields(value, cls._FIELDS, "StructuralSufficiencyReceipt")
        if row["abi_version"] != STRUCTURAL_SUFFICIENCY_ABI_VERSION:
            raise ValueError("unsupported Structural Sufficiency ABI")
        for name in ("counts", "minimums", "maximums"):
            if type(row[name]) is not dict:
                raise TypeError(f"{name} must be exact dict")
        rebuilt = cls.create(
            contract_set_ref=row["contract_set_ref"],
            episode_set_ref=row["episode_set_ref"],
            denominator_ref=row["denominator_ref"],
            counts=row["counts"],
            minimums=row["minimums"],
            maximums=row["maximums"],
            violations=wire_refs(row["violations"], "violations"),
        )
        if rebuilt.receipt_ref != row["receipt_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical StructuralSufficiencyReceipt encoding")
        return rebuilt


def _expression_depth(expression: SemanticExpression) -> int:
    parents: dict[str, str] = {}
    for app in expression.applications:
        for binding in (*app.roles, *app.qualifiers):
            if isinstance(binding.filler, ApplicationFiller):
                parents[binding.filler.node_ref] = app.application_ref
    for scope in expression.scope_operators:
        parents[scope.operand_ref] = scope.scope_ref
    for link in expression.expression_links:
        for operand in link.operand_refs:
            parents[operand] = link.link_ref
    for binder in expression.binders:
        parents[binder.body_ref] = binder.binder_ref
    nodes = {
        *(row.application_ref for row in expression.applications),
        *(row.scope_ref for row in expression.scope_operators),
        *(row.link_ref for row in expression.expression_links),
        *(row.binder_ref for row in expression.binders),
    }
    maximum = 0
    for ref in nodes:
        cursor = ref
        seen: set[str] = set()
        depth = 1
        while cursor in parents:
            if cursor in seen:
                raise ValueError("expected expression contains a cycle")
            seen.add(cursor)
            cursor = parents[cursor]
            depth += 1
        maximum = max(maximum, depth)
    return maximum


def _filler_kind(value: object) -> str:
    if isinstance(value, GroundedReference):
        return "grounded"
    if isinstance(value, LiteralValue):
        return f"literal:{value.value_type}"
    if isinstance(value, BoundVariable):
        return "bound_variable"
    if isinstance(value, ApplicationFiller):
        return "proposition"
    if isinstance(value, UnresolvedValue):
        return "unresolved"
    raise TypeError("unknown expression filler")


class StructuralSufficiencyEvaluator:
    """Measure exact ABI/authority dimensions against reviewed thresholds.

    Denominators are explicit configuration, never inferred from a tiny sample.
    A required dimension absent from the corpus is reported as a violation.
    """

    DEFAULT_MINIMUMS: Mapping[str, int] = MappingProxyType(
        {
            "operator:op:designation": 1,
            "operator:op:type": 1,
            "operator:op:relation": 1,
            "operator:op:state": 1,
            "operator:op:event": 1,
            "mode:OBSERVE": 1,
            "mode:QUERY": 1,
            "mode:REQUEST": 1,
            "mode:SIMULATE": 1,
            "filler:grounded": 1,
            "filler:literal:string": 1,
            "filler:bound_variable": 1,
            "filler:proposition": 1,
            "scope:any": 1,
            "link:any": 1,
            "binder:any": 1,
            "multi_root": 1,
            "outcome:semantic": 1,
            "outcome:ambiguity": 1,
            "outcome:gap": 1,
            "outcome:verification_rejection": 1,
            "outcome:restart": 1,
            "outcome:realization_equivalence": 1,
            "effect_kind:effect": 1,
            "effect_kind:no_effect": 1,
        }
    )

    def __init__(
        self,
        *,
        minimums: Mapping[str, int] | None = None,
        maximums: Mapping[str, int] | None = None,
        denominator_ref: str = "contract:r4:structural-sufficiency-v2",
    ) -> None:
        self._minimums = _counts(minimums or self.DEFAULT_MINIMUMS, "minimums")
        self._maximums = _counts(maximums or {}, "maximums")
        self._denominator_ref = exact_text(denominator_ref, "denominator_ref")

    def evaluate(
        self,
        contracts: Iterable[ExpectedCycleContract],
        *,
        episodes: Iterable[Any] = (),
    ) -> StructuralSufficiencyReceipt:
        contract_rows = tuple(contracts)
        episode_rows = tuple(episodes)
        if not contract_rows:
            raise ValueError("structural sufficiency requires contracts")
        if any(type(row) is not ExpectedCycleContract for row in contract_rows):
            raise TypeError("contracts must contain ExpectedCycleContract")
        counts: Counter[str] = Counter()
        for contract in contract_rows:
            counts["contracts"] += 1
            counts[f"outcome:{contract.outcome_kind.value}"] += 1
            counts[f"relation:{contract.expression_relation.value}"] += 1
            counts[f"mode:{contract.expected_mode.value}"] += 1
            counts[f"decision_status:{contract.expected_decision.status.value}"] += 1
            counts[f"decision_action:{contract.expected_decision.action.value}"] += 1
            counts[f"effect_kind:{contract.expected_effect.kind.value}"] += 1
            for normalized in contract.normalized_assertions:
                kind = normalized.get("kind")
                if type(kind) is str:
                    counts[f"assertion:{kind}"] += 1
            for expression in contract.expected_expressions:
                counts["expressions"] += 1
                counts[f"roots:{len(expression.root_refs)}"] += 1
                counts[f"depth:{_expression_depth(expression)}"] += 1
                if len(expression.root_refs) > 1:
                    counts["multi_root"] += 1
                if expression.scope_operators:
                    counts["scope:any"] += 1
                if expression.expression_links:
                    counts["link:any"] += 1
                if expression.binders:
                    counts["binder:any"] += 1
                if expression.unresolved_fillers:
                    counts["unresolved:any"] += 1
                for app in expression.applications:
                    counts[f"operator:{app.operator}"] += 1
                    counts[f"predicate:{app.predicate_ref}"] += 1
                    for role in app.roles:
                        counts[f"role:{role.role_ref}"] += 1
                        counts[f"filler:{_filler_kind(role.filler)}"] += 1
                    for qualifier in app.qualifiers:
                        counts[f"qualifier:{qualifier.role_ref}"] += 1
                        counts[f"filler:{_filler_kind(qualifier.filler)}"] += 1
                for scope in expression.scope_operators:
                    counts[f"scope_type:{scope.operator_type}"] += 1
                    counts[f"scope_value:{scope.value_ref}"] += 1
                for link in expression.expression_links:
                    counts[f"link_type:{link.link_type}"] += 1
                    counts[f"link_arity:{len(link.operand_refs)}"] += 1
        for episode in episode_rows:
            comparison = getattr(episode, "comparison", None)
            if comparison is None or type(getattr(episode, "episode_ref", None)) is not str:
                raise TypeError("episodes must be authentic episode-like records")
            counts["episodes"] += 1
            counts["episode:aligned" if comparison.passed else "episode:mismatch"] += 1

        violations: list[str] = []
        for key, minimum in self._minimums.items():
            if counts.get(key, 0) < minimum:
                violations.append(f"minimum:{key}:{counts.get(key, 0)}<{minimum}")
        for key, maximum in self._maximums.items():
            if counts.get(key, 0) > maximum:
                violations.append(f"maximum:{key}:{counts.get(key, 0)}>{maximum}")
        contract_set_ref = stable_ref(
            "expected_contract_set_v2",
            [row.contract_ref for row in sorted(contract_rows, key=lambda row: row.contract_ref)],
        )
        episode_set_ref = (
            stable_ref(
                "authentic_episode_set_v3",
                [row.episode_ref for row in sorted(episode_rows, key=lambda row: row.episode_ref)],
            )
            if episode_rows
            else None
        )
        return StructuralSufficiencyReceipt.create(
            contract_set_ref=contract_set_ref,
            episode_set_ref=episode_set_ref,
            denominator_ref=self._denominator_ref,
            counts=dict(counts),
            minimums=self._minimums,
            maximums=self._maximums,
            violations=tuple(sorted(violations)),
        )
