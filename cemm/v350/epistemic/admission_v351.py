"""Explicit Phase-11 epistemic admission policy and Stage-9 coordinator."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..conversation.session_memory import SessionBeliefEntry
from ..csir.canonical_v351 import semantic_fingerprint
from ..csir.model import CSIRNodeKind, ExactAuthorityPin, QualifierKind, TermKind
from ..grounded.model import Claim, CorrectionKind, Proposition
from ..orchestration import StageExecutionStatus, StageOutcome
from ..runtime_abi import artifact_ref
from ..schema.model import semantic_fingerprint as runtime_fingerprint
from .model import (
    AdmissionAssessment, AdmissionClass, EpistemicDecision, EpistemicPlacement,
    WorkingBeliefDelta,
)


@dataclass(frozen=True, slots=True)
class EpistemicAdmissionPolicy:
    """Use-specific policy over exact predicates and structural participant grounding.

    Session participant facts are admitted only into the current context/permission scope;
    they never become global semantic authority or unqualified actual-world truth.
    """

    high_risk_definition_pins: tuple[ExactAuthorityPin, ...] = ()
    corroboration_required_definition_pins: tuple[ExactAuthorityPin, ...] = ()
    scoped_user_asserted_definition_pins: tuple[ExactAuthorityPin, ...] = ()
    non_admitting_context_values: tuple[str, ...] = (
        "hypothetical", "planned", "desired", "fictional", "quoted", "counterfactual"
    )

    def __post_init__(self) -> None:
        for pins, label in (
            (self.high_risk_definition_pins, "high risk"),
            (self.corroboration_required_definition_pins, "corroboration"),
            (self.scoped_user_asserted_definition_pins, "scoped user asserted"),
        ):
            if len({pin.key for pin in pins}) != len(pins):
                raise ValueError(f"{label} epistemic policy pins must be unique")

    @staticmethod
    def _predicate_keys(graph) -> set[tuple[str, str, str, int, str, str]]:
        return {item.predicate_pin.key for item in graph.applications}

    def _non_admitting_context(self, graph) -> bool:
        blocked = set(self.non_admitting_context_values)
        return any(
            qualifier.qualifier_kind is QualifierKind.CONTEXT
            and isinstance(qualifier.value_atom, str)
            and qualifier.value_atom in blocked
            for qualifier in graph.qualifiers
        )

    @staticmethod
    def _speaker_centered(graph, speaker_ref: str) -> bool:
        speaker_terms = {
            term.term_ref for term in graph.terms
            if term.term_kind is TermKind.REFERENT and term.identity_ref == speaker_ref
        }
        if not speaker_terms:
            return False
        for binding in graph.bindings:
            if any(
                filler.kind is CSIRNodeKind.TERM and filler.ref in speaker_terms
                for filler in binding.fillers
            ):
                return True
        return False

    def classify(self, claim: Claim, proposition: Proposition, *, permission_ref: str) -> tuple[AdmissionClass, EpistemicDecision, tuple[str, ...]]:
        predicates = self._predicate_keys(proposition.content)
        if self._non_admitting_context(proposition.content):
            return (
                AdmissionClass.HYPOTHETICAL_ONLY,
                EpistemicDecision.PRESERVE_ONLY,
                ("non_actual_context_isolation",),
            )
        if predicates.intersection(pin.key for pin in self.high_risk_definition_pins):
            return (
                AdmissionClass.HIGH_RISK_NO_AUTO_ADMISSION,
                EpistemicDecision.PRESERVE_ONLY,
                ("high_risk_requires_explicit_admission",),
            )
        if predicates.intersection(pin.key for pin in self.corroboration_required_definition_pins):
            return (
                AdmissionClass.CORROBORATION_REQUIRED,
                EpistemicDecision.PRESERVE_ONLY,
                ("independent_corroboration_required",),
            )
        if predicates.intersection(pin.key for pin in self.scoped_user_asserted_definition_pins):
            return (
                AdmissionClass.SCOPED_USER_ASSERTED_FACT,
                EpistemicDecision.ALLOW,
                ("explicit_scoped_user_asserted_policy",),
            )
        if self._speaker_centered(proposition.content, claim.claimant_ref):
            return (
                AdmissionClass.SESSION_PARTICIPANT_FACT,
                EpistemicDecision.ALLOW,
                ("transport_grounded_participant_centered_claim",),
            )
        return (
            AdmissionClass.ATTRIBUTED_ONLY,
            EpistemicDecision.PRESERVE_ONLY,
            ("claim_preserved_without_world_admission",),
        )


class EpistemicCoordinatorV351:
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "epistemic_coordinator"

    def __init__(self, session_memory, *, policy: EpistemicAdmissionPolicy | None = None) -> None:
        self.session_memory = session_memory
        self.policy = policy or EpistemicAdmissionPolicy()

    def place(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        del capability, store, effect_store, semantic_capabilities
        propositions = {item.proposition_ref: item for item in cycle.artifacts.get("propositions", ())}
        claims = tuple(cycle.artifacts.get("claims", ()))
        corrections = tuple(cycle.artifacts.get("corrections", ()))
        memory = self.session_memory.snapshot(cycle.context_ref, cycle.permission_ref)
        assessments = []
        additions = []
        attributed = []
        admitted = []
        preserved = []
        evidence = set()
        claim_by_proposition = {claim.proposition_ref: claim for claim in claims}

        for claim in claims:
            proposition = propositions.get(claim.proposition_ref)
            if proposition is None:
                continue
            klass, decision, reasons = self.policy.classify(
                claim, proposition, permission_ref=cycle.permission_ref
            )
            assessment_ref = "admission-assessment:" + runtime_fingerprint(
                "admission-assessment",
                (claim.claim_ref, klass.value, decision.value, cycle.context_ref, cycle.permission_ref),
                24,
            )
            proof_refs = (
                "proof:epistemic:source-context-permission-lineage",
                *tuple(proposition.source_refs),
            )
            assessment = AdmissionAssessment(
                assessment_ref=assessment_ref,
                claim_ref=claim.claim_ref,
                proposition_ref=claim.proposition_ref,
                admission_class=klass,
                decision=decision,
                source_ref=claim.claimant_ref,
                source_context_ref=claim.source_context_ref,
                target_context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref,
                evidence_refs=tuple(sorted(set(claim.evidence_refs))),
                proof_refs=tuple(sorted(set(proof_refs))),
                reason_refs=reasons,
            )
            assessments.append(assessment)
            evidence.update(claim.evidence_refs)
            if decision is EpistemicDecision.ALLOW:
                belief_ref = "session-belief:" + runtime_fingerprint(
                    "session-belief",
                    (
                        semantic_fingerprint(proposition.content), claim.claim_ref,
                        cycle.context_ref, cycle.permission_ref,
                    ),
                    32,
                )
                additions.append(
                    SessionBeliefEntry(
                        belief_ref=belief_ref,
                        proposition_ref=proposition.proposition_ref,
                        claim_ref=claim.claim_ref,
                        graph=proposition.content,
                        context_ref=cycle.context_ref,
                        permission_ref=cycle.permission_ref,
                        source_refs=(claim.claimant_ref,),
                        evidence_refs=tuple(sorted(set((*claim.evidence_refs, *proposition.evidence_refs)))),
                        proof_refs=tuple(sorted(set(proof_refs))),
                        confidence=claim.commitment_strength,
                        truth_status="supported",
                    )
                )
                admitted.append(claim.claim_ref)
            else:
                attributed.append(claim.claim_ref)
                if klass is AdmissionClass.HYPOTHETICAL_ONLY:
                    preserved.append(claim.proposition_ref)

        retracts = []
        supersede = []
        for correction in corrections:
            if correction.kind is CorrectionKind.RETRACT:
                retracts.append(correction.target_ref)
                continue
            replacement_claim = claim_by_proposition.get(correction.replacement_ref or "")
            if replacement_claim is None:
                continue
            supersede.append((correction.target_ref, replacement_claim.claim_ref))

        delta = WorkingBeliefDelta(
            delta_ref=artifact_ref(
                "working-belief-delta", cycle.cycle_ref,
                tuple(item.belief_ref for item in additions),
                tuple(sorted(retracts)), tuple(sorted(supersede)),
            ),
            context_ref=cycle.context_ref,
            permission_ref=cycle.permission_ref,
            base_session_revision=memory.revision,
            additions=tuple(additions),
            retract_claim_refs=tuple(sorted(set(retracts))),
            supersede_claims=tuple(sorted(set(supersede))),
            evidence_refs=tuple(sorted(evidence)),
        )
        placement = EpistemicPlacement(
            placement_ref=artifact_ref(
                "epistemic-placement", cycle.cycle_ref,
                tuple(item.assessment_ref for item in assessments),
            ),
            context_ref=cycle.context_ref,
            permission_ref=cycle.permission_ref,
            assessments=tuple(assessments),
            attributed_claim_refs=tuple(sorted(attributed)),
            admitted_claim_refs=tuple(sorted(admitted)),
            preserved_hypothesis_refs=tuple(sorted(preserved)),
            proof_refs=("proof:epistemic:explicit-admission-policy",),
        )
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts={
                "epistemic_placement": placement,
                "working_belief_delta": delta,
                "admission_decisions": tuple(assessments),
            },
        )


__all__ = ["EpistemicAdmissionPolicy", "EpistemicCoordinatorV351"]
