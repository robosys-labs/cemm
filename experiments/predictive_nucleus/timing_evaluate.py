"""Bind prospective timing traces to frozen inputs and gold, retaining omissions."""
from copy import deepcopy

from . import acceptance_contract as base, timing_contract as contract
from .acceptance_scoring import score_rows, _index
from .domain_contract import binary_worlds
from .mixed_composition_run import information_scores


def _keyed(rows):
    result = {r['episode']: r for r in rows}
    base.require(len(result) == len(rows), 'duplicate episode inventory')
    return result


def evaluate(plan, bundle, traces):
    inputs = contract.validate_inputs(bundle['inputs'])
    base.require(plan['version'] == 'timing-plan-v1' and plan['input_sha256'] == base.digest(inputs) and
        all(plan[k + '_sha256'] == base.digest(bundle[k]) for k in ('oracle', 'information', 'cases')),
        'frozen timing plan binding differs')
    observed, cases = _keyed(inputs['episodes']), _keyed(bundle['cases'])
    gold, information = _keyed(bundle['oracle']['episodes']), _keyed(bundle['information']['episodes'])
    base.require(observed.keys() == cases.keys() == gold.keys() == information.keys(), 'gold inventory differs')
    inventory = {}
    enriched = []
    permutations = {r['permutation_pair_id']: r['nontrivial_event_permutation'] for r in bundle['permutation_pairs']}
    for name, case in observed.items():
        ids, target, infos = sorted(case['ids']), gold[name], information[name]['forecasts']
        base.require(len(target['truth']) == len(case['actions']) + 1 and len(infos) == len(case['actions']) and
            target['truth'] == case['observations'], 'full observed targets differ')
        meta = {**deepcopy(cases[name]), 'ids': ids,
                'permutation_nontrivial': permutations[cases[name]['permutation_pair_id']],
                'pre_group_key': contract.history_key(case, 1),
                'forecast_information': []}
        for step, action in enumerate(case['actions']):
            truth, previous = ([reading[i] for i in ids] for reading in target['truth'][step:step + 2][::-1])
            expected = infos[step]
            base.require(expected['information_key'] == contract.information_key(case, step) and
                expected['history_key'] == contract.history_key(case, step) and
                target['possible_worlds'][step] == expected['possible_worlds'] and
                target['information_keys'][step] == expected['information_key'], 'oracle information differs')
            inventory[name, step] = {**{k: cases[name][k] for k in
                ('episode', 'family', 'partition', 'lineage', 'pair_id', 'direction')},
                'step': step, 'ids': ids, 'truth': truth, 'previous_truth': previous,
                'possible_worlds': expected['possible_worlds'], 'information_key': expected['information_key'],
                'action_kind': action['kind']}
            meta['forecast_information'].append({**{k: expected[k] for k in
                ('information_key', 'possible_worlds', 'probabilities')}, 'truth': truth, 'previous_truth': previous})
        enriched.append(meta)
    runs, outputs, failures = {}, {}, []
    for trace in traces:
        seed = trace['model_seed']
        base.fields(trace, ('version', 'input_sha256', 'checkpoint_sha256', 'participant', 'model_seed', 'episodes',
            'source_sha256', 'frozen_predictor_before', 'frozen_predictor_after', 'resources'))
        base.require(type(seed) is int and seed in plan['model_seeds'] and seed not in runs and
            trace['participant'] == 'frozen' and trace['version'] == 'timing-trace-v1' and
            trace['input_sha256'] == plan['input_sha256'] and trace['checkpoint_sha256'] == plan['checkpoints'][str(seed)] and
            trace['frozen_predictor_before'] == trace['frozen_predictor_after'] and trace['source_sha256'] ==
            {'timing_runner.py': plan['software_sha256']['timing_runner.py']}, 'trace binding differs')
        frozen = trace['frozen_predictor_before']; base._frozen_identity(frozen)
        base.require(frozen['state_sha256'] == plan['checkpoint_states'][str(seed)], 'planned checkpoint state differs')
        runs[seed] = trace
        records = _keyed(trace['episodes'])
        base.require(records.keys() <= observed.keys(), 'unplanned trace episode')
        for name, record in records.items():
            base.fields(record, ('episode', 'started', 'events', 'failure', 'ended'))
            case, start = observed[name], record['started']
            base.require(type(record['events']) is list and len(record['events']) <= len(case['actions']),
                         'invalid event inventory')
            if start is None:
                base.require(not record['events'] and record['failure'] is not None, 'missing start without failure')
            else:
                base.fields(start, ('status', 'episode', 'ids', 'world_order', 'implementation', 'implementation_sha256'))
                identity = start['implementation']
                base.require(start['status'] == 'STARTED' and start['episode'] == name and start['ids'] == sorted(case['ids'])
                    and start['world_order'] == [list(w) for w in binary_worlds(len(case['ids']))] and
                    start['implementation_sha256'] == base.digest(identity) and identity == contract.implementation_identity(
                        frozen['predictor'], frozen['state_sha256'], {n: plan['software_sha256'][n]
                            for n in ('timing_contract.py', 'timing_kernel.py', 'timing_session.py')}),
                    'start implementation binding differs')
            for step, event in enumerate(record['events']):
                base.fields(event, ('step', 'forecast', 'feedback'))
                base.require(type(event['step']) is int and event['step'] == step, 'noncontiguous timing events')
                logs = contract.forecast_logs(event['forecast'], case, step, start['implementation_sha256'])
                if event['feedback'] is None:
                    base.require(step == len(record['events']) - 1 and record['failure'] is not None and
                        record['failure']['phase'] == 'feedback' and record['failure']['step'] == step,
                        'missing feedback without terminal failure')
                else:
                    base.require(event['feedback'] == {'status': 'RECEIVED', 'episode': name, 'next_step': step + 1},
                                 'feedback identity differs')
                outputs[seed, name, step] = (logs, event['forecast'])
            if record['failure'] is None:
                count = len(case['actions'])
                base.require(len(record['events']) == count and record['ended'] == {'status': 'ENDED', 'episode': name,
                    'feedback_steps': count, 'predictions': count, 'pending_forecast': False}, 'incomplete episode without failure')
            else:
                failure = record['failure']; base.fields(failure, ('phase', 'step', 'error_type', 'message'))
                phase, step = failure['phase'], failure['step']
                expected = {'start': 0, 'predict': len(record['events']),
                            'feedback': len(record['events']) - 1, 'end': len(case['actions'])}
                base.require(phase in expected and type(step) is int and step == expected[phase] and
                    record['ended'] is None and (phase != 'end' or len(record['events']) == len(case['actions'])),
                    'invalid terminal failure boundary')
                acknowledgments = [event['feedback'] is not None for event in record['events']]
                coherent = ((phase == 'start' and start is None and not record['events']) or
                    (phase == 'predict' and start is not None and step < len(case['actions']) and all(acknowledgments)) or
                    (phase == 'feedback' and start is not None and bool(acknowledgments) and
                     not acknowledgments[-1] and all(acknowledgments[:-1])) or
                    (phase == 'end' and start is not None and all(acknowledgments)))
                base.require(coherent and base.identifier(failure['error_type']) and type(failure['message']) is str,
                             'failure phase contradicts retained events')
                failures.append({'model_seed': seed, 'episode': name, **failure})
    rows = []
    for seed in plan['model_seeds']:
        for (name, step), point in inventory.items():
            logs, forecast = outputs.get((seed, name, step), (None, None))
            rows.append({**point, 'participant': 'frozen', 'model_seed': seed,
                'status': 'UNPRODUCED' if forecast is None else 'ANSWERED', 'log_probabilities': logs,
                'wall_seconds': None if forecast is None else forecast['wall_seconds'],
                'cpu_seconds': None if forecast is None else forecast['cpu_seconds']})
    report = score_rows(rows)
    for point in report['points']:
        expected = information[point['episode']]['forecasts'][point['step']]
        point.update(information_scores(point, expected, [_index(point['previous_truth'])]),
                     oracle_probabilities=expected['probabilities'])
    report.update(failures=failures, execution_complete=not failures and len(outputs) == len(rows),
                  resources={str(seed): run['resources'] for seed, run in runs.items()})
    return report, enriched
