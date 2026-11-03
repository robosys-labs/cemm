"""Paired two-turn communication tasks over pinned G3 physical menus."""
from itertools import product

from .acceptance_contract import digest, require
from .conflict_policy import Evidence

CONVENTIONS = ('persist', 'switch')
FEES = (.05, .75, None)
ARMS = ('learned', 'empirical', 'crossed', 'fixed0', 'fixed1', 'blind', 'free_silent', 'suppressed', 'shuffled')
CASES_PER_PAIR = 512


def cases(bank, law, seed, split):
    index = 0
    for pair in sorted(bank['sites']):
        sites = bank['sites'][pair]
        matrices = [tuple(map(tuple, m)) for m in bank['forecasts'][str(seed)][pair]]
        sources = tuple(digest(['g4-conflict-source-v1', split, pair, s]) for s in (0, 1))
        for first, probe, a0, a1, b0, b1, regime, oa, ob in product(range(2), repeat=9):
            ca, cb = (a0, a1), (b0, b1)
            start, target = sites[first], sites[1-first]
            reading = ca[regime]
            probe_reward = start['rewards'][reading][probe]
            probe_claims = tuple(zip(sources, ca))[::1-2*oa]
            target_claims = tuple(zip(sources, cb))[::1-2*ob]
            visible = Evidence(matrices[first], probe_claims, probe, probe_reward, matrices[1-first], target_claims)
            truth = (cb[regime], cb[1-regime])
            identity = digest(['g4-conflict-v1', law, split, pair, first, probe, ca, cb, regime, oa, ob])
            # The two conventions see exactly this same recipient view, including probe payoff.
            public_hash = digest([start['texts'], target['texts'], visible])
            # Flip target arrival order to avoid fixed points. Half the donors also flip both target reports.
            donor = index ^ 1 ^ ((1 << 4 | 1 << 3) if oa else 0)
            yield dict(index=index, id=identity, pair=pair, first=first, probe=probe, ca=ca, cb=cb,
                       regime=regime, start_order=oa, target_order=ob, public=visible, pubhash=public_hash,
                       target_bits=truth, rewards=tuple(tuple(target['rewards'][b]) for b in truth),
                       explore=ob, probe_reward=probe_reward, donor=donor)
            index += 1
    require(index == 12 * CASES_PER_PAIR, 'incomplete paired schedule')


def split_inventory(train, held):
    def inventory(bank):
        sites = [s for pair in bank['sites'].values() for s in pair]
        return dict(pairs=set(bank['sites']), sites={s['id'] for s in sites},
                    lineages={s['lineage'] for s in sites}, entities={e for s in sites for e in s['entities']},
                    witnesses={w['id'] for s in sites for w in s['witness']},
                    tapes={t for s in sites for row in s['episodes'] for t in row})
    a, b = inventory(train), inventory(held)
    require(all(not a[k] & b[k] for k in a), 'physical training/challenge overlap')
    return {k: [len(a[k]), len(b[k]), len(a[k] & b[k])] for k in a}
