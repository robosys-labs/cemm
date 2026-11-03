"""Outcome-trained routing of a private measurement over two public feature vectors."""
from collections import defaultdict
from dataclasses import dataclass
from math import isfinite

import numpy as np

from .acceptance_contract import require


DIM = 4
RIDGE = 1e-6


def _bit(x):
    return type(x) is int and x in (0, 1)


def _vector(xs):
    values = tuple(xs)
    require(len(values) == DIM and all(type(x) is int and x in (-1, 1) for x in values),
            'expected a bipolar badge vector')
    return values


def _visible(sites, goal, bits):
    left, right = sites
    bits = tuple(bits)
    require(len(bits) == 2 and all(map(_bit, bits)), 'two private bits required')
    return _vector(left), _vector(right), _vector(goal), bits


def _emit(delta, bits):
    if delta == 0:
        return bits[0] if bits[0] == bits[1] else 0
    return bits[int(delta < 0)]


def raw_dot(sites, goal, bits):
    """Control using direct feature overlap without a learned goal-view transform."""
    left, right, target, readings = _visible(sites, goal, bits)
    return _emit(sum((x - y) * g for x, y, g in zip(left, right, target)), readings)


@dataclass(frozen=True)
class SharedSender:
    matrix: tuple

    @classmethod
    def fit(cls, samples):
        # A single design row measures the relative value of the two sites.
        # Integer sufficient statistics combine repeated rows before the solve.
        totals = defaultdict(lambda: [0, 0])
        for sites, goal, bits, emitted, reward in samples:
            left, right, target, (a, b) = _visible(sites, goal, bits)
            require(_bit(emitted) and _bit(reward), 'invalid selected-emission feedback')
            features = tuple((a - b) * (x - y) * g for x, y in zip(left, right) for g in target)
            row = totals[features]
            row[0] += 1
            row[1] += (2 * emitted - 1) * (2 * reward - 1)
        require(totals, 'no sender training samples')
        design = np.asarray(list(totals), dtype=np.float64)
        counts, response = np.asarray(list(totals.values()), dtype=np.float64).T
        gram = design.T @ (counts[:, None] * design)
        rhs = design.T @ response
        weights = np.linalg.solve(gram + RIDGE * np.eye(DIM * DIM), rhs)
        return cls.from_dict({'matrix': weights.reshape(DIM, DIM).tolist()})

    def send(self, sites, goal, bits):
        left, right, target, readings = _visible(sites, goal, bits)
        delta = sum((x - y) * sum(w * g for w, g in zip(row, target))
                    for x, y, row in zip(left, right, self.matrix))
        return _emit(delta, readings)

    def to_dict(self):
        return {'matrix': [list(row) for row in self.matrix]}

    @classmethod
    def from_dict(cls, data):
        require(set(data) == {'matrix'}, 'unexpected shared checkpoint fields')
        matrix = tuple(tuple(row) for row in data['matrix'])
        require(len(matrix) == DIM and all(len(row) == DIM and all(
            type(v) in (float, int) and isfinite(v) for v in row) for row in matrix), 'invalid shared matrix')
        return cls(matrix)


def _best(outcomes, fallback):
    (n0, hits0), (n1, hits1) = outcomes
    return int(hits1 * n0 > hits0 * n1) if n0 and n1 else fallback


@dataclass(frozen=True)
class ExactLookup:
    entries: dict
    fallback: int

    @classmethod
    def fit(cls, samples):
        counts = defaultdict(lambda: [[0, 0], [0, 0]])
        overall = [[0, 0], [0, 0]]
        for sites, goal, bits, emitted, reward in samples:
            key = _visible(sites, goal, bits)
            require(_bit(emitted) and _bit(reward), 'invalid selected-emission feedback')
            for row in (counts[key][emitted], overall[emitted]):
                row[0] += 1
                row[1] += reward
        require(overall[0][0] and overall[1][0], 'both wire symbols must have been explored')
        fallback = _best(overall, 0)
        return cls({k: _best(v, fallback) for k, v in counts.items()}, fallback)

    def send(self, sites, goal, bits):
        return self.entries.get(_visible(sites, goal, bits), self.fallback)

    def to_dict(self):
        return {'entries': [[list(left), list(right), list(goal), list(bits), token]
                            for (left, right, goal, bits), token in sorted(self.entries.items())],
                'fallback': self.fallback}

    @classmethod
    def from_dict(cls, data):
        require(set(data) == {'entries', 'fallback'} and _bit(data['fallback']), 'invalid lookup checkpoint')
        entries = {}
        for left, right, goal, bits, token in data['entries']:
            key = _visible((left, right), goal, bits)
            require(key not in entries and _bit(token), 'invalid lookup entry')
            entries[key] = token
        return cls(entries, data['fallback'])


# Only the frozen #83 control receives these two explicit registration records.
_LEGACY_SITES = {(-1, -1, -1, -1): 0, (1, 1, -1, -1): 1}
_LEGACY_GOALS = {(1, -1, 1, -1): 0, (-1, 1, 1, -1): 1}


def legacy_send(sender, sites, goal, bits):
    """Use #83 within its two registered IDs; an unavailable cell defaults to zero."""
    left, right, target, readings = _visible(sites, goal, bits)
    a, b, g = _LEGACY_SITES.get(left), _LEGACY_SITES.get(right), _LEGACY_GOALS.get(target)
    if a is None or b is None or g is None or a == b:
        return 0
    return sender.send((a, b), g, readings)
