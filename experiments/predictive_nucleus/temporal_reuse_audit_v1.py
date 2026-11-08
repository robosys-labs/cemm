"""Post hoc support audit of opened records; no model, fitting or fresh challenge.

Questions matching the pair of active target inputs are excluded: changing
the untouched third participant alone cannot establish physical transfer.
Two-probe results allow at most two fixed distinct probes, not an adaptive policy.
"""
import argparse
from collections import Counter, defaultdict, deque
from fractions import Fraction
from hashlib import sha256
from itertools import combinations
import json
import lzma
from pathlib import Path
import resource
import time

ROOT = Path(__file__).resolve().parent
INPUT_SHA256 = '3c7ecfe48708cad5dd1450c971876bc426114fd87002ffb4ac19f22c2486aaad'
SOURCE_COMMIT = '94eaddd1bb07a58247660909b958158dbd7ddd67'
PROTOCOL_COMMIT = '8d07a0082241dd9409492bf6343686ec8e633132'
PROTOCOL_SHA256 = '06c1aec73bec7cd886ab30c3d23b9755b4666858f063d64a3575dd1a226b26b7'


def permitted(names, descriptors, target_before):
    """Use public input descriptors only; never inspect a probe's answers."""
    result = []
    for name in names:
        descriptor = descriptors[name]
        if 'before' in descriptor:
            before = descriptor['before']
            if len(before) != 3 or any(type(x) is not int or x not in (0, 1) for x in before):
                raise ValueError('invalid public three-bit input')
            if tuple(before[:2]) != tuple(target_before[:2]):
                result.append(name)
        elif descriptor.get('kind') == 'same_source_receipt':
            result.append(name)
        else:
            raise ValueError('missing public probe input')
    return tuple(result)


def partition(columns, size):
    groups = defaultdict(list)
    for index in range(size):
        groups[tuple(column[index] for column in columns)].append(index)
    return tuple(tuple(block) for block in groups.values())


def accuracy(blocks, target):
    return Fraction(sum(max(Counter(target[i] for i in block).values()) for block in blocks), len(target))


def minimum(probes, target):
    """Breadth-first exact pair-separation cover; repeated probes add no bits."""
    pairs = [(a, b) for a, b in combinations(range(len(target)), 2) if target[a] != target[b]]
    if not pairs:
        return ()
    masks = {}
    for name, column in probes.items():
        mask = sum(1 << i for i, (a, b) in enumerate(pairs) if column[a] != column[b])
        if mask:
            masks.setdefault(mask, name)
    complete, available = (1 << len(pairs)) - 1, 0
    for mask in masks:
        available |= mask
    if available != complete:
        return None
    queue, seen = deque([(0, ())]), {0}
    while queue:
        covered, names = queue.popleft()
        for mask, name in masks.items():
            union = covered | mask
            if union == complete:
                return names + (name,)
            if union not in seen:
                seen.add(union)
                queue.append((union, names + (name,)))
    raise AssertionError('finite cover not found')


def analyze(probes, target):
    """Independently count target-majority mass in each observation partition."""
    size = len(target)
    zero = accuracy(partition((), size), target)
    singles = {name: accuracy(partition((column,), size), target) for name, column in probes.items()}
    best = max(singles, key=singles.get) if singles else None
    one = singles[best] if best is not None else zero
    two, best_pair = one, (best,) if best is not None and one > zero else ()
    for names in combinations(probes, 2):
        score = accuracy(partition(tuple(probes[n] for n in names), size), target)
        if score > two:
            two, best_pair = score, names
    blocks = partition(tuple(probes.values()), size)
    full = accuracy(blocks, target)
    witnesses = [next((pair for pair in combinations(block, 2) if target[pair[0]] != target[pair[1]]), None)
                 for block in blocks]
    policies = []
    for fee in (Fraction(1, 20), Fraction(1), None):
        ask = fee is not None and one - zero > fee
        policies.append({'fee': fee, 'ask': ask, 'selected': best if ask else None,
                         'accuracy': one if ask else zero, 'net': one - fee if ask else zero})
    return {'zero_accuracy': zero, 'one_accuracy': one, 'two_nonadaptive_accuracy': two,
            'full_accuracy': full, 'best_one': best, 'best_two': best_pair,
            'minimum_probes': minimum(probes, target), 'complete_partition': blocks,
            'unresolved_witnesses': tuple(pair for pair in witnesses if pair is not None),
            'one_step_policies': policies}


def case_weight(worlds, contexts=128, targets=16):
    """Reports are conditioned observations; groups are NOT equally weighted."""
    return Fraction(worlds, 12 * contexts * targets)


