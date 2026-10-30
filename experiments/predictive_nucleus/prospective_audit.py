"""Data-only exact-law feasibility audit; no learned predictor or fitting path.

Every declared view is retained. Both equiprobable persistent modes are rebuilt
with the same exogenous design, rather than selecting the realized hidden draw.
Expected ceilings are not hard bounds on a finite sample or a G1 admission.
"""
from collections import defaultdict
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path

from . import acceptance_contract as contract
from . import prospective_data as data
from . import prospective_oracle as oracle
from .world import Action, FAMILIES, World, step


VERSION = 'prospective-data-audit-v1'
SPLITS = ('train', 'selection', 'calibration', 'evaluation')
CASE_FIELDS = ('episode', 'family', 'partition', 'lineage', 'pair_id', 'direction',
               'blueprint_sha256', 'hidden_source_slot', 'template_sha256')


def _indexed(rows):
    contract.require(type(rows) is list and all(type(r) is dict and contract.identifier(r.get('episode'))
                     for r in rows), 'invalid audit episode inventory')
    result = {r['episode']: r for r in rows}
    contract.require(len(result) == len(rows), 'duplicate audit episode')
    return result


def _simulate(case, mode, suppress=None):
    ids = tuple(sorted(case['ids']))
    current = World(ids, tuple(case['observations'][0][name] for name in ids), mode)
    truth = [dict(zip(ids, current.bits))]
    for t, action in enumerate(case['actions']):
        if t != suppress:
            current = step(current, Action(action['kind'], tuple(action['participants']), action.get('value')))
        truth.append(dict(zip(ids, current.bits)))
    tape = deepcopy(case)
    tape['observations'] = [{name: state[name] if shown[name] is not None else None for name in ids}
                            for state, shown in zip(truth, case['observations'], strict=True)]
    return tape, truth


def _masks(case):
    return [[row[name] is not None for name in sorted(case['ids'])] for row in case['observations']]


def _schedule(case, family):
    actions = case['actions']
    middle = actions[int(actions[0]['kind'] == 'set'):len(actions) - int(actions[-1]['kind'] == 'observe')]
    contract.require(middle and all(a['kind'] == 'contact' for a in middle) and
                     all(set(row) == set(case['ids']) for row in case['coverage']),
                     'schedule must be optional leading set, contacts, optional trailing observe with full selected coverage')
    patterns = [FAMILIES[family]] + ([((0, 1), (0, 1))] if family == 'two_contacts' else [])
    for pattern in patterns:
        if len(pattern) != len(middle): continue
        for reverse in (False, True):
            mapping, valid = {}, True
            for edge, action in zip(pattern, middle, strict=True):
                for index, name in zip(edge[::-1] if reverse else edge, action['participants'], strict=True):
                    if index in mapping and mapping[index] != name or index not in mapping and name in mapping.values():
                        valid = False
                    mapping[index] = name
            if valid: return
    raise ValueError('contact schedule does not realize declared family')


