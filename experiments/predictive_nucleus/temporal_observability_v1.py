"""Exact evaluator-side observation support; no learner, training or admission claim.

The uniform population is a declared counterfactual construction. Only the
observed report partitions it: the private proposed operation is never a
condition of the decision calculation. Every probe is a distinct physical
event except verification of the one actual historical event and its replay.
"""
import argparse
from collections import Counter, deque
from fractions import Fraction
from hashlib import sha256
from itertools import product
import json
import lzma
from pathlib import Path
import platform
import resource
import subprocess
import time

from . import bilingual_data as simulator, effect_role_data as oracle
from .physical_query_v1 import choose

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
VERSION = 'temporal-observability-v1'
PROTOCOL = 'TEMPORAL_OBSERVABILITY_PROTOCOL_V1.md'
PROTOCOL_COMMIT = '8d07a0082241dd9409492bf6343686ec8e633132'
PROTOCOL_SHA256 = '06c1aec73bec7cd886ab30c3d23b9755b4666858f063d64a3575dd1a226b26b7'
SOURCES = ('temporal_observability_v1.py', 'tests/test_temporal_observability_v1.py',
           'bilingual_data.py', 'effect_role_data.py', 'set_acquisition_data.py',
           'multisource_law_oracle.py', 'physical_query_v1.py')
LAWS = ('nand', 'nor')
CAUSES = ('local_correction', 'one_event_exception', 'report_only', 'parent_correction')
OPERATIONS = ((0, 0, 1, -1), (0, 1, 0, -1), (1, 0, -1, 1), (1, 1, -1, 1))
FEES = (Fraction(1, 20), Fraction(1), None)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _json(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False,
                       default=lambda x: str(x) if isinstance(x, Fraction) else
                       (_ for _ in ()).throw(TypeError(type(x).__name__))) + '\n').encode()


def _digest(value):
    return sha256(_json(value)).hexdigest()


def _bits(state):
    return tuple((state >> shift) & 1 for shift in (2, 1, 0))


def checked_endpoint(law, mode, operation, state):
    """Cross-check the Boolean simulator against the separate table oracle."""
    _require(law in LAWS and type(mode) is int and mode in (0, 1) and
             type(operation) is int and operation in range(4), 'invalid physical condition')
    state = tuple(state)
    _require(len(state) == 3 and all(type(x) is int and x in (0, 1) for x in state),
             'expected three binary coordinates')
    after = simulator._step(state, OPERATIONS[operation], mode, law)
    endpoint = sum(bit << shift for bit, shift in zip(after, (2, 1, 0)))
    support, probabilities = oracle._distribution(list(state), OPERATIONS[operation], (mode,), law)
    _require(support == [endpoint] and probabilities == [1.], 'physical implementations disagree')
    return endpoint


def partition(columns, size):
    """Canonical world-index blocks; labels and their ordering carry no evidence."""
    _require(type(size) is int and size > 0, 'nonempty world inventory required')
    columns = tuple(tuple(column) for column in columns)
    _require(all(len(column) == size for column in columns), 'observation dimensions differ')
    groups = {}
    for index in range(size):
        groups.setdefault(tuple(column[index] for column in columns), []).append(index)
    return tuple(sorted(tuple(group) for group in groups.values()))


def identifies(blocks, labels):
    return all(len({labels[index] for index in block}) == 1 for block in blocks)