def audit(record):
    summaries, rows, unresolved, example = {}, [], [], None
    for menu in ('immediate', 'lost'):
        summaries[menu] = {'cases': 0, 'weight': Fraction(0), 'minimum_counts': Counter(),
                           'minimum_weights': defaultdict(Fraction), 'weighted': defaultdict(Fraction)}
    if len(record['contexts']) != 128:
        raise ValueError('registered context count differs')
    for ci, context in enumerate(record['contexts']):
        if sum(len(g['support']) for g in context['groups']) != 12:
            raise ValueError('conditioned report groups lost worlds')
        for group in context['groups']:
            if len(group['targets']) != 16 or Fraction(group['report_probability']) != Fraction(len(group['worlds']), 12):
                raise ValueError('registered target or report weights differ')
            for target_name, target in group['targets'].items():
                before = group['probe_descriptors'][target_name]['before']
                weight = case_weight(len(group['worlds']))
                for menu in summaries:
                    names = permitted(group['menus'][menu], group['probe_descriptors'], before)
                    probes = {name: group['probes'][name] for name in names}
                    if any('before' not in group['probe_descriptors'][name] and len(set(column)) != 1
                           for name, column in probes.items()):
                        raise ValueError('replayed receipt carries new information')
                    result = analyze(probes, target)
                    if not (result['zero_accuracy'] <= result['one_accuracy'] <=
                            result['two_nonadaptive_accuracy'] <= result['full_accuracy'] <= 1):
                        raise ValueError('information ceilings are inconsistent')
                    row = {'context': ci, 'prefix_digest': group['prefix_digest'], 'target': target_name,
                           'menu': menu, 'weight': weight, 'allowed_probes': names, **result}
                    rows.append(row)
                    summary = summaries[menu]
                    summary['cases'] += 1
                    summary['weight'] += weight
                    minimum_count = 'unidentifiable' if result['minimum_probes'] is None else str(len(result['minimum_probes']))
                    summary['minimum_counts'][minimum_count] += 1
                    summary['minimum_weights'][minimum_count] += weight
                    for key in ('zero_accuracy', 'one_accuracy', 'two_nonadaptive_accuracy', 'full_accuracy'):
                        summary['weighted'][key] += weight * result[key]
                    cheap = result['one_step_policies'][0]
                    for key in ('accuracy', 'net', 'ask'):
                        summary['weighted']['cheap_' + key] += weight * cheap[key]
                    if result['unresolved_witnesses']:
                        item = {key: row[key] for key in ('context', 'prefix_digest', 'target', 'menu')}
                        item['group_indices'] = result['unresolved_witnesses']
                        item['world_indices'] = tuple(tuple(group['support'][i] for i in pair)
                                                      for pair in result['unresolved_witnesses'])
                        unresolved.append(item)
                        if example is None:
                            a, b = result['unresolved_witnesses'][0]
                            example = {**item, 'physical_context': context['oracle_context'],
                                       'report': group['public_prefix'][-1], 'target_before': before,
                                       'worlds': [group['worlds'][a], group['worlds'][b]],
                                       'target_endpoints': [target[a], target[b]],
                                       'identical_allowed_answers': {n: [column[a], column[b]] for n, column in probes.items()}}
    if any(summary['weight'] != 1 for summary in summaries.values()):
        raise ValueError('population weights do not sum to one')
    return {'status': 'POSTHOC_OPENED_BANK_SUPPORT_AUDIT', 'learner_evaluated': False,
            'scope': 'Finite supplied hypotheses; two-probe ceiling is nonadaptive; no G5 admission.',
            'summary': summaries, 'cases': rows, 'unresolved_cases': unresolved, 'counterexample': example}


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False,
                       default=lambda x: str(x) if isinstance(x, Fraction) else
                       (_ for _ in ()).throw(TypeError(type(x).__name__))) + '\n').encode()


def run(source, output):
    wall, cpu = time.perf_counter(), time.process_time()
    data = Path(source).read_bytes()
    if sha256(data).hexdigest() != INPUT_SHA256:
        raise ValueError('opened input hash differs')
    record = json.loads(lzma.decompress(data))
    expected = {'version': 'temporal-observability-v1', 'source_commit': SOURCE_COMMIT,
                'protocol_commit': PROTOCOL_COMMIT, 'protocol_sha256': PROTOCOL_SHA256}
    if any(record.get(key) != value for key, value in expected.items()):
        raise ValueError('opened source/protocol binding differs')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    result = audit(record)
    result['input'] = {**expected, 'sha256': INPUT_SHA256, 'source_sha256': record['source_sha256']}
    result['audit_source_sha256'] = sha256(Path(__file__).read_bytes()).hexdigest()
    raw = encode(result)
    (output / 'audit.json').write_bytes(raw)
    receipt = {'audit_sha256': sha256(raw).hexdigest(), 'audit_bytes': len(raw),
               'input_sha256': INPUT_SHA256, 'audit_source_sha256': result['audit_source_sha256'],
               'wall_seconds': time.perf_counter() - wall, 'cpu_seconds': time.process_time() - cpu,
               'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    (output / 'execution.json').write_bytes(encode(receipt))
    return {'summary': result['summary'], **receipt}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'results/temporal-observability-v1/results.json.xz')
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    print(encode(run(arguments.input, arguments.output)).decode(), end='')
