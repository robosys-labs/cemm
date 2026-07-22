"""Stage-13 composite commit for session cognition plus Phase-14 learning artifacts.

Candidate semantic records are persisted in candidate/provisional lifecycle only.  The
runtime generation classifier therefore treats them as audit learning state, not active
authority.  No Stage-13 path publishes an ACTIVE semantic revision.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from ..conversation.commit_v351 import SessionMemoryCommitCoordinatorV351
from ..orchestration import StageExecutionStatus, StageOutcome
from ..maintenance import MaintenanceEvent, MaintenanceTrigger
from ..schema.model import semantic_fingerprint
from ..storage.codec import (
    encode_record, record_fingerprints, record_lifecycle, record_ref, record_revision,
)
from ..storage.model import (
    EvidenceRecord, GraphPatch, PatchOperation, PatchOperationKind, RecordDependency, RecordKind,
)
from .inducers_v351 import candidate_pin
from .model import (
    EvidencePolarity, FrontierResolutionStatus, LearningEvidenceLink, LearningPackageStatus, PinnedRecord,
)
from .package import PackageAssembler
from .phase14_model_v351 import DynamicsParameterCandidateV351, LearningCandidateWorkItemV351


class Stage13LearningCommitterV351:
    RUNTIME_ABI = "v351-phase14"
    SERVICE_KIND = "authorized_learning_candidate_committer_v351"

    def __init__(self, session_memory) -> None:
        self.session_commit = SessionMemoryCommitCoordinatorV351(session_memory)
        self.package_assembler = PackageAssembler()

    def commit(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        # Durable candidate/evidence persistence is attempted before mutating bounded
        # session memory. A durable CAS conflict therefore cannot leave the session advanced
        # while the learning DAG failed to commit. Session commit remains after the learning
        # transaction and is idempotently replayable if it independently conflicts.
        raw_work = tuple(cycle.artifacts.get("learning_candidate_work", ()) or ())
        work_items = tuple(item for item in raw_work if isinstance(item, LearningCandidateWorkItemV351))
        parameter_candidates = tuple(item for item in raw_work if isinstance(item, DynamicsParameterCandidateV351))
        # Filter structurally terminal frontiers before staging candidate records.  A stale
        # Stage-11 work item may race a correction/retraction commit; preserving it as an
        # orphan candidate would not publish authority, but would create misleading audit
        # state and future package ambiguity.
        eligible_work = []
        for work in work_items:
            current_frontier = store.get_record(RecordKind.LEARNING_FRONTIER, work.frontier.frontier_ref)
            if current_frontier is not None and current_frontier.payload.resolution_status in {
                FrontierResolutionStatus.RESOLVED, FrontierResolutionStatus.SUPERSEDED,
            }:
                continue
            if work.proposals:
                pre_candidate_pins = tuple(candidate_pin(p.record_kind, p.payload) for p in work.proposals)
                pre_candidate_keys = {pin.key for pin in pre_candidate_pins}
                pre_dependency_pins = tuple(sorted({
                    dep for proposal in work.proposals for dep in proposal.dependency_pins
                    if dep.key not in pre_candidate_keys
                }, key=lambda item: item.key))
                pre_package = self.package_assembler.assemble(
                    package_family=str(work.frontier.metadata.get("phase14_family") or work.frontier.missing_contract),
                    candidate_pins=pre_candidate_pins,
                    dependency_pins=pre_dependency_pins,
                    frontier_refs=(work.frontier.frontier_ref,),
                    evidence_link_refs=(), counterexample_link_refs=(),
                    competence_case_refs=work.competence_case_refs,
                    requested_use_authorizations=work.requested_uses,
                    promotion_policy_ref=work.promotion_policy_ref,
                    review_refs=work.review_refs, provenance_refs=(work.work_ref,),
                    source_lineage_refs=work.source_lineage_refs,
                    scope_ref=f"learning:{cycle.context_ref}", permission_ref=cycle.permission_ref,
                )
                current_package = store.get_record(RecordKind.LEARNING_PACKAGE, pre_package.package_ref)
                if current_package is not None and current_package.payload.lifecycle_status in {
                    LearningPackageStatus.PROMOTED, LearningPackageStatus.SUPERSEDED,
                    LearningPackageStatus.RETRACTED, LearningPackageStatus.INVALIDATED,
                    LearningPackageStatus.REJECTED,
                }:
                    # A terminal package owns the exact candidate identity. Do not stage
                    # orphan candidate/evidence records before discovering that terminal state.
                    continue
            eligible_work.append(work)
        work_items = tuple(eligible_work)
        if not work_items:
            session_outcome = self.session_commit.commit(
                cycle=cycle, capability=capability, store=store, effect_store=effect_store,
                semantic_capabilities=semantic_capabilities,
            )
            if session_outcome.status is not StageExecutionStatus.PERFORMED:
                return session_outcome
            return StageOutcome(
                StageExecutionStatus.PERFORMED,
                artifacts={
                    "commit_receipts": tuple(session_outcome.artifacts.get("commit_receipts", ()) or ()),
                    "committed_read_generation": capability.read_generation,
                    "_parameter_candidates_pending_calibration": parameter_candidates,
                },
                frontier_refs=session_outcome.frontier_refs,
            )

        operations = []
        proof_refs = []
        staged_pins: dict[tuple[str, str, int], PinnedRecord] = {}
        package_refs = []
        evidence_envelopes = tuple(cycle.artifacts.get("evidence_envelopes", ()) or ())
        envelope_by_ref = {str(getattr(item, "evidence_ref", "")): item for item in evidence_envelopes}

        # 1) Stage exact candidate records.  Candidate lifecycles are mandatory; an
        # inducer is never allowed to smuggle ACTIVE authority into Stage 13.
        proposal_by_pin = {}
        for work in sorted(work_items, key=lambda item: item.work_ref):
            for proposal in work.proposals:
                pin = candidate_pin(proposal.record_kind, proposal.payload)
                lifecycle = record_lifecycle(proposal.record_kind, proposal.payload)
                if lifecycle in {"active", "competence_verified"}:
                    raise ValueError(
                        f"Stage 13 refuses authoritative candidate payload:{proposal.record_kind.value}:{pin.record_ref}"
                    )
                previous = proposal_by_pin.get(pin.key)
                if previous is not None and candidate_pin(previous.record_kind, previous.payload) != pin:
                    raise ValueError("candidate identity collision inside one Stage-13 batch")
                proposal_by_pin[pin.key] = proposal
                staged_pins[pin.key] = pin

        for key in sorted(proposal_by_pin):
            proposal = proposal_by_pin[key]
            pin = staged_pins[key]
            current = store.get_record(pin.record_kind, pin.record_ref, pin.revision)
            if current is not None:
                if current.record_fingerprint != pin.record_fingerprint:
                    raise ValueError("existing candidate exact pin differs from induced candidate")
                continue
            deps = tuple(self._dependency(pin_item, "candidate_exact_dependency") for pin_item in proposal.dependency_pins)
            operations.append(PatchOperation(
                operation_ref="patch-operation:phase14-candidate:" + semantic_fingerprint(
                    "phase14-candidate-op", (pin.key, pin.record_fingerprint), 20
                ),
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=pin.record_kind,
                target_ref=pin.record_ref,
                record_revision=pin.revision,
                payload=encode_record(pin.record_kind, proposal.payload),
                dependencies=deps,
                reason="persist non-authoritative exact Phase-14 candidate",
            ))
            proof_refs.extend(proposal.evidence_refs)

        # 2) Persist attributable evidence identities used by learning links.  Existing
        # exact evidence is reused; missing source-span evidence is materialized with its
        # original ref and cycle/source lineage, never synthesized as semantic truth.
        evidence_refs = sorted({ref for work in work_items for p in work.proposals for ref in p.evidence_refs})
        lineage_by_evidence = {}
        for work in work_items:
            for proposal in work.proposals:
                for ref in proposal.evidence_refs:
                    lineage_by_evidence.setdefault(ref, set()).update(work.source_lineage_refs)
        for ref in evidence_refs:
            existing = store.get_record(RecordKind.EVIDENCE, ref)
            if existing is not None:
                continue
            envelope = envelope_by_ref.get(ref)
            source_ref = str(getattr(envelope, "source_ref", "") or f"source:cycle:{cycle.cycle_ref}")
            confidence = float(getattr(envelope, "confidence", 1.0) if envelope is not None else 1.0)
            lineages = tuple(sorted(lineage_by_evidence.get(ref, ())))
            lineage_ref = (
                str(getattr(envelope, "lineage_refs", ())[0])
                if envelope is not None and tuple(getattr(envelope, "lineage_refs", ()) or ())
                else (lineages[0] if lineages else source_ref)
            )
            evidence = EvidenceRecord(
                evidence_ref=ref,
                source_ref=source_ref,
                confidence=max(0.0, min(1.0, confidence)),
                lineage_ref=lineage_ref,
                context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref,
                metadata={
                    "phase14_learning_evidence": True,
                    "cycle_ref": cycle.cycle_ref,
                    "preserves_original_evidence_identity": True,
                },
            )
            operations.append(PatchOperation(
                operation_ref="patch-operation:phase14-evidence:" + semantic_fingerprint(
                    "phase14-evidence-op", ref, 20
                ),
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=RecordKind.EVIDENCE,
                target_ref=ref,
                record_revision=1,
                payload=encode_record(RecordKind.EVIDENCE, evidence),
                reason="persist attributable evidence identity for Phase-14 learning",
            ))

        # 3) Build one exact package per work item. Internal candidate dependencies remain
        # candidate_pins; external prerequisites remain dependency_pins. Evidence links
        # are immutable and point back to the exact package revision.
        for work in sorted(work_items, key=lambda item: item.work_ref):
            if not work.proposals:
                continue
            candidate_pins = tuple(candidate_pin(p.record_kind, p.payload) for p in work.proposals)
            candidate_keys = {pin.key for pin in candidate_pins}
            dependency_pins = tuple(sorted({
                dep for proposal in work.proposals for dep in proposal.dependency_pins
                if dep.key not in candidate_keys
            }, key=lambda item: item.key))
            initial = self.package_assembler.assemble(
                package_family=str(work.frontier.metadata.get("phase14_family") or work.frontier.missing_contract),
                candidate_pins=candidate_pins,
                dependency_pins=dependency_pins,
                frontier_refs=(work.frontier.frontier_ref,),
                evidence_link_refs=(),
                counterexample_link_refs=(),
                competence_case_refs=work.competence_case_refs,
                requested_use_authorizations=work.requested_uses,
                promotion_policy_ref=work.promotion_policy_ref,
                review_refs=work.review_refs,
                provenance_refs=(work.work_ref,),
                source_lineage_refs=work.source_lineage_refs,
                scope_ref=f"learning:{cycle.context_ref}",
                permission_ref=cycle.permission_ref,
            )
            current_package = store.get_record(RecordKind.LEARNING_PACKAGE, initial.package_ref)
            if current_package is not None and current_package.payload.lifecycle_status in {
                LearningPackageStatus.PROMOTED,
                LearningPackageStatus.SUPERSEDED,
                LearningPackageStatus.RETRACTED,
                LearningPackageStatus.INVALIDATED,
                LearningPackageStatus.REJECTED,
            }:
                # Never reopen a completed authority package in place. New contradictory
                # evidence must create a correction/supersession work item explicitly.
                continue
            package_revision = 1 if current_package is None else current_package.revision + 1
            link_refs = []
            links = []
            for pin in candidate_pins:
                proposal = next(p for p in work.proposals if candidate_pin(p.record_kind, p.payload).key == pin.key)
                link_ref = "learning-evidence-link:" + semantic_fingerprint(
                    "phase14-learning-link",
                    (initial.package_ref, package_revision, pin.key, proposal.evidence_refs, work.source_lineage_refs),
                    24,
                )
                link_refs.append(link_ref)
                links.append(LearningEvidenceLink(
                    link_ref=link_ref,
                    package_ref=initial.package_ref,
                    package_revision=package_revision,
                    polarity=EvidencePolarity.SUPPORT,
                    evidence_refs=tuple(sorted(set(proposal.evidence_refs))),
                    source_lineage_refs=tuple(sorted(set(work.source_lineage_refs))),
                    candidate_pin=pin,
                    context_ref=cycle.context_ref,
                    permission_ref=cycle.permission_ref,
                    metadata={"work_ref": work.work_ref, "phase": 14},
                ))
            package = replace(
                initial,
                revision=package_revision,
                supersedes_revision=None if current_package is None else current_package.revision,
                evidence_link_refs=tuple(sorted(link_refs)),
                lifecycle_status=(
                    LearningPackageStatus.COMPETENCE_PENDING
                    if (
                        tuple(work.requested_uses) and tuple(work.competence_case_refs)
                        and tuple(link_refs)
                    )
                    else LearningPackageStatus.EVIDENCE_ACCUMULATING
                ),
                metadata={
                    "phase": 14,
                    "candidate_not_authority": True,
                    "authorization_refs": tuple(work.authorization_refs),
                    "risk_refs": tuple(work.risk_refs),
                    "deferred_reason_refs": tuple(work.deferred_reason_refs),
                    "event_driven": True,
                },
            )
            package_refs.append(package.package_ref)

            # Frontier revision is evidence-accumulating and structural-key stable.
            frontier = work.frontier
            current_frontier = store.get_record(RecordKind.LEARNING_FRONTIER, frontier.frontier_ref)
            if current_frontier is not None and current_frontier.payload.resolution_status in {
                FrontierResolutionStatus.RESOLVED, FrontierResolutionStatus.SUPERSEDED,
            }:
                # Never reopen a completed frontier by accumulating unrelated later evidence.
                # A correction/retraction must classify to a new structural frontier identity.
                package_refs.pop()
                continue
            if current_frontier is not None:
                old = current_frontier.payload
                frontier = replace(
                    frontier,
                    revision=current_frontier.revision + 1,
                    supersedes_revision=current_frontier.revision,
                    evidence_refs=tuple(sorted(set((*old.evidence_refs, *frontier.evidence_refs)))),
                    candidate_refs=tuple(sorted(set((*old.candidate_refs, *(f"{p.record_ref}@{p.revision}" for p in candidate_pins))))),
                )
            else:
                frontier = replace(
                    frontier,
                    candidate_refs=tuple(sorted(set((*frontier.candidate_refs, *(f"{p.record_ref}@{p.revision}" for p in candidate_pins))))),
                )
            frontier_fp = record_fingerprints(RecordKind.LEARNING_FRONTIER, frontier)[1]
            operations.append(PatchOperation(
                operation_ref="patch-operation:phase14-frontier:" + semantic_fingerprint(
                    "phase14-frontier-op", (frontier.frontier_ref, frontier.revision), 20
                ),
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=RecordKind.LEARNING_FRONTIER,
                target_ref=frontier.frontier_ref,
                record_revision=frontier.revision,
                payload=encode_record(RecordKind.LEARNING_FRONTIER, frontier),
                expected_record_revision=None if current_frontier is None else current_frontier.revision,
                expected_record_fingerprint=None if current_frontier is None else current_frontier.record_fingerprint,
                reason="accumulate structural Phase-14 learning frontier",
            ))

            package_fp = record_fingerprints(RecordKind.LEARNING_PACKAGE, package)[1]
            for link in links:
                link_deps = [
                    RecordDependency(
                        RecordKind.LEARNING_PACKAGE,
                        package.package_ref,
                        package.revision,
                        package_fp,
                        "learning_package",
                    ),
                    self._dependency(link.candidate_pin, "learning_candidate"),
                ]
                for evidence_ref in link.evidence_refs:
                    evidence_stored = store.get_record(RecordKind.EVIDENCE, evidence_ref)
                    if evidence_stored is not None:
                        link_deps.append(RecordDependency(
                            RecordKind.EVIDENCE,
                            evidence_ref,
                            evidence_stored.revision,
                            evidence_stored.record_fingerprint,
                            "learning_evidence",
                        ))
                    else:
                        # Staged evidence revision 1; compute the exact fingerprint from the
                        # staged EvidenceRecord operation payload.
                        op = next(
                            item for item in operations
                            if item.record_kind == RecordKind.EVIDENCE and item.target_ref == evidence_ref
                        )
                        from ..storage.codec import decode_record
                        payload = decode_record(RecordKind.EVIDENCE, op.payload)
                        link_deps.append(RecordDependency(
                            RecordKind.EVIDENCE,
                            evidence_ref,
                            1,
                            record_fingerprints(RecordKind.EVIDENCE, payload)[1],
                            "learning_evidence",
                        ))
                operations.append(PatchOperation(
                    operation_ref="patch-operation:phase14-evidence-link:" + semantic_fingerprint(
                        "phase14-evidence-link-op", link.link_ref, 20
                    ),
                    operation_kind=PatchOperationKind.UPSERT,
                    record_kind=RecordKind.LEARNING_EVIDENCE_LINK,
                    target_ref=link.link_ref,
                    record_revision=1,
                    payload=encode_record(RecordKind.LEARNING_EVIDENCE_LINK, link),
                    dependencies=tuple(link_deps),
                    reason="persist immutable attributable Phase-14 learning evidence",
                ))

            package_deps = [
                *(self._dependency(pin, "learning_candidate") for pin in candidate_pins),
                *(self._dependency(pin, "learning_dependency") for pin in dependency_pins),
                RecordDependency(
                    RecordKind.LEARNING_FRONTIER,
                    frontier.frontier_ref,
                    frontier.revision,
                    frontier_fp,
                    "learning_frontier",
                ),
            ]
            for link in links:
                package_deps.append(RecordDependency(
                    RecordKind.LEARNING_EVIDENCE_LINK,
                    link.link_ref,
                    1,
                    record_fingerprints(RecordKind.LEARNING_EVIDENCE_LINK, link)[1],
                    "learning_evidence_link",
                ))
            operations.append(PatchOperation(
                operation_ref="patch-operation:phase14-package:" + semantic_fingerprint(
                    "phase14-package-op", (package.package_ref, package.revision), 20
                ),
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=RecordKind.LEARNING_PACKAGE,
                target_ref=package.package_ref,
                record_revision=package.revision,
                payload=encode_record(RecordKind.LEARNING_PACKAGE, package),
                expected_record_revision=None if current_package is None else current_package.revision,
                expected_record_fingerprint=None if current_package is None else current_package.record_fingerprint,
                dependencies=tuple(package_deps),
                reason="persist exact non-authoritative Phase-14 learning package DAG",
            ))
            proof_refs.append(work.work_ref)

        if not operations:
            session_outcome = self.session_commit.commit(
                cycle=cycle, capability=capability, store=store, effect_store=effect_store,
                semantic_capabilities=semantic_capabilities,
            )
            return StageOutcome(
                session_outcome.status,
                artifacts={
                    "commit_receipts": tuple(session_outcome.artifacts.get("commit_receipts", ()) or ()),
                    "committed_read_generation": capability.read_generation,
                    "_parameter_candidates_pending_calibration": parameter_candidates,
                },
                frontier_refs=session_outcome.frontier_refs,
            )

        expected_revision = int(getattr(effect_store.read_store, "revision", getattr(store, "revision", 0)))
        patch = GraphPatch(
            patch_ref="graph-patch:phase14-learning-batch:" + semantic_fingerprint(
                "phase14-learning-batch-patch",
                (cycle.cycle_ref, capability.pass_ref, expected_revision, tuple(item.operation_ref for item in operations)),
                24,
            ),
            context_ref=cycle.context_ref,
            scope_ref=f"learning:{cycle.context_ref}",
            source_ref="source:phase14:stage11-learning-work",
            permission_ref=cycle.permission_ref,
            operations=tuple(operations),
            expected_store_revision=expected_revision,
            evidence_refs=tuple(sorted(set(evidence_refs))),
            validation_requirements=(
                "phase14_exact_candidate_dependency_closure",
                "phase14_candidate_is_not_authority",
                "phase14_attributable_evidence_lineage",
                "phase14_event_driven_promotion_only",
            ),
            metadata={
                "phase": 14,
                "authoritative_promotion": False,
                "candidate_package_refs": tuple(sorted(set(package_refs))),
            },
        )
        result, effect_receipt = effect_store.authorize_and_apply_patch(
            patch,
            proof_refs=tuple(sorted(set(proof_refs))),
            publishes_authority=False,
        )
        if not getattr(result, "committed", False):
            return StageOutcome(
                StageExecutionStatus.DEFERRED,
                frontier_refs=("frontier:commit:learning-cas-conflict",),
                artifacts={
                    "commit_receipts": (),
                    "committed_read_generation": capability.read_generation,
                    "_effect_authorization_receipts": (effect_receipt,),
                },
            )
        session_outcome = self.session_commit.commit(
            cycle=cycle, capability=capability, store=store, effect_store=effect_store,
            semantic_capabilities=semantic_capabilities,
        )
        package_refs = tuple(sorted(set(package_refs)))
        event = MaintenanceEvent(
            MaintenanceTrigger.LEARNING_EVIDENCE_CHANGED, package_refs,
            cycle.context_ref, cycle.permission_ref,
        )
        current_generation = (
            effect_store.base_store.current_read_generation()
            if hasattr(effect_store.base_store, "current_read_generation") else capability.read_generation
        )
        return StageOutcome(
            session_outcome.status,
            artifacts={
                "commit_receipts": tuple((
                    *tuple(session_outcome.artifacts.get("commit_receipts", ()) or ()), result,
                )),
                "committed_read_generation": current_generation,
                "_effect_authorization_receipts": (effect_receipt,),
                "_learning_package_refs": package_refs,
                "_maintenance_events": (event,) if package_refs else (),
                "_parameter_candidates_pending_calibration": parameter_candidates,
            },
            frontier_refs=session_outcome.frontier_refs,
        )

    @staticmethod
    def _dependency(pin: PinnedRecord, kind: str) -> RecordDependency:
        return RecordDependency(
            pin.record_kind,
            pin.record_ref,
            pin.revision,
            pin.record_fingerprint,
            kind,
        )


__all__ = ["Stage13LearningCommitterV351"]
