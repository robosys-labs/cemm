"""Public sequential inference smoke test, not a causal training pipeline.

The public evaluator and this in-process driver's snapshots are inspectable by
Python callbacks. Ordering and copying are cooperative interface checks, not
security isolation, independent custody, event authentication or G1 evidence.
Current model fitting remains offline; no gradients or scores are produced.
"""
from __future__ import annotations

import inspect
import json
import threading

from .flat_data import event_features, initial_ids, readings
from .schedule_fixture import SensorEpisode


def _observation(value, time, ids=None):
    if (type(value) is not dict or set(value) != {"t", "measurements"} or
            type(value["t"]) is not int or value["t"] != time or
            type(value["measurements"]) is not list):
        raise ValueError("invalid observation envelope")
    for item in value["measurements"]:
        if (type(item) is not dict or set(item) != {"id", "bit"} or
                type(item["id"]) is not str or not item["id"] or
                type(item["bit"]) is not int or item["bit"] not in (0, 1)):
            raise ValueError("invalid sensor record")
    found = readings(value)
    if ids is not None and not set(found) <= set(ids):
        raise ValueError("unknown sensor identity")
    return found


def _snapshot(view):
    """Validate and capture only a public fixture's sensor/action records."""
    if type(view) is not SensorEpisode or len(view.actions) != 4:
        raise ValueError("expected a public four-step sensor view")
    turns, feedbacks, previous, ids = [], [], None, None
    for i in range(4):
        turn = view.learner_turn(i)
        if type(turn) is not dict or set(turn) != {"observation", "action"}:
            raise ValueError("invalid input")
        observation, action = turn["observation"], turn["action"]
        _observation(observation, i, ids)
        if i == 0:
            ids = initial_ids(observation)
            if len(ids) != 3:
                raise ValueError("invalid fixture anchor")
        elif observation != previous:
            raise ValueError("feedback/input chronology differs")
        if (type(action) is not dict or type(action.get("kind")) is not str or
                type(action.get("participants")) is not list or
                any(type(p) is not str for p in action["participants"])):
            raise ValueError("invalid action")
        kind = action["kind"]
        if ((kind == "contact" and set(action) != {"kind", "participants"}) or
                (kind == "set" and set(action) != {"kind", "participants", "value"}) or
                kind not in ("contact", "set")):
            raise ValueError("invalid action envelope")
        event_features(ids, observation, action)
        feedback = view.reveal_after_prediction(i)
        found = _observation(feedback, i + 1, ids)
        if set(found) != set(action["participants"]):
            raise ValueError("feedback must cover exactly the participants")
        turns.append(json.dumps(turn, sort_keys=True))
        feedbacks.append(json.dumps(feedback, sort_keys=True))
        previous = feedback
    # The supplied action curriculum is public and fixed, without role labels.
    actions = [json.loads(row)["action"] for row in turns]
    a, b = actions[0]["participants"] if actions[0]["kind"] == "contact" else (None, None)
    if (actions[1] != {"kind": "contact", "participants": [b, a]} or
            actions[2]["kind"] != "set" or actions[3]["kind"] != "set" or
            actions[2]["participants"] != [a] or actions[3]["participants"] != [a]):
        raise ValueError("invalid public schedule")
    return json.dumps(json.loads(turns[0])["observation"], sort_keys=True), tuple(turns), tuple(feedbacks)


class PublicReplay:
    """Single-use, cooperative, sequential two-consumer inference smoke driver.

    Consumers implement ``start(anchor)``, ``predict(turn)`` and
    ``receive(feedback)``. Both prediction callbacks must return synchronously
    before either feedback callback is invoked. Any callback exception, invalid
    consumer, awaitable return, or concurrent/reentrant call aborts the run.
    Already performed callbacks and side effects cannot be rolled back. A
    concurrent abort may race with an invocation that has already passed its
    state check; callbacks are not transactionally isolated from one another.
    """
    def __init__(self, view):
        self._anchor, self._turns, self._feedbacks = _snapshot(view)
        self._guard = threading.Lock()
        self._state = "ready"

    @property
    def state(self):
        with self._guard:
            return self._state

    def _check(self):
        with self._guard:
            if self._state != "running":
                raise RuntimeError("replay aborted")

    def _invoke(self, callback, payload):
        self._check()
        result = callback(json.loads(payload))
        if inspect.isawaitable(result) or inspect.isgenerator(result) or inspect.isasyncgen(result):
            if inspect.iscoroutine(result) or inspect.isgenerator(result):
                result.close()
            raise TypeError("callbacks must complete synchronously")
        self._check()

    def run(self, first, second):
        with self._guard:
            if self._state == "running":
                self._state = "aborted"
                raise RuntimeError("concurrent or reentrant replay")
            if self._state != "ready":
                raise RuntimeError("replay is single-use")
            self._state = "running"
        try:
            if first is second:
                raise ValueError("two distinct consumer instances required")
            callbacks = []
            for consumer in (first, second):
                methods = tuple(getattr(consumer, name, None) for name in ("start", "predict", "receive"))
                if not all(callable(method) for method in methods):
                    raise TypeError("consumer must implement start, predict and receive")
                callbacks.append(methods)
                self._check()
            for methods in callbacks:
                self._invoke(methods[0], self._anchor)
            for turn, feedback in zip(self._turns, self._feedbacks, strict=True):
                for methods in callbacks:
                    self._invoke(methods[1], turn)
                for methods in callbacks:
                    self._invoke(methods[2], feedback)
            with self._guard:
                if self._state != "running":
                    raise RuntimeError("replay aborted")
                self._state = "completed"
        except BaseException:
            with self._guard:
                self._state = "aborted"
            raise
