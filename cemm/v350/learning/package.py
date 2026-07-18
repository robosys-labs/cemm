"""Candidate induction boundary, package assembly, and exact dependency resolution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol

from ..schema.model import UseAuthorization, semantic_fingerprint
from ..storage.model import RecordKind, StoreSnapshot
from .frontier import EvidenceSummary
from .model import (
    LearningBudget,
    LearningFrontierRecord,
    LearningPackageRecord,
    LearningPackageStatus,
    PinnedRecord,
)


@dataclass(frozen=True, slots=True)
class CandidateProposal:
    """Non-authoritative proposal emitted by an inducer.

    The payload remains a canonical record object for its record kind. This
    wrapper never grants executable meaning or use authorization.
    """

    record_kind: RecordKind
    payload: Any
    evidence_refs: tuple[str, ...]
    dependency_pins: tuple[PinnedRecord, ...] = ()
    confidence: float = 0.0
    proposer_ref: str = "candidate-inducer:unknown"


class CandidateStructureInducer(Protocol):
    def induce(
        self,
        frontier: LearningFrontierRecord,
        evidence: EvidenceSummary,
        *,
        snapshot: StoreSnapshot,
    ) -> tuple[CandidateProposal, ...]: ...


@dataclass(frozen=True, slots=True)
class DependencyResolution:
    valid: bool
    resolved_pins: tuple[PinnedRecord, ...]
    unresolved_pins: tuple[PinnedRecord, ...]
    cycle_refs: tuple[str, ...]
    budget_exhausted: bool = False


class LearningDependencyResolver:
    def __init__(self, store, budget: LearningBudget | None = None) -> None:
        self.store = store
        self.budget = budget or LearningBudget()

    def pin(self, record_kind: RecordKind, record_ref: str, revision: int) -> PinnedRecord:
        stored = self.store.get_record(record_kind, record_ref, revision)
        if stored is None:
            raise KeyError(f"{record_kind.value}:{record_ref}@{revision}")
        return PinnedRecord(record_kind, record_ref, revision, stored.record_fingerprint)

    def verify_pin(self, pin: PinnedRecord) -> bool:
        stored = self.store.get_record(pin.record_kind, pin.record_ref, pin.revision)
        return stored is not None and stored.record_fingerprint == pin.record_fingerprint

    def resolve(self, package: LearningPackageRecord) -> DependencyResolution:
        all_pins = tuple((*package.candidate_pins, *package.dependency_pins))
        if len(all_pins) > self.budget.maximum_dependency_nodes:
            return DependencyResolution(False, (), all_pins, (), True)
        resolved = tuple(pin for pin in all_pins if self.verify_pin(pin))
        unresolved = tuple(pin for pin in all_pins if pin not in resolved)
        cycles = self._package_cycles(package)
        return DependencyResolution(not unresolved and not cycles, resolved, unresolved, cycles)

    def _package_cycles(self, root: LearningPackageRecord) -> tuple[str, ...]:
        graph: dict[str, set[str]] = {root.package_ref: set()}
        queue = [(root, 0)]
        visited: set[tuple[str, int]] = set()
        nodes = 0
        while queue:
            package, depth = queue.pop(0)
            if (package.package_ref, package.revision) in visited:
                continue
            visited.add((package.package_ref, package.revision))
            nodes += 1
            if nodes > self.budget.maximum_dependency_nodes or depth > self.budget.maximum_dependency_depth:
                return ("budget:dependency-closure",)
            for pin in package.dependency_pins:
                if pin.record_kind != RecordKind.LEARNING_PACKAGE:
                    continue
                graph.setdefault(package.package_ref, set()).add(pin.record_ref)
                stored = self.store.get_record(RecordKind.LEARNING_PACKAGE, pin.record_ref, pin.revision)
                if stored is not None and isinstance(stored.payload, LearningPackageRecord):
                    queue.append((stored.payload, depth + 1))
        visiting: set[str] = set()
        done: set[str] = set()
        cycle: list[str] = []

        def visit(node: str) -> bool:
            if node in done:
                return False
            if node in visiting:
                cycle.append(node)
                return True
            visiting.add(node)
            for child in sorted(graph.get(node, ())):
                if visit(child):
                    cycle.append(node)
                    return True
            visiting.remove(node)
            done.add(node)
            return False

        for node in sorted(graph):
            if visit(node):
                return tuple(reversed(cycle))
        return ()


class PackageAssembler:
    def __init__(self, budget: LearningBudget | None = None) -> None:
        self.budget = budget or LearningBudget()

    def assemble(
        self,
        *,
        package_family: str,
        candidate_pins: Iterable[PinnedRecord],
        dependency_pins: Iterable[PinnedRecord],
        frontier_refs: Iterable[str],
        evidence_link_refs: Iterable[str],
        counterexample_link_refs: Iterable[str],
        competence_case_refs: Iterable[str],
        requested_use_authorizations: Iterable[UseAuthorization],
        promotion_policy_ref: str,
        review_refs: Iterable[str] = (),
        provenance_refs: Iterable[str] = (),
        source_lineage_refs: Iterable[str] = (),
        scope_ref: str = "global",
        permission_ref: str = "conversation",
        sensitivity: str = "normal",
    ) -> LearningPackageRecord:
        candidates = tuple(sorted(set(candidate_pins), key=lambda item: item.key))
        dependencies = tuple(sorted(set(dependency_pins), key=lambda item: item.key))
        if len(candidates) > self.budget.maximum_candidates:
            raise ValueError("learning package candidate budget exhausted; preserve unresolved frontier")
        if len(dependencies) > self.budget.maximum_dependency_nodes:
            raise ValueError("learning package dependency budget exhausted; preserve unresolved frontier")
        identity = (
            package_family,
            tuple(item.key + (item.record_fingerprint,) for item in candidates),
            tuple(item.key + (item.record_fingerprint,) for item in dependencies),
            tuple(sorted(set(frontier_refs))),
        )
        package_ref = "learning-package:" + semantic_fingerprint("learning-package-ref", identity, 24)
        return LearningPackageRecord(
            package_ref=package_ref,
            package_family=package_family,
            candidate_pins=candidates,
            dependency_pins=dependencies,
            frontier_refs=tuple(sorted(set(frontier_refs))),
            evidence_link_refs=tuple(sorted(set(evidence_link_refs))),
            counterexample_link_refs=tuple(sorted(set(counterexample_link_refs))),
            competence_case_refs=tuple(sorted(set(competence_case_refs))),
            requested_use_authorizations=tuple(sorted(requested_use_authorizations, key=lambda item: item.operation.value)),
            promotion_policy_ref=promotion_policy_ref,
            review_refs=tuple(sorted(set(review_refs))),
            provenance_refs=tuple(sorted(set(provenance_refs))),
            source_lineage_refs=tuple(sorted(set(source_lineage_refs))),
            scope_ref=scope_ref,
            permission_ref=permission_ref,
            sensitivity=sensitivity,
            lifecycle_status=LearningPackageStatus.CANDIDATE,
        )


class LearningPackageCommitCoordinator:
    """Persist a package/evidence/frontier bundle as one exact dependency DAG.

    Evidence links may point back to the package revision, so the authoritative
    creation path is intentionally one atomic GraphPatch with staged resolution.
    """

    def __init__(self, store) -> None:
        self.store = store

    def persist(
        self,
        package: LearningPackageRecord,
        *,
        evidence_links=(),
        frontiers=(),
        source_ref: str = "source:phase13:package-coordinator",
    ):
        from ..storage.codec import encode_record, record_fingerprints, record_ref, record_revision
        from ..storage.model import GraphPatch, PatchOperation, PatchOperationKind, RecordDependency
        from .model import LearningEvidenceLink

        links = {item.link_ref: item for item in evidence_links}
        frontier_map = {item.frontier_ref: item for item in frontiers}
        package_fp = record_fingerprints(RecordKind.LEARNING_PACKAGE, package)[1]

        def dep_for(kind, record, dependency_kind):
            return RecordDependency(
                kind,
                record_ref(kind, record),
                record_revision(kind, record),
                record_fingerprints(kind, record)[1],
                dependency_kind,
            )

        package_deps = [
            RecordDependency(pin.record_kind, pin.record_ref, pin.revision, pin.record_fingerprint, "learning_candidate")
            for pin in package.candidate_pins
        ] + [
            RecordDependency(pin.record_kind, pin.record_ref, pin.revision, pin.record_fingerprint, "learning_dependency")
            for pin in package.dependency_pins
        ]
        resolved_links = []
        for link_ref in (*package.evidence_link_refs, *package.counterexample_link_refs):
            link = links.get(link_ref)
            if link is None:
                stored = self.store.get_record(RecordKind.LEARNING_EVIDENCE_LINK, link_ref, 1)
                if stored is None or not isinstance(stored.payload, LearningEvidenceLink):
                    raise ValueError(f"package evidence link is unavailable for atomic persistence: {link_ref}")
                package_deps.append(RecordDependency(
                    RecordKind.LEARNING_EVIDENCE_LINK, link_ref, stored.revision,
                    stored.record_fingerprint, "learning_evidence_link",
                ))
            else:
                if link.package_ref != package.package_ref or link.package_revision != package.revision:
                    raise ValueError("staged learning evidence link targets another package revision")
                package_deps.append(dep_for(RecordKind.LEARNING_EVIDENCE_LINK, link, "learning_evidence_link"))
                resolved_links.append(link)
        resolved_frontiers = []
        for frontier_ref in package.frontier_refs:
            frontier = frontier_map.get(frontier_ref)
            if frontier is None:
                stored = self.store.get_record(RecordKind.LEARNING_FRONTIER, frontier_ref)
                if stored is None:
                    raise ValueError(f"package frontier is unavailable for atomic persistence: {frontier_ref}")
                package_deps.append(RecordDependency(
                    RecordKind.LEARNING_FRONTIER, frontier_ref, stored.revision,
                    stored.record_fingerprint, "learning_frontier",
                ))
            else:
                package_deps.append(dep_for(RecordKind.LEARNING_FRONTIER, frontier, "learning_frontier"))
                resolved_frontiers.append(frontier)

        with self.store.snapshot() as snapshot:
            operations = []
            # Staged frontiers are non-authoritative but persisted in the same CAS
            # transaction so package references cannot race a separate write.
            for frontier in resolved_frontiers:
                operations.append(PatchOperation(
                    operation_ref="patch-operation:learning-frontier-bundle:" + semantic_fingerprint(
                        "learning-frontier-bundle", (frontier.frontier_ref, frontier.revision, package.package_ref), 20
                    ),
                    operation_kind=PatchOperationKind.UPSERT,
                    record_kind=RecordKind.LEARNING_FRONTIER,
                    target_ref=frontier.frontier_ref,
                    record_revision=frontier.revision,
                    payload=encode_record(RecordKind.LEARNING_FRONTIER, frontier),
                    reason="persist package frontier in atomic learning bundle",
                ))
            for link in resolved_links:
                link_deps = [RecordDependency(
                    RecordKind.LEARNING_PACKAGE, package.package_ref, package.revision,
                    package_fp, "learning_package",
                )]
                if link.candidate_pin is not None:
                    pin = link.candidate_pin
                    link_deps.append(RecordDependency(
                        pin.record_kind, pin.record_ref, pin.revision, pin.record_fingerprint,
                        "learning_candidate",
                    ))
                for evidence_ref in link.evidence_refs:
                    stored_evidence = self.store.get_record(RecordKind.EVIDENCE, evidence_ref)
                    if stored_evidence is None:
                        raise ValueError(f"learning evidence is unresolved: {evidence_ref}")
                    link_deps.append(RecordDependency(
                        RecordKind.EVIDENCE, evidence_ref, stored_evidence.revision,
                        stored_evidence.record_fingerprint, "learning_evidence",
                    ))
                operations.append(PatchOperation(
                    operation_ref="patch-operation:learning-evidence-bundle:" + semantic_fingerprint(
                        "learning-evidence-bundle", (link.link_ref, package.package_ref), 20
                    ),
                    operation_kind=PatchOperationKind.UPSERT,
                    record_kind=RecordKind.LEARNING_EVIDENCE_LINK,
                    target_ref=link.link_ref,
                    record_revision=1,
                    payload=encode_record(RecordKind.LEARNING_EVIDENCE_LINK, link),
                    dependencies=tuple(link_deps),
                    reason="persist immutable attributable learning evidence link",
                ))
            current = self.store.get_record(RecordKind.LEARNING_PACKAGE, package.package_ref)
            operations.append(PatchOperation(
                operation_ref="patch-operation:learning-package-bundle:" + semantic_fingerprint(
                    "learning-package-bundle", (package.package_ref, package.revision), 20
                ),
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=RecordKind.LEARNING_PACKAGE,
                target_ref=package.package_ref,
                record_revision=package.revision,
                payload=encode_record(RecordKind.LEARNING_PACKAGE, package),
                expected_record_revision=None if current is None else current.revision,
                expected_record_fingerprint=None if current is None else current.record_fingerprint,
                dependencies=tuple(package_deps),
                reason="persist exact non-authoritative learning package DAG",
            ))
            patch = GraphPatch(
                patch_ref="graph-patch:learning-package-bundle:" + semantic_fingerprint(
                    "learning-package-bundle-patch", (package.package_ref, package.revision, snapshot.fingerprint), 24
                ),
                context_ref="learning:package",
                scope_ref=package.scope_ref,
                source_ref=source_ref,
                permission_ref=package.permission_ref,
                operations=tuple(operations),
                expected_store_revision=snapshot.store_revision,
                validation_requirements=("phase13_exact_learning_dag", "candidate_is_not_authority"),
                metadata={"phase": 13, "authoritative_promotion": False},
            )
        return self.store.apply_patch(patch)
