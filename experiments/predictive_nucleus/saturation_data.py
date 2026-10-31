"""Evaluator-only fresh lexical/layout bank for a paired activation ablation.

Reuse the existing generator physics, but introduce two genuinely new lexical
pairs and four/five-participant graphs. Old training stays training; all previously
opened challenge banks are labeled retention. No learner imports this module.
"""
from copy import deepcopy
from itertools import product

from . import acceptance_contract as c, continuation_run as io, binding_data as old
from .bilingual_contract import validate_inputs

VERSION = 'saturation-v1'
WORDS = {'tav': 'kef', 'pel': 'ruz', 'zun': 'wom', 'vek': 'jit'}
HOMES = {4: 0, 5: 2}
SWAPS = {a: b for x, y in (('kef', 'ruz'), ('wom', 'jit')) for a, b in ((x, y), (y, x))}
SCHEDULES = {'diamond4': (4, ((0, 1), (0, 2), (1, 3), (2, 3))),
             'bridge5': (5, ((0, 1), (2, 3), (1, 2), (3, 4), (4, 0)))}
CORES = ((0, 0, 1), (0, 1, 0), (1, 0, 1), (1, 1, 0))


def episode(tag, n, core, mode, direction, law, edges, words, layouts):
    record, gold = old._episode([VERSION, tag], n, core, mode, direction, law, edges, words, layouts)
    for event, cell, (pair, _) in zip(record['utterances'], gold['cells'], words, strict=True):
        event['text'] = ' '.join(WORDS.get(w, w) for w in event['text'].split())
        cell['word'] = WORDS[cell['word']]
        cell['held'] = cell['layout'] != old.LAYOUTS[HOMES[pair]]
    return record, gold


def build_assets():
    training = deepcopy(io._read(io.ROOT / 'data/binding-v1/train-inputs.json.xz'))
    old_count = sum(len(e['utterances']) for e in training['episodes'])
    new_cells = set()
    for n, core, mode, direction, pair, polarity in product(
            (3, 4), CORES, (0, 1), (0, 1), (4, 5), (0, 1)):
        layout = HOMES[pair]
        record, gold = episode(['train', n, core, pair], n, core, mode, direction, 'nand',
                               ((0, 1),), [(pair, polarity)], [layout])
        training['episodes'].append(record)
        new_cells.add((gold['cells'][0]['word'], old.LAYOUTS[layout]))
    training = validate_inputs(training)
    banks = {}
    for law in ('nand', 'nor'):
        records, cases = [], []
        for family, (n, edges) in SCHEDULES.items():
            for core, mode, direction, pair, rotation, polarity in product(
                    CORES, (0, 1), (0, 1), (4, 5), range(3), (0, 1)):
                tag = ['challenge', family, core, pair, rotation]
                words = [(4 + (pair + t) % 2, (rotation + t) % 2) for t in range(len(edges))]
                words[-1] = pair, polarity
                layouts = [(rotation + t) % 3 for t in range(len(edges))]
                record, gold = episode(tag, n, core, mode, direction, law, edges, words, layouts)
                gold.update(family=family, polarity=polarity,
                    lexical_pair_id=c.digest([VERSION, tag, mode, direction]),
                    role_pair_id=c.digest([VERSION, tag, mode, polarity]))
                records.append(record); cases.append(gold)
        inputs = validate_inputs({'version': 'bilingual-input-v1', 'episodes': records})
        banks[law] = {'inputs': inputs, 'oracle': {'version': 'binding-oracle-v1',
            'input_sha256': c.digest(inputs), 'episodes': cases}}
    names = lambda v: {s for r in v['episodes'] for s in r['entities']}
    c.require(not names(training) & names(banks['nand']['inputs']), 'entity split overlaps')
    cells = {(cell['word'], cell['layout']) for g in banks['nand']['oracle']['episodes'] for cell in g['cells']}
    for bank in banks.values():
        for g in bank['oracle']['episodes']:
            for cell in g['cells']:
                c.require(cell['held'] == ((cell['word'], cell['layout']) not in new_cells), 'held cell mislabeled')
    return {'train': training, **banks, 'audit': {
        'old_training_forecasts': old_count,
        'train_forecasts': sum(len(r['utterances']) for r in training['episodes']),
        'challenge_forecasts_per_law': sum(len(r['utterances']) for r in banks['nand']['inputs']['episodes']),
        'challenge_episodes_per_law': len(banks['nand']['inputs']['episodes']),
        'training_cells_new': sorted(new_cells), 'held_cells_new': sorted(cells - new_cells),
        'new_words': list(WORDS.values()), 'families': list(SCHEDULES),
        'independent_custody': False,
        'scope': 'Fresh word-layout cells and four/five-participant graphs; same supplied grammar/physics, public same-team custody.'}}
