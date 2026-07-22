"""Ordinary-runtime advancement of proof-bearing learning candidates.

This module deliberately does *not* infer semantic definitions from frequency
or raw text. It closes the previously missing orchestration between typed
frontiers and the existing candidate/package/competence/promotion machinery.

Sources of candidate structure are limited to:
1. exact candidate refs already attached to a frontier; or
2. explicitly installed reviewed CandidateStructureInducer services.

Promotion remains a separate reviewed/per-use authority boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from ..schema.model import UseAuthorization, UseDecision, UseOperation, semantic_fingerprint
from ..storage.codec import encode_record, record_fingerprints, record_ref, record_revision
from ..storage.model import (
    GraphPatch,
    PatchOperation,
    PatchOperationKind,
    RecordDependency,
    RecordKind,
)
from .competence import LearningCompetenceRunner
from .frontier import EvidenceAggregator
from .model import (
    CompetenceOutcome,
    EvidencePolarity,
    LearningEvidenceLink,
    LearningPackageStatus,
    PinnedRecord,
)
from .package import (
    CandidateProposal,
    LearningPackageCommitCoordinator,
    PackageAssembler,
)


@dataclass(frozen=True, slots=True)
class RuntimeLearningAdvanceTrace:
    frontier_refs: tuple[str, ...]
    candidate_refs: tuple[str, ...]
    package_refs: tuple[str, ...]
    competence_result_refs: tuple[str, ...]
    promotable_package_refs: tuple[str, ...]
    deferred_refs: tuple[str, ...]


class RuntimeLearningAdvancer:
    def __init__(
        self,
        store,
        *,
        inducers=(),
        competence_executors=None,
    ) -> None:
        self.store = store
        self.inducers = tuple(inducers)
        self.competence_executors = dict(competence_executors or {})

    def advance(
        self,
        *,
        context_ref: str,
        permission_ref: str,
        frontier_refs: tuple[str, ...] | None = None,
    ) -> RuntimeLearningAdvanceTrace:
        if frontier_refs:
            frontiers = tuple(
                stored.payload
                for ref in sorted(set(frontier_refs))
                for stored in (self.store.get_record(RecordKind.LEARNING_FRONTIER, ref),)
                if stored is not None
                and stored.payload.context_ref in {context_ref, "global"}
                and stored.payload.permission_ref in {permission_ref, "public"}
                and stored.payload.resolution_status.value in {"open", "partial"}
            )
        else:
            frontiers = tuple(
                item.payload
                for item in self.store.repositories.learning_frontiers.all()
                if item.payload.context_ref in {context_ref, "global"}
                and item.payload.permission_ref in {permission_ref, "public"}
                and item.payload.resolution_status.value in {"open", "partial"}
            )
        candidate_refs = []
        package_refs = []
        competence_refs = []
        promotable_refs = []
        deferred = []

        for frontier in frontiers:
            proposals = list(self._existing_candidate_proposals(frontier))
            if not proposals:
                with self.store.snapshot() as snapshot:
                    evidence = EvidenceAggregator.summarize(
                        tuple(
                            item.payload
                            for item in self.store.repositories.learning_evidence_links.all(
                                all_revisions=True,
                                snapshot=snapshot,
                            )
                            if frontier.frontier_ref
                            in getattr(item.payload, "metadata", {}).get(
                                "frontier_refs", ()
                            )
                        )
                    )
                    for inducer in self.inducers:
                        produced = tuple(
                            inducer.induce(
                                frontier,
                                evidence,
                                snapshot=snapshot,
                            )
                        )
                        proposals.extend(produced)
            if not proposals:
                deferred.append(
                    f"learning:awaiting-candidate:{frontier.frontier_ref}"
                )
                continue

            pins, dependency_pins = self._persist_proposals(frontier, tuple(proposals))
            candidate_refs.extend(pin.record_ref for pin in pins)
            if not pins:
                deferred.append(
                    f"learning:candidate-persist-failed:{frontier.frontier_ref}"
                )
                continue

            package, links = self._package(frontier, pins, dependency_pins)
            existing = self.store.get_record(
                RecordKind.LEARNING_PACKAGE, package.package_ref
            )
            if existing is None:
                result = LearningPackageCommitCoordinator(self.store).persist(
                    package,
                    evidence_links=links,
                    source_ref="source:runtime-learning-advance",
                )
                if not result.committed:
                    deferred.append(
                        f"learning:package-persist:{package.package_ref}"
                    )
                    continue
            else:
                package = existing.payload
            package_refs.append(package.package_ref)

            results = self._run_competence(package)
            competence_refs.extend(item.result_ref for item in results)
            promoted = self._mark_promotable_if_ready(package, results)
            if promoted is not None:
                promotable_refs.append(promoted.package_ref)

        return RuntimeLearningAdvanceTrace(
            frontier_refs=tuple(sorted(item.frontier_ref for item in frontiers)),
            candidate_refs=tuple(sorted(set(candidate_refs))),
            package_refs=tuple(sorted(set(package_refs))),
            competence_result_refs=tuple(sorted(set(competence_refs))),
            promotable_package_refs=tuple(sorted(set(promotable_refs))),
            deferred_refs=tuple(sorted(set(deferred))),
        )

    def _existing_candidate_proposals(self, frontier):
        for raw in frontier.candidate_refs:
            ref, revision = self._split_candidate_ref(raw)
            if revision is None:
                continue
            matches = []
            for kind in frontier.expected_record_kinds:
                stored = self.store.get_record(kind, ref, revision)
                if stored is not None:
                    matches.append(stored)
            if len(matches) != 1:
                continue
            stored = matches[0]
            yield CandidateProposal(
                record_kind=stored.record_kind,
                payload=stored.payload,
                evidence_refs=frontier.evidence_refs,
                dependency_pins=(),
                confidence=float(getattr(stored.payload, "confidence", 1.0)),
                proposer_ref="candidate-inducer:existing-exact-frontier-ref",
            )

    @staticmethod
    def _split_candidate_ref(raw: str):
        raw_str = str(raw)
        if "@" not in raw_str:
            return raw_str, None
        ref, revision = raw_str.rsplit("@", 1)
        try:
            return ref, int(revision)
        except ValueError:
            return raw_str, None

    def _persist_proposals(self, frontier, proposals):
        unique = {}
        for proposal in proposals:
            kind = proposal.record_kind
            ref = record_ref(kind, proposal.payload)
            revision = record_revision(kind, proposal.payload)
            unique[(kind, ref, revision)] = proposal
        operations = []
        pins = []
        dependency_pins = {
            pin.key: pin
            for proposal in proposals
            for pin in proposal.dependency_pins
        }
        with self.store.snapshot() as snapshot:
            for (kind, ref, revision), proposal in sorted(
                unique.items(),
                key=lambda item: (
                    item[0][0].value,
                    item[0][1],
                    item[0][2],
                ),
            ):
                existing = self.store.get_record(
                    kind, ref, revision, snapshot=snapshot
                )
                if existing is not None:
                    pins.append(PinnedRecord(
                        kind, ref, revision, existing.record_fingerprint
                    ))
                    continue
                fingerprint = record_fingerprints(
                    kind, proposal.payload
                )[1]
                operations.append(PatchOperation(
                    operation_ref="patch-operation:runtime-learning-candidate:"
                    + semantic_fingerprint(
                        "runtime-learning-candidate",
                        (frontier.frontier_ref, kind.value, ref, revision),
                        20,
                    ),
                    operation_kind=PatchOperationKind.UPSERT,
                    record_kind=kind,
                    target_ref=ref,
                    record_revision=revision,
                    payload=encode_record(kind, proposal.payload),
                    dependencies=tuple(
                        RecordDependency(
                            pin.record_kind,
                            pin.record_ref,
                            pin.revision,
                            pin.record_fingerprint,
                            "candidate_induction_dependency",
                        )
                        for pin in proposal.dependency_pins
                    ),
                    reason=(
                        "persist non-authoritative runtime learning candidate; "
                        "promotion remains per-use and reviewed"
                    ),
                ))
                pins.append(PinnedRecord(kind, ref, revision, fingerprint))
            if operations:
                patch = GraphPatch(
                    patch_ref="graph-patch:runtime-learning-candidates:"
                    + semantic_fingerprint(
                        "runtime-learning-candidates",
                        (
                            frontier.frontier_ref,
                            tuple(op.operation_ref for op in operations),
                            snapshot.fingerprint,
                        ),
                        24,
                    ),
                    context_ref=frontier.context_ref,
                    scope_ref="learning:candidate",
                    source_ref="source:runtime-learning-advance",
                    permission_ref=frontier.permission_ref,
                    operations=tuple(operations),
                    expected_store_revision=snapshot.store_revision,
                    validation_requirements=(
                        "candidate_is_not_authority",
                        "exact_learning_lineage",
                    ),
                    metadata={"authoritative_promotion": False},
                )
        if operations:
            result = self.store.apply_patch(patch)
            if not result.committed:
                return (), ()
        return (
            tuple(pins),
            tuple(dependency_pins[key] for key in sorted(dependency_pins)),
        )

    def _package(self, frontier, pins, dependency_pins):
        requested = []
        raw_uses = dict(
            frontier.metadata.get("requested_use_decisions", {})
        )
        for operation, decision in sorted(raw_uses.items()):
            requested.append(UseAuthorization(
                UseOperation(str(operation)),
                UseDecision(str(decision)),
                evidence_refs=frontier.evidence_refs,
                reason="explicit learning-frontier requested use",
            ))
        competence_cases = tuple(sorted({
            ref
            for pin in pins
            for ref in getattr(
                self.store.get_record(
                    pin.record_kind, pin.record_ref, pin.revision
                ).payload,
                "competence_case_refs",
                (),
            )
        }))
        preliminary = PackageAssembler().assemble(
            package_family=(
                frontier.metadata.get("package_family")
                or frontier.missing_contract.split(":", 1)[0]
            ),
            candidate_pins=pins,
            dependency_pins=tuple(dependency_pins),
            frontier_refs=(frontier.frontier_ref,),
            evidence_link_refs=(),
            counterexample_link_refs=(),
            competence_case_refs=competence_cases,
            requested_use_authorizations=requested,
            promotion_policy_ref=str(
                frontier.metadata.get(
                    "promotion_policy_ref",
                    "policy:runtime-reviewed-learning-promotion",
                )
            ),
            review_refs=tuple(frontier.metadata.get("review_refs", ())),
            provenance_refs=frontier.evidence_refs,
            source_lineage_refs=tuple(
                sorted(set(self._source_lineage(frontier.evidence_refs)))
            ),
            scope_ref=frontier.context_ref,
            permission_ref=frontier.permission_ref,
            sensitivity=frontier.sensitivity,
        )
        durable_evidence_refs = tuple(
            ref for ref in frontier.evidence_refs
            if self.store.get_record(RecordKind.EVIDENCE, ref) is not None
        )
        durable_lineage = tuple(
            sorted(set(self._source_lineage(durable_evidence_refs)))
        )
        links = []
        if durable_evidence_refs and durable_lineage:
            for pin in pins:
                link_ref = "learning-evidence-link:" + semantic_fingerprint(
                    "runtime-learning-evidence-link",
                    (
                        preliminary.package_ref,
                        pin.key,
                        frontier.frontier_ref,
                        durable_evidence_refs,
                    ),
                    24,
                )
                links.append(LearningEvidenceLink(
                    link_ref=link_ref,
                    package_ref=preliminary.package_ref,
                    package_revision=preliminary.revision,
                    polarity=EvidencePolarity.SUPPORT,
                    evidence_refs=durable_evidence_refs,
                    source_lineage_refs=durable_lineage,
                    candidate_pin=pin,
                    context_ref=frontier.context_ref,
                    permission_ref=frontier.permission_ref,
                    metadata={"frontier_refs": (frontier.frontier_ref,)},
                ))
        status = (
            LearningPackageStatus.COMPETENCE_PENDING
            if requested and competence_cases and links
            else LearningPackageStatus.EVIDENCE_ACCUMULATING
        )
        package = replace(
            preliminary,
            evidence_link_refs=tuple(link.link_ref for link in links),
            lifecycle_status=status,
            metadata={
                **dict(preliminary.metadata),
                "authorization_refs": tuple(
                    frontier.metadata.get("authorization_refs", ())
                ),
                "risk_refs": tuple(frontier.metadata.get("risk_refs", ())),
                "runtime_advanced": True,
            },
        )
        return package, tuple(links)

    def _source_lineage(self, evidence_refs):
        for evidence_ref in evidence_refs:
            stored = self.store.get_record(RecordKind.EVIDENCE, evidence_ref)
            if stored is None:
                continue
            yield stored.payload.lineage_ref or stored.payload.source_ref

    def _run_competence(self, package):
        if (
            package.lifecycle_status
            != LearningPackageStatus.COMPETENCE_PENDING
        ):
            return ()
        existing = tuple(
            item.payload
            for item in self.store.repositories.competence_results.all()
            if item.payload.package_ref == package.package_ref
            and item.payload.package_revision == package.revision
        )
        by_operation = {item.use_operation: item for item in existing}
        runner = LearningCompetenceRunner(self.store)
        results = list(existing)
        for authorization in package.requested_use_authorizations:
            if authorization.decision not in {
                UseDecision.ALLOW,
                UseDecision.PROVISIONAL,
            }:
                continue
            operation = authorization.operation
            if operation in by_operation:
                continue
            executor = self.competence_executors.get(operation.value)
            if executor is None:
                continue
            result = runner.run(package, operation, executor)
            persisted = runner.persist(result)
            if persisted.committed:
                results.append(result)
        return tuple(results)

    def _mark_promotable_if_ready(self, package, results):
        requested = tuple(
            item.operation
            for item in package.requested_use_authorizations
            if item.decision in {UseDecision.ALLOW, UseDecision.PROVISIONAL}
        )
        if not requested:
            return None
        passed = {
            item.use_operation
            for item in results
            if item.outcome == CompetenceOutcome.PASSED
        }
        if not set(requested).issubset(passed):
            return None
        if (
            not package.review_refs
            or not package.metadata.get("authorization_refs")
        ):
            return None
        current = self.store.get_record(
            RecordKind.LEARNING_PACKAGE, package.package_ref
        )
        if current is None:
            return None
        if current.payload.lifecycle_status == LearningPackageStatus.PROMOTABLE:
            return current.payload
        next_package = replace(
            current.payload,
            revision=current.revision + 1,
            supersedes_revision=current.revision,
            lifecycle_status=LearningPackageStatus.PROMOTABLE,
        )
        dependencies = [
            RecordDependency(
                RecordKind.LEARNING_PACKAGE,
                current.record_ref,
                current.revision,
                current.record_fingerprint,
                "learning_package_prior_revision",
            )
        ]
        for result in results:
            stored = self.store.get_record(
                RecordKind.COMPETENCE_RESULT, result.result_ref
            )
            if stored is not None:
                dependencies.append(RecordDependency(
                    stored.record_kind,
                    stored.record_ref,
                    stored.revision,
                    stored.record_fingerprint,
                    "learning_competence",
                ))
        with self.store.snapshot() as snapshot:
            patch = GraphPatch(
                patch_ref="graph-patch:learning-package-promotable:"
                + semantic_fingerprint(
                    "learning-package-promotable",
                    (
                        next_package.package_ref,
                        next_package.revision,
                        snapshot.fingerprint,
                    ),
                    24,
                ),
                context_ref=package.scope_ref,
                scope_ref=package.scope_ref,
                source_ref="source:runtime-learning-advance",
                permission_ref=package.permission_ref,
                operations=(PatchOperation(
                    operation_ref="patch-operation:learning-package-promotable:"
                    + semantic_fingerprint(
                        "learning-package-promotable-operation",
                        (
                            next_package.package_ref,
                            next_package.revision,
                        ),
                        20,
                    ),
                    operation_kind=PatchOperationKind.UPSERT,
                    record_kind=RecordKind.LEARNING_PACKAGE,
                    target_ref=next_package.package_ref,
                    record_revision=next_package.revision,
                    payload=encode_record(
                        RecordKind.LEARNING_PACKAGE, next_package
                    ),
                    expected_record_revision=current.revision,
                    expected_record_fingerprint=current.record_fingerprint,
                    dependencies=tuple(dependencies),
                    reason=(
                        "all explicitly requested use axes passed independent "
                        "competence and carry review/authorization"
                    ),
                ),),
                expected_store_revision=snapshot.store_revision,
                validation_requirements=(
                    "independent_competence_complete",
                    "review_authorization_present",
                ),
            )
        committed = self.store.apply_patch(patch)
        return next_package if committed.committed else None
