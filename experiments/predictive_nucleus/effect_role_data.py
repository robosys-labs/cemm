"""Evaluator-only effect/role teaching and fresh compositions; no learner imports.

The grounded learner receives only the unchanged observed bilingual envelope.
Parser labels, physical actions, conditional targets and goals are separate.
Each four-message final group contains hypothetical alternatives from one shared
prefix, never four sequentially delivered outcomes. VOS is withheld for new words.
"""
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path

from . import acceptance_contract as c, continuation_run as io
from . import bilingual_data as simulator, set_acquisition_data as native
from . import binding_data, saturation_data, centering_data, coordinate_data
from .bilingual_contract import validate_inputs

ROOT = Path(__file__).resolve().parent
VERSION = 'effect-role-v1'
SEEDS = {'teach': 20261102401, 'challenge': 20261102402}
NEW_WORDS = ('lights', 'zef')
LAYOUTS = ('svo', 'osv', 'vos')
LAWS = ('nand', 'nor')
REHEARSAL = ROOT / 'data/saturation-v1/train-inputs.json.xz'
SCHEDULES = {'interleaved_return4': (4, ((0, 1), (1, 2), (0, 3), (3, 1))),
             'cycle_tail5': (5, ((0, 1), (1, 2), (2, 3), (3, 0), (1, 4)))}
CORES = ((0, 0, 1), (0, 1, 0), (1, 0, 1), (1, 1, 0))
CONTACT_WORDS = {word: polarity for pair in binding_data.PAIRS for polarity, word in enumerate(pair)}
CONTACT_WORDS.update({new: CONTACT_WORDS[old] for old, new in saturation_data.WORDS.items()})


def source_digest():
    names = ('effect_role_data.py', 'bilingual_data.py', 'set_acquisition_data.py',
             'multisource_law_oracle.py', 'binding_data.py', 'saturation_data.py',
             'centering_data.py', 'coordinate_data.py', 'bilingual_contract.py')
    return c.digest({name: io._hash(ROOT / name) for name in names})


def law_digest(law):
    return c.digest({'version': VERSION, 'native_law': native.law_digest(law),
        'menu': ['contact(first,second)', 'contact(second,first)', 'set(first,1)', 'set(second,1)'],
        'new_words': {word: 'set grammatical object to one' for word in NEW_WORDS},
        'scope': 'Known noiseless laws and full observed prefixes; physical mode remains persistent.'})


def prefix_key(record, step=None):
    payload = {k: record[k] for k in ('entities', 'anchor', 'context')}
    if step is None: payload['utterances'] = record['utterances'][:-1]
    else:
        payload.update(past=record['utterances'][:step], text=record['utterances'][step]['text'])
    return c.digest(payload)


def _menu(mentions):
    a, b = mentions
    return [[0, a, b, -1], [0, b, a, -1], [1, a, -1, 1], [1, b, -1, 1]]


def _render(roster, a, b, choice, layout, new_word):
    actor, target = (b, a) if choice in (1, 2) else (a, b)
    word = ('contacts', 'dax', 'contacts')[layout] if choice < 2 else new_word
    words = ((roster[actor], word, roster[target]), (roster[target], roster[actor], word),
             (word, roster[target], roster[actor]))[layout]
    action = [0, actor, target, -1] if choice < 2 else [1, target, -1, 1]
    mentions = [roster.index(w) for w in words if w in roster]
    return ' '.join(words), action, _menu(mentions).index(action), {
        'word': word, 'layout': LAYOUTS[layout], 'new_word': word in NEW_WORDS,
        'held_layout': word in NEW_WORDS and layout == 2}


def _distribution(before, action, modes, law):
    """Table oracle for menu equivalence, independent of Boolean simulation."""
    worlds = Counter()
    for mode in modes:
        state = before.copy()
        if action[0] == 1: state[action[1]] = action[3]
        else:
            source, target = action[1 + mode], action[2 - mode]
            state[target] = native.old.TABLES[law][state[source]][state[target]]
        world = sum(bit << (len(state) - i - 1) for i, bit in enumerate(state))
        worlds[world] += 1
    support = sorted(worlds)
    return support, [worlds[w] / len(modes) for w in support]


