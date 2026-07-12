"""MMU gate for graph-patch durable writes.

Validation is operation-aware and uses the same normalized relation identity as
the durable store. Queried/open propositions and internal placeholders fail
closed before memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..kernel.proposition_semantics import is_internal_identifier
from ..memory.relation_identity import (
    RelationIdentity,
    cardinality_from_fields,
    object_key_from_fields,
)
from ..types.context_kernel import ContextKernel
from ..types.graph_patch import GraphPatch, PatchOperation


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
    rejected_operation_target_ids: list[str] = field(default_factory=list)
    quarantine_reason: str = ""
    required_user_confirmation: list[str] = field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return self.status == "accepted"

    @property
    def mean_score(self) -> float:
        return sum(self.scores.values()) / len(self.scores) if self.scores else 0.0


class PatchValidator:
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
        current_signal: Any | None = None,
    ) -> PatchValidationResult:
        result = PatchValidationResult(patch_id=patch.id or "unknown")
        self._patch_check(result, "permission_valid", bool(kernel and kernel.permission.may_store),
                          "permission scope does not allow storage")
        self._patch_check(result, "source_present", bool(patch.source_refs), "no source references in patch")
        trust_ok = bool(
            patch.confidence >= self._min_source_trust
            or (kernel and kernel.memory.source_trust_keys and any(ref in kernel.memory.source_trust_keys for ref in patch.source_refs))
        )
        self._patch_check(result, "source_trust_sufficient", trust_ok, "source trust below threshold")
        self._patch_check(result, "evidence_present", bool(patch.evidence_refs), "no evidence references in patch")
        self._patch_check(result, "confidence_sufficient", patch.confidence >= self._min_confidence,
                          f"patch confidence {patch.confidence:.2f} below {self._min_confidence:.2f}")
        self._patch_check(result, "required_ports_bound", all(op.target_id for op in patch.operations),
                          "some operations are missing target_id")

        risk = float(getattr(getattr(kernel, "permission", None), "risk_score", 0.0) or 0.0)
        self._patch_check(result, "risk_acceptable", risk <= self._max_risk,
                          f"risk {risk:.2f} exceeds {self._max_risk:.2f}")
        freshness_ok, freshness_reason = self._check_temporal_evidence(patch, kernel, current_signal)
        self._patch_check(result, "freshness_valid", freshness_ok, freshness_reason)

        for operation in patch.operations:
            self._validate_operation(operation, patch, result)

        hard_failures = [name for name in result.failed_checks if name not in {"operation_confirmation"}]
        if hard_failures or result.rejected_operation_target_ids:
            result.status = "rejected"
        elif result.required_user_confirmation:
            result.status = "needs_confirmation"
        else:
            result.status = "accepted"
        if result.status == "rejected":
            result.quarantine_reason = "; ".join(result.reasons)
        return result

    def _validate_operation(
        self,
        operation: PatchOperation,
        patch: GraphPatch,
        result: PatchValidationResult,
    ) -> None:
        reasons: list[str] = []
        confirmation_reason = ""
        if not operation.target_id:
            reasons.append("missing target_id")
        if operation.confidence < self._min_confidence:
            reasons.append(f"operation confidence {operation.confidence:.2f} below {self._min_confidence:.2f}")

        if operation.operation == "upsert_relation_candidate":
            fields = operation.fields
            features = fields.get("features", {}) or {}
            proposition_mode = str(features.get("proposition_mode", "asserted") or "asserted")
            open_roles = features.get("open_roles", []) or []
            if proposition_mode == "queried" or open_roles:
                reasons.append("queried/open proposition cannot become durable relation")
            if not RelationIdentity.from_fields(fields).relation_key:
                reasons.append("missing relation_key")
            if not RelationIdentity.from_fields(fields).subject_key:
                reasons.append("missing relation subject")
            object_key = object_key_from_fields(fields)
            if not object_key:
                reasons.append("missing relation object")
            if is_internal_identifier(str(fields.get("object_surface", "") or "")):
                reasons.append("internal identifier cannot be stored as object surface")
            if str(fields.get("object_surface", "") or "").strip().lower() == "topic":
                reasons.append("role label cannot be stored as object value")

            schema_reason = self._schema_reason(fields)
            if schema_reason:
                reasons.append(schema_reason)
            contradiction_ok, contradiction_reason, needs_confirmation = self._relation_consistency(fields)
            if not contradiction_ok:
                reasons.append(contradiction_reason)
            elif needs_confirmation:
                confirmation_reason = contradiction_reason

            subject = str(
                fields.get("subject_entity_id", "")
                or fields.get("subject_concept_id", "")
                or fields.get("subject_surface", "")
            ).lower()
            if subject in {"self", "you", "entity:you", "entity:self"}:
                confirmation_reason = confirmation_reason or "self-referential assertion requires confirmation"

        elif operation.operation == "upsert_concept_candidate":
            surface = str(operation.fields.get("surface", "") or "")
            key = str(operation.fields.get("concept_key", "") or "")
            if is_internal_identifier(surface) or key.startswith("role:"):
                reasons.append("internal role/identifier cannot become durable concept")
        elif operation.operation == "custom:upsert_claim":
            confirmation_reason = "legacy custom claim requires confirmation"

        if reasons:
            result.rejected_operation_target_ids.append(operation.target_id)
            result.rejected_operations.append(f"{operation.target_id or operation.operation}: {'; '.join(reasons)}")
            result.reasons.extend(reason for reason in reasons if reason not in result.reasons)
            result.failed_checks.append(f"operation:{operation.target_id or operation.operation}")
            result.check_results.append(ValidationCheck(
                f"operation:{operation.target_id or operation.operation}", False, 0.0, "; ".join(reasons)
            ))
            return

        result.accepted_operations.append(operation.target_id)
        result.check_results.append(ValidationCheck(
            f"operation:{operation.target_id}", True, 1.0, confirmation_reason
        ))
        if confirmation_reason:
            result.required_user_confirmation.append(operation.target_id)
            result.reasons.append(confirmation_reason)

    def _relation_consistency(self, fields: dict[str, Any]) -> tuple[bool, str, bool]:
        if self._store is None:
            return True, "", False
        identity = RelationIdentity.from_fields(fields)
        cardinality = cardinality_from_fields(fields, schema_store=self._schema_store, default="unknown")
        object_key = object_key_from_fields(fields)
        if hasattr(self._store, "records_for_identity"):
            records = self._store.records_for_identity(identity, active_only=True)
            different = [
                record for record in records
                if getattr(record, "object_key", lambda: "")() not in {"", object_key}
            ]
        else:
            existing = self._store.query_relations(
                relation_key=identity.relation_key,
                subject_entity_id=str(fields.get("subject_entity_id", "") or ""),
                subject_concept_id=str(fields.get("subject_concept_id", "") or ""),
                dimension=identity.dimension,
                relation_scope=identity.relation_scope,
                allow_inheritance=False,
                allow_inverse=False,
                active_only=True,
            )
            different = [
                frame for frame in existing
                if (frame.object.entity_id or frame.object.concept_id or frame.object.surface) not in {"", object_key}
            ]
        if not different:
            return True, "", False
        if cardinality in {"many", "set"}:
            return True, "", False
        update_policy = str((fields.get("features", {}) or {}).get("update_policy", "") or "")
        if cardinality in {"single", "optional_one"} and update_policy in {"replace", "correct", "supersede"}:
            return True, "supersedes prior active value for the same semantic slot", False
        strongest = max(float(getattr(item, "confidence", 0.0) or 0.0) for item in different)
        reason = (
            f"different active value exists for relation slot {identity.as_key()!r}; "
            f"cardinality={cardinality}"
        )
        if cardinality == "unknown" or strongest >= self._contradiction_threshold:
            return True, reason, True
        return True, reason, True

    def _schema_reason(self, fields: dict[str, Any]) -> str:
        if self._schema_store is None:
            return ""
        relation_key = str(fields.get("relation_key", "") or "")
        schema = self._schema_store.get(relation_key) if relation_key else None
        if schema is None:
            return ""
        if not object_key_from_fields(fields) or not RelationIdentity.from_fields(fields).subject_key:
            return f"schema {relation_key}: required subject/object roles are not bound"
        return ""

    def _check_temporal_evidence(
        self,
        patch: GraphPatch,
        kernel: ContextKernel | None,
        current_signal: Any | None,
    ) -> tuple[bool, str]:
        if kernel is None or self._store is None or not patch.evidence_refs:
            return True, ""
        now = float(getattr(getattr(kernel, "time", None), "now", 0.0) or 0.0)
        if now <= 0:
            return True, ""
        signals = []
        for ref in [*patch.evidence_refs, *patch.source_refs]:
            signal = self._store.signals.get(ref)
            if signal is not None and hasattr(signal, "observed_at"):
                signals.append(signal)
        if not signals and current_signal is not None and hasattr(current_signal, "observed_at"):
            signals.append(current_signal)
        for signal in signals:
            age = now - float(signal.observed_at)
            if age > self._temporal_threshold:
                return False, f"evidence {getattr(signal, 'id', '')} is stale ({age:.0f}s)"
        return True, ""

    @staticmethod
    def _patch_check(
        result: PatchValidationResult,
        name: str,
        passed: bool,
        reason: str,
    ) -> None:
        result.scores[name] = 1.0 if passed else 0.0
        result.check_results.append(ValidationCheck(name, passed, result.scores[name], "" if passed else reason))
        if not passed:
            result.failed_checks.append(name)
            if reason and reason not in result.reasons:
                result.reasons.append(reason)
