"""Per-use promotion policy and atomic CAS promotion coordinator."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from ..schema.model import (
    MeaningSchema,
    SchemaLifecycleStatus,
    UseAuthorization,
    UseDecision,
    UseOperation,
    UseProfile,
    semantic_fingerprint,
)
from ..storage.codec import encode_record, record_fingerprints, record_revision
from ..storage.model import GraphPatch, PatchOperation, PatchOperationKind, RecordDependency, RecordKind
from .authority import record_kind_supports_use, record_supports_use
from .frontier import EvidenceSummary
from .model import (
    CompetenceOutcome,
    CompetenceResultRecord,
    LearningEvidenceLink,
    LearningPackageRecord,
    LearningPackageStatus,
    PinnedRecord,
    PromotionDecisionKind,
    PromotionDecisionRecord,
    PromotionUseGrant,
)
from .package import LearningDependencyResolver


@dataclass(frozen=True, slots=True)
class PromotionPolicyResult:
    decision: PromotionDecisionKind
    use_grants: tuple[PromotionUseGrant, ...]
    blocked_reasons: tuple[str, ...]


class PromotionPolicyEngine:
    """Mechanical promotion policy over exact evidence/competence lineage.

    It never inspects semantic keys, concept names, words, or fixture names.
    When bound to a store it additionally verifies record-level structural use
    declarations (for example a lexical sense's explicit use_operation).
    """

    def __init__(self, store=None) -> None:
        self.store = store

    def _pin_supports_use(self, pin: PinnedRecord, operation: UseOperation) -> bool:
        if not record_kind_supports_use(pin.record_kind, operation):
            return False
        if self.store is None:
            return True
        stored = self.store.get_record(pin.record_kind, pin.record_ref, pin.revision)
        return (
            stored is not None
            and stored.record_fingerprint == pin.record_fingerprint
            and record_supports_use(pin.record_kind, stored.payload, operation)
        )

    def evaluate(
        self,
        package: LearningPackageRecord,
        competence_results: Iterable[CompetenceResultRecord],
        evidence: EvidenceSummary,
    ) -> PromotionPolicyResult:
        results = tuple(competence_results)
        blocked: list[str] = []
        if evidence.correction_link_refs or evidence.retraction_link_refs:
            blocked.append("correction_or_retraction_present")
        if package.counterexample_link_refs and not results:
            blocked.append("counterexamples_require_explicit_competence")
        grants: list[PromotionUseGrant] = []
        for requested in package.requested_use_authorizations:
            matching = tuple(
                item for item in results
                if item.package_ref == package.package_ref
                and item.package_revision == package.revision
                and item.use_operation == requested.operation
                and item.candidate_pins == package.candidate_pins
                and item.dependency_pins == package.dependency_pins
            )
            passed = tuple(item for item in matching if item.outcome == CompetenceOutcome.PASSED)
            covered_counterexamples = {
                ref for item in passed for ref in item.counterexample_refs
            }
            if requested.decision == UseDecision.ALLOW:
                if not passed:
                    blocked.append(f"missing_passed_competence:{requested.operation.value}")
                    continue
                missing_counterexamples = set(package.counterexample_link_refs).difference(covered_counterexamples)
                if missing_counterexamples:
                    blocked.append(f"uncovered_counterexamples:{requested.operation.value}")
                    continue
                compatible = tuple(
                    pin for pin in package.candidate_pins
                    if self._pin_supports_use(pin, requested.operation)
                )
                if not compatible:
                    blocked.append(f"no_compatible_candidate_family:{requested.operation.value}")
                    continue
                for pin in compatible:
                    grants.append(PromotionUseGrant(
                        pin,
                        requested.operation,
                        UseDecision.ALLOW,
                        tuple(sorted(item.result_ref for item in passed)),
                        reason="exact per-use competence passed",
                    ))
            elif requested.decision == UseDecision.PROVISIONAL:
                acceptable = tuple(
                    item for item in matching
                    if item.outcome in {CompetenceOutcome.PASSED, CompetenceOutcome.PARTIAL}
                )
                if not acceptable:
                    blocked.append(f"missing_competence:{requested.operation.value}")
                    continue
                compatible = tuple(
                    pin for pin in package.candidate_pins
                    if self._pin_supports_use(pin, requested.operation)
                )
                if not compatible:
                    blocked.append(f"no_compatible_candidate_family:{requested.operation.value}")
                    continue
                for pin in compatible:
                    grants.append(PromotionUseGrant(
                        pin,
                        requested.operation,
                        UseDecision.PROVISIONAL,
                        tuple(sorted(item.result_ref for item in acceptable)),
                        reason="explicit provisional per-use competence",
                    ))
            elif requested.decision == UseDecision.PRESERVE_ONLY:
                for pin in package.candidate_pins:
                    if self._pin_supports_use(pin, requested.operation):
                        grants.append(PromotionUseGrant(pin, requested.operation, UseDecision.PRESERVE_ONLY))
        if blocked:
            return PromotionPolicyResult(PromotionDecisionKind.BLOCK, (), tuple(sorted(set(blocked))))
        positive = tuple(
            grant for grant in grants
            if grant.decision in {UseDecision.ALLOW, UseDecision.PROVISIONAL}
        )
        if not positive:
            return PromotionPolicyResult(
                PromotionDecisionKind.PRESERVE_CANDIDATE, (), ("no_positive_use_authorization",)
            )
        return PromotionPolicyResult(PromotionDecisionKind.PROMOTE, tuple(grants), ())

    def decision_record(
        self,
        package: LearningPackageRecord,
        result: PromotionPolicyResult,
        *,
        policy_ref: str,
        review_refs: tuple[str, ...],
        authorization_refs: tuple[str, ...],
        risk_refs: tuple[str, ...] = (),
    ) -> PromotionDecisionRecord:
        decision_ref = "promotion-decision:" + semantic_fingerprint(
            "promotion-decision-ref",
            (
                package.package_ref,
                package.revision,
                result.decision.value,
                tuple((g.candidate_pin.key, g.operation.value, g.decision.value, g.competence_result_refs) for g in result.use_grants),
                review_refs,
                authorization_refs,
                risk_refs,
                result.blocked_reasons,
            ),
            24,
        )
        return PromotionDecisionRecord(
            decision_ref=decision_ref,
            package_ref=package.package_ref,
            package_revision=package.revision,
            decision=result.decision,
            candidate_pins=package.candidate_pins,
            use_grants=result.use_grants,
            policy_ref=policy_ref,
            review_refs=review_refs,
            authorization_refs=authorization_refs,
            risk_refs=risk_refs,
            reason_refs=result.blocked_reasons,
            scope_ref=package.scope_ref,
            permission_ref=package.permission_ref,
        )


class PromotionCoordinator:
    """Atomically persist a promotion decision and canonical promoted revisions."""

    def __init__(self, store) -> None:
        self.store = store

    def promote(self, package: LearningPackageRecord, decision: PromotionDecisionRecord):
        if decision.decision != PromotionDecisionKind.PROMOTE:
            raise ValueError("only an explicit promote decision can activate semantic use")
        if decision.package_ref != package.package_ref or decision.package_revision != package.revision:
            raise ValueError("promotion decision does not pin the exact package revision")
        if decision.candidate_pins != package.candidate_pins:
            raise ValueError("promotion decision candidate pins differ from package")
        for grant in decision.use_grants:
            stored_candidate = self.store.get_record(
                grant.candidate_pin.record_kind, grant.candidate_pin.record_ref, grant.candidate_pin.revision
            )
            if (
                stored_candidate is None
                or stored_candidate.record_fingerprint != grant.candidate_pin.record_fingerprint
                or not record_supports_use(grant.candidate_pin.record_kind, stored_candidate.payload, grant.operation)
            ):
                raise ValueError("promotion decision grants an operation incompatible with the exact candidate structural contract")
        resolution = LearningDependencyResolver(self.store).resolve(package)
        if not resolution.valid:
            raise ValueError("promotion refused: package dependencies are stale, missing, cyclic, or over budget")
        with self.store.snapshot() as snapshot:
            self._validate_competence_pins(package, decision)
            operations: list[PatchOperation] = []
            decision_dependency_items = [
                *(
                    RecordDependency(pin.record_kind, pin.record_ref, pin.revision, pin.record_fingerprint, "promotion_candidate")
                    for pin in package.candidate_pins
                ),
                *(
                    RecordDependency(pin.record_kind, pin.record_ref, pin.revision, pin.record_fingerprint, "promotion_dependency")
                    for pin in package.dependency_pins
                ),
                RecordDependency(
                    RecordKind.LEARNING_PACKAGE, package.package_ref, package.revision,
                    self._stored_fingerprint(RecordKind.LEARNING_PACKAGE, package.package_ref, package.revision),
                    "promotion_package",
                ),
            ]
            # Promotion authority must depend on the exact competence and evidence
            # substrate, not just on the candidate records. This makes correction/
            # retraction invalidation traverse mechanically through durable edges.
            for result_ref in sorted({ref for grant in decision.use_grants for ref in grant.competence_result_refs}):
                stored_result = self.store.get_record(RecordKind.COMPETENCE_RESULT, result_ref)
                if stored_result is None:
                    raise ValueError(f"missing competence result during promotion: {result_ref}")
                decision_dependency_items.append(RecordDependency(
                    RecordKind.COMPETENCE_RESULT, result_ref, stored_result.revision,
                    stored_result.record_fingerprint, "promotion_competence",
                ))
            for link_ref in sorted(set((*package.evidence_link_refs, *package.counterexample_link_refs))):
                stored_link = self.store.get_record(RecordKind.LEARNING_EVIDENCE_LINK, link_ref)
                if stored_link is None or not isinstance(stored_link.payload, LearningEvidenceLink):
                    raise ValueError(f"missing learning evidence link during promotion: {link_ref}")
                link = stored_link.payload
                if link.package_ref != package.package_ref or link.package_revision != package.revision:
                    raise ValueError("promotion evidence link does not belong to the exact package revision")
                decision_dependency_items.append(RecordDependency(
                    RecordKind.LEARNING_EVIDENCE_LINK, link_ref, stored_link.revision,
                    stored_link.record_fingerprint, "promotion_evidence_link",
                ))
                for evidence_ref in link.evidence_refs:
                    stored_evidence = self.store.get_record(RecordKind.EVIDENCE, evidence_ref)
                    if stored_evidence is None:
                        raise ValueError(f"promotion evidence is unresolved: {evidence_ref}")
                    decision_dependency_items.append(RecordDependency(
                        RecordKind.EVIDENCE, evidence_ref, stored_evidence.revision,
                        stored_evidence.record_fingerprint, "promotion_evidence",
                    ))
            deduped_dependencies = {}
            for dep in decision_dependency_items:
                prior = deduped_dependencies.get(dep.record_ref)
                if prior is not None and (
                    prior.record_kind, prior.revision, prior.fingerprint
                ) != (dep.record_kind, dep.revision, dep.fingerprint):
                    raise ValueError(
                        f"promotion dependency ref resolves to conflicting exact identities: {dep.record_ref}"
                    )
                deduped_dependencies.setdefault(dep.record_ref, dep)
            decision_dependencies = tuple(
                deduped_dependencies[key] for key in sorted(deduped_dependencies)
            )
            operations.append(self._upsert_operation(
                RecordKind.PROMOTION_DECISION,
                decision,
                dependencies=decision_dependencies,
                reason="persist exact reviewed per-use promotion decision",
            ))
            decision_fingerprint = record_fingerprints(RecordKind.PROMOTION_DECISION, decision)[1]
            promoted_count = 0
            for pin in package.candidate_pins:
                grants = decision.grants_for(pin)
                if not grants:
                    continue
                source = self.store.get_record(pin.record_kind, pin.record_ref, pin.revision)
                if source is None or source.record_fingerprint != pin.record_fingerprint:
                    raise ValueError("candidate changed after promotion decision")
                promoted = self._promoted_revision(pin, source.payload, grants, package.permission_ref)
                if promoted is None:
                    continue
                promoted_count += 1
                deps = [
                    RecordDependency(RecordKind.PROMOTION_DECISION, decision.decision_ref, decision.revision, decision_fingerprint, "promotion_decision"),
                    RecordDependency(pin.record_kind, pin.record_ref, pin.revision, pin.record_fingerprint, "promotion_source_candidate"),
                ]
                for result_ref in sorted({ref for grant in grants for ref in grant.competence_result_refs}):
                    stored_result = self.store.get_record(RecordKind.COMPETENCE_RESULT, result_ref)
                    if stored_result is None:
                        raise ValueError(f"missing competence result during promotion: {result_ref}")
                    deps.append(RecordDependency(
                        RecordKind.COMPETENCE_RESULT, result_ref, stored_result.revision,
                        stored_result.record_fingerprint, "promotion_competence",
                    ))
                deps.extend(
                    RecordDependency(dep.record_kind, dep.record_ref, dep.revision, dep.record_fingerprint, "promotion_dependency")
                    for dep in package.dependency_pins
                )
                operations.append(self._upsert_operation(
                    pin.record_kind,
                    promoted,
                    dependencies=tuple(deps),
                    expected_record_revision=self._latest_revision(pin.record_kind, pin.record_ref),
                    expected_record_fingerprint=self._latest_fingerprint(pin.record_kind, pin.record_ref),
                    reason="activate exact candidate only for competence-authorized uses",
                ))
            if promoted_count == 0:
                raise ValueError("promotion decision produced no promotable canonical record revisions")
            promoted_package = replace(
                package,
                revision=package.revision + 1,
                supersedes_revision=package.revision,
                lifecycle_status=LearningPackageStatus.PROMOTED,
                metadata={
                    **dict(package.metadata),
                    "promotion_decision_ref": decision.decision_ref,
                    "authority_source_package_revision": package.revision,
                },
            )
            operations.append(self._upsert_operation(
                RecordKind.LEARNING_PACKAGE,
                promoted_package,
                dependencies=(RecordDependency(
                    RecordKind.PROMOTION_DECISION, decision.decision_ref, decision.revision, decision_fingerprint, "promotion_decision"
                ),),
                expected_record_revision=package.revision,
                expected_record_fingerprint=self._stored_fingerprint(RecordKind.LEARNING_PACKAGE, package.package_ref, package.revision),
                reason="advance package lifecycle only in same CAS transaction as semantic promotion",
            ))
            patch = GraphPatch(
                patch_ref="graph-patch:promotion:" + semantic_fingerprint(
                    "learning-promotion-patch", (decision.decision_ref, snapshot.fingerprint), 24
                ),
                context_ref="learning:promotion",
                scope_ref=package.scope_ref,
                source_ref=decision.policy_ref,
                permission_ref=package.permission_ref,
                operations=tuple(operations),
                expected_store_revision=snapshot.store_revision,
                validation_requirements=(
                    "phase13_exact_per_use_promotion",
                    "phase13_promotion_decision_required",
                    "phase13_independent_competence_required",
                ),
                metadata={"phase": 13, "authoritative_promotion": True, "decision_ref": decision.decision_ref},
            )
        return self.store.apply_patch(patch)

    def _validate_competence_pins(self, package: LearningPackageRecord, decision: PromotionDecisionRecord) -> None:
        source_lineage = set(package.source_lineage_refs)
        for grant in decision.use_grants:
            if grant.decision == UseDecision.PRESERVE_ONLY:
                continue
            for result_ref in grant.competence_result_refs:
                stored = self.store.get_record(RecordKind.COMPETENCE_RESULT, result_ref)
                if stored is None or not isinstance(stored.payload, CompetenceResultRecord):
                    raise ValueError("promotion competence result is missing")
                result = stored.payload
                if result.package_ref != package.package_ref or result.package_revision != package.revision:
                    raise ValueError("promotion attempted to reuse competence from another package revision")
                if result.use_operation != grant.operation:
                    raise ValueError("promotion competence use does not match granted use")
                if result.candidate_pins != package.candidate_pins or result.dependency_pins != package.dependency_pins:
                    raise ValueError("promotion competence substrate differs from exact package")
                if result.outcome != CompetenceOutcome.PASSED and grant.decision == UseDecision.ALLOW:
                    raise ValueError("allow promotion requires passed competence")
                if grant.decision == UseDecision.PROVISIONAL and result.outcome not in {CompetenceOutcome.PASSED, CompetenceOutcome.PARTIAL}:
                    raise ValueError("provisional promotion requires passed or partial competence")
                if source_lineage.intersection(result.independent_lineage_refs):
                    raise ValueError("promotion competence is not independent of induction/source lineage")
                if result.snapshot_revision > self.store.revision:
                    raise ValueError("competence result claims a future store revision")
                # Exact candidate/dependency fingerprints are revalidated at the
                # current snapshot; stale competence is never reusable.
                for pin in (*result.candidate_pins, *result.dependency_pins):
                    current = self.store.get_record(pin.record_kind, pin.record_ref, pin.revision)
                    if current is None or current.record_fingerprint != pin.record_fingerprint:
                        raise ValueError("stale competence result after dependency/candidate change")

    def _promoted_revision(
        self, pin: PinnedRecord, record, grants: tuple[PromotionUseGrant, ...], permission_ref: str
    ):
        if not hasattr(record, "revision"):
            return None
        latest = self._latest_revision(pin.record_kind, pin.record_ref)
        revision = max(latest, int(getattr(record, "revision"))) + 1
        prior_authority = self._prior_authority_revision(pin.record_kind, pin.record_ref)
        kwargs = {"revision": revision}
        if hasattr(record, "supersedes_revision"):
            kwargs["supersedes_revision"] = prior_authority
        if hasattr(record, "permission_ref"):
            kwargs["permission_ref"] = permission_ref
        if isinstance(record, MeaningSchema):
            grant_map = {item.operation: item.decision for item in grants}
            authorizations = []
            for operation in UseOperation:
                decision = grant_map.get(operation)
                if decision is None:
                    previous = record.use_profile.decision_for(operation)
                    decision = UseDecision.PRESERVE_ONLY if previous == UseDecision.PRESERVE_ONLY else UseDecision.DENY
                if decision != UseDecision.DENY:
                    authorizations.append(UseAuthorization(operation, decision, reason="phase13 promotion decision"))
            positive = {item.decision for item in authorizations}
            lifecycle = (
                SchemaLifecycleStatus.ACTIVE if UseDecision.ALLOW in positive
                else SchemaLifecycleStatus.PROVISIONAL
            )
            return replace(record, **kwargs, lifecycle_status=lifecycle, use_profile=UseProfile(tuple(authorizations)))
        if hasattr(record, "lifecycle_status"):
            positive = {item.decision for item in grants}
            if positive == {UseDecision.PRESERVE_ONLY}:
                return None
            lifecycle = (
                SchemaLifecycleStatus.ACTIVE if UseDecision.ALLOW in positive
                else SchemaLifecycleStatus.PROVISIONAL
            )
            return replace(record, **kwargs, lifecycle_status=lifecycle)
        return None

    def _prior_authority_revision(self, kind: RecordKind, ref: str) -> int | None:
        revisions = []
        for stored in self.store.records(kind, all_revisions=True):
            if stored.record_ref != ref:
                continue
            lifecycle = getattr(stored.payload, "lifecycle_status", None)
            if lifecycle == SchemaLifecycleStatus.ACTIVE:
                revisions.append(stored.revision)
        return max(revisions) if revisions else None

    def _latest_revision(self, kind: RecordKind, ref: str) -> int:
        revisions = [item.revision for item in self.store.records(kind, all_revisions=True) if item.record_ref == ref]
        return max(revisions) if revisions else 0

    def _latest_fingerprint(self, kind: RecordKind, ref: str) -> str | None:
        revision = self._latest_revision(kind, ref)
        if revision == 0:
            return None
        stored = self.store.get_record(kind, ref, revision)
        return None if stored is None else stored.record_fingerprint

    def _stored_fingerprint(self, kind: RecordKind, ref: str, revision: int) -> str:
        stored = self.store.get_record(kind, ref, revision)
        if stored is None:
            raise ValueError(f"missing exact record {kind.value}:{ref}@{revision}")
        return stored.record_fingerprint

    @staticmethod
    def _upsert_operation(
        kind: RecordKind,
        record,
        *,
        dependencies: tuple[RecordDependency, ...] = (),
        expected_record_revision: int | None = None,
        expected_record_fingerprint: str | None = None,
        reason: str,
    ) -> PatchOperation:
        if kind == RecordKind.LEARNING_PACKAGE:
            target_ref = record.package_ref
        elif kind == RecordKind.PROMOTION_DECISION:
            target_ref = record.decision_ref
        else:
            from ..storage.codec import record_ref
            target_ref = record_ref(kind, record)
        revision = record_revision(kind, record)
        return PatchOperation(
            operation_ref="patch-operation:promotion:" + semantic_fingerprint(
                "promotion-operation", (kind.value, target_ref, revision, reason), 20
            ),
            operation_kind=PatchOperationKind.UPSERT,
            record_kind=kind,
            target_ref=target_ref,
            record_revision=revision,
            payload=encode_record(kind, record),
            expected_record_revision=expected_record_revision,
            expected_record_fingerprint=expected_record_fingerprint,
            dependencies=dependencies,
            reason=reason,
        )