def _forecasts(record, actions, law):
    """Reuse the native table oracle; preserve bilingual roster bit ordering."""
    names = ['slot' + str(i) for i in range(len(record['entities']))]
    observed = [record['anchor'], *[x['reading'] for x in record['context']],
                *[x['reading'] for x in record['utterances']]]
    all_actions = [x['action'] for x in record['context']] + actions
    as_action = lambda a: {'kind': 'set', 'participants': [names[a[1]]], 'value': a[3]} if a[0] else {
        'kind': 'contact', 'participants': [names[a[1]], names[a[2]]]}
    case = {'episode': record['id'], 'ids': names, 'observations': [dict(zip(names, row, strict=True)) for row in observed],
            'coverage': [names.copy() for _ in all_actions], 'actions': [as_action(a) for a in all_actions]}
    native_rows = native.forecast_episode(case, law)[len(record['context']):]
    result = []
    for t, row in enumerate(native_rows):
        before = record['context'][-1]['reading'] if t == 0 else record['utterances'][t - 1]['reading']
        mentions = [record['entities'].index(w) for w in record['utterances'][t]['text'].split() if w in record['entities']]
        options = [_distribution(before, a, row['surviving_modes'], law) for a in _menu(mentions)]
        actual = (row['possible_worlds'], row['probabilities'])
        result.append({k: row[k] for k in ('possible_worlds', 'probabilities', 'surviving_modes')} | {
            'equivalent_action_indices': [i for i, alternative in enumerate(options) if alternative == actual],
            'information_key': prefix_key(record, t)})
    return result


def _episode(tag, n, core, mode, direction, law, edges, choices, layout, new_word, context_mode):
    handles = ['Q' + c.digest([VERSION, 'identity', tag, i])[:16] for i in range(n)]
    shift = int(c.digest(tag)[:8], 16) % n
    roster = handles[shift:] + handles[:shift]; slots = [roster.index(name) for name in handles]
    initial = [core[handles.index(name) % 3] for name in roster]
    state, context = [0] * n, []
    native_actions = ([[0, 0, 1, -1]] if context_mode == 'established' else []) + [
        [1, i, -1, bit] for i, bit in enumerate(initial)]
    for action in native_actions:
        state = simulator._step(state, action, mode, law)
        context.append({'action': action, 'reading': state.copy()})
    utterances, actions, indices, cells = [], [], [], []
    layouts = [layout] * len(edges) if type(layout) is int else list(layout)
    for edge, choice, event_layout in zip(edges, choices, layouts, strict=True):
        a, b = [slots[i] for i in (edge[::-1] if direction else edge)]
        text, action, index, cell = _render(roster, a, b, choice, event_layout, new_word)
        state = simulator._step(state, action, mode, law)
        utterances.append({'text': text, 'reading': state.copy()}); actions.append(action); indices.append(index); cells.append(cell)
    identity = c.digest([tag, mode, direction, layout, choices, new_word])[:32]
    record = {'id': identity, 'entities': roster, 'anchor': [0] * n, 'context': context, 'utterances': utterances}
    gold = {'id': identity, 'law': law, 'mode': mode, 'direction': direction, 'layout': LAYOUTS[layouts[-1]],
        'context_mode': context_mode, 'actions': actions, 'action_indices': indices,
        'truth': [x['reading'].copy() for x in utterances], 'forecasts': _forecasts(record, actions, law), 'cells': cells}
    return record, gold


def _parser_labels(inputs):
    labels = {}
    for record in inputs['episodes']:
        values = []
        for event in record['utterances']:
            words = event['text'].split(); position = next(i for i, word in enumerate(words) if word not in record['entities'])
            word = words[position]
            c.require(word in CONTACT_WORDS, 'unknown rehearsal-only parser lexeme')
            values.append(CONTACT_WORDS[word] ^ int(position != 1))
        labels[record['id']] = values
    return labels


