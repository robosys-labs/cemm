"""Prequential evidence-adequacy test over bounded joint-world forecasts.

The monitor tests forecasts, not an oracle-defined transition rule. It operates on
already committed, learner-visible forecasts and an externally specified sensor
error model. A threshold crossing is evidence AGAINST that probabilistic model,
not proof of changed physical laws or permission to alter the production runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from math import fsum, isfinite, log
from typing import Mapping


@dataclass(frozen=True)
class EvidenceJudgement:
    status: str
    evidence_id: str
    source_id: str
    observed_likelihood: float
    reference_likelihood: float
    log_e_value: float
    alarm: bool
    observed_bits: int
    missing_bits: int
    conditional_hypothesis_likelihood: tuple[float, float]


class PredictiveAdequacyMonitor:
    """Anytime-valid likelihood-ratio monitor under stated sensor assumptions.

    For a frozen, calibrated conditional forecast p_t, use a fixed reference
    q_t(y)=2**(-observed_bits). The product of q_t(Y_t)/p_t(Y_t) is an e-process
    if forecasts and declared sensor error rates are correct. Ville's bound
    controls probability of *ever* crossing 1/alpha, despite adaptive probes.
    This guarantee DOES NOT survive misspecified noise or outcome-dependent
    sensor selection. Sensors are selected before seeing their values.
    """

    def __init__(self, source_error_rates: Mapping[str, float], alpha: float = 0.05,
                 start_time: int = 0):
        if type(start_time) is not int or start_time < 0:
            raise ValueError("invalid starting time")
        if not (0 < alpha < 1) or not isfinite(alpha):
            raise ValueError("invalid alarm level")
        if not source_error_rates or any(
            not isinstance(source, str) or not source or
            type(error) not in (float, int) or not isfinite(error) or not 0 <= error < 0.5
            for source, error in source_error_rates.items()
        ):
            raise ValueError("source-specific sensor calibration required")
        self.source_error_rates = dict(source_error_rates)
        self.alpha = alpha
        self.time = start_time
        self.log_e_value = 0.0
        self.pending = None
        self.receipts: dict[str, EvidenceJudgement] = {}
        self._signatures: dict[str, tuple] = {}
        self._seen_sensor_event: set[tuple[str, int]] = set()
        self.history: list[EvidenceJudgement] = []

    def commit(self, forecast, *, source_id: str, next_time: int,
               intended_sensor_ids: tuple[str, ...]):
        """Reserve sensor coverage BEFORE any outcome is observed."""
        if self.pending is not None:
            raise RuntimeError("must receive committed sensor event first")
        if source_id not in self.source_error_rates:
            raise ValueError("unreviewed sensor source")
        if next_time != self.time + 1 or type(next_time) is not int:
            raise ValueError("non-sequential future event")
        ids = tuple(forecast.state_probability)
        if not (3 <= len(ids) <= 6 and len(set(ids)) == len(ids)):
            raise ValueError("forecast identity scope invalid")
        selected = tuple(intended_sensor_ids)
        if not selected or len(set(selected)) != len(selected) or any(key not in ids for key in selected):
            raise ValueError("invalid precommitted coverage")
        if (source_id, next_time) in self._seen_sensor_event:
            raise ValueError("repeated physical sensor event")
        total = fsum(forecast.states.values())
        if abs(total - 1) > 1e-6 or not all(isfinite(w) and 0 <= w <= 1 for w in forecast.states.values()):
            raise ValueError("invalid joint predictive distribution")
        if any(h not in (0, 1) or len(bits) != len(ids) or any(bit not in (0, 1) for bit in bits)
               for (h, bits) in forecast.states):
            raise ValueError("invalid joint state or latent alternative")
        self.pending = (deepcopy(forecast), ids, source_id, next_time, selected)

    def observe(self, observation: dict, *, evidence_id: str, source_id: str) -> EvidenceJudgement:
        if not isinstance(evidence_id, str) or not evidence_id:
            raise ValueError("nonempty evidence ID required")
        observed = observation.get("measurements", [])
        if not isinstance(observed, list) or not all(isinstance(m, dict) and set(m) == {"id", "bit"}
                                                       and isinstance(m["id"], str)
                                                       and type(m["bit"]) is int and m["bit"] in (0, 1)
                                                       for m in observed):
            raise ValueError("malformed observation")
        signature = (source_id, observation.get("t"), tuple(sorted((m["id"], m["bit"]) for m in observed)))
        if evidence_id in self.receipts:
            if self._signatures[evidence_id] != signature:
                raise ValueError("evidence ID was reused with different content")
            if self.pending is not None:
                raise RuntimeError("stale replay against pending future evidence")
            return self.receipts[evidence_id]
        if self.pending is None:
            raise RuntimeError("unsolicited observation without committed forecast")
        forecast, ids, expected_source, next_time, coverage = self.pending
        if source_id != expected_source or observation.get("t") != next_time:
            raise ValueError("sensor source/time does not match precommitment")
        if (source_id, next_time) in self._seen_sensor_event:
            raise ValueError("physical event replayed under new evidence ID")
        if (len(set(m["id"] for m in observed)) != len(observed) or
            any(m["id"] not in coverage or type(m["bit"]) is not int or m["bit"] not in (0, 1)
                for m in observed)):
            raise ValueError("sensor values/coverage invalid")
        epsilon = self.source_error_rates[source_id]
        likelihoods = [0.0, 0.0]
        for (h, bits), mass in forecast.states.items():
            conditional = mass
            for m in observed:
                truth = bits[ids.index(m["id"])]
                conditional *= 1 - epsilon if truth == m["bit"] else epsilon
            likelihoods[h] += conditional
        model_probability = fsum(likelihoods)
        reference = 0.5 ** len(observed)
        if model_probability < 0 or model_probability > 1 + 1e-6:
            raise ValueError("non-probabilistic learned forecast")
        # With a purportedly perfect sensor, an impossible outcome produces
        # infinite log evidence against the supplied predictive model.
        self.log_e_value += (log(reference) - log(model_probability)) if model_probability else float("inf")
        alarm = self.log_e_value >= log(1.0 / self.alpha)
        if not observed:
            status = "NO_EVIDENCE"
        elif alarm:
            status = "MODEL_MISMATCH_EVIDENCE"
        elif model_probability < 0.03:
            status = "SURPRISING_BUT_UNCONFIRMED"
        else:
            status = "OBSERVATION_COMPATIBLE"
        result = EvidenceJudgement(status, evidence_id, source_id, model_probability,
                                   reference, self.log_e_value, alarm, len(observed),
                                   len(coverage) - len(observed), tuple(likelihoods))
        self.pending = None
        self.time = next_time
        self._seen_sensor_event.add((source_id, next_time))
        self.receipts[evidence_id] = result
        self._signatures[evidence_id] = signature
        self.history.append(result)
        return result
