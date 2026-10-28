"""Full-feedback view of the already-opened public two-pair fixture.

This development fixture supplies a noiseless reading of every anchor entity
after each action. The additional readings come from the evaluator's sensor,
not from an assumed persistence rule. It does not create new worlds, an
independent oracle, authenticated readings, or an isolation boundary.
"""
from __future__ import annotations

from .causal_replay import FullSensorHistory
from .schedule_fixture import SensorEpisode
from .two_pair_fixture import sensor_view
from .world import Action, observe, step


def full_sensor_evaluation_view(episode):
    """Produce a complete sensor-only view of the supplied public episode.

    The original anchor, action records and measured feedback remain unchanged.
    Within each feedback record, its original ordered measurements are retained;
    remaining anchor identities are appended in sorted-ID order. World state and
    hidden dynamics are read here only by the evaluator when constructing sensor
    readings; neither is placed in the returned learner history.
    """
    original = sensor_view(episode)
    anchor = original._observations[0]
    ids = tuple(sorted(name for name, _ in anchor))
    observations = [anchor]
    world = episode.states[0]
    initial = observe(world, 0, tuple(name for name, _ in anchor))
    if tuple((item["id"], item["bit"]) for item in initial["measurements"]) != anchor:
        raise ValueError("anchor sensor conflicts with initial evaluator state")
    for time, (kind, participants, value) in enumerate(original._action_records, 1):
        world = step(world, Action(kind, participants, value))
        if world != episode.states[time]:
            raise ValueError("evaluator states disagree with action transitions")
        prior = original._observations[time]
        names = tuple(name for name, _ in prior)
        visible = names + tuple(name for name in ids if name not in names)
        measured = observe(world, time, visible)
        current = tuple((item["id"], item["bit"]) for item in measured["measurements"])
        if current[:len(prior)] != prior:
            raise ValueError("full sensor conflicts with original measured feedback")
        observations.append(current)
    return FullSensorHistory.from_sensor_view(SensorEpisode(tuple(observations), original._action_records))
