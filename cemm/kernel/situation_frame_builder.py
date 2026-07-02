"""SituationFrameBuilder — builds SituationFrame from MeaningPerceptPacket.

Implements §8.3 from cemm_foundational_fixes.md and §9 from architecture_new.md.

The SituationFrame is the per-turn situation model that replaces raw-text-to-act
routing. It binds actor/action/object/place/state/need from the MeaningPerceptPacket
and identifies event schema candidates, missing slots, and uncertainty reasons.
"""

from __future__ import annotations

import uuid

from ..types.meaning_percept import (
    MeaningPerceptPacket,
    SituationFrame,
    ReferentAtom,
    ActionAtom,
    StateAtom,
    NeedAtom,
    AffordanceAtom,
    OutcomeAtom,
    ValenceAtom,
    EventSchema,
)
from ..types.context_kernel import ContextKernel
from .event_schema_loader import load_event_schemas, EventSchemaStore


# Seed event schemas — foundational child-learning mappings
_SEED_SCHEMAS: dict[str, EventSchema] = {
    "move_toward_source": EventSchema(
        schema_key="come",
        actor_role="listener",
        action_key="move_toward_source",
        destination_role="speaker",
        expected_outcomes=[OutcomeAtom(
            affected_entity_role="listener",
            changed_dimension="distance",
            direction="decrease",
            confidence=0.8,
            event_key="move_toward_source",
            state_changes=[{"dimension": "distance", "direction": "decrease"}],
        )],
        examples=["come", "come here", "come over"],
        confidence=0.8,
    ),
    "move_to_place": EventSchema(
        schema_key="go_to_place",
        actor_role="actor",
        action_key="move_to_place",
        destination_role="place",
        expected_outcomes=[OutcomeAtom(
            affected_entity_role="actor",
            changed_dimension="distance",
            direction="decrease",
            confidence=0.7,
            event_key="move_to_place",
            state_changes=[{"dimension": "distance", "direction": "decrease"}],
        )],
        examples=["go to kitchen", "let's go", "go there"],
        confidence=0.7,
    ),
    "transfer_object": EventSchema(
        schema_key="give",
        actor_role="listener",
        action_key="transfer_object",
        object_role="object",
        recipient_role="speaker",
        expected_outcomes=[OutcomeAtom(
            affected_entity_role="recipient",
            changed_dimension="possession",
            direction="increase",
            confidence=0.8,
            event_key="transfer_object",
            state_changes=[{"dimension": "possession", "direction": "increase"}],
            resource_changes=[{"resource": "object", "direction": "transfer"}],
        )],
        examples=["give me", "give it to me", "hand me"],
        confidence=0.8,
    ),
    "physically_harm_target": EventSchema(
        schema_key="beat",
        actor_role="actor",
        action_key="physically_harm_target",
        target_role="target",
        expected_outcomes=[
            OutcomeAtom(
                affected_entity_role="target",
                changed_dimension="health",
                direction="decrease",
                confidence=0.9,
                event_key="physically_harm_target",
                state_changes=[{"dimension": "health", "direction": "decrease"}, {"dimension": "safety", "direction": "decrease"}],
            ),
            OutcomeAtom(
                affected_entity_role="target",
                changed_dimension="safety",
                direction="decrease",
                confidence=0.85,
                event_key="physically_harm_target",
            ),
        ],
        examples=["beat him", "hit her", "attack them"],
        confidence=0.9,
    ),
    "consume_food": EventSchema(
        schema_key="eat",
        actor_role="actor",
        action_key="consume_food",
        object_role="food",
        expected_outcomes=[OutcomeAtom(
            affected_entity_role="actor",
            changed_dimension="hunger",
            direction="decrease",
            confidence=0.85,
            event_key="consume_food",
            state_changes=[{"dimension": "hunger", "direction": "decrease"}],
            resource_changes=[{"resource": "food", "direction": "consume"}],
        )],
        examples=["eat", "eat food", "eat lunch"],
        confidence=0.8,
    ),
    "increase_capability": EventSchema(
        schema_key="learn",
        actor_role="self",
        action_key="increase_capability",
        expected_outcomes=[OutcomeAtom(
            affected_entity_role="self",
            changed_dimension="knowledge",
            direction="increase",
            confidence=0.8,
            event_key="increase_capability",
            state_changes=[{"dimension": "knowledge", "direction": "increase"}],
        )],
        examples=["learn", "learn about", "teach me"],
        confidence=0.7,
    ),
    "improve_state": EventSchema(
        schema_key="help",
        actor_role="actor",
        action_key="improve_state",
        target_role="target",
        expected_outcomes=[OutcomeAtom(
            affected_entity_role="target",
            changed_dimension="safety",
            direction="increase",
            confidence=0.7,
            event_key="improve_state",
            state_changes=[{"dimension": "safety", "direction": "increase"}],
        )],
        examples=["help", "help me", "help him"],
        confidence=0.7,
    ),
}


