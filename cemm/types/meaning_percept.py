"""Foundational meaning atoms and runtime packets for the event-centered semantic layer.

These dataclasses implement the primitives defined in architecture.md §5-§9
and cemm_foundational_fixes.md §4. They are the pre-UOL semantic substrate
that must exist before ConversationAct classification.

ConversationAct is a derived control label, not the foundational meaning unit.
EventSchema + EntityState + OutcomeValence are the foundational semantic units.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── ReferentAtom ──────────────────────────────────────────────────────────

@dataclass
class ReferentAtom:
    """A thing the utterance may refer to — person, self, user, object, place, etc."""
    surface: str
    entity_id: str | None = None
    entity_type: str = "unknown"  # self, user, person, object, place, animal, natural_entity, organization, abstract, unknown
    role: str = "topic"  # actor, target, object, place, source, destination, recipient, possessor, topic, speaker, listener
    known: bool = False
    source: str = "context"  # ner, pronoun, lexeme_memory, registry, context, capitalization, deixis
    confidence: float = 0.5


# ── ActionAtom ────────────────────────────────────────────────────────────

@dataclass
class ActionAtom:
    """A candidate verb/action/process with its semantic roles."""
    surface: str
    action_key: str = ""
    actor_role: str | None = None
    target_role: str | None = None
    object_role: str | None = None
    place_role: str | None = None
    modality: str = "observed"  # observed, requested, proposed, hypothetical, commanded, desired
    polarity: str = "affirmed"  # affirmed, negated, possible, unknown
    confidence: float = 0.5


# ── StateAtom ─────────────────────────────────────────────────────────────

@dataclass
class StateAtom:
    """Current or desired entity states."""
    surface: str = ""
    state_key: str = ""  # hungry, fine, sick, angry, useful, capable, confused
    holder_role: str | None = None
    dimension: str = "unknown"  # health, hunger, happiness, safety, knowledge, capability, trust, distance, possession, availability, relationship, unknown
    value: float = 0.0
    polarity: str = "unknown"  # positive, negative, neutral, unknown
    intensity: float = 0.5
    confidence: float = 0.5


# ── RelationAtom ──────────────────────────────────────────────────────────

@dataclass
class RelationAtom:
    """Relational meaning — geospatial, social, possession, etc."""
    relation_key: str = "unknown"  # near, far, inside, from, to, has, lacks, source_of, causes, before, after, during, same_as, part_of, unknown
    source_role: str = ""
    target_role: str = ""
    temporal_scope: str | None = None
    confidence: float = 0.5


# ── NeedAtom ──────────────────────────────────────────────────────────────

@dataclass
class NeedAtom:
    """Biological, social, cognitive, or operational needs."""
    holder_role: str = "user"
    need_key: str = "unknown"  # food, water, safety, help, rest, information, attention, clarity, data, learning, unknown
    intensity: float = 0.5
    known_satisfiers: list[str] = field(default_factory=list)
    confidence: float = 0.5


# ── AffordanceAtom ────────────────────────────────────────────────────────

@dataclass
class AffordanceAtom:
    """What an object/place/entity can provide or enable."""
    entity_role_or_id: str = ""
    affords: list[str] = field(default_factory=list)  # food, movement, information, safety, storage, answer
    condition: str | None = None
    confidence: float = 0.5


# ── OutcomeAtom ───────────────────────────────────────────────────────────

@dataclass
class OutcomeAtom:
    """Predicted result of an event — state changes for affected entities.

    Combines the simplified fields from architecture.md §6.7 with the
    structured fields from cemm_foundational_fixes.md §4.7.
    """
    affected_entity_role: str = ""
    changed_dimension: str = ""  # health, hunger, safety, distance, possession, knowledge, capability, etc.
    direction: str = "unknown"  # increase, decrease, maintain, unknown
    expected_after_state: str | None = None
    confidence: float = 0.5
    # ── Structured fields per §4.7 ──
    event_key: str = ""
    state_changes: list[dict[str, Any]] = field(default_factory=list)
    relation_changes: list[dict[str, Any]] = field(default_factory=list)
    resource_changes: list[dict[str, Any]] = field(default_factory=list)


# ── ValenceAtom ───────────────────────────────────────────────────────────

@dataclass
class ValenceAtom:
    """Whether an outcome is favorable or unfavorable for an entity."""
    affected_entity_role: str = ""
    entity_class: str = "unknown"  # self, human, animal, object, world, unknown
    valence: str = "unknown"  # favorable, unfavorable, mixed, neutral, unknown
    rationale: str = ""
    confidence: float = 0.5


# ── EventSchema ───────────────────────────────────────────────────────────

@dataclass
class EventSchema:
    """Core child-learning unit — maps surface forms to event roles and outcomes."""
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
    confidence: float = 0.5
    source: str = "seed"  # seed, learned, inferred


# ── SafetyFrame ───────────────────────────────────────────────────────────

@dataclass
class SafetyFrame:
    """Safety classification derived before decision — first-class runtime packet."""
    category: str = "none"  # interpersonal_violence, self_harm, illegal_activity, medical_risk, privacy_risk, none
    severity: str = "low"  # low, medium, high
    actor_entity_id: str | None = None
    target_entity_id: str | None = None
    requested_action: str | None = None
    harmful_outcomes: list[OutcomeAtom] = field(default_factory=list)
    allowed_response_mode: str = "none"  # deescalate, refuse, safe_info, ask_safe_context, none
    must_not_do: list[str] = field(default_factory=list)
    confidence: float = 0.5


# ── RetrospectiveRepairFrame ──────────────────────────────────────────────

@dataclass
class RetrospectiveRepairFrame:
    """Detects when user is repairing a previous misunderstanding."""
    repair_type: str = ""  # phatic_clarification, intent_correction, topic_reset
    original_intent: str = ""
    confidence: float = 0.5


# ── SituationFrame ────────────────────────────────────────────────────────

@dataclass
class SituationFrame:
    """Per-turn situation model — built before ConversationAct.

    This is the foundational semantic unit that replaces raw-text-to-act routing.
    """
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
    version: str = "cemm.situation_frame.v1"


# ── MeaningPerceptPacket ──────────────────────────────────────────────────

@dataclass
class MeaningPerceptPacket:
    """The missing foundational packet — built after normalization, before UOL.

    This is where NER, POS-lite role cues, unknown token detection, slang repair,
    and referent binding meet. No component after this should rediscover basic
    token/entity/action meaning independently from raw strings.
    """
    id: str = ""
    signal_id: str = ""
    context_id: str = ""

    raw_text: str = ""
    tokens: list[str] = field(default_factory=list)
    normalized_tokens: list[str] = field(default_factory=list)
    repaired_tokens: list[str] = field(default_factory=list)
    normalized_forms: list[str] = field(default_factory=list)
    punctuation_features: dict[str, Any] = field(default_factory=dict)

    referents: list[ReferentAtom] = field(default_factory=list)
    actions: list[ActionAtom] = field(default_factory=list)
    states: list[StateAtom] = field(default_factory=list)
    relations: list[RelationAtom] = field(default_factory=list)
    needs: list[NeedAtom] = field(default_factory=list)
    affordances: list[AffordanceAtom] = field(default_factory=list)

    unknown_lexemes: list[dict[str, Any]] = field(default_factory=list)
    idiom_candidates: list[dict[str, Any]] = field(default_factory=list)
    affect_markers: list[dict[str, Any]] = field(default_factory=list)

    attention_target: str | None = None
    speaker_entity_id: str = "user"
    listener_entity_id: str = "self"

    confidence: float = 0.5
    version: str = "cemm.meaning_percept.v1"


# ── RetrievalPlan ─────────────────────────────────────────────────────────

@dataclass
class RetrievalPlan:
    """Explicit retrieval plan — replaces implicit requires_evidence gating."""
    mode: str = "none"  # none, profile, self_knowledge, entity_memory, lexeme_memory, world_memory, live_tool_required, procedure_model
    target_predicates: list[str] = field(default_factory=list)
    target_entity_ids: list[str] = field(default_factory=list)
    target_model_kinds: list[str] = field(default_factory=list)
    freshness_required: bool = False
    permission_scope: str = "public"
    reason: str = ""


# ── OutputStateUpdate ─────────────────────────────────────────────────────

@dataclass
class OutputStateUpdate:
    """State update after final realization — fixes pending question tracking."""
    last_assistant_output_signal_id: str = ""
    last_assistant_intent: str = ""
    last_assistant_response_mode: str = ""
    pending_assistant_question: str | None = None
    expected_user_answer_type: str | None = None
    reply_obligation_created: str | None = None
