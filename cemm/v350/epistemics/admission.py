"""Independent actual-world epistemic admission policy."""
from __future__ import annotations

from math import prod

from ..schema.model import semantic_fingerprint
from ..storage import (
    AdmissionDecision, EpistemicAdmissionRecord, KnowledgeStatus, SourceAssessmentRecord,
)
from .model import AdmissionAssessment, AdmissionPolicy, AdmissionRequest


class EpistemicAdmissionEngine:
    """Assess whether attributed proposition evidence may enter a target context.

    The default outcome is preservation/deferment. Grammar, one source, or one
    confidence number can never silently authorize admission.
    """

    def assess(self, request: AdmissionRequest, policy: AdmissionPolicy) -> AdmissionAssessment:
        if request.policy_ref != policy.policy_ref:
            raise ValueError("admission request pins a different policy")
        thresholds = policy.thresholds_for(request.sensitivity)
        satisfied: list[str] = []
        failed: list[str] = []
        if not policy.require_explicit_authorization or request.authorization_ref:
            satisfied.append("explicit_authorization")
        else:
            failed.append("explicit_authorization")
        if request.proof_refs:
            satisfied.append("proof_present")
        else:
            failed.append("proof_present")
        independent_sources = len(set(request.source_refs))
        if independent_sources >= thresholds.minimum_independent_sources:
            satisfied.append("independent_sources")
        else:
            failed.append("independent_sources")
        evidence_values = tuple(value for _ref, value in request.evidence_confidences)
        if evidence_values and min(evidence_values) >= thresholds.minimum_evidence_confidence:
            satisfied.append("evidence_confidence")
        else:
            failed.append("evidence_confidence")
        assessments = {item.source_ref: item for item in request.source_assessments}
        source_dimensions_ok = bool(request.source_refs)
        for source_ref in request.source_refs:
            item = assessments.get(source_ref)
            if item is None or not (
                item.authority >= thresholds.minimum_authority
                and item.reliability >= thresholds.minimum_reliability
                and item.access_quality >= thresholds.minimum_access_quality
                and item.bias_risk <= thresholds.maximum_bias_risk
            ):
                source_dimensions_ok = False
        if source_dimensions_ok:
            satisfied.append("source_dimensions")
        else:
            failed.append("source_dimensions")
        if failed:
            decision = AdmissionDecision.PRESERVE_ATTRIBUTED if "explicit_authorization" in failed else AdmissionDecision.DEFER
            truth = KnowledgeStatus.UNDETERMINED
            confidence = 0.0
        else:
            decision = (
                AdmissionDecision.ADMIT_SUPPORT
                if request.requested_truth_status == KnowledgeStatus.SUPPORTED
                else AdmissionDecision.ADMIT_OPPOSITION
            )
            truth = request.requested_truth_status
            evidence_confidence = 1.0 - prod(1.0 - value for value in evidence_values)
            source_floor = min(
                min(assessments[ref].authority, assessments[ref].reliability, assessments[ref].access_quality, 1.0 - assessments[ref].bias_risk)
                for ref in request.source_refs
            )
            confidence = min(evidence_confidence, source_floor)
        return AdmissionAssessment(
            request_ref=request.request_ref,
            decision=decision,
            truth_status=truth,
            confidence=confidence,
            satisfied_requirements=tuple(sorted(satisfied)),
            failed_requirements=tuple(sorted(failed)),
            evidence_refs=tuple(ref for ref, _ in request.evidence_confidences),
            metadata={"policy_ref": policy.policy_ref, "authorization_ref": request.authorization_ref},
        )


    def source_assessment_records(self, request: AdmissionRequest) -> tuple[SourceAssessmentRecord, ...]:
        records = []
        for assessment in sorted(request.source_assessments, key=lambda item: item.source_ref):
            records.append(SourceAssessmentRecord(
                assessment_ref="source-assessment:" + semantic_fingerprint(
                    "source-assessment-ref",
                    (
                        request.request_ref, request.source_context_ref, assessment.source_ref,
                        assessment.authority, assessment.reliability, assessment.access_quality,
                        assessment.bias_risk, assessment.evidence_refs, dict(assessment.metadata),
                    ),
                    32,
                ),
                source_ref=assessment.source_ref,
                authority=assessment.authority,
                reliability=assessment.reliability,
                access_quality=assessment.access_quality,
                bias_risk=assessment.bias_risk,
                context_ref=request.source_context_ref,
                evidence_refs=assessment.evidence_refs,
                permission_ref=request.permission_ref,
                metadata={**dict(assessment.metadata), "admission_request_ref": request.request_ref},
            ))
        return tuple(records)

    def record(self, request: AdmissionRequest, assessment: AdmissionAssessment) -> EpistemicAdmissionRecord:
        return EpistemicAdmissionRecord(
            admission_ref="epistemic-admission:" + semantic_fingerprint(
                "epistemic-admission-ref",
                (request.request_ref, request.proposition_ref, request.target_context_ref, assessment.decision.value),
                32,
            ),
            proposition_ref=request.proposition_ref,
            source_context_ref=request.source_context_ref,
            target_context_ref=request.target_context_ref,
            decision=assessment.decision,
            truth_status=assessment.truth_status,
            confidence=assessment.confidence,
            source_refs=request.source_refs,
            source_assessment_pins=tuple(
                (item.assessment_ref, item.revision) for item in self.source_assessment_records(request)
            ) if assessment.decision in {AdmissionDecision.ADMIT_SUPPORT, AdmissionDecision.ADMIT_OPPOSITION} else (),
            evidence_refs=assessment.evidence_refs,
            proof_refs=request.proof_refs if assessment.decision in {AdmissionDecision.ADMIT_SUPPORT, AdmissionDecision.ADMIT_OPPOSITION} else (),
            policy_ref=request.policy_ref,
            authorization_ref=request.authorization_ref if assessment.decision in {AdmissionDecision.ADMIT_SUPPORT, AdmissionDecision.ADMIT_OPPOSITION} else None,
            permission_ref=request.permission_ref,
            sensitivity=request.sensitivity,
            valid_time_ref=request.valid_time_ref,
            metadata={**dict(request.metadata), **dict(assessment.metadata), "failed_requirements": assessment.failed_requirements},
        )
