"""Evaluator-side fresh instances with independently assigned primitive meanings."""
import argparse
from collections import Counter
from copy import deepcopy
from itertools import permutations, product
import json
from pathlib import Path
import random
import subprocess

from . import acceptance_contract as c, continuation_run as io
from . import bilingual_data as simulator, effect_role_data as physical
from .bilingual_contract import validate_inputs

VERSION = 'coordinate-transport-v1'
SEED = 20261106101
LAWS, WORDS, LAYOUTS = ('nand', 'nor'), ('lights', 'zef'), ('svo', 'osv', 'vos')
# Patterns address canonical handles A/B/C before their public roster rotation.
PATTERNS = (((0, 0, 1), (1, 1, 1), (0, 1, 0)),
            ((1, 1, 1), (0, 0, 1), (1, 0, 1)))
MEANINGS = ((0, 0, 1, -1), (0, 1, 0, -1), (1, 0, -1, 1), (1, 1, -1, 1))
PROTOCOL = io.ROOT / 'COORDINATE_TRANSPORT_PROTOCOL_V1.md'
PROTOCOL_COMMIT = '97ff1f00ed8f3f3ca330ea14f566bdc87a4d9028'
PROTOCOL_SHA256 = '4ca02dfd87075d6d34bcf322cb9f542a418cc20b87f788fedb74e958368040e4'
TRAINING = io.ROOT / 'data/effect-role-fit-v3/training.json'
TRAINING_SHA256 = '766a8315d66e4a0bfca0079183d3966fbc7a0b4ed65c98177650d245a10671ed'
HISTORY = io.ROOT / 'data/effect-role-v3'
SOURCE_FILES = ('coordinate_transport_data_v1.py', 'acceptance_contract.py', 'continuation_run.py',
                'bilingual_contract.py', 'bilingual_data.py', 'effect_role_data.py',
                'set_acquisition_data.py', 'multisource_law_oracle.py')


def _endpoint(bits):
    return sum(bit << (len(bits) - index - 1) for index, bit in enumerate(bits))


def _checked_step(before, action, mode, law):
    after = simulator._step(before, action, mode, law)
    support, probabilities = physical._distribution(before, action, (mode,), law)
    c.require(support == [_endpoint(after)] and probabilities == [1.],
              'Boolean simulator and table oracle disagree')
    return after


def _public_ticket(number, law, word, layouts, pattern, modes):
    """Create public identities, surfaces and prefixes before meaning assignment."""
    c.require(type(number) is int and number >= 0 and law in LAWS and word in WORDS,
              'invalid public trial recipe')
    c.require(tuple(sorted(layouts)) == tuple(sorted(LAYOUTS)) and
              type(pattern) is int and pattern in (0, 1) and len(modes) == 3 and
              all(type(mode) is int and mode in (0, 1) for mode in modes), 'invalid instance recipe')
    trial_id = c.digest([VERSION, SEED, 'trial', number])[:32]
    prefixes, participants = [], []
    for stage, (layout, bits, mode) in enumerate(zip(layouts, PATTERNS[pattern], modes, strict=True)):
        handles = ['Q' + c.digest([VERSION, SEED, 'entity', number, stage, slot])[:16] for slot in range(3)]
        shift = int(c.digest([VERSION, SEED, 'roster', number, stage])[:8], 16) % 3
        roster = handles[shift:] + handles[:shift]
        a, b = roster.index(handles[0]), roster.index(handles[1])
        initial = [bits[handles.index(name)] for name in roster]
        state, context = [0, 0, 0], []
        actions = [[0, 0, 1, -1]] + [[1, slot, -1, bit] for slot, bit in enumerate(initial)]
        possible = [0, 1]
        for action in actions:
            after = _checked_step(state, action, mode, law)
            possible = [candidate for candidate in possible if _endpoint(after) in
                        physical._distribution(state, action, (candidate,), law)[0]]
            context.append({'action': action, 'reading': after.copy()})
            state = after
        c.require(state == initial and possible == [mode], 'physical context failed to establish mode or bits')
        public_forms = {'svo': (handles[0], word, handles[1]),
                        'osv': (handles[1], handles[0], word),
                        'vos': (word, handles[1], handles[0])}
        prefixes.append({'id': c.digest([VERSION, SEED, 'instance', number, stage])[:32],
                         'entities': roster, 'anchor': [0, 0, 0], 'context': context,
                         'text': ' '.join(public_forms[layout])})
        participants.append((a, b))
    return {'id': trial_id, 'law': law, 'word': word, 'prefixes': prefixes,
            'participants': participants,
            'metadata': {'layouts': list(layouts), 'pattern': pattern, 'modes': list(modes)}}


