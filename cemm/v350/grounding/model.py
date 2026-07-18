"""Phase-8 joint referent and claim-grounding contracts.

Grounding chooses identity candidates under explicit type, storage, context,
time, discourse, and multimodal constraints.  It does not admit claims as facts,
mutate referents, or auto-apply identity merge/split decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping

from ..language.model import Span
from ..schema.model import StorageKind, semantic_fingerprint


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class MentionTargetClass(StrEnum):
    REFERENT = "referent"
    EVENT = "event"
    STATE = "state"
    PROPOSITION = "proposition"
    CLAIM = "claim"
    SCHEMA_TOPIC = "schema_topic"
    CLAIM_SOURCE = "claim_source"
    AUDIENCE = "audience"
    MULTIMODAL_TRACK = "multimodal_track"
    SYSTEM_OUTPUT = "system_output"


class GroundingFactorKind(StrEnum):
    IDENTITY = "identity"
    TYPE = "type"
    STORAGE = "storage"
    CONTEXT = "context"
    TIME = "time"
    DISCOURSE = "discourse"
    SALIENCE = "salience"
    SYNTAX = "syntax"
    DESCRIPTION = "description"
    MULTIMODAL = "multimodal"
    SYSTEM_OUTPUT = "system_output"
    SCHEMA_TOPIC = "schema_topic"
    CLAIM_ROLE = "claim_role"
    COREFERENCE = "coreference"
    DISTINCTNESS = "distinctness"
    PROVISIONAL = "provisional"


class GroundingConstraintKind(StrEnum):
    COREFER = "corefer"
    DISTINCT = "distinct"
    TYPE_COMPATIBLE = "type_compatible"
    STORAGE_COMPATIBLE = "storage_compatible"
    SAME_CONTEXT = "same_context"
    CLAIM_SOURCE = "claim_source"
    CLAIM_AUDIENCE = "claim_audience"


class CandidateOrigin(StrEnum):
    STORE = "store"
    DISCOURSE = "discourse"
    MULTIMODAL = "multimodal"
    SYSTEM_OUTPUT = "system_output"
    SCHEMA = "schema"
    PROVISIONAL = "provisional"


@dataclass(frozen=True, slots=True)
class GroundingFactor:
    factor_ref: str
    factor_kind: GroundingFactorKind
    score: float
    evidence_refs: tuple[str, ...]
    reason: str
    hard: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.factor_ref, "factor_ref")
        if not isfinite(self.score):
            raise ValueError("grounding factor score must be finite")
        if not self.evidence_refs:
            raise ValueError("grounding factor requires evidence")
        if not self.reason.strip():
            raise ValueError("grounding factor requires a reason")


@dataclass(frozen=True, slots=True)
class MentionHypothesis:
    mention_ref: str
    source_ref: str
    span: Span
    surface: str
    normalized_surface: str
    target_class: MentionTargetClass = MentionTargetClass.REFERENT
    expected_type_refs: tuple[str, ...] = ()
    expected_storage_kinds: tuple[StorageKind, ...] = ()
    sense_candidate_refs: tuple[str, ...] = ()
    construction_candidate_refs: tuple[str, ...] = ()
    description_application_refs: tuple[str, ...] = ()
    context_ref: str = "actual"
    time_ref: str | None = None
    syntactic_role: str = ""
    source_role: str = ""
    salience: float = 0.0
    evidence_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in ((self.mention_ref, "mention_ref"), (self.source_ref, "source_ref"),
                             (self.context_ref, "context_ref")):
            _ref(value, label)
        if not self.surface:
            raise ValueError("mention requires surface evidence")
        if not 0 <= self.salience <= 1:
            raise ValueError("mention salience must be within [0, 1]")
        _unique(self.expected_type_refs, "mention expected types")
        _unique(self.expected_storage_kinds, "mention expected storage kinds")
        _unique(self.sense_candidate_refs, "mention sense candidates")
        _unique(self.construction_candidate_refs, "mention construction candidates")
        _unique(self.description_application_refs, "mention descriptions")
        _unique(self.evidence_refs, "mention evidence")
        if not self.evidence_refs:
            raise ValueError("mention hypothesis requires evidence")


@dataclass(frozen=True, slots=True)
class GroundingConstraint:
    constraint_ref: str
    constraint_kind: GroundingConstraintKind
    mention_refs: tuple[str, ...]
    required: bool = True
    evidence_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.constraint_ref, "constraint_ref")
        if not self.mention_refs:
            raise ValueError("grounding constraint requires mentions")
        _unique(self.mention_refs, "grounding constraint mentions")
        if self.constraint_kind in {GroundingConstraintKind.COREFER, GroundingConstraintKind.DISTINCT} and len(self.mention_refs) < 2:
            raise ValueError("coreference/distinctness requires at least two mentions")
        if not self.evidence_refs:
            raise ValueError("grounding constraint requires evidence")


@dataclass(frozen=True, slots=True)
class DiscourseAnchor:
    anchor_ref: str
    referent_ref: str
    context_ref: str
    salience: float
    turn_index: int
    role_refs: tuple[str, ...] = ()
    type_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in ((self.anchor_ref, "anchor_ref"), (self.referent_ref, "referent_ref"),
                             (self.context_ref, "context_ref")):
            _ref(value, label)
        if not 0 <= self.salience <= 1 or self.turn_index < 0:
            raise ValueError("invalid discourse anchor salience/turn")
        _unique(self.role_refs, "discourse roles")
        _unique(self.type_refs, "discourse types")
        _unique(self.evidence_refs, "discourse evidence")
        if not self.evidence_refs:
            raise ValueError("discourse anchor requires evidence")


@dataclass(frozen=True, slots=True)
class MultimodalTrack:
    track_ref: str
    modality: str
    context_ref: str
    referent_ref: str | None = None
    type_refs: tuple[str, ...] = ()
    valid_time_ref: str | None = None
    salience: float = 0.5
    evidence_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in ((self.track_ref, "track_ref"), (self.modality, "modality"),
                             (self.context_ref, "context_ref")):
            _ref(value, label)
        if not 0 <= self.salience <= 1:
            raise ValueError("multimodal salience must be within [0, 1]")
        _unique(self.type_refs, "multimodal types")
        _unique(self.evidence_refs, "multimodal evidence")
        if not self.evidence_refs:
            raise ValueError("multimodal track requires evidence")


@dataclass(frozen=True, slots=True)
class SystemOutputAnchor:
    output_ref: str
    context_ref: str
    content_referent_refs: tuple[str, ...]
    target_refs: tuple[str, ...] = ()
    turn_index: int = 0
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ref(self.output_ref, "output_ref")
        _ref(self.context_ref, "context_ref")
        if self.turn_index < 0:
            raise ValueError("system-output turn index cannot be negative")
        _unique(self.content_referent_refs, "system-output contents")
        _unique(self.target_refs, "system-output targets")
        _unique(self.evidence_refs, "system-output evidence")
        if not self.content_referent_refs and not self.target_refs:
            raise ValueError("system-output anchor requires content or targets")
        if not self.evidence_refs:
            raise ValueError("system-output anchor requires evidence")


@dataclass(frozen=True, slots=True)
class GroundingCandidate:
    candidate_ref: str
    mention_ref: str
    target_ref: str
    origin: CandidateOrigin
    storage_kind: StorageKind
    type_refs: tuple[str, ...]
    context_refs: tuple[str, ...]
    factors: tuple[GroundingFactor, ...]
    provisional: bool = False
    valid_time_ref: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in ((self.candidate_ref, "candidate_ref"), (self.mention_ref, "mention_ref"),
                             (self.target_ref, "target_ref")):
            _ref(value, label)
        if not self.context_refs:
            raise ValueError("grounding candidate requires context")
        _unique(self.type_refs, "candidate types")
        _unique(self.context_refs, "candidate contexts")
        if not self.factors:
            raise ValueError("grounding candidate requires proof factors")
        if self.origin == CandidateOrigin.PROVISIONAL and not self.provisional:
            raise ValueError("provisional-origin candidate must remain provisional")
        _unique(tuple(item.factor_ref for item in self.factors), "candidate factors")

    @property
    def local_score(self) -> float:
        return sum(item.score for item in self.factors)


@dataclass(frozen=True, slots=True)
class GroundingAssignment:
    assignment_ref: str
    candidate_refs: tuple[str, ...]
    mention_to_target: tuple[tuple[str, str], ...]
    score: float
    factor_refs: tuple[str, ...]
    satisfied_constraint_refs: tuple[str, ...] = ()
    violated_optional_constraint_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ref(self.assignment_ref, "assignment_ref")
        if not isfinite(self.score):
            raise ValueError("grounding assignment score must be finite")
        _unique(tuple(item[0] for item in self.mention_to_target), "assignment mentions")
        _unique(self.candidate_refs, "assignment candidates")
        _unique(self.factor_refs, "assignment factors")
        _unique(self.satisfied_constraint_refs, "satisfied constraints")
        _unique(self.violated_optional_constraint_refs, "optional constraint violations")
        if set(self.satisfied_constraint_refs).intersection(self.violated_optional_constraint_refs):
            raise ValueError("constraint cannot be both satisfied and violated")


@dataclass(frozen=True, slots=True)
class GroundingResult:
    grounding_ref: str
    mentions: tuple[MentionHypothesis, ...]
    candidates: tuple[GroundingCandidate, ...]
    assignments: tuple[GroundingAssignment, ...]
    selected_assignment_ref: str | None
    unresolved_mention_refs: tuple[str, ...]
    ambiguous_mention_refs: tuple[str, ...]
    frontier_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.grounding_ref, "grounding_ref")
        mention_sequence = tuple(item.mention_ref for item in self.mentions)
        _unique(mention_sequence, "mentions")
        mention_refs = set(mention_sequence)
        candidate_sequence = tuple(item.candidate_ref for item in self.candidates)
        _unique(candidate_sequence, "candidates")
        candidate_refs = set(candidate_sequence)
        assignment_sequence = tuple(item.assignment_ref for item in self.assignments)
        _unique(assignment_sequence, "assignments")
        assignment_refs = set(assignment_sequence)
        if self.selected_assignment_ref is not None and self.selected_assignment_ref not in assignment_refs:
            raise ValueError("selected grounding assignment is unknown")
        if not set(self.unresolved_mention_refs).issubset(mention_refs):
            raise ValueError("unresolved mention is unknown")
        if not set(self.ambiguous_mention_refs).issubset(mention_refs):
            raise ValueError("ambiguous mention is unknown")
        if set(self.unresolved_mention_refs).intersection(self.ambiguous_mention_refs):
            raise ValueError("mention cannot be both unresolved and ambiguous")
        if not self.evidence_refs:
            raise ValueError("grounding result requires evidence")
        candidates_by_ref = {item.candidate_ref: item for item in self.candidates}
        for candidate in self.candidates:
            if candidate.mention_ref not in mention_refs:
                raise ValueError("candidate references unknown mention")
        for assignment in self.assignments:
            if not set(assignment.candidate_refs).issubset(candidate_refs):
                raise ValueError("assignment references unknown candidate")
            selected_candidates = [candidates_by_ref[ref] for ref in assignment.candidate_refs]
            expected_mapping = {(item.mention_ref, item.target_ref) for item in selected_candidates}
            if set(assignment.mention_to_target) != expected_mapping:
                raise ValueError("assignment mapping does not match selected candidates")
            expected_factor_refs = {
                factor.factor_ref
                for candidate in selected_candidates
                for factor in candidate.factors
            }
            if set(assignment.factor_refs) != expected_factor_refs:
                raise ValueError("assignment factors do not match selected candidates")

    @property
    def selected(self) -> GroundingAssignment | None:
        return next((item for item in self.assignments if item.assignment_ref == self.selected_assignment_ref), None)

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint("grounding-result", self, 64)


@dataclass(frozen=True, slots=True)
class ClaimGrounding:
    claim_grounding_ref: str
    claim_mention_ref: str
    proposition_ref: str
    source_ref: str
    audience_refs: tuple[str, ...]
    source_context_ref: str
    reported_context_ref: str
    evidence_refs: tuple[str, ...]
    confidence: float
    admission_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in ((self.claim_grounding_ref, "claim_grounding_ref"),
                             (self.claim_mention_ref, "claim_mention_ref"),
                             (self.proposition_ref, "proposition_ref"),
                             (self.source_ref, "source_ref"),
                             (self.source_context_ref, "source_context_ref"),
                             (self.reported_context_ref, "reported_context_ref")):
            _ref(value, label)
        if self.source_context_ref == self.reported_context_ref:
            raise ValueError("claim grounding must preserve attributed context")
        if not 0 <= self.confidence <= 1:
            raise ValueError("claim grounding confidence must be within [0, 1]")
        if self.admission_refs:
            raise ValueError("Phase-8 claim grounding cannot admit proposition truth")
        _unique(self.audience_refs, "claim audiences")
        _unique(self.evidence_refs, "claim grounding evidence")
        if not self.evidence_refs:
            raise ValueError("claim grounding requires evidence")


@dataclass(frozen=True, slots=True)
class ProvisionalReferentProposal:
    proposal_ref: str
    mention_ref: str
    referent_ref: str
    storage_kind: StorageKind
    type_refs: tuple[str, ...]
    identity_value: str
    context_ref: str
    evidence_refs: tuple[str, ...]
    confidence: float
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, label in ((self.proposal_ref, "proposal_ref"), (self.mention_ref, "mention_ref"),
                             (self.referent_ref, "referent_ref"), (self.context_ref, "context_ref")):
            _ref(value, label)
        if not self.identity_value:
            raise ValueError("provisional referent requires identity evidence")
        if not 0 <= self.confidence <= 1:
            raise ValueError("proposal confidence must be within [0, 1]")
        if not self.evidence_refs or not self.reasons:
            raise ValueError("provisional proposal requires evidence and reasons")
        _unique(self.type_refs, "provisional types")
        _unique(self.evidence_refs, "provisional evidence")
        _unique(self.reasons, "provisional reasons")


@dataclass(frozen=True, slots=True)
class IdentityMergeProposal:
    proposal_ref: str
    left_ref: str
    right_ref: str
    context_ref: str
    confidence: float
    evidence_refs: tuple[str, ...]
    supporting_factor_refs: tuple[str, ...]
    conflicting_factor_refs: tuple[str, ...] = ()
    requires_review: bool = True

    def __post_init__(self) -> None:
        for value, label in ((self.proposal_ref, "proposal_ref"), (self.left_ref, "left_ref"),
                             (self.right_ref, "right_ref"), (self.context_ref, "context_ref")):
            _ref(value, label)
        if self.left_ref == self.right_ref:
            raise ValueError("merge proposal requires distinct referents")
        if not 0 <= self.confidence <= 1:
            raise ValueError("merge confidence must be within [0, 1]")
        if not self.evidence_refs or not self.supporting_factor_refs:
            raise ValueError("merge proposal requires evidence")
        if not self.requires_review:
            raise ValueError("merge proposal must require review")
        _unique(self.evidence_refs, "merge evidence")
        _unique(self.supporting_factor_refs, "merge supporting factors")
        _unique(self.conflicting_factor_refs, "merge conflicting factors")


@dataclass(frozen=True, slots=True)
class IdentitySplitProposal:
    proposal_ref: str
    referent_ref: str
    partition_keys: tuple[str, ...]
    context_ref: str
    confidence: float
    evidence_refs: tuple[str, ...]
    conflicting_factor_refs: tuple[str, ...]
    requires_review: bool = True

    def __post_init__(self) -> None:
        for value, label in ((self.proposal_ref, "proposal_ref"), (self.referent_ref, "referent_ref"),
                             (self.context_ref, "context_ref")):
            _ref(value, label)
        if len(self.partition_keys) < 2:
            raise ValueError("split proposal requires at least two partitions")
        if not 0 <= self.confidence <= 1:
            raise ValueError("split confidence must be within [0, 1]")
        if not self.evidence_refs or not self.conflicting_factor_refs:
            raise ValueError("split proposal requires conflict evidence")
        if not self.requires_review:
            raise ValueError("split proposal must require review")
        _unique(self.partition_keys, "split partitions")
        _unique(self.evidence_refs, "split evidence")
        _unique(self.conflicting_factor_refs, "split conflicting factors")


def _ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty reference")


def _unique(values: tuple[Any, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {label}")
