"""Compile fully grounded conditional candidates into typed provisional rules.

A single teaching utterance can establish structure, not independent competence.
Consequently these rules are registered as session-scoped provisional revisions
with non-empty atoms and remain disabled until an independent validation path
activates them.  This preserves teachability without self-certification.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

from ..model.identity import Permission, PermissionScope, Provenance, RetentionPolicy, Scope, ScopeLevel
from ..schema.envelope import SchemaEnvelope
from ..schema.rule import (
    CausalWarrant,
    CycleClass,
    RuleAtom,
    RuleKind,
    RuleSchema,
    RuleStrength,
)


@dataclass(frozen=True, slots=True)
class GroundedRuleLearningResult:
    candidate_ref: str
    rule_schema_ref: str = ""
    status: str = "blocked"
    premise_predication_refs: tuple[str, ...] = ()
    conclusion_predication_refs: tuple[str, ...] = ()
    blocker_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


class GroundedRuleLearner:
    def __init__(self, schema_store) -> None:
        self._store = schema_store

    def learn_cycle(self, cycle) -> tuple[GroundedRuleLearningResult, ...]:
        results = []
        for graph_index, graph in enumerate(
            tuple(getattr(cycle, "meaning_candidates", ()) or ())
        ):
            grounding = (
                cycle.grounded_candidates[graph_index]
                if graph_index < len(cycle.grounded_candidates)
                else None
            )
            for candidate in tuple(getattr(graph, "candidate_rules", ()) or ()):
                results.append(self._learn_candidate(
                    candidate,
                    graph,
                    grounding,
                    context_id=cycle.trigger.context_id,
                    cycle_id=cycle.cycle_id,
                ))
        return tuple(results)

    def _learn_candidate(
        self,
        candidate,
        graph,
        grounding,
        *,
        context_id: str,
        cycle_id: str,
    ) -> GroundedRuleLearningResult:
        blockers = []
        if grounding is None:
            blockers.append("missing_graph_grounding")
        if not candidate.premise_predication_refs:
            blockers.append("missing_grounded_premise")
        if not candidate.conclusion_predication_refs:
            blockers.append("missing_grounded_conclusion")
        if blockers:
            return GroundedRuleLearningResult(
                candidate_ref=candidate.rule_id,
                premise_predication_refs=candidate.premise_predication_refs,
                conclusion_predication_refs=candidate.conclusion_predication_refs,
                blocker_refs=tuple(blockers),
            )

        ordered_refs = (
            *candidate.premise_predication_refs,
            *candidate.conclusion_predication_refs,
        )
        grounded = []
        for predication_ref in ordered_refs:
            item = grounding.for_predication(predication_ref)
            if item is None:
                blockers.append(f"ungrounded:{predication_ref}")
                continue
            if item.unresolved_role_refs:
                blockers.append(f"open_roles:{predication_ref}")
            if item.opaque_role_refs:
                blockers.append(f"opaque_roles:{predication_ref}")
            grounded.append(item)
        if blockers:
            return GroundedRuleLearningResult(
                candidate_ref=candidate.rule_id,
                premise_predication_refs=candidate.premise_predication_refs,
                conclusion_predication_refs=candidate.conclusion_predication_refs,
                blocker_refs=tuple(blockers),
            )

        variable_map = self._variable_map(grounded)
        atoms = {
            item.predication_ref: self._atom(item, variable_map)
            for item in grounded
        }
        premise_atoms = tuple(
            atoms[ref] for ref in candidate.premise_predication_refs
        )
        conclusion_atoms = tuple(
            atoms[ref] for ref in candidate.conclusion_predication_refs
        )
        digest = hashlib.sha256(repr((premise_atoms, conclusion_atoms)).encode()).hexdigest()[:16]
        semantic_key = f"learned_rule:{digest}"
        existing = self._store.find_candidates(semantic_key)
        if existing:
            envelope = max(existing, key=lambda item: item.version)
            return GroundedRuleLearningResult(
                candidate_ref=candidate.rule_id,
                rule_schema_ref=envelope.record_id,
                status=envelope.status,
                premise_predication_refs=candidate.premise_predication_refs,
                conclusion_predication_refs=candidate.conclusion_predication_refs,
                evidence_refs=(cycle_id, candidate.construction_ref),
            )

        strength_value = str(candidate.strength or "defeasible")
        strength = RuleStrength(
            strength_value if strength_value in {item.value for item in RuleStrength}
            else RuleStrength.DEFEASIBLE.value
        )
        warrant_value = str(candidate.causal_warrant or "reported_claim")
        warrant = CausalWarrant(
            warrant_value if warrant_value in {item.value for item in CausalWarrant}
            else CausalWarrant.REPORTED_CLAIM.value
        )
        rule = RuleSchema(
            semantic_key=semantic_key,
            premises=premise_atoms,
            conclusions=conclusion_atoms,
            rule_kind=(
                RuleKind.CAUSAL
                if warrant is not CausalWarrant.NONE
                else RuleKind.RELATIONAL
            ),
            strength=strength,
            confidence=float(candidate.confidence),
            causal_warrant=warrant,
            cycle_class=(
                CycleClass.POSITIVE_MONOTONE
                if strength is RuleStrength.STRICT
                else CycleClass.STRATIFIED_DEFEASIBLE
            ),
            sensitivity="ordinary",
            enabled_by_default=False,
            max_firings_per_cycle=16,
            provenance_refs=(cycle_id, candidate.construction_ref),
        )
        envelope = SchemaEnvelope(
            record_id=f"learned:rule:{digest}:v1",
            semantic_key=semantic_key,
            schema_kind="rule",
            status="candidate",
            scope=Scope(level=ScopeLevel.SESSION, session_id=context_id),
            version=1,
            payload=rule,
            confidence=float(candidate.confidence),
            permission=Permission(
                scope=PermissionScope.SESSION_PRIVATE,
                may_store=True,
                may_retrieve=True,
                may_use=True,
                may_share=False,
                may_execute=False,
                retention=RetentionPolicy.SESSION,
            ),
            provenance=Provenance(
                source_id=cycle_id,
                source_kind="user_teaching",
            ),
            support_refs=(candidate.construction_ref,),
        )
        self._store.register(envelope)
        revision = self._store.get_revision(envelope.record_id)
        transition = self._store.transition_to_provisional(
            envelope.record_id,
            revision,
        )
        status = (
            "provisional"
            if getattr(transition.status, "value", transition.status) == "success"
            else "candidate"
        )
        return GroundedRuleLearningResult(
            candidate_ref=candidate.rule_id,
            rule_schema_ref=envelope.record_id,
            status=status,
            premise_predication_refs=candidate.premise_predication_refs,
            conclusion_predication_refs=candidate.conclusion_predication_refs,
            evidence_refs=(cycle_id, candidate.construction_ref),
            blocker_refs=("independent_competence_required",),
        )

    @staticmethod
    def _variable_map(grounded_items) -> dict[str, str]:
        candidates: list[str] = []
        for item in grounded_items:
            for binding in item.role_bindings:
                grounding = binding.grounding
                kind = getattr(grounding, "referent_kind", "") if grounding else ""
                filler = binding.grounded_filler_ref
                if filler in {"user", "self"} or kind in {
                    "discourse_participant",
                    "entity_anchor",
                }:
                    candidates.append(filler)
        return {
            filler: f"$v{index + 1}"
            for index, filler in enumerate(dict.fromkeys(candidates))
        }

    @staticmethod
    def _atom(item, variable_map: dict[str, str]) -> RuleAtom:
        roles = {}
        for binding in item.role_bindings:
            role_key = binding.role_schema_ref.removeprefix("role:")
            filler = binding.grounded_filler_ref
            roles[role_key] = variable_map.get(filler, filler)
        return RuleAtom(
            predicate_key=item.predicate_semantic_key,
            roles=roles,
            polarity="positive",
            context_ref="$context",
        )
