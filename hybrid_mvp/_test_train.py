import sys, json
sys.path.insert(0, 'src')
from cemm_authoritative_hybrid.evaluation import build_release_runtime, _anonymize_sequence, _program_action_sequence
from pathlib import Path

ROOT = Path('.')
runtime = build_release_runtime(ROOT)
episodes = [json.loads(l) for l in open('data/partitions/train.jsonl', encoding='utf-8').read().splitlines() if l.strip()]

def action_types(seq):
    return tuple(at for at, args in seq)

exact_match = 0
type_set_match = 0
accepted_count = 0
abstain_expected = 0
abstain_correct = 0
false_abstain = 0
for i, ep in enumerate(episodes):
    surface = ep['orientation']['source_text']
    expected_seq = _anonymize_sequence(ep['selected_program']['actions'])
    expected_types = action_types(expected_seq)
    is_abstain = expected_types == ('abstain',)
    if is_abstain:
        abstain_expected += 1
    result = runtime.propose_and_verify('eval', surface)
    accepted = result.accepted
    if accepted:
        accepted_count += 1
    proposed_seq = _program_action_sequence(result.program) if result.program else None
    proposed_types = action_types(proposed_seq) if proposed_seq else None

    if is_abstain:
        if not accepted:
            abstain_correct += 1
    else:
        if not accepted:
            false_abstain += 1

    if proposed_types and set(proposed_types) == set(expected_types):
        type_set_match += 1
    elif is_abstain and not accepted:
        type_set_match += 1

n = len(episodes)
print(f'Train episodes: {n}')
print(f'Type set match: {type_set_match}/{n} = {type_set_match/n:.4f}')
print(f'Accepted: {accepted_count}/{n} = {accepted_count/n:.4f}')
print(f'Abstain: expected={abstain_expected}, correct={abstain_correct}, false_abstain={false_abstain}')
