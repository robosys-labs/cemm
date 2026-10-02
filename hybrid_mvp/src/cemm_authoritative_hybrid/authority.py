"""Linked semantic authority: reviewed source records, bounded indexes, hashes.

This module owns :class:`AuthorityBundle`, :class:`LinkedAuthority`, and
:class:`AuthorityLinker`. The linker validates owner, kind, five-operator
role schemas, refs, designations, rules, frames, transition signatures,
capabilities, permissions, policies, adapters, and explicit designations
before returning a :class:`LinkedAuthority`. It builds bounded indexes for
surface/language, target designations, kind, frame, rule signature, state
dimension, event signature, and transition. It emits both a full
content/generation hash and a model-compatibility hash over only the
contribution ABI, semantic kinds/ports, structural action ABI, and model
feature encoding. Compatible reviewed identities, designations, facts, and
rules change the full generation without invalidating weights; any structural
encoding change changes the compatibility hash and blocks model activation
until retraining.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .canonical import sha256_governed_text, stable_ref

__all__ = [
    "AuthorityLinkError",
    "AuthorityStore",
    "AuthorityBundle",
    "DesignationFact",
    "DesignationIndex",
    "LinkedAuthority",
    "AuthorityLinker",
    "AtomRecord",
    "RoleSpec",
    "EventSignature",
    "RuleRecord",
    "DesignationLearningContract",
    "ReviewedSemanticFrame",
    "SourceAttributionControl",
    "ReportedRoleInheritanceControl",
    "CommunicativeControl",
]

FIXED_OPERATORS = frozenset({
    "op:designation", "op:type", "op:relation", "op:state", "op:event",
})


# ---------------------------------------------------------------------------
# Authority record types (owned here)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AtomRecord:
    ref: str
    kind: str
    reviewed: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RoleSpec:
    role: str
    filler_kinds: tuple[str, ...]
    required: bool = True
    proposition_valued: bool = False


@dataclass(frozen=True)
class EventSignature:
    event_type: str
    roles: tuple[RoleSpec, ...]
    valid_session_phases: tuple[str, ...] = ("opening", "active")
    required_capabilities: tuple[str, ...] = ()
    required_permissions: tuple[str, ...] = ()
    adapter_ref: str | None = None
    effect_schema: tuple[Mapping[str, Any], ...] = ()

    @property
    def required_roles(self) -> frozenset[str]:
        return frozenset(item.role for item in self.roles if item.required)


class AuthorityLinkError(Exception):
    """Raised when authority linking fails validation."""


def _freeze_rule_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({
            key: _freeze_rule_value(item) for key, item in value.items()
        })
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_rule_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_rule_value(item) for item in value)
    return value


def _rule_wire_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _rule_wire_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_rule_wire_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_rule_wire_value(item) for item in value)
    return value


@dataclass(frozen=True)
class RuleRecord:
    rule_ref: str
    antecedent: tuple[Mapping[str, Any], ...]
    consequent: tuple[Mapping[str, Any], ...]
    confidence: float = 1.0
    reviewed: bool = True
    source_ref: str | None = None

    def __post_init__(self) -> None:
        for clause in (*self.antecedent, *self.consequent):
            if isinstance(clause, Mapping):
                stance = clause.get("stance", "support")
                if type(stance) is not str or stance not in {"support", "deny"}:
                    raise AuthorityLinkError("rule clause stance must be support or deny")
        object.__setattr__(self, "antecedent", tuple(
            _freeze_rule_value(clause) for clause in self.antecedent
        ))
        object.__setattr__(self, "consequent", tuple(
            _freeze_rule_value(clause) for clause in self.consequent
        ))

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_ref": self.rule_ref,
            "antecedent": _rule_wire_value(self.antecedent),
            "consequent": _rule_wire_value(self.consequent),
            "confidence": self.confidence,
            "reviewed": self.reviewed,
            "source_ref": self.source_ref,
        }


def _validate_role_ref(ref: Any) -> None:
    if (
        type(ref) is not str or not 1 <= len(ref) <= 512
        or not ref.startswith("role:") or any(char.isspace() for char in ref)
        or any(not part for part in ref.split(":"))
    ):
        raise AuthorityLinkError("invalid bounded semantic role ref")


def _validated_source_roles(
    value: Any, allowed_filler_kinds: set[str],
) -> tuple[RoleSpec, ...]:
    """One strict source RoleSpec parser for reviewed frame/contract edges."""
    if type(value) is not list or not 1 <= len(value) <= 16:
        raise AuthorityLinkError("reviewed source roles must be a bounded nonempty list")
    roles: list[RoleSpec] = []
    seen: set[str] = set()
    for row in value:
        if type(row) is not dict or set(row) != {"role", "filler_kinds", "required", "proposition_valued"}:
            raise AuthorityLinkError("reviewed source role has missing or unknown fields")
        ref = row["role"]
        _validate_role_ref(ref)
        if ref in seen:
            raise AuthorityLinkError("duplicate reviewed source role")
        seen.add(ref)
        kinds = row["filler_kinds"]
        if (
            type(kinds) is not list or not 1 <= len(kinds) <= 16
            or any(type(kind) is not str or kind not in allowed_filler_kinds for kind in kinds)
            or len(set(kinds)) != len(kinds)
        ):
            raise AuthorityLinkError("reviewed source role has invalid filler kinds")
        if type(row["required"]) is not bool or type(row["proposition_valued"]) is not bool:
            raise AuthorityLinkError("reviewed source role flags must be booleans")
        if row["proposition_valued"] != ("application" in kinds):
            raise AuthorityLinkError("reviewed source role proposition flag contradicts filler kinds")
        roles.append(RoleSpec(ref, tuple(kinds), row["required"], row["proposition_valued"]))
    return tuple(roles)


@dataclass(frozen=True)
class ReviewedSemanticFrame:
    """Immutable reviewed contribution shape, linked once at activation."""

    frame_ref: str
    target_kind: str
    target_ref: str
    contribution_kinds: tuple[str, ...]
    input_ports: tuple[str, ...]
    output_ports: tuple[str, ...]
    role_candidates: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: Any) -> "ReviewedSemanticFrame":
        if type(value) is not dict or set(value) != {item.name for item in fields(cls)}:
            raise AuthorityLinkError("reviewed frame has missing or unknown fields")
        for name in ("frame_ref", "target_ref"):
            ref = value[name]
            if (
                type(ref) is not str or not 1 <= len(ref) <= 512
                or ":" not in ref or any(char.isspace() for char in ref)
                or any(not part for part in ref.split(":"))
            ):
                raise AuthorityLinkError(f"invalid reviewed frame {name}")
        if not value["frame_ref"].startswith("frame:"):
            raise AuthorityLinkError("reviewed frame identity must be a frame ref")
        if type(value["target_kind"]) is not str:
            raise AuthorityLinkError("reviewed frame target kind must be a string")
        sequences = ("contribution_kinds", "input_ports", "output_ports", "role_candidates")
        for name in sequences:
            sequence = value[name]
            if (
                type(sequence) is not list or not 1 <= len(sequence) <= 16
                or any(type(item) is not str for item in sequence)
                or len(set(sequence)) != len(sequence)
            ):
                raise AuthorityLinkError(f"invalid bounded reviewed frame {name}")
            if name != "contribution_kinds":
                for ref in sequence:
                    _validate_role_ref(ref)
        return cls(**{**value, **{name: tuple(value[name]) for name in sequences}})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceAttributionControl:
    """Reviewed source ownership for one proposition-taking frame role."""

    control_ref: str
    parent_frame_ref: str
    parent_target_ref: str
    content_role_ref: str
    source_role_ref: str
    placement: str

    @classmethod
    def from_dict(cls, value: Any) -> "SourceAttributionControl":
        if type(value) is not dict or set(value) != {item.name for item in fields(cls)}:
            raise AuthorityLinkError(
                "source attribution control has missing or unknown fields"
            )
        for name in (
            "control_ref", "parent_frame_ref", "parent_target_ref",
            "content_role_ref", "source_role_ref",
        ):
            ref = value[name]
            if (
                type(ref) is not str or not 1 <= len(ref) <= 512
                or ":" not in ref or any(char.isspace() for char in ref)
                or any(not part for part in ref.split(":"))
            ):
                raise AuthorityLinkError(f"invalid source attribution {name}")
        if not value["control_ref"].startswith("control:"):
            raise AuthorityLinkError("source attribution identity must be a control ref")
        if not value["parent_frame_ref"].startswith("frame:"):
            raise AuthorityLinkError("source attribution parent must be a frame ref")
        _validate_role_ref(value["content_role_ref"])
        _validate_role_ref(value["source_role_ref"])
        if value["placement"] != "reported":
            raise AuthorityLinkError("unsupported source attribution placement")
        return cls(**value)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReportedRoleInheritanceControl:
    """Reviewed authorization to inherit one report-source role into a child."""

    control_ref: str
    source_attribution_control_ref: str
    child_target_ref: str
    child_role_ref: str
    placement: str

    @classmethod
    def from_dict(cls, value: Any) -> "ReportedRoleInheritanceControl":
        if type(value) is not dict or set(value) != {item.name for item in fields(cls)}:
            raise AuthorityLinkError(
                "reported role inheritance control has missing or unknown fields"
            )
        for name in (
            "control_ref", "source_attribution_control_ref", "child_target_ref",
            "child_role_ref",
        ):
            ref = value[name]
            if (
                type(ref) is not str or not 1 <= len(ref) <= 512
                or ":" not in ref or any(char.isspace() for char in ref)
                or any(not part for part in ref.split(":"))
            ):
                raise AuthorityLinkError(
                    f"invalid reported role inheritance {name}"
                )
        if not value["control_ref"].startswith("control:"):
            raise AuthorityLinkError(
                "reported role inheritance identity must be a control ref"
            )
        if not value["source_attribution_control_ref"].startswith("control:"):
            raise AuthorityLinkError(
                "reported role inheritance source must be a control ref"
            )
        _validate_role_ref(value["child_role_ref"])
        if value["placement"] != "reported":
            raise AuthorityLinkError(
                "unsupported reported role inheritance placement"
            )
        return cls(**value)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommunicativeControl:
    """Reviewed direct communication policy, not an effect or permission grant."""

    control_ref: str
    source_frame_ref: str
    target_ref: str
    actor_role_ref: str
    addressee_role_ref: str
    construction_kind: str = "direct_performed"
    response_kind: str = "reciprocal_event"
    required_capability_ref: str = "cap:respond"

    @classmethod
    def from_dict(cls, value: Any) -> "CommunicativeControl":
        if type(value) is not dict or set(value) != {item.name for item in fields(cls)}:
            raise AuthorityLinkError("communicative control has missing or unknown fields")
        namespaces = {
            "control_ref": "control:", "source_frame_ref": "frame:",
            "target_ref": "event:", "actor_role_ref": "role:",
            "addressee_role_ref": "role:", "required_capability_ref": "cap:",
        }
        for name, prefix in namespaces.items():
            ref = value[name]
            if (
                type(ref) is not str or not 1 <= len(ref) <= 512
                or not ref.startswith(prefix) or any(char.isspace() for char in ref)
                or any(not part for part in ref.split(":"))
            ):
                raise AuthorityLinkError(f"invalid communicative control {name}")
        if type(value["construction_kind"]) is not str or value["construction_kind"] != "direct_performed":
            raise AuthorityLinkError("unsupported communicative construction")
        if type(value["response_kind"]) is not str or value["response_kind"] != "reciprocal_event":
            raise AuthorityLinkError("unsupported communicative response")
        return cls(**value)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DesignationLearningContract:
    """Reviewed existing-target lowering authority, not an execution/review grant.

    Operator/role refs belong to the fixed schemas; other refs must link to
    reviewed atoms. EFFECT may later consume this contract for internal memory
    publication, but its presence never registers an external runtime adapter.
    """

    contract_ref: str
    goal_ref: str
    answer_contract_ref: str
    review_policy_ref: str
    source_operator_ref: str
    source_event_ref: str
    actor_role_ref: str
    surface_role_ref: str
    target_role_ref: str
    capability_ref: str
    permission_ref: str
    commit_operator_ref: str
    designation_label_ref: str
    allowed_target_kinds: tuple[str, ...]
    internal_effect_owner: str
    internal_adapter_ref: str
    requires_explicit_review: bool
    existing_targets_only: bool

    def __post_init__(self) -> None:
        for item in fields(self):
            if item.name.endswith("_ref"):
                value = getattr(self, item.name)
                if (
                    type(value) is not str or not 1 <= len(value) <= 512
                    or ":" not in value or any(char.isspace() for char in value)
                    or any(not part for part in value.split(":"))
                ):
                    raise AuthorityLinkError(f"invalid learning contract ref: {item.name}")
        if self.requires_explicit_review is not True or self.existing_targets_only is not True:
            raise AuthorityLinkError("learning contract requires explicit review and existing targets only")
        if type(self.internal_effect_owner) is not str or self.internal_effect_owner != "EFFECT":
            raise AuthorityLinkError("learning contract lowering must be owned by EFFECT")
        kinds = self.allowed_target_kinds
        supported = {
            "concept", "entity", "event_type", "participant", "relation_type",
            "state_dimension", "state_value",
        }
        if (
            type(kinds) is not tuple or not 1 <= len(kinds) <= len(supported)
            or any(type(kind) is not str or kind not in supported for kind in kinds)
            or len(set(kinds)) != len(kinds) or tuple(sorted(kinds)) != kinds
        ):
            raise AuthorityLinkError("learning contract target kinds must be canonical bounded semantic kinds")

    @classmethod
    def from_dict(cls, value: Any) -> "DesignationLearningContract":
        if type(value) is not dict or set(value) != {item.name for item in fields(cls)}:
            raise AuthorityLinkError("learning contract has missing or unknown fields")
        if type(value["allowed_target_kinds"]) is not list:
            raise AuthorityLinkError("learning contract target kinds must be a list")
        return cls(**{**value, "allowed_target_kinds": tuple(value["allowed_target_kinds"])})

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["allowed_target_kinds"] = list(self.allowed_target_kinds)
        return result


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AuthorityLinkError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


# ---------------------------------------------------------------------------
# AuthorityStore — tracks the active generation
# ---------------------------------------------------------------------------


class AuthorityStore:
    """Holds raw authority data and tracks the active generation.

    ``active_generation`` is set to the generation string on a successful
    link and remains ``None`` on failure.
    """

    __slots__ = ("active_generation",)

    def __init__(self) -> None:
        self.active_generation: str | None = None


# ---------------------------------------------------------------------------
# AuthorityBundle — raw source records + manifest + store
# ---------------------------------------------------------------------------


class AuthorityBundle:
    """Holds raw source records from owner files with a manifest and store.

    The ``manifest`` property returns the manifest dict augmented with a
    ``_store`` key so the linker can set ``active_generation`` on success.
    """

    def __init__(self, manifest_data: Mapping[str, Any], store: AuthorityStore) -> None:
        self._manifest_data = dict(manifest_data)
        self._store = store

    @property
    def manifest(self) -> Mapping[str, Any]:
        """Return manifest dict with store reference for generation tracking."""
        return {**self._manifest_data, "_store": self._store}

    @property
    def store(self) -> AuthorityStore:
        return self._store


# ---------------------------------------------------------------------------
# DesignationIndex — bounded surface/target lookup
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DesignationFact:
    """Canonical surface/target/language identity, distinct from evidence ownership."""

    designation_fact_ref: str
    surface: str
    target_ref: str
    language: str

    @classmethod
    def create(
        cls, *, surface: str, target_ref: str, language: str
    ) -> "DesignationFact":
        if type(surface) is not str or not surface or len(surface) > 512:
            raise ValueError("designation surface must be one bounded exact string")
        if (
            type(target_ref) is not str
            or ":" not in target_ref
            or len(target_ref) > 512
        ):
            raise ValueError("designation target must be one bounded typed ref")
        if type(language) is not str or not language or len(language) > 64:
            raise ValueError("designation language must be one bounded exact string")
        material = {
            "surface": surface,
            "target_ref": target_ref,
            "language": language,
        }
        return cls(
            designation_fact_ref=stable_ref("designation", material),
            surface=surface,
            target_ref=target_ref,
            language=language,
        )


class DesignationIndex:
    """Bounded index for surface→target and target→surface designations.

    Only explicit designations in the source data create entries. Internal
    refs are never automatically lexicalized into surfaces.
    """

    __slots__ = (
        "_facts_by_surface",
        "_facts_by_folded_surface",
        "_facts_by_target",
        "_facts_by_ref",
        "_exact_surface_all_languages",
    )

    def __init__(self, facts: tuple[DesignationFact, ...]) -> None:
        if type(facts) is not tuple or any(
            type(fact) is not DesignationFact for fact in facts
        ):
            raise TypeError("designation index requires exact designation facts")
        facts_by_ref: dict[str, DesignationFact] = {}
        by_surface: dict[tuple[str, str], list[DesignationFact]] = {}
        by_target: dict[tuple[str, str], list[DesignationFact]] = {}
        folded: dict[tuple[str, str], list[DesignationFact]] = {}
        exact_surface: dict[str, list[DesignationFact]] = {}
        for fact in facts:
            if fact.designation_fact_ref in facts_by_ref:
                raise ValueError(
                    f"duplicate designation fact: {fact.designation_fact_ref}"
                )
            facts_by_ref[fact.designation_fact_ref] = fact
            exact_surface.setdefault(fact.surface, []).append(fact)
            by_surface.setdefault((fact.surface, fact.language), []).append(fact)
            by_target.setdefault((fact.target_ref, fact.language), []).append(fact)
            folded.setdefault((fact.surface.casefold(), fact.language), []).append(fact)
        self._facts_by_ref = facts_by_ref
        self._exact_surface_all_languages = {
            key: tuple(sorted(rows, key=lambda row: (row.language, row.target_ref, row.designation_fact_ref)))
            for key, rows in exact_surface.items()
        }
        self._facts_by_surface = {
            key: tuple(
                sorted(rows, key=lambda row: (row.target_ref, row.designation_fact_ref))
            )
            for key, rows in by_surface.items()
        }
        self._facts_by_target = {
            key: tuple(
                sorted(rows, key=lambda row: (row.surface, row.designation_fact_ref))
            )
            for key, rows in by_target.items()
        }
        self._facts_by_folded_surface = {
            key: tuple(
                sorted(rows, key=lambda row: (row.target_ref, row.designation_fact_ref))
            )
            for key, rows in folded.items()
        }

    def facts_for_surface(
        self, surface: str, language: str
    ) -> tuple[DesignationFact, ...]:
        exact = self._facts_by_surface.get((surface, language), ())
        if exact:
            return exact
        return self._facts_by_folded_surface.get((surface.casefold(), language), ())

    def bounded_facts(self, mode: str, key: str, language: str | None, *, maximum: int):
        """Raw bounded exact/folded/target access for a merged evidence reader."""
        if type(maximum) is not int or not 1 <= maximum <= 16:
            raise ValueError("designation maximum must be between one and sixteen")
        if mode == "exact":
            rows = (self._exact_surface_all_languages.get(key, ()) if language is None
                else self._facts_by_surface.get((key, language), ()))
        elif mode == "folded" and language is not None:
            rows = self._facts_by_folded_surface.get((key.casefold(), language), ())
        elif mode == "target" and language is not None:
            rows = self._facts_by_target.get((key, language), ())
        else:
            raise ValueError("unsupported bounded designation lookup")
        return rows[:maximum + 1]

    def exact_facts_for_surface(self, surface: str, maximum: int) -> tuple[tuple[DesignationFact, ...], bool]:
        """Exact language-unspecified retrieval; overflow does not visit omitted rows."""
        if type(surface) is not str or type(maximum) is not int or maximum < 1:
            raise ValueError("exact designation retrieval requires string and positive bound")
        rows = self._exact_surface_all_languages.get(surface, ())
        return rows[:maximum], len(rows) > maximum

    def facts_for_target(
        self, target_ref: str, language: str
    ) -> tuple[DesignationFact, ...]:
        return self._facts_by_target.get((target_ref, language), ())

    def resolve_fact(self, designation_fact_ref: str) -> DesignationFact | None:
        return self._facts_by_ref.get(designation_fact_ref)

    def for_surface(self, surface: str, language: str) -> tuple[str, ...]:
        """Return target refs designated by ``surface`` in ``language``.

        Exact reviewed identity wins.  A bounded Unicode case-folded lookup is
        used only when the exact surface is absent; collisions remain explicit
        alternatives rather than being resolved by spelling heuristics.
        """
        return tuple(
            fact.target_ref for fact in self.facts_for_surface(surface, language)
        )

    def for_target(self, target: str, language: str) -> tuple[str, ...]:
        """Return surfaces that designate ``target`` in ``language``."""
        return tuple(
            fact.surface for fact in self.facts_for_target(target, language)
        )

    def canonical_surface_for_target(
        self,
        surface: str,
        target: str,
        language: str,
    ) -> str | None:
        """Return the linked surface identity matching one target.

        Exact target-linked surfaces are preserved.  Case-folded recovery is
        admitted only when it identifies one canonical reviewed surface for
        the target; ambiguous folded spellings fail closed.
        """
        exact_facts = self._facts_by_surface.get((surface, language), ())
        if any(fact.target_ref == target for fact in exact_facts):
            return surface
        matches = tuple(
            fact.surface
            for fact in self._facts_by_target.get((target, language), ())
            if fact.surface.casefold() == surface.casefold()
        )
        return matches[0] if len(matches) == 1 else None


# ---------------------------------------------------------------------------
# LinkedAuthority — validated, indexed result of linking
# ---------------------------------------------------------------------------


class LinkedAuthority:
    """The validated, indexed result of linking one authority generation.

    Attributes:
        content_hash: full generation hash over all content.
        model_compatibility_hash: hash over structural encoding only.
        generation: the authority generation string.
        designations: :class:`DesignationIndex` for surface/target lookup.
        atoms: dict of ref → :class:`AtomRecord`.
        event_signatures: dict of event_type → :class:`EventSignature`.
        rules: dict of rule_ref → :class:`RuleRecord`.
        capabilities: dict of participant → list of capability refs.
        permissions: tuple of (participant, permission, event) triples.
        adapters: tuple of adapter refs.
        operator_roles: dict of operator → list of role names.
        value_dimensions: dict of value ref → dimension ref.
    """

    __slots__ = (
        "model_compatibility_hash",
        "designations",
        "atoms",
        "event_signatures",
        "capabilities",
        "permissions",
        "adapters",
        "operator_roles",
        "value_dimensions",
        "definition_targets",
        "_by_kind",
        "_by_frame",
        "_by_rule_signature",
        "_by_state_dimension",
        "_by_event_signature",
        "_by_transition",
        "_by_transition_signature",
        "_learning_contracts_by_ref",
        "_learning_contracts_by_source",
        "_capability_grants",
        "_permission_grants",
        "_reviewed_frames_by_target",
        "_source_attribution_by_parent_role",
        "_reported_role_inheritance_by_signature",
        "_rule_generation_state",
        "_communicative_generation_state",
    )

    def __init__(
        self,
        content_hash: str,
        model_compatibility_hash: str,
        generation: str,
        designations: DesignationIndex,
        atoms: dict[str, AtomRecord],
        event_signatures: dict[str, EventSignature],
        rules: dict[str, RuleRecord],
        capabilities: dict[str, list[str]],
        permissions: tuple[tuple[str, str, str], ...],
        adapters: tuple[str, ...],
        operator_roles: dict[str, list[str]],
        value_dimensions: dict[str, str],
        definition_targets: dict[str, str],
        by_kind: dict[str, frozenset[str]],
        by_frame: dict[str, frozenset[str]],
        by_rule_signature: dict[str, dict[str, Any]],
        by_state_dimension: dict[str, frozenset[str]],
        by_event_signature: dict[str, EventSignature],
        by_transition: dict[str, dict[str, Any]],
        by_transition_signature: dict[tuple[str, str, str], dict[str, Any]],
        learning_contracts: tuple[DesignationLearningContract, ...] = (),
        reviewed_frames: tuple[ReviewedSemanticFrame, ...] = (),
        source_attribution_controls: tuple[SourceAttributionControl, ...] = (),
        reported_role_inheritance_controls: tuple[
            ReportedRoleInheritanceControl, ...
        ] = (),
        communicative_controls: tuple[CommunicativeControl, ...] = (),
    ) -> None:
        self.model_compatibility_hash = model_compatibility_hash
        self._rule_generation_state = (
            generation,
            content_hash,
            MappingProxyType(dict(rules)),
        )
        self.designations = designations
        self.atoms = atoms
        self.event_signatures = event_signatures
        self.capabilities = capabilities
        self.permissions = permissions
        self.adapters = adapters
        self.operator_roles = operator_roles
        self.value_dimensions = value_dimensions
        self.definition_targets = definition_targets
        self._by_kind = by_kind
        self._by_frame = by_frame
        self._by_rule_signature = by_rule_signature
        self._by_state_dimension = by_state_dimension
        self._by_event_signature = by_event_signature
        self._by_transition = by_transition
        self._by_transition_signature = by_transition_signature
        self._learning_contracts_by_ref = {
            contract.contract_ref: contract for contract in learning_contracts
        }
        self._learning_contracts_by_source = {
            (contract.source_operator_ref, contract.source_event_ref): contract
            for contract in learning_contracts
        }
        self._capability_grants = frozenset(
            (participant, capability)
            for participant, refs in capabilities.items() for capability in refs
        )
        self._permission_grants = frozenset(permissions)
        frame_targets: dict[str, list[ReviewedSemanticFrame]] = {}
        for frame in reviewed_frames:
            frame_targets.setdefault(frame.target_ref, []).append(frame)
        self._reviewed_frames_by_target = {
            target: tuple(frames) for target, frames in frame_targets.items()
        }
        self._source_attribution_by_parent_role = MappingProxyType({
            (control.parent_target_ref, control.content_role_ref): control
            for control in source_attribution_controls
        })
        source_controls = {
            control.control_ref: control for control in source_attribution_controls
        }
        self._reported_role_inheritance_by_signature = MappingProxyType({
            (
                source_controls[control.source_attribution_control_ref].parent_target_ref,
                source_controls[control.source_attribution_control_ref].content_role_ref,
                control.child_target_ref,
                control.child_role_ref,
            ): control
            for control in reported_role_inheritance_controls
        })
        self._communicative_generation_state = (
            self._rule_generation_state,
            MappingProxyType({control.target_ref: control for control in communicative_controls}),
        )

    @property
    def generation(self) -> str:
        return self._rule_generation_state[0]

    @property
    def content_hash(self) -> str:
        return self._rule_generation_state[1]

    @property
    def rules(self) -> Mapping[str, RuleRecord]:
        return self._rule_generation_state[2]

    def rule_generation_snapshot(self) -> tuple[str, str, Mapping[str, RuleRecord]]:
        return self._rule_generation_state

    def _publish_rule_generation(
        self,
        *,
        parent_generation: str,
        new_generation: str,
        new_content_hash: str,
        rules: Mapping[str, RuleRecord],
    ) -> None:
        """Coordinator-internal atomic publication; not a semantic write API."""
        if parent_generation != self.generation:
            raise AuthorityLinkError("rule publication parent generation is stale")
        if type(new_generation) is not str or not new_generation or new_generation == parent_generation:
            raise AuthorityLinkError("rule publication must advance generation")
        if (type(new_content_hash) is not str or not new_content_hash
                or new_content_hash == self.content_hash):
            raise AuthorityLinkError("rule publication must advance content hash")
        if not isinstance(rules, Mapping) or any(
            type(ref) is not str or not ref or type(rule) is not RuleRecord
            or rule.rule_ref != ref
            for ref, rule in rules.items()
        ):
            raise AuthorityLinkError("rule publication contains an invalid rule collection")
        replacement = MappingProxyType(dict(rules))
        self._rule_generation_state = (new_generation, new_content_hash, replacement)

    def reviewed_frames_for_target(self, target_ref: str) -> tuple[ReviewedSemanticFrame, ...]:
        """Exact activation-cached lookup; no filesystem or bundle scan."""
        return self._reviewed_frames_by_target.get(target_ref, ())

    @property
    def communicative_controls(self) -> Mapping[str, CommunicativeControl]:
        """Immutable target index bound to the exact activated authority state."""
        state, controls = self._communicative_generation_state
        if state is not self._rule_generation_state:
            raise AuthorityLinkError("communicative authority activation identity is stale")
        return controls

    def communicative_control_for_target(self, target_ref: str) -> CommunicativeControl | None:
        """O(1) typed policy lookup; absent authority grants nothing."""
        return self.communicative_controls.get(target_ref)

    def source_attribution_control(
        self, parent_target_ref: str, content_role_ref: str
    ) -> SourceAttributionControl | None:
        """Exact activation-cached source control; absent authority has no default."""
        return self._source_attribution_by_parent_role.get(
            (parent_target_ref, content_role_ref)
        )

    def reported_role_inheritance_control(
        self,
        parent_target_ref: str,
        content_role_ref: str,
        child_target_ref: str,
        child_role_ref: str,
    ) -> ReportedRoleInheritanceControl | None:
        """Exact activation-cached report-role authorization; no structural default."""
        return self._reported_role_inheritance_by_signature.get(
            (
                parent_target_ref,
                content_role_ref,
                child_target_ref,
                child_role_ref,
            )
        )

    def capability_granted(self, actor_ref: str, capability_ref: str) -> bool:
        """Activation-indexed actor-specific capability authority."""
        return (actor_ref, capability_ref) in self._capability_grants

    def permission_granted(self, actor_ref: str, permission_ref: str, event_ref: str) -> bool:
        """Activation-indexed exact actor/permission/event authorization."""
        return (actor_ref, permission_ref, event_ref) in self._permission_grants

    def learning_contract(self, contract_ref: str) -> DesignationLearningContract | None:
        """Exact activation-built lookup; absent authority has no default."""
        return self._learning_contracts_by_ref.get(contract_ref)

    def learning_contract_for_source(
        self, operator_ref: str, event_ref: str
    ) -> DesignationLearningContract | None:
        """Resolve one reviewed source signature without scanning the bundle."""
        return self._learning_contracts_by_source.get((operator_ref, event_ref))

    def by_kind(self, kind: str) -> frozenset[str]:
        """Return all atom refs of the given kind."""
        return self._by_kind.get(kind, frozenset())

    def by_frame(self, frame: str) -> frozenset[str]:
        """Return all atom refs in the given frame."""
        return self._by_frame.get(frame, frozenset())

    def by_rule_signature(self, rule_ref: str) -> dict[str, Any] | None:
        """Return the raw rule data for ``rule_ref``."""
        return self._by_rule_signature.get(rule_ref)

    def by_state_dimension(self, dimension: str) -> frozenset[str]:
        """Return all value refs for the given state dimension."""
        return self._by_state_dimension.get(dimension, frozenset())

    def by_event_signature(self, event_type: str) -> EventSignature | None:
        """Return the event signature for ``event_type``."""
        return self._by_event_signature.get(event_type)

    def by_transition(self, key: str) -> dict[str, Any] | None:
        """Return the transition for ``key``."""
        return self._by_transition.get(key)

    def transition_for(
        self, event_type: str, dimension: str, to_value: str
    ) -> dict[str, Any] | None:
        """Return the exact reviewed transition matching an application."""
        return self._by_transition_signature.get((event_type, dimension, to_value))


# ---------------------------------------------------------------------------
# AuthorityLinker — validates and links authority source records
# ---------------------------------------------------------------------------


class AuthorityLinker:
    """Validates owner files and returns a :class:`LinkedAuthority`.

    ``link`` accepts either a manifest file path or a manifest dict (which may
    carry a ``_store`` key for generation tracking). ``link_path`` accepts a
    path to a manifest JSON file.
    """

    def link(self, manifest: Any) -> LinkedAuthority:
        if isinstance(manifest, (str, Path)):
            return self._link_from_path(Path(manifest))
        if isinstance(manifest, Mapping):
            return self._link_from_dict(manifest)
        raise AuthorityLinkError(f"unsupported manifest type: {type(manifest)}")

    def link_path(self, path: str | Path) -> LinkedAuthority:
        return self._link_from_path(Path(path))

    # -- internal ----------------------------------------------------------

    def _link_from_path(self, path: Path) -> LinkedAuthority:
        path = path.resolve()
        if not path.exists():
            raise AuthorityLinkError(f"manifest not found: {path}")
        manifest_data = json.loads(
            path.read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_json_object
        )
        return self._link_manifest(manifest_data, base_dir=path.parent, store=None)

    def _link_from_dict(self, manifest_dict: Mapping[str, Any]) -> LinkedAuthority:
        store = manifest_dict.get("_store")
        return self._link_manifest(manifest_dict, base_dir=None, store=store)

    def _link_manifest(
        self,
        manifest_data: Mapping[str, Any],
        base_dir: Path | None,
        store: AuthorityStore | None,
    ) -> LinkedAuthority:
        generation = manifest_data.get("generation")
        if not generation:
            raise AuthorityLinkError("manifest missing generation")
        abi_version = manifest_data.get("abi_version", 1)
        owners_meta = manifest_data.get("owners", [])
        if not owners_meta:
            raise AuthorityLinkError("manifest has no owners")

        # Accumulators for merged data across all owners
        all_atoms: dict[str, tuple[AtomRecord, str]] = {}
        all_designations: list[dict[str, Any]] = []
        all_event_signatures: list[dict[str, Any]] = []
        all_rules: list[dict[str, Any]] = []
        all_capabilities: dict[str, list[str]] = {}
        all_permissions: list[list[str]] = []
        all_adapters: list[str] = []
        all_operator_roles: dict[str, list[str]] = {}
        all_value_dimensions: dict[str, str] = {}
        all_definition_targets: dict[str, str] = {}
        all_transitions: list[dict[str, Any]] = []
        all_learning_contracts: list[tuple[DesignationLearningContract, str]] = []
        all_frames: list[ReviewedSemanticFrame] = []
        all_source_attribution_controls: list[SourceAttributionControl] = []
        all_reported_role_inheritance_controls: list[
            ReportedRoleInheritanceControl
        ] = []
        all_communicative_controls: list[CommunicativeControl] = []
        owner_names: set[str] = set()
        owner_paths: set[Path] = set()

        # Load and validate each owner file
        for owner_meta in owners_meta:
            owner_name = owner_meta["name"]
            if type(owner_name) is not str or not owner_name or owner_name in owner_names:
                raise AuthorityLinkError("invalid or duplicate owner name")
            owner_names.add(owner_name)
            owner_path = Path(owner_meta["path"])
            if not owner_path.is_absolute():
                if base_dir is None:
                    raise AuthorityLinkError(
                        f"cannot resolve relative path without base dir: {owner_path}"
                    )
                owner_path = base_dir / owner_path
            owner_path = owner_path.resolve()
            if owner_path in owner_paths:
                raise AuthorityLinkError("duplicate owner path")
            owner_paths.add(owner_path)

            # Verify file hash
            try:
                actual_hash = sha256_governed_text(owner_path)
            except (OSError, UnicodeError) as exc:
                raise AuthorityLinkError(f"cannot read owner {owner_name}") from exc
            if actual_hash != owner_meta["sha256"]:
                raise AuthorityLinkError(
                    f"owner {owner_name} hash mismatch"
                )

            try:
                owner_data = json.loads(
                    owner_path.read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_json_object
                )
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise AuthorityLinkError(f"invalid owner source {owner_name}") from exc
            if type(owner_data) is not dict:
                raise AuthorityLinkError("owner source must be an object")
            if owner_data.get("owner") != owner_name:
                raise AuthorityLinkError(f"owner name mismatch: {owner_name}")
            if "description_graphs" in owner_data:
                raise AuthorityLinkError(
                    "parallel description_graphs authority is forbidden"
                )
            if owner_name == "semantic_affordances" or "frames" in owner_data:
                if set(owner_data) != {
                    "owner", "generation", "frames", "source_attribution_controls",
                    "reported_role_inheritance_controls",
                    "communicative_controls",
                }:
                    raise AuthorityLinkError("reviewed frame owner has missing or unknown fields")
                if owner_data["generation"] != generation:
                    raise AuthorityLinkError("reviewed frame owner generation mismatch")
                if type(owner_data["frames"]) is not list:
                    raise AuthorityLinkError("reviewed frames must be a list")
                all_frames.extend(ReviewedSemanticFrame.from_dict(row) for row in owner_data["frames"])
                controls = owner_data["source_attribution_controls"]
                if type(controls) is not list:
                    raise AuthorityLinkError("source attribution controls must be a list")
                all_source_attribution_controls.extend(
                    SourceAttributionControl.from_dict(row) for row in controls
                )
                inheritance_controls = owner_data[
                    "reported_role_inheritance_controls"
                ]
                if type(inheritance_controls) is not list:
                    raise AuthorityLinkError(
                        "reported role inheritance controls must be a list"
                    )
                all_reported_role_inheritance_controls.extend(
                    ReportedRoleInheritanceControl.from_dict(row)
                    for row in inheritance_controls
                )
                communication = owner_data["communicative_controls"]
                if type(communication) is not list:
                    raise AuthorityLinkError("communicative controls must be a list")
                all_communicative_controls.extend(
                    CommunicativeControl.from_dict(row) for row in communication
                )
            contract_rows = owner_data.get("learning_contracts", [])
            if type(contract_rows) is not list:
                raise AuthorityLinkError("learning_contracts must be a list")
            all_learning_contracts.extend(
                (DesignationLearningContract.from_dict(row), owner_name)
                for row in contract_rows
            )
            # Validate and collect atoms
            for atom_data in owner_data.get("atoms", []):
                ref = atom_data["ref"]
                kind = atom_data["kind"]
                reviewed = atom_data.get("reviewed", True)
                if not reviewed:
                    raise AuthorityLinkError(f"unreviewed atom: {ref}")
                if ref in all_atoms:
                    raise AuthorityLinkError(
                        f"duplicate owner for atom {ref}: "
                        f"{all_atoms[ref][1]} and {owner_name}"
                    )
                all_atoms[ref] = (
                    AtomRecord(ref=ref, kind=kind, reviewed=reviewed),
                    owner_name,
                )

            all_designations.extend(owner_data.get("designations", []))
            all_event_signatures.extend(owner_data.get("event_signatures", []))
            all_rules.extend(owner_data.get("rules", []))

            for participant, caps in owner_data.get("capabilities", {}).items():
                existing = all_capabilities.setdefault(participant, [])
                existing.extend(caps)

            all_permissions.extend(owner_data.get("permissions", []))
            all_adapters.extend(owner_data.get("adapters", []))

            for op, roles in owner_data.get("operator_roles", {}).items():
                if op in all_operator_roles:
                    raise AuthorityLinkError(f"duplicate operator schema owner: {op}")
                # Preserve source type for exact linked-schema validation;
                # converting an object to a list would authorize its keys.
                all_operator_roles[op] = roles

            for value, dim in owner_data.get("value_dimensions", {}).items():
                all_value_dimensions[value] = dim

            for source, target in owner_data.get("definition_targets", {}).items():
                if source in all_definition_targets:
                    raise AuthorityLinkError(
                        f"duplicate definition target owner: {source}"
                    )
                all_definition_targets[source] = target

            all_transitions.extend(owner_data.get("transitions", []))

        learning_contracts = self._validate_learning_contracts(
            all_learning_contracts, all_atoms, all_event_signatures,
            all_operator_roles, all_adapters,
        )
        reviewed_frames = self._validate_reviewed_frames(
            all_frames, all_atoms, all_event_signatures, all_operator_roles,
        )
        source_attribution_controls = self._validate_source_attribution_controls(
            all_source_attribution_controls, reviewed_frames, all_atoms,
            all_event_signatures,
        )
        reported_role_inheritance_controls = (
            self._validate_reported_role_inheritance_controls(
                all_reported_role_inheritance_controls,
                source_attribution_controls,
                all_atoms,
                all_event_signatures,
            )
        )
        communicative_controls = self._validate_communicative_controls(
            all_communicative_controls, reviewed_frames,
            source_attribution_controls, reported_role_inheritance_controls,
            all_atoms, all_event_signatures,
        )

        # -- Validate designations (targets must exist) --------------------
        designation_facts: list[DesignationFact] = []
        designation_fact_refs: set[str] = set()
        for desig in all_designations:
            target = desig["target"]
            if target not in all_atoms:
                raise AuthorityLinkError(f"missing target: {target}")
            try:
                fact = DesignationFact.create(
                    surface=desig["surface"],
                    target_ref=target,
                    language=desig["language"],
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise AuthorityLinkError("designation record is structurally invalid") from exc
            if fact.designation_fact_ref in designation_fact_refs:
                raise AuthorityLinkError(
                    f"duplicate designation fact: {fact.designation_fact_ref}"
                )
            designation_fact_refs.add(fact.designation_fact_ref)
            designation_facts.append(fact)

        # -- Validate operator role schemas --------------------------------
        for op in FIXED_OPERATORS:
            if op not in all_operator_roles:
                raise AuthorityLinkError(f"missing operator role schema: {op}")

        # -- Validate event signatures -------------------------------------
        for es in all_event_signatures:
            event_type = es["event_type"]
            if event_type not in all_atoms:
                raise AuthorityLinkError(
                    f"event signature references unknown event: {event_type}"
                )
            for cap in es.get("required_capabilities", []):
                if cap not in all_atoms:
                    raise AuthorityLinkError(f"missing capability: {cap}")
            for perm in es.get("required_permissions", []):
                if perm not in all_atoms:
                    raise AuthorityLinkError(f"missing permission: {perm}")
            adapter = es.get("adapter_ref")
            if adapter and adapter not in all_atoms:
                raise AuthorityLinkError(f"missing adapter: {adapter}")

        # -- Validate capabilities -----------------------------------------
        for participant, caps in all_capabilities.items():
            if participant not in all_atoms:
                raise AuthorityLinkError(f"missing participant: {participant}")
            for cap in caps:
                if cap not in all_atoms:
                    raise AuthorityLinkError(f"missing capability atom: {cap}")

        # -- Validate permissions ------------------------------------------
        for perm in all_permissions:
            participant, perm_ref, event_ref = perm[0], perm[1], perm[2]
            if participant not in all_atoms:
                raise AuthorityLinkError(f"missing participant: {participant}")
            if perm_ref not in all_atoms:
                raise AuthorityLinkError(f"missing permission atom: {perm_ref}")
            if event_ref not in all_atoms:
                raise AuthorityLinkError(f"missing event atom: {event_ref}")

        # -- Validate adapters ---------------------------------------------
        for adapter in all_adapters:
            if adapter not in all_atoms:
                raise AuthorityLinkError(f"missing adapter atom: {adapter}")

        # -- Validate value dimensions -------------------------------------
        for value, dim in all_value_dimensions.items():
            if value not in all_atoms:
                raise AuthorityLinkError(f"missing value atom: {value}")
            if dim not in all_atoms:
                raise AuthorityLinkError(f"missing dimension atom: {dim}")

        # -- Validate reviewed transitions ---------------------------------
        transition_signatures: set[tuple[str, str, str]] = set()
        transition_refs: set[str] = set()
        for transition in all_transitions:
            required = ("transition_ref", "event_type", "dimension", "to_value")
            if any(
                type(transition.get(field)) is not str or not transition.get(field)
                for field in required
            ):
                raise AuthorityLinkError("transition record is structurally incomplete")
            transition_ref = transition["transition_ref"]
            if transition_ref in transition_refs:
                raise AuthorityLinkError(f"duplicate transition ref: {transition_ref}")
            transition_refs.add(transition_ref)
            event_type = transition["event_type"]
            dimension = transition["dimension"]
            to_value = transition["to_value"]
            from_value = transition.get("from_value")
            if event_type not in all_atoms or all_atoms[event_type][0].kind != "event_type":
                raise AuthorityLinkError(f"transition event is invalid: {event_type}")
            if dimension not in all_atoms or all_atoms[dimension][0].kind != "state_dimension":
                raise AuthorityLinkError(f"transition dimension is invalid: {dimension}")
            if to_value not in all_atoms or all_value_dimensions.get(to_value) != dimension:
                raise AuthorityLinkError(f"transition target value is invalid: {to_value}")
            if from_value is not None and (
                type(from_value) is not str
                or all_value_dimensions.get(from_value) != dimension
            ):
                raise AuthorityLinkError(f"transition source value is invalid: {from_value}")
            adapter = transition.get("adapter_ref")
            if adapter is not None and adapter not in all_adapters:
                raise AuthorityLinkError(f"transition adapter is invalid: {adapter}")
            signature = (event_type, dimension, to_value)
            if signature in transition_signatures:
                raise AuthorityLinkError(
                    "duplicate event/dimension/value transition signature"
                )
            transition_signatures.add(signature)

        for source, target in all_definition_targets.items():
            if source not in all_atoms:
                raise AuthorityLinkError(f"missing definition source atom: {source}")
            if target not in all_atoms:
                raise AuthorityLinkError(f"missing definition target atom: {target}")
            if all_atoms[target][0].kind != "concept":
                raise AuthorityLinkError(
                    f"definition target must be a concept: {target}"
                )

        # -- Build indexes -------------------------------------------------
        atoms_dict = {ref: record for ref, (record, _owner) in all_atoms.items()}

        # Designation index (bounded, explicit only)
        designations = DesignationIndex(tuple(designation_facts))

        # Kind index
        kind_index: dict[str, set[str]] = {}
        for ref, (record, _owner) in all_atoms.items():
            kind_index.setdefault(record.kind, set()).add(ref)
        by_kind = {k: frozenset(v) for k, v in kind_index.items()}

        # Event signature objects and index
        event_sigs: dict[str, EventSignature] = {}
        for es_data in all_event_signatures:
            roles = tuple(
                RoleSpec(
                    role=r["role"],
                    filler_kinds=tuple(r["filler_kinds"]),
                    required=r.get("required", True),
                    proposition_valued=r.get("proposition_valued", False),
                )
                for r in es_data.get("roles", [])
            )
            sig = EventSignature(
                event_type=es_data["event_type"],
                roles=roles,
                valid_session_phases=tuple(
                    es_data.get("valid_session_phases", ("opening", "active"))
                ),
                required_capabilities=tuple(es_data.get("required_capabilities", [])),
                required_permissions=tuple(es_data.get("required_permissions", [])),
                adapter_ref=es_data.get("adapter_ref"),
                effect_schema=tuple(es_data.get("effect_schema", [])),
            )
            event_sigs[es_data["event_type"]] = sig

        # Rule objects and signature index
        rules: dict[str, RuleRecord] = {}
        by_rule_sig: dict[str, dict[str, Any]] = {}
        for rule_data in all_rules:
            ref = rule_data["rule_ref"]
            rules[ref] = RuleRecord(
                rule_ref=ref,
                antecedent=tuple(rule_data.get("antecedent", [])),
                consequent=tuple(rule_data.get("consequent", [])),
                confidence=rule_data.get("confidence", 1.0),
                reviewed=rule_data.get("reviewed", True),
                source_ref=rule_data.get("source_ref"),
            )
            by_rule_sig[ref] = rule_data

        # State dimension index
        state_dim_index: dict[str, set[str]] = {}
        for value, dim in all_value_dimensions.items():
            state_dim_index.setdefault(dim, set()).add(value)
        by_state_dim = {k: frozenset(v) for k, v in state_dim_index.items()}

        # Transition index
        by_transition: dict[str, dict[str, Any]] = {}
        by_transition_signature: dict[tuple[str, str, str], dict[str, Any]] = {}
        for trans in all_transitions:
            key = trans.get("transition_ref", f"trans:{len(by_transition)}")
            by_transition[key] = trans
            by_transition_signature[
                (trans["event_type"], trans["dimension"], trans["to_value"])
            ] = trans

        # -- Compute hashes ------------------------------------------------
        full_payload = {
            "abi_version": abi_version,
            "generation": generation,
            "atoms": {
                ref: {"ref": r.ref, "kind": r.kind, "reviewed": r.reviewed}
                for ref, r in atoms_dict.items()
            },
            "designations": sorted(
                all_designations, key=lambda d: (d["surface"], d["language"], d["target"])
            ),
            "event_signatures": sorted(all_event_signatures, key=lambda e: e["event_type"]),
            "rules": sorted(all_rules, key=lambda r: r["rule_ref"]),
            "capabilities": all_capabilities,
            "permissions": sorted(all_permissions, key=lambda p: (p[0], p[1], p[2])),
            "adapters": sorted(all_adapters),
            "operator_roles": all_operator_roles,
            "value_dimensions": all_value_dimensions,
            "definition_targets": all_definition_targets,
            "transitions": sorted(
                all_transitions, key=lambda t: json.dumps(t, sort_keys=True)
            ),
            "learning_contracts": [contract.to_dict() for contract in learning_contracts],
            "reviewed_frames": [frame.to_dict() for frame in reviewed_frames],
            "communicative_controls": [control.to_dict() for control in communicative_controls],
            "source_attribution_controls": [
                control.to_dict() for control in source_attribution_controls
            ],
            "reported_role_inheritance_controls": [
                control.to_dict()
                for control in reported_role_inheritance_controls
            ],
        }
        content_hash = stable_ref("authority-content", full_payload)

        # Structural / compatibility payload: only encoding-relevant parts
        structural_payload = {
            "abi_version": abi_version,
            "operator_roles": all_operator_roles,
            "kinds": sorted({r.kind for r in atoms_dict.values()}),
            "event_signatures": [
                {
                    "event_type": es["event_type"],
                    "roles": es.get("roles", []),
                }
                for es in sorted(all_event_signatures, key=lambda e: e["event_type"])
            ],
            "value_dimensions": all_value_dimensions,
            "definition_targets": all_definition_targets,
            "reviewed_frames": [frame.to_dict() for frame in reviewed_frames],
            "communicative_controls": [control.to_dict() for control in communicative_controls],
        }
        model_compatibility_hash = stable_ref("authority-compat", structural_payload)

        # -- Set active generation on store --------------------------------
        if store is not None:
            store.active_generation = generation

        return LinkedAuthority(
            content_hash=content_hash,
            model_compatibility_hash=model_compatibility_hash,
            generation=generation,
            designations=designations,
            atoms=atoms_dict,
            event_signatures=event_sigs,
            rules=rules,
            capabilities=all_capabilities,
            permissions=tuple(tuple(p) for p in all_permissions),
            adapters=tuple(all_adapters),
            operator_roles=all_operator_roles,
            value_dimensions=all_value_dimensions,
            definition_targets=all_definition_targets,
            by_kind=by_kind,
            by_frame={frame.frame_ref: frozenset({frame.target_ref}) for frame in reviewed_frames},
            by_rule_signature=by_rule_sig,
            by_state_dimension=by_state_dim,
            by_event_signature=event_sigs,
            by_transition=by_transition,
            by_transition_signature=by_transition_signature,
            learning_contracts=learning_contracts,
            reviewed_frames=reviewed_frames,
            source_attribution_controls=source_attribution_controls,
            reported_role_inheritance_controls=reported_role_inheritance_controls,
            communicative_controls=communicative_controls,
        )

    @staticmethod
    def _validate_reviewed_frames(
        records: list[ReviewedSemanticFrame],
        atoms: dict[str, tuple[AtomRecord, str]],
        signatures: list[dict[str, Any]],
        operator_roles: dict[str, list[str]],
    ) -> tuple[ReviewedSemanticFrame, ...]:
        """Link the currently reviewed event/relation contribution shapes."""
        by_ref: dict[str, ReviewedSemanticFrame] = {}
        target_kinds: dict[str, set[str]] = {}
        signatures_by_event: dict[str, list[dict[str, Any]]] = {}
        filler_kinds = {record.kind for record, _ in atoms.values()} | {"literal", "application"}
        operator_shapes = {
            "event_type": ("op:event", ["role:event", "role:type"]),
            "relation_type": ("op:relation", ["role:subject", "role:relation", "role:object"]),
        }
        for signature in signatures:
            signatures_by_event.setdefault(signature["event_type"], []).append(signature)
        for frame in records:
            if frame.frame_ref in by_ref or frame.frame_ref in atoms:
                raise AuthorityLinkError("duplicate reviewed frame identity")
            target = atoms.get(frame.target_ref)
            if target is None or target[0].kind != frame.target_kind or target[0].reviewed is not True:
                raise AuthorityLinkError("reviewed frame target must match one reviewed atom kind")
            if frame.target_kind not in operator_shapes:
                raise AuthorityLinkError("unsupported reviewed frame target kind")
            operator_ref, expected_schema = operator_shapes[frame.target_kind]
            schema = operator_roles.get(operator_ref)
            if type(schema) is not list or schema != expected_schema:
                raise AuthorityLinkError("reviewed frame requires the complete fixed operator schema")
            if frame.target_kind == "event_type":
                candidates = signatures_by_event.get(frame.target_ref, [])
                if len(candidates) != 1:
                    raise AuthorityLinkError("reviewed event frame requires one linked event signature")
                roles = _validated_source_roles(candidates[0].get("roles"), filler_kinds)
                inputs = tuple(role.role for role in roles)
                outputs = (schema[0],)
                kinds = {"predicate", "anchor", "reference"}
            elif frame.target_kind == "relation_type":
                inputs = (schema[0], schema[2])
                outputs = (schema[1],)
                kinds = {"predicate", "anchor"}
            if not set(frame.contribution_kinds) <= kinds:
                raise AuthorityLinkError("reviewed frame contribution kinds contradict target kind")
            if frame.input_ports != inputs or frame.output_ports != outputs or frame.role_candidates != inputs:
                raise AuthorityLinkError("reviewed frame ports or roles contradict linked signature")
            covered = target_kinds.setdefault(frame.target_ref, set())
            if covered.intersection(frame.contribution_kinds):
                raise AuthorityLinkError("overlapping reviewed frames for one target")
            covered.update(frame.contribution_kinds)
            by_ref[frame.frame_ref] = frame
        return tuple(by_ref[ref] for ref in sorted(by_ref))

    @staticmethod
    def _validate_source_attribution_controls(
        records: list[SourceAttributionControl],
        frames: tuple[ReviewedSemanticFrame, ...],
        atoms: dict[str, tuple[AtomRecord, str]],
        signatures: list[dict[str, Any]],
    ) -> tuple[SourceAttributionControl, ...]:
        """Link source controls to one reviewed frame and exact event signature."""
        frames_by_ref = {frame.frame_ref: frame for frame in frames}
        signatures_by_event: dict[str, list[dict[str, Any]]] = {}
        for signature in signatures:
            signatures_by_event.setdefault(signature["event_type"], []).append(signature)
        filler_kinds = {record.kind for record, _ in atoms.values()} | {
            "literal", "application"
        }
        by_ref: dict[str, SourceAttributionControl] = {}
        by_parent_role: set[tuple[str, str]] = set()
        for control in records:
            if control.control_ref in by_ref or control.control_ref in atoms:
                raise AuthorityLinkError("duplicate source attribution control identity")
            parent_role = (control.parent_target_ref, control.content_role_ref)
            if parent_role in by_parent_role:
                raise AuthorityLinkError("duplicate source attribution parent/content role")
            frame = frames_by_ref.get(control.parent_frame_ref)
            if (
                frame is None
                or frame.target_kind != "event_type"
                or frame.target_ref != control.parent_target_ref
            ):
                raise AuthorityLinkError(
                    "source attribution parent must match one reviewed event frame"
                )
            target = atoms.get(control.parent_target_ref)
            if target is None or target[0].kind != "event_type" or target[0].reviewed is not True:
                raise AuthorityLinkError(
                    "source attribution parent target must be one reviewed event"
                )
            candidates = signatures_by_event.get(control.parent_target_ref, [])
            if len(candidates) != 1:
                raise AuthorityLinkError(
                    "source attribution requires one linked event signature"
                )
            roles = {
                role.role: role
                for role in _validated_source_roles(
                    candidates[0].get("roles"), filler_kinds
                )
            }
            content = roles.get(control.content_role_ref)
            source = roles.get(control.source_role_ref)
            if (
                content is None
                or content.proposition_valued is not True
                or "application" not in content.filler_kinds
            ):
                raise AuthorityLinkError(
                    "source attribution content role must be proposition-valued"
                )
            if (
                source is None
                or source.required is not True
                or source.proposition_valued is not False
                or not source.filler_kinds
                or not set(source.filler_kinds) <= {"entity", "participant"}
            ):
                raise AuthorityLinkError(
                    "source attribution source role must be a required entity or participant"
                )
            if not {
                control.content_role_ref, control.source_role_ref
            } <= set(frame.role_candidates):
                raise AuthorityLinkError(
                    "source attribution roles must belong to the reviewed parent frame"
                )
            by_ref[control.control_ref] = control
            by_parent_role.add(parent_role)
        return tuple(by_ref[ref] for ref in sorted(by_ref))

    @staticmethod
    def _validate_reported_role_inheritance_controls(
        records: list[ReportedRoleInheritanceControl],
        source_controls: tuple[SourceAttributionControl, ...],
        atoms: dict[str, tuple[AtomRecord, str]],
        signatures: list[dict[str, Any]],
    ) -> tuple[ReportedRoleInheritanceControl, ...]:
        """Link exact report-source to child-role inheritance authority."""
        source_by_ref = {control.control_ref: control for control in source_controls}
        signatures_by_event: dict[str, list[dict[str, Any]]] = {}
        for signature in signatures:
            signatures_by_event.setdefault(signature["event_type"], []).append(signature)
        filler_kinds = {record.kind for record, _ in atoms.values()} | {
            "literal", "application"
        }
        by_ref: dict[str, ReportedRoleInheritanceControl] = {}
        signatures_seen: set[tuple[str, str, str, str]] = set()
        for control in records:
            if (
                control.control_ref in by_ref
                or control.control_ref in atoms
                or control.control_ref in source_by_ref
            ):
                raise AuthorityLinkError(
                    "duplicate reported role inheritance control identity"
                )
            source = source_by_ref.get(control.source_attribution_control_ref)
            if source is None or source.placement != control.placement:
                raise AuthorityLinkError(
                    "reported role inheritance requires one linked source control"
                )
            target = atoms.get(control.child_target_ref)
            if (
                target is None
                or target[0].kind != "event_type"
                or target[0].reviewed is not True
            ):
                raise AuthorityLinkError(
                    "reported role inheritance child must be one reviewed event"
                )
            child_candidates = signatures_by_event.get(control.child_target_ref, [])
            parent_candidates = signatures_by_event.get(source.parent_target_ref, [])
            if len(child_candidates) != 1 or len(parent_candidates) != 1:
                raise AuthorityLinkError(
                    "reported role inheritance requires exact event signatures"
                )
            child_roles = {
                role.role: role
                for role in _validated_source_roles(
                    child_candidates[0].get("roles"), filler_kinds
                )
            }
            parent_roles = {
                role.role: role
                for role in _validated_source_roles(
                    parent_candidates[0].get("roles"), filler_kinds
                )
            }
            child_role = child_roles.get(control.child_role_ref)
            source_role = parent_roles.get(source.source_role_ref)
            if (
                child_role is None
                or child_role.required is not True
                or child_role.proposition_valued is not False
                or source_role is None
                or source_role.proposition_valued is not False
                or not set(source_role.filler_kinds) <= set(child_role.filler_kinds)
            ):
                raise AuthorityLinkError(
                    "reported role inheritance roles are absent or incompatible"
                )
            key = (
                source.parent_target_ref,
                source.content_role_ref,
                control.child_target_ref,
                control.child_role_ref,
            )
            if key in signatures_seen:
                raise AuthorityLinkError(
                    "duplicate reported role inheritance signature"
                )
            signatures_seen.add(key)
            by_ref[control.control_ref] = control
        return tuple(by_ref[ref] for ref in sorted(by_ref))

    @staticmethod
    def _validate_communicative_controls(
        records: list[CommunicativeControl],
        frames: tuple[ReviewedSemanticFrame, ...],
        source_controls: tuple[SourceAttributionControl, ...],
        inheritance_controls: tuple[ReportedRoleInheritanceControl, ...],
        atoms: dict[str, tuple[AtomRecord, str]],
        signatures: list[dict[str, Any]],
    ) -> tuple[CommunicativeControl, ...]:
        """Link read-only reciprocal policy once; no normal-cycle scans."""
        frames_by_ref = {frame.frame_ref: frame for frame in frames}
        used_refs = set(atoms) | set(frames_by_ref) | {
            control.control_ref for control in (*source_controls, *inheritance_controls)
        }
        signatures_by_event: dict[str, list[dict[str, Any]]] = {}
        for signature in signatures:
            signatures_by_event.setdefault(signature["event_type"], []).append(signature)
        filler_kinds = {record.kind for record, _ in atoms.values()} | {"literal", "application"}
        targets: set[str] = set()
        by_ref: dict[str, CommunicativeControl] = {}
        for control in records:
            if control.control_ref in used_refs or control.target_ref in targets:
                raise AuthorityLinkError("duplicate communicative control identity or target")
            frame = frames_by_ref.get(control.source_frame_ref)
            target = atoms.get(control.target_ref)
            capability = atoms.get(control.required_capability_ref)
            if (
                frame is None or frame.target_kind != "event_type"
                or frame.target_ref != control.target_ref
                or "predicate" not in frame.contribution_kinds
                or target is None or target[0].kind != "event_type"
                or target[0].reviewed is not True
            ):
                raise AuthorityLinkError("communicative target requires one reviewed predicate event frame")
            if capability is None or capability[0].kind != "capability" or capability[0].reviewed is not True:
                raise AuthorityLinkError("communicative control requires one reviewed capability")
            if control.required_capability_ref != "cap:respond":
                raise AuthorityLinkError("reciprocal_event requires cap:respond")
            if (control.actor_role_ref, control.addressee_role_ref) != ("role:actor", "role:addressee"):
                raise AuthorityLinkError("communicative control requires exact actor and addressee roles")
            candidates = signatures_by_event.get(control.target_ref, [])
            if len(candidates) != 1:
                raise AuthorityLinkError("communicative control requires one exact event signature")
            signature = candidates[0]
            if set(signature) - {
                "event_type", "roles", "valid_session_phases", "required_capabilities",
                "required_permissions", "adapter_ref", "effect_schema",
            }:
                raise AuthorityLinkError("communicative source signature has unknown fields")
            for name in ("effect_schema", "required_permissions"):
                value = signature.get(name, [])
                if type(value) is not list or value:
                    raise AuthorityLinkError("communicative source must have no effects or permissions")
            if signature.get("adapter_ref") is not None:
                raise AuthorityLinkError("communicative source must have no adapter")
            capabilities = signature.get("required_capabilities", [])
            if type(capabilities) is not list or capabilities not in ([], [control.required_capability_ref]):
                raise AuthorityLinkError("communicative source capabilities contradict policy")
            if "valid_session_phases" in signature:
                phases = signature["valid_session_phases"]
                if (
                    type(phases) is not list or not 1 <= len(phases) <= 3
                    or any(type(phase) is not str or phase not in {"opening", "active", "suspended"} for phase in phases)
                    or len(set(phases)) != len(phases)
                ):
                    raise AuthorityLinkError("communicative source has invalid session phases")
            roles = _validated_source_roles(signature.get("roles"), filler_kinds)
            if tuple(role.role for role in roles) != (control.actor_role_ref, control.addressee_role_ref):
                raise AuthorityLinkError("communicative source requires complete actor/addressee signature")
            for role in roles:
                if (
                    role.proposition_valued or "participant" not in role.filler_kinds
                    or not set(role.filler_kinds) <= {"participant", "entity"}
                ):
                    raise AuthorityLinkError("communicative source roles require entity or participant fillers")
            if roles[0].required is not True:
                raise AuthorityLinkError("communicative source actor must be required")
            used_refs.add(control.control_ref)
            targets.add(control.target_ref)
            by_ref[control.control_ref] = control
        return tuple(by_ref[ref] for ref in sorted(by_ref))

    @staticmethod
    def _validate_learning_contracts(
        records: list[tuple[DesignationLearningContract, str]],
        atoms: dict[str, tuple[AtomRecord, str]],
        signatures: list[dict[str, Any]],
        operator_roles: dict[str, list[str]],
        adapters: list[str],
    ) -> tuple[DesignationLearningContract, ...]:
        """Activation-only linking of every authority edge and lowering slot."""
        by_ref: dict[str, DesignationLearningContract] = {}
        sources: set[tuple[str, str]] = set()
        signatures_by_event: dict[str, list[dict[str, Any]]] = {}
        filler_kinds = {record.kind for record, _ in atoms.values()} | {"literal", "application"}
        for signature in signatures:
            signatures_by_event.setdefault(signature["event_type"], []).append(signature)
        atom_fields = {
            "contract_ref": "learning_contract", "goal_ref": "goal",
            "answer_contract_ref": "answer_contract", "review_policy_ref": "policy",
            "source_event_ref": "event_type", "capability_ref": "capability",
            "permission_ref": "permission", "designation_label_ref": "label_type",
            "internal_adapter_ref": "adapter",
        }
        for contract, owner in records:
            if contract.contract_ref in by_ref:
                raise AuthorityLinkError("duplicate learning contract ref")
            source = (contract.source_operator_ref, contract.source_event_ref)
            if source in sources:
                raise AuthorityLinkError("duplicate learning contract source mapping")
            for field_name, kind in atom_fields.items():
                ref = getattr(contract, field_name)
                atom_owner = atoms.get(ref)
                if atom_owner is None or atom_owner[0].kind != kind or atom_owner[0].reviewed is not True:
                    raise AuthorityLinkError(f"invalid learning contract {field_name}: {ref}")
            if atoms[contract.contract_ref][1] != owner:
                raise AuthorityLinkError("learning contract record differs from its atom owner")
            if (
                contract.source_operator_ref != "op:event"
                or operator_roles.get(contract.source_operator_ref) != ["role:event", "role:type"]
                or contract.commit_operator_ref != "op:designation"
                or operator_roles.get(contract.commit_operator_ref) != ["role:target", "role:label_type", "role:surface"]
                or contract.designation_label_ref != "label:lexical"
            ):
                raise AuthorityLinkError("invalid learning contract operator-role lowering")
            if contract.internal_adapter_ref != "adapter:memory" or contract.internal_adapter_ref not in adapters:
                raise AuthorityLinkError("learning contract requires reviewed internal memory adapter authorization")
            candidates = signatures_by_event.get(contract.source_event_ref, [])
            if len(candidates) != 1:
                raise AuthorityLinkError("learning contract requires one exact source event signature")
            signature = candidates[0]
            if set(signature) - {
                "event_type", "roles", "valid_session_phases", "required_capabilities",
                "required_permissions", "adapter_ref", "effect_schema",
            }:
                raise AuthorityLinkError("learning contract source signature has unknown fields")
            # This contract lowers exactly one designation. Additional event
            # effects must not be silently discarded by that internal lowering.
            effects = signature.get("effect_schema", [])
            if type(effects) is not list or effects:
                raise AuthorityLinkError("learning contract source must have no additional effects")
            if "valid_session_phases" in signature:
                phases = signature["valid_session_phases"]
                # Established active conversation signatures use these phases;
                # absence retains EventSignature's opening/active default.
                supported_phases = {"opening", "active", "suspended"}
                if (
                    type(phases) is not list or not 1 <= len(phases) <= len(supported_phases)
                    or any(type(phase) is not str or phase not in supported_phases for phase in phases)
                    or len(set(phases)) != len(phases)
                ):
                    raise AuthorityLinkError("learning contract source has invalid session phases")
            if (
                signature.get("required_capabilities") != [contract.capability_ref]
                or signature.get("required_permissions") != [contract.permission_ref]
                or signature.get("adapter_ref") != contract.internal_adapter_ref
            ):
                raise AuthorityLinkError("learning contract source requirements do not match")
            if (
                contract.actor_role_ref != "role:actor"
                or contract.surface_role_ref != "role:surface"
                or contract.target_role_ref != "role:target"
            ):
                raise AuthorityLinkError("learning contract source roles do not match lowering")
            expected = {
                contract.actor_role_ref: ("participant",),
                contract.surface_role_ref: ("literal",),
                contract.target_role_ref: contract.allowed_target_kinds,
            }
            roles = _validated_source_roles(signature.get("roles"), filler_kinds)
            if len(roles) != len(expected):
                raise AuthorityLinkError("learning contract source role count does not match")
            for role in roles:
                ref = role.role
                if ref not in expected:
                    raise AuthorityLinkError("learning contract source role is invalid")
                if (
                    role.required is not True or role.proposition_valued is not False
                    or role.filler_kinds != expected[ref]
                ):
                    raise AuthorityLinkError("learning contract source role requirements do not match")
            sources.add(source)
            by_ref[contract.contract_ref] = contract
        return tuple(by_ref[ref] for ref in sorted(by_ref))
