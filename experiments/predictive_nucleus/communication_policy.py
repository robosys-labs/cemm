"""Two-stage outcome learning for the isolated one-request, two-action study."""
from collections import defaultdict
from dataclasses import dataclass
from math import isfinite

RIDGE = 1 / 16
Pair = tuple[float, float]


@dataclass(frozen=True)
class Witness:
    source: str
    age: int
    focus_matches: bool

    def key(self):
        if (not isinstance(self.source, str) or not self.source
                or type(self.age) is not int or self.age < 0
                or type(self.focus_matches) is not bool):
            raise ValueError("invalid public witness metadata")
        return self.source, self.age > 0, self.focus_matches


@dataclass(frozen=True)
class ActionSample:
    witness: Witness
    prior: Pair
    claimed: Pair
    action: int
    reward: float


@dataclass(frozen=True)
class RequestSample:
    witness: Witness
    prior: Pair
    opportunity: bool
    reward: float
    requested: bool


def _utilities(pair):
    if len(pair) != 2 or not all(0 <= x <= 1 for x in pair):
        raise ValueError("expected two finite binary-goal utilities")
    return pair


@dataclass(frozen=True)
class Policy:
    weights: dict
    gains: dict

    @classmethod
    def fit_actions(cls, samples):
        """Ridge on the single explored action and its gross terminal reward."""
        terms = defaultdict(lambda: [0.0, RIDGE])
        for row in samples:
            if row.action not in (0, 1) or not 0 <= row.reward <= 1:
                raise ValueError("invalid action feedback")
            baseline = _utilities(row.prior)[row.action]
            shift = _utilities(row.claimed)[row.action] - baseline
            total = terms[row.witness.key()]
            total[0] += shift * (row.reward - baseline)
            total[1] += shift * shift
        return cls({key: xy / xx for key, (xy, xx) in terms.items()}, {})

    def fit_requests(self, samples):
        """Contrast requested/silent rewards under the already fitted action head."""
        arms = defaultdict(lambda: [0.0, 0])
        for row in samples:
            if not 0 <= row.reward <= 1:
                raise ValueError("invalid request feedback")
            key = (*row.witness.key(), row.opportunity)
            arm = arms[key, row.requested]
            arm[0] += row.reward - max(_utilities(row.prior))
            arm[1] += 1
        gains = {}
        for (key, requested), (total, count) in arms.items():
            if requested and (key, False) in arms:
                silent_total, silent_count = arms[key, False]
                gains[key] = total / count - silent_total / silent_count
        return Policy(self.weights.copy(), gains)

    def ask(self, prior, witness, opportunity, cost):
        _utilities(prior)
        if not isfinite(cost) or cost < 0:
            raise ValueError("invalid request cost")
        return self.gains.get((*witness.key(), opportunity), 0.0) > cost

    def values(self, prior, witness=None, claimed=None):
        """Estimated action rewards; the sender's claim never updates the prior."""
        _utilities(prior)
        if claimed is None:
            return tuple(prior)
        if witness is None:
            raise ValueError("delivered claims require an attributed witness")
        weight = self.weights.get(witness.key(), 0.0)
        return tuple(max(0.0, min(1.0, p + weight * (q - p)))
                     for p, q in zip(prior, _utilities(claimed), strict=True))

    def act(self, prior, witness=None, claimed=None):
        first, second = self.values(prior, witness, claimed)
        return int(second > first)

    def to_dict(self):
        return {field: [[*key, value] for key, value in sorted(table.items())]
                for field, table in (("weights", self.weights), ("gains", self.gains))}

    @classmethod
    def from_dict(cls, data):
        tables = []
        for field, width in (("weights", 3), ("gains", 4)):
            table = {}
            for *parts, value in data[field]:
                key = tuple(parts)
                if (len(key) != width or not isinstance(key[0], str) or not key[0]
                        or any(type(x) is not bool for x in key[1:])
                        or key in table or not isfinite(value)):
                    raise ValueError("invalid policy checkpoint row")
                table[key] = value
            tables.append(table)
        return cls(*tables)