def minimum_probe_set(probes, target):
    """Exact minimum set cover over differently targeted world pairs.

    Equivalent partitions and repeated coverage states are collapsed. This
    avoids enumerating every subset of the physical menu. A probe is never
    counted twice; breadth-first search returns a minimum distinct set.
    """
    target = tuple(target)
    _require(target, 'nonempty target inventory required')
    pairs = [(a, b) for a in range(len(target)) for b in range(a) if target[a] != target[b]]
    if not pairs:
        return ()
    candidates, seen_partitions, seen_masks = [], set(), set()
    for name, column in probes.items():
        blocks = partition((column,), len(target))
        mask = sum(1 << bit for bit, (a, b) in enumerate(pairs) if column[a] != column[b])
        if blocks not in seen_partitions and mask and mask not in seen_masks:
            candidates.append((name, mask))
            seen_masks.add(mask)
        seen_partitions.add(blocks)
    complete = (1 << len(pairs)) - 1
    available = 0
    for _, mask in candidates:
        available |= mask
    if available != complete:
        return None
    queue, visited = deque([(0, ())]), {0}
    while queue:
        covered, chosen = queue.popleft()
        for name, mask in candidates:
            combined = covered | mask
            if combined in visited:
                continue
            selected = chosen + (name,)
            if combined == complete:
                return selected
            visited.add(combined)
            queue.append((combined, selected))
    raise AssertionError('complete finite probe menu was unreachable')


def observe(prior, history, evidence_id, column, answer):
    """An exact receipt update; identical delivery never adds corroboration."""
    prior, column = tuple(map(Fraction, prior)), tuple(column)
    _require(len(prior) == len(column) and sum(prior) == 1 and min(prior) >= 0,
             'invalid prior or observation dimensions')
    payload = (column, answer)
    if evidence_id in history:
        _require(history[evidence_id] == payload, 'conflicting evidence identity')
        return prior, dict(history)
    mass = sum(weight for weight, outcome in zip(prior, column) if outcome == answer)
    _require(mass > 0, 'impossible physical observation')
    posterior = tuple(weight / mass if outcome == answer else Fraction(0)
                      for weight, outcome in zip(prior, column))
    return posterior, dict(history, **{evidence_id: payload})


def _distribution(weights, target):
    return tuple(sum(weight for weight, endpoint in zip(weights, target) if endpoint == value)
                 for value in range(8))


def analyze_target(probes, target, fee):
    """Exact one-step Bayes utility under a uniform identical-prefix group."""
    target = tuple(target)
    _require(target and all(type(x) is int and x in range(8) for x in target), 'invalid target endpoints')
    _require(fee is None or (not isinstance(fee, bool) and Fraction(fee) >= 0), 'invalid fee')
    fee = None if fee is None else Fraction(fee)
    size = len(target)
    prior = (Fraction(1, size),) * size
    initial = _distribution(prior, target)
    before, values = max(initial), {}
    rewards = [[int(endpoint == action) for action in range(8)] for endpoint in target]
    for name, column in probes.items():
        blocks = partition((column,), size)
        _require(all(type(x) is int and x in range(8) for x in column), 'invalid probe endpoints')
        after = sum(Fraction(max(Counter(target[i] for i in block).values()), size) for block in blocks)
        values[name] = after
        actual = choose([float(x) for x in prior],
                        [[int(endpoint == answer) for answer in range(8)] for endpoint in column],
                        rewards, None if fee is None else float(fee))
        _require(all(abs(actual[key] - float(value)) <= 1e-12 for key, value in
                     (('expected_before', before), ('expected_after', after), ('value', after - before)))
                 and actual['action'] == initial.index(before)
                 and actual['ask'] == (fee is not None and after - before > fee),
                 'physical_query formula differs from exact reference')
    best = max(values, key=values.get) if values else None
    after = values[best] if best is not None else before
    value = after - before
    ask = fee is not None and value > fee
    selected = best if ask else None
    answers = sorted(set(probes[selected])) if ask else (None,)
    branches = []
    for answer in answers:
        weights, history = observe(prior, {}, selected, probes[selected], answer) if ask else (prior, {})
        repeated, repeated_history = observe(weights, history, selected, probes[selected], answer) if ask else (weights, history)
        _require(weights == repeated and history == repeated_history, 'duplicate receipt changed retained evidence')
        distribution = _distribution(weights, target)
        support = tuple(i for i, weight in enumerate(weights) if weight)
        branches.append({'answer': answer, 'probability': Fraction(len(support), size), 'support': support,
                         'posterior': weights, 'target_distribution': distribution,
                         'action': distribution.index(max(distribution)),
                         'consumed_ids': tuple(history), 'replay_unchanged': True})
    expected = sum(branch['probability'] * max(branch['target_distribution']) for branch in branches)
    _require(expected == (after if ask else before), 'posterior branch utility differs')
    return {'prior': prior, 'before': before, 'after': after, 'value': value, 'ask': ask,
            'selected': selected, 'best_probe': best, 'fee': fee, 'probe_after': values,
            'expected_correctness': expected, 'net': expected - fee if ask else expected,
            'branches': branches, 'formula_checks': len(probes)}


