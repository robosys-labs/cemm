"""Build emission evidence from a completed cognitive cycle."""
from __future__ import annotations

from ..model.requirements import RequirementAssessment
from ..self_model.claim_authorizer import ClaimEvidence
from .emission_closure import EmissionEnvironment


def build_emission_environment(
    plan,
    pack,
    environment_fingerprint: str = "",
) -> EmissionEnvironment:
    return EmissionEnvironment(
        environment_fingerprint=environment_fingerprint or "simple",
        grounding_refs=frozenset(),
        active_schema_refs=frozenset(),
        passed_competence_case_refs=frozenset(),
        passed_round_trip_case_refs=frozenset(),
        claim_evidence=(),
        requirement_assessments=(),
    )


class CycleEmissionEnvironmentBuilder:
    def build(
        self,
        cycle,
        *,
        foundation_fingerprint: str,
        active_schema_refs: frozenset[str],
        passed_competence_case_refs: frozenset[str],
        passed_round_trip_case_refs: frozenset[str],
    ) -> EmissionEnvironment:
        claim_evidence: list[ClaimEvidence] = []

        for result in tuple(getattr(cycle, "retrieval_results", ()) or ()):
            for record_ref in tuple(getattr(result, "record_refs", ()) or ()):
                claim_evidence.append(
                    ClaimEvidence(
                        evidence_id=f"retrieval:{record_ref}",
                        evidence_kind="successful_retrieval",
                        subject_ref="self",
                        semantic_target_ref=record_ref,
                        context_ref=getattr(
                            getattr(cycle, "trigger", None),
                            "context_id",
                            "",
                        ),
                        successful=not bool(getattr(result, "is_empty", True)),
                        provenance_refs=tuple(
                            getattr(result, "evidence_refs", ()) or ()
                        ),
                    )
                )

        for assessment in tuple(
            getattr(cycle, "capability_assessments", ()) or ()
        ):
            claim_evidence.append(
                ClaimEvidence(
                    evidence_id=getattr(assessment, "assessment_id", "")
                    or getattr(assessment, "id", ""),
                    evidence_kind="live_capability_assessment",
                    subject_ref="self",
                    semantic_target_ref=getattr(
                        assessment, "operation_ref", ""
                    ),
                    context_ref=getattr(assessment, "context_ref", ""),
                    successful=bool(
                        getattr(assessment, "is_capable", False)
                        or getattr(assessment, "available", False)
                    ),
                    revision_fingerprint=getattr(
                        assessment,
                        "environment_fingerprint",
                        "",
                    ),
                )
            )

        commit = getattr(cycle, "critical_commit", None)
        if commit is not None:
            for result in tuple(getattr(commit, "results", ()) or ()):
                for record_ref in tuple(getattr(result, "record_refs", ()) or ()):
                    claim_evidence.append(
                        ClaimEvidence(
                            evidence_id=f"commit:{record_ref}",
                            evidence_kind="commit_outcome",
                            subject_ref="self",
                            semantic_target_ref=record_ref,
                            context_ref=getattr(
                                getattr(cycle, "trigger", None),
                                "context_id",
                                "",
                            ),
                            successful=(
                                getattr(result, "status", "") == "committed"
                            ),
                            provenance_refs=(
                                getattr(commit, "mutation_set_ref", ""),
                            ),
                        )
                    )

        for transaction in tuple(
            getattr(cycle, "learning_transactions", ()) or ()
        ):
            claim_evidence.append(
                ClaimEvidence(
                    evidence_id=getattr(transaction, "id", ""),
                    evidence_kind="learning_commit_and_replay",
                    subject_ref="self",
                    semantic_target_ref=getattr(
                        transaction, "target_schema_ref", ""
                    ),
                    context_ref=next(
                        iter(getattr(transaction, "context_refs", ()) or ()),
                        "",
                    ),
                    successful=(
                        getattr(transaction, "status", "") == "committed"
                        and getattr(transaction, "replay_status", "")
                        in {"passed", "completed"}
                    ),
                    provenance_refs=tuple(
                        getattr(transaction, "acquired_evidence_refs", ()) or ()
                    ),
                )
            )

        requirement_assessments = tuple(
            item
            for item in tuple(
                getattr(cycle, "requirement_assessments", ()) or ()
            )
            if isinstance(item, RequirementAssessment)
        )

        snapshot = getattr(cycle, "snapshot", None)
        environment_fingerprint = (
            f"foundation={foundation_fingerprint};"
            f"schema={getattr(snapshot, 'schema_store_revision', '')};"
            f"memory={getattr(snapshot, 'semantic_memory_revision', '')}"
        )
        return EmissionEnvironment(
            environment_fingerprint=environment_fingerprint,
            grounding_refs=frozenset(
                ref
                for graph in tuple(
                    getattr(cycle, "grounded_candidates", ()) or ()
                )
                for assessment in tuple(
                    getattr(graph, "predication_assessments", ()) or ()
                )
                for ref in tuple(
                    getattr(assessment, "grounding_evidence_refs", ()) or ()
                )
            ),
            active_schema_refs=active_schema_refs,
            passed_competence_case_refs=passed_competence_case_refs,
            passed_round_trip_case_refs=passed_round_trip_case_refs,
            claim_evidence=tuple(claim_evidence),
            requirement_assessments=requirement_assessments,
        )
