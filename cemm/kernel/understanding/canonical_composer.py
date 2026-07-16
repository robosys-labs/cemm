"""Canonical composer extensions for typed query ports and constant roles."""
from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from .candidate_graph import (
    CandidateCommunicativeForce,
    CandidatePredication,
    CandidateRule,
)
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
        propositions = {
            item.proposition.predication_ref: item.proposition.id
            for item in graph.candidate_propositions
        }
        forces = []
        for communicative in evidence.communicative_candidates:
            source = set(communicative.source_token_indices)
            candidates = [
                item for item in graph.candidate_predications
                if item.candidate_source != "rule_component"
                and source
                and set(item.source_token_indices) == source
            ]
            if not candidates:
                candidates = [
                    item for item in graph.candidate_predications
                    if item.candidate_source != "rule_component"
                    and source
                    and set(item.source_token_indices) <= source
                ]
            if not candidates:
                continue
            target = max(candidates, key=lambda item: item.confidence)
            forces.append(CandidateCommunicativeForce(
                force=communicative.force,
                target_proposition_ref=propositions.get(target.predication.id, ""),
                confidence=communicative.confidence,
            ))

        candidate_rules = []
        for index, rule in enumerate(evidence.rule_candidates):
            premise = tuple(
                item.predication.id
                for item in graph.candidate_predications
                if item.candidate_source == "rule_component"
                and set(item.source_token_indices)
                and set(item.source_token_indices) <= set(rule.premise_token_indices)
            )
            conclusion = tuple(
                item.predication.id
                for item in graph.candidate_predications
                if item.candidate_source == "rule_component"
                and set(item.source_token_indices)
                and set(item.source_token_indices) <= set(rule.conclusion_token_indices)
            )
            candidate_rules.append(CandidateRule(
                rule_id=f"candidate_rule:{index}:{rule.construction_key}",
                construction_ref=rule.construction_key,
                premise_predication_refs=tuple(dict.fromkeys(premise)),
                conclusion_predication_refs=tuple(dict.fromkeys(conclusion)),
                strength=rule.strength,
                causal_warrant=rule.causal_warrant,
                confidence=rule.confidence,
                source_token_indices=rule.source_token_indices,
            ))
        return replace(
            graph,
            candidate_communicative_forces=tuple(forces),
            candidate_rules=tuple(candidate_rules),
            open_ports=tuple(self._dedupe_ports(list(ports))),
        )

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
            candidate_source=(
                "rule_component"
                if getattr(construction, "metadata", {}).get("embedded_rule_ref")
                else "construction"
            ),
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
