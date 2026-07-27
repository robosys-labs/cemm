"""Capability derivation from semantic dependencies and one operational snapshot.

Missing evidence remains unknown.  Observed unavailability remains unavailable.
Neither condition is converted into a default numeric support value or durable
self state.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping

from cemm.model import stable
from cemm.operational import RESOURCE_STATES, validate_resource_state_score


@dataclass(frozen=True)
class RuntimeObservation:
    target_ref: str
    score: float | None
    source: str
    state: str = "unknown"
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.state not in RESOURCE_STATES:
            raise ValueError(f"invalid runtime observation state: {self.state}")
        validate_resource_state_score(self.state, self.score, label=self.target_ref)
        if not self.target_ref.startswith("resource:"):
            raise ValueError(f"runtime observation target is not a resource: {self.target_ref}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_ref": self.target_ref,
            "score": self.score,
            "source": self.source,
            "state": self.state,
            "evidence": dict(self.evidence),
        }


@dataclass(frozen=True)
class CapabilityAssessment:
    assessment_ref: str
    referent_ref: str
    capability_ref: str
    score: float | None
    status: str
    dependency_scores: Mapping[str, float | None]
    blockers: tuple[str, ...]
    proof: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.status not in RESOURCE_STATES:
            raise ValueError(f"invalid capability status: {self.status}")
        validate_resource_state_score(self.status, self.score, label=self.capability_ref)
        unknown = tuple(self.proof.get("unknown_dependencies", ()))
        if self.status == "unknown" and not unknown:
            raise ValueError("unknown capability assessment requires unknown dependency proof")
        if self.status == "unavailable" and not self.blockers:
            raise ValueError("unavailable capability assessment requires observed blockers")
        if any(value is not None and not 0.0 <= float(value) <= 1.0 for value in self.dependency_scores.values()):
            raise ValueError("capability dependency score is outside [0,1]")

    def as_dict(self) -> dict[str, Any]:
        return {
            "assessment_ref": self.assessment_ref,
            "referent_ref": self.referent_ref,
            "capability_ref": self.capability_ref,
            "score": self.score,
            "status": self.status,
            "dependency_scores": dict(self.dependency_scores),
            "blockers": list(self.blockers),
            "proof": dict(self.proof),
        }


class RuntimeObservationProvider:
    """Read-only projection of the canonical OperationalSnapshot."""

    @staticmethod
    def observe(view_or_snapshot) -> tuple[RuntimeObservation, ...]:
        snapshot = getattr(view_or_snapshot, "operational_snapshot", None) or view_or_snapshot
        if snapshot is None:
            raise ValueError("capability evaluation requires an operational snapshot")
        return tuple(
            RuntimeObservation(
                item.resource_ref,
                item.score,
                item.provider_ref,
                item.state,
                {
                    **dict(item.evidence),
                    "observation_ref": item.observation_ref,
                    "snapshot_ref": snapshot.snapshot_ref,
                    "epistemic_mode": "observed",
                },
            )
            for item in snapshot.observations
        )

    @staticmethod
    def semantic_facts(view_or_snapshot):
        snapshot = getattr(view_or_snapshot, "operational_snapshot", None) or view_or_snapshot
        if snapshot is None or not hasattr(snapshot, "semantic_facts"):
            raise ValueError("semantic runtime facts require an operational snapshot")
        return snapshot.semantic_facts()


class CapabilityEvaluator:
    """Evaluate capability dependencies without conflating unknown and zero."""

    def __init__(self, store, max_depth=12):
        self.s = store
        self.max_depth = int(max_depth)
        if self.max_depth < 1:
            raise ValueError("capability dependency max depth must be positive")

    def _state_scores(self, projection):
        output: dict[str, tuple[float | None, str, str, tuple[str, ...]]] = {}
        for item in projection.get("dimensions", ()):
            dimension_ref = item["dimension_ref"]
            projection_status = str(item.get("status") or "missing")
            values = tuple(item.get("values", ()))
            score: float | None = None
            state = "unknown"
            reason = f"state_projection:{projection_status}"
            blockers: tuple[str, ...] = ()
            if projection_status == "resolved" and len(values) == 1:
                value = values[0]
                if isinstance(value, dict) and "literal" in value:
                    raw = value["literal"].get("value")
                    atom = self.s.atom(dimension_ref)
                    metadata = json.loads(atom["metadata"]) if atom else {}
                    if isinstance(raw, (int, float)):
                        low, high = float(metadata.get("min", 0.0)), float(metadata.get("max", 1.0))
                        score = 1.0 if high == low else (float(raw) - low) / (high - low)
                        if metadata.get("positive_direction") == "lower":
                            score = 1.0 - score
                elif isinstance(value, str):
                    atom = self.s.atom(value)
                    metadata = json.loads(atom["metadata"]) if atom else {}
                    if "support_score" in metadata:
                        score = float(metadata["support_score"])
                if score is not None:
                    score = max(0.0, min(1.0, score))
                    state = "available" if score >= 0.8 else "degraded" if score > 0 else "unavailable"
                    reason = "resolved_state_projection"
                    if state == "unavailable":
                        blockers = (dimension_ref,)
            elif projection_status == "conflicting":
                blockers = (f"conflicting_state:{dimension_ref}",)
            output[dimension_ref] = (score, state, reason, blockers)
        return output

    def evaluate(self, referent_ref, projection, runtime_observations=()):
        direct = self._state_scores(projection)
        runtime_refs: set[str] = set()
        for item in runtime_observations:
            if item.target_ref in runtime_refs:
                raise ValueError(f"duplicate runtime capability evidence: {item.target_ref}")
            runtime_refs.add(item.target_ref)
            direct[item.target_ref] = (
                item.score,
                item.state,
                f"runtime:{item.state}",
                (item.target_ref,) if item.state == "unavailable" else (),
            )

        edges: dict[str, list[str]] = {}
        for edge in projection.get("dependency_edges", ()):
            subject = str(edge["subject"])
            dependency = str(edge["depends_on"])
            edges.setdefault(subject, []).append(dependency)
        memo: dict[str, tuple[float | None, str, str, tuple[str, ...], tuple[str, ...]]] = {}
        visiting: list[str] = []

        def score(node: str, depth: int = 0):
            if node in memo:
                return memo[node]
            if depth >= self.max_depth:
                memo[node] = (None, "unknown", "max_depth", (), (node,))
                return memo[node]
            if node in visiting:
                cycle = tuple(visiting[visiting.index(node):] + [node])
                memo[node] = (None, "unknown", "dependency_cycle", (), cycle)
                return memo[node]
            if node in direct:
                value, state, reason, blockers = direct[node]
                unknowns = (node,) if state == "unknown" else ()
                memo[node] = (value, state, reason, blockers, unknowns)
                return memo[node]
            dependencies = tuple(sorted(set(edges.get(node, ()))))
            if not dependencies:
                memo[node] = (None, "unknown", "no_provider_or_dependency", (), (node,))
                return memo[node]
            visiting.append(node)
            records = [score(dep, depth + 1) for dep in dependencies]
            visiting.pop()
            blockers = tuple(sorted({item for record in records for item in record[3]}))
            unknowns = tuple(sorted({item for record in records for item in record[4]}))
            states = tuple(record[1] for record in records)
            known_values = [record[0] for record in records if record[0] is not None]
            if "unavailable" in states:
                state = "unavailable"
                value = 0.0
                reason = "dependency_unavailable"
            elif "unknown" in states:
                state = "unknown"
                value = None
                reason = "dependency_unknown"
            else:
                value = min(float(item) for item in known_values)
                state = "available" if value >= 0.8 else "degraded" if value > 0 else "unavailable"
                reason = "all_dependencies_observed"
            memo[node] = (value, state, reason, blockers, unknowns)
            return memo[node]

        output = []
        for capability in sorted(set(projection.get("capabilities", ()))):
            value, status, reason, blockers, unknowns = score(capability)
            dependency_nodes = tuple(sorted(set(edges.get(capability, ()))))
            dependency_records = {dep: score(dep) for dep in dependency_nodes}
            dependency_scores = {dep: record[0] for dep, record in dependency_records.items()}
            payload = (
                referent_ref,
                capability,
                value,
                status,
                dependency_scores,
                blockers,
                unknowns,
            )
            output.append(
                CapabilityAssessment(
                    stable("capability-assessment", payload),
                    referent_ref,
                    capability,
                    value,
                    status,
                    dependency_scores,
                    blockers,
                    {
                        "type_facet_closure": list(projection.get("type_facet_closure", ())),
                        "dependency_edges": list(projection.get("dependency_edges", ())),
                        "unknown_dependencies": list(unknowns),
                        "resolution_reason": reason,
                        "native_state_preserved": True,
                        "operational_snapshot_required": True,
                    },
                )
            )
        return tuple(output)
