"""Four learned action alternatives over an immutable acquired world.

Identity markers, event boundaries and the candidate menu are supplied. No
literal word selects an effect, role or sense. Endpoints arrive after forecasts.
"""
from collections import defaultdict
from hashlib import sha256
import math

import torch
from torch import nn
from torch.nn import functional as F

from . import acceptance_contract as c, bilingual_model as prior, domain_contract as domain
from .bilingual_contract import validate_inputs
from .binding_layout_coordinates import LayoutCoordinateEncoder
from .domain_kernel import DomainKernel
from .joint_objective import DTYPE, require


class UnresolvedLexeme(ValueError):
    """Unregistered strings retain separate identities and acquire no meaning."""
    def __init__(self, tokens):
        self.records = [{'token': token, 'id': sha256(token.encode('utf-8')).hexdigest(),
                         'status': 'UNRESOLVED_LEXICAL_IDENTITY'} for token in sorted(set(tokens))]
        super().__init__('unregistered lexical identities: ' + ', '.join(r['token'] for r in self.records))


def _identity_features(token, nonce):
    raw = sha256(b'effect-role-token-v1\0' + token.encode('utf-8') + b'\0' + str(nonce).encode()).digest()
    return tuple(int.from_bytes(raw[i:i + 4], 'big') / 2 ** 31 - 1. for i in range(0, 32, 4))


def _assign(token, used, legacy):
    values = tuple(prior._characters(token))
    if values not in used: return {'features': list(values), 'source': 'characters', 'nonce': None}
    require(not legacy, 'inherited lexical character features collide')
    for nonce in range(256):
        values = _identity_features(token, nonce)
        if values not in used:
            return {'features': list(values), 'source': 'identity_collision', 'nonce': nonce}
    raise ValueError('bounded lexical collision resolution exhausted')


def create_registry(inputs):
    """Register TRAIN tapes only; the first tape is the inherited vocabulary.

Existing character vectors are never rewritten. Only new colliding identities
receive deterministic identity vectors; these are supplied features, not meanings.
"""
    require(type(inputs) is list and bool(inputs), 'ordered training tapes required')
    banks = [validate_inputs(bank) for bank in inputs]
    vocabularies = [{word for record in bank['episodes'] for event in record['utterances']
                    for word in event['text'].split() if word not in record['entities']} for bank in banks]
    legacy = vocabularies[0]; vocabulary = set.union(*vocabularies)
    require(len(vocabulary) <= 256, 'bounded lexical registry exceeded')
    tokens, used = {}, set()
    for token in [*sorted(legacy), *sorted(vocabulary - legacy)]:
        record = {'id': sha256(token.encode('utf-8')).hexdigest(), **_assign(token, used, token in legacy)}
        tokens[token] = record; used.add(tuple(record['features']))
    return {'version': 'effect-role-lexical-registry-v1', 'legacy_tokens': sorted(legacy),
            'training_sha256': [c.digest(bank) for bank in banks], 'tokens': tokens}


def validate_registry(registry):
    c.fields(registry, ('version', 'legacy_tokens', 'training_sha256', 'tokens'))
    tokens, legacy = registry['tokens'], registry['legacy_tokens']
    require(registry['version'] == 'effect-role-lexical-registry-v1' and type(tokens) is dict and
        0 < len(tokens) <= 256 and all(type(t) is str and bool(t) and len(t) <= 512 and len(t.split()) == 1 for t in tokens),
        'invalid lexical registry')
    require(type(legacy) is list and legacy and all(type(t) is str for t in legacy) and
        legacy == sorted(set(legacy)) and set(legacy) <= tokens.keys() and
        type(registry['training_sha256']) is list and registry['training_sha256'] and
        all(c.is_sha(value) for value in registry['training_sha256']), 'invalid registry provenance')
    used, identities = set(), set()
    for token in [*legacy, *sorted(tokens.keys() - set(legacy))]:
        record = tokens[token]; c.fields(record, ('id', 'features', 'source', 'nonce'))
        require(record['id'] == sha256(token.encode('utf-8')).hexdigest() and record['id'] not in identities,
                'lexical identity differs')
        require(type(record['features']) is list and len(record['features']) == 8 and
                all(type(v) is float and math.isfinite(v) for v in record['features']), 'invalid lexical features')
        require({k: record[k] for k in ('features', 'source', 'nonce')} == _assign(token, used, token in legacy),
                'lexical assignment differs')
        used.add(tuple(record['features'])); identities.add(record['id'])
    return registry


def tokenize_batch(messages, rosters, registry):
    """Return ordinary token features/mentions or exact typed unresolved records."""
    validate_registry(registry)
    features, mentions = prior.tokenize_batch(messages, rosters)
    unknown = {word for message, roster in zip(messages, rosters, strict=True)
               for word in message.split() if word not in roster and word not in registry['tokens']}
    if unknown: raise UnresolvedLexeme(unknown)
    for row, (message, roster) in enumerate(zip(messages, rosters, strict=True)):
        for slot, token in enumerate(message.split()):
            if token not in roster:
                features[row, slot, 1:] = torch.tensor(registry['tokens'][token]['features'], dtype=DTYPE)
    return features, mentions


class EffectRoleEncoder(LayoutCoordinateEncoder):
    def __init__(self):
        super().__init__()
        self.order = nn.Bilinear(1, 1, 4, dtype=DTYPE)


