"""Evaluator-only lexical contrasts over existing contact dynamics and envelopes.

The candidate never imports this lexicon. Native action direction changes while
both identity strings and their token positions stay fixed within each pair.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import lzma
from pathlib import Path

from . import acceptance_contract as contract, bilingual_data as previous
from .bilingual_contract import validate_inputs

PAIRS = (('contacts', 'receives'), ('touches', 'accepts'), ('dax', 'vok'), ('mip', 'nuz'))
SWAPS = {a: b for pair in PAIRS for a, b in (pair, pair[::-1])}
BORROWS = {a: b for pair in (('contacts', 'dax'), ('receives', 'vok'), ('touches', 'mip'), ('accepts', 'nuz'))
           for a, b in (pair, pair[::-1])}
REHEARSAL = Path(__file__).parent / 'data/bilingual-v1/train-inputs.json.xz'
REHEARSAL_SHA256 = '77942997c5b7c241a54c7528179cd3d2c4a03d1950a2330747d54fcb689caa8a'


def swap_lexeme(text, roster):
    """Evaluator intervention only: change one word without moving either name."""
    return _replace_word(text, roster, SWAPS)


def borrow_lexeme(text, roster):
    """Evaluator view only: same meaning, counterpart lexicon, unchanged layout."""
    return _replace_word(text, roster, BORROWS)


def _replace_word(text, roster, mapping):
    words = text.split()
    positions = [i for i, word in enumerate(words) if word not in roster]
    contract.require(len(words) == 3 and len(positions) == 1 and
                     words[positions[0]] in mapping, 'invalid lexical-control utterance')
    index = positions[0]; words[index] = mapping[words[index]]
    return ' '.join(words)


def shared_prefix(episode):
    words = episode['utterances'][-1]['text'].split()
    return {'entities': episode['entities'], 'anchor': episode['anchor'], 'context': episode['context'],
        'utterances': episode['utterances'][:-1],
        'contrast_tokens': [word if word in episode['entities'] else '<lexeme>' for word in words]}


def _contrast_bank(bank, split, law):
    episodes, cases = [], []
    for source, meta in zip(bank['inputs']['episodes'], bank['oracle']['episodes'], strict=True):
        if split == 'train' and meta['family'] != 'single': continue
        pair_id = contract.digest(['lexical-pair-v1', source['id']])
        phase = meta['initial_bits'][meta['canonical_slots'][0]]
        for polarity in (0, 1):
            episode, gold = deepcopy(source), deepcopy(meta)
            identity = lambda p: contract.digest(['lexical-episode-v1', source['id'], p])[:32]
            episode['id'] = gold['id'] = identity(polarity)
            for key in ('physical_id', 'role_pair_id', 'bilingual_pair_id', 'synonym_pair_id'):
                gold[key] = contract.digest(['lexical-' + key, meta[key], polarity])
            state = list(source['context'][-1]['reading'])
            actions, truth, opposite, orders, words, effects = [], [], [], [], [], []
            for t, (event, action) in enumerate(zip(source['utterances'], meta['actions'], strict=True)):
                effect = polarity if t == len(source['utterances']) - 1 else (phase + t) % 2
                native = [0, action[2], action[1], -1] if effect else list(action)
                text = swap_lexeme(event['text'], source['entities']) if effect else event['text']
                reverse = [0, native[2], native[1], -1]
                opposite.append(previous._step(state, reverse, meta['mode'], law))
                state = previous._step(state, native, meta['mode'], law)
                episode['utterances'][t] = {'text': text, 'reading': state.copy()}
                actions.append(native); truth.append(state.copy()); orders.append(meta['action_orders'][t] ^ effect)
                words.append(next(word for word in text.split() if word not in source['entities'])); effects.append(effect)
            gold.update(actions=actions, truth=truth, opposite_truth=opposite, action_orders=orders,
                lexemes=words, effect_sequence=effects, lexical_pair_id=pair_id,
                counterpart_id=identity(1 - polarity), contrast_step=len(actions) - 1,
                contrast_synonym=meta['synonym'] if split == 'train' else (meta['synonym'] + len(actions) - 1) % 2,
                effect_polarity=polarity, partition='fresh_training' if split == 'train' else 'lexical_challenge',
                shared_prefix_sha256=contract.digest(shared_prefix(episode)))
            episodes.append(episode); cases.append(gold)
        contract.require(cases[-1]['shared_prefix_sha256'] == cases[-2]['shared_prefix_sha256'] and
                         cases[-1]['truth'][-1] != cases[-2]['truth'][-1], 'invalid identical-prefix lexical contrast')
    inputs = validate_inputs({'version': 'bilingual-input-v1', 'episodes': episodes})
    return {'inputs': inputs, 'oracle': {'version': 'bilingual-oracle-v1',
            'input_sha256': contract.digest(inputs), 'episodes': cases}}


def _inventory(bank):
    records, cases = bank['inputs']['episodes'], bank['oracle']['episodes']
    return {'episodes': len(records), 'forecasts': sum(len(r['utterances']) for r in records),
        'lexical_pairs': len({c['lexical_pair_id'] for c in cases}),
        'critical_final_forecasts': len(records), 'lineages': len({c['lineage'] for c in cases}),
        'role_pairs': len({c['role_pair_id'] for c in cases}),
        'bilingual_pairs': len({c['bilingual_pair_id'] for c in cases}),
        'synonym_pairs': len({c['synonym_pair_id'] for c in cases}),
        'families': dict(Counter(c['family'] for c in cases)),
        'contrast_synonyms': dict(Counter(c['contrast_synonym'] for c in cases)),
        'lexical_polarities': dict(Counter(c['effect_polarity'] for c in cases))}


def _exposures(inputs):
    words = Counter(word for e in inputs['episodes'] for event in e['utterances']
                    for word in event['text'].split() if word not in e['entities'])
    contract.require(set(words) <= set(SWAPS), 'unclassified training lexeme')
    return {'direct': sum(words[a] for a, _ in PAIRS), 'inverse': sum(words[b] for _, b in PAIRS)}


def _add_borrowed_training(bank):
    inputs, gold = bank['inputs']['episodes'], bank['oracle']['episodes']
    for source, meta in list(zip(inputs, gold, strict=True)):
        if meta['synonym'] != 0: continue
        episode, case = deepcopy(source), deepcopy(meta)
        identity = lambda value: contract.digest(['lexical-borrow-train-v1', value])[:32]
        episode['id'] = case['id'] = identity(meta['id'])
        case['counterpart_id'] = identity(meta['counterpart_id'])
        for key in ('physical_id', 'role_pair_id', 'bilingual_pair_id', 'synonym_pair_id', 'lexical_pair_id'):
            case[key] = contract.digest(['lexical-borrow-train-v1', meta[key]])
        episode['utterances'][0]['text'] = borrow_lexeme(source['utterances'][0]['text'], source['entities'])
        case['lexemes'] = [BORROWS[meta['lexemes'][0]]]
        case['shared_prefix_sha256'] = contract.digest(shared_prefix(episode))
        inputs.append(episode); gold.append(case)
    bank['inputs'] = validate_inputs(bank['inputs'])
    bank['oracle']['input_sha256'] = contract.digest(bank['inputs'])
    return bank


def build_assets(config):
    base = previous.build_assets(config)
    fresh = _add_borrowed_training(_contrast_bank(base['train'], 'train', 'nand'))
    raw = REHEARSAL.read_bytes()
    contract.require(sha256(raw).hexdigest() == REHEARSAL_SHA256, 'frozen rehearsal observations changed')
    rehearsal = validate_inputs(json.loads(lzma.decompress(raw)))
    combined = validate_inputs({'version': 'bilingual-input-v1',
        'episodes': rehearsal['episodes'] + fresh['inputs']['episodes']})
    challenge = {law: _contrast_bank(bank, 'challenge', law) for law, bank in base['challenge'].items()}
    audit = {'rehearsal_sha256': REHEARSAL_SHA256,
        'training_order': 'Exact original rehearsal records first, fresh lexical records second.',
        'rehearsal': {'episodes': len(rehearsal['episodes']),
            'forecasts': sum(len(r['utterances']) for r in rehearsal['episodes'])},
        'fresh_training': _inventory(fresh),
        'train': {'episodes': len(combined['episodes']),
            'forecasts': sum(len(r['utterances']) for r in combined['episodes']),
            'gold_or_parser_labels_returned': False},
        'training_law': 'nand', 'transfer_law': 'nor',
        'training_semantic_exposures': {'rehearsal': _exposures(rehearsal),
            'fresh': _exposures(fresh['inputs']), 'total': _exposures(combined),
            'weighting': 'Intentional direct-form retention: equal fresh/rehearsal outcome counts, not equal total semantic effects.'},
        'layout_diagnostic': {'borrowed_training_episodes': len(fresh['inputs']['episodes']) // 3, 'trained_cross_layout_synonym': 0,
            'held_out_cross_layout_synonym': 1, 'challenge_storage': 'No extra episodes; final-lexeme-only collector view.'},
        'dependency': 'Lexical branches, role directions, languages, synonyms, modes and laws are matched dependent views.',
        **{law: _inventory(bank) for law, bank in challenge.items()}}
    training_names = {name for e in combined['episodes'] for name in e['entities']}
    held_names = {name for e in challenge['nand']['inputs']['episodes'] for name in e['entities']}
    audit['split_overlap'] = {'entity_names': len(training_names & held_names),
        'fresh_lineages': len({c['lineage'] for c in fresh['oracle']['episodes']} &
                             {c['lineage'] for c in challenge['nand']['oracle']['episodes']}),
        'whole_families': len(set(previous.FAMILIES['train']) & set(previous.FAMILIES['challenge']))}
    contract.require(not any(audit['split_overlap'].values()), 'lexical split leakage')
    return {'train': {'inputs': combined}, 'challenge': challenge, 'audit': audit}
