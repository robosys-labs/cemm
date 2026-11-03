"""Two independently reset G3 scenes with one coupled two-way action.

Each instrument has a different public badge. The external goal specifies a
badge and asks for the archived native goal at that site. Lookup of the site,
the one-bit measurement code and both native predictive models are supplied.
The sender sees the two private readings, the two badges and the target badge.
Only the simulator sees both possible terminal payoffs.
"""
from itertools import combinations, product

from .acceptance_contract import digest, require
from .communication_world import load_cases

FAMILIES = {'train': 'path_return4', 'challenge': 'branch_return5'}
COUNT = 12
STRATA = ('hidden', 'known', 'costly')


def pairs(law, seed, split):
    """Bind 12 disjoint-roster scene pairs without selecting on model outputs."""
    cases = load_cases(law, seed, family=FAMILIES[split])
    inventory = sorted(cases, key=lambda c: digest(['g4-sender-site-v1', c['id']]))
    rosters = {c['id']: set(c['entities']) for c in inventory}
    candidates = []
    for left, right in combinations(inventory, 2):
        a, b = left['id'], right['id']
        if rosters[a].isdisjoint(rosters[b]):
            candidates.append((digest(['g4-sender-selection-v1', law, split, a, b]), a, b))
    require(len(candidates) >= COUNT, 'insufficient disjoint-roster G3 pairs')
    by_id = {c['id']: c for c in inventory}
    uses = dict.fromkeys(by_id, 0)
    selected = []
    for _ in range(COUNT):
        choice = min(candidates, key=lambda r: (max(uses[r[1]], uses[r[2]]), uses[r[1]] + uses[r[2]], r[0]))
        candidates.remove(choice)
        _, a, b = choice
        uses[a] += 1
        uses[b] += 1
        selected.append((by_id[a], by_id[b]))
    return tuple(selected)


def pair_id(pair, law, split):
    return digest(['g4-sender-pair-v1', law, split, pair[0]['id'], pair[1]['id']])


def round_id(pair_id, bits, tags, goal, source, stratum, rep):
    return digest(['g4-sender-round-v1', pair_id, bits, tags, goal, source, stratum, rep])


def rounds(pair, law, split):
    identity = pair_id(pair, law, split)
    for bits, tags, goal in product(product((0, 1), repeat=2), ((0, 1), (1, 0)), (0, 1)):
        site = tags.index(goal)  # Environment and receiver goal grounding only.
        selected = pair[site]
        witness_ids = tuple(c['witness'][b]['id'] for c, b in zip(pair, bits, strict=True))
        crossed = 'W1' if goal == int(split == 'challenge') else 'W2'
        for source, stratum, rep in product(('W0', crossed), STRATA, range(4)):
            # A single joint action applies this menu position at both sites.
            # The receiver sees the offered order. The sender cannot see it.
            order = (1, 0) if rep % 2 else (0, 1)
            matrix = tuple(tuple(row[a] for a in order) for row in selected['predicted'])
            local = bits[site] if stratum == 'known' else None
            prior = matrix[local] if local is not None else tuple((a + b) / 2 for a, b in zip(*matrix, strict=True))
            source_group = 'shared' if source == 'W0' else 'crossed'
            goal_pair = digest(['g4-sender-goal-pair-v1', identity, bits, tags, source_group, stratum, rep])
            yield dict(id=round_id(identity, bits, tags, goal, source, stratum, rep), pair_id=identity,
                       goal_pair=goal_pair, bits=bits, tags=tags, goal=goal, source=source,
                       source_group=source_group, stratum=stratum, rep=rep, menu_reversed=bool(rep % 2),
                       cost=.75 if stratum == 'costly' else .05, matrix=matrix, local=local, prior=prior,
                       rewards=[selected['rewards'][bits[site]][a] for a in order], witness_ids=witness_ids)
