"""Canonical composer extensions for typed query ports and constant roles."""
from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from .candidate_graph import CandidatePredication
from .composer import SemanticComposer
from ..model.predication import Predication
from ..model.role_binding import OpenPort, RoleBinding


class CanonicalSemanticComposer(SemanticComposer):
    """Preserve every open role and distinguish query ports from missing data."""

    def compose(self, evidence):
        graph = super().compose(evidence)
        ports = tuple(
            port
            for candidate in graph.candidate_predications
            for port in candidate.predication.open_ports
        )
        return replace(graph, open_ports=tuple(self._dedupe_ports(list(ports))))

    def _construction_predication(self, construction):
        predicate_ref = self._resolve_predicate_ref(
            construction.predicate_schema_ref
        )
        bindings: list[RoleBinding] = [
            RoleBinding(
                role_schema_ref=self._role_ref(role_key),
                filler_ref=f"ref:token:{token_index}",
                confidence=construction.confidence,
            )
            for role_key, token_index in construction.role_mappings.items()
            if isinstance(token_index, int) and token_index >= 0
        ]
        constant_roles = dict(
            getattr(construction, "metadata", {}).get("constant_roles", {})
        )
        bound_roles = {binding.role_schema_ref for binding in bindings}
        for role_key, filler_ref in constant_roles.items():
            role_ref = self._role_ref(str(role_key))
            if role_ref in bound_roles:
                continue
            bindings.append(RoleBinding(
                role_schema_ref=role_ref,
                filler_ref=str(filler_ref),
                confidence=construction.confidence,
                evidence_refs=(construction.construction_key,),
            ))
            bound_roles.add(role_ref)

        query = construction.communicative_force in {"ask", "query"}
        ports = tuple(
            OpenPort(
                role_schema_ref=self._role_ref(role_ref),
                required=not query,
                cardinality="one",
            )
            for role_ref in construction.open_role_refs
            if self._role_ref(role_ref) not in bound_roles
        )
        predication = Predication(
            id=f"pred:{uuid4().hex[:12]}",
            predicate_schema_ref=predicate_ref,
            bindings=tuple(bindings),
            open_ports=ports,
            source_span_refs=tuple(
                f"span:{index}" for index in construction.source_token_indices
            ),
            confidence=construction.confidence,
        )
        return CandidatePredication(
            predication=predication,
            candidate_source="construction",
            confidence=construction.confidence,
            source_token_indices=construction.source_token_indices,
        )

    @staticmethod
    def _is_grammatical_key(key: str) -> bool:
        return key.startswith((
            "grammar:",
            "pronoun:",
            "wh:",
            "aux:",
            "determiner:",
            "polarity:",
            "discourse:",
        ))

    @staticmethod
    def _open_port_for(construction):
        # All ports are attached atomically by _construction_predication.
        return None

    @staticmethod
    def _role_ref(role_key: str) -> str:
        return role_key if role_key.startswith("role:") else f"role:{role_key}"
