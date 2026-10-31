"""Evaluator-only third-layout/mixed-sequence bank; no model imports or fitting.

New evidence is a third layout and two new lexical pairs composed in mixed-layout
four/five-contact schedules. Old word/layout failures remain opened retention,
not a newly independent challenge. The public author and custodian are unchanged.
"""
from collections import Counter
from itertools import product

from . import acceptance_contract as c, continuation_run as io
from .bilingual_contract import validate_inputs
from .bilingual_data import _step

PAIRS = (('contacts', 'receives'), ('touches', 'accepts'), ('dax', 'vok'),
         ('mip', 'nuz'), ('tav', 'pel'), ('zun', 'vek'))
LAYOUTS = ('svo', 'osv', 'vos')
# Home layouts are training design, never supplied as learner labels.
HOMES = (0, 0, 1, 1, 0, 1)
BRIDGES = (0, 2)
SCHEDULES = {'return4': ((0, 1), (1, 2), (2, 1), (1, 0)),
             'cross5': ((0, 1), (0, 2), (1, 2), (2, 0), (0, 1))}
SWAPS = {a: b for pair in PAIRS for a, b in (pair, pair[::-1])}


def render(ids, edge, pair, polarity, layout):
    """Generator grammar only; VOS introduces a third distinct identity mask."""
    a, b = edge; word = PAIRS[pair][polarity]
    words = ((ids[a], word, ids[b]), (ids[b], ids[a], word), (word, ids[b], ids[a]))[layout]
    native = [0, b, a, -1] if polarity else [0, a, b, -1]
    mentions = [ids.index(token) for token in words if token in ids]
    order = int(native[1] != mentions[0])
    return ' '.join(words), native, order


def _episode(tag, n, core, mode, direction, law, edges, words, layouts):
    ids = ['B' + c.digest(['binding-v1-name', tag, n, i])[:15] for i in range(n)]
    # Stable nontrivial roster permutations; roles never use ref spelling.
    shift = int(c.digest(tag)[:4], 16) % n
    roster = ids[shift:] + ids[:shift]; slots = [roster.index(name) for name in ids]
    initial = [core[i % len(core)] for i in range(n)]
    initial = [initial[ids.index(name)] for name in roster]
    state, context = [0] * n, []
    for action in [[0, 0, 1, -1]] + [[1, i, -1, bit] for i, bit in enumerate(initial)]:
        state = _step(state, action, mode, law)
        context.append({'action': action, 'reading': state.copy()})
    events, actions, truth, opposite, orders, cells = [], [], [], [], [], []
    for edge, (pair, polarity), layout in zip(edges, words, layouts, strict=True):
        edge = [slots[i] for i in (edge[::-1] if direction else edge)]
        text, action, order = render(roster, edge, pair, polarity, layout)
        opposite.append(_step(state, [0, action[2], action[1], -1], mode, law))
        state = _step(state, action, mode, law)
        events.append({'text': text, 'reading': state.copy()})
        actions.append(action); truth.append(state.copy()); orders.append(order)
        cells.append({'word': PAIRS[pair][polarity], 'layout': LAYOUTS[layout],
                      'held': pair not in BRIDGES and layout != HOMES[pair]})
    identity = c.digest([tag, mode, direction, words, layouts])[:32]
    return ({'id': identity, 'entities': roster, 'anchor': [0] * n,
             'context': context, 'utterances': events},
            {'id': identity, 'law': law, 'mode': mode, 'direction': direction,
             'actions': actions, 'action_orders': orders, 'truth': truth,
             'opposite_truth': opposite, 'cells': cells})


def build_assets():
    train, training_cells = [], set()
    for n, core, mode, direction, pair, polarity in product(
            (3, 4), ((0, 0, 0), (0, 1, 1), (1, 0, 1), (1, 1, 0)),
            (0, 1), (0, 1), range(len(PAIRS)), (0, 1)):
        for layout in range(3) if pair in BRIDGES else (HOMES[pair],):
            tag = ['train', n, core, pair, layout]
            episode, _ = _episode(tag, n, core, mode, direction, 'nand', ((0, 1),),
                                  [(pair, polarity)], [layout])
            train.append(episode); training_cells.add((PAIRS[pair][polarity], LAYOUTS[layout]))
    # Rehearse only old TRAIN evidence. Never import an old challenge into fitting.
    rehearsal = io._read(io.ROOT / 'data/bilingual-v1/train-inputs.json.xz')
    train = validate_inputs({'version': 'bilingual-input-v1', 'episodes': rehearsal['episodes'] + train})
    banks = {}
    for law in ('nand', 'nor'):
        episodes, gold = [], []
        for family, edges in SCHEDULES.items():
            for n, bit, mode, direction, pair, rotation, polarity in product(
                    (3, 6), (0, 1), (0, 1), (0, 1), (4, 5), range(3), (0, 1)):
                tag = ['challenge', family, n, bit, pair, rotation]
                words = [(4 + (pair + t) % 2, (rotation + t) % 2) for t in range(len(edges))]
                words[-1] = (pair, polarity)
                layouts = [(rotation + t) % 3 for t in range(len(edges))]
                episode, case = _episode(tag, n, (bit,) * 3, mode, direction, law, edges, words, layouts)
                case.update(family=family,
                    lexical_pair_id=c.digest([tag, mode, direction]),
                    role_pair_id=c.digest([tag, mode, polarity]), polarity=polarity)
                episodes.append(episode); gold.append(case)
        inputs = validate_inputs({'version': 'bilingual-input-v1', 'episodes': episodes})
        banks[law] = {'inputs': inputs, 'oracle': {'version': 'binding-oracle-v1',
            'input_sha256': c.digest(inputs), 'episodes': gold}}
    challenge_cells = {(x['word'], x['layout']) for e in banks['nand']['oracle']['episodes'] for x in e['cells']}
    audit = {'train_episodes': len(train['episodes']),
        'train_forecasts': sum(len(e['utterances']) for e in train['episodes']),
        'training_cells': sorted(training_cells), 'held_cells': sorted(challenge_cells - training_cells),
        'challenge_episodes_per_law': len(banks['nand']['inputs']['episodes']),
        'challenge_forecasts_per_law': sum(len(e['utterances']) for e in banks['nand']['inputs']['episodes']),
        'families': dict(Counter(e['family'] for e in banks['nand']['oracle']['episodes'])),
        'third_layout': 'vos', 'new_pairs': PAIRS[4:],
        'independent_custody': False,
        'novelty': 'New lexical pairs, third layout, mixed-layout return4/cross5 schedules; not new physics or independent authorship.'}
    names = lambda bank: {v for e in bank['episodes'] for v in e['entities']}
    c.require(not names(train) & names(banks['nand']['inputs']), 'entity split overlaps')
    for bank in banks.values():
        for case in bank['oracle']['episodes']:
            for cell in case['cells']:
                c.require(cell['held'] == ((cell['word'], cell['layout']) not in training_cells), 'held cell mislabeled')
    return {'train': train, **banks, 'audit': audit}