def _validate(bundle):
    contract.fields(bundle, ('config', 'source_sha256', 'splits'))
    config = data.validate_config(bundle['config'])
    contract.require(bundle['source_sha256'] == data.source_digests(), 'prospective source identity changed')
    contract.fields(bundle['splits'], SPLITS)
    lineages, blueprints, episodes, result = {}, {}, set(), []
    for split in SPLITS:
        part = bundle['splits'][split]
        contract.fields(part, ('inputs', 'oracle', 'cases'))
        inputs = contract.validate_inputs(part['inputs'])
        cases, observed = _indexed(part['cases']), _indexed(inputs['episodes'])
        gold = part['oracle']
        contract.fields(gold, ('version', 'input_sha256', 'source_sha256', 'information_law_sha256', 'episodes'))
        contract.require(gold['version'] == 'active-acceptance-oracle-v1' and
                         gold['input_sha256'] == contract.digest(inputs) and
                         gold['source_sha256'] == oracle.source_digest() and
                         gold['information_law_sha256'] == oracle.law_digest(), 'oracle artifact identity differs')
        targets = _indexed(gold['episodes'])
        contract.require(cases.keys() == observed.keys() == targets.keys(), 'audit input/case/oracle inventory differs')
        groups = defaultdict(list)
        for name, case in observed.items():
            metadata = cases[name]
            contract.fields(metadata, CASE_FIELDS)
            contract.require(name not in episodes, 'episode identity reused across splits')
            episodes.add(name)
            contract.require(all(contract.identifier(metadata[k]) for k in ('family', 'lineage')) and
                             type(metadata['hidden_source_slot']) is int and metadata['hidden_source_slot'] in (0, 1),
                             'invalid audit case metadata')
            family = metadata['family']
            eligible = config['evaluation_families'] if split == 'evaluation' else config['development_families']
            contract.require(family in eligible and len(case['ids']) in config['entity_counts'] and
                             len(case['actions']) <= config['max_actions'], 'case outside configured domain')
            _schedule(case, family)
            expected_partition = 'in_family' if family in config['development_families'] else 'held_out'
            contract.require(metadata['partition'] == expected_partition, 'family partition differs')
            blueprint, lineage = metadata['blueprint_sha256'], metadata['lineage']
            contract.require(blueprint == data.blueprint_digest(case) and
                             metadata['template_sha256'] == data.template_digest(case), 'case design digest differs')
            contract.require(lineage not in lineages or lineages[lineage] == (split, blueprint),
                             'lineage crosses split or blueprint')
            contract.require(blueprint not in blueprints or blueprints[blueprint] == (split, lineage),
                             'blueprint reused under a different split or lineage')
            lineages[lineage], blueprints[blueprint] = (split, blueprint), (split, lineage)
            groups[lineage].append((case, metadata))
            target = targets[name]
            contract.fields(target, ('episode', 'truth', 'possible_worlds', 'information_keys'))
            actual, truth = _simulate(case, metadata['hidden_source_slot'])
            contract.require(actual['observations'] == case['observations'] and
                             contract.digest(target['truth']) == contract.digest(truth),
                             'actual observations/truth contradict persistent mode')
            forecasts = oracle.forecast_episode(case)
            contract.require(contract.digest(target['possible_worlds']) == contract.digest([r['possible_worlds'] for r in forecasts]) and
                             target['information_keys'] == [r['information_key'] for r in forecasts],
                             'oracle support is incomplete or information keys differ')
            result.append((split, case, metadata))
        seen_pairs = set()
        for members in groups.values():
            if len(members) == 1:
                case, meta = members[0]
                contacts = [a for a in case['actions'] if a['kind'] == 'contact']
                contract.require(meta['pair_id'] is None and meta['direction'] is None and contacts and
                                 all(a['participants'][0] == a['participants'][1] for a in contacts),
                                 'unpaired draw is not self-contact-only')
                continue
            contract.require(len(members) == 2, 'physical draw needs exactly two reversed views')
            (a, x), (b, y) = members
            contract.require(contract.identifier(x['pair_id']) and x['pair_id'] == y['pair_id'] and
                             x['pair_id'] not in seen_pairs and
                             all(type(m['direction']) is int for m in (x, y)) and
                             {x['direction'], y['direction']} == {0, 1}, 'invalid paired draw identity')
            seen_pairs.add(x['pair_id'])
            contract.require(all(x[k] == y[k] for k in ('family', 'partition', 'hidden_source_slot', 'template_sha256')) and
                             sorted(a['ids']) == sorted(b['ids']) and a['observations'][0] == b['observations'][0] and
                             [sorted(c) for c in a['coverage']] == [sorted(c) for c in b['coverage']] and
                             _masks(a) == _masks(b), 'role views differ in mode, anchor, coverage or masks')
            reverse = deepcopy(a['actions'])
            for action in reverse:
                if action['kind'] == 'contact': action['participants'].reverse()
            contract.require(reverse == b['actions'] and any(a['kind'] == 'contact' and
                             a['participants'][0] != a['participants'][1] for a in reverse), 'role actions are not reversed')
        inventory = defaultdict(int)
        for members in groups.values():
            case, meta = members[0]
            inventory[meta['family'], len(case['ids'])] += 1
        expected = {(family, n): config['draws_per_family_entity'][split]
                    for family in (config['evaluation_families'] if split == 'evaluation' else config['development_families'])
                    for n in config['entity_counts'] if n >= max(3, 1 + max(max(edge) for edge in FAMILIES[family]))}
        contract.require(dict(inventory) == expected, 'configured family/entity physical-draw inventory is incomplete or excessive')
    return config, result


