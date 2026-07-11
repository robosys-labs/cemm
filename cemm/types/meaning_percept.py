from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Evidence ─────────────────────────────────────────────────────────────

@dataclass
class AtomEvidence:
    source: str = ""
    span_id: str = ""
    group_id: str = ""
    surface: str = ""
    confidence: float = 0.5
    rationale: str = ""


# ── Surface / Span ───────────────────────────────────────────────────────

@dataclass
class SurfaceSpan:
    id: str = ""
    start_token: int = 0
    end_token: int = 0
    surface: str = ""
    normalized: str = ""
    tokens: list[str] = field(default_factory=list)
    language: str = "und"
    span_type: str = "token"
    source: str = "surface"
    confidence: float = 0.5


@dataclass
class PredicatePhrase:
    id: str = ""
    group_id: str = ""
    surface: str = ""
    start_token: int = 0
    end_token: int = 0
    predicate_key: str = ""
    predicate_surface: str = ""
    actor_role: str | None = None
    object_role: str | None = None
    target_role: str | None = None
    place_role: str | None = None
    modality: str = "observed"
    polarity: str = "affirmed"
    confidence: float = 0.5
    evidence: list[AtomEvidence] = field(default_factory=list)


@dataclass
class MeaningAtomOutcome:
    id: str = ""
    group_id: str = ""
    predicate_id: str = ""
    atom_kind: str = ""
    atom_key: str = ""
    affected_role: str = ""
    expected_change: str = ""
    valence: str = "unknown"
    confidence: float = 0.5
    evidence: list[AtomEvidence] = field(default_factory=list)


# ── Core Percept Atoms ──────────────────────────────────────────────────

@dataclass
class ReferentAtom:
    surface: str
    entity_id: str | None = None
    entity_type: str = "unknown"
    role: str = "topic"
    known: bool = False
    source: str = "surface"
    confidence: float = 0.5
    group_id: str = ""
    span_id: str = ""
    evidence: list[AtomEvidence] = field(default_factory=list)


@dataclass
class ActionAtom:
    surface: str
    action_key: str = ""
    actor_role: str | None = None
    object_role: str | None = None
    target_role: str | None = None
    place_role: str | None = None
    modality: str = "observed"
    polarity: str = "affirmed"
    source: str = "surface"
    confidence: float = 0.5
    group_id: str = ""
    span_id: str = ""
    evidence: list[AtomEvidence] = field(default_factory=list)
    schema_slots: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class StateAtom:
    surface: str = ""
    state_key: str = ""
    holder_role: str | None = None
    dimension: str = "unknown"
    polarity: str = "unknown"
    intensity: float = 0.5
    value: str | int | float | bool | None = None
    source: str = "surface"
    confidence: float = 0.5
    group_id: str = ""
    span_id: str = ""
    evidence: list[AtomEvidence] = field(default_factory=list)


@dataclass
class RelationAtom:
    relation_key: str = ""
    source_role: str = ""
    target_role: str = ""
    surface: str = ""
    source: str = "surface"
    confidence: float = 0.5
    group_id: str = ""
    span_id: str = ""
    evidence: list[AtomEvidence] = field(default_factory=list)


@dataclass
class NeedAtom:
    holder_role: str = ""
    need_key: str = ""
    intensity: float = 0.5
    known_satisfiers: list[str] = field(default_factory=list)
    source: str = "surface"
    confidence: float = 0.5
    group_id: str = ""
    span_id: str = ""
    evidence: list[AtomEvidence] = field(default_factory=list)


@dataclass
class AffordanceAtom:
    entity_role_or_id: str = ""
    affords: list[str] = field(default_factory=list)
    condition: str = ""
    source: str = "surface"
    confidence: float = 0.5
    group_id: str = ""
    span_id: str = ""
    evidence: list[AtomEvidence] = field(default_factory=list)


