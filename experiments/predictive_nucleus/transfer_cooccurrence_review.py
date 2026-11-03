"""Post hoc reward-free sender control on the sealed G4 transfer bank."""
import json
from collections import Counter, defaultdict
from itertools import product

from experiments.predictive_nucleus import continuation_run as io
from experiments.predictive_nucleus.acceptance_contract import require
from experiments.predictive_nucleus.communication_freeze import _outputs
from experiments.predictive_nucleus.transfer_protocol import RESULT
from experiments.predictive_nucleus.transfer_run import LAWS, inputs


def learn_view(observations):
    """Infer a linear map from displayed goal and unordered site vectors alone."""
    candidates = {}
    for sites, goal in observations:
        possible = set(map(tuple, sites))
        candidates.setdefault(tuple(goal), possible.copy()).intersection_update(possible)
    require(candidates and all(len(v) == 1 for v in candidates.values()),
            'TRAIN co-occurrences do not uniquely identify every observed goal')
    pairs = [(g, next(iter(v))) for g, v in candidates.items()]
    axes = range(len(pairs[0][0]))
    n = len(pairs)
    # The TRAIN Gram matrix is n*I, so integer cross-products give n times
    # the exact least-squares map from goal to site, with no rounding or IDs.
    require(all(sum(g[i]*g[j] for g, _ in pairs) == n*(i == j)
                for i, j in product(axes, repeat=2)), 'unexpected TRAIN Gram matrix')
    matrix = [[sum(site[i]*g[j] for g, site in pairs) for j in axes] for i in axes]
    return matrix, frozenset(candidates)


def query_site(matrix, scale, sites, goal):
    decoded = tuple(sum(w*g for w, g in zip(row, goal, strict=True)) for row in matrix)
    matches = [i for i, site in enumerate(sites) if decoded == tuple(scale*x for x in site)]
    return matches[0] if len(matches) == 1 else None


def review():
    conditions = list(product(LAWS, io.SEEDS))
    models = {}
    for law, seed in conditions:
        train = inputs(law, seed, 'train')
        models[law, seed] = learn_view((r['sites'], r['goal']) for r in train if r['rep'] < 2)
    raw_dir = RESULT/'raw'
    receipt = io._read(raw_dir/'receipt.json')
    require(receipt['status'] == 'complete' and receipt['outputs'] == _outputs(raw_dir),
            'raw publication does not match its receipt')
    reports, distinct = {}, defaultdict(set)
    total = Counter()
    for law, seed in conditions:
        matrix, train_goals = models[law, seed]
        archive = io._read(raw_dir/f'{law}-{seed}.json.xz')
        raw = {r['id']: r for r in archive}
        rows = inputs(law, seed, 'challenge')
        require(len(raw) == len(archive) == len(rows) and raw.keys() == {r['id'] for r in rows},
                'challenge join differs')
        parts = defaultdict(Counter)
        for r in rows:
            saved = raw[r['id']]
            p = parts[r['partition']]
            distinct[r['partition']].add(r['id'])
            site = query_site(matrix, len(train_goals), r['sites'], r['goal'])
            # Unresolved views have a fixed zero-symbol fallback. Count every one.
            token = 0 if site is None else r['bits'][site]
            asked = saved['asked']
            values = r['matrix'][token] if asked and r['local'] is None else r['prior']
            choice = int(values[1] > values[0])
            reward = r['rewards'][choice]
            p['episodes'] += 1
            p['unseen_goal_view_rounds'] += tuple(r['goal']) not in train_goals
            p['unresolved'] += site is None
            p['emission_mismatches'] += token != saved['emitted']
            p['action_mismatches'] += choice != saved['arms']['delivered']['action']
            p['requests'] += asked
            p['successes'] += reward
            p['net_hundredths'] += 100*reward - round(100*r['cost'])*asked
        require(set(parts) == {'fresh', 'recombined'} and all(p['episodes'] == 3072 for p in parts.values()),
                'incomplete partition')
        for p in parts.values():
            total.update(p)
        reports[f'{law}/{seed}'] = dict(train_goal_views=len(train_goals),
                                         matrix_numerator=matrix, partitions=parts)
    return dict(scope='post hoc sender control with the archived request policy',
                conditions=reports, distinct_rounds={k: len(v) for k, v in distinct.items()}, total=total)


if __name__ == '__main__':
    print(json.dumps(review(), sort_keys=True, separators=(',', ':')))
