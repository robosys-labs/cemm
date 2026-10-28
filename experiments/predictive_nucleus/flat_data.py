"""Causal, sensor-only features for the flat recurrent reference model."""
from __future__ import annotations
from math import isfinite

MAX_ENTITIES = 6
FEATURES = 36


def initial_ids(observation: dict) -> tuple[str, ...]:
    values = readings(observation)
    if type(observation.get("t")) is not int or not 3 <= len(values) <= MAX_ENTITIES:
        raise ValueError("initial full observation requires 3-6 entities")
    return tuple(sorted(values))


def readings(observation: dict) -> dict[str, int]:
    records = observation.get("measurements")
    if not isinstance(records, list):
        raise ValueError("invalid observation")
    values = {}
    for m in records:
        if (not isinstance(m, dict) or set(m) != {"id", "bit"} or
                not isinstance(m["id"], str) or not m["id"] or m["id"] in values or
                type(m["bit"]) is not int or m["bit"] not in (0, 1)):
            raise ValueError("invalid sensor measurement")
        values[m["id"]] = m["bit"]
    return values


def event_features(ids: tuple[str, ...], observation: dict, action: dict, *, sensor_error_rate: float = 0.0) -> list[float]:
    seen = readings(observation)
    if not set(seen).issubset(ids):
        raise ValueError("observation introduces an unknown identity")
    if not isinstance(action, dict) or set(action) - {"kind", "participants", "value"}:
        raise ValueError("invalid action")
    kind = action.get("kind")
    members = action.get("participants")
    if not isinstance(members, (list, tuple)) or any(name not in ids for name in members):
        raise ValueError("invalid action participants")
    value = action.get("value")
    if kind == "contact" and (len(members) != 2 or members[0] == members[1] or value is not None):
        raise ValueError("invalid contact")
    if kind == "set" and (len(members) != 1 or type(value) is not int or value not in (0, 1)):
        raise ValueError("invalid set")
    if kind == "observe" and (members or value is not None):
        raise ValueError("invalid observation action")
    if kind not in ("contact", "set", "observe"):
        raise ValueError("invalid action kind")
    padded = list(ids) + [None] * (MAX_ENTITIES - len(ids))
    values = [float(seen.get(name, 0)) if name is not None else 0.0 for name in padded]
    mask = [float(name in seen) if name is not None else 0.0 for name in padded]
    valid = [float(name is not None) for name in padded]
    first = [float(bool(members) and name == members[0]) if name is not None else 0.0 for name in padded]
    second = [float(len(members) == 2 and name == members[1]) if name is not None else 0.0 for name in padded]
    action_kind = [float(kind == k) for k in ("contact", "set", "observe")]
    value_features = [float(kind == "set" and value == x) for x in (0, 1)]
    if (type(sensor_error_rate) not in (float, int) or not isfinite(sensor_error_rate) or
            not 0 <= sensor_error_rate < .5):
        raise ValueError("invalid supplied sensor calibration")
    result = values + mask + valid + first + second + action_kind + value_features + [float(sensor_error_rate)]
    if len(result) != FEATURES:
        raise AssertionError("feature width drift")
    return result


def target_observation(ids: tuple[str, ...], observation: dict) -> list[int]:
    seen = readings(observation)
    if not set(seen).issubset(ids):
        raise ValueError("feedback introduces an unknown identity")
    return [seen.get(name, -1) for name in ids] + [-1] * (MAX_ENTITIES - len(ids))


def sensor_episode(episode) -> list[tuple[list[float], list[int]]]:
    """Extract pre-action inputs and subsequent measured targets only."""
    if not episode.actions:
        raise ValueError("empty episode")
    ids = initial_ids(episode.learner_turn(0)["observation"])
    records = []
    for i in range(len(episode.actions)):
        turn = episode.learner_turn(i)
        feedback = episode.reveal_after_prediction(i)
        if (type(turn["observation"].get("t")) is not int or
                feedback.get("t") != turn["observation"]["t"] + 1):
            raise ValueError("misordered sensor feedback")
        records.append((event_features(ids, turn["observation"], turn["action"]),
                        target_observation(ids, feedback)))
    return records
