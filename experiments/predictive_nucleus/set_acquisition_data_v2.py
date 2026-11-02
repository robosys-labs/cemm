"""Fresh native SET compositions; reuse the frozen v1 observed training tape.

Only evaluation identities and action sequences are new. Atomic SET outcomes,
laws, supplied modes and filtering are familiar. No model or fitter is imported.
The v1 information-record schema is retained; v2 study identity is bound by the
source, input and information-law digests, not by changing that schema's ABI.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from itertools import product
from pathlib import Path
import random

from . import acceptance_contract as c, continuation_run as io, set_acquisition_data as old
from .prospective_data import blueprint_digest, template_digest

ROOT = Path(__file__).resolve().parent
VERSION = 'set-acquisition-v2'
EVALUATION_SEED = 20261102182
FAMILIES = ('interleaved_set', 'rotating_set', 'contact_set_feedback')
LAWS = old.LAWS
TRAIN = 'data/set-acquisition-v1/train-inputs.json.xz'
TRAIN_SHA256 = '7fbdddbe4efd188da6f6d0c82c31010a11cabd82b3038dda4e3513260e9c793a'
HISTORY = tuple(f'data/{folder}/{law}-{suffix}' for folder, suffix in (
    ('set-acquisition-v1', 'inputs.json.xz'),
    ('multisource-law-v1', 'evaluation-inputs.json'),
    ('hidden-cycle-v1', 'inputs.json')) for law in LAWS)


def source_digest():
    return sha256(Path(__file__).read_bytes() + old.source_digest().encode()).hexdigest()


def law_digest(law):
    return c.digest({'study': VERSION, 'inherited_semantic_law_sha256': old.law_digest(law),
        'evaluation_seed': EVALUATION_SEED, 'families': FAMILIES,
        'scope': 'Full observed prefixes; new five-action compositions, not unseen atomic SET outcomes.'})


def _actions(family, handles, value, direction):
    c.require(family in FAMILIES and direction in (0, 1), 'unknown v2 composition or direction')
    a, b, d = handles[:3]
    if family == 'interleaved_set':
        return [old._set(a, value), old._set(b, 1 - value), old._set(a, 1 - value),
                old._set(d, value), old._set(b, value)]
    if family == 'rotating_set':
        return [old._set(a, value), old._set(b, 1 - value), old._set(d, value),
                old._set(a, 1 - value), old._set(d, 1 - value)]
    contact = lambda x, y: {'kind': 'contact', 'participants': [y, x] if direction else [x, y]}
    return [contact(a, b), old._set(b, value), contact(b, d), old._set(d, 1 - value), contact(d, a)]


def _overlap(current, prior):
    return {label: len({fn(e) for e in current} & {fn(e) for e in prior})
            for label, fn in (('blueprint', blueprint_digest), ('template', template_digest))} | {
        'identity': len({i for e in current for i in e['ids']} & {i for e in prior for i in e['ids']})}


def build_assets():
    c.require(io._hash(ROOT / TRAIN) == TRAIN_SHA256, 'frozen v1 observed training tape differs')
    train = c.validate_inputs(io._read(ROOT / TRAIN))
    c.require(len(train['episodes']) == 48 and all(len(e['actions']) == 1 and
        e['actions'][0]['kind'] == 'set' for e in train['episodes']), 'reused training inventory differs')
    laws = {law: {'inputs': {'version': 'active-acceptance-input-v1', 'episodes': []},
                  'cases': [], 'gold': [], 'information': []} for law in LAWS}
    for family, n, core, value in product(FAMILIES, range(3, 7), product((0, 1), repeat=3), (0, 1)):
        root = [VERSION, EVALUATION_SEED, family, n, core, value]
        rng = random.Random(int(c.digest(root), 16))
        handles = [c.digest(['identity', root, i])[:20] for i in range(n)]
        anchor = dict(zip(handles, [*core, *[rng.randrange(2) for _ in range(n - 3)]], strict=True))
        ids = handles.copy(); rng.shuffle(ids)
        lineage = c.digest(['lineage', root]); bridge = family == 'contact_set_feedback'
        for mode, direction in product((0, 1), repeat=2) if bridge else ((0, 0),):
            pair = c.digest(['pair', lineage, mode]) if bridge else None
            episode = c.digest(['episode', root, mode, direction])[:32]
            blueprint = {'episode': episode, 'ids': ids, 'observations': [anchor],
                'coverage': [ids.copy() for _ in range(5)], 'actions': _actions(family, handles, value, direction)}
            for law, bundle in laws.items():
                case = old._realize(blueprint, law, mode); forecasts = old.forecast_episode(case, law)
                bundle['inputs']['episodes'].append(case)
                bundle['cases'].append({'episode': episode, 'family': family, 'partition': 'held_out',
                    'lineage': lineage, 'pair_id': pair, 'direction': direction if bridge else None,
                    'entities': n, 'hidden_source_slot': mode if bridge else None, 'requested': value,
                    'set_points': [{'step': t, 'prior': case['observations'][t][a['participants'][0]],
                        'requested': a['value'], 'changed': case['observations'][t][a['participants'][0]] != a['value']}
                        for t, a in enumerate(case['actions']) if a['kind'] == 'set']})
                bundle['gold'].append({'episode': episode, 'truth': deepcopy(case['observations']),
                    'possible_worlds': [f['possible_worlds'] for f in forecasts],
                    'information_keys': [f['information_key'] for f in forecasts]})
                bundle['information'].append({'episode': episode, 'forecasts': forecasts})
    audit = {'train_episodes': 48, 'train_forecasts': 48, 'training_reused_from': TRAIN,
        'training_file_sha256': TRAIN_SHA256, 'training_input_sha256': c.digest(train),
        'evaluation_episodes_per_law': 384, 'evaluation_forecasts_per_law': 1920,
        'role_pairs_per_law': 128, 'evaluation_seed': EVALUATION_SEED,
        'information_schema': 'set-acquisition-v1-information',
        'scope': 'New identities and five-action templates relative to v1 and the explicitly listed native banks. '
            'Training bytes and atomic SET tuples are reused. Law/mode/reversal views are dependent. '
            'No exhaustive cross-project novelty or independent custody claim.'}
    for law, bundle in laws.items():
        inputs = c.validate_inputs(bundle['inputs'])
        identity = {'input_sha256': c.digest(inputs), 'source_sha256': source_digest(),
                    'information_law_sha256': law_digest(law)}
        oracle = {'version': 'active-acceptance-oracle-v1', **identity, 'episodes': bundle.pop('gold')}
        c.validate_oracle(oracle, inputs, {**identity, 'oracle_source_sha256': identity['source_sha256'],
                                          'oracle_sha256': c.digest(oracle)})
        bundle['oracle'] = oracle
        bundle['information'] = {'version': 'set-acquisition-v1-information', **identity,
                                 'episodes': bundle['information']}
        rows = [f for e in bundle['information']['episodes'] for f in e['forecasts']]
        audit[law] = {'families': dict(Counter(m['family'] for m in bundle['cases'])),
            'identifiable_points': sum(len(f['possible_worlds']) == 1 for f in rows),
            'ambiguous_points': sum(len(f['possible_worlds']) > 1 for f in rows),
            'expected_best_all_action_accuracy': sum(max(f['probabilities']) for f in rows) / len(rows)}
        c.require(len(inputs['episodes']) == 384 and len(rows) == 1920, 'v2 evaluation inventory differs')
    evaluation = laws['nand']['inputs']['episodes']
    audit['split_overlap'] = _overlap(evaluation, train['episodes'])
    audit['historical_overlap'] = {}
    for name in HISTORY:
        prior = c.validate_inputs(io._read(ROOT / name))['episodes']
        audit['historical_overlap'][name] = {'sha256': io._hash(ROOT / name),
            'episode_views': len(prior), **_overlap(evaluation, prior)}
    atomic = lambda episodes: sorted({(e['observations'][t][a['participants'][0]], a['value'])
        for e in episodes for t, a in enumerate(e['actions']) if a['kind'] == 'set'})
    audit['atomic_set_tuples'] = {'train': atomic(train['episodes']), 'evaluation': atomic(evaluation),
                                 'novel_atomic_tuples': []}
    c.require(not any(audit['split_overlap'].values()) and all(not any(row[k] for k in
        ('blueprint', 'template', 'identity')) for row in audit['historical_overlap'].values()) and
        audit['atomic_set_tuples']['train'] == audit['atomic_set_tuples']['evaluation'] ==
        [(0, 0), (0, 1), (1, 0), (1, 1)], 'v2 freshness or atomic inventory differs')
    return {'train': train, 'laws': laws, 'audit': audit}
