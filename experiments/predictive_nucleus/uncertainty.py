"""Bounded exact belief over coherent worlds and *learned* mechanism alternatives.

Kernel probabilities come only from learned model weights; this filter contains
no physics, parity rule or oracle access. It preserves a single latent hypothesis
across repeated predictions and never promotes a forecast into an observation.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import product
from math import isfinite, log2
from typing import Protocol


def entropy(weights):
    return -sum(p * log2(p) for p in weights if p > 0)


class ProbKernel(Protocol):
    def contact(self, a: int, b: int, hypothesis: int) -> tuple[float, float, float, float]: ...
    def intervention(self, previous: int, value: int) -> tuple[float, float]: ...


@dataclass(frozen=True)
class Forecast:
    action: tuple
    states: dict[tuple[int, tuple[int, ...]], float]
    state_probability: dict[str, float]
    full_world_certainty: float
    mechanism_entropy: float
    expected_info_gain: float


@dataclass(frozen=True)
class EvidenceResult:
    status: str
    observed_probability: float
    best_hypothesis_likelihood: float
    mechanism_entropy: float
    evidence_id: str


class EvidenceBelief:
    """Inference bounded to 2 mechanisms x 2^n state vectors (n<=6).

    All input is learner-visible. A mechanism label is only an anonymous index;
    it is NOT an oracle orientation or a true interpretation label.
    """

    def __init__(self, kernel: ProbKernel, observation: dict, *, sensor_error_rate: float = 0.0):
        measurements = observation["measurements"]
        ids = [m["id"] for m in measurements]
        if not (3 <= len(ids) <= 6 and len(ids) == len(set(ids))):
            raise ValueError("initial observation needs 3-6 distinct entity IDs")
        if any(type(m["bit"]) is not int or m["bit"] not in (0, 1) for m in measurements):
            raise ValueError("nonbinary sensor reading")
        self.ids = tuple(sorted(ids))
        bits = tuple(next(m["bit"] for m in measurements if m["id"] == key) for key in self.ids)
        self.mass = {(0, bits): 0.5, (1, bits): 0.5}
        # Initial full observation is a verified starting anchor. Later readings
        # use a declared, independently calibrated symmetric sensor channel.
        # This reliability is supplied instrument metadata, never user text.
        if type(sensor_error_rate) not in (int, float) or not isfinite(sensor_error_rate) or not 0 <= sensor_error_rate < 0.5:
            raise ValueError("sensor error probability must be in [0, 0.5)")
        self.sensor_error_rate = float(sensor_error_rate)
        self.kernel = kernel
        self.t = observation["t"]
        self.pending: Forecast | None = None
        self.receipts: dict[str, EvidenceResult] = {}
        self.receipt_payloads: dict[str, tuple] = {}
        self.observed_evidence = [(self.t, tuple(sorted((m["id"], m["bit"]) for m in measurements)))]
        self.last_diagnostic = "INSUFFICIENT_EVIDENCE"

    def _normalized_action(self, action: dict) -> tuple:
        if set(action) - {"kind", "participants", "value"}:
            raise ValueError("unreviewed action features")
        kind = action["kind"]
        ids = tuple(action.get("participants", ()))
        if any(name not in self.ids for name in ids):
            raise ValueError("unrecognized action participant")
        value = action.get("value")
        if kind == "contact" and (len(ids) != 2 or value is not None):
            raise ValueError("contact needs exactly two ordered participants")
        if kind == "set" and (len(ids) != 1 or type(value) is not int or value not in (0, 1)):
            raise ValueError("set needs a target and bit")
        if kind == "observe" and (ids or value is not None):
            raise ValueError("observe has no participants or value")
        if kind not in ("contact", "set", "observe"):
            raise ValueError("unsupported action")
        return (kind, ids, value)

    def mechanism_masses(self, distribution=None):
        distribution = self.mass if distribution is None else distribution
        by_hypothesis = [0.0, 0.0]
        for (h, _), weight in distribution.items():
            by_hypothesis[h] += weight
        return tuple(by_hypothesis)

    def _transitions(self, state: tuple[int, ...], h: int, action: tuple):
        kind, ids, value = action
        if kind == "observe":
            yield state, 1.0
            return
        i = self.ids.index(ids[0])
        if kind == "set":
            probabilities = self.kernel.intervention(state[i], value)
            for new_bit, probability in enumerate(probabilities):
                new = list(state)
                new[i] = new_bit
                yield tuple(new), probability
            return
        j = self.ids.index(ids[1])
        probs = self.kernel.contact(state[i], state[j], h)
        if len(probs) != 4:
            raise ValueError("kernel must predict four joint pair outcomes")
        for k, probability in enumerate(probs):
            new = list(state)
            new[i], new[j] = k // 2, k % 2
            if i == j:
                raise ValueError("self-contact requires a separately learned contract")
            yield tuple(new), probability

    def preview(self, action: dict, sensor_ids: tuple[str, ...] | None = None) -> Forecast:
        return self._preview_with_mass(action, sensor_ids, self.mass)

    def _preview_with_mass(self, action: dict, sensor_ids, masses) -> Forecast:
        if self.pending is not None:
            raise RuntimeError("cannot preview past an undelivered observation")
        normalized = self._normalized_action(action)
        predicted = defaultdict(float)
        for (h, state), weight in masses.items():
            for next_state, probability in self._transitions(state, h, normalized):
                if not isfinite(probability) or probability < 0 or probability > 1:
                    raise ValueError("invalid kernel probability")
                predicted[(h, next_state)] += weight * probability
        total = sum(predicted.values())
        if abs(total - 1) > 1e-6:
            raise ValueError("predictive mass not normalized")
        if len(predicted) > 128:
            raise ValueError("world belief exceeds 2*2^6 states")
        predicted = {k: v / total for k, v in predicted.items() if v > 0}
        marginals = {name: sum(w for (_, bits), w in predicted.items() if bits[idx])
                     for idx, name in enumerate(self.ids)}
        full = defaultdict(float)
        for (_, bits), w in predicted.items():
            full[bits] += w
        ids = self.ids if sensor_ids is None else sensor_ids
        if len(set(ids)) != len(ids) or any(n not in self.ids for n in ids):
            raise ValueError("invalid hypothetical sensor coverage")
        by_outcome = defaultdict(lambda: [0.0, 0.0])
        for (h, bits), weight in predicted.items():
            truth = tuple(bits[self.ids.index(n)] for n in ids)
            # Probe value comes from future *sensor readings*, not inaccessible
            # oracle state. Account for independent instrument bit errors.
            readings = (truth,) if self.sensor_error_rate == 0 else product((0, 1), repeat=len(ids))
            for seen in readings:
                weight_seen = weight
                for actual, observed in zip(truth, seen):
                    weight_seen *= (1 - self.sensor_error_rate) if actual == observed else self.sensor_error_rate
                by_outcome[seen][h] += weight_seen
        h_before = entropy(self.mechanism_masses(masses))
        h_after = 0.0
        for masses in by_outcome.values():
            total_mass = sum(masses)
            h_after += total_mass * entropy([x / total_mass for x in masses])
        ig = max(0., h_before - h_after)
        return Forecast(normalized, predicted, marginals, max(full.values()), h_before, ig)

    def choose_probe(self, candidates: list[dict], cost: float = 0.0, sensor_ids=None,
                     min_gain: float = 1e-4, interventions: list[dict] | None = None):
        """Read-only information-gain plan; optional bounded two-step preparation.

        A set intervention can prepare an otherwise zero-information world for a
        subsequent contact. We plan through its *learned* predicted state and
        recompute after real feedback, never mutate/presume the outcome. The
        result is a proposal, not an authorized external effect.
        """
        if self.pending is not None:
            raise RuntimeError("action has not received sensor feedback")
        if not candidates:
            raise ValueError("no candidate actions")
        # Experimental sensor geometry: an action may reveal only its chosen
        # participant handles. Planner must not optimize oracle-wide coverage
        # when the intended instrument observes a smaller physical scope.
        def coverage(candidate):
            return tuple(candidate["participants"]) if sensor_ids == "participants" else sensor_ids

        scored = [(self.preview(c, coverage(c)).expected_info_gain, i, c)
                  for i, c in enumerate(candidates)]
        gain, _, action = max(scored, key=lambda x: (x[0], -x[1]))
        if gain > max(min_gain, cost):
            return {"action": action, "expected_info_gain_bits": gain,
                    "query_cost": cost, "reason": "INFORMATIVE_PROBE"}
        best = (0.0, None)
        for intervention in interventions or []:
            if self._normalized_action(intervention)[0] != "set":
                raise ValueError("preparation must be an explicit physical set intervention")
            setup = self.preview(intervention)
            future_gain = max(self._preview_with_mass(c, coverage(c), setup.states).expected_info_gain
                              for c in candidates)
            if future_gain > best[0]:
                best = (future_gain, intervention)
        if best[1] is not None and best[0] > max(min_gain, 2 * cost):
            return {"action": best[1], "expected_info_gain_bits": best[0],
                    "query_cost": 2 * cost, "reason": "PREPARE_INTERVENTION"}
        return {"action": None, "expected_info_gain_bits": gain,
                "query_cost": cost, "reason": "NO_DISCRIMINATING_PROBE"}

    def assess(self, action: dict, min_complete_world_confidence: float = .95) -> dict:
        """No oracle: classify evidence sufficiency for THIS future action only."""
        if not (0 < min_complete_world_confidence <= 1):
            raise ValueError("invalid decision confidence")
        prediction = self.preview(action)
        if self.last_diagnostic in ("MODEL_MISMATCH_CANDIDATE", "CONFLICTING_EVIDENCE"):
            status = self.last_diagnostic
        elif prediction.full_world_certainty >= min_complete_world_confidence:
            status = "PREDICT_WITH_EVIDENCE"
        elif prediction.expected_info_gain >= .01:
            status = "INSUFFICIENT_EVIDENCE"
        else:
            status = "ABSTAIN_UNRESOLVED"
        return {"status": status, "abstain": status != "PREDICT_WITH_EVIDENCE",
                "max_full_world_probability": prediction.full_world_certainty,
                "orientation_entropy": prediction.mechanism_entropy,
                "expected_info_gain_bits": prediction.expected_info_gain}

    def commit_action(self, action: dict) -> Forecast:
        outcome = self.preview(action)
        self.pending = outcome
        return outcome

    def receive(self, observation: dict, evidence_id: str, mismatch_limit: float = 0.03) -> EvidenceResult:
        if not isinstance(evidence_id, str) or not evidence_id:
            raise ValueError("source/evidence ID required")
        signature = (observation.get("t"), tuple(sorted((m["id"], m["bit"]) for m in observation.get("measurements", []))))
        if evidence_id in self.receipts:
            if self.receipt_payloads[evidence_id] != signature:
                raise ValueError("conflicting payload reused an evidence ID")
            if self.pending is not None:
                raise RuntimeError("stale duplicate against a newer pending step")
            return self.receipts[evidence_id]
        if self.pending is None or observation["t"] != self.t + 1:
            raise RuntimeError("observation has no matching pending action")
        records = observation["measurements"]
        if len(set(m["id"] for m in records)) != len(records):
            raise ValueError("duplicate observation entity")
        if any(m["id"] not in self.ids or type(m["bit"]) is not int or m["bit"] not in (0, 1)
               for m in records):
            raise ValueError("invalid observed entity/bit")
        evidence = {self.ids.index(m["id"]): m["bit"] for m in records}
        # Soft conditioning preserves possible worlds after an instrument
        # error. At error_rate=0 this exactly matches the original hard filter.
        remaining = {}
        for key, weight in self.pending.states.items():
            _, bits = key
            emission = 1.0
            for i, observed in evidence.items():
                emission *= (1 - self.sensor_error_rate) if bits[i] == observed else self.sensor_error_rate
            if weight * emission:
                remaining[key] = weight * emission
        likelihood = sum(remaining.values())
        by_hypothesis = self.mechanism_masses(self.pending.states)
        matched_hypothesis = [sum(w for (z, _), w in remaining.items() if z == h) for h in (0, 1)]
        conditional = [matched_hypothesis[h] / by_hypothesis[h] if by_hypothesis[h] else 0.0
                       for h in (0, 1)]
        best = max(conditional)
        if not evidence:
            status = "NO_NEW_EVIDENCE"
            self.mass = self.pending.states
        elif likelihood < 1e-15:
            status = "MODEL_MISMATCH_CANDIDATE"
            self.mass = self.pending.states
        else:
            self.mass = {k: w / likelihood for k, w in remaining.items()}
            if best < mismatch_limit:
                status = "MODEL_MISMATCH_CANDIDATE"
            elif likelihood < mismatch_limit:
                status = "CONFLICTING_EVIDENCE"
            elif entropy(self.mechanism_masses()) >= 0.2:
                status = "INSUFFICIENT_EVIDENCE"
            else:
                status = "EVIDENCE_SUPPORTED"
        self.pending = None
        self.t += 1
        result = EvidenceResult(status, likelihood, best, entropy(self.mechanism_masses()), evidence_id)
        self.receipts[evidence_id] = result
        self.receipt_payloads[evidence_id] = signature
        self.observed_evidence.append(signature)
        self.last_diagnostic = status
        return result
