"""Bounded proposition graphs over CEMM's five fixed operator applications.

A proposition is not a sixth semantic operator.  It is a transient, rooted graph
of ordinary designation/type/relation/state/event applications.  Event-to-event
complements use shared event refs in role:object/role:target, so the exact store
and query engine remain unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Iterable, Mapping

PROPOSITION_GRAPH_ABI = 1
FIXED_OPERATORS = frozenset({
    "op:designation", "op:type", "op:relation", "op:state", "op:event",
})
MAX_PROPOSITION_APPLICATIONS = 24
MAX_PROPOSITION_DEPTH = 6


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def stable(namespace: str, *parts: Any) -> str:
    return f"{namespace}:{hashlib.sha256(canonical((namespace, parts)).encode()).hexdigest()[:24]}"


def _semantic_ref(value: Any) -> str | None:
    if isinstance(value, str) and not value.startswith(("?", "!")):
        return value
    if isinstance(value, Mapping) and "new" in value:
        return str(value["new"])
    return None


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
        if self.stance not in {"support", "oppose"}:
            raise ValueError("unsupported proposition stance")

    @classmethod
    def create(
        cls,
        operator_ref: str,
        args: Mapping[str, Any],
        *,
        stance: str = "support",
        qualifiers: Mapping[str, Any] | None = None,
    ) -> "PropositionApplication":
        material = (operator_ref, dict(args), stance, dict(qualifiers or {}))
        return cls(
            stable("proposition-application", material),
            str(operator_ref),
            dict(args),
            str(stance),
            dict(qualifiers or {}),
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
            "operator": self.operator_ref,
            "args": dict(self.args),
            "stance": self.stance,
        }


@dataclass(frozen=True)
class PropositionGraph:
    proposition_ref: str
    applications: tuple[PropositionApplication, ...]
    root_application_ref: str
    force: str = "claim"
    modality: str = "actual"
    polarity: str = "positive"
    projected_variables: tuple[str, ...] = ()
    depth: int = 1
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
        if self.force not in {
            "claim", "query", "directive", "description", "correction",
            "retraction", "acknowledgment",
        }:
            raise ValueError(f"unsupported proposition force: {self.force}")
        declared = set(self.projected_variables)
        if any(not value.startswith("?") for value in declared):
            raise ValueError("proposition projections must be semantic variables")
        present = {
            value
            for app in self.applications
            for value in app.args.values()
            if isinstance(value, str) and value.startswith("?")
        }
        if declared - present:
            raise ValueError("proposition projects a variable absent from its graph")
        self._assert_acyclic_event_complements()

    def _assert_acyclic_event_complements(self) -> None:
        event_nodes: set[str] = set()
        edges: dict[str, set[str]] = {}
        for app in self.applications:
            if app.operator_ref != "op:event":
                continue
            event_ref = _semantic_ref(app.args.get("role:event"))
            if not event_ref:
                continue
            event_nodes.add(event_ref)
            for role in ("role:object", "role:target"):
                child = _semantic_ref(app.args.get(role))
                if child:
                    edges.setdefault(event_ref, set()).add(child)
        visiting: set[str] = set()
        visited: set[str] = set()

        def walk(node: str) -> None:
            if node in visiting:
                raise ValueError("proposition event-complement cycle")
            if node in visited:
                return
            visiting.add(node)
            for child in edges.get(node, ()):
                if child in event_nodes:
                    walk(child)
            visiting.remove(node)
            visited.add(node)

        for node in event_nodes:
            walk(node)

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
        depth: int = 1,
        provenance: Mapping[str, Any] | None = None,
    ) -> "PropositionGraph":
        apps = tuple(applications)
        material = {
            "abi": PROPOSITION_GRAPH_ABI,
            "applications": [item.as_dict() for item in apps],
            "root": root_application_ref,
            "force": force,
            "modality": modality,
            "polarity": polarity,
            "projected_variables": sorted(set(projected_variables)),
            "depth": int(depth),
        }
        return cls(
            stable("proposition-graph", material),
            apps,
            str(root_application_ref),
            str(force),
            str(modality),
            str(polarity),
            tuple(sorted(set(map(str, projected_variables)))),
            int(depth),
            dict(provenance or {}),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "proposition_graph_abi": PROPOSITION_GRAPH_ABI,
            "proposition_ref": self.proposition_ref,
            "applications": [item.as_dict() for item in self.applications],
            "root_application_ref": self.root_application_ref,
            "force": self.force,
            "modality": self.modality,
            "polarity": self.polarity,
            "projected_variables": list(self.projected_variables),
            "depth": self.depth,
            "provenance": dict(self.provenance),
        }

    def query_packet(self, *, qualifiers: Mapping[str, Any]) -> dict[str, Any]:
        role_kinds = {
            "role:event": "event",
            "role:type": "event_type",
            "role:class": "concept",
            "role:relation": "relation_type",
            "role:dimension": "state_dimension",
            "role:value": "state_value",
        }
        variable_kinds: dict[str, set[str]] = {}
        for app in self.applications:
            for role, value in app.args.items():
                if isinstance(value, str) and value.startswith("?"):
                    variable_kinds.setdefault(value, set()).add(role_kinds.get(role, "atom"))
        declarations = []
        for ref in sorted(variable_kinds):
            kinds = variable_kinds[ref]
            concrete = {item for item in kinds if item != "atom"}
            if len(concrete) > 1:
                raise ValueError(f"proposition variable has incompatible role kinds: {ref}:{sorted(kinds)}")
            declarations.append({
                "ref": ref,
                "filler_kind": next(iter(concrete), "atom"),
            })
        return {
            "force": "query",
            "apps": [],
            "query": {
                "restrictions": [item.packet_application() for item in self.applications],
                "variables": declarations,
                "projection": list(self.projected_variables),
                "qualifiers": dict(qualifiers),
            },
            "directive": None,
            "describe": None,
            "qualifiers": {
                "proposition_ref": self.proposition_ref,
                "proposition_graph_abi": PROPOSITION_GRAPH_ABI,
            },
            "modality": self.modality,
        }


def event_application(
    event_ref: Any,
    event_type_ref: str,
    *,
    actor_ref: Any | None = None,
    target_ref: Any | None = None,
    object_ref: Any | None = None,
) -> PropositionApplication:
    args: dict[str, Any] = {
        "role:event": event_ref,
        "role:type": event_type_ref,
    }
    if actor_ref is not None:
        args["role:actor"] = actor_ref
    if target_ref is not None:
        args["role:target"] = target_ref
    if object_ref is not None:
        args["role:object"] = object_ref
    return PropositionApplication.create("op:event", args)


def capability_inventory_query(target_ref: Any) -> PropositionGraph:
    type_app = PropositionApplication.create(
        "op:type",
        {"role:instance": target_ref, "role:class": "?agent_class"},
    )
    cap_app = PropositionApplication.create(
        "op:relation",
        {
            "role:subject": "?agent_class",
            "role:relation": "rel:entitles_capability",
            "role:object": "?capability",
        },
    )
    return PropositionGraph.create(
        (type_app, cap_app),
        root_application_ref=cap_app.application_ref,
        force="query",
        modality="capability",
        projected_variables=("?capability",),
        depth=2,
        provenance={"construction_family": "capability_inventory_query"},
    )


def desire_knowledge_designation_query(
    experiencer_ref: Any,
    designation_target_ref: Any,
    label_type_ref: str,
) -> PropositionGraph:
    want = event_application(
        "?want_event",
        "event:want",
        actor_ref=experiencer_ref,
        object_ref="?know_event",
    )
    know = event_application(
        "?know_event",
        "event:know",
        actor_ref=experiencer_ref,
        target_ref=designation_target_ref,
        object_ref=label_type_ref,
    )
    return PropositionGraph.create(
        (want, know),
        root_application_ref=want.application_ref,
        force="query",
        projected_variables=(),
        depth=2,
        provenance={"construction_family": "desire_knowledge_designation_query"},
    )
