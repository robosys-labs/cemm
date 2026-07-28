"""Bounded, proof-bearing semantic-target descriptions.

Description reads existing exact authority/world applications.  It never creates
semantic facts, scans the complete store, or fabricates dictionary prose.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Iterable, Mapping

from cemm.model import Fact, stable

DESCRIPTION_ABI = 1
DEFAULT_FACETS = (
    "designation", "kind", "type", "supertype", "defining_relation",
    "frame", "state_schema", "capability", "part_structure", "provenance",
)


@dataclass(frozen=True)
class DescriptionRequest:
    request_ref: str
    target_ref: str
    requested_facets: tuple[str, ...]
    max_depth: int
    max_facts: int
    authority_generation: int
    provenance: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, target_ref: str, *, requested_facets: Iterable[str] = DEFAULT_FACETS,
               max_depth: int = 3, max_facts: int = 48, authority_generation: int = 0,
               provenance: Mapping[str, Any] | None = None):
        facets = tuple(dict.fromkeys(map(str, requested_facets)))
        if not target_ref or not facets:
            raise ValueError("description request requires target and facets")
        if not 1 <= int(max_depth) <= 8 or not 1 <= int(max_facts) <= 256:
            raise ValueError("description request bounds are invalid")
        body = (target_ref, facets, max_depth, max_facts, authority_generation, dict(provenance or {}))
        return cls(stable("description-request-v1", body), str(target_ref), facets,
                   int(max_depth), int(max_facts), int(authority_generation), dict(provenance or {}))

    def as_dict(self):
        return {
            "description_abi": DESCRIPTION_ABI,
            "request_ref": self.request_ref,
            "target_ref": self.target_ref,
            "requested_facets": list(self.requested_facets),
            "max_depth": self.max_depth,
            "max_facts": self.max_facts,
            "authority_generation": self.authority_generation,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True)
class DescriptionResult:
    result_ref: str
    request: DescriptionRequest
    target_kind: str
    preferred_surface: str | None
    facts: tuple[Fact, ...]
    fact_facets: Mapping[str, tuple[str, ...]]
    source_refs: tuple[str, ...]
    claim_refs: tuple[str, ...]
    completeness: str
    missing_facets: tuple[str, ...]
    conflicts: tuple[str, ...] = ()

    def as_dict(self):
        return {
            "description_abi": DESCRIPTION_ABI,
            "result_ref": self.result_ref,
            "request": self.request.as_dict(),
            "target_ref": self.request.target_ref,
            "target_kind": self.target_kind,
            "preferred_surface": self.preferred_surface,
            "facts": [
                {"ref": fact.ref, "operator": fact.operator, "args": dict(fact.args),
                 "stance": fact.stance, "confidence": fact.confidence}
                for fact in self.facts
            ],
            "fact_facets": {key: list(value) for key, value in self.fact_facets.items()},
            "source_refs": list(self.source_refs),
            "claim_refs": list(self.claim_refs),
            "completeness": self.completeness,
            "missing_facets": list(self.missing_facets),
            "conflicts": list(self.conflicts),
        }


class SemanticDescriptionEngine:
    def __init__(self, store: Any, config: Any, authority_generation: int) -> None:
        self.store = store
        self.authority_generation = int(authority_generation)
        self.max_depth = int(getattr(config, "description_max_depth", 3))
        self.max_facts = int(getattr(config, "description_max_facts", 48))
        self.max_designations = int(getattr(config, "description_max_designations", 8))
        self.max_frames = int(getattr(config, "description_max_frames", 8))
        if not 1 <= self.max_depth <= 8 or not 1 <= self.max_facts <= 256:
            raise ValueError("semantic description configuration is outside bounds")

    def request(self, target_ref: str, *, facets: Iterable[str] = DEFAULT_FACETS,
                provenance: Mapping[str, Any] | None = None) -> DescriptionRequest:
        return DescriptionRequest.create(
            target_ref,
            requested_facets=facets,
            max_depth=self.max_depth,
            max_facts=self.max_facts,
            authority_generation=self.authority_generation,
            provenance=provenance,
        )

    def _preferred(self, target_ref: str) -> str | None:
        rows = self.store.db.execute(
            "SELECT surface FROM designation_index WHERE target_ref=? "
            "ORDER BY preferred DESC,prior DESC,label_ref LIMIT ?",
            (target_ref, self.max_designations),
        ).fetchall()
        return str(rows[0][0]) if rows else None

    def _seed_app_refs(self, target_ref: str, limit: int) -> tuple[str, ...]:
        """Return applications mentioning one atom/app through indexed bindings."""
        rows = self.store.db.execute(
            "SELECT DISTINCT b.app_ref FROM bindings b "
            "JOIN applications a ON a.app_ref=b.app_ref "
            "JOIN claims c ON c.app_ref=a.app_ref "
            "WHERE ((b.filler_kind='atom' AND b.filler_value=?) "
            "OR (b.filler_kind='app' AND b.filler_value=?)) "
            "AND c.valid_to IS NULL AND a.generation<=? "
            "ORDER BY a.generation DESC,b.app_ref LIMIT ?",
            (target_ref, target_ref, self.authority_generation, int(limit)),
        ).fetchall()
        return tuple(str(row[0]) for row in rows)

    @staticmethod
    def _adjacent_refs(facts: Iterable[Fact]) -> tuple[str, ...]:
        output: list[str] = []
        seen: set[str] = set()
        for fact in facts:
            for value in fact.args.values():
                candidate = None
                if isinstance(value, str) and ":" in value and not value.startswith(("?", "!")):
                    candidate = value
                elif isinstance(value, Mapping) and set(value) == {"app"}:
                    candidate = str(value["app"])
                if candidate and candidate not in seen:
                    seen.add(candidate)
                    output.append(candidate)
        return tuple(output)

    def _neighbourhood(self, request: DescriptionRequest) -> tuple[Fact, ...]:
        """Breadth-first bounded semantic neighbourhood, never a full-store scan."""
        frontier = [request.target_ref]
        visited_refs: set[str] = set()
        visited_apps: set[str] = set()
        output: list[Fact] = []
        for _depth in range(request.max_depth):
            if not frontier or len(output) >= request.max_facts:
                break
            next_frontier: list[str] = []
            for target in frontier:
                if target in visited_refs:
                    continue
                visited_refs.add(target)
                remaining = request.max_facts - len(output)
                app_refs = self._seed_app_refs(target, remaining)
                fresh_refs = tuple(ref for ref in app_refs if ref not in visited_apps)
                visited_apps.update(fresh_refs)
                hydrated = tuple(self._hydrate(fresh_refs))[:remaining]
                output.extend(hydrated)
                for adjacent in self._adjacent_refs(hydrated):
                    if adjacent not in visited_refs and adjacent not in next_frontier:
                        next_frontier.append(adjacent)
                if len(output) >= request.max_facts:
                    break
            frontier = next_frontier
        return tuple(output[: request.max_facts])

    def _hydrate(self, app_refs: Iterable[str]) -> tuple[Fact, ...]:
        method = getattr(self.store, "_facts_from_app_refs", None)
        if callable(method):
            return tuple(method(tuple(app_refs), limit=self.max_facts))
        refs = tuple(app_refs)
        if not refs:
            return ()
        placeholders = ",".join("?" for _ in refs)
        applications = self.store.db.execute(
            f"SELECT app_ref,operator_ref FROM applications WHERE app_ref IN({placeholders})",
            refs,
        ).fetchall()
        output = []
        for row in applications:
            args = {}
            for binding in self.store.db.execute(
                "SELECT role_ref,filler_kind,filler_value FROM bindings WHERE app_ref=? ORDER BY ordinal",
                (row["app_ref"],),
            ).fetchall():
                args[str(binding["role_ref"])] = self.store.decode_value(
                    binding["filler_kind"], binding["filler_value"]
                )
            output.append(Fact(str(row["app_ref"]), str(row["operator_ref"]), args, "support", 1.0))
        return tuple(output)

    @staticmethod
    def _facet(fact: Fact, target_ref: str) -> str:
        if fact.operator == "op:designation" and fact.args.get("role:target") == target_ref:
            return "designation"
        if fact.operator == "op:type" and fact.args.get("role:instance") == target_ref:
            return "type"
        if fact.operator == "op:relation":
            relation = fact.args.get("role:relation")
            if relation == "rel:subtype_of":
                return "supertype"
            if relation == "rel:has_semantic_frame":
                return "frame"
            if relation in {"rel:requires_capability", "rel:entitles_capability", "rel:has_capability"}:
                return "capability"
            if relation in {"rel:part_of", "rel:has_part"}:
                return "part_structure"
            return "defining_relation"
        if fact.operator == "op:state":
            return "state_schema"
        return "provenance"

    def describe(self, request: DescriptionRequest) -> DescriptionResult:
        if request.authority_generation != self.authority_generation:
            raise ValueError("description request authority generation mismatch")
        atom = self.store.atom(request.target_ref)
        if atom is None:
            target_kind = "unknown"
            facts = ()
        else:
            target_kind = str(atom["kind"])
            facts = self._neighbourhood(request)
        facet_refs: dict[str, list[str]] = {facet: [] for facet in request.requested_facets}
        for fact in facts:
            facet = self._facet(fact, request.target_ref)
            if facet in facet_refs:
                facet_refs[facet].append(fact.ref)
        present = {key for key, values in facet_refs.items() if values}
        if atom is not None:
            present.add("kind")
        missing = tuple(facet for facet in request.requested_facets if facet not in present)
        structural = present.intersection({
            "type", "supertype", "defining_relation", "frame", "state_schema",
            "capability", "part_structure",
        })
        conflicts = tuple(sorted(
            fact.ref for fact in facts if fact.stance == "deny"
        ))
        if conflicts:
            completeness = "conflicting_structure"
        elif not structural:
            completeness = "identity_only"
        elif len(structural) < 2:
            completeness = "partial_structure"
        else:
            completeness = "sufficient_structure"
        app_refs = tuple(fact.ref for fact in facts)
        claim_rows = []
        if app_refs:
            placeholders = ",".join("?" for _ in app_refs)
            claim_rows = self.store.db.execute(
                f"SELECT c.claim_ref,o.source_ref FROM claims c "
                f"JOIN observations o ON o.observation_ref=c.observation_ref "
                f"WHERE c.app_ref IN({placeholders}) AND c.valid_to IS NULL "
                f"ORDER BY c.generation DESC,c.claim_ref LIMIT ?",
                (*app_refs, request.max_facts),
            ).fetchall()
        claim_refs = tuple(dict.fromkeys(str(row["claim_ref"]) for row in claim_rows))
        sources = tuple(dict.fromkeys(str(row["source_ref"]) for row in claim_rows))
        body = (
            request.as_dict(), target_kind, [fact.ref for fact in facts], facet_refs,
            sources, claim_refs, completeness, missing, conflicts,
        )
        return DescriptionResult(
            stable("description-result-v1", body),
            request,
            target_kind,
            self._preferred(request.target_ref),
            facts,
            {key: tuple(values) for key, values in facet_refs.items()},
            sources,
            claim_refs,
            completeness,
            missing,
            conflicts,
        )
