"""Immutable reviewed-source contracts for R4.1 supervision.

These values own reviewed inputs only.  They neither compile a blueprint nor
consult runtime observations, bootstrap proposals, or verifier selections.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import Any, Mapping

from ._r4_source_codec import (
    MAX_R4_SOURCE_RECORDS,
    MAX_R4_TEXT_CHARS,
    canonical_json_bytes,
    construct,
    exact_bool,
    exact_case_ref,
    exact_content_ref,
    exact_content_ref_tuple,
    exact_fields,
    exact_int,
    exact_ref,
    exact_ref_tuple,
    exact_review_refs,
    exact_revision,
    exact_sha256,
    exact_text,
    exact_value_tuple,
    strict_decode,
    wire_content_ref_tuple,
    wire_ref_tuple,
    wire_value_tuple,
)
from .canonical import stable_ref
from .programs import PROGRAM_ABI_VERSION, SWITCH_ACTION_TYPES

R4_REVIEW_MANIFEST_ABI_VERSION = 1
PROPOSAL_SUPERVISION_ABI_VERSION = 1
REALIZATION_SUPERVISION_ABI_VERSION = 1
MUTATION_CONTRACT_ABI_VERSION = 1

MAX_BLUEPRINT_ACTIONS = 208
MAX_DERIVATIONS_PER_CASE = 16
MAX_SELECTORS_PER_ACTION = 27
MAX_REALIZATION_SLOTS = 64
MAX_REFERENCE_FORMS = 16
MAX_LITERAL_ALIGNMENTS = 64

_SOURCE_PATHS = (
    "data/review/r4_1/mutation_contracts.jsonl",
    "data/review/r4_1/proposal_supervision.jsonl",
    "data/review/r4_1/purpose_contract.json",
    "data/review/r4_1/realization_supervision.jsonl",
)
_ABI_VERSIONS = {
    "mutation_contract": 1,
    "proposal_supervision": 1,
    "purpose_contract": 1,
    "r4_review_manifest": 1,
    "realization_supervision": 1,
}
_SAFE_SELECTOR_KINDS = frozenset(
    {
        "context_slot",
        "mode_slot",
        "designation_slot",
        "local_node",
        "frame_slot",
        "role_ref",
        "contribution_slot",
        "reference_slot",
        "scope_slot",
        "expression_link_slot",
        "variable_slot",
        "transition_slot",
        "source_geometry",
        "semantic_kind",
    }
)
_SELECTOR_PREFIXES: Mapping[str, tuple[str, ...]] = {
    "context_slot": ("proposal_context:",),
    "mode_slot": ("mode_slot:",),
    "designation_slot": ("designation_slot:",),
    "local_node": ("application:", "expression_link:", "scope:", "binder:", "local_node:"),
    "frame_slot": ("application_frame_slot:",),
    "role_ref": ("role:",),
    "contribution_slot": ("contribution_slot:",),
    "reference_slot": ("reference_slot:",),
    "scope_slot": ("scope_slot:",),
    "expression_link_slot": ("expression_link_slot:",),
    "variable_slot": ("variable_slot:",),
    "transition_slot": ("transition_slot:",),
    "source_geometry": ("source_geometry:",),
    "semantic_kind": ("semantic_kind:",),
}
_SELECTOR_COUNTS: Mapping[str, tuple[int, int]] = {
    "select_context": (1, 1),
    "select_mode": (1, 1),
    "select_designation": (1, 1),
    "instantiate_operator": (2, 2),
    "bind_role": (3, 3),
    "bind_reference": (3, 3),
    "bind_nested_application": (4, 27),
    "attach_scope": (3, 3),
    "project_variable": (3, 3),
    "propose_transition": (2, 2),
    "complete_program": (0, 0),
    "abstain": (0, 0),
}
_OWNER_PHASES = frozenset({"orient", "propose", "verify", "evaluate", "effect", "realize"})
_SAFE_DISPOSITIONS = frozenset({"frontier", "clarify", "reject"})
_MUTATION_DISPOSITIONS = frozenset({"accept", "reject", "frontier"})
_COPY_SOURCE_KINDS = frozenset(
    {"reviewed_literal", "decision_literal", "effect_literal", "obligation_literal"}
)
_LANGUAGE_RE = re.compile(r"[a-z]{2,8}(?:-[A-Za-z0-9]{1,8})*\Z")


def _factory_only(owner: str) -> TypeError:
    return TypeError(f"use {owner}.create")


def _wire_optional_ref(value: object, name: str) -> str | None:
    if value is None:
        return None
    return exact_ref(value, name)


@dataclass(frozen=True, init=False)
class ReviewSourceFile:
    abi_version: int
    source_ref: str
    path: str
    sha256: str
    record_count: int
    review_refs: tuple[str, ...]

    _FIELDS = frozenset({"abi_version", "source_ref", "path", "sha256", "record_count", "review_refs"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("ReviewSourceFile")

    @classmethod
    def create(cls, *, source_ref: str, path: str, sha256: str, record_count: int, review_refs: tuple[str, ...]) -> "ReviewSourceFile":
        if type(source_ref) is str and source_ref.startswith(("runtime_observation:", "bootstrap_output:")):
            raise ValueError("reviewed source cannot be a runtime or bootstrap output")
        ref = exact_content_ref(source_ref, "source_ref", prefix="reviewed_source:")
        exact_path = exact_text(path, "source path", maximum=256)
        if exact_path not in _SOURCE_PATHS:
            raise ValueError("source path is not an R4.1 reviewed source owner")
        return construct(
            cls,
            abi_version=R4_REVIEW_MANIFEST_ABI_VERSION,
            source_ref=ref,
            path=exact_path,
            sha256=exact_sha256(sha256, "source sha256"),
            record_count=exact_int(record_count, "record_count", minimum=1, maximum=MAX_R4_SOURCE_RECORDS),
            review_refs=exact_review_refs(review_refs),
        )

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "source_ref": self.source_ref, "path": self.path, "sha256": self.sha256, "record_count": self.record_count, "review_refs": list(self.review_refs)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReviewSourceFile":
        row = exact_fields(value, cls._FIELDS, "ReviewSourceFile")
        if row["abi_version"] != R4_REVIEW_MANIFEST_ABI_VERSION:
            raise ValueError("unsupported R4 Review Manifest ABI")
        rebuilt = cls.create(source_ref=row["source_ref"], path=row["path"], sha256=row["sha256"], record_count=row["record_count"], review_refs=wire_ref_tuple(row["review_refs"], "review_refs", nonempty=True))
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical ReviewSourceFile")
        return rebuilt


@dataclass(frozen=True, init=False)
class R4ReviewManifest:
    abi_version: int
    manifest_ref: str
    review_policy_ref: str
    reviewer_refs: tuple[str, ...]
    reviewed_base_revision: str
    authority_generation: str
    source_bundle_ref: str
    scenario_source_sha256: str
    sources: tuple[ReviewSourceFile, ...]
    abi_versions: Mapping[str, int]
    approval_state: str
    supersedes_refs: tuple[str, ...]
    runtime_observations_are_source_authority: bool
    bootstrap_outputs_are_source_authority: bool

    _FIELDS = frozenset({"abi_version", "manifest_ref", "review_policy_ref", "reviewer_refs", "reviewed_base_revision", "authority_generation", "source_bundle_ref", "scenario_source_sha256", "sources", "abi_versions", "approval_state", "supersedes_refs", "runtime_observations_are_source_authority", "bootstrap_outputs_are_source_authority"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("R4ReviewManifest")

    @classmethod
    def create(cls, *, review_policy_ref: str, reviewer_refs: tuple[str, ...], reviewed_base_revision: str, authority_generation: str, source_bundle_ref: str, scenario_source_sha256: str, sources: tuple[ReviewSourceFile, ...], approval_state: str, supersedes_refs: tuple[str, ...], runtime_observations_are_source_authority: bool, bootstrap_outputs_are_source_authority: bool) -> "R4ReviewManifest":
        source_rows = exact_value_tuple(sources, "sources", ReviewSourceFile, nonempty=True, maximum=len(_SOURCE_PATHS), identity=lambda row: row.path)
        if tuple(row.path for row in source_rows) != _SOURCE_PATHS:
            raise ValueError("manifest must bind every exact R4.1 reviewed source")
        if len({row.source_ref for row in source_rows}) != len(source_rows):
            raise ValueError("manifest contains duplicate source refs")
        reviewers = exact_ref_tuple(reviewer_refs, "reviewer_refs", nonempty=True)
        supersedes = exact_ref_tuple(supersedes_refs, "supersedes_refs", nonempty=False)
        runtime_authority = exact_bool(runtime_observations_are_source_authority, "runtime_observations_are_source_authority")
        bootstrap_authority = exact_bool(bootstrap_outputs_are_source_authority, "bootstrap_outputs_are_source_authority")
        if runtime_authority or bootstrap_authority:
            raise ValueError("runtime observations and bootstrap outputs cannot be source authority")
        if approval_state != "approved":
            raise ValueError("review manifest approval_state must be approved")
        material = {
            "abi_version": R4_REVIEW_MANIFEST_ABI_VERSION,
            "review_policy_ref": exact_ref(review_policy_ref, "review_policy_ref"),
            "reviewer_refs": list(reviewers),
            "reviewed_base_revision": exact_revision(reviewed_base_revision, "reviewed_base_revision"),
            "authority_generation": exact_text(authority_generation, "authority_generation"),
            "source_bundle_ref": exact_content_ref(source_bundle_ref, "source_bundle_ref", prefix="r4_review_bundle_v1:"),
            "scenario_source_sha256": exact_sha256(scenario_source_sha256, "scenario_source_sha256"),
            "sources": [row.as_dict() for row in source_rows],
            "abi_versions": dict(_ABI_VERSIONS),
            "approval_state": approval_state,
            "supersedes_refs": list(supersedes),
            "runtime_observations_are_source_authority": runtime_authority,
            "bootstrap_outputs_are_source_authority": bootstrap_authority,
        }
        return construct(cls, manifest_ref=stable_ref("r4_review_manifest_v1", material), sources=source_rows, abi_versions=MappingProxyType(dict(_ABI_VERSIONS)), **{key: value if key not in {"reviewer_refs", "supersedes_refs"} else tuple(value) for key, value in material.items() if key not in {"sources", "abi_versions"}})

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "manifest_ref": self.manifest_ref, "review_policy_ref": self.review_policy_ref, "reviewer_refs": list(self.reviewer_refs), "reviewed_base_revision": self.reviewed_base_revision, "authority_generation": self.authority_generation, "source_bundle_ref": self.source_bundle_ref, "scenario_source_sha256": self.scenario_source_sha256, "sources": [row.as_dict() for row in self.sources], "abi_versions": dict(self.abi_versions), "approval_state": self.approval_state, "supersedes_refs": list(self.supersedes_refs), "runtime_observations_are_source_authority": self.runtime_observations_are_source_authority, "bootstrap_outputs_are_source_authority": self.bootstrap_outputs_are_source_authority}

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "R4ReviewManifest":
        row = exact_fields(value, cls._FIELDS, "R4ReviewManifest")
        if row["abi_version"] != R4_REVIEW_MANIFEST_ABI_VERSION:
            raise ValueError("unsupported R4 Review Manifest ABI")
        if type(row["abi_versions"]) is not dict or row["abi_versions"] != _ABI_VERSIONS:
            raise ValueError("manifest ABI versions are not the exact ABI 1 allocation")
        rebuilt = cls.create(review_policy_ref=row["review_policy_ref"], reviewer_refs=wire_ref_tuple(row["reviewer_refs"], "reviewer_refs", nonempty=True), reviewed_base_revision=row["reviewed_base_revision"], authority_generation=row["authority_generation"], source_bundle_ref=row["source_bundle_ref"], scenario_source_sha256=row["scenario_source_sha256"], sources=wire_value_tuple(row["sources"], "sources", ReviewSourceFile.from_dict, nonempty=True, maximum=len(_SOURCE_PATHS)), approval_state=row["approval_state"], supersedes_refs=wire_ref_tuple(row["supersedes_refs"], "supersedes_refs", nonempty=False), runtime_observations_are_source_authority=row["runtime_observations_are_source_authority"], bootstrap_outputs_are_source_authority=row["bootstrap_outputs_are_source_authority"])
        if rebuilt.manifest_ref != row["manifest_ref"]:
            raise ValueError("manifest ref does not match canonical content")
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical R4ReviewManifest")
        return rebuilt

    @classmethod
    def from_json_bytes(cls, raw: object) -> "R4ReviewManifest":
        return strict_decode(raw, cls.from_dict, owner="R4 review manifest")


@dataclass(frozen=True, init=False)
class DerivationSelector:
    abi_version: int
    selector_ref: str
    selector_kind: str
    value_ref: str

    _FIELDS = frozenset({"abi_version", "selector_ref", "selector_kind", "value_ref"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("DerivationSelector")

    @classmethod
    def create(cls, *, selector_kind: str, value_ref: str) -> "DerivationSelector":
        kind = exact_text(selector_kind, "selector_kind", maximum=64)
        if kind not in _SAFE_SELECTOR_KINDS:
            raise ValueError("unsafe selector kind; raw phrase, regex, and internal-ref spelling selectors are forbidden")
        ref = exact_ref(value_ref, "selector value_ref")
        if not ref.startswith(_SELECTOR_PREFIXES[kind]):
            raise ValueError("source-local selector kind and value namespace disagree")
        material = {"abi_version": PROPOSAL_SUPERVISION_ABI_VERSION, "selector_kind": kind, "value_ref": ref}
        return construct(cls, selector_ref=stable_ref("derivation_selector_v1", material), **material)

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "selector_ref": self.selector_ref, "selector_kind": self.selector_kind, "value_ref": self.value_ref}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DerivationSelector":
        row = exact_fields(value, cls._FIELDS, "DerivationSelector")
        if row["abi_version"] != PROPOSAL_SUPERVISION_ABI_VERSION:
            raise ValueError("unsupported Proposal Supervision ABI")
        rebuilt = cls.create(selector_kind=row["selector_kind"], value_ref=row["value_ref"])
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical DerivationSelector")
        return rebuilt


@dataclass(frozen=True, init=False)
class BlueprintAction:
    abi_version: int
    action_ref: str
    action_index: int
    action_type: str
    selectors: tuple[DerivationSelector, ...]

    _FIELDS = frozenset({"abi_version", "action_ref", "action_index", "action_type", "selectors"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("BlueprintAction")

    @classmethod
    def create(cls, *, action_index: int, action_type: str, selectors: tuple[DerivationSelector, ...]) -> "BlueprintAction":
        index = exact_int(action_index, "action_index", maximum=MAX_BLUEPRINT_ACTIONS - 1)
        action = exact_text(action_type, "action_type", maximum=64)
        if action not in SWITCH_ACTION_TYPES:
            raise ValueError("unsupported Program ABI 2 action type")
        if type(selectors) is not tuple or len(selectors) > MAX_SELECTORS_PER_ACTION or any(type(item) is not DerivationSelector for item in selectors):
            raise TypeError("selectors must be a bounded exact DerivationSelector tuple")
        lower, upper = _SELECTOR_COUNTS[action]
        if not lower <= len(selectors) <= upper:
            raise ValueError("selectors do not match the Program ABI 2 action shape")
        if len({item.selector_ref for item in selectors}) != len(selectors):
            raise ValueError("action contains duplicate selectors")
        material = {"abi_version": PROPOSAL_SUPERVISION_ABI_VERSION, "action_index": index, "action_type": action, "selectors": [item.as_dict() for item in selectors]}
        return construct(cls, action_ref=stable_ref("derivation_action_v1", material), selectors=tuple(selectors), **{key: val for key, val in material.items() if key != "selectors"})

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "action_ref": self.action_ref, "action_index": self.action_index, "action_type": self.action_type, "selectors": [item.as_dict() for item in self.selectors]}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BlueprintAction":
        row = exact_fields(value, cls._FIELDS, "BlueprintAction")
        if row["abi_version"] != PROPOSAL_SUPERVISION_ABI_VERSION:
            raise ValueError("unsupported Proposal Supervision ABI")
        rebuilt = cls.create(action_index=row["action_index"], action_type=row["action_type"], selectors=wire_value_tuple(row["selectors"], "selectors", DerivationSelector.from_dict, nonempty=False, maximum=MAX_SELECTORS_PER_ACTION))
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical BlueprintAction")
        return rebuilt


@dataclass(frozen=True, init=False)
class DerivationBlueprint:
    abi_version: int
    blueprint_ref: str
    program_abi_version: int
    actions: tuple[BlueprintAction, ...]
    root_local_refs: tuple[str, ...]

    _FIELDS = frozenset({"abi_version", "blueprint_ref", "program_abi_version", "actions", "root_local_refs"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("DerivationBlueprint")

    @classmethod
    def create(cls, *, actions: tuple[BlueprintAction, ...], root_local_refs: tuple[str, ...]) -> "DerivationBlueprint":
        if type(actions) is not tuple or not actions or len(actions) > MAX_BLUEPRINT_ACTIONS:
            raise ValueError("derivation blueprint violates its action bound")
        if any(type(item) is not BlueprintAction for item in actions):
            raise TypeError("actions must contain exact BlueprintAction values")
        if tuple(item.action_index for item in actions) != tuple(range(len(actions))):
            raise ValueError("blueprint action indices must be contiguous")
        types = tuple(item.action_type for item in actions)
        if len(actions) < 3 or types[:2] != ("select_context", "select_mode") or types[-1] != "complete_program":
            raise ValueError("derive blueprint must select context/mode and end complete_program")
        if "abstain" in types or types.count("select_context") != 1 or types.count("select_mode") != 1 or types.count("complete_program") != 1:
            raise ValueError("derive blueprint has an invalid Program ABI 2 terminal structure")
        roots = exact_ref_tuple(root_local_refs, "root_local_refs", nonempty=True, maximum=8)
        declared = {selector.value_ref for action in actions for selector in action.selectors if selector.selector_kind == "local_node"}
        if any(root not in declared for root in roots):
            raise ValueError("blueprint root is not a declared source-local node")
        material = {"abi_version": PROPOSAL_SUPERVISION_ABI_VERSION, "program_abi_version": PROGRAM_ABI_VERSION, "actions": [item.as_dict() for item in actions], "root_local_refs": list(roots)}
        return construct(cls, blueprint_ref=stable_ref("derivation_blueprint_v1", material), actions=tuple(actions), root_local_refs=roots, abi_version=PROPOSAL_SUPERVISION_ABI_VERSION, program_abi_version=PROGRAM_ABI_VERSION)

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "blueprint_ref": self.blueprint_ref, "program_abi_version": self.program_abi_version, "actions": [item.as_dict() for item in self.actions], "root_local_refs": list(self.root_local_refs)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DerivationBlueprint":
        row = exact_fields(value, cls._FIELDS, "DerivationBlueprint")
        if row["abi_version"] != PROPOSAL_SUPERVISION_ABI_VERSION or row["program_abi_version"] != PROGRAM_ABI_VERSION:
            raise ValueError("unsupported exact ABI for derivation blueprint")
        rebuilt = cls.create(actions=wire_value_tuple(row["actions"], "actions", BlueprintAction.from_dict, nonempty=True, maximum=MAX_BLUEPRINT_ACTIONS), root_local_refs=wire_ref_tuple(row["root_local_refs"], "root_local_refs", nonempty=True, maximum=8))
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical DerivationBlueprint")
        return rebuilt


@dataclass(frozen=True, init=False)
class TypedAbstention:
    abi_version: int
    abstention_ref: str
    gap_kind_ref: str
    critical: bool
    earliest_owner: str
    safe_disposition: str

    _FIELDS = frozenset({"abi_version", "abstention_ref", "gap_kind_ref", "critical", "earliest_owner", "safe_disposition"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("TypedAbstention")

    @classmethod
    def create(cls, *, gap_kind_ref: str, critical: bool, earliest_owner: str, safe_disposition: str) -> "TypedAbstention":
        owner = exact_text(earliest_owner, "earliest_owner", maximum=16)
        disposition = exact_text(safe_disposition, "safe_disposition", maximum=16)
        if owner not in _OWNER_PHASES:
            raise ValueError("unsupported earliest owner")
        if disposition not in _SAFE_DISPOSITIONS:
            raise ValueError("unsupported safe disposition")
        material = {"abi_version": PROPOSAL_SUPERVISION_ABI_VERSION, "gap_kind_ref": exact_ref(gap_kind_ref, "gap_kind_ref", prefix="gap_kind:"), "critical": exact_bool(critical, "critical"), "earliest_owner": owner, "safe_disposition": disposition}
        return construct(cls, abstention_ref=stable_ref("typed_abstention_v1", material), **material)

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "abstention_ref": self.abstention_ref, "gap_kind_ref": self.gap_kind_ref, "critical": self.critical, "earliest_owner": self.earliest_owner, "safe_disposition": self.safe_disposition}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TypedAbstention":
        row = exact_fields(value, cls._FIELDS, "TypedAbstention")
        if row["abi_version"] != PROPOSAL_SUPERVISION_ABI_VERSION:
            raise ValueError("unsupported Proposal Supervision ABI")
        rebuilt = cls.create(gap_kind_ref=row["gap_kind_ref"], critical=row["critical"], earliest_owner=row["earliest_owner"], safe_disposition=row["safe_disposition"])
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical TypedAbstention")
        return rebuilt


@dataclass(frozen=True, init=False)
class ProposalTarget:
    abi_version: int
    proposal_target_ref: str
    source_case_ref: str
    target_kind: str
    expected_expression_refs: tuple[str, ...]
    expression_relation: str
    derivations: tuple[DerivationBlueprint, ...]
    abstention: TypedAbstention | None
    review_refs: tuple[str, ...]

    _FIELDS = frozenset({"abi_version", "proposal_target_ref", "source_case_ref", "target_kind", "expected_expression_refs", "expression_relation", "derivations", "abstention", "review_refs"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("ProposalTarget")

    @classmethod
    def create(cls, *, source_case_ref: str, target_kind: str, expected_expression_refs: tuple[str, ...], expression_relation: str, derivations: tuple[DerivationBlueprint, ...], abstention: TypedAbstention | None, review_refs: tuple[str, ...]) -> "ProposalTarget":
        kind = exact_text(target_kind, "target_kind", maximum=16)
        if kind not in {"derive", "abstain"}:
            raise ValueError("unsupported proposal target kind")
        if expression_relation != "exact":
            raise ValueError("proposal supervision requires exact expression relation")
        expressions = exact_content_ref_tuple(expected_expression_refs, "expected_expression_refs", nonempty=kind == "derive", maximum=64, prefix="expression:")
        if type(derivations) is not tuple or len(derivations) > MAX_DERIVATIONS_PER_CASE:
            raise ValueError("proposal target violates its derivation bound")
        if any(type(item) is not DerivationBlueprint for item in derivations):
            raise TypeError("derivations must contain exact DerivationBlueprint values")
        if len({item.blueprint_ref for item in derivations}) != len(derivations):
            raise ValueError("proposal target contains duplicate derivations")
        if tuple(item.blueprint_ref for item in derivations) != tuple(sorted(item.blueprint_ref for item in derivations)):
            raise ValueError("derivations must be in canonical order")
        if kind == "derive" and (not derivations or abstention is not None):
            raise ValueError("derive target requires derivations and no abstention")
        if kind == "abstain" and (expressions or derivations or type(abstention) is not TypedAbstention):
            raise ValueError("abstain target requires only one typed abstention")
        material = {"abi_version": PROPOSAL_SUPERVISION_ABI_VERSION, "source_case_ref": exact_case_ref(source_case_ref), "target_kind": kind, "expected_expression_refs": list(expressions), "expression_relation": "exact", "derivations": [item.as_dict() for item in derivations], "abstention": None if abstention is None else abstention.as_dict(), "review_refs": list(exact_review_refs(review_refs))}
        return construct(cls, proposal_target_ref=stable_ref("proposal_supervision_v1", material), expected_expression_refs=expressions, derivations=tuple(derivations), abstention=abstention, review_refs=tuple(material["review_refs"]), **{key: val for key, val in material.items() if key not in {"expected_expression_refs", "derivations", "abstention", "review_refs"}})

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "proposal_target_ref": self.proposal_target_ref, "source_case_ref": self.source_case_ref, "target_kind": self.target_kind, "expected_expression_refs": list(self.expected_expression_refs), "expression_relation": self.expression_relation, "derivations": [item.as_dict() for item in self.derivations], "abstention": None if self.abstention is None else self.abstention.as_dict(), "review_refs": list(self.review_refs)}

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProposalTarget":
        row = exact_fields(value, cls._FIELDS, "ProposalTarget")
        if row["abi_version"] != PROPOSAL_SUPERVISION_ABI_VERSION:
            raise ValueError("unsupported Proposal Supervision ABI")
        if row["abstention"] is not None and type(row["abstention"]) is not dict:
            raise TypeError("abstention must be an exact object or null")
        rebuilt = cls.create(source_case_ref=row["source_case_ref"], target_kind=row["target_kind"], expected_expression_refs=wire_content_ref_tuple(row["expected_expression_refs"], "expected_expression_refs", nonempty=row["target_kind"] == "derive", maximum=64, prefix="expression:"), expression_relation=row["expression_relation"], derivations=wire_value_tuple(row["derivations"], "derivations", DerivationBlueprint.from_dict, nonempty=row["target_kind"] == "derive", maximum=MAX_DERIVATIONS_PER_CASE), abstention=None if row["abstention"] is None else TypedAbstention.from_dict(row["abstention"]), review_refs=wire_ref_tuple(row["review_refs"], "review_refs", nonempty=True))
        if rebuilt.proposal_target_ref != row["proposal_target_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical ProposalTarget")
        return rebuilt

    @classmethod
    def from_json_bytes(cls, raw: object) -> "ProposalTarget":
        return strict_decode(raw, cls.from_dict, owner="proposal supervision")


@dataclass(frozen=True, init=False)
class RealizationSlot:
    abi_version: int
    slot_ref: str
    semantic_ref: str
    required: bool

    _FIELDS = frozenset({"abi_version", "slot_ref", "semantic_ref", "required"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("RealizationSlot")

    @classmethod
    def create(cls, *, slot_ref: str, semantic_ref: str, required: bool) -> "RealizationSlot":
        return construct(cls, abi_version=REALIZATION_SUPERVISION_ABI_VERSION, slot_ref=exact_ref(slot_ref, "slot_ref", prefix="response_slot:"), semantic_ref=exact_ref(semantic_ref, "semantic_ref"), required=exact_bool(required, "required"))

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "slot_ref": self.slot_ref, "semantic_ref": self.semantic_ref, "required": self.required}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RealizationSlot":
        row = exact_fields(value, cls._FIELDS, "RealizationSlot")
        if row["abi_version"] != REALIZATION_SUPERVISION_ABI_VERSION:
            raise ValueError("unsupported Realization Supervision ABI")
        rebuilt = cls.create(slot_ref=row["slot_ref"], semantic_ref=row["semantic_ref"], required=row["required"])
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical RealizationSlot")
        return rebuilt


@dataclass(frozen=True, init=False)
class ReferenceFormChoice:
    abi_version: int
    participant_ref: str
    surface_form: str

    _FIELDS = frozenset({"abi_version", "participant_ref", "surface_form"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("ReferenceFormChoice")

    @classmethod
    def create(cls, *, participant_ref: str, surface_form: str) -> "ReferenceFormChoice":
        return construct(cls, abi_version=REALIZATION_SUPERVISION_ABI_VERSION, participant_ref=exact_ref(participant_ref, "participant_ref", prefix="participant:"), surface_form=exact_text(surface_form, "surface_form", maximum=128))

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "participant_ref": self.participant_ref, "surface_form": self.surface_form}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReferenceFormChoice":
        row = exact_fields(value, cls._FIELDS, "ReferenceFormChoice")
        if row["abi_version"] != REALIZATION_SUPERVISION_ABI_VERSION:
            raise ValueError("unsupported Realization Supervision ABI")
        rebuilt = cls.create(participant_ref=row["participant_ref"], surface_form=row["surface_form"])
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical ReferenceFormChoice")
        return rebuilt


@dataclass(frozen=True, init=False)
class LiteralAlignment:
    abi_version: int
    alignment_ref: str
    slot_ref: str
    copy_source_kind: str
    copy_source_ref: str
    source_literal: str
    source_start: int
    source_end: int
    surface_start: int
    surface_end: int

    _FIELDS = frozenset({"abi_version", "alignment_ref", "slot_ref", "copy_source_kind", "copy_source_ref", "source_literal", "source_start", "source_end", "surface_start", "surface_end"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("LiteralAlignment")

    @classmethod
    def create(cls, *, slot_ref: str, copy_source_kind: str, copy_source_ref: str, source_literal: str, source_start: int, source_end: int, surface_start: int, surface_end: int) -> "LiteralAlignment":
        kind = exact_text(copy_source_kind, "copy_source_kind", maximum=32)
        if kind == "input_surface":
            raise ValueError("input surface cannot author realization gold")
        if kind not in _COPY_SOURCE_KINDS:
            raise ValueError("unsupported literal copy source kind")
        literal = exact_text(source_literal, "source_literal", maximum=MAX_R4_TEXT_CHARS)
        if any(type(value) is not int for value in (source_start, source_end, surface_start, surface_end)):
            raise TypeError("literal alignment spans must use exact integers")
        start = exact_int(source_start, "source_start", maximum=MAX_R4_TEXT_CHARS)
        end = exact_int(source_end, "source_end", maximum=MAX_R4_TEXT_CHARS)
        out_start = exact_int(surface_start, "surface_start", maximum=MAX_R4_TEXT_CHARS)
        out_end = exact_int(surface_end, "surface_end", maximum=MAX_R4_TEXT_CHARS)
        if not start < end <= len(literal) or not out_start < out_end:
            raise ValueError("literal alignment has an invalid span")
        material = {"abi_version": REALIZATION_SUPERVISION_ABI_VERSION, "slot_ref": exact_ref(slot_ref, "slot_ref", prefix="response_slot:"), "copy_source_kind": kind, "copy_source_ref": exact_ref(copy_source_ref, "copy_source_ref"), "source_literal": literal, "source_start": start, "source_end": end, "surface_start": out_start, "surface_end": out_end}
        return construct(cls, alignment_ref=stable_ref("literal_alignment_v1", material), **material)

    def as_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in ("abi_version", "alignment_ref", "slot_ref", "copy_source_kind", "copy_source_ref", "source_literal", "source_start", "source_end", "surface_start", "surface_end")}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LiteralAlignment":
        row = exact_fields(value, cls._FIELDS, "LiteralAlignment")
        if row["abi_version"] != REALIZATION_SUPERVISION_ABI_VERSION:
            raise ValueError("unsupported Realization Supervision ABI")
        rebuilt = cls.create(**{key: row[key] for key in cls._FIELDS if key not in {"abi_version", "alignment_ref"}})
        if rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical literal alignment")
        return rebuilt


@dataclass(frozen=True, init=False)
class RealizationRow:
    abi_version: int
    realization_ref: str
    source_case_ref: str
    response_signature_ref: str
    expression_refs: tuple[str, ...]
    discourse_action_ref: str
    polarity_ref: str
    modality_ref: str
    epistemic_status_ref: str
    output_speaker_ref: str
    output_addressee_ref: str
    authorized_surface: str
    language: str
    semantic_slots: tuple[RealizationSlot, ...]
    reference_forms: tuple[ReferenceFormChoice, ...]
    literal_alignments: tuple[LiteralAlignment, ...]
    review_refs: tuple[str, ...]

    _FIELDS = frozenset({"abi_version", "realization_ref", "source_case_ref", "response_signature_ref", "expression_refs", "discourse_action_ref", "polarity_ref", "modality_ref", "epistemic_status_ref", "output_speaker_ref", "output_addressee_ref", "authorized_surface", "language", "semantic_slots", "reference_forms", "literal_alignments", "review_refs"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("RealizationRow")

    @classmethod
    def create(cls, *, source_case_ref: str, response_signature_ref: str, expression_refs: tuple[str, ...], discourse_action_ref: str, polarity_ref: str, modality_ref: str, epistemic_status_ref: str, output_speaker_ref: str, output_addressee_ref: str, authorized_surface: str, language: str, semantic_slots: tuple[RealizationSlot, ...], reference_forms: tuple[ReferenceFormChoice, ...], literal_alignments: tuple[LiteralAlignment, ...], review_refs: tuple[str, ...]) -> "RealizationRow":
        surface = exact_text(authorized_surface, "authorized_surface", maximum=MAX_R4_TEXT_CHARS)
        language_value = exact_text(language, "language", maximum=64)
        if _LANGUAGE_RE.fullmatch(language_value) is None:
            raise ValueError("language is not canonical")
        slots = exact_value_tuple(semantic_slots, "semantic_slots", RealizationSlot, nonempty=True, maximum=MAX_REALIZATION_SLOTS, identity=lambda item: item.slot_ref)
        forms = exact_value_tuple(reference_forms, "reference_forms", ReferenceFormChoice, nonempty=False, maximum=MAX_REFERENCE_FORMS, identity=lambda item: item.participant_ref)
        alignments = exact_value_tuple(literal_alignments, "literal_alignments", LiteralAlignment, nonempty=False, maximum=MAX_LITERAL_ALIGNMENTS, identity=lambda item: item.alignment_ref)
        slot_refs = {item.slot_ref for item in slots}
        for alignment in alignments:
            if alignment.slot_ref not in slot_refs or alignment.surface_end > len(surface) or surface[alignment.surface_start:alignment.surface_end] != alignment.source_literal[alignment.source_start:alignment.source_end]:
                raise ValueError("literal alignment does not exactly match a declared slot and surface span")
        material = {"abi_version": REALIZATION_SUPERVISION_ABI_VERSION, "source_case_ref": exact_case_ref(source_case_ref), "response_signature_ref": exact_content_ref(response_signature_ref, "response_signature_ref", prefix="response_signature:"), "expression_refs": list(exact_content_ref_tuple(expression_refs, "expression_refs", nonempty=True, maximum=64, prefix="expression:")), "discourse_action_ref": exact_ref(discourse_action_ref, "discourse_action_ref"), "polarity_ref": exact_ref(polarity_ref, "polarity_ref", prefix="polarity:"), "modality_ref": exact_ref(modality_ref, "modality_ref", prefix="modality:"), "epistemic_status_ref": exact_ref(epistemic_status_ref, "epistemic_status_ref", prefix="epistemic_status:"), "output_speaker_ref": exact_ref(output_speaker_ref, "output_speaker_ref", prefix="participant:"), "output_addressee_ref": exact_ref(output_addressee_ref, "output_addressee_ref", prefix="participant:"), "authorized_surface": surface, "language": language_value, "semantic_slots": [item.as_dict() for item in slots], "reference_forms": [item.as_dict() for item in forms], "literal_alignments": [item.as_dict() for item in alignments], "review_refs": list(exact_review_refs(review_refs))}
        return construct(cls, realization_ref=stable_ref("realization_supervision_v1", material), expression_refs=tuple(material["expression_refs"]), semantic_slots=slots, reference_forms=forms, literal_alignments=alignments, review_refs=tuple(material["review_refs"]), **{key: val for key, val in material.items() if key not in {"expression_refs", "semantic_slots", "reference_forms", "literal_alignments", "review_refs"}})

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "realization_ref": self.realization_ref, "source_case_ref": self.source_case_ref, "response_signature_ref": self.response_signature_ref, "expression_refs": list(self.expression_refs), "discourse_action_ref": self.discourse_action_ref, "polarity_ref": self.polarity_ref, "modality_ref": self.modality_ref, "epistemic_status_ref": self.epistemic_status_ref, "output_speaker_ref": self.output_speaker_ref, "output_addressee_ref": self.output_addressee_ref, "authorized_surface": self.authorized_surface, "language": self.language, "semantic_slots": [item.as_dict() for item in self.semantic_slots], "reference_forms": [item.as_dict() for item in self.reference_forms], "literal_alignments": [item.as_dict() for item in self.literal_alignments], "review_refs": list(self.review_refs)}

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RealizationRow":
        row = exact_fields(value, cls._FIELDS, "RealizationRow")
        if row["abi_version"] != REALIZATION_SUPERVISION_ABI_VERSION:
            raise ValueError("unsupported Realization Supervision ABI")
        rebuilt = cls.create(source_case_ref=row["source_case_ref"], response_signature_ref=row["response_signature_ref"], expression_refs=wire_content_ref_tuple(row["expression_refs"], "expression_refs", nonempty=True, maximum=64, prefix="expression:"), discourse_action_ref=row["discourse_action_ref"], polarity_ref=row["polarity_ref"], modality_ref=row["modality_ref"], epistemic_status_ref=row["epistemic_status_ref"], output_speaker_ref=row["output_speaker_ref"], output_addressee_ref=row["output_addressee_ref"], authorized_surface=row["authorized_surface"], language=row["language"], semantic_slots=wire_value_tuple(row["semantic_slots"], "semantic_slots", RealizationSlot.from_dict, nonempty=True, maximum=MAX_REALIZATION_SLOTS), reference_forms=wire_value_tuple(row["reference_forms"], "reference_forms", ReferenceFormChoice.from_dict, nonempty=False, maximum=MAX_REFERENCE_FORMS), literal_alignments=wire_value_tuple(row["literal_alignments"], "literal_alignments", LiteralAlignment.from_dict, nonempty=False, maximum=MAX_LITERAL_ALIGNMENTS), review_refs=wire_ref_tuple(row["review_refs"], "review_refs", nonempty=True))
        if rebuilt.realization_ref != row["realization_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical RealizationRow")
        return rebuilt

    @classmethod
    def from_json_bytes(cls, raw: object) -> "RealizationRow":
        return strict_decode(raw, cls.from_dict, owner="realization supervision")


@dataclass(frozen=True, init=False)
class MutationContract:
    abi_version: int
    mutation_contract_ref: str
    mutation_family_ref: str
    source_case_ref: str
    changed_dimension_ref: str
    expected_earliest_owner: str
    disposition: str
    effect_kind: str
    expected_effect_ref: str | None
    review_refs: tuple[str, ...]

    _FIELDS = frozenset({"abi_version", "mutation_contract_ref", "mutation_family_ref", "source_case_ref", "changed_dimension_ref", "expected_earliest_owner", "disposition", "effect_kind", "expected_effect_ref", "review_refs"})

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise _factory_only("MutationContract")

    @classmethod
    def create(cls, *, mutation_family_ref: str, source_case_ref: str, changed_dimension_ref: str, expected_earliest_owner: str, disposition: str, effect_kind: str, expected_effect_ref: str | None, review_refs: tuple[str, ...]) -> "MutationContract":
        owner = exact_text(expected_earliest_owner, "expected_earliest_owner", maximum=16)
        if owner not in _OWNER_PHASES:
            raise ValueError("unsupported expected earliest owner")
        exact_disposition = exact_text(disposition, "disposition", maximum=16)
        if exact_disposition not in _MUTATION_DISPOSITIONS:
            raise ValueError("unsupported mutation disposition")
        kind = exact_text(effect_kind, "effect_kind", maximum=16)
        if kind not in {"effect", "no_effect"}:
            raise ValueError("unsupported effect kind")
        effect_ref = _wire_optional_ref(expected_effect_ref, "expected_effect_ref")
        if (kind == "effect") != (effect_ref is not None):
            raise ValueError("effect ref must be present exactly for an effect contract")
        material = {"abi_version": MUTATION_CONTRACT_ABI_VERSION, "mutation_family_ref": exact_ref(mutation_family_ref, "mutation_family_ref", prefix="mutation_family:"), "source_case_ref": exact_case_ref(source_case_ref), "changed_dimension_ref": exact_ref(changed_dimension_ref, "changed_dimension_ref"), "expected_earliest_owner": owner, "disposition": exact_disposition, "effect_kind": kind, "expected_effect_ref": effect_ref, "review_refs": list(exact_review_refs(review_refs))}
        return construct(cls, mutation_contract_ref=stable_ref("mutation_contract_v1", material), review_refs=tuple(material["review_refs"]), **{key: val for key, val in material.items() if key != "review_refs"})

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": self.abi_version, "mutation_contract_ref": self.mutation_contract_ref, "mutation_family_ref": self.mutation_family_ref, "source_case_ref": self.source_case_ref, "changed_dimension_ref": self.changed_dimension_ref, "expected_earliest_owner": self.expected_earliest_owner, "disposition": self.disposition, "effect_kind": self.effect_kind, "expected_effect_ref": self.expected_effect_ref, "review_refs": list(self.review_refs)}

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MutationContract":
        row = exact_fields(value, cls._FIELDS, "MutationContract")
        if row["abi_version"] != MUTATION_CONTRACT_ABI_VERSION:
            raise ValueError("unsupported Mutation Contract ABI")
        rebuilt = cls.create(mutation_family_ref=row["mutation_family_ref"], source_case_ref=row["source_case_ref"], changed_dimension_ref=row["changed_dimension_ref"], expected_earliest_owner=row["expected_earliest_owner"], disposition=row["disposition"], effect_kind=row["effect_kind"], expected_effect_ref=row["expected_effect_ref"], review_refs=wire_ref_tuple(row["review_refs"], "review_refs", nonempty=True))
        if rebuilt.mutation_contract_ref != row["mutation_contract_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical MutationContract")
        return rebuilt

    @classmethod
    def from_json_bytes(cls, raw: object) -> "MutationContract":
        return strict_decode(raw, cls.from_dict, owner="mutation contract")


__all__ = [
    "MUTATION_CONTRACT_ABI_VERSION",
    "PROPOSAL_SUPERVISION_ABI_VERSION",
    "R4_REVIEW_MANIFEST_ABI_VERSION",
    "REALIZATION_SUPERVISION_ABI_VERSION",
    "MAX_BLUEPRINT_ACTIONS",
    "MAX_DERIVATIONS_PER_CASE",
    "BlueprintAction",
    "DerivationBlueprint",
    "DerivationSelector",
    "LiteralAlignment",
    "MutationContract",
    "ProposalTarget",
    "R4ReviewManifest",
    "RealizationRow",
    "RealizationSlot",
    "ReferenceFormChoice",
    "ReviewSourceFile",
    "TypedAbstention",
]
