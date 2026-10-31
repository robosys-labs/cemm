"""Narrow, separately versioned timing inputs; the native wire stays frozen."""
import math

from .acceptance_contract import digest, fields, identifier, require, receipt, _logs

VERSION = 'timing-input-v1'
TIMINGS = ('ordered', 'common_snapshot')


def implementation_identity(predictor, weights, sources):
    return {'version': 'timing-inference-v1', 'source_sha256': sources,
        'native_predictor': predictor, 'checkpoint_state_sha256': weights,
        'scheduler': 'binary_delta_union; shared_fixed_mode; common_background_once',
        'domain': {'entities': [3, 4, 5, 6], 'contacts_per_group': 2,
            'full_feedback': True, 'self_contact': False, 'event_limit': 128,
            'max_ordered_world_pairs': 4096, 'max_common_event_outputs': 16},
        'gate_g1': 'NOT_ADMITTED'}


def action_contacts(action, ids):
    require(type(action) is dict, 'action must be an object')
    kind = action.get('kind')
    require(kind in ('contact', 'contact_group'), 'unsupported timing action')
    if kind == 'contact':
        fields(action, ('kind', 'participants'))
        contacts, timing = [action['participants']], 'ordered'
    else:
        fields(action, ('kind', 'timing', 'contacts'))
        contacts, timing = action['contacts'], action['timing']
        require(type(timing) is str and timing in TIMINGS, 'invalid timing')
        require(type(contacts) is list and len(contacts) == 2, 'exactly two grouped contacts required')
    for pair in contacts:
        require(type(pair) is list and len(pair) == 2 and all(type(x) is str and x in ids for x in pair)
                and pair[0] != pair[1], 'distinct known contact handles required')
    return contacts, timing


def observation(value, ids):
    require(type(value) is dict and set(value) == set(ids) and
            all(type(v) is int and v in (0, 1) for v in value.values()), 'full binary observation required')
    return [value[name] for name in ids]


def validate_inputs(value):
    fields(value, ('version', 'episodes'))
    require(value['version'] == VERSION and type(value['episodes']) is list and
            0 < len(value['episodes']) <= 10000, 'invalid timing input inventory')
    names = set()
    for case in value['episodes']:
        fields(case, ('episode', 'ids', 'observations', 'actions', 'coverage'))
        name, ids = case['episode'], case['ids']
        require(identifier(name) and name not in names, 'invalid or duplicate episode')
        names.add(name)
        require(type(ids) is list and 3 <= len(ids) <= 6 and all(identifier(x) for x in ids)
                and len(set(ids)) == len(ids), 'three to six distinct IDs required')
        actions, readings, coverage = case['actions'], case['observations'], case['coverage']
        require(type(actions) is list and 1 <= len(actions) <= 128 and type(readings) is list and
                len(readings) == len(actions) + 1 and type(coverage) is list and len(coverage) == len(actions),
                'invalid timing episode geometry')
        for reading in readings: observation(reading, ids)
        for action, selected in zip(actions, coverage, strict=True):
            action_contacts(action, ids)
            require(type(selected) is list and len(selected) == len(ids) and
                    all(type(x) is str for x in selected) and set(selected) == set(ids), 'full coverage required')
    return value


def _prefix(case, step):
    require(type(step) is int and 0 <= step < len(case['actions']), 'invalid information step')
    return {'ids': sorted(case['ids']), 'observations': case['observations'][:step + 1],
            'actions': case['actions'][:step], 'coverage': [sorted(x) for x in case['coverage'][:step]]}


def history_key(case, step):
    """Delivered prefix only; excludes the queried operation and episode label."""
    return digest(_prefix(case, step))


def information_key(case, step):
    return digest({**_prefix(case, step), 'query': case['actions'][step],
                   'query_coverage': sorted(case['coverage'][step])})


def forecast_logs(value, case, step, implementation):
    fields(value, ('status', 'episode', 'step', 'ids', 'action', 'sensor_ids', 'log',
                   'normalization_log_total', 'implementation_sha256', 'wall_seconds', 'cpu_seconds', 'receipt'))
    require(value['status'] == 'PREDICTED' and value['episode'] == case['episode'] and
            type(value['step']) is int and value['step'] == step and value['ids'] == sorted(case['ids']) and
            value['action'] == case['actions'][step] and value['sensor_ids'] == sorted(case['coverage'][step]) and
            value['implementation_sha256'] == implementation and value['receipt'] == receipt(value),
            'forecast identity/action/coverage/receipt differs')
    require(all(type(value[k]) in (int, float) and math.isfinite(value[k]) and value[k] >= 0
                for k in ('wall_seconds', 'cpu_seconds')), 'invalid forecast timing')
    correction = value['normalization_log_total']
    require(type(correction) is list and len(correction) == 1 and type(correction[0]) in (int, float)
            and math.isfinite(correction[0]) and abs(correction[0]) <= 1e-10, 'invalid raw forecast mass')
    logs = _logs(value['log'], len(case['ids']))
    maximum = max(logs)
    require(math.isfinite(maximum) and abs(maximum + math.log(math.fsum(math.exp(v - maximum)
            for v in logs))) <= 1e-12, 'unnormalized timing forecast')
    return logs
