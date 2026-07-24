"""Canonical runtime bridge for epistemic admission and admitted event projection.

Policies remain external/versioned data or signed services.  This module owns only
mechanics: validate policy proposals, run the existing independent admission
engine, project admitted proposition knowledge, and re-instantiate admitted event
applications into the target context without mutating the source-attributed graph.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol, Iterable

from .epistemics.admission import EpistemicAdmissionEngine
from .epistemics.model import AdmissionPolicy, AdmissionRequest
from .epistemics.truth import FourStateTruthProjector
from .learning.model import PinnedRecord
from .schema.model import PortFillerClass, semantic_fingerprint
from .storage import (
    AdmissionDecision,
    GraphPatch,
    PatchOperation,
    PatchOperationKind,
    RecordDependency,
    RecordKind,
    encode_record,
    record_fingerprints,
)
from .uol.model import (
    EventOccurrence,
    FillerRef,
    SemanticApplication,
)


@dataclass(frozen=True, slots=True)
class EpistemicAdmissionProposal:
    request: AdmissionRequest
    policy: AdmissionPolicy

    def __post_init__(self) -> None:
        if self.request.policy_ref != self.policy.policy_ref:
            raise ValueError("epistemic admission proposal policy identity mismatch")


class EpistemicPolicyProvider(Protocol):
    provider_ref: str
    provider_revision: str

    def proposals(
        self,
        *,
        attributed_claims: tuple[object, ...],
        context_ref: str,
        permission_ref: str,
        store,
    ) -> tuple[EpistemicAdmissionProposal, ...]: ...


@dataclass(frozen=True, slots=True)
class PreparedAdmission:
    proposal: EpistemicAdmissionProposal
    assessment: object
    admission: object
    source_assessments: tuple[object, ...]
    knowledge: object | None


class RuntimeEpistemicCoordinator:
    def __init__(self, store) -> None:
        self.store = store
        self.engine = EpistemicAdmissionEngine()
        self.truth = FourStateTruthProjector()

    def prepare(
        self,
        proposals: Iterable[EpistemicAdmissionProposal],
        *,
        allowed_proposition_refs: set[str],
    ) -> tuple[PreparedAdmission, ...]:
        result: list[PreparedAdmission] = []
        for proposal in proposals:
            request = proposal.request
            if request.proposition_ref not in allowed_proposition_refs:
                raise ValueError(
                    "epistemic policy provider proposed admission outside current claim lineage"
                )
            assessment = self.engine.assess(request, proposal.policy)
            admission = self.engine.record(request, assessment)
            source_records = self.engine.source_assessment_records(request)

            existing = tuple(
                item.payload
                for item in self.store.repositories.epistemic_admissions.all(
                    all_revisions=True
                )
                if item.payload.proposition_ref == request.proposition_ref
                and item.payload.target_context_ref == request.target_context_ref
                and not self.store.is_invalidated(
                    item.record_kind, item.record_ref, item.revision
                )
            )
            projected_admissions = (
                (*existing, admission)
                if assessment.decision
                in {
                    AdmissionDecision.ADMIT_SUPPORT,
                    AdmissionDecision.ADMIT_OPPOSITION,
                }
                else existing
            )
            truth = self.truth.assess(
                request.proposition_ref,
                request.target_context_ref,
                tuple(projected_admissions),
            )
            projection = self.truth.project_knowledge(
                truth,
                tuple(projected_admissions),
                permission_ref=request.permission_ref,
                sensitivity=request.sensitivity,
            )
            knowledge = projection.knowledge_record
            result.append(
                PreparedAdmission(
                    proposal,
                    assessment,
                    admission,
                    source_records
                    if assessment.decision
                    in {
                        AdmissionDecision.ADMIT_SUPPORT,
                        AdmissionDecision.ADMIT_OPPOSITION,
                    }
                    else (),
                    knowledge,
                )
            )
        return tuple(result)


class AdmittedEventProjector:
    """Project event applications through an explicit epistemic context bridge."""

    def __init__(self, store) -> None:
        self.store = store

    def patches_for_admission(self, admission) -> tuple[tuple[GraphPatch, EventOccurrence], ...]:
        if admission.decision != AdmissionDecision.ADMIT_SUPPORT:
            return ()
        proposition = self.store.get_record(RecordKind.PROPOSITION, admission.proposition_ref)
        if proposition is None:
            raise ValueError("admitted proposition is not durable")
        results: list[tuple[GraphPatch, EventOccurrence]] = []
        for content in proposition.payload.content_refs:
            if (
                not isinstance(content, FillerRef)
                or content.filler_class != PortFillerClass.SEMANTIC_APPLICATION
            ):
                continue
            source_app = self.store.get_record(
                RecordKind.SEMANTIC_APPLICATION, content.ref
            )
            if source_app is None:
                continue
            events = tuple(
                item
                for item in self.store.records(RecordKind.EVENT_OCCURRENCE)
                if item.payload.participant_application_ref == source_app.record_ref
                and item.payload.context_ref == admission.source_context_ref
                and not self.store.is_invalidated(
                    item.record_kind, item.record_ref, item.revision
                )
            )
            for source_event in events:
                results.append(
                    self._project_event(
                        source_event,
                        source_app,
                        admission,
                    )
                )
        return tuple(results)

    def _project_event(self, source_event, source_app, admission):
        target_app_ref = "admitted-application:" + semantic_fingerprint(
            "admitted-context-application",
            (
                source_app.record_ref,
                source_app.revision,
                source_app.record_fingerprint,
                admission.admission_ref,
                admission.target_context_ref,
            ),
            32,
        )
        target_app = replace(
            source_app.payload,
            application_ref=target_app_ref,
            context_ref=admission.target_context_ref,
            evidence_refs=tuple(
                sorted(
                    set(
                        (
                            *source_app.payload.evidence_refs,
                            *admission.evidence_refs,
                            admission.admission_ref,
                        )
                    )
                )
            ),
        )
        # A nested semantic application needs an explicit recursive context bridge;
        # do not silently retain a source-context nested application.
        for binding in target_app.bindings:
            for filler in binding.fillers:
                if (
                    isinstance(filler, FillerRef)
                    and filler.filler_class == PortFillerClass.SEMANTIC_APPLICATION
                ):
                    raise ValueError(
                        "nested admitted event application requires explicit recursive context projection"
                    )

        target_event_ref = "admitted-event:" + semantic_fingerprint(
            "admitted-context-event",
            (
                source_event.record_ref,
                source_event.revision,
                admission.admission_ref,
                admission.target_context_ref,
                target_app_ref,
            ),
            32,
        )
        target_referent = replace(
            source_event.payload.referent,
            referent_ref=target_event_ref,
            context_refs=tuple(
                sorted(
                    set(
                        (
                            *source_event.payload.referent.context_refs,
                            admission.target_context_ref,
                        )
                    )
                )
            ),
            provenance_refs=tuple(
                sorted(
                    set(
                        (
                            *source_event.payload.referent.provenance_refs,
                            source_event.record_ref,
                            admission.admission_ref,
                        )
                    )
                )
            ),
        )
        target_event = replace(
            source_event.payload,
            referent=target_referent,
            participant_application_ref=target_app_ref,
            context_ref=admission.target_context_ref,
            admission_refs=tuple(
                sorted(set((*source_event.payload.admission_refs, admission.admission_ref)))
            ),
            provenance_refs=tuple(
                sorted(
                    set(
                        (
                            *source_event.payload.provenance_refs,
                            source_event.record_ref,
                            admission.admission_ref,
                        )
                    )
                )
            ),
        )

        app_fp = record_fingerprints(RecordKind.SEMANTIC_APPLICATION, target_app)[1]
        ref_fp = record_fingerprints(RecordKind.REFERENT, target_referent)[1]
        admission_stored = self.store.get_record(
            RecordKind.EPISTEMIC_ADMISSION,
            admission.admission_ref,
            admission.revision,
        )
        if admission_stored is None:
            raise ValueError("admission must be durable before event projection")
        admission_dep = RecordDependency(
            RecordKind.EPISTEMIC_ADMISSION,
            admission_stored.record_ref,
            admission_stored.revision,
            admission_stored.record_fingerprint,
            "event_epistemic_admission",
        )
        operations = (
            PatchOperation(
                operation_ref="patch-operation:admitted-event-app:"
                + semantic_fingerprint(
                    "admitted-event-app-op", (target_app_ref, admission.admission_ref), 20
                ),
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=RecordKind.SEMANTIC_APPLICATION,
                target_ref=target_app_ref,
                record_revision=1,
                payload=encode_record(RecordKind.SEMANTIC_APPLICATION, target_app),
                dependencies=(
                    RecordDependency(
                        source_app.record_kind,
                        source_app.record_ref,
                        source_app.revision,
                        source_app.record_fingerprint,
                        "source_attributed_application",
                    ),
                    admission_dep,
                ),
                reason="project exact admitted event application into target context",
            ),
            PatchOperation(
                operation_ref="patch-operation:admitted-event-ref:"
                + semantic_fingerprint(
                    "admitted-event-ref-op", (target_event_ref, admission.admission_ref), 20
                ),
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=RecordKind.REFERENT,
                target_ref=target_event_ref,
                record_revision=target_referent.revision,
                payload=encode_record(RecordKind.REFERENT, target_referent),
                dependencies=(admission_dep,),
                reason="persist target-context admitted event identity",
            ),
            PatchOperation(
                operation_ref="patch-operation:admitted-event:"
                + semantic_fingerprint(
                    "admitted-event-op", (target_event_ref, admission.admission_ref), 20
                ),
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=RecordKind.EVENT_OCCURRENCE,
                target_ref=target_event_ref,
                record_revision=1,
                payload=encode_record(RecordKind.EVENT_OCCURRENCE, target_event),
                dependencies=(
                    RecordDependency(
                        RecordKind.SEMANTIC_APPLICATION,
                        target_app_ref,
                        1,
                        app_fp,
                        "event_participants",
                    ),
                    RecordDependency(
                        RecordKind.REFERENT,
                        target_event_ref,
                        target_referent.revision,
                        ref_fp,
                        "event_identity",
                    ),
                    admission_dep,
                ),
                reason="persist admitted target-context event without rewriting source claim",
            ),
        )
        with self.store.snapshot() as snapshot:
            patch = GraphPatch(
                patch_ref="graph-patch:admitted-event:"
                + semantic_fingerprint(
                    "admitted-event-patch",
                    (target_event_ref, admission.admission_ref, snapshot.fingerprint),
                    24,
                ),
                context_ref=admission.target_context_ref,
                scope_ref="epistemic:admitted-event",
                source_ref=admission.admission_ref,
                permission_ref=admission.permission_ref,
                operations=operations,
                expected_store_revision=snapshot.store_revision,
                evidence_refs=admission.evidence_refs,
                validation_requirements=(
                    "event_context_bridge_requires_epistemic_admission",
                    "source_attributed_event_remains_immutable",
                ),
                metadata={
                    "source_event_ref": source_event.record_ref,
                    "admission_ref": admission.admission_ref,
                },
            )
        return patch, target_event
