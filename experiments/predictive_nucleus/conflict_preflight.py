"""TRAIN-only identifiability check for a subsequent two-source communication study."""
from collections import Counter, defaultdict
from itertools import product
from typing import NamedTuple
import json

from .acceptance_contract import require
from .transfer_task import catalogue


class View(NamedTuple):
    actions: tuple
    prior: tuple
    forecasts: tuple
    claims: tuple


def observation(site, forecasts, first_bit, reverse):
    claims = (('W0', first_bit), ('W1', 1 - first_bit))
    matrix = tuple(map(tuple, forecasts))
    prior = tuple((p + q) / 2 for p, q in zip(*matrix, strict=True))
    return View(tuple(map(tuple, site['actions'])), prior, matrix, claims[::-1] if reverse else claims)


def best(values):
    require(len(values) == 2 and values[0] != values[1], 'a unique physical choice is required')
    return int(values[1] > values[0])


def check():
    blind, anonymous = defaultdict(Counter), defaultdict(Counter)
    menus, goals, pairs = set(), set(), set()
    oracle_hits = probe_hits = twins = 0
    for law in ('nand', 'nor'):
        bank = catalogue(law, 'train')
        for pair, sites in bank['sites'].items():
            pairs.add(pair)
            for site in sites:
                menus.add((site['lineage'], tuple(site['entities']), tuple(map(tuple, site['actions']))))
                goals.add(site['id'])
            require(set(sites[0]['entities']).isdisjoint(sites[1]['entities']), 'shared physical entities')
            for tables in bank['forecasts'].values():
                for first, probe, bit_a, bit_b, reverse_a, reverse_b in product(range(2), repeat=6):
                    start = observation(sites[first], tables[pair][first], bit_a, reverse_a)
                    second = 1 - first
                    target = observation(sites[second], tables[pair][second], bit_b, reverse_b)
                    # Construct the public history once for both latent regimes.
                    visible = (start, probe, target)
                    unlabeled = tuple(view._replace(claims=tuple(bit for _, bit in view.claims))
                                      for view in (start, target))
                    feedback, optima = [], []
                    for regime in (0, 1):
                        outcome = sites[first]['rewards'][bit_a ^ regime][probe]
                        payoffs = sites[second]['rewards'][bit_b ^ regime]
                        optimum = best(payoffs)
                        blind[visible][optimum] += 1
                        anonymous[unlabeled, probe, outcome][optimum] += 1
                        feedback.append(outcome)
                        optima.append(optimum)
                        # Only the earlier selected-action outcome reaches this reference rule.
                        sources = [w for w, b in start.claims if int(best(start.forecasts[b]) == probe) == outcome]
                        require(len(sources) == 1, 'earlier outcome does not identify a source')
                        target_bit = dict(target.claims)[sources[0]]
                        oracle_hits += payoffs[best(target.forecasts[target_bit])]
                        probe_hits += outcome
                    require(set(feedback) == set(optima) == {0, 1}, 'non-discriminating twin')
                    twins += 1
    ceilings = {}
    for name, groups in [('outcome_blind', blind), ('unattributed_feedback', anonymous)]:
        require(all(v[0] == v[1] for v in groups.values()), 'unbalanced observable histories')
        ceilings[name + '_max_hits'] = sum(max(v.values()) for v in groups.values())
    require(twins > 0 and oracle_hits == 2 * twins and all(n == twins for n in ceilings.values()),
            'conflict ceilings or reference differ')
    return dict(twins=twins, target_rounds=2 * twins, oracle_hits=oracle_hits, probe_hits=probe_hits,
                distinct_public_histories=len(blind), physical_menus=len(menus),
                native_site_goals=len(goals), compound_pairs=len(pairs), **ceilings)


if __name__ == '__main__':
    print(json.dumps(check(), sort_keys=True, indent=2))
