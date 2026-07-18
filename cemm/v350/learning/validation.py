"""Commit-boundary validation for Phase-13 learning and promotion authority.

The learning layer is deliberately fail-closed.  Durable lineage is not inferred
from free-form patch metadata: exact RecordDependency pins are required for the
records that carry learning/promotion authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ..schema.model import MeaningSchema, SchemaLifecycleStatus, UseDecision
from ..storage.model import PatchOperation, RecordKind
from .authority import record_kind_supports_use, record_supports_use
from .model import (
    CompetenceOutcome,
    CompetenceResultRecord,
    EvidencePolarity,
    LearningEvidenceLink,
    LearningFrontierRecord,
    LearningInvalidationRecord,
    LearningPackageRecord,
    LearningPackageStatus,
    PinnedRecord,
    PromotionDecisionKind,
    PromotionDecisionRecord,
)


@dataclass(frozen=True, slots=True)
class LearningValidationIssue:
    code: str
    target_ref: str
    message: str


_TERMINAL_PACKAGES = {
    LearningPackageStatus.RETRACTED,
    LearningPackageStatus.SUPERSEDED,
    LearningPackageStatus.INVALIDATED,
    LearningPackageStatus.REJECTED,
}

_NON_AUTHORITATIVE_CANDIDATE_LIFECYCLES = {
    SchemaLifecycleStatus.CANDIDATE,
    SchemaLifecycleStatus.STRUCTURALLY_CLOSED,
}


class LearningCommitValidator:
    def __init__(self, resolver) -> None:
        self.resolver = resolver

    def validate_global(self) -> tuple[LearningValidationIssue, ...]:
        """Revalidate every effective non-terminal package on each commit.

        This intentionally makes evidence removal/tombstoning and exact pin loss
        impossible to commit silently while learned authority still depends on it.
        """
        issues: list[LearningValidationIssue] = []
        for package in self._effective_packages():
            if package.lifecycle_status in _TERMINAL_PACKAGES:
                continue
            for pin in (*package.candidate_pins, *package.dependency_pins):
                resolved = self.resolver.resolve(pin.record_kind, pin.record_ref, pin.revision)
                if resolved is None or resolved.record_fingerprint != pin.record_fingerprint:
                    issues.append(LearningValidationIssue(
                        "stale_learning_pin",
                        package.package_ref,
                        f"exact pin no longer resolves: {pin.record_kind.value}:{pin.record_ref}@{pin.revision}",
                    ))
            for link_ref in (*package.evidence_link_refs, *package.counterexample_link_refs):
                stored = self.resolver.resolve(RecordKind.LEARNING_EVIDENCE_LINK, link_ref, 1)
                if stored is None or not isinstance(stored.payload, LearningEvidenceLink):
                    issues.append(LearningValidationIssue(
                        "stale_learning_evidence_link",
                        package.package_ref,
                        f"immutable evidence link no longer resolves: {link_ref}",
                    ))
                    continue
                link = stored.payload
                if link.package_ref != package.package_ref or link.package_revision != self._authority_source_package_revision(package):
                    issues.append(LearningValidationIssue(
                        "learning_evidence_package_mismatch",
                        package.package_ref,
                        f"evidence link {link_ref} targets another package revision",
                    ))
                for evidence_ref in link.evidence_refs:
                    if self.resolver.resolve(RecordKind.EVIDENCE, evidence_ref) is None:
                        issues.append(LearningValidationIssue(
                            "stale_learning_evidence",
                            package.package_ref,
                            f"evidence record no longer resolves: {evidence_ref}",
                        ))
        return tuple(issues)

    def validate_operation(self, operation: PatchOperation, record: Any) -> None:
        kind = operation.record_kind
        if kind == RecordKind.LEARNING_PACKAGE:
            self._validate_package(record, operation)
        elif kind == RecordKind.LEARNING_FRONTIER:
            if not isinstance(record, LearningFrontierRecord):
                raise ValueError("learning frontier record type mismatch")
        elif kind == RecordKind.LEARNING_EVIDENCE_LINK:
            self._validate_evidence_link(record, operation)
        elif kind == RecordKind.COMPETENCE_RESULT:
            self._validate_competence(record, operation)
        elif kind == RecordKind.PROMOTION_DECISION:
            self._validate_promotion_decision(record, operation)
        elif kind == RecordKind.LEARNING_INVALIDATION:
            self._validate_invalidation(record, operation)
        else:
            self._validate_promotion_boundary(operation, record)
            self._validate_pinned_dependency_revision_boundary(operation)

    def _validate_package(self, package: LearningPackageRecord, operation: PatchOperation) -> None:
        if not isinstance(package, LearningPackageRecord):
            raise ValueError("learning package record type mismatch")
        for pin in (*package.candidate_pins, *package.dependency_pins):
            self._require_pin(pin)
        refs = [pin.record_ref for pin in (*package.candidate_pins, *package.dependency_pins)]
        if len(refs) != len(set(refs)):
            raise ValueError("candidate/dependency pin refs must be globally unique within one learning package")

        # A learning package candidate must still be proposal material. Already
        # active/provisional/competence-verified authority belongs in dependency
        # pins, never in the candidate set to be promoted again.
        for pin in package.candidate_pins:
            stored = self.resolver.resolve(pin.record_kind, pin.record_ref, pin.revision)
            if stored is None:
                raise ValueError("learning package candidate is unresolved")
            lifecycle = getattr(stored.payload, "lifecycle_status", None)
            if lifecycle is not None and lifecycle not in _NON_AUTHORITATIVE_CANDIDATE_LIFECYCLES:
                raise ValueError("learning package candidate must be non-authoritative candidate/structurally-closed material")

        for requested in package.requested_use_authorizations:
            if requested.decision not in {UseDecision.ALLOW, UseDecision.PROVISIONAL, UseDecision.PRESERVE_ONLY}:
                continue
            if not any(record_kind_supports_use(pin.record_kind, requested.operation) for pin in package.candidate_pins):
                raise ValueError(
                    f"learning package requests {requested.operation.value} but no candidate record family can carry that use"
                )

        evidence_records: list[tuple[str, Any]] = []
        for link_ref in package.evidence_link_refs:
            stored = self.resolver.resolve(RecordKind.LEARNING_EVIDENCE_LINK, link_ref, 1)
            if stored is None or not isinstance(stored.payload, LearningEvidenceLink):
                raise ValueError(f"learning package evidence link is unresolved: {link_ref}")
            if stored.payload.polarity != EvidencePolarity.SUPPORT:
                raise ValueError("support evidence_link_refs may contain only SUPPORT links")
            evidence_records.append((link_ref, stored))
        for link_ref in package.counterexample_link_refs:
            stored = self.resolver.resolve(RecordKind.LEARNING_EVIDENCE_LINK, link_ref, 1)
            if stored is None or not isinstance(stored.payload, LearningEvidenceLink):
                raise ValueError(f"learning package counterexample link is unresolved: {link_ref}")
            if stored.payload.polarity not in {
                EvidencePolarity.COUNTEREXAMPLE,
                EvidencePolarity.CORRECTION,
                EvidencePolarity.RETRACTION,
            }:
                raise ValueError("counterexample_link_refs must preserve counterexample/correction/retraction polarity")
            evidence_records.append((link_ref, stored))
        for _link_ref, stored in evidence_records:
            link = stored.payload
            if link.package_ref != package.package_ref or link.package_revision != self._authority_source_package_revision(package):
                raise ValueError("learning evidence link must pin the exact authority-source package revision")
            if link.permission_ref != package.permission_ref:
                raise ValueError("learning package/evidence permission scope must remain identical without an explicit permission lattice")

        for frontier_ref in package.frontier_refs:
            stored = self.resolver.resolve(RecordKind.LEARNING_FRONTIER, frontier_ref)
            if stored is None or not isinstance(stored.payload, LearningFrontierRecord):
                raise ValueError(f"learning package frontier is unresolved: {frontier_ref}")

        if package.lifecycle_status == LearningPackageStatus.PROMOTED:
            self._require_dependency_kind(operation, RecordKind.PROMOTION_DECISION, "promotion_decision")
            return
        if package.lifecycle_status in _TERMINAL_PACKAGES:
            # Terminal lifecycle revisions only revoke/narrow authority; the exact
            # invalidation/retraction lineage is validated on LearningInvalidation.
            return

        # Initial/updated candidate packages must materialize their exact DAG as
        # dependency edges; otherwise correction-driven invalidation cannot be
        # complete or deterministic.
        for pin in (*package.candidate_pins, *package.dependency_pins):
            self._require_exact_dependency(operation, pin)
        for _link_ref, stored in evidence_records:
            self._require_stored_dependency(operation, stored)
        for frontier_ref in package.frontier_refs:
            stored = self.resolver.resolve(RecordKind.LEARNING_FRONTIER, frontier_ref)
            assert stored is not None
            self._require_stored_dependency(operation, stored)

    def _validate_evidence_link(self, link: LearningEvidenceLink, operation: PatchOperation) -> None:
        if not isinstance(link, LearningEvidenceLink):
            raise ValueError("learning evidence link type mismatch")
        package = self.resolver.resolve(RecordKind.LEARNING_PACKAGE, link.package_ref, link.package_revision)
        if package is None or not isinstance(package.payload, LearningPackageRecord):
            raise ValueError("learning evidence link must pin an exact package revision")
        if link.candidate_pin is not None:
            self._require_pin(link.candidate_pin)
            if link.candidate_pin.key not in {pin.key for pin in package.payload.candidate_pins}:
                raise ValueError("learning evidence candidate pin is outside the exact package")
            self._require_exact_dependency(operation, link.candidate_pin)
        self._require_stored_dependency(operation, package)
        for evidence_ref in link.evidence_refs:
            evidence = self.resolver.resolve(RecordKind.EVIDENCE, evidence_ref)
            if evidence is None:
                raise ValueError(f"learning evidence ref is unresolved: {evidence_ref}")
            self._require_stored_dependency(operation, evidence)

    def _validate_competence(self, result: CompetenceResultRecord, operation: PatchOperation) -> None:
        if not isinstance(result, CompetenceResultRecord):
            raise ValueError("competence result record type mismatch")
        package_stored = self.resolver.resolve(RecordKind.LEARNING_PACKAGE, result.package_ref, result.package_revision)
        if package_stored is None or not isinstance(package_stored.payload, LearningPackageRecord):
            raise ValueError("competence result must pin an exact learning package revision")
        package = package_stored.payload
        if result.candidate_pins != package.candidate_pins or result.dependency_pins != package.dependency_pins:
            raise ValueError("competence result substrate differs from exact package")
        if set(result.independent_lineage_refs).intersection(package.source_lineage_refs):
            raise ValueError("competence lineage is not independent from package induction/source lineage")
        for pin in (*result.candidate_pins, *result.dependency_pins):
            self._require_pin(pin)
            self._require_exact_dependency(operation, pin)
        self._require_stored_dependency(operation, package_stored)
        if result.outcome == CompetenceOutcome.PASSED and not result.proof_refs:
            raise ValueError("passed competence requires proof refs")
        if not set(result.counterexample_refs).issubset(set(package.counterexample_link_refs)):
            raise ValueError("competence result references counterexamples outside the exact package")

    def _validate_invalidation(self, invalidation: LearningInvalidationRecord, operation: PatchOperation) -> None:
        if not isinstance(invalidation, LearningInvalidationRecord):
            raise ValueError("learning invalidation record type mismatch")
        for pin in invalidation.trigger_pins:
            self._require_exact_dependency(operation, pin)
        for evidence_ref in invalidation.evidence_refs:
            evidence = self.resolver.resolve(RecordKind.EVIDENCE, evidence_ref)
            if evidence is not None:
                self._require_stored_dependency(operation, evidence)

    def _validate_promotion_decision(self, decision: PromotionDecisionRecord, operation: PatchOperation) -> None:
        if not isinstance(decision, PromotionDecisionRecord):
            raise ValueError("promotion decision record type mismatch")
        package_stored = self.resolver.resolve(RecordKind.LEARNING_PACKAGE, decision.package_ref, decision.package_revision)
        if package_stored is None or not isinstance(package_stored.payload, LearningPackageRecord):
            raise ValueError("promotion decision must pin an exact learning package revision")
        package = package_stored.payload
        if decision.candidate_pins != package.candidate_pins:
            raise ValueError("promotion decision candidate pins differ from package")
        if decision.permission_ref != package.permission_ref:
            raise ValueError("promotion may not broaden package permission scope")
        self._require_stored_dependency(operation, package_stored)
        for pin in (*package.candidate_pins, *package.dependency_pins):
            self._require_exact_dependency(operation, pin)

        evidence_links = []
        for link_ref in (*package.evidence_link_refs, *package.counterexample_link_refs):
            stored = self.resolver.resolve(RecordKind.LEARNING_EVIDENCE_LINK, link_ref, 1)
            if stored is None or not isinstance(stored.payload, LearningEvidenceLink):
                raise ValueError(f"promotion evidence link is unresolved: {link_ref}")
            evidence_links.append(stored.payload)
            self._require_stored_dependency(operation, stored)
            for evidence_ref in stored.payload.evidence_refs:
                evidence = self.resolver.resolve(RecordKind.EVIDENCE, evidence_ref)
                if evidence is None:
                    raise ValueError(f"promotion evidence is unresolved: {evidence_ref}")
                self._require_stored_dependency(operation, evidence)

        if decision.decision != PromotionDecisionKind.PROMOTE:
            return
        if any(link.polarity in {EvidencePolarity.CORRECTION, EvidencePolarity.RETRACTION} for link in evidence_links):
            raise ValueError("correction/retraction evidence blocks promotion until a new package revision resolves it")

        requested = {item.operation: item.decision for item in package.requested_use_authorizations}
        all_counterexamples = set(package.counterexample_link_refs)
        for grant in decision.use_grants:
            requested_decision = requested.get(grant.operation)
            if requested_decision is None:
                raise ValueError("promotion grant operation was not requested by the exact package revision")
            if grant.decision == UseDecision.ALLOW and requested_decision != UseDecision.ALLOW:
                raise ValueError("promotion grant broadens requested per-use authority")
            if grant.decision == UseDecision.PROVISIONAL and requested_decision not in {UseDecision.ALLOW, UseDecision.PROVISIONAL}:
                raise ValueError("provisional promotion was not requested by package policy")
            self._require_pin(grant.candidate_pin)
            stored_candidate = self.resolver.resolve(
                grant.candidate_pin.record_kind, grant.candidate_pin.record_ref, grant.candidate_pin.revision
            )
            if stored_candidate is None or not record_supports_use(
                grant.candidate_pin.record_kind, stored_candidate.payload, grant.operation
            ):
                raise ValueError("promotion grant operation is incompatible with candidate structural contract")
            covered_counterexamples: set[str] = set()
            for result_ref in grant.competence_result_refs:
                stored = self.resolver.resolve(RecordKind.COMPETENCE_RESULT, result_ref, 1)
                if stored is None or not isinstance(stored.payload, CompetenceResultRecord):
                    raise ValueError(f"promotion competence result is unresolved: {result_ref}")
                self._require_stored_dependency(operation, stored)
                result = stored.payload
                if result.package_ref != decision.package_ref or result.package_revision != decision.package_revision:
                    raise ValueError("promotion attempted to reuse competence from another package revision")
                if result.use_operation != grant.operation:
                    raise ValueError("promotion grant and competence use differ")
                if result.candidate_pins != decision.candidate_pins or result.dependency_pins != package.dependency_pins:
                    raise ValueError("promotion competence substrate fingerprint set differs")
                if grant.decision == UseDecision.ALLOW and result.outcome != CompetenceOutcome.PASSED:
                    raise ValueError("allow promotion requires passed competence")
                if grant.decision == UseDecision.PROVISIONAL and result.outcome not in {CompetenceOutcome.PASSED, CompetenceOutcome.PARTIAL}:
                    raise ValueError("provisional promotion requires passed or partial competence")
                covered_counterexamples.update(result.counterexample_refs)
            if all_counterexamples.difference(covered_counterexamples):
                raise ValueError("promotion competence does not cover every exact counterexample link")

    def _validate_promotion_boundary(self, operation: PatchOperation, record: Any) -> None:
        lifecycle = getattr(record, "lifecycle_status", None)
        if lifecycle not in {
            SchemaLifecycleStatus.PROVISIONAL,
            SchemaLifecycleStatus.COMPETENCE_VERIFIED,
            SchemaLifecycleStatus.ACTIVE,
        }:
            return
        packages = []
        for package in self._all_nonterminal_package_revisions():
            for pin in package.candidate_pins:
                if (
                    pin.record_kind == operation.record_kind
                    and pin.record_ref == operation.target_ref
                    and operation.record_revision > pin.revision
                ):
                    packages.append((package, pin))
        if not packages:
            return  # reviewed boot/manual authority remains governed by its existing source path
        decision_deps = [
            dep for dep in operation.dependencies if dep.record_kind == RecordKind.PROMOTION_DECISION
        ]
        if not decision_deps:
            raise ValueError("learned candidate activation requires an exact PromotionDecision dependency")
        authorized = False
        for dependency in decision_deps:
            if dependency.revision is None or dependency.fingerprint is None:
                continue
            stored = self.resolver.resolve(RecordKind.PROMOTION_DECISION, dependency.record_ref, dependency.revision)
            if (
                stored is None
                or stored.record_fingerprint != dependency.fingerprint
                or not isinstance(stored.payload, PromotionDecisionRecord)
            ):
                continue
            decision = stored.payload
            if decision.decision != PromotionDecisionKind.PROMOTE:
                continue
            for package, pin in packages:
                if decision.package_ref != package.package_ref or decision.package_revision != package.revision:
                    continue
                grants = decision.grants_for(pin)
                if not grants:
                    continue
                permission_ref = getattr(record, "permission_ref", package.permission_ref)
                if permission_ref != package.permission_ref:
                    raise ValueError("learned promotion cannot broaden permission scope")
                if isinstance(record, MeaningSchema):
                    granted = {(grant.operation, grant.decision) for grant in grants}
                    for auth in record.use_profile.authorizations:
                        if auth.decision in {UseDecision.ALLOW, UseDecision.PROVISIONAL} and (auth.operation, auth.decision) not in granted:
                            raise ValueError("schema contains executable use not granted by PromotionDecision")
                authorized = True
        if not authorized:
            raise ValueError("promotion decision does not authorize this exact learned candidate revision")

    def _validate_pinned_dependency_revision_boundary(self, operation: PatchOperation) -> None:
        """Prevent silent dependency drift behind a promoted/nonterminal package.

        Exact historical pins intentionally remain readable, so merely inserting a
        newer revision would otherwise leave competence apparently valid even when
        effective dependency authority changed.  The package must be explicitly
        invalidated/superseded first. Promotion of its own candidate is exempted by
        the exact PromotionDecision dependency checked above.
        """
        if any(dep.record_kind == RecordKind.PROMOTION_DECISION for dep in operation.dependencies):
            return
        for package in self._effective_packages():
            if package.lifecycle_status in _TERMINAL_PACKAGES:
                continue
            for pin in (*package.candidate_pins, *package.dependency_pins):
                if (
                    pin.record_kind == operation.record_kind
                    and pin.record_ref == operation.target_ref
                    and operation.record_revision > pin.revision
                ):
                    raise ValueError(
                        "cannot revise a record pinned by a nonterminal learning package; invalidate/supersede the package first"
                    )

    @staticmethod
    def _authority_source_package_revision(package: LearningPackageRecord) -> int:
        value = package.metadata.get("authority_source_package_revision")
        return package.revision if value is None else int(value)

    def _effective_packages(self) -> tuple[LearningPackageRecord, ...]:
        latest: dict[str, LearningPackageRecord] = {}
        for stored in self.resolver.records(RecordKind.LEARNING_PACKAGE):
            package = stored.payload
            if not isinstance(package, LearningPackageRecord):
                continue
            current = latest.get(package.package_ref)
            if current is None or package.revision > current.revision:
                latest[package.package_ref] = package
        return tuple(latest[key] for key in sorted(latest))

    def _all_nonterminal_package_revisions(self) -> tuple[LearningPackageRecord, ...]:
        effective = {item.package_ref: item for item in self._effective_packages()}
        result = []
        for stored in self.resolver.records(RecordKind.LEARNING_PACKAGE):
            package = stored.payload
            if not isinstance(package, LearningPackageRecord):
                continue
            latest = effective.get(package.package_ref)
            if latest is None or latest.lifecycle_status in _TERMINAL_PACKAGES:
                continue
            result.append(package)
        return tuple(result)

    def _require_pin(self, pin: PinnedRecord) -> None:
        stored = self.resolver.resolve(pin.record_kind, pin.record_ref, pin.revision)
        if stored is None or stored.record_fingerprint != pin.record_fingerprint:
            raise ValueError(
                f"stale/missing exact pin {pin.record_kind.value}:{pin.record_ref}@{pin.revision}"
            )

    @staticmethod
    def _dependency_matches(dep, kind: RecordKind, ref: str, revision: int, fingerprint: str) -> bool:
        return (
            dep.record_kind == kind
            and dep.record_ref == ref
            and dep.revision == revision
            and dep.fingerprint == fingerprint
        )

    def _require_exact_dependency(self, operation: PatchOperation, pin: PinnedRecord) -> None:
        if not any(
            self._dependency_matches(dep, pin.record_kind, pin.record_ref, pin.revision, pin.record_fingerprint)
            for dep in operation.dependencies
        ):
            raise ValueError(
                f"learning authority record is missing exact dependency edge: {pin.record_kind.value}:{pin.record_ref}@{pin.revision}"
            )

    def _require_stored_dependency(self, operation: PatchOperation, stored) -> None:
        if not any(
            self._dependency_matches(dep, stored.record_kind, stored.record_ref, stored.revision, stored.record_fingerprint)
            for dep in operation.dependencies
        ):
            raise ValueError(
                f"learning authority record is missing exact dependency edge: {stored.record_kind.value}:{stored.record_ref}@{stored.revision}"
            )

    @staticmethod
    def _require_dependency_kind(operation: PatchOperation, kind: RecordKind, dependency_kind: str) -> None:
        if not any(
            dep.record_kind == kind
            and dep.revision is not None
            and dep.fingerprint is not None
            and dep.dependency_kind == dependency_kind
            for dep in operation.dependencies
        ):
            raise ValueError(f"learning authority record requires exact {dependency_kind} dependency")
