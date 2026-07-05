"""PatchValidator — MMU gate for all durable-write operations.

Every GraphPatch must pass through validation before reaching
durable storage. This enforces the architecture rule that no
component writes directly to memory without a validation barrier.

Phase 8 upgrade: operation-level validation, schema compatibility,
contradiction detection, compression gain, reversibility, and richer
PatchValidationResult with accepted/rejected operations.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from ..types.graph_patch import GraphPatch, PatchOperation
from ..types.context_kernel import ContextKernel


@dataclass
class ValidationCheck:
    check_name: str
    passed: bool
    score: float = 0.0
    reason: str = ""


@dataclass
class PatchValidationResult:
    patch_id: str
    status: str = "rejected"
    reasons: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    failed_checks: list[str] = field(default_factory=list)
    check_results: list[ValidationCheck] = field(default_factory=list)
    accepted_operations: list[str] = field(default_factory=list)
    rejected_operations: list[str] = field(default_factory=list)
    quarantine_reason: str = ""
    required_user_confirmation: list[str] = field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return self.status == "accepted"

    @property
    def mean_score(self) -> float:
        return sum(self.scores.values()) / len(self.scores) if self.scores else 0.0


class PatchValidator:
    """Memory-management unit: gates all GraphPatch writes to durable storage.

    Runs 12 checks against every patch before it reaches the store.
    Validates at both patch-level and operation-level.
    """

    def __init__(
        self,
        store: Any | None = None,
        schema_store: Any | None = None,
        min_confidence: float = 0.3,
        min_source_trust: float = 0.3,
        max_risk: float = 0.8,
        contradiction_threshold: float = 0.7,
        temporal_threshold: int = 86400,
    ) -> None:
        self._store = store
        self._schema_store = schema_store
        self._min_confidence = min_confidence
        self._min_source_trust = min_source_trust
        self._max_risk = max_risk
        self._contradiction_threshold = contradiction_threshold
        self._temporal_threshold = temporal_threshold

    def validate(
        self,
        patch: GraphPatch,
        kernel: ContextKernel | None = None,
    ) -> PatchValidationResult:
        scores: dict[str, float] = {}
        reasons: list[str] = []
        failed: list[str] = []
        checks: list[ValidationCheck] = []
        accepted_ops: list[str] = []
        rejected_ops: list[str] = []
        needs_confirmation: list[str] = []

        # ── Patch-level checks ──────────────────────────────────────

        # 1. Permission valid — may_store must be True
        perm_ok = kernel is not None and kernel.permission.may_store
        scores["permission_valid"] = 1.0 if perm_ok else 0.0
        checks.append(ValidationCheck("permission_valid", perm_ok, 1.0 if perm_ok else 0.0,
                       "permission scope does not allow storage" if not perm_ok else ""))
        if not perm_ok:
            failed.append("permission_valid")
            reasons.append("permission scope does not allow storage")

        # 2. Source present — patch must carry at least one source ref
        source_ok = bool(patch.source_refs)
        scores["source_present"] = 1.0 if source_ok else 0.0
        checks.append(ValidationCheck("source_present", source_ok, 1.0 if source_ok else 0.0,
                       "no source references in patch" if not source_ok else ""))
        if not source_ok:
            failed.append("source_present")
            reasons.append("no source references in patch")

        # 3. Source trust sufficient
        trust_ok = True
        if kernel is not None and kernel.memory.source_trust_keys:
            trust_ok = any(ref in kernel.memory.source_trust_keys for ref in patch.source_refs)
        else:
            trust_ok = patch.confidence >= self._min_source_trust
        scores["source_trust_sufficient"] = 1.0 if trust_ok else 0.0
        checks.append(ValidationCheck("source_trust_sufficient", trust_ok, 1.0 if trust_ok else 0.0,
                       f"source trust {patch.confidence:.2f} below threshold {self._min_source_trust}" if not trust_ok else ""))
        if not trust_ok:
            failed.append("source_trust_sufficient")
            reasons.append(f"source trust {patch.confidence:.2f} below threshold {self._min_source_trust}")

        # 4. Evidence present
        ev_ok = bool(patch.evidence_refs)
        scores["evidence_present"] = 1.0 if ev_ok else 0.0
        checks.append(ValidationCheck("evidence_present", ev_ok, 1.0 if ev_ok else 0.0,
                       "no evidence references in patch" if not ev_ok else ""))
        if not ev_ok:
            failed.append("evidence_present")
            reasons.append("no evidence references in patch")

        # 5. Freshness valid — check stale current-world claims
        freshness_ok = True
        freshness_reason = ""
        if self._store is not None and kernel is not None:
            freshness_ok, freshness_reason = self._check_freshness(patch, kernel)
        scores["freshness_valid"] = 1.0 if freshness_ok else 0.0
        checks.append(ValidationCheck("freshness_valid", freshness_ok, 1.0 if freshness_ok else 0.0, freshness_reason))
        if not freshness_ok:
            failed.append("freshness_valid")
            reasons.append(freshness_reason)

        # 6. Temporal scope valid
        temporal_ok = True
        temporal_reason = ""
        if self._store is not None and kernel is not None:
            temporal_ok, temporal_reason = self._check_temporal(patch, kernel)
        scores["temporal_scope_valid"] = 1.0 if temporal_ok else 0.0
        checks.append(ValidationCheck("temporal_scope_valid", temporal_ok, 1.0 if temporal_ok else 0.0, temporal_reason))
        if not temporal_ok:
            failed.append("temporal_scope_valid")
            reasons.append(temporal_reason)

        # 7. Required ports bound — every operation should name a target_id
        ports_ok = all(op.target_id for op in patch.operations) if patch.operations else True
        scores["required_ports_bound"] = 1.0 if ports_ok else 0.0
        checks.append(ValidationCheck("required_ports_bound", ports_ok, 1.0 if ports_ok else 0.0,
                       "some operations missing target_id" if not ports_ok else ""))
        if not ports_ok:
            failed.append("required_ports_bound")
            reasons.append("some operations missing target_id")

        # 8. Contradiction absent or resolved
        contradiction_ok = True
        contradiction_reason = ""
        if self._store is not None:
            contradiction_ok, contradiction_reason = self._check_contradiction(patch)
        scores["contradiction_absent_or_resolved"] = 1.0 if contradiction_ok else 0.0
        checks.append(ValidationCheck("contradiction_absent_or_resolved", contradiction_ok,
                       1.0 if contradiction_ok else 0.0, contradiction_reason))
        if not contradiction_ok:
            failed.append("contradiction_absent_or_resolved")
            reasons.append(contradiction_reason)

        # 9. Risk acceptable
        risk_ok = True
        risk_reason = ""
        if kernel is not None and hasattr(kernel, 'permission'):
            risk_score = getattr(kernel.permission, 'risk_score', 0.0)
            if risk_score > self._max_risk:
                risk_ok = False
                risk_reason = f"risk {risk_score:.2f} exceeds max {self._max_risk}"
        scores["risk_acceptable"] = 1.0 if risk_ok else 0.0
        checks.append(ValidationCheck("risk_acceptable", risk_ok, 1.0 if risk_ok else 0.0, risk_reason))
        if not risk_ok:
            failed.append("risk_acceptable")
            reasons.append(risk_reason)

        # 10. Confidence sufficient
        conf_ok = patch.confidence >= self._min_confidence
        scores["confidence_sufficient"] = 1.0 if conf_ok else 0.0
        checks.append(ValidationCheck("confidence_sufficient", conf_ok, 1.0 if conf_ok else 0.0,
                       f"confidence {patch.confidence:.2f} below threshold {self._min_confidence}" if not conf_ok else ""))
        if not conf_ok:
            failed.append("confidence_sufficient")
            reasons.append(f"confidence {patch.confidence:.2f} below threshold {self._min_confidence}")

        # 11. Schema compatibility — check operations against known schemas
        schema_ok = True
        schema_reason = ""
        if self._schema_store is not None:
            schema_ok, schema_reason = self._check_schema_compatibility(patch)
        scores["schema_compatible"] = 1.0 if schema_ok else 0.0
        checks.append(ValidationCheck("schema_compatible", schema_ok, 1.0 if schema_ok else 0.0, schema_reason))
        if not schema_ok:
            failed.append("schema_compatible")
            reasons.append(schema_reason)

        # 12. Reversibility — inverse operations exist where needed
        reversibility_ok = self._check_reversibility(patch)
        scores["reversibility_ok"] = 1.0 if reversibility_ok else 0.0
        checks.append(ValidationCheck("reversibility_ok", reversibility_ok, 1.0 if reversibility_ok else 0.0,
                       "irreversible operation without inverse" if not reversibility_ok else ""))
        if not reversibility_ok:
            failed.append("reversibility_ok")
            reasons.append("irreversible operation without inverse")

        # 13. Compression gain — novel or compressing information
        compression_ok = True
        compression_reason = ""
        for op in patch.operations:
            if op.operation in ("upsert_relation_candidate",) and op.target_id:
                if self._store is not None and hasattr(self._store, 'claims'):
                    existing = self._store.claims.find_by_subject(
                        op.fields.get("subject_entity_id", ""),
                        op.fields.get("predicate", ""),
                    )
                    for claim in existing:
                        if claim.object_value == op.fields.get("object_value", ""):
                            compression_ok = False
                            compression_reason = f"duplicates existing claim {claim.id}"
                            break
        scores["compression_gain"] = 1.0 if compression_ok else 0.0
        checks.append(ValidationCheck("compression_gain", compression_ok, 1.0 if compression_ok else 0.0, compression_reason))
        if not compression_ok:
            failed.append("compression_gain")
            reasons.append(compression_reason)

        # ── Operation-level validation ───────────────────────────────
        for op in patch.operations:
            op_ok = True
            op_reasons: list[str] = []

            if not op.target_id:
                op_ok = False
                op_reasons.append("missing target_id")

            if op.confidence < self._min_confidence:
                op_ok = False
                op_reasons.append(f"op confidence {op.confidence:.2f} below {self._min_confidence}")

            # Check for custom:upsert_claim outside adapter
            if op.operation == "custom:upsert_claim":
                needs_confirmation.append(op.target_id)

            if op_ok:
                accepted_ops.append(op.target_id or op.operation)
            else:
                rejected_ops.append(f"{op.target_id or op.operation}: {'; '.join(op_reasons)}")

        # ── Determine overall status ─────────────────────────────────
        mean = sum(scores.values()) / len(scores) if scores else 0.0
        if not failed and not rejected_ops:
            status = "accepted"
        elif not failed and rejected_ops:
            status = "needs_confirmation"
        elif mean >= 0.6:
            status = "needs_confirmation"
        elif mean >= 0.3:
            status = "quarantined"
        else:
            status = "rejected"

        quarantine_reason = ""
        if status == "quarantined":
            quarantine_reason = "; ".join(reasons)

        return PatchValidationResult(
            patch_id=patch.id or "unknown",
            status=status,
            reasons=reasons,
            scores=scores,
            failed_checks=failed,
            check_results=checks,
            accepted_operations=accepted_ops,
            rejected_operations=rejected_ops,
            quarantine_reason=quarantine_reason,
            required_user_confirmation=needs_confirmation,
        )

    # ── Helper check methods ──────────────────────────────────────────

    def _check_freshness(self, patch: GraphPatch, kernel: ContextKernel) -> tuple[bool, str]:
        """Check that current-world claims have fresh evidence."""
        if not patch.evidence_refs:
            return True, ""
        if hasattr(kernel, 'time') and kernel.time.now > 0:
            for ref in patch.evidence_refs:
                if self._store is not None:
                    sig = getattr(self._store, 'signals', None)
                    if sig is not None:
                        s = sig.get(ref)
                        if s is not None:
                            age = kernel.time.now - s.observed_at
                            if age > 3600:
                                return False, f"evidence {ref} is stale ({age:.0f}s old)"
        return True, ""

    def _check_temporal(self, patch: GraphPatch, kernel: ContextKernel) -> tuple[bool, str]:
        """Check temporal containment — validity period coherent with observation."""
        if not patch.evidence_refs:
            return True, ""
        if hasattr(kernel, 'time') and kernel.time.now > 0:
            for ref in patch.evidence_refs:
                if self._store is not None:
                    sig = getattr(self._store, 'signals', None)
                    if sig is not None:
                        s = sig.get(ref)
                        if s is not None and hasattr(s, 'observed_at'):
                            age = kernel.time.now - s.observed_at
                            if age > self._temporal_threshold:
                                return False, f"evidence {ref} outside temporal scope ({age:.0f}s old, threshold {self._temporal_threshold}s)"
        return True, ""

    def _check_contradiction(self, patch: GraphPatch) -> tuple[bool, str]:
        """Check if patch contradicts existing active memory."""
        claims = getattr(self._store, 'claims', None)
        if claims is None:
            return True, ""
        for op in patch.operations:
            if op.operation in ("custom:upsert_claim", "upsert_relation_candidate") and op.target_id:
                subject = op.fields.get("subject_entity_id", "")
                predicate = op.fields.get("predicate", "")
                if subject and predicate:
                    existing = claims.find_by_subject(subject, predicate)
                    for claim in existing:
                        if claim.status.value == "active" and claim.object_value != op.fields.get("object_value", ""):
                            if claim.confidence >= self._contradiction_threshold:
                                return False, (f"contradicts active claim {claim.id}: "
                                             f"existing={claim.object_value!r}, new={op.fields.get('object_value', '')!r}")
        return True, ""

    def _check_schema_compatibility(self, patch: GraphPatch) -> tuple[bool, str]:
        """Check operations against predicate schemas."""
        for op in patch.operations:
            if op.operation == "observe_predicate_schema":
                key = op.fields.get("predicate_key", "")
                if key and self._schema_store is not None:
                    record = self._schema_store.get(key)
                    if record is not None:
                        required_roles = getattr(record, 'required_roles', [])
                        arg_roles = op.fields.get("argument_roles", [])
                        for role in required_roles:
                            if role not in arg_roles:
                                return False, f"schema {key}: missing required role {role}"
        return True, ""

    def _check_reversibility(self, patch: GraphPatch) -> bool:
        """Check that irreversible operations have inverse operations."""
        irreversible = {"merge_concepts", "mark_counterexample"}
        has_irreversible = any(op.operation in irreversible for op in patch.operations)
        if has_irreversible and not patch.inverse_operations:
            return False
        return True
