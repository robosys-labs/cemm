"""Bounded worksheet-local records for deterministic R4 supervision authoring.

These records are intentionally not persistent supervision ABIs.  They carry
purpose-scoped recipes and inert candidates only until reviewed concrete rows
are published through the existing authenticated review-bundle boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from ._r4_source_codec import (
    exact_case_ref,
    exact_content_ref_tuple,
    exact_ref,
    exact_ref_tuple,
    exact_review_refs,
    exact_text,
)
from .canonical import canonical_bytes, stable_ref
from .forms import FormLattice
from .proposal_context import ProposalContext
from .r3_codec import freeze_json, thaw_json
from .r4_expansion import ExpandedCase, SourceUniverse
from .r4_purpose import PURPOSES
from .r4_supervision import MutationContract, ProposalTarget, RealizationRow

RECIPE_KINDS = ("proposal", "designation", "realization", "mutation")
CANDIDATE_KINDS = RECIPE_KINDS
MAX_RECIPE_FAMILIES_PER_KIND_PURPOSE = 128
MAX_RECIPE_INSTANCES_PER_KIND = 512
MAX_RECIPE_MEMBERS = 4_096
MAX_CANDIDATE_REFS = 128
MAX_RECIPE_PARAMETERS = 128
MAX_OPERATION_COUNT_FIELDS = 64

__all__ = [
    "AuthoringRecipe",
    "AuthoringCandidate",
    "AuthoringResult",
    "validate_authoring_recipes",
    "RECIPE_KINDS",
    "MAX_RECIPE_FAMILIES_PER_KIND_PURPOSE",
    "MAX_RECIPE_INSTANCES_PER_KIND",
]


def _purpose(value: object) -> str:
    purpose = exact_text(value, "purpose", maximum=16)
    if purpose not in PURPOSES:
        raise ValueError("unsupported R4 authoring purpose")
    return purpose


def _kind(value: object, name: str, allowed: tuple[str, ...]) -> str:
    kind = exact_text(value, name, maximum=32)
    if kind not in allowed:
        raise ValueError(f"unsupported {name.replace('_', ' ')}")
    return kind


def _frozen_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or len(value) > MAX_RECIPE_PARAMETERS:
        raise TypeError(f"{name} must be a bounded mapping")
    frozen = freeze_json(dict(value))
    if not isinstance(frozen, Mapping):
        raise TypeError(f"{name} must freeze to a mapping")
    return frozen


def _exception_codes(value: object) -> tuple[str, ...]:
    if type(value) is not tuple or len(value) > 32:
        raise TypeError("exception_codes must be a bounded exact tuple")
    codes = tuple(exact_text(code, "exception code", maximum=128) for code in value)
    if len(codes) != len(set(codes)) or any(
        left >= right for left, right in zip(codes, codes[1:])
    ):
        raise ValueError("exception_codes must be unique and canonical")
    return codes


@dataclass(frozen=True, init=False)
class AuthoringRecipe:
    recipe_ref: str
    recipe_kind: str
    purpose: str
    normalized_family_key: tuple[object, ...]
    member_case_refs: tuple[str, ...]
    ancestry_refs: tuple[str, ...]
    reviewed_parameters: Mapping[str, object]
    review_refs: tuple[str, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use AuthoringRecipe.create")

    @classmethod
    def create(
        cls,
        *,
        recipe_kind: str,
        purpose: str,
        normalized_family_key: tuple[object, ...],
        member_case_refs: tuple[str, ...],
        ancestry_refs: tuple[str, ...],
        reviewed_parameters: Mapping[str, object],
        review_refs: tuple[str, ...],
    ) -> "AuthoringRecipe":
        if (
            type(normalized_family_key) is not tuple
            or not normalized_family_key
            or len(normalized_family_key) > 64
        ):
            raise ValueError("normalized_family_key must be a bounded nonempty tuple")
        family_key = tuple(freeze_json(item) for item in normalized_family_key)
        members = exact_content_ref_tuple(
            member_case_refs,
            "member_case_refs",
            nonempty=True,
            maximum=MAX_RECIPE_MEMBERS,
            prefix="expanded_case_v2:",
        )
        ancestors = exact_ref_tuple(
            ancestry_refs,
            "ancestry_refs",
            nonempty=False,
            maximum=MAX_RECIPE_INSTANCES_PER_KIND,
            prefix="authoring_recipe:",
        )
        parameters = _frozen_mapping(reviewed_parameters, "reviewed_parameters")
        reviews = exact_review_refs(review_refs)
        material = {
            "recipe_kind": _kind(recipe_kind, "recipe_kind", RECIPE_KINDS),
            "purpose": _purpose(purpose),
            "normalized_family_key": thaw_json(family_key),
            "member_case_refs": list(members),
            "ancestry_refs": list(ancestors),
            "reviewed_parameters": thaw_json(parameters),
            "review_refs": list(reviews),
        }
        instance = object.__new__(cls)
        object.__setattr__(instance, "recipe_ref", stable_ref("authoring_recipe", material))
        object.__setattr__(instance, "recipe_kind", material["recipe_kind"])
        object.__setattr__(instance, "purpose", material["purpose"])
        object.__setattr__(instance, "normalized_family_key", family_key)
        object.__setattr__(instance, "member_case_refs", members)
        object.__setattr__(instance, "ancestry_refs", ancestors)
        object.__setattr__(instance, "reviewed_parameters", parameters)
        object.__setattr__(instance, "review_refs", reviews)
        return instance


@dataclass(frozen=True, init=False)
class AuthoringCandidate:
    candidate_ref: str
    candidate_kind: str
    source_case_ref: str
    purpose: str
    recipe_ref: str
    input_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    generator_source_ref: str
    provenance_refs: tuple[str, ...]
    verification_receipt_ref: str
    selectable: bool
    exception_codes: tuple[str, ...]
    proposed_row: Mapping[str, object] | None

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use AuthoringCandidate.create")

    @classmethod
    def create(
        cls,
        *,
        candidate_kind: str,
        source_case_ref: str,
        purpose: str,
        recipe_ref: str,
        input_refs: tuple[str, ...],
        evidence_refs: tuple[str, ...],
        generator_source_ref: str,
        provenance_refs: tuple[str, ...],
        verification_receipt_ref: str,
        selectable: bool,
        exception_codes: tuple[str, ...],
        proposed_row: Mapping[str, object] | None,
    ) -> "AuthoringCandidate":
        if type(selectable) is not bool:
            raise TypeError("selectable must be an exact bool")
        exceptions = _exception_codes(exception_codes)
        row = None if proposed_row is None else _frozen_mapping(proposed_row, "proposed_row")
        if selectable and row is None:
            raise ValueError("selectable candidate requires a concrete proposed row")
        if selectable and exceptions:
            raise ValueError("selectable candidate cannot retain exception codes")
        material = {
            "candidate_kind": _kind(
                candidate_kind,
                "candidate_kind",
                CANDIDATE_KINDS,
            ),
            "source_case_ref": exact_case_ref(source_case_ref),
            "purpose": _purpose(purpose),
            "recipe_ref": exact_ref(recipe_ref, "recipe_ref", prefix="authoring_recipe:"),
            "input_refs": list(
                exact_ref_tuple(
                    input_refs,
                    "input_refs",
                    nonempty=True,
                    maximum=MAX_CANDIDATE_REFS,
                )
            ),
            "evidence_refs": list(
                exact_ref_tuple(
                    evidence_refs,
                    "evidence_refs",
                    nonempty=False,
                    maximum=MAX_CANDIDATE_REFS,
                )
            ),
            "generator_source_ref": exact_ref(
                generator_source_ref,
                "generator_source_ref",
                prefix="generator_source:",
            ),
            "provenance_refs": list(
                exact_ref_tuple(
                    provenance_refs,
                    "provenance_refs",
                    nonempty=True,
                    maximum=MAX_CANDIDATE_REFS,
                )
            ),
            "verification_receipt_ref": exact_ref(
                verification_receipt_ref,
                "verification_receipt_ref",
                prefix="authoring_verification:",
            ),
            "selectable": selectable,
            "exception_codes": list(exceptions),
            "proposed_row": None if row is None else thaw_json(row),
        }
        instance = object.__new__(cls)
        object.__setattr__(instance, "candidate_ref", stable_ref("authoring_candidate", material))
        for field, value in material.items():
            if field in {"input_refs", "evidence_refs", "provenance_refs", "exception_codes"}:
                value = tuple(value)
            if field == "proposed_row" and value is not None:
                value = row
            object.__setattr__(instance, field, value)
        return instance


def validate_authoring_recipes(recipes: tuple[AuthoringRecipe, ...]) -> int:
    if type(recipes) is not tuple:
        raise TypeError("recipes must be an exact tuple")
    counts: dict[tuple[str, str], int] = {}
    kind_counts: dict[str, int] = {}
    family_owner: dict[tuple[str, str, bytes], str] = {}
    member_owner: dict[tuple[str, str], AuthoringRecipe] = {}
    operations = 0
    for recipe in recipes:
        if type(recipe) is not AuthoringRecipe:
            raise TypeError("recipes must contain exact AuthoringRecipe values")
        operations += 1 + len(recipe.member_case_refs)
        bucket = (recipe.recipe_kind, recipe.purpose)
        kind_counts[recipe.recipe_kind] = kind_counts.get(recipe.recipe_kind, 0) + 1
        if kind_counts[recipe.recipe_kind] > MAX_RECIPE_INSTANCES_PER_KIND:
            raise ValueError("more than 512 purpose-scoped recipe instances per kind")
        counts[bucket] = counts.get(bucket, 0) + 1
        if counts[bucket] > MAX_RECIPE_FAMILIES_PER_KIND_PURPOSE:
            raise ValueError("more than 128 recipe families in one kind/purpose")
        family_identity = (
            recipe.recipe_kind,
            recipe.purpose,
            canonical_bytes(recipe.normalized_family_key),
        )
        prior = family_owner.setdefault(family_identity, recipe.recipe_ref)
        if prior != recipe.recipe_ref:
            raise ValueError("normalized family-key collision")
        for case_ref in recipe.member_case_refs:
            key = (recipe.recipe_kind, case_ref)
            prior_recipe = member_owner.get(key)
            if prior_recipe is not None and prior_recipe.purpose != recipe.purpose:
                raise ValueError("recipe case ownership crosses purposes")
            if prior_recipe is not None:
                raise ValueError("recipe member has more than one owner")
            member_owner[key] = recipe
    return operations


@dataclass(frozen=True)
class AuthoringResult:
    universe: SourceUniverse
    supervised_cases: tuple[ExpandedCase, ...]
    cases_by_ref: Mapping[str, ExpandedCase]
    form_lattices_by_case: Mapping[str, FormLattice]
    proposal_contexts_by_case: Mapping[str, ProposalContext]
    proposal_targets_by_case: Mapping[str, ProposalTarget]
    proposals: tuple[AuthoringCandidate, ...]
    designations: tuple[AuthoringCandidate, ...]
    realizations: tuple[RealizationRow, ...]
    mutation_contracts: tuple[MutationContract, ...]
    mutation_families: tuple["ReviewedMutationFamily", ...]  # noqa: F821 -- Task 12
    recipes: tuple[AuthoringRecipe, ...]
    effect_projection: "NormalEffectProjection | None"  # noqa: F821 -- Task 12
    operation_counts: Mapping[str, int]
    linear_operation_bound: int
    max_recipe_families_per_kind_purpose: int
    max_recipe_instances_per_kind: int
    max_designation_targets_per_span: int
    max_realization_variants_per_case: int
    max_mutation_families_per_case: int

    def __post_init__(self) -> None:
        if type(self.universe) is not SourceUniverse:
            raise TypeError("authoring universe must be exact SourceUniverse")
        if type(self.supervised_cases) is not tuple or any(
            type(case) is not ExpandedCase for case in self.supervised_cases
        ):
            raise TypeError("supervised_cases must contain exact ExpandedCase values")
        validate_authoring_recipes(self.recipes)
        for field in ("proposals", "designations"):
            rows = getattr(self, field)
            if type(rows) is not tuple or any(
                type(row) is not AuthoringCandidate for row in rows
            ):
                raise TypeError(f"{field} must contain exact AuthoringCandidate values")
        for field, expected_type in (
            ("realizations", RealizationRow),
            ("mutation_contracts", MutationContract),
        ):
            rows = getattr(self, field)
            if type(rows) is not tuple or any(type(row) is not expected_type for row in rows):
                raise TypeError(f"{field} contains a noncanonical value")
        universe_refs = {case.case_ref for case in self.universe.cases}
        supervised_refs = {case.case_ref for case in self.supervised_cases}
        if not supervised_refs.issubset(universe_refs):
            raise ValueError("supervised cases must belong to the source universe")
        mappings = (
            ("cases_by_ref", self.cases_by_ref, ExpandedCase),
            ("form_lattices_by_case", self.form_lattices_by_case, FormLattice),
            ("proposal_contexts_by_case", self.proposal_contexts_by_case, ProposalContext),
            ("proposal_targets_by_case", self.proposal_targets_by_case, ProposalTarget),
        )
        for name, mapping, expected_type in mappings:
            if not isinstance(mapping, Mapping):
                raise TypeError(f"{name} must be a mapping")
            if any(type(value) is not expected_type for value in mapping.values()):
                raise TypeError(f"{name} contains a noncanonical value")
            object.__setattr__(self, name, MappingProxyType(dict(mapping)))
        if set(self.cases_by_ref) != universe_refs:
            raise ValueError("cases_by_ref must index the complete universe")
        if type(self.mutation_families) is not tuple:
            raise TypeError("mutation_families must be an exact tuple")
        if not isinstance(self.operation_counts, Mapping) or len(self.operation_counts) > MAX_OPERATION_COUNT_FIELDS:
            raise TypeError("operation_counts must be a bounded mapping")
        counts: dict[str, int] = {}
        for key, value in self.operation_counts.items():
            name = exact_text(key, "operation count name", maximum=128)
            if type(value) is not int or value < 0:
                raise ValueError("operation counts must be nonnegative integers")
            counts[name] = value
        object.__setattr__(self, "operation_counts", MappingProxyType(counts))
        for field in (
            "linear_operation_bound",
            "max_recipe_families_per_kind_purpose",
            "max_recipe_instances_per_kind",
            "max_designation_targets_per_span",
            "max_realization_variants_per_case",
            "max_mutation_families_per_case",
        ):
            value = getattr(self, field)
            if type(value) is not int or value < 0:
                raise ValueError(f"{field} must be a nonnegative integer")
        if self.operation_count > self.linear_operation_bound:
            raise ValueError("authoring operation count exceeds its linear bound")

    @property
    def case_count(self) -> int:
        return len(self.universe.cases)

    @property
    def supervised_case_count(self) -> int:
        return len(self.supervised_cases)

    @property
    def context_build_count(self) -> int:
        return self.operation_counts.get("proposal_context_builds", 0)

    @property
    def mutation_contract_count(self) -> int:
        return len(self.mutation_contracts)

    @property
    def operation_count(self) -> int:
        return sum(self.operation_counts.values())