def make_context(law, mode, old, state, number=0):
    """Build twelve worlds, then pool ONLY by the actually delivered report."""
    _require(type(old) is int and old in range(4) and type(state) is int and state in range(8)
             and type(number) is int and number >= 0, 'invalid context recipe')
    table = tuple(tuple(checked_endpoint(law, mode, op, _bits(s)) for s in range(8)) for op in range(4))
    ticket = 'E' + _digest([VERSION, number])[:16]
    handles = [ticket + '/' + str(slot) for slot in range(3)]
    prefix = [{'evidence_id': ticket + f'/calibration/{op}/{s}', 'source': 'physical_sensor',
               'scope': 'parent', 'time': -2, 'entities': handles, 'before': _bits(s),
               'action': OPERATIONS[op], 'endpoint': table[op][s]}
              for op, s in product(range(4), range(8))]
    prefix += [{'evidence_id': ticket + f'/teaching/{word}/{s}', 'source': 'physical_sensor',
                'scope': 'parent', 'time': -1, 'entities': handles, 'before': _bits(s),
                'word': word, 'endpoint': table[old][s]}
               for word, s in product(('tested_word', 'protected_word'), range(8))]
    worlds = [{'new': new, 'cause': cause, 'report': table[new][state]}
              for new in range(4) if new != old for cause in CAUSES]
    groups = []
    for report in sorted({world['report'] for world in worlds}):
        support = tuple(i for i, world in enumerate(worlds) if world['report'] == report)
        selected_worlds = [worlds[i] for i in support]
        claim = {'evidence_id': ticket + '/report', 'physical_event_id': ticket + '/original',
                 'source': 'claimant', 'scope': 'local', 'time': 0, 'entities': handles,
                 'before': _bits(state), 'word': 'tested_word', 'endpoint': report}
        public = prefix + [claim]
        original = tuple(table[old if w['cause'] == 'report_only' else w['new']][state] for w in selected_worlds)
        probes = {'verify_original': original}
        descriptors = {'verify_original': {'event_id': ticket + '/original', 'time': 0, 'scope': 'local',
                                           'before': _bits(state), 'kind': 'actual_event_measurement'}}
        targets = {}
        for scope, s in product(('local', 'sibling'), range(8)):
            column = tuple(table[w['new'] if w['cause'] == 'parent_correction' or
                                 (scope == 'local' and w['cause'] == 'local_correction') else old][s]
                           for w in selected_worlds)
            name = scope + '/' + str(s)
            probes[name] = column
            descriptors[name] = {'event_id': ticket + '/probe/' + name, 'time': 1,
                                  'scope': scope, 'before': _bits(s), 'kind': 'fresh_physical_instance'}
            targets[name] = column
        probes['protected_word'] = (table[old][state],) * len(support)
        probes['report_replay'] = (report,) * len(support)
        descriptors['protected_word'] = {'event_id': ticket + '/protected', 'time': 1, 'scope': 'local',
                                          'before': _bits(state), 'kind': 'protected_word_instance'}
        descriptors['report_replay'] = {'event_id': ticket + '/original', 'evidence_id': claim['evidence_id'],
                                        'kind': 'same_source_receipt'}
        groups.append({'public_prefix': public, 'prefix_digest': _digest(public), 'support': support,
                       'report_probability': Fraction(len(support), 12), 'worlds': selected_worlds,
                       'prior': (Fraction(1, len(support)),) * len(support), 'probes': probes,
                       'probe_descriptors': descriptors, 'targets': targets,
                       'target_time': 2, 'target_event_prefix': ticket + '/target/',
                       'menus': {'immediate': tuple(probes), 'lost': tuple(name for name in probes if name != 'verify_original'),
                                 'none': ()}})
    _require(sum(len(group['support']) for group in groups) == 12, 'report conditioning lost worlds')
    return {'oracle_context': {'law': law, 'mode': mode, 'old': old, 'state': state},
            'public_pre_report': prefix, 'pre_report_prior': (Fraction(1, 12),) * 12,
            'physical_endpoint_table': table, 'worlds': worlds, 'groups': groups}


