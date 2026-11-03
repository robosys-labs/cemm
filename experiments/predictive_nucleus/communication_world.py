"""G4 physical decisions over opened, immutable G3 v3 forecast records.

Each observation hypothesis is a genuine physical prefix. Both hypotheses share
the initial anchor, roster, commanded calibration action and offered surface
menu. A private sensor saw slot zero immediately after calibration. Its reading
indexes the two possible prefixes; neither the hidden mode nor later readings
are receiver observations. Messages never enter physical replay.

Reuse the grounded lexical decoder and native model *through their published
canonical predictions*, without refitting or re-running them. Expected reward
uses G3's probability of the full supplied goal world. Realized reward comes
from the archived physical endpoint and is private to the environment/scorer.
"""
from collections import defaultdict
from itertools import combinations, product
import math

from . import acceptance_contract as c, continuation_run as io
from .acceptance_scoring import _index

DATA = io.ROOT / 'data/effect-role-v3'
FIT = io.ROOT / 'data/effect-role-fit-v3'
NATIVE = io.ROOT / 'data/set-acquisition-fit-v2'
TRACES = io.ROOT / 'results/effect-role-v3/traces'
# Three roots of the opened G3 archive at a0ec72982c9f2b1808564c88da46b1e2aa316fb6.
FREEZE = '5380210e7957c8b170c8e8ee39d8b4be130e32eb81dad52e9cff7d9f392b5922'
MANIFEST = '71f92c8fa36e8fc346d7e24d1a14a1abb1e74ed820c96dbfe688f158e52761b0'
TRAINING = '766a8315d66e4a0bfca0079183d3966fbc7a0b4ed65c98177650d245a10671ed'


def _bound(path, digest):
    c.require(io._hash(path) == digest, 'G3 archive hash differs: ' + path.name)
    return io._read(path)


def _target(before, participants, goal):
    target = list(before)
    for slot, bit in zip(participants, goal, strict=True):
        target[slot] = bit
    return target


def _cases(law, inputs, evaluator, trace, family_filter=None):
    records = {r['id']: r for r in inputs['episodes']}
    metadata = {r['id']: r for r in evaluator['oracle']['episodes']}
    finals = {p['id']: p['logp'] for p in trace['points'] if p['view'] == 'canonical'
              and p['step'] == len(records[p['id']]['utterances']) - 1}
    c.require(finals.keys() == records.keys() == metadata.keys(), 'G3 episode inventory differs')
    by_context = defaultdict(dict)
    for group in evaluator['goal_groups']:
        record = records[group['episodes'][0]]
        meta = metadata[record['id']]
        if meta['context_mode'] != 'established' or (family_filter is not None and meta['family'] != family_filter):
            continue  # The unresolved condition did not perform the witnessed calibration.
        reading = record['context'][0]['reading'][0]
        pair = by_context[meta['family'], meta['lineage'], meta['layout'], meta['direction']]
        c.require(reading in (0, 1) and reading not in pair, 'ambiguous physical witness')
        pair[reading] = group

    result = []
    for (family, lineage, layout, direction), pair in sorted(by_context.items()):
        c.require(set(pair) == {0, 1}, 'missing witnessed alternative')
        groups = [pair[i] for i in (0, 1)]
        alternatives = [[records[i] for i in g['episodes']] for g in groups]
        first, other = (e[0] for e in alternatives)
        entities, anchor, participants = first['entities'], first['anchor'], groups[0]['participants']
        texts = [[r['utterances'][-1]['text'] for r in rows] for rows in alternatives]
        actions = [[metadata[r['id']]['actions'][-1] for r in rows] for rows in alternatives]
        c.require(texts[0] == texts[1] and actions[0] == actions[1] and len(set(texts[0])) == 4
                  and entities == other['entities'] and anchor == other['anchor']
                  and participants == groups[1]['participants']
                  and first['context'][0]['action'] == other['context'][0]['action'], 'public context differs')
        witnesses = []
        for bit, r in enumerate((first, other)):
            evidence = dict(time=1, entity=entities[0], reading=bit, action=r['context'][0]['action'])
            witnesses.append(dict(evidence, id=c.digest(['g4-calibration', law, entities, anchor, evidence])))
        for goal in product((0, 1), repeat=2):
            targets = [_target(g['before'], participants, goal) for g in groups]
            for menu in combinations(range(4), 2):
                outcomes = [[int(rows[a]['utterances'][-1]['reading'] == target) for a in menu]
                            for rows, target in zip(alternatives, targets, strict=True)]
                # Eligibility uses only task mechanics. Never screen on a learned forecast.
                if outcomes not in ([[1, 0], [0, 1]], [[0, 1], [1, 0]]):
                    continue
                episode_ids = [[rows[a]['id'] for a in menu] for rows in alternatives]
                predicted = [[math.exp(finals[key][_index(target)]) for key in keys]
                             for keys, target in zip(episode_ids, targets, strict=True)]
                result.append(dict(id=c.digest([law, lineage, layout, direction, menu, goal]),
                    family=family, lineage=lineage, entities=entities, anchor=anchor, participants=participants,
                    goal=list(goal), texts=[texts[0][a] for a in menu], actions=[actions[0][a] for a in menu],
                    episodes=episode_ids, witness=witnesses, predicted=predicted, rewards=outcomes))
    return tuple(result)


def load_cases(law, seed, family=None):
    """Return crossed two-action tasks for both physical hypotheses, ordered by witness bit.

    episodes[h][a] identifies the exact G3 trace row (final step, canonical view).
    predicted[h][a] is its exact-target probability; rewards[h][a] is the
    environment-only realized binary payoff. witness[h] is the native sensor
    receipt, not the communication envelope. Split by family to hold out structure.
    """
    c.require(law in ('nand', 'nor') and type(seed) is int and seed in io.SEEDS, 'unknown G3 condition')
    c.require(family in (None, 'path_return4', 'branch_return5'), 'unknown physical family')
    freeze = _bound(DATA / 'freeze.json', FREEZE)
    manifest = _bound(TRACES / 'manifest.json', MANIFEST)
    training = _bound(FIT / 'training.json', TRAINING)
    language = training['checkpoints'][f'grounded/{seed}']
    world = freeze['world_checkpoints'][f'{law}/{seed}']
    checkpoint = _bound(FIT / language['file'], language['sha256'])
    c.require(io._hash(NATIVE / world['file']) == world['sha256'], 'G3 native checkpoint differs')
    inputs, evaluator = [_bound(DATA / name, freeze['artifacts'][name]['sha256'])
                         for name in (f'{law}-inputs.json.xz', f'{law}-evaluator.json.xz')]
    name = f'trace-{law}-{seed}-grounded-fresh.json.xz'
    trace = _bound(TRACES / name, manifest['artifacts'][name]['sha256'])
    c.require(trace['arm'] == 'grounded' and trace['bank'] == 'fresh' and trace['law'] == law
              and trace['seed'] == seed and trace['state_sha256'] == checkpoint['state_sha256']
              and trace['freeze_sha256'] == FREEZE and trace['training_sha256'] == TRAINING,
              'G3 trace provenance differs')
    return _cases(law, inputs, evaluator, trace, family)
