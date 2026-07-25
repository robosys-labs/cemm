"""Recursive state entitlement and generic state-timeline projection.

State-space competence is data-driven: type/facet closure recursively grants
state dimensions/capabilities/resources/mechanisms. No referent-specific state
schema is introduced here, and projection uses targeted store lookups rather
than scanning the whole semantic graph.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cemm.config import Config
from cemm.model import canonical


@dataclass(frozen=True)
class StateDimensionProjection:
    dimension_ref: str
    domain_ref: str | None
    domain_type: str | None
    cardinality: str
    status: str
    values: tuple[Any, ...]
    support: tuple[dict[str, Any], ...]
    opposition: tuple[dict[str, Any], ...]
    contradiction_lineage: tuple[dict[str, Any], ...]
    default_expectation: Any = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "dimension_ref": self.dimension_ref,
            "domain_ref": self.domain_ref,
            "domain_type": self.domain_type,
            "cardinality": self.cardinality,
            "status": self.status,
            "values": list(self.values),
            "support": list(self.support),
            "opposition": list(self.opposition),
            "contradiction_lineage": list(self.contradiction_lineage),
            "default_expectation": self.default_expectation,
        }


@dataclass(frozen=True)
class StateSpaceProjection:
    referent_ref: str
    direct_types: tuple[str, ...]
    type_facet_closure: tuple[str, ...]
    dimensions: tuple[StateDimensionProjection, ...]
    capabilities: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()
    mechanisms: tuple[str, ...] = ()
    dependency_edges: tuple[dict[str, str], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "referent_ref": self.referent_ref,
            "direct_types": list(self.direct_types),
            "type_facet_closure": list(self.type_facet_closure),
            "dimensions": [x.as_dict() for x in self.dimensions],
            "capabilities": list(self.capabilities),
            "resources": list(self.resources),
            "mechanisms": list(self.mechanisms),
            "dependency_edges": list(self.dependency_edges),
        }


class StateProjector:
    """Project recursively entitled state space from exact graph authority."""

    def __init__(self, store, config: Config | None = None, authority_generation: int | None = None):
        self.s = store
        self.config = config or Config()
        self.authority_generation = store.generation if authority_generation is None else int(authority_generation)
        self._entitlement_cache: OrderedDict[tuple[Any, ...], dict[str, Any]] = OrderedDict()

    def _symbol(self, role: str) -> str | None:
        try:
            return self.s.symbol(role)
        except ValueError:
            return None

    def _authority_objects(self, subject: str, relation_role: str) -> set[str]:
        relation = self._symbol(relation_role)
        if not relation:
            return set()
        return set(
            self.s.relation_objects(
                subject,
                relation,
                authority_only=True,
                upto_generation=self.authority_generation,
            )
        )

    def _type_closure(self, referent_ref: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
        direct = set(self.s.type_classes(referent_ref))
        atom = self.s.atom(referent_ref)
        if atom and atom["kind"] == "concept":
            direct.add(referent_ref)

        closure = set(direct)
        queue = list(sorted(direct))
        while queue:
            current = queue.pop(0)
            parents = self._authority_objects(current, "profile.subtype_relation")
            parents |= self._authority_objects(current, "profile.facet_relation")
            for parent in sorted(parents):
                if parent not in closure:
                    closure.add(parent)
                    queue.append(parent)
        return tuple(sorted(direct)), tuple(sorted(closure))

    def _dependency_edges(self, roots: set[str]) -> tuple[dict[str, str], ...]:
        """Return bounded recursive dependency edges for entitled operational refs.

        One generic semantic relation is used regardless of whether the dependency
        target is a state spec, resource, capability, or another semantic object.
        Target kind/definitions carry the semantics; the kernel does not branch on
        domain-specific dependency relation names.
        """
        relation = self._symbol("profile.depends_on_relation")
        if not relation:
            return ()
        edges: list[dict[str, str]] = []
        seen_nodes = set(roots)
        queue = list(sorted(roots))
        while queue:
            subject = queue.pop(0)
            for target in sorted(
                self.s.relation_objects(
                    subject,
                    relation,
                    authority_only=True,
                    upto_generation=self.authority_generation,
                )
            ):
                edge = {"subject": subject, "depends_on": target}
                if edge not in edges:
                    edges.append(edge)
                if target not in seen_nodes:
                    seen_nodes.add(target)
                    queue.append(target)
        return tuple(edges)

    def _entitlement_template(self, referent_ref: str) -> dict[str, Any]:
        direct, closure = self._type_closure(referent_ref)
        key = (self.authority_generation, closure)
        cached = self._entitlement_cache.get(key)
        if cached is not None:
            self._entitlement_cache.move_to_end(key)
            return {**cached, "direct_types": direct}

        # Entitlement belongs to type/facet authority, not per-referent schemas.
        subjects = set(closure)
        dimensions: set[str] = set()
        capabilities: set[str] = set()
        resources: set[str] = set()
        mechanisms: set[str] = set()
        for subject in subjects:
            dimensions |= self._authority_objects(subject, "profile.entitles_dimension_relation")
            capabilities |= self._authority_objects(subject, "profile.entitles_capability_relation")
            resources |= self._authority_objects(subject, "profile.entitles_resource_relation")
            mechanisms |= self._authority_objects(subject, "profile.mechanism_applies_relation")

        operational_roots = capabilities | resources | mechanisms
        template = {
            "closure": closure,
            "dimensions": tuple(sorted(dimensions)),
            "capabilities": tuple(sorted(capabilities)),
            "resources": tuple(sorted(resources)),
            "mechanisms": tuple(sorted(mechanisms)),
            "dependency_edges": self._dependency_edges(operational_roots),
        }
        self._entitlement_cache[key] = template
        self._entitlement_cache.move_to_end(key)
        while len(self._entitlement_cache) > self.config.state_projection_cache_limit:
            self._entitlement_cache.popitem(last=False)
        return {**template, "direct_types": direct}

    def _domain(self, dimension_ref: str) -> tuple[str | None, str | None]:
        import json

        domains = sorted(self._authority_objects(dimension_ref, "profile.dimension_domain_relation"))
        domain_ref = domains[0] if len(domains) == 1 else None
        domain_type = None
        if domain_ref:
            atom = self.s.atom(domain_ref)
            if atom:
                domain_type = json.loads(atom["metadata"]).get("domain_type")
        if not domain_type:
            atom = self.s.atom(dimension_ref)
            if atom:
                domain_type = json.loads(atom["metadata"]).get("domain_type")
        return domain_ref, domain_type

    @staticmethod
    def _age_seconds(timestamp: str | None) -> float | None:
        if not timestamp:
            return None
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds())
        except (TypeError, ValueError):
            return None

    def _reconcile_claims(
        self,
        dimension_ref: str,
        domain_ref: str | None,
        domain_type: str | None,
        meta: dict[str, Any],
        claims: list[dict[str, Any]],
    ) -> StateDimensionProjection:
        cardinality = meta.get("cardinality") or ("one" if meta.get("exclusive") else "many")
        support = [c for c in claims if c["stance"] == "support" and c["valid_to"] is None]
        opposition = [c for c in claims if c["stance"] == "deny" and c["valid_to"] is None]
        values_by_sig = {canonical(c["value"]): c["value"] for c in support}
        denied = {canonical(c["value"]): c for c in opposition}
        contradictions: list[dict[str, Any]] = []
        for c in support:
            sig = canonical(c["value"])
            if sig in denied:
                contradictions.append({"support_claim": c["claim_ref"], "deny_claim": denied[sig]["claim_ref"]})
        if cardinality == "one" and len(values_by_sig) > 1:
            contradictions.append({"exclusive_values": [values_by_sig[k] for k in sorted(values_by_sig)]})

        if not support:
            status = "missing"
        elif contradictions:
            status = "conflicting"
        else:
            newest = max((c.get("observed_at") or c.get("valid_from") or "" for c in support), default="")
            stale_after = meta.get("stale_after_seconds")
            age = self._age_seconds(newest)
            if stale_after is not None and age is not None and age > float(stale_after):
                status = "stale"
            elif max((float(c.get("confidence", 0.0)) for c in support), default=0.0) < self.config.state_support_threshold:
                status = "uncertain"
            else:
                status = "resolved"

        return StateDimensionProjection(
            dimension_ref=dimension_ref,
            domain_ref=domain_ref,
            domain_type=domain_type,
            cardinality=cardinality,
            status=status,
            values=tuple(values_by_sig[k] for k in sorted(values_by_sig)),
            support=tuple(support),
            opposition=tuple(opposition),
            contradiction_lineage=tuple(contradictions),
            default_expectation=meta.get("default_expectation"),
        )

    def project(self, referent_ref: str) -> StateSpaceProjection:
        import json

        template = self._entitlement_template(referent_ref)
        dimensions = []
        for dimension_ref in template["dimensions"]:
            atom = self.s.atom(dimension_ref)
            meta = json.loads(atom["metadata"]) if atom else {}
            domain_ref, domain_type = self._domain(dimension_ref)
            claims = self.s.state_claim_records(referent_ref, dimension_ref)
            dimensions.append(self._reconcile_claims(dimension_ref, domain_ref, domain_type, meta, claims))
        return StateSpaceProjection(
            referent_ref=referent_ref,
            direct_types=template["direct_types"],
            type_facet_closure=template["closure"],
            dimensions=tuple(dimensions),
            capabilities=template["capabilities"],
            resources=template["resources"],
            mechanisms=template["mechanisms"],
            dependency_edges=template["dependency_edges"],
        )
