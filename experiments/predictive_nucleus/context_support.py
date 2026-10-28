"""Observed state-action coverage for a single experimental episode.

This is a conservative eligibility signal, not a model of world physics.
Only received sensor readings can supply a context or its outcome. Contexts
are shared across same-kind participants and preserve ordered action slots.
"""
from __future__ import annotations

from collections import Counter


class ObservedContextSupport:
    def __init__(self, verified_anchor: dict):
        if type(verified_anchor.get("t")) is not int or verified_anchor["t"] < 0:
            raise ValueError("invalid anchor time")
        measurements = verified_anchor.get("measurements")
        if not isinstance(measurements, list) or not 3 <= len(measurements) <= 6:
            raise ValueError("verified anchor requires 3-6 measurements")
        readings = self._validate_measurements(measurements)
        self.ids = tuple(sorted(readings))
        self.time = verified_anchor["t"]
        self._known = readings
        self._contexts = Counter()
        self._receipts = {}
        self.pending = None

    @staticmethod
    def _validate_measurements(measurements):
        readings = {}
        for m in measurements:
            if (not isinstance(m, dict) or set(m) != {"id", "bit"} or
                    not isinstance(m["id"], str) or not m["id"] or
                    type(m["bit"]) is not int or m["bit"] not in (0, 1) or m["id"] in readings):
                raise ValueError("invalid or duplicate sensor measurement")
            readings[m["id"]] = m["bit"]
        return readings

    def _action(self, action):
        if not isinstance(action, dict) or set(action) - {"kind", "participants", "value"}:
            raise ValueError("invalid action")
        kind = action.get("kind")
        participants = action.get("participants")
        if not isinstance(participants, (tuple, list)) or any(p not in self.ids for p in participants):
            raise ValueError("invalid action participants")
        ids = tuple(participants)
        value = action.get("value")
        if kind == "contact" and (len(ids) != 2 or ids[0] == ids[1] or value is not None):
            raise ValueError("contact requires two distinct ordered participants")
        if kind == "set" and (len(ids) != 1 or type(value) is not int or value not in (0, 1)):
            raise ValueError("set requires one participant and binary value")
        if kind == "observe" and (ids or value is not None):
            raise ValueError("observe has no operands")
        if kind not in ("contact", "set", "observe"):
            raise ValueError("unreviewed action kind")
        return kind, ids, value

    def assess(self, action: dict) -> dict:
        if self.pending is not None:
            raise RuntimeError("cannot assess before committed feedback")
        kind, participants, _ = self._action(action)
        if kind != "contact":
            return {"supported": False, "status": "UNSUPPORTED_ACTION", "observed_events": 0}
        if any(name not in self._known for name in participants):
            return {"supported": False, "status": "UNOBSERVED_INPUT", "observed_events": 0}
        signature = (kind, tuple(self._known[name] for name in participants))
        count = self._contexts[signature]
        return {"supported": count > 0, "status": "OBSERVED_CONTEXT" if count else "UNTESTED_CONTEXT",
                "observed_events": count}

    def commit_action(self, action: dict, *, intended_sensor_ids, next_time: int):
        if self.pending is not None:
            raise RuntimeError("previous feedback is still pending")
        if type(next_time) is not int or next_time != self.time + 1:
            raise ValueError("non-sequential action time")
        kind, participants, value = self._action(action)
        coverage = tuple(intended_sensor_ids)
        if not coverage or len(set(coverage)) != len(coverage) or any(x not in self.ids for x in coverage):
            raise ValueError("invalid precommitted sensor coverage")
        # Snapshot only directly observed pre-action readings, never belief MAP,
        # hidden state, simulator family, or the as-yet-unseen outcome.
        signature = None
        if kind == "contact" and all(x in self._known for x in participants):
            signature = (kind, tuple(self._known[x] for x in participants))
        self.pending = (kind, participants, value, coverage, next_time, signature)

    def receive(self, observation: dict, evidence_id: str):
        if not isinstance(evidence_id, str) or not evidence_id:
            raise ValueError("evidence ID required")
        measurements = observation.get("measurements")
        if not isinstance(measurements, list):
            raise ValueError("invalid sensor observation")
        readings = self._validate_measurements(measurements)
        signature = (observation.get("t"), tuple(sorted(readings.items())))
        if evidence_id in self._receipts:
            if self._receipts[evidence_id] != signature:
                raise ValueError("conflicting evidence ID")
            if self.pending is not None:
                raise RuntimeError("stale replay while later feedback is pending")
            return
        if self.pending is None:
            raise RuntimeError("no matching precommitted action")
        kind, participants, _, coverage, expected_time, observed_context = self.pending
        if type(observation.get("t")) is not int or observation["t"] != expected_time:
            raise ValueError("feedback time mismatch")
        if any(name not in coverage for name in readings):
            raise ValueError("feedback outside precommitted coverage")
        if kind == "contact" and observed_context is not None and all(p in readings for p in participants):
            self._contexts[observed_context] += 1
        # The declared sandbox contract assumes physical effects are confined
        # to action participants. Their earlier measurements expire on action;
        # a dropout is not an observation. Other IDs retain their last reading.
        for name in participants:
            self._known.pop(name, None)
        self._known.update(readings)
        self.time = expected_time
        self._receipts[evidence_id] = signature
        self.pending = None
