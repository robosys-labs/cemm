"""Public, noiseless coverage diagnostic for a proposed participant sensor mask.

Evaluator-only offline reconstruction from complete simulator states. This is
not a training source, a causal prediction interface, a matched evaluation,
independent sensor custody, or a blinded challenge. No model scores are made.
It does not verify that the supplied states follow the simulator dynamics.
"""
from __future__ import annotations

from copy import deepcopy
from collections import Counter

from .world import Action, Episode, World, observe


def participant_replay(episode: Episode) -> tuple[tuple[dict, dict], ...]:
    """Reconstruct full initial anchor and noiseless action-local feedback.

    Set and contact actions reveal their unique participants, in their action
    order; an observation-only action reveals nothing in this diagnostic.
    Post-action feedback is the next action's pre-action observation. Returned
    data are ordinary mutable copies, never references to the source episode.
    This offline function returns future feedback and cannot enforce that a
    learner waits until prediction; no learner should consume this diagnostic.
    """
    if type(episode) is not Episode or not episode.actions:
        raise ValueError("expected a nonempty evaluator episode")
    if len(episode.states) != len(episode.actions) + 1:
        raise ValueError("misaligned evaluator episode")
    first = episode.states[0]
    if type(first) is not World:
        raise ValueError("invalid evaluator state")
    ids = first.ids
    for state in episode.states:
        if type(state) is not World or state.ids != ids:
            raise ValueError("inconsistent evaluator identities")
    for action in episode.actions:
        if type(action) is not Action or type(action.participants) is not tuple:
            raise ValueError("invalid evaluator action")
        members = action.participants
        if any(type(name) is not str or name not in ids for name in members):
            raise ValueError("unknown action participant")
        if action.kind == "set":
            valid = len(members) == 1 and type(action.value) is int and action.value in (0, 1)
        elif action.kind == "contact":
            valid = len(members) == 2 and action.value is None
        elif action.kind == "observe":
            valid = not members and action.value is None
        else:
            valid = False
        if not valid:
            raise ValueError("invalid evaluator action")

    previous = observe(first, 0, ids)
    records = []
    for index, action in enumerate(episode.actions):
        visible = tuple(dict.fromkeys(action.participants))
        feedback = observe(episode.states[index + 1], index + 1, visible)
        turn = {"observation": deepcopy(previous), "action": action.public()}
        records.append((turn, deepcopy(feedback)))
        previous = feedback
    return tuple(records)


def coverage_report(episodes) -> dict:
    """Count visibility and complete pairs, not model performance or accuracy.

    Contact usability mirrors the current structured learner's requirement:
    two distinct participants must appear in both immediate observations.
    Set usability likewise requires the participant in pre- and post-inputs.
    """
    counts = Counter()
    for episode in episodes:
        records = participant_replay(episode)
        counts["episodes"] += 1
        for turn, feedback in records:
            action = turn["action"]
            kind = action["kind"]
            names = action["participants"]
            pre = {item["id"] for item in turn["observation"]["measurements"]}
            post = {item["id"] for item in feedback["measurements"]}
            counts["actions"] += 1
            counts[f"{kind}_actions"] += 1
            counts["empty_feedback"] += not post
            counts["pre_measurements"] += len(pre)
            counts["post_measurements"] += len(post)
            if kind == "contact" and len(set(names)) == 2 and set(names) <= pre and set(names) <= post:
                counts["complete_contact_pairs"] += 1
            if kind == "set" and set(names) <= pre and set(names) <= post:
                counts["complete_set_pairs"] += 1
    keys = ("episodes", "actions", "set_actions", "contact_actions", "observe_actions",
            "empty_feedback", "pre_measurements", "post_measurements",
            "complete_contact_pairs", "complete_set_pairs")
    return {key: counts[key] for key in keys}


def main() -> None:
    """Reproduce the 600-episode public training-schedule coverage diagnostic."""
    import argparse
    import json
    from .protocol import read_protocol, verify_protocol
    from .world import make_episode

    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    config = read_protocol()
    verify_protocol(config)
    seeds = config["splits"]["train"]["seeds"]
    episodes = [make_episode("train", seeds[i % len(seeds)], i,
                             ("single_contact", "two_contacts")[i % 2])
                for i in range(600)]
    print(json.dumps({"status": "PUBLIC_DEVELOPMENT_COVERAGE_ONLY",
                      "gate_g1": "NOT_RUN", "sensor": "NOISELESS_PARTICIPANT_ONLY",
                      "observe_feedback": "EMPTY", "counts": coverage_report(episodes)},
                     sort_keys=True))


if __name__ == "__main__":
    main()
