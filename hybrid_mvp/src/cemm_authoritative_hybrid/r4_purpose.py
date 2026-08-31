"""Reviewed R4.1 purpose, duplicate-risk, and denominator contracts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ._r4_source_codec import (
    MAX_R4_SOURCE_RECORDS,
    canonical_json_bytes,
    construct,
    exact_abi,
    exact_bool,
    exact_case_ref,
    exact_content_ref,
    exact_content_ref_tuple,
    exact_fields,
    exact_int,
    exact_ref,
    exact_ref_tuple,
    exact_review_refs,
    exact_text,
    strict_decode,
    wire_ref_tuple,
    wire_value_tuple,
)
from .canonical import stable_ref

PURPOSE_CONTRACT_ABI_VERSION = 1
PURPOSES = ("train", "selection", "calibration", "frozen_test")
MAX_DUPLICATE_RISK_GROUPS = 4_096
MAX_GROUP_MEMBERS = 4_096
MAX_CHALLENGE_HOLDOUTS = 1_024
MAX_DENOMINATOR_MINIMA = 4_096
MAX_AGGREGATE_MEMBERSHIP_LINKS = 65_536

_CLASSIFICATIONS = frozenset(
    {
        "semantic_supervision",
        "typed_abstention",
        "verification_rejection",
        "diagnostic_only",
    }
)
_DUPLICATE_NAMESPACES = frozenset(
    {
        "source_case_lineage",
        "paraphrase_family",
        "normalization_family",
        "mutation_lineage",
        "environment_provenance",
        "trajectory_lineage",
    }
)
_CHALLENGE_NAMESPACES = frozenset(
    {
        "semantic_identity",
        "operator",
        "role",
        "mode",
        "participant",
        "topology",
        "response_action",
        "realization_action",
    }
)
_CHALLENGE_IDENTITY_PREFIXES = {
    "semantic_identity": ("event:", "concept:", "entity:", "rel:", "dim:", "value:", "label:", "cap:"),
    "operator": ("op:",),
    "role": ("role:",),
    "mode": ("mode:",),
    "participant": ("participant:",),
    "topology": ("topology:",),
    "response_action": ("response_action:",),
    "realization_action": ("realization_action:",),
}
_DENOMINATOR_FAMILIES = frozenset(
    {
        "semantic_expression",
        "operator",
        "mode",
        "role",
        "state_compatibility",
        "topology",
        "typed_abstention",
        "critical_residual",
        "transition_effect",
        "no_effect",
        "response_meaning",
        "perspective_reference",
        "literal_copy",
    }
)


def _factory_only(owner: str) -> TypeError:
    return TypeError(f"use {owner}.create")


def _purpose(value: object) -> str:
    purpose = exact_text(value, "purpose", maximum=16)
    if purpose not in PURPOSES:
        raise ValueError("unsupported R4 purpose")
    return purpose


def _optional_ref(value: object, name: str) -> str | None:
    return None if value is None else exact_ref(value, name)


def _canonical_nested(value: object, expected_type: type[Any], name: str) -> Any:
    if type(value) is not expected_type:
        raise TypeError(f"{name} must be exact {expected_type.__name__}")
    try:
        rebuilt = expected_type.from_dict(value.as_dict())
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"{name} is not canonical") from exc
    if rebuilt != value:
        raise ValueError(f"{name} is not canonical")
    return rebuilt


def _bounded_link_count(rows: tuple[Any, ...], field: str, current: int) -> int:
    total = current
    for row in rows:
        links = getattr(row, field, None)
        if type(links) is not tuple:
            raise ValueError("nested membership links are not canonical")
        total += len(links)
        if total > MAX_AGGREGATE_MEMBERSHIP_LINKS:
            raise ValueError("aggregate membership link bound is violated")
    return total


@dataclass(frozen=True, init=False)
class PurposeMembership:
    abi_version: int
    membership_ref: str
    source_case_ref: str
    classification: str
    purpose: str | None
    duplicate_risk_group_refs: tuple[str, ...]
    diagnostic_reason_ref: str | None
    review_refs: tuple[str, ...]

    _FIELDS = frozenset({"abi_version", "membership_ref", "source_case_ref", "classification", "purpose", "duplicate_risk_group_refs", "diagnostic_reason_ref", "review_refs"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("PurposeMembership")

    @classmethod
    def create(cls, *, source_case_ref: str, classification: str, purpose: str | None, duplicate_risk_group_refs: tuple[str, ...], diagnostic_reason_ref: str | None, review_refs: tuple[str, ...]) -> "PurposeMembership":
        kind = exact_text(classification, "classification", maximum=32)
        if kind not in _CLASSIFICATIONS:
            raise ValueError("unsupported source-case classification")
        purpose_value = None if purpose is None else _purpose(purpose)
        reason = _optional_ref(diagnostic_reason_ref, "diagnostic_reason_ref")
        groups = exact_ref_tuple(duplicate_risk_group_refs, "duplicate_risk_group_refs", nonempty=False, maximum=128, prefix="duplicate_risk_group:")
        if kind == "diagnostic_only":
            if purpose_value is not None:
                raise ValueError("diagnostic-only membership cannot enter a purpose")
            if reason is None:
                raise ValueError("diagnostic reason is required")
            if groups:
                raise ValueError("diagnostic-only membership cannot enter a duplicate-risk group")
        else:
            if reason is not None:
                raise ValueError("supervised membership cannot carry a diagnostic reason")
            if groups and purpose_value is not None:
                raise ValueError("grouped supervised membership cannot own a direct purpose")
            if not groups and purpose_value is None:
                raise ValueError("ungrouped supervised membership requires one direct purpose")
        material = {"abi_version": PURPOSE_CONTRACT_ABI_VERSION, "source_case_ref": exact_case_ref(source_case_ref), "classification": kind, "purpose": purpose_value, "duplicate_risk_group_refs": list(groups), "diagnostic_reason_ref": reason, "review_refs": list(exact_review_refs(review_refs))}
        return construct(cls, membership_ref=stable_ref("purpose_membership_v1", material), duplicate_risk_group_refs=groups, review_refs=tuple(material["review_refs"]), **{key: value for key, value in material.items() if key not in {"duplicate_risk_group_refs", "review_refs"}})

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "membership_ref": self.membership_ref, "source_case_ref": self.source_case_ref, "classification": self.classification, "purpose": self.purpose, "duplicate_risk_group_refs": list(self.duplicate_risk_group_refs), "diagnostic_reason_ref": self.diagnostic_reason_ref, "review_refs": list(self.review_refs)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PurposeMembership":
        row = exact_fields(value, cls._FIELDS, "PurposeMembership")
        exact_abi(row["abi_version"], PURPOSE_CONTRACT_ABI_VERSION, "Purpose Contract")
        rebuilt = cls.create(source_case_ref=row["source_case_ref"], classification=row["classification"], purpose=row["purpose"], duplicate_risk_group_refs=wire_ref_tuple(row["duplicate_risk_group_refs"], "duplicate_risk_group_refs", nonempty=False, maximum=128, prefix="duplicate_risk_group:"), diagnostic_reason_ref=row["diagnostic_reason_ref"], review_refs=wire_ref_tuple(row["review_refs"], "review_refs", nonempty=True))
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical PurposeMembership")
        return rebuilt


@dataclass(frozen=True, init=False)
class DuplicateRiskGroup:
    abi_version: int
    group_ref: str
    namespace: str
    purpose: str
    member_case_refs: tuple[str, ...]
    reason_ref: str
    review_refs: tuple[str, ...]

    _FIELDS = frozenset({"abi_version", "group_ref", "namespace", "purpose", "member_case_refs", "reason_ref", "review_refs"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("DuplicateRiskGroup")

    @classmethod
    def create(cls, *, group_ref: str, namespace: str, purpose: str, member_case_refs: tuple[str, ...], reason_ref: str, review_refs: tuple[str, ...]) -> "DuplicateRiskGroup":
        exact_namespace = exact_text(namespace, "namespace", maximum=64)
        if exact_namespace not in _DUPLICATE_NAMESPACES:
            raise ValueError("unsupported duplicate-risk namespace")
        members = exact_content_ref_tuple(member_case_refs, "member_case_refs", nonempty=True, maximum=MAX_GROUP_MEMBERS, prefix="expanded_case_v2:")
        if len(members) < 2:
            raise ValueError("duplicate-risk group requires at least two members")
        return construct(cls, abi_version=PURPOSE_CONTRACT_ABI_VERSION, group_ref=exact_ref(group_ref, "group_ref", prefix="duplicate_risk_group:"), namespace=exact_namespace, purpose=_purpose(purpose), member_case_refs=members, reason_ref=exact_ref(reason_ref, "reason_ref"), review_refs=exact_review_refs(review_refs))

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "group_ref": self.group_ref, "namespace": self.namespace, "purpose": self.purpose, "member_case_refs": list(self.member_case_refs), "reason_ref": self.reason_ref, "review_refs": list(self.review_refs)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DuplicateRiskGroup":
        row = exact_fields(value, cls._FIELDS, "DuplicateRiskGroup")
        exact_abi(row["abi_version"], PURPOSE_CONTRACT_ABI_VERSION, "Purpose Contract")
        rebuilt = cls.create(group_ref=row["group_ref"], namespace=row["namespace"], purpose=row["purpose"], member_case_refs=wire_ref_tuple(row["member_case_refs"], "member_case_refs", nonempty=True, maximum=MAX_GROUP_MEMBERS, prefix="expanded_case_v2:"), reason_ref=row["reason_ref"], review_refs=wire_ref_tuple(row["review_refs"], "review_refs", nonempty=True))
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical DuplicateRiskGroup")
        return rebuilt


@dataclass(frozen=True, init=False)
class ChallengeHoldout:
    abi_version: int
    holdout_ref: str
    identity_namespace: str
    identity_ref: str
    purpose: str
    member_case_refs: tuple[str, ...]
    reason_ref: str
    review_refs: tuple[str, ...]

    _FIELDS = frozenset({"abi_version", "holdout_ref", "identity_namespace", "identity_ref", "purpose", "member_case_refs", "reason_ref", "review_refs"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("ChallengeHoldout")

    @classmethod
    def create(cls, *, holdout_ref: str, identity_namespace: str, identity_ref: str, purpose: str, member_case_refs: tuple[str, ...], reason_ref: str, review_refs: tuple[str, ...]) -> "ChallengeHoldout":
        namespace = exact_text(identity_namespace, "identity_namespace", maximum=64)
        if namespace not in _CHALLENGE_NAMESPACES:
            raise ValueError("unsupported challenge identity namespace")
        identity = exact_ref(identity_ref, "identity_ref")
        if not identity.startswith(_CHALLENGE_IDENTITY_PREFIXES[namespace]):
            raise ValueError("challenge identity and namespace disagree")
        if namespace == "operator" and identity not in {
            "op:designation", "op:type", "op:relation", "op:state", "op:event"
        }:
            raise ValueError("challenge identity and namespace disagree")
        return construct(cls, abi_version=PURPOSE_CONTRACT_ABI_VERSION, holdout_ref=exact_ref(holdout_ref, "holdout_ref", prefix="challenge_holdout:"), identity_namespace=namespace, identity_ref=identity, purpose=_purpose(purpose), member_case_refs=exact_content_ref_tuple(member_case_refs, "member_case_refs", nonempty=True, maximum=MAX_GROUP_MEMBERS, prefix="expanded_case_v2:"), reason_ref=exact_ref(reason_ref, "reason_ref"), review_refs=exact_review_refs(review_refs))

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "holdout_ref": self.holdout_ref, "identity_namespace": self.identity_namespace, "identity_ref": self.identity_ref, "purpose": self.purpose, "member_case_refs": list(self.member_case_refs), "reason_ref": self.reason_ref, "review_refs": list(self.review_refs)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ChallengeHoldout":
        row = exact_fields(value, cls._FIELDS, "ChallengeHoldout")
        exact_abi(row["abi_version"], PURPOSE_CONTRACT_ABI_VERSION, "Purpose Contract")
        rebuilt = cls.create(holdout_ref=row["holdout_ref"], identity_namespace=row["identity_namespace"], identity_ref=row["identity_ref"], purpose=row["purpose"], member_case_refs=wire_ref_tuple(row["member_case_refs"], "member_case_refs", nonempty=True, maximum=MAX_GROUP_MEMBERS, prefix="expanded_case_v2:"), reason_ref=row["reason_ref"], review_refs=wire_ref_tuple(row["review_refs"], "review_refs", nonempty=True))
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical ChallengeHoldout")
        return rebuilt


@dataclass(frozen=True, init=False)
class DenominatorMinimum:
    abi_version: int
    minimum_ref: str
    denominator_ref: str
    denominator_family: str
    purpose: str
    minimum: int
    review_refs: tuple[str, ...]

    _FIELDS = frozenset({"abi_version", "minimum_ref", "denominator_ref", "denominator_family", "purpose", "minimum", "review_refs"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("DenominatorMinimum")

    @classmethod
    def create(cls, *, denominator_ref: str, denominator_family: str, purpose: str, minimum: int, review_refs: tuple[str, ...]) -> "DenominatorMinimum":
        family = exact_text(denominator_family, "denominator_family", maximum=64)
        if family not in _DENOMINATOR_FAMILIES:
            raise ValueError("unsupported denominator family")
        material = {"abi_version": PURPOSE_CONTRACT_ABI_VERSION, "denominator_ref": exact_ref(denominator_ref, "denominator_ref", prefix="denominator:"), "denominator_family": family, "purpose": _purpose(purpose), "minimum": exact_int(minimum, "minimum", minimum=1, maximum=MAX_R4_SOURCE_RECORDS), "review_refs": list(exact_review_refs(review_refs))}
        return construct(cls, minimum_ref=stable_ref("denominator_minimum_v1", material), review_refs=tuple(material["review_refs"]), **{key: value for key, value in material.items() if key != "review_refs"})

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "minimum_ref": self.minimum_ref, "denominator_ref": self.denominator_ref, "denominator_family": self.denominator_family, "purpose": self.purpose, "minimum": self.minimum, "review_refs": list(self.review_refs)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DenominatorMinimum":
        row = exact_fields(value, cls._FIELDS, "DenominatorMinimum")
        exact_abi(row["abi_version"], PURPOSE_CONTRACT_ABI_VERSION, "Purpose Contract")
        rebuilt = cls.create(denominator_ref=row["denominator_ref"], denominator_family=row["denominator_family"], purpose=row["purpose"], minimum=row["minimum"], review_refs=wire_ref_tuple(row["review_refs"], "review_refs", nonempty=True))
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical DenominatorMinimum")
        return rebuilt


def _validate_purpose_relationships(
    memberships: tuple[PurposeMembership, ...],
    duplicate_risk_groups: tuple[DuplicateRiskGroup, ...],
    challenge_holdouts: tuple[ChallengeHoldout, ...],
    denominator_minima: tuple[DenominatorMinimum, ...],
) -> int:
    """Validate indexed SR4 semantic relations and return logical work units."""

    operations = 0
    membership_by_case: dict[str, PurposeMembership] = {}
    membership_groups_by_case: dict[str, frozenset[str]] = {}
    for membership in memberships:
        operations += 1 + len(membership.duplicate_risk_group_refs)
        membership_by_case[membership.source_case_ref] = membership
        membership_groups_by_case[membership.source_case_ref] = frozenset(
            membership.duplicate_risk_group_refs
        )

    group_by_ref: dict[str, DuplicateRiskGroup] = {}
    group_members_by_ref: dict[str, frozenset[str]] = {}
    for group in duplicate_risk_groups:
        operations += 1 + len(group.member_case_refs)
        group_by_ref[group.group_ref] = group
        group_members_by_ref[group.group_ref] = frozenset(group.member_case_refs)

    parent: dict[str, str] = {}
    rank: dict[str, int] = {}

    def find(case_ref: str) -> str:
        nonlocal operations
        operations += 1
        root = case_ref
        while parent[root] != root:
            operations += 1
            root = parent[root]
        while parent[case_ref] != case_ref:
            operations += 1
            next_ref = parent[case_ref]
            parent[case_ref] = root
            case_ref = next_ref
        return root

    def union(left: str, right: str) -> None:
        nonlocal operations
        operations += 1
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return
        left_rank = rank[left_root]
        right_rank = rank[right_root]
        if left_rank < right_rank:
            left_root, right_root = right_root, left_root
        parent[right_root] = left_root
        if left_rank == right_rank:
            rank[left_root] += 1

    for group in duplicate_risk_groups:
        first_member = group.member_case_refs[0]
        for member_case_ref in group.member_case_refs:
            operations += 1
            if member_case_ref not in membership_by_case:
                raise ValueError("duplicate-risk group contains an unknown source case")
        for member_case_ref in group.member_case_refs:
            operations += 1
            if group.group_ref not in membership_groups_by_case[member_case_ref]:
                raise ValueError("group membership is not declared by every member")
            if member_case_ref not in parent:
                parent[member_case_ref] = member_case_ref
                rank[member_case_ref] = 0
            if member_case_ref != first_member:
                union(first_member, member_case_ref)

    for membership in memberships:
        for group_ref in membership.duplicate_risk_group_refs:
            operations += 1
            group = group_by_ref.get(group_ref)
            if group is None:
                raise ValueError(
                    "purpose membership references an unknown duplicate-risk group"
                )
            if membership.source_case_ref not in group_members_by_ref[group_ref]:
                raise ValueError("group membership must be declared both ways")

    purpose_by_component: dict[str, str] = {}
    for group in duplicate_risk_groups:
        operations += 1
        root = find(group.member_case_refs[0])
        component_purpose = purpose_by_component.get(root)
        if component_purpose is not None and component_purpose != group.purpose:
            raise ValueError("duplicate-risk component must remain in one purpose")
        purpose_by_component[root] = group.purpose

    effective_purpose_by_case: dict[str, str | None] = {}
    for membership in memberships:
        operations += 1
        if membership.duplicate_risk_group_refs:
            root = find(membership.source_case_ref)
            effective_purpose_by_case[membership.source_case_ref] = (
                purpose_by_component[root]
            )
        else:
            effective_purpose_by_case[membership.source_case_ref] = membership.purpose

    for holdout in challenge_holdouts:
        for member_case_ref in holdout.member_case_refs:
            operations += 1
            if member_case_ref not in membership_by_case:
                raise ValueError("challenge holdout contains an unknown source case")
            if effective_purpose_by_case[member_case_ref] != holdout.purpose:
                raise ValueError("challenge holdout members must match its purpose")

    purposes_by_denominator: dict[str, set[str]] = {}
    family_by_denominator: dict[str, str] = {}
    for minimum in denominator_minima:
        operations += 1
        family = family_by_denominator.setdefault(
            minimum.denominator_ref, minimum.denominator_family
        )
        if family != minimum.denominator_family:
            raise ValueError("each denominator ref must use one family")
        purposes_by_denominator.setdefault(minimum.denominator_ref, set()).add(
            minimum.purpose
        )
    if any(purposes != set(PURPOSES) for purposes in purposes_by_denominator.values()):
        raise ValueError("each denominator ref must cover all four purposes")
    return operations


@dataclass(frozen=True, init=False)
class PurposeContract:
    abi_version: int
    purpose_contract_ref: str
    source_set_ref: str
    memberships: tuple[PurposeMembership, ...]
    duplicate_risk_groups: tuple[DuplicateRiskGroup, ...]
    challenge_holdouts: tuple[ChallengeHoldout, ...]
    denominator_minima: tuple[DenominatorMinimum, ...]
    review_refs: tuple[str, ...]
    solver_output_is_authority: bool

    _FIELDS = frozenset({"abi_version", "purpose_contract_ref", "source_set_ref", "memberships", "duplicate_risk_groups", "challenge_holdouts", "denominator_minima", "review_refs", "solver_output_is_authority"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("PurposeContract")

    @classmethod
    def create(cls, *, source_set_ref: str, memberships: tuple[PurposeMembership, ...], duplicate_risk_groups: tuple[DuplicateRiskGroup, ...], challenge_holdouts: tuple[ChallengeHoldout, ...], denominator_minima: tuple[DenominatorMinimum, ...], review_refs: tuple[str, ...], solver_output_is_authority: bool) -> "PurposeContract":
        if type(memberships) is not tuple or not memberships or len(memberships) > MAX_R4_SOURCE_RECORDS or any(type(item) is not PurposeMembership for item in memberships):
            raise ValueError("memberships must be a bounded nonempty exact tuple")
        aggregate_links = _bounded_link_count(memberships, "duplicate_risk_group_refs", 0)
        canonical_memberships = tuple(
            _canonical_nested(item, PurposeMembership, "membership") for item in memberships
        )
        case_refs = tuple(item.source_case_ref for item in canonical_memberships)
        if len(case_refs) != len(set(case_refs)):
            raise ValueError("duplicate source case membership")
        if any(left >= right for left, right in zip(case_refs, case_refs[1:])):
            raise ValueError("memberships must be in canonical source-case order")
        if type(duplicate_risk_groups) is not tuple or len(duplicate_risk_groups) > MAX_DUPLICATE_RISK_GROUPS or any(type(item) is not DuplicateRiskGroup for item in duplicate_risk_groups):
            raise ValueError("duplicate-risk groups violate their bound")
        aggregate_links = _bounded_link_count(
            duplicate_risk_groups, "member_case_refs", aggregate_links
        )
        canonical_groups = tuple(
            _canonical_nested(item, DuplicateRiskGroup, "duplicate-risk group")
            for item in duplicate_risk_groups
        )
        if type(challenge_holdouts) is not tuple or len(challenge_holdouts) > MAX_CHALLENGE_HOLDOUTS or any(type(item) is not ChallengeHoldout for item in challenge_holdouts):
            raise ValueError("challenge holdouts violate their bound")
        aggregate_links = _bounded_link_count(
            challenge_holdouts, "member_case_refs", aggregate_links
        )
        canonical_holdouts = tuple(
            _canonical_nested(item, ChallengeHoldout, "challenge holdout")
            for item in challenge_holdouts
        )
        if type(denominator_minima) is not tuple or not denominator_minima or len(denominator_minima) > MAX_DENOMINATOR_MINIMA or any(type(item) is not DenominatorMinimum for item in denominator_minima):
            raise ValueError("denominator bound is violated")
        canonical_minima = tuple(
            _canonical_nested(item, DenominatorMinimum, "denominator minimum")
            for item in denominator_minima
        )
        for rows, name, identity in (
            (canonical_groups, "duplicate-risk groups", lambda item: item.group_ref),
            (canonical_holdouts, "challenge holdouts", lambda item: item.holdout_ref),
        ):
            identities = tuple(identity(item) for item in rows)
            if len(identities) != len(set(identities)):
                raise ValueError(f"{name} contain duplicate identities")
            if any(left >= right for left, right in zip(identities, identities[1:])):
                raise ValueError(f"{name} must be in canonical order")
        minimum_identities = tuple(
            (PURPOSES.index(item.purpose), item.denominator_ref)
            for item in canonical_minima
        )
        if len(minimum_identities) != len(set(minimum_identities)):
            raise ValueError("denominator minima contain duplicate identities")
        if any(
            left >= right
            for left, right in zip(minimum_identities, minimum_identities[1:])
        ):
            raise ValueError("denominator minima must be in canonical order")
        holdout_identities = tuple(
            (item.identity_namespace, item.identity_ref) for item in canonical_holdouts
        )
        if len(holdout_identities) != len(set(holdout_identities)):
            raise ValueError("duplicate holdout identity tuple")
        _validate_purpose_relationships(
            canonical_memberships,
            canonical_groups,
            canonical_holdouts,
            canonical_minima,
        )
        solver_authority = exact_bool(solver_output_is_authority, "solver_output_is_authority")
        if solver_authority:
            raise ValueError("solver output cannot be purpose authority")
        material = {"abi_version": PURPOSE_CONTRACT_ABI_VERSION, "source_set_ref": exact_content_ref(source_set_ref, "source_set_ref", prefix="r4_source_set_v1:"), "memberships": [item.as_dict() for item in canonical_memberships], "duplicate_risk_groups": [item.as_dict() for item in canonical_groups], "challenge_holdouts": [item.as_dict() for item in canonical_holdouts], "denominator_minima": [item.as_dict() for item in canonical_minima], "review_refs": list(exact_review_refs(review_refs)), "solver_output_is_authority": solver_authority}
        return construct(cls, purpose_contract_ref=stable_ref("purpose_contract_v1", material), memberships=canonical_memberships, duplicate_risk_groups=canonical_groups, challenge_holdouts=canonical_holdouts, denominator_minima=canonical_minima, review_refs=tuple(material["review_refs"]), **{key: value for key, value in material.items() if key not in {"memberships", "duplicate_risk_groups", "challenge_holdouts", "denominator_minima", "review_refs"}})

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "purpose_contract_ref": self.purpose_contract_ref, "source_set_ref": self.source_set_ref, "memberships": [item.as_dict() for item in self.memberships], "duplicate_risk_groups": [item.as_dict() for item in self.duplicate_risk_groups], "challenge_holdouts": [item.as_dict() for item in self.challenge_holdouts], "denominator_minima": [item.as_dict() for item in self.denominator_minima], "review_refs": list(self.review_refs), "solver_output_is_authority": self.solver_output_is_authority}

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PurposeContract":
        row = exact_fields(value, cls._FIELDS, "PurposeContract")
        exact_abi(row["abi_version"], PURPOSE_CONTRACT_ABI_VERSION, "Purpose Contract")
        rebuilt = cls.create(source_set_ref=row["source_set_ref"], memberships=wire_value_tuple(row["memberships"], "memberships", PurposeMembership.from_dict, nonempty=True, maximum=MAX_R4_SOURCE_RECORDS), duplicate_risk_groups=wire_value_tuple(row["duplicate_risk_groups"], "duplicate_risk_groups", DuplicateRiskGroup.from_dict, nonempty=False, maximum=MAX_DUPLICATE_RISK_GROUPS), challenge_holdouts=wire_value_tuple(row["challenge_holdouts"], "challenge_holdouts", ChallengeHoldout.from_dict, nonempty=False, maximum=MAX_CHALLENGE_HOLDOUTS), denominator_minima=wire_value_tuple(row["denominator_minima"], "denominator_minima", DenominatorMinimum.from_dict, nonempty=True, maximum=MAX_DENOMINATOR_MINIMA), review_refs=wire_ref_tuple(row["review_refs"], "review_refs", nonempty=True), solver_output_is_authority=row["solver_output_is_authority"])
        if rebuilt.purpose_contract_ref != row["purpose_contract_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical PurposeContract")
        return rebuilt

    @classmethod
    def from_json_bytes(cls, raw: object) -> "PurposeContract":
        return strict_decode(raw, cls.from_dict, owner="purpose contract")


def _validation_operation_count_for_test(contract: PurposeContract) -> int:
    """Return deterministic semantic-validation work for bounded test fixtures."""

    if type(contract) is not PurposeContract:
        raise TypeError("contract must be exact PurposeContract")
    return _validate_purpose_relationships(
        contract.memberships,
        contract.duplicate_risk_groups,
        contract.challenge_holdouts,
        contract.denominator_minima,
    )


def validate_recipe_ancestry(
    recipes: tuple[object, ...],
    ancestry_edges: tuple[tuple[str, str], ...],
) -> int:
    """Validate explicit authoring ancestry without deriving similarity edges."""

    from .r4_authoring import AuthoringRecipe, validate_authoring_recipes

    operations = validate_authoring_recipes(recipes)
    if any(type(recipe) is not AuthoringRecipe for recipe in recipes):
        raise TypeError("recipe ancestry requires exact AuthoringRecipe values")
    by_ref = {recipe.recipe_ref: recipe for recipe in recipes}
    if len(by_ref) != len(recipes):
        raise ValueError("recipe ancestry contains duplicate recipes")
    if type(ancestry_edges) is not tuple or len(ancestry_edges) > MAX_GROUP_MEMBERS:
        raise TypeError("ancestry_edges must be a bounded exact tuple")
    edges: list[tuple[str, str]] = []
    for edge in ancestry_edges:
        operations += 1
        if type(edge) is not tuple or len(edge) != 2:
            raise TypeError("recipe ancestry edges must be exact pairs")
        parent_ref = exact_ref(edge[0], "ancestry parent", prefix="authoring_recipe:")
        child_ref = exact_ref(edge[1], "ancestry child", prefix="authoring_recipe:")
        parent_recipe = by_ref.get(parent_ref)
        child_recipe = by_ref.get(child_ref)
        if parent_recipe is None or child_recipe is None:
            raise ValueError("recipe ancestry references an unknown recipe")
        if parent_recipe.purpose != child_recipe.purpose:
            raise ValueError("recipe ancestry crosses purposes")
        if parent_recipe.recipe_kind != child_recipe.recipe_kind:
            raise ValueError("recipe ancestry crosses recipe kinds")
        edges.append((parent_ref, child_ref))
    if len(edges) != len(set(edges)):
        raise ValueError("recipe ancestry edges must be unique")
    declared = {
        (parent_ref, recipe.recipe_ref)
        for recipe in recipes
        for parent_ref in recipe.ancestry_refs
    }
    if set(edges) != declared:
        raise ValueError("recipe ancestry edges differ from reviewed recipe declarations")

    children: dict[str, list[str]] = {ref: [] for ref in by_ref}
    indegree = {ref: 0 for ref in by_ref}
    for parent_ref, child_ref in edges:
        children[parent_ref].append(child_ref)
        indegree[child_ref] += 1
    pending = sorted(ref for ref, degree in indegree.items() if degree == 0)
    visited = 0
    while pending:
        current = pending.pop()
        visited += 1
        operations += 1
        for child_ref in children[current]:
            indegree[child_ref] -= 1
            if indegree[child_ref] == 0:
                pending.append(child_ref)
    if visited != len(by_ref):
        raise ValueError("recipe ancestry must be acyclic")
    return operations


def recipe_ancestry_duplicate_risk_groups(
    recipes: tuple[object, ...],
    ancestry_edges: tuple[tuple[str, str], ...],
) -> tuple[DuplicateRiskGroup, ...]:
    """Lower explicit recipe ancestry to the existing duplicate-risk contract."""

    validate_recipe_ancestry(recipes, ancestry_edges)
    by_ref = {recipe.recipe_ref: recipe for recipe in recipes}
    neighbors: dict[str, set[str]] = {ref: set() for ref in by_ref}
    for parent_ref, child_ref in ancestry_edges:
        neighbors[parent_ref].add(child_ref)
        neighbors[child_ref].add(parent_ref)
    groups: list[DuplicateRiskGroup] = []
    remaining = {ref for ref, adjacent in neighbors.items() if adjacent}
    while remaining:
        seed = min(remaining)
        component: set[str] = set()
        pending = [seed]
        while pending:
            current = pending.pop()
            if current in component:
                continue
            component.add(current)
            pending.extend(sorted(neighbors[current] - component, reverse=True))
        remaining -= component
        component_recipes = tuple(by_ref[ref] for ref in sorted(component))
        members = tuple(
            sorted(
                {
                    case_ref
                    for recipe in component_recipes
                    for case_ref in recipe.member_case_refs
                }
            )
        )
        if len(members) < 2:
            continue
        purpose = component_recipes[0].purpose
        material = {
            "namespace": "normalization_family",
            "purpose": purpose,
            "recipe_refs": sorted(component),
            "member_case_refs": list(members),
        }
        groups.append(
            DuplicateRiskGroup.create(
                group_ref=stable_ref("duplicate_risk_group", material),
                namespace="normalization_family",
                purpose=purpose,
                member_case_refs=members,
                reason_ref="duplicate_reason:reviewed-recipe-ancestry",
                review_refs=tuple(
                    sorted(
                        {
                            review_ref
                            for recipe in component_recipes
                            for review_ref in recipe.review_refs
                        }
                    )
                ),
            )
        )
    return tuple(sorted(groups, key=lambda group: group.group_ref))


__all__ = [
    "MAX_CHALLENGE_HOLDOUTS",
    "MAX_DENOMINATOR_MINIMA",
    "MAX_DUPLICATE_RISK_GROUPS",
    "MAX_GROUP_MEMBERS",
    "MAX_AGGREGATE_MEMBERSHIP_LINKS",
    "PURPOSE_CONTRACT_ABI_VERSION",
    "PURPOSES",
    "ChallengeHoldout",
    "DenominatorMinimum",
    "DuplicateRiskGroup",
    "PurposeContract",
    "PurposeMembership",
    "recipe_ancestry_duplicate_risk_groups",
    "validate_recipe_ancestry",
]
