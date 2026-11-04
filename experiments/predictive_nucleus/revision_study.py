"""Bounded G5 correction challenge on previously opened, frozen G3 physical banks."""

from collections import Counter
from itertools import permutations, product

from .revision_memory import Memory, Receipt, meaning
from .revision_preflight import layout, target_form

FEES = (.05, .75, None)
SEEDS = (7, 11, 23, 37, 53)
LAWS = ('nand', 'nor')


def select_triples(bank, seed):
    """Metadata-only split selection; never pick by test outcomes or forecasts."""
    sites = {s['id']: (s, bank['forecasts'][str(seed)][pair][j])
             for pair, group in bank['sites'].items() for j, s in enumerate(group)
             if layout(s) is not None}
    found = {}
    for ids in permutations(sorted(sites), 3):
        triple = [sites[i] for i in ids]
        shapes = tuple(layout(s[0]) for s in triple)
        if (len(set(shapes)) == 3
                and len({s[0]['lineage'] for s in triple}) == 3
                and all(not set(x[0]['entities']) & set(y[0]['entities'])
                        for x, y in permutations(triple, 2))):
            found.setdefault(shapes, triple)
    if len(found) != 6:
        raise ValueError(f'insufficient disjoint physical triples: {len(found)}')
    return list(found.values())


def receipt(site, identity, term, scope, time, reading, intended):
    model, matrix = site
    # A realized action payoff, not a teacher-given meaning or correct role.
    return Receipt(identity, term, scope, time, 'verified-sensor',
                   tuple(matrix[reading]), model['rewards'][reading][intended])


def act(state, truth, fee, informative=True):
    # A supplied, perfect optional question: available only if it discriminates.
    ask = state is None and informative and fee is not None and fee < .5
    chosen = truth if ask else (state if state is not None else 0)
    return int(chosen == truth), int(ask)


def scoped_latest(memory, term, scope):
    """Strong naive reference: most specific/latest single physical event."""
    events = [r for r in memory.snapshot()
              if r.term == term and scope[:len(r.scope)] == r.scope
              and meaning(r) is not None]
    return meaning(max(events, key=lambda r: (len(r.scope), r.event_time))) if events else None


def score_bank(law, seed, bank):
    totals = Counter()
    for k, (earlier, probe, later) in enumerate(select_triples(bank, seed)):
        options = (target_form(later[0], 0), target_form(later[0], 1))
        assert options[0] != options[1]
        assert options[0] != target_form(earlier[0], 0)
        for old, regional, sentinel, local, phase, claimed, duplicate, reversal in product(range(2), repeat=8):
            for destination, checkable in product(range(3), range(2)):
                root = (f'world-{law}-{k}',)
                region = root + (f'region-{k}',)
                here = region + (f'unit-a-{k}',)
                other = region + (f'unit-b-{k}',)
                elsewhere = root + (f'external-{k}',)
                scope = (here, other, elsewhere)[destination]
                memory = Memory()
                global_receipt = receipt(earlier, f'global-{k}', 'qor', root, 0, local, old)
                memory.add(global_receipt)
                memory.add(receipt(earlier, f'sentinel-{k}', 'nav', root, 0, local, sentinel))
                # A scoped meaning differing from its parent needs corroboration.
                memory.add(receipt(earlier, f'region-1-{k}', 'qor', region, 1, local, regional))
                memory.add(receipt(probe, f'region-2-{k}', 'qor', region, 2, 1-local, regional))
                memory.add(receipt(earlier, f'local-exception-{k}', 'qor', here, 3, 1-local, 1-regional))
                assert memory.belief('qor', here) is None
                current = regional ^ reversal  # kept evaluator-side
                # Phase 1 has identical public information for both opposite targets.
                later_receipt = (
                    receipt(probe, f'probe-{k}', 'qor', here, 4, local, current)
                    if phase == 0 else
                    Receipt(f'probe-{k}', 'qor', here, 4, 'verified-sensor', (.5, .5), 1)
                )
                memory.add(later_receipt)
                memory.add(Receipt(f'claim-{k}', 'qor', here, 5,
                                   'unverified-witness', None, claimed, False))
                if duplicate:
                    memory.add(global_receipt)  # late replay of a single physical event
                retained = Memory(memory.snapshot())  # reset; only evidence crosses episodes
                predicted = retained.belief('qor', scope)
                target = (current, regional, old)[destination]
                unresolved = destination == 0 and phase == 1
                if unresolved:
                    assert predicted is None
                    totals['unresolved'] += 1
                else:
                    assert predicted == target, (law, seed, k, destination, old, regional, current)
                    totals['resolved'] += 1
                assert retained.belief('nav', scope) == sentinel
                totals['sentinel_retained'] += 1
                totals['scoped_latest_correct'] += scoped_latest(retained, 'qor', scope) == target
                for i, fee in enumerate(FEES):
                    ok, asked = act(predicted, target, fee, bool(checkable))
                    basic_ok, basic_asked = act(None, target, fee, bool(checkable))
                    totals[f'policy_success_{i}'] += ok
                    totals[f'policy_questions_{i}'] += asked
                    totals[f'baseline_success_{i}'] += basic_ok
                    totals[f'baseline_questions_{i}'] += basic_asked
                    totals[f'policy_net100_{i}'] += 100*ok - int((fee or 0)*100)*asked
                    totals[f'baseline_net100_{i}'] += 100*basic_ok - int((fee or 0)*100)*basic_asked
                    if unresolved and checkable and i == 0:
                        assert asked and ok
                        totals['cheap_resolved'] += 1
                    if not unresolved:
                        assert asked == 0
                totals['cases'] += 1
    assert totals['cases'] == 9216 and totals['resolved'] == 7680 and totals['unresolved'] == 1536
    assert totals['sentinel_retained'] == totals['cases']
    assert totals['policy_questions_0'] == totals['cheap_resolved'] == 768
    assert totals['policy_questions_1'] == totals['policy_questions_2'] == 0
    assert totals['baseline_questions_0'] > totals['policy_questions_0']
    assert totals['policy_net100_0'] > totals['baseline_net100_0']
    return dict(totals)


if __name__ == '__main__':
    import json
    from .transfer_task import catalogue
    print(json.dumps({
        f'{law}-{seed}': score_bank(law, seed, catalogue(law, 'challenge'))
        for law in LAWS for seed in SEEDS
    }, indent=2, sort_keys=True))
