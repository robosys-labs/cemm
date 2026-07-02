"""OutcomeEvaluator — predicts outcomes and valences from SituationFrame.

Implements §8.4 from cemm_foundational_fixes.md and §7 from architecture_new.md.

Evaluates expected outcomes for affected entities and determines whether
they are favorable or unfavorable (valence). Valence is entity-relative:
the same event can be favorable to one entity and unfavorable to another.

Examples:
    come -> distance(listener, speaker) decreases -> favorable to speaker
    eat -> hunger decreases -> favorable to actor
    beat him -> target health/safety decreases -> unfavorable to target
    learn -> self knowledge increases -> favorable to self
"""

from __future__ import annotations

from ..types.meaning_percept import (
    SituationFrame,
    OutcomeAtom,
    ValenceAtom,
)


# Entity class lookup by role
_ROLE_TO_CLASS: dict[str, str] = {
    "self": "self",
    "user": "human",
    "actor": "human",
    "listener": "human",
    "speaker": "human",
    "target": "human",
    "third_party": "human",
    "him": "human",
    "her": "human",
    "them": "human",
    "recipient": "human",
    "object": "object",
    "place": "world",
}

# Dimensions that are favorable when increased
_FAVORABLE_INCREASE = {"health", "happiness", "safety", "knowledge", "capability", "trust", "possession"}
# Dimensions that are favorable when decreased
_FAVORABLE_DECREASE = {"hunger", "thirst", "distance", "error_rate", "uncertainty", "confusion"}


class OutcomeEvaluator:
    """Evaluates outcomes and valences from a SituationFrame."""

    def evaluate(self, frame: SituationFrame) -> tuple[list[OutcomeAtom], list[ValenceAtom]]:
        """Return (outcomes, valences) for the given situation frame.

        Outcomes may already be partially populated from event schemas;
        this method enriches them and computes valence atoms.
        """
        outcomes = list(frame.expected_outcomes)

        # If no outcomes from schema, try to derive from action
        if not outcomes and frame.action:
            outcomes = self._derive_outcomes(frame)

        # Compute valences from outcomes
        valences = self._compute_valences(outcomes, frame)

        return outcomes, valences

    def _derive_outcomes(self, frame: SituationFrame) -> list[OutcomeAtom]:
        """Derive outcomes from action + state context when no schema matched."""
        outcomes: list[OutcomeAtom] = []
        if not frame.action:
            return outcomes

        action_key = frame.action.action_key

        # Harm actions
        if action_key in ("physically_harm_target", "attack", "hit", "beat"):
            target_role = "target" if frame.target else "third_party"
            outcomes.append(OutcomeAtom(
                affected_entity_role=target_role,
                changed_dimension="health",
                direction="decrease",
                confidence=0.85,
                event_key=action_key,
                state_changes=[{"dimension": "health", "direction": "decrease"}, {"dimension": "safety", "direction": "decrease"}],
            ))
            outcomes.append(OutcomeAtom(
                affected_entity_role=target_role,
                changed_dimension="safety",
                direction="decrease",
                confidence=0.8,
                event_key=action_key,
            ))

        # Movement actions
        elif action_key in ("move_toward_source", "move_to_place", "change_location"):
            actor = "actor" if frame.actor else "user"
            outcomes.append(OutcomeAtom(
                affected_entity_role=actor,
                changed_dimension="distance",
                direction="decrease",
                confidence=0.7,
                event_key=action_key,
                state_changes=[{"dimension": "distance", "direction": "decrease"}],
            ))

        # Transfer actions
        elif action_key in ("transfer_object", "transfer_to_speaker", "acquire_object"):
            recipient = "recipient" if frame.recipient else "speaker"
            outcomes.append(OutcomeAtom(
                affected_entity_role=recipient,
                changed_dimension="possession",
                direction="increase",
                confidence=0.75,
                event_key=action_key,
                state_changes=[{"dimension": "possession", "direction": "increase"}],
                resource_changes=[{"resource": "object", "direction": "transfer"}],
            ))

        # Consumption actions
        elif action_key in ("consume_food", "consume_liquid"):
            actor = "actor" if frame.actor else "user"
            dim = "hunger" if action_key == "consume_food" else "thirst"
            outcomes.append(OutcomeAtom(
                affected_entity_role=actor,
                changed_dimension=dim,
                direction="decrease",
                confidence=0.8,
                event_key=action_key,
                state_changes=[{"dimension": dim, "direction": "decrease"}],
                resource_changes=[{"resource": "food" if action_key == "consume_food" else "liquid", "direction": "consume"}],
            ))

        # Learning actions
        elif action_key in ("increase_capability", "transfer_knowledge"):
            outcomes.append(OutcomeAtom(
                affected_entity_role="self",
                changed_dimension="knowledge",
                direction="increase",
                confidence=0.75,
                event_key=action_key,
                state_changes=[{"dimension": "knowledge", "direction": "increase"}],
            ))

        # Help actions
        elif action_key == "improve_state":
            target = "target" if frame.target else "user"
            outcomes.append(OutcomeAtom(
                affected_entity_role=target,
                changed_dimension="safety",
                direction="increase",
                confidence=0.6,
                event_key=action_key,
                state_changes=[{"dimension": "safety", "direction": "increase"}],
            ))

        return outcomes

    def _compute_valences(self, outcomes: list[OutcomeAtom], frame: SituationFrame) -> list[ValenceAtom]:
        """Compute entity-relative valence from outcomes."""
        valences: list[ValenceAtom] = []
        seen: set[str] = set()

        for outcome in outcomes:
            role = outcome.affected_entity_role
            if role in seen:
                continue
            seen.add(role)

            entity_class = _ROLE_TO_CLASS.get(role, "unknown")
            dim = outcome.changed_dimension
            direction = outcome.direction

            # Determine valence
            is_favorable = False
            if direction == "increase" and dim in _FAVORABLE_INCREASE:
                is_favorable = True
            elif direction == "decrease" and dim in _FAVORABLE_DECREASE:
                is_favorable = True

            # Special case: harming a human is always unfavorable for that human
            if dim in ("health", "safety") and direction == "decrease" and entity_class == "human":
                is_favorable = False

            valence = "favorable" if is_favorable else "unfavorable"
            rationale = f"{dim} {direction} for {role}"

            valences.append(ValenceAtom(
                affected_entity_role=role,
                entity_class=entity_class,
                valence=valence,
                rationale=rationale,
                confidence=outcome.confidence,
            ))

        return valences
