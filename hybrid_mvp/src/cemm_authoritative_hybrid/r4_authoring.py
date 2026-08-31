"""Bounded worksheet-local records for deterministic R4 supervision authoring.

These records are intentionally not persistent supervision ABIs.  They carry
purpose-scoped recipes and inert candidates only until reviewed concrete rows
are published through the existing authenticated review-bundle boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, get_args

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
from .contributions import ContributionExpander, ContributionKind
from .cycle import Orientation
from .expressions import (
    ApplicationFiller,
    BoundVariable,
    GroundedReference,
    LiteralValue,
    SemanticExpression,
    UnresolvedValue,
)
from .literal_codec import decode_literal_slot
from .forms import EvidenceItem, EvidencePacket, FormResolver
from .forms import FormLattice
from .grounding import Grounder, GroundingResult
from .proposal_context import (
    ApplicationFrameSlot,
    ContributionSlot,
    ExpressionLinkSlot,
    ProposalContext,
    ProposalContextBuilder,
    ReferenceSlot,
    ScopeSlot,
    VariableSlot,
)
from .r4_derivation_compiler import ReviewedDerivationCompiler
from .r4_realization_compiler import (
    ReviewedRealizationCompiler,
    response_subject_from_proposal,
)
from .r3_codec import freeze_json, thaw_json
from .r4_expansion import ExpandedCase, SourceUniverse
from .r4_purpose import PURPOSES
from .r4_supervision import (
    BlueprintAction,
    DerivationBlueprint,
    GroundedSelectorBinding,
    ExpressionSetResponseSubject,
    LiteralAlignment,
    MutationContract,
    ProposalTarget,
    RealizationRow,
    RealizationSlot,
    SourceAssignmentBlueprint,
    SourceAssignmentEntry,
    SourceSpan,
    StructuralSelectorBinding,
    TypedGapResponseSubject,
    TypedAbstention,
    VerificationRejection,
    VerifierRejectionResponseSubject,
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
_ALL_CONTRIBUTION_KINDS = frozenset(get_args(ContributionKind))

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
    "build_reviewed_proposal_authoring",
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


_OWNER_TO_ABSTENTION_PHASE = {
    "form-context": "orient",
    "authority-link": "orient",
    "recursive-composer": "propose",
    "exact-verifier": "verify",
    "decision-query-proof": "evaluate",
    "epistemic-state": "evaluate",
    "capability-effect": "effect",
    "learning-dialogue": "evaluate",
    "persistence-recovery": "effect",
    "response-contract": "realize",
    "runtime-activation": "propose",
}
_SAFE_ACTION_TO_DISPOSITION = {
    "request_proposal_review": "frontier",
    "stop_without_surface": "frontier",
    "request_clarification": "clarify",
    "reject_candidate": "reject",
}


def _source_spans(
    context: ProposalContext,
    source_unit_refs: tuple[str, ...],
    surface_ref: str,
) -> tuple[SourceSpan, ...]:
    by_unit = {unit_ref: (start, end) for unit_ref, start, end in context.source_unit_spans}
    return tuple(
        SourceSpan.create(surface_ref=surface_ref, start=by_unit[unit_ref][0], end=by_unit[unit_ref][1])
        for unit_ref in sorted(source_unit_refs, key=lambda ref: by_unit[ref])
    )


class _BlueprintBuilder:
    def __init__(self, *, case: ExpandedCase, context: ProposalContext) -> None:
        self.case = case
        self.context = context
        self.selectors: list[GroundedSelectorBinding | StructuralSelectorBinding] = []
        self.actions: list[BlueprintAction] = []
        self.assignment_targets: dict[str, tuple[str, int, str | None]] = {}
        self.used_contributions: dict[str, ContributionSlot] = {}

    def structural(self, selector_kind: str, value_ref: str) -> int:
        handle = len(self.selectors)
        self.selectors.append(
            StructuralSelectorBinding.create(
                selector_handle=handle,
                selector_kind=selector_kind,
                value_ref=value_ref,
            )
        )
        return handle

    def grounded(
        self,
        *,
        selector_kind: str,
        graph_component_ref: str,
        semantic_kind_ref: str,
        source_unit_refs: tuple[str, ...],
        source_selector_kind: str,
        source_selector_ref: str,
    ) -> int:
        handle = len(self.selectors)
        self.selectors.append(
            GroundedSelectorBinding.create(
                selector_handle=handle,
                selector_kind=selector_kind,
                source_case_ref=self.case.case_ref,
                surface_ref=self.case.surface_ref,
                graph_component_ref=graph_component_ref,
                semantic_kind_ref=semantic_kind_ref,
                spans=_source_spans(self.context, source_unit_refs, self.case.surface_ref),
                source_selector_kind=source_selector_kind,
                source_selector_ref=source_selector_ref,
            )
        )
        return handle

    def action(self, action_type: str, selector_handles: tuple[int, ...]) -> int:
        index = len(self.actions)
        self.actions.append(
            BlueprintAction.create(
                action_index=index,
                action_type=action_type,
                selector_handles=selector_handles,
            )
        )
        return index

    def remember_assignment(
        self,
        contribution: ContributionSlot,
        *,
        assignment_kind: str,
        target_action_index: int,
        target_role_ref: str | None,
    ) -> None:
        self.used_contributions[contribution.slot_ref] = contribution
        for unit_ref in contribution.source_unit_refs:
            previous = self.assignment_targets.get(unit_ref)
            current = (contribution.slot_ref, target_action_index, target_role_ref)
            if previous is not None and previous != current:
                raise ValueError(f"one source unit maps to more than one proposal action: {unit_ref}")
            self.assignment_targets[unit_ref] = current

    def source_assignments(self) -> SourceAssignmentBlueprint:
        residual_by_source = {
            row.source_unit_ref: row for row in self.context.residual_evidence
        }
        residual_contribution_kinds = {"binder", "connector", "discourse", "qualifier", "scope"}
        if self.case.contract.expression_relation.value == "conflict":
            residual_contribution_kinds = set(_ALL_CONTRIBUTION_KINDS)
        residual_contribution_by_source: dict[str, ContributionSlot] = {}
        for contribution in self.context.contribution_slots:
            if contribution.kind not in residual_contribution_kinds:
                continue
            for unit_ref in contribution.source_unit_refs:
                residual_contribution_by_source.setdefault(unit_ref, contribution)
        rows: list[SourceAssignmentEntry] = []
        for unit_ref in self.context.source_unit_refs:
            target = self.assignment_targets.get(unit_ref)
            if target is None:
                residual = residual_by_source.get(unit_ref)
                residual_contribution = residual_contribution_by_source.get(unit_ref)
                if residual is None and residual_contribution is None:
                    raise ValueError(f"observed source unit lacks exact assignment: {unit_ref}")
                if residual is not None:
                    contribution_slot_ref = residual.residual_ref
                    contribution_kind = residual.contribution_kind
                    critical = residual.critical
                else:
                    contribution_slot_ref = residual_contribution.slot_ref
                    contribution_kind = residual_contribution.kind
                    critical = False
                rows.append(
                    SourceAssignmentEntry.create(
                        source_unit_ref=unit_ref,
                        contribution_slot_ref=contribution_slot_ref,
                        contribution_kind=contribution_kind,
                        assignment_kind="residual",
                        target_action_index=None,
                        target_role_ref=None,
                        residual_kind=contribution_kind,
                        critical=critical,
                    )
                )
                continue
            contribution_ref, action_index, role_ref = target
            contribution = self.used_contributions[contribution_ref]
            if contribution.kind == "predicate":
                assignment_kind = "predicate"
            elif contribution.kind in {"anchor", "literal", "binder", "open_variable"}:
                assignment_kind = "role"
            elif contribution.kind in {"qualifier", "reference", "scope", "connector", "discourse"}:
                assignment_kind = contribution.kind
            else:
                raise ValueError("unsupported contribution kind for proposal assignment")
            rows.append(
                SourceAssignmentEntry.create(
                    source_unit_ref=unit_ref,
                    contribution_slot_ref=contribution.slot_ref,
                    contribution_kind=contribution.kind,
                    assignment_kind=assignment_kind,
                    target_action_index=action_index,
                    target_role_ref=role_ref,
                    residual_kind=None,
                    critical=False,
                )
            )
        return SourceAssignmentBlueprint.create(
            observed_source_unit_refs=self.context.source_unit_refs,
            assignments=tuple(rows),
        )


def _mode_slot(context: ProposalContext, mode: str):
    matches = tuple(row for row in context.mode_slots if row.mode == mode)
    if len(matches) != 1:
        raise ValueError("reviewed proposal requires one matching mode slot")
    return matches[0]


def _contribution_for_source(
    *,
    context: ProposalContext,
    kind: str,
    source_unit_refs: tuple[str, ...],
) -> ContributionSlot:
    matches = _unique_contributions(tuple(
        row
        for row in context.contribution_slots
        if row.kind == kind and row.source_unit_refs == source_unit_refs
    ))
    if len(matches) != 1:
        raise ValueError("reviewed source evidence does not resolve to one contribution")
    return matches[0]


def _unique_contributions(rows: tuple[ContributionSlot, ...] | list[ContributionSlot]) -> tuple[ContributionSlot, ...]:
    unique: dict[str, ContributionSlot] = {}
    for row in rows:
        unique[row.slot_ref] = row
    return tuple(unique[slot_ref] for slot_ref in sorted(unique))


def _frame_for_application(context: ProposalContext, application) -> ApplicationFrameSlot:
    matches = tuple(
        row
        for row in context.application_frames
        if row.operator_ref == application.operator
        and row.predicate_target_ref == application.predicate_ref
    )
    if len(matches) > 1:
        grounded_role_targets = {
            (binding.role_ref, binding.filler.target_ref)
            for binding in (*application.roles, *application.qualifiers)
            if type(binding.filler) is GroundedReference
        }
        explicit_role_refs = {binding.role_ref for binding in (*application.roles, *application.qualifiers)}
        role_compatible = tuple(
            row
            for row in matches
            if set(row.derived_role_targets).issubset(grounded_role_targets)
            and (set(row.required_roles) - {role for role, _target in row.derived_role_targets}).issubset(explicit_role_refs)
        )
        if role_compatible:
            matches = role_compatible
    if len(matches) > 1:
        derived_count = max(len(row.derived_role_targets) for row in matches)
        matches = tuple(row for row in matches if len(row.derived_role_targets) == derived_count)
    if len(matches) > 1:
        source_count = max(len(row.source_unit_refs) for row in matches)
        matches = tuple(row for row in matches if len(row.source_unit_refs) == source_count)
    if len(matches) != 1:
        raise ValueError("reviewed expression does not resolve to one application frame")
    return matches[0]


def _predicate_contribution(
    context: ProposalContext,
    frame: ApplicationFrameSlot,
) -> ContributionSlot:
    matches = _unique_contributions(tuple(
        row
        for row in context.contribution_slots
        if row.kind == "predicate"
        and row.target_ref == frame.predicate_target_ref
        and frame.structural_role_ref in row.output_ports
        and row.source_unit_refs == frame.source_unit_refs
    ))
    if len(matches) != 1:
        scored = tuple(
            (
                len(set(row.provenance_refs) & set(frame.provenance_refs)),
                len(row.provenance_refs),
                row,
            )
            for row in matches
        )
        if scored:
            best_score = max((first, second) for first, second, _row in scored)
            matches = tuple(
                row
                for first, second, row in scored
                if (first, second) == best_score
            )
    if len(matches) != 1:
        raise ValueError("reviewed application frame lacks one predicate contribution")
    return matches[0]


def _role_contribution(
    *,
    context: ProposalContext,
    role_ref: str,
    filler: object,
    forbidden_source_unit_refs: frozenset[str] = frozenset(),
) -> ContributionSlot:
    matches: list[ContributionSlot] = []
    def collect(forbidden: frozenset[str]) -> list[ContributionSlot]:
        collected: list[ContributionSlot] = []
        for row in context.contribution_slots:
            if role_ref not in row.output_ports:
                continue
            if forbidden and set(row.source_unit_refs) & forbidden:
                continue
            if type(filler) is GroundedReference and row.target_ref == filler.target_ref:
                collected.append(row)
            elif type(filler) is LiteralValue and row.kind == "literal":
                try:
                    literal_kind, literal_value = decode_literal_slot(row)
                except (TypeError, ValueError):
                    continue
                if literal_kind == filler.value_type and literal_value == filler.value:
                    collected.append(row)
        return collected

    matches = collect(forbidden_source_unit_refs)
    if not matches and forbidden_source_unit_refs:
        matches = collect(frozenset())
    matches = list(_unique_contributions(matches))
    if len(matches) != 1:
        raise ValueError("reviewed role filler does not resolve to one contribution")
    return matches[0]


def _reference_slot(
    context: ProposalContext,
    role_ref: str,
    filler: GroundedReference,
) -> ReferenceSlot:
    matches = tuple(
        row
        for row in context.reference_slots
        if row.target_ref == filler.target_ref and role_ref in row.compatible_roles
    )
    if len(matches) != 1:
        raise ValueError("reviewed reference filler does not resolve to one context reference")
    return matches[0]


def _reference_slot_for_binding(
    *,
    builder: _BlueprintBuilder,
    context: ProposalContext,
    frame: ApplicationFrameSlot,
    role_ref: str,
    filler: GroundedReference,
) -> ReferenceSlot:
    matches = tuple(
        row
        for row in context.reference_slots
        if row.target_ref == filler.target_ref and role_ref in row.compatible_roles
    )
    if len(matches) == 1:
        return matches[0]
    available_source_bearing = tuple(
        row
        for row in matches
        if row.source_unit_refs
        and all(unit_ref not in builder.assignment_targets for unit_ref in row.source_unit_refs)
    )
    if len(available_source_bearing) == 1:
        return available_source_bearing[0]
    if len(available_source_bearing) > 1:
        spans = {
            unit_ref: (start, end)
            for unit_ref, start, end in context.source_unit_spans
        }
        frame_units = tuple(spans[unit_ref] for unit_ref in frame.source_unit_refs)
        frame_start = min(start for start, _end in frame_units)
        frame_end = max(end for _start, end in frame_units)
        scored = []
        for row in available_source_bearing:
            ref_units = tuple(spans[unit_ref] for unit_ref in row.source_unit_refs)
            ref_start = min(start for start, _end in ref_units)
            ref_end = max(end for _start, end in ref_units)
            if ref_end <= frame_start:
                distance = frame_start - ref_end
            elif frame_end <= ref_start:
                distance = ref_start - frame_end
            else:
                distance = 0
            scored.append((distance, ref_start, ref_end, row))
        best = min((distance, start, end) for distance, start, end, _row in scored)
        nearest = tuple(row for distance, start, end, row in scored if (distance, start, end) == best)
        if len(nearest) == 1:
            return nearest[0]
    sourceless = tuple(row for row in matches if not row.source_unit_refs)
    if len(sourceless) == 1:
        return sourceless[0]
    if sourceless and {
        (row.target_ref, row.target_kind, row.compatible_roles, row.resolution_kind)
        for row in sourceless
    } == {
        (
            sourceless[0].target_ref,
            sourceless[0].target_kind,
            sourceless[0].compatible_roles,
            sourceless[0].resolution_kind,
        )
    }:
        return tuple(sorted(sourceless, key=lambda row: row.slot_ref))[0]
    raise ValueError("reviewed reference filler does not resolve to one context reference")


def _reference_contribution(
    context: ProposalContext,
    reference: ReferenceSlot,
) -> ContributionSlot:
    matches = _unique_contributions(tuple(
        row
        for row in context.contribution_slots
        if row.kind == "reference"
        and row.target_ref == reference.target_ref
        and row.source_unit_refs == reference.source_unit_refs
        and any(role_ref in row.output_ports for role_ref in reference.compatible_roles)
    ))
    if len(matches) != 1:
        raise ValueError("reviewed reference slot does not resolve to one contribution")
    return matches[0]


def _scope_slot(context: ProposalContext, scope) -> ScopeSlot:
    matches = tuple(
        row
        for row in context.scope_slots
        if row.operator_type == scope.operator_type and row.value_ref == scope.value_ref
    )
    if len(matches) != 1:
        raise ValueError("reviewed scope does not resolve to one context scope")
    return matches[0]


def _link_slot(context: ProposalContext, link) -> ExpressionLinkSlot:
    matches = tuple(
        row for row in context.expression_link_slots if row.link_type == link.link_type
    )
    if len(matches) != 1:
        raise ValueError("reviewed expression link does not resolve to one context link")
    return matches[0]


def _variable_slot(context: ProposalContext, binder, expression: SemanticExpression) -> VariableSlot:
    body_apps = {
        row.application_ref: row
        for row in expression.applications
    }
    candidates: list[VariableSlot] = []
    for slot in context.variable_slots:
        for app in body_apps.values():
            if app.application_ref != binder.body_ref:
                continue
            frame = _frame_for_application(context, app)
            if slot.application_frame_ref != frame.slot_ref:
                continue
            if any(
                type(binding.filler) is BoundVariable
                and binding.filler.variable_ref == binder.variable_ref
                and binding.role_ref == slot.role_ref
                for binding in app.roles
            ):
                candidates.append(slot)
    if len(candidates) != 1:
        raise ValueError("reviewed variable binder does not resolve to one context variable")
    return candidates[0]


def _semantic_kind_ref(value: str | None) -> str:
    return f"semantic_kind:{value or 'structural'}"


def _build_derivation_blueprint(
    *,
    case: ExpandedCase,
    context: ProposalContext,
    expression: SemanticExpression,
) -> DerivationBlueprint:
    builder = _BlueprintBuilder(case=case, context=context)
    mode = _mode_slot(context, case.contract.expected_mode.value)
    context_handle = builder.structural("context_slot", context.context_ref)
    residual_unit_refs = {
        row.source_unit_ref for row in context.residual_evidence
    }
    mode_source_refs = set(mode.source_unit_refs)
    if mode.mode == "QUERY":
        mode_source_refs |= {
            unit_ref
            for row in context.contribution_slots
            if row.kind == "discourse"
            for unit_ref in row.source_unit_refs
            if unit_ref not in residual_unit_refs
        }
    unit_span_index = {
        unit_ref: (start, end) for unit_ref, start, end in context.source_unit_spans
    }
    selected_mode_source_unit_refs = tuple(
        sorted(mode_source_refs, key=lambda ref: unit_span_index[ref])
    )
    mode_contributions = tuple(
        row
        for row in context.contribution_slots
        if row.kind == "discourse"
        and row.source_unit_refs
        and set(row.source_unit_refs).issubset(mode_source_refs)
    )
    exact_mode_contributions = tuple(
        row for row in mode_contributions if row.source_unit_refs == selected_mode_source_unit_refs
    )
    if len(exact_mode_contributions) == 1:
        mode_contribution = exact_mode_contributions[0]
        mode_handle = builder.grounded(
            selector_kind="mode_slot",
            graph_component_ref=mode.slot_ref,
            semantic_kind_ref=_semantic_kind_ref("discourse"),
            source_unit_refs=mode_contribution.source_unit_refs,
            source_selector_kind="contribution",
            source_selector_ref=mode_contribution.slot_ref,
        )
        mode_assignment_contributions = (mode_contribution,)
    elif mode_contributions:
        mode_handle = builder.grounded(
            selector_kind="mode_slot",
            graph_component_ref=mode.slot_ref,
            semantic_kind_ref=_semantic_kind_ref("discourse"),
            source_unit_refs=selected_mode_source_unit_refs,
            source_selector_kind="source_unit",
            source_selector_ref=selected_mode_source_unit_refs[0],
        )
        mode_assignment_contributions = mode_contributions
    else:
        mode_handle = builder.structural("mode_slot", mode.slot_ref)
        mode_assignment_contributions = ()
    builder.action("select_context", (context_handle,))
    mode_action_index = builder.action("select_mode", (mode_handle,))
    for mode_contribution in mode_assignment_contributions:
        builder.remember_assignment(
            mode_contribution,
            assignment_kind="discourse",
            target_action_index=mode_action_index,
            target_role_ref=None,
        )

    frame_by_application: dict[str, ApplicationFrameSlot] = {}
    deferred_designation_predicates: list[tuple[ContributionSlot, int]] = []
    for application in expression.applications:
        frame = _frame_for_application(context, application)
        frame_by_application[application.application_ref] = frame
        designation = context.designation(frame.designation_slot_ref)
        if designation is None:
            raise ValueError("reviewed application frame lacks designation slot")
        designation_handle = builder.grounded(
            selector_kind="designation_slot",
            graph_component_ref=designation.slot_ref,
            semantic_kind_ref=_semantic_kind_ref(designation.target_kind),
            source_unit_refs=designation.source_unit_refs,
            source_selector_kind="source_unit",
            source_selector_ref=designation.source_unit_refs[0],
        )
        builder.action("select_designation", (designation_handle,))
        local_handle = builder.structural("local_node", application.application_ref)
        predicate = _predicate_contribution(context, frame)
        designation_predicate_owns_source = (
            application.operator == "op:designation"
            and any(
                binding.role_ref == "role:surface"
                and type(binding.filler) is BoundVariable
                for binding in application.roles
            )
        )
        if application.operator == "op:designation" and not designation_predicate_owns_source:
            frame_handle = builder.grounded(
                selector_kind="frame_slot",
                graph_component_ref=frame.slot_ref,
                semantic_kind_ref=_semantic_kind_ref(frame.predicate_kind),
                source_unit_refs=frame.source_unit_refs,
                source_selector_kind="source_unit",
                source_selector_ref=frame.source_unit_refs[0],
            )
        else:
            frame_handle = builder.grounded(
                selector_kind="frame_slot",
                graph_component_ref=frame.slot_ref,
                semantic_kind_ref=_semantic_kind_ref(frame.predicate_kind),
                source_unit_refs=predicate.source_unit_refs,
                source_selector_kind="contribution",
                source_selector_ref=predicate.slot_ref,
            )
        action_index = builder.action("instantiate_operator", (local_handle, frame_handle))
        if application.operator != "op:designation" or designation_predicate_owns_source:
            builder.remember_assignment(
                predicate,
                assignment_kind="predicate",
                target_action_index=action_index,
                target_role_ref=None,
            )
        else:
            deferred_designation_predicates.append((predicate, action_index))

    for application in expression.applications:
        frame = frame_by_application[application.application_ref]
        for binding in (*application.roles, *application.qualifiers):
            filler = binding.filler
            sibling_reference_units = frozenset(
                unit_ref
                for sibling in (*application.roles, *application.qualifiers)
                if sibling is not binding
                and type(sibling.filler) is GroundedReference
                and (sibling.role_ref, sibling.filler.target_ref) not in frame.derived_role_targets
                for reference in context.reference_slots
                if reference.target_ref == sibling.filler.target_ref
                and sibling.role_ref in reference.compatible_roles
                for unit_ref in reference.source_unit_refs
            )
            if (
                type(filler) is GroundedReference
                and (binding.role_ref, filler.target_ref) in frame.derived_role_targets
            ):
                continue
            if type(filler) is ApplicationFiller:
                variant = builder.structural("variant_tag", "action_variant:role")
                parent = builder.structural("local_node", application.application_ref)
                role = builder.structural("role_ref", binding.role_ref)
                child = builder.structural("local_node", filler.node_ref)
                builder.action("bind_nested_application", (variant, parent, role, child))
                continue
            if type(filler) is BoundVariable:
                continue
            if type(filler) is UnresolvedValue:
                raise ValueError("semantic derivation cannot bind unresolved filler")
            if type(filler) is GroundedReference:
                try:
                    reference = _reference_slot_for_binding(
                        builder=builder,
                        context=context,
                        frame=frame,
                        role_ref=binding.role_ref,
                        filler=filler,
                    )
                except ValueError:
                    contribution = _role_contribution(
                        context=context,
                        role_ref=binding.role_ref,
                        filler=filler,
                        forbidden_source_unit_refs=frozenset(builder.assignment_targets),
                    )
                else:
                    app = builder.structural("local_node", application.application_ref)
                    role = builder.structural("role_ref", binding.role_ref)
                    if reference.source_unit_refs:
                        contribution = _reference_contribution(context, reference)
                        ref_handle = builder.grounded(
                            selector_kind="reference_slot",
                            graph_component_ref=reference.slot_ref,
                            semantic_kind_ref=_semantic_kind_ref(reference.target_kind),
                            source_unit_refs=reference.source_unit_refs,
                            source_selector_kind="contribution",
                            source_selector_ref=contribution.slot_ref,
                        )
                    else:
                        contribution = None
                        ref_handle = builder.structural("reference_slot", reference.slot_ref)
                    action_index = builder.action("bind_reference", (app, role, ref_handle))
                    if contribution is not None:
                        builder.remember_assignment(
                            contribution,
                            assignment_kind="reference",
                            target_action_index=action_index,
                            target_role_ref=binding.role_ref,
                        )
                    continue
            else:
                contribution = _role_contribution(
                    context=context,
                    role_ref=binding.role_ref,
                    filler=filler,
                    forbidden_source_unit_refs=sibling_reference_units,
                )
            app = builder.structural("local_node", application.application_ref)
            role = builder.structural("role_ref", binding.role_ref)
            contribution_handle = builder.grounded(
                selector_kind="contribution_slot",
                graph_component_ref=contribution.slot_ref,
                semantic_kind_ref=_semantic_kind_ref(contribution.target_kind or contribution.kind),
                source_unit_refs=contribution.source_unit_refs,
                source_selector_kind="contribution",
                source_selector_ref=contribution.slot_ref,
            )
            action_index = builder.action("bind_role", (app, role, contribution_handle))
            builder.remember_assignment(
                contribution,
                assignment_kind="role",
                target_action_index=action_index,
                target_role_ref=binding.role_ref,
            )

    for scope in expression.scope_operators:
        slot = _scope_slot(context, scope)
        local = builder.structural("local_node", scope.scope_ref)
        contribution = _contribution_for_source(
            context=context,
            kind="scope",
            source_unit_refs=slot.source_unit_refs,
        )
        slot_handle = builder.grounded(
            selector_kind="scope_slot",
            graph_component_ref=slot.slot_ref,
            semantic_kind_ref=_semantic_kind_ref("scope_value"),
            source_unit_refs=slot.source_unit_refs,
            source_selector_kind="contribution",
            source_selector_ref=contribution.slot_ref,
        )
        operand = builder.structural("local_node", scope.operand_ref)
        action_index = builder.action("attach_scope", (local, slot_handle, operand))
        builder.remember_assignment(
            contribution,
            assignment_kind="scope",
            target_action_index=action_index,
            target_role_ref=None,
        )

    for link in expression.expression_links:
        slot = _link_slot(context, link)
        variant = builder.structural("variant_tag", "action_variant:link")
        local = builder.structural("local_node", link.link_ref)
        link_contribution = None
        for contribution_kind in ("connector", "discourse"):
            try:
                link_contribution = _contribution_for_source(
                    context=context,
                    kind=contribution_kind,
                    source_unit_refs=slot.source_unit_refs,
                )
            except ValueError:
                continue
            break
        if link_contribution is None:
            raise ValueError("reviewed expression link lacks exact source contribution")
        slot_handle = builder.grounded(
            selector_kind="expression_link_slot",
            graph_component_ref=slot.slot_ref,
            semantic_kind_ref=_semantic_kind_ref("link"),
            source_unit_refs=slot.source_unit_refs,
            source_selector_kind="contribution",
            source_selector_ref=link_contribution.slot_ref,
        )
        operands = tuple(builder.structural("local_node", ref) for ref in link.operand_refs)
        action_index = builder.action("bind_nested_application", (variant, local, slot_handle, *operands))
        builder.remember_assignment(
            link_contribution,
            assignment_kind=link_contribution.kind,
            target_action_index=action_index,
            target_role_ref=None,
        )

    for binder in expression.binders:
        slot = _variable_slot(context, binder, expression)
        local = builder.structural("local_node", binder.binder_ref)
        variable_contributions = tuple(
            row
            for row in context.contribution_slots
            if row.kind in {"open_variable", "binder"}
            and row.source_unit_refs
            and set(row.source_unit_refs).issubset(set(slot.source_unit_refs))
        )
        exact_variable_contribution = tuple(
            row for row in variable_contributions if row.source_unit_refs == slot.source_unit_refs
        )
        if len(exact_variable_contribution) == 1:
            variable_selector_source_kind = "contribution"
            variable_selector_source_ref = exact_variable_contribution[0].slot_ref
            assignment_contributions = exact_variable_contribution
        else:
            variable_selector_source_kind = "source_unit"
            variable_selector_source_ref = slot.source_unit_refs[0]
            assignment_contributions = variable_contributions
        slot_handle = builder.grounded(
            selector_kind="variable_slot",
            graph_component_ref=slot.slot_ref,
            semantic_kind_ref=_semantic_kind_ref("open_variable"),
            source_unit_refs=slot.source_unit_refs,
            source_selector_kind=variable_selector_source_kind,
            source_selector_ref=variable_selector_source_ref,
        )
        body = builder.structural("local_node", binder.body_ref)
        action_index = builder.action("project_variable", (local, slot_handle, body))
        for contribution in assignment_contributions:
            builder.remember_assignment(
                contribution,
                assignment_kind="role",
                target_action_index=action_index,
                target_role_ref=slot.role_ref,
            )

    for predicate, action_index in deferred_designation_predicates:
        if all(unit_ref not in builder.assignment_targets for unit_ref in predicate.source_unit_refs):
            builder.remember_assignment(
                predicate,
                assignment_kind="predicate",
                target_action_index=action_index,
                target_role_ref=None,
            )

    builder.action("complete_program", ())
    return DerivationBlueprint.create(
        selector_bindings=tuple(builder.selectors),
        actions=tuple(builder.actions),
        root_local_refs=expression.root_refs,
        expected_expression_ref=expression.expression_ref,
        source_assignment_blueprint=builder.source_assignments(),
    )


def _proposal_target_for_case(
    *,
    case: ExpandedCase,
    context: ProposalContext,
    review_refs: tuple[str, ...],
) -> ProposalTarget:
    if case.source_disposition.value == "semantic":
        derivations = tuple(
            _build_derivation_blueprint(case=case, context=context, expression=expression)
            for expression in case.contract.expected_expressions
        )
        relation = "single" if len(derivations) == 1 else "conflict"
        return ProposalTarget.create(
            source_case_ref=case.case_ref,
            target_kind="derive",
            expected_expression_refs=tuple(
                sorted(expression.expression_ref for expression in case.contract.expected_expressions)
            ),
            match_policy="exact",
            expected_expression_relation=relation,
            derivations=tuple(sorted(derivations, key=lambda row: row.blueprint_ref)),
            abstention=None,
            verification_rejection=None,
            review_refs=review_refs,
        )
    gap = case.contract.expected_gap
    if gap is None:
        raise ValueError("nonsemantic proposal target lacks expected gap")
    if case.source_disposition.value == "explicit_gap":
        abstention = TypedAbstention.create(
            gap_kind_ref=f"gap_kind:{gap.kind}",
            critical=True,
            earliest_owner=_OWNER_TO_ABSTENTION_PHASE[gap.recommended_owner],
            safe_disposition=_SAFE_ACTION_TO_DISPOSITION[gap.safe_response_action],
        )
        return ProposalTarget.create(
            source_case_ref=case.case_ref,
            target_kind="abstain",
            expected_expression_refs=(),
            match_policy="exact",
            expected_expression_relation="none",
            derivations=(),
            abstention=abstention,
            verification_rejection=None,
            review_refs=review_refs,
        )
    if gap.error_code is None:
        raise ValueError("verification rejection lacks source error code")
    namespace, separator, error_name = gap.error_code.partition(":")
    if namespace != "verification" or separator != ":" or not error_name:
        raise ValueError("verification rejection source error is not canonical")
    rejection = VerificationRejection.create(
        input_kind="adversarial_blueprint",
        adversarial_blueprint_ref=stable_ref(
            "adversarial_blueprint",
            {
                "case_ref": case.case_ref,
                "normalized_assertions": thaw_json(case.contract.normalized_assertions),
            },
        ),
        mutation_payload_ref=None,
        expected_owner="verify",
        verification_error_code=f"verification_error:{error_name}",
        rejection_disposition="reject",
        critical=True,
    )
    return ProposalTarget.create(
        source_case_ref=case.case_ref,
        target_kind="verification_rejection",
        expected_expression_refs=(),
        match_policy="exact",
        expected_expression_relation="none",
        derivations=(),
        abstention=None,
        verification_rejection=rejection,
        review_refs=review_refs,
    )


def _selection_recipe_rows(selection: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    rows = selection.get("proposal_recipe_selections")
    if type(rows) is not list:
        raise TypeError("reviewed selection proposal recipes must be an exact list")
    return tuple(rows)


def _designation_selection_rows(selection: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    rows = selection.get("designation_selections")
    if type(rows) is not list:
        raise TypeError("reviewed selection designations must be an exact list")
    return tuple(rows)


def _neutral_realization_surface(proposal: ProposalTarget) -> str:
    if proposal.target_kind == "derive":
        return "Acknowledged."
    if proposal.target_kind == "abstain":
        return "I need more reviewed evidence before I can answer."
    if proposal.target_kind == "verification_rejection":
        return "I rejected that invalid candidate."
    raise ValueError("unknown proposal target kind")


def _realization_family_key(
    *,
    case: ExpandedCase,
    proposal: ProposalTarget,
    surface: str,
) -> tuple[object, ...]:
    subject = response_subject_from_proposal(proposal)
    response = case.contract.expected_response
    return (
        "realization",
        subject.subject_kind,
        proposal.expected_expression_relation,
        case.language,
        f"response_action:{response.discourse_action}",
        response.polarity_ref,
        response.modality_ref,
        response.epistemic_status_ref,
        "participant:system",
        "participant:user",
        surface,
    )


def _realization_slot_for_subject(subject) -> RealizationSlot:
    if type(subject) is ExpressionSetResponseSubject:
        return RealizationSlot.create(
            slot_ref="response_slot:subject",
            semantic_ref=subject.response_subject_ref,
            required=True,
            qualifier_refs=(),
        )
    if type(subject) is TypedGapResponseSubject:
        return RealizationSlot.create(
            slot_ref="response_slot:gap",
            semantic_ref=subject.typed_gap.abstention_ref,
            required=True,
            qualifier_refs=(),
        )
    if type(subject) is VerifierRejectionResponseSubject:
        return RealizationSlot.create(
            slot_ref="response_slot:verifier_rejection",
            semantic_ref=subject.verifier_rejection.verification_rejection_ref,
            required=True,
            qualifier_refs=(),
        )
    raise TypeError("unknown response subject")


def _realization_row_for_case(
    *,
    case: ExpandedCase,
    proposal: ProposalTarget,
    review_refs: tuple[str, ...],
) -> RealizationRow:
    subject = response_subject_from_proposal(proposal)
    surface = _neutral_realization_surface(proposal)
    slot = _realization_slot_for_subject(subject)
    literal_ref = stable_ref(
        "reviewed_literal",
        {
            "literal": surface,
            "language": case.language,
            "review_refs": list(review_refs),
        },
    )
    response = case.contract.expected_response
    return RealizationRow.create(
        source_case_ref=case.case_ref,
        response_subject=subject,
        bindings=(),
        discourse_action_ref=f"response_action:{response.discourse_action}",
        polarity_ref=response.polarity_ref,
        modality_ref=response.modality_ref,
        epistemic_status_ref=response.epistemic_status_ref,
        output_speaker_ref="participant:system",
        output_addressee_ref="participant:user",
        authorized_surface=surface,
        language=case.language,
        semantic_slots=(slot,),
        alignments=(
            LiteralAlignment.create(
                slot_ref=slot.slot_ref,
                literal_source_ref=literal_ref,
                surface_start=0,
                surface_end=len(surface),
            ),
        ),
        review_refs=review_refs,
    )


def build_reviewed_proposal_authoring(
    *,
    universe: SourceUniverse,
    source_cache: SourceAuthoringCache,
    authority: LinkedAuthority,
    selection: Mapping[str, object],
    case_purposes: Mapping[str, str | None],
    review_refs: tuple[str, ...],
    input_refs: tuple[str, ...],
    generator_source_ref: str,
) -> AuthoringResult:
    """Expand a completed reviewer selection into verified proposal candidates."""

    if type(universe) is not SourceUniverse:
        raise TypeError("universe must be exact SourceUniverse")
    if type(source_cache) is not SourceAuthoringCache:
        raise TypeError("source_cache must be exact SourceAuthoringCache")
    if type(authority) is not LinkedAuthority:
        raise TypeError("authority must be exact LinkedAuthority")
    reviews = exact_review_refs(review_refs)
    inputs = exact_ref_tuple(input_refs, "input_refs", nonempty=True)
    generator = exact_ref(generator_source_ref, "generator_source_ref", prefix="generator_source:")
    supervised_refs = {
        case.case_ref
        for case in universe.cases
        if source_disposition_is_supervision_eligible(case.source_disposition)
    }
    if set(source_cache.cases_by_ref) != supervised_refs:
        raise ValueError("source cache does not match reviewed supervised universe")

    suggestion_by_family = {
        row.family_ref: row
        for row in source_cache.proposal_recipe_suggestions_by_case.values()
    }
    recipes: list[AuthoringRecipe] = []
    recipe_by_case: dict[str, AuthoringRecipe] = {}
    for selection_row in _selection_recipe_rows(selection):
        family_ref = selection_row["family_ref"]
        suggestion = suggestion_by_family[family_ref]
        for recipe in selection_row["purpose_recipes"]:
            if recipe["decision"] != "approve":
                continue
            row = AuthoringRecipe.create(
                recipe_kind="proposal",
                purpose=recipe["purpose"],
                normalized_family_key=suggestion.normalized_family_key,
                member_case_refs=tuple(recipe["member_case_refs"]),
                ancestry_refs=(),
                reviewed_parameters=recipe["reviewed_parameters"],
                review_refs=reviews,
            )
            recipes.append(row)
            for case_ref in row.member_case_refs:
                if case_ref in recipe_by_case:
                    raise ValueError("reviewed proposal recipe assigns a case twice")
                recipe_by_case[case_ref] = row
    if set(recipe_by_case) != supervised_refs:
        raise ValueError("reviewed proposal recipes do not cover the supervised set")

    designation_selection_by_case = {
        row["source_case_ref"]: row for row in _designation_selection_rows(selection)
    }
    designation_recipe_by_key: dict[tuple[str, str], AuthoringRecipe] = {}
    designation_members: dict[tuple[str, str], list[str]] = {}
    for case_ref in supervised_refs:
        purpose = case_purposes.get(case_ref)
        selection_row = designation_selection_by_case.get(case_ref)
        if type(purpose) is not str or type(selection_row) is not dict:
            raise ValueError("reviewed designation selection is incomplete")
        key = (purpose, selection_row["decision"])
        designation_members.setdefault(key, []).append(case_ref)
    for (purpose, decision), members in sorted(designation_members.items()):
        row = AuthoringRecipe.create(
            recipe_kind="designation",
            purpose=purpose,
            normalized_family_key=("designation", decision),
            member_case_refs=tuple(sorted(members)),
            ancestry_refs=(),
            reviewed_parameters={"decision": decision},
            review_refs=reviews,
        )
        recipes.append(row)
        designation_recipe_by_key[(purpose, decision)] = row

    compiler = ReviewedDerivationCompiler()
    realization_compiler = ReviewedRealizationCompiler(authority)
    proposals: list[AuthoringCandidate] = []
    proposal_targets_by_case: dict[str, ProposalTarget] = {}
    operations = dict(source_cache.operation_counts)
    operations.update(
        {
            "proposal_target_builds": 0,
            "derivation_compilations": 0,
            "designation_candidate_builds": 0,
            "realization_row_builds": 0,
            "realization_compilations": 0,
        }
    )
    for case in source_cache.cases:
        recipe = recipe_by_case[case.case_ref]
        context = source_cache.proposal_contexts_by_case[case.case_ref]
        try:
            target = _proposal_target_for_case(
                case=case,
                context=context,
                review_refs=reviews,
            )
            for blueprint in target.derivations:
                compiled = compiler.compile(
                    case=case,
                    context=context,
                    blueprint=blueprint,
                )
                operations["derivation_compilations"] += compiled.operation_count
            proposal_targets_by_case[case.case_ref] = target
            proposed_row = target.as_dict()
            selectable = True
            exceptions: tuple[str, ...] = ()
        except (TypeError, ValueError) as exc:
            proposed_row = None
            selectable = False
            exceptions = (f"proposal_expansion:{type(exc).__name__}",)
        operations["proposal_target_builds"] += 1
        proposals.append(
            AuthoringCandidate.create(
                candidate_kind="proposal",
                source_case_ref=case.case_ref,
                purpose=recipe.purpose,
                recipe_ref=recipe.recipe_ref,
                input_refs=inputs,
                evidence_refs=(),
                generator_source_ref=generator,
                provenance_refs=tuple(sorted((context.context_ref, case.contract_ref))),
                verification_receipt_ref=stable_ref(
                    "authoring_verification",
                    {
                        "kind": "proposal",
                        "source_case_ref": case.case_ref,
                        "selectable": selectable,
                        "exceptions": list(exceptions),
                    },
                ),
                selectable=selectable,
                exception_codes=exceptions,
                proposed_row=proposed_row,
            )
        )

    realization_recipe_by_case: dict[str, AuthoringRecipe] = {}
    realization_members: dict[tuple[str, tuple[object, ...]], list[str]] = {}
    for case in source_cache.cases:
        proposal = proposal_targets_by_case[case.case_ref]
        purpose = case_purposes.get(case.case_ref)
        if type(purpose) is not str:
            raise ValueError("realization case lacks purpose")
        surface = _neutral_realization_surface(proposal)
        family_key = _realization_family_key(
            case=case,
            proposal=proposal,
            surface=surface,
        )
        realization_members.setdefault((purpose, family_key), []).append(
            case.case_ref
        )
    for (purpose, family_key), members in sorted(realization_members.items()):
        row = AuthoringRecipe.create(
            recipe_kind="realization",
            purpose=purpose,
            normalized_family_key=family_key,
            member_case_refs=tuple(sorted(members)),
            ancestry_refs=(),
            reviewed_parameters={
                "surface_template": family_key[-1],
                "reviewed_literal_alignment": "full_surface",
            },
            review_refs=reviews,
        )
        recipes.append(row)
        for case_ref in row.member_case_refs:
            realization_recipe_by_case[case_ref] = row

    realizations: list[RealizationRow] = []
    for case in source_cache.cases:
        proposal = proposal_targets_by_case[case.case_ref]
        recipe = realization_recipe_by_case[case.case_ref]
        row = _realization_row_for_case(
            case=case,
            proposal=proposal,
            review_refs=reviews,
        )
        compiled = realization_compiler.compile(
            case=case,
            proposal=proposal,
            row=row,
        )
        operations["realization_compilations"] += compiled.operation_count
        operations["realization_row_builds"] += 1
        if compiled.response_signature_ref != row.response_signature_ref:
            raise ValueError("reviewed realization signature does not compile")
        realizations.append(row)
        if case.case_ref not in recipe.member_case_refs:
            raise ValueError("realization row lacks a recipe owner")

    designations: list[AuthoringCandidate] = []
    for case in source_cache.cases:
        selection_row = designation_selection_by_case[case.case_ref]
        purpose = case_purposes[case.case_ref]
        if type(purpose) is not str:
            raise ValueError("designation case lacks purpose")
        recipe = designation_recipe_by_key[(purpose, selection_row["decision"])]
        candidate_set = source_cache.designation_sets_by_case[case.case_ref]
        approved = set(selection_row["approved_binding_refs"])
        bindings = tuple(
            row for row in candidate_set.bindings if row.binding_ref in approved
        )
        if len(bindings) != len(approved):
            raise ValueError("designation selection references unknown bindings")
        proposed_row = {
            "source_case_ref": case.case_ref,
            "surface_ref": case.surface_ref,
            "designation_facts": [
                {
                    "surface_start": row.source_start,
                    "surface_end": row.source_end,
                    "source_text": row.source_text,
                    "unit_refs": list(row.unit_refs),
                    "designation_fact_ref": row.designation_fact_ref,
                    "target_ref": row.target_ref,
                }
                for row in bindings
            ],
        }
        operations["designation_candidate_builds"] += 1
        designations.append(
            AuthoringCandidate.create(
                candidate_kind="designation",
                source_case_ref=case.case_ref,
                purpose=purpose,
                recipe_ref=recipe.recipe_ref,
                input_refs=inputs,
                evidence_refs=(),
                generator_source_ref=generator,
                provenance_refs=tuple(sorted((candidate_set.candidate_set_ref, case.contract_ref))),
                verification_receipt_ref=stable_ref(
                    "authoring_verification",
                    {
                        "kind": "designation",
                        "source_case_ref": case.case_ref,
                        "binding_count": len(bindings),
                    },
                ),
                selectable=True,
                exception_codes=(),
                proposed_row=proposed_row,
            )
        )

    return AuthoringResult(
        universe=universe,
        supervised_cases=source_cache.cases,
        cases_by_ref={case.case_ref: case for case in universe.cases},
        form_lattices_by_case=source_cache.form_lattices_by_case,
        proposal_contexts_by_case=source_cache.proposal_contexts_by_case,
        proposal_targets_by_case=proposal_targets_by_case,
        proposals=tuple(proposals),
        designations=tuple(designations),
        realizations=tuple(realizations),
        mutation_contracts=(),
        mutation_families=(),
        recipes=tuple(sorted(recipes, key=lambda row: row.recipe_ref)),
        effect_projection=None,
        operation_counts=operations,
        linear_operation_bound=200 * max(1, len(source_cache.cases)),
        max_recipe_families_per_kind_purpose=MAX_RECIPE_FAMILIES_PER_KIND_PURPOSE,
        max_recipe_instances_per_kind=MAX_RECIPE_INSTANCES_PER_KIND,
        max_designation_targets_per_span=8,
        max_realization_variants_per_case=4,
        max_mutation_families_per_case=8,
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
