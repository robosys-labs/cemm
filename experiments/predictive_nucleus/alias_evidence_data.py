"""Fixed observed-evidence substitution, reusing the frozen continuation recipe.

Preparation alone imports physics. Selection uses initial anchors and leading
sets, never realized outcomes/modes. Public disjoint blueprints are not new laws.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import lzma
from pathlib import Path

from . import acceptance_contract as contract, continuation_data as continuation
from . import prospective_oracle as oracle
from .prospective_data import blueprint_digest, template_digest, _realize

PRIOR = Path(__file__).parent / 'data' / 'continuation-assets-v1.json.xz'


def _precontact(case):
    """Compute the first contact's inputs without reading any later observation."""
    bits = dict(case['observations'][0])
    for t, action in enumerate(case['actions']):
        if action['kind'] == 'contact':
            return t, tuple(bits[i] for i in action['participants'])
        contract.require(action['kind'] == 'set', 'unexpected acquisition prefix')
        bits[action['participants'][0]] = action['value']
    raise ValueError('missing contact')


def _exposure(inputs):
    cases = inputs['episodes']
    return {'episodes': len(cases), 'actions': sum(len(c['actions']) for c in cases),
        'visible_events': sum(any(v is not None for v in r.values()) for c in cases for r in c['observations'][1:]),
        'visible_bits': sum(v is not None for c in cases for r in c['observations'][1:] for v in r.values())}


