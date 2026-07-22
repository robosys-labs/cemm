"""Strict post-pass Phase-14 competence and promotion maintenance.

Promotion is deliberately not a Stage-11/13 side effect.  This service consumes explicit
package-targeted maintenance events after the semantic-pass lease is released.  It may run
independent competence for installed executors and may publish only the exact package
revision whose evidence, candidate pins, dependency pins, competence, review and activation
authorization all validate.
"""
from __future__ import annotations

from ..maintenance import MaintenanceTrigger
from ..schema.model import UseDecision
from ..storage.model import RecordKind
from .competence import LearningCompetenceRunner
from .frontier import EvidenceAggregator
from .model import LearningPackageStatus, PromotionDecisionKind
from .phase14_model_v351 import PromotionMaintenanceResultV351
from .promotion import PromotionCoordinator, PromotionPolicyEngine
from ..schema.model import semantic_fingerprint


class Phase14LearningMaintenanceV351:
    RUNTIME_ABI = "v351-phase14"
    SERVICE_KIND = "event_driven_learning_maintenance_v351"

    _ELIGIBLE_TRIGGERS = frozenset({
        MaintenanceTrigger.LEARNING_EVIDENCE_CHANGED,
        MaintenanceTrigger.COMPETENCE_COMPLETED,
        MaintenanceTrigger.REVIEW_DECISION,
        MaintenanceTrigger.EXPLICIT_CONSOLIDATION,
    })

    def __init__(self, store, *, competence_executors=None) -> None:
        self.store = store
        self.competence_executors = dict(competence_executors or {})

    def handle(self, event):
        before = self.store.current_read_generation().authority_generation
        if event.trigger not in self._ELIGIBLE_TRIGGERS:
            return self._result(event, before, before, (), (), (), ("maintenance:trigger-not-eligible",))
        # Empty event scope is intentionally a no-op.  Phase 14 forbids request-frequency
        # global scans that silently promote unrelated packages.
        package_refs = tuple(sorted(set(event.ref_set)))
        if not package_refs:
            return self._result(event, before, before, (), (), (), ("maintenance:explicit-package-refs-required",))

        promoted = []
        decisions = []
        blocked = []
        replay = []
        for package_ref in package_refs:
            stored = self.store.get_record(RecordKind.LEARNING_PACKAGE, package_ref)
            if stored is None:
                blocked.append(f"{package_ref}:missing")
                continue
            package = stored.payload
            expected_scope = f"learning:{event.context_ref}"
            if package.scope_ref not in {expected_scope, "global"}:
                blocked.append(f"{package_ref}:scope-mismatch")
                continue
            if package.permission_ref not in {event.permission_ref, "public"}:
                blocked.append(f"{package_ref}:permission-mismatch")
                continue
            if package.lifecycle_status in {
                LearningPackageStatus.PROMOTED, LearningPackageStatus.SUPERSEDED,
                LearningPackageStatus.RETRACTED, LearningPackageStatus.INVALIDATED,
                LearningPackageStatus.REJECTED,
            }:
                continue
            if package.lifecycle_status not in {
                LearningPackageStatus.CANDIDATE, LearningPackageStatus.EVIDENCE_ACCUMULATING,
                LearningPackageStatus.COMPETENCE_PENDING, LearningPackageStatus.PROMOTABLE,
            }:
                blocked.append(f"{package_ref}:lifecycle:{package.lifecycle_status.value}")
                continue

            requested_positive = tuple(
                item for item in package.requested_use_authorizations
                if item.decision in {UseDecision.ALLOW, UseDecision.PROVISIONAL}
            )
            executor_pins = dict(package.metadata.get("competence_executor_pins", {}) or {})
            if requested_positive:
                missing_executor_pins = tuple(
                    item.operation.value for item in requested_positive
                    if item.operation.value not in executor_pins
                )
                if missing_executor_pins:
                    blocked.append(
                        f"{package_ref}:competence-executor-pin-required:{','.join(sorted(missing_executor_pins))}"
                    )
                    continue
            competence = list(self._competence_for(package, executor_pins))
            if requested_positive and package.competence_case_refs:
                completed = {item.use_operation for item in competence}
                for authorization in requested_positive:
                    if authorization.operation in completed:
                        continue
                    executor = self.competence_executors.get(authorization.operation.value)
                    if executor is None:
                        continue
                    raw_pin = executor_pins[authorization.operation.value]
                    if not isinstance(raw_pin, dict):
                        blocked.append(f"{package_ref}:invalid-competence-executor-pin:{authorization.operation.value}")
                        continue
                    runner_ref = str(raw_pin.get("runner_ref", ""))
                    runner_revision = str(raw_pin.get("runner_revision", ""))
                    if not runner_ref or not runner_revision:
                        blocked.append(f"{package_ref}:invalid-competence-executor-pin:{authorization.operation.value}")
                        continue
                    declared_ref = str(getattr(executor, "COMPETENCE_RUNNER_REF", ""))
                    declared_revision = str(getattr(executor, "COMPETENCE_RUNNER_REVISION", ""))
                    if (declared_ref, declared_revision) != (runner_ref, runner_revision):
                        blocked.append(f"{package_ref}:competence-executor-identity-mismatch:{authorization.operation.value}")
                        continue
                    runner = LearningCompetenceRunner(
                        self.store, runner_ref=runner_ref, runner_revision=runner_revision
                    )
                    result = runner.run(package, authorization.operation, executor)
                    persisted = runner.persist(result)
                    if getattr(persisted, "committed", False):
                        competence.append(result)
                        completed.add(authorization.operation)

            # No review or activation authorization is synthesized by maintenance.
            if not package.review_refs or not tuple(package.metadata.get("authorization_refs", ()) or ()):
                blocked.append(f"{package_ref}:review-or-authorization-required")
                continue
            if requested_positive and not package.competence_case_refs:
                blocked.append(f"{package_ref}:competence-cases-required")
                continue

            evidence_links = tuple(
                item.payload for item in self.store.repositories.learning_evidence_links.all(all_revisions=True)
                if item.payload.package_ref == package.package_ref
                and item.payload.package_revision == package.revision
            )
            summary = EvidenceAggregator.summarize(evidence_links)
            engine = PromotionPolicyEngine(self.store)
            result = engine.evaluate(package, tuple(competence), summary)
            if result.decision != PromotionDecisionKind.PROMOTE:
                blocked.extend(f"{package_ref}:{reason}" for reason in (result.blocked_reasons or (result.decision.value,)))
                continue
            decision = engine.decision_record(
                package,
                result,
                policy_ref=package.promotion_policy_ref,
                review_refs=tuple(package.review_refs),
                authorization_refs=tuple(package.metadata.get("authorization_refs", ()) or ()),
                risk_refs=tuple(package.metadata.get("risk_refs", ()) or ()),
            )
            try:
                commit = PromotionCoordinator(self.store).promote(package, decision)
            except (ValueError, RuntimeError) as exc:
                blocked.append(f"{package_ref}:promotion-blocked:{type(exc).__name__}")
                continue
            if not getattr(commit, "committed", False):
                blocked.append(f"{package_ref}:promotion-cas-conflict")
                continue
            promoted.append(package_ref)
            decisions.append(decision.decision_ref)
            replay.append("replay:authority-generation-changed:" + package_ref)

        after = self.store.current_read_generation().authority_generation
        return self._result(event, before, after, promoted, decisions, replay, blocked)

    def _competence_for(self, package, executor_pins):
        results = []
        for item in self.store.repositories.competence_results.all(all_revisions=True):
            result = item.payload
            if result.package_ref != package.package_ref or result.package_revision != package.revision:
                continue
            raw_pin = executor_pins.get(result.use_operation.value)
            if not isinstance(raw_pin, dict):
                continue
            if (
                str(raw_pin.get("runner_ref", "")) != result.runner_ref
                or str(raw_pin.get("runner_revision", "")) != result.runner_revision
            ):
                continue
            results.append(result)
        return tuple(results)

    @staticmethod
    def _result(event, before, after, promoted, decisions, replay, blocked):
        return PromotionMaintenanceResultV351(
            result_ref="promotion-maintenance-result:" + semantic_fingerprint(
                "phase14-promotion-maintenance-result",
                (event.trigger.value, tuple(event.ref_set), before, after, tuple(promoted), tuple(decisions), tuple(blocked)),
                24,
            ),
            promoted_package_refs=tuple(sorted(set(promoted))),
            decision_refs=tuple(sorted(set(decisions))),
            authority_generation_before=int(before),
            authority_generation_after=int(after),
            restart_required=bool(after != before),
            replay_requirement_refs=tuple(sorted(set(replay))),
            blocked_refs=tuple(sorted(set(blocked))),
        )


__all__ = ["Phase14LearningMaintenanceV351"]
