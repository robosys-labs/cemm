"""Advisory evidence diagnostics for the active joint-log participant.

Reuse direct observed-context accounting without inventing the historical
monitor's two-hypothesis belief interface. The uniform-reference log e-process
has an anytime interpretation ONLY under correct forecasts, noiseless readings
and predictable coverage/ignorable dropout. This does not establish calibration,
authenticate sensors, diagnose a cause, or authorize a research gate.
"""
from math import exp, fsum, isfinite, log

from .domain_contract import DomainSupport, binary_worlds


VERSION = 'active-evidence-v2'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def _logsumexp(values):
    high = max(values, default=-float('inf'))
    return high if high == -float('inf') else high + log(fsum(exp(v - high) for v in values))


def _wire_log(value):
    if value is None or isfinite(value):
        return value
    return 'positive_infinity' if value > 0 else 'negative_infinity'


class ActiveEvidence:
    """One bounded transport episode; predictions never supply support counts.

    begin/bind precede feedback. preview is pure; receive commits only after
    the filter accepts the same validated observation. The session enforces its
    128-action cap and binds action/coverage/configuration into the receipt.
    """
    def __init__(self, ids, anchor, alpha=.05):
        require(type(ids) in (list, tuple) and 3 <= len(ids) <= 6 and
                all(type(x) is str and x for x in ids) and len(set(ids)) == len(ids) and
                tuple(ids) == tuple(sorted(ids)), 'three to six sorted distinct sensor IDs required')
        require(type(alpha) in (int, float) and isfinite(alpha) and 0 < alpha < 1, 'invalid evidence alpha')
        self.ids, self._alpha = tuple(ids), float(alpha)
        self._validate_observation(anchor, full=True)
        self.worlds = binary_worlds(len(self.ids))
        self.support = DomainSupport(self._envelope(anchor, 0))
        self.time, self.log_e_value, self.episode_alarm, self.scored_steps = 0, 0., False, 0
        self._pending, self._receipt = None, None

    @property
    def alpha(self):
        return self._alpha

    @property
    def contract(self):
        return {'version': VERSION, 'alpha': self.alpha, 'reference': 'uniform_visible_joint_outcome',
                'heuristic_surprise_reference_ratio': 4.,
                'sensor_noise': 0., 'coverage': 'selected_before_feedback',
                'dropout_assumption': 'predictable_or_value_independent',
                'assumptions_verified': False, 'calibration': 'NOT_ESTABLISHED', 'advisory_only': True,
                'provenance': 'logical_episode_step_receipt; not authenticated physical sensors',
                'support_scope': 'episode_observed_contact_inputs_and_aliases; supplied_participant_locality'}

    def _validate_observation(self, observation, full=False):
        require(type(observation) is dict and set(observation) == set(self.ids), 'observation ID scope mismatch')
        require(all((v is None and not full) or (type(v) is int and v in (0, 1))
                    for v in observation.values()), 'invalid evidence observation')

    def _envelope(self, observation, time):
        return {'t': time, 'measurements': [{'id': name, 'bit': observation[name]}
                for name in self.ids if observation[name] is not None]}

    def sensor_ids(self, ids):
        require(type(ids) in (tuple, list) and bool(ids) and
                all(type(x) is str and x in self.ids for x in ids) and
                len(set(ids)) == len(ids), 'invalid intended sensor IDs')
        return tuple(sorted(ids))

    def begin(self, action, logs, sensor_ids):
        require(self._pending is None, 'previous evidence feedback is pending')
        coverage = self.sensor_ids(sensor_ids)
        if logs is not None:
            require(type(logs) in (tuple, list) and len(logs) == len(self.worlds) and
                    all(v is None or (type(v) in (int, float) and
                        (isfinite(v) or v == -float('inf'))) for v in logs), 'invalid joint log forecast')
            logs = tuple(-float('inf') if v is None else float(v) for v in logs)
            total = _logsumexp(logs)
            require(isfinite(total) and abs(total) <= 1e-10, 'joint log forecast is not normalized')
        else:
            total = None
        support = self.support.assess(action)
        if support['status'] == 'UNSUPPORTED_ACTION':
            support = {'status': 'NOT_APPLICABLE', 'supported': None, 'observed_events': 0}
        self.support.commit_action(action, intended_sensor_ids=coverage, next_time=self.time + 1)
        self._pending, self._receipt = (logs, total, coverage), None
        return {'contract': self.contract, 'sensor_ids': list(coverage), 'context_support': support,
                'prediction_available': logs is not None, 'episode_alarm': self.episode_alarm,
                'log_e_value': _wire_log(self.log_e_value), 'scored_steps': self.scored_steps}

    def bind(self, receipt):
        require(self._pending is not None and self._receipt is None and type(receipt) is str and
                len(receipt) == 64 and all(c in '0123456789abcdef' for c in receipt), 'invalid evidence receipt')
        self._receipt = receipt

    def _assessment(self, observation, receipt):
        require(self._pending is not None and self._receipt is not None and receipt == self._receipt,
                'evidence receipt mismatch or duplicate feedback')
        self._validate_observation(observation)
        logs, total, coverage = self._pending
        require(all(observation[name] is None for name in self.ids if name not in coverage),
                'feedback outside precommitted sensor coverage')
        readings = [(i, observation[name]) for i, name in enumerate(self.ids) if observation[name] is not None]
        likelihood, reference, increment = None, None, None
        next_log_e, scored = self.log_e_value, bool(readings) and logs is not None
        if logs is not None:
            # Empty feedback adds exactly zero, including after an infinite alarm.
            likelihood = (min(0., _logsumexp([mass for bits, mass in zip(self.worlds, logs)
                          if all(bits[i] == value for i, value in readings)]) - total) if readings else 0.)
            reference = -len(readings) * log(2.)
            increment = reference - likelihood
            next_log_e += increment
        alarm = self.episode_alarm or next_log_e >= -log(self.alpha)
        if not readings:
            status = 'NO_EVIDENCE'
        elif logs is None:
            status = 'UNSUPPORTED_PREDICTION'
        elif next_log_e >= -log(self.alpha):
            status = 'MODEL_MISMATCH_EVIDENCE'
        elif increment > log(4.):
            status = 'SURPRISING_BUT_UNCONFIRMED'
        else:
            status = 'OBSERVATION_COMPATIBLE'
        result = {'status': status, 'prediction_available': logs is not None,
                  'observed_log_likelihood': _wire_log(likelihood),
                  'reference_log_likelihood': _wire_log(reference), 'log_e_increment': _wire_log(increment),
                  'log_e_value': _wire_log(next_log_e), 'episode_alarm': alarm,
                  'impossible_observation': likelihood == -float('inf'),
                  'observed_bits': len(readings), 'missing_bits': len(coverage) - len(readings),
                  'outside_coverage_bits': len(self.ids) - len(coverage),
                  'scored_steps': self.scored_steps + int(scored), 'committed': False}
        return result, next_log_e, alarm

    def preview(self, observation, receipt):
        return self._assessment(observation, receipt)[0]

    def receive(self, observation, receipt):
        result, next_log_e, alarm = self._assessment(observation, receipt)
        self.support.receive(self._envelope(observation, self.time + 1), receipt)
        self.time += 1
        self.log_e_value, self.episode_alarm = next_log_e, alarm
        self.scored_steps = result['scored_steps']
        self._pending, self._receipt = None, None
        result['committed'] = True
        return result
