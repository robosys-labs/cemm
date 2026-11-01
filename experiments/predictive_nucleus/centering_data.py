"""Evaluator-only new event structures with the exact previous training tape.

Only ordered interaction structures are new. Words, layouts, physics and the
eight training-withheld lexical cells have already appeared in open studies.
No learner imports this generator or receives its action/order annotations.
"""
from itertools import permutations, product

from . import acceptance_contract as c, continuation_run as io, binding_data as old
from . import saturation_data as previous
from .bilingual_contract import validate_inputs
from .bilingual_data import FAMILIES

VERSION = 'centering-v1'
TRAINING = io.ROOT / 'data/saturation-v1/train-inputs.json.xz'
SCHEDULES = {'relay4': (4, ((0, 1), (1, 2), (2, 0), (0, 3))),
             'fork_return5': (5, ((0, 1), (0, 2), (2, 3), (1, 4), (4, 0)))}


def ordered_shape(edges):
    """Canonical active-entity shape, ignoring directions but retaining time.

    Renamed entities, unused extra slots and reversed lexical effects cannot
    manufacture novelty. At most six active entities keep this bounded.
    """
    vertices = sorted({v for edge in edges for v in edge})
    c.require(0 < len(vertices) <= 6 and all(len(e) == 2 for e in edges), 'invalid schedule')
    local = {v: i for i, v in enumerate(vertices)}
    return min(tuple(tuple(sorted((p[local[a]], p[local[b]]))) for a, b in edges)
               for p in permutations(range(len(vertices))))


def novelty(schedules):
    prior = {**{'bilingual-' + k: v for part in FAMILIES.values() for k, v in part.items()},
             **{'binding-' + k: v for k, v in old.SCHEDULES.items()},
             **{'saturation-' + k: v[1] for k, v in previous.SCHEDULES.items()}}
    opened = {ordered_shape(edges) for edges in prior.values()}
    shapes = {name: ordered_shape(edges) for name, (_, edges) in schedules.items()}
    c.require(len(set(shapes.values())) == len(shapes), 'duplicate proposed event structure')
    c.require(not set(shapes.values()) & opened, 'previously opened event structure')
    for n, edges in schedules.values():
        c.require(type(n) is int and 3 <= n <= 6 and
                  {v for edge in edges for v in edge} == set(range(n)), 'inactive or invalid schedule entity')
    return {'new_ordered_shapes': {k: list(map(list, v)) for k, v in shapes.items()},
            'compared_opened_families': sorted(prior),
            'equivalence': 'Ignore edge directions and active-entity spelling; preserve event order. Inactive slots do not establish novelty.'}


def episode(tag, n, core, mode, direction, law, edges, words, layouts):
    record, gold = old._episode([VERSION, tag], n, core, mode, direction, law, edges, words, layouts)
    for event, cell, (pair, _) in zip(record['utterances'], gold['cells'], words, strict=True):
        event['text'] = ' '.join(previous.WORDS.get(w, w) for w in event['text'].split())
        cell['word'] = previous.WORDS[cell['word']]
        cell['held'] = cell['layout'] != old.LAYOUTS[previous.HOMES[pair]]
    return record, gold


def build_assets():
    shape_audit = novelty(SCHEDULES)
    training_hash = io._hash(TRAINING)
    c.require(training_hash == io._read(io.ROOT / 'saturation_freeze_v1.json')['train-inputs.json.xz'],
              'previous training bytes changed')
    training = validate_inputs(io._read(TRAINING))
    training_cells = set()
    for record in training['episodes']:
        for event in record['utterances']:
            words = event['text'].split(); word = next(w for w in words if w not in record['entities'])
            training_cells.add((word, {0: 'vos', 1: 'svo', 2: 'osv'}[words.index(word)]))
    banks = {}
    for law in ('nand', 'nor'):
        records, cases = [], []
        for family, (n, edges) in SCHEDULES.items():
            for core, mode, direction, pair, rotation, polarity in product(
                    previous.CORES, (0, 1), (0, 1), (4, 5), range(3), (0, 1)):
                tag = ['challenge', family, core, pair, rotation]
                words = [(4 + (pair + t) % 2, (rotation + t) % 2) for t in range(len(edges))]
                words[-1] = pair, polarity
                layouts = [(rotation + t) % 3 for t in range(len(edges))]
                record, gold = episode(tag, n, core, mode, direction, law, edges, words, layouts)
                gold.update(family=family, polarity=polarity,
                    lexical_pair_id=c.digest([VERSION, tag, mode, direction]),
                    role_pair_id=c.digest([VERSION, tag, mode, polarity]))
                for cell in gold['cells']:
                    c.require(cell['held'] == ((cell['word'], cell['layout']) not in training_cells), 'held cell mislabeled')
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
        'scope': 'Fresh ordered event structures only; identical prior training tape, opened words/layouts/physics. Held flags mean absent from training, not new to prior evaluation. Public same-team custody.'}}
