"""Public memory diagnostic v2; resets ALL entity bits before the query.

Supplied physics, noiseless sensors and authored probe; not an independent
oracle, learned acquisition policy or G1 gate. Legacy fixtures stay unchanged.
"""
from collections import Counter, defaultdict
from itertools import permutations
import json
import math

import torch

from .joint_objective import batch_histories
from .empirical_joint import context, queries
from .schedule_fixture import SensorEpisode
from .world import Action, World, observe, step

N_CASES = 256
QUERY_STEP = 6


def make_history(case, *, informative, composition=False):
    if (type(case) is not int or not 0 <= case < N_CASES or
            type(informative) is not bool or type(composition) is not bool):
        raise ValueError('invalid public fixture selection')
    initial = tuple((case >> i) & 1 for i in (7, 6, 5))
    mode, x, y, z, reverse = ((case >> i) & 1 for i in (4, 3, 2, 1, 0))
    ids = ('unit-a', 'unit-b', 'unit-c')
    a, b, c = ids
    left, right, other = (b, c, a) if composition else (a, b, c)
    query = (right, left) if reverse else (left, right)
    probe = int(informative)
    actions = (Action('set', (a,), probe), Action('set', (b,), probe), Action('contact', (a, b)),
               Action('set', (left,), x), Action('set', (right,), y), Action('set', (other,), z),
               Action('contact', query), Action('observe'))
    world, observations = World(ids, initial, mode), []
    for t in range(len(actions) + 1):
        if t:
            world = step(world, actions[t - 1])
        sensor = observe(world, t, ids if t % 2 == 0 else ids[::-1])
        observations.append(tuple((m['id'], m['bit']) for m in sensor['measurements']))
    return SensorEpisode(tuple(observations), tuple((a.kind, a.participants, a.value) for a in actions))


def histories(*, informative, composition=False):
    # Keep legacy renaming code and data immutable. No fit or scoring here.
    from .informative_curriculum import rename
    result = []
    for case in range(N_CASES):
        history = make_history(case, informative=informative, composition=composition)
        ids = tuple(sorted(name for name, _ in history._observations[0]))
        result.extend(rename(history, names) for names in permutations(ids))
    return tuple(result)


def bounds(batch, *, current_only=False):
    """Empirical Bayes bounds on this finite opened fixture, not model scores."""
    if type(current_only) is not bool:
        raise ValueError('current_only must be boolean')
    grouped = [defaultdict(Counter) for _ in range(len(batch.actions))]
    targets = batch.observations[1:].to(dtype=torch.long).tolist()
    for t, e, pre, action, past in queries(batch):
        key = (pre, action) if current_only else (pre, action, past)
        grouped[t][key][tuple(targets[t][e])] += 1
    rows = []
    for t, groups in enumerate(grouped):
        n = sum(sum(counts.values()) for counts in groups.values())
        correct = sum(max(counts.values()) for counts in groups.values())
        nll = brier = 0.0
        for counts in groups.values():
            size = sum(counts.values())
            nll -= sum(count * math.log(count / size) for count in counts.values())
            brier += size - sum(count * count for count in counts.values()) / size
        rows.append({'step': t, 'queries': n, 'prefixes': len(groups), 'max_correct': correct,
                     'map_ceiling': correct / n, 'min_mean_nll': nll / n, 'min_mean_brier': brier / n,
                     'ambiguous_queries': sum(sum(c.values()) for c in groups.values() if len(c) > 1)})
    return rows


def coverage(training, evaluation, *, mode):
    """Preforecast-key overlap only: never fit or score empirical predictions."""
    known = {context(pre, action, past, mode)[0] for _, _, pre, action, past in queries(training)}
    counts = [Counter(queries=0, covered=0) for _ in range(len(evaluation.actions))]
    for t, _, pre, action, past in queries(evaluation):
        counts[t]['queries'] += 1
        counts[t]['covered'] += context(pre, action, past, mode)[0] in known
    return {'training_keys': len(known), 'steps': [dict(step=t, **row) for t, row in enumerate(counts)]}


def audit():
    from . import informative_curriculum as old
    result = {'status': 'PUBLIC_FIXTURE_AND_KEY_AUDIT_NO_MODEL_SCORES', 'gate_g1': 'HOLD_REVISE',
              'independent_oracle': False, 'legacy': {}, 'v2': {}}
    for informative in (False, True):
        condition = 'informative' if informative else 'uninformative'
        train = batch_histories(histories(informative=informative))
        for composition in (False, True):
            name = condition + ('_second_pair' if composition else '_same_pair')
            legacy = batch_histories(old.histories(informative=informative, composition=composition))
            candidate = batch_histories(histories(informative=informative, composition=composition))
            for version, data in (('legacy', legacy), ('v2', candidate)):
                full, current = bounds(data), bounds(data, current_only=True)
                result[version][name] = {'input_sha256': data.digest(), 'history_bounds': full,
                    'current_only_bounds': current, 'all_step_map_ceiling': sum(r['max_correct'] for r in full) /
                     sum(r['queries'] for r in full)}
            result['v2'][name]['key_coverage'] = {mode: coverage(train, candidate, mode=mode)
                                                 for mode in ('prefix', 'local', 'contact')}
    return result


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2, sort_keys=True, allow_nan=False))
