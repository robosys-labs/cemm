"""Restart rehydration and stale-authority refusal for promoted learning packages."""
from __future__ import annotations

from dataclasses import dataclass

from ..schema.model import MeaningSchema, SchemaLifecycleStatus, UseDecision, schema_authorizes_use
from ..storage.model import DependencyEdge, RecordKind
from .authority import record_supports_use
from .model import (
    CompetenceResultRecord,
    LearningPackageRecord,
    LearningPackageStatus,
    PromotionDecisionKind,
    PromotionDecisionRecord,
    PromotionUseGrant,
)
from .package import LearningDependencyResolver


@dataclass(frozen=True, slots=True)
class RehydrationIssue:
    code: str
    target_ref: str
    message: str


@dataclass(frozen=True, slots=True)
class RehydrationReport:
    active_package_refs: tuple[str, ...]
    stale_package_refs: tuple[str, ...]
    grants: tuple[PromotionUseGrant, ...]
    issues: tuple[RehydrationIssue, ...]

    @property
    def valid(self) -> bool:
        return not self.stale_package_refs and not self.issues


class LearningRehydrationCoordinator:
    """Reconstruct effective learned authority only from exact durable lineage."""

    def __init__(self, store) -> None:
        self.store = store

    def audit(self) -> RehydrationReport:
        packages = self._effective_packages()
        decisions = self._effective_decisions()
        active: list[str] = []
        stale: list[str] = []
        grants: list[PromotionUseGrant] = []
        issues: list[RehydrationIssue] = []
        resolver = LearningDependencyResolver(self.store)
        for package in packages:
            if package.lifecycle_status != LearningPackageStatus.PROMOTED:
                continue
            resolution = resolver.resolve(package)
            if not resolution.valid:
                stale.append(package.package_ref)
                issues.append(RehydrationIssue(
                    "stale_package_dependencies", package.package_ref,
                    "exact candidate/dependency pins no longer resolve; learned authority must not reactivate",
                ))
                continue
            matching = [
                item for item in decisions
                if item.package_ref == package.package_ref
                and item.package_revision == int(
                    package.metadata.get("authority_source_package_revision", package.supersedes_revision or package.revision)
                )
                and item.decision == PromotionDecisionKind.PROMOTE
            ]
            if len(matching) != 1:
                stale.append(package.package_ref)
                issues.append(RehydrationIssue(
                    "promotion_decision_cardinality", package.package_ref,
                    f"expected one exact promote decision, found {len(matching)}",
                ))
                continue
            decision = matching[0]
            if not self._decision_competence_is_current(package, decision):
                stale.append(package.package_ref)
                issues.append(RehydrationIssue(
                    "stale_promotion_competence", package.package_ref,
                    "promotion competence or substrate fingerprint is stale/missing",
                ))
                continue
            if not self._promoted_authority_is_current(decision):
                stale.append(package.package_ref)
                issues.append(RehydrationIssue(
                    "stale_promoted_authority", package.package_ref,
                    "promoted canonical authority is missing, revoked, or no longer pinned to its decision",
                ))
                continue
            active.append(package.package_ref)
            grants.extend(decision.use_grants)
        return RehydrationReport(
            tuple(sorted(active)), tuple(sorted(set(stale))),
            tuple(sorted(grants, key=lambda item: (item.candidate_pin.key, item.operation.value))),
            tuple(issues),
        )

    def require_clean(self) -> RehydrationReport:
        report = self.audit()
        if not report.valid:
            details = "; ".join(f"{item.code}:{item.target_ref}" for item in report.issues)
            raise RuntimeError("stale learned authority refused during rehydration: " + details)
        return report

    def _decision_competence_is_current(self, package: LearningPackageRecord, decision: PromotionDecisionRecord) -> bool:
        for grant in decision.use_grants:
            for result_ref in grant.competence_result_refs:
                stored = self.store.get_record(RecordKind.COMPETENCE_RESULT, result_ref)
                if stored is None or not isinstance(stored.payload, CompetenceResultRecord):
                    return False
                result = stored.payload
                if result.package_ref != decision.package_ref or result.package_revision != decision.package_revision:
                    return False
                if result.candidate_pins != decision.candidate_pins or result.dependency_pins != package.dependency_pins:
                    return False
                for pin in (*result.candidate_pins, *result.dependency_pins):
                    current = self.store.get_record(pin.record_kind, pin.record_ref, pin.revision)
                    if current is None or current.record_fingerprint != pin.record_fingerprint:
                        return False
        return True

    def _promoted_authority_is_current(self, decision: PromotionDecisionRecord) -> bool:
        edges = tuple(
            stored.payload for stored in self.store.records(RecordKind.DEPENDENCY, all_revisions=True)
            if isinstance(stored.payload, DependencyEdge) and stored.payload.active
        )
        for grant in decision.use_grants:
            if grant.decision == UseDecision.PRESERVE_ONLY:
                continue
            current = self.store.get_record(grant.candidate_pin.record_kind, grant.candidate_pin.record_ref)
            if current is None or current.revision <= grant.candidate_pin.revision:
                return False
            if not record_supports_use(grant.candidate_pin.record_kind, current.payload, grant.operation):
                return False
            if isinstance(current.payload, MeaningSchema):
                if current.payload.use_profile.decision_for(grant.operation) != grant.decision:
                    return False
                if not schema_authorizes_use(
                    current.payload, grant.operation, provisional=(grant.decision == UseDecision.PROVISIONAL)
                ):
                    return False
            else:
                lifecycle = getattr(current.payload, "lifecycle_status", None)
                expected = (
                    SchemaLifecycleStatus.ACTIVE
                    if grant.decision == UseDecision.ALLOW
                    else SchemaLifecycleStatus.PROVISIONAL
                )
                if lifecycle != expected:
                    return False
            decision_edge = any(
                edge.dependent_kind == grant.candidate_pin.record_kind
                and edge.dependent_ref == grant.candidate_pin.record_ref
                and edge.dependent_revision == current.revision
                and edge.prerequisite_kind == RecordKind.PROMOTION_DECISION
                and edge.prerequisite_ref == decision.decision_ref
                and edge.prerequisite_revision == decision.revision
                for edge in edges
            )
            source_edge = any(
                edge.dependent_kind == grant.candidate_pin.record_kind
                and edge.dependent_ref == grant.candidate_pin.record_ref
                and edge.dependent_revision == current.revision
                and edge.prerequisite_kind == grant.candidate_pin.record_kind
                and edge.prerequisite_ref == grant.candidate_pin.record_ref
                and edge.prerequisite_revision == grant.candidate_pin.revision
                and edge.prerequisite_fingerprint == grant.candidate_pin.record_fingerprint
                for edge in edges
            )
            if not decision_edge or not source_edge:
                return False
        return True

    def _effective_packages(self) -> tuple[LearningPackageRecord, ...]:
        by_ref: dict[str, LearningPackageRecord] = {}
        for stored in self.store.records(RecordKind.LEARNING_PACKAGE, all_revisions=True):
            item = stored.payload
            if isinstance(item, LearningPackageRecord):
                current = by_ref.get(item.package_ref)
                if current is None or item.revision > current.revision:
                    by_ref[item.package_ref] = item
        return tuple(by_ref[key] for key in sorted(by_ref))

    def _effective_decisions(self) -> tuple[PromotionDecisionRecord, ...]:
        by_ref: dict[str, PromotionDecisionRecord] = {}
        for stored in self.store.records(RecordKind.PROMOTION_DECISION, all_revisions=True):
            item = stored.payload
            if isinstance(item, PromotionDecisionRecord):
                current = by_ref.get(item.decision_ref)
                if current is None or item.revision > current.revision:
                    by_ref[item.decision_ref] = item
        return tuple(by_ref[key] for key in sorted(by_ref))
