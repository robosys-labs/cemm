"""Frozen learned-coordinate hypotheses projected into native physical outcomes."""
from copy import deepcopy

import torch

from . import acceptance_contract as c, continuation_run as io
from .effect_role_lexical import LexicalEffectRoleEncoder, encoder, inherited_ids
from .effect_role_model import action_candidates, combine, pack, validate_registry
from .effect_role_run import world_for
from .g3_train_coordinate_intervention import read_locked
from .joint_objective import DTYPE, fingerprint

VERSION = 'coordinate-transport-v1'
TRAINING_SHA256 = '766a8315d66e4a0bfca0079183d3966fbc7a0b4ed65c98177650d245a10671ed'
TRANSFORMS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
VIEWS = ('intact', 'zero_layout', 'cycled_layout')
ENDPOINT_ENCODING = 'domain_contract.world_index:ordered-roster-msb-first-binary-v1'


def restore(seed, law):
    """Restore the pinned v3 language and the requested acquired native world."""
    c.require(type(seed) is int and seed in (7, 11, 23, 37, 53) and
              type(law) is str and law in ('nand', 'nor'), 'unregistered model seed or law')
    fitted = io.ROOT / 'data/effect-role-fit-v3'
    training = read_locked(fitted / 'training.json', TRAINING_SHA256)
    c.require(training['version'] == 'effect-role-v3' and training['complete'] is True,
              'complete v3 training receipt required')
    data = io.ROOT / 'data/effect-role-v3'
    freeze = read_locked(data / 'freeze.json', training['freeze_sha256'])
    c.require(freeze['version'] == training['version'], 'frozen study differs')
    registry = read_locked(data / 'lexical-registry.json',
                           freeze['artifacts']['lexical-registry.json']['sha256'])
    legacy = inherited_ids(registry)
    key = f'grounded/{seed}'
    report, item = training['reports'][key], training['checkpoints'][key]
    c.require(item['file'] == f'grounded-{seed}.json', 'grounded checkpoint path differs')
    saved = read_locked(fitted / item['file'], item['sha256'])
    c.require(saved['arm'] == 'grounded' and saved['seed'] == seed, 'checkpoint identity differs')
    state = {name: torch.tensor(value, dtype=DTYPE) for name, value in saved['state'].items()}
    c.require(all(bool(torch.isfinite(value).all()) for value in state.values()),
              'nonfinite grounded checkpoint')
    parent = {name.removeprefix('parent.'): value for name, value in state.items()
              if name.startswith('parent.')}
    net = encoder(seed, parent, registry, legacy)
    c.require(fingerprint(net.state_dict()) == report['initial_sha256'], 'initial grounded state differs')
    net.load_state_dict(state, strict=True)
    net.eval().requires_grad_(False)
    language_sha = fingerprint(net.state_dict())
    c.require(language_sha == saved['state_sha256'] == report['final_sha256'] and
              list(net.new_ids) == report['new_ids'] and legacy == report['legacy_ids'] and
              c.digest(registry) == report['registry_sha256'] and
              fingerprint(net.parent.state_dict()) == report['protected_initial_sha256'] ==
              report['protected_final_sha256'], 'language or lexical frame binding differs')
    c.require(report['world_sha256'] == freeze['world_checkpoints'][f'nand/{seed}']['state_sha256'],
              'language training world differs')
    world = world_for(freeze, law, seed)
    world_sha = fingerprint(world.state_dict())
    c.require(world_sha == freeze['world_checkpoints'][f'{law}/{seed}']['state_sha256'],
              'acquired world state differs')
    metadata = {'seed': seed, 'law': law, 'training_sha256': TRAINING_SHA256,
                'freeze_sha256': training['freeze_sha256'], 'checkpoint_sha256': item['sha256'],
                'language_sha256': language_sha, 'registry_sha256': c.digest(registry),
                'world_sha256': world_sha, 'new_ids': list(net.new_ids)}
    return net, world, registry, metadata


