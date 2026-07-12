"""Fail-closed semantic integrity checks at the UOL/contract boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .proposition_semantics import (
    can_materialize_domain_edge,
    is_internal_identifier,
    is_queried,
    is_role_placeholder,
    open_roles,
)

_DOMAIN_EDGE_TYPES = frozenset({
    "same_as", "is_a", "part_of", "used_for", "has_property",
    "causes", "enables", "prevents", "before", "after", "evaluates",
})


@dataclass(slots=True)
class IntegrityViolation:
    code: str
    message: str
    atom_ids: list[str] = field(default_factory=list)
    edge_ids: list[str] = field(default_factory=list)
    blocking: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "atom_ids": list(self.atom_ids),
            "edge_ids": list(self.edge_ids),
            "blocking": self.blocking,
        }


@dataclass(slots=True)
class IntegrityReport:
    violations: list[IntegrityViolation] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return any(item.blocking for item in self.violations)

    @property
    def valid(self) -> bool:
        return not self.blocked

    @property
    def errors(self) -> list[str]:
        return [item.message for item in self.violations if item.blocking]

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocked": self.blocked,
            "violations": [item.to_dict() for item in self.violations],
        }


class SemanticIntegrityValidator:
    def validate_graph(self, graph: Any) -> IntegrityReport:
        report = IntegrityReport()
        relation_atoms = {
            atom.id: atom for atom in graph.atoms.values()
            if getattr(atom, "kind", "") == "relation"
        }

        for atom in graph.atoms.values():
            if is_role_placeholder(atom):
                for resolution in getattr(graph, "concept_resolutions", []) or []:
                    if resolution.atom_id == atom.id and getattr(resolution, "concept_id", ""):
                        report.violations.append(IntegrityViolation(
                            code="role_placeholder_concept_resolution",
                            message="role metadata received a durable concept identity",
                            atom_ids=[atom.id],
                        ))

        for edge in graph.edges:
            if edge.edge_type not in _DOMAIN_EDGE_TYPES:
                continue
            source = graph.atoms.get(edge.source_id)
            target = graph.atoms.get(edge.target_id)
            if source is None or target is None:
                continue
            if is_role_placeholder(source) or is_role_placeholder(target):
                report.violations.append(IntegrityViolation(
                    code="role_placeholder_domain_edge",
                    message="typed domain edge contains role metadata as a semantic filler",
                    atom_ids=[source.id, target.id],
                    edge_ids=[edge.id],
                ))
            relation_atom_id = str((edge.features or {}).get("relation_atom_id", "") or "")
            relation_atom = relation_atoms.get(relation_atom_id)
            if relation_atom is not None and not can_materialize_domain_edge(relation_atom):
                report.violations.append(IntegrityViolation(
                    code="non_asserted_domain_edge",
                    message="queried/open proposition materialized as an asserted domain edge",
                    atom_ids=[relation_atom.id, source.id, target.id],
                    edge_ids=[edge.id],
                ))

        query_groups = {
            atom.group_id for atom in relation_atoms.values()
            if is_queried(atom) or open_roles(atom)
        }
        for observation in getattr(graph, "structural_observations", []) or []:
            if getattr(observation, "source_group_id", "") not in query_groups:
                continue
            if getattr(observation, "operation", "") in {
                "upsert_relation_candidate", "upsert_concept_candidate"
            }:
                report.violations.append(IntegrityViolation(
                    code="query_generated_durable_patch",
                    message="query group generated a durable semantic write candidate",
                ))

        graph.trace["semantic_integrity"] = report.to_dict()
        graph.trace["integrity_blocked"] = report.blocked
        return report

    @staticmethod
    def public_value_is_safe(value: str) -> bool:
        return bool(str(value or "").strip()) and not is_internal_identifier(value)
