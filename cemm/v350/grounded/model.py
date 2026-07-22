"""Grounded semantic substrate for CEMM v3.5.1 Phase 9.

These are cycle-local semantic/discourse contracts.  They deliberately keep identity,
state, claims, world belief, query gaps and answer projections distinct.  None of the
classes below imply durable admission merely by existing in a cycle workspace.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Iterable, Mapping

from ..csir.model import CSIRGraph, CSIRRef, ExactAuthorityPin


class GroundedModelError(ValueError):
    pass


class IdentityCandidateStatus(str, Enum):
    CANDIDATE = "candidate"
    PROVISIONAL = "provisional"
    RESOLVED = "resolved"
    DISPUTED = "disputed"


class CorrectionKind(str, Enum):
    CORRECT = "correct"
    RETRACT = "retract"
    SUPERSEDE = "supersede"


class GapKind(str, Enum):
    REFERENT = "referent"
    PROPERTY = "property"
    STATE = "state"
    RELATION = "relation"
    EVENT_ROLE = "event_role"
    PROPOSITION_TRUTH = "proposition_truth"
    DEFINITION = "definition"
    CAUSAL_EXPLANATION = "causal_explanation"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class SemanticContext:
    """Cycle/world context identity without admitting any proposition as true."""

    context_ref: str
    context_kind: str
    permission_ref: str
    parent_context_ref: str | None = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ref(self.context_ref, "context_ref")
        _ref(self.context_kind, "context_kind")
        _ref(self.permission_ref, "context permission_ref")
        if self.parent_context_ref is not None:
            _ref(self.parent_context_ref, "parent_context_ref")
            if self.parent_context_ref == self.context_ref:
                raise GroundedModelError("semantic context cannot parent itself")
        _unique(self.evidence_refs, "context evidence")


def _ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise GroundedModelError(f"{label} must be non-empty")


def _unique(values: Iterable[Any], label: str) -> None:
    values = tuple(values)
    if len(values) != len(set(values)):
        raise GroundedModelError(f"{label} must be unique")


def _score(value: float, label: str) -> None:
    if not isfinite(value) or not 0.0 <= value <= 1.0:
        raise GroundedModelError(f"{label} must be finite in [0,1]")


@dataclass(frozen=True, slots=True)
class Referent:
    referent_ref: str
    context_refs: tuple[str, ...]
    permission_ref: str
    exact_type_pins: tuple[ExactAuthorityPin, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    durable_identity: bool = False

    def __post_init__(self) -> None:
        _ref(self.referent_ref, "referent_ref")
        _ref(self.permission_ref, "permission_ref")
        if not self.context_refs:
            raise GroundedModelError("referent requires at least one context")
        _unique(self.context_refs, "referent contexts")
        _unique((x.key for x in self.exact_type_pins), "referent type pins")
        _unique(self.evidence_refs, "referent evidence")


@dataclass(frozen=True, slots=True)
class TypeAssertion:
    assertion_ref: str
    referent_ref: str
    type_pin: ExactAuthorityPin
    support: float
    context_ref: str
    evidence_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ref(self.assertion_ref, "type assertion_ref")
        _ref(self.referent_ref, "type assertion referent_ref")
        _ref(self.context_ref, "type assertion context_ref")
        _score(self.support, "type assertion support")
        _unique(self.evidence_refs, "type assertion evidence")
        _unique(self.proof_refs, "type assertion proofs")


@dataclass(frozen=True, slots=True)
class AliasName:
    alias_ref: str
    referent_ref: str
    surface: str
    language_tag: str
    normalized_key: str
    evidence_refs: tuple[str, ...]
    context_ref: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.alias_ref, "alias_ref"),
            (self.referent_ref, "alias referent_ref"),
            (self.surface, "alias surface"),
            (self.language_tag, "alias language_tag"),
            (self.normalized_key, "alias normalized_key"),
            (self.context_ref, "alias context_ref"),
        ):
            _ref(value, label)
        if not self.evidence_refs:
            raise GroundedModelError("alias/name requires evidence")
        _unique(self.evidence_refs, "alias evidence")


@dataclass(frozen=True, slots=True)
class IdentityCandidate:
    candidate_ref: str
    mention_ref: str
    referent_ref: str
    status: IdentityCandidateStatus
    support: float
    evidence_refs: tuple[str, ...]
    constraint_refs: tuple[str, ...] = ()
    competing_candidate_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.candidate_ref, "identity candidate_ref"),
            (self.mention_ref, "identity mention_ref"),
            (self.referent_ref, "identity referent_ref"),
        ):
            _ref(value, label)
        _score(self.support, "identity support")
        if not self.evidence_refs:
            raise GroundedModelError("identity candidate requires evidence")
        _unique(self.evidence_refs, "identity evidence")
        _unique(self.constraint_refs, "identity constraints")
        _unique(self.competing_candidate_refs, "identity competitors")
        if self.candidate_ref in self.competing_candidate_refs:
            raise GroundedModelError("identity candidate cannot compete with itself")


@dataclass(frozen=True, slots=True)
class Property:
    property_ref: str
    application_ref: CSIRRef
    holder_ref: str
    property_definition_pin: ExactAuthorityPin
    value_refs: tuple[CSIRRef, ...]
    context_ref: str
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ref(self.property_ref, "property_ref")
        _ref(self.holder_ref, "property holder_ref")
        _ref(self.context_ref, "property context_ref")
        if not self.value_refs:
            raise GroundedModelError("property requires at least one value")
        _unique(self.value_refs, "property values")
        _unique(self.evidence_refs, "property evidence")


@dataclass(frozen=True, slots=True)
class Relation:
    relation_ref: str
    application_ref: CSIRRef
    relation_definition_pin: ExactAuthorityPin
    participant_refs: tuple[tuple[ExactAuthorityPin, CSIRRef], ...]
    context_ref: str
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ref(self.relation_ref, "relation_ref")
        _ref(self.context_ref, "relation context_ref")
        if not self.participant_refs:
            raise GroundedModelError("relation requires participants")
        _unique((pin.key for pin, _ in self.participant_refs), "relation role ports")
        _unique(self.evidence_refs, "relation evidence")


@dataclass(frozen=True, slots=True)
class StateValueCandidate:
    # Categorical values use an exact semantic pin; continuous/vector/relational domains
    # may instead point at a CSIR value node or carry a finite literal observation.
    value_pin: ExactAuthorityPin | None
    support: float
    value_ref: CSIRRef | None = None
    literal_value: str | int | float | bool | None = None
    evidence_refs: tuple[str, ...] = ()
    active_assignment_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        choices = sum(value is not None for value in (self.value_pin, self.value_ref, self.literal_value))
        if choices != 1:
            raise GroundedModelError(
                "state value candidate requires exactly one pin, CSIR value ref, or literal value"
            )
        if isinstance(self.literal_value, float) and not isfinite(self.literal_value):
            raise GroundedModelError("state literal value must be finite")
        _score(self.support, "state value support")
        _unique(self.evidence_refs, "state value evidence")
        _unique(self.active_assignment_refs, "state assignment refs")

    @property
    def identity_key(self):
        if self.value_pin is not None:
            return ("pin", self.value_pin.key)
        if self.value_ref is not None:
            return ("ref", self.value_ref.kind.value, self.value_ref.ref)
        return ("literal", type(self.literal_value).__name__, repr(self.literal_value))


@dataclass(frozen=True, slots=True)
class StateVariable:
    state_variable_ref: str
    holder_ref: str
    dimension_pin: ExactAuthorityPin
    entitled_value_pins: tuple[ExactAuthorityPin, ...]
    value_candidates: tuple[StateValueCandidate, ...]
    context_ref: str
    valid_time_ref: str | None = None
    entitlement_proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ref(self.state_variable_ref, "state_variable_ref")
        _ref(self.holder_ref, "state holder_ref")
        _ref(self.context_ref, "state context_ref")
        _unique((x.key for x in self.entitled_value_pins), "entitled state values")
        _unique((x.identity_key for x in self.value_candidates), "state value candidates")
        entitled = {x.key for x in self.entitled_value_pins}
        invalid = [
            x.value_pin.key for x in self.value_candidates
            if x.value_pin is not None and entitled and x.value_pin.key not in entitled
        ]
        if invalid:
            raise GroundedModelError(f"active/candidate state values outside entitlement:{invalid}")
        _unique(self.entitlement_proof_refs, "state entitlement proofs")


@dataclass(frozen=True, slots=True)
class TimeContext:
    time_ref: str
    context_ref: str
    relation_to_cycle: str
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ref(self.time_ref, "time_ref")
        _ref(self.context_ref, "time context_ref")
        _ref(self.relation_to_cycle, "time relation_to_cycle")
        _unique(self.evidence_refs, "time context evidence")


@dataclass(frozen=True, slots=True)
class ParticipantRole:
    role_ref: str
    referent_ref: str
    frame_ref: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _ref(self.role_ref, "participant role_ref")
        _ref(self.referent_ref, "participant referent_ref")
        _ref(self.frame_ref, "participant frame_ref")
        if not self.evidence_refs:
            raise GroundedModelError("participant role binding requires evidence")
        _unique(self.evidence_refs, "participant role evidence")


@dataclass(frozen=True, slots=True)
class Mention:
    mention_ref: str
    source_ref: str
    span_start: int
    span_end: int
    form_candidate_refs: tuple[str, ...] = ()
    identity_candidate_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ref(self.mention_ref, "mention_ref")
        _ref(self.source_ref, "mention source_ref")
        if self.span_start < 0 or self.span_end < self.span_start:
            raise GroundedModelError("invalid mention span")
        _unique(self.form_candidate_refs, "mention forms")
        _unique(self.identity_candidate_refs, "mention identity candidates")


@dataclass(frozen=True, slots=True)
class MentionChain:
    chain_ref: str
    mention_refs: tuple[str, ...]
    referent_candidate_refs: tuple[str, ...]
    resolved_referent_ref: str | None = None
    proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ref(self.chain_ref, "mention chain_ref")
        if not self.mention_refs:
            raise GroundedModelError("mention chain requires mentions")
        _unique(self.mention_refs, "mention chain mentions")
        _unique(self.referent_candidate_refs, "mention chain candidates")
        if self.resolved_referent_ref is not None:
            _ref(self.resolved_referent_ref, "resolved referent_ref")


@dataclass(frozen=True, slots=True)
class Proposition:
    proposition_ref: str
    content: CSIRGraph
    context_ref: str
    source_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    truth_status: str = "undetermined"

    def __post_init__(self) -> None:
        _ref(self.proposition_ref, "proposition_ref")
        _ref(self.context_ref, "proposition context_ref")
        _ref(self.truth_status, "proposition truth_status")
        _unique(self.source_refs, "proposition sources")
        _unique(self.evidence_refs, "proposition evidence")


@dataclass(frozen=True, slots=True)
class Claim:
    claim_ref: str
    proposition_ref: str
    claimant_ref: str
    audience_refs: tuple[str, ...]
    source_context_ref: str
    reported_context_ref: str
    evidence_refs: tuple[str, ...]
    commitment_strength: float

    def __post_init__(self) -> None:
        for value, label in (
            (self.claim_ref, "claim_ref"),
            (self.proposition_ref, "claim proposition_ref"),
            (self.claimant_ref, "claimant_ref"),
            (self.source_context_ref, "claim source_context_ref"),
            (self.reported_context_ref, "claim reported_context_ref"),
        ):
            _ref(value, label)
        # Source and reported contexts are distinct semantic roles, but a claim may
        # legitimately be made in and about the same context.  Attribution is preserved
        # structurally by the two fields; equality never implies world admission.
        _unique(self.audience_refs, "claim audiences")
        if not self.evidence_refs:
            raise GroundedModelError("claim requires evidence")
        _unique(self.evidence_refs, "claim evidence")
        _score(self.commitment_strength, "claim commitment strength")


@dataclass(frozen=True, slots=True)
class InformationGap:
    gap_ref: str
    kind: GapKind
    variable_ref: CSIRRef
    restriction_graph: CSIRGraph
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _ref(self.gap_ref, "gap_ref")
        if self.variable_ref.kind.value != "variable":
            raise GroundedModelError("information gap must preserve an explicit CSIR variable")
        if not self.evidence_refs:
            raise GroundedModelError("information gap requires evidence")
        _unique(self.evidence_refs, "information gap evidence")


@dataclass(frozen=True, slots=True)
class AnswerProjection:
    projection_ref: str
    requested_variable_ref: CSIRRef
    projection_pin: ExactAuthorityPin | None = None
    requested_port_pin: ExactAuthorityPin | None = None
    # Exact grounded causal projection identities. Empty for ordinary queries; these are
    # semantic projection outputs and are never inferred from English wording in Stage 10.
    causal_target_variable_ref: str = ""
    causal_source_variable_ref: str = ""
    causal_contrast_value_ref: str = ""
    causal_intervention_context_ref: str = ""

    def __post_init__(self) -> None:
        _ref(self.projection_ref, "answer projection_ref")
        if self.requested_variable_ref.kind.value != "variable":
            raise GroundedModelError("answer projection must target a query variable")


@dataclass(frozen=True, slots=True)
class Query:
    query_ref: str
    query_graph: CSIRGraph
    gap_refs: tuple[str, ...]
    answer_projection: AnswerProjection
    speaker_ref: str
    audience_refs: tuple[str, ...]
    context_ref: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _ref(self.query_ref, "query_ref")
        _ref(self.speaker_ref, "query speaker_ref")
        _ref(self.context_ref, "query context_ref")
        if not self.gap_refs:
            raise GroundedModelError("query must preserve at least one explicit gap")
        _unique(self.gap_refs, "query gaps")
        _unique(self.audience_refs, "query audiences")
        if not self.evidence_refs:
            raise GroundedModelError("query requires evidence")
        _unique(self.evidence_refs, "query evidence")


@dataclass(frozen=True, slots=True)
class CorrectionRetraction:
    correction_ref: str
    kind: CorrectionKind
    source_ref: str
    target_ref: str
    replacement_ref: str | None
    context_ref: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, label in (
            (self.correction_ref, "correction_ref"),
            (self.source_ref, "correction source_ref"),
            (self.target_ref, "correction target_ref"),
            (self.context_ref, "correction context_ref"),
        ):
            _ref(value, label)
        if self.kind in {CorrectionKind.CORRECT, CorrectionKind.SUPERSEDE} and not self.replacement_ref:
            raise GroundedModelError(f"{self.kind.value} requires replacement_ref")
        if self.kind is CorrectionKind.RETRACT and self.replacement_ref is not None:
            raise GroundedModelError("retraction cannot silently introduce replacement content")
        if not self.evidence_refs:
            raise GroundedModelError("correction/retraction requires evidence")
        _unique(self.evidence_refs, "correction/retraction evidence")


@dataclass(frozen=True, slots=True)
class GroundedSemanticSubstrate:
    substrate_ref: str
    contexts: tuple[SemanticContext, ...] = ()
    referents: tuple[Referent, ...] = ()
    type_assertions: tuple[TypeAssertion, ...] = ()
    aliases: tuple[AliasName, ...] = ()
    identity_candidates: tuple[IdentityCandidate, ...] = ()
    properties: tuple[Property, ...] = ()
    relations: tuple[Relation, ...] = ()
    state_variables: tuple[StateVariable, ...] = ()
    time_contexts: tuple[TimeContext, ...] = ()
    participant_roles: tuple[ParticipantRole, ...] = ()
    mentions: tuple[Mention, ...] = ()
    mention_chains: tuple[MentionChain, ...] = ()
    propositions: tuple[Proposition, ...] = ()
    claims: tuple[Claim, ...] = ()
    gaps: tuple[InformationGap, ...] = ()
    queries: tuple[Query, ...] = ()
    corrections: tuple[CorrectionRetraction, ...] = ()
    frontier_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.substrate_ref, "substrate_ref")
        context_refs = tuple(item.context_ref for item in self.contexts)
        _unique(context_refs, "substrate contexts")
        contexts = set(context_refs)
        parent_by_context = {item.context_ref: item.parent_context_ref for item in self.contexts}
        for context in self.contexts:
            if context.parent_context_ref is not None and context.parent_context_ref not in contexts:
                raise GroundedModelError(
                    f"semantic context references missing parent:{context.parent_context_ref}"
                )
            seen: set[str] = set()
            current: str | None = context.context_ref
            while current is not None:
                if current in seen:
                    raise GroundedModelError(f"cyclic semantic context ancestry:{context.context_ref}")
                seen.add(current)
                current = parent_by_context.get(current)

        referent_refs = tuple(item.referent_ref for item in self.referents)
        _unique(referent_refs, "substrate referents")
        referents = set(referent_refs)
        if contexts:
            for referent in self.referents:
                missing = set(referent.context_refs).difference(contexts)
                if missing:
                    raise GroundedModelError(
                        f"referent references missing semantic contexts:{sorted(missing)}"
                    )

        _unique((x.candidate_ref for x in self.identity_candidates), "identity candidates")
        _unique((x.mention_ref for x in self.mentions), "mentions")
        _unique((x.chain_ref for x in self.mention_chains), "mention chains")
        _unique((x.proposition_ref for x in self.propositions), "propositions")
        _unique((x.claim_ref for x in self.claims), "claims")
        _unique((x.gap_ref for x in self.gaps), "gaps")
        _unique((x.query_ref for x in self.queries), "queries")
        _unique((x.correction_ref for x in self.corrections), "corrections")
        _unique(self.frontier_refs, "substrate frontiers")

        mention_refs = {item.mention_ref for item in self.mentions}
        identity_refs = {item.candidate_ref for item in self.identity_candidates}
        proposition_refs = {item.proposition_ref for item in self.propositions}
        gap_refs = {item.gap_ref for item in self.gaps}

        for assertion in self.type_assertions:
            if assertion.referent_ref not in referents:
                raise GroundedModelError(f"type assertion references missing referent:{assertion.referent_ref}")
        for alias in self.aliases:
            if alias.referent_ref not in referents:
                raise GroundedModelError(f"alias references missing referent:{alias.referent_ref}")
        for property_value in self.properties:
            if property_value.holder_ref not in referents:
                raise GroundedModelError(f"property references missing holder:{property_value.holder_ref}")
        for state in self.state_variables:
            if state.holder_ref not in referents:
                raise GroundedModelError(f"state variable references missing holder:{state.holder_ref}")
        for role in self.participant_roles:
            if role.referent_ref not in referents:
                raise GroundedModelError(f"participant role references missing referent:{role.referent_ref}")
        for candidate in self.identity_candidates:
            if candidate.mention_ref not in mention_refs:
                raise GroundedModelError(f"identity candidate references missing mention:{candidate.mention_ref}")
            if candidate.referent_ref not in referents:
                raise GroundedModelError(f"identity candidate references missing referent:{candidate.referent_ref}")
            missing_competitors = set(candidate.competing_candidate_refs).difference(identity_refs)
            if missing_competitors:
                raise GroundedModelError(
                    f"identity candidate references missing competitors:{sorted(missing_competitors)}"
                )
        for chain in self.mention_chains:
            missing = set(chain.mention_refs).difference(mention_refs)
            if missing:
                raise GroundedModelError(f"mention chain references missing mentions:{sorted(missing)}")
            missing_candidates = set(chain.referent_candidate_refs).difference(identity_refs)
            if missing_candidates:
                raise GroundedModelError(
                    f"mention chain references missing identity candidates:{sorted(missing_candidates)}"
                )
            if chain.resolved_referent_ref is not None and chain.resolved_referent_ref not in referents:
                raise GroundedModelError(
                    f"mention chain resolves to missing referent:{chain.resolved_referent_ref}"
                )
        for mention in self.mentions:
            missing = set(mention.identity_candidate_refs).difference(identity_refs)
            if missing:
                raise GroundedModelError(f"mention references missing identity candidates:{sorted(missing)}")
        for claim in self.claims:
            if claim.proposition_ref not in proposition_refs:
                raise GroundedModelError(f"claim references missing proposition:{claim.proposition_ref}")
            if claim.claimant_ref not in referents:
                raise GroundedModelError(f"claim references missing claimant referent:{claim.claimant_ref}")
        for query in self.queries:
            missing = set(query.gap_refs).difference(gap_refs)
            if missing:
                raise GroundedModelError(f"query references missing information gaps:{sorted(missing)}")
            if not any(
                gap.variable_ref == query.answer_projection.requested_variable_ref
                for gap in self.gaps if gap.gap_ref in query.gap_refs
            ):
                raise GroundedModelError(
                    "query answer projection must target a variable preserved by one of its gaps"
                )


__all__ = [
    "AliasName",
    "AnswerProjection",
    "Claim",
    "CorrectionKind",
    "CorrectionRetraction",
    "GapKind",
    "GroundedModelError",
    "GroundedSemanticSubstrate",
    "IdentityCandidate",
    "IdentityCandidateStatus",
    "InformationGap",
    "Mention",
    "MentionChain",
    "ParticipantRole",
    "Property",
    "Proposition",
    "Query",
    "Referent",
    "SemanticContext",
    "Relation",
    "StateValueCandidate",
    "StateVariable",
    "TimeContext",
    "TypeAssertion",
]