class SituationFrameBuilder:
    """Builds SituationFrame from MeaningPerceptPacket + ContextKernel."""

    def __init__(self, event_schema_store: EventSchemaStore | None = None) -> None:
        self._schemas = dict(_SEED_SCHEMAS)
        self._event_store = event_schema_store or load_event_schemas()
        # Merge JSON-defined action schemas into seed schemas
        for key, loaded in self._event_store.action_schemas.items():
            if key not in self._schemas:
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
                self._schemas[key] = EventSchema(
                    schema_key=loaded.schema_key,
                    actor_role=loaded.actor_role,
                    action_key=loaded.action_key,
                    target_role=loaded.target_role,
                    object_role=loaded.object_role,
                    destination_role=loaded.destination_role,
                    recipient_role=loaded.recipient_role,
                    expected_outcomes=outcomes,
                    examples=list(loaded.aliases),
                    confidence=0.7,
                )

    def build(
        self,
        percept: MeaningPerceptPacket,
        kernel: ContextKernel,
    ) -> SituationFrame:
        """Build a SituationFrame from the meaning percept and kernel context."""
        frame = SituationFrame(
            id=uuid.uuid4().hex[:16],
            signal_id=percept.signal_id,
            context_id=percept.context_id,
        )

        # Bind actor — first referent with role=actor or the user
        for ref in percept.referents:
            if ref.role == "actor":
                frame.actor = ref
                break
        if not frame.actor and percept.referents:
            # Default: user is the actor
            for ref in percept.referents:
                if ref.entity_type == "user":
                    frame.actor = ref
                    break

        # Bind action — first action atom
        if percept.actions:
            frame.action = percept.actions[0]

        # Bind target — first referent with role=target
        for ref in percept.referents:
            if ref.role == "target":
                frame.target = ref
                break

        # Bind object — first referent with role=object
        for ref in percept.referents:
            if ref.role == "object":
                frame.object = ref
                break

        # Bind place — first referent with entity_type=place or role=place
        for ref in percept.referents:
            if ref.entity_type == "place" or ref.role == "place":
                frame.place = ref
                break

        # Bind recipient — first referent with role=recipient
        for ref in percept.referents:
            if ref.role == "recipient":
                frame.recipient = ref
                break

        # Copy state reports
        frame.state_reports = list(percept.states)

        # Copy needs
        frame.needs = list(percept.needs)

        # Match event schema candidates
        if frame.action:
            schema = self._schemas.get(frame.action.action_key)
            if schema:
                frame.event_schema_ids.append(schema.schema_key)
                # Copy expected outcomes from schema
                frame.expected_outcomes.extend(schema.expected_outcomes)

        # Identify missing slots based on schema
        if frame.action and frame.action.action_key in self._schemas:
            schema = self._schemas[frame.action.action_key]
            if schema.actor_role and not frame.actor:
                frame.missing_slots.append("actor")
            if schema.object_role and not frame.object:
                frame.missing_slots.append("object")
            if schema.target_role and not frame.target:
                frame.missing_slots.append("target")
            if schema.destination_role and not frame.destination:
                frame.missing_slots.append("destination")

        # Add uncertainty reasons
        if percept.unknown_lexemes:
            for lex in percept.unknown_lexemes:
                frame.uncertainty_reasons.append(
                    f"unknown_lexeme:{lex['surface']}"
                )
        if percept.idiom_candidates:
            for idiom in percept.idiom_candidates:
                frame.uncertainty_reasons.append(
                    f"idiom_candidate:{idiom['surface']}"
                )
        if frame.missing_slots:
            frame.uncertainty_reasons.append(
                f"missing_slots:{','.join(frame.missing_slots)}"
            )

        # Compute confidence
        filled_slots = sum(1 for s in [frame.actor, frame.action, frame.target,
                                        frame.object, frame.place, frame.recipient] if s)
        frame.confidence = min(0.9, 0.3 + filled_slots * 0.1)

        return frame

    def get_schema(self, action_key: str) -> EventSchema | None:
        """Retrieve a seed event schema by action key."""
        return self._schemas.get(action_key)
