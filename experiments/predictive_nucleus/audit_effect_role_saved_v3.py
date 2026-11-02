"""Independent v3 saved-record driver using frozen v1/v2 audit arithmetic.

No model, study scorer or oracle imports. Pre-score validates every current and
opened-reference row before target parsing. Full mode reproduces all gates.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

if __package__:
    from . import audit_effect_role_saved_v2 as previous
else:
    import audit_effect_role_saved_v2 as previous

h, v1 = previous.h, previous.v1
LAWS, SEEDS, ARMS, BANKS = previous.LAWS, previous.SEEDS, previous.ARMS, previous.BANKS
require, index_rows, inventory, measured = previous.require, previous.index_rows, previous.inventory, previous.measured
retained, lexical_receipt = previous.retained, previous.lexical_receipt
verify_analysis, opened_comparison = previous.verify_analysis, previous.opened_comparison
REFERENCES = ('v1', 'v2')
OPENED = {version: 'opened_effect_role_' + version for version in REFERENCES}


def evidence_roles(version):
    require(version in REFERENCES, 'opened reference study')
    roles = json.loads(json.dumps(previous.EVIDENCE_ROLES))
    for arm in ('grounded', 'masked', 'parser', 'text_only'): roles[arm]['origin'] = 'current_v3'
    roles['parser']['role'] = 'parser_control'
    roles['text_only'].pop('reproduction_required')
    roles['reference_grounded']['origin'] = 'archived_v1' if version == 'v1' else 'frozen_v2_checkpoint_reforecast'
    return roles


def protected_state(state, parent, registry):
    """Account for every saved coordinate: unchanged parent88 plus new4."""
    require(set(state) == {'parent.' + name for name in parent} | {'new_coordinates'}, 'factored state key inventory')
    require(h.tensor_shape(state['new_coordinates'])[0] == [2, 2], 'new coordinate shape')
    parent_hash, count = h.fingerprint(parent)
    require(count == 88, 'parent scalar inventory')
    protected = {name: state['parent.' + name] for name in parent}
    require(h.fingerprint(protected) == (parent_hash, 88), 'protected parent scalar mutation')
    require(h.fingerprint(state)[1] == 92, 'total factored scalar inventory')
    initial = {'parent.' + name: value for name, value in parent.items()}; initial['new_coordinates'] = [[0., 0.], [0., 0.]]
    legacy = sorted(registry['tokens'][word]['id'] for word in registry['legacy_tokens'])
    new = sorted({item['id'] for item in registry['tokens'].values()} - set(legacy))
    require(len(new) == 2 and len(legacy) == len(set(legacy)), 'registry acquisition identity inventory')
    return {'initial_sha256': h.fingerprint(initial)[0], 'protected_parameters': 88, 'learned_parameters': 4,
        'protected_initial_sha256': parent_hash, 'protected_final_sha256': parent_hash, 'protected_unchanged': True,
        'registry_sha256': h.canonical(registry), 'legacy_ids': legacy, 'new_ids': new}


def reference_provenance(value, config, training_sha256, checkpoint):
    expected = {'source_study': 'effect-role-v2',
        'source_checkpoint_publication': config['checkpoint_publication'],
        'source_implementation_publication': config['implementation_publication'],
        'source_training_sha256': training_sha256, 'source_checkpoint_sha256': checkpoint['sha256'],
        'state_sha256': checkpoint['state_sha256']}
    require(all(value[k] == v for k, v in expected.items()) and value['parameters_frozen'] is True and
        type(value['model_updates']) is int and value['model_updates'] == 0, 'frozen-v2 reference provenance')


def raw_inventory(directory, artifacts, receipts):
    """Reject omitted, unmanifested and interrupted raw-stage artifacts."""
    expected = set(artifacts) | set(receipts) | {'attempt.json', 'manifest.json'}
    entries = list(directory.iterdir())
    require({p.name for p in entries} == expected and all(p.is_file() and not p.is_symlink() for p in entries),
        'exact raw directory inventory')



def audit_saved(repo, audit, pre_score=False, publication=None):
    root = repo / 'experiments/predictive_nucleus'; data = root / 'data/effect-role-v3'
    fitted = root / 'data/effect-role-fit-v3'; traces = root / 'results/effect-role-v3/traces'; scored = traces.parent / 'scored'
    config, freeze, trained, manifest = [h.read(p) for p in (root / 'effect_role_protocol_v3.json', data / 'freeze.json',
        fitted / 'training.json', traces / 'manifest.json')]
    references = {}
    for version in REFERENCES:
        paths = {'data': root / ('data/effect-role-' + version), 'fit': root / ('data/effect-role-fit-' + version),
                 'traces': root / ('results/effect-role-' + version + '/traces')}
        references[version] = {**paths, 'training': h.read(paths['fit'] / 'training.json'),
            'freeze': h.read(paths['data'] / 'freeze.json')}
        old_config = h.read(root / ('effect_role_protocol_' + version + '.json'))
        audit.check(all(config[k] == old_config[k] for k in ('fit', 'analysis', 'model_seeds', 'parameters')),
                    'unchanged training budget/gates/seeds/size/' + version)
        audit.equal(freeze['world_checkpoints'], references[version]['freeze']['world_checkpoints'], 'unchanged native mapping/' + version)
        prior_fit = references[version]['training']
        audit.check(prior_fit['complete'] is True and prior_fit['version'] == 'effect-role-' + version and
            prior_fit['runtime'] == references[version]['freeze']['runtime'] and
            prior_fit['freeze_sha256'] == h.sha(paths['data'] / 'freeze.json'), 'reference fit original runtime/binding/' + version)
    references['v1']['manifest'] = h.read(references['v1']['traces'] / 'manifest.json')
    interruption_path = root / 'results/effect-role-interruption-v2.json'
    interruption = h.read(interruption_path)
    audit.equal(freeze['historical'].get(interruption_path.relative_to(root).as_posix()), h.sha(interruption_path),
                'frozen v2 interruption receipt')
    audit.check(interruption['decision'] == 'STOP_INCOMPLETE_EVIDENCE' and interruption['execution_complete'] is False and
        interruption['g3_complete'] is False and interruption['scientific_decision'] is None,
        'explicit incomplete v2 reference status')
    audit.check(interruption['source_publication'] == config['reference_v2']['implementation_publication'] and
        interruption['weights_publication'] == config['reference_v2']['checkpoint_publication'] and
        interruption['freeze_sha256'] == h.sha(references['v2']['data'] / 'freeze.json'), 'interruption reference provenance')
    audit.equal(freeze['parent_result_publication'], config['parent_result_publication'], 'parent publication binding')
    audit.equal(config['model_seeds'], list(SEEDS), 'seeds'); audit.equal(config['arms'], list(ARMS), 'arms')
    audit.equal([freeze['version'], trained['version']], ['effect-role-v3'] * 2, 'study identity')
    audit.equal(h.sha(root / 'effect_role_protocol_v3.json'),
                (root / 'snapshots/effect_role_protocol_v3.sha256').read_text().split()[0], 'protocol lock')
    audit.equal(freeze['protocol_sha256'], h.sha(root / 'effect_role_protocol_v3.json'), 'protocol binding')
    for name, digest in {**freeze['sources'], **freeze['historical']}.items(): audit.equal(h.sha(root / name), digest, name)
    commitment = h.read(root / 'effect_role_freeze_v3.json')
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
    registry = h.read(data / 'lexical-registry.json')
    audit.equal(trained['training_input_sha256'], {k: h.canonical(v) for k, v in observed.items()}, 'observed TRAIN binding')
    audit.equal({k: sum(len(e['utterances']) for e in v['episodes']) for k, v in observed.items()}, config['training_forecasts'], 'TRAIN counts')
    for version, reference in references.items():
        for name in ('teach-inputs.json.xz', 'rehearsal-inputs.json.xz', 'parser-labels.json.xz', 'lexical-registry.json'):
            audit.equal(h.sha(data / name), h.sha(reference['data'] / name), 'exact unchanged training/' + version + '/' + name)
    expected_keys = {f'{arm}/{seed}' for arm in ARMS for seed in SEEDS}
    require(set(trained['reports']) == set(trained['checkpoints']) == expected_keys, '15 fit inventory')
    parents = h.read(root / 'data/coordinate-fit-v1/checkpoints.json.xz')['checkpoints']
    require(set(freeze['world_checkpoints']) == {f'{law}/{seed}' for law in LAWS for seed in SEEDS}, 'ten native checkpoints')
    for key, item in freeze['world_checkpoints'].items():
        path = root / 'data/set-acquisition-fit-v2' / item['file']; world = h.read(path)
        audit.equal([h.sha(path), *h.fingerprint(world['state'])], [item['sha256'], item['state_sha256'], 562], 'immutable world/' + key)
    protection = {}
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
            protection[key] = protected_state(record['state'], parents[f'coordinates/{seed}']['state'], registry)
            audit.equal({k: report[k] for k in protection[key]}, protection[key], 'actual protected88+learned4/' + key)
    reference_checkpoints = {}
    for version, reference in references.items():
        reference_checkpoints[version] = {}
        for seed in SEEDS:
            key = f'grounded/{seed}'; item = reference['training']['checkpoints'][key]
            path = reference['fit'] / item['file']; record = h.read(path)
            digest = reference['training']['reports'][key]['final_sha256']
            audit.equal([h.sha(path), path.stat().st_size, record['arm'], record['seed'], *h.fingerprint(record['state']), record['state_sha256']],
                        [item['sha256'], item['bytes'], 'grounded', seed, digest, 92, digest], 'actual reference checkpoint/' + version + '/' + str(seed))
            reference_checkpoints[version][seed] = {**item, 'state_sha256': digest}
    saved_lexical = h.read(traces / 'lexical-identities.json')
    lexical = lexical_receipt(registry, [observed[k] for k in ('rehearsal', 'teach')], config['unknown_tokens'], saved_lexical)
    audit.equal(saved_lexical, lexical, 'known/unknown identity control arithmetic')
    inputs = {(law, bank): h.read(data / f'{law}-inputs.json.xz') if bank == 'fresh' else
        h.read(root / f'data/{bank[:-10]}-v1/{law}-inputs.json.xz') for law in LAWS for bank in
        ('fresh', *(b + '_retention' for b in BANKS))}
    inputs.update({(law, OPENED[version]): h.read(reference['data'] / f'{law}-inputs.json.xz')
                   for version, reference in references.items() for law in LAWS})
    for law in LAWS:
        fresh = inputs[law, 'fresh']['episodes']
        audit.equal([len(fresh), sum(len(e['utterances']) for e in fresh)],
                    [config['fresh_episodes_per_law'], config['fresh_forecasts_per_law']], 'fresh input counts/' + law)
    schedules = [(law, seed, arm, bank) for law in LAWS for seed in SEEDS for arm in ARMS for bank in
                 (('fresh', *(b + '_retention' for b in BANKS), *OPENED.values()) if arm == 'grounded' else ('fresh', *OPENED.values()))]
    schedules += [(law, seed, 'reference_v2', OPENED['v2']) for law in LAWS for seed in SEEDS]
    filenames = {f'trace-{law}-{seed}-{arm}-{bank}.json.xz' for law, seed, arm, bank in schedules}
    require(set(manifest['artifacts']) == filenames | {'lexical-identities.json'}, 'raw file inventory')
    require({p.name for p in traces.glob('trace-*.json.xz')} == filenames, 'unexpected unmanifested forecasts')
    for name, item in manifest['artifacts'].items():
        audit.equal([h.sha(traces / name), (traces / name).stat().st_size], [item['sha256'], item['bytes']], 'raw bytes/' + name)
    expected_shards = {f'{law}/{seed}' for law in LAWS for seed in SEEDS}
    require(set(manifest['shards']) == expected_shards, 'complete shard inventory')
    shard_paths, execution_publications = [], []
    for law in LAWS:
        for seed in SEEDS:
            key = f'{law}/{seed}'; item = manifest['shards'][key]
            require(item['file'] == f'shard-{law}-{seed}.json' and
                item['attempt']['file'] == f'shard-attempt-{law}-{seed}.json', 'shard receipt paths')
            values = []
            for receipt in (item, item['attempt']):
                path = traces / receipt['file']; shard_paths.append(path)
                audit.equal([h.sha(path), path.stat().st_size], [receipt['sha256'], receipt['bytes']], 'shard receipt bytes/' + key)
                values.append(h.read(path))
            shard, attempt = values
            identity = {k: manifest[k] for k in ('weights_publication', 'runtime', 'freeze_sha256', 'training_sha256')}
            audit.check(all(value[k] == v for value in values for k, v in identity.items()) and
                all(value['law'] == law and value['seed'] == seed for value in values) and
                shard['execution_publication'] == attempt['execution_publication'] and
                shard['complete'] is True and shard['oracle_opened'] is False, 'shard stage identity/' + key)
            partition = {name: manifest['artifacts'][name] for name in filenames if name.startswith(f'trace-{law}-{seed}-')}
            audit.check(len(partition) == 16 and shard['artifacts'] == partition, 'exact shard partition/' + key)
            execution_publications.append(shard['execution_publication'])
    require({p.name for p in traces.glob('shard-*.json')} == {p.name for p in shard_paths}, 'unexpected shard receipts')
    raw_inventory(traces, manifest['artifacts'], (p.name for p in shard_paths))
    def published(commit, paths):
        require(type(commit) is str and len(commit) == 40 and set(commit) <= set('0123456789abcdef'), 'publication commit')
        for path in paths:
            raw = subprocess.check_output(['git', '-C', str(repo), 'show', commit + ':' + path.relative_to(repo).as_posix()])
            audit.equal(hashlib.sha256(raw).hexdigest(), h.sha(path), 'published/' + str(path.relative_to(root)))
    published(trained['source_publication'], [data / 'freeze.json', *[root / name for name in freeze['sources']],
        *[data / name for name in freeze['artifacts']]])
    parent_paths = [interruption_path]
    for reference in references.values(): parent_paths += [reference['data'] / 'freeze.json', reference['fit'] / 'training.json']
    parent_paths += [references['v1']['traces'] / 'manifest.json', references['v1']['traces'].parent / 'scored/decision.json']
    published(config['parent_result_publication'], parent_paths)
    published(config['reference_v2']['checkpoint_publication'], [references['v2']['fit'] / 'training.json',
        *[references['v2']['fit'] / item['file'] for item in reference_checkpoints['v2'].values()]])
    published(config['reference_v2']['implementation_publication'], [references['v2']['data'] / 'freeze.json',
        *[root / name for name in references['v2']['freeze']['sources']],
        *[references['v2']['data'] / name for name in references['v2']['freeze']['artifacts']]])
    published(manifest['weights_publication'], [fitted / 'training.json', *[fitted / v['file'] for v in trained['checkpoints'].values()]])
    raw_publication = publication or subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    published(raw_publication, [traces / 'manifest.json', traces / 'attempt.json', *shard_paths, *[traces / name for name in manifest['artifacts']]])
    for execution in execution_publications:
        require(type(execution) is str and len(execution) == 40 and set(execution) <= set('0123456789abcdef'), 'shard execution publication')
        for earlier, later in ((manifest['weights_publication'], execution), (execution, raw_publication)):
            audit.check(subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', earlier, later],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0, 'shard publication ancestry')
    def trace(law, seed, arm, bank):
        value = h.read(traces / f'trace-{law}-{seed}-{arm}-{bank}.json.xz'); observed = inputs[law, bank]
        expected_state = reference_checkpoints['v2'][seed]['state_sha256'] if arm == 'reference_v2' else trained['reports'][f'{arm}/{seed}']['final_sha256']
        require((value['law'], value['seed'], value['arm'], value['bank']) == (law, seed, arm, bank) and
            value['input_sha256'] == h.canonical(observed) and value['state_sha256'] == expected_state and
            all(value[k] == manifest[k] for k in ('weights_publication', 'runtime', 'freeze_sha256', 'training_sha256')), 'trace provenance')
        if arm == 'reference_v2':
            reference_provenance(value, config['reference_v2'], h.sha(references['v2']['fit'] / 'training.json'), reference_checkpoints['v2'][seed])
        records = {r['id']: r for r in observed['episodes']}; require(len(records) == len(observed['episodes']), 'observed duplicate identity')
        return index_rows(value['points'], records, 'grounded' if arm == 'reference_v2' else arm, bank == 'fresh' or bank in OPENED.values())
    reference = references['v1']; old, training = reference['manifest'], reference['training']
    audit.check(old['complete'] is True and old['oracle_opened'] is False and
        old['runtime'] == training['runtime'] == reference['freeze']['runtime'] and
        old['training_sha256'] == h.sha(reference['fit'] / 'training.json') and
        old['freeze_sha256'] == h.sha(reference['data'] / 'freeze.json'), 'archived v1 original runtime/stage binding')
    def archive_v1(law, seed):
        reference = references['v1']; old = reference['manifest']
        name = f'trace-{law}-{seed}-grounded-fresh.json.xz'; path = reference['traces'] / name
        require(h.sha(path) == old['artifacts'][name]['sha256'], 'archived v1 trace bytes')
        value = h.read(path); observed = inputs[law, OPENED['v1']]
        require((value['law'], value['seed'], value['arm'], value['bank']) == (law, seed, 'grounded', 'fresh') and
            value['input_sha256'] == h.canonical(observed) and value['state_sha256'] == reference_checkpoints['v1'][seed]['state_sha256'] and
            all(value[k] == old[k] for k in ('weights_publication', 'runtime', 'freeze_sha256', 'training_sha256')),
            'archived v1 identity/input/state/original runtime')
        return index_rows(value['points'], {r['id']: r for r in observed['episodes']})
    totals = {key: 0 for key in ('fresh', 'retention', 'opened_v1', 'opened_v2', 'reference_v2')}
    categories = {bank: 'opened_' + version for version, bank in OPENED.items()}
    for law, seed, arm, bank in schedules:
        category = 'reference_v2' if arm == 'reference_v2' else categories.get(bank, 'fresh' if bank == 'fresh' else 'retention')
        totals[category] += sum(map(len, trace(law, seed, arm, bank).values()))
    archived_rows = {'v1': sum(sum(map(len, archive_v1(law, seed).values())) for law in LAWS for seed in SEEDS)}
    audit.equal(totals, {k: config[k + '_saved_forecasts'] for k in totals}, 'all raw counts')
    audit.equal(sum(totals.values()), config['total_saved_forecasts'], 'complete current forecast count')
    audit.equal(archived_rows['v1'] * 2, config['opened_v1_saved_forecasts'], 'complete archived v1 grounded rows')
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
            opened_evaluators = {version: h.read(reference['data'] / f'{law}-evaluator.json.xz') for version, reference in references.items()}
            opened_inventories = {version: inventory(inputs[law, OPENED[version]], value) for version, value in opened_evaluators.items()}
            forecasts = [f for g in gold.values() for f in g['forecasts']]
            audit.equal([sum(len(f['possible_worlds']) == 1 for f in forecasts), sum(len(f['possible_worlds']) > 1 for f in forecasts),
                sum(c['held_layout'] for g in gold.values() for c in g['cells']), len(evaluator['goal_groups']),
                sum(len(g['goals']) for g in evaluator['goal_groups'])], [config[k] for k in ('identifiable_forecasts_per_law',
                'ambiguous_forecasts_per_law', 'held_new_word_forecasts_per_law', 'goal_groups_per_law', 'goal_decisions_per_law')],
                'conditional/held/goal counts/' + law)
            for seed in SEEDS:
                key = f'{law}/{seed}'; print('Audit ' + key, flush=True)
                path = scored / f'report-{law}-{seed}.json.xz'; audit.equal(h.sha(path), score_manifest['reports'][key]['sha256'], 'score bytes/' + key)
                saved = h.read(path); require(set(saved) == {'fresh', 'retention', 'opened'} and set(saved['opened']) == set(REFERENCES), 'score wrapper inventory')
                raw = {arm: trace(law, seed, arm, 'fresh') for arm in ARMS}
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
                opened_details = {}
                for version in REFERENCES:
                    old_records, old_gold, old_pairs = opened_inventories[version]
                    current = trace(law, seed, 'grounded', OPENED[version])
                    old_views = archive_v1(law, seed) if version == 'v1' else trace(law, seed, 'reference_v2', OPENED['v2'])
                    opened_indexed = {'grounded': current['canonical'], 'masked': current['masked'],
                        **{arm: trace(law, seed, arm, OPENED[version])['canonical'] for arm in ('parser', 'text_only')}}
                    wrapper = saved['opened'][version]
                    opened_checks, points, old_reports, old_goals = verify_analysis(audit, wrapper['analysis'], opened_indexed,
                        old_records, old_gold, old_pairs, opened_evaluators[version]['goal_groups'], config['analysis'], key + '/opened_' + version)
                    comparisons = {view: opened_comparison(points[arm], measured(old_views[view], old_records, old_gold))
                                   for view, arm in (('canonical', 'grounded'), ('masked', 'masked'))}
                    opened_checks.update(opened_identifiable_world_retention=not comparisons['canonical']['identifiable_world_regressions'],
                                         opened_taught_action_retention=not comparisons['canonical']['action_regressions'])
                    audit.equal(wrapper['comparisons'], comparisons, 'all opened regressions/repairs/' + key + '/' + version)
                    audit.equal(wrapper['evidence_roles'], evidence_roles(version), 'opened evidence roles/' + key + '/' + version)
                    audit.check(wrapper['version'] == 'effect-role-opened-regression-v3' and wrapper['reference_study'] == version and
                        wrapper['checks'] == opened_checks and wrapper['passed'] == all(opened_checks.values()), 'opened complete decision/' + key + '/' + version)
                    checks[key].update({'opened_' + version + '/' + k: v for k, v in opened_checks.items()})
                    opened_details[version] = {'world': old_reports['grounded']['all'], 'goals': old_goals['grounded']['all'],
                        'identifiable_world_regressions': comparisons['canonical']['identifiable_world_regressions'],
                        'action_regressions': comparisons['canonical']['action_regressions']}
                details[key] = {'checks': checks[key], 'fresh': reports['grounded']['all'], 'goals': goal_reports['grounded']['all'], 'opened': opened_details}
        passed = all(all(v.values()) for v in checks.values()) and all(lexical['checks'].values())
        expected = 'DEVELOPMENT_G3_COMPLETE' if passed else 'REVISE_EFFECT_ROLE_GROUNDING'
        audit.check(saved_decision['checks'] == checks and saved_decision['lexical_identity_checks'] == lexical['checks'] and
            saved_decision['decision'] == expected and saved_decision['g3_complete'] == passed and saved_decision['execution_complete'] is True and
            saved_decision['scientific_admission'] is False and saved_decision['next_stage'] == ('G4' if passed else 'G3'), 'exact complete decision')
    audit.check(not any((p / 'failure.json').exists() for p in (fitted, traces, *([] if pre_score else [scored]))), 'no interrupted stages')
    require('torch' not in sys.modules and not any(k.endswith(('effect_role_scoring', 'effect_role_scoring_v2', 'effect_role_scoring_v3',
        'effect_role_model', 'effect_role_neutral', 'effect_role_lexical', 'effect_role_lexical_fit')) for k in sys.modules), 'model/scorer imported')
    return {'version': 'effect-role-saved-audit-v3', 'mode': 'pre-score' if pre_score else 'full', 'decision': expected,
        'audit_passed': audit.discrepancy_count == 0, 'check_count': audit.checks, 'discrepancy_count': audit.discrepancy_count,
        'discrepancies': audit.discrepancies, 'forecast_counts': totals, 'trace_files': len(filenames),
        'archived_forecasts_validated': archived_rows, 'protected_language_states': protection,
        'reference_v2_publications': config['reference_v2'], 'incomplete_parent_decision': interruption['decision'],
        'shard_receipts_validated': len(execution_publications),
        'lexical_identity_checks': lexical['checks'], 'evaluator_targets_parsed': not pre_score, 'evaluator_bytes_hashed': True,
        'score_files_read': not pre_score, 'model_execution': False, 'original_scorer_execution': False, 'original_oracle_execution': False,
        'new_fits': 0, 'new_collections': 0, 'scientific_admission': False, 'independent_custody': False,
        'scope': 'Complete source/data/weights/raw publication and runtime bindings; all current and frozen-v2 reforecast rows plus archived v1 grounded rows, dimensions, normalization and views. '
            'All ten saved language extensions contain exactly unchanged parent88 plus four learned coordinates and no extra saved weights. '
            'Full mode also checks every fresh/opened decision gate, critical world/action summaries, every fresh/opened point metric, all goal and retention records. '
            'Canonical opened regressions are gated; masked regressions and ambiguous actual-world changes are descriptive. '
            'All four TRAIN artifacts remain identical. Current v3 parser/text-only controls are collected on every challenge bank. No cross-runtime bit reproduction is required. Archived v1 keeps its original runtime; frozen-v2 reforecasts use the v3 runtime. '
            'Saved conditional targets are validated but not regenerated. ECE, omitted rich summaries, timing and memory costs are not independently recomputed. '
            'Lexical receipts and deterministic registry assignments are checked without invoking the tokenizer. Publication is verified in local git objects, not remote custody.',
        'raw_publication': raw_publication, 'auditor_sha256': h.sha(__file__), 'helper_sha256': h.sha(h.__file__),
        'v1_arithmetic_sha256': h.sha(v1.__file__), 'v2_arithmetic_sha256': h.sha(previous.__file__), 'details': details}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pre-score', action='store_true'); parser.add_argument('--publication')
    args = parser.parse_args(); report = audit_saved(args.repo.resolve(), h.Audit(), args.pre_score, args.publication)
    with args.output.open('x') as stream: json.dump(h.safe(report), stream, sort_keys=True, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({k: report[k] for k in ('decision', 'audit_passed', 'check_count', 'discrepancy_count')}), flush=True)
    return int(not report['audit_passed'])


if __name__ == '__main__': raise SystemExit(main())