@torch.no_grad()
def project(net, world, registry, records, view):
    """Project prefix-only instances through four fixed learned-coordinate views."""
    validate_registry(registry)
    registry_sha = c.digest(registry)
    c.require(type(net) is LexicalEffectRoleEncoder and not net.training and
              net.registry_sha256 == registry_sha and
              all(not p.requires_grad and p.grad is None for p in net.parameters()),
              'explicit frozen language with matching registry required')
    c.require(type(view) is str and view in VIEWS, 'unknown mapping intervention')
    c.require(type(records) is list and records, 'nonempty prefix-only record list required')
    language_sha, world_sha = fingerprint(net.state_dict()), fingerprint(world.state_dict())
    episodes, identities, prefixes = [], {}, {}
    for record in records:
        c.fields(record, ('id', 'entities', 'anchor', 'context', 'text'))
        c.require(c.identifier(record['id']) and record['id'] not in identities and
                  type(record['entities']) is list and len(record['entities']) == 3 and
                  type(record['text']) is str, 'invalid or duplicate three-participant instance')
        tokens = [word for word in record['text'].split() if word not in record['entities']]
        c.require(len(tokens) == 1 and tokens[0] in registry['tokens'], 'registered lexical identity required')
        identity = registry['tokens'][tokens[0]]['id']
        c.require(identity in net.new_ids, 'transport requires an acquired lexical identity')
        identities[record['id']] = identity
        prefixes[record['id']] = c.digest({key: record[key] for key in ('entities', 'anchor', 'context', 'text')})
        episodes.append({key: record[key] for key in ('id', 'entities', 'anchor', 'context')} |
                        {'utterances': [{'text': record['text'], 'reading': [0, 0, 0]}]})
    inputs = {'version': 'bilingual-input-v1', 'episodes': episodes}
    complemented = deepcopy(inputs)
    for record in complemented['episodes']:
        record['utterances'][0]['reading'] = [1, 1, 1]
    groups = pack(inputs, world, registry)
    other = {}
    for group in pack(complemented, world, registry):
        event, = group['events']
        actions = action_candidates(event['mentions'])
        for index, record in enumerate(group['records']):
            other[record['id']] = (group['state'][index], event['features'][index],
                event['mentions'][index], event['likelihood'][index], actions[index])
    variants = []
    for signs in TRANSFORMS:
        candidate = deepcopy(net)
        candidate.new_coordinates.mul_(torch.tensor(signs, dtype=DTYPE))
        layout = candidate.parent.layout[0].weight
        if view == 'zero_layout':
            layout.zero_()
        elif view == 'cycled_layout':
            layout.copy_(layout.roll(1, dims=1))
        variants.append(candidate)
    checks = {'records': 0, 'endpoint_complement_checks': 0, 'projection_checks': 0,
              'uniform_hypothesis_checks': 0, 'maximum_projection_error': 0., 'maximum_uniform_error': 0.}
    rows = {}
    for group in groups:
        event, = group['events']
        actions = action_candidates(event['mentions'])
        options = event['likelihood'] + group['state'][:, None, :, None]
        native = options.logsumexp(2).exp()
        action_weights, likelihoods = [], []
        for candidate in variants:
            action_logp = candidate(event['features'])
            raw, _ = combine(action_logp, options)
            action_weights.append(action_logp.exp())
            likelihoods.append(raw.exp())
        action_weights = torch.stack(action_weights, dim=1)
        likelihoods = torch.stack(likelihoods, dim=1)
        error = float((likelihoods - action_weights @ native).abs().max())
        uniform_error = float((action_weights.mean(1) - .25).abs().max())
        c.require(error <= 1e-12 and uniform_error <= 1e-12, 'hypothesis projection invariant failed')
        checks['maximum_projection_error'] = max(checks['maximum_projection_error'], error)
        checks['maximum_uniform_error'] = max(checks['maximum_uniform_error'], uniform_error)
        for index, record in enumerate(group['records']):
            evidence_id = record['id']
            actual = (group['state'][index], event['features'][index], event['mentions'][index],
                      event['likelihood'][index], actions[index])
            c.require(all(torch.equal(a, b) for a, b in zip(actual, other[evidence_id], strict=True)),
                      'endpoint placeholder changed a pre-observation input')
            frame = {'version': VERSION, 'language_sha256': language_sha,
                     'registry_sha256': registry_sha, 'world_sha256': world_sha,
                     'lexical_id': identities[evidence_id], 'transforms': [list(t) for t in TRANSFORMS],
                     'view': view}
            rows[evidence_id] = {'evidence_id': evidence_id, 'prefix_digest': prefixes[evidence_id],
                'entities': list(record['entities']), 'actions': actions[index].tolist(),
                'endpoint_encoding': ENDPOINT_ENCODING, 'action_probabilities': action_weights[index].tolist(),
                'native_likelihood': native[index].tolist(), 'likelihood': likelihoods[index].tolist(),
                'frame': frame, 'frame_digest': c.digest(frame)}
            checks['records'] += 1
            checks['endpoint_complement_checks'] += 1
            checks['projection_checks'] += len(TRANSFORMS)
            checks['uniform_hypothesis_checks'] += 1
    c.require(set(rows) == set(other) == set(identities), 'projection inventory differs')
    checks['language_unchanged'] = fingerprint(net.state_dict()) == language_sha
    checks['world_unchanged'] = fingerprint(world.state_dict()) == world_sha
    c.require(checks['language_unchanged'] and checks['world_unchanged'] and c.digest(registry) == registry_sha,
              'projection changed frozen language, world or registry')
    return rows, checks
