"""Fresh v3 participant structures over exactly the published v1 training evidence.

The observation/oracle schemas and physical semantics are unchanged. Previously
opened word/layout cells remain TRAIN-withheld; they are not fresh lexical cells.
Only the challenge identities and participant structures are new.
"""
from collections import Counter, defaultdict
from itertools import product

from . import acceptance_contract as c, continuation_run as io
from . import effect_role_data as prior, effect_role_data_v2 as previous

ROOT, LAWS = io.ROOT, prior.LAWS
VERSION = 'effect-role-v3'
SEEDS = {'identity': 20261102601, 'challenge': 20261102602}
PARENT = ROOT / 'data/effect-role-v2'
PARENT_FREEZE_SHA256 = 'be204b7a610a892ce0f62a83f8144159512f36d29da0339eb12591c4a8f73a4a'
TRAINING_PARENT = previous.PARENT
TRAINING_FILES = dict(previous.TRAINING_FILES)
HISTORY = {'v1': TRAINING_PARENT, 'v2': PARENT}
SCHEDULES = {'path_return4': (4, ((0, 1), (1, 2), (2, 3), (1, 0))),
             'branch_return5': (5, ((0, 1), (1, 2), (2, 3), (2, 4), (2, 1)))}
SOURCE_FILES = ('effect_role_data_v3.py', *previous.SOURCE_FILES)


def source_digest():
    return c.digest({name: io._hash(ROOT / name) for name in SOURCE_FILES})


def law_digest(law):
    return c.digest({'study': VERSION, 'unchanged_semantic_law_sha256': prior.law_digest(law),
        'seeds': SEEDS, 'participant_schedules': SCHEDULES,
        'scope': 'New participant structures and identities; unchanged physics, words, layouts, training and goals.'})


def previous_schedules():
    return {**previous.previous_schedules(),
            **{'effect-role-v2/' + name: edges for name, (_, edges) in previous.SCHEDULES.items()}}


def novelty(schedules):
    audit = previous.novelty(schedules); old = previous_schedules()
    shape = prior.centering_data.ordered_shape
    ordered = {shape(edges) for edges in old.values()}
    unordered = {previous._unordered(edges) for edges in old.values()}
    c.require(not {shape(edges) for _, edges in schedules.values()} & ordered,
              'previously opened participant structure including v2')
    c.require(not {previous._unordered(edges) for _, edges in schedules.values()} & unordered,
              'previously opened undirected participant multigraph including v2')
    return {**audit, 'compared_opened_families': sorted(old), 'prior_recipe_entries': len(old),
        'prior_distinct_ordered_shapes': len(ordered), 'prior_distinct_unordered_multigraphs': len(unordered),
        'ordered_overlap': 0, 'unordered_multigraph_overlap': 0, 'previous_schedule_sha256': c.digest(old)}