def _group_result(group):
    size, causes = len(group['worlds']), tuple(world['cause'] for world in group['worlds'])
    result, failures, checks = {}, [], Counter()
    for menu_name, names in group['menus'].items():
        probes = {name: group['probes'][name] for name in names}
        blocks = partition(tuple(probes.values()), size)
        ambiguity = [block for block in blocks if {'one_event_exception', 'report_only'} <= {causes[i] for i in block}]
        menu = {'partitions': {name: partition((column,), size) for name, column in probes.items()},
                'complete_partition': blocks, 'cause_identifiable': identifies(blocks, causes),
                'minimum_cause_probes': minimum_probe_set(probes, causes),
                'exception_report_ambiguity': ambiguity, 'targets': {}}
        for target_name, target in group['targets'].items():
            minimum = minimum_probe_set(probes, target)
            if menu_name != 'none' and minimum is None:
                failures.append({'menu': menu_name, 'target': target_name, 'reason': 'target_unidentifiable'})
            policies = [analyze_target(probes, target, fee) for fee in FEES]
            permutation = tuple(reversed(range(size)))
            renamed = {'renamed/' + str(i): tuple(column[j] for j in permutation)
                       for i, column in enumerate(probes.values())}
            invariant = analyze_target(renamed, tuple(target[i] for i in permutation), FEES[0])
            _require(all(invariant[key] == policies[0][key] for key in
                         ('before', 'after', 'value', 'net', 'ask')), 'renaming or world ordering changed utility')
            for policy in policies:
                _require(not policy['ask'] or (policy['fee'] == FEES[0] and menu_name != 'none'
                         and policy['selected'] not in ('protected_word', 'report_replay')), 'paid uninformative query')
                for branch in policy['branches']:
                    delivered = list(group['public_prefix'])
                    if policy['ask']:
                        descriptor = group['probe_descriptors'][policy['selected']]
                        delivered.append({**descriptor, 'evidence_id': descriptor['event_id'] + '/physical',
                                          'source': 'physical_sensor', 'endpoint': branch['answer']})
                    branch['consumed_ids'] = tuple(row['evidence_id'] for row in delivered)
                    branch['delivered_prefix_digest'] = _digest(delivered)
                    branch['target_event_id'] = group['target_event_prefix'] + target_name
                checks['formula'] += policy['formula_checks']
                checks['replay'] += len(policy['branches'])
            checks['renaming'] += 1
            menu['targets'][target_name] = {'minimum_probes': minimum,
                                            'identifiable': identifies(blocks, target), 'policies': policies}
        result[menu_name] = menu
    for name in ('protected_word', 'report_replay'):
        _require(len(partition((group['probes'][name],), size)) == 1, 'uninformative evidence split worlds')
    _require(result['lost']['exception_report_ambiguity'], 'lost original event incorrectly identifies the cause')
    return {'menus': result, 'failures': failures, 'checks': dict(checks)}


