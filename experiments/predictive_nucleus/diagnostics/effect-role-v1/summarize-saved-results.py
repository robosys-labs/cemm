#!/usr/bin/env python3
"""Summarize completed G3 saved reports; never execute a model or a scorer.

Reads training.json, collection/scoring manifests, decision.json, scored reports,
and optional saved audit reports only. No raw forecasts, targets or checkpoints
are opened. Existing scientific decisions are copied, not recalculated.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import lzma
import math
from pathlib import Path


WORLD_FIELDS = ('planned_points', 'correct', 'accuracy', 'mean_nll', 'mean_brier',
                'mean_oracle_kl', 'max_oracle_total_variation', 'map_outside_support',
                'known_unchanged_errors')
ARMS = ('grounded', 'masked', 'parser', 'text_only')
BANKS = ('bilingual_retention', 'lexical_retention', 'binding_retention',
         'saturation_retention', 'centering_retention', 'coordinate_retention')
GOAL_NAMES = ('all', 'attainable', 'impossible', 'effect_sensitive', 'set_required', 'contact_required')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON field: ' + key)
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError('nonstandard JSON number: ' + value)


def read(path):
    raw = path.read_bytes()
    decoded = lzma.decompress(raw) if path.suffix == '.xz' else raw
    value = json.loads(decoded, object_pairs_hook=unique_object, parse_constant=invalid_constant)
    require(type(value) is dict, 'expected object: ' + str(path))
    return value, {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def selected(value, names):
    return {name: value[name] for name in names}


def failed(checks):
    require(type(checks) is dict and all(type(value) is bool for value in checks.values()),
            'invalid saved acceptance checks')
    return sorted(key for key, value in checks.items() if not value)


def numeric(value):
    if value == 'positive_infinity':
        return math.inf
    if value == 'negative_infinity':
        return -math.inf
    require(type(value) in (int, float) and not math.isnan(value), 'invalid saved numerical score')
    return value


def safe(value):
    if isinstance(value, dict):
        return {key: safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(item) for item in value]
    if type(value) is float:
        require(not math.isnan(value), 'undefined summary arithmetic')
        if math.isinf(value):
            return 'positive_infinity' if value > 0 else 'negative_infinity'
    return value


def mean(values):
    return math.fsum(numeric(value) / len(values) for value in values) if values else None


def world_strata(report):
    return {name: selected(report[name], WORLD_FIELDS) for name in ('all', 'identifiable', 'ambiguous')}


def descriptive_points(points):
    """Aggregate existing point metrics only; no new forecast or oracle scoring."""
    def summary(rows):
        actions = [row['action_correct'] for row in rows if row['action_correct'] is not None]
        count = len(rows)
        return {'planned_points': count, 'correct': sum(row['correct'] for row in rows),
            'accuracy': sum(row['correct'] for row in rows) / count if count else None,
            'action_accuracy': sum(actions) / count if count and len(actions) == count else None,
            'mean_nll': mean([row['nll'] for row in rows]),
            'mean_oracle_kl': mean([row['oracle_kl'] for row in rows]),
            'max_oracle_total_variation': max((numeric(row['oracle_total_variation']) for row in rows), default=None),
            'map_outside_support': sum(row['map_outside_support'] for row in rows),
            'known_unchanged_errors': sum(row['known_unchanged_errors'] for row in rows)}
    return {name: summary(points if name == 'all' else
                          [row for row in points if row['answerable'] == (name == 'identifiable')])
            for name in ('all', 'identifiable', 'ambiguous')}


def compact_goals(report):
    return selected(report, (*GOAL_NAMES, 'by_family', 'by_layout'))


def compact_fresh(fresh):
    require(set(fresh['reports']) == set(fresh['points']) == set(fresh['goals']) == set(ARMS),
            'fresh arm inventory differs')
    candidate = fresh['reports']['grounded']
    held = [point for point in fresh['points']['grounded'] if point['held_layout']]
    require(all(point['new_word'] and point['layout'] == 'vos' for point in held), 'invalid saved held-layout flag')
    held_words = defaultdict(list)
    for point in held:
        held_words[point['word']].append(point)
    by_axis = {name: {key: world_strata(value) for key, value in candidate[name].items()}
               for name in ('by_family', 'by_layout', 'by_effect', 'by_lexicon', 'by_cell')}
    controls = {}
    for arm in ('masked', 'parser', 'text_only'):
        report = fresh['reports'][arm]
        controls[arm] = {'world': world_strata(report), 'actions': report['actions'],
                         'actions_by_lexicon': report['actions_by_lexicon'],
                         'goals': compact_goals(fresh['goals'][arm])}
    return {'passed': fresh['passed'], 'failed_checks': failed(fresh['checks']),
        'world': world_strata(candidate), 'actions': candidate['actions'],
        'actions_by_lexicon': candidate['actions_by_lexicon'],
        'by_taught_lexeme_layout': candidate['by_taught_lexeme_layout'],
        'held_new_vos': descriptive_points(held),
        'held_new_vos_by_word': {word: descriptive_points(rows) for word, rows in sorted(held_words.items())},
        **by_axis,
        **{name: {key: value for key, value in candidate[name].items() if key != 'records'}
           for name in ('trajectories', 'role_pairs', 'bilingual')},
        'goals': compact_goals(fresh['goals']['grounded']), 'goal_gains': fresh['comparisons'],
        'controls': controls}


def compact_retention(report):
    rows = report['points']
    require(report['planned'] == len(rows), 'retention saved point count differs')
    counts = {'nll_worse': 0, 'nll_better': 0, 'nll_equal': 0, 'nll_undefined': 0}
    for row in rows:
        change = row['nll_change']
        if change is None:
            counts['nll_undefined'] += 1
        else:
            change = numeric(change)
            counts['nll_worse' if change > 0 else 'nll_better' if change < 0 else 'nll_equal'] += 1
    fields = ('planned', 'correct', 'archived_correct', 'exact_world_vectors', 'mean_nll',
              'archived_mean_nll', 'mean_nll_change', 'max_logp_change',
              'mean_candidate_set_mass', 'max_candidate_set_mass')
    return {'passed': report['passed'], 'failed_checks': failed(report['checks']), **selected(report, fields),
        **{name: len(report[name]) for name in ('regressions', 'repairs', 'world_map_changes', 'action_map_changes')},
        **counts,
        'max_abs_probability_change': max((numeric(row['max_abs_probability_change']) for row in rows), default=None),
        'max_total_variation': max((numeric(row['total_variation']) for row in rows), default=None)}


def resource_totals(receipts):
    names = ('cpu_seconds', 'wall_seconds', 'peak_rss_kib')
    require(all(all(type(receipt[name]) in (int, float) and math.isfinite(receipt[name]) and receipt[name] >= 0
                    for name in names) for receipt in receipts), 'invalid saved resource receipt')
    return {'cpu_seconds': math.fsum(receipt['cpu_seconds'] for receipt in receipts),
            'wall_seconds': math.fsum(receipt['wall_seconds'] for receipt in receipts),
            'peak_rss_kib': max((receipt['peak_rss_kib'] for receipt in receipts), default=0)}


def summarize(fitted, traces, scored, audit_paths):
    training, training_file = read(fitted / 'training.json')
    collection, collection_file = read(traces / 'manifest.json')
    manifest, score_manifest_file = read(scored / 'manifest.json')
    decision, decision_file = read(scored / 'decision.json')
    require(training.get('complete') is True and collection.get('complete') is True and
            decision.get('execution_complete') is True, 'only completed saved execution may be summarized')
    require(collection['training_sha256'] == training_file['sha256'] and
            manifest['trace_manifest_sha256'] == collection_file['sha256'], 'saved-stage hash binding differs')
    require(training['freeze_sha256'] == collection['freeze_sha256'], 'training/collection freeze differs')
    require(training['runtime'] == collection['runtime'] == manifest['runtime'], 'saved runtime receipts differ')
    expected = {f'{law}/{seed}' for law in ('nand', 'nor') for seed in (7, 11, 23, 37, 53)}
    require(set(decision['checks']) == set(manifest['reports']) == expected, 'completed score inventory differs')
    fit_keys = {f'{arm}/{seed}' for arm in ('grounded', 'parser', 'text_only') for seed in (7, 11, 23, 37, 53)}
    require(set(training['reports']) == set(training['checkpoints']) == fit_keys, 'completed fit inventory differs')
    results, failures, retention_totals, raw_counts = {}, {}, defaultdict(int), defaultdict(int)
    report_bytes = 0
    for key in sorted(expected):
        law, seed = key.split('/')
        report, receipt = read(scored / f'report-{law}-{seed}.json.xz')
        require(receipt == manifest['reports'][key], 'scored report bytes differ: ' + key)
        report_bytes += receipt['bytes']
        require(set(report) == {'fresh', 'retention'} and set(report['retention']) == set(BANKS),
                'saved report/bank inventory differs: ' + key)
        fresh = compact_fresh(report['fresh'])
        retained = {bank: compact_retention(report['retention'][bank]) for bank in BANKS}
        combined = {**report['fresh']['checks'], **{bank + '/' + check: value
                    for bank in BANKS for check, value in report['retention'][bank]['checks'].items()}}
        require(combined == decision['checks'][key], 'saved report/decision checks differ: ' + key)
        failures[key] = failed(decision['checks'][key])
        results[key] = {'passed': not failures[key], 'fresh': fresh, 'retention': retained}
        raw_counts['fresh'] += sum(len(rows) for rows in report['fresh']['points'].values())
        for bank, value in retained.items():
            raw_counts['retention'] += value['planned']
            for name in ('planned', 'regressions', 'repairs', 'world_map_changes', 'action_map_changes',
                         'nll_worse', 'nll_better', 'nll_equal', 'nll_undefined'):
                retention_totals[name] += value[name]
    fits = {key: selected(report, ('parameters', 'updates', 'observed_forecasts_per_update',
             'final_objective', 'world_unchanged', 'world_sha256', 'resources'))
            for key, report in sorted(training['reports'].items())}
    native_by_seed = defaultdict(set)
    for key, report in fits.items():
        native_by_seed[key.split('/')[1]].add(report['world_sha256'])
    audits = []
    for path in audit_paths:
        report, receipt = read(path)
        require(report.get('version') == 'effect-role-saved-audit-v1', 'not a G3 saved audit report')
        require(report['raw_publication'] == manifest['traces_publication'] and report['forecast_counts'] == dict(raw_counts),
                'saved audit belongs to different evidence')
        require(report['mode'] == 'pre-score' or report['mode'] == 'full' and report['decision'] == decision['decision'],
                'saved audit mode/decision differs')
        audits.append({'file': str(path.resolve()), **receipt, **selected(report,
            ('mode', 'decision', 'audit_passed', 'check_count', 'discrepancy_count', 'forecast_counts',
             'evaluator_targets_parsed', 'model_execution', 'original_scorer_execution', 'new_fits', 'new_collections'))})
    stages = {'training': training['resources'], 'collection': collection['resources'], 'scoring': manifest['resources']}
    full_audits = [report for report in audits if report['mode'] == 'full']
    return safe({'version': 'cemm-g3-saved-summary-v1',
        'scope': 'Descriptive summary of completed saved reports; no raw evaluator/forecast files, new fits, predictions or scientific rescoring.',
        'decision': {key: value for key, value in decision.items() if key != 'checks'},
        'failed_checks_by_law_seed': failures,
        'failed_lexical_identity_checks': failed(decision['lexical_identity_checks']),
        'conditions': results, 'fits': fits,
        'totals': {'law_seed_conditions': len(expected), 'passed_conditions': sum(not row for row in failures.values()),
            'failed_conditions': sum(bool(row) for row in failures.values()), 'fits': len(fits),
            'saved_forecasts': dict(raw_counts), 'retention': dict(retention_totals),
            'fresh_grounded_held_new_vos': sum(row['fresh']['held_new_vos']['all']['planned_points'] for row in results.values()),
            'scored_report_bytes': report_bytes, 'collection_artifact_files': len(collection['artifacts']),
            'collection_artifact_bytes': sum(item['bytes'] for item in collection['artifacts'].values())},
        'native_immutability': {'all_fits_record_world_unchanged': all(row['world_unchanged'] is True for row in fits.values()),
            'fit_receipts': len(fits), 'matching_native_hash_per_seed': all(len(values) == 1 for values in native_by_seed.values()),
            'training_native_hashes_by_seed': {seed: sorted(values) for seed, values in sorted(native_by_seed.items())},
            'collection_completed': collection['complete'], 'collection_oracle_opened': collection['oracle_opened'],
            'full_saved_audit_passed': all(row['audit_passed'] for row in full_audits) if full_audits else None,
            'basis': 'Saved fit immutability receipts and completed collection; optional full saved audit also verifies all ten native checkpoints. This summarizer does not reopen checkpoint bytes.'},
        'resources': {'stages': stages, 'pipeline_totals': resource_totals(list(stages.values())),
            'fit_report_subtotal': resource_totals([row['resources'] for row in fits.values()]),
            'note': 'Pipeline totals sum stage CPU/wall receipts only. Fit subtotals are already inside training. Peak RSS is the maximum, never the sum. Preparation, tests, publication and audits are excluded.'},
        'provenance': {'source_publication': training['source_publication'],
            'weights_publication': collection['weights_publication'], 'traces_publication': manifest['traces_publication'],
            'freeze_sha256': training['freeze_sha256'], 'runtime': training['runtime'],
            'training': training_file, 'collection_manifest': collection_file,
            'score_manifest': score_manifest_file, 'decision': decision_file, 'all_report_hashes_verified': True},
        'saved_audits': audits})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('fitted', 'traces', 'scored', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--audit', type=Path, action='append', default=[], help='Optional completed saved audit report; repeatable')
    args = parser.parse_args()
    report = summarize(args.fitted, args.traces, args.scored, args.audit)
    with args.output.open('x') as stream:
        json.dump(report, stream, sort_keys=True, separators=(',', ':'), allow_nan=False)
        stream.write('\n')
    print(json.dumps({'output': str(args.output.resolve()), 'decision': report['decision']['decision'],
        'failed_conditions': report['totals']['failed_conditions'],
        'failed_lexical_identity_checks': report['failed_lexical_identity_checks'],
        'bytes': args.output.stat().st_size}, sort_keys=True))


if __name__ == '__main__':
    main()
