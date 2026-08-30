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
from .affordances import SemanticAffordanceIndex
from .authority import LinkedAuthority
from .config import RuntimeConfig
from .contributions import ContributionExpander
from .cycle import Orientation
from .expressions import (
    ApplicationFiller,
    BoundVariable,
    GroundedReference,
    LiteralValue,
    SemanticExpression,
    UnresolvedValue,
)
from .forms import EvidenceItem, EvidencePacket, FormResolver
from .forms import FormLattice
from .grounding import Grounder, GroundingResult
from .proposal_context import ProposalContext, ProposalContextBuilder
from .r3_codec import freeze_json, thaw_json
from .r4_expansion import ExpandedCase, SourceUniverse
from .r4_purpose import PURPOSES
from .r4_supervision import (
    MutationContract,
    ProposalTarget,
    RealizationRow,
    source_disposition_is_supervision_eligible,
)

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
    "DesignationBindingSuggestion",
    "DesignationCandidateSet",
    "ProposalRecipeSuggestion",
    "SourceAuthoringCache",
    "build_source_authoring_cache",
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
class DesignationBindingSuggestion:
    binding_ref: str
    source_case_ref: str
    surface_ref: str
    source_start: int
    source_end: int
    source_text: str
    unit_refs: tuple[str, ...]
    designation_fact_ref: str
    target_ref: str

    @classmethod
    def create(
        cls,
        *,
        source_case_ref: str,
        surface_ref: str,
        source_start: int,
        source_end: int,
        source_text: str,
        unit_refs: tuple[str, ...],
        designation_fact_ref: str,
        target_ref: str,
    ) -> "DesignationBindingSuggestion":
        if (
            type(source_start) is not int
            or type(source_end) is not int
            or source_start < 0
            or source_end <= source_start
        ):
            raise ValueError("designation suggestion has invalid source geometry")
        units = exact_ref_tuple(
            unit_refs,
            "unit_refs",
            nonempty=True,
            maximum=8,
            prefix="unit:",
            canonical_order=False,
        )
        material = {
            "source_case_ref": exact_case_ref(source_case_ref),
            "surface_ref": exact_ref(
                surface_ref,
                "surface_ref",
                prefix="reviewed_surface:",
            ),
            "source_start": source_start,
            "source_end": source_end,
            "source_text": exact_text(source_text, "source_text", maximum=4096),
            "unit_refs": list(units),
            "designation_fact_ref": exact_ref(
                designation_fact_ref,
                "designation_fact_ref",
                prefix="designation:",
            ),
            "target_ref": exact_ref(target_ref, "target_ref"),
        }
        return cls(
            binding_ref=stable_ref("designation_binding_suggestion", material),
            unit_refs=units,
            **{key: value for key, value in material.items() if key != "unit_refs"},
        )


@dataclass(frozen=True)
class DesignationCandidateSet:
    candidate_set_ref: str
    source_case_ref: str
    surface_ref: str
    bindings: tuple[DesignationBindingSuggestion, ...]

    @classmethod
    def create(
        cls,
        *,
        source_case_ref: str,
        surface_ref: str,
        bindings: tuple[DesignationBindingSuggestion, ...],
    ) -> "DesignationCandidateSet":
        if type(bindings) is not tuple or len(bindings) > 512 or any(
            type(row) is not DesignationBindingSuggestion for row in bindings
        ):
            raise TypeError("designation bindings must be one bounded exact tuple")
        case_ref = exact_case_ref(source_case_ref)
        exact_surface_ref = exact_ref(
            surface_ref,
            "surface_ref",
            prefix="reviewed_surface:",
        )
        if any(
            row.source_case_ref != case_ref or row.surface_ref != exact_surface_ref
            for row in bindings
        ):
            raise ValueError("designation binding crosses its case or surface")
        identities = tuple(row.binding_ref for row in bindings)
        if len(identities) != len(set(identities)):
            raise ValueError("designation candidate set contains duplicate bindings")
        order = tuple(
            (row.source_start, row.source_end, row.target_ref, row.designation_fact_ref)
            for row in bindings
        )
        if any(left >= right for left, right in zip(order, order[1:])):
            raise ValueError("designation bindings must be in canonical geometry order")
        material = {
            "source_case_ref": case_ref,
            "surface_ref": exact_surface_ref,
            "binding_refs": list(identities),
        }
        return cls(
            candidate_set_ref=stable_ref("designation_candidate_set", material),
            source_case_ref=case_ref,
            surface_ref=exact_surface_ref,
            bindings=bindings,
        )


