"""Public schedule feasibility fixture; not training or gate evidence.

This openly enumerable factorial contains no secret, independent sensor
custody, physical-event authentication, blind challenge or leakage protection.
The evaluator constructs the initial state and uses simulator transitions;
only copies of sensor/action records are returned by SensorEpisode. Offline
access cannot enforce prediction before feedback. No frozen challenge is read.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import random

from .world import Action, Episode, World, observe, step


def _digest(block: int, case: int, purpose: str) -> bytes:
    return sha256(f"public-schedule-v1/{block}/{case}/{purpose}".encode()).digest()


def _order(names: tuple[str, ...], block: int, time: int) -> tuple[str, ...]:
    values = list(names)
    random.Random(int.from_bytes(_digest(block, 0, f"sensor/{time}"), "big")).shuffle(values)
    return tuple(values)


def make_evaluator_episode(case: int, *, block: int = 0) -> Episode:
    """Build one of 32 public combinations; no frozen protocol split is used.

    Participant slots are selected from block alone. The case spans all
    combinations of initial ordered participant bits, two set values, and
    simulator orientation. IDs and sensor order depend only on the public
    block and are intentionally shared across cases. This is a paired mechanics
    fixture, not a set of independently drawn or blinded worlds.
    """
    if type(case) is not int or not 0 <= case < 32 or type(block) is not int or block < 0:
        raise ValueError("invalid public fixture index")
    ids = tuple(_digest(block, 0, f"identity/{i}").hex()[:12] for i in range(3))
    if len(set(ids)) != len(ids):
        raise ValueError("fixture identity collision")
    slots = list(range(3))
    random.Random(int.from_bytes(_digest(block, 0, "participant-slots"), "big")).shuffle(slots)
    a, b, other = slots
    pair, values, orientation = case // 8, (case // 2) % 4, case % 2
    bits = [0, 0, 0]
    bits[a], bits[b], bits[other] = pair // 2, pair % 2, block % 2
    initial = World(ids, tuple(bits), orientation)
    actions = (Action("contact", (ids[a], ids[b])), Action("contact", (ids[b], ids[a])),
               Action("set", (ids[a],), values // 2), Action("set", (ids[a],), values % 2))
    states = [initial]
    sensors = [observe(initial, 0, _order(ids, block, 0))]
    for t, action in enumerate(actions, 1):
        states.append(step(states[-1], action))
        sensors.append(observe(states[-1], t, _order(action.participants, block, t)))
    return Episode(f"public-schedule-v1-{block}-{case}", "public_fixture", "factorial", block,
                   tuple(states), actions, tuple(sensors))


@dataclass(frozen=True)
class SensorEpisode:
    """Immutable offline sensor-only history; access is not a causal guard."""
    _observations: tuple[tuple[tuple[str, int], ...], ...]
    _action_records: tuple[tuple[str, tuple[str, ...], int | None], ...]

    @property
    def actions(self):
        # Consumers use only the count; the next action is obtained from turn.
        return (None,) * len(self._action_records)

    def _index(self, index):
        if type(index) is not int or not 0 <= index < len(self._action_records):
            raise IndexError("invalid turn")
        return index

    def _observation(self, index):
        return {"t": index, "measurements": [{"id": name, "bit": bit}
                                                for name, bit in self._observations[index]]}

    def learner_turn(self, index):
        index = self._index(index)
        kind, members, value = self._action_records[index]
        action = {"kind": kind, "participants": list(members)}
        if kind == "set":
            action["value"] = value
        return {"observation": self._observation(index), "action": action}

    def reveal_after_prediction(self, index):
        return self._observation(self._index(index) + 1)


def sensor_view(episode: Episode) -> SensorEpisode:
    """Copy the one realized evaluator trace; callers may obtain two views.

    This fixture-only converter does not independently authenticate records or
    prove that simulator transitions occurred. It never copies hidden state.
    """
    if type(episode) is not Episode or episode.split != "public_fixture" or episode.family != "factorial":
        raise ValueError("expected public factorial fixture")
    if len(episode.actions) != 4 or len(episode.sensors) != 5:
        raise ValueError("invalid fixture length")
    for action in episode.actions:
        if (type(action) is not Action or type(action.kind) is not str or
                type(action.participants) is not tuple or
                any(type(name) is not str or not name for name in action.participants)):
            raise ValueError("invalid fixture action")
    observations = []
    anchor_ids = None
    for t, observation in enumerate(episode.sensors):
        if (type(observation) is not dict or set(observation) != {"t", "measurements"} or
                type(observation["t"]) is not int or observation["t"] != t):
            raise ValueError("invalid observation envelope")
        records = observation["measurements"]
        if type(records) is not list:
            raise ValueError("invalid sensor measurements")
        values = []
        for item in records:
            if (type(item) is not dict or set(item) != {"id", "bit"} or
                    type(item["id"]) is not str or not item["id"] or
                    type(item["bit"]) is not int or item["bit"] not in (0, 1)):
                raise ValueError("invalid sensor record")
            values.append((item["id"], item["bit"]))
        names = [name for name, _ in values]
        if len(set(names)) != len(names):
            raise ValueError("duplicate identity")
        if t == 0:
            anchor_ids = set(names)
            if len(anchor_ids) != 3:
                raise ValueError("invalid full anchor")
        elif set(names) != set(episode.actions[t - 1].participants) or not set(names) <= anchor_ids:
            raise ValueError("feedback visibility differs from participants")
        observations.append(tuple(values))
    actions = tuple((action.kind, action.participants, action.value) for action in episode.actions)
    # Match the explicitly declared four-action curriculum; no hidden state is read.
    first, second, third, fourth = actions
    if (first[0] != "contact" or len(first[1]) != 2 or first[1][0] == first[1][1] or first[2] is not None or
            second != ("contact", first[1][::-1], None) or
            third[0] != "set" or fourth[0] != "set" or third[1] != (first[1][0],) or
            fourth[1] != third[1] or type(third[2]) is not int or third[2] not in (0, 1) or
            type(fourth[2]) is not int or fourth[2] not in (0, 1)):
        raise ValueError("invalid public schedule")
    return SensorEpisode(tuple(observations), actions)


def main() -> None:
    """Report public fixture coverage only, without training or scoring."""
    from collections import Counter
    import json
    from .geometry_diagnostic import coverage_report

    episodes = [make_evaluator_episode(i) for i in range(32)]
    contact_contexts = [Counter(), Counter()]
    set_contexts = [Counter(), Counter()]
    for episode in episodes:
        view = sensor_view(episode)
        for i in range(4):
            turn = view.learner_turn(i)
            action = turn["action"]
            values = {m["id"]: m["bit"] for m in turn["observation"]["measurements"]}
            if i < 2:
                key = "".join(str(values[name]) for name in action["participants"])
                contact_contexts[i][key] += 1
            else:
                key = str(values[action["participants"][0]]) + str(action["value"])
                set_contexts[i - 2][key] += 1
    print(json.dumps({"status": "PUBLIC_SCHEDULE_FEASIBILITY_ONLY", "gate_g1": "NOT_RUN",
                      "counts": coverage_report(episodes),
                      "observed_contact_pre_bits_by_position": contact_contexts,
                      "observed_set_pre_bit_and_value_by_position": set_contexts}, sort_keys=True))


if __name__ == "__main__":
    main()
