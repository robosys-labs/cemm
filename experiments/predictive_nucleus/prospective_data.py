"""Public same-author prospective assets; evaluator physics, never learner features.

Blueprint rejection precedes the hidden-mode draw. There is at most one leading
set and one trailing observe (independent probability 1/2 each), never a set
between contacts. Two-contact templates choose overlap or repetition equally.
Missing bit-events are sampled independently of truth, with a cumulative cap of
three. Public deterministic seeds provide reproducibility, not blind custody.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import argparse
import json
import lzma
import random

from . import acceptance_contract as contract
from . import prospective_oracle as oracle
from .world import Action, FAMILIES, World, step

ROOT = Path(__file__).resolve().parent
PROTOCOL = ROOT / 'prospective_data_protocol_v1.json'
LOCK = ROOT / 'snapshots' / 'prospective_data_protocol_v1.sha256'
SPLITS = ('train', 'selection', 'calibration', 'evaluation')


def read_config():
    """Read only the separately locked prospective data contract."""
    return contract.load_json(PROTOCOL, LOCK.read_text(encoding='ascii').split()[0])


def validate_config(value=None):
    """Validate explicit engineering reductions without changing the frozen law/scope."""
    frozen = read_config()
    value = deepcopy(frozen if value is None else value)
    contract.fields(value, tuple(frozen))
    adjustable = {'entity_counts', 'split_seeds', 'draws_per_family_entity',
                  'max_blueprint_attempts', 'max_cumulative_missing_bits'}
    for key in frozen.keys() - adjustable:
        contract.require(contract.digest(value[key]) == contract.digest(frozen[key]),
                         f'unreviewed prospective contract field: {key}')
    counts = value['entity_counts']
    contract.require(type(counts) is list and counts and
        all(type(n) is int and 3 <= n <= 6 for n in counts) and counts == sorted(set(counts)),
        'invalid entity inventory')
    old = json.loads((ROOT / 'protocol.json').read_text(encoding='utf-8'))
    reserved = {seed for row in old['splits'].values() for seed in row['seeds']}
    contract.fields(value['split_seeds'], SPLITS)
    seeds = list(value['split_seeds'].values())
    contract.require(all(type(s) is int and s >= 0 and s not in reserved for s in seeds)
        and len(set(seeds)) == len(seeds), 'fresh disjoint split seeds required')
    contract.fields(value['draws_per_family_entity'], SPLITS)
    contract.require(all(type(n) is int and 1 <= n <= frozen['draws_per_family_entity'][split]
        for split, n in value['draws_per_family_entity'].items()), 'invalid blueprint draw counts')
    contract.require(type(value['max_blueprint_attempts']) is int and
        1 <= value['max_blueprint_attempts'] <= 10000, 'invalid blueprint attempt bound')
    contract.require(type(value['max_cumulative_missing_bits']) is int and
        0 <= value['max_cumulative_missing_bits'] <= 3, 'invalid cumulative missingness cap')
    contract.digest(value)
    return value


def _canonical(case, template=False):
    """Canonicalize all identity renamings and global contact reversal, without gold."""
    values = []
    for reverse in (False, True):
        actions = deepcopy(case['actions'])
        for action in actions:
            if reverse and action['kind'] == 'contact': action['participants'].reverse()
        order = list(dict.fromkeys(i for a in actions for i in a['participants']))
        def signature(i):
            return (() if template else (case['observations'][0][i],
                *[i in row for row in case['coverage']],
                *[row[i] is not None for row in case['observations'][1:]]))
        order += sorted((i for i in case['ids'] if i not in order), key=signature)
        index = {name: i for i, name in enumerate(order)}
        record = {'entities': len(order), 'actions': [[a['kind'],
            [index[i] for i in a['participants']], a.get('value')] for a in actions]}
        if not template:
            record.update(initial=[case['observations'][0][i] for i in order],
                coverage=[sorted(index[i] for i in row) for row in case['coverage']],
                masks=[[row[i] is not None for i in order] for row in case['observations'][1:]])
        values.append(contract.digest(record))
    return min(values)


def blueprint_digest(case):
    """Identity/reversal invariant anchor/action/coverage/mask hash; later bits excluded."""
    return _canonical(case)


def template_digest(case):
    """Action-template hash including N and set values, excluding bits and sensors."""
    return _canonical(case, template=True)


def _rng(label, material):
    return random.Random(int(contract.digest([label, *material]), 16))


def _candidate(config, material, family, entities):
    rng = _rng('blueprint-v1', material)
    ids = [contract.digest(['physical-id-v1', *material, i])[:20] for i in range(entities)]
    initial = dict(zip(ids, [rng.randrange(2) for _ in ids], strict=True))
    topology = FAMILIES[family]
    if family == 'two_contacts' and rng.randrange(2): topology = ((0, 1), (0, 1))
    actions = []
    if rng.random() < .5:
        actions.append({'kind': 'set', 'participants': [rng.choice(ids)], 'value': rng.randrange(2)})
    actions += [{'kind': 'contact', 'participants': [ids[a], ids[b]]} for a, b in topology]
    if rng.random() < .5: actions.append({'kind': 'observe', 'participants': []})
    contract.require(len(actions) <= config['max_actions'], 'prospective action budget exceeded')
    missing_count = rng.randrange(config['max_cumulative_missing_bits'] + 1)
    missing = set(rng.sample(range(len(actions) * entities), missing_count))
    rng.shuffle(ids)
    observations = [{i: initial[i] for i in ids}]
    observations += [{i: None if t * entities + j in missing else 0 for j, i in enumerate(ids)}
                     for t in range(len(actions))]
    return {'episode': 'blueprint', 'ids': ids, 'observations': observations,
            'actions': actions, 'coverage': [ids.copy() for _ in actions]}


def _realize(case, mode):
    """Evaluator-only truth simulation; replace only placeholder delivered bits."""
    world = World(tuple(case['ids']), tuple(case['observations'][0][i] for i in case['ids']), mode)
    truth = [dict(zip(world.ids, world.bits, strict=True))]
    for t, action in enumerate(case['actions']):
        world = step(world, Action(action['kind'], tuple(action['participants']), action.get('value')))
        truth.append(dict(zip(world.ids, world.bits, strict=True)))
        case['observations'][t + 1] = {i: truth[-1][i] if v is not None else None
                                      for i, v in case['observations'][t + 1].items()}
    return truth


def source_digests():
    names = ('prospective_data.py', 'prospective_oracle.py', 'world.py', 'protocol.py', 'protocol.json',
             'acceptance_contract.py', 'prospective_audit.py', 'observed_io.py',
             PROTOCOL.name, 'snapshots/' + LOCK.name)
    return {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def build_assets(config=None):
    """Build fresh observed/gold artifacts, without fitting, model replay or gate scoring."""
    config = validate_config(config)
    bundle = {'config': config, 'source_sha256': {}, 'splits': {}}
    used = set()
    for split in SPLITS:
        inputs = {'version': 'active-acceptance-input-v1', 'episodes': []}
        gold, cases = [], []
        families = config['evaluation_families'] if split == 'evaluation' else config['development_families']
        for family in families:
            minimum = max(3, 1 + max(max(pair) for pair in FAMILIES[family]))
            for entities in config['entity_counts']:
                if entities < minimum: continue
                for draw in range(config['draws_per_family_entity'][split]):
                    root = [config['version'], split, config['split_seeds'][split], family, entities, draw]
                    for attempt in range(config['max_blueprint_attempts']):
                        material = [*root, attempt]
                        candidate = _candidate(config, material, family, entities)
                        fingerprint = blueprint_digest(candidate)
                        if fingerprint not in used: break
                    else:
                        raise ValueError(f'unique blueprint budget exhausted: {split}/{family}/{entities}/{draw}')
                    used.add(fingerprint)
                    # No actual mode, truth or oracle is consulted before this point.
                    mode = _rng('hidden-mode-v1', root).randrange(2)
                    lineage = contract.digest(['lineage-v1', *root, fingerprint])
                    paired = family != 'self_contact'
                    for direction in ((0, 1) if paired else (None,)):
                        case = deepcopy(candidate)
                        case['episode'] = contract.digest(['episode-v1', *root, direction])[:32]
                        if direction == 1:
                            for action in case['actions']:
                                if action['kind'] == 'contact': action['participants'].reverse()
                        truth = _realize(case, mode)
                        forecasts = oracle.forecast_episode(case)
                        inputs['episodes'].append(case)
                        gold.append({'episode': case['episode'], 'truth': truth,
                            'possible_worlds': [row['possible_worlds'] for row in forecasts],
                            'information_keys': [row['information_key'] for row in forecasts]})
                        cases.append({'episode': case['episode'], 'family': family,
                            'partition': 'in_family' if family in config['development_families'] else 'held_out',
                            'lineage': lineage, 'pair_id': lineage if paired else None, 'direction': direction,
                            'blueprint_sha256': fingerprint, 'hidden_source_slot': mode,
                            'template_sha256': template_digest(case)})
        contract.validate_inputs(inputs)
        bundle['splits'][split] = {'inputs': inputs, 'oracle': {
            'version': 'active-acceptance-oracle-v1', 'input_sha256': contract.digest(inputs),
            'source_sha256': oracle.source_digest(), 'information_law_sha256': oracle.law_digest(),
            'episodes': gold}, 'cases': cases}
    bundle['source_sha256'] = source_digests()
    return bundle


def write_assets(destination, config=None):
    """Build/audit first; refuse existing directories; write a completion manifest last.

    A write failure may leave a new incomplete directory without its manifest.
    Neither this exporter nor its public deterministic seeds provide gold custody.
    """
    from .prospective_audit import audit_assets
    destination = Path(destination)
    if destination.exists(): raise FileExistsError(destination)
    assets = build_assets(config)
    audit = audit_assets(assets)
    destination.mkdir()
    files = {}
    def write(name, value):
        path = destination / name
        files[name] = {'sha256': contract.write_json(path, value),
                       'content_sha256': contract.digest(value), 'bytes': path.stat().st_size}
    for split, records in assets['splits'].items():
        write(split + '.inputs.json', records['inputs'])
        write(split + '.oracle.json', records['oracle'])
    write('audit.json', audit)
    archive = {'bundle': assets, 'audit': audit}
    raw = json.dumps(archive, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    compressed = lzma.compress(raw, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64)
    with (destination / 'asset-bundle.json.xz').open('xb') as stream: stream.write(compressed)
    files['asset-bundle.json.xz'] = {'sha256': sha256(compressed).hexdigest(),
        'content_sha256': contract.digest(archive), 'bytes': len(compressed), 'encoding': 'xz-compressed-json'}
    manifest = {'version': 'prospective-data-assets-v1', 'config': assets['config'],
        'source_sha256': assets['source_sha256'], 'cases': {s: row['cases'] for s, row in assets['splits'].items()},
        'files': files, 'gate_g1': 'NOT_ADMITTED', 'acceptance_plan_created': False}
    manifest_sha = contract.write_json(destination / 'manifest.json', manifest)
    return {'directory': str(destination.resolve()), 'manifest_sha256': manifest_sha,
            'artifact_count': len(files) + 1, 'gate_g1': 'NOT_ADMITTED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='new destination directory')
    args = parser.parse_args()
    print(json.dumps(write_assets(args.output), sort_keys=True))


if __name__ == '__main__':
    main()