@dataclass(frozen=True)
class ProposalRecipeSuggestion:
    suggestion_ref: str
    source_case_ref: str
    target_kind: str
    family_ref: str
    normalized_family_key: tuple[object, ...]
    case_parameters: Mapping[str, object]
    selectable: bool

    @classmethod
    def create(
        cls,
        *,
        source_case_ref: str,
        target_kind: str,
        normalized_family_key: tuple[object, ...],
        case_parameters: Mapping[str, object],
    ) -> "ProposalRecipeSuggestion":
        if target_kind not in {"derive", "abstain", "verification_rejection"}:
            raise ValueError("unsupported proposal recipe suggestion target")
        if (
            type(normalized_family_key) is not tuple
            or not normalized_family_key
            or len(normalized_family_key) > 64
        ):
            raise ValueError("proposal recipe family key must be bounded and nonempty")
        family_key = tuple(freeze_json(item) for item in normalized_family_key)
        parameters = _frozen_mapping(case_parameters, "case_parameters")
        family_material = {
            "target_kind": target_kind,
            "normalized_family_key": thaw_json(family_key),
        }
        family_ref = stable_ref("proposal_recipe_family_suggestion", family_material)
        material = {
            "source_case_ref": exact_case_ref(source_case_ref),
            "target_kind": target_kind,
            "family_ref": family_ref,
            "normalized_family_key": thaw_json(family_key),
            "case_parameters": thaw_json(parameters),
            "selectable": False,
        }
        return cls(
            suggestion_ref=stable_ref("proposal_recipe_suggestion", material),
            source_case_ref=material["source_case_ref"],
            target_kind=target_kind,
            family_ref=family_ref,
            normalized_family_key=family_key,
            case_parameters=parameters,
            selectable=False,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "suggestion_ref": self.suggestion_ref,
            "source_case_ref": self.source_case_ref,
            "target_kind": self.target_kind,
            "family_ref": self.family_ref,
            "normalized_family_key": thaw_json(self.normalized_family_key),
            "case_parameters": thaw_json(self.case_parameters),
            "selectable": self.selectable,
        }


def _semantic_kind(authority: LinkedAuthority, ref: str) -> str:
    atom = authority.atoms.get(ref)
    if atom is not None:
        return atom.kind
    if ref.startswith("scope_value:"):
        return "scope_value"
    raise ValueError("proposal recipe family references absent semantic authority")


