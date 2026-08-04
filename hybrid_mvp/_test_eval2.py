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
accepted_count = 0
abstain_expected = 0
abstain_correct = 0
false_abstain = 0
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
    if accepted:
        accepted_count += 1
    proposed_seq = _program_action_sequence(result.program) if result.program else None
    proposed_types = action_types(proposed_seq) if proposed_seq else None
    proposed_op = operator(proposed_seq) if proposed_seq else None

    if is_abstain:
        if not accepted:
            abstain_correct += 1
    else:
        if not accepted:
            false_abstain += 1

    # Operator match (only for non-abstain)
    if not is_abstain and proposed_op and proposed_op == expected_op:
        operator_match += 1
    if is_abstain and not accepted:
        operator_match += 1  # abstain correct counts

    if proposed_seq == expected_seq:
        exact_match += 1
    if proposed_types and set(proposed_types) == set(expected_types):
        type_set_match += 1
    elif is_abstain and not accepted:
        type_set_match += 1

    if (not is_abstain and proposed_op != expected_op) or (is_abstain and accepted):
        mismatches.append((i, surface[:50], is_abstain, accepted, expected_op, proposed_op))

n = len(episodes)
print(f'Exact match: {exact_match}/{n} = {exact_match/n:.4f}')
print(f'Type set match: {type_set_match}/{n} = {type_set_match/n:.4f}')
print(f'Operator match: {operator_match}/{n} = {operator_match/n:.4f}')
print(f'Accepted: {accepted_count}/{n} = {accepted_count/n:.4f}')
print(f'Abstain: expected={abstain_expected}, correct={abstain_correct}, false_abstain={false_abstain}')
print(f'Abstention precision: {abstain_correct}/{abstain_correct+false_abstain} = {abstain_correct/(abstain_correct+false_abstain) if abstain_correct+false_abstain > 0 else 1.0:.4f}')
print(f'Abstention recall: {abstain_correct}/{abstain_expected} = {abstain_correct/abstain_expected if abstain_expected > 0 else 1.0:.4f}')
print(f'E2E (accepted for non-abstain + not accepted for abstain): {accepted_count - false_abstain + abstain_correct}/{n} = {(accepted_count - false_abstain + abstain_correct)/n:.4f}')
print(f'Mismatches (operator): {len(mismatches)}')
for i, surf, abst, acc, eop, pop in mismatches:
    print(f'  [{i}] {surf} abst={abst} acc={acc} exp_op={eop} got_op={pop}')
