"""TRAIN-only feasibility of revising a previously physically corroborated relation."""
from collections import Counter
from itertools import permutations, product
import json

from experiments.predictive_nucleus.acceptance_contract import require
from experiments.predictive_nucleus.transfer_task import catalogue


def layout(site):
    first, second = site['actions']
    if first[0] or second[0] or first[1:3] != second[1:3][::-1]:
        return None
    tokens = [text.split() for text in site['texts']]
    names = [[w for w in row if w in site['entities']] for row in tokens]
    words = [[w for w in row if w not in site['entities']] for row in tokens]
    if names[0] != names[1][::-1] or words[0] != words[1]:
        return None
    return tokens[0].index(words[0][0])


def triples(law):
    bank = catalogue(law, 'train')
    sites = {}
    for pair, group in bank['sites'].items():
        for index, site in enumerate(group):
            if layout(site) is not None:
                sites[site['id']] = site, bank['forecasts']['7'][pair][index]
    # One deterministic triple per ordered layout sequence. Each held-for-reset
    # surface uses new names and a new lineage relative to the other two menus.
    chosen = {}
    for keys in permutations(sorted(sites), 3):
        menus = [sites[key][0] for key in keys]
        shapes = tuple(map(layout, menus))
        if (len(set(shapes)) == 3 and len({s['lineage'] for s in menus}) == 3 and
                all(set(a['entities']).isdisjoint(b['entities']) for a,b in permutations(menus, 2))):
            chosen.setdefault(shapes, tuple(sites[key] for key in keys))
    require(len(chosen) == 6, 'missing cross-layout triple')
    return chosen.values()


def observe(model_site, term, stamp, reading, intended):
    site, forecasts = model_site
    # Only the physical payoff and both public hypotheses enter this receipt.
    # The key has no action ID, tape ID, answer, convention or observed payoff.
    key = (term, site['id'], stamp)
    return key, (tuple(forecasts[reading]), site['rewards'][reading][intended])


def decode(event):
    predictions, observed = event
    choices = [i for i,p in enumerate(predictions) if int(p > .5) == observed]
    require(len(choices) == 1, 'physical observation cannot distinguish the meanings')
    return choices[0]


def target_form(site, index):
    words = site['texts'][index].split()
    words[layout(site)] = 'qor'
    return tuple(words)


def check():
    counts = Counter()
    for law in ('nand', 'nor'):
        for earlier, probe, later in triples(law):
            counts['triples'] += 1
            for old, sentinel, local, swap, replay, assertion in product(range(2), repeat=6):
                warm = observe(earlier, 'qor', 0, local, old)
                other = observe(earlier, 'nav', 0, local, sentinel)
                disputed = observe(earlier, 'qor', 1, 1-local, 1-old)
                base = (warm, other, disputed)
                # Both hypotheses have exactly this visible history. The initial
                # contradiction could be persistent or a one-off exception.
                alternatives = (decode(warm[1]), decode(disputed[1]))
                require(set(alternatives) == {0,1}, 'prefeedback alternatives collapse')
                probe_observations, targets = [], []
                for reversal in (0,1):
                    current = old ^ reversal  # evaluator only
                    calibration = observe(probe, 'qor', 2, local, current)
                    probe_observations.append(calibration)
                    stream = (*base, calibration, (warm, disputed)[replay])
                    ledger = dict(stream)
                    require(len(ledger) == len(base)+1, 'duplicate raised evidence count')
                    # Episode ends. Only the attributed record set travels across reset.
                    kept = dict(ledger)
                    focus = [key for key in kept if key[0] == 'qor']
                    newest = max(focus, key=lambda key: key[2])
                    sense = decode(kept[newest])
                    require(decode(kept[other[0]]) == sentinel and len(focus) == 3, 'history/sentinel lost')
                    # On the next roster the same directed readings are offered in
                    # counterbalanced slots. Native-layout candidate alignment is supplied.
                    display = [0,1] if not swap else [1,0]
                    options = [target_form(later[0], i) for i in display]
                    surface = target_form(later[0], 0)
                    direct_slot = options.index(surface)
                    payoffs = later[0]['rewards'][local]
                    require(surface != target_form(earlier[0], 0) and
                            payoffs[current] != payoffs[1-current], 'target surface or reward ambiguous')
                    correct = display.index(current)
                    targets.append(correct)
                    counts['target_decisions'] += 1
                    counts['dated_verified_hits'] += (direct_slot ^ sense) == correct
                    counts['last_arrival_hits'] += (direct_slot ^ decode(stream[-1][1])) == correct
                    counts['last_claim_hits'] += (direct_slot ^ assertion) == correct
                    counts['reset_after_query_hits'] += (
                        decode(observe(later, 'qor', 3, local, current)[1]) == current)
                    counts['sentinel_retained'] += decode(kept[other[0]]) == sentinel
                require(probe_observations[0][0] == probe_observations[1][0] and
                        probe_observations[0][1][0] == probe_observations[1][1][0] and
                        probe_observations[0][1][1] != probe_observations[1][1][1] and
                        len(set(targets)) == 2, 'twins differ outside observed payoff or need same choice')
                counts['indistinguishable_prepayoff_twins'] += 1
    n = counts['target_decisions']
    require(n == 2*counts['indistinguishable_prepayoff_twins'] == counts['dated_verified_hits']
            == counts['reset_after_query_hits'] == counts['sentinel_retained']
            == 2*counts['last_arrival_hits'] == 2*counts['last_claim_hits'], 'ceiling mismatch')
    return dict(counts, no_later_payoff_max_hits=n//2, no_later_payoff_unresolved=n,
                post_reset_additional_queries_retained=0, post_reset_additional_queries_reset=n,
                target_scope='TRAIN only, seed 7; two known directed interpretations per term')


if __name__ == '__main__':
    print(json.dumps(check(), indent=2, sort_keys=True))
