"""Full-feedback counterpart of the opened PR43 one-pair training fixture.

The same deterministic public actions, IDs and anchor are used, but each
post-action sensor samples all anchor IDs. Additional sensor values are
simulator observations, not persistence imputations. Offline histories and
the evaluator remain inspectable; this is neither custody nor a G1 challenge.
"""
from __future__ import annotations

from .causal_replay import FullSensorHistory
from .development_run import _training_history
from .schedule_fixture import SensorEpisode, make_evaluator_episode
from .world import Action, observe, step


def make_full_training_history(case, *, block=0):
    """Measure all IDs at each of the same five public action steps.

    Existing measurements keep their relative order; missing IDs are appended
    in sorted anchor-ID order. The simulator measures the entire requested
    list on the actual post-action world. Sensor coverage is deliberately
    supplied and noiseless; more observed bits are not an equal-data budget.
    """
    episode = make_evaluator_episode(case, block=block)
    original = _training_history(episode)
    anchor = original._observations[0]
    ids = tuple(sorted(name for name, _ in anchor))
    observations = [anchor]
    world = episode.states[0]
    for time, (kind, participants, value) in enumerate(original._action_records, 1):
        world = step(world, Action(kind, participants, value))
        prior = original._observations[time]
        names = tuple(name for name, _ in prior)
        visible = names + tuple(name for name in ids if name not in names)
        measured = observe(world, time, visible)
        current = tuple((item["id"], item["bit"]) for item in measured["measurements"])
        if current[:len(prior)] != prior:
            raise RuntimeError("full sensor conflicts with original measured feedback")
        observations.append(current)
    return FullSensorHistory.from_sensor_view(SensorEpisode(tuple(observations), original._action_records))
