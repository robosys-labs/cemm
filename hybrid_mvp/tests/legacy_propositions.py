"""Old proposition graph types used by fixture owners.

This module owns the legacy :class:`Application` and
:class:`PropositionGraph` types that the development/typed_fixture profile
fixture owners use to build the simple observation programs returned by the
:class:`FixtureProposalOwner`. The new recursive
:class:`SemanticSwitchProgram` lives in :mod:`cemm_authoritative_hybrid.programs`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping
import hashlib
import json

__all__ = [
    "FIXED_OPERATORS",
    "MAX_APPLICATIONS",
    "MAX_DEPTH",
    "Application",
    "PropositionGraph",
    "SemanticSwitchProgram",
]

FIXED_OPERATORS = frozenset({
    "op:designation", "op:type", "op:relation", "op:state", "op:event"
})

MAX_APPLICATIONS = 24
MAX_DEPTH = 6


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _stable(namespace: str, *parts: Any) -> str:
    return f"{namespace}:{hashlib.sha256(_canonical(parts).encode('utf-8')).hexdigest()[:24]}"


def _is_variable(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("?")


def _app_link(value: Any) -> str | None:
    if isinstance(value, Mapping) and set(value) == {"app"}:
        ref = value.get("app")
        return str(ref) if isinstance(ref, str) and ref else None
    return None


@dataclass(frozen=True)
class Application:
    application_ref: str
    operator: str
    args: Mapping[str, Any]
    stance: str = "support"
    qualifiers: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.operator not in FIXED_OPERATORS:
            raise ValueError(f"non-kernel operator: {self.operator}")
        if not self.application_ref or not self.args:
            raise ValueError("application requires ref and args")
        if any(not str(role).startswith("role:") for role in self.args):
            raise ValueError("malformed role")
        if self.stance not in {"support", "deny"}:
            raise ValueError("invalid stance")

    @classmethod
    def create(
        cls,
        operator: str,
        args: Mapping[str, Any],
        *,
        stance: str = "support",
        qualifiers: Mapping[str, Any] | None = None,
        application_ref: str | None = None,
    ) -> "Application":
        material = (operator, dict(args), stance, dict(qualifiers or {}))
        return cls(
            application_ref or _stable("app", material),
            operator,
            dict(args),
            stance,
            dict(qualifiers or {}),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "application_ref": self.application_ref,
            "operator": self.operator,
            "args": dict(self.args),
            "stance": self.stance,
            "qualifiers": dict(self.qualifiers),
        }


@dataclass(frozen=True)
class PropositionGraph:
    graph_ref: str
    applications: tuple[Application, ...]
    root_application_ref: str
    force: str = "claim"
    modality: str = "actual"
    polarity: str = "positive"
    projected_variables: tuple[str, ...] = ()
    depth: int = 1
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 1 <= len(self.applications) <= MAX_APPLICATIONS:
            raise ValueError("application bound violated")
        if not 1 <= self.depth <= MAX_DEPTH:
            raise ValueError("depth bound violated")
        refs = [app.application_ref for app in self.applications]
        if len(refs) != len(set(refs)):
            raise ValueError("duplicate application refs")
        if self.root_application_ref not in refs:
            raise ValueError("root missing")
        declared = set(self.projected_variables)
        if any(not _is_variable(v) for v in declared):
            raise ValueError("invalid projection")
        present: set[str] = set()
        links: dict[str, set[str]] = {ref: set() for ref in refs}
        for app in self.applications:
            for value in app.args.values():
                if _is_variable(value):
                    present.add(value)
                child = _app_link(value)
                if child:
                    if child not in links:
                        raise ValueError(f"dangling app link: {child}")
                    links[app.application_ref].add(child)
        if declared - present:
            raise ValueError("projection absent from graph")
        self._assert_acyclic(links)

    @staticmethod
    def _assert_acyclic(links: Mapping[str, set[str]]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()
        def walk(node: str) -> None:
            if node in visiting:
                raise ValueError("application cycle")
            if node in visited:
                return
            visiting.add(node)
            for child in links[node]:
                walk(child)
            visiting.remove(node)
            visited.add(node)
        for node in links:
            walk(node)

    @classmethod
    def create(
        cls,
        applications: Iterable[Application],
        root_application_ref: str,
        *,
        force: str = "claim",
        modality: str = "actual",
        polarity: str = "positive",
        projected_variables: Iterable[str] = (),
        depth: int = 1,
        provenance: Mapping[str, Any] | None = None,
    ) -> "PropositionGraph":
        apps = tuple(applications)
        material = ([a.as_dict() for a in apps], root_application_ref, force, modality, polarity, tuple(projected_variables))
        return cls(
            _stable("graph", material), apps, root_application_ref, force, modality,
            polarity, tuple(projected_variables), depth, dict(provenance or {})
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "graph_ref": self.graph_ref,
            "applications": [a.as_dict() for a in self.applications],
            "root_application_ref": self.root_application_ref,
            "force": self.force,
            "modality": self.modality,
            "polarity": self.polarity,
            "projected_variables": list(self.projected_variables),
            "depth": self.depth,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True)
class SemanticSwitchProgram:
    """Legacy simple semantic switch program used by fixture owners.

    The development/typed_fixture profile fixture owners build these simple
    observation programs. The new recursive
    :class:`cemm_authoritative_hybrid.programs.SemanticSwitchProgram` is used by
    the neural proposer and exact verifier.
    """

    program_ref: str
    mode: str
    context_event_ref: str
    graph: PropositionGraph
    requested_transition: Mapping[str, Any] | None = None
    evidence: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        mode: str,
        context_event_ref: str,
        graph: PropositionGraph,
        *,
        requested_transition: Mapping[str, Any] | None = None,
        evidence: Mapping[str, Any] | None = None,
    ) -> "SemanticSwitchProgram":
        return cls(
            _stable("program", mode, context_event_ref, graph.graph_ref, requested_transition),
            mode, context_event_ref, graph, dict(requested_transition or {}) or None,
            dict(evidence or {}),
        )
