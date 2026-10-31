"""Evaluator-side bilingual trajectories; learner files contain observed evidence only.

Names, token boundaries and the one-contact-per-utterance interface are supplied.
SVO/OSV realization and the Boolean simulator belong to this generator, never
candidate inference. Every physical trajectory keeps its bilingual/synonym twins.
"""
from collections import Counter
from itertools import product
import random

from . import acceptance_contract as contract
from .bilingual_contract import validate_inputs

FAMILIES = {
    'train': {'single': ((0, 1),), 'two_contact': ((0, 1), (1, 2))},
    'challenge': {'chain': ((0, 1), (1, 2), (2, 3)),
                  'fork': ((0, 1), (0, 2), (0, 1)),
                  'cycle': ((0, 1), (1, 2), (2, 0)),
                  'repeated': ((0, 1),) * 5,
                  'disjoint': ((0, 1), (2, 3), (0, 1), (2, 3))}}
CORES = {'train': ((0, 0, 0), (0, 1, 1), (1, 0, 1), (1, 1, 0)),
         'challenge': ((0, 0, 0), (1, 1, 1))}
LEXEMES = {'svo': ('contacts', 'touches'), 'osv': ('dax', 'mip')}
LAWS = ('nand', 'nor')


def _step(before, action, mode, law):
    """Simulator implementation, deliberately absent from the model module."""
    after = list(before)
    if action[0] == 1:
        after[action[1]] = action[3]
    else:
        first, second = action[1:3]
        source, target = (first, second) if mode == 0 else (second, first)
        a, b = before[source], before[target]
        after[target] = 1 - (a & b) if law == 'nand' else 1 - (a | b)
    return after


def _bank(config, split, law):
    inputs, gold = [], []
    counts = config['data'][split + '_entity_counts']
    for family, edges in FAMILIES[split].items():
        for n in counts:
            if max(max(edge) for edge in edges) >= n: continue
            for core in CORES[split]:
                root = [config['version'], split, config['data']['split_seeds'][split], family, n, core]
                lineage = contract.digest(['bilingual-lineage-v1', *root])
                rng = random.Random(int(lineage, 16))
                handles = ['E' + contract.digest(['bilingual-name-v1', *root, i])[:14] for i in range(n)]
                ids = handles.copy(); rng.shuffle(ids)
                slot = [ids.index(handle) for handle in handles]
                values = [*core, *[rng.randrange(2) for _ in range(n - 3)]]
                initial = [values[handles.index(handle)] for handle in ids]
                for mode, direction, language, synonym in product((0, 1), (0, 1), LEXEMES, (0, 1)):
                    physical = contract.digest(['bilingual-physical-v1', lineage, mode, direction])
                    episode_id = contract.digest([physical, language, synonym])[:32]
                    pair = contract.digest(['bilingual-role-pair-v1', lineage, mode, language, synonym])
                    state = [0] * n; context = []
                    acquisition = [[0, 0, 1, -1]] + [[1, i, -1, bit] for i, bit in enumerate(initial)]
                    for action in acquisition:
                        state = _step(state, action, mode, law)
                        context.append({'action': action, 'reading': state.copy()})
                    events, actions, truth, opposite, orders, lexemes = [], [], [], [], [], []
                    for t, edge in enumerate(edges):
                        first, second = [slot[i] for i in (edge[::-1] if direction else edge)]
                        action = [0, first, second, -1]
                        word_index = synonym if split == 'train' else (synonym + t) % 2
                        word = LEXEMES[language][word_index]
                        words = [ids[first], word, ids[second]] if language == 'svo' else [ids[second], ids[first], word]
                        opposite.append(_step(state, [0, second, first, -1], mode, law))
                        state = _step(state, action, mode, law)
                        events.append({'text': ' '.join(words), 'reading': state.copy()})
                        actions.append(action); truth.append(state.copy()); orders.append(0 if language == 'svo' else 1)
                        lexemes.append(word)
                    inputs.append({'id': episode_id, 'entities': ids.copy(), 'anchor': [0] * n,
                                   'context': context, 'utterances': events})
                    gold.append({'id': episode_id, 'lineage': lineage, 'physical_id': physical,
                        'role_pair_id': pair, 'bilingual_pair_id': contract.digest([physical, synonym]),
                        'synonym_pair_id': contract.digest([physical, language]),
                        'direction': direction, 'language': language, 'synonym': synonym, 'family': family,
                        'mode': mode, 'law': law, 'actions': actions, 'action_orders': orders,
                        'truth': truth, 'opposite_truth': opposite, 'initial_bits': initial.copy(),
                        'lexemes': lexemes, 'canonical_slots': slot.copy()})
    envelope = validate_inputs({'version': 'bilingual-input-v1', 'episodes': inputs})
    return {'inputs': envelope, 'oracle': {'version': 'bilingual-oracle-v1',
            'input_sha256': contract.digest(envelope), 'episodes': gold}}


def build_assets(config):
    contract.require(contract.identifier(config.get('version')), 'study version required')
    settings = config['data']
    contract.fields(settings, ('split_seeds', 'train_entity_counts', 'challenge_entity_counts'))
    contract.fields(settings['split_seeds'], ('train', 'challenge'))
    seeds = list(settings['split_seeds'].values())
    contract.require(all(type(seed) is int and seed >= 20261031000 for seed in seeds) and
                     len(set(seeds)) == 2, 'fresh disjoint split seeds required')
    for split in ('train', 'challenge'):
        counts = settings[split + '_entity_counts']
        contract.require(type(counts) is list and counts == sorted(set(counts)) and counts and
            all(type(n) is int and 3 <= n <= 6 for n in counts), 'invalid entity count inventory')
    train = _bank(config, 'train', 'nand')
    challenge = {law: _bank(config, 'challenge', law) for law in LAWS}
    audit = {'training_law': 'nand', 'transfer_law': 'nor', 'full_feedback': True,
        'dependency': 'Modes, directions, bilingual and synonym views share trajectories; these are not independent trials.',
        'supplied': ['opaque entity handles', 'whitespace token boundaries', 'one contact per utterance',
                     'native observed acquisition and reset events', 'full noiseless endpoint observations']}
    for split, bank in [('train', train), *[(law, bank) for law, bank in challenge.items()]]:
        records, cases = bank['inputs']['episodes'], bank['oracle']['episodes']
        audit[split] = {'episodes': len(records), 'forecasts': sum(len(r['utterances']) for r in records),
            'lineages': len({r['lineage'] for r in cases}), 'physical_trajectories': len({r['physical_id'] for r in cases}),
            'role_pairs': len({r['role_pair_id'] for r in cases}),
            'bilingual_pairs': len({r['bilingual_pair_id'] for r in cases}),
            'synonym_pairs': len({r['synonym_pair_id'] for r in cases}),
            'critical_forecasts': sum(a != b for r in cases for a, b in zip(r['truth'], r['opposite_truth'], strict=True)),
            'families': dict(Counter(r['family'] for r in cases)),
            'entity_counts': dict(Counter(len(r['entities']) for r in records))}
    names = [set(name for e in b['inputs']['episodes'] for name in e['entities']) for b in (train, challenge['nand'])]
    audit['split_overlap'] = {'entity_names': len(names[0] & names[1]),
        'lineages': len({e['lineage'] for e in train['oracle']['episodes']} &
                        {e['lineage'] for e in challenge['nand']['oracle']['episodes']}),
        'whole_families': len(set(FAMILIES['train']) & set(FAMILIES['challenge']))}
    contract.require(not any(audit['split_overlap'].values()), 'bilingual split leakage')
    return {'train': train, 'challenge': challenge, 'audit': audit}