def build_assets():
    for path, digest in ((PARENT, PARENT_FREEZE_SHA256), (TRAINING_PARENT, previous.PARENT_FREEZE_SHA256)):
        c.require(io._hash(path / 'freeze.json') == digest, 'published parent freeze differs: ' + path.name)
    frozen = {version: io._read(path / 'freeze.json') for version, path in HISTORY.items()}
    def read_parent(version, name):
        path = HISTORY[version] / name
        c.require(io._hash(path) == frozen[version]['artifacts'][name]['sha256'], 'published artifact differs: ' + str(path))
        return io._read(path)
    copied = {key: read_parent('v1', name) for key, name in TRAINING_FILES.items()}
    for name in TRAINING_FILES.values():
        c.require(io._hash(PARENT / name) == frozen['v2']['artifacts'][name]['sha256'] ==
            frozen['v1']['artifacts'][name]['sha256'], 'v2 changed published TRAIN bytes: ' + name)
    for key in ('teach', 'rehearsal'): prior.validate_inputs(copied[key])
    old_audit = read_parent('v1', 'audit.json')
    old_inputs = {version: {law: read_parent(version, law + '-inputs.json.xz') for law in LAWS} for version in HISTORY}
    laws = {}
    for law in LAWS:
        records, gold = [], []
        for family, (n, edges) in SCHEDULES.items():
            for core, mode, direction, layout, context_mode, phase, final in product(prior.CORES,
                    (0, 1), (0, 1), range(3), ('established', 'unresolved'), (0, 1), range(4)):
                tag = [VERSION, SEEDS, family, core, context_mode, phase]
                choices = [0 if (t + phase) % 2 == 0 else 3 for t in range(len(edges))]; choices[-1] = final
                word = ('lights', 'zef', prior.NEW_WORDS[phase])[layout]
                layouts = [(layout + t - len(edges) + 1) % 3 for t in range(len(edges))]
                record, meta = prior._episode(tag, n, core, mode, direction, law, edges, choices, layouts, word, context_mode)
                group = c.digest([tag, mode, direction, layout, 'goal-group'])
                meta.update(family=family, lineage=c.digest(tag), phase=phase,
                    role_pair_id=c.digest([tag, mode, layout, final, 'role-pair']),
                    bilingual_pair_id=c.digest([tag, mode, direction, final, 'bilingual']) if layout < 2 else None,
                    translation_group_id=c.digest([tag, mode, direction, final, 'translation']),
                    effect_pair_id=c.digest([group, 'effect-pair', int(final in (1, 2))]),
                    goal_group_id=group, final_choice=final, shared_prefix_sha256=prior.prefix_key(record))
                records.append(record); gold.append(meta)
        inputs = prior.validate_inputs({'version': 'bilingual-input-v1', 'episodes': records}); groups = defaultdict(list)
        for meta in gold: groups[meta['goal_group_id']].append(meta)
        by_id = {e['id']: e for e in records}
        laws[law] = {'inputs': inputs, 'oracle': {'version': 'effect-role-oracle-v1', 'input_sha256': c.digest(inputs),
            'source_sha256': source_digest(), 'information_law_sha256': law_digest(law), 'episodes': gold},
            'goal_groups': [prior._goal_group(members, by_id) for _, members in sorted(groups.items())]}
    names = lambda bank: {v for e in bank['episodes'] for v in e['entities']}
    identities = lambda bank: {e['id'] for e in bank['episodes']}
    shapes = lambda bank: {prior.centering_data.ordered_shape(tuple(tuple(e['entities'].index(w) for w in
        event['text'].split() if w in e['entities']) for event in e['utterances'])) for e in bank['episodes']}
    overlaps = {}
    for version, banks in old_inputs.items():
        by_law = {law: {'episode_identity': len(identities(laws[law]['inputs']) & identities(banks[law])),
            'entity_identity': len(names(laws[law]['inputs']) & names(banks[law])),
            'ordered_participant_shape': len(shapes(laws[law]['inputs']) & shapes(banks[law]))} for law in LAWS}
        merged = {key: max(v[key] for v in by_law.values()) for key in by_law['nand']}
        c.require(not any(merged.values()), 'challenge overlaps opened ' + version)
        overlaps.update({'old_' + version + '_challenge_overlap': merged, 'old_' + version + '_challenge_overlap_by_law': by_law})
    training_overlap = {key: max(len(names(bank['inputs']) & names(copied[key])) for bank in laws.values())
                        for key in ('teach', 'rehearsal')}
    c.require(not any(training_overlap.values()), 'challenge reuses TRAIN identities')
    audit = {**novelty(SCHEDULES), 'version': VERSION, 'split_seeds': SEEDS, 'training_reused_from': 'data/effect-role-v1',
        'training_artifact_sha256': {name: frozen['v1']['artifacts'][name]['sha256'] for name in TRAINING_FILES.values()},
        'teach_episodes': len(copied['teach']['episodes']),
        **{k + '_forecasts': sum(len(e['utterances']) for e in copied[k]['episodes']) for k in ('teach', 'rehearsal')},
        'teaching_identifiability': old_audit['teaching_identifiability'], 'taught_words': list(prior.NEW_WORDS),
        'new_words': [], 'new_lexical_layout_cells': [],
        'training_withheld_but_opened_cells': [[word, 'vos'] for word in prior.NEW_WORDS],
        **overlaps,
        'training_entity_overlap': training_overlap,
        'scope': 'Fresh ordered participant structures and opaque identities only. V1 supplies archived reference evidence; v2 supplies exposed inputs and checkpoints despite incomplete original evidence. '
                 'V2 checkpoint reference forecasts require a separate prospective collection. All words/layouts/laws are previously opened; '
            'new-word/VOS and held-layout labels retain their TRAIN-withheld meaning. Exact v1 teaching, rehearsal, parser labels '
            'and lexical registry are reused. Conditional worlds and goals are recomputed prospectively, not selected by model outcomes. '
            'All paired views and hypothetical final alternatives remain dependent. Same-team custody.'}
    for law, bank in laws.items():
        cases = bank['oracle']['episodes']; forecasts = [f for e in cases for f in e['forecasts']]
        goals = [g for group in bank['goal_groups'] for g in group['goals']]
        audit[law] = {'episodes': len(cases), 'forecasts': len(forecasts), 'families': dict(Counter(e['family'] for e in cases)),
            'identifiable_forecasts': sum(len(f['possible_worlds']) == 1 for f in forecasts),
            'ambiguous_forecasts': sum(len(f['possible_worlds']) > 1 for f in forecasts),
            'endpoint_identifiable_actions': sum(len(f['equivalent_action_indices']) == 1 for f in forecasts),
            'held_new_word_forecasts': sum(cell['held_layout'] for e in cases for cell in e['cells']),
            'goal_groups': len(bank['goal_groups']), 'goal_decisions': len(goals),
            'impossible_goals': sum(not g['attainable'] for g in goals),
            'effect_sensitive_goals': sum(g['effect_sensitive'] for g in goals),
            'set_required_goals': sum(g['set_required'] for g in goals),
            'contact_required_goals': sum(g['contact_required'] for g in goals)}
    return {**copied, 'laws': laws, 'audit': audit}
