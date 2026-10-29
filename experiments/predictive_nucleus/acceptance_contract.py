"""Prospective artifact checks and evaluator-only joins; no learner or oracle implementation."""
from copy import deepcopy
from hashlib import sha256
from itertools import product
import json
import math
from pathlib import Path

VERSION = 'active-acceptance-v1'
ROOT = Path(__file__).parent
MAX_BYTES = 64 * 1024 * 1024
INFERENCE_SOURCES = ('active_paths.py', 'active_participant.py', 'active_evidence.py', 'domain_contract.py',
    'domain_kernel.py', 'domain_flat.py', 'active_checkpoint.py', 'context_support.py', 'external_participant.py',
    'masked_replay.py', 'comparison_scoring.py', 'joint_objective.py')


def require(condition, message):
    if not condition: raise ValueError(message)


def fields(value, names):
    require(type(value) is dict and set(value) == set(names), 'unexpected or missing fields: ' + str(names))


def identifier(value):
    return type(value) is str and 0 < len(value) <= 128


def is_sha(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def load_json(path, expected_sha256):
    require(is_sha(expected_sha256), 'explicit expected artifact SHA required')
    with Path(path).open('rb') as stream: raw = stream.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES and sha256(raw).hexdigest() == expected_sha256, 'artifact size/hash mismatch')
    def pairs(items):
        require(len(dict(items)) == len(items), 'duplicate JSON field')
        return dict(items)
    def invalid(value): raise ValueError('nonfinite JSON constant: ' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def write_json(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    require(len(raw) <= MAX_BYTES, 'artifact exceeds size limit')
    with Path(path).open('xb') as stream: stream.write(raw)
    return sha256(raw).hexdigest()


def contract_digest():
    raw = (ROOT / 'acceptance_protocol_v1.json').read_bytes()
    expected = (ROOT / 'snapshots/active_acceptance_protocol_v1.sha256').read_text().split()[0]
    require(is_sha(expected) and sha256(raw).hexdigest() == expected, 'acceptance contract changed')
    return expected


def software_sources():
    names = (*INFERENCE_SOURCES, 'acceptance_contract.py', 'acceptance_runner.py', 'acceptance_scoring.py')
    return {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def receipt(forecast):
    canonical = {k: v for k, v in forecast.items() if k not in ('wall_seconds', 'cpu_seconds', 'receipt')}
    return sha256(json.dumps(canonical, sort_keys=True, allow_nan=False).encode()).hexdigest()


def validate_inputs(inputs):
    data = deepcopy(inputs)
    fields(data, ('version', 'episodes'))
    require(data['version'] == 'active-acceptance-input-v1' and type(data['episodes']) is list and
            bool(data['episodes']), 'invalid input version or empty episodes')
    seen = set()
    for case in data['episodes']:
        fields(case, ('episode', 'ids', 'observations', 'actions', 'coverage'))
        name, ids, observations, actions, coverage = (case[k] for k in
            ('episode', 'ids', 'observations', 'actions', 'coverage'))
        require(identifier(name) and name not in seen, 'duplicate or invalid episode')
        seen.add(name)
        require(type(ids) is list and 3 <= len(ids) <= 6 and all(map(identifier, ids)) and
                len(set(ids)) == len(ids), 'invalid physical IDs')
        require(type(actions) is list and 1 <= len(actions) <= 128 and type(observations) is list and
                len(observations) == len(actions) + 1 and type(coverage) is list and
                len(coverage) == len(actions), 'invalid episode length')
        for t, observed in enumerate(observations):
            fields(observed, ids)
            require(all((v is None and t > 0) or type(v) is int and v in (0, 1)
                        for v in observed.values()), 'invalid observed bit or partial anchor')
        for t, action in enumerate(actions):
            require(type(action) is dict and action.get('kind') in ('contact', 'set', 'observe'), 'invalid action')
            fields(action, ('kind', 'participants', 'value') if action['kind'] == 'set' else ('kind', 'participants'))
            members = action['participants']
            require(type(members) is list and len(members) == {'contact': 2, 'set': 1, 'observe': 0}[action['kind']]
                    and all(type(v) is str and v in ids for v in members), 'invalid action operands')
            if action['kind'] == 'set':
                require(type(action['value']) is int and action['value'] in (0, 1), 'invalid intervention value')
            chosen = coverage[t]
            require(type(chosen) is list and bool(chosen) and all(type(v) is str and v in ids for v in chosen)
                    and len(set(chosen)) == len(chosen), 'invalid selected coverage')
            require(all(v is None or k in chosen for k, v in observations[t + 1].items()), 'reading outside coverage')
    digest(data)
    return data


def information_key(case, step):
    require(type(step) is int and 0 <= step < len(case['actions']), 'invalid prediction point')
    ids = sorted(case['ids'])
    actions = [[a['kind'], [ids.index(i) for i in a['participants']], a.get('value')]
               for a in case['actions'][:step + 1]]
    return digest({'entities': len(ids), 'actions': actions,
        'observations': [[x[i] for i in ids] for x in case['observations'][:step + 1]],
        'coverage': [sorted(ids.index(i) for i in row) for row in case['coverage'][:step + 1]]})


def _index(bits):
    result = 0
    for bit in bits: result = 2 * result + bit
    return result


def validate_plan(plan, inputs):
    inputs = validate_inputs(inputs)
    plan = deepcopy(plan)
    fields(plan, ('version', 'contract_sha256', 'study_id', 'scope', 'input_sha256', 'oracle_sha256',
                  'oracle_source_sha256', 'information_law_sha256', 'model_seeds', 'participants',
                  'reference_participant', 'cases', 'split_lineage', 'development_families', 'software_sha256'))
    require(plan['version'] == 'active-acceptance-plan-v1' and plan['contract_sha256'] == contract_digest(),
            'plan contract/version mismatch')
    require(identifier(plan['study_id']) and plan['scope'] in ('SYNTHETIC_INVARIANTS', 'PROSPECTIVE_DIAGNOSTIC'),
            'invalid study scope')
    require(plan['software_sha256'] == software_sources(), 'acceptance/inference software differs from plan')
    require(all(is_sha(plan[k]) for k in ('input_sha256', 'oracle_sha256', 'oracle_source_sha256',
            'information_law_sha256')) and plan['input_sha256'] == digest(inputs), 'plan input/hash mismatch')
    seeds = plan['model_seeds']
    require(type(seeds) is list and bool(seeds) and all(type(s) is int and s >= 0 for s in seeds) and
            len(set(seeds)) == len(seeds), 'invalid model seed inventory')
    if plan['scope'] == 'PROSPECTIVE_DIAGNOSTIC':
        require(sorted(seeds) == [7, 11, 23, 37, 53], 'all five original model seeds required')
    arms = plan['participants']
    require(type(arms) is dict and bool(arms) and all(map(identifier, arms)) and
            identifier(plan['reference_participant']) and plan['reference_participant'] in arms,
            'invalid participant inventory/reference')
    for expected in arms.values():
        fields(expected, [str(s) for s in seeds])
        require(all(is_sha(v) for v in expected.values()), 'every participant/seed needs a frozen checkpoint hash')
    lineages = plan['split_lineage']
    fields(lineages, ('train', 'selection', 'calibration', 'evaluation'))
    known = set()
    for values in lineages.values():
        require(type(values) is list and all(map(identifier, values)) and len(set(values)) == len(values),
                'invalid split lineage inventory')
        require(not known.intersection(values), 'duplicate-risk lineage crosses partitions')
        known.update(values)
    families = plan['development_families']
    require(type(families) is list and all(map(identifier, families)) and len(set(families)) == len(families),
            'invalid development families')
    cases = _keyed(plan['cases'], 'episode')
    observed = _keyed(inputs['episodes'], 'episode')
    require(cases.keys() == observed.keys(), 'plan/input episode inventory differs')
    pairs = {}
    for name, row in cases.items():
        fields(row, ('episode', 'family', 'partition', 'lineage', 'pair_id', 'direction'))
        require(identifier(row['family']) and row['partition'] in ('in_family', 'held_out') and
                row['lineage'] in lineages['evaluation'], 'invalid case stratum/lineage')
        require(row['partition'] != 'held_out' or row['family'] not in families, 'held-out family used in development')
        if row['pair_id'] is None:
            require(row['direction'] is None, 'unpaired direction')
        else:
            require(identifier(row['pair_id']) and type(row['direction']) is int and row['direction'] in (0, 1),
                    'invalid role pair identity')
            pairs.setdefault(row['pair_id'], []).append(row)
    for members in pairs.values():
        require(len(members) == 2 and {r['direction'] for r in members} == {0, 1} and
                len({(r['family'], r['partition'], r['lineage']) for r in members}) == 1, 'incomplete/cross-stratum role pair')
        a, b = [observed[r['episode']] for r in sorted(members, key=lambda r: r['direction'])]
        require(set(a['ids']) == set(b['ids']) and a['observations'][0] == b['observations'][0] and
                len(a['actions']) == len(b['actions']) and
                [sorted(x) for x in a['coverage']] == [sorted(x) for x in b['coverage']], 'role pair scope differs')
        reversed_actions = deepcopy(a['actions'])
        for action in reversed_actions:
            if action['kind'] == 'contact': action['participants'].reverse()
        require(reversed_actions == b['actions'] and any(x['kind'] == 'contact' and
                x['participants'][0] != x['participants'][1] for x in a['actions']), 'role pair is not a directed reversal')
    return plan


def _keyed(rows, key):
    require(type(rows) is list and all(type(r) is dict and identifier(r.get(key)) for r in rows), 'invalid record inventory')
    result = {r[key]: r for r in rows}
    require(len(result) == len(rows), 'duplicate record identity')
    return result


def validate_oracle(oracle, inputs, plan):
    fields(oracle, ('version', 'input_sha256', 'source_sha256', 'information_law_sha256', 'episodes'))
    require(oracle['version'] == 'active-acceptance-oracle-v1' and digest(oracle) == plan['oracle_sha256'] and
            oracle['input_sha256'] == digest(inputs) and oracle['source_sha256'] == plan['oracle_source_sha256'] and
            oracle['information_law_sha256'] == plan['information_law_sha256'], 'oracle commitment mismatch')
    gold = _keyed(oracle['episodes'], 'episode'); cases = _keyed(inputs['episodes'], 'episode')
    require(gold.keys() == cases.keys(), 'oracle/input episode inventory differs')
    supports = {}
    for name, case in cases.items():
        row, ids, steps = gold[name], sorted(case['ids']), len(case['actions'])
        fields(row, ('episode', 'truth', 'possible_worlds', 'information_keys'))
        require(type(row['truth']) is list and len(row['truth']) == steps + 1 and
                type(row['possible_worlds']) is list and len(row['possible_worlds']) == steps and
                type(row['information_keys']) is list and len(row['information_keys']) == steps, 'oracle horizon differs')
        for truth, visible in zip(row['truth'], case['observations'], strict=True):
            fields(truth, ids)
            require(all(type(v) is int and v in (0, 1) for v in truth.values()) and
                    all(v is None or truth[k] == v for k, v in visible.items()), 'oracle contradicts delivered observation')
        for t, possible in enumerate(row['possible_worlds']):
            require(type(possible) is list and bool(possible) and all(type(w) is int and 0 <= w < 2 ** len(ids)
                    for w in possible) and possible == sorted(set(possible)), 'invalid oracle support')
            key = information_key(case, t)
            require(row['information_keys'][t] == key and _index([row['truth'][t + 1][i] for i in ids]) in possible,
                    'oracle information key or actual outcome outside support')
            require(key not in supports or supports[key] == possible, 'same visible information has conflicting oracle support')
            supports[key] = possible
    return gold


def _logs(encoded, entities):
    fields(encoded, ('values', 'null_status'))
    require(encoded['null_status'] == 'negative_infinity' and type(encoded['values']) is list and
            len(encoded['values']) == 1 and type(encoded['values'][0]) is list and
            len(encoded['values'][0]) == 2 ** entities, 'forecast world geometry differs')
    values = encoded['values'][0]
    require(all(v is None or type(v) in (int, float) and math.isfinite(v) for v in values), 'invalid forecast log coordinate')
    return [-math.inf if v is None else float(v) for v in values]


def _frozen_identity(identity):
    fields(identity, ('predictor', 'state_sha256', 'effective_control', 'checkpoint_metadata',
                      'current_metadata', 'module_training'))
    metadata, spec, current = identity['checkpoint_metadata'], identity['predictor'], identity['current_metadata']
    fields(metadata, ('version', 'predictor', 'state_sha256', 'origin', 'provenance', 'scope'))
    fields(spec, ('kind', 'configuration', 'control', 'domain', 'supplied_biases', 'source_sha256'))
    require(metadata['version'] == 'cemm-active-checkpoint-v1' and digest(spec) == digest(metadata['predictor']) and
            identity['state_sha256'] == metadata['state_sha256'] and identity['effective_control'] == spec['control'],
            'frozen specification/state/control differs from checkpoint metadata')
    require(type(current) is dict and (identity['state_sha256'] is None or is_sha(identity['state_sha256'])),
            'invalid current predictor metadata')
    if spec['kind'] == 'no_change':
        require(current == {} and identity['state_sha256'] is None and identity['module_training'] is None,
                'no-change claims learned state')
    else:
        require(digest(current.get('checkpoint_metadata')) == digest(metadata) and
                digest(current.get('training_provenance')) == digest(metadata['provenance']),
                'current checkpoint/training provenance differs from checkpoint')
        if spec['kind'] == 'empirical':
            require(current.get('control_name') == spec['control'] and identity['module_training'] is None,
                    'empirical policy differs from checkpoint')
        else:
            adaptation = current.get('domain_adaptation', {})
            require(type(identity['module_training']) is dict and bool(identity['module_training']) and
                    all(v is False for v in identity['module_training'].values()) and
                    adaptation.get('active_learned_parameters_sha256') == identity['state_sha256'] and
                    digest(adaptation.get('training_provenance')) == digest(metadata['provenance']),
                    'neural evaluation mode/adaptation differs from checkpoint')


def _forecast(forecast, started, case, step):
    ids = sorted(case['ids'])
    required = {'status', 'episode', 'step', 'ids', 'raw_log', 'log', 'subtracted_log_mass', 'filter',
                'wall_seconds', 'cpu_seconds', 'receipt', 'action', 'evidence', 'implementation_sha256'}
    require(type(forecast) is dict and set(forecast) == required | ({'reason'} if forecast.get('status') == 'ABSTAIN' else set()),
            'unexpected or missing forecast fields')
    require(type(forecast) is dict and forecast.get('status') in ('PREDICTED', 'ABSTAIN') and
            forecast.get('episode') == case['episode'] and type(forecast.get('step')) is int and
            forecast['step'] == step and list(forecast.get('ids', [])) == ids and
            forecast.get('receipt') == receipt(forecast), 'forecast identity/receipt mismatch')
    require(forecast.get('action') == case['actions'][step] and
            forecast.get('evidence', {}).get('sensor_ids') == sorted(case['coverage'][step]) and
            forecast.get('implementation_sha256') == started['implementation_sha256'], 'forecast action/coverage/implementation differs')
    for key in ('wall_seconds', 'cpu_seconds'):
        require(type(forecast.get(key)) in (int, float) and math.isfinite(forecast[key]) and forecast[key] >= 0,
                'invalid forecast timing')
    correction = forecast['subtracted_log_mass']
    require(type(correction) is list and len(correction) == 1 and type(correction[0]) in (int, float) and
            math.isfinite(correction[0]) and abs(correction[0]) <= 1e-10, 'invalid normalization correction')
    if forecast['status'] == 'ABSTAIN':
        require(forecast.get('log') is None and forecast.get('raw_log') is None and correction[0] == 0,
                'abstention contains a distribution')
        return None
    logs, raw = _logs(forecast['log'], len(ids)), _logs(forecast['raw_log'], len(ids))
    require(all((a == b == -math.inf) or (math.isfinite(a) and math.isfinite(b) and
                abs((a - correction[0]) - b) <= 1e-12) for a, b in zip(raw, logs, strict=True)),
            'raw and normalized forecasts disagree')
    maximum = max(logs)
    require(math.isfinite(maximum) and abs(maximum + math.log(sum(math.exp(x - maximum) for x in logs))) <= 1e-12,
            'forecast is not normalized')
    return logs


def validate_bundle(plan, inputs, oracle, traces):
    inputs = validate_inputs(inputs); plan = validate_plan(plan, inputs)
    oracle = deepcopy(oracle); gold = validate_oracle(oracle, inputs, plan)
    require(type(traces) is list, 'trace list required')
    run_map, incomplete = {}, []
    cases = _keyed(inputs['episodes'], 'episode'); strata = _keyed(plan['cases'], 'episode')
    for trace in deepcopy(traces):
        required = {'version', 'input_sha256', 'checkpoint_sha256', 'participant', 'model_seed', 'episodes',
                    'source_sha256', 'frozen_predictor_before', 'frozen_predictor_after'}
        require(type(trace) is dict and required <= set(trace) and set(trace) <= required | {'resources'}, 'invalid trace fields')
        arm, seed = trace['participant'], trace['model_seed']
        require(type(seed) is int and arm in plan['participants'] and seed in plan['model_seeds'] and
                (arm, seed) not in run_map, 'duplicate or unexpected participant/seed')
        require(trace['version'] == 'active-acceptance-trace-v1' and trace['input_sha256'] == digest(inputs) and
                trace['checkpoint_sha256'] == plan['participants'][arm][str(seed)] and
                digest(trace['frozen_predictor_before']) == digest(trace['frozen_predictor_after']) and
                type(trace['frozen_predictor_before']) is dict, 'trace checkpoint/input/frozen-state mismatch')
        _frozen_identity(trace['frozen_predictor_before'])
        require(type(trace['source_sha256']) is dict and bool(trace['source_sha256']) and
                trace['source_sha256'].get('acceptance_runner.py') == plan['software_sha256']['acceptance_runner.py'] and
                all(plan['software_sha256'].get(k) == v for k, v in trace['source_sha256'].items()),
                'trace source hashes differ from plan')
        outputs = _keyed(trace['episodes'], 'episode')
        require(outputs.keys() <= cases.keys(), 'unplanned output episode')
        for name, output in outputs.items():
            fields(output, ('episode', 'started', 'events', 'failure', 'ended'))
            require(type(output['events']) is list and len(output['events']) <= len(cases[name]['actions']), 'invalid event inventory')
            started = output['started']
            if started is None:
                require(not output['events'] and output['failure'] is not None, 'missing start without failure')
            else:
                require(started.get('status') == 'STARTED' and started.get('episode') == name and
                        list(started.get('ids', [])) == sorted(cases[name]['ids']) and
                        started.get('world_order') == [list(w) for w in product((0, 1), repeat=len(cases[name]['ids']))] and
                        started.get('implementation_sha256') == sha256(json.dumps(started['implementation'], sort_keys=True).encode()).hexdigest(),
                        'startup identity/world order mismatch')
                identity = trace['frozen_predictor_before']
                require(started['implementation'].get('source_sha256') ==
                        {k: plan['software_sha256'][k] for k in INFERENCE_SOURCES}, 'inference sources differ from plan')
                require(started['implementation'].get('checkpoint') == identity.get('checkpoint_metadata') and
                        started['implementation'].get('control') == identity.get('effective_control'),
                        'startup checkpoint/control differs from frozen identity')
                state = started['implementation'].get('checkpoint_state_sha256')
                table = started['implementation'].get('empirical_table_sha256')
                require((state if state is not None else table) == identity.get('state_sha256'),
                        'startup learned state differs from frozen identity')
            for t, event in enumerate(output['events']):
                fields(event, ('step', 'forecast', 'feedback'))
                require(type(event['step']) is int and event['step'] == t, 'noncontiguous/duplicate output step')
                _forecast(event['forecast'], started, cases[name], t)
                feedback = event['feedback']
                if feedback is None:
                    require(t == len(output['events']) - 1 and output['failure'] is not None, 'missing feedback before continuation')
                else:
                    require(feedback.get('status') == 'RECEIVED' and feedback.get('episode') == name and
                            type(feedback.get('next_step')) is int and feedback['next_step'] == t + 1, 'feedback acknowledgment differs')
            if output['failure'] is None:
                require(len(output['events']) == len(cases[name]['actions']) and output['ended'] is not None and
                        all(e['feedback'] is not None for e in output['events']) and
                        output['ended'].get('status') == 'ENDED' and output['ended'].get('pending_forecast') is False and
                        type(output['ended'].get('feedback_steps')) is int and
                        output['ended']['feedback_steps'] == len(output['events']) and
                        type(output['ended'].get('predictions')) is int and
                        output['ended']['predictions'] == len(output['events']),
                        'successful episode is incomplete')
            else:
                failure = output['failure']
                require(type(failure) is dict and failure.get('phase') in ('start', 'predict', 'feedback', 'end') and
                        type(failure.get('step')) is int and 0 <= failure['step'] <= len(cases[name]['actions']) and
                        identifier(failure.get('error_type')) and type(failure.get('message')) is str,
                        'invalid failure record')
                phase, t, events = failure['phase'], failure['step'], output['events']
                require(output['ended'] is None, 'failed episode also claims completion')
                if phase == 'start':
                    require(started is None and not events and t == 0, 'start failure inventory differs')
                elif phase == 'predict':
                    require(started is not None and t < len(cases[name]['actions']) and len(events) == t and
                            all(e['feedback'] is not None for e in events), 'prediction failure inventory differs')
                elif phase == 'feedback':
                    require(started is not None and len(events) == t + 1 and events[-1]['feedback'] is None and
                            all(e['feedback'] is not None for e in events[:-1]), 'feedback failure inventory differs')
                else:
                    require(started is not None and t == len(events) == len(cases[name]['actions']) and
                            all(e['feedback'] is not None for e in events), 'end failure inventory differs')
        run_map[arm, seed] = (trace, outputs)
    rows = []
    for arm in plan['participants']:
        for seed in plan['model_seeds']:
            trace, outputs = run_map.get((arm, seed), (None, {}))
            if trace is None: incomplete.append({'participant': arm, 'model_seed': seed, 'reason': 'MISSING_TRIAL'})
            for name, case in cases.items():
                output, ids = outputs.get(name), sorted(case['ids'])
                if output is None: incomplete.append({'participant': arm, 'model_seed': seed, 'episode': name, 'reason': 'MISSING_EPISODE'})
                for t, action in enumerate(case['actions']):
                    event = output['events'][t] if output and t < len(output['events']) else None
                    logs = _forecast(event['forecast'], output['started'], case, t) if event else None
                    rows.append({'participant': arm, 'model_seed': seed, **strata[name], 'step': t, 'ids': ids,
                        'truth': [gold[name]['truth'][t + 1][i] for i in ids],
                        'previous_truth': [gold[name]['truth'][t][i] for i in ids],
                        'possible_worlds': gold[name]['possible_worlds'][t], 'information_key': information_key(case, t),
                        'action_kind': action['kind'], 'status': 'UNPRODUCED' if event is None else 'ABSTAIN' if logs is None else 'ANSWERED',
                        'log_probabilities': logs, 'wall_seconds': event['forecast']['wall_seconds'] if event else None,
                        'cpu_seconds': event['forecast']['cpu_seconds'] if event else None})
    metadata = {'version': VERSION, 'gate_g1': 'NOT_ADMITTED', 'scientific_admission': False,
        'contract_sha256': contract_digest(), 'plan_sha256': digest(plan), 'input_sha256': digest(inputs),
        'oracle_sha256': digest(oracle), 'oracle_source_sha256': plan['oracle_source_sha256'],
        'information_law_sha256': plan['information_law_sha256'], 'scope': plan['scope'],
        'reference_participant': plan['reference_participant'], 'incomplete_inventory': incomplete,
        'trace_sha256': [digest(t) for t in traces], 'independent_custody_verified': False,
        'oracle_support_completeness_verified': False, 'capacity_or_compute_match_established': False,
        'source_sha256': {'acceptance_contract.py': sha256(Path(__file__).read_bytes()).hexdigest()},
        'frozen_software_sha256': plan['software_sha256'],
        'physical_lineages': len({r['lineage'] for r in plan['cases']}),
        'seed_labels_authenticated': False,
        'reused_checkpoints': [{'participant': arm, 'checkpoint_sha256': checkpoint,
            'model_seeds': [s for s in plan['model_seeds'] if inventory[str(s)] == checkpoint]}
            for arm, inventory in plan['participants'].items() for checkpoint in sorted(set(inventory.values()))
            if sum(value == checkpoint for value in inventory.values()) > 1],
        'runs': [{'participant': arm, 'model_seed': seed, 'checkpoint_sha256': trace['checkpoint_sha256'],
                  'frozen_predictor': trace['frozen_predictor_before'], 'source_sha256': trace['source_sha256'],
                  'resources': trace.get('resources')} for (arm, seed), (trace, _) in run_map.items()],
        'declared_lineage_only': True, 'failure_records': [{'participant': arm, 'model_seed': seed, 'episode': name,
            **row['failure']} for (arm, seed), (_, outputs) in run_map.items() for name, row in outputs.items() if row['failure']]}
    return {'rows': rows, 'metadata': metadata}
