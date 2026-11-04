"""Provenance-preserving two-meaning memory. Neither interpretation is gold-labeled."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Receipt:
    evidence_id: str
    term: str
    scope: tuple[str, ...]
    event_time: int
    source: str
    probabilities: tuple[float, float] | None
    outcome: int | None
    physical: bool = True


def meaning(receipt):
    """Infer a supported interpretation from observed payoff and physical forecasts."""
    if not receipt.physical or receipt.probabilities is None or receipt.outcome is None:
        return None
    p, q = receipt.probabilities
    if not (0 <= p <= 1 and 0 <= q <= 1 and type(receipt.outcome) is int
            and receipt.outcome in (0, 1)):
        raise ValueError('invalid physical evidence')
    likelihoods = (p, q) if receipt.outcome else (1-p, 1-q)
    if abs(likelihoods[0] - likelihoods[1]) < .5:
        return None
    return int(likelihoods[1] > likelihoods[0])


class Memory:
    """Retain hypotheses across resets; require corroboration after a contradiction."""

    def __init__(self, records=()):
        self.records = {}
        for record in records:
            self.add(record)

    def add(self, record):
        if not record.evidence_id or not record.term or not record.source or not record.scope:
            raise ValueError('missing evidence identity/provenance')
        prior = self.records.get(record.evidence_id)
        if prior is not None and prior != record:
            raise ValueError('conflicting reuse of a physical evidence identity')
        self.records[record.evidence_id] = record

    def snapshot(self):
        return tuple(sorted(self.records.values(), key=lambda r: r.evidence_id))

    def belief(self, term, scope):
        """0/1 if grounded, None if missing or conflicting. Scope hierarchy is supplied."""
        established, pending = None, None
        for depth in range(1, len(scope)+1):
            relevant = [r for r in self.records.values()
                        if r.term == term and r.scope == scope[:depth] and meaning(r) is not None]
            by_time = {}
            for r in relevant:
                by_time.setdefault(r.event_time, set()).add(meaning(r))
            for timestamp in sorted(by_time):
                alternatives = by_time[timestamp]
                if len(alternatives) != 1:
                    pending = 'conflict'
                    continue
                candidate = next(iter(alternatives))
                if established is None:
                    established, pending = candidate, None
                elif candidate == established:
                    pending = None
                elif pending == candidate:
                    established, pending = candidate, None
                else:
                    pending = candidate
        return established if pending is None else None
