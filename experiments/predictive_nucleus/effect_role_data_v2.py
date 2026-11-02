"""Fresh participant structures over exactly the published v1 training evidence.

The observation/oracle schemas and physical semantics are unchanged. Previously
opened word/layout cells remain TRAIN-withheld; they are not fresh lexical cells.
Only the challenge identities and participant structures are new.
"""
from collections import Counter, defaultdict
from itertools import permutations, product

from . import acceptance_contract as c, continuation_run as io, effect_role_data as prior
from . import world, mixed_composition_data as mixed, multisource_law_data as multi
from . import hidden_cycle_data as hidden, joint_correlation_data as joint, timing_data as timing

ROOT, LAWS = io.ROOT, prior.LAWS
VERSION = 'effect-role-v2'
SEEDS = {'identity': 20261102501, 'challenge': 20261102502}
PARENT = ROOT / 'data/effect-role-v1'
PARENT_FREEZE_SHA256 = '7b500d3bb1811dd484ea0af9ce7131776e7aea6d7a60a33f0e8490e34d494dca'
TRAINING_FILES = {'teach': 'teach-inputs.json.xz', 'rehearsal': 'rehearsal-inputs.json.xz',
                  'parser_labels': 'parser-labels.json.xz', 'lexical_registry': 'lexical-registry.json'}
SCHEDULES = {'hub_return4': (4, ((0, 1), (1, 2), (1, 3), (1, 0))),
             'triangle_fan5': (5, ((0, 1), (1, 2), (2, 0), (0, 3), (0, 4)))}
SOURCE_FILES = ('effect_role_data_v2.py', 'effect_role_data.py', 'acceptance_contract.py',
    'bilingual_contract.py', 'bilingual_data.py', 'binding_data.py', 'centering_data.py',
    'continuation_run.py', 'coordinate_data.py', 'multisource_law_oracle.py', 'prospective_data.py',
    'prospective_oracle.py', 'protocol.py', 'saturation_data.py', 'set_acquisition_data.py', 'world.py',
    'mixed_composition_data.py', 'multisource_law_data.py', 'hidden_cycle_data.py',
    'joint_correlation_data.py', 'timing_data.py', 'timing_contract.py', 'timing_oracle.py',
    'continuation_data.py', 'set_acquisition_data_v2.py', 'sensor_transfer_data.py', 'comparison_data.py')


def source_digest():
    return c.digest({name: io._hash(ROOT / name) for name in SOURCE_FILES})


def law_digest(law):
    return c.digest({'study': VERSION, 'unchanged_semantic_law_sha256': prior.law_digest(law),
        'seeds': SEEDS, 'participant_schedules': SCHEDULES,
        'scope': 'New participant structures and identities; unchanged physics, words, layouts, training and goals.'})


def previous_schedules():
    """Bounded source recipes only; never load historical outcomes or forecasts."""
    schedules = {**{'bilingual/' + p + '/' + k: v for p, fs in prior.simulator.FAMILIES.items() for k, v in fs.items()},
        **{'binding/' + k: v for k, v in prior.binding_data.SCHEDULES.items()},
        **{label + '/' + k: edges for label, module in (('saturation', prior.saturation_data),
            ('centering', prior.centering_data), ('coordinate', prior.coordinate_data), ('effect-role-v1', prior))
            for k, (_, edges) in module.SCHEDULES.items()}, **{'world/' + k: v for k, v in world.FAMILIES.items()}}
    schedules.update({'continuation/single': ((0, 1),), 'continuation/two-overlap': ((0, 1), (1, 2)),
        'continuation/two-repeat': ((0, 1), (0, 1)), 'continuation/self': ((0, 0),)})
    for count in (3, 4, 5):
        for name, edges in {'chain': tuple((i, i + 1) for i in range(count)),
            'fork': tuple((0, i + 1) for i in range(count)), 'cycle': tuple((i, (i + 1) % count) for i in range(count)),
            'disjoint': tuple((0, 1) if i % 2 == 0 else (2, 3) for i in range(count))}.items():
            schedules['continuation/' + name + str(count)] = edges
    schedules.update({'mixed/' + k: tuple(e for e in v if e is not None) for k, v in mixed.FAMILIES.items()})
    schedules.update({'multisource/' + p + '/' + k: v for p, fs in multi.FAMILIES.items() for k, v in fs.items()})
    schedules.update({'hidden-cycle/' + k: v for k, v in hidden.FAMILIES.items()})
    schedules.update({'joint-correlation/' + p + '/' + k: v for p, fs in joint.MOTIFS.items() for k, v in fs.items()})
    for name, (edges, suffix, _) in timing.FAMILIES.items():
        schedules['timing/' + name + '/ordered'] = ((0, 1),) + tuple(edges) + tuple(suffix)
        schedules['timing/' + name + '/permuted'] = ((0, 1),) + tuple(reversed(edges)) + tuple(suffix)
    schedules.update({'set-v1/contact-projection': ((0, 1), (1, 2), (0, 2)),
        'set-v2/contact-projection': ((0, 1), (1, 2), (2, 0)),
        'sensor-transfer/reordered': ((0, 1), (1, 2)), 'sensor-transfer/reversed': ((1, 0), (2, 0)),
        'comparison/same-pair': ((0, 1), (0, 1)), 'comparison/composition': ((0, 1), (1, 2))})
    return schedules


