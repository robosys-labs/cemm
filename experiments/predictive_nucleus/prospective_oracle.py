"""Evaluator-only exact alternatives for the declared persistent binary-contact law.

Transitions compose affine maps over GF(2); no simulator or learner is imported.
An episode's hidden mode is retained even when its current world coincides with
another mode. This oracle assumes the declared exogenous design, not its proof.
"""
from collections import Counter
from hashlib import sha256
from pathlib import Path

from . import acceptance_contract as contract


LAW = {
    'version': 'prospective-binary-contact-information-law-v1',
    'world_contract': 'binary-contact-v1',
    'entities': [3, 4, 5, 6],
    'world_order': 'lexicographic binary vectors in sorted physical-ID order',
    'initial_anchor': 'complete, noiseless, independent of hidden source slot',
    'hidden_source_slot': {'values': [0, 1], 'probabilities': [0.5, 0.5],
                           'persistence': 'one fixed mode for the whole episode'},
    'contact': 'source = participants[mode]; target = participants[1-mode]; target ^= source',
    'self_contact': 'one physical coordinate; its GF(2) sum with itself is zero',
    'set': 'replace exactly the named coordinate with the supplied binary value',
    'observe': 'identity transition',
    'readings': 'noiseless visible binary values; null is absent evidence',
    'design': 'actions, selected coverage, missingness and opaque IDs are exogenous to hidden mode and outcomes',
    'conditioning': 'delivered observations before prediction, past/current actions and selected coverage only',
    'excluded': ['actual hidden mode', 'evaluator family', 'current feedback', 'future observations/actions'],
    'scope': 'evaluator-only law-conditional probabilities; no independent-custody or model-performance claim',
}


def law_digest():
    return contract.digest(LAW)


def source_digest():
    return sha256(Path(__file__).read_bytes()).hexdigest()


def forecast_episode(case):
    """Return exact pre-feedback support, probabilities and persistent mode IDs.

    The initial mode prior is uniform. Deterministic transitions and noiseless,
    exogenous readings preserve equal weights among surviving modes. A complete
    episode is rejected if any delivered feedback contradicts both alternatives.
    """
    case = contract.validate_inputs({'version': 'active-acceptance-input-v1',
                                     'episodes': [case]})['episodes'][0]
    ids = sorted(case['ids'])
    n = len(ids)
    # Each coordinate is an affine form in the original anchor; bit n is the
    # constant term. Row XOR composes contact, including aliased coordinates.
    anchor = (1 << n) | sum(case['observations'][0][name] << (n - i - 1)
                            for i, name in enumerate(ids))
    forms = {mode: [1 << (n - i - 1) for i in range(n)] for mode in (0, 1)}
    forecasts = []
    for t, action in enumerate(case['actions']):
        operands = [ids.index(name) for name in action['participants']]
        states = {}
        for mode, rows in forms.items():
            if action['kind'] == 'contact':
                rows[operands[1 - mode]] ^= rows[operands[mode]]
            elif action['kind'] == 'set':
                rows[operands[0]] = action['value'] << n
            states[mode] = [(row & anchor).bit_count() % 2 for row in rows]
        mass = Counter(sum(bit << (n - i - 1) for i, bit in enumerate(bits)) for bits in states.values())
        possible = sorted(mass)
        forecasts.append({'information_key': contract.information_key(case, t),
                          'possible_worlds': possible,
                          'probabilities': [mass[world] / len(forms) for world in possible],
                          'surviving_modes': sorted(forms)})
        reading = case['observations'][t + 1]
        forms = {mode: rows for mode, rows in forms.items()
                 if all(reading[name] is None or reading[name] == states[mode][i]
                        for i, name in enumerate(ids))}
        contract.require(bool(forms), f'delivered history contradicts binary-contact-v1 at step {t}')
    return forecasts
