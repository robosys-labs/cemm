"""EntityFactExtractor — convert bound meaning into teachable claim candidates.

Atom-first approach: extracts EntityFactCandidate objects from RelationAtom,
StateAtom, and AffordanceAtom produced by upstream multilingual parsers.

No regex, no surface-text patterns, no hardcoded English constants.
All linguistic data is data-driven from uol_semantics.json via uol_metadata.
Complies with AGENTS.md §3.1 (surface evidence is not authority) and §5
(forbidden: raw-text checks, English cue tables, regex surface patterns).

Output types are EntityFactCandidate / EntityFactExtractionResult so that
ActResolutionPlanner can consume them directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from ...types.conversation_act import ConversationActPacket
from ...types.meaning_percept import (
    MeaningPerceptPacket,
    ReferentAtom,
    RelationAtom,
    SituationFrame,
    StateAtom,
)
from ...types.context_kernel import ContextKernel
from .uol_metadata import (
    cue_set,
    pronoun_to_entity as _pronoun_to_entity_map,
)


# ── Data-driven linguistic sets (from uol_semantics.json) ─────────────────

_PRONOUN_KEYS = set(_pronoun_to_entity_map().keys())
_BLOCKED_SUBJECTS = cue_set("user_subject") | cue_set("self_target") | _PRONOUN_KEYS


# ── Relation predicate mapping (structural, not language-specific) ─────────

_DEFAULT_RELATION_PREDICATES = {
    "same_as": "same_as",
    "is_a": "is_a",
    "type_of": "is_a",
    "kind_of": "is_a",
    "part_of": "part_of",
    "has": "has_property",
    "has_property": "has_property",
    "affords": "affords",
    "used_for": "used_for",
    "made_of": "made_of",
    "source_of": "source_of",
    "causes": "causes",
    "before": "before",
    "after": "after",
    "means": "means",
    "is": "is",
}


# ── Candidate / result types ────────────────────────────────────────────────


@dataclass
class EntityFactCandidate:
    """Candidate claim extracted from the current turn."""

    subject_entity_id: str
    predicate: str
    object_value: str | int | float | bool | None = None
    object_entity_id: str | None = None
    qualifiers: dict[str, Any] = field(default_factory=dict)
    evidence_span: str = ""
    source: str = "entity_fact_extractor"
    confidence: float = 0.5
    trust: float = 0.5
    domain: str = "semantic"
    reason: str = ""

    def to_claim_dict(self) -> dict[str, Any]:
        """Convert to dict format compatible with SemanticEventGraph.claim_candidates."""
        return {
            "subject": self.subject_entity_id,
            "predicate": self.predicate,
            "object": str(self.object_value or self.object_entity_id or ""),
            "confidence": self.confidence,
            "source": self.source,
        }


@dataclass
class EntityFactExtractionResult:
    """Fact extraction output with traceable skips."""

    candidates: list[EntityFactCandidate] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.5


# ── Extractor ───────────────────────────────────────────────────────────────


class EntityFactExtractor:
    """Extract structured claim candidates from meaning atoms.

    Atom-first approach: extracts from RelationAtom, StateAtom, AffordanceAtom
    produced by upstream multilingual parsers. No surface-text fallback.

    Also tracks topic state for pronoun coreference across turns.
    """

    def __init__(
        self,
        relation_predicates: dict[str, str] | None = None,
        min_confidence: float = 0.45,
    ) -> None:
        self._relation_predicates = dict(_DEFAULT_RELATION_PREDICATES)
        if relation_predicates:
            self._relation_predicates.update(relation_predicates)
        self._min_confidence = min_confidence

    def extract(
        self,
        percept: MeaningPerceptPacket,
        situation: SituationFrame | None = None,
        conversation_act: ConversationActPacket | None = None,
        active_topic_entity_id: str | None = None,
        kernel: ContextKernel | None = None,
    ) -> EntityFactExtractionResult:
        """Extract candidate entity facts.

        The caller decides whether candidates may be written to memory. This
        method only decides whether the turn contains structured facts worth
        considering.
        """
        result = EntityFactExtractionResult()
        if not self._may_extract(conversation_act):
            result.skipped.append({
                "reason": "conversation_act_disallows_fact_extraction",
                "act_types": conversation_act.act_types if conversation_act else [],
            })
            return result

        referents = self._referent_index(percept.referents)
        active_topic = active_topic_entity_id or self._active_topic(percept, situation, kernel)

        # Atom-first: structured atoms from upstream parsers
        result.candidates.extend(self._from_relations(percept.relations, referents, percept))
        result.candidates.extend(self._from_states(percept.states, referents, active_topic, percept))
        result.candidates.extend(self._from_situation(situation, percept, active_topic))

        result.candidates = self._dedupe(
            c for c in result.candidates
            if c.confidence >= self._min_confidence and self._valid_subject(c.subject_entity_id)
        )
        if result.candidates:
            result.confidence = sum(c.confidence for c in result.candidates) / len(result.candidates)
        return result

    # ── ConversationAct gating ──────────────────────────────────────────────

    def _may_extract(self, conversation_act: ConversationActPacket | None) -> bool:
        if conversation_act is None:
            return True
        allowed = {
            "claim_assertion",
            "preference_assertion",
            "definition_teaching",
            "teaching_offer",
            "teaching_instruction_query",
            "explicit_remember",
            "entity_description",
            "unknown",
        }
        blocked = {
            "greeting",
            "phatic_checkin",
            "playful_acknowledgment",
            "confusion_repair",
            "playful_repair",
            "frustration_signal",
            "story_request",
            "creative_request",
            "user_state_report",
            "safety_response",
        }
        act_types = set(conversation_act.act_types)
        if act_types & allowed:
            return True
        if act_types & blocked:
            return False
        return conversation_act.allows_memory_write

    # ── Atom-first extraction ───────────────────────────────────────────────

    def _referent_index(self, referents: Iterable[ReferentAtom]) -> dict[str, ReferentAtom]:
        index: dict[str, ReferentAtom] = {}
        for ref in referents:
            for key in (ref.role, ref.entity_id, ref.surface):
                if key:
                    index[key.lower()] = ref
        return index

    def _active_topic(
        self,
        percept: MeaningPerceptPacket,
        situation: SituationFrame | None,
        kernel: ContextKernel | None,
    ) -> str | None:
        if kernel and kernel.topic.active_topic_surface:
            return kernel.topic.active_topic_entity_id or kernel.topic.active_topic_surface
        if percept.attention_target:
            return percept.attention_target
        if situation:
            for ref in (situation.object, situation.target, situation.actor):
                if ref and (ref.entity_id or ref.surface):
                    return ref.entity_id or ref.surface
        for ref in percept.referents:
            if ref.role in {"topic", "object", "target"} and (ref.entity_id or ref.surface):
                return ref.entity_id or ref.surface
        return None

    def _from_relations(
        self,
        relations: Iterable[RelationAtom],
        referents: dict[str, ReferentAtom],
        percept: MeaningPerceptPacket,
    ) -> list[EntityFactCandidate]:
        candidates: list[EntityFactCandidate] = []
        for relation in relations:
            predicate = self._relation_predicates.get(relation.relation_key)
            if not predicate:
                continue
            source = self._resolve_ref(relation.source_role, referents)
            target = self._resolve_ref(relation.target_role, referents)

            # Fallback to feature-based extraction when referent resolution
            # fails (e.g. possessive relations store object in features)
            subj_surface = relation.features.get("subject_surface", "")
            obj_surface = relation.features.get("object_surface", "")

            if not source and subj_surface:
                source = self._resolve_ref(subj_surface, referents)
            if not target and obj_surface:
                target = self._resolve_ref(obj_surface, referents)

            if not source:
                if subj_surface:
                    source = ReferentAtom(
                        entity_id=subj_surface if subj_surface in ("user", "self") else "",
                        surface=subj_surface,
                        role="subject",
                        entity_type="self" if subj_surface == "user" else "unknown",
                    )
                else:
                    continue

            if not target and obj_surface:
                target = ReferentAtom(
                    entity_id="",
                    surface=obj_surface,
                    role="object",
                    entity_type="unknown",
                )

            if not target:
                continue

            subject = source.entity_id or source.surface
            obj_entity = target.entity_id or target.surface
            candidates.append(EntityFactCandidate(
                subject_entity_id=subject,
                predicate=predicate,
                object_entity_id=obj_entity,
                object_value=target.surface if not target.entity_id else None,
                evidence_span=self._span(percept),
                confidence=min(0.9, relation.confidence + 0.1),
                trust=0.65,
                reason=f"relation_atom:{relation.relation_key}",
            ))
        return candidates

    def _from_states(
        self,
        states: Iterable[StateAtom],
        referents: dict[str, ReferentAtom],
        active_topic: str | None,
        percept: MeaningPerceptPacket,
    ) -> list[EntityFactCandidate]:
        candidates: list[EntityFactCandidate] = []
        for state in states:
            holder = self._resolve_ref(state.holder_role or "", referents)
            subject = (holder.entity_id or holder.surface) if holder else active_topic
            if not subject or not state.state_key:
                continue
            predicate = f"state.{state.dimension}" if state.dimension and state.dimension != "unknown" else "has_state"
            candidates.append(EntityFactCandidate(
                subject_entity_id=subject,
                predicate=predicate,
                object_value=state.state_key,
                qualifiers={
                    "polarity": state.polarity,
                    "intensity": state.intensity,
                    "value": state.value,
                },
                evidence_span=self._span(percept),
                confidence=state.confidence,
                trust=0.6,
                reason="state_atom",
            ))
        return candidates

    def _from_situation(
        self,
        situation: SituationFrame | None,
        percept: MeaningPerceptPacket,
        active_topic: str | None,
    ) -> list[EntityFactCandidate]:
        if situation is None or situation.action is None:
            return []
        candidates: list[EntityFactCandidate] = []
        subject_ref = situation.actor or situation.object or situation.target
        subject = (subject_ref.entity_id or subject_ref.surface) if subject_ref else active_topic
        if not subject:
            return []
        for affordance in situation.affordances:
            entity = affordance.entity_role_or_id or subject
            for item in affordance.affords:
                candidates.append(EntityFactCandidate(
                    subject_entity_id=entity,
                    predicate="affords",
                    object_value=item,
                    qualifiers={"condition": affordance.condition},
                    evidence_span=self._span(percept),
                    confidence=affordance.confidence,
                    trust=0.6,
                    reason="affordance_atom",
                ))
        return candidates

    # ── Topic state tracking ────────────────────────────────────────────────

    def update_topic_state(
        self,
        kernel: ContextKernel,
        percept: MeaningPerceptPacket,
        candidates: list[EntityFactCandidate],
        signal_id: str,
        observed_at: float,
    ) -> None:
        """Update kernel.topic from extracted fact candidates and percept referents.

        Topic tracking is a fact-extraction concern, not a role-binding concern.
        """
        new_topic = self._detect_new_topic(percept)
        if new_topic:
            surface, entity_type = new_topic
            kernel.topic.active_topic_surface = surface
            kernel.topic.active_topic_type = entity_type
            kernel.topic.active_topic_entity_id = surface.lower().replace(" ", "_")
            kernel.topic.last_updated_signal_id = signal_id
            kernel.topic.last_updated_at = observed_at

        real_candidates = [
            candidate for candidate in candidates
            if candidate.reason != "affordance_atom"
            and candidate.subject_entity_id not in {"fresh_source_requirement", "clarity_need"}
        ]
        if real_candidates:
            subj = real_candidates[0].subject_entity_id.replace("_", " ")
            if subj:
                kernel.topic.last_taught_entity_surface = subj
                kernel.topic.last_taught_entity_id = real_candidates[0].subject_entity_id
                kernel.topic.last_updated_signal_id = signal_id
                kernel.topic.last_updated_at = observed_at

                if not new_topic:
                    if not kernel.topic.active_topic_surface or subj.lower() != kernel.topic.active_topic_surface.lower():
                        kernel.topic.active_topic_surface = subj
                        kernel.topic.active_topic_type = ""
                        kernel.topic.active_topic_entity_id = real_candidates[0].subject_entity_id

    def _detect_new_topic(
        self,
        percept: MeaningPerceptPacket,
    ) -> tuple[str, str] | None:
        """Detect a new conversation topic from referents.

        Returns (surface, entity_type) or None.
        Prefers capitalized unknown entities, then non-pronoun referents.
        """
        referents = [
            ref for ref in percept.referents
            if ref.source not in ("pronoun", "deixis")
        ]
        for idx, ref in enumerate(referents):
            if ref.known and ref.source == "ner":
                continue
            if ref.entity_type == "person":
                merged = [ref.surface]
                j = idx + 1
                while j < len(referents):
                    nxt = referents[j]
                    if nxt.entity_type != "person" or nxt.role != ref.role:
                        break
                    merged.append(nxt.surface)
                    j += 1
                if len(merged) > 1:
                    return (" ".join(merged), ref.entity_type)
            return (ref.surface, ref.entity_type)
        return None

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _resolve_ref(self, key: str, referents: dict[str, ReferentAtom]) -> ReferentAtom | None:
        if not key:
            return None
        return referents.get(key.lower())

    def _span(self, percept: MeaningPerceptPacket) -> str:
        return percept.raw_text or " ".join(percept.tokens)

    def _valid_subject(self, subject: str) -> bool:
        return bool(subject) and subject.lower() not in _BLOCKED_SUBJECTS

    def _dedupe(self, candidates: Iterable[EntityFactCandidate]) -> list[EntityFactCandidate]:
        out: list[EntityFactCandidate] = []
        seen: set[tuple[str, str, str, str]] = set()
        for candidate in candidates:
            key = (
                candidate.subject_entity_id,
                candidate.predicate,
                str(candidate.object_entity_id or ""),
                str(candidate.object_value or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(candidate)
        return out