def encoder(seed, parent_state):
    """Copy all 88 accepted scalars; the four additional scalars start at zero."""
    require(type(seed) is int and 0 <= seed < 2 ** 63 and isinstance(parent_state, dict),
            'valid seed and explicit parent tensors required')
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed); net = EffectRoleEncoder()
    state = net.state_dict()
    require(set(state) == set(parent_state), 'parent language tensor inventory differs')
    copied = 0
    with torch.no_grad():
        for name, target in state.items():
            source = parent_state[name]
            if isinstance(source, torch.Tensor):
                require(source.dtype == DTYPE and source.device.type == 'cpu', 'parent tensor dtype/device differs')
            source = torch.as_tensor(source, dtype=DTYPE)
            expected = target[:2] if name.startswith('order.') else target
            require(source.shape == expected.shape and bool(torch.isfinite(source).all()), 'parent tensor geometry differs')
            expected.copy_(source); copied += source.numel()
            if name.startswith('order.'): target[2:].zero_()
    require(copied == 88 and sum(p.numel() for p in net.parameters()) == 92, 'effect/role parameter inventory differs')
    return net


def action_candidates(mentions):
    contacts = prior.action_candidates(mentions)
    sets = torch.full_like(contacts, -1)
    sets[:, :, 0], sets[:, :, 1], sets[:, :, 3] = 1, mentions, 1
    return torch.cat((contacts, sets), 1)


def _frozen(world):
    require(type(world) is DomainKernel and world.memory is True and not world.training and
            all(not parameter.requires_grad for parameter in world.parameters()), 'explicit frozen persistent world required')


@torch.no_grad()
def frozen_options(world, pre, state, mentions):
    _frozen(world); entities = domain.validate_anchor(pre, 1); actions = action_candidates(mentions)
    require(len(actions) == len(pre) and bool((mentions < entities).all()), 'identity outside world')
    require(isinstance(state, torch.Tensor) and state.shape == (len(pre), 2), 'invalid mode state')
    _, pending = world.predict(pre.repeat_interleave(4, 0), actions.reshape(-1, 4), state.repeat_interleave(4, 0))
    return pending.reshape(len(pre), 4, 2, 2 ** entities).detach()


def combine(action_logp, options):
    """Marginalize four actions while preserving the same two persistent modes."""
    require(isinstance(action_logp, torch.Tensor) and action_logp.device.type == 'cpu' and
        action_logp.dtype == DTYPE and action_logp.ndim == 2 and action_logp.shape[1] == 4 and
        len(action_logp) > 0 and not bool((torch.isnan(action_logp) | torch.isposinf(action_logp)).any()) and
        bool((action_logp.logsumexp(-1).abs() <= 1e-10).all()), 'invalid action probabilities')
    require(isinstance(options, torch.Tensor) and options.device.type == 'cpu' and options.dtype == DTYPE and
        options.ndim == 4 and options.shape[:3] == (len(action_logp), 4, 2) and options.shape[3] in (8, 16, 32, 64) and
        not bool((torch.isnan(options) | torch.isposinf(options)).any()) and
        bool((options.flatten(2).logsumexp(-1).abs() <= 1e-10).all()), 'invalid native action forecasts')
    pending = domain.safe_logsumexp(options + action_logp[:, :, None, None], 1)
    return domain.safe_logsumexp(pending, 1), pending


def text_only_context(pre, mentions):
    entities = domain.validate_anchor(pre, 1); actions = action_candidates(mentions)
    require(len(actions) == len(pre) and bool((mentions < entities).all()), 'identity outside world')
    context = torch.zeros(len(pre), 48, dtype=DTYPE)
    context[:, 6:6 + entities] = 1.
    context[:, 36:] = F.one_hot(mentions, 6).to(DTYPE).flatten(1)
    return context


def pack(inputs, world, registry):
    """Cache likelihoods from earlier readings only; SET-only context is legal."""
    _frozen(world); validate_registry(registry)
    grouped = defaultdict(list)
    for record in validate_inputs(inputs)['episodes']:
        grouped[len(record['entities']), len(record['utterances']), len(record['context'])].append(record)
    result = []
    for (n, steps, context_steps), records in sorted(grouped.items()):
        tensor = lambda values: torch.tensor(values, dtype=DTYPE)
        pre = tensor([r['anchor'] for r in records]); state = world.initial(len(records))
        with torch.no_grad():
            for t in range(context_steps):
                action = torch.tensor([r['context'][t]['action'] for r in records], dtype=torch.long)
                post = tensor([r['context'][t]['reading'] for r in records])
                _, pending = world.predict(pre, action, state)
                state, pre = world.receive(pending, post), post
        group = {'n': n, 'records': records, 'state': state.detach(), 'events': []}
        for t in range(steps):
            features, mentions = tokenize_batch([r['utterances'][t]['text'] for r in records],
                                                [r['entities'] for r in records], registry)
            uniform = world.initial(len(records))
            likelihood = frozen_options(world, pre, uniform, mentions) - uniform[:, None, :, None]
            post = tensor([r['utterances'][t]['reading'] for r in records])
            group['events'].append({'features': features, 'mentions': mentions, 'likelihood': likelihood,
                'post': post, 'target': domain.world_index(post), 'text_context': text_only_context(pre, mentions)})
            pre = post
        result.append(group)
    return result


def forecasts(arm, net, world, group, view='canonical'):
    """Masked views alter this event only; preceding feedback remains canonical."""
    require(arm in ('grounded', 'parser', 'text_only') and view in ('canonical', 'masked'), 'unknown forecast arm/view')
    _frozen(world); state = group['state']
    for event in group['events']:
        features = event['features']
        if view == 'masked':
            features = features.clone(); features[:, :, 1:] = 0.
        if arm == 'text_only':
            yield net(features, event['text_context'], group['n']), None
        else:
            actions = net(event['features'])
            options = event['likelihood'] + state[:, None, :, None]
            raw, pending = combine(actions, options)
            if view == 'masked':
                actions = net(features); raw, _ = combine(actions, options)
            yield raw, actions
            state = world.receive(pending, event['post'])
