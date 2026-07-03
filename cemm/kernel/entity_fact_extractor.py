"""EntityFactExtractor - convert bound meaning into teachable claim candidates.

Implements Gap 7 from cemm_v3_1_operational_meaning_spine.md.

This module is deliberately separate from UOL mapping. Claim extraction is not a
side effect of seeing a predicate token; it is a structured operation over
MeaningPerceptPacket + SituationFrame + discourse context.

The extractor is conservative:

* It prefers relation/state atoms created upstream by multilingual parsers.
* It uses simple surface patterns only as a fallback seed path.
* It emits candidates, never committed claims.
* It records evidence spans and confidence so online learning can grade trust.

Output types are EntityFactCandidate / EntityFactExtractionResult so that
ActResolutionPlanner can consume them directly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from ..types.conversation_act import ConversationActPacket
from ..types.meaning_percept import (
    MeaningPerceptPacket,
    ReferentAtom,
    RelationAtom,
    SituationFrame,
    StateAtom,
)
from ..types.context_kernel import ContextKernel


# ── Relation predicate mapping ──────────────────────────────────────────────

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
}

_BLOCKED_SUBJECTS = {"i", "me", "my", "you", "your", "he", "she", "it", "we", "they", "this", "that"}

_TOPIC_PRONOUNS = {"it", "that", "this", "he", "she", "they"}


# ── Clause segmentation ─────────────────────────────────────────────────────

_CLAUSE_SPLIT_RE = re.compile(
    r"\s+(that|which)\s+"
    r"|\s+(and|but|or)\s+"
    r"|[,]\s*"
    r"|[.]\s*",
    re.IGNORECASE,
)


@dataclass
class Clause:
    """A single clause extracted from a complex sentence."""
    text: str = ""
    is_relative: bool = False
    is_coordinate: bool = False
    delimiter: str = ""


def _segment_clauses(text: str) -> list[Clause]:
    """Split text into clauses at conjunctions, relative pronouns, and punctuation."""
    text = text.strip()
    if not text:
        return []

    clauses: list[Clause] = []
    current = ""
    i = 0

    while i < len(text):
        match = _CLAUSE_SPLIT_RE.search(text, i)
        if not match:
            current += text[i:]
            break

        current += text[i:match.start()]
        delim = match.group(0).strip().rstrip(",").rstrip(".").strip()
        is_rel = match.group(1) is not None
        is_coord = match.group(2) is not None

        if current.strip():
            clauses.append(Clause(text=current.strip()))
        current = ""

        if is_rel:
            current = delim + " "
        elif is_coord:
            current = delim + " "

        i = match.end()

    if current.strip():
        clauses.append(Clause(text=current.strip()))

    for clause in clauses[1:]:
        lower = clause.text.lower()
        if lower.startswith("that ") or lower.startswith("which "):
            clause.is_relative = True
            clause.delimiter = "that" if lower.startswith("that") else "which"
        elif lower.startswith("and ") or lower.startswith("but ") or lower.startswith("or "):
            clause.is_coordinate = True
            clause.delimiter = lower.split()[0]

    return clauses


# ── Per-clause regex patterns (fallback for surface text) ───────────────────

_CLAUSE_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # X is a type of Y / X is a kind of Y
    (re.compile(
        r"^(\w[\w ]*?)\s+is\s+a\s+(?:type|kind)\s+of\s+(\w[\w ]*?)$",
        re.IGNORECASE), "is_a", "subj_obj"),
    # X is shaped like Y / X is shaped like a Y
    (re.compile(
        r"^(\w[\w ]*?)\s+is\s+shaped\s+like\s+(?:a\s+|an\s+)?(\w[\w ]*?)$",
        re.IGNORECASE), "shape", "subj_obj"),
    # X has shape Y / X has the shape of Y
    (re.compile(
        r"^(\w[\w ]*?)\s+has\s+(?:the\s+)?shape\s+(?:of\s+|like\s+)?(?:a\s+|an\s+)?(\w[\w ]*?)$",
        re.IGNORECASE), "shape", "subj_obj"),
    # X is usually COLOR / X is often COLOR / X is typically COLOR
    (re.compile(
        r"^(\w[\w ]*?)\s+is\s+(?:usually|often|typically)\s+(\w[\w ]*?)$",
        re.IGNORECASE), "typical_color", "subj_obj"),
    # X is used for Y
    (re.compile(
        r"^(\w[\w ]*?)\s+is\s+used\s+for\s+(\w[\w ]*?)$",
        re.IGNORECASE), "function", "subj_obj"),
    # X comes from PLACE
    (re.compile(
        r"^(\w[\w ]*?)\s+comes\s+from\s+(\w[\w ]*?)$",
        re.IGNORECASE), "source", "subj_obj"),
    # X is something you eat / X is eaten / X is something eaten
    (re.compile(
        r"^(\w[\w ]*?)\s+is\s+(?:something\s+)?(?:you\s+)?eat(?:en)?$",
        re.IGNORECASE), "edible", "flag"),
    # you eat X
    (re.compile(
        r"^you\s+eat\s+(\w[\w ]*?)$",
        re.IGNORECASE), "edible", "you_eat"),
    # X can ACTION
    (re.compile(
        r"^(\w[\w ]*?)\s+can\s+(\w[\w ]*?)$",
        re.IGNORECASE), "affordance", "subj_obj"),
    # X is a Y (simple categorization)
    (re.compile(
        r"^(\w[\w ]*?)\s+is\s+a(?:n)?\s+(\w[\w ]*?)$",
        re.IGNORECASE), "is_a", "subj_obj"),
    # ── No-subject patterns (for relative clauses with inherited subject) ──
    (re.compile(
        r"^is\s+shaped\s+like\s+(?:a\s+|an\s+)?(\w[\w ]*?)$",
        re.IGNORECASE), "shape", "no_subj_obj"),
    (re.compile(
        r"^is\s+(?:usually|often|typically)\s+(\w[\w ]*?)$",
        re.IGNORECASE), "typical_color", "no_subj_obj"),
    (re.compile(
        r"^is\s+a\s+(?:type|kind)\s+of\s+(\w[\w ]*?)$",
        re.IGNORECASE), "is_a", "no_subj_obj"),
    (re.compile(
        r"^is\s+a(?:n)?\s+(\w[\w ]*?)$",
        re.IGNORECASE), "is_a", "no_subj_obj"),
    (re.compile(
        r"^is\s+used\s+for\s+(\w[\w ]*?)$",
        re.IGNORECASE), "function", "no_subj_obj"),
    (re.compile(
        r"^is\s+(?:something\s+)?(?:you\s+)?eat(?:en)?$",
        re.IGNORECASE), "edible", "no_subj_flag"),
    (re.compile(
        r"^you\s+eat$",
        re.IGNORECASE), "edible", "relative_eat"),
]


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

    Atom-first approach: prefers RelationAtom, StateAtom, AffordanceAtom from
    upstream multilingual parsers. Falls back to clause-segmented surface
    patterns for English teaching sentences.

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

        # Fallback: clause-segmented surface patterns
        result.candidates.extend(
            self._from_surface_patterns(percept, kernel, active_topic)
        )

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
            if not source or not target:
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

    # ── Surface pattern fallback (clause-segmented) ─────────────────────────

    def _from_surface_patterns(
        self,
        percept: MeaningPerceptPacket,
        kernel: ContextKernel | None,
        active_topic: str | None,
    ) -> list[EntityFactCandidate]:
        raw_text = percept.raw_text.strip()
        if not raw_text:
            return []

        clauses = _segment_clauses(raw_text)
        if not clauses:
            return []

        candidates: list[EntityFactCandidate] = []
        parent_subject = ""

        for idx, clause in enumerate(clauses):
            clause_text = clause.text.strip()

            if clause.is_relative:
                clause_text = re.sub(r"^(?:that|which)\s+", "", clause_text, flags=re.IGNORECASE)
            if clause.is_coordinate:
                clause_text = re.sub(r"^(?:and|but|or)\s+", "", clause_text, flags=re.IGNORECASE)

            if not clause_text:
                continue

            matched = False
            for pattern, predicate_name, layout in _CLAUSE_PATTERNS:
                m = pattern.match(clause_text)
                if not m:
                    continue
                groups = m.groups()
                matched = True

                if layout == "subj_obj":
                    subj_raw = groups[0].strip() if len(groups) >= 1 else ""
                    obj_raw = groups[1].strip() if len(groups) >= 2 else ""
                    if not subj_raw or not obj_raw:
                        break
                    subj = self._resolve_subject(subj_raw, kernel, active_topic)
                    obj = self._preserve_case(obj_raw, percept)
                    candidates.append(EntityFactCandidate(
                        subject_entity_id=subj.lower().replace(" ", "_"),
                        predicate=predicate_name,
                        object_value=obj.lower().replace(" ", "_"),
                        evidence_span=percept.raw_text,
                        confidence=0.7,
                        trust=0.6,
                        reason=f"surface_pattern:{predicate_name}",
                    ))
                    if idx == 0:
                        parent_subject = subj

                elif layout == "flag":
                    subj_raw = groups[0].strip() if groups else ""
                    if not subj_raw:
                        break
                    subj = self._resolve_subject(subj_raw, kernel, active_topic)
                    candidates.append(EntityFactCandidate(
                        subject_entity_id=subj.lower().replace(" ", "_"),
                        predicate=predicate_name,
                        object_value="true",
                        evidence_span=percept.raw_text,
                        confidence=0.7,
                        trust=0.6,
                        reason=f"surface_pattern:{predicate_name}",
                    ))
                    if idx == 0:
                        parent_subject = subj

                elif layout == "you_eat":
                    obj_raw = groups[0].strip() if groups else ""
                    if not obj_raw:
                        break
                    obj = self._preserve_case(obj_raw, percept)
                    candidates.append(EntityFactCandidate(
                        subject_entity_id=obj.lower().replace(" ", "_"),
                        predicate=predicate_name,
                        object_value="true",
                        evidence_span=percept.raw_text,
                        confidence=0.6,
                        trust=0.55,
                        reason="surface_pattern:edible_you_eat",
                    ))

                elif layout == "no_subj_obj":
                    obj_raw = groups[0].strip() if groups else ""
                    if not obj_raw:
                        break
                    subj = parent_subject or (kernel.topic.active_topic_surface if kernel else "") or active_topic or ""
                    if not subj:
                        break
                    obj = self._preserve_case(obj_raw, percept)
                    candidates.append(EntityFactCandidate(
                        subject_entity_id=subj.lower().replace(" ", "_"),
                        predicate=predicate_name,
                        object_value=obj.lower().replace(" ", "_"),
                        evidence_span=percept.raw_text,
                        confidence=0.65,
                        trust=0.55,
                        reason="surface_pattern:coreference",
                    ))

                elif layout in ("no_subj_flag", "relative_eat"):
                    subj = parent_subject or (kernel.topic.active_topic_surface if kernel else "") or active_topic or ""
                    if not subj:
                        break
                    candidates.append(EntityFactCandidate(
                        subject_entity_id=subj.lower().replace(" ", "_"),
                        predicate=predicate_name,
                        object_value="true",
                        evidence_span=percept.raw_text,
                        confidence=0.65,
                        trust=0.55,
                        reason="surface_pattern:coreference",
                    ))

                break

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

        if candidates:
            subj = candidates[0].subject_entity_id.replace("_", " ")
            if subj:
                kernel.topic.last_taught_entity_surface = subj
                kernel.topic.last_taught_entity_id = candidates[0].subject_entity_id
                kernel.topic.last_updated_signal_id = signal_id
                kernel.topic.last_updated_at = observed_at

                if not new_topic:
                    if not kernel.topic.active_topic_surface or subj.lower() != kernel.topic.active_topic_surface.lower():
                        kernel.topic.active_topic_surface = subj
                        kernel.topic.active_topic_type = ""
                        kernel.topic.active_topic_entity_id = candidates[0].subject_entity_id

    def _detect_new_topic(
        self,
        percept: MeaningPerceptPacket,
    ) -> tuple[str, str] | None:
        """Detect a new conversation topic from referents.

        Returns (surface, entity_type) or None.
        Prefers capitalized unknown entities, then non-pronoun referents.
        """
        for ref in percept.referents:
            if ref.source in ("pronoun", "deixis"):
                continue
            if ref.known and ref.source == "ner":
                continue
            return (ref.surface, ref.entity_type)
        return None

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _resolve_subject(self, surface: str, kernel: ContextKernel | None, active_topic: str | None) -> str:
        """Resolve a subject surface, handling pronoun coreference."""
        surface_lower = surface.lower().strip()
        if surface_lower in _TOPIC_PRONOUNS:
            if kernel and kernel.topic.active_topic_surface:
                return kernel.topic.active_topic_surface
            if active_topic:
                return active_topic
        return surface

    def _resolve_ref(self, key: str, referents: dict[str, ReferentAtom]) -> ReferentAtom | None:
        if not key:
            return None
        return referents.get(key.lower())

    def _span(self, percept: MeaningPerceptPacket) -> str:
        return percept.raw_text or " ".join(percept.tokens)

    def _preserve_case(self, surface: str, percept: MeaningPerceptPacket) -> str:
        """Recover original casing from percept referents or raw text."""
        surface_lower = surface.lower()
        for ref in percept.referents:
            if ref.surface.lower() == surface_lower:
                return ref.surface
        for word in percept.raw_text.split():
            clean = word.strip(".,!?;:\"'()[]{}")
            if clean.lower() == surface_lower:
                return clean
        return surface

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