def build_assets(config):
    config = deepcopy(config)
    data = config['data']
    contract.require(data['split_seeds'] == dict(zip(continuation.SPLITS, range(20261030021, 20261030025))),
                     'alias evidence split seeds differ')
    contract.require(data['draws_per_cell'] == {'train': 8, 'selection': 4, 'calibration': 4, 'evaluation': 4},
                     'alias evidence requires the fixed draw inventory')
    bundle = continuation.build_assets(config)
    baseline = bundle['splits']['train']
    treatment = {'inputs': deepcopy(baseline['inputs']), 'cases': deepcopy(baseline['cases'])}
    original = {c['episode']: c for c in baseline['inputs']['episodes']}
    selected = {}
    for n in data['entity_counts']:
        choices = [r['lineage'] for r in baseline['cases'] if r['family'] == 'single_contact' and
            r['entities'] == n and r['direction'] == 0 and len(set(_precontact(original[r['episode']])[1])) == 2]
        contract.require(len(choices) >= 2, 'insufficient prespecified unequal-input replacement lineages')
        selected[n] = choices[:2]
    chosen = {lineage for group in selected.values() for lineage in group}
    replacements, bits = [], Counter()
    for case, meta in zip(treatment['inputs']['episodes'], treatment['cases'], strict=True):
        if meta['lineage'] not in chosen: continue
        t, pre = _precontact(case)
        first = case['actions'][t]['participants'][0]
        case['actions'][t]['participants'] = [first, first]
        _realize(case, meta['hidden_source_slot'])
        meta.update(family='self_contact', acquisition_step=None, query_steps=[t], query_scope='self_contact',
                    blueprint_sha256=blueprint_digest(case), template_sha256=template_digest(case), self_prebit=pre[0])
        replacements.append(case['episode']); bits[f'N{len(case["ids"])}/bit{pre[0]}'] += 1
    contract.validate_inputs(treatment['inputs'])
    contract.require(_exposure(baseline['inputs']) == _exposure(treatment['inputs']), 'substitution changed exposure')
    treatment['audit'] = {'selected_lineages': {str(n): rows for n, rows in selected.items()},
        'replaced_episodes': replacements, 'self_prebit_counts': dict(sorted(bits.items())),
        'baseline_exposure': _exposure(baseline['inputs']), 'alias_exposure': _exposure(treatment['inputs']),
        'selection': 'first two unequal precontact single-contact physical lineages per N; before mode/outcomes',
        'dependency': 'both original reversed views retained as related views of the same source lineage; not independent aliases'}
    bundle['alias_training'] = treatment

    prior_raw = PRIOR.read_bytes()
    prior = json.loads(lzma.decompress(prior_raw))
    prior_blueprints = {r['blueprint_sha256'] for split in prior['splits'].values() for r in split['cases']}
    prior_self = {r['blueprint_sha256'] for r in prior['splits']['evaluation']['cases'] if r['family'] == 'self_contact'}
    evaluation = bundle['splits']['evaluation']
    retained = [i for i, r in enumerate(evaluation['cases']) if r['family'] != 'self_contact']
    evaluation['cases'] = [evaluation['cases'][i] for i in retained]
    evaluation['inputs']['episodes'] = [evaluation['inputs']['episodes'][i] for i in retained]
    evaluation['oracle']['episodes'] = [evaluation['oracle']['episodes'][i] for i in retained]
    used = {blueprint_digest(c) for split in bundle['splits'].values() for c in split['inputs']['episodes']}
    used.update(blueprint_digest(c) for c in treatment['inputs']['episodes'])
    used.update(prior_self)
    fresh_self = set()
    rejected = 0
    for n in data['entity_counts']:
        for bit in (0, 1):
            for draw in range(2):
                root = [config['version'], 'evaluation', data['split_seeds']['evaluation'], 'balanced-self', n, bit, draw]
                for attempt in range(data['max_blueprint_attempts']):
                    case = continuation._candidate([*root, attempt], 'self_contact', n, 1, 'evaluation')
                    t, _ = _precontact(case)
                    who = case['actions'][t]['participants'][0]
                    case['observations'][0][who] = bit
                    for action in case['actions'][:t]:
                        if action['participants'] == [who]: action['value'] = bit
                    blueprint = blueprint_digest(case)
                    if blueprint not in used: break
                    rejected += 1
                else: raise ValueError(f'fresh self blueprint budget exhausted: N{n}/bit{bit}/{draw}')
                used.add(blueprint); fresh_self.add(blueprint)
                # Query, inputs, actions and all rejection decisions precede the mode.
                mode = continuation._rng('alias-hidden-mode-v1', root).randrange(2)
                lineage = contract.digest(['alias-self-lineage-v1', *root, blueprint])
                case['episode'] = contract.digest(['alias-self-episode-v1', *root])[:32]
                truth = _realize(case, mode)
                forecasts = oracle.forecast_episode(case)
                contract.require(_precontact(case)[1] == (bit, bit) and len(forecasts[t]['possible_worlds']) == 1,
                                 'balanced self query differs')
                evaluation['inputs']['episodes'].append(case)
                evaluation['oracle']['episodes'].append({'episode': case['episode'], 'truth': truth,
                    'possible_worlds': [r['possible_worlds'] for r in forecasts],
                    'information_keys': [r['information_key'] for r in forecasts]})
                evaluation['cases'].append({'episode': case['episode'], 'family': 'self_contact',
                    'partition': 'in_family', 'lineage': lineage, 'pair_id': None, 'direction': None,
                    'blueprint_sha256': blueprint, 'template_sha256': template_digest(case),
                    'hidden_source_slot': mode, 'entities': n, 'contact_count': 1,
                    'acquisition_step': None, 'query_steps': [t], 'query_scope': 'self_contact', 'self_prebit': bit})
    contract.validate_inputs(evaluation['inputs'])
    evaluation['oracle']['input_sha256'] = contract.digest(evaluation['inputs'])
    bundle['audit']['evaluation']['planned_actions'] = _exposure(evaluation['inputs'])['actions']
    bundle['audit']['alias_training'] = treatment['audit']
    bundle['audit']['fresh_self'] = {'queries': len(fresh_self), 'draws_per_N_and_prebit': 2,
        'prior_self_blueprint_overlap': len(fresh_self & prior_self), 'rejected_proposals': rejected,
        'exclusions': 'both training tapes, selection/calibration, current evaluation, prior continuation-v1 self blueprints'}
    bundle['audit']['prior_bank_blueprint_overlap'] = {split: len({blueprint_digest(c) for c in rows['inputs']['episodes']} &
        prior_blueprints) for split, rows in {**bundle['splits'], 'alias_training': treatment}.items()}
    bundle['audit']['prior_bank_scope'] = 'canonical overlap is descriptive; fresh seeds do not imply novel physics or independent custody'
    bundle['source_sha256'].update({Path(__file__).name: sha256(Path(__file__).read_bytes()).hexdigest(),
                                   'data/continuation-assets-v1.json.xz': sha256(prior_raw).hexdigest()})
    return bundle
