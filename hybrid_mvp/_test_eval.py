import sys, json
sys.path.insert(0, 'src')
from cemm_authoritative_hybrid.evaluation import build_release_runtime, _anonymize_sequence, _program_action_sequence
from pathlib import Path

ROOT = Path('.')
runtime = build_release_runtime(ROOT)
episodes = [json.loads(l) for l in open('data/partitions/test.jsonl', encoding='utf-8').read().splitlines() if l.strip()]

def action_types(seq):
    return tuple(at for at, args in seq)

def operator(seq):
    for at, args in seq:
        if at == 'instantiate_operator' and args:
            return args[0]
    return None

exact_match = 0
type_set_match = 0
operator_match = 0
abstain_expected = 0
abstain_correct = 0
mismatches = []
for i, ep in enumerate(episodes):
    surface = ep['orientation']['source_text']
    expected_seq = _anonymize_sequence(ep['selected_program']['actions'])
    expected_types = action_types(expected_seq)
    is_abstain = expected_types == ('abstain',)
    expected_op = operator(expected_seq)
    if is_abstain:
        abstain_expected += 1
    result = runtime.propose_and_verify('eval', surface)
    accepted = result.accepted
    proposed_seq = _program_action_sequence(result.program) if result.program else None
    proposed_types = action_types(proposed_seq) if proposed_seq else None
    proposed_op = operator(proposed_seq) if proposed_seq else None

    # Exact match
    if proposed_seq == expected_seq:
        exact_match += 1
    # Type set match
    if proposed_types and set(proposed_types) == set(expected_types):
        type_set_match += 1
    # Operator match
    if proposed_op and proposed_op == expected_op:
        operator_match += 1
    # Abstain
    if is_abstain and not accepted:
        abstain_correct += 1

    if proposed_seq != expected_seq:
        mismatches.append((i, surface[:50], is_abstain, accepted, expected_op, proposed_op, expected_types, proposed_types))

n = len(episodes)
print(f'Exact match: {exact_match}/{n} = {exact_match/n:.4f}')
print(f'Type set match: {type_set_match}/{n} = {type_set_match/n:.4f}')
print(f'Operator match: {operator_match}/{n} = {operator_match/n:.4f}')
print(f'Abstain: expected={abstain_expected}, correct={abstain_correct}')
print(f'Mismatches: {len(mismatches)}')
for i, surf, abst, acc, eop, pop, et, pt in mismatches[:20]:
    print(f'  [{i}] {surf} abst={abst} acc={acc} exp_op={eop} got_op={pop}')
    print(f'    exp_types={et}')
    print(f'    got_types={pt}')
