"""FrameBinder - role binding over CEMM foundational meaning atoms.

FrameBinder turns a MeaningPerceptPacket into a bound SituationFrame by solving
the small but crucial semantic problem:

    who did what to whom, with what object, where, and with what state effect?

NER is intentionally not required here. NER may create ReferentAtom instances
upstream, but the binder only consumes CEMM-native atoms: referents, actions,
states, relations, schemas, and context. That keeps the module multilingual,
Pi-friendly, and compatible with online meaning learning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable
import copy
import uuid

from ..types.context_kernel import ContextKernel
from ..types.meaning_percept import (
    ActionAtom,
    EventSchema,
    MeaningPerceptPacket,
    OutcomeAtom,
    ReferentAtom,
    RelationAtom,
    SituationFrame,
    StateAtom,
)
from .event_schema_loader import EventSchemaStore, load_event_schemas


_ROLE_FIELDS = (
    "actor",
    "object",
    "target",
    "place",
    "source",
    "destination",
    "recipient",
)

_PERSON_ENTITY_TYPES = {"self", "user", "person", "human", "animal"}
_OBJECT_ENTITY_TYPES = {"object", "food", "tool", "artifact", "natural_entity", "abstract", "unknown"}
_PLACE_ENTITY_TYPES = {"place", "location", "city", "country", "room", "venue"}

_ROLE_ALIASES = {
    "self": "actor",
    "user": "actor",
    "speaker": "actor",
    "listener": "target",
    "theme": "object",
    "patient": "target",
    "location": "place",
    "to": "destination",
    "from": "source",
}


@dataclass
class RoleCandidate:
    """A scored referent candidate for a semantic role."""

    role: str
    referent: ReferentAtom
    score: float
    evidence: list[str] = field(default_factory=list)


@dataclass
class RoleBinding:
    """The selected binding for one semantic role."""

    role: str
    referent: ReferentAtom | None
    score: float = 0.0
    evidence: list[str] = field(default_factory=list)
    ambiguous: bool = False
    alternatives: list[RoleCandidate] = field(default_factory=list)


@dataclass
class FrameBindingTrace:
    """Trace data for debugging and training export."""

    selected_action: str = ""
    selected_schema: str = ""
    role_bindings: dict[str, RoleBinding] = field(default_factory=dict)
    missing_roles: list[str] = field(default_factory=list)
    uncertainty_reasons: list[str] = field(default_factory=list)
    rejected_candidates: list[RoleCandidate] = field(default_factory=list)
    confidence: float = 0.5


@dataclass
class BoundSituationFrame:
    """A SituationFrame plus the trace explaining how binding happened."""

    frame: SituationFrame
    trace: FrameBindingTrace


class FrameBinder:
    """Bind CEMM meaning atoms into a SituationFrame.

    The binder is deliberately deterministic first. Later, each scorer here can
    be replaced by a small learned ranker trained from FrameBindingTrace records.
    """

    def __init__(
        self,
        event_schema_store: EventSchemaStore | None = None,
        schemas: dict[str, EventSchema] | None = None,
        ambiguity_margin: float = 0.08,
        min_role_score: float = 0.35,
    ) -> None:
        self._event_store = event_schema_store or load_event_schemas()
        self._schemas = dict(schemas or {})
        # Merge JSON-defined action schemas, keyed by action_key for lookup
        for key, loaded in self._event_store.action_schemas.items():
            if loaded.action_key and loaded.action_key not in self._schemas:
                outcomes = [
                    OutcomeAtom(
                        affected_entity_role=o.get("affected_entity_role", ""),
                        changed_dimension=o.get("changed_dimension", ""),
                        direction=o.get("direction", "unknown"),
                        confidence=o.get("confidence", 0.5),
                        event_key=loaded.action_key,
                    )
                    for o in loaded.expected_outcomes
                ]
                self._schemas[loaded.action_key] = EventSchema(
                    schema_key=loaded.schema_key,
                    actor_role=loaded.actor_role,
                    action_key=loaded.action_key,
                    object_role=loaded.object_role,
                    target_role=loaded.target_role,
                    place_role=loaded.place_role,
                    source_role=loaded.source_role,
                    destination_role=loaded.destination_role,
                    recipient_role=loaded.recipient_role,
                    expected_outcomes=outcomes,
                    examples=list(loaded.aliases),
                    confidence=0.7,
                    source="seed",
                )
        self._ambiguity_margin = ambiguity_margin
        self._min_role_score = min_role_score

    def bind(
        self,
        percept: MeaningPerceptPacket,
        kernel: ContextKernel,
        base_frame: SituationFrame | None = None,
    ) -> BoundSituationFrame:
        """Return a bound situation frame for the percept.

        The result keeps all original percept atoms but upgrades the frame with
        role assignments, schema outcomes, missing slots, and a binding trace.
        """
        frame = copy.deepcopy(base_frame) if base_frame else SituationFrame(
            id=uuid.uuid4().hex[:16],
            signal_id=percept.signal_id,
            context_id=percept.context_id,
        )
        trace = FrameBindingTrace()

        action = self._select_action(percept.actions)
        frame.action = action
        trace.selected_action = action.action_key if action else ""

        schema = self._schema_for_action(action)
        if schema:
            trace.selected_schema = schema.schema_key
            if schema.schema_key and schema.schema_key not in frame.event_schema_ids:
                frame.event_schema_ids.append(schema.schema_key)
            frame.expected_outcomes = self._merge_outcomes(
                frame.expected_outcomes,
                schema.expected_outcomes,
            )

        referents = self._with_context_referents(percept, kernel)
        relation_hints = self._relation_hints(percept.relations)
        required_roles = self._required_roles(action, schema)

        used_ids: set[str] = set()
        for role in _ROLE_FIELDS:
            desired_role = self._desired_role(role, action, schema)
            candidates = self._score_role_candidates(
                role=role,
                desired_role=desired_role,
                referents=referents,
                action=action,
                relations=relation_hints,
                used_ids=used_ids,
                percept=percept,
                kernel=kernel,
            )
            binding = self._select_binding(role, candidates)
            trace.role_bindings[role] = binding

            if binding.referent is not None:
                setattr(frame, role, binding.referent)
                used_ids.add(self._referent_key(binding.referent))
            elif role in required_roles:
                trace.missing_roles.append(role)
                frame.missing_slots.append(role)

            for candidate in candidates:
                if binding.referent is None or self._referent_key(candidate.referent) != self._referent_key(binding.referent):
                    trace.rejected_candidates.append(candidate)

        frame.state_reports = self._bind_state_holders(percept.states, frame, kernel)
        frame.needs = list(percept.needs)
        frame.affordances = list(percept.affordances)

        self._add_uncertainty(percept, frame, trace)
        frame.confidence = trace.confidence = self._frame_confidence(frame, trace)
        return BoundSituationFrame(frame=frame, trace=trace)

    def _select_action(self, actions: list[ActionAtom]) -> ActionAtom | None:
        if not actions:
            return None

        def score(action: ActionAtom, index: int) -> float:
            value = action.confidence
            if action.action_key:
                value += 0.18
            if action.modality in {"requested", "commanded", "proposed"}:
                value += 0.08
            if action.polarity == "negated":
                value -= 0.03
            value -= index * 0.015
            return value

        return max(enumerate(actions), key=lambda item: score(item[1], item[0]))[1]

    def _schema_for_action(self, action: ActionAtom | None) -> EventSchema | None:
        if action is None:
            return None
        key = action.action_key or action.surface
        if not key:
            return None
        schema = self._schemas.get(key)
        if schema is not None:
            return schema
        loaded = self._event_store.action_schemas.get(key)
        if loaded is None:
            return None
        outcomes = [
            OutcomeAtom(
                affected_entity_role=o.get("affected_entity_role", ""),
                changed_dimension=o.get("changed_dimension", ""),
                direction=o.get("direction", "unknown"),
                confidence=o.get("confidence", 0.5),
                event_key=loaded.action_key,
            )
            for o in loaded.expected_outcomes
        ]
        return EventSchema(
            schema_key=loaded.schema_key,
            actor_role=loaded.actor_role,
            action_key=loaded.action_key,
            object_role=loaded.object_role,
            target_role=loaded.target_role,
            place_role=loaded.place_role,
            source_role=loaded.source_role,
            destination_role=loaded.destination_role,
            recipient_role=loaded.recipient_role,
            expected_outcomes=outcomes,
            examples=list(loaded.aliases),
            confidence=0.7,
            source="seed",
        )

    def _with_context_referents(
        self,
        percept: MeaningPerceptPacket,
        kernel: ContextKernel,
    ) -> list[ReferentAtom]:
        referents = list(percept.referents)
        keys = {self._referent_key(ref) for ref in referents}
        speaker_id = percept.speaker_entity_id or "user"
        listener_id = percept.listener_entity_id or getattr(kernel.self_view, "self_id", "self") or "self"

        for ref in (
            ReferentAtom(
                surface="user",
                entity_id=speaker_id,
                entity_type="user",
                role="speaker",
                known=True,
                source="context",
                confidence=0.92,
            ),
            ReferentAtom(
                surface="self",
                entity_id=listener_id,
                entity_type="self",
                role="listener",
                known=True,
                source="context",
                confidence=0.92,
            ),
        ):
            key = self._referent_key(ref)
            if key not in keys:
                keys.add(key)
                referents.append(ref)
        return referents

    def _relation_hints(self, relations: Iterable[RelationAtom]) -> dict[str, set[str]]:
        hints: dict[str, set[str]] = {role: set() for role in _ROLE_FIELDS}
        for relation in relations:
            source_role = self._canonical_role(relation.source_role)
            target_role = self._canonical_role(relation.target_role)
            relation_key = relation.relation_key
            if relation_key in {"to", "toward", "into", "destination", "near"}:
                if target_role:
                    hints["destination"].add(target_role)
            if relation_key in {"from", "out_of", "source"}:
                if source_role:
                    hints["source"].add(source_role)
            if relation_key in {"has", "owns", "possesses"}:
                if source_role:
                    hints["actor"].add(source_role)
                if target_role:
                    hints["object"].add(target_role)
            if relation_key in {"with", "using", "instrument"}:
                if target_role:
                    hints["object"].add(target_role)
            if relation_key in {"inside", "at", "in", "on"}:
                if target_role:
                    hints["place"].add(target_role)
        return hints

    def _required_roles(self, action: ActionAtom | None, schema: EventSchema | None) -> set[str]:
        roles: set[str] = set()
        if schema:
            for field_name in (
                "actor_role",
                "object_role",
                "target_role",
                "place_role",
                "source_role",
                "destination_role",
                "recipient_role",
            ):
                role = getattr(schema, field_name, None)
                if role:
                    roles.add(self._field_from_schema_role(field_name, role))
        if action:
            for field_name in ("actor_role", "object_role", "target_role", "place_role"):
                role = getattr(action, field_name, None)
                if role:
                    roles.add(field_name.removesuffix("_role"))
        return {role for role in roles if role in _ROLE_FIELDS}

    def _desired_role(
        self,
        field_role: str,
        action: ActionAtom | None,
        schema: EventSchema | None,
    ) -> str:
        if schema:
            schema_role = getattr(schema, f"{field_role}_role", None)
            if schema_role:
                return self._canonical_role(schema_role)
        if action:
            action_role = getattr(action, f"{field_role}_role", None)
            if action_role:
                return self._canonical_role(action_role)
        return field_role

    def _score_role_candidates(
        self,
        role: str,
        desired_role: str,
        referents: list[ReferentAtom],
        action: ActionAtom | None,
        relations: dict[str, set[str]],
        used_ids: set[str],
        percept: MeaningPerceptPacket,
        kernel: ContextKernel,
    ) -> list[RoleCandidate]:
        candidates: list[RoleCandidate] = []
        for ref in referents:
            evidence: list[str] = []
            score = ref.confidence * 0.35
            ref_role = self._canonical_role(ref.role)
            ref_key = self._referent_key(ref)

            if ref_key in used_ids:
                score -= 0.35
                evidence.append("already_bound_penalty")

            if ref_role == role:
                score += 0.45
                evidence.append("explicit_role")
            if desired_role and ref_role == desired_role:
                score += 0.35
                evidence.append("desired_role")
            if ref_role in relations.get(role, set()):
                score += 0.25
                evidence.append("relation_hint")

            score += self._entity_type_score(role, desired_role, ref, percept, kernel, evidence)
            score += self._context_role_score(role, desired_role, ref, action, evidence)

            if score >= 0.05:
                candidates.append(RoleCandidate(
                    role=role,
                    referent=ref,
                    score=max(0.0, min(1.0, score)),
                    evidence=evidence,
                ))

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates

    def _entity_type_score(
        self,
        role: str,
        desired_role: str,
        ref: ReferentAtom,
        percept: MeaningPerceptPacket,
        kernel: ContextKernel,
        evidence: list[str],
    ) -> float:
        entity_type = (ref.entity_type or "").lower()
        score = 0.0
        self_id = getattr(kernel.self_view, "self_id", "") or "self"
        ref_id = ref.entity_id or ref.surface

        if desired_role in {"speaker", "user", "actor"} and entity_type == "user":
            score += 0.28
            evidence.append("speaker_user_context")
        if desired_role in {"listener", "self", "target"} and (entity_type == "self" or ref_id == self_id):
            score += 0.28
            evidence.append("listener_self_context")

        if role in {"actor", "target", "recipient"} and entity_type in _PERSON_ENTITY_TYPES:
            score += 0.12
            evidence.append("person_like_entity")
        if role == "object" and entity_type in _OBJECT_ENTITY_TYPES:
            score += 0.14
            evidence.append("object_like_entity")
        if role in {"place", "source", "destination"} and entity_type in _PLACE_ENTITY_TYPES:
            score += 0.18
            evidence.append("place_like_entity")

        if percept.attention_target and ref_id == percept.attention_target:
            score += 0.12
            evidence.append("attention_target")

        if ref.known:
            score += 0.04
            evidence.append("known_referent")
        if ref.source == "ner":
            score += 0.02
            evidence.append("ner_evidence_optional")
        return score

    def _context_role_score(
        self,
        role: str,
        desired_role: str,
        ref: ReferentAtom,
        action: ActionAtom | None,
        evidence: list[str],
    ) -> float:
        score = 0.0
        ref_role = self._canonical_role(ref.role)
        modality = action.modality if action else ""

        if modality in {"requested", "commanded"}:
            if role == "actor" and ref_role in {"listener", "self"}:
                score += 0.16
                evidence.append("command_listener_actor")
            if role in {"target", "recipient"} and ref_role in {"speaker", "user"}:
                score += 0.12
                evidence.append("command_speaker_target")

        if modality in {"observed", "proposed", "hypothetical"}:
            if role == "actor" and ref_role in {"speaker", "user", "actor"}:
                score += 0.10
                evidence.append("speaker_default_actor")

        if desired_role in {"target", "object"} and ref_role == "topic":
            score += 0.06
            evidence.append("topic_as_content_role")
        return score

    def _select_binding(self, role: str, candidates: list[RoleCandidate]) -> RoleBinding:
        if not candidates:
            return RoleBinding(role=role, referent=None)
        best = candidates[0]
        if best.score < self._min_role_score:
            return RoleBinding(
                role=role,
                referent=None,
                alternatives=candidates[:3],
            )
        ambiguous = len(candidates) > 1 and (best.score - candidates[1].score) <= self._ambiguity_margin
        return RoleBinding(
            role=role,
            referent=best.referent,
            score=best.score,
            evidence=list(best.evidence),
            ambiguous=ambiguous,
            alternatives=candidates[1:4],
        )

    def _bind_state_holders(
        self,
        states: list[StateAtom],
        frame: SituationFrame,
        kernel: ContextKernel,
    ) -> list[StateAtom]:
        bound: list[StateAtom] = []
        default_holder = None
        if frame.actor:
            default_holder = frame.actor.role
        elif getattr(kernel.user, "user_id", None):
            default_holder = "user"
        for state in states:
            state_copy = copy.deepcopy(state)
            if not state_copy.holder_role:
                state_copy.holder_role = default_holder or "user"
            bound.append(state_copy)
        return bound

    def _merge_outcomes(
        self,
        existing: list[OutcomeAtom],
        new_items: list[OutcomeAtom],
    ) -> list[OutcomeAtom]:
        merged = list(existing)
        seen = {
            (o.affected_entity_role, o.changed_dimension, o.direction, o.event_key)
            for o in merged
        }
        for item in new_items:
            key = (item.affected_entity_role, item.changed_dimension, item.direction, item.event_key)
            if key not in seen:
                seen.add(key)
                merged.append(copy.deepcopy(item))
        return merged

    def _add_uncertainty(
        self,
        percept: MeaningPerceptPacket,
        frame: SituationFrame,
        trace: FrameBindingTrace,
    ) -> None:
        for lexeme in percept.unknown_lexemes:
            surface = lexeme.get("surface", "") if isinstance(lexeme, dict) else str(lexeme)
            if surface:
                reason = f"unknown_lexeme:{surface}"
                trace.uncertainty_reasons.append(reason)
                frame.uncertainty_reasons.append(reason)
        for role, binding in trace.role_bindings.items():
            if binding.ambiguous:
                reason = f"ambiguous_role:{role}"
                trace.uncertainty_reasons.append(reason)
                frame.uncertainty_reasons.append(reason)
        for role in trace.missing_roles:
            reason = f"missing_role:{role}"
            trace.uncertainty_reasons.append(reason)
            if reason not in frame.uncertainty_reasons:
                frame.uncertainty_reasons.append(reason)

    def _frame_confidence(self, frame: SituationFrame, trace: FrameBindingTrace) -> float:
        selected = [b for b in trace.role_bindings.values() if b.referent is not None]
        if not selected:
            base = 0.35 if frame.action else 0.25
        else:
            base = sum(b.score for b in selected) / len(selected)
        if frame.action:
            base = 0.7 * base + 0.3 * frame.action.confidence
        if trace.missing_roles:
            base -= min(0.25, 0.08 * len(trace.missing_roles))
        if any(b.ambiguous for b in trace.role_bindings.values()):
            base -= 0.08
        return max(0.05, min(0.95, base))

    def _field_from_schema_role(self, field_name: str, role_value: str) -> str:
        field_role = field_name.removesuffix("_role")
        canonical = self._canonical_role(role_value)
        if field_role in _ROLE_FIELDS:
            return field_role
        if canonical in _ROLE_FIELDS:
            return canonical
        return _ROLE_ALIASES.get(canonical, field_role)

    def _canonical_role(self, role: str | None) -> str:
        if not role:
            return ""
        role = role.strip().lower()
        return _ROLE_ALIASES.get(role, role)

    def _referent_key(self, ref: ReferentAtom) -> str:
        return (ref.entity_id or ref.surface or "").lower()