@dataclass
class OutcomeAtom:
    affected_entity_role: str = ""
    changed_dimension: str = ""
    direction: str = "unknown"
    event_key: str = ""
    confidence: float = 0.5
    group_id: str = ""
    predicate_id: str = ""
    expected_after_state: str | None = None
    state_changes: list[dict[str, Any]] = field(default_factory=list)
    relation_changes: list[dict[str, Any]] = field(default_factory=list)
    resource_changes: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ValenceAtom:
    target_role: str = ""
    valence: str = "neutral"
    intensity: float = 0.5
    source: str = "surface"
    confidence: float = 0.5
    affected_entity_role: str = ""
    entity_class: str = "unknown"
    rationale: str = ""
    evidence: list[AtomEvidence] = field(default_factory=list)


# ── Extension Atoms ──────────────────────────────────────────────────────

@dataclass
class QualityAtom:
    surface: str = ""
    quality_key: str = ""
    holder_role: str = ""
    dimension: str = "unknown"
    polarity: str = "unknown"
    intensity: float = 0.5
    value: str = ""
    source: str = "surface"
    confidence: float = 0.5
    group_id: str = ""
    span_id: str = ""
    evidence: list[AtomEvidence] = field(default_factory=list)


@dataclass
class QuantityAtom:
    surface: str = ""
    quantity_key: str = ""
    value: str | int | float | None = None
    unit: str = ""
    approximate: bool = False
    source: str = "surface"
    confidence: float = 0.5
    group_id: str = ""
    span_id: str = ""
    evidence: list[AtomEvidence] = field(default_factory=list)


@dataclass
class TimeAtom:
    surface: str = ""
    time_key: str = ""
    relation: str = "unknown"
    value: str = ""
    tense: str = ""
    reference_point: str = ""
    source: str = "surface"
    confidence: float = 0.5
    group_id: str = ""
    span_id: str = ""
    evidence: list[AtomEvidence] = field(default_factory=list)


@dataclass
class PlaceAtom:
    surface: str = ""
    place_key: str = ""
    relation: str = "unknown"
    spatial_relation: str = ""
    reference_entity_role: str = ""
    source: str = "surface"
    confidence: float = 0.5
    group_id: str = ""
    span_id: str = ""
    evidence: list[AtomEvidence] = field(default_factory=list)


@dataclass
class IntentAtom:
    surface: str = ""
    intent_key: str = "statement"
    target_role: str = ""
    is_question: bool = False
    is_command: bool = False
    is_teaching: bool = False
    is_repair: bool = False
    target: str = ""
    polarity: str = "affirmed"
    source: str = "surface"
    confidence: float = 0.5
    group_id: str = ""
    span_id: str = ""
    evidence: list[AtomEvidence] = field(default_factory=list)


@dataclass
class ModalityAtom:
    surface: str = ""
    modality_key: str = "observed"
    scope: str = "group"
    modality_type: str = ""
    polarity: str = "affirmed"
    source: str = "surface"
    confidence: float = 0.5
    group_id: str = ""
    span_id: str = ""
    evidence: list[AtomEvidence] = field(default_factory=list)


@dataclass
class EvidenceAtom:
    surface: str = ""
    evidence_key: str = ""
    source_role: str = "user"
    freshness: str = "unknown"
    evidence_type: str = ""
    supports_claim: str = ""
    confidence: float = 0.5
    group_id: str = ""
    span_id: str = ""


@dataclass
class SourceAtom:
    source_role: str = "user"
    surface: str = ""
    reliability: str = "unverified"
    permission_scope: str = "public"
    source_type: str = ""
    confidence: float = 0.5
    group_id: str = ""
    span_id: str = ""


# ── Permission / Self (new in v4) ───────────────────────────────────────

@dataclass
class PermissionAtom:
    permission_key: str = "conversation"
    scope: str = "conversation"
    holder_role: str = "user"
    target_role: str = "source"
    confidence: float = 0.5
    group_id: str = ""
    span_id: str = ""


@dataclass
class SelfAtom:
    self_key: str = "self"
    role: str = "listener"
    surface: str = "self"
    confidence: float = 0.8
    group_id: str = ""
    span_id: str = ""


# ── Hypothesis / Interpretation (new in v4) ─────────────────────────────

@dataclass
class CandidateInterpretation:
    id: str = ""
    group_id: str = ""
    span_id: str = ""
    surface: str = ""
    interpretation_kind: str = "atom"
    atom_kind: str = ""
    atom_key: str = ""
    role: str = ""
    predicate_key: str = ""
    candidate_act_type: str = ""
    features: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    selected: bool = False
    evidence: list[AtomEvidence] = field(default_factory=list)