def _resources(case, missing_limit):
    cumulative, rows = 0, []
    for t, observed in enumerate(case['observations'][1:]):
        before = 2 ** cumulative
        missing = sum(bit is None for bit in observed.values())
        cumulative += missing
        after, expansions = 2 ** cumulative, before * 2 ** len(case['ids'])
        rows.append({'step': t, 'missing_bits': missing, 'live_histories_before': before,
                     'candidate_expansions': expansions, 'live_histories_after': after,
                     'within_expansion_limit': expansions <= 512, 'within_live_path_limit': after <= 64})
    return {'cumulative_missing_bits': cumulative, 'within_configured_missing_limit': cumulative <= missing_limit,
            'within_dense_support_bounds': all(r['within_expansion_limit'] and r['within_live_path_limit'] for r in rows),
            'steps': rows}


def _carry(case, mode, truth):
    contacts = [t for t, a in enumerate(case['actions']) if a['kind'] == 'contact']
    witnesses, pairs = [], 0
    for earlier in contacts[:-1]:
        _, suppressed = _simulate(case, mode, suppress=earlier)
        for later in contacts:
            if later <= earlier: continue
            pairs += 1
            destination = case['actions'][later]['participants'][1 - mode]
            factual, alternate = truth[later + 1][destination], suppressed[later + 1][destination]
            if factual != alternate:
                witnesses.append({'earlier_step': earlier, 'later_step': later, 'destination': destination,
                                  'factual_bit': factual, 'suppressed_bit': alternate})
    return {'tested_contact_pairs': pairs, 'witnesses': witnesses}


def _branch(case, mode):
    tape, truth = _simulate(case, mode)
    rows = []
    for t, prediction in enumerate(oracle.forecast_episode(tape)):
        probabilities, possible = prediction['probabilities'], prediction['possible_worlds']
        maximum = max(probabilities)
        best = next(w for w, p in zip(possible, probabilities, strict=True) if p == maximum)
        actual = sum(truth[t + 1][name] << (len(case['ids']) - i - 1) for i, name in enumerate(sorted(case['ids'])))
        rows.append({**prediction, 'step': t, 'action_kind': case['actions'][t]['kind'],
                     'actual_world': actual, 'answerable': len(possible) == 1,
                     'bayes_map_probability': maximum, 'lexicographic_map_world': best,
                     'map_correct': best == actual, 'map_tied': probabilities.count(maximum) > 1,
                     'entropy_nats': -math.fsum(p * math.log(p) for p in probabilities),
                     'brier_floor': 1. - math.fsum(p * p for p in probabilities)})
    return {'mode': mode, 'law_weight': .5, 'points': rows,
            'trajectory_exact': all(r['map_correct'] for r in rows), 'carry': _carry(case, mode, truth)}


def _point_metrics(points):
    n = len(points)
    mean = lambda key: math.fsum(r[key] for r in points) / n if n else None
    return {'expected_step_mass': n / 2, 'bayes_map_accuracy': mean('bayes_map_probability'),
            'frozen_lexicographic_map_accuracy': mean('map_correct'),
            'mean_entropy_nats': mean('entropy_nats'), 'mean_brier_floor': mean('brier_floor'),
            'expected_tied_step_mass': sum(r['map_tied'] for r in points) / 2}


