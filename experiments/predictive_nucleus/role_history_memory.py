"""First-action-normalized full-history memory for public development.

This exact-prefix control is not a learned transition law, a custody boundary
or an independent challenge. It supports three-entity anchors with a distinct
two-operand first contact. The first delivered action fixes anonymous slots;
no later action, outcome, evaluator state or hidden role is used to choose
them. Measurement-list order is deliberately discarded; chronological order,
action operand order and all measured bits remain part of the key.
"""
from __future__ import annotations

from dataclasses import dataclass

from .causal_replay import FullSensorHistory
from .flat_data import initial_ids
from .history_memory import HistoryMemory
from .sensor_controls import _observation, _turn

SLOTS = ("r0", "r1", "r2")


def _mapping(ids, action):
    """Return slot labels from the current first action, or None if unsupported."""
    members = action["participants"]
    if len(ids) != 3 or action["kind"] != "contact" or len(members) != 2 or len(set(members)) != 2:
        return None
    remaining = tuple(name for name in ids if name not in members)
    if len(remaining) != 1:
        return None
    return dict(zip((*members, remaining[0]), SLOTS))


def _observation_to_slots(observation, mapping):
    readings = _observation(observation, ids=tuple(mapping))
    return {"t": observation["t"], "measurements":
            [{"id": mapping[name], "bit": bit}
             for name, bit in sorted(readings.items(), key=lambda pair: mapping[pair[0]])]}


def _action_to_slots(action, mapping):
    result = {"kind": action["kind"], "participants": [mapping[name] for name in action["participants"]]}
    if action["kind"] == "set":
        result["value"] = action["value"]
    return result


def _normalized_history(history):
    if type(history) is not FullSensorHistory:
        raise ValueError("expected full sensor history")
    first = history.learner_turn(0)
    ids = initial_ids(first["observation"])
    _, action = _turn(ids, first, time=0)
    mapping = _mapping(ids, action)
    if mapping is None:
        raise ValueError("unsupported first action or anchor")
    observations = []
    for i in range(len(history.actions) + 1):
        original = first["observation"] if i == 0 else history.reveal_after_prediction(i - 1)
        normalized = _observation_to_slots(original, mapping)
        observations.append(tuple((item["id"], item["bit"]) for item in normalized["measurements"]))
    actions = []
    for i in range(len(history.actions)):
        action = _action_to_slots(history.learner_turn(i)["action"], mapping)
        actions.append((action["kind"], tuple(action["participants"]), action.get("value")))
    return FullSensorHistory(tuple(observations), tuple(actions))


@dataclass(frozen=True)
class RoleHistoryMemory:
    """Frozen empirical full-feedback table, with declared first-action slots."""
    _memory: HistoryMemory

    def __post_init__(self):
        if type(self._memory) is not HistoryMemory or self._memory.feedback_policy != "full":
            raise ValueError("expected full sensor memory")

    @classmethod
    def fit(cls, histories):
        """Read complete sensor targets only; reject unsupported training traces."""
        return cls(HistoryMemory.fit_full_sensor(_normalized_history(h) for h in histories))

    def new_predictor(self):
        return RoleHistoryPredictor(self._memory)


class RoleHistoryPredictor:
    """Single-consumer sequential adapter; no online fitting or inferred facts."""

    def __init__(self, memory):
        self._memory = memory
        self._ids = None
        self._pending = False

    def start(self, anchor):
        if self._pending:
            raise RuntimeError("feedback required before reset")
        seen = _observation(anchor, time=0)
        self._ids = initial_ids(anchor)
        self._time, self._seen = 0, dict(seen)
        # A copy avoids caller mutation before the first action arrives.
        self._anchor = {"t": 0, "measurements": [{"id": k, "bit": v} for k, v in seen.items()]}
        self._mapping = None
        self._model = None
        self._unsupported = len(self._ids) != 3

    def predict(self, turn):
        if self._ids is None:
            raise RuntimeError("initial observation required")
        if self._pending:
            raise RuntimeError("feedback required before prediction")
        seen, action = _turn(self._ids, turn, time=self._time)
        if seen != self._seen:
            raise ValueError("turn does not match latest observation")
        if self._time == 0 and not self._unsupported:
            self._mapping = _mapping(self._ids, action)
            if self._mapping is None:
                self._unsupported = True
            else:
                self._model = self._memory.new_predictor()
                self._model.start(_observation_to_slots(self._anchor, self._mapping))
        if self._unsupported:
            result = {"status": "ABSTAIN", "reason": "UNSUPPORTED_FIRST_ACTION_OR_ANCHOR",
                      "ids": self._ids, "worlds": None}
        else:
            normalized = {"observation": _observation_to_slots(turn["observation"], self._mapping),
                          "action": _action_to_slots(action, self._mapping)}
            scored = self._model.predict(normalized)
            worlds = scored["worlds"]
            if worlds is not None:
                indices = tuple(SLOTS.index(self._mapping[name]) for name in self._ids)
                worlds = {tuple(world[i] for i in indices): probability for world, probability in worlds.items()}
            result = {"status": scored["status"], "reason": scored["reason"], "ids": self._ids, "worlds": worlds}
        self._pending = True
        return result

    def receive(self, feedback):
        if not self._pending:
            raise RuntimeError("prediction required before feedback")
        seen = _observation(feedback, time=self._time + 1, ids=self._ids)
        if set(seen) != set(self._ids):
            raise ValueError("full feedback must measure every anchor identity")
        if self._model is not None:
            self._model.receive(_observation_to_slots(feedback, self._mapping))
        self._time += 1
        self._seen = dict(seen)
        self._pending = False
