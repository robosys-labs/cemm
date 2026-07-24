"""Atomic Phase-14 persistence coordinator."""
from __future__ import annotations

from ..learning.model import LearningFrontierRecord, PinnedRecord
from ..schema.model import semantic_fingerprint
from ..storage.codec import encode_record, record_fingerprints, record_ref, record_revision
from ..storage.model import GraphPatch, PatchOperation, PatchOperationKind, RecordDependency, RecordKind
from .model import ImpactProofRecord, SignificanceAssessmentRecord


class SignificanceCommitCoordinator:
    def __init__(self, store) -> None:
        self.store = store

    def commit(
        self,
        records: tuple[tuple[ImpactProofRecord, SignificanceAssessmentRecord], ...],
        frontiers: tuple[LearningFrontierRecord, ...] = (),
        frontier_dependency_pins: tuple[PinnedRecord, ...] = (),
    ):
        if not records and not frontiers:
            raise ValueError("Phase-14 commit requires assessments or explicit uncertainty frontiers")
        contexts = {item.context_ref for _, item in records} | {item.context_ref for item in frontiers}
        permissions = {item.permission_ref for _, item in records} | {item.permission_ref for item in frontiers}
        if len(contexts) > 1 or len(permissions) > 1:
            raise ValueError("one Phase-14 patch cannot mix context or permission scopes")
        if frontiers and not frontier_dependency_pins:
            raise ValueError("significance frontiers require exact causal dependency pins")
        with self.store.snapshot() as snapshot:
            operations = []
            for proof, assessment in records:
                source = self._exact(assessment.source_pin)
                rule = self._exact(assessment.rule_pin)
                proof_fp = record_fingerprints(RecordKind.IMPACT_PROOF, proof)[1]
                proof_deps = [
                    RecordDependency(assessment.source_pin.record_kind, assessment.source_pin.record_ref, assessment.source_pin.revision, assessment.source_pin.record_fingerprint, "impact_source"),
                    RecordDependency(RecordKind.IMPACT_RULE, assessment.rule_pin.record_ref, assessment.rule_pin.revision, assessment.rule_pin.record_fingerprint, "impact_rule"),
                ]
                proof_deps.extend(RecordDependency(pin.record_kind, pin.record_ref, pin.revision, pin.record_fingerprint, "impact_binding_source") for pin in proof.binding_source_pins)
                proof_deps.extend(RecordDependency(pin.record_kind, pin.record_ref, pin.revision, pin.record_fingerprint, "impact_prerequisite_proof") for pin in proof.prerequisite_proof_pins)
                operations.append(self._upsert(RecordKind.IMPACT_PROOF, proof, tuple(proof_deps), "persist proof-bearing impact binding"))
                deps = [
                    RecordDependency(assessment.source_pin.record_kind, source.record_ref, source.revision, source.record_fingerprint, "significance_source"),
                    RecordDependency(RecordKind.IMPACT_RULE, rule.record_ref, rule.revision, rule.record_fingerprint, "significance_rule"),
                    RecordDependency(RecordKind.IMPACT_PROOF, proof.proof_ref, proof.revision, proof_fp, "significance_proof"),
                ]
                for evidence_ref in assessment.importance_evidence_refs:
                    stored = self.store.get_record(RecordKind.IMPORTANCE_EVIDENCE, evidence_ref)
                    if stored is None:
                        raise ValueError(f"importance evidence is unresolved: {evidence_ref}")
                    deps.append(RecordDependency(RecordKind.IMPORTANCE_EVIDENCE, stored.record_ref, stored.revision, stored.record_fingerprint, "importance_evidence"))
                if assessment.importance_policy_pin is not None:
                    pin = assessment.importance_policy_pin
                    self._exact(pin)
                    deps.append(RecordDependency(pin.record_kind, pin.record_ref, pin.revision, pin.record_fingerprint, "importance_policy"))
                operations.append(self._upsert(RecordKind.SIGNIFICANCE_ASSESSMENT, assessment, tuple(deps), "persist stakeholder-relative significance"))
            frontier_deps = tuple(RecordDependency(pin.record_kind, pin.record_ref, pin.revision, pin.record_fingerprint, "significance_frontier_cause") for pin in frontier_dependency_pins)
            for frontier in frontiers:
                operations.append(self._upsert(RecordKind.LEARNING_FRONTIER, frontier, frontier_deps, "persist unresolved significance binding frontier"))
            patch = GraphPatch(
                patch_ref="graph-patch:phase14:" + semantic_fingerprint(
                    "phase14-patch", (snapshot.fingerprint, tuple(op.operation_ref for op in operations)), 24
                ),
                context_ref=(records[0][1].context_ref if records else frontiers[0].context_ref),
                scope_ref="phase14:significance",
                source_ref="source:phase14:significance-coordinator",
                permission_ref=(records[0][1].permission_ref if records else frontiers[0].permission_ref),
                operations=tuple(operations), expected_store_revision=snapshot.store_revision,
                validation_requirements=("phase14_exact_lineage", "phase14_stakeholder_relative", "phase14_no_state_mutation"),
                metadata={"phase": 14},
            )
        return self.store.apply_patch(patch)

    def _exact(self, pin: PinnedRecord):
        stored = self.store.get_record(pin.record_kind, pin.record_ref, pin.revision)
        if stored is None or stored.record_fingerprint != pin.record_fingerprint:
            raise ValueError(f"stale exact dependency pin: {pin.key}")
        return stored

    @staticmethod
    def _upsert(kind: RecordKind, record, deps: tuple[RecordDependency, ...], reason: str) -> PatchOperation:
        return PatchOperation(
            operation_ref="patch-operation:phase14:" + semantic_fingerprint(
                "phase14-op", (kind.value, record_ref(kind, record), record_revision(kind, record), reason), 20
            ),
            operation_kind=PatchOperationKind.UPSERT, record_kind=kind, target_ref=record_ref(kind, record),
            record_revision=record_revision(kind, record), payload=encode_record(kind, record), dependencies=deps, reason=reason,
        )
