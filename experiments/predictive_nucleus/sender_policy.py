"""Outcome-only one-bit encoder and cue-free request value, with no model updates at evaluation."""
from collections import defaultdict
from dataclasses import dataclass
from math import isfinite

from .acceptance_contract import require


def _sign(bit):
    require(type(bit) is int and bit in (0, 1), 'binary observation required')
    return 2 * bit - 1


def _placement(tags, goal):
    require(tuple(tags) in ((0, 1), (1, 0)) and type(goal) is int and goal in (0, 1),
            'distinct public badges and a target required')
    return tags[0], goal


@dataclass(frozen=True)
class Sender:
    weights: dict

    @classmethod
    def fit(cls, samples):
        """Estimate how each private reading interacts with the explored wire symbol.

        On the balanced factorial exploration, the signed moment is the linear
        contrast of observed terminal rewards. There is no target message.
        """
        totals = defaultdict(lambda: [0, 0, 0])
        for tags, goal, bits, emitted, reward in samples:
            row = totals[_placement(tags, goal)]
            contrast = _sign(emitted) * _sign(reward)
            left, right = bits
            row[0] += _sign(left) * contrast
            row[1] += _sign(right) * contrast
            row[2] += 1
        return cls({key: (left / n, right / n) for key, (left, right, n) in totals.items()})

    def send(self, tags, goal, bits):
        left, right = bits
        w0, w1 = self.weights.get(_placement(tags, goal), (0., 0.))
        return int(w0 * _sign(left) + w1 * _sign(right) > 0)

    def to_dict(self):
        return {'weights': [[*key, *weight] for key, weight in sorted(self.weights.items())]}

    @classmethod
    def from_dict(cls, data):
        weights = {}
        for tag, goal, left, right in data['weights']:
            require(tag in (0, 1) and goal in (0, 1) and all(isfinite(x) and abs(x) <= 1 for x in (left, right))
                    and (tag, goal) not in weights, 'invalid sender checkpoint')
            weights[tag, goal] = left, right
        return cls(weights)


def _margin(prior):
    a, b = prior
    require(0 <= a <= 1 and 0 <= b <= 1, 'invalid sensor-only action values')
    return min(3, int(4 * abs(a - b)))


@dataclass(frozen=True)
class Requester:
    gains: dict

    @classmethod
    def fit(cls, samples):
        totals = defaultdict(lambda: [0, 0])
        for prior, requested, reward in samples:
            require(type(requested) is bool and type(reward) is int and reward in (0, 1), 'invalid request feedback')
            row = totals[_margin(prior), requested]
            row[0] += reward
            row[1] += 1
        gains = {}
        for k in range(4):
            paid, silent = totals[k, True], totals[k, False]
            if paid[1] and silent[1]:
                gains[k] = paid[0] / paid[1] - silent[0] / silent[1]
        return cls(gains)

    def ask(self, prior, cost):
        require(isfinite(cost) and cost >= 0, 'invalid request cost')
        return self.gains.get(_margin(prior), 0.) > cost

    def to_dict(self):
        return {'gains': [[k, v] for k, v in sorted(self.gains.items())]}

    @classmethod
    def from_dict(cls, data):
        gains = {}
        for k, v in data['gains']:
            require(type(k) is int and 0 <= k <= 3 and isfinite(v) and abs(v) <= 1
                    and k not in gains, 'invalid requester checkpoint')
            gains[k] = v
        return cls(gains)


def values(prior, matrix, local, token):
    """A report only selects a hypothetical payoff vector. It never updates the sensor."""
    require(token is None or type(token) is int and token in (0, 1), 'unknown wire token')
    return tuple(prior if token is None or local is not None else matrix[token])