def _expression_family(
    expression: SemanticExpression,
    authority: LinkedAuthority,
) -> Mapping[str, object]:
    nodes: dict[str, tuple[str, int]] = {
        row.application_ref: ("application", index)
        for index, row in enumerate(expression.applications)
    }
    nodes.update(
        (row.scope_ref, ("scope", index))
        for index, row in enumerate(expression.scope_operators)
    )
    nodes.update(
        (row.link_ref, ("link", index))
        for index, row in enumerate(expression.expression_links)
    )
    nodes.update(
        (row.binder_ref, ("binder", index))
        for index, row in enumerate(expression.binders)
    )
    if len(nodes) != (
        len(expression.applications)
        + len(expression.scope_operators)
        + len(expression.expression_links)
        + len(expression.binders)
    ):
        raise ValueError("proposal recipe expression has colliding node identities")
    variables = {
        row.variable_ref: index for index, row in enumerate(expression.binders)
    }
    unresolved = {
        row.unresolved_ref: row for row in expression.unresolved_fillers
    }

    def node(ref: str) -> list[object]:
        try:
            kind, index = nodes[ref]
        except KeyError as exc:
            raise ValueError("proposal recipe references an unknown expression node") from exc
        return [kind, index]

    def filler(value: object) -> list[object]:
        if type(value) is GroundedReference:
            return ["grounded", _semantic_kind(authority, value.target_ref)]
        if type(value) is LiteralValue:
            return ["literal", value.value_type]
        if type(value) is BoundVariable:
            if value.variable_ref not in variables:
                raise ValueError("proposal recipe contains an unbound variable")
            return ["bound_variable", variables[value.variable_ref]]
        if type(value) is ApplicationFiller:
            return ["expression_node", *node(value.node_ref)]
        if type(value) is UnresolvedValue:
            row = unresolved.get(value.unresolved_ref)
            if row is None:
                raise ValueError("proposal recipe unresolved value lacks its typed owner")
            return [
                "unresolved",
                row.contribution_kind,
                list(row.expected_kinds),
                row.critical,
            ]
        raise TypeError("proposal recipe contains an unsupported filler")

    def bindings(rows: tuple[object, ...]) -> list[object]:
        return [
            [row.role_ref, filler(row.filler)]
            for row in rows
        ]

    return freeze_json(
        {
            "applications": [
                {
                    "operator": row.operator,
                    "predicate_kind": _semantic_kind(authority, row.predicate_ref),
                    "roles": bindings(row.roles),
                    "qualifiers": bindings(row.qualifiers),
                }
                for row in expression.applications
            ],
            "roots": [node(ref) for ref in expression.root_refs],
            "scopes": [
                {
                    "operator_type": row.operator_type,
                    "value_kind": _semantic_kind(authority, row.value_ref),
                    "operand": node(row.operand_ref),
                }
                for row in expression.scope_operators
            ],
            "links": [
                {
                    "link_type": row.link_type,
                    "operands": [node(ref) for ref in row.operand_refs],
                }
                for row in expression.expression_links
            ],
            "binders": [
                {
                    "variable": variables[row.variable_ref],
                    "body": node(row.body_ref),
                }
                for row in expression.binders
            ],
            "unresolved": [
                {
                    "owner": node(row.owner_application_ref),
                    "role_ref": row.role_ref,
                    "contribution_kind": row.contribution_kind,
                    "expected_kinds": list(row.expected_kinds),
                    "critical": row.critical,
                }
                for row in expression.unresolved_fillers
            ],
        }
    )


def _proposal_recipe_suggestion(
    case: ExpandedCase,
    authority: LinkedAuthority,
) -> ProposalRecipeSuggestion:
    disposition = case.source_disposition.value
    target_kind = {
        "semantic": "derive",
        "explicit_gap": "abstain",
        "verification_rejection": "verification_rejection",
    }[disposition]
    contract = case.contract
    family: dict[str, object] = {
        "mode": contract.expected_mode.value,
        "outcome_kind": contract.outcome_kind.value,
        "expression_relation": contract.expression_relation.value,
    }
    if target_kind == "derive":
        family["expressions"] = [
            thaw_json(_expression_family(expression, authority))
            for expression in contract.expected_expressions
        ]
    else:
        gap = contract.expected_gap
        if gap is None:
            raise ValueError("nonsemantic proposal suggestion lacks its expected gap")
        family["gap"] = {
            "kind": gap.kind,
            "status": gap.status,
            "recommended_owner": gap.recommended_owner,
            "safe_response_action": gap.safe_response_action,
            "error_shape": (
                None if gap.error_code is None else gap.error_code.split(":", 1)[0]
            ),
        }
        if target_kind == "verification_rejection":
            family["expected_owner"] = contract.expected_owner
    parameters = {
        "contract_ref": contract.contract_ref,
        "surface_ref": case.surface_ref,
        "context_ref": case.context_ref,
        "assertion_refs": list(contract.assertion_refs),
        "expected_expression_refs": [
            expression.expression_ref for expression in contract.expected_expressions
        ],
        "expected_gap": (
            None if contract.expected_gap is None else contract.expected_gap.as_dict()
        ),
    }
    return ProposalRecipeSuggestion.create(
        source_case_ref=case.case_ref,
        target_kind=target_kind,
        normalized_family_key=(family,),
        case_parameters=parameters,
    )


