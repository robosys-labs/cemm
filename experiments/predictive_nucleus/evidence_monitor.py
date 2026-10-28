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
from types import MappingProxyType
from typing import Mapping

from .uncertainty import forecast_signature


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
    change_point_log_e_value: float | None = None
    change_point_alarm: bool = False


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
        # The calibration and threshold are part of the pre-outcome contract.
        self._source_error_rates = MappingProxyType(dict(source_error_rates))
        self._alpha = alpha
        self.time = start_time
        self.log_e_value = 0.0
        self.change_point_log_e_value = 0.0
        self._pending = None
        self.receipts: dict[str, EvidenceJudgement] = {}
        self._signatures: dict[str, tuple] = {}
        self._receipt_forecasts: dict[str, tuple] = {}
        self._seen_sensor_event: set[tuple[str, int]] = set()
        self.history: list[EvidenceJudgement] = []

    @property
    def source_error_rates(self):
        return self._source_error_rates

    @property
    def alpha(self):
        return self._alpha

    @property
    def pending(self):
        """Inspection copy: callers cannot mutate the committed forecast."""
        return deepcopy(self._pending)

    @property
    def last_observation_signature(self):
        if not self.history:
            return None
        return self._signatures[self.history[-1].evidence_id]

    @property
    def last_forecast_signature(self):
        if not self.history:
            return None
        return self._receipt_forecasts[self.history[-1].evidence_id]

    @staticmethod
    def _validate_states(forecast, ids, message):
        try:
            states = forecast.states
            if not states or any(
                type(h) is not int or h not in (0, 1) or
                not isinstance(bits, tuple) or len(bits) != len(ids) or
                any(type(bit) is not int or bit not in (0, 1) for bit in bits) or
                type(weight) not in (int, float) or not isfinite(weight) or not 0 <= weight <= 1
                for (h, bits), weight in states.items()
            ) or abs(fsum(states.values()) - 1) > 1e-6:
                raise ValueError(message)
        except (AttributeError, TypeError, OverflowError, ValueError) as exc:
            raise ValueError(message) from exc

    def commit(self, forecast, *, source_id: str, next_time: int,
               intended_sensor_ids: tuple[str, ...], alternative_forecast=None):
        """Reserve sensor coverage BEFORE any outcome is observed."""
        if self._pending is not None:
            raise RuntimeError("must receive committed sensor event first")
        if source_id not in self.source_error_rates:
            raise ValueError("unreviewed sensor source")
        if next_time != self.time + 1 or type(next_time) is not int:
            raise ValueError("non-sequential future event")
        ids = tuple(forecast.state_probability)
        if not (3 <= len(ids) <= 6 and len(set(ids)) == len(ids) and
                all(isinstance(key, str) and key for key in ids)):
            raise ValueError("forecast identity scope invalid")
        selected = tuple(intended_sensor_ids)
        if not selected or len(set(selected)) != len(selected) or any(key not in ids for key in selected):
            raise ValueError("invalid precommitted coverage")
        if (source_id, next_time) in self._seen_sensor_event:
            raise ValueError("repeated physical sensor event")
        self._validate_states(forecast, ids, "invalid joint predictive distribution")
        # Ensure the eventual evidence receipt can carry an immutable binding
        # before accepting the forecast, rather than failing after feedback.
        forecast_signature(forecast)
        if alternative_forecast is not None:
            if tuple(alternative_forecast.state_probability) != ids:
                raise ValueError("alternate prediction identity scope must match")
            self._validate_states(alternative_forecast, ids, "alternate predictive distribution invalid")
        self._pending = (deepcopy(forecast), ids, source_id, next_time, selected,
                         deepcopy(alternative_forecast))

    def observe(self, observation: dict, *, evidence_id: str, source_id: str) -> EvidenceJudgement:
        if not isinstance(evidence_id, str) or not evidence_id:
            raise ValueError("nonempty evidence ID required")
        if (not isinstance(observation, dict) or type(observation.get("t")) is not int or
                observation["t"] < 0 or not isinstance(observation.get("measurements"), list)):
            raise ValueError("malformed observation envelope")
        observed = observation["measurements"]
        if not isinstance(observed, list) or not all(isinstance(m, dict) and set(m) == {"id", "bit"}
                                                       and isinstance(m["id"], str)
                                                       and type(m["bit"]) is int and m["bit"] in (0, 1)
                                                       for m in observed):
            raise ValueError("malformed observation")
        signature = (source_id, observation.get("t"), tuple(sorted((m["id"], m["bit"]) for m in observed)))
        if evidence_id in self.receipts:
            if self._signatures[evidence_id] != signature:
                raise ValueError("evidence ID was reused with different content")
            if self._pending is not None:
                raise RuntimeError("stale replay against pending future evidence")
            return self.receipts[evidence_id]
        if self._pending is None:
            raise RuntimeError("unsolicited observation without committed forecast")
        forecast, ids, expected_source, next_time, coverage, alternative = self._pending
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
        if alternative is not None:
            alt_likelihood = 0.0
            for (_, bits), weight in alternative.states.items():
                emission = weight
                for m in observed:
                    emission *= 1 - epsilon if bits[ids.index(m["id"])] == m["bit"] else epsilon
                alt_likelihood += emission
            if model_probability == 0:
                ratio_log = float("inf") if alt_likelihood > 0 else 0.0
            elif alt_likelihood == 0:
                ratio_log = float("-inf")
            else:
                ratio_log = log(alt_likelihood) - log(model_probability)
            # A zero e-value is absorbing. In particular, do not turn
            # -inf + inf into NaN when a later outcome is impossible under p.
            # The latter has null probability zero; the generic process still
            # flags it. An already infinite e-value also remains infinite.
            if isfinite(self.change_point_log_e_value):
                self.change_point_log_e_value += ratio_log
        else:
            alt_likelihood = None
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
                                   len(coverage) - len(observed), tuple(likelihoods),
                                   self.change_point_log_e_value if alternative is not None else None,
                                   bool(alternative is not None and
                                        self.change_point_log_e_value >= log(1.0 / self.alpha)))
        self._pending = None
        self.time = next_time
        self._seen_sensor_event.add((source_id, next_time))
        self.receipts[evidence_id] = result
        self._signatures[evidence_id] = signature
        self._receipt_forecasts[evidence_id] = forecast_signature(forecast)
        self.history.append(result)
        return result
