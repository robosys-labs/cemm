"""Independent, isolated per-use competence execution for Phase 13."""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import tempfile
from typing import Protocol

from ..schema.model import MeaningSchema, SchemaLifecycleStatus, UseAuthorization, UseDecision, UseOperation, UseProfile, semantic_fingerprint
from ..storage.codec import encode_record
from ..storage.model import (
    GraphPatch,
    PatchOperation,
    PatchOperationKind,
    RecordDependency,
    RecordKind,
)
from ..storage.store import SemanticStore
from .authority import record_supports_use
from .model import CompetenceOutcome, CompetenceResultRecord, LearningPackageRecord, PinnedRecord
from .package import LearningDependencyResolver


@dataclass(frozen=True, slots=True)
class CompetenceObservation:
    passed_case_refs: tuple[str, ...]
    failed_case_refs: tuple[str, ...]
    counterexample_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()
    failure_frontier_refs: tuple[str, ...] = ()
    independent_lineage_refs: tuple[str, ...] = ()
    environment_refs: tuple[str, ...] = ()
    performance_ms: tuple[tuple[str, float], ...] = ()
    metadata: dict[str, object] | None = None


class CompetenceExecutor(Protocol):
    def execute(
        self,
        sandbox: "CompetenceSandbox",
        package: LearningPackageRecord,
        operation: UseOperation,
        case_refs: tuple[str, ...],
    ) -> CompetenceObservation: ...


class CompetenceSandbox:
    """Temporary store with no write path back to the authoritative overlay."""

    def __init__(self, store: SemanticStore) -> None:
        self.store = store

    def activate_candidate(self, pin: PinnedRecord, operation: UseOperation) -> None:
        """Assert that the requested candidate is already isolated-active.

        Candidate records are transformed *while copied* into the isolated
        sandbox. Durable record revisions are immutable, so attempting an
        in-place same-revision lifecycle rewrite would correctly fail CAS.
        """
        stored = self.store.get_record(pin.record_kind, pin.record_ref, pin.revision)
        if stored is None:
            raise ValueError("competence sandbox candidate pin is missing")
        record = stored.payload
        if not record_supports_use(pin.record_kind, record, operation):
            # A transformed lexical record still carries its canonical declared
            # use_operation; other lifecycle-only families are checked below.
            declared = getattr(record, "use_operation", None)
            if declared is not None and declared != operation:
                raise ValueError("candidate structural use axis differs from requested competence operation")
        lifecycle = getattr(record, "lifecycle_status", None)
        if lifecycle is not None and lifecycle != SchemaLifecycleStatus.ACTIVE:
            raise ValueError("competence candidate was not isolated-active in sandbox substrate")
        if isinstance(record, MeaningSchema):
            if record.use_profile.decision_for(operation) != UseDecision.ALLOW:
                raise ValueError("competence schema does not authorize requested operation inside sandbox")


