"""Generic Phase-14 impact and importance engines."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..learning.model import FrontierResolutionStatus, LearningFrontierRecord, PinnedRecord
from ..schema.model import SchemaClass, semantic_fingerprint
from ..storage.codec import record_ref
from ..storage.model import RecordKind
from ..uol.model import (
    EventOccurrence, FillerRef, ImpactAssessment, ImportanceAssessment, ImportanceClass,
    SemanticApplication, StateDelta,
)
from .model import (
    ImpactProofRecord, ImpactRuleRecord, ImportanceEvidencePolarity, ImportanceEvidenceRecord,
    ImportancePolicyRecord, SignificanceAssessmentRecord,
)


@dataclass(frozen=True, slots=True)
class ResolvedSource:
    pin: PinnedRecord
    payload: object
    context_ref: str
    permission_ref: str
    application: SemanticApplication | None
    application_pin: PinnedRecord | None


class ImpactRuleRegistry:
    def __init__(self, rules: Iterable[ImpactRuleRecord]) -> None:
        by_ref = {}
        for rule in rules:
            if rule.executable:
                by_ref.setdefault(rule.rule_ref, []).append(rule)
        effective = []
        for rule_ref in sorted(by_ref):
            revisions = by_ref[rule_ref]
            superseded = {r.supersedes_revision for r in revisions if r.supersedes_revision is not None}
            effective.extend(r for r in revisions if r.revision not in superseded)
        self._rules = tuple(sorted(effective, key=lambda r: (r.rule_ref, r.revision)))

    def candidates(self, source: ResolvedSource) -> tuple[ImpactRuleRecord, ...]:
        source_schema_pin = None
        if isinstance(source.payload, SemanticApplication):
            source_schema_pin = (source.payload.schema_ref, source.payload.schema_revision)
        elif isinstance(source.payload, EventOccurrence) and source.application is not None:
            source_schema_pin = (source.application.schema_ref, source.application.schema_revision)
        result = []
        for rule in self._rules:
            if source.pin.record_kind not in rule.source_record_kinds:
                continue
            if rule.context_constraints and source.context_ref not in rule.context_constraints:
                continue
            if rule.source_schema_pins and source_schema_pin not in rule.source_schema_pins:
                continue
            result.append(rule)
        return tuple(sorted(result, key=lambda r: (-r.priority, r.rule_ref, r.revision)))


class StakeholderResolver:
    """Resolve only from explicit structural bindings. No names or relationship heuristics."""

    @staticmethod
    def _port_refs(application: SemanticApplication | None, ports: tuple[str, ...]) -> tuple[str, ...]:
        if application is None:
            return ()
        result: list[str] = []
        wanted = set(ports)
        for binding in application.bindings:
            if binding.port_ref not in wanted:
                continue
            for filler in binding.fillers:
                if isinstance(filler, FillerRef):
                    result.append(filler.ref)
        return tuple(sorted(set(result)))

    def resolve(self, source: ResolvedSource, rule: ImpactRuleRecord) -> tuple[tuple[str, ...], tuple[str, ...]]:
        stakeholders = set(rule.fixed_stakeholder_refs)
        affected = set(rule.fixed_affected_refs)
        stakeholders.update(self._port_refs(source.application, rule.stakeholder_port_refs))
        affected.update(self._port_refs(source.application, rule.affected_port_refs))
        if isinstance(source.payload, StateDelta):
            # State deltas expose the affected holder structurally; rules still decide whether to use it.
            if "holder" in rule.affected_port_refs:
                affected.add(source.payload.holder_ref)
        return tuple(sorted(stakeholders)), tuple(sorted(affected))


class ImportanceAggregator:
    def assess(
        self,
        *,
        subject_ref: str,
        stakeholder_ref: str,
        context_ref: str,
        permission_ref: str,
        evidence: Iterable[ImportanceEvidenceRecord],
        policy: ImportancePolicyRecord,
    ) -> tuple[ImportanceAssessment | None, tuple[ImportanceEvidenceRecord, ...]]:
        if not policy.executable:
            raise ValueError("importance policy is not active/authorized for IMPACT use")
        weights = {(ref, rev): weight for ref, rev, weight in policy.channel_weights}
        relevant = tuple(
            item for item in evidence
            if item.subject_ref == subject_ref
            and item.stakeholder_ref == stakeholder_ref
            and item.context_ref == context_ref
            and item.permission_ref in {"public", permission_ref}
            and (item.channel_schema_ref, item.channel_schema_revision) in weights
        )
        if not relevant:
            return None, ()
        support = 0.0
        oppose = 0.0
        reasons: list[str] = []
        refs: list[str] = []
        for item in relevant:
            contribution = min(1.0, item.weight * weights[(item.channel_schema_ref, item.channel_schema_revision)])
            if item.polarity == ImportanceEvidencePolarity.SUPPORT:
                support += contribution
            else:
                oppose += contribution
            refs.append(item.evidence_ref)
            reasons.extend(item.reason_refs or (item.evidence_ref,))
        denominator = max(1.0, support + oppose)
        score = max(0.0, min(1.0, (support - oppose) / denominator))
        if score >= policy.high_threshold:
            cls = ImportanceClass.HIGH
        elif score >= policy.low_threshold:
            cls = ImportanceClass.MODERATE
        else:
            cls = ImportanceClass.LOW
        ref = "importance:" + semantic_fingerprint(
            "importance-assessment-ref",
            (subject_ref, stakeholder_ref, context_ref, tuple(sorted(refs)), policy.policy_ref, policy.revision),
            24,
        )
        return ImportanceAssessment(
            assessment_ref=ref,
            subject_ref=subject_ref,
            stakeholder_ref=stakeholder_ref,
            context_ref=context_ref,
            score=score,
            importance_class=cls,
            evidence_refs=tuple(sorted(refs)),
            reasons=tuple(sorted(set(reasons))),
        ), relevant


class SignificanceEngine:
    def __init__(self, store) -> None:
        self.store = store
        self.resolver = StakeholderResolver()
        self.importance = ImportanceAggregator()

    def resolve_source(self, pin: PinnedRecord) -> ResolvedSource:
        stored = self.store.get_record(pin.record_kind, pin.record_ref, pin.revision)
        if stored is None or stored.record_fingerprint != pin.record_fingerprint:
            raise ValueError("stale/missing exact Phase-14 source pin")
        payload = stored.payload
        context_ref = stored.context_ref or getattr(payload, "context_ref", "actual")
        permission_ref = stored.permission_ref or getattr(payload, "permission_ref", "conversation")
        application = None
        application_pin = None
        if isinstance(payload, SemanticApplication):
            application = payload
            application_pin = pin
        elif isinstance(payload, EventOccurrence):
            # EventOccurrence stores only participant_application_ref, never a revision.
            # Do not recover latest-by-ref here; assess() must receive an explicit exact pin.
            application = None
            application_pin = None
        return ResolvedSource(pin, payload, context_ref, permission_ref, application, application_pin)

    def assess(
        self,
        source_pin: PinnedRecord,
        rule: ImpactRuleRecord,
        rule_pin: PinnedRecord,
        *,
        importance_evidence: Iterable[ImportanceEvidenceRecord] = (),
        importance_policy: ImportancePolicyRecord | None = None,
        importance_policy_pin: PinnedRecord | None = None,
        prerequisite_proof_pins: tuple[PinnedRecord, ...] = (),
        participant_application_pin: PinnedRecord | None = None,
    ) -> tuple[tuple[tuple[ImpactProofRecord, SignificanceAssessmentRecord], ...], tuple[LearningFrontierRecord, ...]]:
        source = self.resolve_source(source_pin)
        if isinstance(source.payload, EventOccurrence):
            if participant_application_pin is None or participant_application_pin.record_kind != RecordKind.SEMANTIC_APPLICATION or participant_application_pin.record_ref != source.payload.participant_application_ref:
                raise ValueError("event impact requires the exact participant application pin")
            app_stored = self.store.get_record(participant_application_pin.record_kind, participant_application_pin.record_ref, participant_application_pin.revision)
            if app_stored is None or app_stored.record_fingerprint != participant_application_pin.record_fingerprint or not isinstance(app_stored.payload, SemanticApplication):
                raise ValueError("stale/missing exact participant application pin")
            source = ResolvedSource(source.pin, source.payload, source.context_ref, source.permission_ref, app_stored.payload, participant_application_pin)
        stored_rule = self.store.get_record(rule_pin.record_kind, rule_pin.record_ref, rule_pin.revision)
        if stored_rule is None or stored_rule.record_fingerprint != rule_pin.record_fingerprint or stored_rule.payload != rule:
            raise ValueError("impact rule object does not match exact durable rule_pin")
        if not rule.executable:
            raise ValueError("candidate/provisional impact rule cannot execute")
        if importance_policy is not None:
            if importance_policy_pin is None:
                raise ValueError("importance policy use requires an exact importance_policy_pin")
            stored_policy = self.store.get_record(importance_policy_pin.record_kind, importance_policy_pin.record_ref, importance_policy_pin.revision)
            if stored_policy is None or stored_policy.record_fingerprint != importance_policy_pin.record_fingerprint or stored_policy.payload != importance_policy:
                raise ValueError("importance policy object does not match exact durable policy pin")
        provided_kinds = {pin.record_kind for pin in prerequisite_proof_pins}
        if set(rule.prerequisite_proof_kinds).difference(provided_kinds):
            raise ValueError("impact rule prerequisite proof kinds are not satisfied")
        for pin in prerequisite_proof_pins:
            stored = self.store.get_record(pin.record_kind, pin.record_ref, pin.revision)
            if stored is None or stored.record_fingerprint != pin.record_fingerprint:
                raise ValueError("stale prerequisite proof pin for impact assessment")
        stakeholders, affected = self.resolver.resolve(source, rule)
        frontiers: list[LearningFrontierRecord] = []
        if not stakeholders or not affected:
            frontier_ref = "learning-frontier:impact:" + semantic_fingerprint(
                "impact-binding-frontier", (source_pin.key, rule_pin.key, stakeholders, affected), 24
            )
            frontiers.append(LearningFrontierRecord(
                frontier_ref=frontier_ref,
                target_ref=source_pin.record_ref,
                missing_contract="impact_stakeholder_or_affected_binding",
                expected_record_kinds=(RecordKind.REFERENT, RecordKind.SEMANTIC_APPLICATION),
                expected_schema_classes=(SchemaClass.REFERENT_TYPE,),
                accepted_anchor_types=(), evidence_refs=(), resolution_status=FrontierResolutionStatus.OPEN,
                context_ref=source.context_ref, permission_ref=source.permission_ref,
            ))
            return (), tuple(frontiers)
        results = []
        for stakeholder in stakeholders:
            for affected_ref in affected:
                proof_ref = "impact-proof:" + semantic_fingerprint(
                    "impact-proof-ref", (source_pin.key, rule_pin.key, stakeholder, affected_ref, source.context_ref), 24
                )
                proof = ImpactProofRecord(
                    proof_ref=proof_ref, source_pin=source_pin, rule_pin=rule_pin, stakeholder_ref=stakeholder,
                    affected_ref=affected_ref, context_ref=source.context_ref, permission_ref=source.permission_ref,
                    binding_source_pins=(() if source.application_pin is None else (source.application_pin,)),
                    prerequisite_proof_pins=prerequisite_proof_pins,
                    prerequisite_proof_refs=tuple(pin.record_ref for pin in prerequisite_proof_pins),
                    confidence=rule.confidence,
                )
                event_ref = source_pin.record_ref
                impact_ref = "impact:" + semantic_fingerprint(
                    "impact-assessment-ref", (proof_ref, rule.affected_facet_refs, rule.direction.value, rule.valence.value), 24
                )
                impact = ImpactAssessment(
                    assessment_ref=impact_ref,
                    source_event_or_state_ref=event_ref,
                    affected_ref=affected_ref,
                    stakeholder_ref=stakeholder,
                    affected_facet_refs=rule.affected_facet_refs,
                    direction=rule.direction,
                    valence=rule.valence,
                    context_ref=source.context_ref,
                    reversibility=rule.reversibility,
                    magnitude_ref=rule.magnitude_ref,
                    duration_ref=rule.duration_ref,
                    confidence=rule.confidence,
                    proof_refs=(proof_ref,),
                )
                importance = None
                relevant = ()
                if importance_policy is not None:
                    importance, relevant = self.importance.assess(
                        subject_ref=event_ref,
                        stakeholder_ref=stakeholder,
                        context_ref=source.context_ref,
                        permission_ref=source.permission_ref,
                        evidence=importance_evidence,
                        policy=importance_policy,
                    )
                assessment_ref = "significance:" + semantic_fingerprint(
                    "significance-ref", (impact_ref, None if importance is None else importance.assessment_ref), 24
                )
                results.append((proof, SignificanceAssessmentRecord(
                    assessment_ref=assessment_ref, source_pin=source_pin, rule_pin=rule_pin, proof_ref=proof_ref,
                    impact=impact, importance=importance,
                    importance_evidence_refs=tuple(sorted(item.evidence_ref for item in relevant)),
                    importance_policy_pin=importance_policy_pin, frontier_refs=(), context_ref=source.context_ref,
                    permission_ref=source.permission_ref,
                )))
        return tuple(results), tuple(frontiers)