def _realize(ticket, meaning):
    """Apply an independently selected primitive action to each public instance."""
    c.require(type(meaning) is int and meaning in range(4), 'invalid primitive meaning')
    records, outcomes, endpoints, actions, indices = [], [], [], [], []
    for prefix, participants, mode in zip(ticket['prefixes'], ticket['participants'],
                                           ticket['metadata']['modes'], strict=True):
        primitive_actions = physical._menu(participants)
        before = prefix['context'][-1]['reading']
        alternatives = []
        for action in primitive_actions:
            support, probabilities = physical._distribution(before, action, (mode,), ticket['law'])
            c.require(len(support) == 1 and probabilities == [1.], 'established-mode oracle is ambiguous')
            alternatives.append(support[0])
        action = primitive_actions[meaning]
        after = _checked_step(before, action, mode, ticket['law'])
        c.require(_endpoint(after) == alternatives[meaning], 'selected outcome differs from counterfactual table')
        mentions = [prefix['entities'].index(token) for token in prefix['text'].split()
                    if token in prefix['entities']]
        record = deepcopy(prefix)
        text = record.pop('text')
        record['utterances'] = [{'text': text, 'reading': after}]
        records.append(record)
        outcomes.append(alternatives)
        endpoints.append(_endpoint(after))
        actions.append(action)
        indices.append(physical._menu(mentions).index(action))
    validate_inputs({'version': 'bilingual-input-v1', 'episodes': records})
    public = {'id': ticket['id'], 'law': ticket['law'], 'demonstrations': records[:2],
              'query': deepcopy(ticket['prefixes'][2])}
    instance_ids = [record['id'] for record in records]
    oracle = {'id': ticket['id'], 'law': ticket['law'], 'word': ticket['word'], 'meaning': meaning,
              'canonical_action': list(MEANINGS[meaning]), 'physical_actions': actions,
              'action_indices': indices, 'endpoints': endpoints, 'outcomes_by_meaning': outcomes,
              'instance_ids': instance_ids, 'evidence_ids': [identity + '/utterance/0' for identity in instance_ids],
              'metadata': deepcopy(ticket['metadata'])}
    return public, oracle


def _historical():
    c.require(io._hash(TRAINING) == TRAINING_SHA256, 'published training receipt differs')
    training = io._read(TRAINING)
    c.require(io._hash(HISTORY / 'freeze.json') == training['freeze_sha256'], 'published data freeze differs')
    frozen = io._read(HISTORY / 'freeze.json')
    names, episodes = {}, {}
    hashes = {TRAINING.relative_to(io.ROOT).as_posix(): TRAINING_SHA256,
              (HISTORY / 'freeze.json').relative_to(io.ROOT).as_posix(): training['freeze_sha256']}
    for name in ('teach-inputs.json.xz', 'rehearsal-inputs.json.xz'):
        path = HISTORY / name
        c.require(io._hash(path) == frozen['artifacts'][name]['sha256'], 'historical input bytes differ')
        bank = validate_inputs(io._read(path))
        key = path.relative_to(io.ROOT).as_posix()
        names[key] = {name for record in bank['episodes'] for name in record['entities']}
        episodes[key] = {record['id'] for record in bank['episodes']}
        hashes[key] = frozen['artifacts'][name]['sha256']
    return names, episodes, hashes


