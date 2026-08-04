import sys, json
sys.path.insert(0, 'src')
from cemm_authoritative_hybrid.evaluation import build_release_runtime, _anonymize_sequence, _program_action_sequence
from pathlib import Path

ROOT = Path('.')
runtime = build_release_runtime(ROOT)
episodes = [json.loads(l) for l in open('data/partitions/test.jsonl', encoding='utf-8').read().splitlines() if l.strip()]

failing_surfaces = ['you cannot learn that', 'teach me', 'cold restart', 'alice likes the book', 'greet carol']
abstain_surfaces = ['available', 'job', 'progenitor', 'role', 'server']

for s in failing_surfaces + abstain_surfaces:
    result = runtime.propose_and_verify('eval', s)
    proposal = result.proposal
    candidates = getattr(proposal, 'candidates', None) if proposal else None
    candidate_types = []
    if candidates:
        for c in candidates:
            seq = _program_action_sequence(c)
            types = tuple(at for at, args in seq)
            candidate_types.append(types)
    print(f'{s}: accepted={result.accepted}, num_candidates={len(candidates) if candidates else 0}, candidate_types={candidate_types[:3]}')
