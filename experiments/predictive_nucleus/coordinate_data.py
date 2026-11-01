"""Fresh ordered graphs for the fixed-budget response-coordinate comparison.

All words/layouts and laws are opened; only event structures are fresh. Learners
receive the identical prior observed tape and never import this evaluator.
"""
from itertools import product

from . import acceptance_contract as c, continuation_run as io, centering_data as previous
from .bilingual_contract import validate_inputs
from .saturation_data import CORES

VERSION = 'coordinate-v1'
TRAINING = previous.TRAINING
SCHEDULES = {'fanout_cross4': (4, ((0, 1), (0, 2), (0, 3), (1, 2))),
             'chain_shortcut5': (5, ((0, 1), (1, 2), (2, 3), (3, 4), (1, 3)))}


def novelty(schedules):
    audit = previous.novelty(schedules)
    opened = {previous.ordered_shape(edges) for _, edges in previous.SCHEDULES.values()}
    c.require(not {previous.ordered_shape(edges) for _, edges in schedules.values()} & opened,
              'previously opened centering event structure')
    audit['compared_opened_families'] += ['centering-' + key for key in previous.SCHEDULES]
    return audit


def build_assets():
    shape_audit = novelty(SCHEDULES)
    training_hash = io._hash(TRAINING)
    c.require(training_hash == io._read(io.ROOT / 'centering_freeze_v1.json')['train-inputs.json.xz'],
              'previous training bytes changed')
    training = validate_inputs(io._read(TRAINING)); training_cells = set()
    for record in training['episodes']:
        for event in record['utterances']:
            tokens = event['text'].split()
            word = next(w for w in tokens if w not in record['entities'])
            training_cells.add((word, {0: 'vos', 1: 'svo', 2: 'osv'}[tokens.index(word)]))
    banks = {}
    for law in ('nand', 'nor'):
        records, cases = [], []
        for family, (n, edges) in SCHEDULES.items():
            for core, mode, direction, pair, rotation, polarity in product(
                    CORES, (0, 1), (0, 1), (4, 5), range(3), (0, 1)):
                tag = [VERSION, 'challenge', family, core, pair, rotation]
                words = [(4 + (pair + t) % 2, (rotation + t) % 2) for t in range(len(edges))]
                words[-1] = pair, polarity
                layouts = [(rotation + t) % 3 for t in range(len(edges))]
                record, gold = previous.episode(tag, n, core, mode, direction, law, edges, words, layouts)
                gold.update(family=family, polarity=polarity,
                    lexical_pair_id=c.digest([tag, mode, direction]),
                    role_pair_id=c.digest([tag, mode, polarity]))
                for cell in gold['cells']:
                    c.require(cell['held'] == ((cell['word'], cell['layout']) not in training_cells),
                              'held cell mislabeled')
                records.append(record); cases.append(gold)
        inputs = validate_inputs({'version': 'bilingual-input-v1', 'episodes': records})
        banks[law] = {'inputs': inputs, 'oracle': {'version': 'binding-oracle-v1',
            'input_sha256': c.digest(inputs), 'episodes': cases}}
    names = lambda v: {s for r in v['episodes'] for s in r['entities']}
    c.require(not names(training) & names(banks['nand']['inputs']), 'entity split overlaps')
    cells = {(cell['word'], cell['layout']) for g in banks['nand']['oracle']['episodes'] for cell in g['cells']}
    return {'train': training, **banks, 'audit': {
        'training_file_sha256': training_hash, 'training_content_sha256': c.digest(training),
        'train_forecasts': sum(len(r['utterances']) for r in training['episodes']),
        'challenge_forecasts_per_law': sum(len(r['utterances']) for r in banks['nand']['inputs']['episodes']),
        'challenge_episodes_per_law': len(banks['nand']['inputs']['episodes']),
        'training_cells': sorted(training_cells), 'training_withheld_cells': sorted(cells - training_cells),
        'new_words': [], 'new_lexical_layout_cells': [], 'families': list(SCHEDULES),
        **shape_audit, 'independent_custody': False,
        'scope': 'Fresh ordered event structures only; words/layouts/laws already opened. Same observed training tape. Public same-team custody.'}}