def build_assets():
    public, oracle = [], []
    rng = random.Random(SEED)
    designs = product(LAWS, WORDS, permutations(LAYOUTS), range(2), product((0, 1), repeat=3))
    for base, (law, word, layouts, pattern, modes) in enumerate(designs):
        tickets = [_public_ticket(4 * base + offset, law, word, layouts, pattern, modes) for offset in range(4)]
        meanings = list(range(4))
        rng.shuffle(meanings)
        for ticket, meaning in zip(tickets, meanings, strict=True):
            observed, gold = _realize(ticket, meaning)
            public.append(observed)
            oracle.append(gold)
    trial_ids = [trial['id'] for trial in public]
    instances = [instance for trial in public for instance in (*trial['demonstrations'], trial['query'])]
    instance_ids = [instance['id'] for instance in instances]
    entities = [name for instance in instances for name in instance['entities']]
    cells = Counter((row['law'], row['word'], row['meaning'], tuple(row['metadata']['layouts']),
                     row['metadata']['pattern'], tuple(row['metadata']['modes'])) for row in oracle)
    c.require(len(trial_ids) == len(set(trial_ids)) == len(cells) == 1536 and set(cells.values()) == {1},
              'incomplete or repeated registered trial inventory')
    c.require(len(instance_ids) == len(set(instance_ids)) == 4608 and
              len(entities) == len(set(entities)) == 13824, 'repeated or missing fresh instance identities')
    old_names, old_episodes, hashes = _historical()
    entity_overlap = {name: len(set(entities) & previous) for name, previous in old_names.items()}
    episode_overlap = {name: len(set(instance_ids) & previous) for name, previous in old_episodes.items()}
    c.require(not any(entity_overlap.values()) and not any(episode_overlap.values()), 'historical identity overlap')
    inputs = {'version': VERSION, 'trials': public}
    evaluator = {'version': VERSION, 'trials': oracle}
    audit = {'version': VERSION, 'seed': SEED, 'trials': len(public), 'instances': len(instances),
             'unique_entities': len(entities), 'trial_ids_sha256': c.digest(sorted(trial_ids)),
             'instance_ids_sha256': c.digest(sorted(instance_ids)),
             'trials_by_law': dict(Counter(row['law'] for row in oracle)),
             'trials_by_word': dict(Counter(row['word'] for row in oracle)),
             'trials_by_meaning': dict(Counter(str(row['meaning']) for row in oracle)),
             'trials_by_pattern': dict(Counter(str(row['metadata']['pattern']) for row in oracle)),
             'historical_entity_overlap': entity_overlap, 'historical_episode_overlap': episode_overlap,
             'historical_sha256': hashes, 'all_instance_modes_identified_by_public_context': True,
             'initial_bit_order': 'Patterns address canonical handles A/B/C before public roster rotation.',
             'identity_assignment': 'Public tickets and instances precede balanced shuffled meaning assignment.',
             'scope': 'Fresh participant identities and instances with already exposed words, layouts, laws and action menu.'}
    return {'inputs': inputs, 'evaluator': evaluator, 'audit': audit}


def _source_state():
    c.require(io._hash(PROTOCOL) == PROTOCOL_SHA256, 'prospective transport protocol differs')
    head = io._git('rev-parse', 'HEAD')
    io._git('merge-base', '--is-ancestor', PROTOCOL_COMMIT, head)
    sources = {}
    for name in SOURCE_FILES:
        path = io.ROOT / name
        committed = subprocess.check_output(['git', '-C', str(io.REPO), 'show',
                                             head + ':' + path.relative_to(io.REPO).as_posix()])
        c.require(committed == path.read_bytes(), 'unpublished data-generation source ' + name)
        sources[name] = io._hash(path)
    return head, sources


def prepare(output):
    head, sources = _source_state()
    output = Path(output)
    c.require(not output.exists(), 'data output already exists')
    assets = build_assets()
    c.require(sources == {name: io._hash(io.ROOT / name) for name in SOURCE_FILES} and
              io._hash(PROTOCOL) == PROTOCOL_SHA256, 'data-generation source changed during preparation')
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {}
    for key, filename in (('inputs', 'inputs.json.xz'), ('evaluator', 'evaluator.json.xz'), ('audit', 'audit.json')):
        artifacts[filename] = io._write(output / filename, assets[key])
    frozen = {'version': VERSION, 'seed': SEED, 'protocol_commit': PROTOCOL_COMMIT,
              'protocol_sha256': PROTOCOL_SHA256, 'source_commit': head, 'sources': sources,
              'artifacts': artifacts, 'input_content_sha256': c.digest(assets['inputs']),
              'evaluator_content_sha256': c.digest(assets['evaluator']),
              'trials': assets['audit']['trials'], 'instances': assets['audit']['instances'],
              'historical_sha256': assets['audit']['historical_sha256']}
    io._write(output / 'freeze.json', frozen)
    return frozen


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    print(json.dumps(prepare(parser.parse_args().output), sort_keys=True))
