"""Public two-pair schedule mechanics; not a training split or challenge.

The 64 cases exhaust an open factorial and share identities within a block.
The evaluator, hidden states and complete offline histories remain accessible
in the process. This fixture supplies no independence, blind custody, source
authentication, or security boundary, and no model performance is reported.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
import random

from .flat_data import event_features, initial_ids, readings
from .schedule_fixture import SensorEpisode
from .world import Action, Episode, World, observe, step


def _digest(block: int, purpose: str) -> bytes:
    return sha256(f"public-two-pair-v1/{block}/{purpose}".encode()).digest()


def _order(ids: tuple[str, ...], block: int, time: int) -> tuple[str, ...]:
    names = list(ids)
    random.Random(int.from_bytes(_digest(block, f"sensor/{time}"), "big")).shuffle(names)
    return tuple(names)


def make_evaluator_episode(case: int, *, block: int = 0) -> Episode:
    """Construct an open 3-bit, two-set-value, two-orientation factorial.

    Identity allocation, participant positions, sensor order and the action
    schedule do not depend on the case. Twin cases differing only in orientation
    have the same initial observation and actions. A public twin is not a
    blinded or independently custodied environment.
    """
    if type(case) is not int or not 0 <= case < 64 or type(block) is not int or block < 0:
        raise ValueError("invalid public two-pair case")
    ids = tuple(_digest(block, f"id/{i}").hex()[:12] for i in range(3))
    if len(set(ids)) != 3:
        raise ValueError("identity collision")
    positions = list(range(3))
    random.Random(int.from_bytes(_digest(block, "positions"), "big")).shuffle(positions)
    a, b, c = (ids[i] for i in positions)
    bits_index, values, orientation = case // 8, (case // 2) % 4, case % 2
    role_bits = (bits_index // 4, (bits_index // 2) % 2, bits_index % 2)
    bits = [0] * 3
    for slot, value in zip(positions, role_bits):
        bits[slot] = value
    actions = (Action("contact", (a, b)), Action("set", (b,), values // 2),
               Action("observe"), Action("contact", (b, c)), Action("set", (c,), values % 2))
    initial = World(ids, tuple(bits), orientation)
    states, sensors = [initial], [observe(initial, 0, _order(ids, block, 0))]
    for time, action in enumerate(actions, 1):
        states.append(step(states[-1], action))
        # This observe-only action explicitly measures B,C. Its visibility and
        # one-action cost are supplied by the public experiment design.
        visible = (b, c) if action.kind == "observe" else action.participants
        sensors.append(observe(states[-1], time, _order(visible, block, time)))
    return Episode(f"public-two-pair-v1-{block}-{case}", "public_two_pair", "two_pair_fixture", block,
                   tuple(states), actions, tuple(sensors))


def sensor_view(episode: Episode) -> SensorEpisode:
    """Return an immutable sensor/action copy, with no evaluator state fields.

    The complete offline view is accessible to callers and does not enforce
    prediction-before-feedback. Validation checks shape and chronology, not
    physical provenance or whether supplied states follow the simulator.
    """
    if (type(episode) is not Episode or episode.split != "public_two_pair" or
            episode.family != "two_pair_fixture" or len(episode.actions) != 5 or len(episode.sensors) != 6):
        raise ValueError("expected public two-pair fixture")
    records = []
    for action in episode.actions:
        if (type(action) is not Action or type(action.kind) is not str or
                type(action.participants) is not tuple or
                any(type(name) is not str or not name for name in action.participants)):
            raise ValueError("invalid action")
        records.append((action.kind, action.participants, action.value))
    first, second, third, fourth, fifth = records
    if (first[0] != "contact" or len(first[1]) != 2 or first[1][0] == first[1][1] or first[2] is not None or
            second[0] != "set" or second[1] != first[1][1:] or type(second[2]) is not int or second[2] not in (0, 1) or
            third != ("observe", (), None) or fourth[0] != "contact" or len(fourth[1]) != 2 or
            fourth[1][0] != first[1][1] or fourth[1][1] in first[1] or fourth[2] is not None or
            fifth[0] != "set" or fifth[1] != fourth[1][1:] or type(fifth[2]) is not int or fifth[2] not in (0, 1)):
        raise ValueError("invalid public two-pair schedule")
    ids = None
    observations = []
    for time, observation in enumerate(episode.sensors):
        if (type(observation) is not dict or set(observation) != {"t", "measurements"} or
                type(observation["t"]) is not int or observation["t"] != time or
                type(observation["measurements"]) is not list):
            raise ValueError("invalid observation")
        for item in observation["measurements"]:
            if (type(item) is not dict or set(item) != {"id", "bit"} or type(item["id"]) is not str or
                    not item["id"] or type(item["bit"]) is not int or item["bit"] not in (0, 1)):
                raise ValueError("invalid measurement")
        found = readings(observation)
        if time == 0:
            ids = initial_ids(observation)
            if len(ids) != 3 or set(ids) != set(first[1] + fourth[1][1:]):
                raise ValueError("invalid initial anchor")
        else:
            expected = fourth[1] if time == 3 else records[time - 1][1]
            if set(found) != set(expected):
                raise ValueError("unexpected sensor visibility")
        observations.append(tuple((item["id"], item["bit"]) for item in observation["measurements"]))
    return SensorEpisode(tuple(observations), tuple(records))


def fixture_report() -> dict:
    """Count public observed contexts only; neither train nor score models."""
    counts = [Counter() for _ in range(5)]
    actions, observed_bits = Counter(), 0
    previous_twin = None
    indistinguishable_twins = 0
    for case in range(64):
        view = sensor_view(make_evaluator_episode(case))
        if case % 2 == 0:
            previous_twin = view
        else:
            # Equality compares the complete sensor/action records, not the
            # evaluator's state or hidden mechanism label.
            indistinguishable_twins += int(view == previous_twin)
        for i in range(5):
            turn = view.learner_turn(i)
            feedback = view.reveal_after_prediction(i)
            before, after, action = readings(turn["observation"]), readings(feedback), turn["action"]
            ids = initial_ids(view.learner_turn(0)["observation"])
            event_features(ids, turn["observation"], action)
            names = action["participants"]
            actions[action["kind"]] += 1
            observed_bits += len(after)
            if action["kind"] == "contact" and all(n in before and n in after for n in names):
                counts[i]["".join(str(before[n]) for n in names)] += 1
            elif action["kind"] == "set" and names[0] in before and names[0] in after:
                counts[i][str(before[names[0]]) + str(action["value"])] += 1
    return {"status": "PUBLIC_TWO_PAIR_FEASIBILITY_ONLY", "gate_g1": "NOT_RUN",
            "cases": 64, "shared_identity_blocks": 1, "independent_world_claim": False,
            "steps_per_case": 5, "contact_actions": actions["contact"], "set_actions": actions["set"],
            "observe_actions": actions["observe"], "observed_feedback_bits": observed_bits,
            "orientation_twin_pairs": 32, "identical_sensor_history_twin_pairs": indistinguishable_twins,
            "complete_contacts": sum(sum(counts[i].values()) for i in (0, 3)),
            "complete_sets": sum(sum(counts[i].values()) for i in (1, 4)),
            "contexts_by_action_position": [dict(sorted(c.items())) for c in counts]}


def main():
    print(json.dumps(fixture_report(), sort_keys=True))


if __name__ == "__main__":
    main()
