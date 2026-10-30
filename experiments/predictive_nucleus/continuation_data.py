"""One bounded continuation study; evaluator-only construction, no learner import.

The first ordinary contact is informative acquisition counted in the contact
budget. Query indices and masks are fixed before the persistent hidden mode.
The public recipe is reproducible, not independent challenge custody.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import random

from . import acceptance_contract as contract, prospective_oracle as oracle
from .prospective_data import SPLITS, blueprint_digest, template_digest, _realize

DEVELOPMENT = ('single_contact', 'two_contacts')


def _rng(label, material):
    return random.Random(int(contract.digest([label, *material]), 16))


def _cells(split, entities):
    families = (*DEVELOPMENT, 'three_contact_chain', 'fork', 'cycle', 'disjoint', 'self_contact')
    for family in families if split == 'evaluation' else DEVELOPMENT:
        lengths = (1,) if family in ('single_contact', 'self_contact') else (2,) if family == 'two_contacts' else (3, 4, 5)
        for count in lengths:
            minimum = count + 1 if family in ('three_contact_chain', 'fork') else count if family == 'cycle' else 4 if family == 'disjoint' else 3
            for n in entities:
                if n >= minimum: yield family, n, count


def _candidate(material, family, entities, count, split):
    rng = _rng('continuation-blueprint-v1', material)
    ids = [contract.digest(['continuation-id-v1', *material, i])[:20] for i in range(entities)]
    initial = dict(zip(ids, [rng.randrange(2) for _ in ids], strict=True))
    if family == 'single_contact': edges = [(0, 1)]
    elif family == 'two_contacts': edges = [(0, 1), (0, 1) if rng.randrange(2) else (1, 2)]
    elif family == 'three_contact_chain': edges = [(i, i + 1) for i in range(count)]
    elif family == 'fork': edges = [(0, i + 1) for i in range(count)]
    elif family == 'cycle': edges = [(i, (i + 1) % count) for i in range(count)]
    elif family == 'disjoint': edges = [(0, 1) if i % 2 == 0 else (2, 3) for i in range(count)]
    else: edges = [(0, 0)]
    actions, before = [], dict(initial)
    if rng.random() < .5:
        who, value = rng.choice(ids), rng.randrange(2)
        actions.append({'kind': 'set', 'participants': [who], 'value': value})
        before[who] = value
    first = len(actions)
    if family != 'self_contact' and not any(before[ids[i]] for i in edges[0]): return None
    actions += [{'kind': 'contact', 'participants': [ids[a], ids[b]]} for a, b in edges]
    if rng.random() < .5: actions.append({'kind': 'observe', 'participants': []})
    rng.shuffle(ids)
    available = [(t, i) for t in range(first + 1, len(actions)) for i in ids]
    missing = set(rng.sample(available, rng.randrange(min(3, len(available)) + 1))) if (
        split == 'evaluation' and family != 'self_contact') else set()
    observations = [{i: initial[i] for i in ids}]
    observations += [{i: None if (t, i) in missing else 0 for i in ids} for t in range(len(actions))]
    return {'episode': 'blueprint', 'ids': ids, 'observations': observations,
            'actions': actions, 'coverage': [ids.copy() for _ in actions]}


def build_assets(config):
    """Return strict observed/oracle splits and separate evaluator query metadata.

    config.data contains entity_counts, split_seeds, draws_per_cell and
    max_blueprint_attempts. Smaller inventories support implementation tests;
    the study runner pins the actual complete config before fitting.
    """
    config = deepcopy(config)
    contract.require(contract.identifier(config.get('version')), 'study version required')
    data = config['data']
    contract.fields(data, ('entity_counts', 'split_seeds', 'draws_per_cell', 'max_blueprint_attempts'))
    entities = data['entity_counts']
    contract.require(type(entities) is list and entities and entities == sorted(set(entities)) and
                     all(type(n) is int and 3 <= n <= 6 for n in entities), 'invalid entity inventory')
    for name in ('split_seeds', 'draws_per_cell'): contract.fields(data[name], SPLITS)
    seeds = list(data['split_seeds'].values())
    contract.require(all(type(s) is int and s >= 20261030011 for s in seeds) and
                     len(set(seeds)) == len(seeds), 'fresh disjoint split seeds required')
    contract.require(all(type(n) is int and 1 <= n <= (8 if split == 'train' else 4)
        for split, n in data['draws_per_cell'].items()), 'invalid draw inventory')
    attempts = data['max_blueprint_attempts']
    contract.require(type(attempts) is int and 1 <= attempts <= 10000, 'invalid attempt budget')
    contract.digest(config)
    bundle = {'config': config, 'source_sha256': {}, 'splits': {}, 'audit': {}}
    used, rejected = set(), Counter()
    for split in SPLITS:
        inputs = {'version': 'active-acceptance-input-v1', 'episodes': []}
        gold, metadata, inventory = [], [], Counter()
        for family, n, count in _cells(split, entities):
            for draw in range(data['draws_per_cell'][split]):
                root = [config['version'], split, data['split_seeds'][split], family, n, count, draw]
                for attempt in range(attempts):
                    candidate = _candidate([*root, attempt], family, n, count, split)
                    if candidate is None:
                        rejected['uninformative_proposal'] += 1
                        continue
                    blueprint = blueprint_digest(candidate)
                    if blueprint not in used: break
                    rejected['duplicate_proposal'] += 1
                else: raise ValueError(f'blueprint budget exhausted: {split}/{family}/{n}/{count}/{draw}')
                used.add(blueprint)
                # All rejection, observations masks, actions and query indices precede this draw.
                mode = _rng('continuation-hidden-mode-v1', root).randrange(2)
                lineage = contract.digest(['continuation-lineage-v1', *root, blueprint])
                paired = family != 'self_contact'
                contacts = [t for t, a in enumerate(candidate['actions']) if a['kind'] == 'contact']
                query_steps = contacts[1:] if paired else contacts
                for direction in ((0, 1) if paired else (None,)):
                    case = deepcopy(candidate)
                    case['episode'] = contract.digest(['continuation-episode-v1', *root, direction])[:32]
                    if direction == 1:
                        for action in case['actions']:
                            if action['kind'] == 'contact': action['participants'].reverse()
                    truth = _realize(case, mode)
                    forecasts = oracle.forecast_episode(case)
                    contract.require(all(len(forecasts[t]['possible_worlds']) == 1 for t in query_steps),
                                     'declared query is not identifiable')
                    contract.require(len(forecasts[contacts[0]]['possible_worlds']) == (2 if paired else 1),
                                     'acquisition/self-contact support differs from design')
                    inputs['episodes'].append(case)
                    gold.append({'episode': case['episode'], 'truth': truth,
                        'possible_worlds': [row['possible_worlds'] for row in forecasts],
                        'information_keys': [row['information_key'] for row in forecasts]})
                    metadata.append({'episode': case['episode'], 'family': family,
                        'partition': 'in_family' if family in DEVELOPMENT else 'held_out',
                        'lineage': lineage, 'pair_id': lineage if paired else None, 'direction': direction,
                        'blueprint_sha256': blueprint, 'template_sha256': template_digest(case),
                        'hidden_source_slot': mode, 'entities': n, 'contact_count': count,
                        'acquisition_step': contacts[0] if paired else None, 'query_steps': query_steps.copy(),
                        'query_scope': 'self_contact' if not paired else 'continuation' if query_steps else 'acquisition_only'})
                inventory[f'{family}/N{n}/K{count}'] += 1
        contract.validate_inputs(inputs)
        bundle['splits'][split] = {'inputs': inputs, 'oracle': {
            'version': 'active-acceptance-oracle-v1', 'input_sha256': contract.digest(inputs),
            'source_sha256': oracle.source_digest(), 'information_law_sha256': oracle.law_digest(),
            'episodes': gold}, 'cases': metadata}
        missing = [sum(v is None for row in c['observations'][1:] for v in row.values()) for c in inputs['episodes']]
        bundle['audit'][split] = {'physical_draws': sum(inventory.values()), 'episode_views': len(metadata),
            'planned_actions': sum(len(c['actions']) for c in inputs['episodes']),
            'contact_predictions': sum(r['contact_count'] for r in metadata), 'physical_draws_by_cell': dict(inventory),
            'continuation_queries': sum(len(r['query_steps']) for r in metadata if r['query_scope'] == 'continuation'),
            'self_contact_queries': sum(len(r['query_steps']) for r in metadata if r['query_scope'] == 'self_contact'),
            'max_cumulative_missing_bits': max(missing), 'max_dense_histories': max(2 ** m for m in missing),
            'max_dense_expansions': max(2 ** (m + len(c['ids'])) for m, c in zip(missing, inputs['episodes']))}
    bundle['audit'].update(proposal_rejections=dict(rejected), cross_split_blueprint_overlap=0,
        scope='PUBLIC_SAME_AUTHOR_ENGINEERING_ASSETS', gate_g1='NOT_ADMITTED',
        interpretation='Conditional query identifiability, not measured learner performance or independent custody.')
    names = ('continuation_data.py', 'prospective_data.py', 'prospective_oracle.py', 'world.py',
             'protocol.py', 'protocol.json', 'acceptance_contract.py')
    bundle['source_sha256'] = {name: sha256((Path(__file__).parent / name).read_bytes()).hexdigest() for name in names}
    return bundle