def _goal_group(members, records):
    ordered = sorted(members, key=lambda g: g['final_choice'])
    c.require([g['final_choice'] for g in ordered] == [0, 1, 2, 3], 'incomplete final action menu')
    first = records[ordered[0]['id']]; group = ordered[0]['goal_group_id']
    c.require(all(records[g['id']]['entities'] == first['entities'] and prefix_key(records[g['id']]) ==
        prefix_key(first) for g in ordered), 'hypothetical alternatives lack a shared observed prefix')
    before = first['utterances'][-2]['reading']; a, b = ordered[0]['actions'][-1][1:3]
    goals = []
    for bits in product((0, 1), repeat=2):
        utilities = []
        for gold in ordered:
            f = gold['forecasts'][-1]; value = 0.
            for world, probability in zip(f['possible_worlds'], f['probabilities'], strict=True):
                after = [(world >> (len(before) - i - 1)) & 1 for i in range(len(before))]
                value += probability * (all(after[i] == target for i, target in zip((a, b), bits)) and
                    all(after[i] == before[i] for i in range(len(before)) if i not in (a, b)))
            utilities.append(value)
        best = max(utilities); contact, intervention = max(utilities[:2]), max(utilities[2:])
        goals.append({'id': c.digest([group, 'goal', bits]), 'target_bits': list(bits), 'oracle_utilities': utilities,
            'optimal_choices': [i for i, value in enumerate(utilities) if value == best], 'max_utility': best,
            'attainable': best > 0, 'effect_sensitive': contact != intervention,
            'set_required': intervention > contact, 'contact_required': contact > intervention})
    return {'id': group, 'episodes': [g['id'] for g in ordered], 'participants': [a, b], 'before': before.copy(),
            'shared_prefix_sha256': prefix_key(first), 'goals': goals}


