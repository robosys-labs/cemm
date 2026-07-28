"""Language-neutral semantic contribution and affordance ABI.

A designation identifies a possible semantic target.  This module derives the
bounded ways that target may participate in atomic graph composition.  It does
not parse text, choose an interpretation, create semantic identity, or write
world state.

The ABI is deliberately small.  Open vocabulary grows through designations and
semantic targets; it does not require one form-pack entry or one construction
family per learned word.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any, Iterable, Mapping

SEMANTIC_CONTRIBUTION_ABI = 1
MAX_PORTS_PER_PROFILE = 16
MAX_ROLES_PER_PROFILE = 12
_PORT = re.compile(r"^[a-z][a-z0-9_.-]*:[a-zA-Z0-9_.-]+$")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def stable(namespace: str, *parts: Any) -> str:
    digest = hashlib.sha256(canonical((namespace, parts)).encode("utf-8")).hexdigest()[:24]
    return f"{namespace}:{digest}"


def _bounded_refs(values: Iterable[Any], *, label: str, limit: int = MAX_PORTS_PER_PROFILE) -> tuple[str, ...]:
    refs = tuple(sorted({str(item) for item in values if str(item)}))
    if len(refs) > limit:
        raise ValueError(f"{label} exceeds bound {limit}")
    if any(not _PORT.fullmatch(item) for item in refs):
        raise ValueError(f"{label} contains malformed semantic port/ref: {refs}")
    return refs


class ContributionKind:
    ANCHOR = "anchor"
    PREDICATE = "predicate"
    BINDER = "binder"
    REFERENCE = "reference"
    SCOPE = "scope"
    DISCOURSE = "discourse"
    CONNECTOR = "connector"
    QUALIFIER = "qualifier"
    LITERAL = "literal"
    OPEN_VARIABLE = "open_variable"

    ALL = frozenset({
        ANCHOR, PREDICATE, BINDER, REFERENCE, SCOPE,
        DISCOURSE, CONNECTOR, QUALIFIER, LITERAL, OPEN_VARIABLE,
    })


@dataclass(frozen=True)
class FrameRoleSpec:
    role_ref: str
    required: bool = True
    filler_kinds: tuple[str, ...] = ()
    ports_required: tuple[str, ...] = ()
    cardinality: str = "one"

    def __post_init__(self) -> None:
        if not _PORT.fullmatch(self.role_ref):
            raise ValueError(f"semantic frame role is malformed: {self.role_ref!r}")
        if self.cardinality not in {"one", "many"}:
            raise ValueError(f"unsupported semantic frame cardinality: {self.cardinality}")
        if len(self.filler_kinds) > 8:
            raise ValueError("semantic frame filler-kind set exceeds bound")
        if any(not item for item in self.filler_kinds):
            raise ValueError("semantic frame filler kinds must be non-empty")
        _bounded_refs(self.ports_required, label=f"role {self.role_ref} required ports")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FrameRoleSpec":
        return cls(
            role_ref=str(value.get("role_ref") or ""),
            required=bool(value.get("required", True)),
            filler_kinds=tuple(sorted({str(item) for item in value.get("filler_kinds", ()) if str(item)})),
            ports_required=_bounded_refs(value.get("ports_required", ()), label="role ports_required"),
            cardinality=str(value.get("cardinality", "one")),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "role_ref": self.role_ref,
            "required": self.required,
            "filler_kinds": list(self.filler_kinds),
            "ports_required": list(self.ports_required),
            "cardinality": self.cardinality,
        }


@dataclass(frozen=True)
class AffordanceProfile:
    profile_ref: str
    contribution_kind: str
    semantic_ref: str
    semantic_kind: str
    ports_provided: tuple[str, ...] = ()
    ports_required: tuple[str, ...] = ()
    roles: tuple[FrameRoleSpec, ...] = ()
    score: float = 0.0
    source_ref: str = "derived:semantic-kind"
    predicate: bool = False
    replace_defaults: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.contribution_kind not in ContributionKind.ALL:
            raise ValueError(f"unsupported contribution kind: {self.contribution_kind}")
        for name, value in (
            ("profile_ref", self.profile_ref),
            ("semantic_ref", self.semantic_ref),
            ("semantic_kind", self.semantic_kind),
        ):
            if not value:
                raise ValueError(f"affordance profile requires {name}")
        if not -4.0 <= float(self.score) <= 4.0:
            raise ValueError("affordance score is outside bounded range")
        _bounded_refs(self.ports_provided, label=f"{self.profile_ref} ports_provided")
        _bounded_refs(self.ports_required, label=f"{self.profile_ref} ports_required")
        if len(self.roles) > MAX_ROLES_PER_PROFILE:
            raise ValueError("semantic frame role count exceeds bound")
        refs = tuple(item.role_ref for item in self.roles)
        if len(refs) != len(set(refs)):
            raise ValueError(f"duplicate frame role in {self.profile_ref}")
        if self.predicate and self.contribution_kind != ContributionKind.PREDICATE:
            raise ValueError("only predicate contributions may carry predicate=true")

    @classmethod
    def from_frame_atom(
        cls,
        *,
        target_ref: str,
        target_kind: str,
        frame_ref: str,
        metadata: Mapping[str, Any],
    ) -> "AffordanceProfile":
        payload = dict(metadata.get("semantic_frame", metadata))
        contribution_kind = str(payload.get("contribution_kind") or "")
        return cls(
            profile_ref=str(frame_ref),
            contribution_kind=contribution_kind,
            semantic_ref=str(target_ref),
            semantic_kind=str(target_kind),
            ports_provided=_bounded_refs(payload.get("ports_provided", ()), label=f"{frame_ref} ports_provided"),
            ports_required=_bounded_refs(payload.get("ports_required", ()), label=f"{frame_ref} ports_required"),
            roles=tuple(FrameRoleSpec.from_dict(item) for item in payload.get("roles", ())),
            score=float(payload.get("score", 0.0)),
            source_ref=str(frame_ref),
            predicate=bool(payload.get("predicate", contribution_kind == ContributionKind.PREDICATE)),
            replace_defaults=bool(payload.get("replace_defaults", False)),
            metadata={
                key: value
                for key, value in payload.items()
                if key not in {
                    "contribution_kind", "ports_provided", "ports_required",
                    "roles", "score", "predicate", "replace_defaults",
                }
            },
        )

    def as_features(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "semantic_contribution_abi": SEMANTIC_CONTRIBUTION_ABI,
            "contribution_kind": self.contribution_kind,
            "semantic_ref": self.semantic_ref,
            "semantic_kind": self.semantic_kind,
            "affordance_ref": self.profile_ref,
            "ports_provided": list(self.ports_provided),
            "ports_required": list(self.ports_required),
            "semantic_roles": [item.as_dict() for item in self.roles],
        }
        if self.predicate:
            result["predicate"] = True
        result.update(dict(self.metadata))
        return result

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile_ref": self.profile_ref,
            "contribution_kind": self.contribution_kind,
            "semantic_ref": self.semantic_ref,
            "semantic_kind": self.semantic_kind,
            "ports_provided": list(self.ports_provided),
            "ports_required": list(self.ports_required),
            "roles": [item.as_dict() for item in self.roles],
            "score": self.score,
            "source_ref": self.source_ref,
            "predicate": self.predicate,
            "replace_defaults": self.replace_defaults,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SemanticContribution:
    contribution_ref: str
    unit_ref: str
    surface: str
    semantic_ref: str
    semantic_kind: str
    contribution_kind: str
    affordance_ref: str
    ports_provided: tuple[str, ...]
    ports_required: tuple[str, ...]
    roles: tuple[FrameRoleSpec, ...]
    score: float
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "contribution_ref": self.contribution_ref,
            "unit_ref": self.unit_ref,
            "surface": self.surface,
            "semantic_ref": self.semantic_ref,
            "semantic_kind": self.semantic_kind,
            "contribution_kind": self.contribution_kind,
            "affordance_ref": self.affordance_ref,
            "ports_provided": list(self.ports_provided),
            "ports_required": list(self.ports_required),
            "roles": [item.as_dict() for item in self.roles],
            "score": self.score,
            "provenance": dict(self.provenance),
        }


_ENTITY_KINDS = frozenset({
    "entity", "participant", "resource", "source", "existential",
    "event", "time", "place", "quantity",
})


class SemanticAffordanceIndex:
    """Generation-pinned semantic target → bounded contribution profiles."""

    FRAME_RELATION_REF = "rel:has_semantic_frame"

    def __init__(
        self,
        store: Any,
        authority_generation: int | None = None,
        *,
        max_profiles_per_target: int = 4,
    ) -> None:
        if not 1 <= int(max_profiles_per_target) <= 8:
            raise ValueError("semantic affordance profile bound must be in 1..8")
        self.store = store
        self.authority_generation = authority_generation
        self.max_profiles_per_target = int(max_profiles_per_target)
        self._cache: dict[str, tuple[AffordanceProfile, ...]] = {}
        revisions = getattr(store, "revisions", lambda: {"world_revision": 0})()
        self.snapshot_ref = stable(
            "semantic-affordance-index",
            SEMANTIC_CONTRIBUTION_ABI,
            authority_generation,
            int(revisions.get("world_revision", 0)),
            self.max_profiles_per_target,
        )

    @staticmethod
    def _kind(atom: Any) -> str:
        try:
            return str(atom["kind"])
        except (KeyError, TypeError):
            return str(getattr(atom, "kind", ""))

    @staticmethod
    def _metadata(atom: Any) -> Mapping[str, Any]:
        try:
            raw = atom["metadata"]
        except (KeyError, TypeError):
            raw = getattr(atom, "metadata", {})
        if isinstance(raw, str):
            raw = json.loads(raw)
        return dict(raw or {})

    def _profile(
        self,
        semantic_ref: str,
        semantic_kind: str,
        suffix: str,
        contribution_kind: str,
        *,
        ports_provided: Iterable[str] = (),
        ports_required: Iterable[str] = (),
        roles: Iterable[FrameRoleSpec] = (),
        score: float = 0.0,
        predicate: bool = False,
        metadata: Mapping[str, Any] | None = None,
    ) -> AffordanceProfile:
        return AffordanceProfile(
            profile_ref=f"derived-affordance:{semantic_kind}:{suffix}",
            contribution_kind=contribution_kind,
            semantic_ref=semantic_ref,
            semantic_kind=semantic_kind,
            ports_provided=_bounded_refs(ports_provided, label="derived ports_provided"),
            ports_required=_bounded_refs(ports_required, label="derived ports_required"),
            roles=tuple(roles),
            score=float(score),
            source_ref="derived:semantic-kind",
            predicate=predicate,
            metadata=dict(metadata or {}),
        )

    def _explicit_profiles(self, target_ref: str, target_kind: str) -> tuple[AffordanceProfile, ...]:
        relation_atom = self.store.atom(self.FRAME_RELATION_REF)
        if relation_atom is None:
            return ()
        frame_refs = tuple(sorted(set(self.store.relation_objects(
            target_ref,
            self.FRAME_RELATION_REF,
            authority_only=True,
            upto_generation=self.authority_generation,
        ))))
        if len(frame_refs) > self.max_profiles_per_target:
            raise ValueError(f"semantic target has too many explicit frames: {target_ref}")
        output: list[AffordanceProfile] = []
        for frame_ref in frame_refs:
            atom = (
                self.store.authority_atom(frame_ref, upto_generation=self.authority_generation)
                if hasattr(self.store, "authority_atom")
                else self.store.atom(frame_ref)
            )
            if atom is None:
                raise ValueError(f"semantic frame is missing or outside pinned authority: {frame_ref}")
            if self._kind(atom) != "semantic_frame":
                raise ValueError(f"semantic frame ref is not semantic_frame: {frame_ref}")
            profile = AffordanceProfile.from_frame_atom(
                target_ref=target_ref,
                target_kind=target_kind,
                frame_ref=frame_ref,
                metadata=self._metadata(atom),
            )
            self._validate_profile_authority(profile)
            output.append(profile)
        return tuple(output)

    def _validate_profile_authority(self, profile: AffordanceProfile) -> None:
        operator = profile.metadata.get("kernel_operator_ref")
        if operator:
            atom = self.store.atom(str(operator))
            if atom is None or self._kind(atom) != "operator":
                raise ValueError(f"affordance references missing/non-operator: {operator}")
        for role in profile.roles:
            atom = self.store.atom(role.role_ref)
            if atom is None or self._kind(atom) != "role":
                raise ValueError(f"affordance references missing/non-role: {role.role_ref}")
            if operator and role.role_ref not in self.store.roles(str(operator)):
                raise ValueError(
                    f"affordance role {role.role_ref} is not permitted by {operator}"
                )

    def _dimensions_for_value(self, value_ref: str) -> tuple[str, ...]:
        method = getattr(self.store, "dimensions_for_value", None)
        if not callable(method):
            return ()
        return tuple(sorted(set(method(
            value_ref,
            authority_only=True,
            upto_generation=self.authority_generation,
        ))))

    def _default_profiles(self, semantic_ref: str, kind: str) -> tuple[AffordanceProfile, ...]:
        if kind in _ENTITY_KINDS:
            return (self._profile(
                semantic_ref, kind, "argument", ContributionKind.ANCHOR,
                ports_provided=("argument:atom", f"argument:{kind}"),
                score=0.02,
            ),)
        if kind == "concept":
            return (
                self._profile(
                    semantic_ref, kind, "class-predicate", ContributionKind.PREDICATE,
                    ports_provided=("predicate:type",),
                    ports_required=("argument:subject",),
                    roles=(FrameRoleSpec("role:instance", True, ("atom",)),),
                    predicate=True,
                    metadata={"kernel_operator_ref": "op:type"},
                ),
                self._profile(
                    semantic_ref, kind, "concept-anchor", ContributionKind.ANCHOR,
                    ports_provided=("argument:concept",), score=-0.04,
                ),
            )
        if kind == "event_type":
            return (
                self._profile(
                    semantic_ref, kind, "event-predicate", ContributionKind.PREDICATE,
                    ports_provided=("predicate:event",),
                    predicate=True, score=0.08,
                    metadata={"kernel_operator_ref": "op:event"},
                ),
                self._profile(
                    semantic_ref, kind, "event-type-anchor", ContributionKind.ANCHOR,
                    ports_provided=("argument:event_type",), score=-0.08,
                ),
            )
        if kind == "relation_type":
            return (
                self._profile(
                    semantic_ref, kind, "relation-predicate", ContributionKind.PREDICATE,
                    ports_provided=("predicate:relation",),
                    ports_required=("argument:subject", "argument:object"),
                    roles=(
                        FrameRoleSpec("role:subject", True, ("atom",)),
                        FrameRoleSpec("role:object", True, ("atom",)),
                    ),
                    predicate=True, score=0.08,
                    metadata={"kernel_operator_ref": "op:relation"},
                ),
                self._profile(
                    semantic_ref, kind, "relation-anchor", ContributionKind.ANCHOR,
                    ports_provided=("argument:relation_type",), score=-0.08,
                ),
            )
        if kind == "state_dimension":
            return (
                self._profile(
                    semantic_ref, kind, "dimension-predicate", ContributionKind.PREDICATE,
                    ports_provided=("predicate:state_dimension",),
                    ports_required=("argument:subject", "argument:value"),
                    roles=(
                        FrameRoleSpec("role:subject", True, ("atom",)),
                        FrameRoleSpec("role:value", True, ("state_value",)),
                    ),
                    predicate=True, score=0.08,
                    metadata={"kernel_operator_ref": "op:state", "state_dimension_ref": semantic_ref},
                ),
                self._profile(
                    semantic_ref, kind, "dimension-anchor", ContributionKind.ANCHOR,
                    ports_provided=("argument:state_dimension",), score=-0.08,
                ),
            )
        if kind == "value":
            dimensions = self._dimensions_for_value(semantic_ref)
            profiles = [self._profile(
                semantic_ref, kind, "value-anchor", ContributionKind.ANCHOR,
                ports_provided=("argument:value",), score=0.0,
                metadata={"candidate_dimension_refs": list(dimensions)},
            )]
            # A bare value is a safe predicative contribution only when exact
            # authority gives one dimension.  Zero/multiple dimensions remain
            # anchors until another graph slot resolves the dimension.
            if len(dimensions) == 1:
                profiles.insert(0, self._profile(
                    semantic_ref, kind, "state-value-predicate", ContributionKind.PREDICATE,
                    ports_provided=("predicate:state_value", "argument:value"),
                    ports_required=("argument:subject",),
                    predicate=True, score=0.05,
                    metadata={
                        "kernel_operator_ref": "op:state",
                        "state_dimension_ref": dimensions[0],
                    },
                ))
            return tuple(profiles)
        if kind == "label_type":
            return (
                self._profile(
                    semantic_ref, kind, "designation-property", ContributionKind.PREDICATE,
                    ports_provided=("predicate:designation",),
                    ports_required=("argument:subject",),
                    roles=(FrameRoleSpec("role:target", True, ("atom",)),),
                    predicate=True, score=0.08,
                    metadata={
                        "kernel_operator_ref": "op:designation",
                        "property_kind": "designation",
                        "property_ref": semantic_ref,
                    },
                ),
                self._profile(
                    semantic_ref, kind, "label-anchor", ContributionKind.ANCHOR,
                    ports_provided=("argument:label_type",), score=-0.08,
                ),
            )
        if kind == "capability":
            return (
                self._profile(
                    semantic_ref, kind, "capability-target", ContributionKind.PREDICATE,
                    ports_provided=("predicate:capability", "argument:capability"),
                    ports_required=("argument:subject",),
                    predicate=True, score=0.04,
                    metadata={"capability_ref": semantic_ref},
                ),
                self._profile(
                    semantic_ref, kind, "capability-anchor", ContributionKind.ANCHOR,
                    ports_provided=("argument:capability",), score=0.0,
                ),
            )
        return (self._profile(
            semantic_ref, kind, "opaque-anchor", ContributionKind.ANCHOR,
            ports_provided=("argument:semantic_atom",), score=-0.2,
        ),)

    def profiles_for(self, semantic_ref: str) -> tuple[AffordanceProfile, ...]:
        ref = str(semantic_ref)
        cached = self._cache.get(ref)
        if cached is not None:
            return cached
        # Semantic targets may be reviewed authority atoms or learned/world atoms.
        # Only explicit frame contracts require authority scope; safe default
        # affordances are derived from the target's already-validated semantic kind.
        atom = self.store.atom(ref)
        if atom is None:
            raise ValueError(f"semantic affordance target is missing: {ref}")
        kind = self._kind(atom)
        explicit = self._explicit_profiles(ref, kind)
        defaults = self._default_profiles(ref, kind)
        candidates = explicit if any(item.replace_defaults for item in explicit) else explicit + defaults
        unique: dict[str, AffordanceProfile] = {}
        for profile in candidates:
            unique.setdefault(canonical(profile.as_dict()), profile)
        ordered = tuple(sorted(
            unique.values(),
            key=lambda item: (-float(item.score), item.profile_ref, item.contribution_kind),
        )[: self.max_profiles_per_target])
        if not ordered:
            raise ValueError(f"semantic target has no bounded affordance: {ref}")
        self._cache[ref] = ordered
        return ordered

    def feature_alternatives_for_target(
        self,
        semantic_ref: str,
        *,
        base_features: Mapping[str, Any] | None = None,
        label_type: str | None = None,
    ) -> tuple[dict[str, Any], ...]:
        base = dict(base_features or {})
        if label_type:
            base.setdefault("label_type", str(label_type))
        rows = ({**base, **profile.as_features()} for profile in self.profiles_for(semantic_ref))
        unique = {canonical(row): row for row in rows}
        return tuple(unique[key] for key in sorted(unique))

    def contributions_for(
        self,
        *,
        unit_ref: str,
        surface: str,
        semantic_ref: str,
        base_score: float = 0.0,
        provenance: Mapping[str, Any] | None = None,
    ) -> tuple[SemanticContribution, ...]:
        return tuple(
            SemanticContribution(
                contribution_ref=stable(
                    "semantic-contribution", unit_ref, surface, semantic_ref, profile.profile_ref,
                ),
                unit_ref=str(unit_ref),
                surface=str(surface),
                semantic_ref=str(semantic_ref),
                semantic_kind=profile.semantic_kind,
                contribution_kind=profile.contribution_kind,
                affordance_ref=profile.profile_ref,
                ports_provided=profile.ports_provided,
                ports_required=profile.ports_required,
                roles=profile.roles,
                score=float(base_score) + float(profile.score),
                provenance={**dict(provenance or {}), "affordance_source_ref": profile.source_ref},
            )
            for profile in self.profiles_for(semantic_ref)
        )

    def validate_targets(self, semantic_refs: Iterable[str]) -> dict[str, Any]:
        rows = {
            str(ref): [item.as_dict() for item in self.profiles_for(str(ref))]
            for ref in sorted(set(map(str, semantic_refs)))
        }
        return {
            "semantic_contribution_abi": SEMANTIC_CONTRIBUTION_ABI,
            "snapshot_ref": self.snapshot_ref,
            "target_count": len(rows),
            "profiles": rows,
        }
