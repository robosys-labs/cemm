"""Exact public-history control with fully observed sensor targets only.

Training requires complete post-action readings in the ordinary feedback stream;
partial readings are never completed using persistence or evaluator state. The
frozen identity-specific table is a development control, not evidence of
independent data, authenticated sensors, or an unbiased complete-world sample.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import json

from .causal_replay import DevelopmentHistory, FullSensorHistory, _development_snapshot
from .flat_data import initial_ids
from .schedule_fixture import SensorEpisode
from .sensor_controls import _observation, _turn


def _encode(value):
    # Mapping order is immaterial; ordered participant and sensor lists are not.
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class HistoryMemory:
    """Frozen empirical distribution indexed by exact delivered public history.

    IDs are literal: renaming even one identity creates a distinct context.
    Keys include the anchor, each preceding turn and feedback in order, and
    the current turn. The current feedback is never part of the lookup.
    Repeated episodes contribute repeated counts. Sensor noise and selection
    of fully observed targets can bias counts; they are not calibrated gold.
    """

    _rows: tuple
    episode_count: int
    total_events: int
    complete_targets: int
    feedback_policy: str = "participants"

    def __post_init__(self):
        if (self.feedback_policy not in ("participants", "full") or type(self._rows) is not tuple or
                any(type(n) is not int or n < 0 for n in
                    (self.episode_count, self.total_events, self.complete_targets)) or
                not self.episode_count <= self.total_events <= 12 * self.episode_count or
                self.complete_targets > self.total_events):
            raise ValueError("invalid history table counts")
        keys, total = set(), 0
        for row in self._rows:
            if type(row) is not tuple or len(row) != 2:
                raise ValueError("invalid history table row")
            key, outcomes = row
            if (type(key) is not tuple or not 2 <= len(key) <= 24 or len(key) % 2 or
                    any(type(part) is not str for part in key) or key in keys or
                    type(outcomes) is not tuple or not outcomes):
                raise ValueError("invalid history table key")
            keys.add(key)
            try:
                entries = [json.loads(part) for part in key]
                if any(_encode(value) != part for value, part in zip(entries, key, strict=True)):
                    raise ValueError("noncanonical history table key")
                anchor = entries[0]
                _observation(anchor, time=0)
                ids = initial_ids(anchor)
                previous = key[0]
                for i, turn in enumerate(entries[1::2]):
                    _, action = _turn(ids, turn, time=i)
                    if _encode(turn["observation"]) != previous:
                        raise ValueError("history chronology differs")
                    if 2 + 2 * i < len(entries):
                        feedback = entries[2 + 2 * i]
                        measured = _observation(feedback, time=i + 1, ids=ids)
                        if self.feedback_policy == "full" and set(measured) != set(ids):
                            raise ValueError("incomplete full feedback")
                        if (self.feedback_policy == "participants" and action["kind"] != "observe" and
                                not set(measured) <= set(action["participants"])):
                            raise ValueError("invalid history feedback")
                        previous = key[2 + 2 * i]
            except (TypeError, KeyError, IndexError, ValueError) as exc:
                raise ValueError("invalid history table key") from exc
            worlds = set()
            for entry in outcomes:
                if type(entry) is not tuple or len(entry) != 2:
                    raise ValueError("invalid history table outcome")
                world, count = entry
                if (type(world) is not tuple or len(world) != len(ids) or
                        any(type(bit) is not int or bit not in (0, 1) for bit in world) or
                        world in worlds or type(count) is not int or count < 1):
                    raise ValueError("invalid history table outcome")
                worlds.add(world)
                total += count
        if total != self.complete_targets:
            raise ValueError("history table count mismatch")

    @classmethod
    def fit(cls, histories):
        """Fit on DevelopmentHistory records, without reading evaluator state.

        Split membership and provenance are the caller's responsibility. A
        complete feedback is a complete *sensor reading*, not assured truth.
        """
        return cls._fit(histories, "participants")

    @classmethod
    def fit_full_sensor(cls, histories):
        """Fit explicitly complete feedback without fabricating missing bits."""
        return cls._fit(histories, "full")

    @classmethod
    def _fit(cls, histories, policy):
        counts = defaultdict(Counter)
        episodes = total = complete = 0
        for history in histories:
            expected_type = FullSensorHistory if policy == "full" else DevelopmentHistory
            if type(history) is not expected_type:
                raise ValueError("expected immutable development history")
            anchor, turns, feedbacks = _development_snapshot(
                SensorEpisode(history._observations, history._action_records), feedback_policy=policy)
            ids = initial_ids(json.loads(anchor))
            prefix = [_encode(json.loads(anchor))]
            for turn, feedback in zip(turns, feedbacks, strict=True):
                turn = _encode(json.loads(turn))
                feedback_obj = json.loads(feedback)
                key = tuple((*prefix, turn))
                measured = _observation(feedback_obj, ids=ids)
                total += 1
                if set(measured) == set(ids):
                    counts[key][tuple(measured[name] for name in ids)] += 1
                    complete += 1
                prefix.extend((turn, _encode(feedback_obj)))
            episodes += 1
        # Nested tuples avoid caller mutation of the stored counts.
        rows = tuple((key, tuple(sorted(outcomes.items()))) for key, outcomes in sorted(counts.items()))
        return cls(rows, episodes, total, complete, policy)

    def new_predictor(self):
        return HistoryMemoryPredictor(self)


class HistoryMemoryPredictor:
    """Sequential, single-consumer adapter; no online fitting or security boundary."""

    def __init__(self, memory):
        if type(memory) is not HistoryMemory:
            raise ValueError("expected fitted history memory")
        self._table = dict(memory._rows)
        self._feedback_policy = memory.feedback_policy
        self._prefix = None
        self._pending = None

    def start(self, anchor):
        if self._pending is not None:
            raise RuntimeError("feedback required before reset")
        _observation(anchor)
        self._ids = initial_ids(anchor)
        self._time = anchor["t"]
        self._previous = _encode(anchor)
        self._prefix = [self._previous]

    def predict(self, turn):
        if self._prefix is None:
            raise RuntimeError("initial observation required")
        if self._pending is not None:
            raise RuntimeError("feedback required before prediction")
        _, action = _turn(self._ids, turn, time=self._time)
        if _encode(turn["observation"]) != self._previous:
            raise ValueError("turn does not match latest observation")
        encoded = _encode(turn)
        outcomes = self._table.get(tuple((*self._prefix, encoded)))
        self._prefix.append(encoded)
        self._pending = (action["kind"], tuple(action["participants"]))
        if outcomes is None:
            return {"status": "ABSTAIN", "reason": "UNSEEN_COMPLETE_TARGET_CONTEXT",
                    "ids": self._ids, "worlds": None}
        total = sum(count for _, count in outcomes)
        return {"status": "PREDICTED", "reason": None, "ids": self._ids,
                "worlds": {world: count / total for world, count in outcomes}}

    def receive(self, feedback):
        if self._pending is None:
            raise RuntimeError("prediction required before feedback")
        seen = _observation(feedback, time=self._time + 1, ids=self._ids)
        kind, participants = self._pending
        if self._feedback_policy == "full" and set(seen) != set(self._ids):
            raise ValueError("full feedback must measure every anchor identity")
        if self._feedback_policy == "participants" and kind != "observe" and not set(seen) <= set(participants):
            raise ValueError("action feedback may contain only participants")
        self._previous = _encode(feedback)
        self._prefix.append(self._previous)
        self._time += 1
        self._pending = None
