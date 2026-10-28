"""Observed state-action coverage for a single experimental episode.

This is a conservative eligibility signal, not a model of world physics.
Only received sensor readings can supply a context or its outcome. Contexts
are shared across same-kind participants and preserve ordered action slots.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from math import fsum, isfinite


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
        self._anchor_signature = (self.time, tuple(sorted(readings.items())))
        self._known = readings
        self._contexts = Counter()
        self._receipts = {}
        self._action_history = []
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

    def assess_posterior(self, action: dict, belief) -> dict:
        """Measure current joint-belief mass whose input contexts were observed.

        This is an opt-in diagnostic: it does not alter the v6 raw-reading
        assessment, mutate belief, choose a threshold, or certify calibration.
        A high fraction means only that the *model's* current distribution
        places mass on contexts recorded from completed sensor events. It does
        not establish that the belief, sensors, or transition law are correct.
        """
        if self.pending is not None:
            raise RuntimeError("cannot assess before committed context feedback")
        kind, participants, _ = self._action(action)
        if kind != "contact":
            raise ValueError("posterior context assessment requires a contact")
        if getattr(belief, "pending", None) is not None:
            raise RuntimeError("cannot assess before committed belief feedback")
        belief_ids = getattr(belief, "ids", None)
        if not isinstance(belief_ids, tuple) or belief_ids != self.ids:
            raise ValueError("context and belief identity scope/order must match")
        if type(getattr(belief, "t", None)) is not int or belief.t != self.time:
            raise ValueError("context and belief time must match")
        expected_history = (self._anchor_signature, *self._receipts.values())
        history = getattr(belief, "observed_evidence", None)
        if not isinstance(history, (list, tuple)) or tuple(history) != expected_history:
            raise ValueError("context and belief sensor histories must match")
        receipts = getattr(belief, "receipts", None)
        payloads = getattr(belief, "receipt_payloads", None)
        signature_for = getattr(belief, "receipt_forecast_signature", None)
        if not isinstance(receipts, Mapping) or not isinstance(payloads, Mapping) or not callable(signature_for):
            raise ValueError("belief lacks committed action provenance")
        ids = tuple(receipts)
        if tuple(payloads.get(key) for key in ids) != expected_history[1:]:
            raise ValueError("context and belief receipt histories must match")
        signatures = [signature_for(key) for key in ids]
        if (any(not isinstance(s, tuple) or len(s) != 3 or s[0] != self.ids for s in signatures) or
                tuple(s[1] for s in signatures) != tuple(self._action_history)):
            raise ValueError("context and belief committed action histories must match")
        masses = getattr(belief, "mass", None)
        if not isinstance(masses, Mapping) or not masses:
            raise ValueError("invalid joint belief distribution")
        grouped = defaultdict(list)
        weights = []
        positions = tuple(self.ids.index(name) for name in participants)
        for key, weight in masses.items():
            if (not isinstance(key, tuple) or len(key) != 2 or
                    type(key[0]) is not int or key[0] not in (0, 1) or
                    not isinstance(key[1], tuple) or len(key[1]) != len(self.ids) or
                    any(type(bit) is not int or bit not in (0, 1) for bit in key[1]) or
                    type(weight) not in (int, float) or not 0 <= weight <= 1 or not isfinite(weight)):
                raise ValueError("invalid joint belief distribution")
            weights.append(weight)
            if weight:
                grouped[tuple(key[1][position] for position in positions)].append(weight)
        total = fsum(weights)
        if not isfinite(total) or abs(total - 1.0) > 1e-9:
            raise ValueError("joint belief distribution must be normalized")
        contexts = []
        observed_weights, unobserved_weights = [], []
        for bits, group in sorted(grouped.items()):
            mass = fsum(group) / total
            count = self._contexts[(kind, bits)]
            contexts.append({"input_bits": list(bits), "posterior_mass": mass,
                             "observed_events": count})
            (observed_weights if count else unobserved_weights).append(mass)
        observed_mass, unobserved_mass = fsum(observed_weights), fsum(unobserved_weights)
        status = ("NO_OBSERVED_CONTEXT_MASS" if observed_mass == 0 else
                  "ALL_OBSERVED_CONTEXT_MASS" if unobserved_mass == 0 else
                  "PARTIAL_OBSERVED_CONTEXT_MASS")
        return {"status": status, "observed_context_mass": observed_mass,
                "unobserved_context_mass": unobserved_mass, "contexts": contexts}

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
        kind, participants, value, coverage, expected_time, observed_context = self.pending
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
        self._action_history.append((kind, participants, value))
        self.pending = None
