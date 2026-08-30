"""Reviewed R4 mutations with authentic earliest-owner execution.

Expected labels are review contracts only.  Mutation observations are created
exclusively from a concrete owner result; the executor never copies expected
labels into observed fields and rejects plain callback functions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable

from .canonical import stable_ref
from .r3_codec import (
    exact_bool,
    exact_fields,
    exact_refs,
    exact_text,
    freeze_json,
    thaw_json,
    wire_refs,
)
from .r4_contracts import ExpectedCycleContract
from .r4_expansion import ExpandedCase

SEMANTIC_MUTATION_ABI_VERSION = 2
MUTATION_OBSERVATION_ABI_VERSION = 2
MUTATION_EXECUTION_REQUEST_ABI_VERSION = 1
MAX_REVIEWED_MUTATIONS_PER_CASE = 8

__all__ = [
    "SEMANTIC_MUTATION_ABI_VERSION",
    "MUTATION_OBSERVATION_ABI_VERSION",
    "MUTATION_EXECUTION_REQUEST_ABI_VERSION",
    "MutationBoundaryResult",
    "MutationExecutionRequest",
    "MutationExecutionOwner",
    "SemanticMutation",
    "MutationObservation",
    "MutationGenerator",
    "MutationExecutor",
]


@dataclass(frozen=True)
class MutationBoundaryResult:
    earliest_owner: str
    status: str
    error_code: str
    artifact_ref: str

    def __post_init__(self) -> None:
        for name in ("earliest_owner", "status", "error_code", "artifact_ref"):
            exact_text(getattr(self, name), name)


@runtime_checkable
class MutationExecutionOwner(Protocol):
    def execute_mutation(
        self, request: "MutationExecutionRequest"
    ) -> MutationBoundaryResult:
        """Execute the altered artifact through its authentic earliest owner."""
        raise NotImplementedError


@dataclass(frozen=True, init=False)
class SemanticMutation:
    abi_version: int
    mutation_ref: str
    parent_case_ref: str
    parent_contract_ref: str
    scope: str
    dimension: str
    changed_path: str
    before: Any
    after: Any
    mutated_case: Mapping[str, Any]
    expected_earliest_owner: str
    expected_status: str
    expected_error_code: str
    lineage_refs: tuple[str, ...]
    review_refs: tuple[str, ...]

    _FIELDS = frozenset(
        {
            "abi_version",
            "mutation_ref",
            "parent_case_ref",
            "parent_contract_ref",
            "scope",
            "dimension",
            "changed_path",
            "before",
            "after",
            "mutated_case",
            "expected_earliest_owner",
            "expected_status",
            "expected_error_code",
            "lineage_refs",
            "review_refs",
        }
    )

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use SemanticMutation.create")

    @classmethod
    def create(
        cls,
        *,
        parent_case_ref: str,
        parent_contract_ref: str,
        scope: str,
        dimension: str,
        changed_path: str,
        before: Any,
        after: Any,
        mutated_case: Mapping[str, Any],
        expected_earliest_owner: str,
        expected_status: str,
        expected_error_code: str,
        lineage_refs: tuple[str, ...],
        review_refs: tuple[str, ...],
    ) -> "SemanticMutation":
        scope_name = exact_text(scope, "scope")
        if scope_name not in {"contract", "environment", "derivation", "persistence"}:
            raise ValueError("unsupported mutation scope")
        frozen_before = freeze_json(before)
        frozen_after = freeze_json(after)
        if thaw_json(frozen_before) == thaw_json(frozen_after):
            raise ValueError("mutation must change its declared dimension")
        frozen_case = freeze_json(dict(mutated_case))
        if not isinstance(frozen_case, Mapping):
            raise TypeError("mutated_case must freeze to a mapping")
        values = {
            "parent_case_ref": exact_text(parent_case_ref, "parent_case_ref"),
            "parent_contract_ref": exact_text(parent_contract_ref, "parent_contract_ref"),
            "scope": scope_name,
            "dimension": exact_text(dimension, "dimension"),
            "changed_path": exact_text(changed_path, "changed_path"),
            "before": frozen_before,
            "after": frozen_after,
            "mutated_case": frozen_case,
            "expected_earliest_owner": exact_text(
                expected_earliest_owner, "expected_earliest_owner"
            ),
            "expected_status": exact_text(expected_status, "expected_status"),
            "expected_error_code": exact_text(
                expected_error_code, "expected_error_code"
            ),
            "lineage_refs": exact_refs(lineage_refs, "lineage_refs", nonempty=True),
            "review_refs": exact_refs(review_refs, "review_refs", nonempty=True),
        }
        material = {
            "abi_version": SEMANTIC_MUTATION_ABI_VERSION,
            **{
                key: thaw_json(value)
                if key in {"before", "after", "mutated_case"}
                else list(value)
                if type(value) is tuple
                else value
                for key, value in values.items()
            },
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", SEMANTIC_MUTATION_ABI_VERSION)
        object.__setattr__(obj, "mutation_ref", stable_ref("semantic_mutation_v2", material))
        for name, value in values.items():
            object.__setattr__(obj, name, value)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "mutation_ref": self.mutation_ref,
            "parent_case_ref": self.parent_case_ref,
            "parent_contract_ref": self.parent_contract_ref,
            "scope": self.scope,
            "dimension": self.dimension,
            "changed_path": self.changed_path,
            "before": thaw_json(self.before),
            "after": thaw_json(self.after),
            "mutated_case": thaw_json(self.mutated_case),
            "expected_earliest_owner": self.expected_earliest_owner,
            "expected_status": self.expected_status,
            "expected_error_code": self.expected_error_code,
            "lineage_refs": list(self.lineage_refs),
            "review_refs": list(self.review_refs),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SemanticMutation":
        row = exact_fields(value, cls._FIELDS, "SemanticMutation")
        if row["abi_version"] != SEMANTIC_MUTATION_ABI_VERSION:
            raise ValueError("unsupported Semantic Mutation ABI")
        if type(row["mutated_case"]) is not dict:
            raise TypeError("mutated_case must be exact dict")
        rebuilt = cls.create(
            parent_case_ref=row["parent_case_ref"],
            parent_contract_ref=row["parent_contract_ref"],
            scope=row["scope"],
            dimension=row["dimension"],
            changed_path=row["changed_path"],
            before=row["before"],
            after=row["after"],
            mutated_case=row["mutated_case"],
            expected_earliest_owner=row["expected_earliest_owner"],
            expected_status=row["expected_status"],
            expected_error_code=row["expected_error_code"],
            lineage_refs=wire_refs(row["lineage_refs"], "lineage_refs", nonempty=True),
            review_refs=wire_refs(row["review_refs"], "review_refs", nonempty=True),
        )
        if rebuilt.mutation_ref != row["mutation_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical SemanticMutation")
        return rebuilt


@dataclass(frozen=True, init=False)
class MutationExecutionRequest:
    """Label-free mutation payload admitted to the authentic execution owner."""

    abi_version: int
    request_ref: str
    scope: str
    dimension: str
    changed_path: str
    mutated_case: Mapping[str, Any]

    _FIELDS = frozenset(
        {
            "abi_version",
            "request_ref",
            "scope",
            "dimension",
            "changed_path",
            "mutated_case",
        }
    )

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use MutationExecutionRequest.create")

    @classmethod
    def create(cls, mutation: SemanticMutation) -> "MutationExecutionRequest":
        if type(mutation) is not SemanticMutation:
            raise TypeError("mutation must be exact SemanticMutation")
        frozen_case = freeze_json(thaw_json(mutation.mutated_case))
        if not isinstance(frozen_case, Mapping):
            raise TypeError("mutated_case must freeze to a mapping")
        values = {
            "scope": mutation.scope,
            "dimension": mutation.dimension,
            "changed_path": mutation.changed_path,
            "mutated_case": thaw_json(frozen_case),
        }
        material = {
            "abi_version": MUTATION_EXECUTION_REQUEST_ABI_VERSION,
            **values,
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", MUTATION_EXECUTION_REQUEST_ABI_VERSION)
        object.__setattr__(
            obj,
            "request_ref",
            stable_ref("mutation_execution_request_v1", material),
        )
        object.__setattr__(obj, "scope", mutation.scope)
        object.__setattr__(obj, "dimension", mutation.dimension)
        object.__setattr__(obj, "changed_path", mutation.changed_path)
        object.__setattr__(obj, "mutated_case", frozen_case)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "request_ref": self.request_ref,
            "scope": self.scope,
            "dimension": self.dimension,
            "changed_path": self.changed_path,
            "mutated_case": thaw_json(self.mutated_case),
        }


@dataclass(frozen=True, init=False)
class MutationObservation:
    abi_version: int
    observation_ref: str
    mutation_ref: str
    actual_earliest_owner: str
    actual_status: str
    actual_error_code: str
    observed_artifact_ref: str
    matched_expectation: bool

    _FIELDS = frozenset(
        {
            "abi_version",
            "observation_ref",
            "mutation_ref",
            "actual_earliest_owner",
            "actual_status",
            "actual_error_code",
            "observed_artifact_ref",
            "matched_expectation",
        }
    )

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use MutationObservation.create")

    @classmethod
    def create(
        cls,
        *,
        mutation: SemanticMutation,
        result: MutationBoundaryResult,
    ) -> "MutationObservation":
        if type(mutation) is not SemanticMutation:
            raise TypeError("mutation must be exact SemanticMutation")
        if type(result) is not MutationBoundaryResult:
            raise TypeError("result must be exact MutationBoundaryResult")
        matched = (
            result.earliest_owner == mutation.expected_earliest_owner
            and result.status == mutation.expected_status
            and result.error_code == mutation.expected_error_code
        )
        material = {
            "abi_version": MUTATION_OBSERVATION_ABI_VERSION,
            "mutation_ref": mutation.mutation_ref,
            "actual_earliest_owner": result.earliest_owner,
            "actual_status": result.status,
            "actual_error_code": result.error_code,
            "observed_artifact_ref": result.artifact_ref,
            "matched_expectation": matched,
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", MUTATION_OBSERVATION_ABI_VERSION)
        object.__setattr__(obj, "observation_ref", stable_ref("mutation_observation_v2", material))
        object.__setattr__(obj, "mutation_ref", mutation.mutation_ref)
        object.__setattr__(obj, "actual_earliest_owner", result.earliest_owner)
        object.__setattr__(obj, "actual_status", result.status)
        object.__setattr__(obj, "actual_error_code", result.error_code)
        object.__setattr__(obj, "observed_artifact_ref", result.artifact_ref)
        object.__setattr__(obj, "matched_expectation", matched)
        return obj

    @property
    def passed(self) -> bool:
        return self.matched_expectation

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "observation_ref": self.observation_ref,
            "mutation_ref": self.mutation_ref,
            "actual_earliest_owner": self.actual_earliest_owner,
            "actual_status": self.actual_status,
            "actual_error_code": self.actual_error_code,
            "observed_artifact_ref": self.observed_artifact_ref,
            "matched_expectation": self.matched_expectation,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MutationObservation":
        row = exact_fields(value, cls._FIELDS, "MutationObservation")
        if row["abi_version"] != MUTATION_OBSERVATION_ABI_VERSION:
            raise ValueError("unsupported Mutation Observation ABI")
        material = {
            "abi_version": MUTATION_OBSERVATION_ABI_VERSION,
            "mutation_ref": exact_text(row["mutation_ref"], "mutation_ref"),
            "actual_earliest_owner": exact_text(
                row["actual_earliest_owner"], "actual_earliest_owner"
            ),
            "actual_status": exact_text(row["actual_status"], "actual_status"),
            "actual_error_code": exact_text(
                row["actual_error_code"], "actual_error_code"
            ),
            "observed_artifact_ref": exact_text(
                row["observed_artifact_ref"], "observed_artifact_ref"
            ),
            "matched_expectation": exact_bool(
                row["matched_expectation"], "matched_expectation"
            ),
        }
        observation_ref = stable_ref("mutation_observation_v2", material)
        if row["observation_ref"] != observation_ref:
            raise ValueError("non-canonical MutationObservation")
        obj = object.__new__(cls)
        object.__setattr__(obj, "observation_ref", observation_ref)
        for name, item in material.items():
            object.__setattr__(obj, name, item)
        if obj.as_dict() != dict(row):
            raise ValueError("non-canonical MutationObservation")
        return obj


class MutationGenerator:
    """Compile bounded reviewed contracts for one authentic source case."""

    def __init__(
        self,
        reviewed_contracts: tuple[object, ...] | None = None,
        *,
        compiler: object | None = None,
        max_mutations_per_case: int = MAX_REVIEWED_MUTATIONS_PER_CASE,
    ) -> None:
        from .r4_mutation_compiler import ReviewedMutationCompiler
        from .r4_supervision import MutationContract

        if type(max_mutations_per_case) is not int or not (
            1 <= max_mutations_per_case <= MAX_REVIEWED_MUTATIONS_PER_CASE
        ):
            raise ValueError("invalid mutation bound")
        if reviewed_contracts is None:
            self._contracts_by_case = None
            self._compiler = ReviewedMutationCompiler()
            self._maximum = max_mutations_per_case
            return
        if type(reviewed_contracts) is not tuple or any(
            type(row) is not MutationContract for row in reviewed_contracts
        ):
            raise TypeError("reviewed mutation contracts must be one exact tuple")
        if not reviewed_contracts:
            raise ValueError("reviewed mutation contracts cannot be empty")
        exact_compiler = ReviewedMutationCompiler() if compiler is None else compiler
        if type(exact_compiler) is not ReviewedMutationCompiler:
            raise TypeError("mutation compiler must be exact ReviewedMutationCompiler")
        by_case: dict[str, list[object]] = {}
        pair_refs: set[tuple[str, str]] = set()
        for contract in reviewed_contracts:
            pair = (contract.source_case_ref, contract.mutation_family_ref)
            if pair in pair_refs:
                raise ValueError("reviewed mutation contracts duplicate a case/family pair")
            pair_refs.add(pair)
            rows = by_case.setdefault(contract.source_case_ref, [])
            rows.append(contract)
            if len(rows) > max_mutations_per_case:
                raise ValueError("reviewed mutation contracts exceed the per-case bound")
        self._contracts_by_case = {
            case_ref: tuple(
                sorted(
                    rows,
                    key=lambda row: (
                        row.mutation_family_ref,
                        row.mutation_contract_ref,
                    ),
                )
            )
            for case_ref, rows in by_case.items()
        }
        self._compiler = exact_compiler
        self._maximum = max_mutations_per_case

    def generate(self, case: ExpandedCase) -> tuple[SemanticMutation, ...]:
        if type(case) is not ExpandedCase:
            raise TypeError("case must be exact ExpandedCase")
        if self._contracts_by_case is None:
            raise TypeError("reviewed mutation contracts are required")
        contracts = self._contracts_by_case.get(case.case_ref, ())
        return tuple(
            self._compiler.compile(case=case, contract=contract)
            for contract in contracts[: self._maximum]
        )


class MutationExecutor:
    """Execute mutations through an object implementing MutationExecutionOwner."""

    def __init__(self, owner: MutationExecutionOwner) -> None:
        if callable(owner) and not hasattr(owner, "execute_mutation"):
            raise TypeError("plain callback mutation runners are forbidden")
        if not isinstance(owner, MutationExecutionOwner):
            raise TypeError("owner must implement MutationExecutionOwner")
        self._owner = owner

    def execute(
        self, mutations: Iterable[SemanticMutation]
    ) -> tuple[MutationObservation, ...]:
        rows = tuple(mutations)
        if any(type(row) is not SemanticMutation for row in rows):
            raise TypeError("mutations must contain SemanticMutation")
        results: list[MutationObservation] = []
        for mutation in rows:
            request = MutationExecutionRequest.create(mutation)
            observed = self._owner.execute_mutation(request)
            if type(observed) is not MutationBoundaryResult:
                raise TypeError("mutation owner returned non-canonical result")
            results.append(MutationObservation.create(mutation=mutation, result=observed))
        return tuple(results)
