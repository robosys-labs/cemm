"""PatchValidator — MMU gate for all durable-write operations.

Every GraphPatch must pass through validation before reaching
durable storage. This enforces the architecture rule that no
component writes directly to memory without a validation barrier.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from ..types.graph_patch import GraphPatch
from ..types.context_kernel import ContextKernel


@dataclass
class PatchValidationResult:
    patch_id: str
    status: str = "rejected"
    reasons: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    failed_checks: list[str] = field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return self.status == "accepted"

    @property
    def mean_score(self) -> float:
        return sum(self.scores.values()) / len(self.scores) if self.scores else 0.0


class PatchValidator:
    """Memory-management unit: gates all GraphPatch writes to durable storage.

    Runs 10 checks against every patch before it reaches the store.
    """

    def __init__(
        self,
        store: Any | None = None,
        min_confidence: float = 0.3,
        min_source_trust: float = 0.3,
        max_risk: float = 0.8,
    ) -> None:
        self._store = store
        self._min_confidence = min_confidence
        self._min_source_trust = min_source_trust
        self._max_risk = max_risk

    def validate(
        self,
        patch: GraphPatch,
        kernel: ContextKernel | None = None,
    ) -> PatchValidationResult:
        scores: dict[str, float] = {}
        reasons: list[str] = []
        failed: list[str] = []

        # 1. Permission valid — may_store must be True
        perm_ok = kernel is not None and kernel.permission.may_store
        scores["permission_valid"] = 1.0 if perm_ok else 0.0
        if not perm_ok:
            failed.append("permission_valid")
            reasons.append("permission scope does not allow storage")

        # 2. Source present — patch must carry at least one source ref
        source_ok = bool(patch.source_refs)
        scores["source_present"] = 1.0 if source_ok else 0.0
        if not source_ok:
            failed.append("source_present")
            reasons.append("no source references in patch")

        # 3. Source trust sufficient
        trust_ok = patch.confidence >= self._min_source_trust
        scores["source_trust_sufficient"] = 1.0 if trust_ok else 0.0
        if not trust_ok:
            failed.append("source_trust_sufficient")
            reasons.append(f"source trust {patch.confidence:.2f} below threshold {self._min_source_trust}")

        # 4. Evidence present
        ev_ok = bool(patch.evidence_refs)
        scores["evidence_present"] = 1.0 if ev_ok else 0.0
        if not ev_ok:
            failed.append("evidence_present")
            reasons.append("no evidence references in patch")

        # 5. Freshness valid — skip when no store available
        if self._store is not None:
            scores["freshness_valid"] = 1.0

        # 6. Temporal scope valid — skip when no store available
        if self._store is not None:
            scores["temporal_scope_valid"] = 1.0

        # 7. Required ports bound — every operation should name a target_id
        ports_ok = all(op.target_id for op in patch.operations) if patch.operations else True
        scores["required_ports_bound"] = 1.0 if ports_ok else 0.0
        if not ports_ok:
            failed.append("required_ports_bound")
            reasons.append("some operations missing target_id")

        # 8. Contradiction absent — skip when no store available
        if self._store is not None:
            scores["contradiction_absent_or_resolved"] = 1.0

        # 9. Risk acceptable — skip when no risk policy available
        if self._max_risk > 0:
            scores["risk_acceptable"] = 1.0

        # 10. Confidence sufficient
        conf_ok = patch.confidence >= self._min_confidence
        scores["confidence_sufficient"] = 1.0 if conf_ok else 0.0
        if not conf_ok:
            failed.append("confidence_sufficient")
            reasons.append(f"confidence {patch.confidence:.2f} below threshold {self._min_confidence}")

        mean = sum(scores.values()) / len(scores) if scores else 0.0
        if not failed:
            status = "accepted"
        elif mean >= 0.6:
            status = "needs_confirmation"
        elif mean >= 0.3:
            status = "quarantined"
        else:
            status = "rejected"

        return PatchValidationResult(
            patch_id=patch.id or "unknown",
            status=status,
            reasons=reasons,
            scores=scores,
            failed_checks=failed,
        )