def source_receipt():
    """Refuse full enumeration until protocol and all executable sources are committed."""
    def git(*args):
        return subprocess.check_output(['git', '-C', str(REPO), *args], text=True).strip()
    _require(sha256((ROOT / PROTOCOL).read_bytes()).hexdigest() == PROTOCOL_SHA256, 'protocol bytes differ')
    _require(git('status', '--porcelain', '--untracked-files=no') == '', 'clean tracked source required')
    commit = git('rev-parse', 'HEAD')
    git('merge-base', '--is-ancestor', PROTOCOL_COMMIT, commit)
    hashes = {}
    for name in (*SOURCES, PROTOCOL):
        path = ROOT / name
        published = subprocess.check_output(['git', '-C', str(REPO), 'show', commit + ':' + path.relative_to(REPO).as_posix()])
        _require(published == path.read_bytes(), 'uncommitted source ' + name)
        hashes[name] = sha256(published).hexdigest()
    return {'source_commit': commit, 'source_sha256': hashes,
            'protocol_commit': PROTOCOL_COMMIT, 'protocol_sha256': PROTOCOL_SHA256}


def run(output):
    """Run once into a new directory; execution identity is separate from results."""
    source = source_receipt()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    wall, cpu = time.perf_counter(), time.process_time()
    contexts, failures, counts = [], [], Counter()
    for number, (law, mode, old, state) in enumerate(product(LAWS, range(2), range(4), range(8))):
        context = make_context(law, mode, old, state, number)
        for group in context['groups']:
            group['analysis'] = _group_result(group)
            failures.extend({'context': number, 'prefix': group['prefix_digest'], **item}
                            for item in group['analysis']['failures'])
            counts.update(group['analysis']['checks'])
            counts['report_groups'] += 1
            counts['coincident_report_groups'] += int(group['public_prefix'][-1]['endpoint'] == context['physical_endpoint_table'][old][state])
            for menu_name in ('immediate', 'lost'):
                menu = group['analysis']['menus'][menu_name]
                counts[menu_name + '_cause_identifiable_groups'] += int(menu['cause_identifiable'])
                counts[menu_name + '_exception_report_ambiguous_groups'] += int(bool(menu['exception_report_ambiguity']))
        counts.update(contexts=1, worlds=len(context['worlds']), old_new_designs=3, physical_crosschecks=32)
        contexts.append(context)
    _require(counts['contexts'] == 128 and counts['worlds'] == 1536 and counts['old_new_designs'] == 384,
             'registered population differs')
    _require(source_receipt() == source, 'source changed during enumeration')
    result = {'version': VERSION, **source, 'counts': dict(counts), 'failures': failures,
              'decision': 'REVISE_TEMPORAL_OBSERVATION_PREFLIGHT' if failures else 'KEEP_TEMPORAL_OBSERVATION_PREFLIGHT',
              'scope': 'Exact constructed observation-support analysis; no learner or G5 admission.',
              'endpoint_encoding': 'three roster bits, most-significant bit first',
              'rational_encoding': 'exact Fraction strings', 'contexts': contexts}
    data = lzma.compress(_json(result), format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64)
    (output / 'results.json.xz').write_bytes(data)
    receipt = {'version': VERSION, **source, 'result_sha256': sha256(data).hexdigest(), 'result_bytes': len(data),
               'wall_seconds': time.perf_counter() - wall, 'cpu_seconds': time.process_time() - cpu,
               'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               'python': platform.python_version(), 'platform': platform.platform(), 'pid': __import__('os').getpid(),
               'source_lines': len(Path(__file__).read_text().splitlines()),
               'test_lines': len((ROOT / SOURCES[1]).read_text().splitlines()),
               'inclusive_python_lines': sum(len(path.read_text().splitlines()) for path in ROOT.rglob('*.py'))}
    (output / 'execution.json').write_bytes(_json(receipt))
    return {'decision': result['decision'], 'counts': result['counts'], 'result_sha256': receipt['result_sha256']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    print(json.dumps(run(parser.parse_args().output), sort_keys=True))
