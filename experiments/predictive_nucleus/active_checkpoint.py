"""Strict learned-state JSON artifacts for fresh episodes, never executable code.

Source hashes bind local inference definitions, not an independent evaluation or
authenticated training history. No optimizer or live episode state is retained.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path

import torch

from . import active_paths
from .domain_contract import DomainMemory, binary_worlds, domain_context, require
from .domain_flat import DomainFlatGRU
from .domain_kernel import DomainKernel
from .joint_objective import fingerprint

VERSION = 'cemm-active-checkpoint-v1'
MAX_BYTES = 16 * 1024 * 1024
DOMAIN = {'entities': [3, 4, 5, 6], 'self_contact': True, 'binary_state': True,
          'full_initial_anchor': True, 'visible_readings_noiseless': True}
SCOPE = {'fresh_episodes_only': True, 'optimizer_resume': False, 'live_session_resume': False,
         'provenance_authenticated': False, 'gate_g1': 'NOT_ADMITTED'}


def _sha(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _fields(value, names):
    require(type(value) is dict and set(value) == set(names), 'checkpoint fields differ')


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _plain(value, depth=0):
    require(depth < 20 and type(value) in (dict, list, str, int, float, bool, type(None)),
            'plain bounded JSON metadata required')
    if type(value) is dict:
        require(all(type(k) is str for k in value), 'metadata keys must be strings')
        for v in value.values(): _plain(v, depth + 1)
    elif type(value) is list:
        for v in value: _plain(v, depth + 1)
    elif type(value) is float:
        require(math.isfinite(value), 'nonfinite metadata')


def _provenance(value):
    _plain(value)
    require(type(value) is dict and {'training_input_sha256', 'objective', 'completed_updates'} <= set(value),
            'declared training provenance fields required')
    digest, objective, updates = value['training_input_sha256'], value['objective'], value['completed_updates']
    require(type(objective) is str and objective in
            ('observed_joint_nll', 'observed_counts', 'no_change', 'untrained_or_inherited') and
            type(updates) is int and updates >= 0, 'invalid training objective/update count')
    require(_sha(digest) or (digest is None and updates == 0 and
            objective in ('no_change', 'untrained_or_inherited')), 'invalid training input fingerprint')
    return deepcopy(value)


def _factory(kind, config):
    names = {'kernel': ('hidden', 'persistence', 'role_tying', 'memory'),
             'flat': ('hidden', 'persistence'), 'empirical': ('mode',), 'no_change': ()}
    require(type(kind) is str and kind in names, 'unregistered predictor kind')
    _fields(config, names[kind])
    if kind in ('kernel', 'flat'):
        require(type(config['hidden']) is int and 0 < config['hidden'] <= 256 and
                all(type(v) is bool for k, v in config.items() if k != 'hidden'), 'invalid model configuration')
        with torch.random.fork_rng(devices=[]):
            return (DomainKernel if kind == 'kernel' else DomainFlatGRU)(**config)
    if kind == 'empirical':
        require(type(config['mode']) is str, 'invalid memory mode')
        return DomainMemory(config['mode'])
    return None


def _sources(kind):
    names = ['active_checkpoint.py', 'active_paths.py', 'domain_contract.py', 'masked_replay.py',
             'comparison_scoring.py', 'joint_objective.py']
    if kind in ('kernel', 'flat'): names.append('domain_' + kind + '.py')
    root = Path(__file__).parent
    return {name: sha256((root / name).read_bytes()).hexdigest() for name in names}


def _biases(kind, config):
    if kind == 'kernel':
        return {'locality_and_factorization': True, 'two_modes': True,
                'identifier_equivariance': True, 'role_swap_tying': config['role_tying'],
                'persistent_mode_memory': config['memory'], 'nonparticipant_persistence': config['persistence'],
                'self_contact': 'supplied_per_mode_alias_conditioning'}
    if kind == 'flat':
        return {'sorted_identity_slots': True, 'maximum_slots': 6, 'existence_mask': True,
                'output_geometry': 'condition_on_zero_padded_tail',
                'nonparticipant_persistence': config['persistence'], 'self_contact': 'shared_physical_coordinate'}
    return {'observed_only_counts': True, 'context_abstraction': config['mode']} if kind == 'empirical' else {
        'prediction': 'last_actually_observed_bit'}


def predictor_spec(*, model=None, memory=None, control=None):
    """Describe only registered predictors; reconstruction never executes file content."""
    require(sum((model is not None, memory is not None, control == 'no_change')) == 1,
            'exactly one model, memory or no_change control required')
    if model is not None:
        require(type(model) in (DomainKernel, DomainFlatGRU) and control is None, 'unregistered model/control')
        kind = 'kernel' if type(model) is DomainKernel else 'flat'
        config = {'hidden': model.pair[0].out_features if kind == 'kernel' else model.hidden,
                  'persistence': model.persistence}
        if kind == 'kernel': config.update(role_tying=model.role_tying, memory=model.memory)
    elif memory is not None:
        require(type(memory) is DomainMemory, 'unregistered empirical memory')
        kind, config, control = 'empirical', {'mode': memory.mode}, active_paths.empirical_control(memory, control)
    else:
        kind, config = 'no_change', {}
    expected = _factory(kind, config)
    predictor = model if model is not None else memory
    if predictor is not None:
        require(type(predictor.supported_entities) in (tuple, list) and
                tuple(predictor.supported_entities) == (3, 4, 5, 6) and
                type(predictor.supports_self_contact) is bool and predictor.supports_self_contact,
                'predictor domain differs from registered domain')
    if model is not None:
        topology = lambda m: [(name, type(module)) for name, module in m.named_modules()]
        require(topology(model) == topology(expected), 'registered model topology differs')
    return {'kind': kind, 'configuration': config, 'control': control, 'domain': deepcopy(DOMAIN),
            'supplied_biases': _biases(kind, config), 'source_sha256': _sources(kind)}


def _tensors(model, records=None):
    expected = model.state_dict()
    if records is None:
        return {name: {'dtype': str(t.dtype), 'shape': list(t.shape),
                       'values': t.detach().cpu().flatten().tolist()} for name, t in expected.items()}
    _fields(records, expected)
    restored = {}
    for name, template in expected.items():
        row = records[name]
        _fields(row, ('dtype', 'shape', 'values'))
        require(row['dtype'] == str(template.dtype) and type(row['shape']) is list and
                all(type(n) is int for n in row['shape']) and row['shape'] == list(template.shape) and
                type(row['values']) is list and len(row['values']) == template.numel(), 'invalid tensor geometry')
        scalar = float if template.is_floating_point() else int
        require(all(type(v) is scalar and (scalar is int or math.isfinite(v)) for v in row['values']),
                'invalid tensor scalar')
        value = torch.tensor(row['values'], dtype=template.dtype).reshape(template.shape)
        if name in dict(model.named_buffers()):
            require(torch.equal(value, template), 'registered geometry buffer differs')
        restored[name] = value
    model.load_state_dict(restored, strict=True)
    return model


def _tuples(value):
    require(type(value) in (list, int), 'empirical keys require integer coordinates')
    return tuple(_tuples(v) for v in value) if type(value) is list else value


def _key(key, mode):
    require(type(key) is tuple and len(key) == (5 if mode == 'prefix' else 6), 'invalid empirical key')
    n = key[0]
    binary_worlds(n)
    if mode == 'prefix':
        require(all(type(value) is tuple for value in key[1:]) and
                all(type(row) is tuple and len(row) == 3 and all(type(v) is tuple for v in row)
                    for row in key[4]), 'invalid prefix coordinates')
        require(domain_context(key[2], key[3], key[4], mode)[0] == key and len(key[2]) == n,
                'noncanonical prefix key')
        return n
    _, kind, value, aliases, pre, history = key
    require(type(pre) is tuple and type(history) is tuple and
            aliases in ((0, 0), (0, 1), (0,), ()), 'invalid abstraction coordinates/aliases')
    action = (kind, 0 if kind != 2 else -1,
              (0 if aliases == (0, 0) else 1) if kind == 0 else -1, value)
    expected = domain_context(pre, action, (), mode)[0]
    require(key[:-1] == expected[:-1] and len(pre) == n and (mode != 'local' or not history),
            'noncanonical abstraction key')
    for signature in history:
        require(type(signature) is tuple and len(signature) == 3 and signature[0] in ((0, 0), (0, 1)),
                'invalid contact history alias')
        size = len(set(signature[0]))
        require(all(type(bits) is tuple and len(bits) == size and all(type(b) is int and b in (-1, 0, 1) for b in bits)
                    for bits in signature[1:]), 'invalid contact history reading')
    return n


def _table(memory, state=None):
    if state is None:
        return {'origin_table_sha256': memory.origin_digest,
                'rows': [[key, sorted(counts.items())] for key, counts in sorted(memory.table.items())]}
    _fields(state, ('origin_table_sha256', 'rows'))
    require(state['origin_table_sha256'] is None or _sha(state['origin_table_sha256']), 'invalid table origin')
    require(type(state['rows']) is list, 'invalid table rows')
    for row in state['rows']:
        require(type(row) is list and len(row) == 2 and type(row[1]) is list and bool(row[1]), 'invalid table row')
        key, entries = _tuples(row[0]), row[1]
        n = _key(key, memory.mode)
        require(key not in memory.table, 'duplicate empirical context')
        counts = Counter()
        for entry in entries:
            require(type(entry) is list and len(entry) == 2, 'invalid outcome row')
            bits, count = _tuples(entry[0]), entry[1]
            require(type(bits) is tuple and len(bits) == n and all(type(b) is int and b in (0, 1) for b in bits) and bits not in counts and
                    type(count) is int and count > 0, 'invalid empirical outcome/count')
            counts[bits] = count
        memory.table[key] = counts
    memory.origin_digest = state['origin_table_sha256']
    return memory


def _origin(model):
    data = getattr(model, 'domain_adaptation', None)
    if data is None: return None
    require(type(data) is dict, 'invalid adaptation origin')
    if data.get('version') == VERSION: return deepcopy(data['origin'])
    require(data.get('version') == 'shared-domain-adaptation-v1', 'unknown adaptation origin')
    result = {key: data.get(key) for key in ('source_full_state_sha256', 'source_learned_parameters_sha256')}
    require(all(_sha(v) for v in result.values()), 'invalid adaptation fingerprint')
    return result


def _restore(document):
    _fields(document, ('version', 'predictor', 'state', 'state_sha256', 'origin', 'provenance', 'scope'))
    require(document['version'] == VERSION and _json(document['scope']) == _json(SCOPE), 'checkpoint version/scope differs')
    spec = document['predictor']
    _fields(spec, ('kind', 'configuration', 'control', 'domain', 'supplied_biases', 'source_sha256'))
    predictor = _factory(spec['kind'], spec['configuration'])
    model = predictor if spec['kind'] in ('kernel', 'flat') else None
    memory = predictor if spec['kind'] == 'empirical' else None
    if memory is not None: memory.control_name = spec['control']
    require(_json(predictor_spec(model=model, memory=memory, control=spec['control'])) == _json(spec),
            'checkpoint configuration/domain/bias/source mismatch')
    provenance = _provenance(document['provenance'])
    objective, updates = provenance['objective'], provenance['completed_updates']
    valid = ((model is not None and ((objective == 'observed_joint_nll' and updates > 0) or
              (objective == 'untrained_or_inherited' and updates == 0))) or
             (memory is not None and objective in ('observed_counts', 'untrained_or_inherited') and updates == 0) or
             (spec['kind'] == 'no_change' and objective == 'no_change' and updates == 0))
    require(valid, 'training provenance incompatible with predictor')
    origin = document['origin']
    require(origin is None or (spec['kind'] == 'kernel' and type(origin) is dict and
            set(origin) == {'source_full_state_sha256', 'source_learned_parameters_sha256'} and
            all(_sha(v) for v in origin.values())), 'invalid learned-state origin')
    if model is not None: _tensors(model, document['state']); model.eval()
    elif memory is not None: _table(memory, document['state'])
    else: require(document['state'] is None, 'no_change has no learned state')
    digest = fingerprint(model.state_dict()) if model is not None else memory.digest() if memory is not None else None
    require(document['state_sha256'] == digest, 'learned-state fingerprint mismatch')
    metadata = {key: deepcopy(value) for key, value in document.items() if key != 'state'}
    if model is not None:
        model.domain_adaptation = {'version': VERSION, 'origin': deepcopy(origin),
            'active_learned_parameters_sha256': digest, 'training_provenance': provenance,
            'supplied_biases': deepcopy(spec['supplied_biases'])}
    if predictor is not None:
        predictor.checkpoint_metadata = deepcopy(metadata)
        predictor.training_provenance = deepcopy(provenance)
    return {'model': model, 'memory': memory, 'control': spec['control'], 'metadata': metadata}


def save_checkpoint(path, *, model=None, memory=None, control=None, provenance):
    """Validate before exclusive creation; never mutate a source predictor or RNG."""
    spec = predictor_spec(model=model, memory=memory, control=control)
    if model is not None:
        require(all(t.device.type == 'cpu' and t.layout == torch.strided for t in model.state_dict().values()),
                'CPU strided learned tensors required')
    state = _tensors(model) if model is not None else _table(memory) if memory is not None else None
    digest = fingerprint(model.state_dict()) if model is not None else memory.digest() if memory is not None else None
    document = {'version': VERSION, 'predictor': spec, 'state': state, 'state_sha256': digest,
                'origin': _origin(model), 'provenance': _provenance(provenance), 'scope': deepcopy(SCOPE)}
    raw = _json(document) + b'\n'
    require(len(raw) <= MAX_BYTES, 'checkpoint exceeds size limit')
    # JSON round-trip validates serialized scalar types and table coordinate shape.
    restored = _restore(json.loads(raw))
    with Path(path).open('xb') as stream: stream.write(raw)
    return {'sha256': sha256(raw).hexdigest(), 'kind': spec['kind'], 'state_sha256': digest,
            'metadata': restored['metadata']}


def load_checkpoint(path, expected_sha256):
    """Load trusted local constructors only, after byte hash and schema checks."""
    require(_sha(expected_sha256), 'explicit expected checkpoint SHA-256 required')
    with Path(path).open('rb') as stream: raw = stream.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES and sha256(raw).hexdigest() == expected_sha256, 'checkpoint size/hash mismatch')
    def pairs(items):
        require(len(dict(items)) == len(items), 'duplicate JSON field')
        return dict(items)
    def invalid(value): raise ValueError('nonfinite JSON constant: ' + value)
    return _restore(json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid))