@dataclass
class MeaningHypothesis:
    id: str = ""
    group_id: str = ""
    span_id: str = ""
    surface: str = ""
    hypothesis_type: str = "lexical"
    candidates: list[CandidateInterpretation] = field(default_factory=list)
    selected_candidate_ids: list[str] = field(default_factory=list)
    confidence: float = 0.5
    reason: str = ""


@dataclass
class MeaningGroup:
    id: str = ""
    parent_group_id: str = ""
    relation_to_parent: str = ""
    surface: str = ""
    start_token: int = 0
    end_token: int = 0
    tokens: list[str] = field(default_factory=list)
    connective_before: str = ""
    separator_before: str = ""
    separator_after: str = ""
    group_type: str = "clause"
    referents: list[ReferentAtom] = field(default_factory=list)
    actions: list[ActionAtom] = field(default_factory=list)
    states: list[StateAtom] = field(default_factory=list)
    relations: list[RelationAtom] = field(default_factory=list)
    needs: list[NeedAtom] = field(default_factory=list)
    intents: list[IntentAtom] = field(default_factory=list)
    predicate_ids: list[str] = field(default_factory=list)
    outcome_ids: list[str] = field(default_factory=list)
    hypothesis_ids: list[str] = field(default_factory=list)
    child_group_ids: list[str] = field(default_factory=list)
    candidate_act_types: list[str] = field(default_factory=list)
    uncertainty_reasons: list[str] = field(default_factory=list)
    confidence: float = 0.5


# ── EventSchema ──────────────────────────────────────────────────────────

@dataclass
class EventSchema:
    schema_key: str = ""
    actor_role: str | None = None
    action_key: str = ""
    object_role: str | None = None
    target_role: str | None = None
    place_role: str | None = None
    source_role: str | None = None
    destination_role: str | None = None
    recipient_role: str | None = None
    preconditions: list[str] = field(default_factory=list)
    expected_outcomes: list[OutcomeAtom] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    source: str = "seed"
    confidence: float = 0.5


# ── SafetyFrame ─────────────────────────────────────────────────────────

@dataclass
class SafetyFrame:
    category: str = "none"
    severity: str = "low"
    rationale: str = ""
    actor_entity_id: str | None = None
    target_entity_id: str | None = None
    requested_action: str | None = None
    harmful_outcomes: list[OutcomeAtom] = field(default_factory=list)
    must_not_do: list[str] = field(default_factory=list)
    allowed_response_mode: str = "none"
    confidence: float = 0.5


# ── RetrospectiveRepairFrame ────────────────────────────────────────────

@dataclass
class RetrospectiveRepairFrame:
    needed: bool = False
    reason: str = ""
    failed_turn_id: str = ""
    repair_target: str = ""
    repair_type: str = ""
    original_intent: str = ""
    confidence: float = 0.5


# ── SituationFrame ──────────────────────────────────────────────────────

@dataclass
class SituationFrame:
    id: str = ""
    signal_id: str = ""
    context_id: str = ""
    actor: ReferentAtom | None = None
    action: ActionAtom | None = None
    object: ReferentAtom | None = None
    target: ReferentAtom | None = None
    place: ReferentAtom | None = None
    source: ReferentAtom | None = None
    destination: ReferentAtom | None = None
    recipient: ReferentAtom | None = None
    state_reports: list[StateAtom] = field(default_factory=list)
    needs: list[NeedAtom] = field(default_factory=list)
    affordances: list[AffordanceAtom] = field(default_factory=list)
    expected_outcomes: list[OutcomeAtom] = field(default_factory=list)
    valences: list[ValenceAtom] = field(default_factory=list)
    event_schema_ids: list[str] = field(default_factory=list)
    missing_slots: list[str] = field(default_factory=list)
    uncertainty_reasons: list[str] = field(default_factory=list)
    safety_frame: SafetyFrame | None = None
    repair_frame: RetrospectiveRepairFrame | None = None
    confidence: float = 0.5