@dataclass(frozen=True)
class SourceAuthoringCache:
    cases: tuple[ExpandedCase, ...]
    cases_by_ref: Mapping[str, ExpandedCase]
    form_lattices_by_case: Mapping[str, FormLattice]
    grounding_results_by_case: Mapping[str, GroundingResult]
    proposal_contexts_by_case: Mapping[str, ProposalContext]
    designation_sets_by_case: Mapping[str, DesignationCandidateSet]
    proposal_recipe_suggestions_by_case: Mapping[str, ProposalRecipeSuggestion]
    operation_counts: Mapping[str, int]

    def __post_init__(self) -> None:
        if type(self.cases) is not tuple or any(
            type(case) is not ExpandedCase for case in self.cases
        ):
            raise TypeError("source authoring cases must be exact ExpandedCase values")
        case_refs = tuple(case.case_ref for case in self.cases)
        if len(case_refs) != len(set(case_refs)):
            raise ValueError("source authoring cases contain duplicate identities")
        expected = set(case_refs)
        for name in (
            "cases_by_ref",
            "form_lattices_by_case",
            "grounding_results_by_case",
            "proposal_contexts_by_case",
            "designation_sets_by_case",
            "proposal_recipe_suggestions_by_case",
        ):
            mapping = getattr(self, name)
            if not isinstance(mapping, Mapping) or set(mapping) != expected:
                raise ValueError(f"{name} must index the exact eligible case set")
            object.__setattr__(self, name, MappingProxyType(dict(mapping)))
        if not isinstance(self.operation_counts, Mapping) or any(
            type(value) is not int or value < 0
            for value in self.operation_counts.values()
        ):
            raise TypeError("source authoring operation counts are invalid")
        object.__setattr__(
            self,
            "operation_counts",
            MappingProxyType(dict(self.operation_counts)),
        )

    @property
    def operation_count(self) -> int:
        return sum(self.operation_counts.values())


