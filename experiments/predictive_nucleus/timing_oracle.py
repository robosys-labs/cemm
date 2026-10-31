"""Evaluator-only timing oracle; independent truth tables and shared fixed mode.

The common-snapshot delta union is supplied event timing semantics. Its events
read one pre-group state; they do not independently resample the physical mode.
Only past delivered observations condition a forecast.
"""
from collections import Counter
from hashlib import sha256
from pathlib import Path

from . import acceptance_contract as common, timing_contract as contract

TABLES = {'nand': ((1, 1), (1, 0)), 'nor': ((1, 0), (0, 0))}


def law_digest(law):
    common.require(law in TABLES, 'unknown timing law')
    return common.digest({'version': 'timing-law-v1', 'law': law,
        'target_table_by_source_then_target': TABLES[law], 'source_unchanged': True,
        'hidden_source_slot': {'values': [0, 1], 'probabilities': [.5, .5], 'persistence': 'whole episode'},
        'ordered': 'Apply contact outputs in list order; no intermediate feedback.',
        'common_snapshot': 'Each contact reads the same world and mode; XOR the anchor with the union of binary deltas.',
        'conditioning': 'Delivered prefix observations only; action timing is observed, law and mode are not.',
        'domain': {'entities': [3, 4, 5, 6], 'full_binary_readings': True, 'distinct_contact_operands': True}})


def source_digest():
    return sha256(Path(__file__).read_bytes()).hexdigest()


def _contact(state, pair, law, mode):
    output = dict(state)
    source, target = pair[mode], pair[1 - mode]
    output[target] = TABLES[law][state[source]][state[target]]
    return output


def _advance(state, action, law, mode):
    if action['kind'] == 'contact':
        return _contact(state, action['participants'], law, mode)
    contacts = action['contacts']
    if action['timing'] == 'ordered':
        for pair in contacts:
            state = _contact(state, pair, law, mode)
        return state
    events = [_contact(state, pair, law, mode) for pair in contacts]
    return {name: value ^ int(any(event[name] != value for event in events)) for name, value in state.items()}


def forecast_episode(case, law):
    law_digest(law)
    case = contract.validate_inputs({'version': 'timing-input-v1', 'episodes': [case]})['episodes'][0]
    ids = sorted(case['ids'])
    modes = {mode: dict(case['observations'][0]) for mode in (0, 1)}
    rows = []
    for step, action in enumerate(case['actions']):
        modes = {mode: _advance(state, action, law, mode) for mode, state in modes.items()}
        counts = Counter(sum(state[name] << (len(ids) - i - 1) for i, name in enumerate(ids))
                         for state in modes.values())
        possible = sorted(counts)
        rows.append({'information_key': contract.information_key(case, step),
            'history_key': contract.history_key(case, step), 'possible_worlds': possible,
            'probabilities': [counts[world] / len(modes) for world in possible], 'surviving_modes': sorted(modes)})
        reading = case['observations'][step + 1]
        modes = {mode: state for mode, state in modes.items() if state == reading}
        common.require(bool(modes), f'delivered evidence contradicts {law} at step {step}')
    return rows