class LearningCompetenceRunner:
    def __init__(self, store: SemanticStore, *, runner_ref: str = "learning-competence-runner:v1", runner_revision: str = "1") -> None:
        self.store = store
        self.runner_ref = runner_ref
        self.runner_revision = runner_revision

    def run(
        self,
        package: LearningPackageRecord,
        operation: UseOperation,
        executor: CompetenceExecutor,
        *,
        case_refs: tuple[str, ...] | None = None,
    ) -> CompetenceResultRecord:
        resolver = LearningDependencyResolver(self.store)
        resolution = resolver.resolve(package)
        if not resolution.valid:
            raise ValueError("cannot run competence on unresolved/stale/cyclic package")
        cases = tuple(sorted(set(case_refs or package.competence_case_refs)))
        if not cases:
            raise ValueError("competence requires explicit independent cases")
        with self.store.snapshot() as source_snapshot:
            with tempfile.TemporaryDirectory(prefix="cemm-v350-phase13-competence-") as directory:
                sandbox_store = SemanticStore(Path(directory) / "overlay.sqlite", boot_path=self.store.boot_path)
                try:
                    self._copy_exact_substrate(sandbox_store, package, operation)
                    sandbox = CompetenceSandbox(sandbox_store)
                    observation = executor.execute(sandbox, package, operation, cases)
                finally:
                    sandbox_store.close()
            self.store.assert_snapshot(source_snapshot)
        independent = set(observation.independent_lineage_refs)
        if not independent:
            raise ValueError("competence must carry independent lineage refs")
        if independent.intersection(package.source_lineage_refs):
            raise ValueError("competence lineage must be independent from package induction/source lineage")
        passed = tuple(sorted(set(observation.passed_case_refs)))
        failed = tuple(sorted(set(observation.failed_case_refs)))
        if set(passed).union(failed) != set(cases):
            outcome = CompetenceOutcome.PARTIAL
        elif failed:
            outcome = CompetenceOutcome.FAILED
        else:
            outcome = CompetenceOutcome.PASSED
        result_ref = "competence-result:" + semantic_fingerprint(
            "learning-competence-result-ref",
            (
                package.package_ref, package.revision, operation.value, cases,
                tuple(pin.key + (pin.record_fingerprint,) for pin in package.candidate_pins),
                tuple(pin.key + (pin.record_fingerprint,) for pin in package.dependency_pins),
                outcome.value, passed, failed,
                tuple(sorted(set(observation.counterexample_refs))),
                tuple(sorted(set(observation.proof_refs))),
                tuple(sorted(set(observation.failure_frontier_refs))),
                tuple(sorted(independent)),
                tuple(sorted(set(observation.environment_refs))),
                source_snapshot.fingerprint, self.runner_ref, self.runner_revision,
            ),
            24,
        )
        return CompetenceResultRecord(
            result_ref=result_ref,
            package_ref=package.package_ref,
            package_revision=package.revision,
            use_operation=operation,
            candidate_pins=package.candidate_pins,
            dependency_pins=package.dependency_pins,
            case_refs=cases,
            outcome=outcome,
            passed_case_refs=passed,
            failed_case_refs=failed,
            counterexample_refs=tuple(sorted(set(observation.counterexample_refs))),
            proof_refs=tuple(sorted(set(observation.proof_refs))),
            failure_frontier_refs=tuple(sorted(set(observation.failure_frontier_refs))),
            snapshot_revision=source_snapshot.store_revision,
            boot_fingerprint=source_snapshot.boot_fingerprint,
            overlay_fingerprint=source_snapshot.overlay_fingerprint,
            runner_ref=self.runner_ref,
            runner_revision=self.runner_revision,
            independent_lineage_refs=tuple(sorted(independent)),
            environment_refs=tuple(sorted(set(observation.environment_refs))),
            performance_ms=tuple(sorted(observation.performance_ms)),
            metadata=dict(observation.metadata or {}),
        )

    def persist(self, result: CompetenceResultRecord):
        """Persist an immutable competence result with its exact causal DAG."""
        from ..storage.codec import record_fingerprints
        from ..storage.model import RecordDependency

        package_stored = self.store.get_record(
            RecordKind.LEARNING_PACKAGE, result.package_ref, result.package_revision
        )
        if package_stored is None:
            raise ValueError("competence package revision is missing before persistence")
        dependencies = [RecordDependency(
            RecordKind.LEARNING_PACKAGE, result.package_ref, result.package_revision,
            package_stored.record_fingerprint, "competence_package",
        )]
        dependencies.extend(
            RecordDependency(pin.record_kind, pin.record_ref, pin.revision, pin.record_fingerprint, "competence_substrate")
            for pin in (*result.candidate_pins, *result.dependency_pins)
        )
        with self.store.snapshot() as snapshot:
            operation = PatchOperation(
                operation_ref="patch-operation:competence-result:" + semantic_fingerprint(
                    "competence-result-operation", (result.result_ref, result.substrate_fingerprint), 20
                ),
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=RecordKind.COMPETENCE_RESULT,
                target_ref=result.result_ref,
                record_revision=1,
                payload=encode_record(RecordKind.COMPETENCE_RESULT, result),
                dependencies=tuple(dependencies),
                reason="persist immutable independent per-use competence proof",
            )
            patch = GraphPatch(
                patch_ref="graph-patch:competence-result:" + semantic_fingerprint(
                    "competence-result-patch", (result.result_ref, snapshot.fingerprint), 24
                ),
                context_ref="learning:competence",
                scope_ref=result.package_ref,
                source_ref=self.runner_ref,
                permission_ref=result.permission_ref,
                operations=(operation,),
                expected_store_revision=snapshot.store_revision,
                validation_requirements=("phase13_independent_competence", "phase13_exact_substrate"),
                metadata={"phase": 13, "authoritative_promotion": False},
            )
        return self.store.apply_patch(patch)

    def _copy_exact_substrate(
        self, sandbox: SemanticStore, package: LearningPackageRecord, operation: UseOperation
    ) -> None:
        operations = []
        candidate_keys = {pin.key for pin in package.candidate_pins}
        for pin in (*package.dependency_pins, *package.candidate_pins):
            source = self.store.get_record(pin.record_kind, pin.record_ref, pin.revision)
            if source is None or source.record_fingerprint != pin.record_fingerprint:
                raise ValueError("source package pin is stale before competence")
            existing = sandbox.get_record(pin.record_kind, pin.record_ref, pin.revision)
            if existing is not None:
                if pin.key in candidate_keys:
                    # Boot authority with the same identity is not an isolated
                    # candidate substrate; competence must not silently test it.
                    raise ValueError("candidate identity already exists in competence boot substrate")
                if existing.record_fingerprint != pin.record_fingerprint:
                    raise ValueError("sandbox boot substrate differs from exact package dependency pin")
                continue
            payload = source.payload
            if pin.key in candidate_keys:
                payload = self._competence_activation(pin, payload, operation, package.competence_case_refs)
            operations.append(PatchOperation(
                operation_ref="patch-operation:competence-copy:" + semantic_fingerprint(
                    "competence-copy", (pin.key, operation.value, pin.key in candidate_keys), 20
                ),
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=pin.record_kind,
                target_ref=pin.record_ref,
                record_revision=pin.revision,
                payload=encode_record(pin.record_kind, payload),
                dependencies=(),
                reason="copy exact source substrate into isolated competence overlay; candidate lifecycle activation is sandbox-only",
            ))
        if not operations:
            return
        result = sandbox.apply_patch(GraphPatch(
            patch_ref="graph-patch:competence-substrate:" + semantic_fingerprint(
                "competence-substrate-patch", tuple(op.operation_ref for op in operations), 24
            ),
            context_ref="competence:sandbox",
            scope_ref="phase13:competence",
            source_ref="source:phase13:competence-runner",
            permission_ref="internal",
            operations=tuple(operations),
            expected_store_revision=sandbox.revision,
            validation_requirements=("copy_exact_competence_substrate",),
            metadata={"authoritative_promotion": False},
        ))
        if not result.committed:
            raise ValueError("failed to build competence sandbox: " + "; ".join(result.errors))

    @staticmethod
    def _competence_activation(
        pin: PinnedRecord, record, operation: UseOperation, case_refs: tuple[str, ...]
    ):
        if not record_supports_use(pin.record_kind, record, operation):
            return record
        if isinstance(record, MeaningSchema):
            # Per-use isolation: proposed permissions on every other axis remain
            # non-authoritative even inside the sandbox.
            profile = UseProfile((UseAuthorization(operation, UseDecision.ALLOW, reason="isolated competence only"),))
            return replace(record, lifecycle_status=SchemaLifecycleStatus.ACTIVE, use_profile=profile)
        if hasattr(record, "lifecycle_status"):
            kwargs = {"lifecycle_status": SchemaLifecycleStatus.ACTIVE}
            if hasattr(record, "competence_case_refs") and not getattr(record, "competence_case_refs"):
                kwargs["competence_case_refs"] = case_refs
            return replace(record, **kwargs)
        return record
