"""Sensor-only controls for public development, not challenge evaluation.

Persistence is a deterministic forecast over the IDs in the supplied anchor;
anchor completeness is an external assumption. It is not a calibrated joint
distribution. The empirical control predicts *local observed participant
outcomes*, not complete-world probabilities. Its table is fitted offline from
supplied histories, then frozen; it never learns from query feedback. Neither
control authenticates histories, establishes independent custody, or accesses
simulator gold. Unseen or incomplete lookup contexts explicitly abstain.
The full-anchor wrapper lifts local outcomes by assuming all nonparticipants
persist at their last readings; it does not establish that assumption.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass

from .flat_data import event_features, initial_ids, readings


def _observation(value, *, time=None, ids=None):
    if (type(value) is not dict or set(value) != {"t", "measurements"} or
            type(value["t"]) is not int or value["t"] < 0 or
            (time is not None and value["t"] != time) or
            type(value["measurements"]) is not list):
        raise ValueError("invalid sensor observation")
    for item in value["measurements"]:
        if (type(item) is not dict or set(item) != {"id", "bit"} or
                type(item["id"]) is not str or not item["id"] or
                type(item["bit"]) is not int or item["bit"] not in (0, 1)):
            raise ValueError("invalid sensor reading")
    measured = readings(value)
    if ids is not None and not set(measured) <= set(ids):
        raise ValueError("unknown sensor identity")
    return measured


def _turn(ids, turn, *, time=None):
    if type(turn) is not dict or set(turn) != {"observation", "action"}:
        raise ValueError("invalid learner turn")
    observation, action = turn["observation"], turn["action"]
    seen = _observation(observation, time=time, ids=ids)
    if (type(action) is not dict or type(action.get("participants")) is not list or
            any(type(name) is not str for name in action["participants"])):
        raise ValueError("invalid action")
    kind = action.get("kind")
    keys = {"kind", "participants", "value"} if kind == "set" else {"kind", "participants"}
    if set(action) != keys:
        raise ValueError("invalid action envelope")
    event_features(ids, observation, action)
    return seen, action


class NoChange:
    """Latest actual readings, with explicit prediction-before-feedback order."""

    def __init__(self):
        self._ids = None
        self._time = None
        self._latest = None
        self._last_observation = None
        self._pending = False

    def start(self, anchor):
        if self._pending:
            raise RuntimeError("feedback required before reset")
        seen = _observation(anchor)
        ids = initial_ids(anchor)
        self._ids, self._time = ids, anchor["t"]
        self._latest, self._last_observation = dict(seen), dict(seen)

    def preview(self, turn):
        if self._ids is None:
            raise RuntimeError("initial observation required")
        if self._pending:
            raise RuntimeError("feedback required before prediction")
        seen, _ = _turn(self._ids, turn, time=self._time)
        if seen != self._last_observation:
            raise ValueError("turn does not match latest observation")
        return {name: self._latest[name] for name in self._ids}

    def predict(self, turn):
        prediction = self.preview(turn)
        self._pending = True
        return prediction

    def receive(self, feedback):
        if not self._pending:
            raise RuntimeError("prediction required before feedback")
        seen = _observation(feedback, time=self._time + 1, ids=self._ids)
        self._latest.update(seen)
        self._last_observation = dict(seen)
        self._time += 1
        self._pending = False


def _key(action, before):
    kind, members = action["kind"], action["participants"]
    if kind == "observe" or any(name not in before for name in members):
        return None
    if kind == "contact":
        return (kind, before[members[0]], before[members[1]])
    return (kind, before[members[0]], action["value"])


@dataclass(frozen=True)
class EventMemory:
    """Frozen empirical table over ordered action-local sensor outcomes.

    Counts are immutable tuples; returned probability dicts are fresh copies.
    Full event history and entity identities are intentionally not keys. This
    is a shared relative-slot event table, not an identity-specific memorizer.
    """
    rows: tuple
    episode_count: int
    eligible_events: int

    def __post_init__(self):
        if (type(self.rows) is not tuple or type(self.episode_count) is not int or self.episode_count < 0 or
                type(self.eligible_events) is not int or self.eligible_events < 0):
            raise ValueError("invalid frozen table")
        seen_keys, total = set(), 0
        for row in self.rows:
            if type(row) is not tuple or len(row) != 2:
                raise ValueError("invalid frozen row")
            key, outcomes = row
            if (type(key) is not tuple or len(key) != 3 or type(key[0]) is not str or
                    key[0] not in ("contact", "set") or
                    any(type(bit) is not int or bit not in (0, 1) for bit in key[1:]) or
                    key in seen_keys or type(outcomes) is not tuple or not outcomes):
                raise ValueError("invalid frozen key")
            seen_keys.add(key)
            seen_outcomes = set()
            for entry in outcomes:
                if type(entry) is not tuple or len(entry) != 2:
                    raise ValueError("invalid frozen outcome")
                outcome, count = entry
                if (type(outcome) is not tuple or len(outcome) != (2 if key[0] == "contact" else 1) or
                        any(type(bit) is not int or bit not in (0, 1) for bit in outcome) or
                        outcome in seen_outcomes or type(count) is not int or count < 1):
                    raise ValueError("invalid frozen outcome")
                seen_outcomes.add(outcome)
                total += count
        if total != self.eligible_events or (total and not self.episode_count):
            raise ValueError("frozen table count mismatch")

    @classmethod
    def fit(cls, episodes):
        """Fit on caller-supplied training histories; split custody is external.

        This interface cannot independently verify partition membership,
        provenance or duplicate episodes. It is not a challenge-data guard.
        """
        counts = defaultdict(Counter)
        episode_count = eligible_events = 0
        for episode in episodes:
            if not episode.actions:
                raise ValueError("empty sensor episode")
            ids = None
            previous = None
            first_time = None
            for i in range(len(episode.actions)):
                turn = episode.learner_turn(i)
                if i == 0:
                    if type(turn) is not dict or set(turn) != {"observation", "action"}:
                        raise ValueError("invalid learner turn")
                    _observation(turn["observation"])
                    first_time = turn["observation"]["t"]
                    ids = initial_ids(turn["observation"])
                before, action = _turn(ids, turn, time=first_time + i)
                if previous is not None and before != previous:
                    raise ValueError("sensor timeline is inconsistent")
                feedback = episode.reveal_after_prediction(i)
                after = _observation(feedback, time=first_time + i + 1, ids=ids)
                key = _key(action, before)
                members = action["participants"]
                if key is not None and all(name in after for name in members):
                    outcome = tuple(after[name] for name in members)
                    counts[key][outcome] += 1
                    eligible_events += 1
                previous = after
            episode_count += 1
        rows = tuple((key, tuple(sorted(outcomes.items()))) for key, outcomes in sorted(counts.items()))
        return cls(rows, episode_count, eligible_events)

    def predict(self, ids, turn):
        """Return local empirical probabilities or explicit abstention.

        Observation history is not updated; the caller supplies each current
        sensor-only turn. Rates are unsmoothed frequencies, not calibrated.
        """
        if (type(ids) is not tuple or not 3 <= len(ids) <= 6 or
                any(type(name) is not str or not name for name in ids) or len(set(ids)) != len(ids)):
            raise ValueError("invalid known identities")
        before, action = _turn(ids, turn)
        if action["kind"] == "observe":
            return {"status": "ABSTAIN", "reason": "UNSUPPORTED_ACTION", "probabilities": None}
        key = _key(action, before)
        if key is None:
            return {"status": "ABSTAIN", "reason": "INCOMPLETE_CONTEXT", "probabilities": None}
        for candidate, outcomes in self.rows:
            if candidate == key:
                total = sum(count for _, count in outcomes)
                return {"status": "PREDICTED", "reason": None,
                        "probabilities": {outcome: count / total for outcome, count in outcomes}}
        return {"status": "ABSTAIN", "reason": "UNSEEN_CONTEXT", "probabilities": None}


class FullWorldEventMemory:
    """Lift local empirical outcomes with an explicit persistence assumption.

    The output is a joint distribution only over the IDs supplied in the
    anchor. Participant outcomes come from a frozen relative-slot event table;
    nonparticipants retain their latest actual reading, even when it is stale.
    Neither anchor completeness, persistence nor a sensor model is established
    by this control. Rates are unsmoothed and calibration is not established.
    """

    def __init__(self, memory):
        if type(memory) is not EventMemory:
            raise ValueError("expected a frozen event table")
        self._memory = memory
        self._persistence = NoChange()

    def start(self, anchor):
        self._persistence.start(anchor)

    def _forecast(self, turn):
        latest = self._persistence.preview(turn)
        ids = tuple(latest)
        local = self._memory.predict(ids, turn)
        seen = readings(turn["observation"])
        participants = turn["action"]["participants"]
        carried = tuple(name for name in ids if name not in participants)
        stale = tuple(name for name in carried if name not in seen)
        result = {"status": local["status"], "reason": local["reason"],
                  "ids": ids, "worlds": None, "carried_nonparticipants": carried,
                  "stale_nonparticipants": stale, "calibration": "NOT_ESTABLISHED"}
        if local["status"] == "PREDICTED":
            worlds = {}
            for outcome, probability in local["probabilities"].items():
                proposed = latest.copy()
                proposed.update(zip(participants, outcome))
                worlds[tuple(proposed[name] for name in ids)] = probability
            result["worlds"] = worlds
        return result

    def preview(self, turn):
        """Return a fresh forecast without advancing the feedback sequence."""
        return self._forecast(deepcopy(turn))

    def predict(self, turn):
        """Commit a forecast or abstention before accepting feedback."""
        snapshot = deepcopy(turn)
        result = self._forecast(snapshot)
        self._persistence.predict(snapshot)
        return result

    def receive(self, feedback):
        """Update last readings only; never fit the frozen event table."""
        self._persistence.receive(feedback)
