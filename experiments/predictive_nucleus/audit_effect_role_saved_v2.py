"""Independent v2 artifact driver using unchanged v1 audit arithmetic.

No model, original study scorer or oracle is imported. Opened v1 evidence is
retention evidence; archived controls retain their explicit origin labels.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

if __package__:
    from . import audit_effect_role_saved as v1
else:
    import audit_effect_role_saved as v1

h = v1.h
LAWS, SEEDS, ARMS, BANKS = v1.LAWS, v1.SEEDS, v1.ARMS, v1.BANKS
require, average = v1.require, v1.average
index_rows, inventory, measured = v1.index_rows, v1.inventory, v1.measured
summary, goals, decision_checks = v1.summary, v1.goals, v1.decision_checks
retained, compare_subset, lexical_receipt = v1.retained, v1.compare_subset, v1.lexical_receipt
OPENED = 'opened_effect_role_v1'
EVIDENCE_ROLES = {
    'grounded': {'origin': 'current_v2', 'view': 'canonical', 'role': 'candidate'},
    'masked': {'origin': 'current_v2', 'view': 'masked', 'role': 'causal_control'},
    'parser': {'origin': 'archived_v1', 'view': 'canonical', 'role': 'descriptive_parser_baseline'},
    'text_only': {'origin': 'archived_v1', 'view': 'canonical', 'role': 'text_only_control',
        'reproduction_required': 'Runner verifies current v2 state and curve exactly reproduce v1.'},
    'reference_grounded': {'origin': 'archived_v1', 'views': ['canonical', 'masked'],
        'role': 'opened_regression_reference', 'gated_view': 'canonical'}}


def opened_comparison(now, before):
    require(now.keys() == before.keys(), 'opened comparison inventory')
    rows = []
    for key in sorted(now):
        p, old = now[key], before[key]
        nll, previous_nll, kl, previous_kl = p['nll'], old['nll'], p['oracle_kl'], old['oracle_kl']
        rows.append({'id': key[0], 'step': key[1], **{k: p[k] for k in ('family', 'layout', 'word', 'new_word',
            'held_layout', 'answerable', 'action_index', 'correct', 'map_world', 'action_correct', 'map_action', 'map_outside_support')},
            **{'archived_' + k: old[k] for k in ('correct', 'map_world', 'action_correct', 'map_action', 'map_outside_support')},
            'world_map_changed': p['map_world'] != old['map_world'], 'action_map_changed': p['map_action'] != old['map_action'],
            'world_repair': p['correct'] and not old['correct'], 'world_regression': old['correct'] and not p['correct'],
            'action_repair': p['action_correct'] and not old['action_correct'],
            'action_regression': old['action_correct'] and not p['action_correct'],
            'nll': nll, 'archived_nll': previous_nll, 'nll_change': h.difference(nll, previous_nll),
            'true_probability_change': math.exp(-nll) - math.exp(-previous_nll),
            'oracle_kl': kl, 'archived_oracle_kl': previous_kl, 'oracle_kl_change': h.difference(kl, previous_kl),
            'oracle_total_variation': p['oracle_total_variation'], 'archived_oracle_total_variation': old['oracle_total_variation']})
    changes = {name: [[r['id'], r['step']] for r in rows if r[field]] for name, field in (
        ('world_repairs', 'world_repair'), ('world_regressions', 'world_regression'), ('world_map_changes', 'world_map_changed'),
        ('action_repairs', 'action_repair'), ('action_regressions', 'action_regression'), ('action_map_changes', 'action_map_changed'))}
    for label, selector, flag in (('identifiable_world', 'answerable', True), ('ambiguous_world', 'answerable', False),
            ('new_word_action', 'new_word', True), ('old_word_action', 'new_word', False)):
        for change in ('repair', 'regression'):
            changes[label + '_' + change + 's'] = [[r['id'], r['step']] for r in rows
                if r[selector] == flag and r[label.split('_')[-1] + '_' + change]]
    mean = lambda k: average([r[k] for r in rows])
    nll, previous_nll, kl, previous_kl = [mean(k) for k in ('nll', 'archived_nll', 'oracle_kl', 'archived_oracle_kl')]
    return {'planned': len(rows), 'identifiable_planned': sum(r['answerable'] for r in rows),
        'ambiguous_planned': sum(not r['answerable'] for r in rows), **{k: sum(r[k] for r in rows)
            for k in ('correct', 'archived_correct', 'action_correct', 'archived_action_correct')}, **changes,
        'nll_worse': sum(r['nll_change'] is not None and r['nll_change'] > 0 for r in rows),
        'nll_better': sum(r['nll_change'] is not None and r['nll_change'] < 0 for r in rows),
        'nll_equal': sum(r['nll_change'] == 0 for r in rows), 'nll_undefined': sum(r['nll_change'] is None for r in rows),
        'mean_nll': nll, 'archived_mean_nll': previous_nll, 'mean_nll_change': h.difference(nll, previous_nll),
        'mean_oracle_kl': kl, 'archived_mean_oracle_kl': previous_kl,
        'mean_oracle_kl_change': h.difference(kl, previous_kl), 'points': rows}


def verify_analysis(audit, saved, indexed, records, gold, pairs, groups, limits, label):
    points = {arm: measured(rows, records, gold) for arm, rows in indexed.items()}
    reports = {arm: summary(rows, pairs) for arm, rows in points.items()}
    goal_reports = {arm: goals(rows, groups) for arm, rows in points.items()}
    checks, comparisons = decision_checks(reports, goal_reports, limits)
    for arm, rows in points.items():
        compare_subset(audit, saved['reports'][arm], reports[arm], label + '/' + arm)
        audit.equal(saved['points'][arm], [{k: v for k, v in p.items() if k not in ('probabilities', 'logp')}
            for p in rows.values()], label + '/all point metrics/' + arm)
        audit.equal(saved['goals'][arm], goal_reports[arm], label + '/all goal records/' + arm)
    audit.equal(saved['comparisons'], comparisons, label + '/goal control gains')
    audit.check(saved['checks'] == checks and saved['passed'] == all(checks.values()), label + '/decision')
    return checks, points, reports, goal_reports


def audit_saved(repo, audit, pre_score=False, publication=None):
    root = repo / 'experiments/predictive_nucleus'; data = root / 'data/effect-role-v2'
    fitted = root / 'data/effect-role-fit-v2'; traces = root / 'results/effect-role-v2/traces'; scored = traces.parent / 'scored'
    config, freeze, trained, manifest = [h.read(p) for p in (root / 'effect_role_protocol_v2.json', data / 'freeze.json',
        fitted / 'training.json', traces / 'manifest.json')]
    parent_data, parent_fit, parent_traces = (root / p for p in
        ('data/effect-role-v1', 'data/effect-role-fit-v1', 'results/effect-role-v1/traces'))
    parent_training, parent_manifest = h.read(parent_fit / 'training.json'), h.read(parent_traces / 'manifest.json')
    parent_freeze = h.read(parent_data / 'freeze.json')
    audit.equal(freeze['world_checkpoints'], parent_freeze['world_checkpoints'], 'unchanged parent native checkpoint mapping')
    parent_config = h.read(root / 'effect_role_protocol_v1.json')
    audit.check(all(config[k] == parent_config[k] for k in ('fit', 'analysis', 'model_seeds', 'parameters')),
                'unchanged training budget/gates/seeds/size')
    audit.equal(freeze['parent_result_publication'], config['parent_result_publication'], 'parent publication binding')
    audit.equal(config['model_seeds'], list(SEEDS), 'seeds'); audit.equal(config['arms'], list(ARMS), 'arms')
    audit.equal([freeze['version'], trained['version']], ['effect-role-v2'] * 2, 'study identity')
    audit.equal(h.sha(root / 'effect_role_protocol_v2.json'),
                (root / 'snapshots/effect_role_protocol_v2.sha256').read_text().split()[0], 'protocol lock')
    audit.equal(freeze['protocol_sha256'], h.sha(root / 'effect_role_protocol_v2.json'), 'protocol binding')
    for name, digest in {**freeze['sources'], **freeze['historical']}.items(): audit.equal(h.sha(root / name), digest, name)
    commitment = h.read(root / 'effect_role_freeze_v2.json')
    audit.equal(set(commitment), set(freeze['artifacts']) | {'freeze.json'}, 'frozen inventory')
    for name, digest in commitment.items(): audit.equal(h.sha(data / name), digest, 'frozen/' + name)
    for name, item in freeze['artifacts'].items():
        audit.equal([h.sha(data / name), (data / name).stat().st_size], [item['sha256'], item['bytes']], 'artifact/' + name)
    audit.equal(h.canonical(freeze['runtime']), freeze['runtime_sha256'], 'runtime hash')
    audit.check({k: freeze['runtime'][k] for k in config['execution']['runtime']} == config['execution']['runtime'], 'runtime versions')
    for receipt in (trained, manifest):
        audit.check(receipt['complete'] is True and receipt['runtime'] == freeze['runtime'] and
            receipt['freeze_sha256'] == h.sha(data / 'freeze.json'), 'stage completion/runtime/binding')
    audit.check(manifest['oracle_opened'] is False and manifest['training_sha256'] == h.sha(fitted / 'training.json'), 'raw binding')
    for receipt, attempt, names in ((trained, h.read(fitted / 'attempt.json'), ('source_publication', 'runtime', 'freeze_sha256')),
            (manifest, h.read(traces / 'attempt.json'), ('weights_publication', 'runtime', 'freeze_sha256', 'training_sha256'))):
        audit.check(all(receipt[k] == attempt[k] for k in names), 'stage attempt identity')
    observed = {k: h.read(data / f'{k}-inputs.json.xz') for k in ('rehearsal', 'teach')}
    audit.equal(trained['training_input_sha256'], {k: h.canonical(v) for k, v in observed.items()}, 'observed TRAIN binding')
    audit.equal({k: sum(len(e['utterances']) for e in v['episodes']) for k, v in observed.items()}, config['training_forecasts'], 'TRAIN counts')
    for name in ('teach-inputs.json.xz', 'rehearsal-inputs.json.xz', 'parser-labels.json.xz', 'lexical-registry.json'):
        audit.equal(h.sha(data / name), h.sha(parent_data / name), 'exact unchanged training artifact/' + name)
    expected_keys = {f'{arm}/{seed}' for arm in ARMS for seed in SEEDS}
    require(set(trained['reports']) == set(trained['checkpoints']) == expected_keys, '15 fit inventory')
    parents = h.read(root / 'data/coordinate-fit-v1/checkpoints.json.xz')['checkpoints']
    require(set(freeze['world_checkpoints']) == {f'{law}/{seed}' for law in LAWS for seed in SEEDS}, 'ten native checkpoints')
    for key, item in freeze['world_checkpoints'].items():
        path = root / 'data/set-acquisition-fit-v2' / item['file']; world = h.read(path)
        audit.equal([h.sha(path), *h.fingerprint(world['state'])], [item['sha256'], item['state_sha256'], 562], 'immutable world/' + key)
    reproduced = {}
    for key in sorted(expected_keys):
        arm, seed = key.split('/'); item, report = trained['checkpoints'][key], trained['reports'][key]
        path = fitted / item['file']; record = h.read(path)
        audit.equal([h.sha(path), path.stat().st_size], [item['sha256'], item['bytes']], 'checkpoint/' + key)
        audit.equal([record['arm'], record['seed'], *h.fingerprint(record['state']), record['state_sha256']],
            [arm, int(seed), report['final_sha256'], config['parameters'][arm], report['final_sha256']], 'actual fitted state/' + key)
        audit.equal(report, h.read(fitted / f'fit-{arm}-{seed}.json'), 'fit report copy/' + key)
        audit.check(report['world_unchanged'] is True and report['world_sha256'] == freeze['world_checkpoints'][f'nand/{seed}']['state_sha256'], 'world receipt')
        audit.equal(report['settings'], config['fit'], 'fit recipe'); audit.equal(report['updates'], config['fit']['updates'], 'fit exposure')
        audit.equal(report['parameters'], config['parameters'][arm], 'parameter budget')
        audit.equal(report['observed_forecasts_per_update'], config['training_forecasts'], 'tape exposure')
        audit.check(report['fresh_optimizer'] is True, 'fresh optimizer')
        audit.equal(report['optimizer'], {'name': 'Adam', 'betas': [.9, .999], 'eps': 1e-8, 'weight_decay': 0., 'amsgrad': False}, 'optimizer recipe')
        if arm != 'text_only':
            initial = json.loads(json.dumps(parents[f'coordinates/{seed}']['state']))
            for name in initial:
                if name.startswith('order.'): initial[name] += [[[0.]], [[0.]]] if name.endswith('weight') else [0., 0.]
            audit.equal(h.fingerprint(initial), (report['initial_sha256'], 92), 'actual copied88+zero4/' + key)
        else:
            old_item, old_report = parent_training['checkpoints'][key], parent_training['reports'][key]
            old_path = parent_fit / old_item['file']; current_hash = h.sha(path)
            reproduced[seed] = {'checkpoint_bytes_equal': current_hash == h.sha(old_path) == item['sha256'] == old_item['sha256'],
                'report_except_resources_equal': {k: v for k, v in report.items() if k != 'resources'} ==
                    {k: v for k, v in old_report.items() if k != 'resources'},
                'checkpoint_sha256': current_hash, 'state_sha256': report['final_sha256']}
    reproduction = {'version': 'effect-role-text-only-reproduction-v2', 'passed': all(
        r['checkpoint_bytes_equal'] and r['report_except_resources_equal'] for r in reproduced.values()),
        'resources_excluded': True, 'seeds': reproduced}
    audit.check(reproduction['passed'] and len(reproduced) == len(SEEDS), 'exact text-only control reproduction')
    audit.equal(trained['text_only_reproduction'], reproduction, 'text-only reproduction receipt')
    registry = h.read(data / 'lexical-registry.json')
    saved_lexical = h.read(traces / 'lexical-identities.json')
    lexical = lexical_receipt(registry, [observed[k] for k in ('rehearsal', 'teach')], config['unknown_tokens'], saved_lexical)
    audit.equal(saved_lexical, lexical, 'known/unknown identity control arithmetic')
    inputs = {(law, bank): h.read(data / f'{law}-inputs.json.xz') if bank == 'fresh' else
        h.read(root / f'data/{bank[:-10]}-v1/{law}-inputs.json.xz') for law in LAWS for bank in
        ('fresh', *(b + '_retention' for b in BANKS))}
    inputs.update({(law, OPENED): h.read(parent_data / f'{law}-inputs.json.xz') for law in LAWS})
    for law in LAWS:
        fresh = inputs[law, 'fresh']['episodes']
        audit.equal([len(fresh), sum(len(e['utterances']) for e in fresh)],
                    [config['fresh_episodes_per_law'], config['fresh_forecasts_per_law']], 'fresh input counts/' + law)
    schedules = [(law, seed, arm, bank) for law in LAWS for seed in SEEDS for arm in ARMS for bank in
                 (('fresh', *(b + '_retention' for b in BANKS), OPENED) if arm == 'grounded' else ('fresh',))]
    filenames = {f'trace-{law}-{seed}-{arm}-{bank}.json.xz' for law, seed, arm, bank in schedules}
    require(set(manifest['artifacts']) == filenames | {'lexical-identities.json'}, 'raw file inventory')
    require({p.name for p in traces.glob('trace-*.json.xz')} == filenames, 'unexpected unmanifested forecasts')
    for name, item in manifest['artifacts'].items():
        audit.equal([h.sha(traces / name), (traces / name).stat().st_size], [item['sha256'], item['bytes']], 'raw bytes/' + name)
    def published(commit, paths):
        require(type(commit) is str and len(commit) == 40 and set(commit) <= set('0123456789abcdef'), 'publication commit')
        for path in paths:
            raw = subprocess.check_output(['git', '-C', str(repo), 'show', commit + ':' + path.relative_to(repo).as_posix()])
            audit.equal(hashlib.sha256(raw).hexdigest(), h.sha(path), 'published/' + str(path.relative_to(root)))
    published(trained['source_publication'], [data / 'freeze.json', *[root / name for name in freeze['sources']],
        *[data / name for name in freeze['artifacts']]])
    published(config['parent_result_publication'], [parent_data / 'freeze.json', parent_fit / 'training.json',
        parent_traces / 'manifest.json', root / 'results/effect-role-v1/scored/decision.json'])
    published(manifest['weights_publication'], [fitted / 'training.json', *[fitted / v['file'] for v in trained['checkpoints'].values()]])
    raw_publication = publication or subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    published(raw_publication, [traces / 'manifest.json', *[traces / name for name in manifest['artifacts']]])
    def trace(law, seed, arm, bank):
        value = h.read(traces / f'trace-{law}-{seed}-{arm}-{bank}.json.xz'); observed = inputs[law, bank]
        require((value['law'], value['seed'], value['arm'], value['bank']) == (law, seed, arm, bank) and
            value['input_sha256'] == h.canonical(observed) and value['state_sha256'] == trained['reports'][f'{arm}/{seed}']['final_sha256']
            and all(value[k] == manifest[k] for k in ('weights_publication', 'runtime', 'freeze_sha256', 'training_sha256')), 'trace provenance')
        records = {r['id']: r for r in observed['episodes']}; require(len(records) == len(observed['episodes']), 'observed duplicate identity')
        return index_rows(value['points'], records, arm, bank in ('fresh', OPENED))
    audit.check(parent_manifest['complete'] is True and parent_manifest['oracle_opened'] is False and
        parent_manifest['runtime'] == parent_training['runtime'] == freeze['runtime'] and
        parent_manifest['training_sha256'] == h.sha(parent_fit / 'training.json') and
        parent_manifest['freeze_sha256'] == h.sha(parent_data / 'freeze.json'), 'archived stage binding')
    def archive_points(law, seed, arm):
        name = f'trace-{law}-{seed}-{arm}-fresh.json.xz'; path = parent_traces / name
        require(h.sha(path) == parent_manifest['artifacts'][name]['sha256'], 'archived trace bytes')
        value = h.read(path); observed = inputs[law, OPENED]
        require((value['law'], value['seed'], value['arm'], value['bank']) == (law, seed, arm, 'fresh') and
            value['input_sha256'] == h.canonical(observed) and value['state_sha256'] == parent_training['reports'][f'{arm}/{seed}']['final_sha256'] and
            all(value[k] == parent_manifest[k] for k in ('weights_publication', 'runtime', 'freeze_sha256', 'training_sha256')),
            'archived trace identity/input/state/runtime')
        return index_rows(value['points'], {r['id']: r for r in observed['episodes']}, arm)
    totals = {'fresh': 0, 'retention': 0, 'opened': 0}
    for law, seed, arm, bank in schedules:
        totals['opened' if bank == OPENED else 'fresh' if bank == 'fresh' else 'retention'] += sum(map(len, trace(law, seed, arm, bank).values()))
    archived_rows = sum(sum(map(len, archive_points(law, seed, arm).values())) for law in LAWS for seed in SEEDS for arm in ARMS)
    audit.equal(totals, {k: config[k + '_saved_forecasts'] for k in ('fresh', 'retention', 'opened')}, 'all raw counts')
    audit.equal(sum(totals.values()), config['total_saved_forecasts'], 'complete current forecast count')
    audit.equal(archived_rows, config['opened_saved_forecasts'] * 2, 'complete archived candidate/control rows')
    require(audit.discrepancy_count == 0, 'pre-score evidence verification failed before evaluator parsing')
    checks, details, expected = {}, {}, None
    if not pre_score:
        score_manifest, saved_decision = h.read(scored / 'manifest.json'), h.read(scored / 'decision.json')
        audit.check(score_manifest['runtime'] == freeze['runtime'] and score_manifest['trace_manifest_sha256'] == h.sha(traces / 'manifest.json'), 'score runtime/raw binding')
        audit.equal(score_manifest['traces_publication'], raw_publication, 'scored publication matches audited raw commit')
        expected_reports = {f'{law}/{seed}' for law in LAWS for seed in SEEDS}
        audit.equal(set(score_manifest['reports']), expected_reports, 'score report inventory')
        for law in LAWS:
            evaluator = h.read(data / f'{law}-evaluator.json.xz'); records, gold, pairs = inventory(inputs[law, 'fresh'], evaluator)
            old_evaluator = h.read(parent_data / f'{law}-evaluator.json.xz')
            old_records, old_gold, old_pairs = inventory(inputs[law, OPENED], old_evaluator)
            forecasts = [f for g in gold.values() for f in g['forecasts']]
            audit.equal([sum(len(f['possible_worlds']) == 1 for f in forecasts), sum(len(f['possible_worlds']) > 1 for f in forecasts),
                sum(c['held_layout'] for g in gold.values() for c in g['cells']), len(evaluator['goal_groups']),
                sum(len(g['goals']) for g in evaluator['goal_groups'])], [config[k] for k in ('identifiable_forecasts_per_law',
                'ambiguous_forecasts_per_law', 'held_new_word_forecasts_per_law', 'goal_groups_per_law', 'goal_decisions_per_law')],
                'conditional/held/goal counts/' + law)
            for seed in SEEDS:
                key = f'{law}/{seed}'; print('Audit ' + key, flush=True)
                path = scored / f'report-{law}-{seed}.json.xz'; audit.equal(h.sha(path), score_manifest['reports'][key]['sha256'], 'score bytes/' + key)
                saved = h.read(path); raw = {arm: trace(law, seed, arm, 'fresh') for arm in ARMS}
                indexed = {arm: views['canonical'] for arm, views in raw.items()}; indexed['masked'] = raw['grounded']['masked']
                fresh_checks, _, reports, goal_reports = verify_analysis(audit, saved['fresh'], indexed, records, gold, pairs,
                    evaluator['goal_groups'], config['analysis'], key + '/fresh')
                checks[key] = fresh_checks
                for bank in BANKS:
                    full = bank + '_retention'; observed = inputs[law, full]; cases = {r['id']: r for r in observed['episodes']}
                    archive = h.read(root / f'results/set-acquisition-v2/traces/trace-{law}-{seed}-acquired-{full}.json.xz')
                    require(archive['input_sha256'] == h.canonical(observed), 'archive observed input')
                    result = retained(trace(law, seed, 'grounded', full)['canonical'],
                        index_rows(archive['points'], cases, fresh=False, archived=True)['canonical'], cases, config['analysis'])
                    audit.equal(saved['retention'][full], result, 'all retention records/' + key + '/' + bank)
                    checks[key].update({full + '/' + k: v for k, v in result['checks'].items()})
                current = trace(law, seed, 'grounded', OPENED); old_views = archive_points(law, seed, 'grounded')
                opened_indexed = {'grounded': current['canonical'], 'masked': current['masked'],
                    **{arm: archive_points(law, seed, arm)['canonical'] for arm in ('parser', 'text_only')}}
                opened_checks, opened_points, opened_reports, opened_goals = verify_analysis(audit,
                    saved['opened']['analysis'], opened_indexed, old_records, old_gold, old_pairs,
                    old_evaluator['goal_groups'], config['analysis'], key + '/opened')
                comparisons = {view: opened_comparison(opened_points[arm], measured(old_views[view], old_records, old_gold))
                               for view, arm in (('canonical', 'grounded'), ('masked', 'masked'))}
                opened_checks.update(opened_identifiable_world_retention=not comparisons['canonical']['identifiable_world_regressions'],
                                     opened_taught_action_retention=not comparisons['canonical']['action_regressions'])
                audit.equal(saved['opened']['comparisons'], comparisons, 'all opened regressions/repairs/' + key)
                audit.equal(saved['opened']['evidence_roles'], EVIDENCE_ROLES, 'opened evidence roles/' + key)
                audit.check(saved['opened']['version'] == 'effect-role-opened-regression-v2' and
                    saved['opened']['checks'] == opened_checks and saved['opened']['passed'] == all(opened_checks.values()),
                    'opened complete decision/' + key)
                checks[key].update({'opened/' + k: v for k, v in opened_checks.items()})
                details[key] = {'checks': checks[key], 'fresh': reports['grounded']['all'], 'goals': goal_reports['grounded']['all'],
                    'opened': opened_reports['grounded']['all'], 'opened_goals': opened_goals['grounded']['all'],
                    'opened_identifiable_world_regressions': comparisons['canonical']['identifiable_world_regressions'],
                    'opened_action_regressions': comparisons['canonical']['action_regressions']}
        passed = all(all(v.values()) for v in checks.values()) and all(lexical['checks'].values())
        expected = 'DEVELOPMENT_G3_COMPLETE' if passed else 'REVISE_EFFECT_ROLE_GROUNDING'
        audit.check(saved_decision['checks'] == checks and saved_decision['lexical_identity_checks'] == lexical['checks'] and
            saved_decision['decision'] == expected and saved_decision['g3_complete'] == passed and saved_decision['execution_complete'] is True and
            saved_decision['scientific_admission'] is False and saved_decision['next_stage'] == ('G4' if passed else 'G3'), 'exact complete decision')
        audit.equal(saved_decision['text_only_reproduction'], reproduction, 'decision exact control reproduction')
    audit.check(not any((p / 'failure.json').exists() for p in (fitted, traces, *([] if pre_score else [scored]))), 'no interrupted stages')
    require('torch' not in sys.modules and not any(k.endswith(('effect_role_scoring', 'effect_role_scoring_v2',
        'effect_role_model', 'effect_role_neutral', 'effect_role_neutral_fit')) for k in sys.modules), 'model/scorer imported')
    return {'version': 'effect-role-saved-audit-v2', 'mode': 'pre-score' if pre_score else 'full', 'decision': expected,
        'audit_passed': audit.discrepancy_count == 0, 'check_count': audit.checks, 'discrepancy_count': audit.discrepancy_count,
        'discrepancies': audit.discrepancies, 'forecast_counts': totals, 'trace_files': len(filenames),
        'archived_forecasts_validated': archived_rows, 'text_only_reproduction': reproduction,
        'lexical_identity_checks': lexical['checks'], 'evaluator_targets_parsed': not pre_score, 'evaluator_bytes_hashed': True,
        'score_files_read': not pre_score, 'model_execution': False, 'original_scorer_execution': False, 'original_oracle_execution': False,
        'new_fits': 0, 'new_collections': 0, 'scientific_admission': False, 'independent_custody': False,
        'scope': 'Complete source/data/weights/raw publication and runtime bindings; all raw rows, dimensions, normalization and views. '
            'Full mode also checks every fresh/opened decision gate, critical world/action summaries, every fresh/opened point metric, all goal and retention records. '
            'Canonical opened regressions are gated; masked regressions and ambiguous actual-world changes are descriptive. '
            'All four training artifacts and every text-only state/report except measured resources must exactly reproduce v1. '
            'Saved conditional targets are validated but not regenerated. ECE, omitted rich summaries, timing and memory costs are not independently recomputed. '
            'Lexical receipts and deterministic registry assignments are checked without invoking the tokenizer. Publication is verified in local git objects, not remote custody.',
        'raw_publication': raw_publication, 'auditor_sha256': h.sha(__file__), 'helper_sha256': h.sha(h.__file__),
        'v1_arithmetic_sha256': h.sha(v1.__file__), 'details': details}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pre-score', action='store_true'); parser.add_argument('--publication')
    args = parser.parse_args(); report = audit_saved(args.repo.resolve(), h.Audit(), args.pre_score, args.publication)
    with args.output.open('x') as stream: json.dump(h.safe(report), stream, sort_keys=True, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({k: report[k] for k in ('decision', 'audit_passed', 'check_count', 'discrepancy_count')}), flush=True)
    return int(not report['audit_passed'])


if __name__ == '__main__': raise SystemExit(main())
