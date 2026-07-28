"""Transient proposition graphs over CEMM's five fixed semantic operators.

A proposition is a bounded, cycle-local graph.  It is not a sixth operator, a
persistent atom kind, or a second semantic store.  Application-valued arguments
refer to roots of applications in the same flattened candidate using
``{"app": application_ref}``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

PROPOSITION_GRAPH_ABI = 2
ATOMIC_COMPOSITION_ABI = 1
FIXED_OPERATORS = frozenset({
    "op:designation", "op:type", "op:relation", "op:state", "op:event",
})
MAX_PROPOSITION_APPLICATIONS = 24
MAX_PROPOSITION_DEPTH = 6
MAX_PROPOSITION_PORTS = 16
_VALID_FORCES = frozenset({
    "claim", "query", "directive", "description", "correction",
    "retraction", "acknowledgment",
})


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def stable(namespace: str, *parts: Any) -> str:
    payload = canonical((namespace, parts)).encode("utf-8")
    return f"{namespace}:{hashlib.sha256(payload).hexdigest()[:24]}"


def _walk_values(value: Any):
    if isinstance(value, Mapping):
        for child in value.values():
            yield from _walk_values(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _walk_values(child)
    else:
        yield value


def _app_ref(value: Any) -> str | None:
    if isinstance(value, Mapping) and set(value) == {"app"}:
        ref = value.get("app")
        return str(ref) if isinstance(ref, str) and ref else None
    return None


def _variables(value: Any) -> set[str]:
    return {
        str(item) for item in _walk_values(value)
        if isinstance(item, str) and item.startswith("?")
    }


@dataclass(frozen=True)
class PropositionCoverage:
    """Recursive provenance back to the original observed form units."""

    source_hypothesis_ref: str
    direct_unit_refs: tuple[str, ...] = ()
    expanded_unit_refs: tuple[str, ...] = ()
    child_proposition_refs: tuple[str, ...] = ()
    role_by_source_unit_ref: Mapping[str, str] = field(default_factory=dict)
    projected_slots: Mapping[str, Any] = field(default_factory=dict)
    residual_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_hypothesis_ref:
            raise ValueError("proposition coverage requires hypothesis provenance")
        for label, values in (
            ("direct", self.direct_unit_refs),
            ("expanded", self.expanded_unit_refs),
            ("children", self.child_proposition_refs),
            ("residuals", self.residual_refs),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate proposition {label} coverage")
        if set(self.direct_unit_refs) - set(self.expanded_unit_refs):
            raise ValueError("direct proposition coverage is not included in expanded coverage")
        if set(self.role_by_source_unit_ref) - set(self.expanded_unit_refs):
            raise ValueError("proposition role map refers to uncovered source units")

    @classmethod
    def create(
        cls,
        source_hypothesis_ref: str,
        *,
        direct_unit_refs: Iterable[str] = (),
        child_coverages: Iterable["PropositionCoverage"] = (),
        child_proposition_refs: Iterable[str] = (),
        role_by_source_unit_ref: Mapping[str, str] | None = None,
        projected_slots: Mapping[str, Any] | None = None,
        residual_refs: Iterable[str] = (),
    ) -> "PropositionCoverage":
        direct = tuple(dict.fromkeys(map(str, direct_unit_refs)))
        children = tuple(child_coverages)
        expanded = list(direct)
        seen = set(direct)
        for child in children:
            overlap = seen.intersection(child.expanded_unit_refs)
            if overlap:
                raise ValueError(
                    "sibling/direct proposition coverage overlaps: " + ",".join(sorted(overlap))
                )
            expanded.extend(child.expanded_unit_refs)
            seen.update(child.expanded_unit_refs)
        return cls(
            str(source_hypothesis_ref),
            direct,
            tuple(expanded),
            tuple(dict.fromkeys(map(str, child_proposition_refs))),
            dict(role_by_source_unit_ref or {}),
            dict(projected_slots or {}),
            tuple(dict.fromkeys(map(str, residual_refs))),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_hypothesis_ref": self.source_hypothesis_ref,
            "direct_unit_refs": list(self.direct_unit_refs),
            "expanded_unit_refs": list(self.expanded_unit_refs),
            "child_proposition_refs": list(self.child_proposition_refs),
            "role_by_source_unit_ref": dict(self.role_by_source_unit_ref),
            "projected_slots": dict(self.projected_slots),
            "residual_refs": list(self.residual_refs),
        }


@dataclass(frozen=True)
class PropositionApplication:
    application_ref: str
    operator_ref: str
    args: Mapping[str, Any]
    stance: str = "support"
    qualifiers: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.operator_ref not in FIXED_OPERATORS:
            raise ValueError(f"proposition uses non-kernel operator: {self.operator_ref}")
        if not self.application_ref or not self.args:
            raise ValueError("proposition application requires ref and role bindings")
        if any(not str(role).startswith("role:") for role in self.args):
            raise ValueError("proposition application contains malformed role")
        if self.stance not in {"support", "deny"}:
            raise ValueError("unsupported proposition stance")

    @classmethod
    def create(
        cls,
        operator_ref: str,
        args: Mapping[str, Any],
        *,
        stance: str = "support",
        qualifiers: Mapping[str, Any] | None = None,
        application_ref: str | None = None,
    ) -> "PropositionApplication":
        material = (operator_ref, dict(args), stance, dict(qualifiers or {}))
        return cls(
            str(application_ref or stable("proposition-application-v2", material)),
            str(operator_ref),
            dict(args),
            str(stance),
            dict(qualifiers or {}),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PropositionApplication":
        return cls.create(
            str(value["operator"]),
            dict(value.get("args", {})),
            stance=str(value.get("stance", "support")),
            qualifiers=dict(value.get("qualifiers", {})),
            application_ref=value.get("application_ref"),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "application_ref": self.application_ref,
            "operator": self.operator_ref,
            "args": dict(self.args),
            "stance": self.stance,
            "qualifiers": dict(self.qualifiers),
        }

    def packet_application(self) -> dict[str, Any]:
        return {
            "application_ref": self.application_ref,
            "operator": self.operator_ref,
            "args": dict(self.args),
            "stance": self.stance,
        }


@dataclass(frozen=True)
class PropositionGraph:
    proposition_ref: str
    semantic_signature: str
    applications: tuple[PropositionApplication, ...]
    root_application_ref: str
    force: str = "claim"
    modality: str = "actual"
    polarity: str = "positive"
    projected_variables: tuple[str, ...] = ()
    ports_provided: tuple[str, ...] = ()
    ports_required: tuple[str, ...] = ()
    depth: int = 1
    coverage: PropositionCoverage | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 1 <= len(self.applications) <= MAX_PROPOSITION_APPLICATIONS:
            raise ValueError("proposition application count exceeds bound")
        if not 1 <= int(self.depth) <= MAX_PROPOSITION_DEPTH:
            raise ValueError("proposition depth exceeds bound")
        refs = tuple(item.application_ref for item in self.applications)
        if len(refs) != len(set(refs)):
            raise ValueError("proposition graph contains duplicate application refs")
        if self.root_application_ref not in refs:
            raise ValueError("proposition root is not in graph")
        if self.force not in _VALID_FORCES:
            raise ValueError(f"unsupported proposition force: {self.force}")
        for label, ports in (("provided", self.ports_provided), ("required", self.ports_required)):
            if len(ports) > MAX_PROPOSITION_PORTS or len(ports) != len(set(ports)):
                raise ValueError(f"proposition {label} ports violate bounds")
            if any(":" not in port for port in ports):
                raise ValueError(f"malformed proposition {label} port")
        declared = set(self.projected_variables)
        if any(not item.startswith("?") for item in declared):
            raise ValueError("proposition projections must be semantic variables")
        present = set().union(*(_variables(app.args) for app in self.applications))
        if declared - present:
            raise ValueError("proposition projects a variable absent from its graph")
        app_refs = set(refs)
        for app in self.applications:
            for value in app.args.values():
                child = _app_ref(value)
                if child and child not in app_refs:
                    raise ValueError(f"proposition refers to absent child application: {child}")
        self._assert_acyclic_application_links()
        expected = self._signature(
            self.applications, self.root_application_ref, self.force, self.modality,
            self.polarity, self.projected_variables,
        )
        if self.semantic_signature != expected:
            raise ValueError("proposition semantic signature mismatch")

    @staticmethod
    def _signature(applications, root, force, modality, polarity, projected_variables) -> str:
        material = {
            "applications": [item.packet_application() for item in applications],
            "root": root,
            "force": force,
            "modality": modality,
            "polarity": polarity,
            "projected_variables": sorted(set(projected_variables)),
        }
        return hashlib.sha256(canonical(material).encode("utf-8")).hexdigest()

    def _assert_acyclic_application_links(self) -> None:
        edges = {
            app.application_ref: {
                child for child in (_app_ref(value) for value in app.args.values()) if child
            }
            for app in self.applications
        }
        visiting: set[str] = set()
        visited: set[str] = set()

        def walk(ref: str) -> None:
            if ref in visiting:
                raise ValueError("proposition application-link cycle")
            if ref in visited:
                return
            visiting.add(ref)
            for child in edges.get(ref, ()):
                walk(child)
            visiting.remove(ref)
            visited.add(ref)

        for ref in edges:
            walk(ref)

    @classmethod
    def create(
        cls,
        applications: Iterable[PropositionApplication],
        *,
        root_application_ref: str,
        force: str = "claim",
        modality: str = "actual",
        polarity: str = "positive",
        projected_variables: Iterable[str] = (),
        ports_provided: Iterable[str] = (),
        ports_required: Iterable[str] = (),
        depth: int = 1,
        coverage: PropositionCoverage | None = None,
        provenance: Mapping[str, Any] | None = None,
    ) -> "PropositionGraph":
        apps = tuple(applications)
        projection = tuple(sorted(set(map(str, projected_variables))))
        signature = cls._signature(apps, root_application_ref, force, modality, polarity, projection)
        material = {
            "abi": PROPOSITION_GRAPH_ABI,
            "signature": signature,
            "depth": int(depth),
            "coverage": coverage.as_dict() if coverage else None,
        }
        return cls(
            stable("proposition-graph-v2", material),
            signature,
            apps,
            str(root_application_ref),
            str(force),
            str(modality),
            str(polarity),
            projection,
            tuple(sorted(set(map(str, ports_provided)))),
            tuple(sorted(set(map(str, ports_required)))),
            int(depth),
            coverage,
            dict(provenance or {}),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PropositionGraph":
        if int(value.get("proposition_graph_abi", -1)) != PROPOSITION_GRAPH_ABI:
            raise ValueError("unsupported proposition graph ABI")
        coverage_raw = value.get("coverage")
        coverage = None
        if isinstance(coverage_raw, Mapping):
            coverage = PropositionCoverage(
                source_hypothesis_ref=str(coverage_raw["source_hypothesis_ref"]),
                direct_unit_refs=tuple(map(str, coverage_raw.get("direct_unit_refs", ()))),
                expanded_unit_refs=tuple(map(str, coverage_raw.get("expanded_unit_refs", ()))),
                child_proposition_refs=tuple(map(str, coverage_raw.get("child_proposition_refs", ()))),
                role_by_source_unit_ref={str(k): str(v) for k, v in dict(coverage_raw.get("role_by_source_unit_ref", {})).items()},
                projected_slots=dict(coverage_raw.get("projected_slots", {})),
                residual_refs=tuple(map(str, coverage_raw.get("residual_refs", ()))),
            )
        graph = cls(
            proposition_ref=str(value["proposition_ref"]),
            semantic_signature=str(value["semantic_signature"]),
            applications=tuple(PropositionApplication.from_dict(item) for item in value.get("applications", ())),
            root_application_ref=str(value["root_application_ref"]),
            force=str(value.get("force", "claim")),
            modality=str(value.get("modality", "actual")),
            polarity=str(value.get("polarity", "positive")),
            projected_variables=tuple(map(str, value.get("projected_variables", ()))),
            ports_provided=tuple(map(str, value.get("ports_provided", ()))),
            ports_required=tuple(map(str, value.get("ports_required", ()))),
            depth=int(value.get("depth", 1)),
            coverage=coverage,
            provenance=dict(value.get("provenance", {})),
        )
        expected_ref = stable(
            "proposition-graph-v2",
            {
                "abi": PROPOSITION_GRAPH_ABI,
                "signature": graph.semantic_signature,
                "depth": graph.depth,
                "coverage": graph.coverage.as_dict() if graph.coverage else None,
            },
        )
        if graph.proposition_ref != expected_ref:
            raise ValueError("proposition graph identity mismatch")
        return graph

    @classmethod
    def from_packet(
        cls,
        packet: Mapping[str, Any],
        *,
        coverage: PropositionCoverage | None,
        provenance: Mapping[str, Any] | None = None,
        root_application_ref: str | None = None,
        depth: int = 1,
    ) -> "PropositionGraph":
        force = str(packet.get("force", "claim"))
        if force == "query":
            raw_apps = tuple(dict(item) for item in dict(packet.get("query") or {}).get("restrictions", ()))
            projection = tuple(dict(packet.get("query") or {}).get("projection", ()))
        elif force == "directive":
            raw_apps = tuple(dict(item) for item in dict(packet.get("directive") or {}).get("content", ()))
            projection = ()
        else:
            raw_apps = tuple(dict(item) for item in packet.get("apps", ()))
            projection = ()
        if not raw_apps:
            raise ValueError("packet cannot become a proposition graph without applications")
        apps = tuple(PropositionApplication.from_dict(item) for item in raw_apps)
        root = str(root_application_ref or apps[-1].application_ref)
        packet_qualifiers = {
            **dict(packet.get("qualifiers", {}) or {}),
            **(
                dict(dict(packet.get("query") or {}).get("qualifiers", {}) or {})
                if force == "query" else {}
            ),
        }
        return cls.create(
            apps,
            root_application_ref=root,
            force=force,
            modality=str(packet.get("modality", "actual")),
            polarity=str(packet_qualifiers.get("polarity", "positive")),
            projected_variables=projection,
            ports_provided=packet_qualifiers.get("ports_provided", ()),
            ports_required=packet_qualifiers.get("ports_required", ()),
            depth=depth,
            coverage=coverage,
            provenance={
                **dict(provenance or {}),
                "packet_qualifiers": packet_qualifiers,
                "describe_request": packet.get("describe"),
            },
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "proposition_graph_abi": PROPOSITION_GRAPH_ABI,
            "atomic_composition_abi": ATOMIC_COMPOSITION_ABI,
            "proposition_ref": self.proposition_ref,
            "semantic_signature": self.semantic_signature,
            "applications": [item.as_dict() for item in self.applications],
            "root_application_ref": self.root_application_ref,
            "force": self.force,
            "modality": self.modality,
            "polarity": self.polarity,
            "projected_variables": list(self.projected_variables),
            "ports_provided": list(self.ports_provided),
            "ports_required": list(self.ports_required),
            "depth": self.depth,
            "coverage": self.coverage.as_dict() if self.coverage else None,
            "provenance": dict(self.provenance),
        }

    def packet(self) -> dict[str, Any]:
        qualifiers = {
            **dict(self.provenance.get("packet_qualifiers", {}) or {}),
            "proposition_ref": self.proposition_ref,
            "proposition_graph_abi": PROPOSITION_GRAPH_ABI,
            "atomic_composition_abi": ATOMIC_COMPOSITION_ABI,
            "root_application_ref": self.root_application_ref,
        }
        applications = [item.packet_application() for item in self.applications]
        packet = {
            "force": self.force,
            "apps": applications if self.force not in {"query", "directive"} else [],
            "query": None,
            "directive": None,
            "describe": self.provenance.get("describe_request"),
            "qualifiers": qualifiers,
            "modality": self.modality,
        }
        if self.force == "query":
            role_kinds = {
                "role:event": "event", "role:type": "event_type", "role:class": "concept",
                "role:relation": "relation_type", "role:dimension": "state_dimension",
                "role:value": "state_value",
            }
            variable_kinds: dict[str, set[str]] = {}
            for app in self.applications:
                for role, value in app.args.items():
                    if isinstance(value, str) and value.startswith("?"):
                        variable_kinds.setdefault(value, set()).add(role_kinds.get(role, "atom"))
            variables = []
            for ref in sorted(variable_kinds):
                concrete = {kind for kind in variable_kinds[ref] if kind != "atom"}
                if len(concrete) > 1:
                    raise ValueError(f"incompatible variable role kinds: {ref}:{sorted(concrete)}")
                variables.append({"ref": ref, "filler_kind": next(iter(concrete), "atom")})
            packet["query"] = {
                "restrictions": applications,
                "variables": variables,
                "projection": list(self.projected_variables),
                "qualifiers": dict(qualifiers),
            }
        elif self.force == "directive":
            packet["directive"] = {"content": applications}
        return packet


@dataclass(frozen=True)
class PropositionUnit:
    """Transient form-lattice-compatible unit wrapping one proposition graph."""

    unit_ref: str
    proposition: PropositionGraph
    token_start: int
    token_end: int
    char_start: int
    char_end: int
    score: float = 0.0
    surface: str = ""
    normalized: str = ""
    kind: str = "proposition"
    semantic_ref: str | None = None
    atom_kind: str | None = None
    source_kind: str = "proposition_graph"

    @classmethod
    def create(cls, proposition: PropositionGraph, *, token_start: int, token_end: int,
               char_start: int, char_end: int, score: float = 0.0, surface: str = ""):
        if token_start < 0 or token_end <= token_start or char_start < 0 or char_end < char_start:
            raise ValueError("invalid proposition unit bounds")
        ref = stable(
            "proposition-unit-v1", proposition.proposition_ref, token_start, token_end,
            char_start, char_end,
        )
        return cls(ref, proposition, token_start, token_end, char_start, char_end,
                   float(score), str(surface), str(surface).casefold())

    @property
    def features(self) -> Mapping[str, Any]:
        root = next(app for app in self.proposition.applications
                    if app.application_ref == self.proposition.root_application_ref)
        return {
            "semantic_kind": "proposition",
            "proposition_graph_abi": PROPOSITION_GRAPH_ABI,
            "atomic_composition_abi": ATOMIC_COMPOSITION_ABI,
            "proposition_ref": self.proposition.proposition_ref,
            "proposition_graph": self.proposition.as_dict(),
            "root_application_ref": self.proposition.root_application_ref,
            "root_operator_ref": root.operator_ref,
            "embedded_force": self.proposition.force,
            "modality": self.proposition.modality,
            "polarity": self.proposition.polarity,
            "depth": self.proposition.depth,
            "projected_variables": list(self.proposition.projected_variables),
            "ports_provided": list(dict.fromkeys(("argument:proposition", *self.proposition.ports_provided))),
            "ports_required": list(self.proposition.ports_required),
            "expanded_source_unit_refs": list(
                self.proposition.coverage.expanded_unit_refs if self.proposition.coverage else ()
            ),
            "top_level_executable": False,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "unit_ref": self.unit_ref,
            "kind": self.kind,
            "surface": self.surface,
            "normalized": self.normalized,
            "token_start": self.token_start,
            "token_end": self.token_end,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "semantic_ref": None,
            "atom_kind": None,
            "source_kind": self.source_kind,
            "score": self.score,
            "features": dict(self.features),
        }