# ── RetrievalPlan ───────────────────────────────────────────────────────

@dataclass
class RetrievalPlan:
    mode: str = "none"
    query: str = ""
    targets: list[str] = field(default_factory=list)
    reason: str = ""
    target_predicates: list[str] = field(default_factory=list)
    target_entity_ids: list[str] = field(default_factory=list)
    target_model_kinds: list[str] = field(default_factory=list)
    freshness_required: bool = False
    permission_scope: str = "public"
    confidence: float = 0.5


# ── MeaningPerceptPacket ────────────────────────────────────────────────

@dataclass
class MeaningPerceptPacket:
    id: str = ""
    signal_id: str = ""
    context_id: str = ""
    raw_text: str = ""
    tokens: list[str] = field(default_factory=list)
    normalized_tokens: list[str] = field(default_factory=list)
    cased_tokens: list[str] = field(default_factory=list)
    repaired_tokens: list[str] = field(default_factory=list)
    normalized_forms: list[str] = field(default_factory=list)
    punctuation_features: dict[str, Any] = field(default_factory=dict)
    language: str = "und"
    language_confidence: float = 0.0
    code_switched: bool = False
    spans: list[SurfaceSpan] = field(default_factory=list)

    # Group/hypothesis structure (v4)
    meaning_groups: list[MeaningGroup] = field(default_factory=list)
    predicate_phrases: list[PredicatePhrase] = field(default_factory=list)
    atom_outcomes: list[MeaningAtomOutcome] = field(default_factory=list)
    meaning_hypotheses: list[MeaningHypothesis] = field(default_factory=list)

    # UOL graph integration
    uol_graph: Any | None = None
    uol_training_example: dict[str, Any] = field(default_factory=dict)
    graph_patch_candidates: list[Any] = field(default_factory=list)

    # Pipeline trace
    core_loop_trace: dict[str, Any] = field(default_factory=dict)
    core_loop_stage: str = "perceived"

    # Flat atom lists (v3 compat, still populated)
    referents: list[ReferentAtom] = field(default_factory=list)
    actions: list[ActionAtom] = field(default_factory=list)
    states: list[StateAtom] = field(default_factory=list)
    relations: list[RelationAtom] = field(default_factory=list)
    needs: list[NeedAtom] = field(default_factory=list)
    affordances: list[AffordanceAtom] = field(default_factory=list)
    outcomes: list[OutcomeAtom] = field(default_factory=list)
    valences: list[ValenceAtom] = field(default_factory=list)
    qualities: list[QualityAtom] = field(default_factory=list)
    quantities: list[QuantityAtom] = field(default_factory=list)
    times: list[TimeAtom] = field(default_factory=list)
    places: list[PlaceAtom] = field(default_factory=list)
    intents: list[IntentAtom] = field(default_factory=list)
    modalities: list[ModalityAtom] = field(default_factory=list)
    evidence: list[EvidenceAtom] = field(default_factory=list)
    sources: list[SourceAtom] = field(default_factory=list)
    permissions: list[PermissionAtom] = field(default_factory=list)
    self_atoms: list[SelfAtom] = field(default_factory=list)

    # 3.3 candidate-action lists (F-001, F-004, F-005)
    candidate_actions: list[ActionAtom] = field(default_factory=list)
    candidate_atom_outcomes: list[MeaningAtomOutcome] = field(default_factory=list)
    semantic_gaps: list[Any] = field(default_factory=list)

    unknown_lexemes: list[dict[str, Any]] = field(default_factory=list)
    idiom_candidates: list[dict[str, Any]] = field(default_factory=list)
    affect_markers: list[dict[str, Any]] = field(default_factory=list)

    attention_target: str | None = None
    speaker_entity_id: str = "user"
    listener_entity_id: str = "self"
    perception_trace: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    version: str = "4.1"


# ── OutputStateUpdate ────────────────────────────────────────────────────

@dataclass
class OutputStateUpdate:
    last_assistant_output_signal_id: str = ""
    last_assistant_intent: str = ""
    last_assistant_response_mode: str = ""
    pending_assistant_question: str | None = None
    expected_user_answer_type: str | None = None
    reply_obligation_created: str | None = None
