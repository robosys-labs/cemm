"""G5 v2: one outcome-fitted switch parameter; TRAIN-only fitting.

No evaluator meaning label enters the learner. Prior scoped rule stays unchanged.
"""
from itertools import product
from math import log, exp

from .revision_memory import Memory, Receipt
from .revision_study import receipt, select_triples

GRID = (.0025, .005, .01, .02, .04, .08, .16, .32)
EPS = 1e-12
CONFIDENCE = .95


def posterior(memory, term, scope, switch):
    """P(meaning=1) from selected physical payoffs, not interpretation labels."""
    if not (0 < switch < .5) or not scope:
        raise ValueError('bad scope or transition parameter')
    p = .5
    for depth in range(1, len(scope) + 1):
        buckets = {}
        for r in memory.snapshot():
            if r.term != term or r.scope != scope[:depth] or not r.physical:
                continue
            if r.probabilities is None or r.outcome is None:
                continue
            if type(r.outcome) is not int or r.outcome not in (0, 1):
                raise ValueError('invalid payoff')
            a, b = r.probabilities
            if not (0 <= a <= 1 and 0 <= b <= 1):
                raise ValueError('invalid conditional forecast')
            likelihood = (a, b) if r.outcome else (1-a, 1-b)
            buckets.setdefault(r.event_time, []).append(likelihood)
        for time in sorted(buckets):
            prior = switch + (1 - 2*switch)*p
            factors = buckets[time]
            # Combining same-time observations is commutative; no invented
            # state transition between simultaneous independent receipts.
            log_odds = log(prior / (1-prior))
            seen = set()
            for a, b in factors:
                la, lb = log(max(a, EPS)), log(max(b, EPS))
                if la != lb:
                    seen.add(lb > la)
                log_odds += lb - la
            p = (1/(1+exp(-log_odds)) if log_odds >= 0
                 else exp(log_odds)/(1+exp(log_odds)))
            # Opposing same-time physical observations are unresolved, even
            # if an inherited prior has high confidence.
            if len(seen) == 2:
                p = .5
    return p


def decision(p):
    if not 0 <= p <= 1:
        raise ValueError('invalid belief')
    return 1 if p >= CONFIDENCE else (0 if p <= 1-CONFIDENCE else None)


def history(earlier, probe, key, old, regional, sentinel, reading, phase, reversal):
    """Construct the public prefix only; target meaning is returned to generator."""
    root = (f'world-{key}',)
    region = root + (f'region-{key}',)
    here = region + (f'unit-a-{key}',)
    sibling = region + (f'unit-b-{key}',)
    outside = root + (f'external-{key}',)
    current = regional ^ reversal  # evaluator-side: not passed to posterior()
    m = Memory((
        receipt(earlier, f'global-{key}', 'qor', root, 0, reading, old),
        receipt(earlier, f'sentinel-{key}', 'nav', root, 0, reading, sentinel),
        receipt(earlier, f'region-1-{key}', 'qor', region, 1, reading, regional),
        receipt(probe, f'region-2-{key}', 'qor', region, 2, 1-reading, regional),
        receipt(earlier, f'exception-{key}', 'qor', here, 3, 1-reading, 1-regional),
    ))
    last = (receipt(probe, f'probe-{key}', 'qor', here, 4, reading, current)
            if phase == 0 else
            Receipt(f'probe-{key}', 'qor', here, 4, 'verified-sensor', (.5, .5), 1))
    m.add(last)
    return m, (here, sibling, outside), (current, regional, old)


def train_samples(bank, seed):
    """Only TRAIN physical forecasts and next selected-action payoffs."""
    for key, (earlier, probe, later) in enumerate(select_triples(bank, seed)):
        for old, regional, sentinel, reading, phase, reversal in product((0,1), repeat=6):
            m, scopes, truths = history(
                earlier, probe, f'train-{key}', old, regional, sentinel,
                reading, phase, reversal)
            for scope, truth in zip(scopes, truths, strict=True):
                # The training target is an observed selected payoff, never a
                # role, meaning, latent state, or evaluator label.
                predicted = tuple(later[1][reading])
                observed = later[0]['rewards'][reading][truth]
                yield m, 'qor', scope, predicted, observed


def payoff_nll(samples, switch):
    loss = 0.
    for m, term, scope, (a,b), outcome in samples:
        p = posterior(m, term, scope, switch)
        likelihood = (1-p)*a + p*b
        likelihood = likelihood if outcome else 1-likelihood
        loss -= log(max(likelihood, EPS))
    return loss / len(samples)


def fit_train(bank, seed):
    """Fixed-grid one-scalar maximum predictive likelihood, no gold meanings."""
    samples = tuple(train_samples(bank, seed))
    if not samples:
        raise ValueError('empty training data')
    losses = [payoff_nll(samples, switch) for switch in GRID]
    winner = min(range(len(GRID)), key=lambda k: (losses[k], GRID[k]))
    return {'switch': GRID[winner], 'train_count': len(samples),
            'train_mean_nll': losses[winner],
            'grid_mean_nll': dict(zip(map(str, GRID), losses))}


if __name__ == '__main__':
    import json
    from .transfer_task import catalogue
    results = {f'{law}-{seed}': fit_train(catalogue(law, 'train'), seed)
               for law in ('nand','nor') for seed in (7, 11, 23, 37, 53)}
    print(json.dumps(results, indent=2, sort_keys=True))