def _unordered(edges):
    vertices = sorted({v for edge in edges for v in edge}); local = {v: i for i, v in enumerate(vertices)}
    return min(tuple(sorted(tuple(sorted((p[local[a]], p[local[b]]))) for a, b in edges))
               for p in permutations(range(len(vertices))))


def novelty(schedules):
    audit = prior.coordinate_data.novelty(schedules); previous = previous_schedules()
    shape = prior.centering_data.ordered_shape
    old = {shape(edges) for edges in previous.values()}; old_unordered = {_unordered(edges) for edges in previous.values()}
    c.require(not {shape(edges) for _, edges in schedules.values()} & old, 'previously opened participant structure')
    c.require(not {_unordered(edges) for _, edges in schedules.values()} & old_unordered,
              'previously opened undirected participant multigraph')
    return {**audit, 'compared_opened_families': sorted(previous), 'prior_recipe_entries': len(previous),
        'prior_distinct_ordered_shapes': len(old), 'ordered_overlap': 0, 'unordered_multigraph_overlap': 0,
        'previous_schedule_sha256': c.digest(previous)}


def build_assets():
    c.require(io._hash(PARENT / 'freeze.json') == PARENT_FREEZE_SHA256, 'published v1 freeze differs')
    frozen = io._read(PARENT / 'freeze.json')
    def read_parent(name):
        c.require(io._hash(PARENT / name) == frozen['artifacts'][name]['sha256'], 'published v1 artifact differs: ' + name)
        return io._read(PARENT / name)
    copied = {key: read_parent(name) for key, name in TRAINING_FILES.items()}
    for key in ('teach', 'rehearsal'): prior.validate_inputs(copied[key])
    old_audit = read_parent('audit.json'); old_inputs = {law: read_parent(law + '-inputs.json.xz') for law in LAWS}
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
    fresh = laws['nand']['inputs']
    overlap_by_law = {law: {'episode_identity': len(identities(laws[law]['inputs']) & identities(old_inputs[law])),
        'entity_identity': len(names(laws[law]['inputs']) & names(old_inputs[law])),
        'ordered_participant_shape': len(shapes(laws[law]['inputs']) & shapes(old_inputs[law]))} for law in LAWS}
    overlap = {key: max(v[key] for v in overlap_by_law.values()) for key in overlap_by_law['nand']}
    training_overlap = {k: len(names(fresh) & names(copied[k])) for k in ('teach', 'rehearsal')}
    c.require(not any(overlap.values()) and not any(training_overlap.values()), 'challenge overlaps previous evidence')
    audit = {**novelty(SCHEDULES), 'version': VERSION, 'split_seeds': SEEDS, 'training_reused_from': 'data/effect-role-v1',
        'training_artifact_sha256': {name: frozen['artifacts'][name]['sha256'] for name in TRAINING_FILES.values()},
        'teach_episodes': len(copied['teach']['episodes']),
        **{k + '_forecasts': sum(len(e['utterances']) for e in copied[k]['episodes']) for k in ('teach', 'rehearsal')},
        'teaching_identifiability': old_audit['teaching_identifiability'], 'taught_words': list(prior.NEW_WORDS),
        'new_words': [], 'new_lexical_layout_cells': [],
        'training_withheld_but_opened_cells': [[word, 'vos'] for word in prior.NEW_WORDS],
        'old_v1_challenge_overlap': overlap, 'old_v1_challenge_overlap_by_law': overlap_by_law,
        'training_entity_overlap': training_overlap,
        'scope': 'Fresh ordered participant structures and opaque identities only. All words/layouts/laws are previously opened; '
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
