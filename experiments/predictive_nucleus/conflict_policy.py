"""Outcome-only source weighting over two attributed reports and frozen physical forecasts."""
from collections import Counter
from dataclasses import dataclass
from math import exp, isfinite
from typing import NamedTuple

import numpy as np

from .acceptance_contract import require


class Evidence(NamedTuple):
    probe_matrix: tuple
    probe_claims: tuple
    probe_action: int
    probe_reward: int | None
    target_matrix: tuple
    target_claims: tuple


def _bit(value):
    return type(value) is int and value in (0, 1)


def _reports(claims):
    reports = dict(claims)
    require(len(claims) == len(reports) == 2 and
            all(isinstance(source, str) and source and (b is None or _bit(b))
                for source, b in reports.items()), 'expected two attributed reports')
    return reports


def _features(evidence):
    """Earlier selected-payoff likelihood difference and the two associated target readings."""
    earlier, later = _reports(evidence.probe_claims), _reports(evidence.target_claims)
    require(earlier.keys() == later.keys() and _bit(evidence.probe_action) and
            (evidence.probe_reward is None or _bit(evidence.probe_reward)), 'invalid observed probe')
    # Sorting touches only the coordinate order. All source parameters are shared.
    left, right = sorted(earlier)
    advantage = 0.
    if evidence.probe_reward is not None:
        a = evidence.probe_action
        low, high = (row[a] for row in evidence.probe_matrix)
        require(0 <= low <= 1 and 0 <= high <= 1, 'invalid probe forecasts')
        support = (low, high, (low + high) / 2)
        scores = [support[2 if earlier[s] is None else earlier[s]] for s in (left, right)]
        advantage = (2 * evidence.probe_reward - 1) * (scores[1] - scores[0])
    return advantage, (.5 if later[left] is None else later[left]), (.5 if later[right] is None else later[right])


def values(matrix, p):
    """Expected gross action rewards given P(current private bit = 1)."""
    require(0 <= p <= 1 and len(matrix) == 2 and all(len(row) == 2 for row in matrix)
            and all(0 <= v <= 1 for row in matrix for v in row), 'invalid physical forecast or belief')
    return tuple((1-p) * low + p * high for low, high in zip(*matrix))


def choose(matrix, p, fee):
    """First physical action and whether a perfect physical verification is worth buying."""
    utility = values(matrix, p)
    require(fee is None or isfinite(fee) and fee >= 0, 'invalid verification cost')
    perfect = (1-p) * max(matrix[0]) + p * max(matrix[1])
    return int(utility[1] > utility[0]), fee is not None and perfect - max(utility) > fee


@dataclass(frozen=True)
class Receiver:
    weight: float
    kind: str = 'neural'

    def __post_init__(self):
        require(self.kind in ('neural', 'empirical') and isfinite(self.weight) and abs(self.weight) <= 16
                and (self.kind != 'empirical' or self.weight in (-1, 1)), 'invalid receiver')

    def probability(self, evidence):
        x, left, right = _features(evidence)
        z = self.weight * x
        if self.kind == 'neural':
            q = 1 / (1 + exp(-z))
        else:
            q = .5 if z == 0 else float(z > 0)
        return (1-q) * left + q * right


def fit(samples):
    """Fit both conventions exclusively from the reward of each explored target action."""
    histogram = Counter()
    for evidence, action, reward in samples:
        require(_bit(action) and _bit(reward), 'invalid selected target feedback')
        x, left, right = _features(evidence)
        low = values(evidence.target_matrix, left)[action]
        high = values(evidence.target_matrix, right)[action]
        histogram[x, low, high, reward] += 1
    require(histogram, 'empty target feedback')
    rows = sorted(histogram)
    x, low, high, reward = np.asarray(rows, dtype=np.float64).T
    counts = np.asarray([histogram[r] for r in rows], dtype=np.float64)
    frequency = counts / counts.sum()
    spread = high - low
    weight = 0.
    for _ in range(128):
        q = 1 / (1 + np.exp(-weight * x))
        pred = low + q * spread
        clipped = np.clip(pred, 1e-12, 1 - 1e-12)
        slope = (pred - reward) / (clipped * (1 - clipped)) * spread * q * (1-q) * x
        weight = float(np.clip(weight - 4 * np.sum(frequency * slope), -16, 16))
    errors = {}
    for sign in (1, -1):
        q = np.where(x == 0, .5, (sign*x > 0).astype(float))
        errors[sign] = np.sum(counts * (low + q * spread - reward)**2)
    return Receiver(weight), Receiver(1 if errors[1] <= errors[-1] else -1, 'empirical')