def _summary(records):
    points = [p for r in records for branch in r['modes'] for p in branch['points']]
    actual = [p for r in records for p in r['modes'][r['hidden_source_slot']]['points']]
    pairs = defaultdict(list)
    for record in records:
        if record['pair_id'] is not None: pairs[record['split'], record['pair_id']].append(record)
    pair_exact = math.fsum(.5 * all(r['modes'][m]['trajectory_exact'] for r in members)
                          for members in pairs.values() for m in (0, 1))
    law = {'all': _point_metrics(points),
           'contact': _point_metrics([p for p in points if p['action_kind'] == 'contact']),
           'answerable': _point_metrics([p for p in points if p['answerable']]),
           'ambiguous': _point_metrics([p for p in points if not p['answerable']])}
    in_family = _point_metrics([p for r in records if r['partition'] == 'in_family'
                               for branch in r['modes'] for p in branch['points']])
    ceiling = in_family['bayes_map_accuracy']
    branches = [b for r in records for b in r['modes']]
    return {'counts': {'episodes': len(records), 'physical_draws': len({r['lineage'] for r in records}),
                'role_pairs': len(pairs), 'planned_steps': len(actual),
                'contact_steps': sum(p['action_kind'] == 'contact' for p in actual),
                'answerable_steps': sum(p['answerable'] for p in actual),
                'ambiguous_steps': sum(not p['answerable'] for p in actual)},
            'law_expected': law,
            'frozen_lexicographic_trajectory_exact': math.fsum(b['trajectory_exact'] for b in branches) / len(branches),
            'frozen_lexicographic_role_pair_exact': pair_exact / len(pairs) if pairs else None,
            'original_in_family_target': {'target': .95, 'expected_all_action_ceiling': ceiling,
                'expected_ceiling_at_least_target': ceiling >= .95 if ceiling is not None else None,
                'admission_decision': False},
            'resources': {'episodes_with_dense_bound_exceedance': sum(not r['resources']['within_dense_support_bounds'] for r in records),
                'episodes_exceeding_configured_missing_bits': sum(not r['resources']['within_configured_missing_limit'] for r in records),
                'maximum_candidate_expansions': max(p['candidate_expansions'] for r in records for p in r['resources']['steps']),
                'maximum_live_histories_after_feedback': max(p['live_histories_after'] for r in records for p in r['resources']['steps'])},
            'carry': {'mode_branches': len(branches),
                'tested_contact_pairs': sum(b['carry']['tested_contact_pairs'] for b in branches),
                'witnesses': sum(len(b['carry']['witnesses']) for b in branches),
                'branches_with_witness': sum(bool(b['carry']['witnesses']) for b in branches),
                'expected_fraction_of_views_with_witness': sum(bool(b['carry']['witnesses']) for b in branches) / len(branches)}}


def audit_assets(bundle):
    """Validate all generated assets and report exact-law/data-only diagnostics."""
    original = contract.digest(bundle)
    config, cases = _validate(bundle)
    records = [{**deepcopy(meta), 'split': split, 'entities': len(case['ids']),
                'resources': _resources(case, config['max_cumulative_missing_bits']),
                'modes': [_branch(case, mode) for mode in (0, 1)]} for split, case, meta in cases]
    by_split = {}
    for split in SPLITS:
        selected = [r for r in records if r['split'] == split]
        by_split[split] = {**_summary(selected), 'by_family': {
            family: _summary([r for r in selected if r['family'] == family])
            for family in sorted({r['family'] for r in selected})}}
    templates = defaultdict(set)
    for r in records: templates[r['template_sha256']].add(r['split'])
    report = {'version': VERSION, 'gate_g1': 'NOT_ADMITTED', 'learned_model_evaluated': False,
        'scope': 'Exact conditional-law engineering audit of public same-author assets; no research result.',
        'ceiling_interpretation': 'Expected under both equiprobable persistent modes, not a hard bound on a finite realized sample.',
        'conjunction_interpretation': 'Frozen lexicographic MAP with delivered feedback; not an optimal trajectory/pair policy ceiling.',
        'pair_tie_caveat': 'A balanced unidentified reversed pair can have zero conjunction credit even for exact calibrated forecasts.',
        'resource_interpretation': 'Conservative dense-support history counts without merging; no measured model cost or oracle pruning.',
        'carry_interpretation': 'Suppress one earlier contact and compare the later contact destination; unrelated surviving bystander differences do not count.',
        'selection_policy': 'All supplied cases retained regardless of ambiguity, carry witnesses or resource limits.',
        'assumptions': {'balanced_persistent_mode_law': True, 'paired_mode_mask_anchor_consistency_checked': True,
                        'cross_split_blueprint_lineage_reuse': False, 'exogenous_design_independently_authenticated': False,
                        'configured_resource_envelope_satisfied': all(r['resources']['within_dense_support_bounds'] and
                            r['resources']['within_configured_missing_limit'] for r in records),
                        'independent_custody_verified': False, 'scientific_comparison_design_complete': False},
        'bundle_sha256': original, 'source_sha256': {**deepcopy(bundle['source_sha256']),
            'prospective_audit.py': sha256(Path(__file__).read_bytes()).hexdigest()},
        'aggregate': _summary(records), 'by_split': by_split,
        'templates_shared_across_splits': {k: sorted(v) for k, v in sorted(templates.items()) if len(v) > 1},
        'cases': records}
    contract.require(contract.digest(bundle) == original, 'audit mutated input assets')
    json.dumps(report, allow_nan=False)
    return report
