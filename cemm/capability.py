"""Recursive operational-profile and capability evaluation."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping

from cemm.model import Fact, lit, stable


@dataclass(frozen=True)
class RuntimeObservation:
    target_ref: str
    score: float
    source: str
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self):
        return {
            "target_ref": self.target_ref,
            "score": self.score,
            "source": self.source,
            "evidence": dict(self.evidence),
        }


@dataclass(frozen=True)
class CapabilityAssessment:
    assessment_ref: str
    referent_ref: str
    capability_ref: str
    score: float
    status: str
    dependency_scores: Mapping[str, float]
    blockers: tuple[str, ...]
    proof: Mapping[str, Any]

    def as_dict(self):
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
    """Expose runtime facts as evidence scores, never as lexical labels."""

    @staticmethod
    def observe(view) -> tuple[RuntimeObservation, ...]:
        blockers = tuple(view.critical_blockers)
        return (
            RuntimeObservation("resource:runtime_process", 1.0 if view.process_available else 0.0, "runtime", {"process_available": view.process_available}),
            RuntimeObservation("resource:semantic_runtime", max(0.0, min(1.0, float(view.semantic_runtime_support))), "runtime"),
            RuntimeObservation("resource:language_realizer", max(0.0, min(1.0, float(view.language_realizer_support))), "runtime"),
            RuntimeObservation("resource:output_channel", 0.0 if blockers else 1.0, "runtime", {"blockers": list(blockers)}),
        )

    @staticmethod
    def semantic_facts(view):
        """Ephemeral exact facts for queries; never persisted as global self cognition."""
        values = (
            ("dim:runtime_process_support", 1.0 if view.process_available else 0.0),
            ("dim:semantic_runtime_support", max(0.0, min(1.0, float(view.semantic_runtime_support)))),
            ("dim:language_realizer_support", max(0.0, min(1.0, float(view.language_realizer_support)))),
            ("dim:critical_blocker_count", len(view.critical_blockers)),
        )
        return tuple(
            Fact(
                stable("runtime-state", view.self_ref, dimension, value, view.world_revision),
                "op:state",
                {"role:subject": view.self_ref, "role:dimension": dimension, "role:value": lit(value, "int" if isinstance(value, int) else "float")},
                "support",
                1.0,
                True,
                {"runtime_provider": True, "revision": view.world_revision},
            )
            for dimension, value in values
        )


class CapabilityEvaluator:
    """Evaluate dependency graphs without per-capability code branches."""

    def __init__(self, store, max_depth=12, unknown_score=0.0):
        self.s = store
        self.max_depth = int(max_depth)
        self.unknown_score = float(unknown_score)

    def _state_scores(self, projection):
        output = {}
        for item in projection.get("dimensions", ()):
            dimension_ref = item["dimension_ref"]
            status = item.get("status")
            values = item.get("values", ())
            score = self.unknown_score
            if status == "resolved" and values:
                value = values[0]
                if isinstance(value, dict) and "literal" in value:
                    raw = value["literal"].get("value")
                    atom = self.s.atom(dimension_ref)
                    metadata = json.loads(atom["metadata"]) if atom else {}
                    if isinstance(raw, (int, float)):
                        low, high = metadata.get("min", 0.0), metadata.get("max", 1.0)
                        score = 1.0 if high == low else (float(raw) - float(low)) / (float(high) - float(low))
                        if metadata.get("positive_direction") == "lower":
                            score = 1.0 - score
                elif isinstance(value, str):
                    atom = self.s.atom(value)
                    metadata = json.loads(atom["metadata"]) if atom else {}
                    if "support_score" in metadata:
                        score = float(metadata["support_score"])
            output[dimension_ref] = max(0.0, min(1.0, score))
        return output

    def evaluate(self, referent_ref, projection, runtime_observations=()):
        direct_scores = self._state_scores(projection)
        direct_scores.update({item.target_ref: max(0.0, min(1.0, item.score)) for item in runtime_observations})
        edges = {}
        for edge in projection.get("dependency_edges", ()):
            edges.setdefault(edge["subject"], []).append(edge["depends_on"])
        memo = {}
        visiting = set()

        def score(node, depth=0):
            if node in memo:
                return memo[node]
            if depth > self.max_depth or node in visiting:
                memo[node] = self.unknown_score
                return memo[node]
            if node in direct_scores:
                memo[node] = direct_scores[node]
                return memo[node]
            dependencies = sorted(set(edges.get(node, ())))
            if not dependencies:
                memo[node] = self.unknown_score
                return memo[node]
            visiting.add(node)
            values = [score(dep, depth + 1) for dep in dependencies]
            visiting.remove(node)
            memo[node] = min(values) if values else self.unknown_score
            return memo[node]

        output = []
        for capability in projection.get("capabilities", ()):
            value = score(capability)
            dependency_scores = {dep: score(dep) for dep in sorted(set(edges.get(capability, ())))}
            blockers = tuple(sorted(dep for dep, dep_score in dependency_scores.items() if dep_score < 0.5))
            status = "available" if value >= 0.8 else "degraded" if value > 0.0 else "unavailable"
            payload = (referent_ref, capability, value, dependency_scores, blockers)
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
                        "native_state_preserved": True,
                    },
                )
            )
        return tuple(output)
