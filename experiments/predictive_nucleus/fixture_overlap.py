"""Finite public fixture trace-overlap audit; not calibration or a challenge.

Normalize opaque handles by their order in the first public action, then
ignore measurement order. This compares complete *observed* histories. It
does not establish sampling independence, provenance, blindness, or model
performance; coincident traces can occur in independent discrete draws.
"""
from __future__ import annotations

import json
from collections import Counter

from .flat_data import event_features, initial_ids, readings
from .schedule_fixture import SensorEpisode, make_evaluator_episode, sensor_view


def normalized_trace(view: SensorEpisode) -> tuple:
    """Canonicalize one complete public sensor/action history.

    A and B name the first action's ordered operands, not hidden simulator
    roles. The remaining anchor handle is C. Measurement order is ignored;
    action order, times, sensor bits and coverage are retained. The input is
    a sensor-only view: evaluator state and orientation are never read.
    """
    if type(view) is not SensorEpisode or len(view.actions) != 4:
        raise ValueError("expected a four-step public sensor view")
    first = view.learner_turn(0)
    anchor, first_action = first["observation"], first["action"]
    ids = initial_ids(anchor)
    if anchor.get("t") != 0 or len(ids) != 3:
        raise ValueError("expected a three-identity initial anchor")
    event_features(ids, anchor, first_action)
    members = first_action["participants"]
    if first_action["kind"] != "contact" or len(members) != 2 or members[0] == members[1]:
        raise ValueError("first action must contact distinct participants")
    remaining = set(ids) - set(members)
    if len(remaining) != 1:
        raise ValueError("invalid first-action identities")
    role = {members[0]: "A", members[1]: "B", remaining.pop(): "C"}

    def observation(record, time):
        if (type(record) is not dict or set(record) != {"t", "measurements"} or
                type(record["t"]) is not int or record["t"] != time):
            raise ValueError("invalid observation time or envelope")
        values = readings(record)
        if not set(values) <= set(ids):
            raise ValueError("unknown observation identity")
        return time, tuple(sorted((role[name], bit) for name, bit in values.items()))

    trace = []
    previous = None
    for time in range(4):
        turn = view.learner_turn(time)
        if type(turn) is not dict or set(turn) != {"observation", "action"}:
            raise ValueError("invalid learner turn")
        before, action = turn["observation"], turn["action"]
        before_normalized = observation(before, time)
        if previous is not None and before_normalized != previous:
            raise ValueError("feedback and next input differ")
        event_features(ids, before, action)
        after = observation(view.reveal_after_prediction(time), time + 1)
        trace.append((before_normalized, action["kind"],
                      tuple(role[name] for name in action["participants"]),
                      action.get("value"), after))
        previous = after
    return tuple(trace)


def _samples_from_trace(trace: tuple) -> tuple[tuple, tuple]:
    """Mirror the structured extractor's immediate visibility eligibility.

    A contact contributes its ordered pre/post pair only when both distinct
    participants are observed before and after. A set contributes its
    participant's before/value/after tuple only when observed at both times.
    Incomplete events are excluded; no missing bits are imputed.
    """
    contacts, sets = [], []
    for before, kind, members, value, after in trace:
        pre = dict(before[1])
        post = dict(after[1])
        if (kind == "contact" and len(members) == 2 and len(set(members)) == 2 and
                all(name in pre and name in post for name in members)):
            a, b = members
            contacts.append((pre[a], pre[b], post[a], post[b]))
        elif (kind == "set" and len(members) == 1 and
              members[0] in pre and members[0] in post):
            name = members[0]
            sets.append((pre[name], value, post[name]))
    return tuple(contacts), tuple(sets)


def observed_local_samples(view: SensorEpisode) -> tuple[tuple, tuple]:
    """Return structured-style local contact and set samples from sensors."""
    return _samples_from_trace(normalized_trace(view))


def audit_blocks(blocks=(0, 1, 2, 3)) -> dict:
    """Count exact overlaps in explicitly enumerated fixture blocks only.

    Local multiset intersection sums the minimum count for each tuple across
    the two blocks. It omits episode grouping and does not count independent
    physical events, establish independent sampling, or prove leakage.
    """
    if (type(blocks) is not tuple or not blocks or
            any(type(block) is not int or block < 0 for block in blocks) or
            len(set(blocks)) != len(blocks)):
        raise ValueError("expected distinct nonnegative public block indexes")
    histories = {}
    local_contacts, local_sets = {}, {}
    for block in blocks:
        histories[block] = set()
        local_contacts[block], local_sets[block] = Counter(), Counter()
        for case in range(32):
            trace = normalized_trace(sensor_view(make_evaluator_episode(case, block=block)))
            histories[block].add(trace)
            contacts, sets = _samples_from_trace(trace)
            local_contacts[block].update(contacts)
            local_sets[block].update(sets)
    return {
        "status": "PUBLIC_FINITE_FIXTURE_OVERLAP_ONLY",
        "gate_g1": "NOT_RUN",
        "calibration_or_challenge": False,
        "cases_per_block": 32,
        "unique_normalized_traces": {str(block): len(histories[block]) for block in blocks},
        "pairwise_overlap": [
            {"blocks": [a, b], "unique_shared_traces": len(histories[a] & histories[b])}
            for i, a in enumerate(blocks) for b in blocks[i + 1:]
        ],
        "local_sample_summary": {
            str(block): {
                "contact_events": sum(local_contacts[block].values()),
                "unique_contact_samples": len(local_contacts[block]),
                "set_events": sum(local_sets[block].values()),
                "unique_set_samples": len(local_sets[block]),
            } for block in blocks
        },
        "pairwise_local_overlap": [
            {
                "blocks": [a, b],
                "unique_shared_contact_samples": len(local_contacts[a].keys() & local_contacts[b].keys()),
                "shared_contact_events_by_multiplicity": sum((local_contacts[a] & local_contacts[b]).values()),
                "unique_shared_set_samples": len(local_sets[a].keys() & local_sets[b].keys()),
                "shared_set_events_by_multiplicity": sum((local_sets[a] & local_sets[b]).values()),
            }
            for i, a in enumerate(blocks) for b in blocks[i + 1:]
        ],
    }


def main():
    print(json.dumps(audit_blocks(), sort_keys=True))


if __name__ == "__main__":
    main()
