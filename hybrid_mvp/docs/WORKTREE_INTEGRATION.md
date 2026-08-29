# Parallel Worktree Integration Receipt

> **Historical evidence:** This document is retained for analysis and forensic
> provenance only. It owns no current execution or phase status. Current status
> is derived from
> [`governance/replay_status.jsonl`](../governance/replay_status.jsonl).

The MVP was developed in four independent Git worktrees and merged into an isolated integration branch.

## 1. Worktree ownership

| Worktree | Ownership | Tip commit |
|---|---|---|
| `authority` | five-operator types, immutable authority, stores, proof inference | `0146218251fa64d261c879e61ba6df557b2f6110` |
| `neural` | form evidence, retrieval, graph-action candidates, PyTorch ranker, split construction | `12efb42892e10f823c3fa96d8550f13e06a0fd15` |
| `runtime` | recursive compiler, verifier, evaluator, obligations, realization | `3526f03b7199eaaafeccb404b64d10f69e5eba6e` |
| `evaluation` | adversarial tests, validation scripts, initial architecture docs | `cda7d77583ac21f3fb87b7bf9d0887ad295c982d` |

## 2. Merge commits

| Merge | Commit |
|---|---|
| authority worktree | `2e18a99c9daf3375a4a5e70c7b874ba06243a47a` |
| neural worktree | `929f36b58d7a10fc9b8c92c586a4445f539af44c` |
| runtime worktree | `59663872880ea86cfe315fc32babacdd7ce150a0` |
| evaluation worktree | `fd5b14c7d2163bd1392a123c7b8b65fc1838c3b9` |

## 3. Integration hardening after merge

The integration branch then added cross-workstream corrections for:

- closed-class evidence;
- train-only vocabularies;
- content-disjoint lexical partitions;
- explicit-state candidate compatibility;
- model-to-authority content hashing;
- cycle-local event identity;
- capability as recursive event admissibility;
- unspecified event roles as query variables;
- unknown residual coverage;
- typed operation blockers;
- denial realization without internal refs.

## 4. Isolation

The worktrees were created under:

```text
/mnt/data/cemm_authoritative_build/worktrees/
```

The project has its own Git history and does not modify `robosys-labs/cemm`, the deterministic true-hybrid bundle, or the earlier neural MVP bundle.

The release contains `artifacts/worktree_history.bundle` so the full branch and merge history can be inspected independently.