def build_assets():
    shape_audit = coordinate_data.novelty(SCHEDULES)
    opened = {centering_data.ordered_shape(edges) for _, edges in coordinate_data.SCHEDULES.values()}
    c.require(not opened & {centering_data.ordered_shape(edges) for _, edges in SCHEDULES.values()},
              'coordinate challenge structure reused')
    shape_audit['compared_opened_families'] += ['coordinate-' + k for k in coordinate_data.SCHEDULES]
    c.require(io._hash(REHEARSAL) == io._read(ROOT / 'coordinate_freeze_v1.json')['train-inputs.json.xz'],
              'historical TRAIN rehearsal bytes differ')
    rehearsal = validate_inputs(io._read(REHEARSAL))
    legacy = {w for e in rehearsal['episodes'] for event in e['utterances'] for w in event['text'].split() if w not in e['entities']}
    c.require(not legacy & set(NEW_WORDS) and sum(len(e['utterances']) for e in rehearsal['episodes']) == 1152,
              'new lexical identity or rehearsal inventory differs')
    taught, teaching_gold = [], []
    for word, layout, bit, mode in product(NEW_WORDS, (0, 1), (0, 1), (0, 1)):
        tag = [VERSION, SEEDS['teach'], 'teach', word, layout, bit]
        record, gold = _episode(tag, 3, (bit, bit, 1), mode, 0, 'nand', ((0, 1),), [3], layout, word, 'established')
        taught.append(record); teaching_gold.append(gold)
    teach = validate_inputs({'version': 'bilingual-input-v1', 'episodes': taught})
    proof = {}
    for word, layout in product(NEW_WORDS, LAYOUTS[:2]):
        examples = [g for g in teaching_gold if g['cells'][0]['word'] == word and g['layout'] == layout]
        compatible = [g['forecasts'][0]['equivalent_action_indices'] for g in examples]
        shared = sorted(set.intersection(*map(set, compatible)))
        c.require(len(examples) == 4 and shared == [examples[0]['action_indices'][0]] and
            all(len(row) > 1 for row in compatible), 'teaching must identify action across individually ambiguous endpoints')
        proof[word + '/' + layout] = {'episodes': [g['id'] for g in examples], 'compatible_actions': compatible,
                                      'intersection': shared, 'action_index': shared[0]}
    laws = {}
    for law in LAWS:
        episodes, gold = [], []
        for family, (n, edges) in SCHEDULES.items():
            for core, mode, direction, layout, context_mode, phase, final in product(
                    CORES, (0, 1), (0, 1), range(3), ('established', 'unresolved'), (0, 1), range(4)):
                tag = [VERSION, SEEDS['challenge'], family, core, context_mode, phase]
                choices = [0 if (t + phase) % 2 == 0 else 3 for t in range(len(edges))]; choices[-1] = final
                word = ('lights', 'zef', NEW_WORDS[phase])[layout]
                layouts = [(layout + t - len(edges) + 1) % 3 for t in range(len(edges))]
                record, meta = _episode(tag, n, core, mode, direction, law, edges, choices, layouts, word, context_mode)
                group = c.digest([tag, mode, direction, layout, 'goal-group'])
                meta.update(family=family, lineage=c.digest(tag), phase=phase,
                    role_pair_id=c.digest([tag, mode, layout, final, 'role-pair']),
                    bilingual_pair_id=c.digest([tag, mode, direction, final, 'bilingual']) if layout < 2 else None,
                    translation_group_id=c.digest([tag, mode, direction, final, 'translation']),
                    effect_pair_id=c.digest([group, 'effect-pair', int(final in (1, 2))]),
                    goal_group_id=group, final_choice=final, shared_prefix_sha256=prefix_key(record))
                episodes.append(record); gold.append(meta)
        inputs = validate_inputs({'version': 'bilingual-input-v1', 'episodes': episodes})
        by_group = defaultdict(list)
        for meta in gold: by_group[meta['goal_group_id']].append(meta)
        records = {e['id']: e for e in episodes}
        laws[law] = {'inputs': inputs, 'oracle': {'version': 'effect-role-oracle-v1',
            'input_sha256': c.digest(inputs), 'source_sha256': source_digest(),
            'information_law_sha256': law_digest(law), 'episodes': gold},
            'goal_groups': [_goal_group(members, records) for _, members in sorted(by_group.items())]}
    names = lambda bank: {name for e in bank['episodes'] for name in e['entities']}
    c.require(not names(teach) & names(rehearsal) and not (names(teach) | names(rehearsal)) & names(laws['nand']['inputs']),
              'teaching/rehearsal/challenge identity overlap')
    parser_labels = {'version': 'effect-role-parser-labels-v1', 'teach_input_sha256': c.digest(teach),
        'rehearsal_input_sha256': c.digest(rehearsal), 'teach': {g['id']: g['action_indices'] for g in teaching_gold},
        'rehearsal': _parser_labels(rehearsal)}
    audit = {**shape_audit, 'version': VERSION, 'split_seeds': SEEDS, 'new_words': list(NEW_WORDS),
        'teach_episodes': len(taught), 'teach_forecasts': len(taught), 'rehearsal_forecasts': 1152,
        'rehearsal_file': REHEARSAL.relative_to(ROOT).as_posix(), 'rehearsal_sha256': io._hash(REHEARSAL),
        'teaching_identifiability': proof, 'new_word_training_layouts': list(LAYOUTS[:2]),
        'new_word_withheld_layouts': ['vos'], 'entity_split_overlap': 0,
        'scope': 'Fresh ordered mixed-effect and mixed-layout structures and participants; only VOS cells are withheld for the two new words. '
            'Laws/action menu/identity linkage/layout features are supplied. Final branches, role/language/mode/law views '
            'are dependent. Goal alternatives are hypothetical, not sequential feedback. Public same-team custody.'}
    for law, bank in laws.items():
        cases = bank['oracle']['episodes']; forecasts = [f for g in cases for f in g['forecasts']]
        goals = [g for group in bank['goal_groups'] for g in group['goals']]
        audit[law] = {'episodes': len(cases), 'forecasts': len(forecasts),
            'families': dict(Counter(g['family'] for g in cases)),
            'identifiable_forecasts': sum(len(f['possible_worlds']) == 1 for f in forecasts),
            'ambiguous_forecasts': sum(len(f['possible_worlds']) > 1 for f in forecasts),
            'endpoint_identifiable_actions': sum(len(f['equivalent_action_indices']) == 1 for f in forecasts),
            'held_new_word_forecasts': sum(cell['held_layout'] for g in cases for cell in g['cells']),
            'goal_groups': len(bank['goal_groups']), 'goal_decisions': len(goals),
            'impossible_goals': sum(not g['attainable'] for g in goals),
            'effect_sensitive_goals': sum(g['effect_sensitive'] for g in goals),
            'set_required_goals': sum(g['set_required'] for g in goals),
            'contact_required_goals': sum(g['contact_required'] for g in goals)}
    return {'teach': teach, 'rehearsal': rehearsal, 'laws': laws, 'audit': audit, 'parser_labels': parser_labels}
