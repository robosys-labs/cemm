"""Evaluator-only persistent-mode oracle for two separately learned pair laws.

Truth-table lookup is independent of the generator's Boolean implementation.
No actual mode, learner, future feedback or simulator is an oracle argument.
"""
from collections import Counter
from hashlib import sha256
from pathlib import Path

from . import acceptance_contract as contract

TABLES = {'nand': ((1, 1), (1, 0)), 'nor': ((1, 0), (0, 0))}


def law_digest(law):
    contract.require(law in TABLES, 'unknown observed pair law')
    return contract.digest({'version': 'multisource-observed-pair-law-v1', 'law': law,
        'target_table_by_source_then_target': TABLES[law], 'source_unchanged': True,
        'hidden_source_slot': {'values': [0, 1], 'probabilities': [.5, .5], 'persistence': 'whole episode'},
        'entities': [3, 4, 5, 6], 'full_initial_anchor': True, 'visible_readings_noiseless': True,
        'actions_and_masks_exogenous': True, 'distinct_contact_operands_only': True,
        'conditioning': 'Delivered past readings and current/past actions only; law is evaluator metadata.'})


def source_digest():
    return sha256(Path(__file__).read_bytes()).hexdigest()


def forecast_episode(case, law):
    law_digest(law)
    case = contract.validate_inputs({'version': 'active-acceptance-input-v1', 'episodes': [case]})['episodes'][0]
    ids = sorted(case['ids'])
    modes = {mode: dict(case['observations'][0]) for mode in (0, 1)}
    result = []
    for t, action in enumerate(case['actions']):
        members = action['participants']
        contract.require(action['kind'] == 'contact' and len(set(members)) == 2,
                         'law oracle requires distinct pair contacts')
        for mode, state in modes.items():
            source, target = members[mode], members[1 - mode]
            state[target] = TABLES[law][state[source]][state[target]]
        counts = Counter(sum(state[name] << (len(ids) - i - 1) for i, name in enumerate(ids))
                         for state in modes.values())
        possible = sorted(counts)
        result.append({'information_key': contract.information_key(case, t), 'possible_worlds': possible,
            'probabilities': [counts[w] / len(modes) for w in possible], 'surviving_modes': sorted(modes)})
        reading = case['observations'][t + 1]
        modes = {mode: state for mode, state in modes.items()
                 if all(value is None or state[name] == value for name, value in reading.items())}
        contract.require(bool(modes), f'delivered evidence contradicts {law} at step {t}')
    return result