def build_source_authoring_cache(
    *,
    cases: tuple[ExpandedCase, ...],
    authority: LinkedAuthority,
    form_pack: Mapping[str, object],
    config: RuntimeConfig,
) -> SourceAuthoringCache:
    """Build each eligible source artifact once without proposal/runtime output."""

    if type(cases) is not tuple or any(type(case) is not ExpandedCase for case in cases):
        raise TypeError("cases must contain exact ExpandedCase values")
    if type(authority) is not LinkedAuthority:
        raise TypeError("authority must be exact LinkedAuthority")
    if type(config) is not RuntimeConfig:
        raise TypeError("config must be exact RuntimeConfig")
    if not isinstance(form_pack, Mapping):
        raise TypeError("form_pack must be a mapping")
    eligible = tuple(
        case
        for case in cases
        if source_disposition_is_supervision_eligible(case.source_disposition)
    )
    case_refs = tuple(case.case_ref for case in eligible)
    if len(case_refs) != len(set(case_refs)):
        raise ValueError("eligible source cases contain duplicate identities")

    resolver = FormResolver(form_pack, config)

    class _DesignationStore:
        def build_index(self):
            return authority.designations

    grounder = Grounder(
        authority=authority,
        config=config,
        form_pack=form_pack,
        form_pack_hash=resolver.form_pack_hash,
        designation_store=_DesignationStore(),
    )
    affordances = SemanticAffordanceIndex(authority, config)
    expander = ContributionExpander(affordances, config)
    context_builder = ProposalContextBuilder(
        authority,
        affordances,
        config,
        form_pack=form_pack,
    )
    cases_by_ref: dict[str, ExpandedCase] = {}
    lattices: dict[str, FormLattice] = {}
    groundings: dict[str, GroundingResult] = {}
    contexts: dict[str, ProposalContext] = {}
    designation_sets: dict[str, DesignationCandidateSet] = {}
    proposal_suggestions: dict[str, ProposalRecipeSuggestion] = {}
    operations = {
        "form_lattice_builds": 0,
        "grounding_builds": 0,
        "proposal_context_builds": 0,
        "designation_span_probes": 0,
        "proposal_recipe_normalizations": 0,
    }
    for case in eligible:
        cases_by_ref[case.case_ref] = case
        evidence_item = EvidenceItem.create(
            source="text",
            content=case.surface,
            source_ref=stable_ref("r4_authoring_source", case.case_ref),
            provenance_refs=(case.surface_ref,),
            adapter_receipt_ref=None,
        )
        packet = EvidencePacket.create(
            items=(evidence_item,),
            source_text=case.surface,
            form_pack_hash=resolver.form_pack_hash,
        )
        lattice = resolver.resolve_evidence(packet)
        operations["form_lattice_builds"] += 1
        grounding = grounder.ground_lattice(lattice, case.contract.revision_pin)
        operations["grounding_builds"] += 1
        contributions = expander.expand(grounding, lattice)
        constraints = case.contract.situation_constraints
        orientation = Orientation.create(
            session_ref="session:r4-authoring",
            turn_ref=case.case_ref,
            source_text=case.surface,
            mode=case.contract.expected_mode,
            participant_frame="participant:user",
            temporal_frame="now",
            participants=("participant:user", "participant:system"),
            active_turn_ref=case.case_ref,
            event_refs=(),
            focus_refs=(),
            obligation_refs=(),
            capability_summary=tuple(constraints.get("capability_refs", ())),
            permission_summary=tuple(constraints.get("permission_refs", ())),
            budgets={"proposal": config.max_applications},
            scanned_atom_count=0,
            index_probes=(),
            visited_refs=(),
            revision_pin=case.contract.revision_pin,
        )
        context = context_builder.build(
            orientation=orientation,
            evidence=packet,
            form_lattice=lattice,
            grounding_result=grounding,
            contributions=contributions,
        )
        operations["proposal_context_builds"] += 1

        word_units = tuple(unit for unit in lattice.units if unit.source_text.strip())
        bindings: list[DesignationBindingSuggestion] = []
        for start in range(len(word_units)):
            for width in range(1, min(8, len(word_units) - start) + 1):
                operations["designation_span_probes"] += 1
                span = word_units[start : start + width]
                source_start = span[0].source_start
                source_end = span[-1].source_end
                source_text = case.surface[source_start:source_end]
                facts = authority.designations.facts_for_surface(
                    source_text.strip(),
                    case.language,
                )
                if len(facts) > config.max_designations_per_span:
                    raise ValueError("designation target bound exceeded for one exact span")
                for fact in facts:
                    if fact.target_ref not in authority.atoms:
                        raise ValueError("designation fact targets absent authority")
                    bindings.append(
                        DesignationBindingSuggestion.create(
                            source_case_ref=case.case_ref,
                            surface_ref=case.surface_ref,
                            source_start=source_start,
                            source_end=source_end,
                            source_text=source_text,
                            unit_refs=tuple(unit.unit_ref for unit in span),
                            designation_fact_ref=fact.designation_fact_ref,
                            target_ref=fact.target_ref,
                        )
                    )
        bindings.sort(
            key=lambda row: (
                row.source_start,
                row.source_end,
                row.target_ref,
                row.designation_fact_ref,
            )
        )
        candidate_set = DesignationCandidateSet.create(
            source_case_ref=case.case_ref,
            surface_ref=case.surface_ref,
            bindings=tuple(bindings),
        )
        if not candidate_set.bindings and case.source_disposition.value == "semantic":
            raise ValueError("semantic source case lacks explicit designation evidence")
        lattices[case.case_ref] = lattice
        groundings[case.case_ref] = grounding
        contexts[case.case_ref] = context
        designation_sets[case.case_ref] = candidate_set
        proposal_suggestions[case.case_ref] = _proposal_recipe_suggestion(
            case,
            authority,
        )
        operations["proposal_recipe_normalizations"] += 1
    return SourceAuthoringCache(
        cases=eligible,
        cases_by_ref=cases_by_ref,
        form_lattices_by_case=lattices,
        grounding_results_by_case=groundings,
        proposal_contexts_by_case=contexts,
        designation_sets_by_case=designation_sets,
        proposal_recipe_suggestions_by_case=proposal_suggestions,
        operation_counts=operations,
    )


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
