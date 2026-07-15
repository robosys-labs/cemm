"""Proof-carrying emission environment from canonical cycle artifacts."""
from __future__ import annotations

from ..model.requirements import RequirementAssessment
from ..self_model.claim_authorizer import ClaimEvidence
from .emission_closure import EmissionEnvironment


class CanonicalCycleEmissionEnvironmentBuilder:
    def build(
        self,
        cycle,
        *,
        foundation_fingerprint: str,
        active_schema_refs: frozenset[str],
        passed_competence_case_refs: frozenset[str],
        passed_round_trip_case_refs: frozenset[str],
    ) -> EmissionEnvironment:
        claim_evidence = []
        grounding_refs = set()

        for graph in tuple(getattr(cycle, "grounded_candidates", ()) or ()):
            for predication in tuple(getattr(graph, "predications", ()) or ()):
                grounding_refs.add(predication.predication_ref)
                definition = getattr(predication, "definition", None)
                if definition is not None and definition.schema_record_ref:
                    grounding_refs.add(definition.schema_record_ref)
                for binding in predication.role_bindings:
                    if binding.grounded_filler_ref:
                        grounding_refs.add(binding.grounded_filler_ref)

        for result in tuple(getattr(cycle, "retrieval_results", ()) or ()):
            for fact in tuple(getattr(result, "records", ()) or ()):
                claim_evidence.append(ClaimEvidence(
                    evidence_id=f"retrieval:{fact.fact_id}",
                    evidence_kind="successful_retrieval",
                    subject_ref="self",
                    semantic_target_ref=fact.fact_id,
                    context_ref=fact.context_ref,
                    successful=True,
                    provenance_refs=tuple(fact.evidence_refs),
                ))
                grounding_refs.add(fact.fact_id)
            for record_ref in tuple(getattr(result, "record_refs", ()) or ()):
                claim_evidence.append(ClaimEvidence(
                    evidence_id=f"retrieval:{record_ref}",
                    evidence_kind="successful_retrieval",
                    subject_ref="self",
                    semantic_target_ref=record_ref,
                    context_ref=getattr(cycle.trigger, "context_id", ""),
                    successful=not bool(getattr(result, "is_empty", True)),
                    provenance_refs=tuple(
                        getattr(result, "evidence_refs", ()) or ()
                    ),
                ))

        for assessment in tuple(
            getattr(cycle, "capability_assessments", ()) or ()
        ):
            claim_evidence.append(ClaimEvidence(
                evidence_id=assessment.assessment_id,
                evidence_kind="live_capability_assessment",
                subject_ref=assessment.subject_ref,
                semantic_target_ref=assessment.operation_schema_ref,
                context_ref=assessment.context_ref,
                successful=assessment.is_capable,
                revision_fingerprint=assessment.environment_fingerprint,
                provenance_refs=tuple(assessment.evidence_refs),
            ))

        commit = getattr(cycle, "critical_commit", None)
        if commit is not None:
            for result in tuple(getattr(commit, "results", ()) or ()):
                for record_ref in tuple(getattr(result, "record_refs", ()) or ()):
                    claim_evidence.append(ClaimEvidence(
                        evidence_id=f"commit:{record_ref}",
                        evidence_kind="commit_outcome",
                        subject_ref="self",
                        semantic_target_ref=record_ref,
                        context_ref=getattr(cycle.trigger, "context_id", ""),
                        successful=getattr(result, "status", "") == "committed",
                        provenance_refs=(
                            getattr(commit, "mutation_set_ref", ""),
                        ),
                    ))

        requirement_assessments = tuple(
            item
            for item in tuple(
                getattr(cycle, "requirement_assessments", ()) or ()
            )
            if isinstance(item, RequirementAssessment)
        )
        snapshot = cycle.snapshot
        return EmissionEnvironment(
            environment_fingerprint=(
                f"foundation={foundation_fingerprint};"
                f"schema={snapshot.schema_store_revision};"
                f"memory={snapshot.semantic_memory_revision}"
            ),
            grounding_refs=frozenset(grounding_refs),
            active_schema_refs=active_schema_refs,
            passed_competence_case_refs=passed_competence_case_refs,
            passed_round_trip_case_refs=passed_round_trip_case_refs,
            claim_evidence=tuple(claim_evidence),
            requirement_assessments=requirement_assessments,
        )
