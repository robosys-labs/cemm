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


def _untouched(case, bit):
    t, _ = _precontact(case)
    known = dict(case['observations'][0])
    for action in case['actions'][:t]: known[action['participants'][0]] = action['value']
    return next((i for i in sorted(case['ids']) if i not in case['actions'][t]['participants'] and known[i] == bit), None)


def _gold(case, truth):
    forecasts = oracle.forecast_episode(case)
    return {'episode': case['episode'], 'truth': truth,
        'possible_worlds': [r['possible_worlds'] for r in forecasts],
        'information_keys': [r['information_key'] for r in forecasts]}


def build_assets(config):
    config = deepcopy(config)
    data = config['data']
    v2 = config['version'] == 'alias-evidence-v2'
    first_seed = 20261030031 if v2 else 20261030021
    contract.require(data['split_seeds'] == dict(zip(continuation.SPLITS, range(first_seed, first_seed + 4))),
                     'alias evidence split seeds differ')
    contract.require(data['draws_per_cell'] == {'train': 8, 'selection': 4, 'calibration': 4, 'evaluation': 4},
                     'alias evidence requires the fixed draw inventory')
    bundle = continuation.build_assets(config)
    baseline = bundle['splits']['train']
    original = {c['episode']: c for c in baseline['inputs']['episodes']}
    selected, targets = {}, {}
    for n in data['entity_counts']:
        if v2:
            selected[n] = []
            for bit in (0, 1):
                row = next((r for r in baseline['cases'] if r['family'] == 'two_contacts' and r['entities'] == n and
                    r['direction'] == 0 and r['lineage'] not in selected[n] and _untouched(original[r['episode']], bit)), None)
                contract.require(row is not None, 'insufficient prespecified untouched-bit replacement lineages')
                selected[n].append(row['lineage'])
                targets[row['lineage']] = (_untouched(original[row['episode']], bit), bit, (n - 3 + bit) % 2)
            continue
        choices = [r['lineage'] for r in baseline['cases'] if r['family'] == 'single_contact' and
            r['entities'] == n and r['direction'] == 0 and len(set(_precontact(original[r['episode']])[1])) == 2]
        contract.require(len(choices) >= 2, 'insufficient prespecified unequal-input replacement lineages')
        selected[n] = choices[:2]
    chosen = {lineage for group in selected.values() for lineage in group}
    if v2:
        # Discard preliminary realization for these blueprints. Fixed mode allocation
        # precedes final ordinary AND treatment realization; it is not a learner label.
        for i, (case, meta) in enumerate(zip(baseline['inputs']['episodes'], baseline['cases'], strict=True)):
            if meta['lineage'] not in chosen: continue
            meta['hidden_source_slot'] = targets[meta['lineage']][2]
            baseline['oracle']['episodes'][i] = _gold(case, _realize(case, meta['hidden_source_slot']))
        baseline['oracle']['input_sha256'] = contract.digest(baseline['inputs'])
    treatment = {'inputs': deepcopy(baseline['inputs']), 'cases': deepcopy(baseline['cases'])}
    replacements, bits = [], Counter()
    for case, meta in zip(treatment['inputs']['episodes'], treatment['cases'], strict=True):
        if meta['lineage'] not in chosen: continue
        t, pre = _precontact(case)
        first = case['actions'][t]['participants'][0]
        if v2:
            first, bit, _ = targets[meta['lineage']]
            t = [i for i, a in enumerate(case['actions']) if a['kind'] == 'contact'][1]
            pre = (bit, bit)
        case['actions'][t]['participants'] = [first, first]
        _realize(case, meta['hidden_source_slot'])
        contract.require(case['observations'][t][first] == pre[0], 'alias prebit differs from prospective selection')
        meta.update(family='acquired_self_contact' if v2 else 'self_contact',
                    acquisition_step=meta['acquisition_step'] if v2 else None, query_steps=[t], query_scope='self_contact',
                    blueprint_sha256=blueprint_digest(case), template_sha256=template_digest(case), self_prebit=pre[0])
        replacements.append(case['episode']); bits[f'N{len(case["ids"])}/bit{pre[0]}'] += 1
    contract.validate_inputs(treatment['inputs'])
    contract.require(_exposure(baseline['inputs']) == _exposure(treatment['inputs']), 'substitution changed exposure')
    treatment['audit'] = {'selected_lineages': {str(n): rows for n, rows in selected.items()},
        'replaced_episodes': replacements, 'self_prebit_counts': dict(sorted(bits.items())),
        'baseline_exposure': _exposure(baseline['inputs']), 'alias_exposure': _exposure(treatment['inputs']),
        'selection': 'first two unequal precontact single-contact physical lineages per N; before mode/outcomes',
        'dependency': 'both original reversed views retained as related views of the same source lineage; not independent aliases'}
    if v2:
        treatment['audit'].update(selection='first distinct two-contact lineage per N and known untouched prebit; anchor/leading-set only',
            mode_assignment='(N - 3 + prebit) % 2, allocated before final realization for both arms',
            mode_by_lineage={lineage: {'target': who, 'prebit': bit, 'mode': mode} for lineage, (who, bit, mode) in targets.items()},
            acquisition='first distinct informative contact and its full delivered feedback precede the alias; no reset')
    bundle['alias_training'] = treatment

    prior_raw = PRIOR.read_bytes()
    prior = json.loads(lzma.decompress(prior_raw))
    prior_blueprints = {r['blueprint_sha256'] for split in prior['splits'].values() for r in split['cases']}
    prior_self = {r['blueprint_sha256'] for r in prior['splits']['evaluation']['cases'] if r['family'] == 'self_contact'}
    older_training = set()
    if v2:
        old_path = PRIOR.with_name('alias-evidence-assets-v1.json.xz')
        old_raw = old_path.read_bytes(); old = json.loads(lzma.decompress(old_raw))
        prior_self.update(r['blueprint_sha256'] for r in old['splits']['evaluation']['cases'] if r['family'] == 'self_contact')
        older_training = {r['blueprint_sha256'] for rows in (old['splits']['train'], old['alias_training']) for r in rows['cases']}
        prior_blueprints.update(r['blueprint_sha256'] for rows in old['splits'].values() for r in rows['cases'])
        prior_blueprints.update(older_training)
        bundle['source_sha256']['data/' + old_path.name] = sha256(old_raw).hexdigest()
    evaluation = bundle['splits']['evaluation']
    retained = [i for i, r in enumerate(evaluation['cases']) if r['family'] != 'self_contact']
    evaluation['cases'] = [evaluation['cases'][i] for i in retained]
    evaluation['inputs']['episodes'] = [evaluation['inputs']['episodes'][i] for i in retained]
    evaluation['oracle']['episodes'] = [evaluation['oracle']['episodes'][i] for i in retained]
    used = {blueprint_digest(c) for split in bundle['splits'].values() for c in split['inputs']['episodes']}
    used.update(blueprint_digest(c) for c in treatment['inputs']['episodes'])
    used.update(prior_self)
    used.update(older_training)
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
    if v2:
        bundle['audit']['fresh_self']['exclusions'] += ', opened alias-evidence-v1 self and both training tapes'
        bundle['audit']['fresh_self']['opened_alias_v1_training_overlap'] = len(fresh_self & older_training)
    bundle['audit']['prior_bank_blueprint_overlap'] = {split: len({blueprint_digest(c) for c in rows['inputs']['episodes']} &
        prior_blueprints) for split, rows in {**bundle['splits'], 'alias_training': treatment}.items()}
    bundle['audit']['prior_bank_scope'] = 'canonical overlap is descriptive; fresh seeds do not imply novel physics or independent custody'
    bundle['source_sha256'].update({Path(__file__).name: sha256(Path(__file__).read_bytes()).hexdigest(),
                                   'data/continuation-assets-v1.json.xz': sha256(prior_raw).hexdigest()})
    return bundle
