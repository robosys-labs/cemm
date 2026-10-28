"""Episode-level abstention guard for already observed forecast evidence.

This module does not alter a belief, select physical actions, or resolve the
cause of a surprise. It keeps a conflict visible for the rest of the episode
and combines two prequential e-processes with fixed equal weights.
"""
from __future__ import annotations

from math import exp, isfinite, log, log1p


def equally_weighted_log_e(first: float, second: float) -> float:
    """log((exp(first) + exp(second)) / 2), including exact zero/infinity."""
    if first != first or second != second:
        raise ValueError("NaN evidence value")
    high, low = max(first, second), min(first, second)
    if not isfinite(high):
        return high  # both -inf, or at least one +inf
    return high + log1p(exp(low - high)) - log(2.0)


class EpisodeEvidenceGuard:
    """Latch heuristic conflict and a single mixed-process statistical alarm.

    The mixture has an anytime alpha bound only when both underlying processes
    are valid under the same null and their alternatives are fixed/predictable.
    The additional conflict heuristic is *not* covered by that guarantee.
    A new episode requires a new guard; there is no automatic conflict reset.
    """

    def __init__(self, alpha: float = .05, *, start_time: int = 0):
        if type(alpha) not in (int, float) or not isfinite(alpha) or not 0 < alpha < 1:
            raise ValueError("invalid guard alpha")
        if type(start_time) is not int or start_time < 0:
            raise ValueError("invalid guard start time")
        self.alpha = float(alpha)
        self.time = start_time
        self._conflicts: set[str] = set()
        self._portfolio_alarm = False
        self.portfolio_log_e = 0.0

    def record(self, monitor, belief, belief_result):
        """Consume each finished monitor/feedback step exactly once in order."""
        if monitor.pending is not None or monitor.time != self.time + 1 or not monitor.history:
            raise ValueError("guard requires the next completed sensor event")
        source, time, readings = monitor.last_observation_signature
        if (belief.t != time or belief.receipts.get(belief_result.evidence_id) != belief_result or
                belief.receipt_payloads.get(belief_result.evidence_id) != (time, readings)):
            raise ValueError("monitor and belief must refer to the same sensor event")
        if (belief.receipt_forecast_signature(belief_result.evidence_id) != monitor.last_forecast_signature or
                belief.sensor_error_rate != monitor.source_error_rates[source]):
            raise ValueError("monitor and belief must use the same committed forecast and sensor calibration")
        mixed = equally_weighted_log_e(monitor.log_e_value, monitor.change_point_log_e_value)
        if belief_result.status in ("CONFLICTING_EVIDENCE", "MODEL_MISMATCH_CANDIDATE"):
            self._conflicts.add(belief_result.status)
        self.portfolio_log_e = mixed
        self._portfolio_alarm |= mixed >= log(1.0 / self.alpha)
        self.time = monitor.time

    @property
    def conflicts(self):
        return frozenset(self._conflicts)

    @property
    def portfolio_alarm(self):
        return self._portfolio_alarm

    @property
    def blocked(self) -> bool:
        return bool(self._conflicts) or self._portfolio_alarm
