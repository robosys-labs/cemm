"""Reviewed R4 mutations with authentic earliest-owner execution.

Expected labels are review contracts only.  Mutation observations are created
exclusively from a concrete owner result; the executor never copies expected
labels into observed fields and rejects plain callback functions.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable

from .canonical import stable_ref
from .r3_codec import (
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

__all__ = [
    "SEMANTIC_MUTATION_ABI_VERSION",
    "MUTATION_OBSERVATION_ABI_VERSION",
    "MutationBoundaryResult",
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
    def execute_mutation(self, mutation: "SemanticMutation") -> MutationBoundaryResult:
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


@dataclass(frozen=True)
class _MutationSpec:
    scope: str
    dimension: str
    path: str
    owner: str
    status: str
    code: str


_SPECS = (
    _MutationSpec("contract", "invalid_role", "contract.expected_expressions[0].applications[0].roles[0].role_ref", "expected-contract-compiler", "rejected", "invalid_role_ref"),
    _MutationSpec("contract", "missing_predicate", "contract.expected_expressions[0].applications[0].predicate_ref", "expected-contract-compiler", "rejected", "authority_ref_missing"),
    _MutationSpec("contract", "dangling_root", "contract.expected_expressions[0].root_refs[0]", "semantic-expression", "rejected", "unknown_root_ref"),
    _MutationSpec("environment", "permission_removed", "environment.situation_constraints.permission_refs", "EVALUATE", "denied", "permission_missing"),
    _MutationSpec("environment", "adapter_removed", "environment.situation_constraints.adapter_refs", "EVALUATE", "adapter_missing", "adapter_missing"),
    _MutationSpec("environment", "source_untrusted", "environment.situation_constraints.evidence_policy_refs", "EVALUATE", "contested", "untrusted_observation"),
    _MutationSpec("persistence", "stale_revision", "contract.revision_pin.world_revision", "EFFECT", "stale_revision", "stale_revision"),
    _MutationSpec("contract", "decision_action_mismatch", "contract.expected_decision.action", "expected-contract-compiler", "rejected", "decision_contract_mismatch"),
)


class MutationGenerator:
    """Generate bounded one-dimension mutations from one authentic case."""

    def __init__(self, *, max_mutations_per_case: int = len(_SPECS)) -> None:
        if type(max_mutations_per_case) is not int or not 1 <= max_mutations_per_case <= len(_SPECS):
            raise ValueError("invalid mutation bound")
        self._maximum = max_mutations_per_case

    def generate(self, case: ExpandedCase) -> tuple[SemanticMutation, ...]:
        if type(case) is not ExpandedCase:
            raise TypeError("case must be exact ExpandedCase")
        rows: list[SemanticMutation] = []
        for spec in _SPECS[: self._maximum]:
            payload = copy.deepcopy(case.as_dict())
            changed = self._apply(payload, spec)
            if changed is None:
                continue
            before, after = changed
            rows.append(
                SemanticMutation.create(
                    parent_case_ref=case.case_ref,
                    parent_contract_ref=case.contract_ref,
                    scope=spec.scope,
                    dimension=spec.dimension,
                    changed_path=spec.path,
                    before=before,
                    after=after,
                    mutated_case=payload,
                    expected_earliest_owner=spec.owner,
                    expected_status=spec.status,
                    expected_error_code=spec.code,
                    lineage_refs=(
                        case.case_ref,
                        case.contract_ref,
                        stable_ref("mutation_family", spec.dimension),
                    ),
                    review_refs=case.contract.review_provenance_refs,
                )
            )
        return tuple(rows)

    @staticmethod
    def _apply(payload: dict[str, Any], spec: _MutationSpec) -> tuple[Any, Any] | None:
        contract = payload["contract"]
        expressions = contract.get("expected_expressions", [])
        if spec.dimension in {"invalid_role", "missing_predicate", "dangling_root"}:
            if not expressions or not expressions[0].get("applications"):
                return None
            expression = expressions[0]
            if spec.dimension == "invalid_role":
                roles = expression["applications"][0].get("roles", [])
                if not roles:
                    return None
                before = roles[0]["role_ref"]
                roles[0]["role_ref"] = "not-a-role"
                return before, roles[0]["role_ref"]
            if spec.dimension == "missing_predicate":
                app = expression["applications"][0]
                before = app["predicate_ref"]
                app["predicate_ref"] = "entity:authority-ref-does-not-exist"
                return before, app["predicate_ref"]
            before = expression["root_refs"][0]
            expression["root_refs"][0] = "application:dangling-root"
            return before, expression["root_refs"][0]
        if spec.dimension == "decision_action_mismatch":
            before = contract["expected_decision"]["action"]
            contract["expected_decision"]["action"] = "request_effect"
            contract["expected_decision"]["status"] = "supported"
            return before, contract["expected_decision"]["action"]
        if spec.dimension == "stale_revision":
            before = contract["revision_pin"]["world_revision"]
            contract["revision_pin"]["world_revision"] = before + 1
            return before, contract["revision_pin"]["world_revision"]
        environment = payload.setdefault("environment", {})
        constraints = environment.setdefault("situation_constraints", {})
        if spec.dimension == "permission_removed":
            before = copy.deepcopy(constraints.get("permission_refs", []))
            constraints["permission_refs"] = []
            return before, []
        if spec.dimension == "adapter_removed":
            before = copy.deepcopy(constraints.get("adapter_refs", []))
            constraints["adapter_refs"] = []
            return before, []
        before = copy.deepcopy(constraints.get("evidence_policy_refs", []))
        constraints["evidence_policy_refs"] = ["policy:evidence:untrusted_conversation"]
        constraints["trusted_observation"] = False
        return before, constraints["evidence_policy_refs"]


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
            observed = self._owner.execute_mutation(mutation)
            if type(observed) is not MutationBoundaryResult:
                raise TypeError("mutation owner returned non-canonical result")
            results.append(MutationObservation.create(mutation=mutation, result=observed))
        return tuple(results)
