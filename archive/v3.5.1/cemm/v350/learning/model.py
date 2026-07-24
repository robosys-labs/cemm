"""Phase-13 learning lifecycle contracts.

The learning layer owns evidence/frontier/package/competence/promotion lifecycle.
It never owns domain semantics: candidate semantic records remain canonical
schema/language/transition/storage records and become executable only through
per-record, per-use promotion decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import TYPE_CHECKING, Any, Mapping

from ..schema.model import SchemaClass, UseAuthorization, UseDecision, UseOperation, semantic_fingerprint

if TYPE_CHECKING:
    from ..storage.model import RecordKind


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class LearningPackageStatus(StrEnum):
    FRONTIER = "frontier"
    CANDIDATE = "candidate"
    EVIDENCE_ACCUMULATING = "evidence_accumulating"
    COMPETENCE_PENDING = "competence_pending"
    PROMOTABLE = "promotable"
    BLOCKED = "blocked"
    CONTRADICTED = "contradicted"
    PROMOTED = "promoted_for_selected_uses"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"
    INVALIDATED = "invalidated"
    REJECTED = "rejected"


class FrontierResolutionStatus(StrEnum):
    OPEN = "open"
    PARTIAL = "partial"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"


class EvidencePolarity(StrEnum):
    SUPPORT = "support"
    COUNTEREXAMPLE = "counterexample"
    CORRECTION = "correction"
    RETRACTION = "retraction"


class CompetenceOutcome(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class PromotionDecisionKind(StrEnum):
    PROMOTE = "promote"
    PRESERVE_CANDIDATE = "preserve_candidate"
    BLOCK = "block"
    REJECT = "reject"
    RETRACT = "retract"
    SUPERSEDE = "supersede"


class InvalidationStatus(StrEnum):
    PROPOSED = "proposed"
    APPLIED = "applied"
    RECOMPUTATION_REQUIRED = "recomputation_required"
    RESOLVED = "resolved"


@dataclass(frozen=True, slots=True)
class PinnedRecord:
    record_kind: RecordKind
    record_ref: str
    revision: int
    record_fingerprint: str

    def __post_init__(self) -> None:
        _ref(self.record_ref, "pinned record_ref")
        _ref(self.record_fingerprint, "pinned record fingerprint")
        if self.revision < 1:
            raise ValueError("pinned record revision must be positive")

    @property
    def key(self) -> tuple[str, str, int]:
        return self.record_kind.value, self.record_ref, self.revision


@dataclass(frozen=True, slots=True)
class PromotionUseGrant:
    """Per exact candidate revision, per-use authority decision."""

    candidate_pin: PinnedRecord
    operation: UseOperation
    decision: UseDecision
    competence_result_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    reason: str = ""

    def __post_init__(self) -> None:
        if self.decision not in {UseDecision.ALLOW, UseDecision.PROVISIONAL, UseDecision.PRESERVE_ONLY}:
            raise ValueError("promotion grant cannot encode implicit deny as positive authority")
        _unique(self.competence_result_refs, "promotion competence result refs")
        _unique(self.evidence_refs, "promotion grant evidence refs")
        if self.decision in {UseDecision.ALLOW, UseDecision.PROVISIONAL} and not self.competence_result_refs:
            raise ValueError("executable/provisional promotion requires exact competence result refs")


@dataclass(frozen=True, slots=True)
class LearningPackageRecord:
    package_ref: str
    package_family: str
    candidate_pins: tuple[PinnedRecord, ...]
    dependency_pins: tuple[PinnedRecord, ...]
    frontier_refs: tuple[str, ...]
    evidence_link_refs: tuple[str, ...]
    counterexample_link_refs: tuple[str, ...]
    competence_case_refs: tuple[str, ...]
    requested_use_authorizations: tuple[UseAuthorization, ...]
    promotion_policy_ref: str
    review_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    source_lineage_refs: tuple[str, ...] = ()
    scope_ref: str = "global"
    permission_ref: str = "conversation"
    sensitivity: str = "normal"
    lifecycle_status: LearningPackageStatus = LearningPackageStatus.CANDIDATE
    revision: int = 1
    supersedes_revision: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.package_ref, "package_ref"),
            (self.package_family, "package_family"),
            (self.promotion_policy_ref, "promotion_policy_ref"),
            (self.scope_ref, "scope_ref"),
            (self.permission_ref, "permission_ref"),
            (self.sensitivity, "sensitivity"),
        ):
            _ref(value, label)
        if self.revision < 1:
            raise ValueError("learning package revision must be positive")
        if self.supersedes_revision is not None and not 1 <= self.supersedes_revision < self.revision:
            raise ValueError("learning package supersedes_revision must target an older revision")
        if not self.candidate_pins:
            raise ValueError("learning package requires at least one exact candidate pin")
        _unique(tuple(item.key for item in self.candidate_pins), "learning package candidate pins")
        _unique(tuple(item.key for item in self.dependency_pins), "learning package dependency pins")
        _unique(self.frontier_refs, "learning package frontiers")
        _unique(self.evidence_link_refs, "learning package evidence links")
        _unique(self.counterexample_link_refs, "learning package counterexample links")
        _unique(self.competence_case_refs, "learning package competence cases")
        _unique(tuple(item.operation for item in self.requested_use_authorizations), "learning package requested uses")
        _unique(self.review_refs, "learning package reviews")
        _unique(self.provenance_refs, "learning package provenance")
        _unique(self.source_lineage_refs, "learning package source lineage")
        if set(self.evidence_link_refs).intersection(self.counterexample_link_refs):
            raise ValueError("support and counterexample links must remain independently attributable")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint("learning-package", self, 64)


@dataclass(frozen=True, slots=True)
class LearningFrontierRecord:
    frontier_ref: str
    missing_contract: str
    expected_record_kinds: tuple[RecordKind, ...]
    expected_schema_classes: tuple[SchemaClass, ...]
    accepted_anchor_types: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    candidate_refs: tuple[str, ...] = ()
    target_ref: str | None = None
    dependency_depth: int = 0
    sensitivity: str = "normal"
    best_question_uol_ref: str | None = None
    resolution_status: FrontierResolutionStatus = FrontierResolutionStatus.OPEN
    context_ref: str = "actual"
    permission_ref: str = "conversation"
    revision: int = 1
    supersedes_revision: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.frontier_ref, "frontier_ref"),
            (self.missing_contract, "missing_contract"),
            (self.sensitivity, "sensitivity"),
            (self.context_ref, "context_ref"),
            (self.permission_ref, "permission_ref"),
        ):
            _ref(value, label)
        if self.target_ref is not None:
            _ref(self.target_ref, "frontier target_ref")
        if self.best_question_uol_ref is not None:
            _ref(self.best_question_uol_ref, "frontier question UOL ref")
        if self.dependency_depth < 0:
            raise ValueError("frontier dependency depth cannot be negative")
        if self.revision < 1:
            raise ValueError("frontier revision must be positive")
        if self.supersedes_revision is not None and not 1 <= self.supersedes_revision < self.revision:
            raise ValueError("frontier supersedes_revision must target an older revision")
        _unique(self.expected_record_kinds, "frontier expected record kinds")
        _unique(self.expected_schema_classes, "frontier expected schema classes")
        _unique(self.accepted_anchor_types, "frontier anchor types")
        _unique(self.evidence_refs, "frontier evidence")
        _unique(self.candidate_refs, "frontier candidates")
        if not (self.expected_record_kinds or self.expected_schema_classes):
            raise ValueError("frontier must declare an expected structural family")

    @property
    def structural_key(self) -> str:
        return semantic_fingerprint(
            "learning-frontier-key",
            (
                self.target_ref,
                self.missing_contract,
                tuple(item.value for item in self.expected_record_kinds),
                tuple(item.value for item in self.expected_schema_classes),
                self.accepted_anchor_types,
                self.context_ref,
                self.permission_ref,
            ),
            48,
        )


@dataclass(frozen=True, slots=True)
class LearningEvidenceLink:
    link_ref: str
    package_ref: str
    package_revision: int
    polarity: EvidencePolarity
    evidence_refs: tuple[str, ...]
    source_lineage_refs: tuple[str, ...]
    candidate_pin: PinnedRecord | None = None
    context_ref: str = "actual"
    time_ref: str | None = None
    weight: float = 1.0
    permission_ref: str = "conversation"
    revision: int = 1
    supersedes_revision: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.link_ref, "learning evidence link_ref"),
            (self.package_ref, "learning evidence package_ref"),
            (self.context_ref, "learning evidence context_ref"),
            (self.permission_ref, "learning evidence permission_ref"),
        ):
            _ref(value, label)
        if self.package_revision < 1:
            raise ValueError("learning evidence package revision must be positive")
        if self.revision != 1 or self.supersedes_revision is not None:
            raise ValueError("learning evidence links are append-only immutable identities; corrections/retractions require a new link_ref")
        if not isfinite(self.weight) or self.weight < 0.0:
            raise ValueError("learning evidence weight must be finite and non-negative")
        _unique(self.evidence_refs, "learning evidence refs")
        _unique(self.source_lineage_refs, "learning evidence source lineages")
        if not self.evidence_refs:
            raise ValueError("learning evidence link requires evidence")
        if not self.source_lineage_refs:
            raise ValueError("learning evidence link requires attributable source lineage")


@dataclass(frozen=True, slots=True)
class CompetenceResultRecord:
    result_ref: str
    package_ref: str
    package_revision: int
    use_operation: UseOperation
    candidate_pins: tuple[PinnedRecord, ...]
    dependency_pins: tuple[PinnedRecord, ...]
    case_refs: tuple[str, ...]
    outcome: CompetenceOutcome
    passed_case_refs: tuple[str, ...]
    failed_case_refs: tuple[str, ...]
    counterexample_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    failure_frontier_refs: tuple[str, ...]
    snapshot_revision: int
    boot_fingerprint: str
    overlay_fingerprint: str
    runner_ref: str
    runner_revision: str
    independent_lineage_refs: tuple[str, ...]
    environment_refs: tuple[str, ...]
    performance_ms: tuple[tuple[str, float], ...] = ()
    permission_ref: str = "internal"
    revision: int = 1
    supersedes_revision: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.result_ref, "competence result_ref"),
            (self.package_ref, "competence package_ref"),
            (self.boot_fingerprint, "competence boot fingerprint"),
            (self.overlay_fingerprint, "competence overlay fingerprint"),
            (self.runner_ref, "competence runner_ref"),
            (self.runner_revision, "competence runner_revision"),
            (self.permission_ref, "competence permission_ref"),
        ):
            _ref(value, label)
        if self.package_revision < 1 or self.snapshot_revision < 0:
            raise ValueError("competence revisions must be valid")
        if self.revision != 1 or self.supersedes_revision is not None:
            raise ValueError("competence results are append-only immutable identities; reruns require a new result_ref")
        _unique(tuple(item.key for item in self.candidate_pins), "competence candidate pins")
        _unique(tuple(item.key for item in self.dependency_pins), "competence dependency pins")
        for values, label in (
            (self.case_refs, "competence cases"),
            (self.passed_case_refs, "competence passed cases"),
            (self.failed_case_refs, "competence failed cases"),
            (self.counterexample_refs, "competence counterexamples"),
            (self.proof_refs, "competence proof refs"),
            (self.failure_frontier_refs, "competence failure frontiers"),
            (self.independent_lineage_refs, "competence independent lineages"),
            (self.environment_refs, "competence environments"),
        ):
            _unique(values, label)
        if not self.case_refs:
            raise ValueError("competence result requires explicit competence cases")
        if not set(self.passed_case_refs).issubset(self.case_refs) or not set(self.failed_case_refs).issubset(self.case_refs):
            raise ValueError("competence outcomes must reference declared cases")
        if set(self.passed_case_refs).intersection(self.failed_case_refs):
            raise ValueError("a competence case cannot both pass and fail")
        if self.outcome == CompetenceOutcome.PASSED:
            if self.failed_case_refs or set(self.passed_case_refs) != set(self.case_refs):
                raise ValueError("passed competence requires every declared case to pass")
            if not self.proof_refs:
                raise ValueError("passed competence requires proof lineage")
        for name, value in self.performance_ms:
            _ref(name, "competence performance metric")
            if not isfinite(value) or value < 0.0:
                raise ValueError("competence performance measurements must be non-negative")

    @property
    def substrate_fingerprint(self) -> str:
        return semantic_fingerprint(
            "competence-substrate",
            (
                self.package_ref,
                self.package_revision,
                self.use_operation.value,
                tuple(item.key + (item.record_fingerprint,) for item in self.candidate_pins),
                tuple(item.key + (item.record_fingerprint,) for item in self.dependency_pins),
                self.case_refs,
                self.snapshot_revision,
                self.boot_fingerprint,
                self.overlay_fingerprint,
                self.runner_ref,
                self.runner_revision,
            ),
            64,
        )


@dataclass(frozen=True, slots=True)
class PromotionDecisionRecord:
    decision_ref: str
    package_ref: str
    package_revision: int
    decision: PromotionDecisionKind
    candidate_pins: tuple[PinnedRecord, ...]
    use_grants: tuple[PromotionUseGrant, ...]
    policy_ref: str
    review_refs: tuple[str, ...]
    authorization_refs: tuple[str, ...]
    risk_refs: tuple[str, ...] = ()
    reason_refs: tuple[str, ...] = ()
    scope_ref: str = "global"
    permission_ref: str = "internal"
    revision: int = 1
    supersedes_revision: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.decision_ref, "promotion decision_ref"),
            (self.package_ref, "promotion package_ref"),
            (self.policy_ref, "promotion policy_ref"),
            (self.scope_ref, "promotion scope_ref"),
            (self.permission_ref, "promotion permission_ref"),
        ):
            _ref(value, label)
        if self.package_revision < 1:
            raise ValueError("promotion package revision must be positive")
        if self.revision != 1 or self.supersedes_revision is not None:
            raise ValueError("promotion decisions are append-only immutable identities; review changes require a new decision_ref")
        _unique(tuple(item.key for item in self.candidate_pins), "promotion candidate pins")
        _unique(
            tuple((item.candidate_pin.key, item.operation.value) for item in self.use_grants),
            "promotion per-record use grants",
        )
        for values, label in (
            (self.review_refs, "promotion reviews"),
            (self.authorization_refs, "promotion authorizations"),
            (self.risk_refs, "promotion risks"),
            (self.reason_refs, "promotion reasons"),
        ):
            _unique(values, label)
        known = {item.key for item in self.candidate_pins}
        if any(grant.candidate_pin.key not in known for grant in self.use_grants):
            raise ValueError("promotion grant targets a candidate outside the exact package decision")
        if self.decision == PromotionDecisionKind.PROMOTE:
            if not self.use_grants:
                raise ValueError("promote decision requires at least one explicit use grant")
            if not any(item.decision in {UseDecision.ALLOW, UseDecision.PROVISIONAL} for item in self.use_grants):
                raise ValueError("promote decision requires at least one executable or provisional use grant")
            if not self.review_refs or not self.authorization_refs:
                raise ValueError("promotion requires explicit review and authorization")
        elif self.use_grants:
            raise ValueError("non-promote decision cannot carry positive use grants")

    def grants_for(self, pin: PinnedRecord) -> tuple[PromotionUseGrant, ...]:
        return tuple(item for item in self.use_grants if item.candidate_pin.key == pin.key)


@dataclass(frozen=True, slots=True)
class LearningInvalidationRecord:
    invalidation_ref: str
    trigger_pins: tuple[PinnedRecord, ...]
    affected_pins: tuple[PinnedRecord, ...]
    package_refs: tuple[str, ...]
    invalidated_decision_refs: tuple[str, ...]
    recomputation_frontier_refs: tuple[str, ...]
    replay_required_refs: tuple[str, ...]
    reason: str
    status: InvalidationStatus
    evidence_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    context_ref: str = "actual"
    permission_ref: str = "internal"
    revision: int = 1
    supersedes_revision: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.invalidation_ref, "invalidation_ref"),
            (self.reason, "invalidation reason"),
            (self.context_ref, "invalidation context_ref"),
            (self.permission_ref, "invalidation permission_ref"),
        ):
            _ref(value, label)
        if self.revision < 1:
            raise ValueError("invalidation revision must be positive")
        if self.supersedes_revision is not None and not 1 <= self.supersedes_revision < self.revision:
            raise ValueError("invalidation supersedes_revision must target an older revision")
        _unique(tuple(item.key for item in self.trigger_pins), "invalidation trigger pins")
        # PatchOperation dependencies are keyed by record_ref. Multiple trigger
        # revisions of one identity must be collapsed into one causal change event.
        _unique(tuple(item.record_ref for item in self.trigger_pins), "invalidation trigger refs")
        _unique(tuple(item.key for item in self.affected_pins), "invalidation affected pins")
        for values, label in (
            (self.package_refs, "invalidation packages"),
            (self.invalidated_decision_refs, "invalidation decisions"),
            (self.recomputation_frontier_refs, "invalidation recomputation frontiers"),
            (self.replay_required_refs, "invalidation replay refs"),
            (self.evidence_refs, "invalidation evidence"),
            (self.proof_refs, "invalidation proofs"),
        ):
            _unique(values, label)
        if not self.trigger_pins:
            raise ValueError("invalidation requires at least one exact changed/retracted trigger")


@dataclass(frozen=True, slots=True)
class LearningBudget:
    maximum_dependency_depth: int = 8
    maximum_frontiers: int = 128
    maximum_candidates: int = 64
    maximum_dependency_nodes: int = 256
    maximum_competence_cases: int = 64

    def __post_init__(self) -> None:
        for value, label in (
            (self.maximum_dependency_depth, "maximum_dependency_depth"),
            (self.maximum_frontiers, "maximum_frontiers"),
            (self.maximum_candidates, "maximum_candidates"),
            (self.maximum_dependency_nodes, "maximum_dependency_nodes"),
            (self.maximum_competence_cases, "maximum_competence_cases"),
        ):
            if value < 1:
                raise ValueError(f"{label} must be positive")


def _ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty reference")


def _unique(values, label: str) -> None:
    items = tuple(values)
    if len(items) != len(set(items)):
        raise ValueError(f"{label} must be unique")
